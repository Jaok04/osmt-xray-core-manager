#!/usr/bin/env python3
"""Contrato fixture-only de directorios para supervisor root y Xray no privilegiado.

No crea ni modifica rutas del host. Las funciones de preparación sólo aceptan
un árbol temporal marcado explícitamente como fixture.
"""
from __future__ import annotations

import os
import pathlib
import stat
from typing import Any


class DirectoryContractError(Exception):
    """El layout de directorios no cumple el contrato esperado."""


SERVICE_USER = "xray"
SERVICE_GROUP = "xray"
STATE_DIRECTORY = "/var/lib/xray"
RUNTIME_DIRECTORY = "/run/xray"
EVIDENCE_PARENT = "/var/lib/xray-manager"
EVIDENCE_DIRECTORY = "/var/lib/xray-manager/evidence"
EVIDENCE_FILE_MODE = 0o600
SERVICE_DIRECTORY_MODE = 0o770
ROOT_PRIVATE_MODE = 0o700


def _fail(message: str) -> None:
    raise DirectoryContractError(message)


def _validate_gid(service_gid: int) -> None:
    if type(service_gid) is not int or service_gid <= 0:
        _fail("El GID del grupo de servicio debe ser un entero positivo.")


def build_directory_contract(service_gid: int) -> dict[str, Any]:
    """Devuelve el contrato declarativo propuesto; no toca el sistema."""
    _validate_gid(service_gid)
    return {
        "schema": 1,
        "environment": "fixture_contract",
        "identity": {
            "supervisor_user": "root",
            "supervisor_uid": 0,
            "service_user": SERVICE_USER,
            "service_group": SERVICE_GROUP,
            "service_gid": service_gid,
        },
        "systemd": {
            "User": "root",
            "Group": SERVICE_GROUP,
            "StateDirectory": "xray",
            "StateDirectoryMode": "0770",
            "RuntimeDirectory": "xray",
            "RuntimeDirectoryMode": "0770",
            "ProtectSystem": "strict",
            "NoNewPrivileges": "true",
            "CapabilityBoundingSet": (
                "CAP_CHOWN CAP_SETUID CAP_SETGID CAP_NET_BIND_SERVICE"
            ),
            "AmbientCapabilities": (
                "CAP_CHOWN CAP_SETUID CAP_SETGID CAP_NET_BIND_SERVICE"
            ),
            "ReadWritePaths": [
                STATE_DIRECTORY,
                RUNTIME_DIRECTORY,
                EVIDENCE_DIRECTORY,
            ],
        },
        "directories": [
            {"path": STATE_DIRECTORY, "owner_uid": 0, "owner_gid": service_gid,
             "mode": SERVICE_DIRECTORY_MODE, "service_group_write": True,
             "lifecycle": "persistent_state"},
            {"path": RUNTIME_DIRECTORY, "owner_uid": 0, "owner_gid": service_gid,
             "mode": SERVICE_DIRECTORY_MODE, "service_group_write": True,
             "lifecycle": "systemd_runtime"},
            {"path": EVIDENCE_PARENT, "owner_uid": 0, "owner_gid": 0,
             "mode": ROOT_PRIVATE_MODE, "service_group_write": False,
             "lifecycle": "persistent_parent"},
            {"path": EVIDENCE_DIRECTORY, "owner_uid": 0, "owner_gid": 0,
             "mode": ROOT_PRIVATE_MODE, "service_group_write": False,
             "lifecycle": "persistent_evidence"},
        ],
        "evidence_file": {
            "owner_uid": 0,
            "owner_gid": 0,
            "mode": EVIDENCE_FILE_MODE,
            "contains_config_bytes": False,
            "contains_secrets": False,
        },
    }


def _fixture_root(root: pathlib.Path) -> pathlib.Path:
    root = pathlib.Path(root)
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        _fail("La raíz fixture debe ser un directorio absoluto no simbólico.")
    root_info = root.lstat()
    if (not stat.S_ISDIR(root_info.st_mode) or root_info.st_uid != os.geteuid()
            or stat.S_IMODE(root_info.st_mode) & 0o022):
        _fail("La raíz fixture tiene propietario o permisos inseguros.")
    marker = root / ".xray-manager-fixture"
    try:
        info = marker.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) != 0o600
                or marker.read_text(encoding="utf-8") != "fixture-only\n"):
            _fail("El marcador de raíz fixture no es válido.")
    except OSError as exc:
        raise DirectoryContractError("No se pudo validar la raíz fixture.") from exc
    return root


