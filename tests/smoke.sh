#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ENTRY="$ROOT/bin/xray-manager"
OUT="$(mktemp)"
TMPDIR_TEST="$(mktemp -d)"
trap 'rm -f "$OUT"; rm -rf "$TMPDIR_TEST"' EXIT
bash -n "$ENTRY" "$ROOT/lib/ui.sh" "$ROOT/lib/system.sh" "$ROOT/modules/connections.sh" "$ROOT/modules/vless_model.sh" "$ROOT/modules/vless_xray_26_10_31.sh" "$ROOT/modules/users.sh" "$ROOT/modules/users_v2.sh" "$ROOT/modules/users_v2_menu.sh" "$ROOT/modules/main_menu.sh" "$ROOT/tests/users.sh" "$ROOT/tests/users_v2.sh" "$ROOT/tests/users_v2_menu.sh"
printf '0\ns\n' | "$ENTRY" >"$OUT"
grep -q 'MENÚ PRINCIPAL' "$OUT"
grep -q 'Cerrando Xray Core Manager' "$OUT"
printf '9\n\n0\ns\n' | "$ENTRY" >"$OUT"
grep -q 'INFORMACIÓN Y AYUDA' "$OUT"
grep -q '0.2.0-dev' "$OUT"

# El modelo neutral resuelve exactamente las nueve modalidades VLESS.
source "$ROOT/modules/vless_model.sh"
while IFS='|' read -r mode expected_transport expected_security; do
	MODEL="$(vless_model_build 'conn-test-01' "$mode" '127.0.0.1' '443')"
	jq -e --arg mode "$mode" --arg transport "$expected_transport" --arg security "$expected_security" '
        .schema_version == "1" and .connection_id == "conn-test-01" and
        .protocol == "vless" and .mode_id == $mode and
        .transport == $transport and .security == $security and
        .listen_address == "127.0.0.1" and .listen_port == 443 and
        .transport_options == {} and .security_options == {} and .users == [] and
        (has("flow") | not)
    ' <<<"$MODEL" >/dev/null
done <<'MODES'
vless_ws|websocket|none
vless_tcp_tls|raw|tls
vless_ws_tls|websocket|tls
vless_reality|raw|reality
vless_grpc_tls|grpc|tls
vless_grpc_reality|grpc|reality
vless_xhttp|xhttp|none
vless_xhttp_tls|xhttp|tls
vless_xhttp_reality|xhttp|reality
MODES
for invalid_mode in vless_httpupgrade vless_ws_reality vmess_ws ''; do
	if vless_model_build conn-test "$invalid_mode" 127.0.0.1 443 >/dev/null 2>&1; then
		echo "ERROR: se aceptó modalidad VLESS inválida: $invalid_mode" >&2
		exit 1
	fi
done
for invalid_port in 0 65536 abc ''; do
	if vless_model_build conn-test vless_ws 127.0.0.1 "$invalid_port" >/dev/null 2>&1; then
		echo "ERROR: se aceptó puerto inválido: $invalid_port" >&2
		exit 1
	fi
done
for invalid_address in '' '127.0.0.1 0.0.0.0'; do
	if vless_model_build conn-test vless_ws "$invalid_address" 443 >/dev/null 2>&1; then
		echo "ERROR: se aceptó dirección de escucha inválida." >&2
		exit 1
	fi
done
if vless_model_build '' vless_ws 127.0.0.1 443 >/dev/null 2>&1; then
	echo "ERROR: se aceptó ID de conexión vacío." >&2
	exit 1
fi
if vless_model_build conn-test vless_ws 127.0.0.1 >/dev/null 2>&1; then
	echo "ERROR: se aceptó una llamada con argumentos incompletos." >&2
	exit 1
