#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -m 700 "$TMP/base" "$TMP/keys" "$TMP/run"
cat >"$TMP/catalog.json" <<'JSON'
[
 {"id":"conn-vmess-ws","name":"VMess WS","protocol_id":"vmess_ws","port":62101,"max_users":5,"state":"draft","runtime_applied":false,"created_at":"2026-11-02T00:00:00Z"},
 {"id":"conn-vmess-hu-tls","name":"VMess HTTPUpgrade TLS","protocol_id":"vmess_httpupgrade_tls","port":62102,"max_users":5,"state":"draft","runtime_applied":false,"created_at":"2026-11-02T00:00:00Z"}
]
JSON
chmod 600 "$TMP/catalog.json"
cat >"$TMP/xray" <<'XRAY'
#!/usr/bin/env bash
[[ "$1" == run && "$2" == -test && "$3" == -config && -s "$4" ]]
XRAY
chmod 700 "$TMP/xray"
openssl req -x509 -newkey rsa:2048 -nodes -keyout "$TMP/tls.key" -out "$TMP/tls.crt" -days 1 -subj '/CN=localhost' >/dev/null 2>&1
chmod 600 "$TMP/tls.key"
export APP_ROOT="$ROOT" CONNECTION_DATA_FILE="$TMP/catalog.json"
export XRAY_MANAGER_CONNECTIONS_DIR="$TMP/base" XRAY_MANAGER_VMESS_DIR="$TMP/vmess" XRAY_MANAGER_VMESS_SECRETS_DIR="$TMP/vmess/secrets"
export XRAY_MANAGER_MASTER_KEY_FILE="$TMP/keys/master.key" XRAY_MANAGER_INTEGRITY_LOCK="$TMP/run/integrity.lock"
export CONNECTION_LOCK="$XRAY_MANAGER_INTEGRITY_LOCK" XRAY_VALIDATION_BINARY="$TMP/xray"
source "$ROOT/modules/vmess_model.sh"
source "$ROOT/modules/vmess_xray_26_10_31.sh"
source "$ROOT/modules/vmess_assistant.sh"
ui_pause() { :; }
printf '127.0.0.1\n1\n\nws@example.test\n\n/ws\n\ns\n' | connections_vmess_assistant conn-vmess-ws vmess_ws >/dev/null
jq -e 'any(.[];.id=="conn-vmess-ws" and .vmess_configuration_revision==1 and .state=="draft" and .runtime_applied==false)' "$CONNECTION_DATA_FILE" >/dev/null
[[ ! -e "$XRAY_MANAGER_MASTER_KEY_FILE" ]]
# HTTPUpgrade-TLS: clave privada protegida en el almacén y recuperable.
printf '127.0.0.1\n1\n\nhttpupgrade@example.test\n\n/upgrade\nedge.example.test\n%s\n%s\ns\n' "$TMP/tls.crt" "$TMP/tls.key" | connections_vmess_assistant conn-vmess-hu-tls vmess_httpupgrade_tls >/dev/null
jq -e 'any(.[];.id=="conn-vmess-hu-tls" and .protocol_id=="vmess_httpupgrade_tls" and .vmess_configuration_revision==1 and .vmess_secret_ref=="secrets/conn-vmess-hu-tls.r000001.bin" and .vmess_configuration_ref=="configurations/conn-vmess-hu-tls.r000001.json" and .state=="draft" and .runtime_applied==false)' "$CONNECTION_DATA_FILE" >/dev/null
jq -e 'all(.[] | select(.protocol_id|startswith("vmess_")); has("vmess_configuration_ref") and (has("configuration_ref")|not) and (has("secret_ref")|not))' "$CONNECTION_DATA_FILE" >/dev/null
[[ -d "$TMP/vmess/configurations" && -d "$TMP/vmess/secrets" && "$(stat -c '%a' "$TMP/vmess")" == 700 && "$(stat -c '%a' "$TMP/vmess/configurations")" == 700 && "$(stat -c '%a' "$TMP/vmess/secrets")" == 700 && ! -d "$TMP/base/configurations" && ! -d "$TMP/secrets" ]]
[[ -f "$XRAY_MANAGER_MASTER_KEY_FILE" && "$(stat -c '%a' "$XRAY_MANAGER_MASTER_KEY_FILE")" == 600 ]]
if grep -R -F 'PRIVATE KEY' "$TMP/vmess/configurations" "$CONNECTION_DATA_FILE" "$TMP/vmess/secrets"; then
    echo 'ERROR: secreto VMess expuesto en archivos persistentes.' >&2
    exit 1
fi
python3 "$ROOT/scripts/vmess_config_store.py" read --connection-id conn-vmess-hu-tls --base "$XRAY_MANAGER_VMESS_DIR" --catalog "$CONNECTION_DATA_FILE" --lock "$XRAY_MANAGER_INTEGRITY_LOCK" --secrets-dir "$XRAY_MANAGER_VMESS_SECRETS_DIR" --master-key "$XRAY_MANAGER_MASTER_KEY_FILE" --secret-output "$TMP/recovered.key" >/dev/null
cmp "$TMP/tls.key" "$TMP/recovered.key"
connections_vmess_assistant_restore conn-vmess-hu-tls vmess_httpupgrade_tls >/dev/null
python3 "$ROOT/scripts/vmess_config_store.py" audit --base "$XRAY_MANAGER_VMESS_DIR" --catalog "$CONNECTION_DATA_FILE" --lock "$XRAY_MANAGER_INTEGRITY_LOCK" --secrets-dir "$XRAY_MANAGER_VMESS_SECRETS_DIR" --master-key "$XRAY_MANAGER_MASTER_KEY_FILE" >"$TMP/audit.json"
jq -e '.broken_references==[] and .orphan_files==[] and .orphan_secret_files==[] and .unsafe_entries==[] and .automatic_deletion==false' "$TMP/audit.json" >/dev/null
# Un enlace simbólico no debe pasar inadvertido en la auditoría.
ln -s "$TMP/vmess/configurations/conn-vmess-hu-tls.r000001.json" "$TMP/vmess/configurations/rogue.json"
python3 "$ROOT/scripts/vmess_config_store.py" audit --base "$XRAY_MANAGER_VMESS_DIR" --catalog "$CONNECTION_DATA_FILE" --lock "$XRAY_MANAGER_INTEGRITY_LOCK" --secrets-dir "$XRAY_MANAGER_VMESS_SECRETS_DIR" --master-key "$XRAY_MANAGER_MASTER_KEY_FILE" >"$TMP/audit-symlink.json"
jq -e '.unsafe_entries==["configurations/rogue.json"]' "$TMP/audit-symlink.json" >/dev/null

echo 'OK: VMess usa almacén aislado y referencias propias; protege clave TLS, recupera y audita; HTTPUpgrade-TLS incluido.'