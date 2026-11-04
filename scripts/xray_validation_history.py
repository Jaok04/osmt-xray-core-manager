#!/usr/bin/env python3
"""Consultas de historial y comparación read-only para informes C-05B."""
from __future__ import annotations

import datetime as dt
from typing import Any

import xray_validation_store as storemod


class ValidationHistoryError(Exception):
    """Error controlado del servicio de historial."""


def _timestamp(value: Any, field: str = "created_at") -> dt.datetime:
    if not isinstance(value, str) or not value or len(value) > 40:
        raise ValidationHistoryError(f"Fecha inválida en {field}.")
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except (ValueError, OverflowError):
        raise ValidationHistoryError(f"Fecha inválida en {field}.") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValidationHistoryError(f"La fecha {field} debe incluir zona horaria.")
    return parsed.astimezone(dt.timezone.utc)


def _date_bound(value: str | dt.datetime | None, field: str) -> dt.datetime | None:
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        parsed = value
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValidationHistoryError(f"{field} debe incluir zona horaria.")
        return parsed.astimezone(dt.timezone.utc)
    return _timestamp(value, field)


def _safe_limit(value: int, field: str, maximum: int) -> int:
    if type(value) is not int or value < 0 or value > maximum:
        raise ValidationHistoryError(f"{field} fuera de rango.")
    return value


class ValidationHistoryService:
    """Consulta informes C-05B sin modificar el almacén ni las configuraciones."""

    def __init__(self, root: str | None = None, *, store: storemod.ValidationReportStore | None = None):
        self.store = store or storemod.ValidationReportStore(root)

    def _verified_reports(self) -> list[dict[str, Any]]:
        # Un solo lock y una sola verificación íntegra del catálogo por consulta.
        with self.store.locked():
            catalog = self.store._catalog()
            self.store._verify_catalog_reports(catalog)
            reports = []
            for entry in catalog["reports"]:
                report = storemod._strict_json(
                    storemod._read(self.store._report_path(entry["validation_id"]), storemod.MAX_REPORT),
                    "Informe",
                )
                reports.append(report)
            return reports

    def list_history(
        self, *, config_id: str | None = None, revision: str | None = None,
        date_from: str | dt.datetime | None = None, date_to: str | dt.datetime | None = None,
        validation_type: str | None = None, result: str | None = None,
        limit: int = 100, offset: int = 0,
    ) -> dict[str, Any]:
        if config_id is not None and (not isinstance(config_id, str) or not storemod.CONFIG_RE.fullmatch(config_id)):
            raise ValidationHistoryError("config_id inválido.")
        if revision is not None and (not isinstance(revision, str) or not storemod.REV_RE.fullmatch(revision)):
            raise ValidationHistoryError("revision inválida.")
        if validation_type is not None and validation_type != "static_and_native":
            raise ValidationHistoryError("validation_type no admitido.")
        if result is not None and (not isinstance(result, str) or result not in storemod.RESULTS):
            raise ValidationHistoryError("result no admitido.")
        start = _date_bound(date_from, "date_from")
        end = _date_bound(date_to, "date_to")
        if start and end and start > end:
            raise ValidationHistoryError("date_from no puede ser posterior a date_to.")
        limit = _safe_limit(limit, "limit", 1000)
        offset = _safe_limit(offset, "offset", 1000000)
        reports = self._verified_reports()
        selected = []
        for report in reports:
            created = _timestamp(report.get("created_at"))
            if config_id is not None and report.get("config_id") != config_id:
                continue
            if revision is not None and report.get("revision") != revision:
                continue
            if start and created < start:
                continue
            if end and created > end:
                continue
            if validation_type and report.get("validation_type") != validation_type:
                continue
            if result and report.get("result") != result:
                continue
            selected.append(report)
        selected.sort(key=lambda item: (_timestamp(item["created_at"]), item["stored_at"], item["validation_id"]), reverse=True)
        total = len(selected)
        page = selected[offset:offset + limit]
        return {
            "total": total, "limit": limit, "offset": offset,
            "reports": [{
                "validation_id": r["validation_id"], "config_id": r["config_id"],
                "revision": r["revision"], "created_at": r["created_at"],
                "stored_at": r["stored_at"], "validation_type": r["validation_type"],
                "result": r["result"], "content_sha256": r["content_sha256"],
                "content_size_bytes": r["content_size_bytes"],
            } for r in page],
        }

    def get_report_detail(self, validation_id: str) -> dict[str, Any]:
        if not isinstance(validation_id, str) or not storemod.ID_RE.fullmatch(validation_id):
            raise ValidationHistoryError("validation_id inválido.")
        try:
            return self.store.get_report(validation_id)
        except storemod.ValidationStoreError as exc:
            raise ValidationHistoryError(str(exc)) from None

    def get_latest_report(self, *, config_id: str | None = None) -> dict[str, Any] | None:
        result = self.list_history(config_id=config_id, limit=1)
        if not result["reports"]:
            return None
        return self.get_report_detail(result["reports"][0]["validation_id"])

    def compare_reports(self, first_id: str, second_id: str) -> dict[str, Any]:
        first = self.get_report_detail(first_id)
        second = self.get_report_detail(second_id)
        if first["config_id"] != second["config_id"]:
            raise ValidationHistoryError("La comparación exige informes de la misma configuración.")
        a = {item["name"]: item for item in first["checks"]}
        b = {item["name"]: item for item in second["checks"]}
        added = sorted(b.keys() - a.keys())
        removed = sorted(a.keys() - b.keys())
        changed = []
        for name in sorted(a.keys() & b.keys()):
            fields = [field for field in ("status", "errors", "warnings", "details") if a[name].get(field) != b[name].get(field)]
            if fields:
                changed.append({"name": name, "fields": fields, "before": {k: a[name].get(k) for k in fields},
                                "after": {k: b[name].get(k) for k in fields}})
        return {
            "config_id": first["config_id"],
            "first": {k: first.get(k) for k in ("validation_id", "revision", "created_at", "stored_at", "result", "content_sha256", "content_size_bytes", "xray_version", "xray_binary_sha256")},
            "second": {k: second.get(k) for k in ("validation_id", "revision", "created_at", "stored_at", "result", "content_sha256", "content_size_bytes", "xray_version", "xray_binary_sha256")},
            "summary": {
                "result_changed": first["result"] != second["result"],
                "content_changed": first["content_sha256"] != second["content_sha256"],
                "size_changed": first["content_size_bytes"] != second["content_size_bytes"],
                "xray_version_changed": first.get("xray_version") != second.get("xray_version"),
                "xray_binary_changed": first.get("xray_binary_sha256") != second.get("xray_binary_sha256"),
                "checks_added": added, "checks_removed": removed, "checks_changed": changed,
            },
        }


__all__ = ["ValidationHistoryError", "ValidationHistoryService"]
