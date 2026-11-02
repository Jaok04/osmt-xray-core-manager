#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
cat >"$TMP/xray" <<'XRAY'
#!/usr/bin/env bash
[[ "$1" == run && "$2" == -test && "$3" == -config && -s "$4" ]]
printf 'Configuration OK.\n'
XRAY
chmod 700 "$TMP/xray"
cat >"$TMP/connections.json" <<'JSON'
[{"id":"conn-test","name":"Test VLESS","protocol_id":"vless_ws","port":62001,"max_users":2,"state":"draft","runtime_applied":false,"created_at":"2026-11-02T00:00:00Z"}]
JSON
export APP_ROOT="$ROOT"
export CONNECTION_DATA_FILE="$TMP/connections.json"
export XRAY_VALIDATION_BINARY="$TMP/xray"
source "$ROOT/modules/vless_model.sh"
source "$ROOT/modules/vless_xray_26_10_31.sh"
source "$ROOT/modules/vless_assistant.sh"
ui_pause() { :; }
printf '127.0.0.1\n/ws-test\n' | connections_vless_assistant conn-test vless_ws
jq -e 'length == 1 and .[0].state == "draft" and .[0].runtime_applied == false and .[0].protocol_id == "vless_ws"' "$CONNECTION_DATA_FILE" >/dev/null
if printf '127.0.0.1\ninvalid-path\n' | connections_vless_assistant conn-test vless_ws >/dev/null 2>&1; then
  echo 'ERROR: se aceptó una ruta WS inválida.' >&2
  exit 1
fi
jq -e '.[0].state == "draft" and .[0].runtime_applied == false' "$CONNECTION_DATA_FILE" >/dev/null
echo 'OK: asistente VLESS construye/valida temporalmente, rechaza opciones inválidas y conserva el borrador sin activar runtime.'
