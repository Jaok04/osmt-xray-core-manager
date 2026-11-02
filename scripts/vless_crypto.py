#!/usr/bin/env python3
"""Primitive criptográfica del almacén VLESS; ningún secreto se pasa por CLI."""
from __future__ import annotations
import base64, binascii, json, os, re, secrets, stat, tempfile
from pathlib import Path
from typing import Union
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

FORMAT_VERSION = 1
ALGORITHM = "AES-256-GCM"
KEY_BYTES, NONCE_BYTES = 32, 12
MAX_PLAINTEXT_BYTES, MAX_BLOB_BYTES = 512 * 1024, 1024 * 1024
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")

class VaultError(Exception):
    """Error seguro del almacén criptográfico."""

def _safe_id(value: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise VaultError("identificador de conexión no válido")
    return value

def _check_root() -> None:
    if os.geteuid() != 0:
        raise VaultError("la operación de clave maestra requiere root")

def _check_directory(path: Path, create: bool) -> None:
    _check_root()
    path = path.absolute()
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current = current / component
        try:
            st = current.lstat()
        except FileNotFoundError:
            if not create or current != path:
                raise VaultError("falta un directorio padre seguro")
            try:
                current.mkdir(mode=0o700)
                st = current.lstat()
            except OSError as exc:
                raise VaultError("no se pudo crear el directorio privado") from exc
        except OSError as exc:
            raise VaultError("no se pudo acceder al directorio privado") from exc
        if not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode):
            raise VaultError("la ruta contiene un componente que no es directorio regular")
    st = path.lstat()
    if st.st_uid != 0 or stat.S_IMODE(st.st_mode) != 0o700:
        raise VaultError("el directorio debe ser root:root con modo 0700")

def _read_key_file(path: Path) -> bytes:
    try:
        st = path.lstat()
    except OSError as exc:
        raise VaultError("no existe una clave maestra válida") from exc
    if not stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode) or st.st_nlink != 1:
        raise VaultError("la clave maestra no es un archivo regular seguro")
    if st.st_uid != 0 or stat.S_IMODE(st.st_mode) != 0o600:
        raise VaultError("la clave maestra debe ser root:root con modo 0600")
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "rb") as stream:
            key = stream.read(KEY_BYTES + 1)
    except OSError as exc:
        raise VaultError("no se pudo leer la clave maestra") from exc
    if len(key) != KEY_BYTES:
        raise VaultError("la clave maestra tiene una longitud inválida")
    return key

def ensure_master_key(key_path: Union[str, Path]) -> Path:
    """Crea la clave una sola vez; nunca reemplaza una clave existente."""
    _check_root()
    path = Path(key_path)
    _check_directory(path.parent, create=True)
    if path.exists() or path.is_symlink():
        _read_key_file(path)
        return path
    key = secrets.token_bytes(KEY_BYTES)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    except FileExistsError:
        _read_key_file(path)
        return path
    except OSError as exc:
        raise VaultError("no se pudo crear la clave maestra") from exc
    try:
        os.fchown(fd, 0, 0)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(key)
            stream.flush()
            os.fsync(stream.fileno())
        dirfd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path

def load_master_key(key_path: Union[str, Path]) -> bytes:
    """Lee una clave existente. No crea ni regenera claves."""
    path = Path(key_path)
    _check_directory(path.parent, create=False)
    return _read_key_file(path)

def _aad(connection_id: str, schema_version: int) -> bytes:
    connection_id = _safe_id(connection_id)
    if isinstance(schema_version, bool) or not isinstance(schema_version, int) or schema_version < 1:
        raise VaultError("versión de esquema no válida")
    return f"xray-manager:vless-secret:v{FORMAT_VERSION}:{connection_id}:{schema_version}".encode()

