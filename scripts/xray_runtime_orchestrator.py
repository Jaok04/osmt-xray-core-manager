#!/usr/bin/env python3
"""Orquestación R-05 de publicación runtime con adaptador de servicio simulado."""
from __future__ import annotations

import os
import secrets
from contextvars import ContextVar
from functools import wraps
from argparse import Namespace
from pathlib import Path

import xray_runtime_journal as journal
import xray_runtime_active_profile as active_profile_store_module
import xray_runtime_preflight as preflight
import xray_runtime_publisher as publisher
import xray_runtime_service_adapter as service_adapter
import xray_runtime_attestation as runtime_attestation
import xray_runtime_staging as staging

GENERATION_PREFIX = "generation-"
_SERVICE_BACKEND = ContextVar("xray_runtime_service_backend", default=service_adapter)


def _service_backend():
    return _SERVICE_BACKEND.get()


def _with_service_backend(function):
    """Inyección interna de backend; solo se admiten dobles de prueba explícitos."""
    @wraps(function)
    def wrapped(*args, service_backend=None, **kwargs):
        backend = service_adapter if service_backend is None else service_backend
        if backend is not service_adapter and getattr(backend, "RUNTIME_BACKEND_TEST_ONLY", False) is not True:
            _fail("Backend externo no habilitado: H6-C solo admite el adaptador fixture o dobles de prueba.")
        required = ("status", "start", "restart", "restore", "ServiceAdapterError")
        if any(not hasattr(backend, name) for name in required):
            _fail("El backend inyectado no cumple el contrato R-05.")
        token = _SERVICE_BACKEND.set(backend)
        try:
            return function(*args, **kwargs)
        finally:
            _SERVICE_BACKEND.reset(token)
    return wrapped


def _attestation_snapshot(stage: str, record: dict):
    backend = _service_backend()
    provider = getattr(backend, "attestation_snapshot", None)
    if not callable(provider):
        return None
    if getattr(backend, "RUNTIME_BACKEND_TEST_ONLY", False) is not True:
        _fail("La captura de atestación H6-C solo está disponible en dobles de prueba.")
    return provider(stage, record)


def _persist_test_attestation(record: dict, before: dict | None):
    if before is None:
        return None
    backend = _service_backend()
    store = getattr(backend, "attestation_store", None)
    unit_file = getattr(backend, "attestation_unit_file", None)
    if not isinstance(store, runtime_attestation.AttestationStore) or unit_file is None:
        _fail("El backend de prueba no configuró almacén y unidad para H6-B.")
    after = _attestation_snapshot("after", record)
    confirmed = _attestation_snapshot("confirmed", record)
    result = store.record(record, before, after, confirmed, Path(unit_file))
    return {"status": result["status"], "attestation": result["attestation"]}


def _recovery_attestation(record: dict):
    backend = _service_backend()
    store = getattr(backend, "attestation_store", None)
    if store is None:
        return None
    if not isinstance(store, runtime_attestation.AttestationStore):
        raise runtime_attestation.AttestationError("Almacén H6-B inyectado no válido.")
    evidence = store.read(record["operation_id"])
    if evidence is None:
        raise runtime_attestation.AttestationError(
            "La transición se recuperó sin atestación H6-B persistida; no se marca como completada."
        )
    if (evidence["generation_id"] != record["orchestration"]["generation_id"]
            or evidence["config_sha256"] != record["publication"]["config_sha256"]):
        raise runtime_attestation.AttestationError(
            "La atestación H6-B no corresponde a la generación/hash del journal."
        )
    return {"status": "ATTESTED_RECOVERED", "attestation": evidence}




class RuntimeOrchestrationError(Exception):
    pass


def _fail(message: str) -> None:
    raise RuntimeOrchestrationError(message)


def _operation_dir(operation_store: Path, operation_id: str) -> Path:
    if not journal.OP_RE.fullmatch(operation_id):
        _fail("operation_id inválido.")
    operations = operation_store / "operations"
    journal.check_operation_store(operation_store)
    journal.check_dir(operations, 0o700, 0, 0)
    path = operations / operation_id
    journal.check_dir(path, 0o700, 0, 0)
    return path


def _load(operation_store: Path, operation_id: str) -> tuple[Path, dict]:
    path = _operation_dir(operation_store, operation_id)
    return path, journal.read_journal(path)


def _save(path: Path, record: dict) -> None:
    journal.write_journal(path, record)
    journal.fsync_dir(path)


def _service_action_performed(record: dict) -> bool:
    request = record["orchestration"]["request"]
    service_action_attempted = request["action"] in {"start", "restart"} and request["result"] not in {
        "not_requested", "requested", "rejected", "exception",
    }
    return service_action_attempted or record["orchestration"]["rollback"]["service_status"] == "restored"


def _mark_recovery_required(path: Path, record: dict, reason: str) -> dict:
    record["state"] = "recovery_required"
    record["recovery"]["attempts"] += 1
    record["recovery"]["last_action"] = "r05_fail_closed"
    record["recovery"]["last_error"] = reason[:240]
    record["orchestration"]["phase"] = "recovery_required"
    record["orchestration"]["rollback"]["last_error"] = reason[:240]
    _save(path, record)
    return {
        "status": "RECOVERY_REQUIRED", "operation_id": record["operation_id"],
        "generation_id": record["orchestration"]["generation_id"],
        "reason": reason, "runtime_published": record["publication"]["status"] == "published",
        "service_action_performed": _service_action_performed(record),
    }


