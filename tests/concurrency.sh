#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
DATA="$TMP/data"
RUN="$TMP/run"
mkdir -p "$DATA" "$RUN"
CONNECTION_FILE="$DATA/connections.json"
USER_FILE="$DATA/users.json"
LOCK_FILE="$RUN/integrity.lock"
printf '%s\n' '[{"id":"conn-stress","name":"Stress VLESS","protocol_id":"vless_ws","port":52001,"max_users":32,"state":"draft","runtime_applied":false,"created_at":"2026-11-01T00:00:00Z"}]' >"$CONNECTION_FILE"
printf '%s\n' '[]' >"$USER_FILE"
chmod 600 "$CONNECTION_FILE" "$USER_FILE"

run_user_op() {
	local op="$1" value="$2" extra="${3:-}"
	case "$op" in
	create) printf 'conn-stress\n%s\n' "$value" ;;
	edit) printf '%s\n%s\n' "$value" "$extra" ;;
	delete) printf '%s\nELIMINAR\n' "$value" ;;
	*) return 2 ;;
	esac | bash -c '
		set -Eeuo pipefail
		APP_ROOT="$1"
		source "$APP_ROOT/modules/connections.sh"
		source "$APP_ROOT/modules/users.sh"
		ui_clear() { :; }
		ui_title() { :; }
		ui_pause() { :; }
		CONNECTION_DATA_DIR="$2"
		CONNECTION_DATA_FILE="$3"
		CONNECTION_LOCK="$4"
		USER_DATA_DIR="$2"
		USER_DATA_FILE="$5"
		USER_LOCK="$4"
		case "$6" in
			create) users_create ;;
			edit) users_edit ;;
			delete) users_delete ;;
		esac
	' _ "$ROOT" "$DATA" "$CONNECTION_FILE" "$LOCK_FILE" "$USER_FILE" "$op" >"$TMP/$op-$value.log"
}

pids=()
for i in $(seq -w 1 16); do
	run_user_op create "Concurrent-$i" &
	pids+=("$!")
done
for pid in "${pids[@]}"; do wait "$pid"; done
jq -e 'length == 16 and ([.[].uuid] | length == (unique | length)) and all(.[]; .connection_id == "conn-stress" and .state == "draft" and .runtime_applied == false)' "$USER_FILE" >/dev/null
[[ "$(stat -c '%a' "$USER_FILE")" == 600 ]]

pids=()
while IFS= read -r uuid; do
	run_user_op edit "$uuid" "Edited-${uuid:0:8}" &
	pids+=("$!")
done < <(jq -r '.[].uuid' "$USER_FILE")
for pid in "${pids[@]}"; do wait "$pid"; done
jq -e 'length == 16 and all(.[]; (.label | startswith("Edited-"))) and ([.[].uuid] | length == (unique | length))' "$USER_FILE" >/dev/null

pids=()
while IFS= read -r uuid; do
	run_user_op delete "$uuid" &
	pids+=("$!")
done < <(jq -r '.[].uuid' "$USER_FILE")
for pid in "${pids[@]}"; do wait "$pid"; done
jq -e 'length == 0' "$USER_FILE" >/dev/null

# La conexión solo se elimina cuando ya no quedan usuarios asociados.
printf 'conn-stress\nELIMINAR\n' | bash -c '
	set -Eeuo pipefail
	APP_ROOT="$1"
	source "$APP_ROOT/modules/connections.sh"
	ui_clear() { :; }
	ui_title() { :; }
	ui_pause() { :; }
	CONNECTION_DATA_DIR="$2"
	CONNECTION_DATA_FILE="$3"
	CONNECTION_LOCK="$4"
	USER_DATA_FILE="$5"
	connections_delete_draft
' _ "$ROOT" "$DATA" "$CONNECTION_FILE" "$LOCK_FILE" "$USER_FILE" >/dev/null
jq -e 'length == 0' "$CONNECTION_FILE" >/dev/null

echo 'OK: 16 altas, 16 ediciones y 16 eliminaciones concurrentes; sin pérdidas de registros ni asociaciones residuales.'