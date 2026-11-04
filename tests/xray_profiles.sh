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
print("PASS: rollback rename/update/restore, WAL tras caída abrupta, recuperación al reabrir y limpieza create/duplicate.")
PYTXN

printf '%s\n' 'OK: almacén, menú, copias independientes, revisiones, restauración no destructiva, concurrencia, nombres únicos y controles de filesystem.'
