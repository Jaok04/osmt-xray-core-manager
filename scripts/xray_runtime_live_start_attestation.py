#!/usr/bin/env python3
"""Evidencia correlativa de arranque live; no afirma bytes cargados en memoria.

Correlaciona publicación, timestamps systemd, MainPID/InvocationID, identidad
xray:xray y hash estable del archivo. El resultado es deliberadamente
launch_correlated_only: Xray no expone una atestación criptográfica del
contenido ya cargado, por lo que configuration_loaded permanece False.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any


class StartAttestationError(Exception):
    """La invocación no puede correlacionarse con la publicación."""


def _fail(message: str) -> None:
    raise StartAttestationError(message)


def _parse_systemd_time(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip() or value in {"n/a", "0"}:
        _fail(f"systemd no proporcionó {field} válido.")
    normalized = re.sub(r" ([+-][0-9]{2})$", r" \g<1>00", value)
    try:
        parsed = datetime.strptime(normalized, "%a %Y-%m-%d %H:%M:%S %z")
    except ValueError as exc:
        raise StartAttestationError(f"Formato inválido en {field}.") from exc
    return parsed


def _parse_publication_time(value: Any) -> datetime:
    if not isinstance(value, str):
        _fail("La publicación no contiene timestamp verificable.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise StartAttestationError("Timestamp de publicación inválido.") from exc
    if parsed.tzinfo is None:
        _fail("El timestamp de publicación debe incluir zona horaria.")
    return parsed


def attest_start(*, publication: dict[str, Any], systemd: dict[str, Any],
                 process: dict[str, Any], config_sha256_before: str,
                 config_sha256_after: str) -> dict[str, Any]:
    """Verifica correlación temporal y de identidad, no el contenido en memoria."""
    if not isinstance(publication, dict) or publication.get("status") != "published":
        _fail("No existe publicación confirmada para correlacionar.")
    operation_id = publication.get("operation_id")
    if not isinstance(operation_id, str) or not re.fullmatch(r"runtime-op-[0-9a-f]{32}", operation_id):
        _fail("operation_id de publicación inválido.")
    expected_hash = publication.get("config_sha256")
    if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
        _fail("Hash de publicación inválido.")
    if config_sha256_before != expected_hash or config_sha256_after != expected_hash:
        _fail("El archivo runtime no conserva el hash publicado a través de la observación.")
    if not isinstance(systemd, dict) or systemd.get("read_only") is not True:
        _fail("Snapshot systemd inválido o no read-only.")
    if (systemd.get("unit") != "xray.service" or systemd.get("load_state") != "loaded"
            or systemd.get("active_state") != "active" or systemd.get("sub_state") != "running"
            or systemd.get("result") != "success" or systemd.get("exec_main_status") not in {"0", 0}
            or systemd.get("user") != "xray" or systemd.get("group") != "xray"):
        _fail("xray.service no está activo bajo la identidad administrada esperada.")
    pid = systemd.get("main_pid")
    invocation = systemd.get("invocation_id")
    if type(pid) is not int or pid <= 1 or not isinstance(invocation, str) or not re.fullmatch(r"[0-9a-fA-F]{32}", invocation):
        _fail("MainPID/InvocationID no son válidos.")
    published_at = _parse_publication_time(publication.get("published_at"))
    exec_started = _parse_systemd_time(systemd.get("exec_main_start_timestamp"), "ExecMainStartTimestamp")
    active_entered = _parse_systemd_time(systemd.get("active_enter_timestamp"), "ActiveEnterTimestamp")
    if exec_started < published_at or active_entered < published_at or active_entered < exec_started:
        _fail("La invocación activa no es posterior a la publicación confirmada.")
    if not isinstance(process, dict) or process.get("read_only") is not True or process.get("identity_verified") is not True:
        _fail("No existe atestación read-only válida de identidad del proceso.")
    if (process.get("pid") != pid or process.get("systemd_main_pid") != pid
            or process.get("systemd_invocation_id") != invocation
            or type(process.get("effective_uid")) is not int or process["effective_uid"] < 1
            or type(process.get("effective_gid")) is not int or process["effective_gid"] < 1
            or type(process.get("process_starttime_ticks")) is not int or process["process_starttime_ticks"] < 0
            or tuple(process.get("argv", ())) != ("/usr/local/bin/xray", "run", "-config", "/etc/xray/config.json")
            or process.get("configuration_loaded") is not False
            or process.get("configuration_evidence") != "not_attested"):
        _fail("La identidad del proceso no corresponde a la invocación systemd observada.")
    if process.get("executable_path") != "/usr/local/bin/xray":
        _fail("El proceso observado no ejecuta el binario Xray administrado.")
    executable_hash = process.get("executable_sha256")
    if not isinstance(executable_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", executable_hash):
        _fail("No existe hash válido del ejecutable observado.")
    return {
        "verified": True,
        "evidence_level": "launch_correlated_file_unchanged",
        "operation_id": operation_id,
        "published_config_sha256": expected_hash,
        "runtime_config_sha256_before": config_sha256_before,
        "runtime_config_sha256_after": config_sha256_after,
        "main_pid": pid,
        "invocation_id": invocation,
        "exec_main_start_timestamp": systemd["exec_main_start_timestamp"],
        "active_enter_timestamp": systemd["active_enter_timestamp"],
        "process_starttime_ticks": process.get("process_starttime_ticks"),
        "executable_sha256": executable_hash,
        "configuration_loaded": False,
        "configuration_evidence": "launch_correlated_only",
        "read_only": True,
    }
