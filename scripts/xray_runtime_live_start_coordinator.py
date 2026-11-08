#!/usr/bin/env python3
"""Coordinación durable start→observación; sin CLI ni integración al menú.

La función sólo opera con dependencias explícitas inyectadas. Si la llamada al
controlador o la observación queda ambigua, persiste recovery_required y nunca
reintenta automáticamente. La evidencia terminal es correlativa, no prueba
bytes de configuración cargados en memoria.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Callable

import xray_runtime_live_start_attestation as start_attestation


class StartCoordinatorError(Exception):
    """El inicio no puede confirmarse de forma durable y correlacionada."""


def _fail(message: str) -> None:
    raise StartCoordinatorError(message)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _valid_generation(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"generation-[0-9a-f]{32}", value) is not None


def start_published_operation(*, store: Any, operation_id: str, generation_id: str,
                              backend: Any, systemd_observer: Callable[[], dict],
                              process_observer: Callable[[], dict],
                              config_hash_reader: Callable[[], str],
                              confirmation: bool) -> dict[str, Any]:
    """Solicita start una sola vez y persiste cada fase antes de avanzar.

    Esta API no es expuesta por CLI/menú. Caller debe poseer lifecycle lock;
    backend debe ser el LiveRuntimeBackend configurado con el mismo descriptor.
    """
    if confirmation is not True:
        _fail("El inicio requiere confirmación explícita.")
    if not isinstance(operation_id, str) or not re.fullmatch(r"runtime-op-[0-9a-f]{32}", operation_id):
        _fail("operation_id inválido.")
    if not _valid_generation(generation_id):
        _fail("generation_id inválido.")
    record = store.load(operation_id)
    if record.get("environment") != "live" or record.get("state") not in {"config_published", "published_pending_start"}:
        _fail("La operación no está publicada y pendiente de start.")
    publication = record.get("publication")
    if (not isinstance(publication, dict) or publication.get("status") != "published"
            or publication.get("target") != "/etc/xray/config.json"
            or publication.get("operation_id", operation_id) != operation_id):
        _fail("El journal no acredita una publicación live utilizable.")
    expected_hash = publication.get("config_sha256")
    if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
        _fail("Hash de publicación inválido.")
    before_hash = config_hash_reader()
    if before_hash != expected_hash:
        _fail("El hash runtime actual no coincide con la publicación; start bloqueado.")

    request = {"action": "start", "status": "requested", "requested_at": _now(),
               "generation_id": generation_id, "confirmation": True,
               "published_config_sha256": expected_hash}
    state = record["state"]
    store.transition(operation_id, expected_state=state, new_state="service_action_requested",
                     updates={"service_action": request})

    try:
        controller = backend.start(operation_id=operation_id, generation_id=generation_id,
                                   confirmation=True)
        if (not isinstance(controller, dict)
                or controller.get("result") != "accepted_not_verified"
                or controller.get("postcondition") != "pending_observation"):
            _fail("El controlador no devolvió aceptación pendiente verificable.")
    except Exception as exc:
        _mark_recovery(store, operation_id, "service_action_requested", "controller_outcome_ambiguous", exc)
        raise StartCoordinatorError("Resultado de start ambiguo; journal en recovery_required. No reintentar sin reconciliar.") from exc

    accepted = {**request, "status": "accepted", "accepted_at": _now(),
                "controller": controller.get("controller_result", {}).get("controller", "modules/xray_service.sh"),
                "controller_result": "accepted", "controller_returncode": controller.get("controller_result", {}).get("returncode")}
    try:
        store.transition(operation_id, expected_state="service_action_requested", new_state="service_action_accepted",
                         updates={"service_action": accepted})
    except Exception as exc:
        _mark_recovery(store, operation_id, "service_action_requested", "acceptance_persistence_failed", exc)
        raise StartCoordinatorError("El controlador aceptó start, pero no se pudo persistir la aceptación; requiere reconciliación.") from exc

    try:
        systemd = systemd_observer()
        process = process_observer()
        after_hash = config_hash_reader()
        evidence = start_attestation.attest_start(
            publication={**publication, "operation_id": operation_id},
            systemd=systemd, process=process,
            config_sha256_before=before_hash, config_sha256_after=after_hash,
        )
        if evidence.get("verified") is not True or evidence.get("configuration_loaded") is not False:
            _fail("La evidencia post-start no cumple el nivel probatorio permitido.")
    except Exception as exc:
        _mark_recovery(store, operation_id, "service_action_accepted", "post_start_observation_unverified", exc)
        raise StartCoordinatorError("Start aceptado, pero la observación posterior no pudo acreditarse; journal en recovery_required.") from exc

    observed = {"status": "active_correlated", "observed_at": _now(),
                "main_pid": evidence["main_pid"], "invocation_id": evidence["invocation_id"],
                "active_enter_timestamp": evidence["active_enter_timestamp"],
                "exec_main_start_timestamp": evidence["exec_main_start_timestamp"],
                "process_starttime_ticks": evidence["process_starttime_ticks"],
                "executable_sha256": evidence["executable_sha256"],
                "runtime_config_sha256": after_hash,
                "evidence_level": evidence["evidence_level"],
                "configuration_loaded": False}
    final_action = {**accepted, "status": "observed_active", "observed_at": observed["observed_at"]}
    completed = store.transition(
        operation_id, expected_state="service_action_accepted", new_state="service_observed_active",
        updates={"service_action": final_action, "post_systemd": observed,
                 "configuration_evidence": "pending"},
    )
    return {"status": "SERVICE_ACTIVE_CORRELATED", "operation_id": operation_id,
            "generation_id": generation_id, "journal_state": completed["state"],
            "evidence": evidence, "configuration_loaded": False,
            "completed": False, "read_only_observation": True}


def _mark_recovery(store: Any, operation_id: str, expected_state: str,
                   decision: str, error: Exception) -> None:
    try:
        store.transition(operation_id, expected_state=expected_state, new_state="recovery_required",
                         updates={"recovery": {"attempts": 1, "decision": decision,
                                               "error_code": type(error).__name__}})
    except Exception as journal_error:
        raise StartCoordinatorError("No se pudo persistir recovery_required; requiere reconciliación manual prioritaria.") from journal_error