def _record_observation(record: dict, observed: dict, status: str) -> None:
    evidence = record["orchestration"]["verification"]
    evidence["status"] = status
    evidence["observed_state"] = observed["active_state"]
    evidence["observed_generation_id"] = observed["loaded_generation_id"]
    evidence["observed_config_sha256"] = observed["loaded_config_sha256"]
    evidence["verified_at"] = journal.now()


def _matches(observed: dict, *, state: str, generation_id: str | None,
             config_sha256: str | None) -> bool:
    return (observed["active_state"] == state
            and observed["loaded_generation_id"] == generation_id
            and observed["loaded_config_sha256"] == config_sha256)


def _commit_active_profile(active_profile_store: Path | None, adapter_root: Path,
                           operation_id: str, record: dict) -> dict | None:
    """Registra el perfil solo con servicio fixture active y generación/hash exactos."""
    if active_profile_store is None:
        return None
    generation_id = record["orchestration"]["generation_id"]
    config_hash = record["publication"]["config_sha256"]
    observed = _service_backend().status(adapter_root, request_generation_id=generation_id)
    if not _matches(observed, state="active", generation_id=generation_id,
                    config_sha256=config_hash):
        raise active_profile_store_module.ActiveProfileError(
            "El servicio fixture ya no coincide con la generación publicada; no se actualiza el perfil activo."
        )
    value = {
        "schema_version": 1,
        "profile_id": record["source"]["profile_id"],
        "revision": record["source"]["revision"],
        "validation_id": record["source"]["validation_id"],
        "generation_id": generation_id,
        "config_sha256": config_hash,
        "operation_id": operation_id,
        "applied_at": journal.now(),
        "service_unit": "xray.service",
        "service_state": "active",
        "config_target": "etc/xray/config.json",
    }
    return active_profile_store_module.ActiveProfileStore(active_profile_store).set_active(value)


