#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
chmod 711 "$TMP"
trap 'rm -rf "$TMP"' EXIT
BASE="$TMP/connections"; CERTS="$TMP/certificates"; SECRETS="$TMP/secrets"; KEYS="$TMP/keys"; RUN="$TMP/run"; RUNTIME="$TMP/cert-runtime"
mkdir -m 700 "$BASE" "$BASE/configurations" "$SECRETS" "$CERTS" "$CERTS/managed" "$CERTS/secrets" "$KEYS" "$RUN" "$TMP/mockbin"
openssl rand -out "$KEYS/master.key" 32; chmod 600 "$KEYS/master.key"
openssl req -x509 -newkey rsa:2048 -nodes -keyout "$TMP/tls.key" -out "$TMP/tls.pem" -days 2 -subj '/CN=localhost' >/dev/null 2>&1
chmod 600 "$TMP/tls.key" "$TMP/tls.pem"
cat > "$TMP/mockbin/systemctl" <<'SYSTEMCTL'
#!/usr/bin/env bash
printf 'User=www-data\nGroup=www-data\nSupplementaryGroups=\n'
SYSTEMCTL
chmod 700 "$TMP/mockbin/systemctl"
cat > "$TMP/xray" <<'XRAY'
#!/usr/bin/env bash
set -Eeuo pipefail
[[ "$1" == run && "$2" == -test && "$3" == -config && -s "$4" ]]
config="$4"
cert="$(jq -r '.inbounds[0].streamSettings.tlsSettings.certificates[0].certificateFile' "$config")"
key="$(jq -r '.inbounds[0].streamSettings.tlsSettings.certificates[0].keyFile' "$config")"
[[ "$cert" == "$XRAY_MANAGER_CERTIFICATES_RUNTIME_DIR"/*/certificate.pem ]]
[[ "$key" == "$XRAY_MANAGER_CERTIFICATES_RUNTIME_DIR"/*/private-key.pem ]]
runuser -u www-data -- test -r "$cert"
runuser -u www-data -- test -r "$key"
printf '%s\n' "$cert|$key" >>"$XRAY_TEST_CALLS"
[[ "${XRAY_FAIL:-0}" != 1 ]]
printf 'Configuration OK.\n'
XRAY
chmod 700 "$TMP/xray"
cat > "$BASE/connections.json" <<'JSON'
[{"id":"vless-tls-ok","name":"VLESS TLS OK","protocol_id":"vless_tcp_tls","port":62301,"max_users":1,"state":"draft","runtime_applied":false},{"id":"vless-tls-fail","name":"VLESS TLS fail","protocol_id":"vless_tcp_tls","port":62302,"max_users":1,"state":"draft","runtime_applied":false}]
JSON
chmod 600 "$BASE/connections.json"
python3 "$ROOT/scripts/certificate_store.py" --base "$CERTS" --catalog "$CERTS/catalog.json" --managed-dir "$CERTS/managed" --secrets-dir "$CERTS/secrets" --master-key "$KEYS/master.key" --lock "$CERTS/catalog.lock" import --storage-type managed --certificate-file "$TMP/tls.pem" --private-key-file "$TMP/tls.key" --certificate-id cert-assistant >/dev/null
export PATH="$TMP/mockbin:$PATH"
export APP_ROOT="$ROOT"
export CONNECTION_DATA_FILE="$BASE/connections.json"
export CONNECTION_DATA_DIR="$BASE"
export XRAY_MANAGER_CONNECTIONS_DIR="$BASE"
export XRAY_MANAGER_SECRETS_DIR="$SECRETS"
export XRAY_MANAGER_MASTER_KEY_FILE="$KEYS/master.key"
export XRAY_MANAGER_CERTIFICATES_DIR="$CERTS"
export XRAY_MANAGER_CERTIFICATES_CATALOG_FILE="$CERTS/catalog.json"
export XRAY_MANAGER_CERTIFICATES_MANAGED_DIR="$CERTS/managed"
export XRAY_MANAGER_CERTIFICATES_SECRETS_DIR="$CERTS/secrets"
export XRAY_MANAGER_CERTIFICATES_LOCK="$CERTS/catalog.lock"
export XRAY_MANAGER_CERTIFICATES_RUNTIME_DIR="$RUNTIME"
export XRAY_MANAGER_INTEGRITY_LOCK="$RUN/integrity.lock"
export CONNECTION_LOCK="$XRAY_MANAGER_INTEGRITY_LOCK"
export XRAY_VALIDATION_BINARY="$TMP/xray"
export XRAY_TEST_CALLS="$TMP/xray.calls"
source "$ROOT/modules/vless_model.sh"
source "$ROOT/modules/vless_xray_26_10_31.sh"
source "$ROOT/modules/vless_assistant.sh"
ui_pause() { :; }
printf '127.0.0.1\ncert-assistant\ns\n' | connections_vless_assistant vless-tls-ok vless_tcp_tls
jq -e 'any(.[]; .id == "vless-tls-ok" and .configuration_revision == 1 and .secret_ref == null)' "$CONNECTION_DATA_FILE" >/dev/null
jq -e '.security_options == {certificate_id:"cert-assistant"}' "$BASE/configurations/vless-tls-ok.r000001.json" >/dev/null
[[ ! -e "$SECRETS/vless-tls-ok.r000001.bin" ]]
[[ -d "$RUNTIME" && -z "$(find "$RUNTIME" -mindepth 1 -maxdepth 1 -print -quit)" ]]
[[ "$(wc -l <"$XRAY_TEST_CALLS")" -eq 1 ]]
if printf '127.0.0.1\ncert-assistant\ns\n' | XRAY_FAIL=1 connections_vless_assistant vless-tls-fail vless_tcp_tls; then
	echo 'ERROR: se esperaba el rechazo del Xray simulado.' >&2; exit 1
