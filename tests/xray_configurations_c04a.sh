#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT
umask 077
KEY="$TMP/master.key"
dd if=/dev/urandom of="$KEY" bs=32 count=1 status=none
chmod 600 "$KEY"
new_store() { STORE="$TMP/$1"; }
cli() { python3 "$ROOT/scripts/xray_configurations.py" --store "$STORE" --master-key "$KEY" "$@"; }
expect_fail() {
    if "$@" >"$TMP/out" 2>"$TMP/err"; then
        printf 'Expected command failure: %s\n' "$*" >&2
        exit 1
    fi
}
new_store basic
A="$(cli create --name 'Delete revisions' --template minimal)"
A_ID="$(jq -r .config_id <<<"$A")"
printf '{"log":{"loglevel":"error"}}\n' > "$TMP/edited.json"
P="$(cli preview-edit --config-id "$A_ID" --source "$TMP/edited.json")"
cli edit --config-id "$A_ID" --source "$TMP/edited.json" --expected-sha256 "$(jq -r .sha256 <<<"$P")" --expected-revision r000001 --confirm >/dev/null
B="$(cli create --name 'Keep this' --template empty)"
B_ID="$(jq -r .config_id <<<"$B")"
expect_fail cli delete --config-id "$A_ID" --expected-name 'Delete revisions'
expect_fail cli delete --config-id "$A_ID" --expected-name 'Delete revisions' --confirm
expect_fail cli delete --config-id "$A_ID" --expected-name 'Wrong name' --confirm --assert-not-active
expect_fail cli delete --config-id invalid --expected-name invalid --confirm --assert-not-active
DELETE_PREVIEW="$(cli preview-delete --config-id "$A_ID")"
[[ "$(jq -r .integrity_verified <<<"$DELETE_PREVIEW")" == true ]]
[[ "$(jq -r .operator_must_assert_not_active <<<"$DELETE_PREVIEW")" == true ]]
[[ "$(jq -r .revisions_count <<<"$DELETE_PREVIEW")" == 2 ]]
DELETED="$(cli delete --config-id "$A_ID" --expected-name 'Delete revisions' --confirm --assert-not-active)"
[[ "$(jq -r .deleted <<<"$DELETED")" == true ]]
[[ "$(jq -r .revisions_deleted <<<"$DELETED")" == 2 ]]
[[ "$(jq -r .profiles_and_profile_copies_untouched <<<"$DELETED")" == true ]]
[[ ! -e "$STORE/items/$A_ID" ]]
[[ "$(jq 'length' <<<"$(cli list)")" == 1 ]]
[[ "$(jq -r '.[0].config_id' <<<"$(cli list)")" == "$B_ID" ]]
cli delete --config-id "$B_ID" --expected-name 'Keep this' --confirm --assert-not-active >/dev/null
[[ "$(jq 'length' <<<"$(cli list)")" == 0 ]]

new_store integrity
C="$(cli create --name 'Corrupt ciphertext' --template minimal)"
C_ID="$(jq -r .config_id <<<"$C")"
printf 'tamper\n' >> "$STORE/items/$C_ID/revisions/r000001/config.enc.json"
expect_fail cli delete --config-id "$C_ID" --expected-name 'Corrupt ciphertext' --confirm --assert-not-active
[[ -d "$STORE/items/$C_ID" ]]
[[ "$(jq -r '.configurations[0].config_id' "$STORE/catalog.json")" == "$C_ID" ]]

new_store unexpected
D="$(cli create --name 'Unexpected file' --template empty)"
D_ID="$(jq -r .config_id <<<"$D")"
printf 'unexpected\n' > "$STORE/items/$D_ID/extra"
chmod 600 "$STORE/items/$D_ID/extra"
expect_fail cli delete --config-id "$D_ID" --expected-name 'Unexpected file' --confirm --assert-not-active
[[ -f "$STORE/items/$D_ID/extra" ]]
[[ "$(jq -r '.configurations[0].config_id' "$STORE/catalog.json")" == "$D_ID" ]]

