#!/usr/bin/env python3
"""Publicación atómica mínima de configuración live; nunca controla el servicio.

Sólo publica una configuración staged y validada. No inicia/reinicia Xray,
no habilita systemd y no integra el flujo al menú.
"""
from __future__ import annotations

import fcntl
import grp
import hashlib
import json
import os
import pwd
import re
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any

import certificate_resolver
import xray_runtime_live_journal as live_journal
import xray_runtime_staging as staging
import xray_runtime_systemd_adapter as systemd_adapter

CONFIG_FILE = Path("/etc/xray/config.json")
CONFIG_DIR = Path("/etc/xray")
UNIT_FILE = Path("/etc/systemd/system/xray.service")
XRAY_BINARY = Path("/usr/local/bin/xray")
STAGING_ROOT = Path("/run/xray-manager-runtime-staging")
OPERATION_ROOT = live_journal.LIVE_ROOT
LIFECYCLE_LOCK = Path("/run/lock/xray-manager-lifecycle.lock")
INTEGRITY_LOCK = Path("/run/xray-manager/integrity.lock")
MAX_CONFIG = live_journal.MAX_SNAPSHOT
STAGE_RE = re.compile(r"live-[A-Za-z0-9_-]{1,64}\Z")
TERMINAL_STATES = {"completed", "rolled_back"}


class LivePublisherError(Exception):
    """Precondición o resultado de publicación live no demostrado."""


def fail(message: str) -> None:
    raise LivePublisherError(message)


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
            raise LivePublisherError("No se pudo inspeccionar una ruta administrada.") from exc
        if stat.S_ISLNK(info.st_mode):
            fail("Una ruta administrada contiene un componente symlink.")


def _check_dir(path: Path, *, uid: int, gid: int, mode: int) -> None:
    _check_components(path)
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != uid or info.st_gid != gid
            or stat.S_IMODE(info.st_mode) != mode):
        fail(f"Directorio inseguro: {path}; propietario/grupo/modo inesperados.")


def _read_regular(path: Path, *, uid: int, gid: int, mode: int, limit: int) -> bytes:
    _check_components(path)
    try:
        entry = path.lstat()
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                     | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NONBLOCK", 0))
    except OSError as exc:
        raise LivePublisherError("No se pudo abrir un archivo administrado.") from exc
    try:
        info = os.fstat(fd)
        if ((entry.st_dev, entry.st_ino) != (info.st_dev, info.st_ino)
                or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or (info.st_uid, info.st_gid) != (uid, gid)
                or stat.S_IMODE(info.st_mode) != mode
                or not 1 <= info.st_size <= limit):
            fail("Archivo administrado con tipo, propietario, permisos o tamaño inseguros.")
        chunks, total = [], 0
        while True:
            part = os.read(fd, min(65536, limit + 1 - total))
            if not part:
                break
            chunks.append(part)
            total += len(part)
            if total > limit:
                fail("Archivo administrado excede el tamaño permitido.")
        data = b"".join(chunks)
        if total != info.st_size:
            fail("Archivo administrado cambió durante su lectura.")
        return data
    finally:
        os.close(fd)


def _read_optional_config() -> bytes | None:
    _check_dir(CONFIG_DIR, uid=0, gid=grp.getgrnam("xray").gr_gid, mode=0o750)
    try:
        CONFIG_FILE.lstat()
    except FileNotFoundError:
        return None
    return _read_regular(
        CONFIG_FILE, uid=0, gid=grp.getgrnam("xray").gr_gid, mode=0o640,
        limit=MAX_CONFIG,
    )


