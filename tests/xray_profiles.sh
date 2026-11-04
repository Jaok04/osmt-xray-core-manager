#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT
STORE="$TMP/store"
KEY="$TMP/master.key"
KEY_WRONG="$TMP/wrong-master.key"
umask 077
dd if=/dev/urandom of="$KEY" bs=32 count=1 status=none
dd if=/dev/urandom of="$KEY_WRONG" bs=32 count=1 status=none
chmod 600 "$KEY" "$KEY_WRONG"
CLI=(python3 "$ROOT/scripts/xray_profiles.py" --store "$STORE" --master-key "$KEY")
WRONG_CLI=(python3 "$ROOT/scripts/xray_profiles.py" --store "$STORE" --master-key "$KEY_WRONG")
NO_KEY_STORE="$TMP/no-key-store"
NO_KEY_CLI=(python3 "$ROOT/scripts/xray_profiles.py" --store "$NO_KEY_STORE" --master-key "$TMP/missing-master.key")
CONFIG="$TMP/source.json"
CONFIG2="$TMP/updated.json"
printf '%s\n' '{"log":{"loglevel":"warning"},"inbounds":[],"outbounds":[{"protocol":"freedom","tag":"direct"}],"test_secret":"profile-secret-marker"}' >"$CONFIG"
printf '%s\n' '{"log":{"loglevel":"error"},"inbounds":[],"outbounds":[{"protocol":"freedom","tag":"direct"}],"test_secret":"updated-secret-marker"}' >"$CONFIG2"
EMPTY="$("${CLI[@]}" create --name "Perfil vacío")"
[[ "$(jq -r .config_present <<<"$EMPTY")" == false ]]
if "${NO_KEY_CLI[@]}" create --name "No debe persistir" --config-file "$CONFIG" >"$TMP/no-key.out" 2>&1; then
	echo "ERROR: se creó una revisión sin clave maestra." >&2
	exit 1
fi
[[ ! -e "$TMP/missing-master.key" ]]
[[ "$("${NO_KEY_CLI[@]}" list | jq length)" == 0 ]]
[[ "$(find "$NO_KEY_STORE/profiles" -mindepth 1 -maxdepth 1 -type d | wc -l)" == 0 ]]
CREATED="$("${CLI[@]}" create --name "Perfil base" --description "Base de prueba" --notes "Notas" --config-file "$CONFIG")"
ID="$(jq -r .profile_id <<<"$CREATED")"
REV="$(jq -r .current_revision <<<"$CREATED")"
[[ "$REV" == r000001 ]]
PROFILE_DIR="$STORE/profiles/$ID"
CONFIG_COPY="$PROFILE_DIR/revisions/$REV/config.enc.json"
[[ -f "$CONFIG_COPY" && ! -L "$CONFIG_COPY" ]]
[[ "$(jq -r .config.storage "$PROFILE_DIR/revisions/$REV/manifest.json")" == aes-256-gcm ]]
! grep -q 'profile-secret-marker' "$CONFIG_COPY"
python3 - "$ROOT" "$STORE" "$KEY" "$ID" "$REV" "$CONFIG" <<'PYCRYPT'
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(sys.argv[1]) / "scripts"))
from xray_profiles import ProfileStore
store = ProfileStore(sys.argv[2], sys.argv[3])
plain, _ = store.read_revision_config(sys.argv[4], sys.argv[5])
assert __import__("json").loads(plain) == __import__("json").loads(pathlib.Path(sys.argv[6]).read_text())
PYCRYPT
[[ "$(stat -c '%a' "$STORE")" == 700 ]]
[[ "$(stat -c '%a' "$STORE/profiles")" == 700 ]]
[[ "$(stat -c '%a' "$PROFILE_DIR")" == 700 ]]
[[ "$(stat -c '%a' "$CONFIG_COPY")" == 600 ]]
[[ "$(stat -c '%a' "$PROFILE_DIR/metadata.json")" == 600 ]]
DUP="$("${CLI[@]}" duplicate --profile-id "$ID" --name "Perfil copia" --description "Descripción copia" --notes "Notas copia")"
DUP_ID="$(jq -r .profile_id <<<"$DUP")"
[[ "$DUP_ID" != "$ID" ]]
! cmp -s "$CONFIG_COPY" "$STORE/profiles/$DUP_ID/revisions/r000001/config.enc.json"
! grep -q 'profile-secret-marker' "$STORE/profiles/$DUP_ID/revisions/r000001/config.enc.json"
python3 - "$ROOT" "$STORE" "$KEY" "$PROFILE_DIR/revisions/r000001/config.enc.json" "$DUP_ID" <<'PYAAD'
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(sys.argv[1]) / "scripts"))
from xray_profiles import ProfileStore, ProfileError
blob=json.loads(pathlib.Path(sys.argv[4]).read_text())
blob["profile_id"]=sys.argv[5]
try:
    ProfileStore(sys.argv[2], sys.argv[3]).decrypt_config(
        json.dumps(blob, sort_keys=True, separators=(",", ":")).encode(), sys.argv[5], "r000001"
    )
except ProfileError:
    pass
else:
    raise SystemExit("AAD no vinculó ciphertext a la identidad destino")
PYAAD
python3 - "$ROOT" "$STORE" "$KEY" "$DUP_ID" <<'PYCRYPT2'
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(sys.argv[1]) / "scripts"))
from xray_profiles import ProfileStore
plain, _ = ProfileStore(sys.argv[2], sys.argv[3]).read_revision_config(sys.argv[4], "r000001")
assert b"profile-secret-marker" in plain
PYCRYPT2
[[ "$(jq -r .profile_id "$STORE/profiles/$DUP_ID/revisions/r000001/manifest.json")" == "$DUP_ID" ]]
[[ "$(jq -r .description "$STORE/profiles/$DUP_ID/metadata.json")" == "Descripción copia" ]]
[[ "$(jq -r .notes "$STORE/profiles/$DUP_ID/metadata.json")" == "Notas copia" ]]
if "${CLI[@]}" create --name "perfil BASE" >"$TMP/duplicate-name.out" 2>&1; then
	echo "ERROR: se aceptó un nombre duplicado." >&2
	exit 1
