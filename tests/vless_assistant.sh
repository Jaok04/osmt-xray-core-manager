#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
cat >"$TMP/xray" <<'XRAY'
#!/usr/bin/env bash
[[ "$1" == run && "$2" == -test && "$3" == -config && -s "$4" ]]
cp "$4" "$XRAY_CAPTURE_CONFIG"
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
export XRAY_MANAGER_CERTIFICATES_CATALOG_FILE="$TMP/certificates/catalog.json"
export XRAY_MANAGER_CERTIFICATES_DIR="$TMP/certificates"
export XRAY_MANAGER_CERTIFICATES_MANAGED_DIR="$TMP/certificates/managed"
export XRAY_MANAGER_CERTIFICATES_SECRETS_DIR="$TMP/certificates/secrets"
export XRAY_MANAGER_CERTIFICATES_LOCK="$TMP/run/certificate.lock"
export XRAY_MANAGER_CERTIFICATES_RUNTIME_DIR="$TMP/cert-runtime"
export XRAY_MANAGER_INTEGRITY_LOCK="$TMP/run/integrity.lock"
export XRAY_MANAGER_CONNECTIONS_FILE="$TMP/connections/connections.json"
export XRAY_MANAGER_USERS_DIR="$TMP/users"
export XRAY_MANAGER_USERS_FILE="$TMP/users/users.json"
export CONNECTION_LOCK="$XRAY_MANAGER_INTEGRITY_LOCK"
mkdir -m 700 "$TMP/connections" "$TMP/secrets" "$TMP/keys" "$TMP/run" "$TMP/certificates" "$TMP/certificates/managed" "$TMP/certificates/secrets"
cp "$TMP/connections.json" "$TMP/connections/connections.json"
chmod 600 "$TMP/connections/connections.json"
export CONNECTION_DATA_FILE="$TMP/connections/connections.json"
export XRAY_VALIDATION_BINARY="$TMP/xray"
export XRAY_CAPTURE_CONFIG="$TMP/captured-xray.json"
# shellcheck source=modules/vless_model.sh
source "$ROOT/modules/users.sh"
source "$ROOT/modules/users_v2.sh"
source "$ROOT/modules/vless_model.sh"
# shellcheck source=modules/vless_xray_26_10_31.sh
source "$ROOT/modules/vless_xray_26_10_31.sh"
source "$ROOT/modules/vless_assistant.sh"
ui_pause() { :; }
# Sin almacén V2, el asistente falla cerrado y no inicializa datos ni recurre a legacy.
if printf '127.0.0.1\n/ws-test\n' | connections_vless_assistant conn-test vless_ws >/dev/null 2>&1; then
	echo 'ERROR: el asistente aceptó generar sin almacén Usuarios V2.' >&2
	exit 1
fi
[[ ! -e "$XRAY_MANAGER_USERS_FILE" ]]
mkdir -m 700 -p "$XRAY_MANAGER_USERS_DIR"
ID="$(users_identity_create)"
V2_ASSOC_ID="$(users_association_create "$ID" conn-test 'Cliente V2 draft' uuid 11111111-1111-4111-8111-111111111111 active unlimited 0 none 0 0 auto)"
printf '127.0.0.1\n/ws-test\ns\n' | connections_vless_assistant conn-test vless_ws
jq -e --arg assoc "$V2_ASSOC_ID" '.inbounds[0].settings.clients == [{id:"11111111-1111-4111-8111-111111111111",email:("assoc:"+$assoc)}]' "$XRAY_CAPTURE_CONFIG" >/dev/null
jq -e 'length == 1 and .[0].state == "draft" and .[0].runtime_applied == false and .[0].protocol_id == "vless_ws"' "$CONNECTION_DATA_FILE" >/dev/null
[[ ! -e "$XRAY_MANAGER_MASTER_KEY_FILE" ]]
if printf '127.0.0.1\ninvalid-path\n' | connections_vless_assistant conn-test vless_ws >/dev/null 2>&1; then
	echo 'ERROR: se aceptó una ruta WS inválida.' >&2
	exit 1
fi
jq -e '.[0].state == "draft" and .[0].runtime_applied == false and .[0].configuration_revision == 1' "$CONNECTION_DATA_FILE" >/dev/null
# REALITY: la clave privada se cifra, no queda en configuración ni catálogo.
cat >"$CONNECTION_DATA_FILE" <<'JSON'
[{"id":"conn-test","name":"Test VLESS","protocol_id":"vless_ws","port":62001,"max_users":2,"state":"draft","runtime_applied":false,"created_at":"2026-11-02T00:00:00Z"},{"id":"reality-test","name":"Test REALITY","protocol_id":"vless_reality","port":62002,"max_users":2,"state":"draft","runtime_applied":false,"created_at":"2026-11-02T00:00:00Z"}]
JSON
ID_REALITY="$(users_identity_create)"
users_association_create "$ID_REALITY" reality-test 'Cliente REALITY' uuid 22222222-2222-4222-8222-222222222222 active unlimited 0 none 0 0 auto >/dev/null
chmod 600 "$CONNECTION_DATA_FILE"
secret='PRIVATE-REALITY-KEY-TEST-DO-NOT-LEAK'
printf '127.0.0.1\nexample.com:443\n%s\nexample.com\n0123456789abcdef\ns\n' "$secret" | connections_vless_assistant reality-test vless_reality
jq -e 'any(.[]; .id == "reality-test" and .secret_ref == "secrets/reality-test.r000001.bin" and .state == "draft" and .runtime_applied == false)' "$CONNECTION_DATA_FILE" >/dev/null
if grep -R -F "$secret" "$TMP/connections/configurations" "$TMP/secrets" "$CONNECTION_DATA_FILE"; then
	echo 'ERROR: clave REALITY en texto claro dentro del almacén.' >&2
	exit 1
