#!/usr/bin/env python3
"""Registro activo de perfiles para runtime aislado B4; no consulta servicios reales."""
from __future__ import annotations

import contextlib
import fcntl
import json
import os
import re
import secrets
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MARKER = ".xray-manager-b4-active-fixture"
ACTIVE_FILE = "active-profile.json"
LOCK_FILE = "active-profile.lock"
PROFILE_RE = re.compile(r"profile-[0-9a-f]{32}\Z")
REVISION_RE = re.compile(r"r[0-9]{6}\Z")
VALIDATION_RE = re.compile(r"pvalidation-[0-9a-f]{32}\Z")
OPERATION_RE = re.compile(r"runtime-op-[0-9a-f]{32}\Z")
GENERATION_RE = re.compile(r"generation-[0-9a-f]{32}\Z")
SHA_RE = re.compile(r"[0-9a-f]{64}\Z")
MAX_BYTES = 65536


class ActiveProfileError(Exception):
    pass


def _fail(message: str) -> None:
    raise ActiveProfileError(message)


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def _check_components(path: Path) -> None:
    if not path.is_absolute():
        _fail("La ruta del registro activo debe ser absoluta.")
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode):
            _fail("No se permiten enlaces simbólicos en el registro activo B4.")


def _check_dir(path: Path) -> None:
    st = path.lstat()
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != 0 or st.st_gid != 0 or stat.S_IMODE(st.st_mode) != 0o700:
        _fail("Directorio del registro activo debe ser root:root 0700.")


def _read_regular(path: Path, limit: int = MAX_BYTES) -> bytes:
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0))
    except OSError:
        _fail("No se pudo abrir un archivo regular del registro activo B4.")
    try:
        st = os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_gid != 0
                or st.st_nlink != 1 or stat.S_IMODE(st.st_mode) != 0o600 or st.st_size > limit):
            _fail("Archivo inseguro o excesivo en el registro activo B4.")
        chunks = []
        remaining = limit + 1
        while remaining:
            part = os.read(fd, min(65536, remaining))
            if not part:
                break
            chunks.append(part)
            remaining -= len(part)
        data = b"".join(chunks)
        if len(data) != st.st_size or len(data) > limit:
            _fail("El registro activo cambió durante su lectura.")
        return data
    finally:
        os.close(fd)


def _strict_json(data: bytes) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("clave duplicada")
            result[key] = value
        return result
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError("constante no finita")))
    except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
        _fail("JSON inválido en el registro activo B4.")
    if not isinstance(value, dict):
        _fail("El registro activo B4 debe ser un objeto JSON.")
    return value


