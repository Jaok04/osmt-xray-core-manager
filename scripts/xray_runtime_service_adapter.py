#!/usr/bin/env python3
"""Adaptador de servicio simulado R-05; nunca invoca systemd ni procesos."""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import secrets
import stat
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

GENERATION_RE = re.compile(r"generation-[0-9a-f]{32}\Z")
SHA_RE = re.compile(r"[0-9a-f]{64}\Z")
MARKER = ".xray-manager-r05-service-fixture"
STATE_FILE = "service-state.json"
AUDIT_FILE = "adapter-audit.json"
LOCK_FILE = "adapter.lock"
MAX_BYTES = 1024 * 1024


class ServiceAdapterError(Exception):
    pass


def _fail(message: str) -> None:
    raise ServiceAdapterError(message)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json_bytes(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def _reject_symlinks(path: Path) -> None:
    if not path.is_absolute():
        _fail("La ruta del fixture R-05 debe ser absoluta.")
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode):
            _fail("El fixture R-05 contiene un componente symlink.")


def _check_root(root: Path) -> None:
    _reject_symlinks(root)
    try:
        info = root.lstat()
    except OSError:
        _fail("No existe el directorio fixture del adaptador R-05.")
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_gid != 0
            or stat.S_IMODE(info.st_mode) != 0o700):
        _fail("El directorio fixture R-05 debe ser root:root 0700.")
    marker = _read_regular(root / MARKER)
    if marker != {"schema_version": 1, "purpose": "xray-runtime-r05-service-fixture"}:
        _fail("Marcador del adaptador R-05 inválido.")


@contextmanager
def _fixture_lock(root: Path):
    """Serializa cada transacción fixture completa entre procesos.

    El lock vive dentro del directorio root-only del fixture y se mantiene
    durante lectura, CAS, escritura del estado y append de auditoría.
    """
    _check_root(root)
    lock_path = root / LOCK_FILE
    _reject_symlinks(lock_path)
    flags = os.O_RDWR | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(lock_path, flags)
    except OSError:
        _fail("No se pudo abrir el lock del adaptador R-05.")
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_gid != 0
                or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600
                or info.st_size < 1 or info.st_size > 4096):
            _fail("Lock del adaptador R-05 con tipo, propietario, permisos o tamaño inseguro.")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
        except OSError:
            _fail("No se pudo adquirir el lock exclusivo del adaptador R-05.")
        # Revalidar el directorio y el lock después de adquirirlo.
        _check_root(root)
        current = os.stat(lock_path, follow_symlinks=False)
        locked = os.fstat(fd)
        if (not stat.S_ISREG(current.st_mode) or current.st_dev != locked.st_dev
                or current.st_ino != locked.st_ino):
            _fail("El lock del adaptador R-05 cambió durante su adquisición.")
        lock_marker = _read_regular(lock_path)
        if lock_marker != {"schema_version": 1, "purpose": "xray-runtime-r05-adapter-lock"}:
            _fail("Marcador del lock del adaptador R-05 inválido.")
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def _read_regular(path: Path) -> dict:
    _reject_symlinks(path)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        _fail("No se pudo abrir un archivo fixture R-05.")
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_gid != 0
                or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600
                or info.st_size < 1 or info.st_size > MAX_BYTES):
            _fail("Archivo fixture R-05 con tipo, propietario, permisos o tamaño inseguro.")
        data = b""
        while len(data) <= MAX_BYTES:
            chunk = os.read(fd, min(65536, MAX_BYTES + 1 - len(data)))
            if not chunk:
                break
            data += chunk
        if len(data) != info.st_size or len(data) > MAX_BYTES:
            _fail("Archivo fixture R-05 cambió durante lectura.")
        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ValueError("duplicate")
                result[key] = value
            return result
        try:
            value = json.loads(data.decode("utf-8"), object_pairs_hook=pairs,
                               parse_constant=lambda _: (_ for _ in ()).throw(ValueError("constant")))
        except (UnicodeError, ValueError, json.JSONDecodeError):
            _fail("JSON fixture R-05 inválido.")
        if not isinstance(value, dict):
            _fail("El archivo fixture R-05 debe contener un objeto.")
        return value
    finally:
        os.close(fd)


