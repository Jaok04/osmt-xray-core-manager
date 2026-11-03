#!/usr/bin/env python3
"""Preflight de solo lectura para migración de TLS histórico VMess/VLESS."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization

import vmess_config_store as vmess
import vless_config_store as vless

DEFAULTS = {
    "connections": Path("/var/lib/xray-manager/connections"),
    "vmess": Path("/var/lib/xray-manager/vmess"),
    "vless_secrets": Path("/var/lib/xray-manager/secrets"),
    "vmess_secrets": Path("/var/lib/xray-manager/vmess/secrets"),
    "catalog": Path("/var/lib/xray-manager/connections/connections.json"),
    "master_key": Path("/etc/xray-manager/keys/master.key"),
    "integrity_lock": Path("/run/xray-manager/integrity.lock"),
    "certificate_catalog": Path("/var/lib/xray-manager/certificates/catalog.json"),
}
MAX_CATALOG = 4 * 1024 * 1024
MAX_CONFIG = 512 * 1024
MAX_BLOB = 1024 * 1024
MAX_CERT = 1024 * 1024


class MigrationPlanError(Exception):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_read(path: Path, limit: int, *, private: bool = True) -> bytes:
    try:
        before = path.lstat()
    except OSError as exc:
        raise MigrationPlanError("archivo requerido ausente o inaccesible") from exc
    if not stat.S_ISREG(before.st_mode) or stat.S_ISLNK(before.st_mode) or before.st_nlink != 1:
        raise MigrationPlanError("archivo no regular, symlink o hardlink")
    if before.st_uid != 0 or before.st_gid != 0:
        raise MigrationPlanError("archivo no pertenece a root:root")
    mode = stat.S_IMODE(before.st_mode)
    if (private and mode != 0o600) or (not private and mode & 0o022):
        raise MigrationPlanError(f"permisos inseguros: {path}")
    if before.st_size < 1 or before.st_size > limit:
        raise MigrationPlanError("tamaño de archivo fuera de límites")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as stream:
        current = os.fstat(stream.fileno())
        identity = lambda s: (s.st_dev, s.st_ino, s.st_uid, s.st_gid, stat.S_IMODE(s.st_mode), s.st_nlink, s.st_size)
        if identity(current) != identity(before):
            raise MigrationPlanError("archivo cambió durante apertura")
        data = stream.read(limit + 1)
    if len(data) != before.st_size or len(data) > limit:
        raise MigrationPlanError("archivo cambió durante lectura")
    return data


def safe_directory(path: Path) -> None:
    path = path.absolute()
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            st = current.lstat()
        except OSError as exc:
            raise MigrationPlanError("directorio requerido ausente") from exc
        if not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode):
            raise MigrationPlanError("ruta de directorio insegura")
    target = path.lstat()
    if target.st_uid != 0 or target.st_gid != 0 or stat.S_IMODE(target.st_mode) & 0o022:
        raise MigrationPlanError("directorio final debe ser root:root y no escribible por grupo/otros")


def acquire_existing_lock(path: Path) -> int | None:
    # No crea archivos: si el lock operativo aún no existe, el preflight se
    # protege con hashes antes/después y reporta el modo de consistencia.
    if not path.exists() and not path.is_symlink():
        return None
    st = path.lstat()
    if not stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode) or st.st_uid != 0 or st.st_gid != 0 or stat.S_IMODE(st.st_mode) != 0o600 or st.st_nlink != 1:
        raise MigrationPlanError("archivo de bloqueo inseguro")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    fcntl.flock(fd, fcntl.LOCK_SH)
    return fd


def release_lock(fd: int | None) -> None:
    if fd is not None:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def load_json(data: bytes, label: str) -> Any:
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise MigrationPlanError(f"{label} JSON inválido") from exc


def cert_metadata(cert_bytes: bytes, key_bytes: bytes) -> dict[str, str]:
    try:
        cert = x509.load_pem_x509_certificate(cert_bytes)
        private_key = serialization.load_pem_private_key(key_bytes, password=None)
        cert_pub = cert.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        key_pub = private_key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        if cert_pub != key_pub:
            raise MigrationPlanError("la clave privada no corresponde al certificado")
        now = datetime.now(timezone.utc)
        not_before = cert.not_valid_before.replace(tzinfo=timezone.utc)
        not_after = cert.not_valid_after.replace(tzinfo=timezone.utc)
        if now < not_before:
            raise MigrationPlanError("certificado aún no vigente")
        if now > not_after:
            raise MigrationPlanError("certificado vencido")
        return {
            "fingerprint_sha256": cert.fingerprint(hashes.SHA256()).hex(),
            "public_key_fingerprint_sha256": hashlib.sha256(cert_pub).hexdigest(),
            "not_before": not_before.isoformat(),
            "not_after": not_after.isoformat(),
        }
    except MigrationPlanError:
        raise
    except Exception as exc:
        raise MigrationPlanError("certificado o clave PEM inválidos") from exc


def protocol_layout(protocol: str, entry: dict[str, Any], roots: dict[str, Path]):
    mode = entry.get("protocol_id")
    if protocol == "vless":
        if mode not in vless.MODES:
            raise MigrationPlanError("modalidad VLESS desconocida")
        ref_field, revision_field, schema_field, secret_field = "configuration_ref", "configuration_revision", "configuration_schema_version", "secret_ref"
        base, secrets_dir = roots["connections"], roots["vless_secrets"]
    else:
        if mode not in vmess.MODES:
            raise MigrationPlanError("modalidad VMess desconocida")
        ref_field, revision_field, schema_field, secret_field = "vmess_configuration_ref", "vmess_configuration_revision", "vmess_configuration_schema_version", "vmess_secret_ref"
        base, secrets_dir = roots["vmess"], roots["vmess_secrets"]
    return mode, ref_field, revision_field, schema_field, secret_field, base, secrets_dir


def inspect_entry(protocol: str, entry: dict[str, Any], roots: dict[str, Path], master_key: bytes | None) -> tuple[dict[str, Any], bytes | None]:
    cid = entry.get("id")
    if not isinstance(cid, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", cid):
        raise MigrationPlanError("connection_id inválido")
    mode, ref_field, revision_field, schema_field, secret_field, base, secrets_dir = protocol_layout(protocol, entry, roots)
    security = (vless.MODES if protocol == "vless" else vmess.MODES)[mode][1]
    if security != "tls":
        raise MigrationPlanError("no es modalidad TLS")
    ref = entry.get(ref_field)
    match = re.fullmatch(rf"configurations/{re.escape(cid)}\.r([0-9]{{6}})\.json", ref if isinstance(ref, str) else "")
    revision = entry.get(revision_field)
    schema = entry.get(schema_field)
    if not match or isinstance(revision, bool) or type(revision) is not int or revision != int(match.group(1)) or schema != 1 or isinstance(schema, bool):
        raise MigrationPlanError("referencia/revisión/esquema de configuración incoherentes")
    safe_directory(base)
    config_dir = base / "configurations"
    safe_directory(config_dir)
    config_path = config_dir / f"{cid}.r{revision:06d}.json"
    config_bytes = safe_read(config_path, MAX_CONFIG)
    config = load_json(config_bytes, "configuración")
    secret_ref = entry.get(secret_field)
    if protocol == "vless":
        vless.validate_config(config, entry, secret_ref, allow_legacy_tls=True)
    else:
        vmess.validate_catalog_metadata(entry, ref, config, secret_ref)
        vmess.validate(config, entry, secret_ref, allow_legacy_tls=True)
    security_options = config.get("security_options")
    if not isinstance(security_options, dict):
        raise MigrationPlanError("security_options inválido")
    if set(security_options) == {"certificate_id"}:
        import certificate_store
        central_catalog = certificate_store.load_catalog(roots["certificate_catalog"])
        central_matches = [x for x in central_catalog["certificates"] if x.get("certificate_id") == security_options["certificate_id"]]
        if len(central_matches) != 1 or central_matches[0].get("status") != "active":
            raise MigrationPlanError("certificado TLS central ausente, duplicado o inactivo")
        return ({
            "connection_id": cid, "protocol": protocol, "mode": mode,
            "revision": revision, "status": "ALREADY_CENTRAL",
            "certificate_id": security_options["certificate_id"],
            "input_hashes": {"configuration": digest(config_bytes)},
            "_input_files": [(str(config_path), digest(config_bytes), MAX_CONFIG, True)],
        }, None)
    if set(security_options) != {"certificate_file", "secret_ref"}:
        raise MigrationPlanError("contrato TLS histórico no reconocido")
    if not isinstance(secret_ref, str) or security_options.get("secret_ref") != secret_ref:
        raise MigrationPlanError("referencia del secreto TLS no coincide")
    secret_match = re.fullmatch(rf"secrets/{re.escape(cid)}\.r([0-9]{{6}})\.bin", secret_ref)
    if not secret_match or int(secret_match.group(1)) != revision:
        raise MigrationPlanError("revisión del secreto no coincide con configuración")
    safe_directory(secrets_dir)
    secret_path = secrets_dir / f"{cid}.r{revision:06d}.bin"
    blob = safe_read(secret_path, MAX_BLOB)
    if master_key is None:
        raise MigrationPlanError("clave maestra no disponible")
    if protocol == "vless":
        import vless_crypto
        private_bytes = vless_crypto.decrypt_secret(blob, master_key, cid, 1)
    else:
        private_bytes = vmess.decrypt(blob, master_key, cid)
    cert_path_value = security_options.get("certificate_file")
    if not isinstance(cert_path_value, str) or not cert_path_value.startswith("/") or len(cert_path_value) > 4096:
        raise MigrationPlanError("ruta de certificado histórico inválida")
    cert_path = Path(cert_path_value)
    cert_bytes = safe_read(cert_path, MAX_CERT, private=False)
    metadata = cert_metadata(cert_bytes, private_bytes)
    # No se conserva el PEM ni se devuelve la clave privada al llamador.
    del private_bytes
    record = {
        "connection_id": cid, "protocol": protocol, "mode": mode,
        "revision": revision, "status": "READY",
        "fingerprint_sha256": metadata["fingerprint_sha256"],
        "public_key_fingerprint_sha256": metadata["public_key_fingerprint_sha256"],
        "not_before": metadata["not_before"], "not_after": metadata["not_after"],
        "certificate_source": cert_path_value,
        "input_hashes": {
            "configuration": digest(config_bytes),
            "secret_blob": digest(blob),
            "certificate": digest(cert_bytes),
        },
        "_input_files": [
            (str(config_path), digest(config_bytes), MAX_CONFIG, True),
            (str(secret_path), digest(blob), MAX_BLOB, True),
            (str(cert_path), digest(cert_bytes), MAX_CERT, False),
        ],
    }
    return record, (metadata["fingerprint_sha256"] + ":" + metadata["public_key_fingerprint_sha256"]).encode()


def run(args: argparse.Namespace) -> dict[str, Any]:
    if os.geteuid() != 0:
        raise MigrationPlanError("preflight requiere root")
    roots = {
        "connections": Path(args.connections).absolute(),
        "vmess": Path(args.vmess).absolute(),
        "vless_secrets": Path(args.vless_secrets).absolute(),
        "vmess_secrets": Path(args.vmess_secrets).absolute(),
        "catalog": Path(args.catalog).absolute(),
        "master_key": Path(args.master_key).absolute(),
        "certificate_catalog": Path(args.certificate_catalog).absolute(),
    }
    lock_fd = acquire_existing_lock(Path(args.integrity_lock).absolute())
    try:
        catalog_bytes = safe_read(roots["catalog"], MAX_CATALOG)
        catalog = load_json(catalog_bytes, "catálogo de conexiones")
        if not isinstance(catalog, list) or not all(isinstance(x, dict) for x in catalog):
            raise MigrationPlanError("catálogo de conexiones debe ser una lista de objetos")
        ids = [x.get("id") for x in catalog]
        if any(not isinstance(x, str) for x in ids) or len(ids) != len(set(ids)):
            raise MigrationPlanError("IDs del catálogo ausentes o duplicados")
        candidates = []
        for entry in catalog:
            mode = entry.get("protocol_id")
            protocol = "vless" if isinstance(mode, str) and mode in vless.MODES else "vmess" if isinstance(mode, str) and mode in vmess.MODES else None
            if protocol is None or args.protocol not in ("all", protocol):
                continue
            modes = vless.MODES if protocol == "vless" else vmess.MODES
            if modes[mode][1] != "tls":
                continue
            candidates.append((protocol, entry))
        master_key = None
        master_key_hash = None
        if candidates:
            try:
                import certificate_crypto
                master_key = certificate_crypto.load_master_key(roots["master_key"])
                master_key_hash = digest(safe_read(roots["master_key"], 32))
            except Exception:
                master_key = None
        records = []
        groups: dict[bytes, list[str]] = {}
        for protocol, entry in candidates:
            try:
                item, group_key = inspect_entry(protocol, entry, roots, master_key)
                if item["status"] == "READY" and group_key:
                    groups.setdefault(group_key, []).append(item["connection_id"])
                records.append(item)
            except Exception as exc:
                records.append({
                    "connection_id": entry.get("id") if isinstance(entry.get("id"), str) else "<invalid>",
                    "protocol": protocol, "mode": entry.get("protocol_id"),
                    "status": "BLOCKED", "reason": str(exc)[:180],
                })
        # Revalida todos los archivos observados para detectar cambios externos.
        observed = [(str(roots["catalog"]), digest(catalog_bytes), MAX_CATALOG, True)]
        if master_key_hash is not None:
            observed.append((str(roots["master_key"]), master_key_hash, 32, True))
        for record in records:
            observed.extend(record.pop("_input_files", []))
        for filename, expected_hash, limit, private in observed:
            current = safe_read(Path(filename), limit, private=private)
            if digest(current) != expected_hash:
                raise MigrationPlanError("un archivo de entrada cambió durante el preflight; repetir")
        group_map = {}
        for index, (key, members) in enumerate(sorted(groups.items(), key=lambda x: x[0]), 1):
            group_map[f"group-{index:04d}"] = sorted(members)
        plan_basis = {
            "format": "xray-manager-tls-migration-plan",
            "format_version": 1,
            "protocol_scope": args.protocol,
            "catalog_sha256": digest(catalog_bytes),
            "records": records,
            "deduplication_groups": group_map,
        }
        plan_id = digest(json.dumps(plan_basis, sort_keys=True, separators=(",", ":")).encode())[:24]
        return {
            **plan_basis,
            "plan_id": plan_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "tls_candidates": len(candidates),
                "ready": sum(x["status"] == "READY" for x in records),
                "already_central": sum(x["status"] == "ALREADY_CENTRAL" for x in records),
                "blocked": sum(x["status"] == "BLOCKED" for x in records),
                "deduplication_groups": len(group_map),
            },
            "read_only": True,
            "writes_performed": False,
            "automatic_migration": False,
            "automatic_deletion": False,
            "consistency": "shared integrity lock when present; input hashes checked before/after",
        }
    finally:
        release_lock(lock_fd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    plan = sub.add_parser("plan", help="inventario TLS histórico de solo lectura")
    plan.add_argument("--protocol", choices=("all", "vless", "vmess"), default="all")
    for name, path in DEFAULTS.items():
        option = "--" + name.replace("_", "-")
        plan.add_argument(option, default=str(path))
    args = parser.parse_args()
    try:
        result = run(args)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return 0
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {str(exc)[:220]}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
