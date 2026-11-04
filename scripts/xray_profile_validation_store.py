#!/usr/bin/env python3
"""Historial transaccional de validaciones estáticas ligadas a profile_id + revision."""
from __future__ import annotations

import base64
import contextlib
import fcntl
import hashlib
import json
import os
import re
import secrets
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_ROOT = "/var/lib/xray-manager/profile-validations"
PROFILE_RE = re.compile(r"profile-[0-9a-f]{32}\Z")
REVISION_RE = re.compile(r"r[0-9]{6}\Z")
VALIDATION_RE = re.compile(r"pvalidation-[0-9a-f]{32}\Z")
SHA_RE = re.compile(r"[0-9a-f]{64}\Z")
NAME_RE = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")
MAX_REPORT = 1024 * 1024
MAX_REPORTS = 10000
MAX_CONTENT = 16 * 1024 * 1024


class ProfileValidationError(Exception):
    pass


def _fail(message: str) -> None:
    raise ProfileValidationError(message)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def _strict_json(data: bytes, label: str) -> Any:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("clave duplicada")
            result[key] = value
        return result
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError("constante no finita")))
    except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
        _fail(f"{label} no contiene JSON estricto válido.")


def _check_no_symlink_components(path: Path) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode):
            _fail("Componente simbólico no permitido en el historial de perfiles.")


def _check_path(path: Path, expected: str, mode: int) -> None:
    try:
        st = path.lstat()
    except FileNotFoundError:
        _fail(f"No existe el recurso requerido: {path.name}.")
    if expected == "dir":
        valid = stat.S_ISDIR(st.st_mode) and st.st_uid == 0 and st.st_gid == 0 and stat.S_IMODE(st.st_mode) == mode
    else:
        valid = stat.S_ISREG(st.st_mode) and st.st_uid == 0 and st.st_gid == 0 and st.st_nlink == 1 and stat.S_IMODE(st.st_mode) == mode
    if not valid:
        _fail(f"Recurso con tipo, propietario o permisos inseguros: {path.name}.")


def _read_regular(path: Path, limit: int) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        _fail("No se pudo abrir un archivo del historial de validación.")
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_gid != 0 or st.st_nlink != 1 or stat.S_IMODE(st.st_mode) != 0o600:
            _fail("Archivo inseguro en el historial de validación.")
        if st.st_size > limit:
            _fail("Archivo del historial excede el límite.")
        chunks = []
        remaining = limit + 1
        while remaining:
            part = os.read(fd, min(1024 * 1024, remaining))
            if not part:
                break
            chunks.append(part)
            remaining -= len(part)
        data = b"".join(chunks)
        if len(data) != st.st_size or len(data) > limit:
            _fail("El archivo del historial cambió durante su lectura.")
        return data
    finally:
        os.close(fd)


def _atomic_write(path: Path, data: bytes, exclusive: bool = False) -> None:
    if path.exists() or path.is_symlink():
        _check_path(path, "file", 0o600)
        if exclusive:
            _fail("Colisión de archivo en el historial de validación.")
    temp = path.parent / (".tmp-" + secrets.token_hex(16))
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        os.fchown(fd, 0, 0)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(fd)
        if exclusive:
            os.link(temp, path, follow_symlinks=False)
            temp.unlink()
        else:
            os.replace(temp, path)
        dfd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        with contextlib.suppress(FileNotFoundError):
            temp.unlink()
        with contextlib.suppress(OSError):
            os.close(fd)


def _sanitize(value: Any, limit: int = 240) -> str:
    value = str(value)
    value = re.sub(r"(?i)(password|passwd|token|secret|private.?key|uuid)(\s*[=:]\s*)[^\s,;]+",
                   r"\1\2[REDACTED]", value)
    value = re.sub(r"(?i)://[^/@\s]+:[^/@\s]+@", "://[REDACTED]@", value)
    return "".join(ch for ch in value if ch.isprintable())[:limit]


