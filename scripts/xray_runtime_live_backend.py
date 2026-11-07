#!/usr/bin/env python3
"""Contrato aislado del backend runtime live; no se conecta a R-05 ni al menú.

Observa systemd/proceso y delega mutaciones en xray_service.sh. No ejecuta
systemctl directamente ni afirma qué configuración reside en memoria.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

import xray_runtime_process_attestation as process_attestation
import xray_runtime_service_control as service_control
import xray_runtime_systemd_adapter as systemd_adapter


class LiveBackendError(Exception):
    """Precondición, observación o mutación live no demostrada."""


def _fail(message: str) -> None:
    raise LiveBackendError(message)


class LiveRuntimeBackend:
    RUNTIME_BACKEND_LIVE = True

    def __init__(
        self, *, lifecycle_lock_fd: int, lifecycle_lock_path: Path,
        systemd_observer: Callable[[], dict] | None = None,
        process_observer: Callable[[], dict] | None = None,
        action_runner: Callable[..., dict] | None = None,
        operation_evidence_reader: Callable[[str, str], dict] | None = None,
    ):
        self.lifecycle_lock_fd = lifecycle_lock_fd
        self.lifecycle_lock_path = Path(lifecycle_lock_path)
        self._systemd_observer = systemd_observer or systemd_adapter.status
        self._process_observer = process_observer or process_attestation.observe_process_identity
        self._action_runner = action_runner or service_control.run_action
        self._operation_evidence_reader = operation_evidence_reader

    @staticmethod
    def _validate_snapshot(snapshot: dict) -> None:
        if not isinstance(snapshot, dict) or snapshot.get("read_only") is not True:
            _fail("Snapshot systemd inválido o no read-only.")
        if snapshot.get("unit") != "xray.service":
            _fail("La unidad observada no es xray.service.")
        if snapshot.get("load_state") != "loaded":
            _fail("La unidad xray.service no está cargada.")
        state = snapshot.get("active_state")
        if state not in {"active", "inactive", "failed", "unknown"}:
            _fail("Estado systemd transitorio/no reconocido; operación bloqueada.")
        main_pid = snapshot.get("main_pid")
        invocation_id = snapshot.get("invocation_id")
        if state == "inactive":
            if main_pid not in (None, 0) or invocation_id not in (None, ""):
                _fail("Snapshot contradictorio: inactive no puede conservar MainPID ni InvocationID.")
        elif state == "active":
            if (not isinstance(main_pid, int) or isinstance(main_pid, bool) or main_pid <= 1
                    or not isinstance(invocation_id, str)
                    or not re.fullmatch(r"[0-9a-fA-F]{32}", invocation_id)
                    or snapshot.get("sub_state") != "running"
                    or snapshot.get("result") != "success"):
                _fail("Snapshot active incompleto: requiere MainPID, InvocationID, running y result=success.")
        if snapshot.get("runtime_config_sha256") is not None and not re.fullmatch(
            r"[0-9a-f]{64}", str(snapshot["runtime_config_sha256"])
        ):
            _fail("Hash runtime inválido.")
        if snapshot.get("loaded_generation_id") is not None or snapshot.get("loaded_config_sha256") is not None:
            _fail("No se admite atribuir generación/hash cargados sin evidencia específica.")

    def status(self) -> dict:
        observed = self._systemd_observer()
        self._validate_snapshot(observed)
        process = None
        if observed["active_state"] == "active":
            process = self._process_observer()
            if (not isinstance(process, dict) or process.get("read_only") is not True
                    or process.get("identity_verified") is not True
                    or process.get("configuration_loaded") is not False
                    or process.get("configuration_evidence") != "not_attested"
                    or process.get("pid") != observed.get("main_pid")
                    or process.get("systemd_main_pid") != observed.get("main_pid")
                    or process.get("systemd_invocation_id") != observed.get("invocation_id")):
                _fail("La identidad del proceso no está correlacionada con el snapshot systemd.")
        return {
            "unit": observed["unit"],
            "load_state": observed["load_state"],
            "active_state": observed["active_state"],
            "sub_state": observed.get("sub_state"),
            "result": observed.get("result"),
            "main_pid": observed.get("main_pid"),
            "invocation_id": observed.get("invocation_id"),
            "active_enter_timestamp": observed.get("active_enter_timestamp"),
            "fragment_path": observed.get("fragment_path"),
            "published_config_sha256": None,
            "runtime_config_sha256": observed.get("runtime_config_sha256"),
            "process_identity": process,
            "loaded_generation_id": None,
            "loaded_config_sha256": None,
            "configuration_loaded": False,
            "configuration_evidence": "not_attested",
            "read_only": True,
        }

    def _mutate(self, action: str, *, operation_id: str, generation_id: str,
                confirmation: bool, recovery_reason: str | None = None) -> dict:
        if confirmation is not True:
            _fail("La acción requiere confirmación explícita.")
        if self._operation_evidence_reader is None:
            _fail("No existe un verificador confiable de evidencia operation/generation/validation/publication.")
        if (not isinstance(operation_id, str) or not re.fullmatch(r"runtime-op-[0-9a-f]{32}", operation_id)
                or not isinstance(generation_id, str) or not re.fullmatch(r"generation-[0-9a-f]{32}", generation_id)):
            _fail("Se requiere operation_id y generation_id válidos.")
        evidence = self._operation_evidence_reader(operation_id, generation_id)
        if (not isinstance(evidence, dict) or evidence.get("verified") is not True
                or evidence.get("environment") != "live"
                or evidence.get("operation_id") != operation_id
                or evidence.get("generation_id") != generation_id
                or evidence.get("publication_status") != "published"
                or evidence.get("validation_result") not in {"PASS", "PASS_WITH_WARNINGS"}
                or not isinstance(evidence.get("published_config_sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", evidence["published_config_sha256"])):
            _fail("La evidencia no acredita una publicación live validada para esta operación.")
        expected_runtime_config_sha256 = evidence["published_config_sha256"]
        before = self.status()
        if before["runtime_config_sha256"] != expected_runtime_config_sha256:
            _fail("CAS rechazado: runtime no coincide con el hash publicado por la operación verificada.")
        state = before["active_state"]
        if action == "start" and state != "inactive":
            _fail("start solo se permite desde inactive.")
        if action == "restart" and state != "active":
            _fail("restart solo se permite desde active.")
        if action == "stop":
            if state != "active" or not before["process_identity"]:
                _fail("stop requiere servicio active e identidad de proceso verificada.")
            if not isinstance(recovery_reason, str) or not recovery_reason.strip():
                _fail("stop requiere una justificación de recuperación.")
        if action not in {"start", "restart", "stop"}:
            _fail("Acción no permitida.")
        # Reobservación inmediatamente antes de delegar: CAS conservador frente
        # a cambios externos; lifecycle lock solo serializa operaciones Manager.
        confirm = self.status()
        stable = ("active_state", "main_pid", "invocation_id", "runtime_config_sha256")
        if any(before.get(key) != confirm.get(key) for key in stable):
            _fail("CAS rechazado: systemd/proceso/configuración cambió antes de la acción.")
        result = self._action_runner(
            action, lifecycle_lock_fd=self.lifecycle_lock_fd,
            lifecycle_lock_path=self.lifecycle_lock_path,
        )
        if not isinstance(result, dict) or result.get("result") != "accepted":
            _fail("El controlador no confirmó la solicitud; requiere nueva observación.")
        return {
            "action": action, "result": "accepted_not_verified",
            "before": confirm, "controller_result": result,
            "operation_evidence": evidence,
            "postcondition": "pending_observation",
            "configuration_loaded": False,
        }

    def start(self, *, operation_id: str, generation_id: str, confirmation: bool) -> dict:
        return self._mutate("start", operation_id=operation_id, generation_id=generation_id,
                            confirmation=confirmation)

    def restart(self, *, operation_id: str, generation_id: str, confirmation: bool) -> dict:
        return self._mutate("restart", operation_id=operation_id, generation_id=generation_id,
                            confirmation=confirmation)

    def stop(self, *, operation_id: str, generation_id: str, confirmation: bool,
             recovery_reason: str) -> dict:
        return self._mutate("stop", operation_id=operation_id, generation_id=generation_id,
                            confirmation=confirmation, recovery_reason=recovery_reason)

    def restore(self, **_kwargs) -> dict:
        _fail("restore live no está implementado: requiere rollback atómico de archivo y CAS de InvocationID; no se delega una restauración parcial.")
