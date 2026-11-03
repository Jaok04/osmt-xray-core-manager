#!/usr/bin/env python3
"""Catálogo y almacén central de certificados TLS de Xray Manager."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import secrets
import stat
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization

import certificate_crypto as crypto

SCHEMA_VERSION = 1
MAX_CERTIFICATE_BYTES = 1024 * 1024
MAX_PRIVATE_KEY_BYTES = crypto.MAX_PRIVATE_KEY_BYTES
ID_RE = re.compile(r"^cert-[A-Za-z0-9][A-Za-z0-9_.-]{0,120}$")


class StoreError(Exception):
    """Error controlado del catálogo de certificados."""


def require_root() -> None:
    if os.geteuid() != 0:
        raise StoreError("la gestión de certificados requiere root")


def safe_dir(path: Path, create: bool = False) -> None:
    path = path.absolute()
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            st = current.lstat()
        except FileNotFoundError:
            if not create or current != path:
                raise StoreError(f"falta un directorio seguro: {current.parent}")
            current.mkdir(mode=0o700)
            st = current.lstat()
        if not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode):
            raise StoreError(f"componente de ruta no seguro: {current}")
    st = path.lstat()
    if st.st_uid != 0 or st.st_gid != 0 or stat.S_IMODE(st.st_mode) != 0o700:
        raise StoreError(f"directorio debe ser root:root modo 0700: {path}")


def read_regular(path: Path, limit: int, *, require_private: bool = False) -> bytes:
    try:
        st = path.lstat()
    except OSError as exc:
        raise StoreError(f"no se pudo acceder al archivo: {path}") from exc
    if not stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode) or st.st_nlink != 1:
        raise StoreError("se rechaza archivo no regular, symlink o hardlink")
    if st.st_size < 1 or st.st_size > limit:
        raise StoreError("tamaño de archivo no válido")
    if require_private and (
        st.st_uid != 0 or st.st_gid != 0 or stat.S_IMODE(st.st_mode) != 0o600
    ):
        raise StoreError("la clave privada de origen debe ser root:root modo 0600")
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if (
                opened.st_dev, opened.st_ino, opened.st_uid, opened.st_gid,
                stat.S_IMODE(opened.st_mode), opened.st_nlink, opened.st_size
            ) != (
                st.st_dev, st.st_ino, st.st_uid, st.st_gid,
                stat.S_IMODE(st.st_mode), st.st_nlink, st.st_size
            ):
                raise StoreError("el archivo cambió durante la apertura")
            data = stream.read(limit + 1)
    except OSError as exc:
        raise StoreError(f"no se pudo leer el archivo: {path}") from exc
    if len(data) != st.st_size or len(data) > limit:
        raise StoreError("el archivo cambió durante la lectura")
    return data


def atomic_write(path: Path, data: bytes, mode: int = 0o600) -> None:
    safe_dir(path.parent)
    if path.exists() or path.is_symlink():
        raise StoreError(f"el destino ya existe: {path.name}")
    fd, tmp_name = tempfile.mkstemp(prefix=".certificate.", dir=path.parent)
    try:
        os.fchown(fd, 0, 0)
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(tmp_name, path, follow_symlinks=False)
        os.unlink(tmp_name)
        dirfd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def load_catalog(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise StoreError("catálogo symlink rechazado")
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "revision": 0, "certificates": []}
    safe_dir(path.parent)
    raw = read_regular(path, 4 * 1024 * 1024, require_private=True)
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise StoreError("catálogo de certificados corrupto") from exc
    if (
        not isinstance(value, dict)
        or set(value) != {"schema_version", "revision", "certificates"}
        or isinstance(value["schema_version"], bool)
        or type(value["schema_version"]) is not int
        or value["schema_version"] != SCHEMA_VERSION
        or isinstance(value["revision"], bool)
        or not isinstance(value["revision"], int)
        or value["revision"] < 0
        or not isinstance(value["certificates"], list)
    ):
        raise StoreError("estructura o versión del catálogo no válida")
    seen_ids: set[str] = set()
    seen_fingerprints: set[str] = set()
    required_fields = {
        "certificate_id", "storage_type", "certificate_source", "secret_ref",
        "fingerprint_sha256", "public_key_fingerprint_sha256", "subject",
        "issuer", "sans", "not_before", "not_after", "status", "revision",
        "created_at", "updated_at",
    }
    for item in value["certificates"]:
        if not isinstance(item, dict) or set(item) != required_fields:
            raise StoreError("estructura de registro de certificado no válida")
        cid = item.get("certificate_id")
        fingerprint = item.get("fingerprint_sha256")
        if not isinstance(cid, str) or not ID_RE.fullmatch(cid) or cid in seen_ids:
            raise StoreError("ID de certificado inválido o duplicado")
        if not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
            raise StoreError("huella de certificado inválida")
        if fingerprint in seen_fingerprints:
            raise StoreError("huella de certificado duplicada en catálogo")
        if item.get("storage_type") not in ("managed", "reference"):
            raise StoreError("tipo de almacenamiento no válido")
        if item.get("storage_type") == "managed" and item.get("certificate_source") != f"managed/{cid}.pem":
            raise StoreError("referencia managed no válida")
        if item.get("storage_type") == "reference" and (
            not isinstance(item.get("certificate_source"), str)
            or not Path(item["certificate_source"]).is_absolute()
        ):
            raise StoreError("referencia externa no válida")
        if item.get("secret_ref") != f"secrets/{cid}.r000001.bin":
            raise StoreError("referencia al secreto central no válida")
        if (item.get("status") != "active" or isinstance(item.get("revision"), bool)
            or type(item.get("revision")) is not int or item.get("revision") != 1):
            raise StoreError("estado o revisión de certificado no soportados")
        for field in ("public_key_fingerprint_sha256",):
            if not isinstance(item.get(field), str) or not re.fullmatch(r"[0-9a-f]{64}", item[field]):
                raise StoreError(f"campo {field} no válido")
        if not isinstance(item.get("sans"), list) or not all(isinstance(x, str) for x in item["sans"]):
            raise StoreError("SAN del certificado no válidos")
        for field in ("subject", "issuer", "not_before", "not_after", "created_at", "updated_at"):
            if not isinstance(item.get(field), str):
                raise StoreError(f"campo {field} no válido")
        seen_ids.add(cid)
        seen_fingerprints.add(fingerprint)
    return value


def write_catalog(path: Path, catalog: dict[str, Any]) -> None:
    safe_dir(path.parent)
    if path.is_symlink():
        raise StoreError("destino de catálogo symlink rechazado")
    data = (json.dumps(catalog, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    tmp_fd, tmp_name = tempfile.mkstemp(prefix=".catalog.", dir=path.parent)
    try:
        os.fchown(tmp_fd, 0, 0)
        os.fchmod(tmp_fd, 0o600)
        with os.fdopen(tmp_fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp_name, path)
        dirfd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def parse_certificate(certificate_bytes: bytes, private_key_bytes: bytes) -> dict[str, Any]:
    try:
        certificate = x509.load_pem_x509_certificate(certificate_bytes)
        private_key = serialization.load_pem_private_key(private_key_bytes, password=None)
    except (ValueError, TypeError) as exc:
        raise StoreError("certificado PEM o clave privada PEM no válidos/no compatibles") from exc
    cert_public = certificate.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    key_public = private_key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    if cert_public != key_public:
        raise StoreError("la clave privada no corresponde al certificado")
    fingerprint = certificate.fingerprint(hashes.SHA256()).hex()
    try:
        san_ext = certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        sans = sorted(set(san_ext.value.get_values_for_type(x509.DNSName)))
    except x509.ExtensionNotFound:
        sans = []
    not_before = certificate.not_valid_before.replace(tzinfo=timezone.utc).isoformat()
    not_after = certificate.not_valid_after.replace(tzinfo=timezone.utc).isoformat()
    subject = certificate.subject.rfc4514_string()
    issuer = certificate.issuer.rfc4514_string()
    public_fingerprint = hashlib.sha256(cert_public).hexdigest()
    return {
        "fingerprint_sha256": fingerprint,
        "public_key_fingerprint_sha256": public_fingerprint,
        "subject": subject,
        "issuer": issuer,
        "sans": sans,
        "not_before": not_before,
        "not_after": not_after,
    }


def acquire_lock(path: Path):
    safe_dir(path.parent, create=True)
    if path.exists() or path.is_symlink():
        st = path.lstat()
        if not stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode) or st.st_uid != 0 or st.st_gid != 0 or stat.S_IMODE(st.st_mode) != 0o600:
            raise StoreError("archivo de bloqueo inseguro")
    fd = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    os.fchown(fd, 0, 0)
    os.fchmod(fd, 0o600)
    fcntl.flock(fd, fcntl.LOCK_EX)
    return fd


def import_certificate(args: argparse.Namespace) -> dict[str, Any]:
    require_root()
    base = Path(args.base).absolute()
    managed = Path(args.managed_dir).absolute()
    secrets_dir = Path(args.secrets_dir).absolute()
    catalog_path = Path(args.catalog).absolute()
    safe_dir(base, create=True)
    lock_fd = acquire_lock(Path(args.lock).absolute())
    try:
        safe_dir(managed, create=True)
        safe_dir(secrets_dir, create=True)
        cert_path = Path(args.certificate_file).absolute()
        key_path = Path(args.private_key_file).absolute()
        certificate_bytes = read_regular(cert_path, MAX_CERTIFICATE_BYTES)
        private_key_bytes = read_regular(key_path, MAX_PRIVATE_KEY_BYTES, require_private=True)
        metadata = parse_certificate(certificate_bytes, private_key_bytes)
        now_dt = datetime.now(timezone.utc)
        if now_dt.isoformat() < metadata["not_before"] or now_dt.isoformat() > metadata["not_after"]:
            raise StoreError("el certificado no está dentro de su período de validez")
        catalog = load_catalog(catalog_path)
        duplicate = next(
            (item for item in catalog["certificates"]
             if item["fingerprint_sha256"] == metadata["fingerprint_sha256"]),
            None,
        )
        if duplicate:
            if duplicate["public_key_fingerprint_sha256"] != metadata["public_key_fingerprint_sha256"]:
                raise StoreError("colisión de huella con clave pública diferente")
            raise StoreError(f"certificado ya registrado: {duplicate['certificate_id']}")
        certificate_id = args.certificate_id or ("cert-" + secrets.token_hex(8))
        if not ID_RE.fullmatch(certificate_id):
            raise StoreError("ID de certificado no válido")
        if any(item["certificate_id"] == certificate_id for item in catalog["certificates"]):
            raise StoreError("ID de certificado ya existe")
        revision = 1
        key = crypto.load_master_key(args.master_key)
        blob = crypto.encrypt_private_key(private_key_bytes, key, certificate_id, revision)
        secret_ref = f"secrets/{certificate_id}.r{revision:06d}.bin"
        secret_path = secrets_dir / f"{certificate_id}.r{revision:06d}.bin"
        if args.storage_type == "managed":
            cert_ref = f"managed/{certificate_id}.pem"
            cert_destination = managed / f"{certificate_id}.pem"
            atomic_write(cert_destination, certificate_bytes, 0o600)
        else:
            cert_ref = str(cert_path)
        atomic_write(secret_path, blob, 0o600)
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "certificate_id": certificate_id,
            "storage_type": args.storage_type,
            "certificate_source": cert_ref,
            "secret_ref": secret_ref,
            **metadata,
            "status": "active",
            "revision": revision,
            "created_at": now,
            "updated_at": now,
        }
        catalog["certificates"].append(record)
        catalog["certificates"].sort(key=lambda item: item["certificate_id"])
        catalog["revision"] += 1
        write_catalog(catalog_path, catalog)
        return {
            "status": "imported",
            "certificate_id": certificate_id,
            "storage_type": args.storage_type,
            "fingerprint_sha256": metadata["fingerprint_sha256"],
            "sans": metadata["sans"],
            "revision": revision,
            "secret_ref": secret_ref,
        }
    finally:
        os.close(lock_fd)


def show_certificate(args: argparse.Namespace) -> dict[str, Any]:
    require_root()
    base = Path(args.base).absolute()
    lock_fd = None
    if base.exists():
        safe_dir(base)
        lock_fd = acquire_lock(Path(args.lock).absolute())
    try:
        catalog = load_catalog(Path(args.catalog).absolute())
        for item in catalog["certificates"]:
            if item["certificate_id"] == args.certificate_id:
                return {"status": "ok", "certificate": item}
        raise StoreError("certificado no encontrado")
    finally:
        if lock_fd is not None:
            os.close(lock_fd)


def list_certificates(args: argparse.Namespace) -> dict[str, Any]:
    require_root()
    base = Path(args.base).absolute()
    lock_fd = None
    if base.exists():
        safe_dir(base)
        lock_fd = acquire_lock(Path(args.lock).absolute())
    try:
        catalog = load_catalog(Path(args.catalog).absolute())
        return {
            "status": "ok",
            "catalog_revision": catalog["revision"],
            "certificates": catalog["certificates"],
        }
    finally:
        if lock_fd is not None:
            os.close(lock_fd)


def audit_certificates(args: argparse.Namespace) -> dict[str, Any]:
    require_root()
    base = Path(args.base).absolute()
    managed = Path(args.managed_dir).absolute()
    secrets_dir = Path(args.secrets_dir).absolute()
    lock_fd = None
    if base.exists():
        safe_dir(base)
        lock_fd = acquire_lock(Path(args.lock).absolute())
    try:
        catalog = load_catalog(Path(args.catalog).absolute())
        if managed.exists():
            safe_dir(managed)
        if secrets_dir.exists():
            safe_dir(secrets_dir)
        key = crypto.load_master_key(args.master_key) if catalog["certificates"] else None
        referenced: set[str] = set()
        broken: list[dict[str, str]] = []
        for item in catalog["certificates"]:
            cid = item["certificate_id"]
            try:
                secret_ref = item["secret_ref"]
                expected = f"secrets/{cid}.r000001.bin"
                if secret_ref != expected:
                    raise StoreError("referencia de secreto no válida")
                referenced.add(f"{cid}.r000001.bin")
                if key is None:
                    raise StoreError("clave maestra no disponible")
                secret = crypto.decrypt_private_key(
                    read_regular(
                        secrets_dir / f"{cid}.r000001.bin",
                        crypto.MAX_BLOB_BYTES,
                        require_private=True,
                    ),
                    key,
                    cid,
                    1,
                )
                source = item["certificate_source"]
                if item["storage_type"] == "managed":
                    if source != f"managed/{cid}.pem":
                        raise StoreError("referencia managed no válida")
                    cert_path = managed / f"{cid}.pem"
                    cert_bytes = read_regular(
                        cert_path, MAX_CERTIFICATE_BYTES, require_private=True
                    )
                else:
                    cert_path = Path(source)
                    if not cert_path.is_absolute():
                        raise StoreError("ruta reference no válida")
                    cert_bytes = read_regular(cert_path, MAX_CERTIFICATE_BYTES)
                metadata = parse_certificate(cert_bytes, secret)
                if metadata["fingerprint_sha256"] != item["fingerprint_sha256"]:
                    raise StoreError("huella de certificado no coincide")
                if metadata["public_key_fingerprint_sha256"] != item["public_key_fingerprint_sha256"]:
                    raise StoreError("huella de clave pública no coincide")
            except Exception as exc:
                broken.append({"certificate_id": cid, "reason": str(exc)})
        actual: set[str] = set()
        unsafe: list[str] = []
        if secrets_dir.exists():
            for path in secrets_dir.iterdir():
                st = path.lstat()
                if (
                    path.is_symlink()
                    or not stat.S_ISREG(st.st_mode)
                    or st.st_uid != 0
                    or st.st_gid != 0
                    or stat.S_IMODE(st.st_mode) != 0o600
                    or st.st_nlink != 1
                ):
                    unsafe.append(path.name)
                elif path.name.endswith(".bin"):
                    actual.add(path.name)
        managed_actual: set[str] = set()
        if managed.exists():
            for path in managed.iterdir():
                st = path.lstat()
                if (
                    path.is_symlink()
                    or not stat.S_ISREG(st.st_mode)
                    or st.st_uid != 0
                    or st.st_gid != 0
                    or stat.S_IMODE(st.st_mode) != 0o600
                    or st.st_nlink != 1
                ):
                    unsafe.append("managed/" + path.name)
                elif path.name.endswith(".pem"):
                    managed_actual.add(path.name)
        managed_referenced = {
            item["certificate_id"] + ".pem"
            for item in catalog["certificates"]
            if item["storage_type"] == "managed"
        }
        return {
            "status": "audit",
            "catalog_revision": catalog["revision"],
            "certificates": len(catalog["certificates"]),
            "broken_references": broken,
            "orphan_secret_files": sorted(actual - referenced),
            "orphan_managed_files": sorted(managed_actual - managed_referenced),
            "unsafe_entries": sorted(unsafe),
            "automatic_deletion": False,
        }
    finally:
        if lock_fd is not None:
            os.close(lock_fd)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="/var/lib/xray-manager/certificates")
    parser.add_argument("--catalog", default="/var/lib/xray-manager/certificates/catalog.json")
    parser.add_argument("--managed-dir", default="/var/lib/xray-manager/certificates/managed")
    parser.add_argument("--secrets-dir", default="/var/lib/xray-manager/certificates/secrets")
    parser.add_argument("--master-key", default="/etc/xray-manager/keys/master.key")
    parser.add_argument("--lock", default="/var/lib/xray-manager/certificates/catalog.lock")
    sub = parser.add_subparsers(dest="action", required=True)
    imp = sub.add_parser("import")
    imp.add_argument("--storage-type", choices=("managed", "reference"), required=True)
    imp.add_argument("--certificate-file", required=True)
    imp.add_argument("--private-key-file", required=True)
    imp.add_argument("--certificate-id")
    show = sub.add_parser("show")
    show.add_argument("--certificate-id", required=True)
    sub.add_parser("list")
    sub.add_parser("audit")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.action == "import":
            result = import_certificate(args)
        elif args.action == "show":
            result = show_certificate(args)
        elif args.action == "list":
            result = list_certificates(args)
        else:
            result = audit_certificates(args)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (StoreError, crypto.CertificateCryptoError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
