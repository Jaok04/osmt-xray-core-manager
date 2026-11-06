#!/usr/bin/env python3
"""Inspección read-only y fail-closed de identidad de un proceso Xray vía procfs.

No consulta systemd ni realiza operaciones mutadoras. La evidencia se limita
al proceso/ejecutable/argv/UID/GID observados; nunca acredita la configuración
que Xray haya cargado.
"""
from __future__ import annotations

import hashlib
import os
import re
import stat
from pathlib import Path

EXPECTED_EXECUTABLE = "/usr/local/bin/xray"
MAX_CMDLINE_BYTES = 1024 * 1024
MAX_EXECUTABLE_BYTES = 512 * 1024 * 1024


class ProcessIdentityError(Exception):
    """Error controlado al inspeccionar la identidad de un proceso."""


def _fail(message: str) -> None:
    raise ProcessIdentityError(message)


def _read_bounded(path: Path, limit: int) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        _fail("No se pudo leer la información requerida del proceso.")
    try:
        chunks = []
        total = 0
        while True:
            chunk = os.read(fd, min(65536, limit + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > limit:
                _fail("La información del proceso excede el límite permitido.")
        return b"".join(chunks)
    finally:
        os.close(fd)


def _proc_stat_starttime(raw: bytes, expected_pid: int) -> int:
    try:
        text = raw.decode("ascii")
        left = text.index("(")
        right = text.rindex(")")
        pid = int(text[:left].strip())
        fields_after_comm = text[right + 1:].strip().split()
        # fields_after_comm[0] es el campo 3 (state); starttime es campo 22.
        state = fields_after_comm[0]
        starttime = int(fields_after_comm[19])
    except (UnicodeError, ValueError, IndexError):
        _fail("procfs devolvió /stat mal formado.")
    if pid != expected_pid or starttime < 0:
        _fail("La identidad PID/starttime de procfs no es válida.")
    if state not in {"R", "S", "D", "T", "t", "W", "K", "P", "I"}:
        _fail("El estado del proceso no permite considerarlo un proceso Xray vivo.")
    return starttime


def _effective_id(raw: bytes, key: bytes) -> int:
    prefix = key + b":"
    matches = [line[len(prefix):].split() for line in raw.splitlines()
               if line.startswith(prefix)]
    if len(matches) != 1 or len(matches[0]) != 4:
        _fail("procfs devolvió identificadores UID/GID mal formados.")
    try:
        ids = [int(value) for value in matches[0]]
    except ValueError:
        _fail("procfs devolvió identificadores UID/GID no numéricos.")
    if any(value < 0 for value in ids):
        _fail("procfs devolvió identificadores UID/GID inválidos.")
    return ids[1]


def _read_executable_hash(exe_link: Path) -> tuple[str, tuple[int, int, int, int]]:
    try:
        fd = os.open(exe_link, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0))
    except OSError:
        _fail("No se pudo abrir el ejecutable asociado al proceso.")
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != 0
                or before.st_nlink != 1 or not before.st_mode & stat.S_IXUSR
                or before.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
                or before.st_size < 1 or before.st_size > MAX_EXECUTABLE_BYTES):
            _fail("El ejecutable del proceso tiene tipo, propietario, enlaces, permisos o tamaño inseguros.")
        digest = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_EXECUTABLE_BYTES:
                _fail("El ejecutable excede el tamaño máximo permitido.")
            digest.update(chunk)
        after = os.fstat(fd)
        signature_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        signature_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        if signature_before != signature_after or total != before.st_size:
            _fail("El ejecutable cambió durante su inspección.")
        return digest.hexdigest(), signature_after
    finally:
        os.close(fd)