fi
printf '1\n1\n1\n0\n0\n0\n0\ns\n' | "$ENTRY" >"$OUT"
grep -q 'GESTIÓN DE PROTOCOLOS Y CONEXIONES' "$OUT"
grep -q 'ADMINISTRAR VLESS' "$OUT"
grep -q 'VLESS-WS (Sin TLS)' "$OUT"
source "$ROOT/config/manager.conf"
source "$ROOT/lib/ui.sh"
source "$ROOT/modules/connections.sh"
connections_show_catalog >"$OUT"
grep -q 'CATÁLOGO DE PROTOCOLOS' "$OUT"
grep -q 'vless_ws' "$OUT"
printf 'opcion-invalida\n\n0\ns\n' | "$ENTRY" >"$OUT"
grep -q 'Opción no válida' "$OUT"

printf '  Demo de prueba  \nvless_ws\n51001\n25\n\n' | bash -c '
    set -Eeuo pipefail
    APP_ROOT="$1"
    source "$APP_ROOT/config/manager.conf"
    source "$APP_ROOT/lib/ui.sh"
    source "$APP_ROOT/modules/connections.sh"
    CONNECTION_DATA_DIR="$2/data"
    CONNECTION_DATA_FILE="$CONNECTION_DATA_DIR/connections.json"
    CONNECTION_LOCK="$2/run/connections.lock"
    connections_create_draft
' _ "$ROOT" "$TMPDIR_TEST" >"$OUT"
DATA="$TMPDIR_TEST/data/connections.json"
jq -e 'length == 1 and .[0].name == "Demo de prueba" and .[0].protocol_id == "vless_ws" and .[0].port == 51001 and .[0].max_users == 25 and .[0].state == "draft" and .[0].runtime_applied == false' "$DATA" >/dev/null
[[ "$(stat -c '%a' "$DATA")" == "600" ]]
ID="$(jq -r '.[0].id' "$DATA")"

printf '%s\nNueva etiqueta\n\n51002\n40\n\n' "$ID" | bash -c '
    set -Eeuo pipefail
    APP_ROOT="$1"
    source "$APP_ROOT/config/manager.conf"
    source "$APP_ROOT/lib/ui.sh"
    source "$APP_ROOT/modules/connections.sh"
    CONNECTION_DATA_DIR="$2/data"
    CONNECTION_DATA_FILE="$CONNECTION_DATA_DIR/connections.json"
    CONNECTION_LOCK="$2/run/connections.lock"
    connections_edit_draft
' _ "$ROOT" "$TMPDIR_TEST" >"$OUT"
jq -e --arg id "$ID" 'length == 1 and .[0].id == $id and .[0].name == "Nueva etiqueta" and .[0].port == 51002 and .[0].max_users == 40' "$DATA" >/dev/null

jq '.[0].state = "active"' "$DATA" >"$DATA.tmp"
chmod 600 "$DATA.tmp"
mv "$DATA.tmp" "$DATA"
printf '%s\nNombre no permitido\n\n\n\n' "$ID" | bash -c '
    set -Eeuo pipefail
    APP_ROOT="$1"
    source "$APP_ROOT/config/manager.conf"
    source "$APP_ROOT/lib/ui.sh"
    source "$APP_ROOT/modules/connections.sh"
    CONNECTION_DATA_DIR="$2/data"
    CONNECTION_DATA_FILE="$CONNECTION_DATA_DIR/connections.json"
    CONNECTION_LOCK="$2/run/connections.lock"
    connections_edit_draft
' _ "$ROOT" "$TMPDIR_TEST" >"$OUT" || true
grep -q 'estado draft' "$OUT"
jq -e --arg id "$ID" 'length == 1 and .[0].id == $id and .[0].state == "active" and .[0].name == "Nueva etiqueta"' "$DATA" >/dev/null

printf '%s\nELIMINAR\n\n' "$ID" | bash -c '
    set -Eeuo pipefail
    APP_ROOT="$1"
    source "$APP_ROOT/config/manager.conf"
    source "$APP_ROOT/lib/ui.sh"
    source "$APP_ROOT/modules/connections.sh"
    CONNECTION_DATA_DIR="$2/data"
    CONNECTION_DATA_FILE="$CONNECTION_DATA_DIR/connections.json"
    CONNECTION_LOCK="$2/run/connections.lock"
    connections_delete_draft
' _ "$ROOT" "$TMPDIR_TEST" >"$OUT" || true
grep -q 'estado draft' "$OUT"
jq -e --arg id "$ID" 'length == 1 and .[0].id == $id' "$DATA" >/dev/null

