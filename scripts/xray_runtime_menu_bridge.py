#!/usr/bin/env python3
"""Puente de menú hacia R-05 exclusivamente en un entorno fixture aislado."""
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from argparse import Namespace
from pathlib import Path

import xray_runtime_orchestrator as orchestrator
import xray_runtime_service_adapter as fixture_adapter


class MenuBridgeError(Exception):
    pass


def _fail(message: str) -> None:
    raise MenuBridgeError(message)


def _fixture_root(value: str) -> Path:
    root = Path(value)
    if not root.is_absolute():
        _fail("XRAY_RUNTIME_FIXTURE_ROOT debe ser una ruta absoluta.")
    current = Path(root.anchor)
    for part in root.parts[1:]:
        current /= part
        info = current.lstat()
        if stat.S_ISLNK(info.st_mode):
            _fail("La raíz fixture contiene un componente simbólico.")
    info = root.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_gid != 0
            or stat.S_IMODE(info.st_mode) not in {0o700, 0o755}):
        _fail("La raíz fixture debe ser un directorio root con permisos 0700 o 0755.")
    marker = root / ".xray-manager-r02-fixture"
    marker_info = marker.lstat()
    if (not stat.S_ISREG(marker_info.st_mode) or marker_info.st_uid != 0
            or marker_info.st_nlink != 1 or stat.S_IMODE(marker_info.st_mode) != 0o600):
        _fail("El marcador R-02 fixture no es seguro.")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    marker_fd = os.open(marker, flags)
    try:
        opened = os.fstat(marker_fd)
        if (not stat.S_ISREG(opened.st_mode) or opened.st_uid != 0 or opened.st_gid != 0
                or opened.st_nlink != 1 or stat.S_IMODE(opened.st_mode) != 0o600
                or opened.st_size > 4096):
            _fail("El marcador R-02 fixture cambió o tiene atributos inseguros.")
        marker_data = os.read(marker_fd, 4097)
        if len(marker_data) != opened.st_size or len(marker_data) > 4096:
            _fail("El marcador R-02 fixture cambió durante la lectura.")
    finally:
        os.close(marker_fd)
    value = json.loads(marker_data.decode("utf-8"))
    if value != {"schema_version": 1, "purpose": "xray-runtime-r02-isolated-fixture"}:
        _fail("El marcador no identifica un fixture R-02 reconocido.")
    return root.resolve(strict=True)


def _under(root: Path, value: str, label: str, *, allow_missing: bool = True) -> Path:
    path = Path(value)
    if not path.is_absolute():
        _fail(f"{label} debe ser una ruta absoluta.")
    resolved = path.resolve(strict=not allow_missing)
    try:
        resolved.relative_to(root)
    except ValueError:
        _fail(f"{label} debe permanecer dentro de XRAY_RUNTIME_FIXTURE_ROOT.")
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            if stat.S_ISLNK(current.lstat().st_mode):
                _fail(f"{label} contiene un componente simbólico.")
        except FileNotFoundError:
            if not allow_missing:
                raise
    return resolved


def apply_from_menu(args: argparse.Namespace) -> dict:
    if os.geteuid() != 0:
        _fail("El puente fixture R-05 requiere root.")
    root = _fixture_root(args.fixture_root)
    path_fields = (
        "profile_store", "master_key", "validation_store", "xray_binary", "service_state",
        "bindings_file", "staging_root", "lease_root", "connections_catalog", "connections_base",
        "vmess_base", "connection_lock", "certificate_base", "certificate_catalog", "managed_dir",
        "certificate_secrets_dir", "certificate_lock", "certificate_master_key", "service_root",
        "operation_store", "lifecycle_lock", "application_lock", "adapter_root", "active_profile_store",
    )
    paths = {}
    for name in path_fields:
        value = getattr(args, name, None)
        if value:
            paths[name] = _under(root, value, name)
    required = set(path_fields)
    if required - paths.keys():
        _fail("Faltan rutas fixture requeridas: " + ", ".join(sorted(required - paths.keys())))
    staging_args = Namespace(
        fixture_root=str(root), profile_store=str(paths["profile_store"]),
        master_key=str(paths["master_key"]), validation_store=str(paths["validation_store"]),
        profile_id=args.profile_id, revision=args.revision, xray_binary=str(paths["xray_binary"]),
        service_state=str(paths["service_state"]), bindings_file=str(paths["bindings_file"]),
        service_uid=args.service_uid, service_gid=args.service_gid,
        staging_root=str(paths["staging_root"]), lease_root=str(paths["lease_root"]),
        timeout=args.timeout, connections_catalog=str(paths["connections_catalog"]),
        connections_base=str(paths["connections_base"]), vmess_base=str(paths["vmess_base"]),
        connection_lock=str(paths["connection_lock"]), certificate_base=str(paths["certificate_base"]),
        certificate_catalog=str(paths["certificate_catalog"]), managed_dir=str(paths["managed_dir"]),
        certificate_secrets_dir=str(paths["certificate_secrets_dir"]),
        certificate_lock=str(paths["certificate_lock"]),
        certificate_master_key=str(paths["certificate_master_key"]),
    )
    result = orchestrator.apply_operation(
        staging_args=staging_args, service_root=paths["service_root"],
        operation_store=paths["operation_store"], lifecycle_lock=paths["lifecycle_lock"],
        application_lock=paths["application_lock"], lease_root=paths["lease_root"],
        service_uid=args.service_uid, service_gid=args.service_gid,
        adapter_root=paths["adapter_root"], confirm_restart=args.confirm_restart,
        active_profile_store=paths["active_profile_store"],
        service_backend=fixture_adapter,
    )
    result["execution_scope"] = "fixture_only"
    result["real_systemd_invoked"] = False
    result["real_xray_modified"] = False
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-root", required=True)
    for name in (
        "profile-store", "master-key", "validation-store", "xray-binary", "service-state",
        "bindings-file", "staging-root", "lease-root", "connections-catalog", "connections-base",
        "vmess-base", "connection-lock", "certificate-base", "certificate-catalog", "managed-dir",
        "certificate-secrets-dir", "certificate-lock", "certificate-master-key", "service-root",
        "operation-store", "lifecycle-lock", "application-lock", "adapter-root",
    ):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--active-profile-store", required=True)
    parser.add_argument("--profile-id", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--service-uid", required=True, type=int)
    parser.add_argument("--service-gid", required=True, type=int)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--confirm-restart", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = apply_from_menu(args)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (MenuBridgeError, orchestrator.RuntimeOrchestrationError, OSError, ValueError,
            KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
