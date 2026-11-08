#!/usr/bin/env python3
"""Adaptador fixture B4.3-B: evidencia persistente antes de liberar el gate."""
from __future__ import annotations

import os
import stat
from typing import Any

import xray_runtime_evidence_store as store


class SupervisorEvidenceError(Exception):
    """Fallo cerrado al preparar evidencia persistente del supervisor."""


def prepare_persistent_evidence(*, plan: dict[str, Any], target_pid: int,
                                fixture_root_fd: int) -> dict[str, Any]:
    if not isinstance(plan, dict) or plan.get("environment") != "fixture":
        raise SupervisorEvidenceError("El adaptador sólo admite planes fixture.")
    invocation_id = plan.get("invocation_id")
    service_gid = plan.get("service_gid")
    if (type(target_pid) is not int or target_pid <= 1
            or type(service_gid) is not int or service_gid <= 0
            or plan.get("target_pid") != target_pid):
        raise SupervisorEvidenceError("PID o GID del proceso bloqueado no coincide con el plan.")
    metadata = plan.get("fd_metadata")
    if not isinstance(metadata, dict):
        raise SupervisorEvidenceError("Faltan metadatos verificados del memfd.")
    digest, size = metadata.get("sha256"), metadata.get("size_bytes")
    if (not isinstance(digest, str) or len(digest) != 64
            or any(ch not in "0123456789abcdef" for ch in digest)
            or type(size) is not int or not 1 <= size <= 16 * 1024 * 1024
            or digest != plan.get("expected_sha256") or size != plan.get("expected_size")):
        raise SupervisorEvidenceError("Hash/tamaño no proceden de metadatos verificados del memfd.")
    try:
        root_info = os.fstat(fixture_root_fd)
        if (not stat.S_ISDIR(root_info.st_mode) or root_info.st_uid != 0
                or root_info.st_gid != 0 or stat.S_IMODE(root_info.st_mode) != 0o711):
            raise SupervisorEvidenceError("El descriptor raíz no es un ancla fixture confiable.")
        name = store.create_evidence_from_root_fd(
            fixture_root_fd=fixture_root_fd, service_gid=service_gid,
            invocation_id=invocation_id,
            metadata={"pid": target_pid, "config_sha256": digest,
                      "config_size_bytes": size},
        )
        verified = store.verify_evidence_from_root_fd(
            fixture_root_fd=fixture_root_fd, service_gid=service_gid,
            invocation_id=invocation_id,
        )
        record = verified.get("record", {})
        if (not verified.get("verified") or record.get("pid") != target_pid
                or record.get("config_sha256") != digest
                or record.get("config_size_bytes") != size
                or record.get("evidence_status") != "prepared_before_exec"):
            raise SupervisorEvidenceError("La evidencia persistente no coincide con la invocación.")
        return {"verified": True, "persistent": True, "reference": name,
                "evidence_status": "prepared_before_exec"}
    except store.EvidenceStoreError as exc:
        raise SupervisorEvidenceError("No se pudo crear y verificar evidencia B4.3-A.") from exc