jq '.[0].state = "draft"' "$DATA" >"$DATA.tmp"
chmod 600 "$DATA.tmp"
mv "$DATA.tmp" "$DATA"
printf '%s\nNO\n\n' "$ID" | bash -c '
    set -Eeuo pipefail
    APP_ROOT="$1"
    source "$APP_ROOT/config/manager.conf"
    source "$APP_ROOT/lib/ui.sh"
    source "$APP_ROOT/modules/connections.sh"
    CONNECTION_DATA_DIR="$2/data"
    CONNECTION_DATA_FILE="$CONNECTION_DATA_DIR/connections.json"
    CONNECTION_LOCK="$2/run/connections.lock"
    connections_delete_draft
' _ "$ROOT" "$TMPDIR_TEST" >"$OUT"
jq -e 'length == 1' "$DATA" >/dev/null

printf '%s\nELIMINAR\n\n' "$ID" | bash -c '
    set -Eeuo pipefail
    APP_ROOT="$1"
    source "$APP_ROOT/config/manager.conf"
    source "$APP_ROOT/lib/ui.sh"
    source "$APP_ROOT/modules/connections.sh"
    CONNECTION_DATA_DIR="$2/data"
    CONNECTION_DATA_FILE="$CONNECTION_DATA_DIR/connections.json"
    CONNECTION_LOCK="$2/run/connections.lock"
    connections_delete_draft
' _ "$ROOT" "$TMPDIR_TEST" >"$OUT"
jq -e 'length == 0' "$DATA" >/dev/null
# Dos altas concurrentes deben conservar ambos registros gracias a flock.
create_parallel() {
	local label="$1" port="$2"
	printf '%s\nvless_ws\n%s\n5\n\n' "$label" "$port" | bash -c '
        set -Eeuo pipefail
        APP_ROOT="$1"
        source "$APP_ROOT/config/manager.conf"
        source "$APP_ROOT/lib/ui.sh"
        source "$APP_ROOT/modules/connections.sh"
        CONNECTION_DATA_DIR="$2/data"
        CONNECTION_DATA_FILE="$CONNECTION_DATA_DIR/connections.json"
        CONNECTION_LOCK="$2/run/connections.lock"
        connections_create_draft
    ' _ "$ROOT" "$TMPDIR_TEST" >"$TMPDIR_TEST/$label.log"
}
create_parallel Parallel-A 51011 &
PID_A=$!
create_parallel Parallel-B 51012 &
PID_B=$!
wait "$PID_A"
wait "$PID_B"
jq -e 'length == 2 and ([.[].port] | sort) == [51011,51012]' "$DATA" >/dev/null

printf '%s\n' '{invalid json' >"$TMPDIR_TEST/data/connections.json"
if bash -c '
    set -Eeuo pipefail
    APP_ROOT="$1"
    source "$APP_ROOT/config/manager.conf"
    source "$APP_ROOT/modules/connections.sh"
    CONNECTION_DATA_DIR="$2/data"
    CONNECTION_DATA_FILE="$CONNECTION_DATA_DIR/connections.json"
    CONNECTION_LOCK="$2/run/connections.lock"
    connections_lock lock_fd
' _ "$ROOT" "$TMPDIR_TEST" >/dev/null 2>&1; then
	echo "ERROR: se aceptó un JSON corrupto." >&2
	exit 1
fi
grep -q 'invalid json' "$TMPDIR_TEST/data/connections.json"
printf '%s\n' "OK: menú, catálogo, alta, edición, protección de estados, cancelación/eliminación, JSON corrupto, permisos y modelo VLESS (nueve modalidades y validaciones negativas)."

# Pruebas aisladas del módulo de usuarios VLESS.
bash "$ROOT/tests/users.sh"
bash "$ROOT/tests/users_v2.sh"
bash "$ROOT/tests/users_v2_menu.sh"

bash "$ROOT/tests/xray_admin.sh"
bash "$ROOT/tests/stage2_navigation.sh"
bash "$ROOT/tests/stage2_existing.sh"