def _restore_after_failure(
    operation_store: Path, operation_id: str, lifecycle_lock: Path,
    application_lock: Path, adapter_root: Path, restore_outcome: str = "success",
    crash_at: str | None = None,
) -> dict:
    fds = publisher._acquire(operation_store, lifecycle_lock, application_lock)
    try:
        operation_dir, record = _load(operation_store, operation_id)
        if record["state"] == "rolled_back":
            return {"status": "ALREADY_ROLLED_BACK", "operation_id": operation_id}
        if record["state"] not in {"config_published", "service_restart_requested", "service_start_requested",
                                   "service_verified", "rollback_started", "rollback_config_restored",
                                   "rollback_failed"}:
            return _mark_recovery_required(operation_dir, record, "Estado no recuperable por rollback R-05.")
        if record["state"] not in {"rollback_started", "rollback_config_restored", "rollback_failed"}:
            record["state"] = "rollback_started"
            record["rollback"]["status"] = "started"
            record["rollback"]["started_at"] = journal.now()
            record["rollback"]["last_error"] = None
            record["orchestration"]["phase"] = "rollback_started"
            record["orchestration"]["rollback"]["config_status"] = "not_started"
            _save(operation_dir, record)

        if record["state"] != "rollback_config_restored":
            result = publisher._rollback_locked(
                operation_dir, record, timeout=20, crash_at=None
            )
            record = journal.read_journal(operation_dir)
            if result.get("status") not in {"ROLLBACK_CONFIG_RESTORED", "ALREADY_RESTORED"}:
                record["orchestration"]["rollback"]["config_status"] = "failed"
                record["orchestration"]["rollback"]["service_status"] = "not_started"
                record["orchestration"]["rollback"]["last_error"] = result.get("reason", result.get("status", "rollback_config_failed"))
                record["state"] = "recovery_required"
                record["orchestration"]["phase"] = "recovery_required"
                record["recovery"]["attempts"] += 1
                record["recovery"]["last_action"] = "r05_config_rollback_failed"
                record["recovery"]["last_error"] = record["orchestration"]["rollback"]["last_error"][:240]
                _save(operation_dir, record)
                return {"status": "RECOVERY_REQUIRED", "operation_id": operation_id,
                        "generation_id": record["orchestration"]["generation_id"],
                        "config_rollback": "failed", "service_restore": "not_attempted"}
            record["orchestration"]["rollback"]["config_status"] = "restored"
            record["orchestration"]["rollback"]["last_error"] = None
            _save(operation_dir, record)
            if crash_at == "after_rollback_config":
                raise journal.SimulatedCrash("after_rollback_config")
        else:
            record["orchestration"]["rollback"]["config_status"] = "restored"

        initial = record["orchestration"]["initial_service"]
        initial_state = initial["active_state"]
        if initial_state in {"failed", "unknown"}:
            record["orchestration"]["rollback"]["service_status"] = "failed"
            return _mark_recovery_required(operation_dir, record, "No se restaura automáticamente un estado previo failed/unknown.")
        try:
            observed = _service_backend().status(
                adapter_root, request_generation_id=record["orchestration"]["generation_id"]
            )
        except _service_backend().ServiceAdapterError as exc:
            record["orchestration"]["rollback"]["service_status"] = "failed"
            return _mark_recovery_required(
                operation_dir, record,
                f"La configuración se restauró, pero no se pudo consultar el servicio fixture: {exc}",
            )
        if initial_state == "inactive":
            if observed["active_state"] == "inactive":
                record["orchestration"]["rollback"]["service_status"] = "unchanged"
            else:
                record["orchestration"]["rollback"]["service_status"] = "failed"
                return _mark_recovery_required(operation_dir, record, "El servicio previo inactive cambió inesperadamente; no se emite start.")
        else:
            old_generation = initial["loaded_generation_id"]
            old_hash = initial["loaded_config_sha256"]
            if _matches(observed, state="active", generation_id=old_generation, config_sha256=old_hash):
                record["orchestration"]["rollback"]["service_status"] = "unchanged"
            elif record["orchestration"]["request"]["action"] == "none":
                record["orchestration"]["rollback"]["service_status"] = "failed"
                record["orchestration"]["rollback"]["last_error"] = "El servicio cambió sin una petición R-05; no se sobrescribe el estado externo."
                return _mark_recovery_required(operation_dir, record, "El servicio cambió externamente; se restauró el archivo, pero no se modifica el estado externo.")
            elif observed["loaded_generation_id"] != record["orchestration"]["generation_id"]:
                record["orchestration"]["rollback"]["service_status"] = "failed"
                record["orchestration"]["rollback"]["last_error"] = "La generación cargada no pertenece a esta operación; no se sobrescribe el estado externo."
                return _mark_recovery_required(operation_dir, record, "El servicio informa una generación distinta; se restauró el archivo, pero se conserva el estado externo para intervención.")
            else:
                try:
                    result = _service_backend().restore(
                        adapter_root,
                        generation_id=record["orchestration"]["generation_id"],
                        expected_current_generation_id=record["orchestration"]["generation_id"],
                        previous_state="active",
                        previous_generation_id=old_generation,
                        previous_config_sha256=old_hash,
                        outcome=restore_outcome,
                    )
                    observed = _service_backend().status(
                        adapter_root, request_generation_id=record["orchestration"]["generation_id"]
                    )
                except _service_backend().ServiceAdapterError:
                    result, observed = {"result": "failed"}, None
                if (observed is None or result["result"] != "restored"
                        or not _matches(observed, state="active", generation_id=old_generation,
                                        config_sha256=old_hash)):
                    record["orchestration"]["rollback"]["service_status"] = "failed"
                    record["orchestration"]["rollback"]["last_error"] = "No se verificó la restauración del servicio previo."
                    return _mark_recovery_required(operation_dir, record, "La configuración se restauró, pero el servicio previo no pudo verificarse.")
                record["orchestration"]["rollback"]["service_status"] = "restored"
                if crash_at == "after_service_restore":
                    raise journal.SimulatedCrash("after_service_restore")

        record["state"] = "rolled_back"
        record["rollback"]["status"] = "rolled_back"
        record["rollback"]["completed_at"] = journal.now()
        record["rollback"]["restored_config_sha256"] = record["snapshot"]["previous_config_sha256"]
        record["rollback"]["validation"] = "PASS"
        record["rollback"]["last_error"] = None
        record["orchestration"]["phase"] = "rolled_back"
        record["orchestration"]["rollback"]["last_error"] = None
        record["recovery"]["last_action"] = "r05_rollback_and_service_reconciled"
        record["recovery"]["last_error"] = None
        _save(operation_dir, record)
        return {
            "status": "ROLLED_BACK", "operation_id": operation_id,
            "generation_id": record["orchestration"]["generation_id"],
            "config_rollback": "restored",
            "service_restore": record["orchestration"]["rollback"]["service_status"],
            "runtime_published": True,
            "service_action_performed": _service_action_performed(record),
        }
    finally:
        journal.release_locks(fds)


