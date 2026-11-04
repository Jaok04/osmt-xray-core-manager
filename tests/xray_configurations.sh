#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT
umask 077
KEY="$TMP/master.key"
WRONG="$TMP/wrong.key"
dd if=/dev/urandom of="$KEY" bs=32 count=1 status=none
dd if=/dev/urandom of="$WRONG" bs=32 count=1 status=none
chmod 600 "$KEY" "$WRONG"
STORE="$TMP/store"
CLI=(python3 "$ROOT/scripts/xray_configurations.py" --store "$STORE" --master-key "$KEY")
EMPTY="$("${CLI[@]}" create --name 'Configuración vacía')"
[[ "$(jq -r .config_present <<<"$EMPTY")" == false ]]
[[ "$(jq -r .current_revision <<<"$EMPTY")" == null ]]
MINIMAL="$("${CLI[@]}" create --name 'Plantilla mínima' --template minimal)"
ID="$(jq -r .config_id <<<"$MINIMAL")"
REV="$(jq -r .current_revision <<<"$MINIMAL")"
[[ "$REV" == r000001 ]]
DIR="$STORE/items/$ID"
[[ "$(stat -c '%a' "$STORE")" == 700 && "$(stat -c '%a' "$STORE/items")" == 700 ]]
[[ "$(stat -c '%a' "$DIR")" == 700 && "$(stat -c '%a' "$DIR/revisions/$REV")" == 700 ]]
[[ "$(stat -c '%a' "$DIR/metadata.json")" == 600 && "$(stat -c '%a' "$DIR/revisions/$REV/config.enc.json")" == 600 ]]
! grep -q '"loglevel"' "$DIR/revisions/$REV/config.enc.json"
[[ "$(jq -r .config.storage "$DIR/revisions/$REV/manifest.json")" == aes-256-gcm ]]
python3 - "$ROOT" "$STORE" "$KEY" "$ID" "$REV" <<'PY'
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(sys.argv[1]) / 'scripts'))
from xray_configurations import ConfigurationStore
store = ConfigurationStore(sys.argv[2], sys.argv[3])
plain, manifest = store.verify_revision(sys.argv[4], sys.argv[5])
assert plain == b'{"log":{"loglevel":"warning"}}\n'
assert manifest['validation']['status'] == 'pending'
PY
LIST="$("${CLI[@]}" list)"
[[ "$(jq length <<<"$LIST")" ==  2 ]]
[[ "$(jq -r '[.[] | select(.activation_status == "not_managed_by_independent_configurations")] | length' <<<"$LIST")" == 2 ]]
SHOW="$("${CLI[@]}" show --config-id "$ID")"
[[ "$(jq -r .revision_manifest.revision <<<"$SHOW")" == "$REV" ]]
if "${CLI[@]}" create --name 'PLANTILLA MÍNIMA' --template minimal >"$TMP/duplicate.out" 2>&1; then echo 'ERROR: nombre duplicado aceptado' >&2; exit 1; fi
# Clave equivocada: autenticación AES-GCM debe fallar.
WRONG_CLI=(python3 "$ROOT/scripts/xray_configurations.py" --store "$STORE" --master-key "$WRONG")
if "${WRONG_CLI[@]}" show --config-id "$ID" >"$TMP/wrong.out" 2>&1; then echo 'ERROR: clave incorrecta aceptada' >&2; exit 1; fi
# Alterar ciphertext y recalcular hash no evita el control GCM.
cp "$DIR/revisions/$REV/config.enc.json" "$TMP/blob.backup"
python3 - "$DIR/revisions/$REV/config.enc.json" "$DIR/revisions/$REV/manifest.json" <<'PYTAMPER'
import base64, hashlib, json, pathlib, sys
blob_path, manifest_path = map(pathlib.Path, sys.argv[1:])
blob = json.loads(blob_path.read_text())
data = bytearray(base64.b64decode(blob['ciphertext'])); data[0] ^= 1
blob['ciphertext'] = base64.b64encode(data).decode()
encoded = json.dumps(blob, sort_keys=True, indent=2).encode() + b'\n'
blob_path.write_bytes(encoded); blob_path.chmod(0o600)
manifest = json.loads(manifest_path.read_text())
manifest['config']['stored_size_bytes'] = len(encoded)
manifest['config']['ciphertext_sha256'] = hashlib.sha256(encoded).hexdigest()
manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n'); manifest_path.chmod(0o600)
PYTAMPER
if "${CLI[@]}" show --config-id "$ID" >"$TMP/tampered.out" 2>&1; then echo 'ERROR: ciphertext alterado aceptado' >&2; exit 1; fi
mv "$TMP/blob.backup" "$DIR/revisions/$REV/config.enc.json"; chmod 600 "$DIR/revisions/$REV/config.enc.json"
# Catálogo inseguro/corrupto se rechaza y no se repara automáticamente.
cp "$STORE/catalog.json" "$TMP/catalog.backup"
printf '%s\n' '{"schema_version":true,"configurations":[]}' > "$STORE/catalog.json"; chmod 600 "$STORE/catalog.json"
if "${CLI[@]}" list >"$TMP/catalog-bad.out" 2>&1; then echo 'ERROR: catálogo malformado aceptado' >&2; exit 1; fi
mv "$TMP/catalog.backup" "$STORE/catalog.json"; chmod 600 "$STORE/catalog.json"
# No se crea ni regenera la clave maestra cuando falta.
NO_KEY_STORE="$TMP/no-key-store"
NO_KEY_CLI=(python3 "$ROOT/scripts/xray_configurations.py" --store "$NO_KEY_STORE" --master-key "$TMP/missing.key")
if "${NO_KEY_CLI[@]}" create --name 'No debe crear clave' --template minimal >"$TMP/no-key.out" 2>&1; then echo 'ERROR: persistencia sin clave maestra' >&2; exit 1; fi
[[ ! -e "$TMP/missing.key" ]]
[[ ! -e "$NO_KEY_STORE/catalog.json" ]]
printf '%s\n' 'PASS: C-01 create/list/show, plantillas, contratos, permisos, AES-256-GCM, AAD, corrupción y clave sintética.'
# SIGKILL après publicación del catálogo, antes de retirar WAL: siguiente lock revierte.
CRASH_STORE="$TMP/crash-store"
CRASH_CLI=(python3 "$ROOT/scripts/xray_configurations.py" --store "$CRASH_STORE" --master-key "$KEY")
set +e
python3 - "$ROOT" "$CRASH_STORE" "$KEY" <<'PFSIGKILL'
import os, pathlib, signal, sys
sys.path.insert(0, str(pathlib.Path(sys.argv[1]) / 'scripts'))
import xray_configurations as xc
store = xc.ConfigurationStore(sys.argv[2], sys.argv[3])
original = xc.atomic_write
def publish_then_die(path, data):
    original(path, data)
    if path == store.catalog_path:
        os.kill(os.getpid(), signal.SIGKILL)
