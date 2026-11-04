#!/usr/bin/env python3
"""Almacén privado de candidatos runtime originados en perfiles.

No publica /etc/xray/config.json, no prepara systemd y no inicia Xray.
La activación efectiva queda reservada al flujo de perfiles de Etapa 5.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MAX_CONFIG_BYTES = 16 * 1024 * 1024
PROFILE_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class CandidateError(Exception):
    pass


def fail(message: str) -> None:
    raise CandidateError(message)


def ensure_no_symlink_components(path: Path) -> None:
    absolute = path.absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        try:
            if current.is_symlink():
                fail(f"componente simbólico no permitido: {current}")
        except OSError as exc:
            fail(f"no se pudo inspeccionar la ruta: {exc}")


def read_regular_file(path: Path, max_bytes: int) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        fail(f"no se pudo abrir el archivo de entrada: {exc.strerror}")
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
            fail("el candidato debe ser un archivo regular sin hardlinks")
        if st.st_size < 1 or st.st_size > max_bytes:
            fail("tamaño del candidato fuera de los límites permitidos")
        chunks = []
        remaining = max_bytes + 1
        while remaining:
            chunk = os.read(fd, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if len(data) != st.st_size or len(data) > max_bytes:
            fail("el candidato cambió durante su lectura o excede el límite")
        return data
    finally:
        os.close(fd)


def validate_candidate(data: bytes) -> None:
    try:
        value = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError):
        fail("el candidato no contiene JSON válido")
    if not isinstance(value, dict):
        fail("la configuración Xray debe ser un objeto JSON")
    if not isinstance(value.get("inbounds"), list) or not isinstance(value.get("outbounds"), list):
        fail("la configuración Xray debe contener inbounds y outbounds como arreglos")


def validate_with_xray(binary: Path, candidate: Path, timeout: int) -> None:
    ensure_no_symlink_components(binary)
    try:
        st = binary.stat()
    except OSError:
        fail("no se encontró el binario Xray especificado")
    if (not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or st.st_uid != 0
            or stat.S_IMODE(st.st_mode) & 0o022 or not os.access(binary, os.X_OK)):
        fail("el binario Xray debe ser regular, root-owned, no modificable por grupo/otros y ejecutable")
    try:
        result = subprocess.run(
            [str(binary), "run", "-test", "-config", str(candidate)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={"PATH": "/usr/bin:/bin", "HOME": "/nonexistent", "LANG": "C"},
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        fail("la validación nativa de Xray excedió el tiempo límite")
    except OSError:
        fail("no fue posible ejecutar el validador Xray")
    if result.returncode != 0:
        fail(f"Xray rechazó el candidato (código {result.returncode}); no se almacenó")


def write_private(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(fd)
    finally:
        os.close(fd)


def fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def stage_candidate(
    candidate_path: Path,
    binary_path: Path,
    store_root: Path,
    profile_id: str,
    profile_revision: str,
    timeout: int = 20,
) -> dict[str, Any]:
    if os.geteuid() != 0:
        fail("el staging de candidatos runtime requiere root")
    if not PROFILE_TOKEN.fullmatch(profile_id) or not PROFILE_TOKEN.fullmatch(profile_revision):
        fail("identificador o revisión de perfil con formato no permitido")
    if timeout < 1 or timeout > 120:
        fail("timeout fuera del rango permitido")

    ensure_no_symlink_components(candidate_path)
    data = read_regular_file(candidate_path, MAX_CONFIG_BYTES)
    validate_candidate(data)

    ensure_no_symlink_components(store_root)
    store_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    store_stat = store_root.stat()
    if (store_root.is_symlink() or not stat.S_ISDIR(store_stat.st_mode)
            or store_stat.st_uid != 0):
        fail("el almacén de candidatos debe ser un directorio real propiedad de root")
    os.chmod(store_root, 0o700)

    lock_path = store_root / ".candidates.lock"
    lock_fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        lock_stat = os.fstat(lock_fd)
        if (not stat.S_ISREG(lock_stat.st_mode) or lock_stat.st_nlink != 1
                or lock_stat.st_uid != 0):
            fail("archivo de bloqueo inseguro")
        os.fchmod(lock_fd, 0o600)
        fcntl.flock(lock_fd, fcntl.LOCK_EX)

        profile_dir = store_root / profile_id
        profile_dir.mkdir(mode=0o700, exist_ok=True)
        profile_stat = profile_dir.stat()
        if (profile_dir.is_symlink() or not stat.S_ISDIR(profile_stat.st_mode)
                or profile_stat.st_uid != 0):
            fail("directorio de perfil inseguro: debe ser real y propiedad de root")
        os.chmod(profile_dir, 0o700)

        final_dir = profile_dir / profile_revision
        if final_dir.exists() or final_dir.is_symlink():
            fail("ya existe un candidato para este perfil y revisión; no se sobrescribirá")

        temp_dir = Path(tempfile.mkdtemp(prefix=".candidate-", dir=profile_dir))
        try:
            os.chmod(temp_dir, 0o700)
            staged_config = temp_dir / "config.json"
            staged_manifest = temp_dir / "manifest.json"
            write_private(staged_config, data)
            # Xray valida exactamente los bytes que se almacenarán, no se vuelve a leer
            # el archivo de origen (evita una sustitución TOCTOU entre lectura y prueba).
            validate_with_xray(binary_path, staged_config, timeout)
            manifest = {
                "schema_version": 1,
                "source": {"type": "profile", "profile_id": profile_id, "profile_revision": profile_revision},
                "candidate": {"file": "config.json", "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()},
                "validation": {"json": "pass", "xray_native": "pass", "binary": str(binary_path)},
                "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            }
            manifest_bytes = (json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode()
            write_private(staged_manifest, manifest_bytes)
            fsync_directory(temp_dir)
            os.rename(temp_dir, final_dir)
            fsync_directory(profile_dir)
        except Exception:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            raise

        return {
            "status": "STAGED",
            "profile_id": profile_id,
            "profile_revision": profile_revision,
            "config_path": str(final_dir / "config.json"),
            "manifest_path": str(final_dir / "manifest.json"),
            "sha256": manifest["candidate"]["sha256"],
            "size_bytes": len(data),
            "runtime_published": False,
            "service_started": False,
        }
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    stage = sub.add_parser("stage", help="valida y almacena un candidato de perfil sin aplicarlo")
    stage.add_argument("--candidate", required=True, type=Path)
    stage.add_argument("--xray-binary", default=os.environ.get("XRAY_RUNTIME_BINARY", "/usr/local/bin/xray"), type=Path)
    stage.add_argument("--store", default=os.environ.get("XRAY_RUNTIME_CANDIDATES_DIR", "/var/lib/xray-manager/runtime/candidates"), type=Path)
    stage.add_argument("--profile-id", required=True)
    stage.add_argument("--profile-revision", required=True)
    stage.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args()

    try:
        result = stage_candidate(
            args.candidate, args.xray_binary, args.store,
            args.profile_id, args.profile_revision, args.timeout,
        )
    except CandidateError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError) as exc:
        print(f"ERROR: operación de staging fallida ({type(exc).__name__})", file=sys.stderr)
        return 1

    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())