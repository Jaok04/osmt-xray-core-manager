#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export APP_ROOT="$ROOT"
source "$ROOT/config/manager.conf"
source "$ROOT/lib/ui.sh"
source "$ROOT/modules/connections.sh"
CONNECTION_CATALOG="$ROOT/config/protocols.tsv"
CONNECTION_DATA_DIR="$TMP/data"
CONNECTION_DATA_FILE="$CONNECTION_DATA_DIR/connections.json"
CONNECTION_LOCK="$TMP/run/integrity.lock"
mkdir -p "$CONNECTION_DATA_DIR" "$TMP/run"
cat >"$CONNECTION_DATA_FILE" <<'JSON'
[{"id":"existing-vless","name":"Existing VLESS","protocol_id":"vless_ws","port":59000,"max_users":5,"state":"draft","runtime_applied":false,"created_at":"2026-11-02T00:00:00Z"}]
JSON
chmod 600 "$CONNECTION_DATA_FILE"
ui_clear() { :; }
ui_title() { :; }
ui_pause() { :; }

snapshot() { jq -S . "$CONNECTION_DATA_FILE" >"$TMP/snapshot.json"; }

connections_vmess_assistant() { return 3; }
snapshot
printf 'Cancelled VMess\n59001\n5\n' | connections_create_draft vmess_ws >"$TMP/cancel.out"
jq -S . "$CONNECTION_DATA_FILE" >"$TMP/after.json"
cmp "$TMP/snapshot.json" "$TMP/after.json"
grep -F 'se retiró el borrador base' "$TMP/cancel.out" >/dev/null
echo 'PASS: cancelar creación común VMess deja el catálogo sin cambios'

connections_vmess_assistant() { return 1; }
snapshot
printf 'Failed VMess\n59002\n5\n' | connections_create_draft vmess_ws >"$TMP/failure.out"
jq -S . "$CONNECTION_DATA_FILE" >"$TMP/after.json"
cmp "$TMP/snapshot.json" "$TMP/after.json"
echo 'PASS: fallo previo al guardado no deja un draft vacío'

connections_vmess_assistant() {
    local id="$1" next="$TMP/configured.json"
    jq --arg id "$id" 'map(if .id==$id then . + {vmess_configuration_ref:"configurations/test.r000001.json",vmess_configuration_revision:1,vmess_configuration_schema_version:1} else . end)' "$CONNECTION_DATA_FILE" >"$next"
    cat "$next" >"$CONNECTION_DATA_FILE"
    return 1
}
printf 'Persisted VMess\n59003\n5\n' | connections_create_draft vmess_ws >"$TMP/persisted.out"
jq -e 'any(.[]; .protocol_id=="vmess_ws" and .vmess_configuration_ref=="configurations/test.r000001.json")' "$CONNECTION_DATA_FILE" >/dev/null
echo 'PASS: no se elimina un borrador que ya tiene configuración VMess publicada'

if connections_remove_unconfigured_vmess_draft "$(jq -r '.[]|select(.protocol_id=="vmess_ws")|.id' "$CONNECTION_DATA_FILE")"; then
    echo 'ERROR: se permitió retirar un borrador VMess configurado.' >&2
    exit 1
fi
echo 'PASS: la limpieza condicional protege referencias VMess existentes'
