#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

init_case() {
	local name="$1"
	CASE="$TMP/$name"
	DATA="$CASE/data"
	RUN="$CASE/run"
	mkdir -p "$DATA" "$RUN"
	CONN="$DATA/connections.json"
	USER="$DATA/users.json"
	LOCK="$RUN/integrity.lock"
	printf '%s\n' '[{"id":"conn-race","name":"Race VLESS","protocol_id":"vless_ws","port":52101,"max_users":10,"state":"draft","runtime_applied":false,"created_at":"2026-11-01T00:00:00Z"}]' >"$CONN"
	printf '%s\n' '[]' >"$USER"
	chmod 600 "$CONN" "$USER"
	export ROOT DATA CONN USER LOCK CASE
}

# Orden 1: users_create obtiene primero el lock. La segunda consulta de
# conexión se detiene dentro de la sustitución de comando mientras conserva
# el lock; el borrado concurrente debe esperar y luego detectar al usuario.
init_case user_first
printf '0\n' >"$CASE/detail_calls"
(
	APP_ROOT="$ROOT"
	source "$ROOT/modules/connections.sh"
	source "$ROOT/modules/users.sh"
	ui_clear() { :; }
	ui_title() { :; }
	ui_pause() { :; }
	CONNECTION_DATA_DIR="$DATA"
	CONNECTION_DATA_FILE="$CONN"
	CONNECTION_LOCK="$LOCK"
	USER_DATA_DIR="$DATA"
	USER_DATA_FILE="$USER"
	USER_LOCK="$LOCK"
	users_connection_details() {
		local n
		n="$(<"$CASE/detail_calls")"
		n=$((n + 1))
		printf '%s\n' "$n" >"$CASE/detail_calls"
		if ((n == 2)); then
			: >"$CASE/user_holds_lock"
			while [[ ! -e "$CASE/release_user" ]]; do sleep 0.01; done
		fi
		jq -er --arg id "$1" '.[] | select(.id == $id and (.protocol_id|startswith("vless_")) and .state == "draft") | [.id,.name,.protocol_id,(.port|tostring),(.max_users|tostring)] | @tsv' "$CONN"
	}
	printf 'conn-race\nUser wins\n' | users_create
) >"$CASE/user.log" 2>&1 &
USER_PID=$!
for _ in $(seq 1 500); do
	[[ -e "$CASE/user_holds_lock" ]] && break
	sleep 0.01
done
[[ -e "$CASE/user_holds_lock" ]] || {
	echo 'ERROR: users_create no alcanzó la sección protegida.' >&2
	cat "$CASE/user.log" >&2 || true
	printf 'detail_calls=' >&2
	cat "$CASE/detail_calls" >&2 || true
	exit 1
}
(
	APP_ROOT="$ROOT"
	source "$ROOT/modules/connections.sh"
	source "$ROOT/modules/users.sh"
	ui_clear() { :; }
	ui_title() { :; }
	ui_pause() { :; }
	CONNECTION_DATA_DIR="$DATA"
	CONNECTION_DATA_FILE="$CONN"
	CONNECTION_LOCK="$LOCK"
	USER_DATA_FILE="$USER"
	printf 'conn-race\nELIMINAR\n' | connections_delete_draft
) >"$CASE/delete.log" 2>&1 &
DELETE_PID=$!
sleep 0.1
: >"$CASE/release_user"
wait "$USER_PID"
if wait "$DELETE_PID"; then
	echo 'ERROR: se eliminó una conexión después de que users_create guardó un usuario.' >&2
	exit 1
fi
jq -e 'length == 1 and .[0].connection_id == "conn-race" and .[0].label == "User wins"' "$USER" >/dev/null
jq -e 'length == 1 and .[0].id == "conn-race"' "$CONN" >/dev/null

# Orden 2: connections_delete_draft obtiene primero el lock. Se detiene
# después de adquirirlo y antes de confirmar. users_create queda esperando;
# al confirmar el borrado, debe revalidar y abortar sin crear huérfanos.
init_case delete_first
(
	APP_ROOT="$ROOT"
	source "$ROOT/modules/connections.sh"
	source "$ROOT/modules/users.sh"
	ui_clear() { :; }
	ui_title() { :; }
	ui_pause() { :; }
	CONNECTION_DATA_DIR="$DATA"
	CONNECTION_DATA_FILE="$CONN"
	CONNECTION_LOCK="$LOCK"
	USER_DATA_FILE="$USER"
	connections_lock() {
		local -n fd_ref="$1"
		mkdir -p "$CONNECTION_DATA_DIR" "$(dirname "$CONNECTION_LOCK")"
		exec {fd_ref}>"$CONNECTION_LOCK"
		flock -x "$fd_ref"
		: >"$CASE/delete_holds_lock"
		while [[ ! -e "$CASE/release_delete" ]]; do sleep 0.01; done
	}
	printf 'conn-race\nELIMINAR\n' | connections_delete_draft
) >"$CASE/delete.log" 2>&1 &
DELETE_PID=$!
for _ in $(seq 1 500); do
	[[ -e "$CASE/delete_holds_lock" ]] && break
	sleep 0.01
done
[[ -e "$CASE/delete_holds_lock" ]] || {
	echo 'ERROR: connections_delete_draft no alcanzó el lock.' >&2
	exit 1
}
(
	APP_ROOT="$ROOT"
	source "$ROOT/modules/connections.sh"
	source "$ROOT/modules/users.sh"
	ui_clear() { :; }
	ui_title() { :; }
	ui_pause() { :; }
	CONNECTION_DATA_DIR="$DATA"
	CONNECTION_DATA_FILE="$CONN"
	CONNECTION_LOCK="$LOCK"
	USER_DATA_DIR="$DATA"
	USER_DATA_FILE="$USER"
	USER_LOCK="$LOCK"
	printf 'conn-race\nDelete wins\n' | users_create
) >"$CASE/user.log" 2>&1 &
USER_PID=$!
sleep 0.1
: >"$CASE/release_delete"
wait "$DELETE_PID"
if wait "$USER_PID"; then
	echo 'ERROR: users_create guardó un usuario después de eliminarse la conexión.' >&2
	exit 1
fi
jq -e 'length == 0' "$USER" >/dev/null
jq -e 'length == 0' "$CONN" >/dev/null

echo 'OK: carrera real users_create vs connections_delete_draft validada en ambos órdenes; sin usuarios huérfanos ni conexiones indebidamente eliminadas.'