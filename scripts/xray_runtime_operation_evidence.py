#!/usr/bin/env python3
"""Verifica la cadena journal -> validación -> staging -> publicación.

La implementación actual sólo puede leer journals R-03 marcados como fixture.
No constituye un emisor de evidencia live ni habilita el backend live.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import xray_profile_validation_store as validation_store_module
import xray_runtime_journal as journal
import xray_runtime_publisher as publisher


class OperationEvidenceError(Exception):
    pass


PUBLISHED_STATES = {
    "config_published", "published_pending_apply", "published_pending_start",
    "service_restart_requested", "service_start_requested", "service_verified", "completed",
}


def _fail(message: str) -> None:
    raise OperationEvidenceError(message)


def verify_published_operation(
    *, operation_store: Path, operation_id: str, generation_id: str,
    validation_store: Path, runtime_config_path: Path,
) -> dict[str, Any]:
    """Devuelve evidencia comprobada; falla cerrado ante cualquier discrepancia.

    El journal actual fuerza explícitamente marcadores fixture. Por diseño el
    resultado lleva environment=fixture y nunca autoriza una mutación live.
    """
    if not isinstance(operation_id, str) or not journal.OP_RE.fullmatch(operation_id):
        _fail("operation_id inválido.")
    if not isinstance(generation_id, str) or not journal.GENERATION_RE.fullmatch(generation_id):
        _fail("generation_id inválido.")
    operation_store = Path(operation_store)
    validation_store = Path(validation_store)
    runtime_config_path = Path(runtime_config_path)
    journal.check_operation_store(operation_store)
    operation_dir = operation_store / "operations" / operation_id
    record = journal.read_journal(operation_dir)
    orchestration = record.get("orchestration")
    if record.get("schema_version") != 2 or not isinstance(orchestration, dict):
        _fail("La operación no contiene metadatos R-05 schema 2.")
    if orchestration.get("generation_id") != generation_id:
        _fail("generation_id no corresponde a operation_id.")
    if record.get("state") not in PUBLISHED_STATES:
        _fail("La operación no está en un estado publicado utilizable.")
    publication = record.get("publication", {})
    if publication.get("status") != "published":
        _fail("El journal no confirma publicación.")
    if record.get("rollback", {}).get("status") != "not_started":
        _fail("La operación tiene rollback iniciado; no autoriza start/restart.")
    manifest, staged_bytes = publisher._validate_stage(operation_dir, record)
    staged_hash = hashlib.sha256(staged_bytes).hexdigest()
    published_hash = publication.get("config_sha256")
    if (not isinstance(published_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", published_hash)
            or staged_hash != record["staging"].get("config_sha256")
            or staged_hash != published_hash
            or manifest.get("validation_id") != record["source"].get("validation_id")
            or manifest.get("profile_id") != record["source"].get("profile_id")
            or manifest.get("revision") != record["source"].get("revision")
            or manifest.get("profile_content_sha256") != record["source"].get("profile_content_sha256")
            or manifest.get("native_validation") != "PASS"):
        _fail("La identidad de validación/staging/publicación no forma una cadena coherente.")

    reports = validation_store_module.ProfileValidationReportStore(validation_store)
    with reports.read_only_locked():
        catalog = reports._load_catalog()
        all_reports = reports._verify_all(catalog)
    report = next((item for item in all_reports
                   if item.get("validation_id") == record["source"]["validation_id"]), None)
    if (report is None or report.get("profile_id") != record["source"]["profile_id"]
            or report.get("revision") != record["source"]["revision"]
            or report.get("content_sha256") != record["source"]["profile_content_sha256"]
            or report.get("result") not in {"PASS", "PASS_WITH_WARNINGS"}
            or report.get("xray", {}).get("binary_sha256") != manifest.get("xray_binary", {}).get("sha256")):
        _fail("El informe persistido no acredita esta revisión, contenido y binario Xray.")
    required = {"json_syntax", "xray_structure", "required_parameters", "types_values",
                "references_conflicts", "xray_native"}
    checks = {item.get("name"): item.get("status") for item in report.get("checks", [])
              if isinstance(item, dict)}
    if not required.issubset(checks) or any(checks[name] != "PASS" for name in required):
        _fail("El informe persistido no supera todas las comprobaciones requeridas.")

    expected_target = Path(record["service"]["service_root"]) / "etc" / "xray" / "config.json"
    if runtime_config_path != expected_target:
        _fail("La ruta runtime solicitada no coincide con el destino de la operación.")
    current = journal.read_regular(runtime_config_path, journal.MAX_FILE, 0,
                                   record["service"]["gid"], 0o640,
                                   "config runtime publicada")
    if hashlib.sha256(current).hexdigest() != published_hash:
        _fail("Los bytes runtime actuales no coinciden con la publicación de esta operación.")
    return {
        "verified": True, "environment": "fixture",
        "operation_id": operation_id, "generation_id": generation_id,
        "validation_id": record["source"]["validation_id"],
        "profile_id": record["source"]["profile_id"],
        "revision": record["source"]["revision"],
        "published_config_sha256": published_hash,
        "runtime_config_sha256": hashlib.sha256(current).hexdigest(),
        "publication_status": "published", "validation_result": report["result"],
    }