fi
grep -q 'Ya existe un perfil' "$TMP/duplicate-name.out"
UPDATED="$("${CLI[@]}" update --profile-id "$ID" --description "Descripción nueva" --config-file "$CONFIG2")"
[[ "$(jq -r .current_revision <<<"$UPDATED")" == r000002 ]]
[[ "$(jq -r .description "$PROFILE_DIR/metadata.json")" == "Descripción nueva" ]]
[[ -f "$PROFILE_DIR/revisions/r000001/config.enc.json" && -f "$PROFILE_DIR/revisions/r000002/config.enc.json" ]]
[[ "$(jq -r .validation_status "$PROFILE_DIR/metadata.json")" == not_validated ]]
HASH_BEFORE="$(sha256sum "$PROFILE_DIR/revisions/r000002/config.enc.json" | awk '{print $1}')"
"${CLI[@]}" rename --profile-id "$ID" --name "Perfil renombrado" >/dev/null
HASH_AFTER="$(sha256sum "$PROFILE_DIR/revisions/r000002/config.enc.json" | awk '{print $1}')"
[[ "$HASH_BEFORE" == "$HASH_AFTER" ]]
[[ "$(jq -r .name "$PROFILE_DIR/metadata.json")" == "Perfil renombrado" ]]
RESTORED="$("${CLI[@]}" restore --profile-id "$ID" --revision r000001)"
[[ "$(jq -r .current_revision <<<"$RESTORED")" == r000003 ]]
[[ -f "$PROFILE_DIR/revisions/r000001/config.enc.json" && -f "$PROFILE_DIR/revisions/r000002/config.enc.json" ]]
[[ "$(jq -r .config.storage "$PROFILE_DIR/revisions/r000003/manifest.json")" == aes-256-gcm ]]
python3 - "$ROOT" "$STORE" "$KEY" "$ID" <<'PYCRYPT3'
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(sys.argv[1]) / "scripts"))
from xray_profiles import ProfileStore
plain, _ = ProfileStore(sys.argv[2], sys.argv[3]).read_revision_config(sys.argv[4], "r000003")
assert __import__("json").loads(plain)["log"]["loglevel"] == "warning"
assert __import__("json").loads(plain)["test_secret"] == "profile-secret-marker"
PYCRYPT3
if "${WRONG_CLI[@]}" restore --profile-id "$ID" --revision r000003 >"$TMP/wrong-key.out" 2>&1; then
	echo "ERROR: se aceptó una clave maestra incorrecta." >&2
	exit 1
fi
VERSIONS="$("${CLI[@]}" versions --profile-id "$ID")"
[[ "$(jq length <<<"$VERSIONS")" == 3 ]]
[[ "$(jq -r '[.[] | select(.current)] | length' <<<"$VERSIONS")" == 1 ]]
# Las operaciones de lectura/restauración rechazan una revisión cuyo hash no coincide.
cp "$PROFILE_DIR/revisions/r000003/config.enc.json" "$TMP/current-config.backup"
python3 - "$PROFILE_DIR/revisions/r000003/config.enc.json" <<'PYTAMPER'
import base64, json, pathlib, sys
p=pathlib.Path(sys.argv[1]); value=json.loads(p.read_text())
data=bytearray(base64.b64decode(value["ciphertext"])); data[0] ^= 1
value["ciphertext"]=base64.b64encode(data).decode("ascii")
p.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")))
p.chmod(0o600)
PYTAMPER
if "${CLI[@]}" restore --profile-id "$ID" --revision r000003 >"$TMP/tampered-restore.out" 2>&1; then
	echo "ERROR: se restauró una revisión alterada." >&2
	exit 1
fi
if "${CLI[@]}" list >"$TMP/tampered-list.out" 2>&1; then
	echo "ERROR: el catálogo aceptó la revisión actual alterada." >&2
	exit 1
fi
mv "$TMP/current-config.backup" "$PROFILE_DIR/revisions/r000003/config.enc.json"
chmod 600 "$PROFILE_DIR/revisions/r000003/config.enc.json"
printf '%s\n' '{"x":1,"x":2}' >"$TMP/duplicate-key.json"
if "${CLI[@]}" create --name "Clave duplicada" --config-file "$TMP/duplicate-key.json" >"$TMP/bad.out" 2>&1; then
	echo "ERROR: se aceptaron claves JSON duplicadas." >&2
	exit 1
fi
printf '%s\n' '[]' >"$TMP/array.json"
if "${CLI[@]}" create --name "Array" --config-file "$TMP/array.json" >"$TMP/bad-array.out" 2>&1; then
	echo "ERROR: se aceptó una configuración que no es objeto." >&2
	exit 1
fi
ln -s "$CONFIG" "$TMP/source-link.json"
if "${CLI[@]}" create --name "Symlink" --config-file "$TMP/source-link.json" >"$TMP/link.out" 2>&1; then
	echo "ERROR: se aceptó symlink de origen." >&2
	exit 1
fi
ln "$CONFIG" "$TMP/source-hardlink.json"
if "${CLI[@]}" create --name "Hardlink" --config-file "$TMP/source-hardlink.json" >"$TMP/hardlink.out" 2>&1; then
	echo "ERROR: se aceptó hardlink de origen." >&2
	exit 1
fi
ln -s "$STORE" "$TMP/store-link"
if python3 "$ROOT/scripts/xray_profiles.py" --store "$TMP/store-link" list >"$TMP/store-link.out" 2>&1; then
	echo "ERROR: se aceptó un almacén simbólico." >&2
	exit 1
fi
# Dos procesos que intentan registrar el mismo nombre deben serializarse.
set +e
"${CLI[@]}" create --name "Perfil concurrente" >"$TMP/race-a.out" 2>"$TMP/race-a.err" &
PID_A=$!
"${CLI[@]}" create --name "Perfil concurrente" >"$TMP/race-b.out" 2>"$TMP/race-b.err" &
PID_B=$!
wait "$PID_A"
STATUS_A=$?
wait "$PID_B"
STATUS_B=$?
set -e
[[ $(((STATUS_A == 0) + (STATUS_B == 0))) == 1 ]]
LIST="$("${CLI[@]}" list)"
[[ "$(jq length <<<"$LIST")" == 4 ]]
[[ "$(jq -r '[.[] | select(.active_status == "not_integrated")] | length' <<<"$LIST")" == 4 ]]

