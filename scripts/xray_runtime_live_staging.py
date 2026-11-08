#!/usr/bin/env python3
"""Staging TLS live aislado; no publica configuración ni controla el servicio.

La API productiva usa rutas fijas. No acepta fixture roots ni rutas alternativas
por CLI/entorno. La ejecución queda separada de R-02 y del menú.
"""
from __future__ import annotations

import fcntl
import grp
import hashlib
import json
import os
import pwd
import re
import shutil
import stat
import sys
import tempfile
from types import SimpleNamespace
from pathlib import Path
from typing import Any

import certificate_resolver
import xray_runtime_preflight
import xray_runtime_staging as staging_fixture
import xray_runtime_staging_core as staging_core
import xray_runtime_systemd_adapter

PROFILE_STORE = Path("/var/lib/xray-manager/profiles")
MASTER_KEY = Path("/etc/xray-manager/keys/master.key")
VALIDATION_STORE = Path("/var/lib/xray-manager/profile-validations")
BINDINGS_ROOT = Path("/var/lib/xray-manager/profile-bindings")
CONNECTIONS_CATALOG = Path("/var/lib/xray-manager/connections/connections.json")
CONNECTIONS_BASE = Path("/var/lib/xray-manager/connections")
VMESS_BASE = Path("/var/lib/xray-manager/vmess")
CONNECTION_LOCK = Path("/run/xray-manager/integrity.lock")
CERTIFICATE_BASE = Path("/var/lib/xray-manager/certificates")
CERTIFICATE_CATALOG = CERTIFICATE_BASE / "catalog.json"
CERTIFICATE_MANAGED = CERTIFICATE_BASE / "managed"
CERTIFICATE_SECRETS = CERTIFICATE_BASE / "secrets"
CERTIFICATE_LOCK = Path("/run/xray-manager-certificate-locks/catalog.lock")
CERTIFICATE_MASTER_KEY = MASTER_KEY
LEASE_ROOT = Path("/run/xray-manager-certificates")
STAGING_ROOT = Path("/run/xray-manager-runtime-staging")
LOCK_FILE = Path("/run/xray-manager-runtime-staging.lock")
XRAY_BINARY = Path("/usr/local/bin/xray")
UNIT_FILE = Path("/etc/systemd/system/xray.service")
CONFIG_FILE = Path("/etc/xray/config.json")
MAX_CONFIG = 16 * 1024 * 1024
MAX_MAPPING = 256 * 1024
PROFILE_RE = re.compile(r"profile-[0-9a-f]{32}\Z")
REVISION_RE = re.compile(r"r[0-9]{6}\Z")


class LiveStagingError(Exception):
    """Error controlado de staging live."""


def fail(message: str) -> None:
    raise LiveStagingError(message)


def _check_components(path: Path, *, allow_missing: bool = False) -> None:
    if not path.is_absolute():
        fail("La ruta administrada debe ser absoluta.")
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            if allow_missing:
                continue
            fail("Falta un componente de una ruta administrada.")
        except OSError as exc:
            raise LiveStagingError("No se pudo inspeccionar una ruta administrada.") from exc
        if stat.S_ISLNK(info.st_mode):
            fail("Una ruta administrada contiene un componente symlink.")


def _check_root_dir(path: Path, mode: int, *, allow_missing: bool = False) -> None:
    _check_components(path, allow_missing=allow_missing)
    if not path.exists():
        if allow_missing:
            return
        fail("Falta un directorio administrado.")
    st = path.lstat()
    if (not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode)
            or st.st_uid != 0 or st.st_gid != 0
            or stat.S_IMODE(st.st_mode) != mode):
        fail(f"Directorio administrado inseguro; se requiere root:root {mode:04o}.")


