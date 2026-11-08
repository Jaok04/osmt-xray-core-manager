#!/usr/bin/env python3
"""Launcher B4-MIN fixture: valida y ejecuta Xray sobre el mismo memfd sellado.

Este módulo es laboratorio únicamente. Exige un root fixture marcado y no
contiene rutas live, integración systemd, backend, R-05 ni menú.
"""
from __future__ import annotations

import argparse
import fcntl
import grp
import hashlib
import os
import pathlib
import pwd
import re
import stat
import subprocess
import sys
from typing import Any

import xray_runtime_config_attestation as attestation


class MemfdLauncherError(Exception):
    """Fallo controlado del launcher/verificador fixture."""


def _fail(message: str) -> None:
    raise MemfdLauncherError(message)


def _fixture_root(path: pathlib.Path) -> pathlib.Path:
    root = pathlib.Path(path)
    if not root.is_absolute():
        _fail("La raíz fixture debe ser absoluta.")
    current = pathlib.Path("/")
    for part in root.parts[1:]:
        current = current / part
        try:
            info = current.lstat()
        except OSError as exc:
            raise MemfdLauncherError("No se pudo inspeccionar la raíz fixture.") from exc
        if stat.S_ISLNK(info.st_mode):
            _fail("La ruta fixture contiene un symlink.")
    info = root.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != 0
            or stat.S_IMODE(info.st_mode) != 0o711):
        _fail("La raíz fixture debe ser root-owned y modo 0711.")
    marker = root / ".xray-manager-fixture"
    marker_info = marker.lstat()
    if (not stat.S_ISREG(marker_info.st_mode) or marker_info.st_uid != 0
            or marker_info.st_gid != 0 or marker_info.st_nlink != 1
            or stat.S_IMODE(marker_info.st_mode) != 0o600):
        _fail("El marcador fixture no es seguro.")
    return root


def _validate_fixture_ancestors(path: pathlib.Path, root: pathlib.Path) -> pathlib.Path:
    candidate = pathlib.Path(os.path.abspath(path))
    try:
        relative = candidate.relative_to(root)
    except ValueError:
        _fail("La ruta está fuera de la raíz fixture.")
    current = root
    for component in relative.parts[:-1]:
        current = current / component
        try:
            info = current.lstat()
        except OSError as exc:
            raise MemfdLauncherError("No se pudo inspeccionar un directorio fixture.") from exc
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_gid != 0
                or info.st_mode & (stat.S_IWGRP | stat.S_IWOTH)):
            _fail("Un directorio antecesor fixture es simbólico o modificable por terceros.")
    return candidate


def _root_owned_readonly_file(path: pathlib.Path, *, label: str) -> os.stat_result:
    path = pathlib.Path(path)
    try:
        info = path.lstat()
    except OSError as exc:
        raise MemfdLauncherError(f"No se pudo inspeccionar {label}.") from exc
    if (not path.is_absolute() or not stat.S_ISREG(info.st_mode)
            or info.st_uid != 0 or info.st_gid != 0 or info.st_nlink != 1
            or info.st_mode & (stat.S_IWGRP | stat.S_IWOTH)):
        _fail(f"{label} no es archivo regular root:root no modificable por grupo/otros.")
    return info


def _validate_link(link: pathlib.Path, fixture_root: pathlib.Path) -> None:
    link = pathlib.Path(link)
    if not link.is_absolute() or link.suffix != ".json":
        _fail("La ruta Xray debe ser absoluta y terminar en .json.")
    link = _validate_fixture_ancestors(link, fixture_root)
    try:
        info = link.lstat()
        parent = link.parent.lstat()
    except OSError as exc:
        raise MemfdLauncherError("No se pudo inspeccionar el enlace JSON fixture.") from exc
    if (not stat.S_ISLNK(info.st_mode) or info.st_uid != 0 or info.st_gid != 0
            or parent.st_uid != 0 or not stat.S_ISDIR(parent.st_mode)
            or parent.st_mode & (stat.S_IWGRP | stat.S_IWOTH)):
        _fail("El enlace JSON o su directorio no están protegidos contra sustitución.")
    try:
        target = os.readlink(link)
    except OSError as exc:
        raise MemfdLauncherError("No se pudo leer el enlace JSON fixture.") from exc
    if target != "/proc/self/fd/3":
        _fail("El enlace JSON debe apuntar exactamente a /proc/self/fd/3.")