def _atomic_write(path: Path, value: dict) -> None:
    data = _json_bytes(value)
    if len(data) > MAX_BYTES:
        _fail("El fixture R-05 excede el tamaño máximo.")
    _reject_symlinks(path)
    temp = path.parent / (".tmp-" + secrets.token_hex(16))
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        os.fchown(fd, 0, 0)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(temp, path)
    dir_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def create_fixture(root: Path, *, active_state: str, sub_state: str,
                   loaded_generation_id: str | None, loaded_config_sha256: str | None) -> None:
    if not root.is_absolute():
        _fail("La ruta del fixture R-05 debe ser absoluta.")
    _reject_symlinks(root)
    parent = root.parent.lstat()
    if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid != 0 or parent.st_gid != 0
            or stat.S_IMODE(parent.st_mode) & 0o022):
        _fail("El directorio padre del fixture R-05 debe ser root:root y no modificable por grupo/otros.")
    if root.exists():
        _fail("No se sobrescribe un fixture R-05 existente.")
    os.mkdir(root, 0o700)
    os.chown(root, 0, 0)
    os.chmod(root, 0o700)
    _atomic_write(root / MARKER, {"schema_version": 1, "purpose": "xray-runtime-r05-service-fixture"})
    _validate_state({
        "schema_version": 1, "unit": "xray.service", "load_state": "loaded",
        "active_state": active_state, "sub_state": sub_state,
        "loaded_generation_id": loaded_generation_id,
        "loaded_config_sha256": loaded_config_sha256,
    })
    _atomic_write(root / STATE_FILE, {
        "schema_version": 1, "unit": "xray.service", "load_state": "loaded",
        "active_state": active_state, "sub_state": sub_state,
        "loaded_generation_id": loaded_generation_id,
        "loaded_config_sha256": loaded_config_sha256,
    })
    _atomic_write(root / AUDIT_FILE, {"schema_version": 1, "events": []})
    _atomic_write(root / LOCK_FILE, {"schema_version": 1, "purpose": "xray-runtime-r05-adapter-lock"})


def _validate_state(value: dict) -> dict:
    fields = {"schema_version", "unit", "load_state", "active_state", "sub_state",
              "loaded_generation_id", "loaded_config_sha256"}
    if (set(value) != fields or value["schema_version"] != 1 or value["unit"] != "xray.service"
            or value["load_state"] != "loaded"
            or not isinstance(value["active_state"], str)
            or value["active_state"] not in {"active", "inactive", "failed", "unknown"}
            or not isinstance(value["sub_state"], str) or not value["sub_state"]):
        _fail("Estado simulado del servicio R-05 inválido.")
    if value["active_state"] == "active" and value["sub_state"] not in {"running", "listening"}:
        _fail("Subestado active incoherente en R-05.")
    if value["active_state"] == "inactive" and value["sub_state"] not in {"dead", "inactive"}:
        _fail("Subestado inactive incoherente en R-05.")
    if value["active_state"] == "failed" and value["sub_state"] != "failed":
        _fail("Subestado failed incoherente en R-05.")
    if value["active_state"] == "unknown" and value["sub_state"] != "unknown":
        _fail("Subestado unknown incoherente en R-05.")
    if value["loaded_generation_id"] is not None and (
            not isinstance(value["loaded_generation_id"], str)
            or not GENERATION_RE.fullmatch(value["loaded_generation_id"])):
        _fail("generation_id cargado inválido en R-05.")
    if value["loaded_config_sha256"] is not None and (
            not isinstance(value["loaded_config_sha256"], str)
            or not SHA_RE.fullmatch(value["loaded_config_sha256"])):
        _fail("Hash cargado inválido en R-05.")
    return value


def _load(root: Path) -> tuple[dict, dict]:
    _check_root(root)
    state = _validate_state(_read_regular(root / STATE_FILE))
    audit = _read_regular(root / AUDIT_FILE)
    if set(audit) != {"schema_version", "events"} or audit["schema_version"] != 1 or not isinstance(audit["events"], list):
        _fail("Bitácora del adaptador R-05 inválida.")
    return state, audit


def _record(root: Path, audit: dict, event: dict) -> None:
    events = audit["events"]
    events.append({"at": _now(), **event})
    if len(events) > 10000:
        _fail("La bitácora del adaptador R-05 alcanzó su límite.")
    _atomic_write(root / AUDIT_FILE, audit)


def status(root: Path, *, request_generation_id: str | None = None) -> dict:
    if request_generation_id is not None and (not isinstance(request_generation_id, str)
                                               or not GENERATION_RE.fullmatch(request_generation_id)):
        _fail("generation_id de consulta inválido.")
    with _fixture_lock(root):
        state, audit = _load(root)
        _record(root, audit, {"action": "status", "unit": "xray.service",
                              "request_generation_id": request_generation_id,
                              "observed_state": state["active_state"],
                              "observed_generation_id": state["loaded_generation_id"],
                              "observed_config_sha256": state["loaded_config_sha256"]})
        return dict(state)