def _validate_record(value: dict) -> dict:
    fields = {"schema_version", "profile_id", "revision", "validation_id", "generation_id",
              "config_sha256", "operation_id", "applied_at", "service_unit", "service_state",
              "config_target"}
    if set(value) != fields or type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        _fail("Esquema del registro activo B4 no reconocido.")
    patterns = (("profile_id", PROFILE_RE), ("revision", REVISION_RE),
                ("validation_id", VALIDATION_RE), ("generation_id", GENERATION_RE),
                ("config_sha256", SHA_RE), ("operation_id", OPERATION_RE))
    for field, pattern in patterns:
        if not isinstance(value.get(field), str) or not pattern.fullmatch(value[field]):
            _fail(f"Identificador inválido en registro activo: {field}.")
    if value["service_unit"] != "xray.service" or value["service_state"] != "active":
        _fail("El registro activo solo admite xray.service verificado como active.")
    if value["config_target"] != "etc/xray/config.json":
        _fail("Destino de configuración no permitido en el registro activo.")
    try:
        if not isinstance(value["applied_at"], str):
            raise ValueError("timestamp type")
        parsed = datetime.fromisoformat(value["applied_at"].replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        _fail("Fecha de aplicación inválida en registro activo.")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _fail("La fecha del registro activo debe incluir zona horaria.")
    return value


class ActiveProfileStore:
    """Almacén fixture-only root:root 0700; el caller aporta evidencia del adaptador simulado."""

    def __init__(self, root: str | os.PathLike[str]):
        self.root = Path(root).absolute()
        self.marker = self.root / MARKER
        self.active_file = self.root / ACTIVE_FILE
        self.lock_file = self.root / LOCK_FILE

    def prepare(self) -> None:
        if os.geteuid() != 0:
            _fail("El registro activo B4 fixture requiere root.")
        _check_components(self.root)
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        _check_dir(self.root)
        if not self.marker.exists() and not self.marker.is_symlink():
            fd = os.open(self.marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
            try:
                os.fchown(fd, 0, 0)
                os.fchmod(fd, 0o600)
                os.write(fd, _json_bytes({"schema_version": 1, "purpose": "xray-manager-b4-active-fixture"}))
                os.fsync(fd)
            finally:
                os.close(fd)
        marker = _strict_json(_read_regular(self.marker))
        if marker != {"schema_version": 1, "purpose": "xray-manager-b4-active-fixture"}:
            _fail("Marcador fixture B4 inválido.")
        if not self.lock_file.exists() and not self.lock_file.is_symlink():
            fd = os.open(self.lock_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
            try:
                os.fchown(fd, 0, 0)
                os.fchmod(fd, 0o600)
                os.fsync(fd)
            finally:
                os.close(fd)
        _read_regular(self.lock_file, 4096)
        if self.active_file.exists() or self.active_file.is_symlink():
            _validate_record(_strict_json(_read_regular(self.active_file)))

    @contextlib.contextmanager
    def locked(self):
        self.prepare()
        fd = os.open(self.lock_file, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0))
        try:
            st = os.fstat(fd)
            if (not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_gid != 0
                    or st.st_nlink != 1 or stat.S_IMODE(st.st_mode) != 0o600):
                _fail("Lock inseguro en el registro activo B4.")
            fcntl.flock(fd, fcntl.LOCK_EX)
            current = self.lock_file.lstat()
            if (current.st_dev, current.st_ino) != (st.st_dev, st.st_ino):
                _fail("La identidad del lock activo cambió.")
            yield
        finally:
            with contextlib.suppress(OSError):
                fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def read(self) -> dict | None:
        with self.locked():
            if not self.active_file.exists() and not self.active_file.is_symlink():
                return None
            return dict(_validate_record(_strict_json(_read_regular(self.active_file))))

    def set_active(self, record: dict) -> dict:
        value = _validate_record(dict(record))
        with self.locked():
            if self.active_file.exists() or self.active_file.is_symlink():
                current = _validate_record(_strict_json(_read_regular(self.active_file)))
                identity = ("profile_id", "revision", "validation_id", "generation_id",
                            "config_sha256", "operation_id")
                if all(current[key] == value[key] for key in identity):
                    return {"status": "ALREADY_RECORDED", "profile_id": value["profile_id"],
                            "revision": value["revision"], "generation_id": value["generation_id"],
                            "config_sha256": value["config_sha256"]}
            temp = self.root / (".active-" + secrets.token_hex(16))
            fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
            try:
                os.fchown(fd, 0, 0)
                os.fchmod(fd, 0o600)
                data = _json_bytes(value)
                view = memoryview(data)
                while view:
                    written = os.write(fd, view)
                    if written <= 0:
                        _fail("Escritura incompleta del registro activo B4.")
                    view = view[written:]
                os.fsync(fd)
                os.replace(temp, self.active_file)
                dfd = os.open(self.root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
                try:
                    os.fsync(dfd)
                finally:
                    os.close(dfd)
            finally:
                with contextlib.suppress(FileNotFoundError):
                    temp.unlink()
                with contextlib.suppress(OSError):
                    os.close(fd)
        return {"status": "ACTIVE_PROFILE_RECORDED", "profile_id": value["profile_id"],
                "revision": value["revision"], "generation_id": value["generation_id"],
                "config_sha256": value["config_sha256"]}
