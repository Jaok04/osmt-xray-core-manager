#!/usr/bin/env python3
"""Private, versioned profile store with authenticated encryption at rest."""
from __future__ import annotations

import argparse
import base64
import binascii
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
import pathlib
import re
import secrets
import stat
import sys
import uuid

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from certificate_crypto import CertificateCryptoError, load_master_key

DEFAULT_STORE = "/var/lib/xray-manager/profiles"
DEFAULT_MASTER_KEY = "/etc/xray-manager/keys/master.key"
MAX_CONFIG = 16 * 1024 * 1024
MAX_ENCRYPTED_CONFIG = 24 * 1024 * 1024
CRYPTO_FORMAT_VERSION = 1
CRYPTO_ALGORITHM = "AES-256-GCM"
NONCE_BYTES = 12
TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")


class ProfileError(Exception):
    pass


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def fail(message: str) -> None:
    raise ProfileError(message)


def check_no_symlink_components(path: pathlib.Path) -> None:
    if not path.is_absolute():
        fail("La ruta del almacén debe ser absoluta.")
    current = pathlib.Path("/")
    for part in path.parts[1:]:
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode):
            fail(f"Componente simbólico no permitido: {current}")


def check_dir(path: pathlib.Path, create: bool = False) -> None:
    check_no_symlink_components(path)
    if create:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        info = path.lstat()
    except FileNotFoundError:
        fail(f"No existe el directorio: {path}")
    if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
        fail(f"No es un directorio real: {path}")
    if info.st_uid != 0:
        fail(f"El directorio no pertenece a root: {path}")
    if stat.S_IMODE(info.st_mode) != 0o700:
        os.chmod(path, 0o700, follow_symlinks=False)
    info = path.stat(follow_symlinks=False)
    if info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o700:
        fail(f"Permisos/propietario inseguros: {path}")


def check_regular(path: pathlib.Path, mode: int = 0o600, required: bool = True) -> bool:
    try:
        info = path.lstat()
    except FileNotFoundError:
        if required:
            fail(f"Falta el archivo requerido: {path.name}")
        return False
    if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
        fail(f"El archivo no es regular: {path.name}")
    if info.st_uid != 0 or info.st_nlink != 1:
        fail(f"Propietario o hardlinks inseguros: {path.name}")
    if stat.S_IMODE(info.st_mode) != mode:
        os.chmod(path, mode, follow_symlinks=False)
    info = path.stat(follow_symlinks=False)
    if info.st_uid != 0 or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != mode:
        fail(f"Metadatos inseguros: {path.name}")
    return True


def read_regular(path: pathlib.Path, limit: int = 4 * 1024 * 1024) -> bytes:
    check_regular(path)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_nlink != 1:
            fail(f"Archivo inseguro: {path.name}")
        if info.st_size > limit:
            fail(f"Archivo demasiado grande: {path.name}")
        chunks = []
        total = 0
        while True:
            block = os.read(fd, min(1024 * 1024, limit + 1 - total))
            if not block:
                break
            chunks.append(block)
            total += len(block)
            if total > limit:
                fail(f"Archivo demasiado grande: {path.name}")
        return b"".join(chunks)
    finally:
        os.close(fd)


