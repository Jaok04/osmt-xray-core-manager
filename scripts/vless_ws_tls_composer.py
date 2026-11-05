#!/usr/bin/env python3
"""Compositor I-01: VLESS-WS-TLS -> revisión inmutable de perfil Xray.

No activa perfiles ni toca Xray/systemd. La asociación TLS se guarda como
archivo privado independiente, en <mapping-root>/<profile-id>/<revision>.json.
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import os
import pathlib
import re
import stat
import subprocess
import sys
import tempfile
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import xray_profiles
import vless_config_store

PROFILE_RE = re.compile(r"^profile-[0-9a-f]{32}$")
REVISION_RE = re.compile(r"^r[0-9]{6}$")
CONNECTION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
TAG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


class ComposerError(Exception):
    pass


def fail(message: str) -> None:
    raise ComposerError(message)


def read_private_json(path: pathlib.Path, limit: int = 4 * 1024 * 1024) -> Any:
    path = path.absolute()
    xray_profiles.check_no_symlink_components(path)
    if path.is_symlink():
        fail(f"Se rechazó una ruta symlink: {path.name}")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0))
    try:
        st = os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_nlink != 1
                or stat.S_IMODE(st.st_mode) != 0o600 or st.st_size > limit):
            fail(f"Archivo inseguro, permisos incorrectos o tamaño excesivo: {path.name}")
        chunks = []
        while True:
            part = os.read(fd, 65536)
            if not part:
                break
            chunks.append(part)
        raw = b"".join(chunks)
        if len(raw) != st.st_size:
            fail(f"El archivo cambió durante la lectura: {path.name}")
    finally:
        os.close(fd)
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ComposerError(f"JSON inválido: {path.name}") from exc


def fsync_directory(path: pathlib.Path) -> None:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def ensure_private_dir(path: pathlib.Path) -> None:
    path = path.absolute()
    cur = pathlib.Path(path.anchor)
    for part in path.parts[1:]:
        cur = cur / part
        try:
            st = cur.lstat()
        except FileNotFoundError:
            cur.mkdir(mode=0o700)
            fsync_directory(cur.parent)
            st = cur.lstat()
        if not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode):
            fail("La ruta del almacén auxiliar contiene un componente inseguro.")
        if cur == path and (st.st_uid != 0 or stat.S_IMODE(st.st_mode) != 0o700):
            fail("El directorio auxiliar debe ser root:root con modo 0700.")


def atomic_private_write(path: pathlib.Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        fail("El archivo auxiliar de esta revisión ya existe; no se sobrescribirá.")
    fd, temp_name = tempfile.mkstemp(prefix=".i01-", dir=path.parent)
    temp = pathlib.Path(temp_name)
    try:
        os.fchown(fd, 0, 0)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temp, path, follow_symlinks=False)
        temp.unlink()
        fsync_directory(path.parent)
    except Exception:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass
        raise



@contextlib.contextmanager
def shared_locks(paths: list[pathlib.Path]):
    """Bloquea catálogos de conexiones/usuarios en lectura hasta confirmar la revisión."""
    opened = []
    try:
        for path in sorted({p.absolute() for p in paths}, key=str):
            xray_profiles.check_no_symlink_components(path)
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            fd = os.open(path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_nlink != 1:
                os.close(fd)
                fail("Lock de catálogo inseguro.")
            os.fchmod(fd, 0o600)
            fcntl.flock(fd, fcntl.LOCK_SH)
            opened.append(fd)
        yield
    finally:
        for fd in reversed(opened):
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)


def load_vless_ws_tls_config(connection: dict, connections_base: pathlib.Path,
                             certificate_catalog: pathlib.Path) -> dict:
    cid = connection.get("id")
    revision = connection.get("configuration_revision")
    reference = connection.get("configuration_ref")
    if (isinstance(revision, bool) or not isinstance(revision, int) or revision < 1
            or isinstance(connection.get("configuration_schema_version"), bool)
            or connection.get("configuration_schema_version") not in (1, 2)
            or reference != f"configurations/{cid}.r{revision:06d}.json"):
        fail("La conexión no tiene una referencia VLESS persistida íntegra.")
    vless_config_store.check_dir(connections_base)
    config_path = connections_base / reference
    xray_profiles.check_no_symlink_components(config_path.absolute())
    vless_config_store.check_dir(config_path.parent)
    try:
        raw = vless_config_store.read_regular(config_path, vless_config_store.MAX_CONFIG)
        config = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, vless_config_store.StoreError) as exc:
        raise ComposerError("No se pudo leer la configuración VLESS persistida.") from exc
    try:
        vless_config_store.validate_config(config, connection, connection.get("secret_ref"), allow_legacy_tls=False)
        if set(config.get("security_options", {})) != {"certificate_id"}:
            fail("VLESS-WS-TLS requiere un certificado central, no secreto por conexión.")
        vless_config_store.validate_central_certificate(
            config["security_options"]["certificate_id"], certificate_catalog
        )
    except vless_config_store.StoreError as exc:
        raise ComposerError(f"Configuración/certificado VLESS no válido: {exc}") from exc
    return config


def export_candidates(connection_id: str, users_file: pathlib.Path,
                      connections_catalog: pathlib.Path, users_lock: pathlib.Path) -> list[dict]:
    env = os.environ.copy()
    env.update({
        "APP_ROOT": str(ROOT),
        "XRAY_MANAGER_USERS_DIR": str(users_file.parent),
        "XRAY_MANAGER_USERS_FILE": str(users_file),
        "XRAY_MANAGER_CONNECTIONS_FILE": str(connections_catalog),
        "XRAY_MANAGER_INTEGRITY_LOCK": str(users_lock),
    })
    command = [
        "bash", "-c",
        'source "$APP_ROOT/modules/users_v2.sh" && users_v2_export_vless_candidate_clients "$1"',
        "i01-export", connection_id,
    ]
    result = subprocess.run(command, env=env, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        fail("Usuarios V2 no pudo exportar candidatos válidos para la conexión.")
    try:
        clients = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ComposerError("La exportación de Usuarios V2 no produjo JSON válido.") from exc
    if not isinstance(clients, list):
        fail("La exportación de Usuarios V2 debe ser un arreglo.")
    seen = set()
    normalized = []
    for item in clients:
        if not isinstance(item, dict) or set(item) != {"id", "email"}:
            fail("Usuarios V2 devolvió un cliente con estructura inválida.")
        uid, email = item["id"], item["email"]
        if not isinstance(uid, str) or not UUID_RE.fullmatch(uid):
            fail("Usuarios V2 devolvió un UUID inválido.")
        if not isinstance(email, str) or not re.fullmatch(r"assoc:[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", email):
            fail("Usuarios V2 devolvió una referencia de asociación inválida.")
        if uid in seen:
            fail("Usuarios V2 devolvió UUID duplicado.")
        seen.add(uid)
        normalized.append({"id": uid, "email": email})
    return normalized


def read_existing_bindings(path: pathlib.Path | None, tls_tags: set[str]) -> list[dict[str, str]]:
    if not tls_tags:
        if path is None:
            return []
    elif path is None:
        fail("El perfil ya contiene inbounds TLS; se requiere el mapping previo exacto.")
    if path is None:
        return []
    value = read_private_json(path, 1024 * 1024)
    if not isinstance(value, dict) or set(value) != {"schema_version", "bindings"} or value["schema_version"] != 1:
        fail("El mapping previo no cumple el contrato R-02.")
    bindings = value["bindings"]
    if not isinstance(bindings, list):
        fail("bindings del mapping previo debe ser un arreglo.")
    result = []
    tags, connections = set(), set()
    for item in bindings:
        if not isinstance(item, dict) or set(item) != {"inbound_tag", "connection_id"}:
            fail("Entrada inválida en el mapping previo.")
        tag, cid = item["inbound_tag"], item["connection_id"]
        if not isinstance(tag, str) or not TAG_RE.fullmatch(tag):
            fail("Tag inválido en el mapping previo.")
        if not isinstance(cid, str) or not CONNECTION_RE.fullmatch(cid):
            fail("ID de conexión inválido en el mapping previo.")
        if tag in tags or cid in connections:
            fail("El mapping previo contiene tags o conexiones duplicados.")
        tags.add(tag)
        connections.add(cid)
        result.append({"inbound_tag": tag, "connection_id": cid})
    if tags != tls_tags:
        fail("El mapping previo no coincide exactamente con todos los inbounds TLS del perfil.")
    return result


def validate_profile_config(config: Any) -> list[dict]:
    if not isinstance(config, dict) or not isinstance(config.get("inbounds"), list):
        fail("La revisión de perfil debe contener inbounds como arreglo.")
    if not isinstance(config.get("outbounds"), list):
        fail("La revisión de perfil debe contener outbounds como arreglo.")
    inbounds = config["inbounds"]
    tags, ports, uuids = set(), set(), set()
    tls_tags = set()
    for inbound in inbounds:
        if not isinstance(inbound, dict):
            fail("El perfil contiene un inbound inválido.")
        tag = inbound.get("tag")
        if not isinstance(tag, str) or not TAG_RE.fullmatch(tag) or tag in tags:
            fail("El perfil contiene tags ausentes, inválidos o duplicados.")
        tags.add(tag)
        port = inbound.get("port")
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535 or port in ports:
            fail("El perfil contiene puertos inválidos o duplicados.")
        ports.add(port)
        stream = inbound.get("streamSettings", {})
        if not isinstance(stream, dict):
            fail("streamSettings de un inbound no es objeto.")
        if stream.get("security") == "tls":
            tls_tags.add(tag)
        settings = inbound.get("settings", {})
        clients = settings.get("clients", []) if isinstance(settings, dict) else []
        if clients is not None:
            if not isinstance(clients, list):
                fail("La lista clients de un inbound no es válida.")
            for client in clients:
                if isinstance(client, dict) and isinstance(client.get("id"), str):
                    uid = client["id"].lower()
                    if uid in uuids:
                        fail("El perfil ya contiene UUID duplicados.")
                    uuids.add(uid)
    return [{"inbound_tag": tag} for tag in sorted(tls_tags)]


def compose(args: argparse.Namespace) -> dict:
    if os.geteuid() != 0:
        fail("I-01 requiere ejecución root para conservar el modelo de permisos.")
    if not PROFILE_RE.fullmatch(args.profile_id or "") or not REVISION_RE.fullmatch(args.expected_revision or ""):
        fail("profile_id o revisión esperada no válidos.")
    if not CONNECTION_RE.fullmatch(args.connection_id or ""):
        fail("connection_id no válido.")

    connections_path = pathlib.Path(args.connections_catalog)
    connections_base = pathlib.Path(args.connections_base)
    users_file = pathlib.Path(args.users_file).absolute()
    users_lock = pathlib.Path(args.users_lock).absolute()
    connection_lock = pathlib.Path(args.connection_lock).absolute()
    xray_profiles.check_no_symlink_components(users_file)
    xray_profiles.check_no_symlink_components(users_lock)
    xray_profiles.check_no_symlink_components(connection_lock)
    certificate_catalog = pathlib.Path(args.certificate_catalog)

    profiles = xray_profiles.ProfileStore(args.profile_store, args.master_key)
    mapping_root = pathlib.Path(args.mapping_root).absolute()
    ensure_private_dir(mapping_root)
    mapping_profile_dir = mapping_root / args.profile_id
    try:
        mapping_profile_dir.mkdir(mode=0o700)
        os.chown(mapping_profile_dir, 0, 0)
        os.chmod(mapping_profile_dir, 0o700)
        fsync_directory(mapping_root)
    except FileExistsError:
        pass
    st = mapping_profile_dir.lstat()
    if (not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode)
            or st.st_uid != 0 or stat.S_IMODE(st.st_mode) != 0o700):
        fail("Directorio de asociaciones de perfil inseguro.")

    with shared_locks([connection_lock, users_lock]):
        catalog = read_private_json(connections_path)
        if not isinstance(catalog, list) or any(not isinstance(x, dict) for x in catalog):
            fail("El catálogo de conexiones no es un arreglo válido.")
        ids = [x.get("id") for x in catalog]
        if len(ids) != len(set(ids)) or any(not isinstance(x, str) for x in ids):
            fail("El catálogo contiene IDs ausentes o duplicados.")
        matches = [x for x in catalog if x.get("id") == args.connection_id]
        if len(matches) != 1:
            fail("La conexión solicitada no existe exactamente una vez.")
        connection = matches[0]
        if connection.get("protocol_id") != "vless_ws_tls":
            fail("I-01 solo admite conexiones protocol_id=vless_ws_tls.")
        if connection.get("state") != "draft" or connection.get("runtime_applied") is not False:
            fail("La conexión debe permanecer en draft y runtime_applied=false.")
        connection_config = load_vless_ws_tls_config(connection, connections_base, certificate_catalog)
        if (connection_config.get("mode_id") != "vless_ws_tls"
                or connection_config.get("connection_id") != args.connection_id
                or connection_config.get("protocol") != "vless"):
            fail("La configuración persistida no coincide con VLESS-WS-TLS.")
        clients = export_candidates(args.connection_id, users_file, connections_path, users_lock)
        if not clients:
            fail("No hay asociaciones activas y vigentes para esta conexión; no se crea una revisión vacía.")

        with profiles.locked():
            meta = profiles.load_metadata(args.profile_id)
            if meta.get("current_revision") != args.expected_revision:
                fail("La revisión actual cambió; se aborta para evitar TOCTOU.")
            original_bytes, _manifest = profiles.read_revision_config(args.profile_id, args.expected_revision)
            try:
                profile_config = json.loads(original_bytes.decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise ComposerError("La revisión esperada contiene JSON inválido.") from exc
            tls_items = validate_profile_config(profile_config)
            tls_tags = {item["inbound_tag"] for item in tls_items}
            prior = read_existing_bindings(
                pathlib.Path(args.existing_bindings) if args.existing_bindings else None, tls_tags
            )

            inbound_tag = "vless-" + args.connection_id
            if not TAG_RE.fullmatch(inbound_tag):
                fail("El ID de conexión produce un inbound tag no válido.")
            if any(item.get("tag") == inbound_tag for item in profile_config["inbounds"]):
                fail("El inbound tag ya existe en el perfil.")
            port = connection_config["listen_port"]
            if any(item.get("port") == port for item in profile_config["inbounds"]):
                fail("El puerto de la conexión ya está ocupado en el perfil.")
            existing_uuids = set()
            for inbound in profile_config["inbounds"]:
                settings = inbound.get("settings", {})
                for client in settings.get("clients", []) if isinstance(settings, dict) else []:
                    if isinstance(client, dict) and isinstance(client.get("id"), str):
                        existing_uuids.add(client["id"].lower())
            for client in clients:
                if client["id"] in existing_uuids:
                    fail("UUID de Usuarios V2 ya existe en otro inbound del perfil.")

            new_inbound = {
                "tag": inbound_tag,
                "listen": connection_config["listen_address"],
                "port": port,
                "protocol": "vless",
                "settings": {"clients": clients, "decryption": "none"},
                "streamSettings": {
                    "network": "ws",
                    "security": "tls",
                    "wsSettings": ({"path": connection_config["transport_options"]["path"]} |
                                   ({"host": connection_config["transport_options"]["host"]}
                                    if connection_config["transport_options"].get("host") else {})),
                    "tlsSettings": {"certificates": []},
                },
            }
            updated = dict(profile_config)
            updated["inbounds"] = list(profile_config["inbounds"]) + [new_inbound]
            bindings = prior + [{"inbound_tag": inbound_tag, "connection_id": args.connection_id}]
            bindings.sort(key=lambda item: item["inbound_tag"])
            if len({x["inbound_tag"] for x in bindings}) != len(bindings) or len({x["connection_id"] for x in bindings}) != len(bindings):
                fail("El mapping TLS resultante contiene tags o conexiones duplicadas.")

            new_revision = profiles.add_revision(
                args.profile_id,
                (json.dumps(updated, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode(),
                source="vless_ws_tls_composer_i01",
            )
            meta["current_revision"] = new_revision
            meta["config_present"] = True
            meta["last_validated_revision"] = None
            meta["validation_status"] = "not_validated"
            meta["modified_at"] = xray_profiles.utc_now()
            profile_catalog = profiles.load_catalog()
            for item in profile_catalog["profiles"]:
                if item["profile_id"] == args.profile_id:
                    item["modified_at"] = meta["modified_at"]
                    break
            profiles.commit_transaction({
                profiles.profile_dir(args.profile_id) / "metadata.json": xray_profiles.json_bytes(meta),
                profiles.catalog_path: xray_profiles.json_bytes(profile_catalog),
            }, remove_dirs=[profiles.profile_dir(args.profile_id) / "revisions" / new_revision])
    mapping_path = mapping_profile_dir / f"{new_revision}.json"
    mapping_doc = {"schema_version": 1, "bindings": bindings}
    try:
        atomic_private_write(
            mapping_path,
            (json.dumps(mapping_doc, sort_keys=True, separators=(",", ":")) + "\n").encode(),
        )
    except Exception as exc:
        raise ComposerError(
            f"REVISIÓN INCOMPLETA {new_revision}: se creó el perfil pero no se pudo persistir el mapping TLS; "
            "no continuar a R-02. Requiere recuperación explícita."
        ) from exc

    return {
        "status": "COMPOSED",
        "profile_id": args.profile_id,
        "source_revision": args.expected_revision,
        "revision": new_revision,
        "inbound_tag": inbound_tag,
        "connection_id": args.connection_id,
        "clients": len(clients),
        "mapping_file": str(mapping_path),
        "validation_status": "pending",
        "runtime_changed": False,
        "service_started": False,
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="I-01: compone una conexión VLESS-WS-TLS en una nueva revisión de perfil.")
    p.add_argument("--profile-store", required=True)
    p.add_argument("--master-key", required=True)
    p.add_argument("--profile-id", required=True)
    p.add_argument("--expected-revision", required=True)
    p.add_argument("--connection-id", required=True)
    p.add_argument("--connections-catalog", required=True)
    p.add_argument("--connections-base", required=True)
    p.add_argument("--connection-lock", required=True)
    p.add_argument("--users-file", required=True)
    p.add_argument("--users-lock", required=True)
    p.add_argument("--certificate-catalog", required=True)
    p.add_argument("--mapping-root", required=True)
    p.add_argument("--existing-bindings")
    return p


def main() -> int:
    try:
        result = compose(parser().parse_args())
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (ComposerError, xray_profiles.ProfileError, vless_config_store.StoreError,
            OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
