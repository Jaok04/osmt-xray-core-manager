#!/usr/bin/env python3
"""Resolución autorizada y temporal de certificados TLS centralizados."""
from __future__ import annotations

import argparse
import fcntl
import grp
import json
import os
import pwd
import re
import shutil
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import certificate_crypto as crypto
import certificate_store as store
import vmess_config_store
import vless_config_store

CONNECTION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
CERTIFICATE_ID_RE = store.ID_RE
LEASE_RE = re.compile(r"^resolve-[0-9a-f]{32}$")
MAX_CONFIG_BYTES = 256 * 1024


class ResolverError(Exception):
    """Error seguro del resolutor."""


def _safe_read(path: Path, limit: int, *, private: bool = True, expected_gid: int = 0, expected_mode: int = 0o600) -> bytes:
    try:
        before = path.lstat()
    except OSError as exc:
        raise ResolverError("falta un archivo requerido") from exc
    if (
        not stat.S_ISREG(before.st_mode)
        or stat.S_ISLNK(before.st_mode)
        or before.st_nlink != 1
        or before.st_uid != 0
        or before.st_gid != expected_gid
        or (private and stat.S_IMODE(before.st_mode) != expected_mode)
        or before.st_size < 1
        or before.st_size > limit
    ):
        raise ResolverError("archivo de configuración inseguro")
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "rb") as stream:
            current = os.fstat(stream.fileno())
            if (
                current.st_dev, current.st_ino, current.st_uid, current.st_gid,
                stat.S_IMODE(current.st_mode), current.st_nlink, current.st_size
            ) != (
                before.st_dev, before.st_ino, before.st_uid, before.st_gid,
                stat.S_IMODE(before.st_mode), before.st_nlink, before.st_size
            ):
                raise ResolverError("archivo cambió durante su apertura")
            data = stream.read(limit + 1)
    except OSError as exc:
        raise ResolverError("no se pudo leer un archivo requerido") from exc
    if len(data) != before.st_size or len(data) > limit:
        raise ResolverError("archivo cambió durante su lectura")
    return data


def _check_private_dir(path: Path) -> None:
    try:
        store.safe_dir(path)
    except (store.StoreError, OSError) as exc:
        raise ResolverError("directorio de datos debe ser una ruta root:root 0700 sin symlinks") from exc


def _acquire_lock(path: Path) -> int:
    _check_private_dir(path.parent)
    if path.exists() or path.is_symlink():
        st = path.lstat()
        if (
            not stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode)
            or st.st_uid != 0 or st.st_gid != 0
            or stat.S_IMODE(st.st_mode) != 0o600 or st.st_nlink != 1
        ):
            raise ResolverError("bloqueo inseguro")
    fd = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    os.fchown(fd, 0, 0)
    os.fchmod(fd, 0o600)
    fcntl.flock(fd, fcntl.LOCK_EX)
    return fd


def _load_connections(path: Path) -> list[dict[str, Any]]:
    raw = _safe_read(path, 4 * 1024 * 1024)
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ResolverError("catálogo de conexiones corrupto") from exc
    if not isinstance(value, list) or not all(isinstance(x, dict) for x in value):
        raise ResolverError("estructura del catálogo de conexiones no válida")
    ids = [x.get("id") for x in value]
    if (
        any(not isinstance(x, str) or not CONNECTION_ID_RE.fullmatch(x) for x in ids)
        or len(ids) != len(set(ids))
    ):
        raise ResolverError("identificadores del catálogo de conexiones no válidos")
    return value


