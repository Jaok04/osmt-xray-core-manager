#!/usr/bin/env python3
"""Publicación atómica y rollback de configuración en XRAY_SERVICE_ROOT fixture.

R-04 no ejecuta systemd, no publica en /etc/xray real y no inicia Xray.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import stat
import sys
from contextvars import ContextVar
from contextlib import contextmanager
from pathlib import Path

import xray_runtime_journal as journal
import xray_runtime_staging as staging

TEMP_RE = re.compile(r"\.config\.json\.r04tmp-[0-9a-f]{32}\.json\Z")
_ACTIVE_LOCK_CONTEXT = ContextVar("xray_runtime_publisher_lock_context", default=None)


def fail(message: str) -> None:
    raise journal.RuntimeJournalError(message)


def _config_target(service_root: Path, service_gid: int) -> Path:
    etc_dir = service_root / "etc"
    config_dir = etc_dir / "xray"
    journal.check_dir(etc_dir, 0o755, 0, 0)
    journal.check_dir(config_dir, 0o750, 0, service_gid)
    return config_dir / "config.json"


def _read_current(target: Path, service_gid: int) -> tuple[bytes | None, dict | None]:
    if target.is_symlink():
        fail("El destino config.json es un symlink.")
    if not target.exists():
        return None, None
    data = journal.read_regular(target, journal.MAX_FILE, 0, service_gid, 0o640, "config runtime fixture")
    info = target.stat()
    return data, {
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
        "uid": info.st_uid,
        "gid": info.st_gid,
        "mode": stat.S_IMODE(info.st_mode),
    }


def _snapshot_metadata(operation_dir: Path, record: dict) -> dict:
    if not journal.verify_snapshot(operation_dir, record):
        fail("La operación no tiene un snapshot completo.")
    snapshot_data = journal.read_regular(
        operation_dir / "snapshot.json", journal.MAX_JOURNAL, 0, 0, 0o600,
        "metadatos snapshot"
    )
    digest = hashlib.sha256(snapshot_data).hexdigest()
    if record["snapshot"]["metadata_sha256"] != digest:
        fail("El hash de snapshot.json no coincide con el journal.")
    return journal.strict_json(snapshot_data, "Metadatos snapshot")


def _validate_stage(operation_dir: Path, record: dict) -> tuple[dict, bytes]:
    manifest, config_data, lease_data = journal.read_staging(
        Path(record["staging"]["staging_dir"]),
        Path(record["staging"]["lease_root"]),
        record["service"]["uid"],
        record["service"]["gid"],
    )
    if (
        manifest["profile_id"] != record["source"]["profile_id"]
        or manifest["revision"] != record["source"]["revision"]
        or manifest["validation_id"] != record["source"]["validation_id"]
        or manifest["profile_content_sha256"] != record["source"]["profile_content_sha256"]
        or manifest["bindings_sha256"] != record["staging"]["bindings_sha256"]
        or manifest["xray_binary"]["path"] != record["service"]["binary_path"]
        or hashlib.sha256(config_data).hexdigest() != record["staging"]["config_sha256"]
        or len(config_data) != record["staging"]["config_size_bytes"]
        or lease_data["manifest_sha256"] != record["staging"]["staging_manifest_sha256"]
        or lease_data["leases"] != record["staging"]["leases"]
    ):
        fail("El staging/lease cambió desde el snapshot R-03.")
    return manifest, config_data


def _check_current_matches_snapshot(target: Path, snapshot: dict, service_gid: int) -> tuple[bytes | None, dict | None]:
    current, metadata = _read_current(target, service_gid)
    previous = snapshot["previous_config"]
    if previous["present"]:
        if metadata is None or metadata["sha256"] != previous["sha256"]:
            fail("TOCTOU: config runtime fixture ya no coincide con el snapshot anterior.")
        if (metadata["size_bytes"] != previous["size_bytes"]
                or metadata["uid"] != previous["uid"]
                or metadata["gid"] != previous["gid"]
                or metadata["mode"] != previous["mode"]):
            fail("TOCTOU: metadatos de config runtime fixture cambiaron desde el snapshot.")
    elif current is not None:
        fail("TOCTOU: apareció una configuración runtime después de registrar no_previous_config.")
    return current, metadata


def _write_temp(config_dir: Path, data: bytes, service_gid: int) -> Path:
    path = config_dir / (".config.json.r04tmp-" + secrets.token_hex(16) + ".json")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                 | getattr(os, "O_NOFOLLOW", 0), 0o640)
    try:
        os.fchown(fd, 0, service_gid)
        os.fchmod(fd, 0o640)
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(fd)
    finally:
        os.close(fd)
    return path


def _verify_published(target: Path, expected_hash: str, service_gid: int) -> None:
    data, metadata = _read_current(target, service_gid)
    if data is None or metadata is None or metadata["sha256"] != expected_hash:
        fail("La verificación posterior al rename atómico no coincide con el candidato.")
    if metadata["uid"] != 0 or metadata["gid"] != service_gid or metadata["mode"] != 0o640:
        fail("La configuración publicada tiene propietario/permisos inesperados.")


def _clean_publish_temps(config_dir: Path, service_gid: int) -> int:
    journal.check_dir(config_dir, 0o750, 0, service_gid)
    removed = 0
    for path in config_dir.iterdir():
        if not TEMP_RE.fullmatch(path.name):
            continue
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0
                or info.st_gid != service_gid or info.st_nlink != 1
                or stat.S_IMODE(info.st_mode) != 0o640):
            fail("Temporal de publicación R-04 inseguro; se conserva evidencia.")
        path.unlink()
        removed += 1
    if removed:
        journal.fsync_dir(config_dir)
    return removed


def _load_operation(operation_store: Path, operation_id: str, *, verify_snapshot: bool = True) -> tuple[Path, dict]:
    if not journal.OP_RE.fullmatch(operation_id):
        fail("operation_id inválido.")
    operations = operation_store / "operations"
    journal.check_dir(operations, 0o700, 0, 0)
    operation_dir = operations / operation_id
    record = journal.read_journal(operation_dir)
    if verify_snapshot:
        _snapshot_metadata(operation_dir, record)
    return operation_dir, record


def _lock_identity(operation_store: Path, lifecycle_lock: Path, application_lock: Path) -> tuple[str, str, str]:
    journal.check_operation_store(operation_store)
    journal.check_fixture_locks(operation_store, lifecycle_lock, application_lock)
    return tuple(os.path.abspath(path) for path in (operation_store, lifecycle_lock, application_lock))


@contextmanager
def transaction_locks(operation_store: Path, lifecycle_lock: Path, application_lock: Path):
    """Propietario único de lifecycle->application locks; contextos anidados los reutilizan."""
    identity = _lock_identity(operation_store, lifecycle_lock, application_lock)
    active = _ACTIVE_LOCK_CONTEXT.get()
    if active is not None:
        if active[0] != identity:
            fail("No se permite cambiar el conjunto de locks dentro de una transacción runtime.")
        yield
        return
    fds = []
    try:
        fds.append(journal.acquire_lock(Path(identity[1])))
        fds.append(journal.acquire_lock(Path(identity[2])))
        token = _ACTIVE_LOCK_CONTEXT.set((identity, tuple(fds)))
        try:
            yield
        finally:
            _ACTIVE_LOCK_CONTEXT.reset(token)
    finally:
        journal.release_locks(fds)


def _acquire(operation_store: Path, lifecycle_lock: Path, application_lock: Path) -> list[int]:
    identity = _lock_identity(operation_store, lifecycle_lock, application_lock)
    active = _ACTIVE_LOCK_CONTEXT.get()
    if active is not None:
        if active[0] != identity:
            fail("Los locks solicitados no coinciden con la transacción runtime propietaria.")
        return []
    fds = []
    try:
        fds.append(journal.acquire_lock(lifecycle_lock))
        fds.append(journal.acquire_lock(application_lock))
        return fds
    except Exception:
        journal.release_locks(fds)
        raise


def publish_operation(
    operation_store: Path,
    operation_id: str,
    lifecycle_lock: Path,
    application_lock: Path,
    timeout: int = 20,
    crash_at: str | None = None,
) -> dict:
    if os.geteuid() != 0:
        fail("R-04 requiere root en el entorno aislado.")
    if not 1 <= timeout <= 120:
        fail("Timeout R-04 fuera de rango.")
    fds = _acquire(operation_store, lifecycle_lock, application_lock)
    temp_path = None
    renamed = False
    try:
        operation_dir, record = _load_operation(operation_store, operation_id)
        if record["state"] == "config_published":
            target = _config_target(Path(record["service"]["service_root"]), record["service"]["gid"])
            _verify_published(target, record["publication"]["config_sha256"], record["service"]["gid"])
            return {"status": "ALREADY_PUBLISHED", "operation_id": operation_id,
                    "config_sha256": record["publication"]["config_sha256"],
                    "runtime_published": False, "service_action_performed": False}
        if record["state"] != "snapshot_saved":
            fail("La operación debe estar en snapshot_saved antes de R-04.")
        manifest, config_data = _validate_stage(operation_dir, record)
        snapshot = _snapshot_metadata(operation_dir, record)
        service_root = Path(record["service"]["service_root"])
        target = _config_target(service_root, record["service"]["gid"])
        config_dir = target.parent
        _check_current_matches_snapshot(target, snapshot, record["service"]["gid"])

        temp_path = _write_temp(config_dir, config_data, record["service"]["gid"])
        staging._service_run(
            Path(manifest["xray_binary"]["path"]), temp_path,
            record["service"]["uid"], record["service"]["gid"], timeout,
        )
        if crash_at == "before_rename":
            raise journal.SimulatedCrash("before_rename")

        # TOCTOU final: el destino debe seguir coincidiendo con el snapshot
        # inmediatamente antes del rename atómico en el mismo filesystem.
        _check_current_matches_snapshot(target, snapshot, record["service"]["gid"])
        os.replace(temp_path, target)
        temp_path = None
        renamed = True
        journal.fsync_dir(config_dir)
        staged_hash = hashlib.sha256(config_data).hexdigest()
        _verify_published(target, staged_hash, record["service"]["gid"])
        if crash_at == "after_rename":
            raise journal.SimulatedCrash("after_rename")

        record["state"] = "config_published"
        record["publication"] = {
            "status": "published",
            "target": "etc/xray/config.json",
            "config_sha256": staged_hash,
            "published_at": journal.now(),
        }
        if record["schema_version"] == 2:
            record["orchestration"]["phase"] = "published"
        journal.write_journal(operation_dir, record)
        journal.fsync_dir(operation_dir)
        return {
            "status": "CONFIG_PUBLISHED",
            "operation_id": operation_id,
            "config_sha256": staged_hash,
            "profile_id": record["source"]["profile_id"],
            "revision": record["source"]["revision"],
            "runtime_published": True,
            "service_action_performed": False,
        }
    except journal.SimulatedCrash:
        raise
    except Exception:
        if temp_path is not None and temp_path.exists() and not renamed:
            temp_path.unlink()
            journal.fsync_dir(temp_path.parent)
        raise
    finally:
        journal.release_locks(fds)


def _mark_recovery_required(operation_dir: Path, record: dict, reason: str) -> dict:
    record["state"] = "recovery_required"
    record["rollback"]["status"] = "recovery_required"
    record["rollback"]["last_error"] = reason[:240]
    record["recovery"]["attempts"] += 1
    record["recovery"]["last_action"] = "manual_intervention_required"
    record["recovery"]["last_error"] = reason[:240]
    journal.write_journal(operation_dir, record)
    return {"status": "RECOVERY_REQUIRED", "operation_id": record["operation_id"], "reason": reason}


def _rollback_locked(operation_dir: Path, record: dict, timeout: int,
                     crash_at: str | None = None) -> dict:
    snapshot = _snapshot_metadata(operation_dir, record)
    previous = snapshot["previous_config"]
    service_gid = record["service"]["gid"]
    target = _config_target(Path(record["service"]["service_root"]), service_gid)
    current, current_meta = _read_current(target, service_gid)
    staged_hash = record["staging"]["config_sha256"]

    if not previous["present"]:
        return _mark_recovery_required(
            operation_dir, record,
            "no_previous_config: no se elimina automáticamente la primera configuración publicada.",
        )

    previous_hash = previous["sha256"]
    if current_meta is None:
        return _mark_recovery_required(operation_dir, record, "El destino runtime desapareció antes del rollback.")
    if current_meta["sha256"] not in {staged_hash, previous_hash}:
        return _mark_recovery_required(operation_dir, record, "El destino runtime no coincide ni con staging ni con snapshot.")
    if current_meta["sha256"] == previous_hash:
        # Puede ser un reintento tras rename y antes del commit del journal.
        try:
            staging._service_run(
                Path(record["service"]["binary_path"]), target,
                record["service"]["uid"], service_gid, timeout,
            )
        except Exception as exc:
            record["state"] = "rollback_failed"
            record["rollback"]["status"] = "failed"
            record["rollback"]["validation"] = "FAIL"
            record["rollback"]["last_error"] = str(exc)[:240]
            record["rollback"]["completed_at"] = journal.now()
            journal.write_journal(operation_dir, record)
            return {"status": "ROLLBACK_FAILED", "operation_id": record["operation_id"]}
        record["state"] = "rollback_config_restored"
        record["rollback"]["status"] = "config_restored"
        record["rollback"]["restored_config_sha256"] = previous_hash
        record["rollback"]["validation"] = "PASS"
        record["rollback"]["completed_at"] = journal.now()
        record["rollback"]["last_error"] = None
        journal.write_journal(operation_dir, record)
        return {"status": "ROLLBACK_CONFIG_RESTORED", "operation_id": record["operation_id"],
                "config_sha256": previous_hash, "service_action_performed": False}

    if record["state"] != "rollback_started":
        record["state"] = "rollback_started"
        record["rollback"]["status"] = "started"
        record["rollback"]["started_at"] = journal.now()
        record["rollback"]["last_error"] = None
        journal.write_journal(operation_dir, record)

    snapshot_config = journal.read_regular(
        operation_dir / "snapshot" / "config.json", journal.MAX_FILE,
        0, 0, 0o600, "snapshot config anterior"
    )
    if hashlib.sha256(snapshot_config).hexdigest() != previous_hash:
        return _mark_recovery_required(operation_dir, record, "Hash del snapshot anterior cambió.")
    temp_path = _write_temp(target.parent, snapshot_config, service_gid)
    os.replace(temp_path, target)
    journal.fsync_dir(target.parent)
    _verify_published(target, previous_hash, service_gid)
    if crash_at == "after_rollback_rename":
        raise journal.SimulatedCrash("after_rollback_rename")

    try:
        staging._service_run(
            Path(record["service"]["binary_path"]), target,
            record["service"]["uid"], service_gid, timeout,
        )
    except Exception as exc:
        record["state"] = "rollback_failed"
        record["rollback"]["status"] = "failed"
        record["rollback"]["restored_config_sha256"] = previous_hash
        record["rollback"]["validation"] = "FAIL"
        record["rollback"]["completed_at"] = journal.now()
        record["rollback"]["last_error"] = str(exc)[:240]
        journal.write_journal(operation_dir, record)
        return {"status": "ROLLBACK_FAILED", "operation_id": record["operation_id"],
                "config_restored": True, "validation": "FAIL"}

    record["state"] = "rollback_config_restored"
    record["rollback"]["status"] = "config_restored"
    record["rollback"]["restored_config_sha256"] = previous_hash
    record["rollback"]["validation"] = "PASS"
    record["rollback"]["completed_at"] = journal.now()
    record["rollback"]["last_error"] = None
    journal.write_journal(operation_dir, record)
    return {"status": "ROLLBACK_CONFIG_RESTORED", "operation_id": record["operation_id"],
            "config_sha256": previous_hash, "service_action_performed": False}


def rollback_operation(
    operation_store: Path,
    operation_id: str,
    lifecycle_lock: Path,
    application_lock: Path,
    timeout: int = 20,
    crash_at: str | None = None,
) -> dict:
    if os.geteuid() != 0:
        fail("Rollback R-04 requiere root en el entorno aislado.")
    if not 1 <= timeout <= 120:
        fail("Timeout de rollback R-04 fuera de rango.")
    fds = _acquire(operation_store, lifecycle_lock, application_lock)
    try:
        operation_dir, record = _load_operation(
            operation_store, operation_id, verify_snapshot=False
        )
        try:
            _snapshot_metadata(operation_dir, record)
        except journal.RuntimeJournalError as exc:
            return _mark_recovery_required(
                operation_dir, record,
                f"Snapshot inválido durante rollback; no se modifica el runtime: {exc}",
            )
        if record["state"] == "rollback_config_restored":
            snapshot = _snapshot_metadata(operation_dir, record)
            previous = snapshot["previous_config"]
            target = _config_target(Path(record["service"]["service_root"]), record["service"]["gid"])
            current, meta = _read_current(target, record["service"]["gid"])
            if previous["present"] and meta and meta["sha256"] == previous["sha256"]:
                return {"status": "ALREADY_RESTORED", "operation_id": operation_id,
                        "service_action_performed": False}
            return _mark_recovery_required(operation_dir, record, "El config restaurado cambió después del rollback.")
        if record["state"] not in {"config_published", "rollback_started"}:
            fail("Rollback sólo admite config_published o rollback_started.")
        return _rollback_locked(operation_dir, record, timeout, crash_at)
    finally:
        journal.release_locks(fds)


def recover_publications(
    operation_store: Path,
    lifecycle_lock: Path,
    application_lock: Path,
    timeout: int = 20,
) -> dict:
    if os.geteuid() != 0:
        fail("La recuperación R-04 requiere root en el entorno aislado.")
    if not 1 <= timeout <= 120:
        fail("Timeout de recuperación R-04 fuera de rango.")
    fds = _acquire(operation_store, lifecycle_lock, application_lock)
    results = []
    try:
        operations = operation_store / "operations"
        if not operations.exists():
            return {"status": "RECOVERY_COMPLETE", "operations": [], "service_action_performed": False}
        journal.check_dir(operations, 0o700, 0, 0)
        for operation_dir in sorted(operations.iterdir()):
            if operation_dir.is_symlink() or not operation_dir.is_dir():
                fail("Entrada inesperada en operation_store.")
            record = journal.read_journal(operation_dir)
            if record["schema_version"] == 2:
                results.append({"operation_id": record["operation_id"], "state": record["state"], "action": "deferred_to_R05_recovery"})
                continue
            if record["state"] in {"snapshot_saved", "config_published", "rollback_started"}:
                target = _config_target(Path(record["service"]["service_root"]), record["service"]["gid"])
                _clean_publish_temps(target.parent, record["service"]["gid"])
                try:
                    snapshot = _snapshot_metadata(operation_dir, record)
                except journal.RuntimeJournalError as exc:
                    result = _mark_recovery_required(
                        operation_dir, record,
                        f"Snapshot inválido durante recuperación; no se modifica el runtime: {exc}",
                    )
                    results.append({"operation_id": record["operation_id"], **result})
                    continue
                current, current_meta = _read_current(target, record["service"]["gid"])
                previous = snapshot["previous_config"]
                staged_hash = record["staging"]["config_sha256"]

                if record["state"] == "snapshot_saved":
                    if current_meta and current_meta["sha256"] == staged_hash:
                        record["state"] = "config_published"
                        record["publication"] = {
                            "status": "published", "target": "etc/xray/config.json",
                            "config_sha256": staged_hash, "published_at": journal.now(),
                        }
                        if record["schema_version"] == 2:
                            record["orchestration"]["phase"] = "published"
                        record["recovery"]["attempts"] += 1
                        record["recovery"]["last_action"] = "detected_rename_before_journal_commit"
                        record["recovery"]["last_error"] = None
                        journal.write_journal(operation_dir, record)
                        result = _rollback_locked(operation_dir, record, timeout)
                        results.append({"operation_id": record["operation_id"], **result})
                    elif previous["present"] and current_meta and current_meta["sha256"] == previous["sha256"]:
                        results.append({"operation_id": record["operation_id"], "status": "NOT_PUBLISHED"})
                    elif not previous["present"] and current is None:
                        results.append({"operation_id": record["operation_id"], "status": "NOT_PUBLISHED"})
                    else:
                        result = _mark_recovery_required(operation_dir, record, "Destino no coincide con snapshot ni con staging.")
                        results.append({"operation_id": record["operation_id"], **result})
                elif record["state"] in {"config_published", "rollback_started"}:
                    result = _rollback_locked(operation_dir, record, timeout)
                    results.append({"operation_id": record["operation_id"], **result})
            elif record["state"] in {"rollback_config_restored", "rolled_back"}:
                try:
                    snapshot = _snapshot_metadata(operation_dir, record)
                except journal.RuntimeJournalError as exc:
                    result = _mark_recovery_required(
                        operation_dir, record,
                        f"Snapshot inválido al verificar rollback; no se modifica el runtime: {exc}",
                    )
                    results.append({"operation_id": record["operation_id"], **result})
                    continue
                previous = snapshot["previous_config"]
                target = _config_target(Path(record["service"]["service_root"]), record["service"]["gid"])
                current, meta = _read_current(target, record["service"]["gid"])
                if not previous["present"] or not meta or meta["sha256"] != previous["sha256"]:
                    result = _mark_recovery_required(operation_dir, record, "Config restaurado no coincide con snapshot.")
                    results.append({"operation_id": record["operation_id"], **result})
                else:
                    results.append({"operation_id": record["operation_id"], "status": "ROLLBACK_CONFIG_RESTORED"})
            else:
                results.append({"operation_id": record["operation_id"], "state": record["state"], "action": "no_op"})
        return {"status": "RECOVERY_COMPLETE", "operations": results, "service_action_performed": False}
    finally:
        journal.release_locks(fds)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("publish", "rollback"):
        item = sub.add_parser(command)
        item.add_argument("--operation-store", required=True)
        item.add_argument("--operation-id", required=True)
        item.add_argument("--lifecycle-lock", required=True)
        item.add_argument("--application-lock", required=True)
        item.add_argument("--timeout", type=int, default=20)
    recover = sub.add_parser("recover")
    recover.add_argument("--operation-store", required=True)
    recover.add_argument("--lifecycle-lock", required=True)
    recover.add_argument("--application-lock", required=True)
    recover.add_argument("--timeout", type=int, default=20)
    inspect = sub.add_parser("inspect")
    inspect.add_argument("--operation-store", required=True)
    inspect.add_argument("--operation-id", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "publish":
            result = publish_operation(
                Path(args.operation_store), args.operation_id,
                Path(args.lifecycle_lock), Path(args.application_lock), args.timeout,
            )
        elif args.command == "rollback":
            result = rollback_operation(
                Path(args.operation_store), args.operation_id,
                Path(args.lifecycle_lock), Path(args.application_lock), args.timeout,
            )
        elif args.command == "recover":
            result = recover_publications(
                Path(args.operation_store), Path(args.lifecycle_lock),
                Path(args.application_lock), args.timeout,
            )
        else:
            result = journal.inspect_operation(Path(args.operation_store), args.operation_id)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (journal.RuntimeJournalError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
