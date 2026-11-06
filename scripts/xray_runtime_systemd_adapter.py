#!/usr/bin/env python3
"""Observación read-only de xray.service para la futura integración R-06.

Este módulo no inicia, detiene, reinicia, habilita ni modifica unidades.
No afirma qué generación cargó el proceso: esa evidencia requiere una
atestación posterior ligada al InvocationID de systemd.
"""
from __future__ import annotations

import grp
import hashlib
import os
import re
import shlex
import stat
import subprocess
from pathlib import Path

UNIT = "xray.service"
DEFAULT_UNIT_FILE = Path("/etc/systemd/system/xray.service")
DEFAULT_CONFIG_FILE = Path("/etc/xray/config.json")
MAX_CONFIG_BYTES = 64 * 1024 * 1024
TIMEOUT_SECONDS = 8

PROPERTIES = (
    "LoadState",
    "ActiveState",
    "SubState",
    "Result",
    "ExecMainStatus",
    "MainPID",
    "ExecMainStartTimestamp",
    "ActiveEnterTimestamp",
    "InvocationID",
    "FragmentPath",
    "User",
    "Group",
    "UnitFileState",
    "NeedDaemonReload",
    "DropInPaths",
    "Type",
    "ExecStartPre",
    "ExecStart",
)


class SystemdAdapterError(Exception):
    """Error controlado al observar la unidad systemd."""


def _fail(message: str) -> None:
    raise SystemdAdapterError(message)


def _check_path_components(path: Path) -> None:
    if not path.is_absolute():
        _fail("La ruta de observación debe ser absoluta.")
    current = Path("/")
    for part in path.parts[1:]:
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            _fail("Falta un componente de la ruta administrada.")
        if stat.S_ISLNK(info.st_mode):
            _fail("Se detectó un componente simbólico en la ruta administrada.")


def _check_unit_file(path: Path) -> None:
    _check_path_components(path)
    try:
        info = path.lstat()
    except OSError:
        _fail("No se pudo consultar el archivo de unidad administrado.")
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_gid != 0
            or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o644):
        _fail("La unidad administrada tiene tipo, propietario, enlaces o permisos inseguros.")
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        _fail("No se pudo leer la unidad administrada.")
    required = (
        "[Unit]",
        "[Service]",
        "User=xray",
        "Group=xray",
        "ExecStartPre=/usr/local/bin/xray run -test -config /etc/xray/config.json",
        "ExecStart=/usr/local/bin/xray run -config /etc/xray/config.json",
        "NoNewPrivileges=true",
        "ProtectSystem=strict",
    )
    if any(line not in content.splitlines() for line in required):
        _fail("La unidad xray.service no coincide con el contrato administrado.")


def _read_config_hash(path: Path, *, expected_gid: int) -> str | None:
    try:
        _check_path_components(path.parent)
        entry = path.lstat()
    except FileNotFoundError:
        return None
    except OSError:
        _fail("No se pudo consultar la configuración runtime.")
    if stat.S_ISLNK(entry.st_mode):
        _fail("La configuración runtime no puede ser un enlace simbólico.")
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                     | getattr(os, "O_CLOEXEC", 0))
    except OSError:
        _fail("No se pudo abrir la configuración runtime para calcular su hash.")
    try:
        info = os.fstat(fd)
        if ((info.st_dev, info.st_ino) != (entry.st_dev, entry.st_ino)
                or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or info.st_uid != 0 or info.st_gid != expected_gid
                or stat.S_IMODE(info.st_mode) != 0o640
                or info.st_size < 1 or info.st_size > MAX_CONFIG_BYTES):
            _fail("La configuración runtime tiene tipo, propietario, enlaces, permisos o tamaño inseguros.")
        digest = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_CONFIG_BYTES:
                _fail("La configuración runtime excede el tamaño máximo.")
            digest.update(chunk)
        if total != info.st_size:
            _fail("La configuración runtime cambió durante la lectura.")
        return digest.hexdigest()
    finally:
        os.close(fd)


def _systemctl_show(systemctl_path: str = "/usr/bin/systemctl") -> dict:
    if not isinstance(systemctl_path, str) or not systemctl_path.startswith("/"):
        _fail("La ruta de systemctl debe ser absoluta.")
    command = [
        systemctl_path, "show", UNIT,
        "--property=" + ",".join(PROPERTIES),
        "--value",
    ]
    env = {
        "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "SYSTEMD_PAGER": "cat",
        "SYSTEMD_COLORS": "0",
    }
    try:
        completed = subprocess.run(
            command, stdin=subprocess.DEVNULL, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=TIMEOUT_SECONDS,
            check=False, env=env,
        )
    except (OSError, subprocess.TimeoutExpired):
        _fail("No se pudo consultar systemd dentro del tiempo permitido.")
    if completed.returncode != 0:
        _fail("systemd no pudo consultar xray.service.")
    values = completed.stdout.splitlines()
    if len(values) != len(PROPERTIES):
        _fail("systemd devolvió un conjunto incompleto de propiedades.")
    return dict(zip(PROPERTIES, values, strict=True))


