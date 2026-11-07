#!/usr/bin/env python3
"""Puente R-05 para delegar mutaciones en el único controlador xray_service.sh.

No ejecuta systemctl directamente. El descriptor lifecycle lock se hereda
explícitamente por Bash; el módulo Bash comprueba ruta, inode y permisos antes
de delegar en xray_service_action_locked().
"""
from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

DEFAULT_SERVICE_MODULE = Path(os.path.abspath(__file__)).parents[1] / "modules" / "xray_service.sh"
ALLOWED_ACTIONS = frozenset({"start", "restart", "stop"})
TIMEOUT_SECONDS = 40


class ServiceControlError(Exception):
    """Error controlado al delegar una operación al controlador de servicio."""


def _fail(message: str) -> None:
    raise ServiceControlError(message)


def _reject_symlink_components(path: Path) -> None:
    if not path.is_absolute():
        _fail("La ruta debe ser absoluta.")
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            _fail("Falta un componente de la ruta.")
        except OSError:
            _fail("No se pudo inspeccionar un componente de la ruta.")
        if stat.S_ISLNK(info.st_mode):
            _fail("La ruta contiene un componente simbólico.")


def _validate_lock_descriptor(fd: int, lock_path: Path) -> None:
    if isinstance(fd, bool) or not isinstance(fd, int) or fd < 0:
        _fail("El descriptor lifecycle lock no es válido.")
    _reject_symlink_components(lock_path)
    try:
        opened = os.fstat(fd)
        current = os.stat(lock_path, follow_symlinks=False)
    except OSError:
        _fail("No se pudo verificar el descriptor lifecycle lock.")
    if ((opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino)
            or not stat.S_ISREG(opened.st_mode) or opened.st_uid != 0
            or opened.st_gid != 0 or opened.st_nlink != 1
            or stat.S_IMODE(opened.st_mode) != 0o600):
        _fail("El descriptor no corresponde al archivo lifecycle lock root:root 0600.")
    # No llamar flock(LOCK_EX) aquí: sobre el mismo open-file-description
    # sería idempotente si ya está bloqueado, pero adquiriría el lock si no lo
    # estuviera. fdinfo acredita que ESTE descriptor porta el FLOCK exclusivo
    # y que el PID propietario es el proceso R-05 que realiza la delegación.
    try:
        fdinfo = Path(f"/proc/self/fdinfo/{fd}").read_text(encoding="ascii")
    except OSError:
        _fail("No se pudo inspeccionar fdinfo del lifecycle lock; se bloquea la acción.")
    expected_device = f"{os.major(opened.st_dev):02x}:{os.minor(opened.st_dev):02x}"
    matching = []
    for line in fdinfo.splitlines():
        if not line.startswith("lock:"):
            continue
        fields = line.split()
        if len(fields) == 9 and fields[1].endswith(":") and fields[1][:-1].isdigit():
            # fdinfo: lock: ID: FLOCK ADVISORY WRITE PID MAJOR:MINOR:INODE 0 EOF
            if (fields[2] == "FLOCK" and fields[3] == "ADVISORY"
                    and fields[4] == "WRITE" and fields[7] == "0"
                    and fields[8] == "EOF"):
                matching.append(fields)
    if not any(
        fields[5] == str(os.getpid())
        and fields[6] == f"{expected_device}:{opened.st_ino}"
        for fields in matching
    ):
        _fail("El descriptor no demuestra un FLOCK exclusivo propiedad del proceso R-05.")


def run_action(
    action: str,
    *,
    lifecycle_lock_fd: int,
    lifecycle_lock_path: Path,
    service_module: Path = DEFAULT_SERVICE_MODULE,
    timeout: int = TIMEOUT_SECONDS,
) -> dict:
    """Ejecuta start/restart/stop a través del controlador Bash único.

    El caller conserva abierto el descriptor durante toda la operación. Esta
    función no publica configuración ni decide si start/restart está permitido;
    esas precondiciones pertenecen al orquestador R-05.
    """
    if not isinstance(action, str) or action not in ALLOWED_ACTIONS:
        _fail("Acción de servicio no permitida para el puente R-05.")
    if type(timeout) is not int or not 1 <= timeout <= 120:
        _fail("Timeout del puente de servicio fuera de rango.")
    if os.geteuid() != 0:
        _fail("El puente de servicio requiere root.")
    lock_path = Path(lifecycle_lock_path)
    module_path = Path(service_module)
    _validate_lock_descriptor(lifecycle_lock_fd, lock_path)
    _reject_symlink_components(module_path)
    try:
        module_info = module_path.lstat()
    except OSError:
        _fail("No se pudo consultar modules/xray_service.sh.")
    if (not stat.S_ISREG(module_info.st_mode) or module_info.st_uid != 0
            or module_info.st_mode & (stat.S_IWGRP | stat.S_IWOTH)):
        _fail("El controlador xray_service.sh no es un archivo regular protegido de modificaciones por grupo/otros.")

    env = {
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "XRAY_MANAGER_LIFECYCLE_LOCK": str(lock_path),
        "XRAY_MANAGER_LIFECYCLE_LOCK_FD": str(lifecycle_lock_fd),
        "XRAY_MANAGER_LIFECYCLE_LOCK_OWNER_PID": str(os.getpid()),
        "XRAY_SERVICE_MODULE": str(module_path),
    }
    command = [
        "/bin/bash", "-c",
        'set -Eeuo pipefail; source "$XRAY_SERVICE_MODULE"; '
        'xray_service_action_inherited_lock "$1"',
        "xray-manager-r05", action,
    ]
    try:
        completed = subprocess.run(
            command, stdin=subprocess.DEVNULL, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout, check=False,
            env=env, pass_fds=(lifecycle_lock_fd,), close_fds=True,
        )
    except subprocess.TimeoutExpired:
        _fail("La acción delegada excedió el timeout; el estado debe observarse antes de reintentar.")
    except OSError:
        _fail("No se pudo invocar el controlador Bash de Xray.")
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        _fail("El controlador xray_service.sh rechazó o no confirmó la acción."
              + ((" Detalle: " + detail[:400]) if detail else ""))
    return {
        "action": action,
        "result": "accepted",
        "returncode": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-1000:],
        "service_action_performed": True,
        "controller": "modules/xray_service.sh",
        "lock_handoff": "inherited_descriptor_verified",
    }
