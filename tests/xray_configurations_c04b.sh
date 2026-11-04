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
A="$("${CLI[@]}" create --name 'Batch A' --template minimal | jq -r .config_id)"
B="$("${CLI[@]}" create --name 'Batch B' --template minimal | jq -r .config_id)"
MISSING='config-00000000000000000000000000000000'
printf '%s' 'EXISTING' > "$TMP/existing.json"
cat > "$TMP/manifest.json" <<EOF
{"schema_version":1,"exports":[
 {"config_id":"$A","revision":null,"destination":"$TMP/a.json","overwrite":false},
 {"config_id":"$B","revision":null,"destination":"$TMP/existing.json","overwrite":false},
 {"config_id":"$MISSING","revision":null,"destination":"$TMP/missing.json","overwrite":false}
]}
EOF
chmod 600 "$TMP/manifest.json"
PREVIEW="$("${CLI[@]}" preview-export-batch --manifest "$TMP/manifest.json")"
[[ "$(jq -r .total <<<"$PREVIEW")" == 3 ]]
[[ "$(jq -r .ready <<<"$PREVIEW")" == 1 ]]
[[ "$(jq -r .errors <<<"$PREVIEW")" == 2 ]]
[[ "$(jq -r '.exports[0].status' <<<"$PREVIEW")" == ready ]]
[[ "$(jq -r '.exports[1].status' <<<"$PREVIEW")" == error ]]
[[ "$(jq -r '.exports[2].status' <<<"$PREVIEW")" == error ]]
HASH="$(jq -r .manifest_sha256 <<<"$PREVIEW")"
PREVIEW_HASH="$(jq -r .preview_sha256 <<<"$PREVIEW")"
if "${CLI[@]}" export-batch --manifest "$TMP/manifest.json" --expected-manifest-sha256 "$HASH" --expected-preview-sha256 "$PREVIEW_HASH" >"$TMP/no-confirm.out" 2>&1; then echo 'ERROR: export-batch sin --confirm aceptado' >&2; exit 1; fi
if "${CLI[@]}" export-batch --manifest "$TMP/manifest.json" --expected-manifest-sha256 "$(printf '0%.0s' {1..64})" --expected-preview-sha256 "$PREVIEW_HASH" --confirm >"$TMP/hash-mismatch.out" 2>&1; then echo 'ERROR: hash de manifiesto incorrecto aceptado' >&2; exit 1; fi
RESULT="$("${CLI[@]}" export-batch --manifest "$TMP/manifest.json" --expected-manifest-sha256 "$HASH" --expected-preview-sha256 "$PREVIEW_HASH" --confirm)"
[[ "$(jq -r .exported <<<"$RESULT")" == 1 ]]
[[ "$(jq -r .errors <<<"$RESULT")" == 2 ]]
[[ "$(jq -r '.results[0].status' <<<"$RESULT")" == exported ]]
[[ "$(jq -r '.results[1].status' <<<"$RESULT")" == error ]]
[[ "$(jq -r '.results[2].status' <<<"$RESULT")" == error ]]
[[ "$(stat -c '%a' "$TMP/a.json")" == 600 ]]
[[ "$(stat -c '%u:%g' "$TMP/a.json")" == 0:0 ]]
printf '%s\n' '{"log":{"loglevel":"warning"}}' > "$TMP/expected.json"
cmp -s "$TMP/expected.json" "$TMP/a.json"
cmp -s <(printf 'EXISTING') "$TMP/existing.json"
# La revisión actual se fija en preview: una revisión nueva invalida el hash de preview anterior.
cat > "$TMP/stale.json" <<EOF
{"schema_version":1,"exports":[{"config_id":"$A","revision":null,"destination":"$TMP/stale-output.json","overwrite":false}]}
EOF
chmod 600 "$TMP/stale.json"
STALE_PREVIEW="$("${CLI[@]}" preview-export-batch --manifest "$TMP/stale.json")"
STALE_MANIFEST_HASH="$(jq -r .manifest_sha256 <<<"$STALE_PREVIEW")"
STALE_PREVIEW_HASH="$(jq -r .preview_sha256 <<<"$STALE_PREVIEW")"
printf '%s\n' '{"log":{"loglevel":"debug"}}' > "$TMP/edit-a.json"
python3 - "$ROOT" "$STORE" "$KEY" "$A" "$TMP/edit-a.json" <<'PYEDIT'
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(sys.argv[1]) / 'scripts'))
from xray_configurations import ConfigurationStore
sc = ConfigurationStore(sys.argv[2], sys.argv[3])
preview = sc.preview_edit(sys.argv[4], sys.argv[5])
sc.edit(sys.argv[4], sys.argv[5], preview['sha256'], preview['current_revision'])
PYEDIT
if "${CLI[@]}" export-batch --manifest "$TMP/stale.json" --expected-manifest-sha256 "$STALE_MANIFEST_HASH" --expected-preview-sha256 "$STALE_PREVIEW_HASH" --confirm >"$TMP/stale-preview.out" 2>&1; then echo 'ERROR: revisión nueva después de preview no detectada' >&2; exit 1; fi
[[ ! -e "$TMP/stale-output.json" ]]
# Destinos repetidos: ambas entradas deben quedar bloqueadas; ninguna escritura parcial.
cat > "$TMP/duplicate.json" <<EOF
{"schema_version":1,"exports":[
 {"config_id":"$A","revision":null,"destination":"$TMP/dup.json","overwrite":false},
 {"config_id":"$B","revision":null,"destination":"$TMP/dup.json","overwrite":false}
]}
EOF
chmod 600 "$TMP/duplicate.json"
DUP="$("${CLI[@]}" preview-export-batch --manifest "$TMP/duplicate.json")"
[[ "$(jq -r .ready <<<"$DUP")" == 0 ]]
[[ "$(jq -r .errors <<<"$DUP")" == 2 ]]
DUP_HASH="$(jq -r .manifest_sha256 <<<"$DUP")"
DUP_PREVIEW_HASH="$(jq -r .preview_sha256 <<<"$DUP")"
DUP_RESULT="$("${CLI[@]}" export-batch --manifest "$TMP/duplicate.json" --expected-manifest-sha256 "$DUP_HASH" --expected-preview-sha256 "$DUP_PREVIEW_HASH" --confirm)"
[[ "$(jq -r .exported <<<"$DUP_RESULT")" == 0 ]]
[[ ! -e "$TMP/dup.json" ]]
# Ruta con '..' y destino symlink se rechazan por elemento.
cat > "$TMP/unsafe.json" <<EOF
{"schema_version":1,"exports":[
 {"config_id":"$A","revision":null,"destination":"$TMP/../escape.json","overwrite":false},
 {"config_id":"$B","revision":null,"destination":"$TMP/link.json","overwrite":true}
]}
EOF
chmod 600 "$TMP/unsafe.json"
ln -s "$TMP/existing.json" "$TMP/link.json"
UNSAFE="$("${CLI[@]}" preview-export-batch --manifest "$TMP/unsafe.json")"
[[ "$(jq -r .ready <<<"$UNSAFE")" == 0 ]]
[[ "$(jq -r .errors <<<"$UNSAFE")" == 2 ]]
# Contratos estrictos, symlink/hardlink y hash del manifiesto.
printf '%s\n' '{"schema_version":true,"exports":[]}' > "$TMP/bad.json"; chmod 600 "$TMP/bad.json"
if "${CLI[@]}" preview-export-batch --manifest "$TMP/bad.json" >"$TMP/bad.out" 2>&1; then echo 'ERROR: manifiesto malformado aceptado' >&2; exit 1; fi
ln -s "$TMP/manifest.json" "$TMP/manifest-link.json"
if "${CLI[@]}" preview-export-batch --manifest "$TMP/manifest-link.json" >"$TMP/link-manifest.out" 2>&1; then echo 'ERROR: manifiesto symlink aceptado' >&2; exit 1; fi
ln "$TMP/manifest.json" "$TMP/manifest-hardlink.json"
if "${CLI[@]}" preview-export-batch --manifest "$TMP/manifest-hardlink.json" >"$TMP/hardlink-manifest.out" 2>&1; then echo 'ERROR: manifiesto hardlink aceptado' >&2; exit 1; fi
# Fallo simulado en la primera exportación no impide completar la segunda.
python3 - "$ROOT" "$STORE" "$KEY" "$A" "$B" "$TMP/partial.json" "$TMP/partial-a.json" "$TMP/partial-b.json" <<'PY'
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(sys.argv[1]) / 'scripts'))
from xray_configurations import ConfigurationStore
root, store_path, key, a, b, manifest_path, out_a, out_b = sys.argv[1:]
manifest = {"schema_version": 1, "exports": [
    {"config_id": a, "revision": None, "destination": out_a, "overwrite": False},
    {"config_id": b, "revision": None, "destination": out_b, "overwrite": False},
]}
pathlib.Path(manifest_path).write_text(json.dumps(manifest), encoding='utf-8')
pathlib.Path(manifest_path).chmod(0o600)
sc = ConfigurationStore(store_path, key)
original = sc.export_file
def injected(cid, *args, **kwargs):
    if cid == a:
        raise OSError('injected per-item failure')
    return original(cid, *args, **kwargs)
sc.export_file = injected
preview = sc.preview_export_batch(manifest_path)
result = sc.export_batch(manifest_path, preview['manifest_sha256'], preview['preview_sha256'], True)
assert result['exported'] == 1 and result['errors'] == 1, result
assert result['results'][0]['status'] == 'error'
assert result['results'][1]['status'] == 'exported'
assert not pathlib.Path(out_a).exists() and pathlib.Path(out_b).is_file()
PY
printf '%s\n' 'PASS: C-04B preview/confirmación, hash optimista, exportación parcial, destinos seguros, duplicados y manifiestos estrictos.'