def atomic_write(path: pathlib.Path, data: bytes) -> None:
    parent = path.parent
    check_dir(parent)
    if path.exists() or path.is_symlink():
        check_regular(path)
    temp = parent / (".%s.%s.tmp" % (path.name, secrets.token_hex(8)))
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(temp, flags, 0o600)
    try:
        os.fchown(fd, 0, 0)
        os.fchmod(fd, 0o600)
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            view = view[written:]
        os.fsync(fd)
    except Exception:
        os.close(fd)
        with contextlib.suppress(FileNotFoundError):
            temp.unlink()
        raise
    else:
        os.close(fd)
    os.replace(temp, path)
    dirfd = os.open(parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(dirfd)
    finally:
        os.close(dirfd)


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def strict_json(data: bytes, label: str) -> object:
    try:
        text = data.decode("utf-8", errors="strict")
        if text.startswith("\ufeff"):
            fail(f"{label}: no se admite BOM UTF-8.")
        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    fail(f"{label}: clave JSON duplicada: {key}")
                result[key] = value
            return result
        value = json.loads(text, object_pairs_hook=pairs, parse_constant=lambda x: fail(f"{label}: valor no finito: {x}"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"{label}: JSON inválido ({exc}).")
    return value


def config_from_file(path_text: str) -> bytes:
    source = pathlib.Path(path_text)
    if not source.is_absolute():
        source = pathlib.Path.cwd() / source
    check_no_symlink_components(source)
    try:
        info = source.lstat()
    except FileNotFoundError:
        fail("No existe el archivo JSON indicado.")
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        fail("El archivo de origen debe ser regular y no tener hardlinks.")
    if info.st_size < 1 or info.st_size > MAX_CONFIG:
        fail("El archivo JSON debe medir entre 1 byte y 16 MiB.")
    fd = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        opened = os.fstat(fd)
        if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino) or opened.st_nlink != 1:
            fail("El archivo de origen cambió durante la apertura.")
        chunks = []
        while True:
            block = os.read(fd, 1024 * 1024)
            if not block:
                break
            chunks.append(block)
            if sum(map(len, chunks)) > MAX_CONFIG:
                fail("El archivo JSON supera 16 MiB.")
    finally:
        os.close(fd)
    parsed = strict_json(b"".join(chunks), "Configuración")
    if not isinstance(parsed, dict):
        fail("La configuración Xray debe ser un objeto JSON.")
    return json_bytes(parsed)


class ProfileStore:
    def __init__(self, store_text: str | None = None, master_key_text: str | None = None):
        self.root = pathlib.Path(store_text or os.environ.get("XRAY_MANAGER_PROFILES_DIR", DEFAULT_STORE))
        self.master_key_path = pathlib.Path(
            master_key_text or os.environ.get("XRAY_MANAGER_MASTER_KEY_FILE", DEFAULT_MASTER_KEY)
        )
        self._master_key: bytes | None = None
        self.profiles = self.root / "profiles"
        self.catalog_path = self.root / "catalog.json"
        self.lock_path = self.root / ".profiles.lock"

    def master_key(self) -> bytes:
        if self._master_key is None:
            try:
                self._master_key = load_master_key(self.master_key_path)
            except CertificateCryptoError as exc:
                fail(f"No se pudo cargar la clave maestra existente: {exc}.")
        return self._master_key

    @staticmethod
    def config_aad(profile_id: str, revision: str) -> bytes:
        if not TOKEN_RE.fullmatch(profile_id) or not re.fullmatch(r"r[0-9]{6}", revision):
            fail("Identidad de perfil/revisión no válida para cifrado.")
        return f"xray-manager:profile-config:v{CRYPTO_FORMAT_VERSION}:{profile_id}:{revision}".encode("utf-8")

    def encrypt_config(self, plaintext: bytes, profile_id: str, revision: str) -> bytes:
        if not isinstance(plaintext, bytes) or not 1 <= len(plaintext) <= MAX_CONFIG:
            fail("Configuración vacía o fuera del límite permitido.")
        nonce = secrets.token_bytes(NONCE_BYTES)
        ciphertext = AESGCM(self.master_key()).encrypt(
            nonce, plaintext, self.config_aad(profile_id, revision)
        )
        envelope = {
            "format_version": CRYPTO_FORMAT_VERSION,
            "algorithm": CRYPTO_ALGORITHM,
            "profile_id": profile_id,
            "revision": revision,
            "nonce": base64.b64encode(nonce).decode("ascii"),
            "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
        }
        return json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def decrypt_config(self, blob: bytes, profile_id: str, revision: str) -> bytes:
        if not isinstance(blob, bytes) or not 1 <= len(blob) <= MAX_ENCRYPTED_CONFIG:
            fail("Blob cifrado vacío o demasiado grande.")
        try:
            envelope = strict_json(blob, "Sobre cifrado")
            expected = {"format_version", "algorithm", "profile_id", "revision", "nonce", "ciphertext"}
            if not isinstance(envelope, dict) or set(envelope) != expected:
                raise ValueError("estructura")
            if (type(envelope["format_version"]) is not int or
                    envelope["format_version"] != CRYPTO_FORMAT_VERSION or
                    envelope["algorithm"] != CRYPTO_ALGORITHM or
                    envelope["profile_id"] != profile_id or envelope["revision"] != revision):
                raise ValueError("metadatos")
            nonce = base64.b64decode(envelope["nonce"], validate=True)
            ciphertext = base64.b64decode(envelope["ciphertext"], validate=True)
            if len(nonce) != NONCE_BYTES or len(ciphertext) < 16:
                raise ValueError("longitud")
            plaintext = AESGCM(self.master_key()).decrypt(
                nonce, ciphertext, self.config_aad(profile_id, revision)
            )
        except (UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError, binascii.Error, InvalidTag) as exc:
            fail("No se pudo autenticar o descifrar la configuración del perfil.")
        if not 1 <= len(plaintext) <= MAX_CONFIG:
            fail("La configuración descifrada excede el límite permitido.")
        return plaintext

    def write_revision_config(self, directory: pathlib.Path, profile_id: str,
                              revision: str, plaintext: bytes) -> dict:
        encrypted = self.encrypt_config(plaintext, profile_id, revision)
        atomic_write(directory / "config.enc.json", encrypted)
        return {
            "file": "config.enc.json",
            "plaintext_size_bytes": len(plaintext),
            "stored_size_bytes": len(encrypted),
            "ciphertext_sha256": hashlib.sha256(encrypted).hexdigest(),
            "storage": "aes-256-gcm",
            "crypto_format_version": CRYPTO_FORMAT_VERSION,
        }

    def prepare(self) -> None:
        check_dir(self.root, create=True)
        if not self.profiles.exists():
            try:
                self.profiles.mkdir(mode=0o700)
            except FileExistsError:
                pass
        check_dir(self.profiles)
        if not (self.lock_path.exists() or self.lock_path.is_symlink()):
            try:
                fd = os.open(self.lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
            except FileExistsError:
                fd = None
            if fd is not None:
                try:
                    os.fchown(fd, 0, 0)
                    os.fchmod(fd, 0o600)
                    os.fsync(fd)
                finally:
                    os.close(fd)
        check_regular(self.lock_path)

    @contextlib.contextmanager
    def locked(self):
        if os.geteuid() != 0:
            fail("El almacén de perfiles requiere ejecución como root.")
        self.prepare()
        fd = os.open(self.lock_path, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600:
                fail("Lock de perfiles inseguro.")
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            with contextlib.suppress(OSError):
                fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def load_catalog(self) -> dict:
        if not self.catalog_path.exists():
            return {"schema_version": 1, "profiles": []}
        value = strict_json(read_regular(self.catalog_path), "Catálogo")
        if not isinstance(value, dict) or value.get("schema_version") != 1 or not isinstance(value.get("profiles"), list):
            fail("El catálogo de perfiles tiene un esquema no reconocido.")
        seen_ids, seen_names = set(), set()
        for item in value["profiles"]:
            if not isinstance(item, dict) or not TOKEN_RE.fullmatch(str(item.get("profile_id", ""))):
                fail("El catálogo contiene una identidad de perfil inválida.")
            key = str(item.get("name", "")).casefold()
            if not key or item["profile_id"] in seen_ids or key in seen_names:
                fail("El catálogo contiene IDs o nombres duplicados.")
            seen_ids.add(item["profile_id"])
            seen_names.add(key)
        return value

    def save_catalog(self, catalog: dict) -> None:
        atomic_write(self.catalog_path, json_bytes(catalog))

    def profile_dir(self, profile_id: str) -> pathlib.Path:
        if not TOKEN_RE.fullmatch(profile_id):
            fail("ID de perfil no válido.")
        path = self.profiles / profile_id
        check_no_symlink_components(path)
        check_dir(path)
        return path

    def load_metadata(self, profile_id: str) -> dict:
        path = self.profile_dir(profile_id) / "metadata.json"
        value = strict_json(read_regular(path), "Metadatos")
        if (not isinstance(value, dict) or value.get("schema_version") != 1 or
                value.get("profile_id") != profile_id or not isinstance(value.get("name"), str) or
                not isinstance(value.get("config_present"), bool)):
            fail("Metadatos de perfil inconsistentes o con esquema no reconocido.")
        current = value.get("current_revision")
        if current is not None and not re.fullmatch(r"r[0-9]{6}", str(current)):
            fail("La revisión actual del perfil no tiene un identificador válido.")
        if bool(current) != value["config_present"]:
            fail("El indicador de configuración no coincide con la revisión actual.")
        return value

    def save_metadata(self, profile_id: str, metadata: dict) -> None:
        atomic_write(self.profile_dir(profile_id) / "metadata.json", json_bytes(metadata))

    @staticmethod
    def unique_name(catalog: dict, name: str, exclude: str | None = None) -> str:
        cleaned = " ".join(name.strip().split())
        if not cleaned or len(cleaned) > 80 or any(ord(c) < 32 for c in cleaned):
            fail("El nombre debe contener entre 1 y 80 caracteres imprimibles.")
        for item in catalog["profiles"]:
            if item["profile_id"] != exclude and item["name"].casefold() == cleaned.casefold():
                fail("Ya existe un perfil con ese nombre.")
        return cleaned

    def revision_ids(self, profile_id: str) -> list[str]:
        directory = self.profile_dir(profile_id) / "revisions"
        check_dir(directory)
        ids = []
        for entry in directory.iterdir():
            if entry.name.startswith("."):
                continue
            if not re.fullmatch(r"r[0-9]{6}", entry.name):
                fail(f"Entrada de revisión no reconocida: {entry.name}")
            check_dir(entry)
            ids.append(entry.name)
        return sorted(ids, key=lambda x: int(x[1:]))

    def read_revision_config(self, profile_id: str, revision: str) -> tuple[bytes, dict]:
        if not re.fullmatch(r"r[0-9]{6}", revision):
            fail("Identificador de revisión no válido.")
        directory = self.profile_dir(profile_id) / "revisions" / revision
        check_dir(directory)
        manifest = strict_json(read_regular(directory / "manifest.json"), "Manifiesto")
        if (not isinstance(manifest, dict) or manifest.get("schema_version") != 1 or
                manifest.get("profile_id") != profile_id or manifest.get("revision") != revision or
                not isinstance(manifest.get("config"), dict)):
            fail(f"Manifiesto inconsistente en {revision}.")
        if manifest["config"].get("file") != "config.enc.json":
            fail(f"Ruta de configuración cifrada no reconocida en {revision}.")
        if manifest["config"].get("storage") != "aes-256-gcm":
            fail(f"Formato de almacenamiento no cifrado/no compatible en {revision}; se rechaza fail-closed.")
        if manifest["config"].get("crypto_format_version") != CRYPTO_FORMAT_VERSION:
            fail(f"Versión criptográfica no compatible en {revision}.")
        blob = read_regular(directory / "config.enc.json", MAX_ENCRYPTED_CONFIG)
        if (manifest["config"].get("stored_size_bytes") != len(blob) or
                manifest["config"].get("ciphertext_sha256") != hashlib.sha256(blob).hexdigest()):
            fail(f"Integridad del blob cifrado incorrecta en {revision}.")
        config = self.decrypt_config(blob, profile_id, revision)
        if manifest["config"].get("plaintext_size_bytes") != len(config):
            fail(f"Tamaño de configuración descifrada incorrecto en {revision}.")
        parsed = strict_json(config, f"Configuración {revision}")
        if not isinstance(parsed, dict):
            fail(f"La revisión {revision} no contiene un objeto JSON.")
        return config, manifest

    def add_revision(self, profile_id: str, config_data: bytes, source: str = "user") -> str:
        profile = self.profile_dir(profile_id)
        revisions = profile / "revisions"
        check_dir(revisions)
        existing = self.revision_ids(profile_id)
        number = (max((int(x[1:]) for x in existing), default=0) + 1)
        revision = f"r{number:06d}"
        temp = revisions / (".revision-" + secrets.token_hex(8))
        temp.mkdir(mode=0o700)
        os.chown(temp, 0, 0)
        os.chmod(temp, 0o700)
        try:
            config_metadata = self.write_revision_config(temp, profile_id, revision, config_data)
            manifest = {
                "schema_version": 1,
                "profile_id": profile_id,
                "revision": revision,
                "created_at": utc_now(),
                "config": config_metadata,
                "source": source,
                "validation": {"json_syntax": "pass", "xray_static": "not_run", "status": "pending"},
            }
            atomic_write(temp / "manifest.json", json_bytes(manifest))
            final = revisions / revision
            if final.exists() or final.is_symlink():
                fail("La revisión ya existe; no se sobrescribirá.")
            os.rename(temp, final)
            dirfd = os.open(revisions, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(dirfd)
            finally:
                os.close(dirfd)
        except Exception:
            if temp.exists():
                for child in temp.iterdir():
                    with contextlib.suppress(OSError):
                        child.unlink()
                with contextlib.suppress(OSError):
                    temp.rmdir()
            raise
        return revision

    def create(self, name: str, description: str = "", notes: str = "", config_data: bytes | None = None, source: str = "zero") -> dict:
        with self.locked():
            catalog = self.load_catalog()
            clean_name = self.unique_name(catalog, name)
            profile_id = "profile-" + uuid.uuid4().hex
            now = utc_now()
            temp = self.profiles / (".new-" + secrets.token_hex(8))
            temp.mkdir(mode=0o700)
            os.chown(temp, 0, 0)
            os.chmod(temp, 0o700)
            final = self.profiles / profile_id
            published = False
            try:
                (temp / "revisions").mkdir(mode=0o700)
                os.chown(temp / "revisions", 0, 0)
                os.chmod(temp / "revisions", 0o700)
                revision = None
                if config_data is not None:
                    revdir = temp / "revisions" / "r000001"
                    revdir.mkdir(mode=0o700)
                    os.chown(revdir, 0, 0)
                    os.chmod(revdir, 0o700)
                    config_metadata = self.write_revision_config(revdir, profile_id, "r000001", config_data)
                    manifest = {
                        "schema_version": 1, "profile_id": profile_id, "revision": "r000001",
                        "created_at": now,
                        "config": config_metadata,
                        "source": source,
                        "validation": {"json_syntax": "pass", "xray_static": "not_run", "status": "pending"},
                    }
                    atomic_write(revdir / "manifest.json", json_bytes(manifest))
                    revision = "r000001"
                metadata = {
                    "schema_version": 1, "profile_id": profile_id, "name": clean_name,
                    "description": description.strip(), "notes": notes.strip(),
                    "created_at": now, "modified_at": now, "current_revision": revision,
                    "last_validated_revision": None, "validation_status": "not_validated",
                    "config_present": revision is not None,
                }
                atomic_write(temp / "metadata.json", json_bytes(metadata))
                if final.exists() or final.is_symlink():
                    fail("La identidad de perfil ya existe; no se sobrescribirá.")
                os.rename(temp, final)
                published = True
                catalog["profiles"].append({"profile_id": profile_id, "name": clean_name,
                                             "created_at": now, "modified_at": now})
                self.save_catalog(catalog)
            except Exception:
                if temp.exists():
                    import shutil
                    shutil.rmtree(temp)
                if published and final.exists():
                    import shutil
                    shutil.rmtree(final)
                raise
            return {"status": "CREATED", "profile_id": profile_id, "name": clean_name,
                    "current_revision": revision, "config_present": revision is not None,
                    "storage": CRYPTO_ALGORITHM if config_data is not None else "none"}

    def list_profiles(self) -> list[dict]:
        with self.locked():
            catalog = self.load_catalog()
            results = []
            for item in catalog["profiles"]:
                meta = self.load_metadata(item["profile_id"])
                if item.get("name") != meta.get("name"):
                    fail(f"El catálogo y los metadatos no coinciden para {item['profile_id']}.")
                if meta.get("current_revision"):
                    self.read_revision_config(meta["profile_id"], meta["current_revision"])
                results.append({
                    "profile_id": meta["profile_id"], "name": meta["name"],
                    "description": meta.get("description", ""), "created_at": meta["created_at"],
                    "modified_at": meta["modified_at"], "current_revision": meta.get("current_revision"),
                    "config_present": bool(meta.get("config_present")),
                    "validation_status": meta.get("validation_status", "not_validated"),
                    "active_status": "not_integrated",
                })
            return results

    def show(self, profile_id: str) -> dict:
        with self.locked():
            meta = self.load_metadata(profile_id)
            revisions = self.revision_ids(profile_id)
            return {"metadata": meta, "revisions": revisions,
                    "storage": CRYPTO_ALGORITHM if meta.get("config_present") else "none"}

    def rename(self, profile_id: str, name: str) -> dict:
        with self.locked():
            catalog = self.load_catalog()
            meta = self.load_metadata(profile_id)
            clean = self.unique_name(catalog, name, exclude=profile_id)
            old = meta["name"]
            meta["name"] = clean
            meta["modified_at"] = utc_now()
            self.save_metadata(profile_id, meta)
            for item in catalog["profiles"]:
                if item["profile_id"] == profile_id:
                    item["name"] = clean
                    item["modified_at"] = meta["modified_at"]
                    break
            try:
                self.save_catalog(catalog)
            except Exception:
                meta["name"] = old
                self.save_metadata(profile_id, meta)
                raise
            return {"status": "RENAMED", "profile_id": profile_id, "name": clean}

    def duplicate(self, profile_id: str, name: str, description: str | None = None, notes: str | None = None) -> dict:
        with self.locked():
            catalog = self.load_catalog()
            source = self.load_metadata(profile_id)
            clean = self.unique_name(catalog, name)
            data = None
            if source.get("current_revision"):
                data, _manifest = self.read_revision_config(profile_id, source["current_revision"])
            new_id = "profile-" + uuid.uuid4().hex
            now = utc_now()
            temp = self.profiles / (".new-" + secrets.token_hex(8))
            temp.mkdir(mode=0o700)
            os.chown(temp, 0, 0)
            os.chmod(temp, 0o700)
            final = self.profiles / new_id
            published = False
            try:
                (temp / "revisions").mkdir(mode=0o700)
                os.chown(temp / "revisions", 0, 0)
                os.chmod(temp / "revisions", 0o700)
                revision = None
                if data is not None:
                    revdir = temp / "revisions" / "r000001"
                    revdir.mkdir(mode=0o700)
                    os.chown(revdir, 0, 0)
                    os.chmod(revdir, 0o700)
                    config_metadata = self.write_revision_config(revdir, new_id, "r000001", data)
                    manifest = {
                        "schema_version": 1, "profile_id": new_id, "revision": "r000001",
                        "created_at": now,
                        "config": config_metadata,
                        "source": {"type": "profile_copy", "profile_id": profile_id,
                                   "revision": source["current_revision"]},
                        "validation": {"json_syntax": "pass", "xray_static": "not_run", "status": "pending"},
                    }
                    atomic_write(revdir / "manifest.json", json_bytes(manifest))
                    revision = "r000001"
                meta = {
                    "schema_version": 1, "profile_id": new_id, "name": clean,
                    "description": source.get("description", "") if description is None else description.strip(),
                    "notes": source.get("notes", "") if notes is None else notes.strip(),
                    "created_at": now, "modified_at": now,
                    "current_revision": revision, "last_validated_revision": None,
                    "validation_status": "not_validated", "config_present": revision is not None,
                }
                atomic_write(temp / "metadata.json", json_bytes(meta))
                if final.exists() or final.is_symlink():
                    fail("La identidad de perfil ya existe; no se sobrescribirá.")
                os.rename(temp, final)
                published = True
                catalog["profiles"].append({"profile_id": new_id, "name": clean,
                                             "created_at": now, "modified_at": now})
                self.save_catalog(catalog)
            except Exception:
                import shutil
                if temp.exists():
                    shutil.rmtree(temp)
                if published and final.exists():
                    shutil.rmtree(final)
                raise
            return {"status": "DUPLICATED", "profile_id": new_id, "name": clean,
                    "current_revision": revision, "config_present": revision is not None}

    def update(self, profile_id: str, name: str | None = None, description: str | None = None,
               notes: str | None = None, config_data: bytes | None = None) -> dict:
        with self.locked():
            catalog = self.load_catalog()
            meta = self.load_metadata(profile_id)
            if name is not None:
                meta["name"] = self.unique_name(catalog, name, exclude=profile_id)
            if description is not None:
                meta["description"] = description.strip()
            if notes is not None:
                meta["notes"] = notes.strip()
            revision = meta.get("current_revision")
            if config_data is not None:
                revision = self.add_revision(profile_id, config_data, source="user_update")
                meta["current_revision"] = revision
                meta["config_present"] = True
                meta["validation_status"] = "not_validated"
            meta["modified_at"] = utc_now()
            self.save_metadata(profile_id, meta)
            for item in catalog["profiles"]:
                if item["profile_id"] == profile_id:
                    item["name"] = meta["name"]
                    item["modified_at"] = meta["modified_at"]
                    break
            self.save_catalog(catalog)
            return {"status": "UPDATED", "profile_id": profile_id, "name": meta["name"],
                    "current_revision": revision, "config_present": bool(meta.get("config_present"))}

    def versions(self, profile_id: str) -> list[dict]:
        with self.locked():
            meta = self.load_metadata(profile_id)
            results = []
            for revision in self.revision_ids(profile_id):
                config, manifest = self.read_revision_config(profile_id, revision)
                actual = hashlib.sha256(config).hexdigest()
                results.append({"revision": revision, "created_at": manifest.get("created_at"),
                                "current": revision == meta.get("current_revision"),
                                "validation": manifest.get("validation", {}).get("status", "unknown"),
                                "sha256": actual})
            return results

    def restore(self, profile_id: str, revision: str) -> dict:
        if not re.fullmatch(r"r[0-9]{6}", revision):
            fail("Identificador de revisión no válido.")
        with self.locked():
            meta = self.load_metadata(profile_id)
            data, _manifest = self.read_revision_config(profile_id, revision)
            new_revision = self.add_revision(profile_id, data, source={"type": "restore", "revision": revision})
            meta["current_revision"] = new_revision
            meta["config_present"] = True
            meta["validation_status"] = "not_validated"
            meta["modified_at"] = utc_now()
            self.save_metadata(profile_id, meta)
            catalog = self.load_catalog()
            for item in catalog["profiles"]:
                if item["profile_id"] == profile_id:
                    item["modified_at"] = meta["modified_at"]
            self.save_catalog(catalog)
            return {"status": "RESTORED_AS_NEW_REVISION", "profile_id": profile_id,
                    "source_revision": revision, "current_revision": new_revision}


def output(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Almacén privado y versionado de perfiles Xray.")
    parser.add_argument("--store", help="Directorio del almacén (solo para pruebas/administración).")
    parser.add_argument("--master-key", help="Ruta de la clave maestra existente; nunca se crea automáticamente.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    create = sub.add_parser("create")
    create.add_argument("--name", required=True)
    create.add_argument("--description", default="")
    create.add_argument("--notes", default="")
    create.add_argument("--config-file")
    duplicate = sub.add_parser("duplicate")
    duplicate.add_argument("--profile-id", required=True)
    duplicate.add_argument("--name", required=True)
    duplicate.add_argument("--description")
    duplicate.add_argument("--notes")
    show = sub.add_parser("show")
    show.add_argument("--profile-id", required=True)
    rename = sub.add_parser("rename")
    rename.add_argument("--profile-id", required=True)
    rename.add_argument("--name", required=True)
    update = sub.add_parser("update")
    update.add_argument("--profile-id", required=True)
    update.add_argument("--name")
    update.add_argument("--description")
    update.add_argument("--notes")
    update.add_argument("--config-file")
    versions = sub.add_parser("versions")
    versions.add_argument("--profile-id", required=True)
    restore = sub.add_parser("restore")
    restore.add_argument("--profile-id", required=True)
    restore.add_argument("--revision", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        store = ProfileStore(args.store, args.master_key)
        if args.command == "list":
            result = store.list_profiles()
        elif args.command == "create":
            data = config_from_file(args.config_file) if args.config_file else None
            result = store.create(args.name, args.description, args.notes, data,
                                  source="json_file" if data is not None else "zero")
        elif args.command == "duplicate":
            result = store.duplicate(args.profile_id, args.name, args.description, args.notes)
        elif args.command == "show":
            result = store.show(args.profile_id)
        elif args.command == "rename":
            result = store.rename(args.profile_id, args.name)
        elif args.command == "update":
            if all(x is None for x in (args.name, args.description, args.notes, args.config_file)):
                fail("Indica al menos un campo para modificar.")
            data = config_from_file(args.config_file) if args.config_file else None
            result = store.update(args.profile_id, args.name, args.description, args.notes, data)
        elif args.command == "versions":
            result = store.versions(args.profile_id)
        elif args.command == "restore":
            result = store.restore(args.profile_id, args.revision)
        else:
            fail("Comando no reconocido.")
        output(result)
        return 0
    except (ProfileError, OSError, ValueError, CertificateCryptoError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())