# El menú real crea y consulta un perfil usando un almacén temporal.
APP_ROOT="$ROOT"
# shellcheck disable=SC2034
export XRAY_MANAGER_PROFILES_DIR="$STORE"
export XRAY_MANAGER_MASTER_KEY_FILE="$KEY"
# shellcheck disable=SC1091
source "$ROOT/lib/ui.sh"
# shellcheck disable=SC1091
source "$ROOT/modules/profiles.sh"
printf '1\nPerfil desde menú\n\n\n1\ns\n\n0\n' | menu_profiles >"$TMP/menu-create.out"
grep -q 'Perfil creado' "$TMP/menu-create.out"
printf '2\n0\n' | menu_profiles >"$TMP/menu-list.out"
grep -q 'CONSULTAR PERFILES' "$TMP/menu-list.out"
grep -q 'Perfil desde menú' "$TMP/menu-list.out"

# Transacciones multiarchivo: fallo normal, caída abrupta y recuperación WAL.
python3 - "$ROOT" "$TMP/transaction-tests" <<'PYTXN'
import os, pathlib, sys
root = pathlib.Path(sys.argv[1])
test_root = pathlib.Path(sys.argv[2])
test_root.mkdir(mode=0o700)
os.chmod(test_root, 0o700)
key = test_root / "synthetic.key"
key.write_bytes(os.urandom(32)); key.chmod(0o600)
sys.path.insert(0, str(root / "scripts"))
import xray_profiles as xp
store = xp.ProfileStore(str(test_root / "store"), str(key))
created = store.create("Nombre inicial", config_data=b'{"version":1}')
pid = created["profile_id"]
original_atomic_write = xp.atomic_write
# Fail exactly when writing the new catalog, after metadata has been written.
failed = {"done": False}
def fail_catalog(path, data):
    if pathlib.Path(path) == store.catalog_path and not failed["done"]:
        failed["done"] = True
        raise OSError("injected catalog write failure")
    return original_atomic_write(path, data)
xp.atomic_write = fail_catalog
try:
    store.rename(pid, "Nombre que debe revertirse")
except OSError:
    pass
else:
    raise AssertionError("injected write failure did not escape")
finally:
    xp.atomic_write = original_atomic_write
assert store.list_profiles()[0]["name"] == "Nombre inicial"
assert not store.transaction_path.exists()
# Directory-fsync failure after metadata replace must trigger rollback.
import stat
original_fsync = xp.os.fsync
failed = {"done": False}
def fail_first_directory_fsync(fd):
    if stat.S_ISDIR(os.fstat(fd).st_mode) and not failed["done"]:
        failed["done"] = True
        raise OSError("injected directory fsync failure")
    return original_fsync(fd)
def arm_fsync_after_journal(path, data):
    result = original_atomic_write(path, data)
    if pathlib.Path(path) == store.transaction_path:
        xp.os.fsync = fail_first_directory_fsync
    return result
xp.atomic_write = arm_fsync_after_journal
try:
    store.rename(pid, "Nombre con fsync fallido")
except OSError:
    pass
else:
    raise AssertionError("directory fsync fault was not propagated")
finally:
    xp.atomic_write = original_atomic_write
    xp.os.fsync = original_fsync
assert store.list_profiles()[0]["name"] == "Nombre inicial"
assert not store.transaction_path.exists()
# Update writes a new revision plus metadata/catalog; failure removes the uncommitted revision.
before_revisions = len(store.versions(pid))
failed = {"done": False}
def fail_update_catalog(path, data):
    if pathlib.Path(path) == store.catalog_path and not failed["done"]:
        failed["done"] = True
        raise OSError("injected update catalog failure")
    return original_atomic_write(path, data)
xp.atomic_write = fail_update_catalog
try:
    store.update(pid, name="Nombre update fallido", config_data=b'{"version":2}')
except OSError:
    pass
else:
    raise AssertionError("update fault injection did not escape")
finally:
    xp.atomic_write = original_atomic_write
assert store.list_profiles()[0]["name"] == "Nombre inicial"
assert len(store.versions(pid)) == before_revisions, "failed update must remove its uncommitted revision"
# Failure to publish the WAL itself must not leave an uncommitted revision behind.
before_revisions = len(store.versions(pid))
def fail_journal_write(path, data):
    if pathlib.Path(path) == store.transaction_path:
        raise OSError("injected journal creation failure")
    return original_atomic_write(path, data)
xp.atomic_write = fail_journal_write
try:
    store.update(pid, config_data=b'{"version":3}')
except OSError:
    pass
else:
    raise AssertionError("journal creation failure did not escape")
finally:
    xp.atomic_write = original_atomic_write
assert len(store.versions(pid)) == before_revisions, "journal failure must clean the prebuilt revision"
assert not store.transaction_path.exists()
# Simulate abrupt process death after metadata replace and before catalog replace.
def crash_before_catalog(path, data):
    if pathlib.Path(path) == store.catalog_path:
        raise SystemExit("simulated process termination")
    return original_atomic_write(path, data)
xp.atomic_write = crash_before_catalog
try:
    store.rename(pid, "Nombre no confirmado")
except SystemExit:
    pass
else:
    raise AssertionError("simulated crash was not triggered")
finally:
    xp.atomic_write = original_atomic_write
assert store.transaction_path.exists(), "WAL must survive simulated process death"
restarted = xp.ProfileStore(str(test_root / "store"), str(key))
assert restarted.list_profiles()[0]["name"] == "Nombre inicial"
assert not restarted.transaction_path.exists(), "startup recovery must consume WAL"
# Simulate death after both target files were replaced but before journal removal.
def crash_after_catalog(path, data):
    result = original_atomic_write(path, data)
    if pathlib.Path(path) == store.catalog_path:
        raise SystemExit("simulated termination after catalog replace")
    return result
xp.atomic_write = crash_after_catalog
try:
    store.rename(pid, "Nombre con commit incompleto")
except SystemExit:
    pass
else:
    raise AssertionError("post-catalog crash was not triggered")
finally:
    xp.atomic_write = original_atomic_write
assert store.transaction_path.exists()
restarted = xp.ProfileStore(str(test_root / "store"), str(key))
# Recovery itself may be interrupted; the same WAL must make rollback idempotent.
def crash_during_recovery(path, data):
    if pathlib.Path(path) == store.catalog_path:
        raise SystemExit("simulated termination during rollback")
    return original_atomic_write(path, data)