def _validate_exec_property(value: str, *, pre_start: bool) -> None:
    if not isinstance(value, str) or not value.strip():
        _fail("systemd no devolvió el comando efectivo de ejecución de xray.service.")
    normalized = " ".join(value.split())
    if not re.search(r"(?:^|[;{]\s*)path=/usr/local/bin/xray(?:\s*;|$)", normalized):
        _fail("El ejecutable efectivo de xray.service no coincide con el binario administrado.")
    match = re.search(r"(?:^|[;{]\s*)argv\[\]=([^;]*)(?:;|$)", normalized)
    if match is None:
        _fail("systemd no devolvió argv efectivo para xray.service.")
    try:
        argv = shlex.split(match.group(1))
    except ValueError:
        _fail("systemd devolvió argv efectivo mal formado para xray.service.")
    expected = ["/usr/local/bin/xray", "run", "-config", "/etc/xray/config.json"]
    if pre_start:
        expected = ["/usr/local/bin/xray", "run", "-test", "-config", "/etc/xray/config.json"]
    if argv != expected:
        _fail("Los argumentos efectivos de xray.service no coinciden con el contrato administrado.")
    if "allow_failure=yes" in normalized or "ignore_errors=yes" in normalized:
        _fail("El comando efectivo de xray.service contiene una opción de fallo no permitida.")


def status(
    *,
    unit_file: Path = DEFAULT_UNIT_FILE,
    config_file: Path = DEFAULT_CONFIG_FILE,
    systemctl_path: str = "/usr/bin/systemctl",
) -> dict:
    """Observa xray.service; no realiza ninguna acción mutadora."""
    unit_file = Path(unit_file)
    config_file = Path(config_file)
    _check_unit_file(unit_file)
    observed = _systemctl_show(systemctl_path)

    if observed["FragmentPath"] != str(unit_file):
        _fail("systemd está usando una unidad distinta de la unidad administrada.")
    if observed["User"] != "xray" or observed["Group"] != "xray":
        _fail("La identidad efectiva de xray.service no coincide con xray:xray.")
    if observed["NeedDaemonReload"] != "no":
        _fail("systemd indica que la definición de xray.service necesita daemon-reload.")
    if observed["DropInPaths"].strip():
        _fail("xray.service tiene drop-ins adicionales no contemplados por el contrato administrado.")
    if observed["Type"] != "simple":
        _fail("El tipo efectivo de xray.service no coincide con Type=simple.")
    _validate_exec_property(observed["ExecStartPre"], pre_start=True)
    _validate_exec_property(observed["ExecStart"], pre_start=False)
    if observed["LoadState"] not in {"loaded", "not-found", "masked", "error", "bad-setting"}:
        _fail("systemd devolvió un LoadState no reconocido.")
    if observed["ActiveState"] not in {
        "active", "inactive", "failed", "activating", "deactivating",
        "reloading", "unknown",
    }:
        _fail("systemd devolvió un ActiveState no reconocido.")
    if observed["MainPID"] and not observed["MainPID"].isdigit():
        _fail("systemd devolvió un MainPID inválido.")
    invocation_id = observed["InvocationID"]
    if invocation_id and not re.fullmatch(r"[0-9a-fA-F]{32}", invocation_id):
        _fail("systemd devolvió un InvocationID inválido.")

    try:
        config_gid = grp.getgrnam("xray").gr_gid
    except KeyError:
        _fail("No existe el grupo xray requerido para validar config.json.")
    config_hash = _read_config_hash(config_file, expected_gid=config_gid)
    return {
        "unit": UNIT,
        "load_state": observed["LoadState"],
        "active_state": observed["ActiveState"],
        "sub_state": observed["SubState"],
        "result": observed["Result"],
        "exec_main_status": observed["ExecMainStatus"],
        "main_pid": int(observed["MainPID"]) if observed["MainPID"] else None,
        "exec_main_start_timestamp": observed["ExecMainStartTimestamp"],
        "active_enter_timestamp": observed["ActiveEnterTimestamp"],
        "invocation_id": invocation_id or None,
        "fragment_path": observed["FragmentPath"],
        "user": observed["User"],
        "group": observed["Group"],
        "unit_file_state": observed["UnitFileState"],
        "need_daemon_reload": observed["NeedDaemonReload"],
        "drop_in_paths": observed["DropInPaths"],
        "service_type": observed["Type"],
        "runtime_config_sha256": config_hash,
        # No se infiere la generación cargada a partir del estado/hash del archivo.
        "loaded_generation_id": None,
        "loaded_config_sha256": None,
        "generation_evidence": "not_attested",
        "read_only": True,
    }