#!/usr/bin/env python3
"""Almacén append-only de informes permanentes de validación Xray.

No carga claves, no lee configuraciones y no modifica estados de configuración.
"""
from __future__ import annotations

import argparse
import base64
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import secrets
import stat
from pathlib import Path
from typing import Any

DEFAULT_ROOT = "/var/lib/xray-manager/validation"
ID_RE = re.compile(r"validation-[0-9a-f]{32}\Z")
CONFIG_RE = re.compile(r"config-[0-9a-f]{32}\Z")
REV_RE = re.compile(r"r[0-9]{6}\Z")
SHA_RE = re.compile(r"[0-9a-f]{64}\Z")
RESULTS = {"PASS", "PASS_WITH_WARNINGS", "FAIL", "INCOMPLETE"}
CHECK_STATES = {"PASS", "FAIL", "INCOMPLETE", "NOT_RUN", "DEFERRED_TO_NATIVE"}
MAX_REPORT = 2 * 1024 * 1024
MAX_REPORTS = 100000
VERSION = 1


class ValidationStoreError(Exception):
    """Error controlado del almacén."""


def _fail(message: str) -> None:
    raise ValidationStoreError(message)


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _strict_json(data: bytes, label: str) -> Any:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                _fail(f"{label}: clave duplicada")
            result[key] = value
        return result
    try:
        return json.loads(data.decode("utf-8", "strict"), object_pairs_hook=pairs,
                          parse_constant=lambda _v: _fail(f"{label}: constante JSON no permitida"))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        _fail(f"{label}: JSON inválido ({type(exc).__name__})")


def _safe_dir(path: Path, create: bool = False) -> None:
    if not path.is_absolute():
        _fail("La ruta del almacén debe ser absoluta.")
    current = Path("/")
    for part in path.parts[1:]:
        current /= part
        try:
            st = current.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(st.st_mode):
            _fail(f"Componente simbólico no permitido: {current}")
    if create:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        st = path.lstat()
    except FileNotFoundError:
        _fail(f"Falta directorio: {path}")
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != 0 or st.st_gid != 0 or stat.S_IMODE(st.st_mode) != 0o700:
        _fail(f"Directorio inseguro (no se repara automáticamente): {path}")


def _check_file(path: Path, limit: int, required: bool = True):
    try:
        st = path.lstat()
    except FileNotFoundError:
        if required:
            _fail(f"Falta archivo: {path.name}")
        return None
    if (not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_gid != 0
            or st.st_nlink != 1 or stat.S_IMODE(st.st_mode) != 0o600 or st.st_size > limit):
        _fail(f"Archivo inseguro o fuera de límite: {path}")
    return st


def _read(path: Path, limit: int) -> bytes:
    before = _check_file(path, limit)
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0))
    try:
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_uid, before.st_gid, before.st_nlink, before.st_size) != (
            after.st_dev, after.st_ino, after.st_uid, after.st_gid, after.st_nlink, after.st_size
        ):
            _fail("El archivo cambió durante su apertura.")
        chunks = bytearray()
        while True:
            block = os.read(fd, min(1024 * 1024, limit + 1 - len(chunks)))
            if not block:
                break
            chunks.extend(block)
            if len(chunks) > limit:
                _fail("Archivo excede el límite permitido.")
        return bytes(chunks)
    finally:
        os.close(fd)


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _atomic_write(path: Path, data: bytes, *, exclusive: bool = False) -> None:
    _safe_dir(path.parent)
    if exclusive and (path.exists() or path.is_symlink()):
        _fail("Colisión de archivo inmutable.")
    if path.exists() or path.is_symlink():
        _check_file(path, max(len(data), MAX_REPORT, 4 * 1024 * 1024))
    temp = path.parent / f".{path.name}.{secrets.token_hex(8)}.tmp"
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        os.fchown(fd, 0, 0)
        os.fchmod(fd, 0o600)
        view = memoryview(data)
        while view:
            count = os.write(fd, view)
            if count <= 0:
                raise OSError("Escritura incompleta")
            view = view[count:]
        os.fsync(fd)
    except Exception:
        os.close(fd)
        with contextlib.suppress(OSError):
            temp.unlink()
        raise
    else:
        os.close(fd)
    try:
        if exclusive:
            if path.exists() or path.is_symlink():
                _fail("Colisión de archivo inmutable.")
            os.rename(temp, path)
        else:
            os.replace(temp, path)
        _fsync_dir(path.parent)
    finally:
        with contextlib.suppress(FileNotFoundError):
            temp.unlink()