xc.atomic_write = publish_then_die
store.create('Crash recovery', 'minimal')
raise SystemExit('SIGKILL injection did not run')
PFSIGKILL
CRASH_STATUS=$?
set -e
[[ "$CRASH_STATUS" -eq 137 ]]
[[ -f "$CRASH_STORE/.configurations.transaction.json" ]]
[[ "$("${CRASH_CLI[@]}" list | jq length)" == 0 ]]
[[ ! -e "$CRASH_STORE/.configurations.transaction.json" ]]
[[ "$(find "$CRASH_STORE/items" -mindepth 1 -maxdepth 1 -type d | wc -l)" == 0 ]]
printf '%s\n' 'PASS: C-01 SIGKILL entre publicación y commit; recuperación WAL idempotente.'
# SIGKILL inmediatamente después de publicar el directorio, antes de actualizar catálogo.
CRASH_DIR_STORE="$TMP/crash-dir-store"
set +e
python3 - "$ROOT" "$CRASH_DIR_STORE" "$KEY" <<'PFDIRCRASH'
import os, pathlib, signal, sys
sys.path.insert(0, str(pathlib.Path(sys.argv[1]) / 'scripts'))
import xray_configurations as xc
store = xc.ConfigurationStore(sys.argv[2], sys.argv[3])
original = xc.os.rename
def rename_then_die(source, destination):
    original(source, destination)
    if pathlib.Path(destination).name.startswith('config-'):
        os.kill(os.getpid(), signal.SIGKILL)