xp.atomic_write = crash_during_recovery
try:
    restarted.recover_transaction()
except SystemExit:
    pass
else:
    raise AssertionError("recovery interruption was not triggered")
finally:
    xp.atomic_write = original_atomic_write
assert restarted.transaction_path.exists(), "journal must remain after interrupted recovery"
restarted = xp.ProfileStore(str(test_root / "store"), str(key))
assert restarted.list_profiles()[0]["name"] == "Nombre inicial"
assert not restarted.transaction_path.exists()
# First-ever create: catalog did not exist when the WAL was written.
empty_store = xp.ProfileStore(str(test_root / "empty-store"), str(key))
def crash_initial_catalog(path, data):
    if pathlib.Path(path) == empty_store.catalog_path:
        raise SystemExit("simulated initial catalog interruption")
    return original_atomic_write(path, data)
xp.atomic_write = crash_initial_catalog
try:
    empty_store.create("Alta inicial interrumpida")
except SystemExit:
    pass
else:
    raise AssertionError("initial create interruption was not triggered")
finally:
    xp.atomic_write = original_atomic_write
assert empty_store.transaction_path.exists()
empty_restarted = xp.ProfileStore(str(test_root / "empty-store"), str(key))
assert empty_restarted.list_profiles() == []
assert not empty_restarted.catalog_path.exists(), "rollback must preserve initially absent catalog"
assert not empty_restarted.transaction_path.exists()
assert len(list(empty_restarted.profiles.glob("profile-*"))) == 0
# The same transaction primitive must roll back a new directory if catalog write fails.
failed = {"done": False}
def fail_create_catalog(path, data):
    if pathlib.Path(path) == restarted.catalog_path and not failed["done"]:
        failed["done"] = True
        raise OSError("injected create catalog failure")
    return original_atomic_write(path, data)
xp.atomic_write = fail_create_catalog
try:
    restarted.create("Alta que debe revertirse")
except OSError:
    pass
else:
    raise AssertionError("create fault injection did not escape")
finally:
    xp.atomic_write = original_atomic_write
assert [x["name"] for x in restarted.list_profiles()] == ["Nombre inicial"]
assert len(list(restarted.profiles.glob("profile-*"))) == 1, "failed create must remove its published profile directory"
# A failed restore must remove the revision that was not committed as current.
restarted.update(pid, config_data=b'{"version":2}')
before_revisions = len(restarted.versions(pid))
failed = {"done": False}
def fail_restore_catalog(path, data):
    if pathlib.Path(path) == restarted.catalog_path and not failed["done"]:
        failed["done"] = True
        raise OSError("injected restore catalog failure")
    return original_atomic_write(path, data)
xp.atomic_write = fail_restore_catalog
try:
    restarted.restore(pid, "r000001")
except OSError:
    pass
else:
    raise AssertionError("restore fault injection did not escape")
finally:
    xp.atomic_write = original_atomic_write
assert len(restarted.versions(pid)) == before_revisions, "failed restore must remove its uncommitted revision"
assert restarted.show(pid)["metadata"]["current_revision"] == "r000002"
# A failed duplicate must not leave a catalog-visible or orphaned destination.
failed = {"done": False}
def fail_duplicate_catalog(path, data):
    if pathlib.Path(path) == restarted.catalog_path and not failed["done"]:
        failed["done"] = True
        raise OSError("injected duplicate catalog failure")
    return original_atomic_write(path, data)
xp.atomic_write = fail_duplicate_catalog
try:
    restarted.duplicate(pid, "Copia que debe revertirse")
except OSError:
    pass
else:
    raise AssertionError("duplicate fault injection did not escape")
finally:
    xp.atomic_write = original_atomic_write
assert [x["name"] for x in restarted.list_profiles()] == ["Nombre inicial"]
assert not restarted.transaction_path.exists()
# The entire journal must be validated before the first rollback write.
from base64 import b64encode
catalog_before = restarted.catalog_path.read_bytes()
malformed_late_entry = {
    "schema_version": 1,
    "changes": [
        {"path": "catalog.json", "old": b64encode(b'{"profiles":[]}').decode("ascii")},
        {"path": "profiles/../escape/metadata.json", "old": None},
    ],
    "remove_dirs": [],
}
original_atomic_write(restarted.transaction_path, xp.json_bytes(malformed_late_entry))
try:
    restarted.recover_transaction()
except xp.ProfileError:
    pass
else:
    raise AssertionError("malformed later WAL entry was accepted")
assert restarted.catalog_path.read_bytes() == catalog_before, "invalid WAL must not partially roll back earlier targets"
assert restarted.transaction_path.exists(), "invalid WAL must be preserved for safe diagnosis"
restarted.transaction_path.unlink()
# Invalid removal targets must also be rejected before any valid snapshot is applied.
malformed_removal = {
    "schema_version": 1,
    "changes": [
        {"path": "catalog.json", "old": b64encode(b'{"profiles":[]}').decode("ascii")},
    ],
    "remove_dirs": ["profiles/../outside"],
}
original_atomic_write(restarted.transaction_path, xp.json_bytes(malformed_removal))
try:
    restarted.recover_transaction()
except xp.ProfileError:
    pass
else:
    raise AssertionError("malformed WAL removal was accepted")
assert restarted.catalog_path.read_bytes() == catalog_before, "invalid removal list must not partially roll back changes"
assert restarted.transaction_path.exists()
restarted.transaction_path.unlink()
print("PASS: rollback rename/update/restore, WAL tras caída abrupta, recuperación al reabrir, validación WAL completa antes de mutar y limpieza create/duplicate.")
PYTXN

# Limpieza de temporales huérfanos: sólo ubicaciones/patrones conocidos y artefactos root-only.
python3 - "$ROOT" "$TMP/orphan-cleanup-tests" <<'PYORPHAN'
import os, pathlib, signal, stat, sys
root = pathlib.Path(sys.argv[1])
test_root = pathlib.Path(sys.argv[2])
test_root.mkdir(mode=0o700)
os.chmod(test_root, 0o700)
key = test_root / "synthetic.key"
key.write_bytes(os.urandom(32)); key.chmod(0o600)
sys.path.insert(0, str(root / "scripts"))
import xray_profiles as xp
store = xp.ProfileStore(str(test_root / "store"), str(key))
created = store.create("Perfil que debe conservarse", config_data=b'{"safe":true}')
pid = created["profile_id"]
profile = store.profiles / pid
revisions = profile / "revisions"
valid_revision = revisions / "r000001"

