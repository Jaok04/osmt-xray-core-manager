#!/usr/bin/env bash
set -euo pipefail
# shellcheck disable=SC2034
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_ROOT="$ROOT"
export APP_ROOT
source "$ROOT/lib/ui.sh"
source "$ROOT/modules/connections.sh"
ui_clear() { :; }
ui_title() { printf '%s\n' "$1"; }
ui_pause() { :; }
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
CONNECTION_DATA_DIR="$TMP/data"
CONNECTION_DATA_FILE="$CONNECTION_DATA_DIR/connections.json"
# shellcheck disable=SC2034
CONNECTION_LOCK="$TMP/run/connections.lock"
USER_DATA_FILE="$TMP/users.json"
mkdir -p "$CONNECTION_DATA_DIR" "$TMP/run"
printf '%s\n' '[]' >"$USER_DATA_FILE"
cat >"$CONNECTION_DATA_FILE" <<'JSON'
[{"id":"conn-1","name":"Original","protocol_id":"vless_ws","port":51001,"max_users":5,"state":"draft","runtime_applied":false,"created_at":"2026-11-02T00:00:00Z"}]
JSON
printf '1\n1\n0\n0\n' | connections_manage_existing vless_ws >"$TMP/detail.out"
grep -q 'Nombre: Original' "$TMP/detail.out"
printf '1\n2\nRenamed\n\n\n\n0\n0\n' | connections_manage_existing vless_ws >"$TMP/edit.out"
jq -e 'length == 1 and .[0].name == "Renamed" and .[0].id == "conn-1"' "$CONNECTION_DATA_FILE" >/dev/null
printf 'OK: selección de conexiones, consulta de detalles y edición de borradores desde el menú jerárquico.\n'