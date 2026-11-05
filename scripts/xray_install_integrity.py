#!/usr/bin/env python3
"""Verificación y registro de integridad de una instalación administrada de Xray-core."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

SCHEMA_VERSION = 1
FIELDS = {
    "schema_version", "managed_by", "version", "architecture",
    "binary_path", "binary_sha256", "geoip_path", "geoip_sha256",
    "geosite_path", "geosite_sha256", "release_package_sha256",
}


class IntegrityError(Exception):
    pass


def fail(message: str) -> None:
    raise IntegrityError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_no_symlink_ancestors(path: Path) -> None:
    absolute = path.absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode):
            fail(f"componente simbólico no permitido: {current}")


def regular_root_file(path: Path, expected_mode: int) -> os.stat_result:
    check_no_symlink_ancestors(path)
    try:
        info = path.lstat()
    except FileNotFoundError:
        fail(f"archivo requerido ausente: {path}")
    if not stat.S_ISREG(info.st_mode):
        fail(f"no es un archivo regular: {path}")
    if info.st_uid != 0 or info.st_gid != 0:
        fail(f"propietario/grupo no root:root: {path}")
    if stat.S_IMODE(info.st_mode) != expected_mode:
        fail(f"permisos inesperados en {path}: se esperaba {expected_mode:04o}")
    return info


def secure_manifest_parent(path: Path) -> None:
    parent = path.parent
    check_no_symlink_ancestors(parent)
    try:
        info = parent.lstat()
    except FileNotFoundError:
        fail(f"directorio del manifiesto ausente: {parent}")
    if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
        fail(f"directorio del manifiesto no válido: {parent}")
    if info.st_uid != 0 or info.st_gid != 0 or stat.S_IMODE(info.st_mode) != 0o700:
        fail(f"el directorio del manifiesto debe ser root:root con permisos 0700: {parent}")


def version_output(binary: Path) -> str:
    try:
        result = subprocess.run(
            [str(binary), "version"], check=True, capture_output=True,
            text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        fail(f"no se pudo consultar la versión del binario: {exc}")
    return (result.stdout or result.stderr).splitlines()[0] if (result.stdout or result.stderr) else ""


def validate_artifacts(binary: Path, geoip: Path, geosite: Path, version: str) -> dict[str, str]:
    regular_root_file(binary, 0o755)
    regular_root_file(geoip, 0o644)
    regular_root_file(geosite, 0o644)
    output = version_output(binary)
    if not re.search(rf"(?:^|\s)Xray {re.escape(version)}(?:\s|$)", output):
        fail(f"la versión ejecutada no coincide con {version}: {output}")
    return {
        "binary_sha256": sha256_file(binary),
        "geoip_sha256": sha256_file(geoip),
        "geosite_sha256": sha256_file(geosite),
    }


def verify(args: argparse.Namespace) -> None:
    manifest = Path(args.manifest)
    binary = Path(args.binary)
    geoip = Path(args.geoip)
    geosite = Path(args.geosite)
    secure_manifest_parent(manifest)
    regular_root_file(manifest, 0o600)
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(f"manifiesto ilegible o JSON inválido: {exc}")
    if not isinstance(data, dict) or set(data) != FIELDS:
        fail("esquema del manifiesto desconocido o incompleto")
    if data["schema_version"] != SCHEMA_VERSION or data["managed_by"] != "xray-core-manager":
        fail("versión de esquema o gestor del manifiesto no reconocido")
    if not isinstance(data["version"], str) or not re.fullmatch(r"\d+\.\d+\.\d+", data["version"]):
        fail("versión inválida en el manifiesto")
    if not isinstance(data["architecture"], str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", data["architecture"]):
        fail("arquitectura inválida en el manifiesto")
    for field in ("binary_sha256", "geoip_sha256", "geosite_sha256", "release_package_sha256"):
        if not isinstance(data[field], str) or not re.fullmatch(r"[a-f0-9]{64}", data[field]):
            fail(f"hash inválido en el manifiesto: {field}")
    if data["architecture"] != args.architecture:
        fail("la arquitectura instalada no coincide con el manifiesto")
    expected_paths = {
        "binary_path": str(binary), "geoip_path": str(geoip), "geosite_path": str(geosite)
    }
    for field, expected in expected_paths.items():
        if data[field] != expected:
            fail(f"ruta no coincide con el manifiesto: {field}")
    hashes = validate_artifacts(binary, geoip, geosite, data["version"])
    for field, actual in hashes.items():
        if data[field] != actual:
            fail(f"integridad no coincide: {field}")
    print(f"OK: Xray {data['version']} íntegro; binario y geodata coinciden con el manifiesto.")


def record(args: argparse.Namespace) -> None:
    manifest = Path(args.manifest)
    binary = Path(args.binary)
    geoip = Path(args.geoip)
    geosite = Path(args.geosite)
    secure_manifest_parent(manifest)
    if manifest.exists() or manifest.is_symlink():
        check_no_symlink_ancestors(manifest)
        try:
            existing = manifest.lstat()
        except FileNotFoundError:
            existing = None
        if existing is not None:
            if not stat.S_ISREG(existing.st_mode) or existing.st_uid != 0 or existing.st_gid != 0 or existing.st_nlink != 1:
                fail("el manifiesto previo no es un archivo regular root:root reemplazable")
    if not re.fullmatch(r"[a-f0-9]{64}", args.package_sha256):
        fail("hash SHA-256 del paquete no válido")
    if not re.fullmatch(r"\d+\.\d+\.\d+", args.version):
        fail("versión Xray no válida para el manifiesto")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", args.architecture):
        fail("arquitectura no válida para el manifiesto")
    hashes = validate_artifacts(binary, geoip, geosite, args.version)
    data = {
        "schema_version": SCHEMA_VERSION,
        "managed_by": "xray-core-manager",
        "version": args.version,
        "architecture": args.architecture,
        "binary_path": str(binary),
        **hashes,
        "geoip_path": str(geoip),
        "geosite_path": str(geosite),
        "release_package_sha256": args.package_sha256,
    }
    fd, temporary = tempfile.mkstemp(prefix=".xray-install.", dir=str(manifest.parent))
    try:
        os.fchmod(fd, 0o600)
        os.fchown(fd, 0, 0)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, manifest)
        directory_fd = os.open(manifest.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    regular_root_file(manifest, 0o600)
    print(f"OK: manifiesto de integridad actualizado: {manifest}")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="command", required=True)
    for name in ("verify", "record"):
        item = sub.add_parser(name)
        item.add_argument("--manifest", required=True)
        item.add_argument("--binary", required=True)
        item.add_argument("--geoip", required=True)
        item.add_argument("--geosite", required=True)
        item.add_argument("--architecture", required=True)
        if name == "record":
            item.add_argument("--version", required=True)
            item.add_argument("--package-sha256", required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "verify":
            verify(args)
        else:
            record(args)
    except IntegrityError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"ERROR: operación de integridad fallida: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