def _acquire_lock() -> int:
    _check_root_dir(LOCK_FILE.parent, 0o755)
    if LOCK_FILE.exists() or LOCK_FILE.is_symlink():
        st = LOCK_FILE.lstat()
        if (not stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode)
                or st.st_uid != 0 or st.st_gid != 0 or st.st_nlink != 1
                or stat.S_IMODE(st.st_mode) != 0o600):
            fail("El lock de staging live existente es inseguro.")
    fd = os.open(LOCK_FILE, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        os.fchown(fd, 0, 0)
        os.fchmod(fd, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        return fd
    except Exception:
        os.close(fd)
        raise


def _read_bindings(profile_id: str, revision: str) -> tuple[list[dict[str, str]], bytes, Path]:
    if not PROFILE_RE.fullmatch(profile_id) or not REVISION_RE.fullmatch(revision):
        fail("profile_id o revision inválido.")
    _check_root_dir(BINDINGS_ROOT, 0o700)
    profile_dir = BINDINGS_ROOT / profile_id
    _check_root_dir(profile_dir, 0o700)
    path = profile_dir / f"{revision}.json"
    _check_components(path)
    try:
        st = path.lstat()
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0))
    except OSError as exc:
        raise LiveStagingError("No se pudo abrir el mapping de perfil/revisión.") from exc
    try:
        current = os.fstat(fd)
        if ((current.st_dev, current.st_ino) != (st.st_dev, st.st_ino)
                or not stat.S_ISREG(current.st_mode) or current.st_uid != 0
                or current.st_gid != 0 or current.st_nlink != 1
                or stat.S_IMODE(current.st_mode) != 0o600
                or not 1 <= current.st_size <= MAX_MAPPING):
            fail("El mapping TLS debe ser regular, root:root 0600 y estar dentro del límite.")
        chunks, total = [], 0
        while True:
            part = os.read(fd, 65536)
            if not part:
                break
            chunks.append(part)
            total += len(part)
            if total > MAX_MAPPING:
                fail("El mapping TLS excede el tamaño permitido.")
        data = b"".join(chunks)
        if total != current.st_size:
            fail("El mapping TLS cambió durante la lectura.")
    finally:
        os.close(fd)
    bindings, parsed_data = staging_fixture._read_mapping(path)
    if parsed_data != data:
        fail("El mapping TLS cambió entre lecturas; se aborta por TOCTOU.")
    return bindings, data, path


def _service_identity(observed: dict[str, Any]) -> tuple[int, int]:
    if (observed.get("unit") != "xray.service"
            or observed.get("load_state") != "loaded"
            or observed.get("fragment_path") != str(UNIT_FILE)
            or observed.get("user") != "xray"
            or observed.get("group") != "xray"
            or observed.get("read_only") is not True
            or observed.get("need_daemon_reload") != "no"
            or observed.get("drop_in_paths") not in ("", None)
            or observed.get("service_type") != "simple"
            or observed.get("active_state") not in {"active", "inactive"}):
        fail("xray.service no satisface el contrato administrado requerido para staging.")
    if observed["active_state"] == "active" and (
            not isinstance(observed.get("main_pid"), int) or observed["main_pid"] <= 0
            or not isinstance(observed.get("invocation_id"), str)
            or not re.fullmatch(r"[0-9a-fA-F]{32}", observed["invocation_id"])):
        fail("xray.service activo no tiene PID e InvocationID verificables.")
    if observed["active_state"] == "inactive" and observed.get("main_pid") not in (None, 0):
        fail("xray.service inactivo presenta un MainPID incompatible.")
    try:
        uid, gid = certificate_resolver.service_identity("xray.service")
        user = pwd.getpwuid(uid)
        group = grp.getgrgid(gid)
    except (certificate_resolver.ResolverError, KeyError) as exc:
        raise LiveStagingError("No se pudo verificar la identidad real xray:xray.") from exc
    if user.pw_name != "xray" or group.gr_name != "xray" or uid <= 0 or gid <= 0:
        fail("La identidad real del servicio no es exactamente xray:xray.")
    return uid, gid


def _same_service_generation(before: dict[str, Any], after: dict[str, Any]) -> bool:
    fields = ("unit", "load_state", "fragment_path", "user", "group",
              "need_daemon_reload", "drop_in_paths", "service_type",
              "unit_file_state", "active_state", "result", "exec_main_status",
              "invocation_id", "main_pid", "runtime_config_sha256",
              "generation_evidence", "loaded_generation_id")
    return all(before.get(field) == after.get(field) for field in fields)


def _write_file(path: Path, data: bytes, gid: int, mode: int) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), mode)
    try:
        os.fchown(fd, 0, gid)
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(fd)
    finally:
        os.close(fd)