def _read_config(path: pathlib.Path, expected_sha256: str, expected_size: int) -> bytes:
    before = _root_owned_readonly_file(path, label="La configuración fuente")
    if (type(expected_size) is not int or not 1 <= expected_size <= attestation.MAX_CONFIG_BYTES
            or before.st_size != expected_size
            or not isinstance(expected_sha256, str)
            or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256)):
        _fail("Tamaño o SHA-256 esperado inválido.")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise MemfdLauncherError("No se pudo abrir la configuración fuente sin seguir symlinks.") from exc
    try:
        opened = os.fstat(fd)
        if (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns) != (
                before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns):
            _fail("La configuración cambió entre lstat y open.")
        chunks = []
        remaining = expected_size
        while remaining:
            chunk = os.read(fd, min(1024 * 1024, remaining))
            if not chunk:
                _fail("La configuración fuente tuvo lectura incompleta.")
            chunks.append(chunk)
            remaining -= len(chunk)
        after = os.fstat(fd)
        if (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            _fail("La configuración fuente cambió durante su lectura.")
        data = b"".join(chunks)
    finally:
        os.close(fd)
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        _fail("El SHA-256 real de la configuración no coincide.")
    return data


def _validate_binary(path: pathlib.Path) -> pathlib.Path:
    info = _root_owned_readonly_file(path, label="El binario Xray")
    if not info.st_mode & stat.S_IXUSR or not os.access(path, os.X_OK):
        _fail("El binario Xray no es ejecutable.")
    return pathlib.Path(path)


def launch_fixture(
    *, fixture_root: pathlib.Path, config_path: pathlib.Path, config_link: pathlib.Path,
    xray_binary: pathlib.Path, expected_sha256: str, expected_size: int,
    test_timeout: float = 20.0,
) -> dict[str, Any]:
    """Valida con Xray y hace exec usando exactamente el mismo descriptor.

    Debe ejecutarse ya como identidad no privilegiada del servicio. El retorno
    normal no ocurre: un test correcto termina en os.execv(Xray).
    """
    root = _fixture_root(pathlib.Path(fixture_root))
    _validate_link(pathlib.Path(config_link), root)
    binary = _validate_binary(pathlib.Path(xray_binary))
    if (isinstance(test_timeout, bool) or not isinstance(test_timeout, (int, float))
            or not 0.1 <= test_timeout <= 120):
        _fail("Timeout de validación fuera del intervalo permitido.")
    source = _validate_fixture_ancestors(pathlib.Path(config_path), root)
    data = _read_config(source, expected_sha256, expected_size)
    try:
        account = pwd.getpwuid(os.geteuid())
        group = grp.getgrgid(os.getegid())
    except KeyError as exc:
        raise MemfdLauncherError("No se pudo resolver la identidad efectiva del launcher.") from exc
    if os.geteuid() == 0 or os.getegid() == 0:
        _fail("El launcher fixture debe ejecutarse sin privilegios root.")

    fd = -1
    try:
        fd, metadata = attestation.create_sealed_memfd(
            data, expected_sha256, owner_uid=os.geteuid(), owner_gid=os.getegid(), mode=0o400,
        )
        if fd != 3:
            os.dup2(fd, 3, inheritable=True)
            os.close(fd)
            fd = 3
        else:
            os.set_inheritable(fd, True)
        info = os.fstat(3)
        if (info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode)) != (
                os.geteuid(), os.getegid(), 0o400):
            _fail("FD 3 no conserva propietario, grupo y modo esperados.")
        seals = fcntl.fcntl(3, fcntl.F_GET_SEALS)
        if seals & attestation.REQUIRED_SEALS != attestation.REQUIRED_SEALS:
            _fail("FD 3 no conserva todos los seals requeridos.")
        readback = os.pread(3, expected_size + 1, 0)
        if len(readback) != expected_size or hashlib.sha256(readback).hexdigest() != expected_sha256:
            _fail("FD 3 no contiene exactamente la configuración esperada.")

        test_argv = [str(binary), "run", "-test", "-config", str(config_link)]
        try:
            checked = subprocess.run(
                test_argv, pass_fds=(3,), stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=float(test_timeout), check=False,
                close_fds=True,
            )
        except subprocess.TimeoutExpired as exc:
            raise MemfdLauncherError("Xray run -test excedió el timeout.") from exc
        if checked.returncode != 0 or "Configuration OK" not in checked.stdout:
            _fail("Xray rechazó la configuración sellada: " + checked.stdout[-1500:])
        os.lseek(3, 0, os.SEEK_SET)
        final_readback = os.pread(3, expected_size + 1, 0)
        if final_readback != data or fcntl.fcntl(3, fcntl.F_GET_SEALS) & attestation.REQUIRED_SEALS != attestation.REQUIRED_SEALS:
            _fail("El descriptor cambió después de la validación Xray.")
        # FD 3 se conserva deliberadamente a través de exec; no heredar otros FDs.
        os.set_inheritable(3, True)
        argv = [str(binary), "run", "-config", str(config_link)]
        os.execv(str(binary), argv)
    except MemfdLauncherError:
        raise
    except (OSError, attestation.ConfigAttestationError) as exc:
        raise MemfdLauncherError("No se pudo preparar el descriptor sellado.") from exc
    finally:
        # exec no ejecuta finally; los caminos de error sí cierran FD 3.
        if fd >= 0:
            try:
                os.close(fd)
            except OSError:
                pass


