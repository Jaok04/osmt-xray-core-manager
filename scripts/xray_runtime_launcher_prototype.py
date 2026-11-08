#!/usr/bin/env python3
"""Prototipo B4.1 aislado del contrato de privilegios del lanzador.

No es un launcher de producción: exige una raíz fixture marcada, no conoce
rutas live y sólo prepara memfd/symlink/evidencia para pruebas controladas.
"""
from __future__ import annotations

import hashlib
import grp
import os
import pathlib
import pwd
import signal
import stat
import subprocess
import tempfile
import time
from typing import Any

import xray_runtime_config_attestation as attestation


class LauncherPrototypeError(Exception):
    """Fallo controlado del prototipo fixture B4.1."""


def _fixture_root(root: pathlib.Path) -> pathlib.Path:
    root = pathlib.Path(root)
    if not root.is_absolute():
        raise LauncherPrototypeError("La raíz fixture debe ser absoluta.")
    try:
        attestation._check_fixture_root(root)
        info = root.lstat()
        marker = (root / ".xray-manager-fixture").lstat()
    except (OSError, attestation.ConfigAttestationError) as exc:
        raise LauncherPrototypeError("La raíz fixture o su marcador no es válido.") from exc
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
            or stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(marker.st_mode)
            or marker.st_uid != os.geteuid() or marker.st_nlink != 1
            or stat.S_IMODE(marker.st_mode) != 0o600):
        raise LauncherPrototypeError("La raíz fixture no satisface el contrato de propiedad/tipo.")
    return root


def _validate_service_identity(plan: dict[str, Any]) -> None:
    uid, gid = plan.get("service_uid"), plan.get("service_gid")
    user, group_name = plan.get("service_user"), plan.get("service_group")
    if (type(uid) is not int or type(gid) is not int or uid <= 0 or gid <= 0
            or not isinstance(user, str) or not user or not isinstance(group_name, str)
            or not group_name):
        raise LauncherPrototypeError("La identidad de servicio del plan no es válida.")
    try:
        account = pwd.getpwnam(user)
        group = grp.getgrnam(group_name)
    except KeyError as exc:
        raise LauncherPrototypeError("La identidad de servicio ya no existe.") from exc
    if (account.pw_uid == 0 or group.gr_gid == 0 or account.pw_uid != uid
            or group.gr_gid != gid or account.pw_gid != gid):
        raise LauncherPrototypeError("La identidad del plan fue alterada o no coincide con NSS.")


def _validate_executable(path: pathlib.Path, label: str) -> pathlib.Path:
    path = pathlib.Path(path)
    try:
        info = path.lstat()
    except OSError as exc:
        raise LauncherPrototypeError(f"Binario {label} no disponible.") from exc
    if (not path.is_absolute() or not stat.S_ISREG(info.st_mode)
            or stat.S_ISLNK(info.st_mode) or info.st_uid != 0
            or info.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            or not os.access(path, os.X_OK)):
        raise LauncherPrototypeError(f"Binario {label} no cumple el contrato de propiedad/permisos.")
    return path


def _validate_descriptor(plan: dict[str, Any]) -> int:
    fd = plan.get("fd")
    if type(fd) is not int or fd < 0:
        raise LauncherPrototypeError("Descriptor fixture inválido.")
    try:
        if not os.get_inheritable(fd):
            raise LauncherPrototypeError("El descriptor no es heredable.")
        seals = attestation.fcntl.fcntl(fd, attestation.fcntl.F_GET_SEALS)
        size = os.fstat(fd).st_size
        expected_size = plan.get("expected_size")
        expected_hash = plan.get("expected_sha256")
        metadata = plan.get("fd_metadata")
        if (seals & attestation.REQUIRED_SEALS != attestation.REQUIRED_SEALS
                or type(expected_size) is not int or not 1 <= expected_size <= attestation.MAX_CONFIG_BYTES
                or size != expected_size or not isinstance(expected_hash, str)
                or len(expected_hash) != 64 or not isinstance(metadata, dict)
                or metadata.get("sha256") != expected_hash
                or metadata.get("size_bytes") != expected_size
                or type(metadata.get("seals")) is not int
                or metadata["seals"] & attestation.REQUIRED_SEALS != attestation.REQUIRED_SEALS
                or metadata.get("inheritable") is not True):
            raise LauncherPrototypeError("El descriptor o sus metadatos no conservan las garantías.")
        digest = hashlib.sha256()
        offset = 0
        while offset < size:
            chunk = os.pread(fd, min(1024 * 1024, size - offset), offset)
            if not chunk:
                raise LauncherPrototypeError("Lectura incompleta del descriptor sellado.")
            digest.update(chunk)
            offset += len(chunk)
        if digest.hexdigest() != expected_hash:
            raise LauncherPrototypeError("El contenido del descriptor no coincide con SHA-256 esperado.")
        return seals
    except OSError as exc:
        raise LauncherPrototypeError("No se pudo verificar el descriptor fixture.") from exc


