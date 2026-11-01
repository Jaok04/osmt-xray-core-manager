#!/usr/bin/env python3
"""Safe users.json legacy-to-v2 cutover. Dry-run by default; apply/rollback require hash token."""
import argparse
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/opt/xray-manager")
USERS = Path(os.environ.get("USERS_V2_CUTOVER_USERS_FILE", "/var/lib/xray-manager/users/users.json"))
CONNECTIONS = Path(os.environ.get("USERS_V2_CUTOVER_CONNECTIONS_FILE", "/var/lib/xray-manager/connections/connections.json"))
LOCK = Path(os.environ.get("USERS_V2_CUTOVER_LOCK_FILE", "/run/xray-manager/integrity.lock"))
BACKUPS = Path(os.environ.get("USERS_V2_CUTOVER_BACKUP_ROOT", "/var/backups/xray-manager/identity-cutover"))
MODULE = ROOT / "modules/users_v2.sh"
JSON_STORE = ROOT / "lib/json_store.sh"


def fail(message):
    raise SystemExit("ERROR: " + message)


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def regular_file(path):
    if path.is_symlink() or not path.is_file():
        fail(f"se requiere archivo regular no simbólico: {path}")


def validate_v2(path):
    cmd = (
        'source "$1"; '
        'USERS_V2_CONNECTIONS_FILE="$2"; '
        'users_v2_validate_file "$3"'
    )
    result = subprocess.run(
        ["bash", "-c", cmd, "cutover-validator", str(MODULE), str(CONNECTIONS), str(path)],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    if result.returncode:
        fail("el documento candidato no supera users_v2_validate_file: " + result.stderr.strip())


def migrate(source, candidate, state):
    cmd = (
        'source "$1"; '
        'USERS_V2_CONNECTIONS_FILE="$3"; '
        'users_v2_migrate_legacy "$2" "$3" "$4" "$5"'
    )
    result = subprocess.run(
        ["bash", "-c", cmd, "cutover-migrator", str(MODULE), str(source),
         str(CONNECTIONS), str(candidate), state],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    if result.returncode:
        fail("falló la migración: " + result.stderr.strip())


def atomic_replace(source, destination):
    if source.parent.resolve() != destination.parent.resolve():
        fail("temporal y destino deben estar en el mismo directorio")
    fd = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        os.fchmod(fd, 0o600)
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(source, destination)
    dfd = os.open(destination.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(dfd)
    finally:
        os.close(dfd)


def load_manifest(folder):
    manifest_path = folder / "manifest.json"
    regular_file(manifest_path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if data.get("status") != "applied":
        fail("el backup no corresponde a un cutover aplicado")
    return data


def write_manifest(path, data):
    fd, name = tempfile.mkstemp(prefix=".manifest-", dir=path.parent)
    tmp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
        dfd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        if tmp.exists():
            tmp.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--apply", action="store_true")
    group.add_argument("--rollback", metavar="BACKUP_DIR")
    parser.add_argument("--state", choices=("active", "suspended", "expired"))
    parser.add_argument("--confirm")
    args = parser.parse_args()

    regular_file(USERS)
    regular_file(CONNECTIONS)
    try:
        connections = json.loads(CONNECTIONS.read_text(encoding="utf-8"))
        if not isinstance(connections, list):
            fail("connections.json no es un arreglo JSON")
    except (ValueError, OSError) as exc:
        fail(f"catálogo de conexiones inválido: {exc}")

    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("a") as lock_stream:
        fcntl.flock(lock_stream.fileno(), fcntl.LOCK_EX)

        if args.rollback:
            folder_arg = Path(args.rollback)
            if folder_arg.is_symlink() or not folder_arg.is_dir():
                fail("directorio de backup inválido")
            folder = folder_arg.resolve()
            if not folder.is_dir():
                fail("directorio de backup inválido")
            try:
                folder.relative_to(BACKUPS.resolve())
            except ValueError:
                fail("el backup debe estar dentro del directorio oficial de cutover")
            manifest = load_manifest(folder)
            old = folder / "users.legacy.json"
            connection_copy = folder / "connections.snapshot.json"
            regular_file(old)
            regular_file(connection_copy)
            old_hash = manifest["legacy_sha256"]
            new_hash = manifest["v2_sha256"]
            conn_hash = manifest["connections_sha256"]
            if sha(old) != old_hash or sha(connection_copy) != conn_hash:
                fail("los hashes del backup no coinciden con el manifest")
            token = "ROLLBACK-USERS-V2-" + new_hash[:12]
            if not args.confirm:
                print("Rollback disponible. Token requerido:", token)
                return
            if args.confirm != token:
                fail("token de rollback incorrecto")
            if sha(USERS) != new_hash:
                fail("users.json cambió desde el cutover; no se sobrescribirán cambios")
            if sha(CONNECTIONS) != conn_hash:
                fail("connections.json cambió desde el cutover; rollback detenido")
            fd, tmp_name = tempfile.mkstemp(prefix=".users-rollback-", dir=USERS.parent)
            os.close(fd)
            tmp = Path(tmp_name)
            shutil.copyfile(old, tmp)
            atomic_replace(tmp, USERS)
            if sha(USERS) != old_hash:
                fail("el hash restaurado no coincide; conservar backup")
            print("ROLLBACK VERIFICADO")
            print("Archivo:", USERS)
            print("SHA256:", old_hash)
            return

        if args.state is None:
            fail("indica --state active|suspended|expired; el estado funcional no se inferirá")
        try:
            legacy = json.loads(USERS.read_text(encoding="utf-8"))
            if not isinstance(legacy, list):
                fail("users.json no está en el esquema legacy de arreglo JSON")
        except (ValueError, OSError) as exc:
            fail(f"users.json inválido: {exc}")

        old_hash = sha(USERS)
        conn_hash = sha(CONNECTIONS)
        token = "APPLY-USERS-V2-" + old_hash[:12]
        fd, tmp_name = tempfile.mkstemp(prefix=".users-v2-candidate-", dir=USERS.parent)
        os.close(fd)
        candidate = Path(tmp_name)
        candidate.unlink()
        try:
            migrate(USERS, candidate, args.state)
            validate_v2(candidate)
            new_hash = sha(candidate)
            result = json.loads(candidate.read_text(encoding="utf-8"))
            print("Candidato validado; el archivo real todavía no se ha reemplazado.")
            print("Legacy SHA256:", old_hash)
            print("Connections SHA256:", conn_hash)
            print("Candidato v2 SHA256:", new_hash)
            print("Registros legacy:", len(legacy))
            print("Identidades propuestas:", len(result["identities"]))
            print("Asociaciones propuestas:", len(result["associations"]))
            print("Estado funcional elegido:", args.state)
            if args.dry_run:
                print("DRY-RUN: no se modificó el registro real.")
                print("Token para aplicar:", token)
                return
            if not args.confirm or args.confirm != token:
                fail("para aplicar se requiere --confirm con el token exacto mostrado por --dry-run")
            # Recheck after the lock and immediately before backup/replace.
            if sha(USERS) != old_hash or sha(CONNECTIONS) != conn_hash:
                fail("los archivos de entrada cambiaron; repite el dry-run")
            BACKUPS.mkdir(parents=True, exist_ok=True)
            os.chmod(BACKUPS, 0o700)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup = BACKUPS / f"{stamp}-{os.getpid()}"
            backup.mkdir(mode=0o700)
            shutil.copy2(USERS, backup / "users.legacy.json")
            shutil.copy2(CONNECTIONS, backup / "connections.snapshot.json")
            for saved in (backup / "users.legacy.json", backup / "connections.snapshot.json"):
                with saved.open("rb") as stream:
                    os.fsync(stream.fileno())
            bfd = os.open(backup, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(bfd)
            finally:
                os.close(bfd)
            if sha(backup / "users.legacy.json") != old_hash:
                fail("no se pudo verificar el backup de users.json")
            if sha(backup / "connections.snapshot.json") != conn_hash:
                fail("no se pudo verificar el backup de connections.json")
            manifest = {
                "status": "prepared",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "legacy_sha256": old_hash,
                "connections_sha256": conn_hash,
                "v2_sha256": new_hash,
                "functional_state": args.state,
                "users_file": str(USERS),
                "connections_file": str(CONNECTIONS),
                "legacy_count": len(legacy),
                "identity_count": len(result["identities"]),
                "association_count": len(result["associations"]),
            }
            manifest_path = backup / "manifest.json"
            write_manifest(manifest_path, manifest)
            atomic_replace(candidate, USERS)
            if sha(USERS) != new_hash:
                fail(f"reemplazo no verificado; backup disponible en {backup}")
            manifest["status"] = "applied"
            manifest["applied_at"] = datetime.now(timezone.utc).isoformat()
            write_manifest(manifest_path, manifest)
            print("CUTOVER APLICADO Y VERIFICADO")
            print("Backup:", backup)
            print("Manifest:", manifest_path)
            print("SHA256 v2:", new_hash)
            print("Consulta token de rollback con:")
            print(f"{sys.argv[0]} --rollback {backup}")
        finally:
            if candidate.exists():
                candidate.unlink()


if __name__ == "__main__":
    main()