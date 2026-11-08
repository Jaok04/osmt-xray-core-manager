#!/usr/bin/env python3
"""Primitive de laboratorio B4: memfd sellado y evidencia por invocación.

Este módulo no está conectado al menú, R-05 ni al backend live. Todas las
escrituras de evidencia exigen un directorio fixture marcado.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import secrets
import stat
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
MAX_CONFIG_BYTES = 16 * 1024 * 1024
INVOCATION_RE = re.compile(r"[0-9a-fA-F]{32}\Z")
REQUIRED_SEALS = (
    getattr(fcntl, "F_SEAL_WRITE", 0x0008)
    | getattr(fcntl, "F_SEAL_GROW", 0x0004)
    | getattr(fcntl, "F_SEAL_SHRINK", 0x0002)
    | getattr(fcntl, "F_SEAL_SEAL", 0x0001)
)


class ConfigAttestationError(Exception):
    """Error controlado de preparación o verificación B4."""


def _fail(message: str) -> None:
    raise ConfigAttestationError(message)


def _check_fixture_root(root: Path) -> None:
    root = Path(root)
    if not root.is_absolute():
        _fail("La raíz fixture debe ser absoluta.")
    current = Path("/")
    for part in root.parts[1:]:
        current = current / part
        try:
            info = current.lstat()
        except OSError:
            _fail("No se pudo verificar la ruta fixture.")
        if stat.S_ISLNK(info.st_mode):
            _fail("La ruta fixture contiene un symlink.")
    info = root.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid():
        _fail("La raíz fixture tiene tipo o propietario inesperado.")
    marker = root / ".xray-manager-fixture"
    try:
        marker_info = marker.lstat()
    except OSError:
        _fail("Falta el marcador fixture requerido.")
    if (not stat.S_ISREG(marker_info.st_mode) or marker_info.st_uid != os.geteuid()
            or marker_info.st_nlink != 1 or stat.S_IMODE(marker_info.st_mode) != 0o600):
        _fail("El marcador fixture no es seguro.")


def create_sealed_memfd(
    config: bytes, expected_sha256: str, *, owner_uid: int | None = None,
    owner_gid: int | None = None, mode: int | None = None,
) -> tuple[int, dict[str, Any]]:
    """Crea un descriptor heredable, inmutable y verificado.

    La asignación opcional de propietario/modo ocurre antes de sellar el inode,
    de modo que un supervisor con CAP_CHOWN puede transferirlo sin CAP_FOWNER.
    """
    if not isinstance(config, bytes) or not config or len(config) > MAX_CONFIG_BYTES:
        _fail("Los bytes de configuración están vacíos o exceden el límite.")
    digest = hashlib.sha256(config).hexdigest()
    if not isinstance(expected_sha256, str) or digest != expected_sha256:
        _fail("El SHA-256 de entrada no coincide con el esperado.")
    if not hasattr(os, "memfd_create") or not hasattr(fcntl, "F_ADD_SEALS"):
        _fail("El kernel/Python no ofrece memfd y seals requeridos.")
    if ((owner_uid is None) != (owner_gid is None)
            or (owner_uid is not None and (type(owner_uid) is not int or owner_uid < 0))
            or (owner_gid is not None and (type(owner_gid) is not int or owner_gid < 0))
            or (mode is not None and (type(mode) is not int or mode < 0 or mode > 0o777))):
        _fail("Propietario o modo de memfd inválido.")
    try:
        fd = os.memfd_create("xray-manager-config", os.MFD_ALLOW_SEALING)
        os.set_inheritable(fd, True)
        view = memoryview(config)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                _fail("Escritura incompleta del memfd.")
            view = view[written:]
        os.fsync(fd)
        if mode is not None:
            os.fchmod(fd, mode)
        if owner_uid is not None and owner_gid is not None:
            os.fchown(fd, owner_uid, owner_gid)
        fcntl.fcntl(fd, fcntl.F_ADD_SEALS, REQUIRED_SEALS)
        seals = fcntl.fcntl(fd, fcntl.F_GET_SEALS)
        if seals & REQUIRED_SEALS != REQUIRED_SEALS:
            _fail("El kernel no confirmó todos los seals requeridos.")
        os.lseek(fd, 0, os.SEEK_SET)
        readback = bytearray()
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            readback.extend(chunk)
        if bytes(readback) != config or hashlib.sha256(readback).hexdigest() != digest:
            _fail("La lectura posterior del memfd no coincide con la configuración.")
        os.lseek(fd, 0, os.SEEK_SET)
        return fd, {
            "sha256": digest,
            "size_bytes": len(config),
            "seals": seals,
            "required_seals": REQUIRED_SEALS,
            "inheritable": os.get_inheritable(fd),
            **({"owner_uid": os.fstat(fd).st_uid, "owner_gid": os.fstat(fd).st_gid,
                "mode": stat.S_IMODE(os.fstat(fd).st_mode)} if mode is not None else {}),
        }
    except Exception:
        try:
            os.close(fd)
        except (OSError, UnboundLocalError):
            pass
        raise


def write_invocation_evidence(
    *, fixture_root: Path, evidence_dir: Path, fd_metadata: dict[str, Any],
    pid: int, invocation_id: str,
) -> Path:
    """Escritura atómica root/owner-only de evidencia previa a exec (fixture)."""
    root = Path(fixture_root)
    directory = Path(evidence_dir)
    _check_fixture_root(root)
    if directory.parent != root or directory.is_symlink():
        _fail("El directorio de evidencia debe ser hijo directo de la raíz fixture.")
    try:
        directory.mkdir(mode=0o700)
    except FileExistsError:
        pass
    info = directory.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
            or info.st_nlink != 2 or stat.S_IMODE(info.st_mode) != 0o700):
        _fail("El directorio de evidencia tiene tipo, propietario o permisos inseguros.")
    if type(pid) is not int or pid <= 1:
        _fail("PID de evidencia inválido.")
    if not isinstance(invocation_id, str) or not INVOCATION_RE.fullmatch(invocation_id):
        _fail("InvocationID inválido.")
    digest = fd_metadata.get("sha256")
    size = fd_metadata.get("size_bytes")
    seals = fd_metadata.get("seals")
    if (not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)
            or type(size) is not int or not 1 <= size <= MAX_CONFIG_BYTES
            or type(seals) is not int or seals & REQUIRED_SEALS != REQUIRED_SEALS
            or fd_metadata.get("inheritable") is not True):
        _fail("Metadatos del descriptor sellado inválidos.")
    record = {
        "schema_version": SCHEMA_VERSION,
        "pid": pid,
        "invocation_id": invocation_id.lower(),
        "config_sha256": digest,
        "config_size_bytes": size,
        "seals": seals,
        "evidence_status": "prepared_before_exec",
    }
    data = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
    target = directory / (invocation_id.lower() + ".json")
    if target.exists() or target.is_symlink():
        _fail("Ya existe evidencia para esta InvocationID; replay rechazado.")
    temp = directory / (".evidence-" + secrets.token_hex(16) + ".tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(temp, flags, 0o600)
    try:
        os.fchown(fd, os.geteuid(), os.getegid())
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(temp, target)
    dir_fd = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)
    return target


def verify_invocation_evidence(
    *, evidence_path: Path, fixture_root: Path, expected_sha256: str,
    expected_size: int, main_pid: int, invocation_id: str,
) -> dict[str, Any]:
    """Correlaciona evidencia con snapshot fixture; no consulta systemd."""
    _check_fixture_root(Path(fixture_root))
    path = Path(evidence_path)
    if path.parent.parent != Path(fixture_root) or path.is_symlink():
        _fail("Ruta de evidencia fuera de fixture o simbólica.")
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
            or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_size < 2 or info.st_size > 4096):
        _fail("Archivo de evidencia inseguro.")
    raw = path.read_bytes()
    try:
        record = json.loads(raw)
    except (UnicodeError, json.JSONDecodeError):
        _fail("Evidencia JSON inválida.")
    if (not isinstance(record, dict) or record.get("schema_version") != SCHEMA_VERSION
            or record.get("evidence_status") != "prepared_before_exec"
            or record.get("pid") != main_pid
            or record.get("invocation_id") != invocation_id.lower()
            or record.get("config_sha256") != expected_sha256
            or record.get("config_size_bytes") != expected_size
            or type(record.get("seals")) is not int
            or record["seals"] & REQUIRED_SEALS != REQUIRED_SEALS):
        _fail("Evidencia no corresponde al proceso, InvocationID o configuración esperada.")
    return {
        "verified": True,
        "environment": "fixture",
        "configuration_loaded": True,
        "configuration_evidence": "sealed_memfd_correlated_to_fixture_process",
        "pid": main_pid,
        "invocation_id": invocation_id.lower(),
        "config_sha256": expected_sha256,
        "config_size_bytes": expected_size,
    }
