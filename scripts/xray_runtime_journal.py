#!/usr/bin/env python3
"""Snapshot y journal R-03 para operaciones runtime aisladas.

Este módulo no publica config.json, no ejecuta systemd y no inicia Xray.
Sólo acepta XRAY_SERVICE_ROOT con marcador explícito de fixture.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import secrets
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import xray_runtime_preflight

MAX_FILE = 16 * 1024 * 1024
MAX_JOURNAL = 1024 * 1024
OP_RE = re.compile(r"runtime-op-[0-9a-f]{32}\Z")
PROFILE_RE = re.compile(r"profile-[0-9a-f]{32}\Z")
REVISION_RE = re.compile(r"r[0-9]{6}\Z")
VALIDATION_RE = re.compile(r"pvalidation-[0-9a-f]{32}\Z")
LEASE_RE = re.compile(r"resolve-[0-9a-f]{32}\Z")
SHA_RE = re.compile(r"[0-9a-f]{64}\Z")
CERT_RE = re.compile(r"cert-[A-Za-z0-9][A-Za-z0-9_.-]{0,120}\Z")


class RuntimeJournalError(Exception):
    pass


class SimulatedCrash(BaseException):
    """Failpoint sólo invocable desde pruebas; no se expone en el CLI."""


def fail(message: str) -> None:
    raise RuntimeJournalError(message)


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def strict_json(data: bytes, label: str) -> Any:
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


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


def reject_symlinks(path: Path, label: str) -> None:
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


def check_dir(path: Path, mode: int = 0o700, uid: int = 0, gid: int = 0) -> None:
    reject_symlinks(path, "Directorio")
    try:
        info = path.lstat()
    except OSError:
        fail(f"No existe el directorio requerido: {path.name}.")
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != uid or info.st_gid != gid
            or stat.S_IMODE(info.st_mode) != mode):
        fail(f"Directorio inseguro: {path.name}.")


def read_regular(path: Path, limit: int, uid: int, gid: int, mode: int,
                 label: str) -> bytes:
    reject_symlinks(path, label)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        fail(f"No se pudo abrir {label}.")
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != uid or info.st_gid != gid
                or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != mode
                or info.st_size < 1 or info.st_size > limit):
            fail(f"{label} tiene tipo, propietario, permisos o tamaño inseguros.")
        chunks = []
        total = 0
        while True:
            block = os.read(fd, min(1024 * 1024, limit + 1 - total))
            if not block:
                break
            chunks.append(block)
            total += len(block)
            if total > limit:
                fail(f"{label} excede el límite.")
        data = b"".join(chunks)
        if len(data) != info.st_size:
            fail(f"{label} cambió durante su lectura.")
        return data
    finally:
        os.close(fd)


def atomic_write(path: Path, data: bytes, uid: int = 0, gid: int = 0,
                 mode: int = 0o600) -> None:
    check_dir(path.parent)
    if path.exists() or path.is_symlink():
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode)
                or info.st_uid != uid or info.st_gid != gid or info.st_nlink != 1
                or stat.S_IMODE(info.st_mode) != mode):
            fail(f"Destino atómico inseguro: {path.name}.")
    temp = path.parent / (".tmp-" + secrets.token_hex(16))
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                 | getattr(os, "O_NOFOLLOW", 0), mode)
    try:
        os.fchown(fd, uid, gid)
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(temp, path)
    fsync_dir(path.parent)


def fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def acquire_lock(path: Path) -> int:
    reject_symlinks(path, "Lock")
    check_dir(path.parent)
    if path.exists():
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_gid != 0
                or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600):
            fail("Archivo de lock inseguro.")
    fd = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    info = os.fstat(fd)
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_gid != 0
            or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600):
        os.close(fd)
        fail("Archivo de lock inseguro.")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        fail("Otra operación runtime mantiene un lock; no se modificó ningún estado.")
    return fd


def release_locks(fds: list[int]) -> None:
    for fd in reversed(fds):
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def read_staging(staging_dir: Path, lease_root: Path,
                 service_uid: int, service_gid: int) -> tuple[dict, bytes, dict]:
    check_dir(staging_dir, 0o750, 0, service_gid)
    manifest_data = read_regular(staging_dir / "manifest.json", MAX_JOURNAL,
                                 0, service_gid, 0o640, "manifiesto staging")
    config_data = read_regular(staging_dir / "config.json", MAX_FILE,
                               0, service_gid, 0o640, "configuración staging")
    manifest = strict_json(manifest_data, "Manifiesto staging")
    required = {
        "schema_version", "status", "fixture_root", "staging_dir", "lease_root",
        "profile_id", "revision", "validation_id",
        "profile_content_sha256", "bindings_sha256", "bindings", "leases",
        "staged_config_sha256", "staged_config_size_bytes", "service_identity",
        "xray_binary", "native_validation", "runtime_published", "service_started",
    }
    if not isinstance(manifest, dict) or set(manifest) != required:
        fail("El manifiesto staging no cumple el contrato R-02.")
    if (type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1 or manifest["status"] != "STAGED"
            or manifest["native_validation"] != "PASS"
            or manifest["runtime_published"] is not False
            or manifest["service_started"] is not False):
        fail("El staging no está en estado STAGED seguro.")
    fixture_root = Path(manifest["fixture_root"]) if isinstance(manifest["fixture_root"], str) else Path(".")
    recorded_staging_dir = Path(manifest["staging_dir"]) if isinstance(manifest["staging_dir"], str) else Path(".")
    recorded_lease_root = Path(manifest["lease_root"]) if isinstance(manifest["lease_root"], str) else Path(".")
    if (not fixture_root.is_absolute() or not recorded_staging_dir.is_absolute()
            or not recorded_lease_root.is_absolute()
            or Path(os.path.abspath(staging_dir)) != Path(os.path.abspath(recorded_staging_dir))
            or Path(os.path.abspath(lease_root)) != Path(os.path.abspath(recorded_lease_root))):
        fail("Rutas fixture_root/lease_root no coinciden con el manifiesto R-02.")
    reject_symlinks(fixture_root, "fixture_root del staging")
    fixture_info = fixture_root.lstat()
    if (not stat.S_ISDIR(fixture_info.st_mode) or fixture_info.st_uid != 0
            or fixture_info.st_gid != 0 or stat.S_IMODE(fixture_info.st_mode) & 0o022):
        fail("fixture_root del staging no es un directorio root:root seguro.")
    fixture_marker = read_regular(
        fixture_root / ".xray-manager-r02-fixture", 4096, 0, 0, 0o600,
        "marcador fixture R-02"
    )
    if strict_json(fixture_marker, "Marcador fixture R-02") != {
        "schema_version": 1, "purpose": "xray-runtime-r02-isolated-fixture"
    }:
        fail("El marcador fixture R-02 no es válido.")
    try:
        recorded_staging_dir.relative_to(fixture_root)
        recorded_lease_root.relative_to(fixture_root)
    except ValueError:
        fail("Staging y leases deben permanecer dentro del fixture R-02.")
    if (not isinstance(manifest["profile_id"], str) or not PROFILE_RE.fullmatch(manifest["profile_id"])
            or not isinstance(manifest["revision"], str) or not REVISION_RE.fullmatch(manifest["revision"])
            or not isinstance(manifest["validation_id"], str) or not VALIDATION_RE.fullmatch(manifest["validation_id"])):
        fail("Identidad profile_id/revision/validation_id inválida en staging.")
    for field in ("profile_content_sha256", "bindings_sha256", "staged_config_sha256"):
        if not isinstance(manifest[field], str) or not SHA_RE.fullmatch(manifest[field]):
            fail(f"Hash inválido en manifiesto staging: {field}.")
    if (not isinstance(manifest["staged_config_size_bytes"], int)
            or isinstance(manifest["staged_config_size_bytes"], bool)
            or manifest["staged_config_size_bytes"] != len(config_data)
            or manifest["staged_config_sha256"] != hashlib.sha256(config_data).hexdigest()):
        fail("Hash/tamaño de config.json no coincide con el manifiesto staging.")
    identity = manifest["service_identity"]
    if (not isinstance(identity, dict) or set(identity) != {"uid", "gid"}
            or identity["uid"] != service_uid or identity["gid"] != service_gid):
        fail("La identidad del staging no coincide con el fixture de servicio.")
    binary = manifest["xray_binary"]
    if (not isinstance(binary, dict) or set(binary) != {"path", "sha256", "size_bytes"}
            or not isinstance(binary["path"], str) or not Path(binary["path"]).is_absolute()
            or not isinstance(binary["sha256"], str) or not SHA_RE.fullmatch(binary["sha256"])
            or type(binary["size_bytes"]) is not int or binary["size_bytes"] <= 0):
        fail("Metadatos del binario Xray en staging inválidos.")
    actual_binary = xray_runtime_preflight._inspect_binary(Path(binary["path"]))
    if (actual_binary["sha256"] != binary["sha256"]
            or actual_binary["size_bytes"] != binary["size_bytes"]):
        fail("El binario Xray cambió después del staging.")

    bindings = manifest["bindings"]
    leases = manifest["leases"]
    if (not isinstance(bindings, list) or not isinstance(leases, list)
            or not 1 <= len(bindings) <= 256 or len(bindings) != len(leases)):
        fail("Asociaciones/leases inconsistentes en el manifiesto staging.")
    check_dir(lease_root, 0o750, 0, service_gid)
    lease_marker = read_regular(
        lease_root / ".xray-manager-r02-leases-fixture", 4096,
        0, service_gid, 0o640, "marcador lease_root fixture"
    )
    if strict_json(lease_marker, "Marcador lease_root") != {
        "schema_version": 1, "purpose": "xray-runtime-r02-isolated-leases"
    }:
        fail("lease_root no corresponde al fixture R-02.")
    seen_tags, seen_connections = set(), set()
    for binding, lease_item in zip(bindings, leases):
        if (not isinstance(binding, dict) or set(binding) != {"inbound_tag", "connection_id"}
                or not isinstance(binding["inbound_tag"], str)
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", binding["inbound_tag"])
                or not isinstance(binding["connection_id"], str)
                or binding["inbound_tag"] in seen_tags
                or binding["connection_id"] in seen_connections
                or not isinstance(lease_item, dict)
                or lease_item.get("connection_id") != binding["connection_id"]):
            fail("Mapa inbound tag → connection_id no coincide con los leases staged.")
        seen_tags.add(binding["inbound_tag"])
        seen_connections.add(binding["connection_id"])
    verified_leases = []
    seen_lease_ids = set()
    for item in leases:
        if (not isinstance(item, dict)
                or set(item) != {"lease_id", "connection_id", "protocol", "certificate_id"}
                or not isinstance(item["lease_id"], str) or not LEASE_RE.fullmatch(item["lease_id"])
                or item["lease_id"] in seen_lease_ids
                or not isinstance(item["connection_id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", item["connection_id"])
                or not isinstance(item["protocol"], str) or item["protocol"] not in {"vless", "vmess"}
                or not isinstance(item["certificate_id"], str) or not CERT_RE.fullmatch(item["certificate_id"])):
            fail("Registro de lease inválido en manifiesto staging.")
        seen_lease_ids.add(item["lease_id"])
        lease_dir = lease_root / item["lease_id"]
        check_dir(lease_dir, 0o750, 0, service_gid)
        lease_manifest_data = read_regular(lease_dir / "manifest.json", 16384, 0, service_gid, 0o640, "manifiesto lease")
        lease_manifest = strict_json(lease_manifest_data, "Manifiesto lease")
        expected_fields = {
            "lease_id", "connection_id", "protocol", "certificate_id",
            "certificate_revision", "certificate_fingerprint_sha256", "service_uid", "service_gid",
        }
        if (not isinstance(lease_manifest, dict) or set(lease_manifest) != expected_fields
                or lease_manifest["lease_id"] != item["lease_id"]
                or lease_manifest["connection_id"] != item["connection_id"]
                or lease_manifest["protocol"] != item["protocol"]
                or lease_manifest["certificate_id"] != item["certificate_id"]
                or lease_manifest["service_uid"] != service_uid
                or lease_manifest["service_gid"] != service_gid
                or type(lease_manifest["certificate_revision"]) is not int
                or lease_manifest["certificate_revision"] < 1
                or not isinstance(lease_manifest["certificate_fingerprint_sha256"], str)
                or not SHA_RE.fullmatch(lease_manifest["certificate_fingerprint_sha256"])):
            fail("Manifiesto TLS no coincide con la asociación staged.")
        for filename in ("certificate.pem", "private-key.pem"):
            read_regular(lease_dir / filename, 1024 * 1024, 0, service_gid, 0o640, "archivo TLS lease")
        verified_leases.append({
            "lease_id": item["lease_id"],
            "connection_id": item["connection_id"],
            "protocol": item["protocol"],
            "certificate_id": item["certificate_id"],
            "certificate_revision": lease_manifest["certificate_revision"],
            "certificate_fingerprint_sha256": lease_manifest["certificate_fingerprint_sha256"],
        })
    return manifest, config_data, {"leases": verified_leases, "manifest_sha256": hashlib.sha256(manifest_data).hexdigest()}


def service_fixture(path: Path, binary_path: str) -> dict:
    # Reutiliza el contrato R-01; no consulta systemd.
    return xray_runtime_preflight._validate_service_fixture(path, binary_path)


def fixture_root(path: Path) -> None:
    check_dir(path, 0o711, 0, 0)
    marker = read_regular(path / ".xray-manager-fixture", 4096, 0, 0, 0o600, "marcador XRAY_SERVICE_ROOT")
    value = strict_json(marker, "Marcador XRAY_SERVICE_ROOT")
    if value != {"schema_version": 1, "purpose": "xray-runtime-isolated-fixture"}:
        fail("XRAY_SERVICE_ROOT no está marcado como fixture aislado; se bloquea la operación.")


def previous_config(service_root: Path, service_gid: int) -> tuple[bytes | None, dict]:
    config_dir = service_root / "etc" / "xray"
    config_path = config_dir / "config.json"
    reject_symlinks(config_dir, "Directorio de configuración fixture")
    etc_dir = service_root / "etc"
    if not etc_dir.exists():
        return None, {"present": False, "reason": "no_previous_config"}
    check_dir(etc_dir, 0o755, 0, 0)
    if not config_dir.exists():
        return None, {"present": False, "reason": "no_previous_config"}
    check_dir(config_dir, 0o750, 0, service_gid)
    if not config_path.exists() and not config_path.is_symlink():
        return None, {"present": False, "reason": "no_previous_config"}
    data = read_regular(config_path, MAX_FILE, 0, service_gid, 0o640, "config runtime anterior")
    info = config_path.stat()
    return data, {
        "present": True,
        "file": "snapshot/config.json",
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
        "uid": info.st_uid,
        "gid": info.st_gid,
        "mode": stat.S_IMODE(info.st_mode),
    }


def clean_atomic_temps(directory: Path) -> None:
    if not directory.exists():
        return
    check_dir(directory, 0o700, 0, 0)
    changed = False
    for item in directory.iterdir():
        if not re.fullmatch(r"\.tmp-[0-9a-f]{32}", item.name):
            continue
        info = item.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_gid != 0
                or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600):
            fail("Temporal atómico inseguro dentro de una operación runtime.")
        item.unlink()
        changed = True
    if changed:
        fsync_dir(directory)


def read_journal(operation_dir: Path) -> dict:
    check_dir(operation_dir, 0o700, 0, 0)
    raw = read_regular(operation_dir / "journal.json", MAX_JOURNAL, 0, 0, 0o600, "journal runtime")
    value = strict_json(raw, "Journal runtime")
    required = {
        "schema_version", "operation_id", "state", "created_at", "updated_at",
        "source", "staging", "service", "snapshot", "publication", "rollback", "recovery",
    }
    if (not isinstance(value, dict) or set(value) != required
            or type(value["schema_version"]) is not int or value["schema_version"] != 1
            or value["operation_id"] != operation_dir.name
            or not OP_RE.fullmatch(operation_dir.name)
            or not isinstance(value["state"], str)
            or value["state"] not in {
                "prepared", "validated", "snapshot_saved", "config_published",
                "rollback_started", "rollback_config_restored", "rollback_failed",
                "rolled_back", "aborted", "recovery_required",
            }):
        fail("Journal runtime corrupto o con identidad incorrecta.")

    source = value["source"]
    source_fields = {"profile_id", "revision", "validation_id", "profile_content_sha256"}
    if (not isinstance(source, dict) or set(source) != source_fields
            or not isinstance(source["profile_id"], str) or not PROFILE_RE.fullmatch(source["profile_id"])
            or not isinstance(source["revision"], str) or not REVISION_RE.fullmatch(source["revision"])
            or not isinstance(source["validation_id"], str) or not VALIDATION_RE.fullmatch(source["validation_id"])
            or not isinstance(source["profile_content_sha256"], str) or not SHA_RE.fullmatch(source["profile_content_sha256"])):
        fail("Identidad de origen inválida en journal runtime.")

    staging = value["staging"]
    staging_fields = {
        "fixture_root", "staging_dir", "lease_root", "staging_manifest_sha256", "config_sha256",
        "config_size_bytes", "bindings_sha256", "bindings", "leases",
    }
    if (not isinstance(staging, dict) or set(staging) != staging_fields
            or not isinstance(staging["fixture_root"], str) or not Path(staging["fixture_root"]).is_absolute()
            or not isinstance(staging["staging_dir"], str) or not Path(staging["staging_dir"]).is_absolute()
            or not isinstance(staging["lease_root"], str) or not Path(staging["lease_root"]).is_absolute()
            or any(not isinstance(staging[key], str) or not SHA_RE.fullmatch(staging[key])
                   for key in ("staging_manifest_sha256", "config_sha256", "bindings_sha256"))
            or type(staging["config_size_bytes"]) is not int or not 1 <= staging["config_size_bytes"] <= MAX_FILE
            or not isinstance(staging["bindings"], list) or not isinstance(staging["leases"], list)
            or not 1 <= len(staging["bindings"]) <= 256 or len(staging["bindings"]) != len(staging["leases"])):
        fail("Metadatos de staging inválidos en journal runtime.")

    service = value["service"]
    service_fields = {
        "unit", "load_state", "active_state", "sub_state", "user", "group",
        "binary_path", "service_root", "uid", "gid",
    }
    if (not isinstance(service, dict) or set(service) != service_fields
            or service["unit"] != "xray.service" or service["load_state"] != "loaded"
            or not isinstance(service["active_state"], str)
            or service["active_state"] not in {"active", "inactive", "failed"}
            or not isinstance(service["sub_state"], str) or not service["sub_state"]
            or service["user"] != "xray" or service["group"] != "xray"
            or not isinstance(service["binary_path"], str) or not Path(service["binary_path"]).is_absolute()
            or not isinstance(service["service_root"], str) or not Path(service["service_root"]).is_absolute()
            or type(service["uid"]) is not int or service["uid"] <= 0
            or type(service["gid"]) is not int or service["gid"] <= 0):
        fail("Estado/identidad de servicio inválido en journal runtime.")

    fixture_root = Path(staging["fixture_root"])
    try:
        Path(staging["staging_dir"]).relative_to(fixture_root)
        Path(staging["lease_root"]).relative_to(fixture_root)
    except ValueError:
        fail("Las rutas de staging/leases del journal escaparon del fixture R-02.")
    reject_symlinks(fixture_root, "fixture_root del journal")
    fixture_info = fixture_root.lstat()
    if (not stat.S_ISDIR(fixture_info.st_mode) or fixture_info.st_uid != 0
            or fixture_info.st_gid != 0 or stat.S_IMODE(fixture_info.st_mode) & 0o022):
        fail("fixture_root del journal no es un directorio root:root seguro.")
    fixture_marker = read_regular(
        fixture_root / ".xray-manager-r02-fixture", 4096, 0, 0, 0o600,
        "marcador fixture R-02 del journal"
    )
    if strict_json(fixture_marker, "Marcador fixture R-02") != {
        "schema_version": 1, "purpose": "xray-runtime-r02-isolated-fixture"
    }:
        fail("El fixture R-02 del journal no está disponible.")
    service_root_path = Path(service["service_root"])
    check_dir(service_root_path, 0o711, 0, 0)
    service_marker = read_regular(
        service_root_path / ".xray-manager-fixture", 4096, 0, 0, 0o600,
        "marcador XRAY_SERVICE_ROOT del journal"
    )
    if strict_json(service_marker, "Marcador XRAY_SERVICE_ROOT") != {
        "schema_version": 1, "purpose": "xray-runtime-isolated-fixture"
    }:
        fail("XRAY_SERVICE_ROOT del journal dejó de ser un fixture válido.")

    snapshot = value["snapshot"]
    snapshot_fields = {"status", "previous_config_present", "previous_config_sha256", "metadata_sha256"}
    if (not isinstance(snapshot, dict) or set(snapshot) != snapshot_fields
            or not isinstance(snapshot["status"], str)
            or snapshot["status"] not in {"pending", "saved"}
            or not isinstance(snapshot["previous_config_present"], bool)
            or (snapshot["previous_config_sha256"] is not None
                and (not isinstance(snapshot["previous_config_sha256"], str)
                     or not SHA_RE.fullmatch(snapshot["previous_config_sha256"])))
            or (snapshot["metadata_sha256"] is not None
                and (not isinstance(snapshot["metadata_sha256"], str)
                     or not SHA_RE.fullmatch(snapshot["metadata_sha256"])))):
        fail("Metadatos snapshot inválidos en journal runtime.")
    if value["state"] == "snapshot_saved" and (snapshot["status"] != "saved" or snapshot["metadata_sha256"] is None):
        fail("Estado snapshot_saved no tiene metadatos snapshot confirmados.")
    lease_root_path = Path(staging["lease_root"])
    check_dir(lease_root_path, 0o750, 0, service["gid"])
    lease_marker = read_regular(
        lease_root_path / ".xray-manager-r02-leases-fixture", 4096,
        0, service["gid"], 0o640, "marcador lease_root del journal"
    )
    if strict_json(lease_marker, "Marcador lease_root del journal") != {
        "schema_version": 1, "purpose": "xray-runtime-r02-isolated-leases"
    }:
        fail("lease_root del journal dejó de ser un fixture válido.")

    publication = value["publication"]
    if (not isinstance(publication, dict)
            or set(publication) != {"status", "target", "config_sha256", "published_at"}
            or not isinstance(publication["status"], str)
            or publication["status"] not in {"not_published", "published"}
            or publication["target"] != "etc/xray/config.json"
            or (publication["config_sha256"] is not None
                and (not isinstance(publication["config_sha256"], str)
                     or not SHA_RE.fullmatch(publication["config_sha256"])))
            or (publication["published_at"] is not None
                and not isinstance(publication["published_at"], str))):
        fail("Metadatos de publicación inválidos en journal runtime.")

    rollback = value["rollback"]
    if (not isinstance(rollback, dict)
            or set(rollback) != {
                "status", "started_at", "completed_at", "restored_config_sha256",
                "validation", "last_error",
            }
            or not isinstance(rollback["status"], str)
            or rollback["status"] not in {
                "not_started", "started", "config_restored", "failed",
                "recovery_required", "rolled_back",
            }
            or (rollback["started_at"] is not None and not isinstance(rollback["started_at"], str))
            or (rollback["completed_at"] is not None and not isinstance(rollback["completed_at"], str))
            or (rollback["restored_config_sha256"] is not None
                and (not isinstance(rollback["restored_config_sha256"], str)
                     or not SHA_RE.fullmatch(rollback["restored_config_sha256"])))
            or (rollback["validation"] is not None
                and rollback["validation"] not in ("PASS", "FAIL"))
            or (rollback["last_error"] is not None and not isinstance(rollback["last_error"], str))):
        fail("Metadatos de rollback inválidos en journal runtime.")
    if publication["status"] == "not_published" and (
        publication["config_sha256"] is not None or publication["published_at"] is not None
    ):
        fail("Una publicación pendiente contiene metadatos de publicación.")
    if publication["status"] == "published" and (
        publication["config_sha256"] is None or publication["published_at"] is None
    ):
        fail("La publicación no conserva hash/fecha.")
    state_contract = {
        "config_published": ("published", "not_started"),
        "rollback_started": ("published", "started"),
        "rollback_config_restored": ("published", "config_restored"),
        "rollback_failed": ("published", "failed"),
        "rolled_back": ("published", "rolled_back"),
    }
    if rollback["status"] == "not_started" and any(
        rollback[field] is not None
        for field in ("started_at", "completed_at", "restored_config_sha256", "validation", "last_error")
    ):
        fail("Rollback not_started contiene metadatos de ejecución.")
    if value["state"] in state_contract:
        expected_publication, expected_rollback = state_contract[value["state"]]
        if publication["status"] != expected_publication or rollback["status"] != expected_rollback:
            fail("El estado del journal contradice publicación/rollback.")
    elif value["state"] in {"prepared", "validated", "snapshot_saved", "aborted"}:
        if publication["status"] != "not_published" or rollback["status"] != "not_started":
            fail("Una operación anterior a publicación contiene metadatos posteriores.")

    recovery = value["recovery"]
    if (not isinstance(recovery, dict) or set(recovery) != {"attempts", "last_action", "last_error"}
            or type(recovery["attempts"]) is not int or recovery["attempts"] < 0
            or (recovery["last_action"] is not None and not isinstance(recovery["last_action"], str))
            or (recovery["last_error"] is not None and not isinstance(recovery["last_error"], str))):
        fail("Metadatos de recuperación inválidos en journal runtime.")
    return value


def write_journal(operation_dir: Path, journal: dict) -> None:
    journal["updated_at"] = now()
    atomic_write(operation_dir / "journal.json", json_bytes(journal), 0, 0, 0o600)


def verify_snapshot(operation_dir: Path, journal: dict) -> bool:
    snapshot_path = operation_dir / "snapshot.json"
    if snapshot_path.is_symlink():
        fail("Metadatos snapshot es un symlink.")
    if not snapshot_path.exists():
        return False
    check_dir(operation_dir / "snapshot", 0o700, 0, 0)
    raw = read_regular(snapshot_path, MAX_JOURNAL, 0, 0, 0o600, "metadatos snapshot")
    snapshot = strict_json(raw, "Metadatos snapshot")
    expected_fields = {
        "schema_version", "operation_id", "source", "staged_config_sha256",
        "service_state", "previous_config", "no_previous_config", "leases",
    }
    if (not isinstance(snapshot, dict) or set(snapshot) != expected_fields
            or type(snapshot.get("schema_version")) is not int or snapshot.get("schema_version") != 1
            or snapshot.get("operation_id") != journal["operation_id"]
            or snapshot.get("source") != journal["source"]
            or snapshot.get("service_state") != journal["service"]
            or snapshot.get("staged_config_sha256") != journal["staging"]["config_sha256"]
            or snapshot.get("leases") != journal["staging"]["leases"]):
        fail("Los metadatos snapshot no corresponden al journal.")
    previous = snapshot.get("previous_config")
    if not isinstance(previous, dict) or not isinstance(previous.get("present"), bool):
        fail("Metadatos de configuración anterior inválidos.")
    if snapshot["no_previous_config"] is not (not previous["present"]):
        fail("no_previous_config no coincide con los metadatos del snapshot.")
    if previous["present"]:
        required_previous = {"present", "file", "sha256", "size_bytes", "uid", "gid", "mode"}
        if (set(previous) != required_previous or previous["file"] != "snapshot/config.json"
                or not isinstance(previous["sha256"], str) or not SHA_RE.fullmatch(previous["sha256"])
                or type(previous["size_bytes"]) is not int or not 1 <= previous["size_bytes"] <= MAX_FILE
                or type(previous["uid"]) is not int or previous["uid"] != 0
                or type(previous["gid"]) is not int or previous["gid"] != journal["service"]["gid"]
                or type(previous["mode"]) is not int or previous["mode"] != 0o640
                or journal["snapshot"]["previous_config_present"] is not True
                or journal["snapshot"]["previous_config_sha256"] != previous["sha256"]):
            fail("Metadatos del snapshot anterior incompletos o inseguros.")
    elif (previous != {"present": False, "reason": "no_previous_config"}
          or journal["snapshot"]["previous_config_present"] is not False
          or journal["snapshot"]["previous_config_sha256"] is not None):
        fail("La ausencia de configuración previa no usa el marcador esperado.")
    config_path = operation_dir / "snapshot" / "config.json"
    if previous["present"]:
        data = read_regular(config_path, MAX_FILE, 0, 0, 0o600, "snapshot config.json")
        if (hashlib.sha256(data).hexdigest() != previous.get("sha256")
                or len(data) != previous.get("size_bytes")):
            fail("El snapshot de configuración anterior no supera la integridad.")
    elif config_path.exists() or config_path.is_symlink():
        fail("Existe un archivo snapshot inesperado para no_previous_config.")
    return True


def check_operation_store(path: Path) -> None:
    check_dir(path, 0o700, 0, 0)
    marker = read_regular(
        path / ".xray-manager-r03-operations-fixture", 4096,
        0, 0, 0o600, "marcador operation_store fixture"
    )
    if strict_json(marker, "Marcador operation_store") != {
        "schema_version": 1, "purpose": "xray-runtime-r03-isolated-operations"
    }:
        fail("operation_store no corresponde al fixture aislado R-03.")


def check_fixture_locks(operation_store: Path, lifecycle_lock: Path,
                        application_lock: Path) -> None:
    root = Path(os.path.abspath(operation_store))
    lifecycle = Path(os.path.abspath(lifecycle_lock))
    application = Path(os.path.abspath(application_lock))
    if lifecycle == application:
        fail("Los locks lifecycle/application deben ser archivos distintos.")
    for path in (lifecycle, application):
        try:
            path.relative_to(root)
        except ValueError:
            fail("Los locks R-03 deben permanecer dentro del operation_store fixture.")
        reject_symlinks(path, "Lock fixture")
        check_dir(path.parent, 0o700, 0, 0)


def ensure_no_active_operation(operations: Path) -> None:
    for operation_dir in sorted(operations.iterdir()):
        if operation_dir.is_symlink() or not operation_dir.is_dir():
            fail("operation_store contiene una entrada inesperada.")
        existing = read_journal(operation_dir)
        if existing["state"] not in {"aborted", "rolled_back"}:
            fail(
                "Existe otra operación runtime no terminal "
                f"({existing['operation_id']}, {existing['state']}); recupérela antes de crear otra."
            )


def prepare_operation(
    *,
    staging_dir: Path,
    service_root: Path,
    service_state: Path,
    operation_store: Path,
    lifecycle_lock: Path,
    application_lock: Path,
    lease_root: Path,
    service_uid: int,
    service_gid: int,
    crash_at: str | None = None,
) -> dict:
    if os.geteuid() != 0:
        fail("R-03 requiere root en el entorno aislado.")
    if service_uid <= 0 or service_gid <= 0:
        fail("UID/GID de servicio fixture deben ser no privilegiados.")
    fixture_root(service_root)
    check_operation_store(operation_store)
    check_fixture_locks(operation_store, lifecycle_lock, application_lock)
    operations = operation_store / "operations"

    locks = []
    try:
        locks.append(acquire_lock(lifecycle_lock))
        locks.append(acquire_lock(application_lock))
        if not operations.exists():
            os.mkdir(operations, 0o700)
            os.chown(operations, 0, 0)
            os.chmod(operations, 0o700)
            fsync_dir(operation_store)
        check_dir(operations, 0o700, 0, 0)
        ensure_no_active_operation(operations)
        manifest, staged_bytes, lease_data = read_staging(
            staging_dir, lease_root, service_uid, service_gid
        )
        service = service_fixture(service_state, manifest["xray_binary"]["path"])
        if service["active_state"] not in {"active", "inactive", "failed"}:
            fail("Estado previo de servicio no admitido.")
        old_config, old_meta = previous_config(service_root, service_gid)

        operation_id = "runtime-op-" + secrets.token_hex(16)
        operation_dir = operations / operation_id
        os.mkdir(operation_dir, 0o700)
        os.chown(operation_dir, 0, 0)
        os.chmod(operation_dir, 0o700)
        fsync_dir(operations)
        journal = {
            "schema_version": 1,
            "operation_id": operation_id,
            "state": "prepared",
            "created_at": now(),
            "updated_at": now(),
            "source": {
                "profile_id": manifest["profile_id"],
                "revision": manifest["revision"],
                "validation_id": manifest["validation_id"],
                "profile_content_sha256": manifest["profile_content_sha256"],
            },
            "staging": {
                "fixture_root": manifest["fixture_root"],
                "staging_dir": str(staging_dir.absolute()),
                "lease_root": str(lease_root.absolute()),
                "staging_manifest_sha256": lease_data["manifest_sha256"],
                "config_sha256": hashlib.sha256(staged_bytes).hexdigest(),
                "config_size_bytes": len(staged_bytes),
                "bindings_sha256": manifest["bindings_sha256"],
                "bindings": manifest["bindings"],
                "leases": lease_data["leases"],
            },
            "service": {
                "unit": service["unit"],
                "load_state": service["load_state"],
                "active_state": service["active_state"],
                "sub_state": service["sub_state"],
                "user": service["user"],
                "group": service["group"],
                "binary_path": service["binary_path"],
                "service_root": str(service_root.absolute()),
                "uid": service_uid,
                "gid": service_gid,
            },
            "snapshot": {
                "status": "pending",
                "previous_config_present": old_meta["present"],
                "previous_config_sha256": old_meta.get("sha256"),
                "metadata_sha256": None,
            },
            "publication": {
                "status": "not_published", "target": "etc/xray/config.json",
                "config_sha256": None, "published_at": None,
            },
            "rollback": {
                "status": "not_started", "started_at": None, "completed_at": None,
                "restored_config_sha256": None, "validation": None, "last_error": None,
            },
            "recovery": {"attempts": 0, "last_action": None, "last_error": None},
        }
        write_journal(operation_dir, journal)
        fsync_dir(operation_dir)
        if crash_at == "after_prepared":
            raise SimulatedCrash("after_prepared")

        (operation_dir / "snapshot").mkdir(mode=0o700)
        os.chown(operation_dir / "snapshot", 0, 0)
        os.chmod(operation_dir / "snapshot", 0o700)
        fsync_dir(operation_dir)
        if crash_at == "after_snapshot_dir":
            raise SimulatedCrash("after_snapshot_dir")
        journal["state"] = "validated"
        write_journal(operation_dir, journal)
        if crash_at == "after_validated":
            raise SimulatedCrash("after_validated")

        if old_config is not None:
            atomic_write(operation_dir / "snapshot" / "config.json", old_config, 0, 0, 0o600)
            if crash_at == "after_snapshot_config":
                raise SimulatedCrash("after_snapshot_config")

        snapshot = {
            "schema_version": 1,
            "operation_id": operation_id,
            "source": journal["source"],
            "staged_config_sha256": journal["staging"]["config_sha256"],
            "service_state": journal["service"],
            "previous_config": old_meta,
            "no_previous_config": not old_meta["present"],
            "leases": lease_data["leases"],
        }
        snapshot_bytes = json_bytes(snapshot)
        atomic_write(operation_dir / "snapshot.json", snapshot_bytes, 0, 0, 0o600)
        if crash_at == "after_snapshot_metadata":
            raise SimulatedCrash("after_snapshot_metadata")

        journal["snapshot"]["status"] = "saved"
        journal["snapshot"]["metadata_sha256"] = hashlib.sha256(snapshot_bytes).hexdigest()
        journal["state"] = "snapshot_saved"
        write_journal(operation_dir, journal)
        fsync_dir(operation_dir / "snapshot")
        fsync_dir(operation_dir)
        if crash_at == "after_snapshot_saved":
            raise SimulatedCrash("after_snapshot_saved")

        return {
            "status": "SNAPSHOT_SAVED",
            "operation_id": operation_id,
            "operation_dir": str(operation_dir),
            "profile_id": journal["source"]["profile_id"],
            "revision": journal["source"]["revision"],
            "validation_id": journal["source"]["validation_id"],
            "previous_config": "saved" if old_meta["present"] else "no_previous_config",
            "previous_service_state": service["active_state"],
            "snapshot_sha256": journal["snapshot"]["metadata_sha256"],
            "runtime_published": False,
            "service_action_performed": False,
        }
    finally:
        release_locks(locks)


def recover_store(
    operation_store: Path,
    lifecycle_lock: Path,
    application_lock: Path,
) -> dict:
    if os.geteuid() != 0:
        fail("La recuperación R-03 requiere root en el entorno aislado.")
    check_operation_store(operation_store)
    check_fixture_locks(operation_store, lifecycle_lock, application_lock)
    operations = operation_store / "operations"
    locks = []
    recovered = []
    try:
        locks.append(acquire_lock(lifecycle_lock))
        locks.append(acquire_lock(application_lock))
        if not operations.exists():
            return {"status": "RECOVERY_COMPLETE", "operations": [], "runtime_modified": False}
        check_dir(operations, 0o700, 0, 0)
        for operation_dir in sorted(operations.iterdir()):
            if operation_dir.is_symlink() or not operation_dir.is_dir():
                fail("El almacén de operaciones contiene una entrada inesperada.")
            if not OP_RE.fullmatch(operation_dir.name):
                fail("ID de directorio de operación inesperado.")
            check_dir(operation_dir, 0o700, 0, 0)
            clean_atomic_temps(operation_dir)
            snapshot_dir = operation_dir / "snapshot"
            if snapshot_dir.is_symlink():
                fail("Directorio snapshot es un symlink; se conserva evidencia.")
            if snapshot_dir.exists():
                clean_atomic_temps(snapshot_dir)
            if not (operation_dir / "journal.json").exists():
                # SIGKILL entre mkdir(operation_dir) y el primer journal:
                # no hubo snapshot ni escritura runtime; sólo se elimina el
                # contenedor vacío creado por esta operación incompleta.
                entries = list(operation_dir.iterdir())
                if entries:
                    if len(entries) == 1 and entries[0].name == "snapshot" and entries[0].is_dir():
                        check_dir(entries[0], 0o700, 0, 0)
                        if any(entries[0].iterdir()):
                            fail("Operación sin journal contiene snapshot inesperado; se conserva evidencia.")
                        entries[0].rmdir()
                    else:
                        fail("Operación sin journal contiene artefactos inesperados; se conserva evidencia.")
                operation_dir.rmdir()
                fsync_dir(operations)
                recovered.append({"operation_id": operation_dir.name, "state": "aborted", "action": "removed_empty_orphan"})
                continue
            journal = read_journal(operation_dir)
            if journal["state"] == "snapshot_saved":
                try:
                    if not verify_snapshot(operation_dir, journal):
                        raise RuntimeJournalError("Snapshot ausente en operación marcada snapshot_saved.")
                    snapshot_data = read_regular(operation_dir / "snapshot.json", MAX_JOURNAL, 0, 0, 0o600, "metadatos snapshot")
                    digest = hashlib.sha256(snapshot_data).hexdigest()
                    if journal["snapshot"]["metadata_sha256"] != digest:
                        raise RuntimeJournalError("Hash de metadatos snapshot no coincide con journal.")
                except RuntimeJournalError as exc:
                    journal["state"] = "recovery_required"
                    journal["recovery"]["attempts"] += 1
                    journal["recovery"]["last_action"] = "snapshot_integrity_failure"
                    journal["recovery"]["last_error"] = str(exc)[:240]
                    write_journal(operation_dir, journal)
                    recovered.append({"operation_id": journal["operation_id"], "state": "recovery_required", "action": "preserved"})
                    continue
                recovered.append({"operation_id": journal["operation_id"], "state": "snapshot_saved", "action": "verified_no_op"})
                continue
            if journal["state"] in {"aborted", "recovery_required"}:
                recovered.append({"operation_id": journal["operation_id"], "state": journal["state"], "action": "no_op"})
                continue
            if journal["state"] in {
                "config_published", "rollback_started", "rollback_config_restored",
                "rollback_failed", "rolled_back",
            }:
                recovered.append({
                    "operation_id": journal["operation_id"],
                    "state": journal["state"],
                    "action": "deferred_to_R04_R05_recovery",
                })
                continue
            if journal["state"] not in {"prepared", "validated"}:
                fail("Estado de journal no reconocido para recuperación R-03.")
            try:
                complete = verify_snapshot(operation_dir, journal)
            except RuntimeJournalError as exc:
                journal["state"] = "recovery_required"
                journal["recovery"]["attempts"] += 1
                journal["recovery"]["last_action"] = "preserve_incomplete_snapshot"
                journal["recovery"]["last_error"] = str(exc)[:240]
                write_journal(operation_dir, journal)
                recovered.append({"operation_id": journal["operation_id"], "state": "recovery_required", "action": "preserved"})
                continue
            if complete:
                snapshot_data = read_regular(operation_dir / "snapshot.json", MAX_JOURNAL, 0, 0, 0o600, "metadatos snapshot")
                journal["snapshot"]["status"] = "saved"
                journal["snapshot"]["metadata_sha256"] = hashlib.sha256(snapshot_data).hexdigest()
                journal["state"] = "snapshot_saved"
                journal["recovery"]["attempts"] += 1
                journal["recovery"]["last_action"] = "completed_snapshot_commit"
                journal["recovery"]["last_error"] = None
                write_journal(operation_dir, journal)
                fsync_dir(operation_dir)
                recovered.append({"operation_id": journal["operation_id"], "state": "snapshot_saved", "action": "completed"})
            else:
                journal["state"] = "aborted"
                journal["recovery"]["attempts"] += 1
                journal["recovery"]["last_action"] = "aborted_before_snapshot"
                journal["recovery"]["last_error"] = None
                write_journal(operation_dir, journal)
                recovered.append({"operation_id": journal["operation_id"], "state": "aborted", "action": "aborted"})
        fsync_dir(operations)
        return {"status": "RECOVERY_COMPLETE", "operations": recovered, "runtime_modified": False}
    finally:
        release_locks(locks)


def inspect_operation(operation_store: Path, operation_id: str) -> dict:
    if not OP_RE.fullmatch(operation_id):
        fail("operation_id inválido.")
    operations = operation_store / "operations"
    check_operation_store(operation_store)
    check_dir(operations, 0o700, 0, 0)
    operation_dir = operations / operation_id
    journal = read_journal(operation_dir)
    return {
        "operation_id": operation_id,
        "state": journal["state"],
        "source": journal["source"],
        "service": journal["service"],
        "snapshot": journal["snapshot"],
        "recovery": journal["recovery"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare", help="crea snapshot/journal sin publicar runtime")
    prepare.add_argument("--staging-dir", required=True)
    prepare.add_argument("--service-root", required=True, help="XRAY_SERVICE_ROOT temporal con marcador fixture")
    prepare.add_argument("--service-state", required=True)
    prepare.add_argument("--operation-store", required=True)
    prepare.add_argument("--lifecycle-lock", required=True)
    prepare.add_argument("--application-lock", required=True)
    prepare.add_argument("--lease-root", required=True)
    prepare.add_argument("--service-uid", type=int, required=True)
    prepare.add_argument("--service-gid", type=int, required=True)
    recover = sub.add_parser("recover", help="recupera journals R-03 idempotentemente")
    recover.add_argument("--operation-store", required=True)
    recover.add_argument("--lifecycle-lock", required=True)
    recover.add_argument("--application-lock", required=True)
    inspect = sub.add_parser("inspect", help="consulta un journal sin modificarlo")
    inspect.add_argument("--operation-store", required=True)
    inspect.add_argument("--operation-id", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "prepare":
            result = prepare_operation(
                staging_dir=Path(args.staging_dir),
                service_root=Path(args.service_root),
                service_state=Path(args.service_state),
                operation_store=Path(args.operation_store),
                lifecycle_lock=Path(args.lifecycle_lock),
                application_lock=Path(args.application_lock),
                lease_root=Path(args.lease_root),
                service_uid=args.service_uid,
                service_gid=args.service_gid,
            )
        elif args.command == "recover":
            result = recover_store(Path(args.operation_store), Path(args.lifecycle_lock), Path(args.application_lock))
        else:
            result = inspect_operation(Path(args.operation_store), args.operation_id)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (RuntimeJournalError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