xc.os.rename = rename_then_die
store.create('Crash after directory publication', 'minimal')
PFDIRCRASH
DIR_CRASH_STATUS=$?
set -e
[[ "$DIR_CRASH_STATUS" -eq 137 ]]
[[ -f "$CRASH_DIR_STORE/.configurations.transaction.json" ]]
[[ "$(python3 "$ROOT/scripts/xray_configurations.py" --store "$CRASH_DIR_STORE" --master-key "$KEY" list | jq length)" == 0 ]]
[[ "$(find "$CRASH_DIR_STORE/items" -mindepth 1 -maxdepth 1 -type d | wc -l)" == 0 ]]

# SIGKILL justo después de publicar WAL y antes del rename: stage se retira al recuperar.
CRASH_WAL_STORE="$TMP/crash-wal-store"
set +e
python3 - "$ROOT" "$CRASH_WAL_STORE" "$KEY" <<'PFWALCRASH'
import os, pathlib, signal, sys
sys.path.insert(0, str(pathlib.Path(sys.argv[1]) / 'scripts'))
import xray_configurations as xc
store = xc.ConfigurationStore(sys.argv[2], sys.argv[3])
original = xc.atomic_write
def wal_then_die(path, data):
    original(path, data)
    if path == store.wal_path:
        os.kill(os.getpid(), signal.SIGKILL)
xc.atomic_write = wal_then_die
store.create('Crash after WAL', 'minimal')
PFWALCRASH
WAL_CRASH_STATUS=$?
set -e
[[ "$WAL_CRASH_STATUS" -eq 137 ]]
[[ -f "$CRASH_WAL_STORE/.configurations.transaction.json" ]]
[[ "$(python3 "$ROOT/scripts/xray_configurations.py" --store "$CRASH_WAL_STORE" --master-key "$KEY" list | jq length)" == 0 ]]
[[ "$(find "$CRASH_WAL_STORE/items" -mindepth 1 -maxdepth 1 -type d | wc -l)" == 0 ]]
printf '%s\n' 'PASS: C-01 crash recovery antes de rename, después de rename y después de catálogo.'

