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

printf '%s\n' 'OK: almacén, menú, copias independientes, revisiones, restauración no destructiva, concurrencia, nombres únicos y controles de filesystem.'