def _mapped_path(root: pathlib.Path, absolute_path: str) -> pathlib.Path:
    if not isinstance(absolute_path, str) or not absolute_path.startswith("/"):
        _fail("La ruta del contrato debe ser absoluta.")
    parts = pathlib.PurePosixPath(absolute_path).parts[1:]
    if not parts or any(part in {".", ".."} for part in parts):
        _fail("La ruta del contrato contiene componentes inválidos.")
    return root.joinpath(*parts)


def _validate_parent_components(root: pathlib.Path, path: pathlib.Path) -> None:
    current = root
    for part in path.relative_to(root).parts[:-1]:
        current = current / part
        try:
            info = current.lstat()
        except OSError as exc:
            raise DirectoryContractError("Falta un directorio padre del layout fixture.") from exc
        if (not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode)
                or info.st_uid != 0 or info.st_gid != 0
                or stat.S_IMODE(info.st_mode) & 0o022):
            _fail("Un directorio padre del layout fixture no es root-owned o permite escritura no confiable.")


def validate_fixture_layout(root: pathlib.Path, service_gid: int) -> dict[str, Any]:
    """Valida propietarios/modos reales dentro de un árbol fixture existente."""
    root = _fixture_root(root)
    contract = build_directory_contract(service_gid)
    for item in contract["directories"]:
        path = _mapped_path(root, item["path"])
        _validate_parent_components(root, path)
        current = root
        for part in path.relative_to(root).parts:
            current = current / part
            try:
                component = current.lstat()
            except OSError as exc:
                raise DirectoryContractError("Falta un directorio requerido del layout fixture.") from exc
            if stat.S_ISLNK(component.st_mode):
                _fail("El layout fixture contiene un componente simbólico.")
        info = path.lstat()
        if (not stat.S_ISDIR(info.st_mode)
                or (info.st_uid, info.st_gid) != (item["owner_uid"], item["owner_gid"])
                or stat.S_IMODE(info.st_mode) != item["mode"]):
            _fail("Propietario, grupo, tipo o modo incorrecto en un directorio del contrato.")
    return {"valid": True, "environment": "fixture", "schema": contract["schema"],
            "checked_directories": len(contract["directories"])}


def prepare_fixture_layout(root: pathlib.Path, service_gid: int) -> dict[str, Any]:
    """Crea sólo directorios ausentes bajo una raíz fixture; nunca repara drift."""
    root = _fixture_root(root)
    contract = build_directory_contract(service_gid)
    for item in contract["directories"]:
        path = _mapped_path(root, item["path"])
        # Todos los padres también deben ser directorios reales, nunca symlinks.
        missing: list[pathlib.Path] = []
        current = path
        while current != root:
            if current.exists() or current.is_symlink():
                break
            missing.append(current)
            current = current.parent
        if current != root:
            if current.is_symlink() or not current.is_dir():
                _fail("Un componente padre del layout fixture no es un directorio seguro.")
            if current != path:
                _validate_parent_components(root, current / "__fixture_target__")
        for directory in reversed(missing):
            if directory == path:
                directory.mkdir(mode=0o700)
            else:
                # Simula sólo los padres estándar /var, /var/lib y /run.
                directory.mkdir(mode=0o755)
                os.chown(directory, 0, 0)
                os.chmod(directory, 0o755)
        if missing:
            os.chown(path, item["owner_uid"], item["owner_gid"])
            os.chmod(path, item["mode"])
        else:
            info = path.lstat()
            if (not stat.S_ISDIR(info.st_mode)
                    or (info.st_uid, info.st_gid) != (item["owner_uid"], item["owner_gid"])
                    or stat.S_IMODE(info.st_mode) != item["mode"]):
                _fail("El layout existente difiere del contrato; no se reparará automáticamente.")
    return validate_fixture_layout(root, service_gid)
