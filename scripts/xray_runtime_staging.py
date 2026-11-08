#!/usr/bin/env python3
"""Staging aislado de una revisión de perfil con asociaciones TLS explícitas.

No publica configuración runtime ni inicia/reinicia servicios. Los leases se
obtienen del resolutor central y permanecen vivos junto al staging aprobado.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import certificate_resolver
import xray_profiles
import xray_runtime_preflight
import xray_runtime_staging_core as staging_core

PROFILE_RE = re.compile(r"profile-[0-9a-f]{32}\Z")
REVISION_RE = re.compile(r"r[0-9]{6}\Z")
TAG_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
CONNECTION_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
MAX_BINDINGS = 256
MAX_MAPPING = 256 * 1024
MAX_CONFIG = 16 * 1024 * 1024


class StagingError(Exception):
    pass


def fail(message: str) -> None:
    raise StagingError(message)


def _reject_symlink_components(path: Path, label: str) -> None:
    if not path.is_absolute():
        fail(f"{label} debe ser una ruta absoluta.")
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode):
            fail(f"{label} contiene un componente symlink.")


def _strict_json(data: bytes, label: str) -> Any:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate")
            result[key] = value
        return result
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError("constant")))
    except (UnicodeError, ValueError, json.JSONDecodeError):
        fail(f"{label} no contiene JSON estricto.")


def _check_fixture_root(path: Path) -> Path:
    if not path.is_absolute():
        fail("fixture_root debe ser absoluto.")
    _reject_symlink_components(path, "fixture_root")
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_gid != 0
            or stat.S_IMODE(info.st_mode) & 0o022):
        fail("fixture_root debe ser un directorio root:root no modificable por grupo/otros.")
    marker = path / ".xray-manager-r02-fixture"
    raw = _read_root_fixture_marker(marker)
    if raw != {"schema_version": 1, "purpose": "xray-runtime-r02-isolated-fixture"}:
        fail("fixture_root no tiene el marcador de entorno aislado R-02.")
    return Path(os.path.abspath(path))


def _read_root_fixture_marker(path: Path) -> dict:
    _reject_symlink_components(path, "Marcador fixture")
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0))
    except OSError:
        fail("No se pudo abrir el marcador fixture obligatorio.")
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_gid != 0
                or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600
                or info.st_size < 1 or info.st_size > 4096):
            fail("Marcador fixture inseguro.")
        data = os.read(fd, 4097)
        if len(data) != info.st_size or len(data) > 4096:
            fail("Marcador fixture cambió durante su lectura.")
    finally:
        os.close(fd)
    value = _strict_json(data, "Marcador fixture")
    if not isinstance(value, dict):
        fail("Marcador fixture inválido.")
    return value


def _ensure_lease_root_fixture(path: Path, service_gid: int) -> None:
    _reject_symlink_components(path, "lease_root")
    parent = path.parent
    parent_info = parent.lstat()
    if (not stat.S_ISDIR(parent_info.st_mode) or parent_info.st_uid != 0
            or parent_info.st_gid != 0 or stat.S_IMODE(parent_info.st_mode) & 0o022):
        fail("El padre de lease_root debe ser root:root y no modificable por grupo/otros.")
    if not path.exists():
        os.mkdir(path, 0o750)
        os.chown(path, 0, service_gid)
        os.chmod(path, 0o750)
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode)
            or info.st_uid != 0 or info.st_gid != service_gid
            or stat.S_IMODE(info.st_mode) != 0o750):
        fail("lease_root debe ser root:grupo-servicio modo 0750.")
    marker = path / ".xray-manager-r02-leases-fixture"
    marker_data = json.dumps(
        {"schema_version": 1, "purpose": "xray-runtime-r02-isolated-leases"},
        sort_keys=True, separators=(",", ":")
    ).encode() + b"\n"
    if marker.exists() or marker.is_symlink():
        fd = os.open(marker, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            st = os.fstat(fd)
            raw = os.read(fd, 4097)
            if (not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_gid != service_gid
                    or st.st_nlink != 1 or stat.S_IMODE(st.st_mode) != 0o640
                    or len(raw) != st.st_size or raw != marker_data):
                fail("Marcador lease_root inseguro o incompatible.")
        finally:
            os.close(fd)
    else:
        fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                     | getattr(os, "O_NOFOLLOW", 0), 0o640)
        try:
            os.fchown(fd, 0, service_gid)
            os.fchmod(fd, 0o640)
            os.write(fd, marker_data)
            os.fsync(fd)
        finally:
            os.close(fd)
        dir_fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)


def _require_fixture_path(root: Path, value: str | Path, label: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        fail(f"{label} debe ser una ruta absoluta dentro de fixture_root.")
    absolute = Path(os.path.abspath(path))
    try:
        absolute.relative_to(root)
    except ValueError:
        fail(f"{label} debe permanecer dentro de fixture_root; se bloquea acceso a datos live.")
    _reject_symlink_components(absolute, label)
    return absolute


def _read_mapping(path: Path) -> tuple[list[dict[str, str]], bytes]:
    if not path.is_absolute():
        fail("La ruta de asociaciones debe ser absoluta.")
    _reject_symlink_components(path, "La ruta de asociaciones")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0))
    try:
        st = os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_gid != 0
                or st.st_nlink != 1 or stat.S_IMODE(st.st_mode) != 0o600
                or st.st_size < 1 or st.st_size > MAX_MAPPING):
            fail("El archivo de asociaciones debe ser regular, root:root 0600 y estar dentro del límite.")
        chunks = []
        while True:
            part = os.read(fd, 65536)
            if not part:
                break
            chunks.append(part)
        data = b"".join(chunks)
        if len(data) != st.st_size:
            fail("El archivo de asociaciones cambió durante su lectura.")
    finally:
        os.close(fd)
    value = _strict_json(data, "El mapa de asociaciones")
    if not isinstance(value, dict) or set(value) != {"schema_version", "bindings"} or value["schema_version"] != 1:
        fail("El mapa debe usar schema_version 1 y el campo bindings.")
    bindings = value["bindings"]
    if not isinstance(bindings, list) or not 1 <= len(bindings) <= MAX_BINDINGS:
        fail("bindings debe contener entre 1 y 256 asociaciones.")
    normalized = []
    seen_tags, seen_connections = set(), set()
    for item in bindings:
        if not isinstance(item, dict) or set(item) != {"inbound_tag", "connection_id"}:
            fail("Cada asociación requiere exactamente inbound_tag y connection_id.")
        tag, cid = item["inbound_tag"], item["connection_id"]
        if not isinstance(tag, str) or not TAG_RE.fullmatch(tag):
            fail("inbound_tag inválido.")
        if not isinstance(cid, str) or not CONNECTION_RE.fullmatch(cid):
            fail("connection_id inválido.")
        if tag in seen_tags:
            fail("Un inbound tag no puede tener más de una asociación.")
        if cid in seen_connections:
            fail("Una conexión central no puede reutilizarse en dos inbounds del mismo staging.")
        seen_tags.add(tag)
        seen_connections.add(cid)
        normalized.append({"inbound_tag": tag, "connection_id": cid})
    normalized.sort(key=lambda item: item["inbound_tag"])
    return normalized, data


def _read_profile(profiles: xray_profiles.ProfileStore, profile_id: str, revision: str) -> tuple[bytes, dict]:
    if not PROFILE_RE.fullmatch(profile_id) or not REVISION_RE.fullmatch(revision):
        fail("profile_id o revision inválido.")
    lock_fd = xray_runtime_preflight._profile_read_lock(profiles)
    try:
        metadata = profiles.load_metadata(profile_id)
        content, manifest = profiles.read_revision_config(profile_id, revision)
        if revision == metadata["current_revision"] and (
            metadata["validation_status"] != "valid" or metadata["last_validated_revision"] != revision
        ):
            fail("La revisión actual no consta como validada.")
        validation = manifest["validation"]
        if validation["json_syntax"] != "pass" or validation["xray_static"] != "pass" or validation["status"] != "valid":
            fail("El manifiesto de la revisión no acredita validación.")
        return content, manifest
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


def _connection_certificate_id(args: argparse.Namespace, connection_id: str) -> tuple[str, str]:
    entries = certificate_resolver._load_connections(Path(args.connections_catalog))
    matches = [item for item in entries if item.get("id") == connection_id]
    if len(matches) != 1:
        fail("La asociación apunta a una conexión central inexistente o ambigua.")
    entry = matches[0]
    config, protocol = certificate_resolver._connection_config(
        entry, connection_id, Path(args.connections_base), Path(args.vmess_base)
    )
    if config.get("security") != "tls":
        fail("La conexión asociada no usa TLS central.")
    options = config.get("security_options")
    if not isinstance(options, dict) or set(options) != {"certificate_id"}:
        fail("La conexión no referencia un certificado central administrado.")
    certificate_id = options["certificate_id"]
    if not isinstance(certificate_id, str) or not certificate_resolver.CERTIFICATE_ID_RE.fullmatch(certificate_id):
        fail("certificate_id central inválido.")
    return certificate_id, protocol


def _service_run(binary: Path, config_path: Path, uid: int, gid: int, timeout: int) -> None:
    def demote():
        os.setgroups([])
        os.setgid(gid)
        os.setuid(uid)
    try:
        result = subprocess.run(
            [str(binary), "run", "-test", "-config", str(config_path)],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            env={"PATH": "/usr/bin:/bin", "HOME": "/nonexistent", "LANG": "C", "LC_ALL": "C"},
            timeout=timeout, check=False, preexec_fn=demote,
        )
    except subprocess.TimeoutExpired:
        fail("La validación nativa bajo identidad de servicio excedió el timeout.")
    except OSError:
        fail("No fue posible ejecutar Xray bajo la identidad de servicio.")
    if result.returncode != 0:
        fail(f"Xray rechazó la configuración staged bajo identidad de servicio (código {result.returncode}).")


def _write_file(path: Path, data: bytes, gid: int, mode: int) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), mode)
    try:
        os.fchown(fd, 0, gid)
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(fd)
    finally:
        os.close(fd)


def stage(args: argparse.Namespace) -> dict[str, Any]:
    if os.geteuid() != 0:
        fail("R-02 staging requiere root.")
    if not 1 <= args.timeout <= 120:
        fail("Timeout fuera del rango permitido.")
    if args.service_uid <= 0 or args.service_gid <= 0:
        fail("La identidad de servicio simulada debe ser no privilegiada.")
    fixture = _check_fixture_root(Path(args.fixture_root))
    for attr, label in (
        ("profile_store", "profile_store"), ("master_key", "master_key"),
        ("validation_store", "validation_store"), ("service_state", "service_state"),
        ("bindings_file", "bindings_file"), ("staging_root", "staging_root"),
        ("lease_root", "lease_root"), ("connections_catalog", "connections_catalog"),
        ("connections_base", "connections_base"), ("vmess_base", "vmess_base"),
        ("connection_lock", "connection_lock"), ("certificate_catalog", "certificate_catalog"),
        ("certificate_base", "certificate_base"), ("managed_dir", "managed_dir"),
        ("certificate_secrets_dir", "certificate_secrets_dir"),
        ("certificate_lock", "certificate_lock"), ("certificate_master_key", "certificate_master_key"),
    ):
        setattr(args, attr, str(_require_fixture_path(fixture, getattr(args, attr), label)))
    profiles = xray_profiles.ProfileStore(args.profile_store, args.master_key)
    validation = xray_runtime_preflight.preflight(
        args.profile_store, args.master_key, args.validation_store,
        args.profile_id, args.revision, args.xray_binary, args.service_state,
    )
    content, _manifest = _read_profile(profiles, args.profile_id, args.revision)
    digest = hashlib.sha256(content).hexdigest()
    if digest != validation["content_sha256"]:
        fail("La revisión cambió después del preflight.")
    document = _strict_json(content, "La revisión de perfil")
    bindings, mapping_bytes = _read_mapping(Path(args.bindings_file))
    try:
        inbound_by_tag = staging_core.validate_profile_bindings(document, bindings)
    except staging_core.StagingCoreError as exc:
        fail(str(exc))

    leases = []
    staging_dir = None
    try:
        staging_root = Path(args.staging_root)
        if not staging_root.is_absolute():
            fail("staging_root debe ser absoluto.")
        _reject_symlink_components(staging_root, "staging_root")
        parent_stat = staging_root.parent.lstat()
        if (not stat.S_ISDIR(parent_stat.st_mode) or stat.S_ISLNK(parent_stat.st_mode)
                or parent_stat.st_uid != 0 or parent_stat.st_gid != 0
                or stat.S_IMODE(parent_stat.st_mode) & 0o022):
            fail("El padre de staging_root debe ser un directorio root:root no modificable por grupo/otros.")
        if staging_root.exists():
            root_stat = staging_root.lstat()
            if (not stat.S_ISDIR(root_stat.st_mode) or stat.S_ISLNK(root_stat.st_mode)
                    or root_stat.st_uid != 0 or root_stat.st_gid != 0
                    or stat.S_IMODE(root_stat.st_mode) != 0o711):
                fail("staging_root existente debe ser root:root modo 0711.")
        else:
            # No se crean ancestros ni se cambian permisos de directorios ajenos.
            if not staging_root.parent.is_dir():
                fail("El directorio padre de staging_root debe existir previamente.")
            os.mkdir(staging_root, 0o711)
            os.chown(staging_root, 0, 0)
            os.chmod(staging_root, 0o711)
        staging_dir = Path(tempfile.mkdtemp(prefix="r02-", dir=staging_root))
        os.chown(staging_dir, 0, args.service_gid)
        os.chmod(staging_dir, 0o750)
        _ensure_lease_root_fixture(Path(args.lease_root), args.service_gid)

        for binding in bindings:
            tag, connection_id = binding["inbound_tag"], binding["connection_id"]
            if tag not in inbound_by_tag:
                fail("Una asociación apunta a un inbound tag que no existe.")
            certificate_id, protocol = _connection_certificate_id(args, connection_id)
            lease = certificate_resolver.prepare(
                connection_id=connection_id, certificate_id=certificate_id,
                connections_catalog=Path(args.connections_catalog),
                connections_base=Path(args.connections_base), vmess_base=Path(args.vmess_base),
                connection_lock=Path(args.connection_lock),
                certificate_catalog=Path(args.certificate_catalog),
                certificate_base=Path(args.certificate_base), managed_dir=Path(args.managed_dir),
                certificate_secrets_dir=Path(args.certificate_secrets_dir),
                certificate_lock=Path(args.certificate_lock),
                master_key_file=Path(args.certificate_master_key),
                runtime_root=Path(args.lease_root),
                service_uid=args.service_uid, service_gid=args.service_gid,
            )
            leases.append(lease)
            try:
                staging_core.inject_tls_lease(
                    document, tag, connection_id, certificate_id, protocol, lease
                )
            except staging_core.StagingCoreError as exc:
                fail(str(exc))

        # Segunda comprobación TOCTOU: perfil, informe, binario e identidad
        # deben seguir correspondiendo a la misma revisión después de resolver leases.
        final_preflight = xray_runtime_preflight.preflight(
            args.profile_store, args.master_key, args.validation_store,
            args.profile_id, args.revision, args.xray_binary, args.service_state,
        )
        current_content, _ = _read_profile(profiles, args.profile_id, args.revision)
        if (final_preflight["validation_id"] != validation["validation_id"]
                or final_preflight["content_sha256"] != digest or current_content != content):
            fail("El perfil o su informe cambió durante el staging; se aborta por TOCTOU.")

        staged_bytes = (json.dumps(document, ensure_ascii=False, sort_keys=True,
                                   separators=(",", ":"), allow_nan=False) + "\n").encode()
        if len(staged_bytes) > MAX_CONFIG:
            fail("La configuración staged excede el límite.")
        config_path = staging_dir / "config.json"
        _write_file(config_path, staged_bytes, args.service_gid, 0o640)
        _service_run(Path(args.xray_binary), config_path, args.service_uid, args.service_gid, args.timeout)

        manifest = {
            "schema_version": 1,
            "status": "STAGED",
            "fixture_root": str(fixture),
            "staging_dir": str(staging_dir.absolute()),
            "lease_root": str(Path(args.lease_root)),
            "profile_id": args.profile_id,
            "revision": args.revision,
            "validation_id": validation["validation_id"],
            "profile_content_sha256": digest,
            "bindings_sha256": hashlib.sha256(mapping_bytes).hexdigest(),
            "bindings": [
                {"inbound_tag": b["inbound_tag"], "connection_id": b["connection_id"]}
                for b in bindings
            ],
            "leases": [
                {
                    "lease_id": item["lease_id"],
                    "connection_id": item["connection_id"],
                    "protocol": item["protocol"],
                    "certificate_id": item["certificate_id"],
                }
                for item in leases
            ],
            "staged_config_sha256": hashlib.sha256(staged_bytes).hexdigest(),
            "staged_config_size_bytes": len(staged_bytes),
            "service_identity": {"uid": args.service_uid, "gid": args.service_gid},
            "xray_binary": final_preflight["xray"],
            "native_validation": "PASS",
            "runtime_published": False,
            "service_started": False,
        }
        manifest_bytes = (json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode()
        _write_file(staging_dir / "manifest.json", manifest_bytes, args.service_gid, 0o640)
        dir_fd = os.open(staging_dir, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
        return {
            "status": "STAGED",
            "profile_id": args.profile_id,
            "revision": args.revision,
            "validation_id": validation["validation_id"],
            "staging_dir": str(staging_dir),
            "config_path": str(config_path),
            "manifest_path": str(staging_dir / "manifest.json"),
            "staged_config_sha256": manifest["staged_config_sha256"],
            "lease_ids": [item["lease_id"] for item in leases],
            "runtime_published": False,
            "service_started": False,
        }
    except Exception as original_error:
        cleanup_failures = []
        if staging_dir is not None and staging_dir.exists() and not staging_dir.is_symlink():
            try:
                shutil.rmtree(staging_dir)
            except OSError:
                cleanup_failures.append("staging_dir:" + staging_dir.name)
        for item in reversed(leases):
            try:
                certificate_resolver.cleanup(Path(args.lease_root), item["lease_id"], args.service_gid)
            except Exception:
                cleanup_failures.append(item["lease_id"])
        if cleanup_failures:
            fail(
                "Falló R-02 y no se pudieron liberar todos los leases; "
                "requieren limpieza manual: " + ", ".join(cleanup_failures)
            )
        raise original_error


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("fixture-root", "profile-store", "master-key", "validation-store", "profile-id", "revision",
                 "xray-binary", "service-state", "bindings-file"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--service-uid", type=int, required=True)
    p.add_argument("--service-gid", type=int, required=True)
    p.add_argument("--staging-root", required=True)
    p.add_argument("--lease-root", required=True)
    p.add_argument("--timeout", type=int, default=20)
    for name in (
        "connections-catalog", "connections-base", "vmess-base", "connection-lock",
        "certificate-base", "certificate-catalog", "managed-dir",
        "certificate-secrets-dir", "certificate-lock", "certificate-master-key",
    ):
        p.add_argument("--" + name, required=True)
    return p


def main() -> int:
    args = parser().parse_args()
    try:
        result = stage(args)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (StagingError, xray_profiles.ProfileError, certificate_resolver.ResolverError,
            xray_runtime_preflight.RuntimePreflightError, OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