def _validate_request(generation_id: str, config_sha256: str) -> None:
    if (not isinstance(generation_id, str) or not GENERATION_RE.fullmatch(generation_id)
            or not isinstance(config_sha256, str) or not SHA_RE.fullmatch(config_sha256)):
        _fail("Petición restart/restore R-05 con identidad o hash inválido.")


def restart(root: Path, *, generation_id: str, config_sha256: str,
            expected_generation_id: str | None, expected_config_sha256: str,
            outcome: str = "success") -> dict:
    with _fixture_lock(root):
        _validate_request(generation_id, config_sha256)
        allowed = {"success", "reject", "timeout_before", "timeout_after", "response_lost_after",
                   "exception_before", "wrong_generation", "wrong_hash", "failed_after",
                   "inactive_after", "unknown_after"}
        if not isinstance(outcome, str) or outcome not in allowed:
            _fail("Perfil de resultado simulado no permitido.")
        if expected_generation_id is not None and (not isinstance(expected_generation_id, str)
                                                    or not GENERATION_RE.fullmatch(expected_generation_id)):
            _fail("generation_id esperado previo inválido.")
        if not SHA_RE.fullmatch(expected_config_sha256):
            _fail("Hash esperado previo inválido.")
        state, audit = _load(root)
        event = {"action": "restart", "unit": "xray.service", "generation_id": generation_id,
                 "config_sha256": config_sha256, "expected_generation_id": expected_generation_id,
                 "expected_config_sha256": expected_config_sha256, "outcome": outcome}
        if (state["active_state"] != "active"
                or state["loaded_generation_id"] != expected_generation_id
                or state["loaded_config_sha256"] != expected_config_sha256):
            _record(root, audit, {**event, "result": "rejected_precondition"})
            return {"result": "rejected", "generation_id": generation_id,
                    "service_action_performed": False, "precondition_failed": True}
        if outcome not in {"reject", "timeout_before", "exception_before"}:
            if outcome == "wrong_generation":
                state["loaded_generation_id"] = "generation-" + ("0" * 32 if generation_id[-1] != "0" else "1" * 32)
                state["loaded_config_sha256"] = config_sha256
            elif outcome == "wrong_hash":
                state["loaded_generation_id"] = generation_id
                state["loaded_config_sha256"] = hashlib.sha256(b"wrong-config").hexdigest()
            else:
                state["loaded_generation_id"] = generation_id
                state["loaded_config_sha256"] = config_sha256
            state["active_state"] = "active"
            state["sub_state"] = "running"
            if outcome == "failed_after":
                state["active_state"], state["sub_state"] = "failed", "failed"
            elif outcome == "inactive_after":
                state["active_state"], state["sub_state"] = "inactive", "dead"
            elif outcome == "unknown_after":
                state["active_state"], state["sub_state"] = "unknown", "unknown"
            _atomic_write(root / STATE_FILE, state)
        result = {
            "success": "accepted", "reject": "rejected", "timeout_before": "timeout",
            "timeout_after": "timeout", "response_lost_after": "response_lost",
            "exception_before": "exception", "wrong_generation": "accepted",
            "wrong_hash": "accepted", "failed_after": "accepted",
            "inactive_after": "accepted", "unknown_after": "accepted",
        }[outcome]
        _record(root, audit, {**event, "result": result})
        return {"result": result, "generation_id": generation_id, "service_action_performed": True}


