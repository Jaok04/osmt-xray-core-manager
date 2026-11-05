#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
chmod 700 "$TMP"
mkdir -m 700 "$TMP/run" "$TMP/connections" "$TMP/connections/configurations" "$TMP/connections/secrets" \
    "$TMP/users" "$TMP/certificates" "$TMP/certificates/managed" "$TMP/certificates/secrets" \
    "$TMP/profiles" "$TMP/bindings"
openssl rand -out "$TMP/master.key" 32
chmod 600 "$TMP/master.key"
openssl req -x509 -newkey rsa:2048 -nodes -keyout "$TMP/cert.key" -out "$TMP/cert.pem" -days 2 -subj '/CN=menu-fixture.invalid' -addext 'subjectAltName=DNS:sni.menu.invalid,DNS:hellen.tvrc.me' >/dev/null 2>&1
chmod 600 "$TMP/cert.key" "$TMP/cert.pem"
python3 "$ROOT/scripts/certificate_store.py" --base "$TMP/certificates" --catalog "$TMP/certificates/catalog.json" \
    --managed-dir "$TMP/certificates/managed" --secrets-dir "$TMP/certificates/secrets" \
    --master-key "$TMP/master.key" --lock "$TMP/run/cert.lock" import --storage-type managed \
    --certificate-file "$TMP/cert.pem" --private-key-file "$TMP/cert.key" --certificate-id cert-menu-fixture >/dev/null
cat >"$TMP/connections/connections.json" <<'JSON'
[{"id":"menu-vless","name":"Menu VLESS WS TLS","protocol_id":"vless_ws_tls","port":443,"max_users":2,"state":"draft","runtime_applied":false}]
JSON
chmod 600 "$TMP/connections/connections.json"
cat >"$TMP/vless.json" <<'JSON'
{"schema_version":2,"connection_id":"menu-vless","protocol":"vless","mode_id":"vless_ws_tls","transport":"websocket","security":"tls","listen_address":"127.0.0.1","listen_port":443,"transport_options":{"path":"/menu","host":"ws.menu.invalid"},"security_options":{"certificate_id":"cert-menu-fixture"},"client_options":{"tls_server_name":"sni.menu.invalid"}}
JSON
chmod 600 "$TMP/vless.json"
python3 "$ROOT/scripts/vless_config_store.py" store --connection-id menu-vless --input "$TMP/vless.json" \
    --base "$TMP/connections" --catalog "$TMP/connections/connections.json" --lock "$TMP/run/integrity.lock" \
    --secrets-dir "$TMP/connections/secrets" --master-key "$TMP/master.key" \
    --certificate-catalog "$TMP/certificates/catalog.json" >/dev/null