def _acquire_one(path: Path) -> int:
    _check_components(path.parent)
    parent = path.parent.lstat()
    if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid != 0 or parent.st_gid != 0
            or stat.S_IMODE(parent.st_mode) & 0o022):
        fail("El directorio padre del lock debe ser root:root y no modificable por grupo/otros.")
    if path.exists() or path.is_symlink():
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_gid != 0
                or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600):
            fail("El archivo lock existente no es root:root 0600.")
    before = path.lstat() if path.exists() else None
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        info = os.fstat(fd)
        if (before is not None and (before.st_dev, before.st_ino) != (info.st_dev, info.st_ino)):
            fail("El archivo lock cambió durante su apertura.")
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_gid != 0
                or info.st_nlink != 1):
            fail("El descriptor lock no es un archivo regular root-owned.")
        os.fchmod(fd, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except BlockingIOError as exc:
        os.close(fd)
        raise LivePublisherError("Otra operación del Manager mantiene un lock requerido.") from exc
    except Exception:
        os.close(fd)
        raise


def _acquire_locks() -> list[int]:
    fds = []
    try:
        # Orden global establecido por el Manager: lifecycle -> integrity.
        fds.append(_acquire_one(LIFECYCLE_LOCK))
        fds.append(_acquire_one(INTEGRITY_LOCK))
        return fds
    except Exception:
        _release_locks(fds)
        raise


def _release_locks(fds: list[int]) -> None:
    for fd in reversed(fds):
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def _read_stage(staging_dir: Path) -> tuple[dict[str, Any], bytes]:
    if not staging_dir.is_absolute() or staging_dir.parent != STAGING_ROOT:
        fail("El staging debe ser un hijo directo de la raíz live administrada.")
    if not STAGE_RE.fullmatch(staging_dir.name):
        fail("Nombre de staging live inválido.")
    _check_dir(STAGING_ROOT, uid=0, gid=0, mode=0o711)
    _check_dir(staging_dir, uid=0, gid=grp.getgrnam("xray").gr_gid, mode=0o750)
    raw_manifest = _read_regular(
        staging_dir / "manifest.json", uid=0, gid=grp.getgrnam("xray").gr_gid,
        mode=0o640, limit=1024 * 1024,
    )
    manifest = staging._strict_json(raw_manifest, "El manifiesto live")
    required = {
        "schema_version", "environment", "status", "profile_id", "revision",
        "validation_id", "profile_content_sha256", "mapping_file", "mapping_sha256",
        "bindings", "leases", "staging_dir", "config_sha256", "config_size_bytes",
        "service_identity", "systemd_observation", "xray_binary", "native_validation",
        "runtime_published", "service_started",
    }
    if set(manifest) != required:
        fail("El manifiesto live tiene campos ausentes o inesperados.")
    if (manifest["schema_version"] != 1 or manifest["environment"] != "live"
            or manifest["status"] != "STAGED" or manifest["staging_dir"] != str(staging_dir)
            or manifest["native_validation"] != "PASS"
            or manifest["runtime_published"] is not False
            or manifest["service_started"] is not False):
        fail("El manifiesto no acredita un staging live puro y no publicado.")
    if (not isinstance(manifest["profile_id"], str)
            or not live_journal.PROFILE_RE.fullmatch(manifest["profile_id"])
            or not isinstance(manifest["revision"], str)
            or not live_journal.REVISION_RE.fullmatch(manifest["revision"])
            or not isinstance(manifest["validation_id"], str)
            or not re.fullmatch(r"pvalidation-[0-9a-f]{32}", manifest["validation_id"])):
        fail("Identidad perfil/revisión/validación del staging inválida.")
    for key in ("profile_content_sha256", "mapping_sha256", "config_sha256"):
        if not isinstance(manifest[key], str) or not live_journal.HASH_RE.fullmatch(manifest[key]):
            fail("Hash del manifiesto live inválido.")
    if (type(manifest["config_size_bytes"]) is not int
            or not 1 <= manifest["config_size_bytes"] <= MAX_CONFIG):
        fail("Tamaño de configuración staged inválido.")
    identity = manifest["service_identity"]
    if (not isinstance(identity, dict)
            or set(identity) != {"user", "group", "uid", "gid"}
            or identity["user"] != "xray" or identity["group"] != "xray"
            or type(identity["uid"]) is not int or identity["uid"] <= 0
            or type(identity["gid"]) is not int or identity["gid"] <= 0):
        fail("Identidad del servicio en manifiesto inválida.")
    binary = manifest["xray_binary"]
    if (not isinstance(binary, dict) or binary.get("path") != str(XRAY_BINARY)
            or not isinstance(binary.get("sha256"), str)
            or not live_journal.HASH_RE.fullmatch(binary["sha256"])):
        fail("La identidad del binario Xray del staging es inválida.")
    config = _read_regular(
        staging_dir / "config.json", uid=0, gid=identity["gid"], mode=0o640,
        limit=MAX_CONFIG,
    )
    if (len(config) != manifest["config_size_bytes"]
            or hashlib.sha256(config).hexdigest() != manifest["config_sha256"]):
        fail("La configuración staged no coincide con el hash/tamaño del manifiesto.")
    return manifest, config


def _service_identity() -> tuple[int, int]:
    try:
        uid, gid = certificate_resolver.service_identity("xray.service")
        user = pwd.getpwuid(uid)
        group = grp.getgrgid(gid)
    except (certificate_resolver.ResolverError, KeyError) as exc:
        raise LivePublisherError("No se pudo verificar la identidad xray:xray.") from exc
    if user.pw_name != "xray" or group.gr_name != "xray" or uid <= 0 or gid <= 0:
        fail("La identidad real del servicio no es xray:xray.")
    return uid, gid


def _validate_systemd(observed: dict[str, Any], manifest: dict[str, Any],
                      expected_config_hash: str | None) -> None:
    if (not isinstance(observed, dict) or observed.get("read_only") is not True
            or observed.get("unit") != "xray.service"
            or observed.get("load_state") != "loaded"
            or observed.get("active_state") != "inactive"
            or observed.get("main_pid") not in (None, 0)
            or observed.get("invocation_id") not in (None, "")
            or observed.get("fragment_path") != str(UNIT_FILE)
            or observed.get("user") != "xray" or observed.get("group") != "xray"
            or observed.get("need_daemon_reload") != "no"
            or observed.get("drop_in_paths") not in ("", None)
            or observed.get("service_type") != "simple"):
        fail("La unidad debe estar cargada, administrada e inactiva antes de publicar.")
    recorded = manifest["systemd_observation"]
    fields = ("unit", "load_state", "active_state", "invocation_id", "main_pid", "fragment_path")
    if not isinstance(recorded, dict) or any(recorded.get(k) != observed.get(k) for k in fields):
        fail("La observación systemd cambió desde el staging; se debe preparar de nuevo.")
    if observed.get("runtime_config_sha256") != expected_config_hash:
        fail("La configuración runtime cambió desde el staging; CAS rechazado.")


def _binary_hash() -> str:
    _check_components(XRAY_BINARY)
    info = XRAY_BINARY.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0
            or info.st_nlink != 1 or not info.st_mode & 0o111):
        fail("El binario Xray no cumple el contrato root-owned ejecutable.")
    digest = hashlib.sha256()
    fd = os.open(XRAY_BINARY, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        opened = os.fstat(fd)
        if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
            fail("El binario Xray cambió durante la apertura.")
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    finally:
        os.close(fd)
    return digest.hexdigest()


def _write_temp(data: bytes, service_gid: int) -> Path:
    fd, name = tempfile.mkstemp(prefix=".config.json.live-", dir=CONFIG_DIR)
    path = Path(name)
    try:
        os.fchown(fd, 0, service_gid)
        os.fchmod(fd, 0o640)
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(fd)
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise
    finally:
        os.close(fd)
    return path


def _verify_config(expected_hash: str, service_gid: int) -> None:
    data = _read_regular(CONFIG_FILE, uid=0, gid=service_gid, mode=0o640, limit=MAX_CONFIG)
    if hashlib.sha256(data).hexdigest() != expected_hash:
        fail("La verificación posterior a publicación no coincide con el candidato.")


def _restore_previous(store: live_journal.LiveOperationStore, operation_id: str,
                      previous: bytes, expected_new_hash: str,
                      service_uid: int, service_gid: int) -> None:
    current = _read_optional_config()
    current_hash = hashlib.sha256(current).hexdigest() if current is not None else None
    previous_hash = hashlib.sha256(previous).hexdigest()
    if current_hash not in {expected_new_hash, previous_hash}:
        fail("Rollback CAS rechazado: config.json ya no coincide con el candidato ni con el snapshot.")
    journal = store.load(operation_id)
    if journal["state"] != "rollback_started":
        store.transition(operation_id, expected_state=journal["state"],
                         new_state="rollback_started")
    temp = _write_temp(previous, service_gid)
    try:
        os.replace(temp, CONFIG_FILE)
        temp = None
        dir_fd = os.open(CONFIG_DIR, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
        _verify_config(previous_hash, service_gid)
        staging._service_run(XRAY_BINARY, CONFIG_FILE, service_uid, service_gid, 20)
        store.transition(
            operation_id, expected_state="rollback_started", new_state="rollback_config_restored",
            updates={"rollback": {"config_status": "restored", "service_status": "not_required"}},
        )
        store.transition(
            operation_id, expected_state="rollback_config_restored", new_state="rolled_back",
            updates={"rollback": {"config_status": "restored", "service_status": "not_required"}},
        )
    finally:
        if temp is not None:
            try:
                temp.unlink()
            except OSError:
                pass


def _ensure_no_open_operation(store: live_journal.LiveOperationStore) -> None:
    store.initialize()
    for path in store.root.iterdir():
        if path.is_symlink() or not path.is_dir() or not live_journal.OP_RE.fullmatch(path.name):
            fail("El almacén live contiene una entrada inesperada; no se publicará.")
        record = store.load(path.name)
        if record["state"] not in TERMINAL_STATES:
            fail(f"Existe una operación live no terminal ({path.name}, {record['state']}); requiere recuperación.")


def publish_live(staging_dir: Path) -> dict[str, Any]:
    """Publica una única configuración live, sin iniciar/detener/reiniciar Xray."""
    if os.geteuid() != 0:
        fail("La publicación live requiere root.")
    staging_dir = Path(staging_dir)
    fds = _acquire_locks()
    operation_id = None
    temp_path = None
    renamed = False
    store = live_journal.LiveOperationStore(OPERATION_ROOT)
    previous: bytes | None = None
    service_uid = service_gid = None
    try:
        _check_dir(CONFIG_DIR, uid=0, gid=grp.getgrnam("xray").gr_gid, mode=0o750)
        manifest, config_data = _read_stage(staging_dir)
        service_uid, service_gid = _service_identity()
        if (manifest["service_identity"]["uid"], manifest["service_identity"]["gid"]) != (service_uid, service_gid):
            fail("La identidad xray:xray cambió desde el staging; se debe preparar de nuevo.")
        if _binary_hash() != manifest["xray_binary"]["sha256"]:
            fail("El binario Xray cambió desde el staging; se debe preparar de nuevo.")
        initial_systemd = systemd_adapter.status(unit_file=UNIT_FILE, config_file=CONFIG_FILE)
        current = _read_optional_config()
        current_hash = hashlib.sha256(current).hexdigest() if current is not None else None
        _validate_systemd(initial_systemd, manifest, current_hash)
        _ensure_no_open_operation(store)

        previous = current
        journal_record = store.create(
            profile_id=manifest["profile_id"], revision=manifest["revision"],
            validation_id=manifest["validation_id"],
            profile_sha256=manifest["profile_content_sha256"],
            staged_sha256=manifest["config_sha256"],
            binary_sha256=manifest["xray_binary"]["sha256"],
            initial_systemd=initial_systemd, previous_config=previous,
        )
        operation_id = journal_record["operation_id"]
        store.transition(operation_id, expected_state="prepared", new_state="validated")
        store.transition(operation_id, expected_state="validated", new_state="snapshot_saved")
        store.transition(
            operation_id, expected_state="snapshot_saved", new_state="publication_requested",
            updates={"publication": {"status": "requested", "target": str(CONFIG_FILE)}},
        )

        temp_path = _write_temp(config_data, service_gid)
        staging._service_run(XRAY_BINARY, temp_path, service_uid, service_gid, 20)

        before_rename = systemd_adapter.status(unit_file=UNIT_FILE, config_file=CONFIG_FILE)
        _validate_systemd(before_rename, manifest, current_hash)
        latest = _read_optional_config()
        if latest != previous:
            fail("CAS rechazado: config.json cambió inmediatamente antes de publicación.")
        os.replace(temp_path, CONFIG_FILE)
        temp_path = None
        renamed = True
        dir_fd = os.open(CONFIG_DIR, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
        expected_hash = hashlib.sha256(config_data).hexdigest()
        _verify_config(expected_hash, service_gid)
        store.transition(
            operation_id, expected_state="publication_requested", new_state="config_published",
            updates={
                "publication": {
                    "status": "published", "target": str(CONFIG_FILE),
                    "config_sha256": expected_hash, "published_at": live_journal._now(),
                },
            },
        )
        return {
            "status": "CONFIG_PUBLISHED", "operation_id": operation_id,
            "profile_id": manifest["profile_id"], "revision": manifest["revision"],
            "config_sha256": expected_hash, "runtime_published": True,
            "service_action_performed": False, "service_started": False,
            "configuration_loaded": False,
        }
    except Exception as exc:
        if operation_id is not None:
            try:
                if not renamed:
                    current_journal = store.load(operation_id)
                    if current_journal["state"] != "recovery_required":
                        store.transition(
                            operation_id, expected_state=current_journal["state"],
                            new_state="recovery_required",
                            updates={"recovery": {
                                "attempts": 1, "decision": "publication_not_confirmed",
                                "error_code": type(exc).__name__,
                            }},
                        )
                elif previous is not None and service_uid is not None and service_gid is not None:
                    _restore_previous(
                        store, operation_id, previous,
                        hashlib.sha256(config_data).hexdigest(), service_uid, service_gid,
                    )
                elif renamed and previous is None:
                    current_journal = store.load(operation_id)
                    store.transition(
                        operation_id, expected_state=current_journal["state"],
                        new_state="recovery_required",
                        updates={"recovery": {
                            "attempts": 1, "decision": "preserve_first_install_config",
                            "error_code": type(exc).__name__,
                        }},
                    )
            except Exception as recovery_exc:
                try:
                    current_journal = store.load(operation_id)
                    if current_journal["state"] != "recovery_required":
                        store.transition(
                            operation_id, expected_state=current_journal["state"],
                            new_state="recovery_required",
                            updates={"recovery": {
                                "attempts": 1, "decision": "manual_recovery_required",
                                "error_code": type(recovery_exc).__name__,
                            }},
                        )
                except Exception:
                    pass
                raise LivePublisherError(
                    "Falló la publicación y la recuperación automática no pudo acreditarse; "
                    f"operación {operation_id} requiere intervención."
                ) from recovery_exc
        raise
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink()
            except OSError:
                pass
        _release_locks(fds)


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staging-dir", required=True)
    args = parser.parse_args()
    try:
        result = publish_live(Path(args.staging_dir))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (LivePublisherError, live_journal.LiveJournalError, staging.StagingError,
            certificate_resolver.ResolverError, systemd_adapter.SystemdAdapterError,
            OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
