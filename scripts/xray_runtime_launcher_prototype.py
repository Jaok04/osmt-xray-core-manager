#!/usr/bin/env python3
"""Prototipo B4.1 aislado del contrato de privilegios del lanzador.

No es un launcher de producción: exige una raíz fixture marcada, no conoce
rutas live y sólo prepara memfd/symlink/evidencia para pruebas controladas.
"""
from __future__ import annotations

import hashlib
import os
import pathlib
import pwd
import grp
import stat
import subprocess
import tempfile
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
    if account.pw_uid == 0 or group.gr_gid == 0:
        raise LauncherPrototypeError("La identidad de servicio de prueba no puede ser root.")
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


def run_fixture_xray_validation(
    plan: dict[str, Any], *, xray_binary: pathlib.Path,
    setpriv_binary: pathlib.Path = pathlib.Path("/usr/bin/setpriv"),
) -> subprocess.CompletedProcess[str]:
    """Ejecuta Xray -test con evidencia escrita para el PID que hará exec.

    Un hijo fork queda bloqueado en una tubería; el padre escribe primero la
    evidencia root/owner-only para el PID del hijo y sólo entonces lo libera
    para exec(setpriv -> Xray). PID se conserva en toda la cadena exec.
    """
    if plan.get("environment") != "fixture" or not isinstance(plan.get("fd"), int):
        raise LauncherPrototypeError("Sólo se admiten planes fixture.")
    binary = pathlib.Path(xray_binary)
    setpriv = pathlib.Path(setpriv_binary)
    if not binary.is_absolute() or not binary.is_file() or not os.access(binary, os.X_OK):
        raise LauncherPrototypeError("Binario Xray de prueba no válido.")
    if not setpriv.is_absolute() or not setpriv.is_file() or not os.access(setpriv, os.X_OK):
        raise LauncherPrototypeError("setpriv no está disponible.")
    fd = plan["fd"]
    if not os.get_inheritable(fd):
        raise LauncherPrototypeError("El descriptor no es heredable.")
    try:
        seals = attestation.fcntl.fcntl(fd, attestation.fcntl.F_GET_SEALS)
        link = pathlib.Path(plan["config_link"])
        workspace = pathlib.Path(plan["workspace"])
        root = _fixture_root(workspace.parent)
        if (seals & attestation.REQUIRED_SEALS != attestation.REQUIRED_SEALS
                or link.parent != workspace or not link.is_symlink()
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
        "--", str(binary), "run", "-test", "-config", str(plan["config_link"]),
    ]
    gate_read, gate_write = os.pipe()
    with tempfile.TemporaryFile() as output:
        child = os.fork()
        if child == 0:
            try:
                os.close(gate_write)
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
        plan["target_pid"] = child
        try:
            evidence = attestation.write_invocation_evidence(
                fixture_root=pathlib.Path(plan["workspace"]).parent,
                evidence_dir=pathlib.Path(plan["workspace"]).parent / "evidence",
                fd_metadata=plan["fd_metadata"], pid=child,
                invocation_id=plan["invocation_id"],
            )
            plan["evidence_path"] = evidence
            os.write(gate_write, b"1")
        except Exception:
            os.close(gate_write)
            os.waitpid(child, 0)
            raise
        os.close(gate_write)
        _, status = os.waitpid(child, 0)
        output.seek(0)
        captured = output.read().decode("utf-8", errors="replace")
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