PYTHONPATH="$ROOT/scripts" python3 - "$TMP" <<'PY'
import json,sys
from pathlib import Path
import xray_profiles
root=Path(sys.argv[1])
store=xray_profiles.ProfileStore(str(root/'profiles'),str(root/'master.key'))
config={"log":{"loglevel":"warning"},"inbounds":[],"outbounds":[{"tag":"direct","protocol":"freedom","settings":{}}]}
store.create("Menu fixture",config_data=(json.dumps(config)+"\n").encode())
PY
export APP_ROOT="$ROOT"
export XRAY_MANAGER_PROFILES_DIR="$TMP/profiles"
export XRAY_MANAGER_MASTER_KEY_FILE="$TMP/master.key"
export XRAY_MANAGER_CONNECTIONS_FILE="$TMP/connections/connections.json"
export XRAY_MANAGER_CONNECTIONS_DIR="$TMP/connections"
export XRAY_MANAGER_USERS_DIR="$TMP/users"
export XRAY_MANAGER_USERS_FILE="$TMP/users/users.json"
export XRAY_MANAGER_INTEGRITY_LOCK="$TMP/run/integrity.lock"
export XRAY_MANAGER_CERTIFICATES_CATALOG_FILE="$TMP/certificates/catalog.json"
export XRAY_MANAGER_PROFILE_BINDINGS_DIR="$TMP/bindings"
source "$ROOT/modules/users_v2.sh"
source "$ROOT/modules/profiles.sh"
mkdir -m 700 -p "$XRAY_MANAGER_USERS_DIR"
identity="$(users_identity_create)"
users_association_create "$identity" menu-vless 'Menu user' uuid 88888888-8888-4888-8888-888888888888 active unlimited 0 none 0 0 auto >/dev/null
ui_clear() { :; }
ui_title() { :; }
ui_pause() { :; }
ui_read_option() { local prompt="$1" name="$2"; read -r "$name"; }
ui_confirm() { local prompt="$1" answer; read -r answer; [[ "$answer" == [sS] || "$answer" == [sS][iI] ]]; }
printf '1\n1\ns\n' | profiles_compose_vless_ws_tls_menu >"$TMP/menu.out"
grep -q 'Host HTTP WebSocket: ws.menu.invalid' "$TMP/menu.out"
grep -q 'SNI/serverName del cliente: sni.menu.invalid' "$TMP/menu.out"
python3 - "$TMP/menu.out" <<'PYJSON'
import json,sys
from pathlib import Path
value=Path(sys.argv[1]).read_text()
start=value.index("{")
depth=0
for end in range(start,len(value)):
    if value[end] == "{": depth += 1
    elif value[end] == "}":
        depth -= 1
        if depth == 0: break
result=json.loads(value[start:end+1])
assert result["status"] == "COMPOSED" and result["runtime_changed"] is False and result["service_started"] is False
PYJSON
current="$(python3 "$ROOT/scripts/xray_profiles.py" --store "$TMP/profiles" --master-key "$TMP/master.key" list | jq -r '.[0].current_revision')"
[[ "$current" == r000002 ]]
profile_id="$(python3 "$ROOT/scripts/xray_profiles.py" --store "$TMP/profiles" --master-key "$TMP/master.key" list | jq -r '.[0].profile_id')"
python3 "$ROOT/scripts/xray_profile_validation.py" \
    --profile-store "$TMP/profiles" --master-key "$TMP/master.key" \
    --validation-store "$TMP/validation" --profile-id "$profile_id" \
    --revision "$current" --xray-binary "$(command -v xray)" >"$TMP/validation.out"
jq -e '(.result == "PASS" or .result == "PASS_WITH_WARNINGS") and .validation_status == "valid"' "$TMP/validation.out" >/dev/null
PYTHONPATH="$ROOT/scripts" python3 - "$TMP/profiles" "$TMP/master.key" "$current" <<'PY'
import json,sys
from pathlib import Path
import xray_profiles
store=xray_profiles.ProfileStore(sys.argv[1],sys.argv[2])
meta=store.load_catalog()["profiles"][0]
data,_=store.read_revision_config(meta["profile_id"],sys.argv[3])
inbound=json.loads(data)["inbounds"][0]
assert inbound["streamSettings"]["wsSettings"] == {"path":"/menu","host":"ws.menu.invalid"}
assert inbound["settings"]["clients"][0]["email"].startswith("assoc:")
PY
export XRAY_MANAGER_VLESS_PUBLIC_ADDRESS=hellen.tvrc.me
export XRAY_MANAGER_VLESS_PUBLIC_PORT=443
printf '1\n2\n\ns\n' | profiles_export_vless_clients_menu >"$TMP/export.out"
grep -q 'Endpoint público: hellen.tvrc.me:443' "$TMP/export.out"
grep -q 'vless://88888888-8888-4888-8888-888888888888@hellen.tvrc.me:443?' "$TMP/export.out"
grep -q 'sni=sni.menu.invalid' "$TMP/export.out"
grep -q 'host=ws.menu.invalid' "$TMP/export.out"
grep -q 'path=%2Fmenu' "$TMP/export.out"
grep -q 'runtime_changed.*false' "$TMP/export.out"
echo 'PASS: menú compone VLESS-WS-TLS y exporta URI NetMod para hellen.tvrc.me:443 sin activar runtime.'
