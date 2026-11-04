#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT
umask 077
KEY="$TMP/master.key"
dd if=/dev/urandom of="$KEY" bs=32 count=1 status=none
chmod 600 "$KEY"
STORE="$TMP/store"
CLI=(python3 "$ROOT/scripts/xray_configurations.py" --store "$STORE" --master-key "$KEY")
CREATED="$("${CLI[@]}" create --name 'C03 base' --template minimal)"
ID="$(jq -r .config_id <<<"$CREATED")"
REV1="$(jq -r .current_revision <<<"$CREATED")"
[[ "$REV1" == r000001 ]]
cat > "$TMP/proposed.json" <<'JSON'
{
  "log": {"loglevel": "warning"},
  "inbounds": [
    {"tag": "local-in-2", "port": 1081, "protocol": "socks"},
    {"tag": "local-in", "port": 1080, "protocol": "socks", "settings": {"auth": "password", "password": "SECRET-C03"}}
  ],
  "outbounds": [{"protocol": "freedom", "tag": "direct"}],
  "routing": {"rules": []},
  "dns": {"servers": ["1.1.1.1"]},
  "custom": {"keep": true}
}
JSON
PREVIEW="$("${CLI[@]}" preview-edit --config-id "$ID" --source "$TMP/proposed.json")"
HASH="$(jq -r .sha256 <<<"$PREVIEW")"
[[ "$(jq -r .current_revision <<<"$PREVIEW")" == "$REV1" ]]
[[ "$(jq -r .diff.structural_available <<<"$PREVIEW")" == true ]]
[[ "$(jq -r .diff.diff.values_omitted <<<"$PREVIEW")" == true ]]
if grep -q 'SECRET-C03' <<<"$PREVIEW"; then exit 1; fi
EDITED="$("${CLI[@]}" edit --config-id "$ID" --source "$TMP/proposed.json" --expected-sha256 "$HASH" --expected-revision "$REV1" --confirm)"
REV2="$(jq -r .created_revision <<<"$EDITED")"
[[ "$REV2" == r000002 ]]
[[ "$(jq -r .saved_as <<<"$EDITED")" == draft ]]
[[ "$(jq -r .previous_revision_unchanged <<<"$EDITED")" == true ]]
[[ "$(jq -r .configuration.current_revision <<<"$EDITED")" == "$REV2" ]]
if grep -q 'SECRET-C03' <<<"$EDITED"; then exit 1; fi
python3 - "$ROOT" "$STORE" "$KEY" "$ID" "$REV1" "$REV2" "$TMP/proposed.json" <<'PY'
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(sys.argv[1]) / "scripts"))
from xray_configurations import ConfigurationStore
store = ConfigurationStore(sys.argv[2], sys.argv[3])
old, _ = store.verify_revision(sys.argv[4], sys.argv[5])
new, manifest = store.verify_revision(sys.argv[4], sys.argv[6])
assert old == b'{"log":{"loglevel":"warning"}}\n'
assert new == pathlib.Path(sys.argv[7]).read_bytes()
assert manifest["source"] == "edit"
assert manifest["validation"]["status"] == "pending"
PY
HISTORY="$("${CLI[@]}" revisions --config-id "$ID")"
[[ "$(jq '.revisions | length' <<<"$HISTORY")" == 2 ]]
[[ "$(jq -r '.revisions[] | select(.revision == "r000001") | .current' <<<"$HISTORY")" == false ]]
[[ "$(jq -r '.revisions[] | select(.revision == "r000002") | .current' <<<"$HISTORY")" == true ]]
COMPARE="$("${CLI[@]}" compare --first "$ID" --second "$ID" --first-revision "$REV1" --second-revision "$REV2")"
[[ "$(jq -r .structural_available <<<"$COMPARE")" == true ]]
[[ "$(jq -r .read_only <<<"$COMPARE")" == true ]]
[[ "$(jq -r .secret_values_in_diff <<<"$COMPARE")" == false ]]
[[ "$(jq -r .diff.values_omitted <<<"$COMPARE")" == true ]]
[[ "$(jq -r .diff.equal <<<"$COMPARE")" == false ]]
if grep -q 'SECRET-C03' <<<"$COMPARE"; then exit 1; fi
SAME="$("${CLI[@]}" compare --first "$ID" --second "$ID" --first-revision "$REV2" --second-revision "$REV2")"
[[ "$(jq -r .diff.equal <<<"$SAME")" == true ]]
[[ "$(jq -r .diff.total_changes <<<"$SAME")" == 0 ]]

