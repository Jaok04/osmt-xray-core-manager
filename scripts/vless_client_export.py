#!/usr/bin/env python3
"""Export exact VLESS-WS-TLS profile revisions as client-importable vless:// URIs."""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import ipaddress
import json
import os
import pathlib
import re
import stat
import sys
import tempfile
from argparse import Namespace
from urllib.parse import quote, urlencode

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import xray_profiles
import vless_config_store

DOMAIN_RE = re.compile(
    r"(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)"
    r"(?:\.(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?))*\.?$"
)
UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)
MAX_MAPPING = 1024 * 1024


class ExportError(Exception):
    pass


def fail(message: str) -> None:
    raise ExportError(message)


def validate_address(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 253 or any(c.isspace() for c in value):
        fail("Endpoint público inválido.")
    try:
        return ipaddress.ip_address(value).compressed
    except ValueError:
        if not DOMAIN_RE.fullmatch(value) or value.endswith(".."):
            fail("El endpoint debe ser un dominio DNS ASCII o una dirección IP.")
        return value.rstrip(".").lower()


def read_private_mapping(path: pathlib.Path) -> dict:
    path = path.absolute()
    xray_profiles.check_no_symlink_components(path)
    try:
        info = path.lstat()
    except FileNotFoundError:
        fail("No existe el mapping privado de la revisión; no se exportará.")
    parent_info = path.parent.lstat()
    if (not stat.S_ISDIR(parent_info.st_mode) or stat.S_ISLNK(parent_info.st_mode) or
            parent_info.st_uid != 0 or parent_info.st_gid != 0 or stat.S_IMODE(parent_info.st_mode) != 0o700):
        fail("El directorio del mapping no es privado root:root 0700.")
    if (not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode) or
            info.st_uid != 0 or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600 or
            info.st_size < 1 or info.st_size > MAX_MAPPING):
        fail("El mapping de la revisión tiene permisos, propietario o tamaño inseguros.")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        opened = os.fstat(fd)
        if (opened.st_dev, opened.st_ino, opened.st_nlink) != (info.st_dev, info.st_ino, 1):
            fail("El mapping cambió durante la apertura.")
        data = b""
        while len(data) <= MAX_MAPPING:
            block = os.read(fd, min(65536, MAX_MAPPING + 1 - len(data)))
            if not block:
                break
            data += block
    finally:
        os.close(fd)
    if len(data) != info.st_size or len(data) > MAX_MAPPING:
        fail("El mapping cambió o supera el tamaño permitido.")
    try:
        value = xray_profiles.strict_json(data, "Mapping privado")
    except xray_profiles.ProfileError as exc:
        raise ExportError("El mapping privado no contiene JSON válido.") from exc
    if not isinstance(value, dict) or set(value) != {"schema_version", "bindings"} or value["schema_version"] != 1:
        fail("Esquema de mapping incompatible.")
    bindings = value["bindings"]
    if not isinstance(bindings, list):
        fail("Las asociaciones del mapping no son una lista.")
    seen_tags, seen_connections = set(), set()
    for item in bindings:
        if (not isinstance(item, dict) or set(item) != {"inbound_tag", "connection_id"} or
                not isinstance(item["inbound_tag"], str) or not item["inbound_tag"] or
                not isinstance(item["connection_id"], str) or not item["connection_id"]):
            fail("Entrada de mapping incompleta o inválida.")
        if item["inbound_tag"] in seen_tags or item["connection_id"] in seen_connections:
            fail("El mapping contiene tags o conexiones duplicadas.")
        seen_tags.add(item["inbound_tag"])
        seen_connections.add(item["connection_id"])
    return {item["inbound_tag"]: item["connection_id"] for item in bindings}


def read_connection_config(args: argparse.Namespace, connection_id: str) -> dict:
    result = vless_config_store.run(Namespace(
        action="read",
        base=args.connections_base,
        catalog=args.connections_catalog,
        lock=args.connection_lock,
        secrets_dir=args.connection_secrets,
        master_key=args.master_key,
        certificate_catalog=args.certificate_catalog,
        connection_id=connection_id,
        secret_output=None,
    ))
    return result["configuration"]


def encode_uri(client_id: str, address: str, port: int, config: dict,
               label: str) -> str:
    if not isinstance(client_id, str) or not UUID_RE.fullmatch(client_id):
        fail("El inbound contiene un UUID de cliente inválido.")
    transport = config["transport_options"]
    client = config.get("client_options", {})
    params = [
        ("encryption", "none"),
        ("security", "tls"),
    ]
    if client.get("tls_server_name"):
        params.append(("sni", client["tls_server_name"]))
    params.append(("type", "ws"))
    if transport.get("host"):
        params.append(("host", transport["host"]))
    params.append(("path", transport["path"]))
    query = urlencode(params, quote_via=quote, safe="")
    fragment = quote(label, safe="-._~")
    try:
        parsed_ip = ipaddress.ip_address(address)
    except ValueError:
        authority = address
    else:
        authority = f"[{address}]" if parsed_ip.version == 6 else address
    return f"vless://{client_id}@{authority}:{port}?{query}#{fragment}"


