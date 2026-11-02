#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
cat >"$TMP/xray" <<'XRAY'
#!/usr/bin/env bash
[[ "$1" == run && "$2" == -test && "$3" == -config && -s "$4" ]]
printf 'Configuration OK.\n'
XRAY
chmod 700 "$TMP/xray"
cat >"$TMP/connections.json" <<'JSON'
[{"id":"conn-test","name":"Test VLESS","protocol_id":"vless_ws","port":62001,"max_users":2,"state":"draft","runtime_applied":false,"created_at":"2026-11-02T00:00:00Z"}]
JSON
export APP_ROOT="$ROOT"
export CONNECTION_DATA_FILE="$TMP/connections.json"
export XRAY_MANAGER_CONNECTIONS_DIR="$TMP/connections"
export XRAY_MANAGER_SECRETS_DIR="$TMP/secrets"
export XRAY_MANAGER_MASTER_KEY_FILE="$TMP/keys/master.key"
export XRAY_MANAGER_INTEGRITY_LOCK="$TMP/run/integrity.lock"
export CONNECTION_LOCK="$XRAY_MANAGER_INTEGRITY_LOCK"
mkdir -m 700 "$TMP/connections" "$TMP/secrets" "$TMP/keys" "$TMP/run"
cp "$TMP/connections.json" "$TMP/connections/connections.json"
chmod 600 "$TMP/connections/connections.json"
export CONNECTION_DATA_FILE="$TMP/connections/connections.json"
export XRAY_VALIDATION_BINARY="$TMP/xray"
# shellcheck source=modules/vless_model.sh
source "$ROOT/modules/vless_model.sh"
# shellcheck source=modules/vless_xray_26_10_31.sh
source "$ROOT/modules/vless_xray_26_10_31.sh"
source "$ROOT/modules/vless_assistant.sh"
ui_pause() { :; }
printf '127.0.0.1\n/ws-test\ns\n' | connections_vless_assistant conn-test vless_ws
jq -e 'length == 1 and .[0].state == "draft" and .[0].runtime_applied == false and .[0].protocol_id == "vless_ws"' "$CONNECTION_DATA_FILE" >/dev/null
[[ ! -e "$XRAY_MANAGER_MASTER_KEY_FILE" ]]
if printf '127.0.0.1\ninvalid-path\n' | connections_vless_assistant conn-test vless_ws >/dev/null 2>&1; then
	echo 'ERROR: se aceptó una ruta WS inválida.' >&2
	exit 1
fi
jq -e '.[0].state == "draft" and .[0].runtime_applied == false and .[0].configuration_revision == 1' "$CONNECTION_DATA_FILE" >/dev/null
# REALITY: la clave privada se cifra, no queda en configuración ni catálogo.
cat >"$CONNECTION_DATA_FILE" <<'JSON'
[{"id":"reality-test","name":"Test REALITY","protocol_id":"vless_reality","port":62002,"max_users":2,"state":"draft","runtime_applied":false,"created_at":"2026-11-02T00:00:00Z"}]
JSON
chmod 600 "$CONNECTION_DATA_FILE"
secret='PRIVATE-REALITY-KEY-TEST-DO-NOT-LEAK'
printf '127.0.0.1\nexample.com:443\n%s\nexample.com\n0123456789abcdef\ns\n' "$secret" | connections_vless_assistant reality-test vless_reality
jq -e '.[0].secret_ref == "secrets/reality-test.r000001.bin" and .[0].state == "draft" and .[0].runtime_applied == false' "$CONNECTION_DATA_FILE" >/dev/null
if grep -R -F "$secret" "$TMP/connections/configurations" "$TMP/secrets" "$CONNECTION_DATA_FILE"; then
	echo 'ERROR: clave REALITY en texto claro dentro del almacén.' >&2
	exit 1
fi
python3 "$ROOT/scripts/vless_config_store.py" read --connection-id reality-test --base "$XRAY_MANAGER_CONNECTIONS_DIR" --catalog "$CONNECTION_DATA_FILE" --lock "$XRAY_MANAGER_INTEGRITY_LOCK" --secrets-dir "$XRAY_MANAGER_SECRETS_DIR" --master-key "$XRAY_MANAGER_MASTER_KEY_FILE" --secret-output "$TMP/recovered.secret" >/dev/null
[[ "$(cat "$TMP/recovered.secret")" == "$secret" ]]
connections_vless_assistant_restore reality-test vless_reality
# TLS: se conserva la ruta del certificado y el contenido de la clave privada queda cifrado.
cat >"$TMP/certificate.pem" <<'CERT'
-----BEGIN CERTIFICATE-----
TEST-CERTIFICATE
-----END CERTIFICATE-----
CERT
printf '%s\n' 'TLS-PRIVATE-KEY-TEST-DO-NOT-LEAK' >"$TMP/tls.key"
chmod 600 "$TMP/tls.key"
jq '. + [{"id":"tls-test","name":"Test TLS","protocol_id":"vless_tcp_tls","port":62003,"max_users":2,"state":"draft","runtime_applied":false,"created_at":"2026-11-02T00:00:00Z"}]' "$CONNECTION_DATA_FILE" >"$TMP/catalog.next"
mv "$TMP/catalog.next" "$CONNECTION_DATA_FILE"
chmod 600 "$CONNECTION_DATA_FILE"
printf '127.0.0.1\n%s\n%s\ns\n' "$TMP/certificate.pem" "$TMP/tls.key" | connections_vless_assistant tls-test vless_tcp_tls
jq -e 'any(.[]; .id == "tls-test" and .secret_ref == "secrets/tls-test.r000001.bin" and .state == "draft" and .runtime_applied == false)' "$CONNECTION_DATA_FILE" >/dev/null
if grep -R -F 'TLS-PRIVATE-KEY-TEST-DO-NOT-LEAK' "$TMP/connections/configurations" "$TMP/secrets" "$CONNECTION_DATA_FILE"; then
	echo 'ERROR: clave TLS en texto claro dentro del almacén.' >&2
	exit 1
fi
python3 "$ROOT/scripts/vless_config_store.py" read --connection-id tls-test --base "$XRAY_MANAGER_CONNECTIONS_DIR" --catalog "$CONNECTION_DATA_FILE" --lock "$XRAY_MANAGER_INTEGRITY_LOCK" --secrets-dir "$XRAY_MANAGER_SECRETS_DIR" --master-key "$XRAY_MANAGER_MASTER_KEY_FILE" --secret-output "$TMP/tls-recovered.secret" >/dev/null
cmp "$TMP/tls.key" "$TMP/tls-recovered.secret"
connections_vless_assistant_restore tls-test vless_tcp_tls
python3 "$ROOT/scripts/vless_config_store.py" audit --base "$XRAY_MANAGER_CONNECTIONS_DIR" --catalog "$CONNECTION_DATA_FILE" --lock "$XRAY_MANAGER_INTEGRITY_LOCK" --secrets-dir "$XRAY_MANAGER_SECRETS_DIR" --master-key "$XRAY_MANAGER_MASTER_KEY_FILE" >"$TMP/audit.json"
jq -e '.broken_references == [] and .orphan_secret_files == [] and .automatic_deletion == false' "$TMP/audit.json" >/dev/null
echo 'OK: asistente VLESS valida, persiste con cifrado, recupera claves TLS/REALITY y conserva borradores sin activar runtime.'