# Comparación entre objetos distintos: orden de claves ignorado y arrays ordenados.
cat > "$TMP/key-order.json" <<'JSONKEYS'
{
  "custom": {"keep": true},
  "dns": {"servers": ["1.1.1.1"]},
  "routing": {"rules": []},
  "outbounds": [{"tag": "direct", "protocol": "freedom"}],
  "inbounds": [
    {"protocol": "socks", "port": 1081, "tag": "local-in-2"},
    {"settings": {"password": "SECRET-C03", "auth": "password"}, "protocol": "socks", "port": 1080, "tag": "local-in"}
  ],
  "log": {"loglevel": "warning"}
}
JSONKEYS
KEY_PREVIEW="$("${CLI[@]}" preview-import --source "$TMP/key-order.json")"
KEY_IMPORT="$("${CLI[@]}" import --source "$TMP/key-order.json" --name 'C03 key order' --expected-sha256 "$(jq -r .sha256 <<<"$KEY_PREVIEW")" --confirm)"
KEY_ID="$(jq -r .configuration.config_id <<<"$KEY_IMPORT")"
KEY_REV="$(jq -r .configuration.current_revision <<<"$KEY_IMPORT")"
KEY_COMPARE="$("${CLI[@]}" compare --first "$ID" --second "$KEY_ID" --first-revision "$REV2" --second-revision "$KEY_REV")"
[[ "$(jq -r .diff.equal <<<"$KEY_COMPARE")" == true ]]
if grep -q 'SECRET-C03' <<<"$KEY_COMPARE"; then exit 1; fi