def start(root: Path, *, generation_id: str, config_sha256: str,
          expected_generation_id: str | None, expected_config_sha256: str | None,
          outcome: str = "success") -> dict:
    """Simula start explícito desde inactive con CAS; nunca invoca systemd."""
    with _fixture_lock(root):
        _validate_request(generation_id, config_sha256)
        allowed = {"success", "reject", "timeout_before", "timeout_after",
                   "response_lost_after", "exception_before", "wrong_generation",
                   "wrong_hash", "failed_after"}
        if not isinstance(outcome, str) or outcome not in allowed:
            _fail("Perfil de resultado start simulado no permitido.")
        if expected_generation_id is not None and (
                not isinstance(expected_generation_id, str)
                or not GENERATION_RE.fullmatch(expected_generation_id)):
            _fail("generation_id esperado previo inválido para start.")
        if expected_config_sha256 is not None and (
                not isinstance(expected_config_sha256, str)
                or not SHA_RE.fullmatch(expected_config_sha256)):
            _fail("Hash esperado previo inválido para start.")
        state, audit = _load(root)
        event = {"action": "start", "unit": "xray.service", "generation_id": generation_id,
                 "config_sha256": config_sha256, "expected_generation_id": expected_generation_id,
                 "expected_config_sha256": expected_config_sha256, "outcome": outcome}
        if (state["active_state"] != "inactive"
                or state["loaded_generation_id"] != expected_generation_id
                or state["loaded_config_sha256"] != expected_config_sha256):
            _record(root, audit, {**event, "result": "rejected_precondition"})
            return {"result": "rejected", "generation_id": generation_id,
                    "service_action_performed": False, "precondition_failed": True}
        if outcome not in {"reject", "timeout_before", "exception_before"}:
            if outcome == "wrong_generation":
                state["loaded_generation_id"] = "generation-" + ("0" * 32 if generation_id[-1] != "0" else "1" * 32)
                state["loaded_config_sha256"] = config_sha256
            elif outcome == "wrong_hash":
                state["loaded_generation_id"] = generation_id
                state["loaded_config_sha256"] = hashlib.sha256(b"wrong-config").hexdigest()
            else:
                state["loaded_generation_id"] = generation_id
                state["loaded_config_sha256"] = config_sha256
            state["active_state"], state["sub_state"] = "active", "running"
            if outcome == "failed_after":
                state["active_state"], state["sub_state"] = "failed", "failed"
            _atomic_write(root / STATE_FILE, state)
        result = {
            "success": "accepted", "reject": "rejected", "timeout_before": "timeout",
            "timeout_after": "timeout", "response_lost_after": "response_lost",
            "exception_before": "exception", "wrong_generation": "accepted",
            "wrong_hash": "accepted", "failed_after": "accepted",
        }[outcome]
        _record(root, audit, {**event, "result": result})
        return {"result": result, "generation_id": generation_id,
                "service_action_performed": outcome not in {"reject", "timeout_before", "exception_before"}}


def restore(root: Path, *, generation_id: str, expected_current_generation_id: str,
            previous_state: str, previous_generation_id: str | None,
            previous_config_sha256: str | None, outcome: str = "success") -> dict:
    with _fixture_lock(root):
        if not isinstance(generation_id, str) or not GENERATION_RE.fullmatch(generation_id):
            _fail("generation_id de restauración inválido.")
        if (not isinstance(expected_current_generation_id, str)
                or not GENERATION_RE.fullmatch(expected_current_generation_id)):
            _fail("generation_id actual esperado inválido para restore.")
        if not isinstance(previous_state, str) or previous_state not in {"active", "inactive"}:
            _fail("R-05 no restaura automáticamente estados failed/unknown.")
        if previous_generation_id is not None and (not isinstance(previous_generation_id, str)
                                                   or not GENERATION_RE.fullmatch(previous_generation_id)):
            _fail("generation_id previo inválido.")
        if previous_config_sha256 is not None and (not isinstance(previous_config_sha256, str)
                                                   or not SHA_RE.fullmatch(previous_config_sha256)):
            _fail("Hash previo inválido.")
        if previous_state == "active" and previous_config_sha256 is None:
            _fail("No se puede verificar la restauración active sin hash previo.")
        if not isinstance(outcome, str) or outcome not in {"success", "fail"}:
            _fail("Resultado de restauración simulado no permitido.")
        state, audit = _load(root)
        event = {"action": "restore", "unit": "xray.service", "generation_id": generation_id,
                 "expected_current_generation_id": expected_current_generation_id,
                 "previous_state": previous_state, "previous_generation_id": previous_generation_id,
                 "previous_config_sha256": previous_config_sha256, "outcome": outcome}
        if state["loaded_generation_id"] != expected_current_generation_id:
            _record(root, audit, {**event, "result": "rejected_precondition"})
            return {"result": "failed", "generation_id": generation_id, "service_action_performed": False}
        if outcome == "success":
            state["active_state"] = previous_state
            state["sub_state"] = "running" if previous_state == "active" else "dead"
            state["loaded_generation_id"] = previous_generation_id
            state["loaded_config_sha256"] = previous_config_sha256
            _atomic_write(root / STATE_FILE, state)
        _record(root, audit, {**event, "result": "restored" if outcome == "success" else "failed"})
        return {"result": "restored" if outcome == "success" else "failed",
                "generation_id": generation_id, "service_action_performed": outcome == "success"}


def audit_events(root: Path) -> list[dict]:
    with _fixture_lock(root):
        _state, audit = _load(root)
        return list(audit["events"])