# C-02: importación con vista previa, UTF-8 exacto y borradores no válidos.
IMPORT_SOURCE="$TMP/source-valid.json"
printf '\357\273\277%s' '{"inbounds":[],"outbounds":[{"protocol":"freedom"}],"routing":{"rules":[]},"dns":{"servers":[]},"custom":{"keep":true}}' > "$IMPORT_SOURCE"
SOURCE_BEFORE="$(sha256sum "$IMPORT_SOURCE" | awk '{print $1}')"
PREVIEW="$("${CLI[@]}" preview-import --source "$IMPORT_SOURCE")"
[[ "$(jq -r .json_valid <<<"$PREVIEW")" == true ]]
[[ "$(jq -r .utf8_bom <<<"$PREVIEW")" == true ]]
[[ "$(jq -r '.sections_detected | join(",")' <<<"$PREVIEW")" == 'inbounds,outbounds,routing,dns' ]]
IMPORT_HASH="$(jq -r .sha256 <<<"$PREVIEW")"
IMPORTED="$("${CLI[@]}" import --source "$IMPORT_SOURCE" --name 'Importación BOM' --expected-sha256 "$IMPORT_HASH" --confirm)"
IMPORT_ID="$(jq -r .configuration.config_id <<<"$IMPORTED")"
IMPORT_REV="$(jq -r .configuration.current_revision <<<"$IMPORTED")"
[[ "$(jq -r .imported_as <<<"$IMPORTED")" == draft ]]
[[ "$(jq -r .configuration.validation_status <<<"$IMPORTED")" == not_validated ]]
[[ "$(sha256sum "$IMPORT_SOURCE" | awk '{print $1}')" == "$SOURCE_BEFORE" ]]
if "${CLI[@]}" import --source "$IMPORT_SOURCE" --name 'Sin confirmación' --expected-sha256 "$IMPORT_HASH" >"$TMP/import-no-confirm.out" 2>&1; then echo 'ERROR: importación sin --confirm aceptada' >&2; exit 1; fi
if "${CLI[@]}" import --source "$IMPORT_SOURCE" --name 'Importación BOM' --expected-sha256 "$IMPORT_HASH" --confirm >"$TMP/import-duplicate.out" 2>&1; then echo 'ERROR: nombre duplicado en importación aceptado' >&2; exit 1; fi
python3 - "$ROOT" "$STORE" "$KEY" "$IMPORT_ID" "$IMPORT_REV" "$IMPORT_SOURCE" <<'PYIMPORT'
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(sys.argv[1]) / 'scripts'))
from xray_configurations import ConfigurationStore
plain, _ = ConfigurationStore(sys.argv[2], sys.argv[3]).verify_revision(sys.argv[4], sys.argv[5])
assert plain == pathlib.Path(sys.argv[6]).read_bytes(), 'Los bytes UTF-8/BOM no se conservaron exactamente'
PYIMPORT
# La importación exige que el hash confirmado coincida con el contenido leído.
printf '%s' '{"outbounds":[]}' > "$TMP/source-changed.json"
CHANGED_PREVIEW="$("${CLI[@]}" preview-import --source "$TMP/source-changed.json")"
printf '%s' '{"outbounds":[{"protocol":"blackhole"}]}' > "$TMP/source-changed.json"
if "${CLI[@]}" import --source "$TMP/source-changed.json" --name 'Hash no coincide' --expected-sha256 "$(jq -r .sha256 <<<"$CHANGED_PREVIEW")" --confirm >"$TMP/hash-mismatch.out" 2>&1; then echo 'ERROR: se aceptó un origen cambiado tras preview' >&2; exit 1; fi
# JSON sintácticamente inválido se puede guardar sólo con aceptación expresa de Borrador.
printf '%s\n' '{"inbounds": [}' > "$TMP/source-invalid.json"
INVALID_PREVIEW="$("${CLI[@]}" preview-import --source "$TMP/source-invalid.json")"
[[ "$(jq -r .json_valid <<<"$INVALID_PREVIEW")" == false ]]
if "${CLI[@]}" import --source "$TMP/source-invalid.json" --name 'JSON inválido' --expected-sha256 "$(jq -r .sha256 <<<"$INVALID_PREVIEW")" --confirm >"$TMP/invalid-denied.out" 2>&1; then echo 'ERROR: JSON inválido importado sin aceptación' >&2; exit 1; fi
INVALID_IMPORTED="$("${CLI[@]}" import --source "$TMP/source-invalid.json" --name 'JSON inválido' --expected-sha256 "$(jq -r .sha256 <<<"$INVALID_PREVIEW")" --confirm --accept-invalid)"
INVALID_ID="$(jq -r .configuration.config_id <<<"$INVALID_IMPORTED")"
INVALID_REV="$(jq -r .configuration.current_revision <<<"$INVALID_IMPORTED")"
python3 - "$ROOT" "$STORE" "$KEY" "$INVALID_ID" "$INVALID_REV" <<'PYINVALID'
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(sys.argv[1]) / 'scripts'))
from xray_configurations import ConfigurationStore
plain, manifest = ConfigurationStore(sys.argv[2], sys.argv[3]).verify_revision(sys.argv[4], sys.argv[5])
assert plain == b'{"inbounds": [}\n'
assert manifest['validation']['status'] == 'pending'
assert manifest['source'] == 'import'
PYINVALID
# Archivo vacío: UTF-8 válido, JSON inválido, preservado como borrador de cero bytes.
: > "$TMP/source-empty.json"
EMPTY_PREVIEW="$("${CLI[@]}" preview-import --source "$TMP/source-empty.json")"
[[ "$(jq -r .size_bytes <<<"$EMPTY_PREVIEW")" == 0 ]]
[[ "$(jq -r .json_valid <<<"$EMPTY_PREVIEW")" == false ]]
EMPTY_IMPORTED="$("${CLI[@]}" import --source "$TMP/source-empty.json" --name 'Importación vacía' --expected-sha256 "$(jq -r .sha256 <<<"$EMPTY_PREVIEW")" --confirm --accept-invalid)"
EMPTY_ID="$(jq -r .configuration.config_id <<<"$EMPTY_IMPORTED")"
EMPTY_REV="$(jq -r .configuration.current_revision <<<"$EMPTY_IMPORTED")"
python3 - "$ROOT" "$STORE" "$KEY" "$EMPTY_ID" "$EMPTY_REV" <<'PYEMPTY'
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(sys.argv[1]) / 'scripts'))
from xray_configurations import ConfigurationStore
plain, manifest = ConfigurationStore(sys.argv[2], sys.argv[3]).verify_revision(sys.argv[4], sys.argv[5])
assert plain == b'' and manifest['config']['plaintext_size_bytes'] == 0
PYEMPTY
# UTF-8 inválido, symlink, hardlink y archivo demasiado grande se rechazan.
printf '\377\376\000' > "$TMP/source-not-utf8.bin"
if "${CLI[@]}" preview-import --source "$TMP/source-not-utf8.bin" >"$TMP/not-utf8.out" 2>&1; then echo 'ERROR: UTF-8 inválido aceptado' >&2; exit 1; fi
ln -s "$IMPORT_SOURCE" "$TMP/source-link.json"
if "${CLI[@]}" preview-import --source "$TMP/source-link.json" >"$TMP/symlink.out" 2>&1; then echo 'ERROR: symlink de origen aceptado' >&2; exit 1; fi
ln "$IMPORT_SOURCE" "$TMP/source-hardlink.json"
if "${CLI[@]}" preview-import --source "$TMP/source-hardlink.json" >"$TMP/hardlink.out" 2>&1; then echo 'ERROR: hardlink de origen aceptado' >&2; exit 1; fi
truncate -s 16777217 "$TMP/source-too-large.json"
if "${CLI[@]}" preview-import --source "$TMP/source-too-large.json" >"$TMP/too-large.out" 2>&1; then echo 'ERROR: archivo >16 MiB aceptado' >&2; exit 1; fi
# Exportación exacta, 0600, no sobrescribe sin autorización y rechaza symlink.
EXPORT_PATH="$TMP/exported-config.json"
EXPORTED="$("${CLI[@]}" export --config-id "$IMPORT_ID" --revision "$IMPORT_REV" --destination "$EXPORT_PATH")"
[[ "$(jq -r .verified_byte_for_byte <<<"$EXPORTED")" == true ]]
[[ "$(jq -r .mode <<<"$EXPORTED")" == 0600 ]]
[[ "$(stat -c '%a' "$EXPORT_PATH")" == 600 ]]
[[ "$(stat -c '%u:%g' "$EXPORT_PATH")" == 0:0 ]]
cmp -s "$IMPORT_SOURCE" "$EXPORT_PATH"
if "${CLI[@]}" export --config-id "$IMPORT_ID" --destination "$EXPORT_PATH" >"$TMP/export-no-overwrite.out" 2>&1; then echo 'ERROR: export sobrescribió sin autorización' >&2; exit 1; fi
"${CLI[@]}" export --config-id "$IMPORT_ID" --destination "$EXPORT_PATH" --overwrite >/dev/null
ln -s "$EXPORT_PATH" "$TMP/export-symlink.json"
if "${CLI[@]}" export --config-id "$IMPORT_ID" --destination "$TMP/export-symlink.json" --overwrite >"$TMP/export-symlink.out" 2>&1; then echo 'ERROR: destino symlink aceptado' >&2; exit 1; fi
# Exportación también conserva exactamente los bytes de un JSON inválido.
"${CLI[@]}" export --config-id "$INVALID_ID" --destination "$TMP/export-invalid.json" >/dev/null
cmp -s "$TMP/source-invalid.json" "$TMP/export-invalid.json"
printf '%s\n' 'PASS: C-02 preview/import UTF-8, BOM, JSON inválido/vacío, límites, symlink/hardlink, hash confirmado y exportación exacta.'
# Fallo parcial de escritura al exportar: un destino previo permanece intacto y no quedan temporales.
printf '%s' 'DESTINO ANTERIOR' > "$TMP/export-preserved.json"
python3 - "$ROOT" "$STORE" "$KEY" "$IMPORT_ID" "$TMP/export-preserved.json" <<'PYEXPORTFAULT'
import os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(sys.argv[1]) / 'scripts'))
import xray_configurations as xc
store = xc.ConfigurationStore(sys.argv[2], sys.argv[3])
original = os.write
calls = 0
def partial_then_fail(fd, data):
    global calls
    calls += 1
    if calls == 1:
        original(fd, bytes(data[:max(1, len(data)//2)]))
        raise OSError('injected export write failure')
    return original(fd, data)
os.write = partial_then_fail
try:
    store.export_file(sys.argv[4], sys.argv[5], overwrite=True)
except OSError:
    pass
else:
    raise SystemExit('export unexpectedly succeeded')
finally:
    os.write = original
assert pathlib.Path(sys.argv[5]).read_bytes() == b'DESTINO ANTERIOR'
assert not list(pathlib.Path(sys.argv[5]).parent.glob('.export-preserved.json.*.tmp'))
PYEXPORTFAULT
printf '%s\n' 'PASS: C-02 fallo parcial de exportación conserva destino anterior y limpia temporal.'