def _execute_restart(
    operation_store: Path, operation_id: str, lifecycle_lock: Path,
    application_lock: Path, adapter_root: Path, restart_outcome: str,
    restore_outcome: str, crash_at: str | None = None,
    active_profile_store: Path | None = None,
) -> dict:
    fds = publisher._acquire(operation_store, lifecycle_lock, application_lock)
    verified = False
    try:
        operation_dir, record = _load(operation_store, operation_id)
        if record["state"] != "config_published":
            _fail("La operación debe estar publicada antes de solicitar restart.")
        gen = record["orchestration"]["generation_id"]
        config_hash = record["publication"]["config_sha256"]
        initial = record["orchestration"]["initial_service"]
        try:
            before = _service_backend().status(adapter_root, request_generation_id=gen)
            unchanged = _matches(
                before, state=initial["active_state"],
                generation_id=initial["loaded_generation_id"],
                config_sha256=initial["loaded_config_sha256"],
            )
        except _service_backend().ServiceAdapterError:
            before, unchanged = None, False
        if not unchanged:
            if before is not None:
                _record_observation(record, before, "fail")
            else:
                record["orchestration"]["verification"]["status"] = "fail"
                record["orchestration"]["verification"]["verified_at"] = journal.now()
            _save(operation_dir, record)
        else:
            attestation_before = _attestation_snapshot("before", record)
            record["orchestration"]["request"] = {
                "generation_id": gen, "action": "restart",
                "requested_at": journal.now(), "result": "requested",
            }
            record["orchestration"]["phase"] = "restart_requested"
            record["state"] = "service_restart_requested"
            _save(operation_dir, record)
            if crash_at == "after_restart_request":
                raise journal.SimulatedCrash("after_restart_request")
            try:
                result = _service_backend().restart(
                    adapter_root, generation_id=gen, config_sha256=config_hash,
                    expected_generation_id=initial["loaded_generation_id"],
                    expected_config_sha256=initial["loaded_config_sha256"],
                    outcome=restart_outcome,
                )
                record["orchestration"]["request"]["result"] = result["result"]
            except _service_backend().ServiceAdapterError:
                record["orchestration"]["request"]["result"] = "exception"
            _save(operation_dir, record)
            if crash_at == "after_restart_transition":
                raise journal.SimulatedCrash("after_restart_transition")
            try:
                observed = _service_backend().status(adapter_root, request_generation_id=gen)
                verified = _matches(observed, state="active", generation_id=gen, config_sha256=config_hash)
                _record_observation(record, observed, "pass" if verified else "fail")
            except _service_backend().ServiceAdapterError:
                record["orchestration"]["verification"]["status"] = "fail"
                record["orchestration"]["verification"]["verified_at"] = journal.now()
                verified = False
            _save(operation_dir, record)
            attestation_result = None
            if verified and attestation_before is not None:
                try:
                    attestation_result = _persist_test_attestation(record, attestation_before)
                except Exception:
                    record["orchestration"]["verification"]["status"] = "fail"
                    verified = False
                    _save(operation_dir, record)
            if verified:
                record["state"] = "service_verified"
                record["orchestration"]["phase"] = "service_verified"
                _save(operation_dir, record)
                if crash_at == "after_service_verified":
                    raise journal.SimulatedCrash("after_service_verified")
                record["state"] = "completed"
                record["orchestration"]["phase"] = "completed"
                _save(operation_dir, record)
                active_result = None
                active_error = None
                if active_profile_store is not None:
                    try:
                        active_result = _commit_active_profile(
                            active_profile_store, adapter_root, operation_id, record
                        )
                    except (active_profile_store_module.ActiveProfileError,
                            _service_backend().ServiceAdapterError, OSError) as exc:
                        active_error = str(exc)[:240]
                result = {
                    "status": "COMPLETED" if active_error is None else "COMPLETED_ACTIVE_REGISTER_PENDING",
                    "operation_id": operation_id,
                    "generation_id": gen, "config_sha256": config_hash,
                    "runtime_published": True, "service_action_performed": True,
                    "service_verified": True,
                }
                if attestation_result is not None:
                    result["runtime_attestation"] = attestation_result
                if active_profile_store is not None:
                    result["active_profile_record"] = active_result
                    result["active_profile_error"] = active_error
                return result
    finally:
        journal.release_locks(fds)
    return _restore_after_failure(
        operation_store, operation_id, lifecycle_lock, application_lock,
        adapter_root, restore_outcome, crash_at,
    )