new_store crash-rename
E="$(cli create --name 'Crash rename' --template minimal)"
E_ID="$(jq -r .config_id <<<"$E")"
set +e
python3 - "$ROOT" "$STORE" "$KEY" "$E_ID" <<'PYCRASHRENAME'
import os, pathlib, signal, sys
sys.path.insert(0, str(pathlib.Path(sys.argv[1]) / "scripts"))
import xray_configurations as xc
store=xc.ConfigurationStore(sys.argv[2], sys.argv[3])
original=xc.os.rename
def crash(src, dst):
    original(src, dst)
    if pathlib.Path(dst).name.startswith(".delete-"):
        os.kill(os.getpid(), signal.SIGKILL)
xc.os.rename=crash
store.delete(sys.argv[4], "Crash rename", True, True)
PYCRASHRENAME
STATUS=$?
set -e
[[ "$STATUS" -eq 137 ]]
[[ -f "$STORE/.configurations.transaction.json" ]]
[[ "$(jq -r '.[0].config_id' <<<"$(cli list)")" == "$E_ID" ]]
[[ -d "$STORE/items/$E_ID" ]]
[[ ! -e "$STORE/.configurations.transaction.json" ]]
if find "$STORE/items" -maxdepth 1 -name ".delete-$E_ID-*" | grep -q .; then exit 1; fi

new_store crash-catalog
F="$(cli create --name 'Crash catalog' --template minimal)"
F_ID="$(jq -r .config_id <<<"$F")"
set +e
python3 - "$ROOT" "$STORE" "$KEY" "$F_ID" <<'PYCRASHCATALOG'
import os, pathlib, signal, sys
sys.path.insert(0, str(pathlib.Path(sys.argv[1]) / "scripts"))
import xray_configurations as xc
store=xc.ConfigurationStore(sys.argv[2], sys.argv[3])
original=xc.atomic_write
def crash(path, data):
    original(path, data)
    if pathlib.Path(path) == store.catalog_path:
        os.kill(os.getpid(), signal.SIGKILL)
xc.atomic_write=crash
store.delete(sys.argv[4], "Crash catalog", True, True)
PYCRASHCATALOG
STATUS=$?
set -e
[[ "$STATUS" -eq 137 ]]
[[ "$(jq -r '.[0].config_id' <<<"$(cli list)")" == "$F_ID" ]]
[[ -d "$STORE/items/$F_ID" ]]
[[ ! -e "$STORE/.configurations.transaction.json" ]]

new_store crash-committed
G="$(cli create --name 'Crash committed' --template minimal)"
G_ID="$(jq -r .config_id <<<"$G")"
set +e
python3 - "$ROOT" "$STORE" "$KEY" "$G_ID" <<'PYCRASHCOMMITTED'
import os, pathlib, signal, sys
sys.path.insert(0, str(pathlib.Path(sys.argv[1]) / "scripts"))
import xray_configurations as xc
store=xc.ConfigurationStore(sys.argv[2], sys.argv[3])
original=xc.shutil.rmtree
def crash(path, *args, **kwargs):
    if pathlib.Path(path).name.startswith(".delete-"):
        os.kill(os.getpid(), signal.SIGKILL)
    return original(path, *args, **kwargs)
xc.shutil.rmtree=crash
store.delete(sys.argv[4], "Crash committed", True, True)
PYCRASHCOMMITTED
STATUS=$?
set -e
[[ "$STATUS" -eq 137 ]]
[[ -f "$STORE/.configurations.transaction.json" ]]
[[ "$(jq 'length' <<<"$(cli list)")" == 0 ]]
[[ ! -e "$STORE/.configurations.transaction.json" ]]
if find "$STORE/items" -maxdepth 1 -name ".delete-$G_ID-*" | grep -q .; then exit 1; fi

printf '%s\n' 'PASS: C-04A deletion guards, full revision integrity, preservation on corruption, tombstone WAL rollback/commit recovery and catalog isolation.'