fi
jq -e 'any(.[]; .id == "vless-tls-fail" and .configuration_revision == 1 and .secret_ref == null)' "$CONNECTION_DATA_FILE" >/dev/null
[[ ! -e "$SECRETS/vless-tls-fail.r000001.bin" ]]
[[ -z "$(find "$RUNTIME" -mindepth 1 -maxdepth 1 -print -quit)" ]]
[[ "$(wc -l <"$XRAY_TEST_CALLS")" -eq 2 ]]
# Recuperación: recorrer todas las modalidades VLESS TLS con sus opciones de transporte.
python3 - "$CONNECTION_DATA_FILE" <<'PYROWS'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]); rows=json.loads(p.read_text())
for i,mode in enumerate(('vless_ws_tls','vless_grpc_tls','vless_xhttp_tls'),start=4):
    rows.append({'id':f'restore-{mode}','name':mode,'protocol_id':mode,'port':62300+i,'max_users':1,'state':'draft','runtime_applied':False})
p.write_text(json.dumps(rows,indent=2)+'\n'); p.chmod(0o600)
PYROWS
store_tls_mode() {
 local id="$1" mode="$2" transport="$3" options="$4" port="$5"
 jq -n --arg id "$id" --arg mode "$mode" --arg transport "$transport" --argjson port "$port" --argjson options "$options" '{schema_version:1,connection_id:$id,protocol:"vless",mode_id:$mode,transport:$transport,security:"tls",listen_address:"127.0.0.1",listen_port:$port,transport_options:$options,security_options:{certificate_id:"cert-assistant"}}' >"$TMP/$id.json"
 chmod 600 "$TMP/$id.json"
 python3 "$ROOT/scripts/vless_config_store.py" store --connection-id "$id" --input "$TMP/$id.json" --base "$BASE" --catalog "$CONNECTION_DATA_FILE" --lock "$CONNECTION_LOCK" --secrets-dir "$SECRETS" --master-key "$KEYS/master.key" --certificate-catalog "$CERTS/catalog.json" >/dev/null
}
store_tls_mode restore-vless_ws_tls vless_ws_tls websocket '{"path":"/ws-restore"}' 62304
store_tls_mode restore-vless_grpc_tls vless_grpc_tls grpc '{"service_name":"grpc-restore"}' 62305
store_tls_mode restore-vless_xhttp_tls vless_xhttp_tls xhttp '{"path":"/xhttp-restore","mode":"auto"}' 62306
for mode in vless_tcp_tls vless_ws_tls vless_grpc_tls vless_xhttp_tls; do
 id="restore-$mode"; [[ "$mode" == vless_tcp_tls ]] && id=vless-tls-ok
 connections_vless_assistant_restore "$id" "$mode"
 [[ -z "$(find "$RUNTIME" -mindepth 1 -maxdepth 1 -print -quit)" ]]
done
[[ "$(wc -l <"$XRAY_TEST_CALLS")" -eq 6 ]]
echo 'PASS: VLESS TLS central prepara y limpia leases en creación y recuperación de RAW/TCP, WS, gRPC y XHTTP; permisos simulados www-data.'
