#!/usr/bin/env python3
"""Cifrado autenticado de secretos de certificados TLS centralizados."""
from __future__ import annotations

import base64
import json
import os
import re
import secrets
import stat
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

FORMAT_VERSION = 1
ALGORITHM = "AES-256-GCM"
KEY_BYTES = 32
NONCE_BYTES = 12
MAX_PRIVATE_KEY_BYTES = 512 * 1024
MAX_BLOB_BYTES = 1024 * 1024
_ID_RE = re.compile(r"^cert-[A-Za-z0-9][A-Za-z0-9_.-]{0,120}$")


class CertificateCryptoError(Exception):
    """Error seguro del almacén criptográfico de certificados."""


def _safe_id(certificate_id: str) -> str:
    if not isinstance(certificate_id, str) or not _ID_RE.fullmatch(certificate_id):
        raise CertificateCryptoError("identificador de certificado no válido")
    return certificate_id


def _aad(certificate_id: str, revision: int) -> bytes:
    certificate_id = _safe_id(certificate_id)
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise CertificateCryptoError("revisión de certificado no válida")
    return (
        f"xray-manager:certificate-secret:v{FORMAT_VERSION}:"
        f"{certificate_id}:{revision}"
    ).encode("utf-8")


def load_master_key(path: str | Path) -> bytes:
    """Lee la clave maestra existente; nunca la crea ni la regenera."""
    if os.geteuid() != 0:
        raise CertificateCryptoError("la operación de clave maestra requiere root")
    key_path = Path(path).absolute()
    parent = key_path.parent
    try:
        parent_stat = parent.lstat()
        key_stat = key_path.lstat()
    except OSError as exc:
        raise CertificateCryptoError("no existe una clave maestra válida") from exc
    if (
        not stat.S_ISDIR(parent_stat.st_mode)
        or stat.S_ISLNK(parent_stat.st_mode)
        or parent_stat.st_uid != 0
        or parent_stat.st_gid != 0
        or stat.S_IMODE(parent_stat.st_mode) != 0o700
    ):
        raise CertificateCryptoError("el directorio de la clave maestra debe ser root:root 0700")
    if (
        not stat.S_ISREG(key_stat.st_mode)
        or stat.S_ISLNK(key_stat.st_mode)
        or key_stat.st_nlink != 1
        or key_stat.st_uid != 0
        or key_stat.st_gid != 0
        or stat.S_IMODE(key_stat.st_mode) != 0o600
        or key_stat.st_size != KEY_BYTES
    ):
        raise CertificateCryptoError("la clave maestra debe ser un archivo root:root 0600 de 32 bytes")
    try:
        fd = os.open(key_path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if (
                opened.st_dev, opened.st_ino, opened.st_uid, opened.st_gid,
                stat.S_IMODE(opened.st_mode), opened.st_nlink, opened.st_size
            ) != (
                key_stat.st_dev, key_stat.st_ino, key_stat.st_uid, key_stat.st_gid,
                stat.S_IMODE(key_stat.st_mode), key_stat.st_nlink, key_stat.st_size
            ):
                raise CertificateCryptoError("la clave maestra cambió durante la apertura")
            key = stream.read(KEY_BYTES + 1)
    except OSError as exc:
        raise CertificateCryptoError("no se pudo leer la clave maestra") from exc
    if len(key) != KEY_BYTES:
        raise CertificateCryptoError("longitud de clave maestra inválida")
    return key


def encrypt_private_key(
    plaintext: bytes, key: bytes, certificate_id: str, revision: int
) -> bytes:
    if not isinstance(plaintext, bytes) or not 1 <= len(plaintext) <= MAX_PRIVATE_KEY_BYTES:
        raise CertificateCryptoError("clave privada vacía o demasiado grande")
    if not isinstance(key, bytes) or len(key) != KEY_BYTES:
        raise CertificateCryptoError("clave AES-256 no válida")
    nonce = secrets.token_bytes(NONCE_BYTES)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, _aad(certificate_id, revision))
    record = {
        "format_version": FORMAT_VERSION,
        "algorithm": ALGORITHM,
        "certificate_id": certificate_id,
        "revision": revision,
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
    }
    blob = json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(blob) > MAX_BLOB_BYTES:
        raise CertificateCryptoError("blob cifrado demasiado grande")
    return blob


def decrypt_private_key(
    blob: bytes, key: bytes, certificate_id: str, revision: int
) -> bytes:
    if not isinstance(blob, bytes) or len(blob) > MAX_BLOB_BYTES:
        raise CertificateCryptoError("blob cifrado no válido o demasiado grande")
    if not isinstance(key, bytes) or len(key) != KEY_BYTES:
        raise CertificateCryptoError("clave AES-256 no válida")
    try:
        record = json.loads(blob.decode("utf-8"))
        expected = {
            "format_version", "algorithm", "certificate_id",
            "revision", "nonce", "ciphertext",
        }
        if not isinstance(record, dict) or set(record) != expected:
            raise ValueError("estructura")
        if (
            isinstance(record["format_version"], bool)
            or type(record["format_version"]) is not int
            or record["format_version"] != FORMAT_VERSION
            or record["algorithm"] != ALGORITHM
            or record["certificate_id"] != certificate_id
            or isinstance(record["revision"], bool)
            or type(record["revision"]) is not int
            or record["revision"] != revision
        ):
            raise ValueError("metadatos")
        nonce = base64.b64decode(record["nonce"], validate=True)
        ciphertext = base64.b64decode(record["ciphertext"], validate=True)
        if len(nonce) != NONCE_BYTES or len(ciphertext) < 16:
            raise ValueError("longitud")
        plaintext = AESGCM(key).decrypt(
            nonce, ciphertext, _aad(certificate_id, revision)
        )
    except (UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError, InvalidTag) as exc:
        raise CertificateCryptoError("no se pudo autenticar o descifrar la clave privada") from exc
    if not 1 <= len(plaintext) <= MAX_PRIVATE_KEY_BYTES:
        raise CertificateCryptoError("clave privada descifrada no válida")
    return plaintext