def _execute_start(
    operation_store: Path, operation_id: str, lifecycle_lock: Path,
    application_lock: Path, adapter_root: Path, start_outcome: str = "success",
    restore_outcome: str = "success", crash_at: str | None = None,
    active_profile_store: Path | None = None,
) -> dict:
    """Ejecuta start explícito solo en el adaptador fixture B4."""
    fds = publisher._acquire(operation_store, lifecycle_lock, application_lock)
    try:
        operation_dir, record = _load(operation_store, operation_id)
        if record["state"] != "service_start_requested":
            _fail("La operación debe tener start explícito confirmado.")
        gen = record["orchestration"]["generation_id"]
        config_hash = record["publication"]["config_sha256"]
        initial = record["orchestration"]["initial_service"]
        try:
            before = _service_backend().status(adapter_root, request_generation_id=gen)
            unchanged = _matches(
                before, state="inactive",
                generation_id=initial["loaded_generation_id"],
                config_sha256=initial["loaded_config_sha256"],
            )
        except _service_backend().ServiceAdapterError:
            before, unchanged = None, False
        if not unchanged:
            if before is not None:
                _record_observation(record, before, "fail")
            else:
                record["orchestration"]["verification"]["status"] = "fail"
                record["orchestration"]["verification"]["verified_at"] = journal.now()
            _save(operation_dir, record)
        else:
            attestation_before = _attestation_snapshot("before", record)
            try:
                result = _service_backend().start(
                    adapter_root, generation_id=gen, config_sha256=config_hash,
                    expected_generation_id=initial["loaded_generation_id"],
                    expected_config_sha256=initial["loaded_config_sha256"],
                    outcome=start_outcome,
                )
                record["orchestration"]["request"]["result"] = result["result"]
            except _service_backend().ServiceAdapterError:
                record["orchestration"]["request"]["result"] = "exception"
            _save(operation_dir, record)
            if crash_at == "after_start_transition":
                raise journal.SimulatedCrash("after_start_transition")
            try:
                observed = _service_backend().status(adapter_root, request_generation_id=gen)
                verified = _matches(observed, state="active", generation_id=gen,
                                     config_sha256=config_hash)
                _record_observation(record, observed, "pass" if verified else "fail")
            except _service_backend().ServiceAdapterError:
                record["orchestration"]["verification"]["status"] = "fail"
                record["orchestration"]["verification"]["verified_at"] = journal.now()
                verified = False
            _save(operation_dir, record)
            attestation_result = None
            if verified and attestation_before is not None:
                try:
                    attestation_result = _persist_test_attestation(record, attestation_before)
                except Exception:
                    record["orchestration"]["verification"]["status"] = "fail"
                    verified = False
                    _save(operation_dir, record)
            if verified:
                record["state"] = "service_verified"
                record["orchestration"]["phase"] = "service_verified"
                _save(operation_dir, record)
                if crash_at == "after_service_verified":
                    raise journal.SimulatedCrash("after_service_verified")
                record["state"] = "completed"
                record["orchestration"]["phase"] = "completed"
                _save(operation_dir, record)
                active_result = None
                active_error = None
                if active_profile_store is not None:
                    try:
                        active_result = _commit_active_profile(
                            active_profile_store, adapter_root, operation_id, record
                        )
                    except (active_profile_store_module.ActiveProfileError,
                            _service_backend().ServiceAdapterError, OSError) as exc:
                        active_error = str(exc)[:240]
                result = {
                    "status": "COMPLETED" if active_error is None else "COMPLETED_ACTIVE_REGISTER_PENDING",
                    "operation_id": operation_id, "generation_id": gen,
                    "config_sha256": config_hash, "runtime_published": True,
                    "service_action_performed": True, "service_started": True,
                    "service_verified": True,
                }
                if attestation_result is not None:
                    result["runtime_attestation"] = attestation_result
                if active_profile_store is not None:
                    result["active_profile_record"] = active_result
                    result["active_profile_error"] = active_error
                return result
    finally:
        journal.release_locks(fds)
    return _restore_after_failure(
        operation_store, operation_id, lifecycle_lock, application_lock,
        adapter_root, restore_outcome, crash_at,
    )


@_with_service_backend
def start_pending_operation(
    *, operation_store: Path, operation_id: str, lifecycle_lock: Path,
    application_lock: Path, adapter_root: Path, confirm_start: bool,
    active_profile_store: Path | None = None, start_outcome: str = "success",
    restore_outcome: str = "success", crash_at: str | None = None,
) -> dict:
    """Inicia explícitamente una publicación pending_start; requiere confirmación y fixture."""
    if type(confirm_start) is not bool:
        _fail("confirm_start debe ser una decisión booleana explícita.")
    if not confirm_start:
        return {"status": "START_CONFIRMATION_REQUIRED", "operation_id": operation_id,
                "service_action_performed": False}
    if os.geteuid() != 0:
        _fail("B4 fixture requiere root para los almacenes POSIX aislados.")
    if active_profile_store is not None:
        active_profile_store_module.ActiveProfileStore(active_profile_store).prepare()
    fds = publisher._acquire(operation_store, lifecycle_lock, application_lock)
    try:
        operation_dir, record = _load(operation_store, operation_id)
        if record["state"] != "published_pending_start":
            _fail("Solo se puede iniciar una operación published_pending_start.")
        initial = record["orchestration"]["initial_service"]
        if initial["active_state"] != "inactive":
            _fail("El inicio explícito B4 requiere estado inicial inactive.")
        gen = record["orchestration"]["generation_id"]
        observed = _service_backend().status(adapter_root, request_generation_id=gen)
        if not _matches(observed, state="inactive",
                        generation_id=initial["loaded_generation_id"],
                        config_sha256=initial["loaded_config_sha256"]):
            _fail("El servicio cambió desde la publicación; no se solicita start.")
        target = publisher._config_target(
            Path(record["service"]["service_root"]), record["service"]["gid"]
        )
        publisher._verify_published(target, record["publication"]["config_sha256"],
                                    record["service"]["gid"])
        record["orchestration"]["confirmation"] = "accepted"
        record["orchestration"]["request"] = {
            "generation_id": gen, "action": "start",
            "requested_at": journal.now(), "result": "requested",
        }
        record["orchestration"]["phase"] = "start_requested"
        record["state"] = "service_start_requested"
        _save(operation_dir, record)
    finally:
        journal.release_locks(fds)
    return _execute_start(
        operation_store, operation_id, lifecycle_lock, application_lock,
        adapter_root, start_outcome, restore_outcome, crash_at, active_profile_store,
    )


