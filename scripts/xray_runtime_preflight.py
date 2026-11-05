#!/usr/bin/env python3
"""Preflight read-only de runtime ligado a una revisión exacta de perfil."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

import xray_profiles
from xray_profile_validation_store import ProfileValidationError, ProfileValidationReportStore

REQUIRED_CHECKS = {"json_syntax", "xray_structure", "required_parameters",
                   "types_values", "references_conflicts", "xray_native"}


class RuntimePreflightError(Exception):
    pass


def _fail(message: str) -> None:
    raise RuntimePreflightError(message)


def _read_root_file(path: Path, limit: int = 65536) -> bytes:
    if not path.is_absolute():
        _fail("La ruta del fixture debe ser absoluta.")
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        if current.is_symlink():
            _fail("El fixture de estado contiene un componente simbólico.")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                 | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NONBLOCK", 0))
    try:
        st = os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_gid != 0
                or st.st_nlink != 1 or stat.S_IMODE(st.st_mode) != 0o600
                or st.st_size > limit):
            _fail("El fixture de estado de servicio tiene permisos o tipo inseguros.")
        chunks = []
        remaining = limit + 1
        while remaining:
            part = os.read(fd, min(65536, remaining))
            if not part:
                break
            chunks.append(part)
            remaining -= len(part)
        data = b"".join(chunks)
        if len(data) != st.st_size or len(data) > limit:
            _fail("El fixture de estado cambió durante su lectura.")
        return data
    finally:
        os.close(fd)


def _strict_object(data: bytes, label: str) -> dict[str, Any]:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate")
            result[key] = value
        return result
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError("constant")))
    except (UnicodeError, ValueError, json.JSONDecodeError):
        _fail(f"{label} no contiene JSON estricto.")
    if not isinstance(value, dict):
        _fail(f"{label} debe ser un objeto JSON.")
    return value


def _profile_read_lock(store: xray_profiles.ProfileStore):
    """Bloqueo compartido puro: evita ProfileStore.locked(), que también limpia huérfanos."""
    root = store.root
    lock = store.lock_path
    for path in (root, store.profiles, lock):
        try:
            st = path.lstat()
        except FileNotFoundError:
            _fail("El almacén de perfiles no está inicializado.")
        if stat.S_ISLNK(st.st_mode):
            _fail("El almacén de perfiles contiene una ruta simbólica.")
    rst, pst, lst = root.stat(), store.profiles.stat(), lock.stat()
    if (not stat.S_ISDIR(rst.st_mode) or rst.st_uid != 0 or stat.S_IMODE(rst.st_mode) != 0o700
            or not stat.S_ISDIR(pst.st_mode) or pst.st_uid != 0 or stat.S_IMODE(pst.st_mode) != 0o700
            or not stat.S_ISREG(lst.st_mode) or lst.st_uid != 0 or lst.st_gid != 0
            or lst.st_nlink != 1 or stat.S_IMODE(lst.st_mode) != 0o600):
        _fail("El almacén/lock de perfiles tiene permisos inseguros.")
    fd = os.open(lock, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        fst = os.fstat(fd)
        if not stat.S_ISREG(fst.st_mode) or fst.st_uid != 0 or fst.st_gid != 0 or fst.st_nlink != 1 or stat.S_IMODE(fst.st_mode) != 0o600:
            _fail("Lock de perfiles inseguro.")
        fcntl.flock(fd, fcntl.LOCK_SH)
        return fd
    except Exception:
        os.close(fd)
        raise


def _inspect_binary(path: Path) -> dict[str, Any]:
    if not path.is_absolute():
        _fail("La ruta del binario Xray debe ser absoluta.")
    current = Path("/")
    for part in path.parts[1:]:
        current = current / part
        if current.is_symlink():
            _fail("El binario Xray o uno de sus componentes es symlink.")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                 | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NONBLOCK", 0))
    try:
        st = os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_nlink != 1
                or stat.S_IMODE(st.st_mode) & 0o022 or not st.st_mode & 0o111):
            _fail("El binario Xray debe ser regular, root-owned, ejecutable y no modificable por grupo/otros.")
        digest = hashlib.sha256()
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        return {"path": str(path), "sha256": digest.hexdigest(), "size_bytes": st.st_size}
    finally:
        os.close(fd)


def _validate_service_fixture(path: Path, binary_path: str) -> dict[str, Any]:
    value = _strict_object(_read_root_file(path), "Fixture de estado")
    required = {"unit", "load_state", "active_state", "sub_state", "user", "group", "binary_path"}
    if set(value) != required:
        _fail("El fixture de estado no cumple el contrato R-01.")
    if (value["unit"] != "xray.service" or value["load_state"] != "loaded"
            or not isinstance(value["active_state"], str)
            or value["active_state"] not in {"active", "inactive", "failed", "unknown"}
            or not isinstance(value["sub_state"], str) or not value["sub_state"]
            or value["user"] != "xray" or value["group"] != "xray"
            or value["binary_path"] != binary_path):
        _fail("El fixture no describe la unidad Xray esperada o no coincide con el binario.")
    if value["active_state"] == "active" and value["sub_state"] not in {"running", "listening"}:
        _fail("Subestado activo incoherente en el fixture.")
    if value["active_state"] == "inactive" and value["sub_state"] not in {"dead", "inactive"}:
        _fail("Subestado inactivo incoherente en el fixture.")
    if value["active_state"] == "failed" and value["sub_state"] != "failed":
        _fail("Subestado failed incoherente en el fixture.")
    if value["active_state"] == "unknown" and value["sub_state"] != "unknown":
        _fail("Subestado unknown incoherente en el fixture.")
    return value


def preflight(profile_store: str, master_key: str, validation_store: str,
              profile_id: str, revision: str, xray_binary: str,
              service_state: str) -> dict[str, Any]:
    profiles = xray_profiles.ProfileStore(profile_store, master_key)
    reports = ProfileValidationReportStore(validation_store)
    binary = _inspect_binary(Path(xray_binary))
    service = _validate_service_fixture(Path(service_state), xray_binary)

    lock_fd = _profile_read_lock(profiles)
    try:
        metadata = profiles.load_metadata(profile_id)
        content, manifest = profiles.read_revision_config(profile_id, revision)
        digest = hashlib.sha256(content).hexdigest()
        if revision == metadata["current_revision"]:
            if (metadata["validation_status"] != "valid"
                    or metadata["last_validated_revision"] != revision):
                _fail("Los metadatos del perfil actual no identifican esta revisión como validada.")
        validation = manifest["validation"]
        if (validation["json_syntax"] != "pass"
                or validation["xray_static"] != "pass"
                or validation["status"] != "valid"):
            _fail("El manifiesto no identifica esta revisión como validada.")
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)

    try:
        report = reports.latest_for_revision(profile_id, revision)
    except ProfileValidationError as exc:
        raise RuntimePreflightError(str(exc)) from exc
    if (report["result"] not in {"PASS", "PASS_WITH_WARNINGS"} or report["profile_id"] != profile_id
            or report["revision"] != revision or report["content_sha256"] != digest
            or report["content_size_bytes"] != len(content)):
        _fail("El informe persistido no corresponde exactamente al perfil/revisión y contenido.")
    checks = {item["name"]: item["status"] for item in report["checks"]}
    if not REQUIRED_CHECKS.issubset(checks) or any(checks[name] != "PASS" for name in REQUIRED_CHECKS):
        _fail("El informe no acredita todas las comprobaciones estáticas y nativas requeridas.")
    report_binary = report.get("xray", {}).get("binary_sha256")
    if report_binary != binary["sha256"]:
        _fail("El informe fue generado con un binario Xray distinto del seleccionado.")
    return {
        "status": "PREFLIGHT_PASS",
        "profile_id": profile_id,
        "revision": revision,
        "validation_id": report["validation_id"],
        "content_sha256": digest,
        "content_size_bytes": len(content),
        "xray": binary,
        "service_fixture": service,
        "runtime_published": False,
        "service_action_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight read-only de runtime por perfil/revisión.")
    parser.add_argument("--profile-store", required=True)
    parser.add_argument("--master-key", required=True)
    parser.add_argument("--validation-store", required=True)
    parser.add_argument("--profile-id", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--xray-binary", required=True)
    parser.add_argument("--service-state", required=True, help="Fixture root-owned 0600; nunca consulta systemd real.")
    args = parser.parse_args()
    try:
        result = preflight(args.profile_store, args.master_key, args.validation_store,
                           args.profile_id, args.revision, args.xray_binary, args.service_state)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (RuntimePreflightError, xray_profiles.ProfileError, ProfileValidationError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