def _connection_config(
    entry: dict[str, Any],
    connection_id: str,
    connections_base: Path,
    vmess_base: Path,
) -> tuple[dict[str, Any], str]:
    protocol_id = entry.get("protocol_id")
    if not isinstance(protocol_id, str):
        raise ResolverError("protocolo de conexión no válido")
    if protocol_id.startswith("vmess_"):
        protocol = "vmess"
        ref_field = "vmess_configuration_ref"
        revision_field = "vmess_configuration_revision"
        schema_field = "vmess_configuration_schema_version"
        base = vmess_base
    elif protocol_id.startswith("vless_"):
        protocol = "vless"
        ref_field = "configuration_ref"
        revision_field = "configuration_revision"
        schema_field = "configuration_schema_version"
        base = connections_base
    else:
        raise ResolverError("el resolutor TLS sólo admite conexiones VMess o VLESS")

    ref = entry.get(ref_field)
    match = re.fullmatch(
        rf"configurations/{re.escape(connection_id)}\.r([0-9]{{6}})\.json",
        ref if isinstance(ref, str) else "",
    )
    revision = entry.get(revision_field)
    schema = entry.get(schema_field)
    if (
        not match or isinstance(revision, bool) or type(revision) is not int
        or revision != int(match.group(1))
        or isinstance(schema, bool) or type(schema) is not int or schema != 1
    ):
        raise ResolverError("referencia o revisión de configuración no válida")
    config_dir = base / "configurations"
    _check_private_dir(base)
    _check_private_dir(config_dir)
    raw = _safe_read(config_dir / f"{connection_id}.r{revision:06d}.json", MAX_CONFIG_BYTES)
    try:
        config = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ResolverError("configuración de conexión corrupta") from exc
    expected_fields = {
        "schema_version", "connection_id", "protocol", "mode_id", "transport",
        "security", "listen_address", "listen_port", "transport_options",
        "security_options",
    }
    if protocol == "vmess":
        expected_fields.add("users")
    modes = vmess_config_store.MODES if protocol == "vmess" else vless_config_store.MODES
    mode_contract = modes.get(protocol_id)
    if (
        not isinstance(config, dict) or set(config) != expected_fields
        or isinstance(config.get("schema_version"), bool)
        or type(config.get("schema_version")) is not int
        or config["schema_version"] != 1
        or config.get("connection_id") != connection_id
        or config.get("protocol") != protocol
        or config.get("mode_id") != protocol_id
        or mode_contract is None
        or (config.get("transport"), config.get("security")) != mode_contract
        or config.get("security") != "tls"
        or config.get("security_options") is None
        or not isinstance(config.get("security_options"), dict)
        or not isinstance(config.get("transport_options"), dict)
        or not isinstance(config.get("listen_address"), str)
        or not config.get("listen_address")
        or isinstance(config.get("listen_port"), bool)
        or type(config.get("listen_port")) is not int
        or config.get("listen_port") != entry.get("port")
        or not isinstance(entry.get("state"), str)
        or not isinstance(entry.get("runtime_applied"), bool)
    ):
        raise ResolverError("la configuración no es una conexión TLS central válida")
    return config, protocol