@_with_service_backend
def apply_operation(
    *, staging_args: Namespace, service_root: Path, operation_store: Path,
    lifecycle_lock: Path, application_lock: Path, lease_root: Path,
    service_uid: int, service_gid: int, adapter_root: Path,
    confirm_restart: bool, restart_outcome: str = "success",
    restore_outcome: str = "success", crash_at: str | None = None,
    active_profile_store: Path | None = None,
) -> dict:
    """Ejecuta R-01→R-04 y orquesta solo el servicio fixture R-05."""
    if type(confirm_restart) is not bool:
        _fail("confirm_restart debe ser una decisión booleana explícita.")
    if os.geteuid() != 0:
        _fail("R-05 fixture requiere root para los almacenes POSIX aislados.")
    if active_profile_store is not None:
        active_profile_store_module.ActiveProfileStore(active_profile_store).prepare()
    initial = _service_backend().status(adapter_root)
    preflight_result = preflight.preflight(
        staging_args.profile_store, staging_args.master_key, staging_args.validation_store,
        staging_args.profile_id, staging_args.revision, staging_args.xray_binary,
        staging_args.service_state,
    )
    service_fixture = preflight_result["service_fixture"]
    if (initial["active_state"] != service_fixture["active_state"]
            or initial["sub_state"] != service_fixture["sub_state"]):
        _fail("El adaptador R-05 y el fixture R-01 discrepan; se bloquea la publicación.")
    staged = staging.stage(staging_args)
    generation_id = GENERATION_PREFIX + secrets.token_hex(16)
    prepared = journal.prepare_operation(
        staging_dir=Path(staged["staging_dir"]),
        service_root=service_root,
        service_state=Path(staging_args.service_state),
        operation_store=operation_store,
        lifecycle_lock=lifecycle_lock,
        application_lock=application_lock,
        lease_root=lease_root,
        service_uid=service_uid,
        service_gid=service_gid,
        generation_id=generation_id,
        adapter_initial={
            "loaded_generation_id": initial["loaded_generation_id"],
            "loaded_config_sha256": initial["loaded_config_sha256"],
        },
    )
    operation_id = prepared["operation_id"]
    operation_dir, record = _load(operation_store, operation_id)
    try:
        rechecked = _service_backend().status(adapter_root, request_generation_id=generation_id)
    except _service_backend().ServiceAdapterError as exc:
        return _mark_recovery_required(operation_dir, record, f"No se pudo revalidar el servicio fixture: {exc}")
    if (record["service"]["active_state"] != initial["active_state"]
            or record["service"]["sub_state"] != initial["sub_state"]
            or not _matches(rechecked, state=initial["active_state"],
                            generation_id=initial["loaded_generation_id"],
                            config_sha256=initial["loaded_config_sha256"])):
        return _mark_recovery_required(operation_dir, record, "El estado del servicio cambió durante preflight/staging; se bloquea la publicación.")
    if record["service"]["active_state"] in {"failed", "unknown"}:
        return _mark_recovery_required(
            operation_dir, record,
            "Estado inicial del servicio failed/unknown; no se publica ni se inicia automáticamente.",
        )
    previous_hash = record["snapshot"]["previous_config_sha256"]
    if record["service"]["active_state"] == "active" and (
            previous_hash is None or initial["loaded_config_sha256"] != previous_hash):
        return _mark_recovery_required(
            operation_dir, record,
            "El hash de la configuración cargada no coincide con el snapshot previo.",
        )
    if record["service"]["active_state"] == "active" and not confirm_restart:
        record["orchestration"]["confirmation"] = "rejected"
    elif record["service"]["active_state"] == "active":
        record["orchestration"]["confirmation"] = "accepted"
    else:
        record["orchestration"]["confirmation"] = "not_required"
    _save(operation_dir, record)
    published = publisher.publish_operation(
        operation_store, operation_id, lifecycle_lock, application_lock,
        timeout=staging_args.timeout,
    )
    if published["status"] not in {"CONFIG_PUBLISHED", "ALREADY_PUBLISHED"}:
        return _mark_recovery_required(operation_dir, journal.read_journal(operation_dir), "R-04 no confirmó la publicación.")
    if crash_at == "after_published":
        raise journal.SimulatedCrash("after_published")
    operation_dir, record = _load(operation_store, operation_id)
    if record["service"]["active_state"] == "inactive" or not confirm_restart:
        try:
            current = _service_backend().status(adapter_root, request_generation_id=generation_id)
            initial = record["orchestration"]["initial_service"]
            unchanged = _matches(current, state=initial["active_state"],
                                 generation_id=initial["loaded_generation_id"],
                                 config_sha256=initial["loaded_config_sha256"])
        except _service_backend().ServiceAdapterError:
            unchanged = False
        if not unchanged:
            return _restore_after_failure(
                operation_store, operation_id, lifecycle_lock, application_lock,
                adapter_root, restore_outcome,
            )
    if record["service"]["active_state"] == "inactive":
        record["state"] = "published_pending_start"
        record["orchestration"]["phase"] = "pending_start"
        _save(operation_dir, record)
        return {"status": "PUBLISHED_PENDING_START", "operation_id": operation_id,
                "generation_id": generation_id, "runtime_published": True,
                "service_action_performed": False, "service_started": False}
    if not confirm_restart:
        record["state"] = "published_pending_apply"
        record["orchestration"]["phase"] = "pending_apply"
        _save(operation_dir, record)
        return {"status": "PUBLISHED_PENDING_APPLY", "operation_id": operation_id,
                "generation_id": generation_id, "runtime_published": True,
                "service_action_performed": False, "service_restart_requested": False}
    return _execute_restart(
        operation_store, operation_id, lifecycle_lock, application_lock,
        adapter_root, restart_outcome, restore_outcome, crash_at,
        active_profile_store,
    )


