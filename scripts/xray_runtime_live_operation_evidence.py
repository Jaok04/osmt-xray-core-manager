#!/usr/bin/env python3
"""Verifica evidencia live antes de delegar una acción de servicio.

La evidencia se deriva del journal live, del informe persistido de validación
perfil/revisión y de los bytes actualmente publicados. No ejecuta systemd ni
modifica el runtime. El caller debe poseer el lifecycle lock.
"""
from __future__ import annotations

import grp
import hashlib
import os
import re
import stat
from pathlib import Path
from typing import Any

import xray_profile_validation_store as validation_store_module
import xray_runtime_live_journal as live_journal

CONFIG_FILE = Path("/etc/xray/config.json")
XRAY_GROUP = "xray"
MAX_CONFIG = live_journal.MAX_SNAPSHOT
GENERATION_RE = re.compile(r"generation-[0-9a-f]{32}\Z")
REQUIRED_CHECKS = {
    "json_syntax", "xray_structure", "required_parameters", "types_values",
    "references_conflicts", "xray_native",
}


class LiveOperationEvidenceError(Exception):
    pass


def _fail(message: str) -> None:
    raise LiveOperationEvidenceError(message)


def _read_published_config(path: Path, gid: int) -> bytes:
    if not path.is_absolute():
        _fail("La ruta runtime debe ser absoluta.")
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            if stat.S_ISLNK(current.lstat().st_mode):
                _fail("La ruta runtime contiene un componente symlink.")
        except FileNotFoundError:
            _fail("No existe la configuración runtime publicada.")
    try:
        parent = path.parent.lstat()
        if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid != 0 or parent.st_gid != gid
                or stat.S_IMODE(parent.st_mode) != 0o750):
            _fail("El directorio de configuración no es root:xray 0750.")
        entry = path.lstat()
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                     | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NONBLOCK", 0))
    except OSError as exc:
        raise LiveOperationEvidenceError("No se pudo abrir la configuración runtime publicada.") from exc
    try:
        info = os.fstat(fd)
        if ((entry.st_dev, entry.st_ino) != (info.st_dev, info.st_ino)
                or not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_gid != gid
                or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o640
                or not 1 <= info.st_size <= MAX_CONFIG):
            _fail("La configuración runtime tiene tipo, propietario, permisos o tamaño inseguros.")
        chunks, total = [], 0
        while True:
            part = os.read(fd, min(65536, MAX_CONFIG + 1 - total))
            if not part:
                break
            chunks.append(part)
            total += len(part)
            if total > MAX_CONFIG:
                _fail("La configuración runtime excede el límite.")
        data = b"".join(chunks)
        if total != info.st_size:
            _fail("La configuración runtime cambió durante la lectura.")
        return data
    finally:
        os.close(fd)


def verify_live_operation(*, operation_id: str, generation_id: str,
                          store: Any | None = None,
                          validation_store: Path | None = None,
                          runtime_config_path: Path | None = None) -> dict[str, Any]:
    """Comprueba la cadena live exacta que precede a start/restart/stop.

    Los parámetros de rutas/dependencias alternativos son puntos de inyección
    para pruebas; la llamada productiva usa las rutas fijas del proyecto.
    """
    if os.geteuid() != 0:
        _fail("La verificación de evidencia live requiere root.")
    if not isinstance(operation_id, str) or not live_journal.OP_RE.fullmatch(operation_id):
        _fail("operation_id inválido.")
    if not isinstance(generation_id, str) or not GENERATION_RE.fullmatch(generation_id):
        _fail("generation_id inválido.")
    store = store or live_journal.LiveOperationStore()
    record = store.load(operation_id)
    if (record.get("environment") != "live" or record.get("operation_id") != operation_id
            or record.get("state") != "service_action_requested"):
        _fail("El journal no está en la fase durable previa a una acción live.")

    action = record.get("service_action")
    if (not isinstance(action, dict) or action.get("status") != "requested"
            or action.get("generation_id") != generation_id
            or action.get("confirmation") is not True
            or action.get("action") not in {"start", "restart", "stop"}
            or action.get("published_config_sha256") != record.get("staged_config_sha256")):
        _fail("La solicitud de acción no vincula confirmación, generación y operación.")

    publication = record.get("publication")
    expected_hash = record.get("staged_config_sha256")
    if (not isinstance(publication, dict) or publication.get("status") != "published"
            or publication.get("target") != str(CONFIG_FILE)
            or not isinstance(publication.get("config_sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", publication["config_sha256"])
            or publication["config_sha256"] != expected_hash):
        _fail("El journal no acredita publicación live de los bytes staged.")

    report_store_path = Path(validation_store) if validation_store is not None else Path(
        "/var/lib/xray-manager/profile-validations"
    )
    reports = validation_store_module.ProfileValidationReportStore(report_store_path)
    with reports.read_only_locked():
        catalog = reports._load_catalog()
        all_reports = reports._verify_all(catalog)
    report = next((item for item in all_reports
                   if item.get("validation_id") == record.get("validation_id")), None)
    if (report is None or report.get("profile_id") != record.get("profile_id")
            or report.get("revision") != record.get("revision")
            or report.get("content_sha256") != record.get("profile_sha256")
            or report.get("result") not in {"PASS", "PASS_WITH_WARNINGS"}
            or report.get("xray", {}).get("binary_sha256") != record.get("binary_sha256")):
        _fail("El informe persistido no acredita perfil, revisión, contenido y binario de esta operación.")
    checks = {item.get("name"): item.get("status") for item in report.get("checks", [])
              if isinstance(item, dict)}
    if not REQUIRED_CHECKS.issubset(checks) or any(checks[name] != "PASS" for name in REQUIRED_CHECKS):
        _fail("El informe persistido no supera todas las comprobaciones requeridas.")

    gid = grp.getgrnam(XRAY_GROUP).gr_gid
    config_path = Path(runtime_config_path) if runtime_config_path is not None else CONFIG_FILE
    current = _read_published_config(config_path, gid)
    current_hash = hashlib.sha256(current).hexdigest()
    if current_hash != publication["config_sha256"]:
        _fail("Los bytes runtime actuales no coinciden con la publicación de esta operación.")

    return {
        "verified": True, "environment": "live",
        "operation_id": operation_id, "generation_id": generation_id,
        "profile_id": record["profile_id"], "revision": record["revision"],
        "validation_id": record["validation_id"],
        "published_config_sha256": publication["config_sha256"],
        "runtime_config_sha256": current_hash,
        "publication_status": "published", "validation_result": report["result"],
        "action": action["action"],
    }