def _certificate_record(
    certificate_id: str,
    catalog: dict[str, Any],
    managed_dir: Path,
    secrets_dir: Path,
    master_key_file: Path,
) -> tuple[bytes, bytes, dict[str, Any]]:
    matches = [
        item for item in catalog["certificates"]
        if item.get("certificate_id") == certificate_id
    ]
    if len(matches) != 1:
        raise ResolverError("certificado central no encontrado")
    item = matches[0]
    if item.get("status") != "active" or item.get("revision") != 1:
        raise ResolverError("certificado central inactivo o revisión no soportada")
    if item["storage_type"] == "managed":
        if item["certificate_source"] != f"managed/{certificate_id}.pem":
            raise ResolverError("referencia managed no válida")
        _check_private_dir(managed_dir)
        cert_path = managed_dir / f"{certificate_id}.pem"
        certificate_bytes = store.read_regular(
            cert_path, store.MAX_CERTIFICATE_BYTES, require_private=True
        )
    elif item["storage_type"] == "reference":
        cert_path = Path(item["certificate_source"])
        if not cert_path.is_absolute():
            raise ResolverError("referencia externa no válida")
        certificate_bytes = store.read_regular(
            cert_path, store.MAX_CERTIFICATE_BYTES
        )
    else:
        raise ResolverError("tipo de almacenamiento no admitido")
    expected_secret = f"secrets/{certificate_id}.r000001.bin"
    if item.get("secret_ref") != expected_secret:
        raise ResolverError("referencia al secreto central no válida")
    _check_private_dir(secrets_dir)
    blob = store.read_regular(
        secrets_dir / f"{certificate_id}.r000001.bin",
        crypto.MAX_BLOB_BYTES,
        require_private=True,
    )
    key = crypto.load_master_key(master_key_file)
    private_key_bytes = crypto.decrypt_private_key(blob, key, certificate_id, 1)
    metadata = store.parse_certificate(certificate_bytes, private_key_bytes)
    now = datetime.now(timezone.utc).isoformat()
    if now < metadata["not_before"] or now > metadata["not_after"]:
        raise ResolverError("certificado fuera de su período de validez")
    if (
        metadata["fingerprint_sha256"] != item["fingerprint_sha256"]
        or metadata["public_key_fingerprint_sha256"] != item["public_key_fingerprint_sha256"]
    ):
        raise ResolverError("huellas del certificado no coinciden con el catálogo")
    return certificate_bytes, private_key_bytes, item


def _write_exclusive(path: Path, data: bytes, gid: int, mode: int) -> None:
    fd = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        mode,
    )
    try:
        os.fchown(fd, 0, gid)
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        path.unlink(missing_ok=True)
        raise


def _runtime_root(path: Path, service_gid: int) -> None:
    if path.exists() or path.is_symlink():
        st = path.lstat()
        if (
            not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode)
            or st.st_uid != 0 or st.st_gid != service_gid
            or stat.S_IMODE(st.st_mode) != 0o750
        ):
            raise ResolverError("directorio temporal TLS existente inseguro")
    else:
        if path.parent.is_symlink() or not path.parent.is_dir():
            raise ResolverError("directorio temporal TLS requiere un padre seguro")
        parent_stat = path.parent.lstat()
        if (
            not stat.S_ISDIR(parent_stat.st_mode) or parent_stat.st_uid != 0
            or parent_stat.st_gid != 0 or parent_stat.st_mode & 0o022
        ):
            raise ResolverError("directorio padre temporal TLS inseguro")
        os.mkdir(path, 0o750)
        os.chown(path, 0, service_gid)
        os.chmod(path, 0o750)