def write_root_file(path, data=b"orphan", mode=0o600):
    path.write_bytes(data)
    os.chown(path, 0, 0)
    os.chmod(path, mode)

# Exact atomic-write temporary names at each controlled location.
root_tmp = store.root / (".catalog.json." + "a" * 16 + ".tmp")
wal_tmp = store.root / ("..profiles.transaction.json." + "9" * 16 + ".tmp")
meta_tmp = profile / (".metadata.json." + "b" * 16 + ".tmp")
config_tmp = valid_revision / (".config.enc.json." + "c" * 16 + ".tmp")
manifest_tmp = valid_revision / (".manifest.json." + "d" * 16 + ".tmp")
for path in (root_tmp, wal_tmp, meta_tmp, config_tmp, manifest_tmp):
    write_root_file(path)

# Fully recognizable interrupted create and revision staging directories.
new_dir = store.profiles / (".new-" + "e" * 16)
new_dir.mkdir(mode=0o700)
os.chown(new_dir, 0, 0); os.chmod(new_dir, 0o700)
(new_dir / "revisions").mkdir(mode=0o700)
os.chown(new_dir / "revisions", 0, 0); os.chmod(new_dir / "revisions", 0o700)
new_rev = new_dir / "revisions" / "r000001"
new_rev.mkdir(mode=0o700)
os.chown(new_rev, 0, 0); os.chmod(new_rev, 0o700)
write_root_file(new_rev / "config.enc.json")
write_root_file(new_rev / "manifest.json")

revision_tmp_dir = revisions / (".revision-" + "f" * 16)
revision_tmp_dir.mkdir(mode=0o700)
os.chown(revision_tmp_dir, 0, 0); os.chmod(revision_tmp_dir, 0o700)
write_root_file(revision_tmp_dir / "config.enc.json")
write_root_file(revision_tmp_dir / "manifest.json")

# Suspicious artifacts must be preserved and reported, never repaired/deleted.
suspicious_dir = store.profiles / (".new-" + "1" * 16)
suspicious_dir.mkdir(mode=0o755)
os.chown(suspicious_dir, 0, 0); os.chmod(suspicious_dir, 0o755)
bad_mode_tmp = store.root / (".catalog.json." + "2" * 16 + ".tmp")
write_root_file(bad_mode_tmp, mode=0o644)
symlink_tmp = store.root / (".catalog.json." + "3" * 16 + ".tmp")
symlink_tmp.symlink_to(root_tmp)
unknown_tmp = store.root / (".catalog.json.not-a-token.tmp")
write_root_file(unknown_tmp)
wrong_owner_tmp = store.root / (".catalog.json." + "4" * 16 + ".tmp")
write_root_file(wrong_owner_tmp)
os.chown(wrong_owner_tmp, 65534, 65534)
hardlink_tmp = store.root / (".catalog.json." + "5" * 16 + ".tmp")
write_root_file(hardlink_tmp)
external_hardlink = test_root / "external-hardlink"
os.link(hardlink_tmp, external_hardlink)

# A real valid revision must survive cleanup.
assert (valid_revision / "config.enc.json").is_file()
first = store.list_profiles()  # recovery first, then cleanup while holding the exclusive lock
assert len(first) == 1 and first[0]["profile_id"] == pid
assert not root_tmp.exists() and not wal_tmp.exists() and not meta_tmp.exists() and not config_tmp.exists() and not manifest_tmp.exists()
assert not new_dir.exists() and not revision_tmp_dir.exists()
assert suspicious_dir.exists() and bad_mode_tmp.exists() and symlink_tmp.is_symlink()
assert wrong_owner_tmp.exists() and hardlink_tmp.exists() and external_hardlink.exists() and unknown_tmp.exists()
assert wrong_owner_tmp.exists() and hardlink_tmp.exists() and external_hardlink.exists()
assert (valid_revision / "config.enc.json").is_file() and (valid_revision / "manifest.json").is_file()
assert store._cleanup_report["removed_files"] == 5
assert store._cleanup_report["removed_directories"] == 2
assert len(store._cleanup_report["anomalies"]) >= 5
second = store.cleanup_orphan_temps()
assert second["removed_files"] == 0 and second["removed_directories"] == 0, second
assert len(second["anomalies"]) == len(store._cleanup_report["anomalies"]), second

# os.replace failure removes only the unpublished temp and preserves the old destination.
original_replace = xp.os.replace
destination = store.root / "catalog.json"
before = destination.read_bytes()
def fail_replace(_src, _dst):
    raise OSError("injected replace failure")
xp.os.replace = fail_replace
try:
    try:
        xp.atomic_write(destination, b'{"must":"not publish"}')
    except OSError:
        pass
    else:
        raise AssertionError("replace fault did not escape")
finally:
    xp.os.replace = original_replace
assert destination.read_bytes() == before
assert set(store.root.glob(".catalog.json.*.tmp")) == {bad_mode_tmp, symlink_tmp, unknown_tmp, wrong_owner_tmp, hardlink_tmp}

# Directory-fsync failure happens after replace: published destination must survive.
original_fsync = xp.os.fsync
catalog_after_fsync_failure = __import__("json").loads(before)
catalog_after_fsync_failure["profiles"][0]["modified_at"] = "9999-12-31T23:59:59Z"
published_data = xp.json_bytes(catalog_after_fsync_failure)
def fail_directory_fsync(fd):
    if stat.S_ISDIR(os.fstat(fd).st_mode):
        raise OSError("injected directory fsync failure")
    return original_fsync(fd)
xp.os.fsync = fail_directory_fsync
try:
    try:
        xp.atomic_write(destination, published_data)
    except OSError:
        pass
    else:
        raise AssertionError("directory fsync fault did not escape")
finally:
    xp.os.fsync = original_fsync
assert destination.read_bytes() == published_data
assert set(store.root.glob(".catalog.json.*.tmp")) == {bad_mode_tmp, symlink_tmp, unknown_tmp, wrong_owner_tmp, hardlink_tmp}
before = destination.read_bytes()