fi
python3 "$ROOT/scripts/vless_config_store.py" read --connection-id reality-test --base "$XRAY_MANAGER_CONNECTIONS_DIR" --catalog "$CONNECTION_DATA_FILE" --lock "$XRAY_MANAGER_INTEGRITY_LOCK" --secrets-dir "$XRAY_MANAGER_SECRETS_DIR" --master-key "$XRAY_MANAGER_MASTER_KEY_FILE" --secret-output "$TMP/recovered.secret" >/dev/null
[[ "$(cat "$TMP/recovered.secret")" == "$secret" ]]
connections_vless_assistant_restore reality-test vless_reality
# TLS: el asistente guarda solo el ID del certificado central, nunca un secreto por conexión.
openssl req -x509 -newkey rsa:2048 -nodes -keyout "$TMP/tls.key" -out "$TMP/certificate.pem" -days 2 -subj '/CN=localhost' >/dev/null 2>&1
chmod 600 "$TMP/tls.key" "$TMP/certificate.pem"
python3 "$ROOT/scripts/certificate_store.py" --base "$TMP/certificates" --catalog "$XRAY_MANAGER_CERTIFICATES_CATALOG_FILE" --managed-dir "$TMP/certificates/managed" --secrets-dir "$TMP/certificates/secrets" --master-key "$XRAY_MANAGER_MASTER_KEY_FILE" --lock "$TMP/run/certificate.lock" import --storage-type managed --certificate-file "$TMP/certificate.pem" --private-key-file "$TMP/tls.key" --certificate-id cert-test >/dev/null
jq '. + [{"id":"tls-test","name":"Test TLS","protocol_id":"vless_tcp_tls","port":62003,"max_users":2,"state":"draft","runtime_applied":false,"created_at":"2026-11-02T00:00:00Z"}]' "$CONNECTION_DATA_FILE" >"$TMP/catalog.next"
mv "$TMP/catalog.next" "$CONNECTION_DATA_FILE"
chmod 600 "$CONNECTION_DATA_FILE"
ID_TLS="$(users_identity_create)"
users_association_create "$ID_TLS" tls-test 'Cliente TLS' uuid 33333333-3333-4333-8333-333333333333 active unlimited 0 none 0 0 auto >/dev/null
if printf '127.0.0.1\n1\ns\n' | connections_vless_assistant tls-test vless_tcp_tls; then
	printf 'INFO: el resolutor pudo validar TLS en este entorno.\n'
else
	printf 'INFO: el asistente falló cerrado al no disponer de identidad real del servicio Xray.\n'
fi
jq -e 'any(.[]; .id == "tls-test" and .secret_ref == null and .state == "draft" and .runtime_applied == false)' "$CONNECTION_DATA_FILE" >/dev/null
jq -e '.security_options == {certificate_id:"cert-test"}' "$TMP/connections/configurations/tls-test.r000001.json" >/dev/null
[[ ! -e "$TMP/secrets/tls-test.r000001.bin" ]]
python3 "$ROOT/scripts/vless_config_store.py" read --connection-id tls-test --base "$XRAY_MANAGER_CONNECTIONS_DIR" --catalog "$CONNECTION_DATA_FILE" --lock "$XRAY_MANAGER_INTEGRITY_LOCK" --secrets-dir "$XRAY_MANAGER_SECRETS_DIR" --master-key "$XRAY_MANAGER_MASTER_KEY_FILE" --certificate-catalog "$XRAY_MANAGER_CERTIFICATES_CATALOG_FILE" >"$TMP/tls-read.json"
jq -e '.configuration.security_options.certificate_id == "cert-test" and .secret_written == false' "$TMP/tls-read.json" >/dev/null
if grep -R -F 'PRIVATE KEY' "$TMP/connections/configurations" "$TMP/secrets" "$CONNECTION_DATA_FILE"; then
	echo 'ERROR: material privado TLS presente en el almacén por conexión.' >&2
	exit 1
fi
if connections_vless_assistant_restore tls-test vless_tcp_tls; then
	printf 'INFO: recuperación TLS central validada.\n'
else
	printf 'INFO: recuperación TLS central falló cerrado sin identidad real de Xray.\n'
fi
python3 "$ROOT/scripts/vless_config_store.py" audit --base "$XRAY_MANAGER_CONNECTIONS_DIR" --catalog "$CONNECTION_DATA_FILE" --lock "$XRAY_MANAGER_INTEGRITY_LOCK" --secrets-dir "$XRAY_MANAGER_SECRETS_DIR" --master-key "$XRAY_MANAGER_MASTER_KEY_FILE" --certificate-catalog "$XRAY_MANAGER_CERTIFICATES_CATALOG_FILE" >"$TMP/audit.json"
jq -e '.broken_references == [] and .orphan_secret_files == [] and .automatic_deletion == false' "$TMP/audit.json" >/dev/null
echo 'OK: asistente VLESS conserva REALITY cifrado, TLS central sin secreto por conexión y fallo cerrado sin identidad Xray.'