def prepare_fixture_launch(
    *, fixture_root: pathlib.Path, config: bytes, expected_sha256: str,
    invocation_id: str, service_user: str = "nobody", service_group: str = "nogroup",
) -> dict[str, Any]:
    """Prepara un descriptor sellado, symlink .json y evidencia fixture root-only."""
    root = _fixture_root(pathlib.Path(fixture_root))
    if not isinstance(invocation_id, str) or not attestation.INVOCATION_RE.fullmatch(invocation_id):
        raise LauncherPrototypeError("InvocationID fixture inválido.")
    try:
        account = pwd.getpwnam(service_user)
        group = grp.getgrnam(service_group)
    except KeyError as exc:
        raise LauncherPrototypeError("La identidad de prueba no existe.") from exc
    if account.pw_uid == 0 or group.gr_gid == 0 or account.pw_gid != group.gr_gid:
        raise LauncherPrototypeError("La identidad de servicio de prueba no puede ser root y debe tener grupo primario coincidente.")
    digest = hashlib.sha256(config).hexdigest()
    if digest != expected_sha256:
        raise LauncherPrototypeError("El hash esperado no coincide con los bytes de configuración.")

    fd, metadata = attestation.create_sealed_memfd(config, expected_sha256)
    workspace = root / ("launch-" + invocation_id.lower())
    try:
        workspace.mkdir(mode=0o711)
        os.chmod(workspace, 0o711)
        config_link = workspace / "config.json"
        os.symlink(f"/proc/self/fd/{fd}", config_link)
        return {
            "environment": "fixture",
            "fd": fd,
            "fd_metadata": metadata,
            "workspace": workspace,
            "config_link": config_link,
            "evidence_path": None,
            "expected_sha256": digest,
            "expected_size": len(config),
            "service_uid": account.pw_uid,
            "service_gid": group.gr_gid,
            "service_user": service_user,
            "service_group": service_group,
            "invocation_id": invocation_id.lower(),
            "launcher_pid": os.getpid(),
        }
    except Exception:
        os.close(fd)
        raise


