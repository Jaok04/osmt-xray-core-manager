#!/usr/bin/env python3
"""Orquestación transaccional de validación y promoción de configuraciones independientes.

Une C-05A y C-05B sin activar Xray ni modificar el runtime. El informe y los
metadatos de promoción se confirman o revierten mediante un journal propio.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

import xray_configurations as configurations
import xray_config_validator as validator
import xray_validation_store as validation_store

REQUIRED_CHECKS = {
    "json_syntax",
    "xray_structure",
    "required_parameters",
    "types_values",
    "references_conflicts",
    "xray_native",
}
PROMOTION_WAL_LIMIT = 48 * 1024 * 1024
CONFIG_RE = re.compile(r"config-[0-9a-f]{32}\Z")
REV_RE = re.compile(r"r[0-9]{6}\Z")
VALIDATION_RE = re.compile(r"validation-[0-9a-f]{32}\Z")
SHA_RE = re.compile(r"[0-9a-f]{64}\Z")


class PromotionError(Exception):
    """Error controlado de validación/promoción."""


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _unb64(value: Any, label: str, limit: int) -> bytes:
    if not isinstance(value, str):
        raise PromotionError(f"{label}: codificación inválida.")
    try:
        result = base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as exc:
        raise PromotionError(f"{label}: base64 inválido.") from exc
    if len(result) > limit:
        raise PromotionError(f"{label}: excede el límite.")
    return result


def _json_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_catalog_bytes(data: bytes) -> dict[str, Any]:
    obj = validation_store._strict_json(data, "Catálogo de informes")
    if (not isinstance(obj, dict) or set(obj) != {"schema_version", "reports"}
            or type(obj["schema_version"]) is not int
            or obj["schema_version"] != validation_store.VERSION
            or not isinstance(obj["reports"], list)
            or len(obj["reports"]) > validation_store.MAX_REPORTS):
        raise PromotionError("Snapshot de catálogo inválido.")
    seen: set[str] = set()
    for item in obj["reports"]:
        if (not isinstance(item, dict)
                or set(item) != {"validation_id", "config_id", "revision", "stored_at", "report_sha256"}
                or not isinstance(item.get("validation_id"), str)
                or not VALIDATION_RE.fullmatch(item["validation_id"])
                or not isinstance(item.get("config_id"), str)
                or not CONFIG_RE.fullmatch(item["config_id"])
                or not isinstance(item.get("revision"), str)
                or not REV_RE.fullmatch(item["revision"])
                or not isinstance(item.get("stored_at"), str)
                or not isinstance(item.get("report_sha256"), str)
                or not SHA_RE.fullmatch(item["report_sha256"])
                or item["validation_id"] in seen):
            raise PromotionError("Entrada de snapshot de catálogo inválida.")
        seen.add(item["validation_id"])
    return obj


def _validate_report_bytes(data: bytes, config_id: str, revision: str,
                           validation_id: str) -> dict[str, Any]:
    report = validation_store._strict_json(data, "Informe de validación")
    if (not isinstance(report, dict)
            or report.get("validation_id") != validation_id
            or report.get("config_id") != config_id
            or report.get("revision") != revision):
        raise PromotionError("Identidad del informe transaccional incoherente.")
    embedded = report.get("report_sha256")
    check = dict(report)
    check["report_sha256"] = None
    if not isinstance(embedded, str) or _json_hash(validation_store._json_bytes(check)) != embedded:
        raise PromotionError("Hash interno del informe transaccional inválido.")
    if type(report.get("schema_version")) is not int or report.get("schema_version") != validation_store.VERSION:
        raise PromotionError("Versión de informe transaccional inválida.")
    return report


class ValidationPromotionService:
    def __init__(self, config_root: str | os.PathLike[str] | None = None,
                 master_key: str | os.PathLike[str] | None = None,
                 validation_root: str | os.PathLike[str] | None = None):
        self.configs = configurations.ConfigurationStore(config_root, master_key)
        self.reports = validation_store.ValidationReportStore(validation_root)
        self.wal_path = self.reports.root / "promotion.transaction.json"

    def _write_wal(self, journal: dict[str, Any], *, exclusive: bool = False) -> None:
        raw = validation_store._json_bytes(journal)
        if len(raw) > PROMOTION_WAL_LIMIT:
            raise PromotionError("Journal de promoción excede el límite.")
        validation_store._atomic_write(self.wal_path, raw, exclusive=exclusive)

    def _recover_unlocked(self) -> None:
        if not self.wal_path.exists() and not self.wal_path.is_symlink():
            return
        validation_store._check_file(self.wal_path, PROMOTION_WAL_LIMIT)
        journal = validation_store._strict_json(
            validation_store._read(self.wal_path, PROMOTION_WAL_LIMIT), "Journal de promoción"
        )
        fields = {
            "schema_version", "state", "config_id", "revision", "validation_id",
            "report_bytes", "old_catalog", "new_catalog", "old_metadata", "new_metadata",
        }
        if (not isinstance(journal, dict) or set(journal) != fields
                or type(journal["schema_version"]) is not int or journal["schema_version"] != 1
                or not isinstance(journal["state"], str)
                or journal["state"] not in {"prepared", "committed"}
                or not isinstance(journal["config_id"], str) or not CONFIG_RE.fullmatch(journal["config_id"])
                or not isinstance(journal["revision"], str) or not REV_RE.fullmatch(journal["revision"])
                or not isinstance(journal["validation_id"], str) or not VALIDATION_RE.fullmatch(journal["validation_id"])):
            raise PromotionError("Journal de promoción inválido; se conserva para inspección.")

        cid, revision, vid = journal["config_id"], journal["revision"], journal["validation_id"]
        report_bytes = _unb64(journal["report_bytes"], "Informe WAL", validation_store.MAX_REPORT)
        old_catalog_bytes = _unb64(journal["old_catalog"], "Catálogo anterior WAL", 16 * 1024 * 1024)
        new_catalog_bytes = _unb64(journal["new_catalog"], "Catálogo nuevo WAL", 16 * 1024 * 1024)
        old_metadata = _unb64(journal["old_metadata"], "Metadatos anteriores WAL", 4 * 1024 * 1024)
        new_metadata = _unb64(journal["new_metadata"], "Metadatos nuevos WAL", 4 * 1024 * 1024)

        _validate_report_bytes(report_bytes, cid, revision, vid)
        old_catalog = _validate_catalog_bytes(old_catalog_bytes)
        new_catalog = _validate_catalog_bytes(new_catalog_bytes)
        old_meta = configurations.strict_json(old_metadata, "Metadatos anteriores")
        new_meta = configurations.strict_json(new_metadata, "Metadatos nuevos")
        metadata_fields = {
            "schema_version", "config_id", "name", "created_at", "modified_at",
            "current_revision", "last_validated_revision", "validation_status", "config_present",
        }
        for snapshot in (old_meta, new_meta):
            if (not isinstance(snapshot, dict) or set(snapshot) != metadata_fields
                    or type(snapshot.get("schema_version")) is not int or snapshot["schema_version"] != 1
                    or snapshot.get("config_id") != cid
                    or type(snapshot.get("config_present")) is not bool
                    or snapshot["config_present"] != (snapshot.get("current_revision") is not None)
                    or not isinstance(snapshot.get("validation_status"), str)
                    or snapshot.get("validation_status") not in {"not_validated", "valid"}):
                raise PromotionError("Snapshot de metadatos del journal inválido.")
            current = snapshot.get("current_revision")
            last = snapshot.get("last_validated_revision")
            if ((current is not None and (not isinstance(current, str) or not REV_RE.fullmatch(current)))
                    or (last is not None and (not isinstance(last, str) or not REV_RE.fullmatch(last)))
                    or (last is not None and (current is None or int(last[1:]) > int(current[1:])))
                    or (snapshot["validation_status"] == "valid" and (current is None or last != current))
                    or (snapshot["validation_status"] == "not_validated" and last == current and last is not None)):
                raise PromotionError("Estado/revisión incoherente en snapshot de metadatos.")
        if (set(old_meta) != set(new_meta)
                or any(old_meta[key] != new_meta[key] for key in metadata_fields - {
                    "last_validated_revision", "validation_status"
                })):
            raise PromotionError("La transacción intenta alterar metadatos fuera del estado de validación.")

        entry = next((x for x in new_catalog["reports"] if x["validation_id"] == vid), None)
        if (entry is None or entry["config_id"] != cid or entry["revision"] != revision
                or entry["report_sha256"] != _json_hash(report_bytes)
                or len(new_catalog["reports"]) != len(old_catalog["reports"]) + 1
                or new_catalog["reports"][:-1] != old_catalog["reports"]
                or any(x["validation_id"] == vid for x in old_catalog["reports"])):
            raise PromotionError("El catálogo del journal no corresponde a una operación append-only.")
        report_path = self.reports._report_path(vid)
        metadata_path = self.configs.items / cid / "metadata.json"

        if journal["state"] == "prepared":
            if report_path.exists() or report_path.is_symlink():
                existing = validation_store._read(report_path, validation_store.MAX_REPORT)
                if existing != report_bytes:
                    raise PromotionError("Colisión de informe durante rollback; journal conservado.")
                report_path.unlink()
                validation_store._fsync_dir(self.reports.reports)
            validation_store._atomic_write(self.reports.catalog_path, old_catalog_bytes)
            configurations.atomic_write(metadata_path, old_metadata)
        else:
            if report_path.exists() or report_path.is_symlink():
                existing = validation_store._read(report_path, validation_store.MAX_REPORT)
                if existing != report_bytes:
                    raise PromotionError("Colisión de informe durante recuperación; journal conservado.")
            else:
                validation_store._atomic_write(report_path, report_bytes, exclusive=True)
            validation_store._atomic_write(self.reports.catalog_path, new_catalog_bytes)
            configurations.atomic_write(metadata_path, new_metadata)

        self.wal_path.unlink()
        validation_store._fsync_dir(self.reports.root)
        self.reports._verify_catalog_reports(self.reports._catalog())
        self.configs._registered_metadata(cid)

    @staticmethod
    def _promotion_eligible(report: dict[str, Any]) -> bool:
        result = report.get("result")
        if result not in {"PASS", "PASS_WITH_WARNINGS"}:
            return False
        checks = report.get("checks")
        if not isinstance(checks, list):
            raise PromotionError("El motor devolvió un informe sin lista de comprobaciones.")
        by_name = {item.get("name"): item for item in checks if isinstance(item, dict)}
        if len(by_name) != len(checks) or not REQUIRED_CHECKS.issubset(by_name):
            raise PromotionError("Resultado PASS sin todas las comprobaciones obligatorias; no se puede persistir como válido.")
        for name in REQUIRED_CHECKS:
            item = by_name[name]
            if item.get("status") != "PASS" or item.get("errors"):
                raise PromotionError(f"Resultado {result} incoherente con la comprobación obligatoria {name}.")
        compatibility = by_name.get("compatibility")
        if (compatibility is None
                or compatibility.get("status") not in {"PASS", "DEFERRED_TO_NATIVE"}
                or compatibility.get("errors")):
            raise PromotionError("Resultado PASS sin comprobación de compatibilidad delegada o satisfactoria.")
        xray = report.get("xray")
        if (not isinstance(xray, dict)
                or not isinstance(xray.get("version"), str) or not xray["version"]
                or not isinstance(xray.get("binary_sha256"), str)
                or not SHA_RE.fullmatch(xray["binary_sha256"])):
            raise PromotionError("Resultado PASS sin identidad verificable del binario Xray.")
        warnings = any(bool(item.get("warnings")) for item in checks)
        if result == "PASS" and warnings:
            raise PromotionError("Resultado PASS incoherente: el informe contiene advertencias.")
        if result == "PASS_WITH_WARNINGS" and not warnings:
            raise PromotionError("Resultado PASS_WITH_WARNINGS sin advertencias registradas.")
        return True

    def _commit_report_and_state(self, config_id: str, revision: str,
                                 report: dict[str, Any], metadata: dict[str, Any],
                                 promote: bool) -> dict[str, Any]:
        catalog = self.reports._catalog()
        self.reports._verify_catalog_reports(catalog)
        if len(catalog["reports"]) >= validation_store.MAX_REPORTS:
            raise PromotionError("Se alcanzó el límite de informes permanentes.")
        normalized = validation_store._normalize_report(config_id, revision, report)
        vid = normalized["validation_id"]
        normalized["report_sha256"] = _json_hash(validation_store._json_bytes(normalized))
        report_bytes = validation_store._json_bytes(normalized)
        if len(report_bytes) > validation_store.MAX_REPORT:
            raise PromotionError("Informe excede el límite.")
        report_path = self.reports._report_path(vid)
        if report_path.exists() or report_path.is_symlink():
            raise PromotionError("Colisión de ID de informe.")
        report_sha = _json_hash(report_bytes)
        new_catalog = {
            "schema_version": validation_store.VERSION,
            "reports": catalog["reports"] + [{
                "validation_id": vid, "config_id": config_id, "revision": revision,
                "stored_at": normalized["stored_at"], "report_sha256": report_sha,
            }],
        }
        old_catalog_bytes = validation_store._json_bytes(catalog)
        new_catalog_bytes = validation_store._json_bytes(new_catalog)
        if len(new_catalog_bytes) > 16 * 1024 * 1024:
            raise PromotionError("Catálogo de informes excede el límite.")
        metadata_path = self.configs.items / config_id / "metadata.json"
        old_metadata = configurations.read_file(metadata_path, 4 * 1024 * 1024)
        updated = dict(metadata)
        if promote:
            updated["last_validated_revision"] = revision
            updated["validation_status"] = "valid" if revision == metadata["current_revision"] else "not_validated"
        new_metadata = configurations.json_bytes(updated)
        journal = {
            "schema_version": 1, "state": "prepared",
            "config_id": config_id, "revision": revision, "validation_id": vid,
            "report_bytes": _b64(report_bytes),
            "old_catalog": _b64(old_catalog_bytes), "new_catalog": _b64(new_catalog_bytes),
            "old_metadata": _b64(old_metadata), "new_metadata": _b64(new_metadata),
        }
        self._write_wal(journal, exclusive=True)
        try:
            validation_store._atomic_write(report_path, report_bytes, exclusive=True)
            validation_store._atomic_write(self.reports.catalog_path, new_catalog_bytes)
            if promote:
                configurations.atomic_write(metadata_path, new_metadata)
            journal["state"] = "committed"
            self._write_wal(journal)
        except Exception:
            self._recover_unlocked()
            raise
        self._recover_unlocked()
        return {
            "validation_id": vid,
            "config_id": config_id,
            "revision": revision,
            "content_sha256": normalized["content_sha256"],
            "result": normalized["result"],
            "promoted": promote,
            "validation_status": updated["validation_status"],
            "last_validated_revision": updated["last_validated_revision"],
            "report_persisted": True,
        }

    def validate(self, config_id: str, revision: str | None = None,
                 xray_binary: str = "/usr/local/bin/xray", timeout: int = 20) -> dict[str, Any]:
        if not isinstance(config_id, str) or not CONFIG_RE.fullmatch(config_id):
            raise PromotionError("ID de configuración inválido.")
        if revision is not None and (not isinstance(revision, str) or not REV_RE.fullmatch(revision)):
            raise PromotionError("Revisión inválida.")
        with self.configs.locked():
            with self.reports.locked():
                self._recover_unlocked()
                metadata = self.configs._registered_metadata(config_id)
                selected = revision or metadata["current_revision"]
                if selected is None:
                    raise PromotionError("La configuración no contiene una revisión para validar.")
                data, _manifest = self.configs.verify_revision(config_id, selected)
                digest = _json_hash(data)
                report = validator.validate_configuration(data, xray_binary=xray_binary, timeout=timeout)
                if report.get("content_sha256") != digest or report.get("content_size_bytes") != len(data):
                    raise PromotionError("El motor no devolvió la huella/tamaño de los bytes exactos.")
                promote = self._promotion_eligible(report)
                result = self._commit_report_and_state(config_id, selected, report, metadata, promote)
                result["current_revision"] = metadata["current_revision"]
                result["selected_revision_is_current"] = selected == metadata["current_revision"]
                result["configuration_applied"] = False
                result["service_started"] = False
                return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida y promueve configuraciones independientes Xray.")
    parser.add_argument("--config-store", default=None)
    parser.add_argument("--master-key", default=None)
    parser.add_argument("--validation-store", default=None)
    parser.add_argument("--xray-binary", default="/usr/local/bin/xray")
    parser.add_argument("--timeout", type=int, default=20)
    sub = parser.add_subparsers(dest="command", required=True)
    validate_cmd = sub.add_parser("validate")
    validate_cmd.add_argument("--config-id", required=True)
    validate_cmd.add_argument("--revision", default=None)
    args = parser.parse_args()
    try:
        service = ValidationPromotionService(args.config_store, args.master_key, args.validation_store)
        result = service.validate(args.config_id, args.revision, args.xray_binary, args.timeout)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (PromotionError, configurations.ConfigurationError,
            validation_store.ValidationStoreError, validator.ValidationInputError,
            OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
