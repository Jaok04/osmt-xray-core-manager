#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
APP_ROOT="$ROOT"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
# Mantener los módulos aislados de los registros reales incluso al volver a cargarlos.
export XRAY_MANAGER_CONNECTIONS_DIR="$TMP/data"
export XRAY_MANAGER_CONNECTIONS_FILE="$TMP/data/connections.json"
export XRAY_MANAGER_USERS_DIR="$TMP/data"
export XRAY_MANAGER_USERS_FILE="$TMP/data/users.json"
export XRAY_MANAGER_INTEGRITY_LOCK="$TMP/run/connections.lock"
source "$ROOT/modules/connections.sh"
source "$ROOT/modules/users.sh"
source "$ROOT/modules/vless_model.sh"
ui_clear() { :; }
ui_title() { :; }
ui_pause() { :; }
ui_read_option() { :; }
CONNECTION_DATA_DIR="$TMP/data"
CONNECTION_DATA_FILE="$CONNECTION_DATA_DIR/connections.json"
CONNECTION_LOCK="$TMP/run/connections.lock"
USER_DATA_DIR="$TMP/data"
USER_DATA_FILE="$USER_DATA_DIR/users.json"
USER_LOCK="$CONNECTION_LOCK"
mkdir -p "$CONNECTION_DATA_DIR"
printf '[{"id":"conn-test-1","name":"VLESS test","protocol_id":"vless_ws","port":51001,"max_users":1,"state":"draft","runtime_applied":false}]\n' >"$CONNECTION_DATA_FILE"
chmod 600 "$CONNECTION_DATA_FILE"

# Regresión determinista: la conexión desaparece entre la consulta inicial
# y la adquisición del bloqueo. La segunda consulta (ya bajo lock) debe abortar.
DETAIL_CALLS_FILE="$TMP/detail_calls"
printf '0\n' >"$DETAIL_CALLS_FILE"
users_connection_details() {
	local calls
	calls="$(<"$DETAIL_CALLS_FILE")"
	calls=$((calls + 1))
	printf '%s\n' "$calls" >"$DETAIL_CALLS_FILE"
	if ((calls == 1)); then
		printf 'conn-test-1\tVLESS test\tvless_ws\t51001\t1\n'
		return 0
	fi
	return 1
}
if printf 'conn-test-1\nCarrera\n' | users_create >/dev/null 2>&1; then
	echo 'ERROR: se creó un usuario después de desaparecer la conexión.' >&2
	exit 1
fi
[[ "$(<"$DETAIL_CALLS_FILE")" -eq 2 ]]
jq -e 'length == 0' "$USER_DATA_FILE" >/dev/null
# Restaurar la función real para las pruebas funcionales restantes.
source "$ROOT/modules/users.sh"

printf 'conn-test-1\nCliente Uno\n\n' | users_create >/dev/null
jq -e 'length == 1 and .[0].connection_id == "conn-test-1" and .[0].label == "Cliente Uno" and .[0].state == "draft" and .[0].runtime_applied == false and (.[0].uuid | test("^[0-9a-f-]{36}$"))' "$USER_DATA_FILE" >/dev/null
UUID="$(jq -r '.[0].uuid' "$USER_DATA_FILE")"
[[ "$(stat -c '%a' "$USER_DATA_FILE")" == "600" ]]
# Límite por conexión: el segundo usuario debe rechazarse.
if printf 'conn-test-1\nCliente Dos\n\n' | users_create >/dev/null 2>&1; then
	echo 'ERROR: se superó max_users.' >&2
	exit 1
fi
# La exportación entrega la forma exacta esperada por VLESS clients.
users_export_clients conn-test-1 | jq -e --arg uuid "$UUID" '. == [{id:$uuid,email:"Cliente Uno"}]' >/dev/null
users_build_vless_model conn-test-1 127.0.0.1 | jq -e --arg uuid "$UUID" '.mode_id == "vless_ws" and .listen_port == 51001 and .users == [{id:$uuid,email:"Cliente Uno"}]' >/dev/null
printf '%s\nCliente Renombrado\n\n' "$UUID" | users_edit >/dev/null
jq -e --arg uuid "$UUID" '.[0].uuid == $uuid and .[0].label == "Cliente Renombrado"' "$USER_DATA_FILE" >/dev/null
# Una conexión con usuarios asociados no se puede borrar.
if printf 'conn-test-1\nELIMINAR\n\n' | connections_delete_draft >/dev/null 2>&1; then
	echo 'ERROR: se eliminó una conexión con usuarios.' >&2
	exit 1
fi
jq -e 'length == 1' "$CONNECTION_DATA_FILE" >/dev/null
printf '%s\nELIMINAR\n\n' "$UUID" | users_delete >/dev/null
jq -e 'length == 0' "$USER_DATA_FILE" >/dev/null
echo 'OK: alta UUID, asociación VLESS, límite por conexión, exportación clients, edición, protección de conexión y eliminación.'