def _recover_one(
    operation_store: Path, operation_id: str, lifecycle_lock: Path,
    application_lock: Path, adapter_root: Path,
    active_profile_store: Path | None = None,
) -> dict:
    fds = publisher._acquire(operation_store, lifecycle_lock, application_lock)
    try:
        operation_dir, record = _load(operation_store, operation_id)
        if record["schema_version"] != 2:
            return {"operation_id": operation_id, "status": "SKIPPED_LEGACY"}
        state = record["state"]
        if state == "completed":
            try:
                attestation_result = _recovery_attestation(record)
            except runtime_attestation.AttestationError as exc:
                return _mark_recovery_required(operation_dir, record, str(exc))
            if active_profile_store is not None:
                try:
                    active_result = _commit_active_profile(
                        active_profile_store, adapter_root, operation_id, record
                    )
                except (active_profile_store_module.ActiveProfileError,
                        _service_backend().ServiceAdapterError, OSError) as exc:
                    return {"operation_id": operation_id, "status": "ACTIVE_REGISTER_RECONCILIATION_REQUIRED",
                            "state": state, "reason": str(exc)[:240]}
                result = {"operation_id": operation_id, "status": "NO_OP",
                          "state": state, "active_profile_record": active_result}
                if attestation_result is not None:
                    result["runtime_attestation"] = attestation_result
                return result
            result = {"operation_id": operation_id, "status": "NO_OP", "state": state}
            if attestation_result is not None:
                result["runtime_attestation"] = attestation_result
            return result
        if state in {"published_pending_apply", "published_pending_start", "rolled_back", "recovery_required"}:
            return {"operation_id": operation_id, "status": "NO_OP", "state": state}
        gen = record["orchestration"]["generation_id"]
        if state == "snapshot_saved":
            snapshot = publisher._snapshot_metadata(operation_dir, record)
            target = publisher._config_target(Path(record["service"]["service_root"]), record["service"]["gid"])
            current, current_meta = publisher._read_current(target, record["service"]["gid"])
            previous = snapshot["previous_config"]
            staged_hash = record["staging"]["config_sha256"]
            if current_meta and current_meta["sha256"] == staged_hash:
                record["state"] = "config_published"
                record["publication"] = {
                    "status": "published", "target": "etc/xray/config.json",
                    "config_sha256": staged_hash, "published_at": journal.now(),
                }
                record["orchestration"]["phase"] = "published"
                record["recovery"]["attempts"] += 1
                record["recovery"]["last_action"] = "r05_detected_rename_before_journal_commit"
                record["recovery"]["last_error"] = None
                _save(operation_dir, record)
                journal.release_locks(fds)
                fds = []
                return _recover_one(operation_store, operation_id, lifecycle_lock,
                                    application_lock, adapter_root)
            not_published = (
                (previous["present"] and current_meta is not None
                 and current_meta["sha256"] == previous["sha256"])
                or (not previous["present"] and current is None)
            )
            if not_published:
                if target.parent.exists():
                    publisher._clean_publish_temps(target.parent, record["service"]["gid"])
                record["state"] = "aborted"
                record["recovery"]["attempts"] += 1
                record["recovery"]["last_action"] = "r05_interrupted_before_publish"
                record["recovery"]["last_error"] = None
                _save(operation_dir, record)
                return {"operation_id": operation_id, "status": "ABORTED_NOT_PUBLISHED",
                        "runtime_published": False, "service_action_performed": False}
            return _mark_recovery_required(operation_dir, record,
                                           "El destino no coincide con snapshot previo ni con la revisión staged.")
        if state == "config_published":
            initial = record["orchestration"]["initial_service"]
            initial_state = initial["active_state"]
            confirmation = record["orchestration"]["confirmation"]
            observed_before = _service_backend().status(adapter_root, request_generation_id=gen)
            if not _matches(observed_before, state=initial_state,
                            generation_id=initial["loaded_generation_id"],
                            config_sha256=initial["loaded_config_sha256"]):
                journal.release_locks(fds)
                fds = []
                return _restore_after_failure(
                    operation_store, operation_id, lifecycle_lock, application_lock,
                    adapter_root, "success",
                )
            if initial_state == "inactive":
                record["state"] = "published_pending_start"
                record["orchestration"]["phase"] = "pending_start"
                _save(operation_dir, record)
                return {"operation_id": operation_id, "status": "PUBLISHED_PENDING_START"}
            if initial_state == "active" and confirmation == "rejected":
                record["state"] = "published_pending_apply"
                record["orchestration"]["phase"] = "pending_apply"
                _save(operation_dir, record)
                return {"operation_id": operation_id, "status": "PUBLISHED_PENDING_APPLY"}
            if initial_state in {"failed", "unknown"} or confirmation != "accepted":
                return _mark_recovery_required(operation_dir, record, "No hay estado/confirmación segura para continuar recovery.")
            # La confirmación fue persistida antes de la caída; puede continuarse una vez.
            record["state"] = "config_published"
            _save(operation_dir, record)
            journal.release_locks(fds)
            fds = []
            return _execute_restart(
                operation_store, operation_id, lifecycle_lock, application_lock,
                adapter_root, "success", "success", active_profile_store=active_profile_store,
            )
        if state in {"service_restart_requested", "service_start_requested", "service_verified"}:
            observed = _service_backend().status(adapter_root, request_generation_id=gen)
            matches_new = _matches(
                observed, state="active", generation_id=gen,
                config_sha256=record["publication"]["config_sha256"],
            )
            if matches_new:
                try:
                    attestation_result = _recovery_attestation(record)
                except runtime_attestation.AttestationError as exc:
                    return _mark_recovery_required(operation_dir, record, str(exc))
                _record_observation(record, observed, "pass")
                record["state"] = "completed"
                record["orchestration"]["phase"] = "completed"
                _save(operation_dir, record)
                active_result = None
                active_error = None
                if active_profile_store is not None:
                    try:
                        active_result = _commit_active_profile(
                            active_profile_store, adapter_root, operation_id, record
                        )
                    except (active_profile_store_module.ActiveProfileError,
                            _service_backend().ServiceAdapterError, OSError) as exc:
                        active_error = str(exc)[:240]
                result = {"operation_id": operation_id,
                          "status": "COMPLETED" if active_error is None else "COMPLETED_ACTIVE_REGISTER_PENDING",
                          "reconciled_by_generation": True, "service_action_performed": True}
                if active_profile_store is not None:
                    result["active_profile_record"] = active_result
                    result["active_profile_error"] = active_error
                if attestation_result is not None:
                    result["runtime_attestation"] = attestation_result
                return result
            # liberar y entrar al rollback coordinado con sus propios locks
            journal.release_locks(fds)
            fds = []
            result = _restore_after_failure(
                operation_store, operation_id, lifecycle_lock, application_lock,
                adapter_root, "success",
            )
            return {"operation_id": operation_id, **result}
        if state in {"rollback_started", "rollback_config_restored", "rollback_failed"}:
            journal.release_locks(fds)
            fds = []
            return {"operation_id": operation_id, **_restore_after_failure(
                operation_store, operation_id, lifecycle_lock, application_lock,
                adapter_root, "success",
            )}
        if state in {"prepared", "validated", "snapshot_saved"}:
            return {"operation_id": operation_id, "status": "NO_PUBLISH", "state": state}
        return _mark_recovery_required(operation_dir, record, "Estado R-05 no reconocido durante recuperación.")
    except _service_backend().ServiceAdapterError as exc:
        if "record" in locals() and record.get("publication", {}).get("status") == "published":
            if fds:
                journal.release_locks(fds)
                fds = []
            return _restore_after_failure(
                operation_store, operation_id, lifecycle_lock, application_lock,
                adapter_root, "fail",
            )
        if "operation_dir" in locals() and "record" in locals():
            return _mark_recovery_required(operation_dir, record, f"Adaptador R-05 no verificable: {exc}")
        raise
    finally:
        if fds:
            journal.release_locks(fds)