def _sanitize(value: Any, limit: int = 240) -> str:
    text = str(value)
    text = re.sub(r"(?i)(password|passwd|token|secret|private.?key|uuid)(\s*[=:]\s*)[^\s,;]+",
                  r"\1\2[REDACTED]", text)
    text = re.sub(r"(?i)://[^/@\s]+:[^/@\s]+@", "://[REDACTED]@", text)
    return "".join(ch for ch in text if ch.isprintable())[:limit]


def _normalize_report(config_id: str, revision: str, report: dict[str, Any]) -> dict[str, Any]:
    if not CONFIG_RE.fullmatch(config_id) or not REV_RE.fullmatch(revision):
        _fail("Identidad de configuración/revisión inválida.")
    if (not isinstance(report, dict) or type(report.get("schema_version")) is not int
            or report.get("schema_version") != 1):
        _fail("Informe de entrada incompatible.")
    digest = report.get("content_sha256")
    if not isinstance(digest, str) or not SHA_RE.fullmatch(digest):
        _fail("Hash de contenido inválido.")
    if type(report.get("content_size_bytes")) is not int or not 1 <= report["content_size_bytes"] <= 16 * 1024 * 1024:
        _fail("Tamaño de contenido inválido.")
    result = report.get("result")
    if not isinstance(result, str) or result not in RESULTS:
        _fail("Resultado de validación inválido.")
    checks_in = report.get("checks")
    if not isinstance(checks_in, list) or not 1 <= len(checks_in) <= 64:
        _fail("Lista de comprobaciones inválida.")
    checks = []
    names = set()
    for item in checks_in:
        if not isinstance(item, dict) or set(item) - {"name", "status", "errors", "warnings", "details"}:
            _fail("Estructura de comprobación inválida.")
        name, status = item.get("name"), item.get("status")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", name) or name in names:
            _fail("Nombre de comprobación inválido o duplicado.")
        if not isinstance(status, str) or status not in CHECK_STATES:
            _fail("Estado de comprobación inválido.")
        names.add(name)
        normalized = {"name": name, "status": status}
        for field in ("errors", "warnings"):
            values = item.get(field, [])
            if not isinstance(values, list) or len(values) > 64:
                _fail("Diagnósticos de comprobación inválidos.")
            normalized[field] = [_sanitize(v) for v in values]
        details = item.get("details", {})
        if not isinstance(details, dict) or len(details) > 32:
            _fail("Detalles de comprobación inválidos.")
        normalized["details"] = {str(k)[:64]: _sanitize(v) for k, v in details.items()
                                 if isinstance(k, str) and isinstance(v, (str, int, float, bool))}
        checks.append(normalized)
    xray_in = report.get("xray", {})
    if not isinstance(xray_in, dict):
        _fail("Metadatos Xray inválidos.")
    xray = {}
    if "version" in xray_in:
        xray["version"] = _sanitize(xray_in["version"], 160)
    if "binary_sha256" in xray_in:
        if not isinstance(xray_in["binary_sha256"], str) or not SHA_RE.fullmatch(xray_in["binary_sha256"]):
            _fail("Hash del binario Xray inválido.")
        xray["binary_sha256"] = xray_in["binary_sha256"]
    created_at = report.get("created_at")
    if not isinstance(created_at, str) or len(created_at) > 40:
        _fail("Fecha de validación inválida.")
    return {
        "schema_version": VERSION,
        "validation_id": "validation-" + secrets.token_hex(16),
        "config_id": config_id,
        "revision": revision,
        "content_sha256": digest,
        "content_size_bytes": report["content_size_bytes"],
        "validator_version": "C-05A/v1",
        "validation_type": "static_and_native",
        "xray_version": xray.get("version"),
        "xray_binary_sha256": xray.get("binary_sha256"),
        "created_at": created_at,
        "stored_at": _now(),
        "result": result,
        "checks": checks,
        "report_sha256": None,
    }