def _terminate_child(child: int) -> None:
    try:
        os.killpg(child, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except OSError:
        try:
            os.kill(child, signal.SIGKILL)
        except ProcessLookupError:
            pass
    while True:
        try:
            os.waitpid(child, 0)
            return
        except InterruptedError:
            continue
        except ChildProcessError:
            return


def run_fixture_xray_validation(
    plan: dict[str, Any], *, xray_binary: pathlib.Path,
    setpriv_binary: pathlib.Path = pathlib.Path("/usr/bin/setpriv"),
    timeout_seconds: float = 30.0,
) -> subprocess.CompletedProcess[str]:
    """Ejecuta Xray -test con evidencia previa a exec y timeout estricto."""
    if not isinstance(plan, dict) or plan.get("environment") != "fixture":
        raise LauncherPrototypeError("Sólo se admiten planes fixture.")
    if (isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float))
            or not 0.1 <= timeout_seconds <= 300):
        raise LauncherPrototypeError("Timeout fuera del intervalo permitido (0.1–300 s).")
    _validate_service_identity(plan)
    binary = _validate_executable(xray_binary, "Xray")
    setpriv = _validate_executable(setpriv_binary, "setpriv")
    fd = plan.get("fd")
    _validate_descriptor(plan)
    try:
        link = pathlib.Path(plan["config_link"])
        workspace = pathlib.Path(plan["workspace"])
        root = _fixture_root(workspace.parent)
        if (not link.is_absolute() or link.parent != workspace or not link.is_symlink()
                or os.readlink(link) != f"/proc/self/fd/{fd}"
                or workspace.parent != root or not workspace.is_dir()
                or not isinstance(plan.get("invocation_id"), str)
                or not attestation.INVOCATION_RE.fullmatch(plan["invocation_id"])):
            raise LauncherPrototypeError("El plan fixture fue alterado o no conserva sus garantías.")
    except (OSError, KeyError, TypeError) as exc:
        raise LauncherPrototypeError("No se pudo verificar el plan fixture.") from exc

    argv = [
        str(setpriv), f"--reuid={plan['service_uid']}",
        f"--regid={plan['service_gid']}", "--clear-groups", "--no-new-privs",
        "--bounding-set=-all,+net_bind_service",
        "--inh-caps=+net_bind_service", "--ambient-caps=+net_bind_service",
        "--", str(binary), "run", "-test", "-config", str(link),
    ]
    gate_read, gate_write = os.pipe()
    child = None
    with tempfile.TemporaryFile() as output:
        try:
            child = os.fork()
            if child == 0:
                try:
                    os.close(gate_write)
                    os.setpgid(0, 0)
                    os.dup2(output.fileno(), 1)
                    os.dup2(output.fileno(), 2)
                    os.close(output.fileno())
                    token = os.read(gate_read, 1)
                    os.close(gate_read)
                    if token != b"1":
                        os._exit(125)
                    os.execv(argv[0], argv)
                except BaseException:
                    os._exit(126)
            os.close(gate_read)
            gate_read = -1
            try:
                os.setpgid(child, child)
            except OSError:
                pass
            plan["target_pid"] = child
            evidence = attestation.write_invocation_evidence(
                fixture_root=pathlib.Path(plan["workspace"]).parent,
                evidence_dir=pathlib.Path(plan["workspace"]).parent / "evidence",
                fd_metadata=plan["fd_metadata"], pid=child,
                invocation_id=plan["invocation_id"],
            )
            plan["evidence_path"] = evidence
            if os.write(gate_write, b"1") != 1:
                raise LauncherPrototypeError("No se pudo liberar el hijo después de escribir evidencia.")
            os.close(gate_write)
            gate_write = -1
            deadline = time.monotonic() + float(timeout_seconds)
            status = None
            while time.monotonic() < deadline:
                try:
                    waited, candidate = os.waitpid(child, os.WNOHANG)
                except InterruptedError:
                    continue
                if waited == child:
                    status = candidate
                    break
                time.sleep(min(0.02, max(0, deadline - time.monotonic())))
            if status is None:
                _terminate_child(child)
                child = None
                output.seek(0)
                captured = output.read().decode("utf-8", errors="replace")
                return subprocess.CompletedProcess(argv, 124, captured, "timeout: Xray fixture validation exceeded limit")
            child = None
            output.seek(0)
            captured = output.read().decode("utf-8", errors="replace")
        except Exception:
            if child is not None:
                _terminate_child(child)
                child = None
            raise
        finally:
            if gate_read >= 0:
                os.close(gate_read)
            if gate_write >= 0:
                os.close(gate_write)
    if os.WIFEXITED(status):
        return subprocess.CompletedProcess(argv, os.WEXITSTATUS(status), captured, "")
    if os.WIFSIGNALED(status):
        return subprocess.CompletedProcess(argv, 128 + os.WTERMSIG(status), captured, "")
    return subprocess.CompletedProcess(argv, 125, captured, "child did not exit normally")


def close_fixture_plan(plan: dict[str, Any]) -> None:
    """Cierra el descriptor fixture; no elimina evidencia para facilitar auditoría."""
    fd = plan.get("fd")
    if isinstance(fd, int):
        try:
            os.close(fd)
        except OSError:
            pass
        plan["fd"] = None
