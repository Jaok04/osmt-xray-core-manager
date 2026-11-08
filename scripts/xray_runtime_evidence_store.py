#!/usr/bin/env python3
"""Almacén de evidencia persistente fixture-only para el contrato B4.3.

No conoce rutas live: exige una raíz marcada y un layout validado antes de
crear o leer evidencia. Los archivos se publican sin sobrescritura mediante
linkat dentro del directorio ya abierto.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import secrets
import stat
from typing import Any

import xray_runtime_directory_contract as directories

INVOCATION_RE = re.compile(r"[0-9a-f]{32}\Z")
MAX_RECORD_BYTES = 4096
DIR_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)


class EvidenceStoreError(Exception):
    """Error controlado del almacén fixture de evidencia."""


def _fail(message: str) -> None:
    raise EvidenceStoreError(message)


def _open_evidence_dir(root: pathlib.Path, service_gid: int) -> int:
    root = pathlib.Path(root)
    try:
        directories.validate_fixture_layout(root, service_gid)
        root_fd = os.open(root, DIR_FLAGS)
    except (OSError, directories.DirectoryContractError) as exc:
        raise EvidenceStoreError("El layout fixture de evidencia no es válido.") from exc

    opened: list[int] = [root_fd]
    try:
        root_info = os.fstat(root_fd)
        if (not stat.S_ISDIR(root_info.st_mode) or root_info.st_uid != os.geteuid()
                or stat.S_IMODE(root_info.st_mode) & 0o022):
            _fail("La raíz fixture abierta tiene propietario o permisos inseguros.")

        # Cada componente se abre relativo al descriptor del padre ya validado.
        # O_NOFOLLOW evita que una sustitución por symlink redirija la ruta.
        current = root_fd
        components = (
            ("var", 0o755),
            ("lib", 0o755),
            ("xray-manager", 0o700),
            ("evidence", 0o700),
        )
        for name, expected_mode in components:
            child = os.open(name, DIR_FLAGS, dir_fd=current)
            opened.append(child)
            info = os.fstat(child)
            if (not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_gid != 0
                    or stat.S_IMODE(info.st_mode) != expected_mode):
                _fail("Un componente anclado del almacén no conserva owner/group/mode.")
            current = child
        result = opened.pop()
        return result
    except OSError as exc:
        raise EvidenceStoreError("No se pudo abrir de forma segura la ruta anclada de evidencia.") from exc
    finally:
        for descriptor in opened:
            os.close(descriptor)


def _validate_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(metadata, dict):
        _fail("Los metadatos de invocación deben ser un objeto.")
    digest = metadata.get("config_sha256")
    size = metadata.get("config_size_bytes")
    pid = metadata.get("pid")
    if (not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)
            or type(size) is not int or not 1 <= size <= 16 * 1024 * 1024
            or type(pid) is not int or pid <= 1):
        _fail("Metadatos inválidos; no se admite contenido de configuración ni secretos.")
    forbidden = {"config", "config_bytes", "uuid", "password", "private_key", "pem", "secret"}
    if forbidden.intersection(key.lower() for key in metadata):
        _fail("Los metadatos contienen campos prohibidos.")
    return {"pid": pid, "config_sha256": digest, "config_size_bytes": size}


def create_evidence(*, fixture_root: pathlib.Path, service_gid: int,
                    invocation_id: str, metadata: dict[str, Any]) -> pathlib.Path:
    """Crea evidencia root-only de forma atómica y sin reemplazo."""
    if not isinstance(invocation_id, str) or not INVOCATION_RE.fullmatch(invocation_id):
        _fail("InvocationID debe ser hexadecimal lowercase de 32 caracteres.")
    clean = _validate_metadata(metadata)
    root = pathlib.Path(fixture_root)
    dir_fd = _open_evidence_dir(root, service_gid)
    name = invocation_id + ".json"
    temp = ".pending-" + secrets.token_hex(16) + ".tmp"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    data = (json.dumps({
        "schema_version": 1,
        "invocation_id": invocation_id,
        "evidence_status": "prepared_before_exec",
        **clean,
    }, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    fd = -1
    try:
        fd = os.open(temp, flags, 0o600, dir_fd=dir_fd)
        os.fchown(fd, 0, 0)
        os.fchmod(fd, 0o600)
        view = memoryview(data)
        while view:
            count = os.write(fd, view)
            if count <= 0:
                _fail("Escritura incompleta de evidencia.")
            view = view[count:]
        os.fsync(fd)
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_gid != 0
                or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600):
            _fail("El archivo temporal no conserva root:root 0600.")
        os.close(fd)
        fd = -1
        try:
            os.link(temp, name, src_dir_fd=dir_fd, dst_dir_fd=dir_fd,
                    follow_symlinks=False)
        except FileExistsError as exc:
            raise EvidenceStoreError("La InvocationID ya tiene evidencia; replay rechazado.") from exc
        os.unlink(temp, dir_fd=dir_fd)
        os.fsync(dir_fd)
        result = root / "var/lib/xray-manager/evidence" / name
        verify_evidence(fixture_root=root, service_gid=service_gid,
                        invocation_id=invocation_id)
        return result
    except EvidenceStoreError:
        try:
            os.unlink(temp, dir_fd=dir_fd)
        except OSError:
            pass
        raise
    except OSError as exc:
        try:
            os.unlink(temp, dir_fd=dir_fd)
        except OSError:
            pass
        raise EvidenceStoreError("No se pudo publicar evidencia atómicamente.") from exc
    finally:
        if fd >= 0:
            os.close(fd)
        os.close(dir_fd)


def verify_evidence(*, fixture_root: pathlib.Path, service_gid: int,
                    invocation_id: str) -> dict[str, Any]:
    """Reabre y verifica evidencia después de una simulación de reinicio."""
    if not isinstance(invocation_id, str) or not INVOCATION_RE.fullmatch(invocation_id):
        _fail("InvocationID inválida.")
    dir_fd = _open_evidence_dir(pathlib.Path(fixture_root), service_gid)
    name = invocation_id + ".json"
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        try:
            fd = os.open(name, flags, dir_fd=dir_fd)
        except OSError as exc:
            raise EvidenceStoreError("No existe evidencia regular para la InvocationID.") from exc
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_gid != 0
                    or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600
                    or not 2 <= info.st_size <= MAX_RECORD_BYTES):
                _fail("El inode de evidencia tiene tipo, enlaces, owner, modo o tamaño inválido.")
            chunks = []
            remaining = info.st_size
            while remaining:
                chunk = os.read(fd, remaining)
                if not chunk:
                    _fail("Lectura incompleta del registro de evidencia.")
                chunks.append(chunk)
                remaining -= len(chunk)
            raw = b"".join(chunks)
        finally:
            os.close(fd)
        try:
            record = json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise EvidenceStoreError("El registro de evidencia no es JSON válido.") from exc
        if (not isinstance(record, dict) or record.get("schema_version") != 1
                or record.get("invocation_id") != invocation_id
                or record.get("evidence_status") != "prepared_before_exec"):
            _fail("El registro no corresponde a la InvocationID solicitada.")
        _validate_metadata(record)
        return {"verified": True, "persistent": True, "record": record}
    finally:
        os.close(dir_fd)