class ValidationReportStore:
    def __init__(self, root: str | os.PathLike[str] | None = None):
        self.root = Path(root or os.environ.get("XRAY_MANAGER_VALIDATION_DIR", DEFAULT_ROOT)).absolute()
        self.reports = self.root / "reports"
        self.catalog_path = self.root / "catalog.json"
        self.lock_path = self.root / "validation.lock"
        self.wal_path = self.root / "transaction.json"

    def prepare(self) -> None:
        if os.geteuid() != 0:
            _fail("El almacén requiere ejecución como root.")
        _safe_dir(self.root, create=True)
        _safe_dir(self.reports, create=True)
        if not self.lock_path.exists() and not self.lock_path.is_symlink():
            fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
            os.fchown(fd, 0, 0); os.fchmod(fd, 0o600); os.fsync(fd); os.close(fd); _fsync_dir(self.root)
        _check_file(self.lock_path, 0)
        _check_file(self.catalog_path, 16 * 1024 * 1024, required=False)
        _check_file(self.wal_path, 8 * 1024 * 1024, required=False)

    @contextlib.contextmanager
    def locked(self):
        self.prepare()
        fd = os.open(self.lock_path, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_gid != 0 or st.st_nlink != 1 or stat.S_IMODE(st.st_mode) != 0o600:
                _fail("Lock inseguro.")
            fcntl.flock(fd, fcntl.LOCK_EX)
            self.recover()
            yield
        finally:
            with contextlib.suppress(OSError):
                fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def _catalog(self) -> dict[str, Any]:
        if not self.catalog_path.exists():
            return {"schema_version": VERSION, "reports": []}
        catalog = _strict_json(_read(self.catalog_path, 16 * 1024 * 1024), "Catálogo")
        if (not isinstance(catalog, dict) or set(catalog) != {"schema_version", "reports"}
                or type(catalog["schema_version"]) is not int or catalog["schema_version"] != VERSION
                or not isinstance(catalog["reports"], list) or len(catalog["reports"]) > MAX_REPORTS):
            _fail("Catálogo inválido; se conserva para inspección.")
        seen = set()
        for item in catalog["reports"]:
            if (not isinstance(item, dict) or set(item) != {"validation_id", "config_id", "revision", "stored_at", "report_sha256"}
                    or not isinstance(item["validation_id"], str) or not ID_RE.fullmatch(item["validation_id"])
                    or not isinstance(item["config_id"], str) or not CONFIG_RE.fullmatch(item["config_id"])
                    or not isinstance(item["revision"], str) or not REV_RE.fullmatch(item["revision"])
                    or not isinstance(item["report_sha256"], str) or not SHA_RE.fullmatch(item["report_sha256"])
                    or item["validation_id"] in seen):
                _fail("Entrada de catálogo inválida.")
            seen.add(item["validation_id"])
        return catalog

    def _report_path(self, validation_id: str) -> Path:
        if not ID_RE.fullmatch(validation_id):
            _fail("ID de informe inválido.")
        return self.reports / f"{validation_id}.json"

    def _verify_catalog_reports(self, catalog: dict[str, Any]) -> None:
        expected = {f"{item['validation_id']}.json" for item in catalog["reports"]}
        actual = {p.name for p in self.reports.iterdir()}
        if actual != expected:
            _fail("El directorio de informes contiene archivos ausentes o inesperados.")
        for item in catalog["reports"]:
            path = self._report_path(item["validation_id"])
            raw = _read(path, MAX_REPORT)
            if hashlib.sha256(raw).hexdigest() != item["report_sha256"]:
                _fail("La integridad de un informe no coincide con el catálogo.")
            report = _strict_json(raw, "Informe")
            if (not isinstance(report, dict) or report.get("validation_id") != item["validation_id"]
                    or report.get("config_id") != item["config_id"] or report.get("revision") != item["revision"]):
                _fail("La identidad del informe no coincide con el catálogo.")
            embedded_hash = report.get("report_sha256")
            report["report_sha256"] = None
            if not isinstance(embedded_hash, str) or hashlib.sha256(_json_bytes(report)).hexdigest() != embedded_hash:
                _fail("La huella interna del informe no coincide.")

    def _write_catalog(self, catalog: dict[str, Any]) -> bytes:
        data = _json_bytes(catalog)
        if len(data) > 16 * 1024 * 1024:
            _fail("Catálogo excede el límite.")
        _atomic_write(self.catalog_path, data)
        return data

    def recover(self) -> None:
        if not self.wal_path.exists() and not self.wal_path.is_symlink():
            return
        wal = _strict_json(_read(self.wal_path, 8 * 1024 * 1024), "Journal")
        fields = {"schema_version", "state", "report_path", "report_bytes", "old_catalog", "new_catalog"}
        if (not isinstance(wal, dict) or set(wal) != fields or type(wal["schema_version"]) is not int
                or wal["schema_version"] != VERSION or not isinstance(wal["state"], str)
                or wal["state"] not in {"prepared", "committed"}
                or not isinstance(wal["report_path"], str)
                or not re.fullmatch(r"reports/validation-[0-9a-f]{32}\.json", wal["report_path"])):
            _fail("Journal inválido; se conserva para inspección.")
        try:
            report_bytes = base64.b64decode(wal["report_bytes"], validate=True)
            old_catalog = base64.b64decode(wal["old_catalog"], validate=True)
            new_catalog = base64.b64decode(wal["new_catalog"], validate=True)
        except (TypeError, ValueError):
            _fail("Snapshots del journal inválidos.")
        if len(report_bytes) > MAX_REPORT or len(old_catalog) > 16*1024*1024 or len(new_catalog) > 16*1024*1024:
            _fail("Journal excede límites.")
        report_path = self.root / wal["report_path"]
        report_id = Path(wal["report_path"]).stem
        if not ID_RE.fullmatch(report_id):
            _fail("ID de informe del journal inválido.")
        wal_report = _strict_json(report_bytes, "Informe WAL")
        old_obj = _strict_json(old_catalog, "Catálogo anterior WAL")
        new_obj = _strict_json(new_catalog, "Catálogo nuevo WAL")
        for candidate in (old_obj, new_obj):
            if (not isinstance(candidate, dict) or set(candidate) != {"schema_version", "reports"}
                    or type(candidate.get("schema_version")) is not int or candidate["schema_version"] != VERSION
                    or not isinstance(candidate.get("reports"), list) or len(candidate["reports"]) > MAX_REPORTS):
                _fail("Catálogo del journal inválido; se conserva para inspección.")
        if not isinstance(wal_report, dict) or wal_report.get("validation_id") != report_id:
            _fail("Identidad del informe WAL inválida.")
        if wal["state"] == "prepared":
            if any(isinstance(x, dict) and x.get("validation_id") == report_id for x in old_obj["reports"]):
                _fail("El catálogo anterior ya contiene el informe del journal.")
            if report_path.exists() or report_path.is_symlink():
                _check_file(report_path, MAX_REPORT)
                report_path.unlink()
                _fsync_dir(self.reports)
            _atomic_write(self.catalog_path, old_catalog)
        else:
            committed_catalog = _strict_json(new_catalog, "Catálogo nuevo WAL")
            entry = next((x for x in committed_catalog.get("reports", [])
                          if isinstance(x, dict) and x.get("validation_id") == report_id), None)
            if (entry is None or entry.get("report_sha256") != hashlib.sha256(report_bytes).hexdigest()
                    or wal_report.get("config_id") != entry.get("config_id")
                    or wal_report.get("revision") != entry.get("revision")):
                _fail("El commit WAL no vincula la identidad y el hash exactos del informe.")
            if report_path.exists() or report_path.is_symlink():
                if _read(report_path, MAX_REPORT) != report_bytes:
                    _fail("Colisión con informe distinto durante recuperación.")
            else:
                _atomic_write(report_path, report_bytes, exclusive=True)
            _atomic_write(self.catalog_path, new_catalog)
        self.wal_path.unlink()
        _fsync_dir(self.root)

    def save_report(self, config_id: str, revision: str, report: dict[str, Any]) -> dict[str, Any]:
        with self.locked():
            catalog = self._catalog()
            if len(catalog["reports"]) >= MAX_REPORTS:
                _fail("Se alcanzó el límite de informes.")
            self._verify_catalog_reports(catalog)
            normalized = _normalize_report(config_id, revision, report)
            validation_id = normalized["validation_id"]
            path = self._report_path(validation_id)
            report_without_hash = _json_bytes(normalized)
            normalized["report_sha256"] = hashlib.sha256(report_without_hash).hexdigest()
            report_bytes = _json_bytes(normalized)
            if len(report_bytes) > MAX_REPORT:
                _fail("Informe excede el límite.")
            report_sha = hashlib.sha256(report_bytes).hexdigest()
            new_catalog = {"schema_version": VERSION, "reports": catalog["reports"] + [{
                "validation_id": validation_id, "config_id": config_id, "revision": revision,
                "stored_at": normalized["stored_at"], "report_sha256": report_sha,
            }]}
            old_bytes, new_bytes = _json_bytes(catalog), _json_bytes(new_catalog)
            wal = {
                "schema_version": VERSION, "state": "prepared",
                "report_path": f"reports/{path.name}",
                "report_bytes": base64.b64encode(report_bytes).decode("ascii"),
                "old_catalog": base64.b64encode(old_bytes).decode("ascii"),
                "new_catalog": base64.b64encode(new_bytes).decode("ascii"),
            }
            _atomic_write(self.wal_path, _json_bytes(wal), exclusive=True)
            _atomic_write(path, report_bytes, exclusive=True)
            _atomic_write(self.catalog_path, new_bytes)
            wal["state"] = "committed"
            _atomic_write(self.wal_path, _json_bytes(wal))
            self.wal_path.unlink()
            _fsync_dir(self.root)
            return normalized

    def get_report(self, validation_id: str) -> dict[str, Any]:
        with self.locked():
            catalog = self._catalog()
            self._verify_catalog_reports(catalog)
            item = next((x for x in catalog["reports"] if x["validation_id"] == validation_id), None)
            if item is None:
                _fail("Informe no encontrado.")
            return _strict_json(_read(self._report_path(validation_id), MAX_REPORT), "Informe")

    def list_reports(self) -> list[dict[str, Any]]:
        with self.locked():
            catalog = self._catalog()
            self._verify_catalog_reports(catalog)
            return list(catalog["reports"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Almacén de informes de validación Xray")
    parser.add_argument("--root", default=None)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    get = sub.add_parser("show")
    get.add_argument("--validation-id", required=True)
    args = parser.parse_args()
    store = ValidationReportStore(args.root)
    try:
        if args.command == "list":
            print(json.dumps(store.list_reports(), ensure_ascii=False, indent=2))
        else:
            print(json.dumps(store.get_report(args.validation_id), ensure_ascii=False, indent=2))
        return 0
    except (ValidationStoreError, OSError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
