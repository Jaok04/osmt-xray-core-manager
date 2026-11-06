#!/usr/bin/env python3
"""Correlación read-only entre xray.service y la identidad de su MainPID."""
from __future__ import annotations

import grp
import pwd
import re
from pathlib import Path
from typing import Callable

import xray_runtime_process_identity as process_identity
import xray_runtime_systemd_adapter as systemd_adapter

EXPECTED_ARGV = (
    "/usr/local/bin/xray", "run", "-config", "/etc/xray/config.json"
)
INVOCATION_RE = re.compile(r"[0-9a-fA-F]{32}\Z")


class ProcessAttestationError(Exception):
    """La identidad del proceso no pudo correlacionarse con systemd."""


def _fail(message: str) -> None:
    raise ProcessAttestationError(message)


def _validate_systemd_snapshot(snapshot: dict) -> None:
    if not isinstance(snapshot, dict) or snapshot.get("read_only") is not True:
        _fail("La observación systemd no es un snapshot read-only válido.")
    if (snapshot.get("active_state") != "active"
            or snapshot.get("sub_state") != "running"
            or snapshot.get("result") != "success"
            or snapshot.get("exec_main_status") != "0"
            or snapshot.get("user") != "xray"
            or snapshot.get("group") != "xray"):
        _fail("xray.service no está en un estado activo verificable.")
    pid = snapshot.get("main_pid")
    if type(pid) is not int or pid <= 1:
        _fail("systemd no proporcionó un MainPID válido.")
    invocation = snapshot.get("invocation_id")
    if not isinstance(invocation, str) or not INVOCATION_RE.fullmatch(invocation):
        _fail("systemd no proporcionó un InvocationID válido.")
    timestamp = snapshot.get("active_enter_timestamp")
    if not isinstance(timestamp, str) or not timestamp.strip() or timestamp in {"n/a", "0"}:
        _fail("systemd no proporcionó ActiveEnterTimestamp válido.")
    if not isinstance(snapshot.get("fragment_path"), str) or not snapshot["fragment_path"].startswith("/"):
        _fail("systemd no proporcionó la ruta de unidad esperada.")


def observe_process_identity(
    *,
    systemd_observer: Callable[[], dict] | None = None,
    process_observer: Callable[..., dict] | None = None,
    proc_root: Path = Path("/proc"),
) -> dict:
    """Correlaciona dos snapshots systemd estables con la identidad de MainPID.

    Los observadores alternativos son puntos de inyección para pruebas. En
    producción se usan H6-A, /proc y las cuentas xray del sistema.
    """
    observe = systemd_adapter.status if systemd_observer is None else systemd_observer
    inspect = process_identity.inspect_process if process_observer is None else process_observer

    before = observe()
    _validate_systemd_snapshot(before)
    try:
        expected_uid = pwd.getpwnam("xray").pw_uid
        expected_gid = grp.getgrnam("xray").gr_gid
    except KeyError:
        _fail("No existe la identidad de sistema xray:xray.")

    process = inspect(
        before["main_pid"],
        expected_uid=expected_uid,
        expected_gid=expected_gid,
        expected_argv=EXPECTED_ARGV,
        expected_executable=process_identity.EXPECTED_EXECUTABLE,
        proc_root=Path(proc_root),
    )
    if (not isinstance(process, dict) or process.get("identity_verified") is not True
            or process.get("read_only") is not True
            or process.get("configuration_loaded") is not False
            or process.get("configuration_evidence") != "not_attested"):
        _fail("El inspector no devolvió evidencia de identidad válida y limitada.")

    after = observe()
    _validate_systemd_snapshot(after)
    stable_fields = (
        "main_pid", "invocation_id", "active_enter_timestamp", "fragment_path",
    )
    if any(before.get(field) != after.get(field) for field in stable_fields):
        _fail("La identidad de la invocación systemd cambió durante la inspección.")
    if process.get("pid") != after["main_pid"]:
        _fail("El PID inspeccionado no coincide con MainPID de systemd.")
    if process.get("executable_path") != process_identity.EXPECTED_EXECUTABLE:
        _fail("El proceso no está ejecutando el binario Xray administrado.")
    if tuple(process.get("argv", ())) != EXPECTED_ARGV:
        _fail("El argv del proceso no coincide con el contrato administrado.")
    if (process.get("effective_uid") != expected_uid
            or process.get("effective_gid") != expected_gid):
        _fail("UID/GID devueltos por el inspector no coinciden con xray:xray.")
    starttime = process.get("process_starttime_ticks")
    if type(starttime) is not int or starttime < 0:
        _fail("El inspector no proporcionó starttime válido.")
    executable_hash = process.get("executable_sha256")
    if not isinstance(executable_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", executable_hash):
        _fail("El inspector no proporcionó SHA-256 válido del ejecutable.")

    return {
        "pid": process["pid"],
        "process_starttime_ticks": starttime,
        "executable_path": process.get("executable_path"),
        "executable_sha256": executable_hash,
        "argv": tuple(process.get("argv", ())),
        "effective_uid": process.get("effective_uid"),
        "effective_gid": process.get("effective_gid"),
        "identity_verified": True,
        "systemd_main_pid": after["main_pid"],
        "systemd_invocation_id": after["invocation_id"],
        "systemd_active_enter_timestamp": after["active_enter_timestamp"],
        "systemd_fragment_path": after["fragment_path"],
        "configuration_loaded": False,
        "configuration_evidence": "not_attested",
        "read_only": True,
    }
