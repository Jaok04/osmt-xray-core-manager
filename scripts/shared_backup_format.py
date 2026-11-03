#!/usr/bin/env python3
"""Contenedor criptográfico compartido para backups Xray Manager.

Este módulo cifra/descifra bytes opacos. No conoce protocolos, catálogos ni
rutas y no crea archivos. El llamador debe obtener la passphrase de forma
interactiva y evitar persistir el payload en claro.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import secrets
import struct
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"XRMGSBKP"
FORMAT_ID = "xray-manager-shared-backup"
FORMAT_VERSION = 1
ALGORITHM = "AES-256-GCM"
KDF = "scrypt"
KEY_BYTES = 32
SALT_BYTES = 16
NONCE_BYTES = 12
TAG_BYTES = 16
HEADER_LENGTH_BYTES = 4
MAX_HEADER_BYTES = 4096
MAX_PLAINTEXT_BYTES = 512 * 1024 * 1024
MAX_PACKAGE_BYTES = MAX_PLAINTEXT_BYTES + TAG_BYTES + MAX_HEADER_BYTES + len(MAGIC) + HEADER_LENGTH_BYTES
MIN_PASSPHRASE_CHARS = 12
MIN_PASSPHRASE_BYTES = 16
MAX_PASSPHRASE_BYTES = 1024

# Perfil único v1. Los valores proceden del contrato aprobado y no se aceptan
# parámetros KDF arbitrarios desde un paquete no confiable.
SCRYPT_N = 2**15
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_MAXMEM = 64 * 1024 * 1024


class SharedBackupFormatError(Exception):
    """Error seguro de formato o autenticación."""


def _passphrase_bytes(passphrase: str) -> bytes:
    if not isinstance(passphrase, str):
        raise SharedBackupFormatError("la contraseña debe proporcionarse como texto")
    try:
        encoded = passphrase.encode("utf-8")
    except UnicodeError as exc:
        raise SharedBackupFormatError("la contraseña no tiene una codificación válida") from exc
    if (
        len(passphrase) < MIN_PASSPHRASE_CHARS
        or len(encoded) < MIN_PASSPHRASE_BYTES
        or len(encoded) > MAX_PASSPHRASE_BYTES
        or "\x00" in passphrase
    ):
        raise SharedBackupFormatError(
            "la contraseña debe tener al menos 12 caracteres, 16 bytes UTF-8 "
            "y no superar 1024 bytes"
        )
    return encoded


def _derive_key(passphrase: bytes, salt: bytes) -> bytes:
    try:
        return hashlib.scrypt(
            passphrase,
            salt=salt,
            n=SCRYPT_N,
            r=SCRYPT_R,
            p=SCRYPT_P,
            dklen=KEY_BYTES,
            maxmem=SCRYPT_MAXMEM,
        )
    except (ValueError, MemoryError) as exc:
        raise SharedBackupFormatError("no fue posible derivar la clave del backup") from exc


def _canonical_json(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("clave JSON duplicada")
        result[key] = value
    return result


def _parse_header(header_bytes: bytes, prefix: bytes, package_length: int) -> tuple[dict[str, Any], bytes, bytes, bytes, int]:
    if not 1 <= len(header_bytes) <= MAX_HEADER_BYTES:
        raise SharedBackupFormatError("longitud de cabecera inválida")
    try:
        header = json.loads(
            header_bytes.decode("ascii"), object_pairs_hook=_reject_duplicate_keys
        )
    except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise SharedBackupFormatError("cabecera JSON inválida") from exc
    if not isinstance(header, dict) or _canonical_json(header) != header_bytes:
        raise SharedBackupFormatError("cabecera no canónica o estructura inválida")

    expected_fields = {
        "format", "format_version", "cipher", "kdf", "kdf_params",
        "salt", "nonce", "ciphertext_length",
    }
    if set(header) != expected_fields:
        raise SharedBackupFormatError("campos de cabecera no compatibles")
    if (
        header["format"] != FORMAT_ID
        or type(header["format_version"]) is not int
        or header["format_version"] != FORMAT_VERSION
        or header["cipher"] != ALGORITHM
        or header["kdf"] != KDF
        or header["kdf_params"] != {"n": SCRYPT_N, "r": SCRYPT_R, "p": SCRYPT_P}
    ):
        raise SharedBackupFormatError("versión, algoritmo o perfil KDF no compatible")
    if (
        not isinstance(header["kdf_params"], dict)
        or set(header["kdf_params"]) != {"n", "r", "p"}
        or any(type(header["kdf_params"][name]) is not int for name in ("n", "r", "p"))
    ):
        raise SharedBackupFormatError("parámetros KDF inválidos")

    try:
        salt = base64.b64decode(header["salt"], validate=True)
        nonce = base64.b64decode(header["nonce"], validate=True)
    except (TypeError, binascii.Error) as exc:
        raise SharedBackupFormatError("salt o nonce inválido") from exc
    if len(salt) != SALT_BYTES or len(nonce) != NONCE_BYTES:
        raise SharedBackupFormatError("longitud de salt o nonce inválida")

    ciphertext_length = header["ciphertext_length"]
    if (
        type(ciphertext_length) is not int
        or not TAG_BYTES < ciphertext_length <= MAX_PLAINTEXT_BYTES + TAG_BYTES
        or len(prefix) + ciphertext_length != package_length
    ):
        raise SharedBackupFormatError("longitud de contenido inválida")
    return header, salt, nonce, prefix, ciphertext_length


def _decode_header(package: bytes) -> tuple[dict[str, Any], bytes, bytes, bytes, bytes]:
    if not isinstance(package, bytes):
        raise SharedBackupFormatError("el paquete debe ser bytes")
    minimum = len(MAGIC) + HEADER_LENGTH_BYTES + TAG_BYTES
    if len(package) < minimum or len(package) > MAX_PACKAGE_BYTES:
        raise SharedBackupFormatError("tamaño de paquete inválido o fuera de límites")
    if package[: len(MAGIC)] != MAGIC:
        raise SharedBackupFormatError("firma de paquete desconocida")

    offset = len(MAGIC)
    header_length = struct.unpack(">I", package[offset : offset + HEADER_LENGTH_BYTES])[0]
    header_start = offset + HEADER_LENGTH_BYTES
    header_end = header_start + header_length
    if header_end + TAG_BYTES > len(package):
        raise SharedBackupFormatError("paquete truncado")
    prefix = package[:header_end]
    header, salt, nonce, aad, ciphertext_length = _parse_header(
        package[header_start:header_end], prefix, len(package)
    )
    ciphertext = package[header_end:]
    if len(ciphertext) != ciphertext_length:
        raise SharedBackupFormatError("longitud de contenido inválida")
    return header, salt, nonce, aad, ciphertext


def encrypt_payload(payload: bytes, passphrase: str) -> bytes:
    """Devuelve un paquete autocontenido; no escribe datos en disco."""
    if not isinstance(payload, bytes) or not 1 <= len(payload) <= MAX_PLAINTEXT_BYTES:
        raise SharedBackupFormatError("contenido vacío, no válido o demasiado grande")
    password = _passphrase_bytes(passphrase)
    salt = secrets.token_bytes(SALT_BYTES)
    nonce = secrets.token_bytes(NONCE_BYTES)
    key = _derive_key(password, salt)

    header = {
        "format": FORMAT_ID,
        "format_version": FORMAT_VERSION,
        "cipher": ALGORITHM,
        "kdf": KDF,
        "kdf_params": {"n": SCRYPT_N, "r": SCRYPT_R, "p": SCRYPT_P},
        "salt": base64.b64encode(salt).decode("ascii"),
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext_length": len(payload) + TAG_BYTES,
    }
    header_bytes = _canonical_json(header)
    if len(header_bytes) > MAX_HEADER_BYTES:
        raise SharedBackupFormatError("cabecera excede el tamaño permitido")
    prefix = MAGIC + struct.pack(">I", len(header_bytes)) + header_bytes
    ciphertext = AESGCM(key).encrypt(nonce, payload, prefix)
    package = prefix + ciphertext
    if len(package) > MAX_PACKAGE_BYTES:
        raise SharedBackupFormatError("paquete excede el tamaño permitido")
    return package


def decrypt_payload(package: bytes, passphrase: str) -> bytes:
    """Autentica la cabecera y el contenido antes de devolver el payload."""
    password = _passphrase_bytes(passphrase)
    _, salt, nonce, aad, ciphertext = _decode_header(package)
    key = _derive_key(password, salt)
    try:
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, aad)
    except InvalidTag as exc:
        raise SharedBackupFormatError(
            "contraseña incorrecta o paquete alterado; autenticación fallida"
        ) from exc
    if not 1 <= len(plaintext) <= MAX_PLAINTEXT_BYTES:
        raise SharedBackupFormatError("contenido descifrado fuera de límites")
    return plaintext



def _write_all(destination: Any, data: bytes) -> None:
    view = memoryview(data)
    while view:
        written = destination.write(view)
        if written is None:
            raise SharedBackupFormatError("el destino no confirmó la escritura")
        if not isinstance(written, int) or written <= 0:
            raise SharedBackupFormatError("no fue posible escribir el paquete completo")
        view = view[written:]


def _read_exact(source: Any, length: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < length:
        part = source.read(length - len(chunks))
        if not part:
            raise SharedBackupFormatError("paquete truncado")
        chunks.extend(part)
    return bytes(chunks)


def encrypt_payload_stream(
    source: Any,
    destination: Any,
    plaintext_length: int,
    passphrase: str,
    *,
    chunk_size: int = 1024 * 1024,
) -> int:
    """Cifra un flujo de longitud conocida sin materializar el payload completo.

    El origen debe entregar exactamente plaintext_length bytes. El destino
    recibe el mismo contenedor binario v1 que encrypt_payload().
    """
    if type(plaintext_length) is not int or not 1 <= plaintext_length <= MAX_PLAINTEXT_BYTES:
        raise SharedBackupFormatError("longitud de payload inválida o fuera de límites")
    if type(chunk_size) is not int or not 1 <= chunk_size <= 16 * 1024 * 1024:
        raise SharedBackupFormatError("tamaño de bloque inválido")
    password = _passphrase_bytes(passphrase)
    salt = secrets.token_bytes(SALT_BYTES)
    nonce = secrets.token_bytes(NONCE_BYTES)
    key = _derive_key(password, salt)
    ciphertext_length = plaintext_length + TAG_BYTES
    header = {
        "format": FORMAT_ID,
        "format_version": FORMAT_VERSION,
        "cipher": ALGORITHM,
        "kdf": KDF,
        "kdf_params": {"n": SCRYPT_N, "r": SCRYPT_R, "p": SCRYPT_P},
        "salt": base64.b64encode(salt).decode("ascii"),
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext_length": ciphertext_length,
    }
    header_bytes = _canonical_json(header)
    if len(header_bytes) > MAX_HEADER_BYTES:
        raise SharedBackupFormatError("cabecera excede el tamaño permitido")
    prefix = MAGIC + struct.pack(">I", len(header_bytes)) + header_bytes
    if len(prefix) + ciphertext_length > MAX_PACKAGE_BYTES:
        raise SharedBackupFormatError("paquete excede el tamaño permitido")

    encryptor = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()
    encryptor.authenticate_additional_data(prefix)
    _write_all(destination, prefix)
    remaining = plaintext_length
    while remaining:
        requested = min(chunk_size, remaining)
        block = source.read(requested)
        if not isinstance(block, (bytes, bytearray, memoryview)) or not block:
            raise SharedBackupFormatError("flujo de entrada truncado o inválido")
        if len(block) > requested:
            raise SharedBackupFormatError("flujo de entrada excede el bloque solicitado")
        remaining -= len(block)
        encrypted = encryptor.update(bytes(block))
        if encrypted:
            _write_all(destination, encrypted)
    if source.read(1):
        raise SharedBackupFormatError("flujo de entrada contiene bytes sobrantes")
    final = encryptor.finalize()
    if final:
        _write_all(destination, final)
    _write_all(destination, encryptor.tag)
    return len(prefix) + ciphertext_length


def verify_package_stream(
    source: Any,
    passphrase: str,
    *,
    chunk_size: int = 1024 * 1024,
) -> int:
    """Autentica un contenedor v1 seekable sin conservar plaintext en memoria.

    Los bloques descifrados por GCM se descartan; no se consideran confiables
    hasta que finalize() valida el tag. El cursor queda al final del paquete.
    """
    if type(chunk_size) is not int or not 1 <= chunk_size <= 16 * 1024 * 1024:
        raise SharedBackupFormatError("tamaño de bloque inválido")
    password = _passphrase_bytes(passphrase)
    try:
        original_position = source.tell()
        source.seek(0, 2)
        package_length = source.tell()
        source.seek(original_position)
    except (AttributeError, OSError) as exc:
        raise SharedBackupFormatError("el flujo de paquete debe permitir seek/tell") from exc
    if package_length < len(MAGIC) + HEADER_LENGTH_BYTES + TAG_BYTES or package_length > MAX_PACKAGE_BYTES:
        raise SharedBackupFormatError("tamaño de paquete inválido o fuera de límites")

    source.seek(0)
    magic = _read_exact(source, len(MAGIC))
    if magic != MAGIC:
        raise SharedBackupFormatError("firma de paquete desconocida")
    length_bytes = _read_exact(source, HEADER_LENGTH_BYTES)
    header_length = struct.unpack(">I", length_bytes)[0]
    if not 1 <= header_length <= MAX_HEADER_BYTES:
        raise SharedBackupFormatError("longitud de cabecera inválida")
    header_bytes = _read_exact(source, header_length)
    prefix = magic + length_bytes + header_bytes
    header, salt, nonce, aad, ciphertext_length = _parse_header(
        header_bytes, prefix, package_length
    )
    key = _derive_key(password, salt)
    ciphertext_size = ciphertext_length - TAG_BYTES
    tag_position = len(prefix) + ciphertext_size
    source.seek(tag_position)
    tag = _read_exact(source, TAG_BYTES)
    if source.read(1):
        raise SharedBackupFormatError("paquete contiene bytes sobrantes")
    source.seek(len(prefix))
    decryptor = Cipher(algorithms.AES(key), modes.GCM(nonce, tag)).decryptor()
    decryptor.authenticate_additional_data(aad)
    remaining = ciphertext_size
    while remaining:
        requested = min(chunk_size, remaining)
        block = source.read(requested)
        if not block:
            raise SharedBackupFormatError("paquete truncado")
        if len(block) > requested:
            raise SharedBackupFormatError("flujo de paquete excede el bloque solicitado")
        remaining -= len(block)
        decryptor.update(block)  # plaintext no autenticado: se descarta
    try:
        decryptor.finalize()
    except InvalidTag as exc:
        raise SharedBackupFormatError(
            "contraseña incorrecta o paquete alterado; autenticación fallida"
        ) from exc
    source.seek(package_length)
    return package_length