# SIGKILL after atomic temp fsync and before replace leaves a temp that the next lock cleans.
pid_child = os.fork()
if pid_child == 0:
    def kill_before_replace(_src, _dst):
        os.kill(os.getpid(), signal.SIGKILL)
    xp.os.replace = kill_before_replace
    xp.atomic_write(destination, b'{"child":"must die"}')
    os._exit(99)
_, status = os.waitpid(pid_child, 0)
assert os.WIFSIGNALED(status) and os.WTERMSIG(status) == signal.SIGKILL
crashed_atomic = [p for p in store.root.glob(".catalog.json.*.tmp") if p not in (bad_mode_tmp, symlink_tmp, unknown_tmp, wrong_owner_tmp, hardlink_tmp)]
assert len(crashed_atomic) == 1
store.list_profiles()
assert not crashed_atomic[0].exists() and destination.read_bytes() == before

# SIGKILL during profile creation leaves .new-* staging; next operation removes it.
pid_child = os.fork()
if pid_child == 0:
    original_rename = xp.os.rename
    def kill_new(src, dst):
        if pathlib.Path(src).name.startswith(".new-"):
            os.kill(os.getpid(), signal.SIGKILL)
        return original_rename(src, dst)
    xp.os.rename = kill_new
    store.create("Alta interrumpida", config_data=b'{"child":true}')
    os._exit(99)
_, status = os.waitpid(pid_child, 0)
assert os.WIFSIGNALED(status) and os.WTERMSIG(status) == signal.SIGKILL
crashed_new = [p for p in store.profiles.glob(".new-*") if p != suspicious_dir]
assert len(crashed_new) == 1
store.list_profiles()
assert not crashed_new[0].exists()

# SIGKILL during revision publication leaves .revision-* staging; next lock cleans it.
pid_child = os.fork()
if pid_child == 0:
    original_rename = xp.os.rename
    def kill_revision(src, dst):
        if pathlib.Path(src).name.startswith(".revision-"):
            os.kill(os.getpid(), signal.SIGKILL)
        return original_rename(src, dst)
    xp.os.rename = kill_revision
    store.update(pid, config_data=b'{"child_revision":true}')
    os._exit(99)
_, status = os.waitpid(pid_child, 0)
assert os.WIFSIGNALED(status) and os.WTERMSIG(status) == signal.SIGKILL
crashed_revision = list(revisions.glob(".revision-*"))
assert len(crashed_revision) == 1
store.list_profiles()
assert not crashed_revision[0].exists()
assert [x["revision"] for x in store.versions(pid)] == ["r000001"]
assert suspicious_dir.exists() and bad_mode_tmp.exists() and symlink_tmp.is_symlink()
print("PASS: temporales exactos, WAL-before-cleanup, SIGKILL, idempotencia, anomalías preservadas y revisiones válidas.")
PYORPHAN

# PF-07: el catálogo debe rechazar esquema/tipos/fechas/identidades malformadas
# sin filtrar AttributeError/TypeError y sin mutar el archivo de origen.
python3 - "$ROOT" "$TMP/catalog-validation" <<'PFCATALOG'
import copy, json, pathlib, sys
root = pathlib.Path(sys.argv[1]); base = pathlib.Path(sys.argv[2])
base.mkdir(mode=0o700); base.chmod(0o700)
key = base / "synthetic.key"; key.write_bytes(b"K" * 32); key.chmod(0o600)
sys.path.insert(0, str(root / "scripts"))
from xray_profiles import ProfileStore, ProfileError, json_bytes
store = ProfileStore(str(base / "store"), str(key))
store.create("Perfil válido")
good = json.loads(store.catalog_path.read_text())
assert store.load_catalog() == good
cases = []
def add(label, mutate):
    value = copy.deepcopy(good); mutate(value); cases.append((label, value))
add("schema bool", lambda v: v.update(schema_version=True))
add("schema string", lambda v: v.update(schema_version="1"))
add("extra top-level", lambda v: v.update(unexpected=True))
add("profiles not list", lambda v: v.update(profiles={}))
add("profile not object", lambda v: v["profiles"].__setitem__(0, "bad"))
add("missing field", lambda v: v["profiles"][0].pop("name"))
add("extra field", lambda v: v["profiles"][0].update(extra="x"))
add("id integer", lambda v: v["profiles"][0].update(profile_id=123))
add("id malformed", lambda v: v["profiles"][0].update(profile_id="../bad"))
add("name null", lambda v: v["profiles"][0].update(name=None))
add("name integer", lambda v: v["profiles"][0].update(name=42))
add("name control", lambda v: v["profiles"][0].update(name="bad\nname"))
add("name DEL", lambda v: v["profiles"][0].update(name="bad\x7fname"))
add("created invalid type", lambda v: v["profiles"][0].update(created_at=123))
add("created invalid date", lambda v: v["profiles"][0].update(created_at="2026-02-30T00:00:00Z"))
add("modified before created", lambda v: v["profiles"][0].update(modified_at="2000-01-01T00:00:00Z"))
add("duplicate id", lambda v: v["profiles"].append(copy.deepcopy(v["profiles"][0])))
add("duplicate name", lambda v: (v["profiles"].append(copy.deepcopy(v["profiles"][0])), v["profiles"][1].update(profile_id="profile-" + "a" * 32)))
for label, malformed in cases:
    raw = json_bytes(malformed); store.catalog_path.write_bytes(raw); store.catalog_path.chmod(0o600)
    try:
        store.load_catalog()
    except ProfileError:
        pass
    except Exception as exc:
        raise AssertionError(f"{label}: uncontrolled {type(exc).__name__}: {exc}") from exc
    else:
        raise AssertionError(f"{label}: malformed catalog accepted")
    assert store.catalog_path.read_bytes() == raw, f"{label}: validation mutated catalog"
store.catalog_path.write_bytes(json_bytes(good)); store.catalog_path.chmod(0o600)
assert store.load_catalog() == good
print(f"PASS: PF-07 rejected {len(cases)} malformed catalog cases with controlled errors; valid catalog preserved.")
PFCATALOG