@_with_service_backend
def recover_operations(
    *, operation_store: Path, lifecycle_lock: Path, application_lock: Path,
    adapter_root: Path, active_profile_store: Path | None = None,
) -> dict:
    """Reconcilia journals R-05 sin repetir acciones ambiguas ni tocar servicios reales."""
    journal.check_operation_store(operation_store)
    if active_profile_store is not None:
        active_profile_store_module.ActiveProfileStore(active_profile_store).prepare()
    operations = operation_store / "operations"
    if not operations.exists():
        return {"status": "RECOVERY_COMPLETE", "operations": [], "service_action_performed": False}
    journal.check_dir(operations, 0o700, 0, 0)
    results = []
    for operation_dir in sorted(operations.iterdir()):
        if operation_dir.is_symlink() or not operation_dir.is_dir() or not journal.OP_RE.fullmatch(operation_dir.name):
            _fail("Entrada inesperada en operation_store durante R-05 recovery.")
        record = journal.read_journal(operation_dir)
        if record["schema_version"] == 2:
            results.append(_recover_one(
                operation_store, record["operation_id"], lifecycle_lock,
                application_lock, adapter_root, active_profile_store,
            ))
    return {"status": "RECOVERY_COMPLETE", "operations": results,
            "service_action_performed": any(item.get("service_action_performed", False) for item in results)}


def inspect_operation(operation_store: Path, operation_id: str) -> dict:
    operation_dir, record = _load(operation_store, operation_id)
    if record["schema_version"] != 2:
        return {"operation_id": operation_id, "state": record["state"], "schema_version": 1}
    return {
        "operation_id": operation_id, "state": record["state"],
        "schema_version": 2, "generation_id": record["orchestration"]["generation_id"],
        "profile_id": record["source"]["profile_id"], "revision": record["source"]["revision"],
        "publication": record["publication"], "orchestration": record["orchestration"],
        "rollback": record["rollback"], "recovery": record["recovery"],
    }
