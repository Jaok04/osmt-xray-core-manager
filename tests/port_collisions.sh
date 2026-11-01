#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
SOCKET_PID=""
cleanup() {
	if [[ -n "$SOCKET_PID" ]]; then
		kill "$SOCKET_PID" 2>/dev/null || true
		wait "$SOCKET_PID" 2>/dev/null || true
	fi
	rm -rf "$TMP"
}
trap cleanup EXIT

init_case() {
	local name="$1"
	CASE="$TMP/$name"
	DATA="$CASE/data"
	RUN="$CASE/run"
	mkdir -p "$DATA" "$RUN"
	CONN="$DATA/connections.json"
	LOCK="$RUN/integrity.lock"
	export CASE DATA RUN CONN LOCK
}

run_create() {
	local label="$1" port="$2" override="$3"
	printf '%s\nvless_ws\n%s\n10\n' "$label" "$port" | bash -c '
		set -Eeuo pipefail
		APP_ROOT="$1"
		source "$APP_ROOT/modules/connections.sh"
		ui_clear() { :; }
		ui_title() { :; }
		ui_line() { :; }
		ui_pause() { :; }
		CONNECTION_DATA_DIR="$2"
		CONNECTION_DATA_FILE="$3"
		CONNECTION_LOCK="$4"
		if [[ "$5" == false ]]; then connections_port_in_use() { return 1; }; fi
		connections_create_draft
	' _ "$ROOT" "$DATA" "$CONN" "$LOCK" "$override"
}

run_edit() {
	local id="$1" port="$2"
	printf '%s\n\n\n%s\n\n' "$id" "$port" | bash -c '
		set -Eeuo pipefail
		APP_ROOT="$1"
		source "$APP_ROOT/modules/connections.sh"
		ui_clear() { :; }
		ui_title() { :; }
		ui_line() { :; }
		ui_pause() { :; }
		CONNECTION_DATA_DIR="$2"
		CONNECTION_DATA_FILE="$3"
		CONNECTION_LOCK="$4"
		connections_port_in_use() { return 1; }
		connections_edit_draft
	' _ "$ROOT" "$DATA" "$CONN" "$LOCK"
}

# Dos altas simultáneas al mismo puerto: el lock debe serializar la
# comprobación y el commit; exactamente una puede reservarlo.
init_case concurrent_create
printf '%s\n' '[]' >"$CONN"
chmod 600 "$CONN"
PORT=53171
pids=()
for n in 1 2; do
	run_create "Concurrent-$n" "$PORT" false >"$CASE/create-$n.log" 2>&1 &
	pids+=("$!")
done
success=0
failure=0
for pid in "${pids[@]}"; do if wait "$pid"; then success=$((success + 1)); else failure=$((failure + 1)); fi; done
[[ "$success" == 1 && "$failure" == 1 ]]
jq -e --argjson port "$PORT" 'length == 1 and .[0].port == $port and .[0].state == "draft"' "$CONN" >/dev/null
[[ "$(stat -c '%a' "$CONN")" == 600 ]]

# Dos ediciones concurrentes de borradores distintos tampoco pueden
# terminar asignando el mismo puerto lógico.
init_case concurrent_edit
cat >"$CONN" <<'JSON'
[
 {"id":"conn-a","name":"A","protocol_id":"vless_ws","port":53201,"max_users":10,"state":"draft","runtime_applied":false,"created_at":"2026-11-01T00:00:00Z"},
 {"id":"conn-b","name":"B","protocol_id":"vless_ws","port":53202,"max_users":10,"state":"draft","runtime_applied":false,"created_at":"2026-11-01T00:00:00Z"}
]
JSON
chmod 600 "$CONN"
pids=()
for id in conn-a conn-b; do
	run_edit "$id" 53203 >"$CASE/edit-$id.log" 2>&1 &
	pids+=("$!")
done
success=0
failure=0
for pid in "${pids[@]}"; do if wait "$pid"; then success=$((success + 1)); else failure=$((failure + 1)); fi; done
[[ "$success" == 1 && "$failure" == 1 ]]
jq -e 'length == 2 and ([.[].port] | length == (unique | length)) and ([.[].port] | map(select(. == 53203)) | length == 1)' "$CONN" >/dev/null
[[ "$(stat -c '%a' "$CONN")" == 600 ]]

# Socket TCP real en escucha: la comprobación ss debe impedir el alta.
init_case occupied_socket
printf '%s\n' '[]' >"$CONN"
chmod 600 "$CONN"
python3 -u -c 'import socket,time; s=socket.socket(); s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1); s.bind(("127.0.0.1",0)); s.listen(1); print(s.getsockname()[1],flush=True); time.sleep(30)' >"$CASE/socket.port" 2>"$CASE/socket.err" &
SOCKET_PID=$!
for _ in $(seq 1 200); do
	[[ -s "$CASE/socket.port" ]] && break
	sleep 0.01
done
[[ -s "$CASE/socket.port" ]]
SOCKET_PORT="$(<"$CASE/socket.port")"
if run_create "Occupied" "$SOCKET_PORT" true >"$CASE/socket-create.log" 2>&1; then
	echo 'ERROR: se aceptó un puerto TCP que ya estaba en escucha.' >&2
	exit 1
fi
grep -q 'ocupado por un socket TCP/UDP' "$CASE/socket-create.log"
jq -e 'length == 0' "$CONN" >/dev/null
kill "$SOCKET_PID" 2>/dev/null || true
wait "$SOCKET_PID" 2>/dev/null || true
SOCKET_PID=""

# Socket UDP enlazado: ss también debe detectar y rechazar el puerto.
python3 -u -c 'import socket,time; s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.bind(("127.0.0.1",0)); print(s.getsockname()[1],flush=True); time.sleep(30)' >"$CASE/socket.port" 2>"$CASE/socket.err" &
SOCKET_PID=$!
for _ in $(seq 1 200); do
	[[ -s "$CASE/socket.port" ]] && break
	sleep 0.01
done
[[ -s "$CASE/socket.port" ]]
SOCKET_PORT="$(<"$CASE/socket.port")"
if run_create "Occupied-UDP" "$SOCKET_PORT" true >"$CASE/socket-udp-create.log" 2>&1; then
	echo 'ERROR: se aceptó un puerto UDP ya enlazado.' >&2
	exit 1
fi
grep -q 'ocupado por un socket TCP/UDP' "$CASE/socket-udp-create.log"
jq -e 'length == 0' "$CONN" >/dev/null

printf '%s\n' 'OK: colisiones concurrentes en altas y ediciones; unicidad preservada; sockets TCP y UDP ocupados rechazados.'