cat > "$TMP/array-order.json" <<'JSONARRAY'
{
  "log": {"loglevel": "warning"},
  "inbounds": [
    {"tag": "local-in", "port": 1080, "protocol": "socks", "settings": {"auth": "password", "password": "SECRET-C03"}},
    {"tag": "local-in-2", "port": 1081, "protocol": "socks"}
  ],
  "outbounds": [{"protocol": "freedom", "tag": "direct"}],
  "routing": {"rules": []},
  "dns": {"servers": ["1.1.1.1"]},
  "custom": {"keep": true}
}
JSONARRAY
ARRAY_PREVIEW="$("${CLI[@]}" preview-import --source "$TMP/array-order.json")"
ARRAY_IMPORT="$("${CLI[@]}" import --source "$TMP/array-order.json" --name 'C03 array order' --expected-sha256 "$(jq -r .sha256 <<<"$ARRAY_PREVIEW")" --confirm)"
ARRAY_ID="$(jq -r .configuration.config_id <<<"$ARRAY_IMPORT")"
ARRAY_REV="$(jq -r .configuration.current_revision <<<"$ARRAY_IMPORT")"
ARRAY_COMPARE="$("${CLI[@]}" compare --first "$ID" --second "$ARRAY_ID" --first-revision "$REV2" --second-revision "$ARRAY_REV")"
[[ "$(jq -r .diff.equal <<<"$ARRAY_COMPARE")" == false ]]
[[ "$(jq -r .diff.sections.inbounds <<<"$ARRAY_COMPARE")" -gt 0 ]]
if "${CLI[@]}" edit --config-id "$ID" --source "$TMP/proposed.json" --expected-sha256 "$(printf '%064d' 0)" --expected-revision "$REV2" --confirm >"$TMP/hash-fail.out" 2>&1; then echo 'ERROR: hash incorrecto aceptado' >&2; exit 1; fi
if "${CLI[@]}" edit --config-id "$ID" --source "$TMP/proposed.json" --expected-sha256 "$HASH" --expected-revision "$REV1" --confirm >"$TMP/stale-fail.out" 2>&1; then echo 'ERROR: revisión obsoleta aceptada' >&2; exit 1; fi
if "${CLI[@]}" edit --config-id "$ID" --source "$TMP/proposed.json" --expected-sha256 "$HASH" --expected-revision "$REV2" >"$TMP/no-confirm.out" 2>&1; then echo 'ERROR: edición sin confirmación aceptada' >&2; exit 1; fi
if "${CLI[@]}" edit --config-id "$ID" --source "$TMP/proposed.json" --expected-sha256 "$HASH" --expected-revision "$REV2" --confirm >"$TMP/no-op.out" 2>&1; then echo 'ERROR: edición idéntica aceptada' >&2; exit 1; fi
printf '%s\n' '{"inbounds": [}' > "$TMP/invalid.json"
INVALID_PREVIEW="$("${CLI[@]}" preview-edit --config-id "$ID" --source "$TMP/invalid.json")"
INVALID_HASH="$(jq -r .sha256 <<<"$INVALID_PREVIEW")"
[[ "$(jq -r .proposed.json_valid <<<"$INVALID_PREVIEW")" == false ]]
[[ "$(jq -r .diff.structural_available <<<"$INVALID_PREVIEW")" == false ]]
if "${CLI[@]}" edit --config-id "$ID" --source "$TMP/invalid.json" --expected-sha256 "$INVALID_HASH" --expected-revision "$REV2" --confirm >"$TMP/invalid-denied.out" 2>&1; then echo 'ERROR: JSON inválido sin aceptación guardado' >&2; exit 1; fi
INVALID_EDIT="$("${CLI[@]}" edit --config-id "$ID" --source "$TMP/invalid.json" --expected-sha256 "$INVALID_HASH" --expected-revision "$REV2" --confirm --accept-invalid)"
REV3="$(jq -r .created_revision <<<"$INVALID_EDIT")"
[[ "$REV3" == r000003 ]]
[[ "$(jq -r .saved_as <<<"$INVALID_EDIT")" == draft ]]
INVALID_COMPARE="$("${CLI[@]}" compare --first "$ID" --second "$ID" --first-revision "$REV2" --second-revision "$REV3")"
[[ "$(jq -r .structural_available <<<"$INVALID_COMPARE")" == false ]]
python3 - "$ROOT" "$STORE" "$KEY" "$ID" "$REV3" <<'PYINVALID'
import sys
sys.path.insert(0, sys.argv[1] + "/scripts")
from xray_configurations import ConfigurationStore
plain, manifest = ConfigurationStore(sys.argv[2], sys.argv[3]).verify_revision(sys.argv[4], sys.argv[5])
assert plain == b'{"inbounds": [}\n'
assert manifest["validation"]["status"] == "pending"
PYINVALID
printf '\357\273\277%s' '{"log":{"loglevel":"error"},"outbounds":[]}' > "$TMP/bom.json"
BOM_PREVIEW="$("${CLI[@]}" preview-edit --config-id "$ID" --source "$TMP/bom.json")"
BOM_HASH="$(jq -r .sha256 <<<"$BOM_PREVIEW")"
BOM_EDIT="$("${CLI[@]}" edit --config-id "$ID" --source "$TMP/bom.json" --expected-sha256 "$BOM_HASH" --expected-revision "$REV3" --confirm)"
REV4="$(jq -r .created_revision <<<"$BOM_EDIT")"
python3 - "$ROOT" "$STORE" "$KEY" "$ID" "$REV4" "$TMP/bom.json" <<'PYBOM'
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(sys.argv[1]) / "scripts"))
from xray_configurations import ConfigurationStore
plain, _ = ConfigurationStore(sys.argv[2], sys.argv[3]).verify_revision(sys.argv[4], sys.argv[5])
assert plain == pathlib.Path(sys.argv[6]).read_bytes()
assert plain.startswith(b"\xef\xbb\xbf")
PYBOM
CRASH_STORE="$TMP/crash-store"
CRASH_CLI=(python3 "$ROOT/scripts/xray_configurations.py" --store "$CRASH_STORE" --master-key "$KEY")
CRASH_CREATED="$("${CRASH_CLI[@]}" create --name 'Crash base' --template minimal)"
CRASH_ID="$(jq -r .config_id <<<"$CRASH_CREATED")"
set +e
python3 - "$ROOT" "$CRASH_STORE" "$KEY" "$CRASH_ID" "$TMP/proposed.json" <<'PFC03CRASH'
import os, pathlib, signal, sys
sys.path.insert(0, str(pathlib.Path(sys.argv[1]) / "scripts"))
import xray_configurations as xc
store = xc.ConfigurationStore(sys.argv[2], sys.argv[3])
original = xc.os.rename
def rename_then_die(source, destination):
    original(source, destination)
    if pathlib.Path(destination).name == "r000002":
        os.kill(os.getpid(), signal.SIGKILL)
xc.os.rename = rename_then_die
preview = store.preview_edit(sys.argv[4], sys.argv[5])
store.edit(sys.argv[4], sys.argv[5], preview["sha256"], "r000001")
raise SystemExit("SIGKILL injection did not run")
PFC03CRASH
CRASH_STATUS=$?
set -e
[[ "$CRASH_STATUS" -eq 137 ]]
[[ -f "$CRASH_STORE/.configurations.transaction.json" ]]
[[ "$("${CRASH_CLI[@]}" show --config-id "$CRASH_ID" | jq -r .current_revision)" == r000001 ]]
[[ ! -e "$CRASH_STORE/.configurations.transaction.json" ]]
[[ ! -e "$CRASH_STORE/items/$CRASH_ID/revisions/r000002" ]]
printf '%s\n' 'PASS: C-03 preview/edit/diff/compare/revisions, bytes/BOM, secret-safe output, stale/hash/confirm guards and WAL recovery.'