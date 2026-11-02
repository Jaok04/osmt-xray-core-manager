#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
APP_ROOT="$ROOT"
export APP_ROOT
source "$ROOT/lib/ui.sh"
source "$ROOT/modules/connections.sh"
ui_clear() { :; }
ui_title() { printf '%s\n' "$1"; }
ui_pause() {
    local pause_input
    IFS= read -r pause_input || true
    : "${pause_input:-}"
}
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
CONNECTION_DATA_DIR="$TMP/data"
CONNECTION_DATA_FILE="$CONNECTION_DATA_DIR/connections.json"
CONNECTION_LOCK="$TMP/run/integrity.lock"
USER_DATA_FILE="$TMP/users.json"
mkdir -p "$CONNECTION_DATA_DIR" "$TMP/run"
printf '%s\n' '[]' >"$CONNECTION_DATA_FILE"
printf '%s\n' '[]' >"$USER_DATA_FILE"
chmod 600 "$CONNECTION_DATA_FILE" "$USER_DATA_FILE"

# VM-38: lista vacía, mensaje informativo y retorno [0] sin modificar catálogo.
printf '\n' | connections_manage_existing vmess_ws >"$TMP/empty.out"
grep -Fq 'No hay configuraciones disponibles para este protocolo o modalidad.' "$TMP/empty.out"
grep -Fq '[0] Volver' "$TMP/empty.out"
jq -e 'length == 0' "$CONNECTION_DATA_FILE" >/dev/null
printf 'PASS VM-38: lista vacía informa, muestra [0] Volver y retorna sin cambios.\n'

# Preparar una única conexión VMess de prueba para navegación y eliminación.
cat >"$CONNECTION_DATA_FILE" <<'JSON'
[{"id":"vmess-edge","name":"VMess Edge","protocol_id":"vmess_ws","port":54123,"max_users":10,"state":"draft","runtime_applied":false,"created_at":"2026-11-02T00:00:00Z"}]
JSON
chmod 600 "$CONNECTION_DATA_FILE"

# VM-39: entrada inválida recuperable en la lista y en el menú de conexión;
# el usuario puede continuar y volver sin alterar el catálogo.
printf 'x\n\n0\n' | connections_manage_existing vmess_ws >"$TMP/list-invalid.out"
grep -Fq 'Selección no válida.' "$TMP/list-invalid.out"
printf 'x\n\n0\n' | connections_existing_menu vmess-edge >"$TMP/menu-invalid.out"
grep -Fq 'Opción no válida.' "$TMP/menu-invalid.out"
jq -e 'length == 1 and .[0].id == "vmess-edge" and .[0].port == 54123' "$CONNECTION_DATA_FILE" >/dev/null
printf 'PASS VM-39: entradas inválidas son recuperables y [0] vuelve sin cambios.\n'

# VM-40: una confirmación incorrecta cancela; sólo la palabra exacta elimina.
printf 'NO\n\n' | connections_delete_draft vmess-edge >"$TMP/delete-cancel.out"
grep -Fq 'Operación cancelada.' "$TMP/delete-cancel.out"
jq -e 'length == 1 and .[0].id == "vmess-edge"' "$CONNECTION_DATA_FILE" >/dev/null
printf 'ELIMINAR\n\n' | connections_delete_draft vmess-edge >"$TMP/delete-confirm.out"
grep -Fq 'Borrador eliminado.' "$TMP/delete-confirm.out"
jq -e 'length == 0' "$CONNECTION_DATA_FILE" >/dev/null
printf 'PASS VM-40: cancelación preserva borrador y confirmación exacta elimina.\n'