def prepare(
    *,
    connection_id: str,
    certificate_id: str,
    connections_catalog: Path,
    connections_base: Path,
    vmess_base: Path,
    connection_lock: Path,
    certificate_catalog: Path,
    certificate_base: Path,
    managed_dir: Path,
    certificate_secrets_dir: Path,
    certificate_lock: Path,
    master_key_file: Path,
    runtime_root: Path,
    service_uid: int,
    service_gid: int,
) -> dict[str, str]:
    if os.geteuid() != 0:
        raise ResolverError("la resolución TLS requiere root")
    if not CONNECTION_ID_RE.fullmatch(connection_id):
        raise ResolverError("ID de conexión no válido")
    if not CERTIFICATE_ID_RE.fullmatch(certificate_id):
        raise ResolverError("ID de certificado no válido")
    if (
        isinstance(service_uid, bool) or not isinstance(service_uid, int) or service_uid <= 0
        or isinstance(service_gid, bool) or not isinstance(service_gid, int) or service_gid <= 0
    ):
        raise ResolverError("identidad de servicio no válida")
    connection_fd = certificate_fd = None
    lease_dir: Path | None = None
    try:
        connection_fd = _acquire_lock(connection_lock)
        certificate_fd = store.acquire_lock(certificate_lock)
        connections = _load_connections(connections_catalog)
        entries = [item for item in connections if item.get("id") == connection_id]
        if len(entries) != 1:
            raise ResolverError("conexión no encontrada")
        entry = entries[0]
        config, protocol = _connection_config(
            entry, connection_id, connections_base, vmess_base
        )
        security_options = config["security_options"]
        if set(security_options) != {"certificate_id"} or security_options.get("certificate_id") != certificate_id:
            raise ResolverError("conexión no está autorizada para este certificado")
        _check_private_dir(certificate_base)
        catalog = store.load_catalog(certificate_catalog)
        cert_bytes, key_bytes, record = _certificate_record(
            certificate_id, catalog, managed_dir, certificate_secrets_dir, master_key_file
        )
        _runtime_root(runtime_root, service_gid)
        import secrets
        lease_id = "resolve-" + secrets.token_hex(16)
        lease_dir = runtime_root / lease_id
        os.mkdir(lease_dir, 0o750)
        os.chown(lease_dir, 0, service_gid)
        os.chmod(lease_dir, 0o750)
        cert_path = lease_dir / "certificate.pem"
        key_path = lease_dir / "private-key.pem"
        _write_exclusive(cert_path, cert_bytes, service_gid, 0o640)
        _write_exclusive(key_path, key_bytes, service_gid, 0o640)
        manifest = {
            "lease_id": lease_id,
            "connection_id": connection_id,
            "protocol": protocol,
            "certificate_id": certificate_id,
            "certificate_revision": record["revision"],
            "certificate_fingerprint_sha256": record["fingerprint_sha256"],
            "service_uid": service_uid,
            "service_gid": service_gid,
        }
        _write_exclusive(
            lease_dir / "manifest.json",
            (json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode(),
            service_gid,
            0o640,
        )
        for path in (lease_dir, cert_path, key_path, lease_dir / "manifest.json"):
            st = path.lstat()
            expected_mode = 0o750 if path == lease_dir else 0o640
            if (
                st.st_uid != 0 or st.st_gid != service_gid
                or stat.S_IMODE(st.st_mode) != expected_mode
                or (path != lease_dir and (not stat.S_ISREG(st.st_mode) or st.st_nlink != 1))
            ):
                raise ResolverError("falló la verificación de permisos del material temporal")
        return {
            "status": "prepared",
            "lease_id": lease_id,
            "connection_id": connection_id,
            "protocol": protocol,
            "certificate_id": certificate_id,
            "certificate_file": str(cert_path),
            "key_file": str(key_path),
        }
    except Exception:
        if lease_dir is not None and lease_dir.exists() and not lease_dir.is_symlink():
            shutil.rmtree(lease_dir)
        raise
    finally:
        if certificate_fd is not None:
            os.close(certificate_fd)
        if connection_fd is not None:
            os.close(connection_fd)


def cleanup(runtime_root: Path, lease_id: str, service_gid: int) -> dict[str, str]:
    if os.geteuid() != 0:
        raise ResolverError("la limpieza TLS requiere root")
    if not LEASE_RE.fullmatch(lease_id):
        raise ResolverError("ID de lease no válido")
    _runtime_root(runtime_root, service_gid)
    target = runtime_root / lease_id
    if not target.exists() and not target.is_symlink():
        return {"status": "absent", "lease_id": lease_id}
    st = target.lstat()
    if (
        not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode)
        or st.st_uid != 0 or st.st_gid != service_gid
        or stat.S_IMODE(st.st_mode) != 0o750
    ):
        raise ResolverError("directorio de lease inseguro; limpieza detenida")
    manifest_path = target / "manifest.json"
    manifest = json.loads(_safe_read(manifest_path, 16 * 1024, expected_gid=service_gid, expected_mode=0o640))
    if manifest.get("lease_id") != lease_id:
        raise ResolverError("manifest de lease no coincide; limpieza detenida")
    for child in target.iterdir():
        child_stat = child.lstat()
        if (
            not stat.S_ISREG(child_stat.st_mode) or stat.S_ISLNK(child_stat.st_mode)
            or child_stat.st_uid != 0 or child_stat.st_gid != service_gid
            or stat.S_IMODE(child_stat.st_mode) != 0o640
            or child_stat.st_nlink != 1
        ):
            raise ResolverError("contenido de lease inseguro; limpieza detenida")
    shutil.rmtree(target)
    return {"status": "cleaned", "lease_id": lease_id}