# PF-08/PF-09/PF-10: límites previos, reconciliación post-crash y contrato estricto de metadatos.
python3 - "$ROOT" "$TMP/pf08-pf10" <<'PFPERSISTENCE'
import copy, json, os, pathlib, signal, stat, sys
base = pathlib.Path(sys.argv[2]); base.mkdir(mode=0o700)
key = base / "synthetic.key"; key.write_bytes(b"S" * 32); key.chmod(0o600)
sys.path.insert(0, str(pathlib.Path(sys.argv[1]) / "scripts"))
import xray_profiles as xp
store = xp.ProfileStore(str(base / "store"), str(key))
created = store.create("Perfil de auditoría", config_data=b'{"v":1}')
pid = created["profile_id"]
profile = store.profiles / pid
metadata_path = profile / "metadata.json"

# PF-08: límites rechazados antes de publicar una revisión.
before = sorted(p.name for p in (profile / "revisions").iterdir())
for kwargs in (
    {"description": "D" * 4097, "config_data": b'{"v":2}'},
    {"notes": "N" * 4097, "config_data": b'{"v":2}'},
    {"config_data": b""},
    {"config_data": b"x" * (xp.MAX_CONFIG + 1)},
):
    try:
        store.update(pid, **kwargs)
    except xp.ProfileError:
        pass
    else:
        raise AssertionError(f"PF-08: accepted invalid update {list(kwargs)}")
    assert sorted(p.name for p in (profile / "revisions").iterdir()) == before
assert store.show(pid)["metadata"]["current_revision"] == "r000001"

# PF-09: kill exactly after final revision rename + directory fsync entry.
original_fsync = xp.os.fsync
revisions_dir = profile / "revisions"
rev_stat = revisions_dir.stat()
child = os.fork()
if child == 0:
    def kill_after_revision_publish(fd):
        info = os.fstat(fd)
        if stat.S_ISDIR(info.st_mode) and (info.st_dev, info.st_ino) == (rev_stat.st_dev, rev_stat.st_ino):
            os.kill(os.getpid(), signal.SIGKILL)
        return original_fsync(fd)
    xp.os.fsync = kill_after_revision_publish
    store.update(pid, config_data=b'{"v":2}')
    os._exit(99)
_, status = os.waitpid(child, 0)
assert os.WIFSIGNALED(status) and os.WTERMSIG(status) == signal.SIGKILL
assert (revisions_dir / "r000002").is_dir(), "fault injection must leave published orphan"
# The next exclusive store operation must remove the uncommitted revision.
assert store.show(pid)["metadata"]["current_revision"] == "r000001"
assert not (revisions_dir / "r000002").exists(), "PF-09: orphan revision survived recovery"
assert (revisions_dir / "r000001").is_dir(), "PF-09: committed revision was removed"

# PF-10: exact schema, exact types, real UTC timestamps and cross-field consistency.
good = json.loads(metadata_path.read_text())
cases = []
def add(label, mutate):
    value = copy.deepcopy(good); mutate(value); cases.append((label, value))
add("boolean schema", lambda v: v.update(schema_version=True))
add("string schema", lambda v: v.update(schema_version="1"))
add("extra key", lambda v: v.update(extra="x"))
add("missing key", lambda v: v.pop("notes"))
add("boolean current revision", lambda v: v.update(current_revision=True))
add("numeric current revision", lambda v: v.update(current_revision=1))
add("boolean config flag", lambda v: v.update(config_present=1))
add("invalid date", lambda v: v.update(created_at="2026-02-30T00:00:00Z"))
add("modified before created", lambda v: v.update(modified_at="2000-01-01T00:00:00Z"))
add("description type", lambda v: v.update(description=[]))
add("description too long", lambda v: v.update(description="D"*4097))
add("notes NUL", lambda v: v.update(notes="a\x00b"))
add("invalid status type", lambda v: v.update(validation_status=[]))
add("unknown status", lambda v: v.update(validation_status="unknown"))
add("last validated after current", lambda v: v.update(last_validated_revision="r999999"))
add("not validated with revision", lambda v: v.update(last_validated_revision="r000001"))
add("current revision missing on disk", lambda v: v.update(current_revision="r000002"))
add("final status without validated revision", lambda v: v.update(validation_status="valid"))
for label, malformed in cases:
    metadata_path.write_text(json.dumps(malformed))
    metadata_path.chmod(0o600)
    try:
        store.load_metadata(pid)
    except xp.ProfileError:
        pass
    except Exception as exc:
        raise AssertionError(f"PF-10 {label}: uncontrolled {type(exc).__name__}: {exc}") from exc
    else:
        raise AssertionError(f"PF-10 {label}: malformed metadata accepted")
metadata_path.write_text(json.dumps(good))
metadata_path.chmod(0o600)
assert store.load_metadata(pid) == good
print(f"PASS: PF-08 prevalidation ({4} cases), PF-09 SIGKILL after revision publication/reconciliation, PF-10 rejected {len(cases)} malformed metadata cases.")
PFPERSISTENCE

# PF-11/PF-12: strict manifest contract and safe reconciliation of published-but-unregistered profiles.
python3 - "$ROOT" "$TMP/pf11-pf12" <<'PFMANIFESTORPHANS'
import copy, json, os, pathlib, signal, stat, sys, uuid
base = pathlib.Path(sys.argv[2]); base.mkdir(mode=0o700)
key = base / "synthetic.key"; key.write_bytes(b"T" * 32); key.chmod(0o600)
sys.path.insert(0, str(pathlib.Path(sys.argv[1]) / "scripts"))
import xray_profiles as xp
store = xp.ProfileStore(str(base / "store"), str(key))
created = store.create("Perfil manifiesto", config_data=b'{"v":1}')
pid = created["profile_id"]
manifest_path = store.profile_dir(pid) / "revisions" / "r000001" / "manifest.json"
good_manifest = json.loads(manifest_path.read_text())
manifest_cases = []
def bad_manifest(label, mutate):
    value = copy.deepcopy(good_manifest); mutate(value); manifest_cases.append((label, value))