def inspect_process(
    pid: int,
    *,
    expected_uid: int,
    expected_gid: int,
    expected_argv: tuple[str, ...] | list[str],
    expected_executable: str = EXPECTED_EXECUTABLE,
    proc_root: Path = Path("/proc"),
) -> dict:
    """Inspecciona un PID; proc_root alternativo se reserva a pruebas aisladas."""
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 1:
        _fail("MainPID debe ser un entero positivo mayor que 1.")
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0
           for value in (expected_uid, expected_gid)):
        _fail("Los UID/GID esperados no son válidos.")
    if (not isinstance(expected_executable, str) or not expected_executable.startswith("/")
            or "\x00" in expected_executable):
        _fail("La ruta esperada del ejecutable debe ser absoluta.")
    if not isinstance(expected_argv, (tuple, list)) or not expected_argv:
        _fail("Se requiere un argv esperado explícito.")
    if any(not isinstance(arg, str) or "\x00" in arg for arg in expected_argv):
        _fail("El argv esperado contiene argumentos inválidos.")

    root = Path(proc_root)
    if not root.is_absolute():
        _fail("La raíz procfs debe ser absoluta.")
    if root != Path("/proc"):
        marker = root / ".xray-manager-proc-fixture"
        try:
            marker_info = marker.lstat()
            marker_value = marker.read_text(encoding="ascii")
        except OSError:
            _fail("Una raíz procfs alternativa requiere un marcador fixture explícito.")
        if (not stat.S_ISREG(marker_info.st_mode) or marker_info.st_nlink != 1
                or marker_value != "xray-manager-proc-fixture-v1\n"):
            _fail("El marcador de raíz procfs fixture no es válido.")
    process_dir = root / str(pid)
    stat_path = process_dir / "stat"
    status_path = process_dir / "status"
    cmdline_path = process_dir / "cmdline"
    exe_link = process_dir / "exe"

    start_before = _proc_stat_starttime(_read_bounded(stat_path, 65536), pid)
    status = _read_bounded(status_path, 1024 * 1024)
    effective_uid = _effective_id(status, b"Uid")
    effective_gid = _effective_id(status, b"Gid")
    if effective_uid != expected_uid or effective_gid != expected_gid:
        _fail("La identidad efectiva UID/GID del proceso no coincide con xray:xray.")

    try:
        executable_path = os.readlink(exe_link)
    except OSError:
        _fail("No se pudo resolver /proc/PID/exe.")
    if executable_path.endswith(" (deleted)") or executable_path != expected_executable:
        _fail("El ejecutable asociado al proceso no coincide con el binario administrado.")

    raw_cmdline = _read_bounded(cmdline_path, MAX_CMDLINE_BYTES)
    if not raw_cmdline or not raw_cmdline.endswith(b"\0"):
        _fail("procfs devolvió cmdline vacío o truncado.")
    try:
        argv = tuple(part.decode("utf-8") for part in raw_cmdline[:-1].split(b"\0"))
    except UnicodeError:
        _fail("procfs devolvió cmdline con codificación inválida.")
    if argv != tuple(expected_argv):
        _fail("El argv efectivo del proceso no coincide con el contrato administrado.")

    executable_sha256, executable_signature = _read_executable_hash(exe_link)

    # Detectar execve/cambios de credenciales durante la ventana: starttime por
    # sí solo no cambia cuando un proceso ejecuta otro binario.
    try:
        executable_path_after = os.readlink(exe_link)
    except OSError:
        _fail("El ejecutable del proceso desapareció durante la inspección.")
    if executable_path_after != executable_path:
        _fail("El ejecutable asociado al proceso cambió durante la inspección.")

    cmdline_after = _read_bounded(cmdline_path, MAX_CMDLINE_BYTES)
    if not cmdline_after or not cmdline_after.endswith(b"\0"):
        _fail("cmdline dejó de ser válido durante la inspección.")
    try:
        argv_after = tuple(part.decode("utf-8") for part in cmdline_after[:-1].split(b"\0"))
    except UnicodeError:
        _fail("cmdline cambió a una codificación inválida durante la inspección.")
    if argv_after != argv:
        _fail("argv cambió durante la inspección del proceso.")

    status_after = _read_bounded(status_path, 1024 * 1024)
    if (_effective_id(status_after, b"Uid") != effective_uid
            or _effective_id(status_after, b"Gid") != effective_gid):
        _fail("UID/GID efectivos cambiaron durante la inspección.")

    executable_sha256_after, executable_signature_after = _read_executable_hash(exe_link)
    if (executable_sha256_after != executable_sha256
            or executable_signature_after != executable_signature):
        _fail("El ejecutable cambió durante la ventana de inspección.")

    # Releer starttime al final detecta desaparición/reutilización observable.
    # No convierte la lectura en una atestación de configuración cargada.
    start_after = _proc_stat_starttime(_read_bounded(stat_path, 65536), pid)
    if start_before != start_after:
        _fail("El PID desapareció o fue reutilizado durante la inspección.")

    return {
        "pid": pid,
        "process_starttime_ticks": start_before,
        "executable_path": executable_path,
        "executable_sha256": executable_sha256,
        "executable_signature": executable_signature,
        "argv": argv,
        "effective_uid": effective_uid,
        "effective_gid": effective_gid,
        "identity_verified": True,
        "configuration_loaded": False,
        "configuration_evidence": "not_attested",
        "read_only": True,
    }