def _proc_starttime(pid: int) -> int:
    try:
        raw = pathlib.Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
        right = raw.rindex(")")
        fields = raw[right + 1:].strip().split()
        observed_pid = int(raw[:raw.index("(")].strip())
        starttime = int(fields[19])
    except (OSError, UnicodeError, ValueError, IndexError) as exc:
        raise MemfdLauncherError("No se pudo leer PID/starttime del proceso.") from exc
    if observed_pid != pid or starttime < 0:
        _fail("PID/starttime procfs no coincide.")
    return starttime


def verify_live_descriptor(
    *, fixture_root: pathlib.Path, pid: int, expected_uid: int, expected_gid: int,
    expected_sha256: str, expected_size: int, xray_binary: pathlib.Path,
    config_link: pathlib.Path,
) -> dict[str, Any]:
    """Verifica desde root el FD sellado vivo; no infiere el estado interno del parser."""
    if os.geteuid() != 0:
        _fail("La inspección del descriptor de otro usuario requiere root.")
    if type(pid) is not int or pid <= 1 or type(expected_uid) is not int or type(expected_gid) is not int:
        _fail("PID/UID/GID esperados inválidos.")
    root = _fixture_root(pathlib.Path(fixture_root))
    binary = _validate_binary(pathlib.Path(xray_binary))
    link = pathlib.Path(config_link)
    _validate_link(link, root)
    proc = pathlib.Path("/proc") / str(pid)
    start_before = _proc_starttime(pid)
    try:
        status_lines = (proc / "status").read_text(encoding="ascii").splitlines()
        uid_line = next(line for line in status_lines if line.startswith("Uid:"))
        gid_line = next(line for line in status_lines if line.startswith("Gid:"))
        uids = [int(x) for x in uid_line.split()[1:]]
        gids = [int(x) for x in gid_line.split()[1:]]
        argv = tuple(x.decode("utf-8") for x in (proc / "cmdline").read_bytes().rstrip(b"\0").split(b"\0"))
        executable = os.readlink(proc / "exe")
    except (OSError, ValueError, StopIteration, UnicodeError) as exc:
        raise MemfdLauncherError("No se pudo inspeccionar identidad/argv del proceso.") from exc
    expected_argv = (str(binary), "run", "-config", str(link))
    if (len(uids) != 4 or len(gids) != 4 or uids[1] != expected_uid or gids[1] != expected_gid
            or executable != str(binary) or argv != expected_argv):
        _fail("El proceso no coincide con UID/GID, ejecutable o argv esperados.")
    descriptor_path = proc / "fd/3"
    try:
        descriptor_link = os.readlink(descriptor_path)
        fd = os.open(descriptor_path, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0))
    except OSError as exc:
        raise MemfdLauncherError("El proceso no conserva el FD 3 inspeccionable.") from exc
    try:
        info = os.fstat(fd)
        seals = fcntl.fcntl(fd, fcntl.F_GET_SEALS)
        if (not descriptor_link.startswith("/memfd:xray-manager-config")
                or info.st_uid != expected_uid or info.st_gid != expected_gid
                or stat.S_IMODE(info.st_mode) != 0o400
                or info.st_size != expected_size
                or seals & attestation.REQUIRED_SEALS != attestation.REQUIRED_SEALS):
            _fail("FD 3 no conserva nombre, owner, modo, tamaño o seals esperados.")
        digest = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > expected_size:
                _fail("El descriptor vivo excede el tamaño esperado.")
            digest.update(chunk)
        if total != expected_size or digest.hexdigest() != expected_sha256:
            _fail("El hash/tamaño del descriptor vivo no coincide.")
    finally:
        os.close(fd)
    start_after = _proc_starttime(pid)
    if start_before != start_after:
        _fail("El PID cambió durante la inspección (posible reutilización).")
    return {
        "verified": True,
        "environment": "fixture",
        "pid": pid,
        "process_starttime_ticks": start_after,
        "effective_uid": expected_uid,
        "effective_gid": expected_gid,
        "argv": expected_argv,
        "executable": str(binary),
        "fd": 3,
        "fd_target": descriptor_link,
        "config_sha256": expected_sha256,
        "config_size_bytes": expected_size,
        "seals": seals,
        "descriptor_process_bound": True,
        "configuration_loaded": False,
        "configuration_evidence": "sealed_memfd_process_bound",
    }


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-root", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--config-link", required=True)
    parser.add_argument("--xray", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--size", required=True, type=int)
    parser.add_argument("--test-timeout", type=float, default=20.0)
    args = parser.parse_args()
    try:
        launch_fixture(
            fixture_root=pathlib.Path(args.fixture_root),
            config_path=pathlib.Path(args.config),
            config_link=pathlib.Path(args.config_link),
            xray_binary=pathlib.Path(args.xray),
            expected_sha256=args.sha256,
            expected_size=args.size,
            test_timeout=args.test_timeout,
        )
    except MemfdLauncherError as exc:
        print(f"launcher fixture rechazado: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