bad_manifest("boolean schema", lambda v: v.update(schema_version=True))
bad_manifest("extra top-level key", lambda v: v.update(extra="x"))
bad_manifest("missing source", lambda v: v.pop("source"))
bad_manifest("invalid timestamp", lambda v: v.update(created_at="2026-02-30T00:00:00Z"))
bad_manifest("extra config key", lambda v: v["config"].update(extra="x"))
bad_manifest("boolean plaintext size", lambda v: v["config"].update(plaintext_size_bytes=True))
bad_manifest("negative stored size", lambda v: v["config"].update(stored_size_bytes=-1))
bad_manifest("invalid hash", lambda v: v["config"].update(ciphertext_sha256="g"*64))
bad_manifest("list source type", lambda v: v.update(source=[]))
bad_manifest("list nested source type", lambda v: v.update(source={"type": [], "profile_id": pid, "revision": "r000001"}))
bad_manifest("list validation state", lambda v: v["validation"].update(xray_static=[]))
bad_manifest("boolean validation status", lambda v: v["validation"].update(status=True))
bad_manifest("inconsistent validation", lambda v: v["validation"].update(xray_static="pass", status="pending"))
for label, malformed in manifest_cases:
    raw = json.dumps(malformed).encode(); manifest_path.write_bytes(raw); manifest_path.chmod(0o600)
    try:
        store.versions(pid)
    except xp.ProfileError:
        pass
    except Exception as exc:
        raise AssertionError(f"PF-11 {label}: uncontrolled {type(exc).__name__}: {exc}") from exc
    else:
        raise AssertionError(f"PF-11 {label}: malformed manifest accepted")
manifest_path.write_text(json.dumps(good_manifest)); manifest_path.chmod(0o600)
assert store.versions(pid)[0]["revision"] == "r000001"

# Crash after final profile rename/fsync but before journal creation: next lock removes exact valid orphan.
def crash_create(identity, name, config):
    final_id = "profile-" + identity
    child = os.fork()
    if child == 0:
        xp.uuid.uuid4 = lambda: uuid.UUID(hex=identity)
        original = store._fsync_dir
        def kill_after_profile_publish(directory):
            if pathlib.Path(directory) == store.profiles:
                os.kill(os.getpid(), signal.SIGKILL)
            return original(directory)
        store._fsync_dir = kill_after_profile_publish
        store.create(name, config_data=config)
        os._exit(99)
    _, status = os.waitpid(child, 0)
    assert os.WIFSIGNALED(status) and os.WTERMSIG(status) == signal.SIGKILL
    assert (store.profiles / final_id).is_dir(), "fault injection did not leave final orphan profile"
    listed = store.list_profiles()
    assert all(item["profile_id"] != final_id for item in listed)
    assert not (store.profiles / final_id).exists(), "PF-12: verified orphan profile survived reconciliation"

crash_create("a"*32, "Alta huérfana sin config", None)
crash_create("b"*32, "Alta huérfana cifrada", b'{"orphan":true}')

# If the catalog itself is absent (first-ever create crash), preserve rather than guess.
empty_store = xp.ProfileStore(str(base / "first-create-store"), str(key))
child = os.fork()
if child == 0:
    identity = "e"*32
    xp.uuid.uuid4 = lambda: uuid.UUID(hex=identity)
    original = empty_store._fsync_dir
    def kill_first_create(directory):
        if pathlib.Path(directory) == empty_store.profiles:
            os.kill(os.getpid(), signal.SIGKILL)
        return original(directory)
    empty_store._fsync_dir = kill_first_create
    empty_store.create("Primera alta interrumpida")
    os._exit(99)
_, status = os.waitpid(child, 0)
assert os.WIFSIGNALED(status) and os.WTERMSIG(status) == signal.SIGKILL
first_orphan = empty_store.profiles / ("profile-" + "e"*32)
assert first_orphan.is_dir() and not empty_store.catalog_path.exists()
assert empty_store.list_profiles() == []
assert first_orphan.is_dir(), "PF-12: without a catalog, ambiguous profiles must be preserved"

# Duplicate has the same publication window and must be reconciled too.
child = os.fork()
if child == 0:
    identity = "c"*32
    xp.uuid.uuid4 = lambda: uuid.UUID(hex=identity)
    original = store._fsync_dir
    def kill_after_duplicate_publish(directory):
        if pathlib.Path(directory) == store.profiles:
            os.kill(os.getpid(), signal.SIGKILL)
        return original(directory)
    store._fsync_dir = kill_after_duplicate_publish
    store.duplicate(pid, "Duplicado huérfano")
    os._exit(99)
_, status = os.waitpid(child, 0)
assert os.WIFSIGNALED(status) and os.WTERMSIG(status) == signal.SIGKILL
duplicate_orphan = store.profiles / ("profile-" + "c"*32)
assert duplicate_orphan.is_dir()
assert all(item["profile_id"] != duplicate_orphan.name for item in store.list_profiles())
assert not duplicate_orphan.exists(), "PF-12: duplicate orphan survived reconciliation"

# Unverifiable candidates must be preserved, not recursively deleted.
child = os.fork()
if child == 0:
    identity = "d"*32
    xp.uuid.uuid4 = lambda: uuid.UUID(hex=identity)
    original = store._fsync_dir
    def kill_after_unverifiable_publish(directory):
        if pathlib.Path(directory) == store.profiles:
            os.kill(os.getpid(), signal.SIGKILL)
        return original(directory)
    store._fsync_dir = kill_after_unverifiable_publish
    store.create("Orphan sospechoso")
    os._exit(99)
_, status = os.waitpid(child, 0)
assert os.WIFSIGNALED(status) and os.WTERMSIG(status) == signal.SIGKILL
suspicious = store.profiles / ("profile-" + "d"*32)
assert suspicious.is_dir(), "fault injection did not leave suspicious candidate"
(suspicious / "metadata.json").chmod(0o644)
store.list_profiles()
assert suspicious.is_dir(), "PF-12: unsafe orphan should be preserved for diagnosis"
assert any("perfil huérfano no verificable" in item for item in store._cleanup_report["anomalies"]), "PF-12: preserved orphan anomaly was not reported"
assert stat.S_IMODE((suspicious / "metadata.json").stat().st_mode) == 0o644, "PF-12: cleanup must not repair unsafe metadata before preserving it"
print(f"PASS: PF-11 rejected {len(manifest_cases)} malformed manifests; PF-12 reconciled create/duplicate SIGKILL orphans and preserved unsafe candidates.")
PFMANIFESTORPHANS

printf '%s\n' 'OK: almacén, menú, copias independientes, revisiones, restauración no destructiva, concurrencia, nombres únicos y controles de filesystem.'