def atomic_output(path: pathlib.Path, data: bytes) -> None:
    path = path.absolute()
    xray_profiles.check_no_symlink_components(path)
    parent_info = path.parent.lstat()
    if (not stat.S_ISDIR(parent_info.st_mode) or stat.S_ISLNK(parent_info.st_mode) or
            parent_info.st_uid != 0 or stat.S_IMODE(parent_info.st_mode) != 0o700):
        fail("El directorio destino debe ser privado root:root 0700; no se cambiarán sus permisos.")
    if path.exists() or path.is_symlink():
        fail("El destino de exportación ya existe; no se sobrescribirá.")
    fd, temp_name = tempfile.mkstemp(prefix=".vless-export-", dir=path.parent)
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
        dfd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass



def require_private_dir(path: pathlib.Path, label: str) -> None:
    try:
        info = path.lstat()
    except FileNotFoundError as exc:
        raise ExportError(f"No existe el directorio privado {label}.") from exc
    if (not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode) or
            info.st_uid != 0 or info.st_gid != 0 or stat.S_IMODE(info.st_mode) != 0o700):
        fail(f"El directorio {label} no es root:root 0700 o contiene un symlink.")


@contextlib.contextmanager
def profile_read_lock(store: xray_profiles.ProfileStore):
    """Acquire a shared lock without ProfileStore's cleanup/recovery side effects."""
    if os.geteuid() != 0:
        fail("La exportación del almacén de perfiles requiere root.")
    for directory in (store.root, store.profiles):
        try:
            info = directory.lstat()
        except FileNotFoundError as exc:
            raise ExportError("El almacén privado de perfiles no existe.") from exc
        if (not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode) or
                info.st_uid != 0 or info.st_gid != 0 or stat.S_IMODE(info.st_mode) != 0o700):
            fail("Directorio del almacén de perfiles inseguro.")
    lock = store.lock_path
    xray_profiles.check_no_symlink_components(lock)
    try:
        info = lock.lstat()
    except FileNotFoundError as exc:
        raise ExportError("Falta el lock existente del almacén de perfiles.") from exc
    if (not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode) or
            info.st_uid != 0 or info.st_gid != 0 or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600):
        fail("Lock del almacén de perfiles inseguro.")
    fd = os.open(lock, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        opened = os.fstat(fd)
        if (opened.st_dev, opened.st_ino, opened.st_uid, opened.st_nlink) != (
                info.st_dev, info.st_ino, info.st_uid, info.st_nlink):
            fail("El lock del almacén cambió durante la apertura.")
        fcntl.flock(fd, fcntl.LOCK_SH)
        yield
    finally:
        with contextlib.suppress(OSError):
            fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def export_profile(args: argparse.Namespace) -> dict:
    address = validate_address(args.address)
    if isinstance(args.port, bool) or not isinstance(args.port, int) or not 1 <= args.port <= 65535:
        fail("Puerto público inválido.")
    if not re.fullmatch(r"profile-[0-9a-f]{32}", args.profile_id):
        fail("ID de perfil inválido.")
    if not re.fullmatch(r"r[0-9]{6}", args.revision):
        fail("ID de revisión inválido.")
    store = xray_profiles.ProfileStore(args.profile_store, args.master_key)
    with profile_read_lock(store):
        profile_dir = store.profiles / args.profile_id
        revisions_dir = profile_dir / "revisions"
        require_private_dir(profile_dir, "perfil")
        require_private_dir(revisions_dir, "revisiones")
        # Validate every revision directory first: ProfileStore's validators may
        # repair directory modes, which this export-only operation must not do.
        for entry in revisions_dir.iterdir():
            if entry.name.startswith("."):
                continue
            if not re.fullmatch(r"r[0-9]{6}", entry.name):
                fail("El almacén contiene una entrada de revisión desconocida.")
            require_private_dir(entry, "revisión")
        revision_dir = revisions_dir / args.revision
        require_private_dir(revision_dir, "revisión solicitada")
        metadata = store.load_metadata(args.profile_id)
        raw, manifest = store.read_revision_config(args.profile_id, args.revision)
        if manifest["validation"]["status"] == "invalid":
            fail("No se exportan clientes desde una revisión marcada como inválida.")
        try:
            profile_config = json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ExportError("La revisión no contiene JSON válido.") from exc
        if not isinstance(profile_config, dict) or not isinstance(profile_config.get("inbounds"), list):
            fail("La revisión no contiene una lista válida de inbounds.")
        mapping_path = pathlib.Path(args.mapping_root) / args.profile_id / f"{args.revision}.json"
        bindings = read_private_mapping(mapping_path)
        all_central_tls = [
            inbound for inbound in profile_config["inbounds"]
            if isinstance(inbound, dict)
            and isinstance(inbound.get("streamSettings"), dict)
            and inbound["streamSettings"].get("security") == "tls"
            and isinstance(inbound["streamSettings"].get("tlsSettings"), dict)
            and inbound["streamSettings"]["tlsSettings"].get("certificates") == []
        ]
        all_tls_tags = {item.get("tag") for item in all_central_tls}
        if None in all_tls_tags or len(all_tls_tags) != len(all_central_tls) or set(bindings) != all_tls_tags:
            fail("El mapping no coincide exactamente con todos los inbounds TLS centralizados de la revisión.")
        inbound_matches = [
            inbound for inbound in all_central_tls
            if inbound.get("protocol") == "vless"
            and inbound.get("streamSettings", {}).get("network") == "ws"
        ]
        if not inbound_matches:
            fail("La revisión no contiene inbounds VLESS-WS-TLS para exportar.")
        uris = []
        exported_tags = set()
        exported_uuids = set()
        for inbound in inbound_matches:
            tag = inbound.get("tag")
            if not isinstance(tag, str) or not tag or tag in exported_tags:
                fail("Tag VLESS-WS-TLS ausente o duplicado.")
            exported_tags.add(tag)
            connection_id = bindings.get(tag)
            if not connection_id:
                fail(f"El inbound {tag} no tiene asociación inequívoca en el mapping.")
            if inbound.get("port") != args.port:
                fail(f"El puerto del inbound {tag} no coincide con el puerto público {args.port}.")
            stream = inbound["streamSettings"]
            ws = stream.get("wsSettings")
            tls = stream.get("tlsSettings")
            if (not isinstance(ws, dict) or not isinstance(ws.get("path"), str) or
                    not ws["path"].startswith("/") or
                    not isinstance(tls, dict) or tls.get("certificates") != []):
                fail(f"El inbound {tag} no cumple el contrato WS-TLS centralizado.")
            settings = inbound.get("settings")
            clients = settings.get("clients") if isinstance(settings, dict) else None
            if not isinstance(clients, list) or not clients:
                fail(f"El inbound {tag} no contiene clientes exportables.")
            source = read_connection_config(args, connection_id)
            if (source.get("mode_id") != "vless_ws_tls" or source.get("transport") != "websocket" or
                    source.get("security") != "tls" or source.get("listen_port") != args.port or
                    source.get("transport_options", {}).get("path") != ws["path"] or
                    source.get("transport_options", {}).get("host") != ws.get("host")):
                fail(f"La configuración fuente de {tag} no coincide con el inbound del perfil.")
            client_options = source.get("client_options", {})
            if not isinstance(client_options, dict):
                fail(f"Opciones de cliente inválidas para {tag}.")
            inbound_ids = set()
            for index, client in enumerate(clients, start=1):
                if not isinstance(client, dict) or set(client) - {"id", "email", "flow"}:
                    fail(f"Cliente {index} de {tag} tiene campos inesperados.")
                if client.get("flow") not in (None, ""):
                    fail(f"Cliente {index} de {tag} declara un flow no compatible con WS-TLS.")
                client_id = client.get("id")
                if not isinstance(client_id, str) or client_id in inbound_ids or client_id in exported_uuids:
                    fail(f"UUID ausente o duplicado en el perfil/inbound {tag}.")
                inbound_ids.add(client_id)
                exported_uuids.add(client_id)
                label = f"{args.profile_id}-{tag}-{index}"
                uris.append(encode_uri(client_id, address, args.port, {
                    "transport_options": source["transport_options"],
                    "client_options": client_options,
                }, label))
        result = {
            "status": "EXPORTED",
            "profile_id": args.profile_id,
            "revision": args.revision,
            "profile_name": metadata["name"],
            "endpoint": f"[{address}]:{args.port}" if ":" in address else f"{address}:{args.port}",
            "validation_status": manifest["validation"]["status"],
            "clients": len(uris),
            "uris": uris,
            "runtime_changed": False,
            "service_started": False,
            "dns_changed": False,
            "firewall_changed": False,
        }
    if args.output:
        payload = ("\n".join(result["uris"]) + "\n").encode("utf-8")
        atomic_output(pathlib.Path(args.output), payload)
        result["output_file"] = str(pathlib.Path(args.output).absolute())
        result["output_mode"] = "0600"
    result["uri_sha256"] = hashlib.sha256("\n".join(result["uris"]).encode()).hexdigest()
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-store", required=True)
    parser.add_argument("--master-key", required=True)
    parser.add_argument("--profile-id", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--mapping-root", required=True)
    parser.add_argument("--connections-base", required=True)
    parser.add_argument("--connections-catalog", required=True)
    parser.add_argument("--connection-lock", required=True)
    parser.add_argument("--connection-secrets", required=True)
    parser.add_argument("--certificate-catalog", required=True)
    parser.add_argument("--address", required=True)
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--output")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = export_profile(args)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return 0
    except (ExportError, xray_profiles.ProfileError, vless_config_store.StoreError,
            OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