class ProfileValidationReportStore:
    def __init__(self, root: str | os.PathLike[str] | None = None):
        self.root = Path(root or os.environ.get("XRAY_MANAGER_PROFILE_VALIDATIONS_DIR", DEFAULT_ROOT)).absolute()
        self.reports = self.root / "reports"
        self.catalog = self.root / "catalog.json"
        self.lock = self.root / ".lock"
        self.wal = self.root / "transaction.json"

    def prepare(self) -> None:
        if os.geteuid() != 0:
            _fail("El historial de validación de perfiles requiere root.")
        _check_no_symlink_components(self.root)
        for path in (self.root, self.reports):
            _check_no_symlink_components(path)
            path.mkdir(mode=0o700, parents=True, exist_ok=True)
            _check_path(path, "dir", 0o700)
        if not self.lock.exists() and not self.lock.is_symlink():
            fd = os.open(self.lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
            try:
                os.fchown(fd, 0, 0)
                os.fchmod(fd, 0o600)
                os.fsync(fd)
            finally:
                os.close(fd)
        _check_path(self.lock, "file", 0o600)
        if self.catalog.exists() or self.catalog.is_symlink():
            _check_path(self.catalog, "file", 0o600)
        if self.wal.exists() or self.wal.is_symlink():
            _check_path(self.wal, "file", 0o600)

    @contextlib.contextmanager
    def locked(self):
        self.prepare()
        fd = os.open(self.lock, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
        try:
            _check_fd = os.fstat(fd)
            if not stat.S_ISREG(_check_fd.st_mode) or _check_fd.st_uid != 0 or _check_fd.st_gid != 0 or _check_fd.st_nlink != 1 or stat.S_IMODE(_check_fd.st_mode) != 0o600:
                _fail("Lock del historial de validación inseguro.")
            fcntl.flock(fd, fcntl.LOCK_EX)
            self._recover()
            yield
        finally:
            with contextlib.suppress(OSError):
                fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)


    @contextlib.contextmanager
    def read_only_locked(self):
        """Bloqueo de lectura que nunca crea, corrige, limpia ni recupera archivos."""
        if os.geteuid() != 0:
            _fail("La consulta de validación de perfiles requiere root.")
        _check_no_symlink_components(self.root)
        for path, expected, mode in ((self.root, "dir", 0o700),
                                     (self.reports, "dir", 0o700),
                                     (self.lock, "file", 0o600)):
            _check_path(path, expected, mode)
        if self.wal.exists() or self.wal.is_symlink():
            _fail("Hay una transacción de validación pendiente; la consulta read-only no la recupera.")
        fd = os.open(self.lock, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_gid != 0 or st.st_nlink != 1 or stat.S_IMODE(st.st_mode) != 0o600:
                _fail("Lock de solo lectura inseguro.")
            fcntl.flock(fd, fcntl.LOCK_SH)
            if self.wal.exists() or self.wal.is_symlink():
                _fail("Hay una transacción de validación pendiente; la consulta read-only no la recupera.")
            yield
        finally:
            with contextlib.suppress(OSError):
                fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def _recover(self) -> None:
        if not self.wal.exists():
            return
        wal = _strict_json(_read_regular(self.wal, 8 * 1024 * 1024), "Journal")
        fields = {"schema_version", "state", "validation_id", "report_bytes", "old_catalog", "new_catalog"}
        if (not isinstance(wal, dict) or set(wal) != fields or type(wal["schema_version"]) is not int
                or wal["schema_version"] != 1 or not isinstance(wal["state"], str) or wal["state"] not in {"prepared", "committed"}
                or not isinstance(wal["validation_id"], str) or not VALIDATION_RE.fullmatch(wal["validation_id"])):
            _fail("Journal de validación inválido; se conserva para inspección.")
        try:
            report_raw = base64.b64decode(wal["report_bytes"], validate=True)
            old_raw = base64.b64decode(wal["old_catalog"], validate=True)
            new_raw = base64.b64decode(wal["new_catalog"], validate=True)
        except (ValueError, TypeError):
            _fail("Snapshots del journal inválidos.")
        if len(report_raw) > MAX_REPORT or len(old_raw) > 8 * 1024 * 1024 or len(new_raw) > 8 * 1024 * 1024:
            _fail("Journal de validación excede límites.")
        report = _strict_json(report_raw, "Informe del journal")
        if not isinstance(report, dict) or report.get("validation_id") != wal["validation_id"]:
            _fail("Identidad del informe WAL inválida.")
        old_catalog = _strict_json(old_raw, "Catálogo anterior WAL")
        new_catalog = _strict_json(new_raw, "Catálogo nuevo WAL")
        for candidate in (old_catalog, new_catalog):
            if (not isinstance(candidate, dict) or set(candidate) != {"schema_version", "reports"}
                    or type(candidate["schema_version"]) is not int or candidate["schema_version"] != 1
                    or not isinstance(candidate["reports"], list)):
                _fail("Snapshot de catálogo WAL inválido.")
        path = self._report_path(wal["validation_id"])
        if wal["state"] == "prepared":
            if path.exists() or path.is_symlink():
                existing = _read_regular(path, MAX_REPORT)
                if existing != report_raw:
                    _fail("Colisión de informe durante rollback del journal.")
                path.unlink()
                dfd = os.open(self.reports, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
                try:
                    os.fsync(dfd)
                finally:
                    os.close(dfd)
            _atomic_write(self.catalog, old_raw)
        else:
            entry = next((x for x in new_catalog["reports"] if isinstance(x, dict)
                          and x.get("validation_id") == wal["validation_id"]), None)
            if (entry is None or entry.get("report_sha256") != hashlib.sha256(report_raw).hexdigest()
                    or entry.get("profile_id") != report.get("profile_id")
                    or entry.get("revision") != report.get("revision")):
                _fail("Commit WAL no vincula la identidad y el hash del informe.")
            if path.exists() or path.is_symlink():
                if _read_regular(path, MAX_REPORT) != report_raw:
                    _fail("Colisión de informe durante recuperación.")
            else:
                _atomic_write(path, report_raw, exclusive=True)
            _atomic_write(self.catalog, new_raw)
        self.wal.unlink()
        dfd = os.open(self.root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)

    def _load_catalog(self) -> dict:
        if not self.catalog.exists():
            return {"schema_version": 1, "reports": []}
        value = _strict_json(_read_regular(self.catalog, 8 * 1024 * 1024), "Catálogo")
        if not isinstance(value, dict) or set(value) != {"schema_version", "reports"} or type(value["schema_version"]) is not int or value["schema_version"] != 1 or not isinstance(value["reports"], list) or len(value["reports"]) > MAX_REPORTS:
            _fail("Catálogo de validaciones de perfiles inválido.")
        seen = set()
        for item in value["reports"]:
            if (not isinstance(item, dict) or set(item) != {"validation_id", "profile_id", "revision", "stored_at", "report_sha256"}
                    or not isinstance(item["validation_id"], str) or not VALIDATION_RE.fullmatch(item["validation_id"])
                    or not isinstance(item["profile_id"], str) or not PROFILE_RE.fullmatch(item["profile_id"])
                    or not isinstance(item["revision"], str) or not REVISION_RE.fullmatch(item["revision"])
                    or not isinstance(item["stored_at"], str) or not isinstance(item["report_sha256"], str) or not SHA_RE.fullmatch(item["report_sha256"])
                    or item["validation_id"] in seen):
                _fail("Entrada de catálogo de validaciones inválida.")
            seen.add(item["validation_id"])
        return value

    def _report_path(self, validation_id: str) -> Path:
        if not VALIDATION_RE.fullmatch(validation_id):
            _fail("ID de informe inválido.")
        return self.reports / (validation_id + ".json")

    def _verify_all(self, catalog: dict) -> list[dict]:
        expected = {x["validation_id"] + ".json" for x in catalog["reports"]}
        actual = {x.name for x in self.reports.iterdir()}
        if actual != expected:
            _fail("El directorio de informes tiene archivos ausentes o inesperados.")
        result = []
        for item in catalog["reports"]:
            raw = _read_regular(self._report_path(item["validation_id"]), MAX_REPORT)
            if hashlib.sha256(raw).hexdigest() != item["report_sha256"]:
                _fail("Hash de catálogo incorrecto para un informe de perfil.")
            report = _strict_json(raw, "Informe")
            if (not isinstance(report, dict) or report.get("validation_id") != item["validation_id"]
                    or report.get("profile_id") != item["profile_id"] or report.get("revision") != item["revision"]):
                _fail("La identidad del informe no coincide con el catálogo.")
            embedded = dict(report)
            embedded["report_sha256"] = None
            if hashlib.sha256(_json_bytes(embedded)).hexdigest() != report["report_sha256"]:
                _fail("Hash interno del informe de perfil incorrecto.")
            result.append(report)
        return result

    def save_report(self, profile_id: str, revision: str, report: dict[str, Any]) -> dict:
        if not PROFILE_RE.fullmatch(profile_id) or not REVISION_RE.fullmatch(revision):
            _fail("Identidad de perfil/revisión inválida.")
        if not isinstance(report, dict) or type(report.get("schema_version")) is not int or report["schema_version"] != 1:
            _fail("Informe de entrada incompatible.")
        digest = report.get("content_sha256")
        size = report.get("content_size_bytes")
        if not isinstance(digest, str) or not SHA_RE.fullmatch(digest) or type(size) is not int or not 1 <= size <= MAX_CONTENT:
            _fail("Hash/tamaño de contenido inválido.")
        result = report.get("result")
        if not isinstance(result, str) or result not in {"PASS", "PASS_WITH_WARNINGS", "FAIL", "INCOMPLETE"}:
            _fail("Resultado de validación inválido.")
        checks_in = report.get("checks")
        if not isinstance(checks_in, list) or not 1 <= len(checks_in) <= 64:
            _fail("Lista de comprobaciones inválida.")
        checks, names = [], set()
        for item in checks_in:
            if not isinstance(item, dict) or set(item) - {"name", "status", "errors", "warnings", "details"}:
                _fail("Comprobación de informe inválida.")
            name, status = item.get("name"), item.get("status")
            if (not isinstance(name, str) or not NAME_RE.fullmatch(name) or name in names
                    or not isinstance(status, str) or status not in {"PASS", "FAIL", "INCOMPLETE", "DEFERRED_TO_NATIVE", "NOT_RUN"}):
                _fail("Nombre/estado de comprobación inválido.")
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
        created = report.get("created_at")
        if not isinstance(created, str) or len(created) > 40:
            _fail("Fecha del informe inválida.")
        try:
            parsed_created = datetime.fromisoformat(created.replace("Z", "+00:00"))
            if parsed_created.tzinfo is None or parsed_created.utcoffset() is None:
                raise ValueError("timezone missing")
        except ValueError:
            _fail("Fecha del informe debe incluir zona horaria ISO-8601.")
        normalized = {
            "schema_version": 1,
            "validation_id": "pvalidation-" + secrets.token_hex(16),
            "profile_id": profile_id,
            "revision": revision,
            "content_sha256": digest,
            "content_size_bytes": size,
            "validator_version": _sanitize(report.get("validator_version", "R-01/v1"), 80),
            "created_at": created,
            "stored_at": _now(),
            "result": result,
            "checks": checks,
            "xray": xray,
            "report_sha256": None,
        }
        with self.locked():
            catalog = self._load_catalog()
            if len(catalog["reports"]) >= MAX_REPORTS:
                _fail("Se alcanzó el límite de informes.")
            self._verify_all(catalog)
            raw0 = _json_bytes(normalized)
            normalized["report_sha256"] = hashlib.sha256(raw0).hexdigest()
            raw = _json_bytes(normalized)
            if len(raw) > MAX_REPORT:
                _fail("Informe demasiado grande.")
            entry = {"validation_id": normalized["validation_id"], "profile_id": profile_id,
                     "revision": revision, "stored_at": normalized["stored_at"],
                     "report_sha256": hashlib.sha256(raw).hexdigest()}
            path = self._report_path(normalized["validation_id"])
            old_catalog_raw = _json_bytes(catalog)
            catalog["reports"].append(entry)
            new_catalog_raw = _json_bytes(catalog)
            wal_value = {
                "schema_version": 1,
                "state": "prepared",
                "validation_id": normalized["validation_id"],
                "report_bytes": base64.b64encode(raw).decode("ascii"),
                "old_catalog": base64.b64encode(old_catalog_raw).decode("ascii"),
                "new_catalog": base64.b64encode(new_catalog_raw).decode("ascii"),
            }
            _atomic_write(self.wal, _json_bytes(wal_value), exclusive=True)
            _atomic_write(path, raw, exclusive=True)
            _atomic_write(self.catalog, new_catalog_raw)
            wal_value["state"] = "committed"
            _atomic_write(self.wal, _json_bytes(wal_value))
            self.wal.unlink()
        return normalized

    def get_report(self, validation_id: str) -> dict:
        with self.locked():
            catalog = self._load_catalog()
            reports = self._verify_all(catalog)
            for report in reports:
                if report["validation_id"] == validation_id:
                    return report
            _fail("Informe no encontrado.")

    def latest_for_revision(self, profile_id: str, revision: str) -> dict:
        if not PROFILE_RE.fullmatch(profile_id) or not REVISION_RE.fullmatch(revision):
            _fail("Identidad de perfil/revisión inválida.")
        with self.read_only_locked():
            catalog = self._load_catalog()
            reports = self._verify_all(catalog)
            matches = [x for x in reports if x["profile_id"] == profile_id and x["revision"] == revision]
            if not matches:
                _fail("No existe informe persistido para el perfil y revisión seleccionados.")
            return matches[-1]

    def list_reports(self) -> list[dict]:
        with self.locked():
            catalog = self._load_catalog()
            reports = self._verify_all(catalog)
            return [{"validation_id": x["validation_id"], "profile_id": x["profile_id"],
                     "revision": x["revision"], "stored_at": x["stored_at"],
                     "result": x["result"], "content_sha256": x["content_sha256"]}
                    for x in reports]
