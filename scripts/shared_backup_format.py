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
    if not 1 <= header_length <= MAX_HEADER_BYTES:
        raise SharedBackupFormatError("longitud de cabecera inválida")
    header_start = offset + HEADER_LENGTH_BYTES
    header_end = header_start + header_length
    if header_end + TAG_BYTES > len(package):
        raise SharedBackupFormatError("paquete truncado")

    header_bytes = package[header_start:header_end]
    try:
        header = json.loads(
            header_bytes.decode("ascii"), object_pairs_hook=_reject_duplicate_keys
        )
    except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise SharedBackupFormatError("cabecera JSON inválida") from exc
    if not isinstance(header, dict) or _canonical_json(header) != header_bytes:
        raise SharedBackupFormatError("cabecera no canónica o estructura inválida")

    expected_fields = {
        "format",
        "format_version",
        "cipher",
        "kdf",
        "kdf_params",
        "salt",
        "nonce",
        "ciphertext_length",
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
        or not TAG_BYTES <= ciphertext_length <= MAX_PLAINTEXT_BYTES + TAG_BYTES
        or header_end + ciphertext_length != len(package)
    ):
        raise SharedBackupFormatError("longitud de contenido inválida")
    aad = package[:header_end]
    ciphertext = package[header_end:]
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
