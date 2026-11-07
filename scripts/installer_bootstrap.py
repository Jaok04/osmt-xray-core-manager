#!/usr/bin/env python3
"""Download and verify one immutable private GitHub repository snapshot."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tarfile
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_ROOT = "https://api.github.com"
MAX_ARCHIVE_BYTES = 200 * 1024 * 1024
MAX_TOTAL_FILE_BYTES = 180 * 1024 * 1024
MAX_FILES = 10000
SUPPORTED_MODES = {"100644": 0o644, "100755": 0o755}
REQUIRED_FILES = {
    "install.sh",
    "bin/xray-manager",
    "config/paths.sh",
    "modules/main_menu.sh",
    "lib/json_store.sh",
    "lib/operation_lock.sh",
}


class BootstrapError(Exception):
    """A fail-closed bootstrap validation or transport error."""


def git_blob_sha1(data: bytes) -> str:
    header = b"blob " + str(len(data)).encode("ascii") + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def _request_bytes(
    url: str,
    token: str,
    *,
    accept: str = "application/vnd.github+json",
    opener: Callable[..., Any] = urlopen,
    limit: int = MAX_ARCHIVE_BYTES,
) -> bytes:
    request = Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": accept,
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "xray-core-manager-installer",
        },
    )
    try:
        with opener(request, timeout=90) as response:
            data = response.read(limit + 1)
    except HTTPError as exc:
        if exc.code in (401, 403, 404):
            raise BootstrapError(
                "GitHub rechazó el acceso. Verifica el PAT y Contents: Read-only "
                "para Jaok04/xray-core-manager."
            ) from None
        raise BootstrapError(f"GitHub respondió HTTP {exc.code}.") from None
    except (URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", None)
        detail = str(reason or exc)
        raise BootstrapError(f"No se pudo conectar con GitHub: {detail}") from None
    if len(data) > limit:
        raise BootstrapError("La respuesta de GitHub supera el límite de tamaño permitido.")
    return data



def _expected_blobs(tree: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if tree.get("truncated") is not False:
        raise BootstrapError("El árbol Git está truncado o no declara truncamiento=false.")
    entries = tree.get("tree")
    if not isinstance(entries, list) or len(entries) > MAX_FILES:
        raise BootstrapError("El árbol Git está ausente o supera el límite de archivos.")

    blobs: dict[str, dict[str, Any]] = {}
    seen_paths: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise BootstrapError("El árbol Git contiene una entrada inválida.")
        path = entry.get("path")
        if not isinstance(path, str) or not path or "\\" in path or "\x00" in path:
            raise BootstrapError("El árbol Git contiene una ruta inválida.")
        raw_parts = path.split("/")
        parsed = PurePosixPath(path)
        if parsed.is_absolute() or any(part in ("", ".", "..") for part in raw_parts):
            raise BootstrapError("El árbol Git contiene una ruta insegura.")
        if path in seen_paths:
            raise BootstrapError("El árbol Git contiene rutas duplicadas.")
        seen_paths.add(path)

        kind = entry.get("type")
        mode = entry.get("mode")
        if kind == "tree" and mode == "040000":
            continue
        if kind != "blob" or mode not in SUPPORTED_MODES:
            raise BootstrapError(
                "El repositorio contiene un tipo de archivo no admitido "
                "(symlink, submódulo o modo especial)."
            )
        sha = entry.get("sha")
        size = entry.get("size")
        if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise BootstrapError("El árbol Git contiene un SHA de blob inválido.")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise BootstrapError("El árbol Git contiene un tamaño inválido.")
        blobs[path] = {"sha": sha, "size": size, "mode": mode}
    if not REQUIRED_FILES.issubset(blobs):
        raise BootstrapError("El árbol descargado no contiene todos los archivos esenciales del Manager.")
    if sum(item["size"] for item in blobs.values()) > MAX_TOTAL_FILE_BYTES:
        raise BootstrapError("El contenido del repositorio supera el tamaño total permitido.")
    return blobs


def extract_verified_tarball(
    archive: bytes,
    tree: dict[str, Any],
    destination: str | os.PathLike[str],
) -> int:
    blobs = _expected_blobs(tree)
    root = Path(destination)
    if not root.is_dir() or any(root.iterdir()):
        raise BootstrapError("El destino temporal de extracción no está vacío.")

    seen: set[str] = set()
    root_prefix: str | None = None
    total_bytes = 0
    try:
        tar = tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz")
    except (tarfile.TarError, OSError):
        raise BootstrapError("El archivo de distribución de GitHub no es un tar.gz válido.") from None

    with tar:
        for member in tar:
            name = member.name
            if not isinstance(name, str) or not name or name.startswith("/") or "\\" in name or "\x00" in name:
                raise BootstrapError("El tarball contiene una ruta absoluta o inválida.")
            raw_name = name[:-1] if name.endswith("/") else name
            raw_parts = raw_name.split("/")
            parts = PurePosixPath(raw_name).parts
            if not raw_parts or any(part in ("", ".", "..") for part in raw_parts):
                raise BootstrapError("El tarball contiene traversal o componentes de ruta inválidos.")
            if root_prefix is None:
                root_prefix = parts[0]
            if parts[0] != root_prefix:
                raise BootstrapError("El tarball contiene más de un directorio raíz.")
            relative = "/".join(parts[1:])
            if not relative:
                if not member.isdir():
                    raise BootstrapError("La raíz del tarball no es un directorio.")
                continue
            if member.isdir():
                if relative not in blobs and not any(path.startswith(relative + "/") for path in blobs):
                    raise BootstrapError("El tarball contiene un directorio inesperado.")
                continue
            if not member.isfile():
                raise BootstrapError("El tarball contiene symlink, hardlink o archivo especial.")
            if relative not in blobs:
                raise BootstrapError(f"El tarball contiene un archivo no versionado: {relative}")
            if relative in seen:
                raise BootstrapError("El tarball contiene archivos duplicados.")
            expected = blobs[relative]
            if member.size != expected["size"]:
                raise BootstrapError(f"Tamaño incorrecto para {relative}.")
            source = tar.extractfile(member)
            if source is None:
                raise BootstrapError(f"No se pudo leer {relative} del tarball.")
            with source:
                data = source.read(expected["size"] + 1)
            if len(data) != expected["size"]:
                raise BootstrapError(f"Lectura incompleta o tamaño excesivo para {relative}.")
            if git_blob_sha1(data) != expected["sha"]:
                raise BootstrapError(f"La integridad Git del archivo {relative} no coincide.")
            target = root.joinpath(*PurePosixPath(relative).parts)
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
            if target.exists() or target.is_symlink():
                raise BootstrapError("La extracción detectó una colisión de rutas.")
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            fd = os.open(target, flags, SUPPORTED_MODES[expected["mode"]])
            with os.fdopen(fd, "wb") as output:
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
            os.chmod(target, SUPPORTED_MODES[expected["mode"]])
            seen.add(relative)
            total_bytes += len(data)
            if total_bytes > MAX_TOTAL_FILE_BYTES:
                raise BootstrapError("El tarball supera el tamaño total permitido.")

    missing = set(blobs) - seen
    if missing:
        first = sorted(missing)[0]
        raise BootstrapError(f"El tarball está incompleto; falta {first}.")
    for directory, _, _ in os.walk(root, topdown=False):
        os.chmod(directory, 0o755)
    return len(seen)


def download_snapshot(
    *,
    repo: str,
    commit: str,
    tree_sha: str,
    tree: dict[str, Any],
    token: str,
    destination: str | os.PathLike[str],
    opener: Callable[..., Any] = urlopen,
) -> int:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise BootstrapError("Identificador de repositorio inválido.")
    if not re.fullmatch(r"[0-9a-f]{40}", commit) or not re.fullmatch(r"[0-9a-f]{40}", tree_sha):
        raise BootstrapError("El commit o tree SHA no tiene formato válido.")
    if tree.get("sha") != tree_sha:
        raise BootstrapError("El SHA del árbol no coincide con el commit resuelto.")
    _expected_blobs(tree)
    archive_url = f"{API_ROOT}/repos/{repo}/tarball/{commit}"
    archive = _request_bytes(archive_url, token, accept="application/vnd.github+json", opener=opener)
    return extract_verified_tarball(archive, tree, destination)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--tree-sha", required=True)
    parser.add_argument("--tree-file", required=True)
    parser.add_argument("--destination", required=True)
    args = parser.parse_args()
    token = os.environ.get("XRAY_MANAGER_GITHUB_TOKEN", "")
    if not token:
        print("ERROR: falta XRAY_MANAGER_GITHUB_TOKEN.", file=sys.stderr)
        return 2
    destination_created = False
    try:
        with open(args.tree_file, "r", encoding="utf-8") as source:
            tree = json.load(source)
        Path(args.destination).mkdir(mode=0o700, parents=False, exist_ok=False)
        destination_created = True
        count = download_snapshot(
            repo=args.repo,
            commit=args.commit,
            tree_sha=args.tree_sha,
            tree=tree,
            token=token,
            destination=args.destination,
        )
    except (BootstrapError, OSError, json.JSONDecodeError) as exc:
        if destination_created:
            shutil.rmtree(args.destination, ignore_errors=True)
        print(f"ERROR: no se pudo preparar la distribución: {exc}", file=sys.stderr)
        return 1
    finally:
        token = ""
        os.environ.pop("XRAY_MANAGER_GITHUB_TOKEN", None)
    print(f"[OK] Snapshot verificado: {count} archivos; commit {args.commit}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