def service_identity(unit: str) -> tuple[int, int]:
    if not re.fullmatch(r"[A-Za-z0-9_.@-]+\.service", unit):
        raise ResolverError("unidad systemd no válida")
    try:
        result = subprocess.run(
            ["systemctl", "show", unit, "-p", "User", "-p", "Group", "-p", "SupplementaryGroups", "--no-pager"],
            check=True, capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ResolverError("no se pudo verificar la identidad efectiva de systemd") from exc
    fields = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            fields[key] = value
    username, groupname = fields.get("User", ""), fields.get("Group", "")
    if not username or not groupname or fields.get("SupplementaryGroups", ""):
        raise ResolverError("la unidad debe declarar User y Group explícitos y no usar grupos suplementarios")
    try:
        user = pwd.getpwnam(username)
        group = grp.getgrnam(groupname)
    except KeyError as exc:
        raise ResolverError("usuario o grupo de servicio no existe") from exc
    if user.pw_uid <= 0 or group.gr_gid <= 0:
        raise ResolverError("identidad de servicio privilegiada rechazada")
    if any(member != username for member in group.gr_mem):
        raise ResolverError("el grupo del servicio contiene miembros adicionales")
    return user.pw_uid, group.gr_gid


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--connections-catalog", default="/var/lib/xray-manager/connections/connections.json")
    parser.add_argument("--connections-base", default="/var/lib/xray-manager/connections")
    parser.add_argument("--vmess-base", default="/var/lib/xray-manager/vmess")
    parser.add_argument("--connection-lock", default="/run/xray-manager/integrity.lock")
    parser.add_argument("--certificate-base", default="/var/lib/xray-manager/certificates")
    parser.add_argument("--certificate-catalog", default="/var/lib/xray-manager/certificates/catalog.json")
    parser.add_argument("--managed-dir", default="/var/lib/xray-manager/certificates/managed")
    parser.add_argument("--certificate-secrets-dir", default="/var/lib/xray-manager/certificates/secrets")
    parser.add_argument("--certificate-lock", default="/var/lib/xray-manager/certificates/catalog.lock")
    parser.add_argument("--master-key", default="/etc/xray-manager/keys/master.key")
    parser.add_argument("--runtime-root", default="/run/xray-manager-certificates")
    parser.add_argument("--service-unit", default="xray.service")
    sub = parser.add_subparsers(dest="action", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--connection-id", required=True)
    prep.add_argument("--certificate-id", required=True)
    clean = sub.add_parser("cleanup")
    clean.add_argument("--lease-id", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        uid, gid = service_identity(args.service_unit)
        if args.action == "prepare":
            result = prepare(
                connection_id=args.connection_id,
                certificate_id=args.certificate_id,
                connections_catalog=Path(args.connections_catalog),
                connections_base=Path(args.connections_base),
                vmess_base=Path(args.vmess_base),
                connection_lock=Path(args.connection_lock),
                certificate_catalog=Path(args.certificate_catalog),
                certificate_base=Path(args.certificate_base),
                managed_dir=Path(args.managed_dir),
                certificate_secrets_dir=Path(args.certificate_secrets_dir),
                certificate_lock=Path(args.certificate_lock),
                master_key_file=Path(args.master_key),
                runtime_root=Path(args.runtime_root),
                service_uid=uid,
                service_gid=gid,
            )
        else:
            result = cleanup(Path(args.runtime_root), args.lease_id, gid)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (ResolverError, store.StoreError, crypto.CertificateCryptoError, OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