def encrypt_secret(plaintext: bytes, key: bytes, connection_id: str, schema_version: int = 1) -> bytes:
    if not isinstance(plaintext, bytes) or len(plaintext) > MAX_PLAINTEXT_BYTES:
        raise VaultError("el secreto debe ser bytes y no superar el tamaño permitido")
    if not isinstance(key, bytes) or len(key) != KEY_BYTES:
        raise VaultError("clave AES-256 no válida")
    nonce = secrets.token_bytes(NONCE_BYTES)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, _aad(connection_id, schema_version))
    record = {"format_version": FORMAT_VERSION, "algorithm": ALGORITHM,
              "nonce": base64.b64encode(nonce).decode("ascii"),
              "ciphertext": base64.b64encode(ciphertext).decode("ascii")}
    encoded = json.dumps(record, separators=(",", ":"), sort_keys=True).encode()
    if len(encoded) > MAX_BLOB_BYTES:
        raise VaultError("el blob cifrado supera el tamaño permitido")
    return encoded

def decrypt_secret(blob: bytes, key: bytes, connection_id: str, schema_version: int = 1) -> bytes:
    if not isinstance(blob, bytes) or len(blob) > MAX_BLOB_BYTES:
        raise VaultError("blob cifrado no válido o demasiado grande")
    if not isinstance(key, bytes) or len(key) != KEY_BYTES:
        raise VaultError("clave AES-256 no válida")
    try:
        record = json.loads(blob.decode("utf-8"))
        if not isinstance(record, dict) or set(record) != {"format_version", "algorithm", "nonce", "ciphertext"}:
            raise VaultError("estructura del blob cifrado no válida")
        if record["format_version"] != FORMAT_VERSION or record["algorithm"] != ALGORITHM:
            raise VaultError("versión o algoritmo del blob no compatible")
        nonce = base64.b64decode(record["nonce"], validate=True)
        ciphertext = base64.b64decode(record["ciphertext"], validate=True)
        if len(nonce) != NONCE_BYTES or len(ciphertext) < 16:
            raise VaultError("longitud del blob cifrado no válida")
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, _aad(connection_id, schema_version))
    except (UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError, binascii.Error, InvalidTag) as exc:
        raise VaultError("no se pudo autenticar o descifrar el secreto") from exc
    if len(plaintext) > MAX_PLAINTEXT_BYTES:
        raise VaultError("el secreto descifrado supera el tamaño permitido")
    return plaintext

def write_encrypted_blob(destination: Union[str, Path], blob: bytes) -> None:
    """Escritura atómica 0600; el padre debe ser un directorio privado root-only."""
    _check_root()
    path = Path(destination)
    _check_directory(path.parent, create=False)
    if not isinstance(blob, bytes) or not 1 <= len(blob) <= MAX_BLOB_BYTES:
        raise VaultError("blob no válido o demasiado grande")
    if path.is_symlink():
        raise VaultError("se rechaza un destino simbólico")
    fd, tmp_name = tempfile.mkstemp(prefix=".vless-secret.", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        os.fchown(fd, 0, 0)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(blob)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        dirfd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    st = path.lstat()
    if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or stat.S_IMODE(st.st_mode) != 0o600:
        raise VaultError("el blob cifrado no conserva los permisos requeridos")

def read_encrypted_blob(source: Union[str, Path]) -> bytes:
    _check_root()
    path = Path(source)
    _check_directory(path.parent, create=False)
    try:
        st = path.lstat()
    except OSError as exc:
        raise VaultError("no existe el blob cifrado") from exc
    if not stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode) or st.st_nlink != 1:
        raise VaultError("el blob cifrado no es un archivo regular seguro")
    if st.st_uid != 0 or stat.S_IMODE(st.st_mode) != 0o600 or st.st_size > MAX_BLOB_BYTES:
        raise VaultError("permisos o tamaño del blob cifrado no válidos")
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "rb") as stream:
            blob = stream.read(MAX_BLOB_BYTES + 1)
    except OSError as exc:
        raise VaultError("no se pudo leer el blob cifrado") from exc
    if len(blob) != st.st_size or len(blob) > MAX_BLOB_BYTES:
        raise VaultError("el blob cifrado cambió durante la lectura o excede el límite")
    return blob