def _prepare_staging_root() -> None:
    _check_root_dir(STAGING_ROOT.parent, 0o755)
    _check_components(STAGING_ROOT, allow_missing=True)
    if not STAGING_ROOT.exists():
        os.mkdir(STAGING_ROOT, 0o711)
        os.chown(STAGING_ROOT, 0, 0)
        os.chmod(STAGING_ROOT, 0o711)
        parent_fd = os.open(STAGING_ROOT.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    _check_root_dir(STAGING_ROOT, 0o711)


def stage_live(profile_id: str, revision: str, *, timeout: int = 20) -> dict[str, Any]:
    """Prepara configuración y leases reales sin publicar ni iniciar xray.service."""
    if os.geteuid() != 0:
        fail("stage_live requiere root.")
    if not PROFILE_RE.fullmatch(profile_id or "") or not REVISION_RE.fullmatch(revision or ""):
        fail("profile_id o revision inválido.")
    if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 120:
        fail("Timeout fuera del rango permitido.")

    lock_fd = _acquire_lock()
    leases: list[dict[str, str]] = []
    staging_dir: Path | None = None
    try:
        initial_service = xray_runtime_systemd_adapter.status(
            unit_file=UNIT_FILE, config_file=CONFIG_FILE
        )
        service_uid, service_gid = _service_identity(initial_service)
        preflight = xray_runtime_preflight.preflight_profile(
            str(PROFILE_STORE), str(MASTER_KEY), str(VALIDATION_STORE),
            profile_id, revision, str(XRAY_BINARY),
        )
        content = preflight.get("profile_content")
        if not isinstance(content, bytes) or hashlib.sha256(content).hexdigest() != preflight.get("content_sha256"):
            fail("El preflight no devolvió el contenido exacto de la revisión.")
        document = staging_fixture._strict_json(content, "La revisión de perfil")
        bindings, mapping_bytes, mapping_path = _read_bindings(profile_id, revision)
        try:
            inbound_by_tag = staging_core.validate_profile_bindings(document, bindings)
        except staging_core.StagingCoreError as exc:
            raise LiveStagingError(str(exc)) from exc

        _prepare_staging_root()
        staging_dir = Path(tempfile.mkdtemp(prefix="live-", dir=STAGING_ROOT))
        os.chown(staging_dir, 0, service_gid)
        os.chmod(staging_dir, 0o750)

        for binding in bindings:
            tag, connection_id = binding["inbound_tag"], binding["connection_id"]
            if tag not in inbound_by_tag:
                fail("Una asociación apunta a un inbound TLS inexistente.")
            certificate_id, protocol = staging_fixture._connection_certificate_id(
                SimpleNamespace(
                    connections_catalog=str(CONNECTIONS_CATALOG),
                    connections_base=str(CONNECTIONS_BASE),
                    vmess_base=str(VMESS_BASE),
                ),
                connection_id,
            )
            lease = certificate_resolver.prepare(
                connection_id=connection_id, certificate_id=certificate_id,
                connections_catalog=CONNECTIONS_CATALOG,
                connections_base=CONNECTIONS_BASE, vmess_base=VMESS_BASE,
                connection_lock=CONNECTION_LOCK,
                certificate_catalog=CERTIFICATE_CATALOG,
                certificate_base=CERTIFICATE_BASE, managed_dir=CERTIFICATE_MANAGED,
                certificate_secrets_dir=CERTIFICATE_SECRETS,
                certificate_lock=CERTIFICATE_LOCK,
                master_key_file=CERTIFICATE_MASTER_KEY,
                runtime_root=LEASE_ROOT, service_uid=service_uid, service_gid=service_gid,
            )
            leases.append(lease)
            try:
                staging_core.inject_tls_lease(
                    document, tag, connection_id, certificate_id, protocol, lease
                )
            except staging_core.StagingCoreError as exc:
                raise LiveStagingError(str(exc)) from exc

        final_preflight = xray_runtime_preflight.preflight_profile(
            str(PROFILE_STORE), str(MASTER_KEY), str(VALIDATION_STORE),
            profile_id, revision, str(XRAY_BINARY),
        )
        current_bindings, current_mapping_bytes, _ = _read_bindings(profile_id, revision)
        final_service = xray_runtime_systemd_adapter.status(
            unit_file=UNIT_FILE, config_file=CONFIG_FILE
        )
        final_identity = _service_identity(final_service)
        if final_identity != (service_uid, service_gid):
            fail("La identidad xray:xray cambió durante staging; se aborta por TOCTOU.")
        if (final_preflight.get("validation_id") != preflight.get("validation_id")
                or final_preflight.get("content_sha256") != preflight.get("content_sha256")
                or final_preflight.get("profile_content") != content
                or current_mapping_bytes != mapping_bytes or current_bindings != bindings
                or not _same_service_generation(initial_service, final_service)):
            fail("Perfil, mapping o unidad cambió durante staging; se aborta por TOCTOU.")

        staged_bytes = (json.dumps(
            document, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ) + "\n").encode()
        if not 1 <= len(staged_bytes) <= MAX_CONFIG:
            fail("La configuración staged excede el límite.")
        config_path = staging_dir / "config.json"
        _write_file(config_path, staged_bytes, service_gid, 0o640)
        staging_fixture._service_run(XRAY_BINARY, config_path, service_uid, service_gid, timeout)

        manifest = {
            "schema_version": 1, "environment": "live", "status": "STAGED",
            "profile_id": profile_id, "revision": revision,
            "validation_id": preflight["validation_id"],
            "profile_content_sha256": preflight["content_sha256"],
            "mapping_file": str(mapping_path),
            "mapping_sha256": hashlib.sha256(mapping_bytes).hexdigest(),
            "bindings": bindings,
            "leases": [{
                "lease_id": item["lease_id"], "connection_id": item["connection_id"],
                "protocol": item["protocol"], "certificate_id": item["certificate_id"],
            } for item in leases],
            "staging_dir": str(staging_dir),
            "config_sha256": hashlib.sha256(staged_bytes).hexdigest(),
            "config_size_bytes": len(staged_bytes),
            "service_identity": {"user": "xray", "group": "xray", "uid": service_uid, "gid": service_gid},
            "systemd_observation": {
                "unit": initial_service["unit"], "load_state": initial_service["load_state"],
                "active_state": initial_service["active_state"],
                "invocation_id": initial_service.get("invocation_id"),
                "main_pid": initial_service.get("main_pid"),
                "fragment_path": initial_service["fragment_path"],
            },
            "xray_binary": final_preflight["xray"],
            "native_validation": "PASS",
            "runtime_published": False,
            "service_started": False,
        }
        manifest_bytes = (json.dumps(manifest, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
        _write_file(staging_dir / "manifest.json", manifest_bytes, service_gid, 0o640)
        dir_fd = os.open(staging_dir, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
        return {
            "status": "STAGED", "profile_id": profile_id, "revision": revision,
            "validation_id": preflight["validation_id"], "staging_dir": str(staging_dir),
            "config_path": str(config_path), "manifest_path": str(staging_dir / "manifest.json"),
            "config_sha256": manifest["config_sha256"],
            "lease_ids": [item["lease_id"] for item in leases],
            "runtime_published": False, "service_started": False,
        }
    except Exception as original_error:
        cleanup_failures = []
        if staging_dir is not None and staging_dir.exists() and not staging_dir.is_symlink():
            try:
                shutil.rmtree(staging_dir)
            except OSError:
                cleanup_failures.append("staging:" + staging_dir.name)
        for item in reversed(leases):
            try:
                certificate_resolver.cleanup(LEASE_ROOT, item["lease_id"], service_gid)
            except Exception:
                cleanup_failures.append(item.get("lease_id", "unknown-lease"))
        if cleanup_failures:
            fail("Falló stage_live y la limpieza compensatoria quedó incompleta; recuperación requerida: "
                 + ", ".join(cleanup_failures))
        raise original_error
    finally:
        os.close(lock_fd)


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-id", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args()
    try:
        result = stage_live(args.profile_id, args.revision, timeout=args.timeout)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (LiveStagingError, staging_fixture.StagingError, certificate_resolver.ResolverError,
            xray_runtime_preflight.RuntimePreflightError,
            xray_runtime_systemd_adapter.SystemdAdapterError,
            OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
