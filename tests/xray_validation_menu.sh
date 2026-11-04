#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
[[ "$(id -u)" -eq 0 ]] || { echo 'SKIP: requiere root para almacenes temporales' >&2; exit 77; }
command -v jq >/dev/null
command -v python3 >/dev/null
TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT
export APP_ROOT="$ROOT"
export XRAY_MANAGER_VALIDATION_DIR="$TMP/validation"
export XRAY_MANAGER_CONFIGURATIONS_DIR="$TMP/configurations"
export XRAY_MANAGER_CONFIGURATIONS_MASTER_KEY_FILE="$TMP/synthetic-master.key"
head -c 32 /dev/urandom > "$XRAY_MANAGER_CONFIGURATIONS_MASTER_KEY_FILE"
chmod 600 "$XRAY_MANAGER_CONFIGURATIONS_MASTER_KEY_FILE"
python3 - "$ROOT" "$XRAY_MANAGER_VALIDATION_DIR" <<'PY'
import sys
sys.path.insert(0, sys.argv[1] + '/scripts')
from xray_validation_store import ValidationReportStore
ValidationReportStore(sys.argv[2]).prepare()
PY
source "$ROOT/config/manager.conf"
source "$ROOT/config/paths.sh"
source "$ROOT/lib/ui.sh"
source "$ROOT/modules/profiles.sh"
source "$ROOT/modules/xray_configurations_menu.sh"
source "$ROOT/modules/xray_validation_menu.sh"

# Las opciones no disponibles no consultan archivos ni runtime.
printf '2\n\n3\n\n0\n' | menu_xray_validation >"$TMP/unavailable.out" 2>&1
grep -q 'archivos externos' "$TMP/unavailable.out"
grep -q 'No se consultó ni modificó el runtime' "$TMP/unavailable.out"

# El historial vacío y el último informe global se presentan sin traceback.
printf '4\n1\n\n5\n0\n0\n' | menu_xray_validation >"$TMP/empty.out" 2>&1
grep -q 'No hay informes de validación' "$TMP/empty.out"
grep -q 'Historial: 0 informe(s)' "$TMP/empty.out"

# Cancelar la validación de una revisión guardada no escribe informe ni promueve estado.
xray_configurations_cli create --name 'C05E cancel test' --template minimal >/dev/null
printf '1\n1\nn\n\n0\n' | menu_xray_validation >"$TMP/cancel.out" 2>&1
grep -q 'Operación cancelada; no se creó ningún informe' "$TMP/cancel.out"
[[ "$(xray_validation_history_cli list | jq -r '.total')" == 0 ]]

# CLI JSON de list/latest/show/compare sobre dos informes sintéticos de la misma configuración.
SAVED="$(python3 - "$ROOT" "$XRAY_MANAGER_VALIDATION_DIR" <<'PYREPORTS'
import json, pathlib, sys
sys.path.insert(0, sys.argv[1] + '/scripts')
from xray_validation_store import ValidationReportStore
store = ValidationReportStore(sys.argv[2])
base = {"schema_version": 1, "created_at": "2026-11-04T18:00:00Z",
        "content_sha256": "a"*64, "content_size_bytes": 12, "result": "PASS",
        "checks": [{"name": "json_syntax", "status": "PASS", "errors": [], "warnings": [], "details": {}}],
        "xray": {"version": "Xray test", "binary_sha256": "b"*64}}
a = store.save_report("config-" + "a"*32, "r000001", base)
b = store.save_report("config-" + "a"*32, "r000002", {**base, "created_at": "2026-11-04T19:00:00Z", "content_sha256": "c"*64})
print(json.dumps([a["validation_id"], b["validation_id"]]))
PYREPORTS
)"
FIRST="$(jq -r '.[0]' <<<"$SAVED")"
SECOND="$(jq -r '.[1]' <<<"$SAVED")"
CID="config-$(printf 'a%.0s' {1..32})"
[[ "$(python3 "$ROOT/scripts/xray_validation_history.py" --store "$XRAY_MANAGER_VALIDATION_DIR" list --config-id "$CID" | jq -r '.total')" == 2 ]]
[[ "$(python3 "$ROOT/scripts/xray_validation_history.py" --store "$XRAY_MANAGER_VALIDATION_DIR" latest --config-id "$CID" | jq -r '.revision')" == r000002 ]]
[[ "$(python3 "$ROOT/scripts/xray_validation_history.py" --store "$XRAY_MANAGER_VALIDATION_DIR" show --validation-id "$FIRST" | jq -r '.revision')" == r000001 ]]
[[ "$(python3 "$ROOT/scripts/xray_validation_history.py" --store "$XRAY_MANAGER_VALIDATION_DIR" compare --first "$FIRST" --second "$SECOND" | jq -r '.summary.content_changed')" == true ]]

# Prueba positiva por el menú completo usando Xray real y almacenes/clave sintéticos.
if [[ -x /usr/local/bin/xray ]]; then
  CONFIG_JSON="$(xray_configurations_cli create --name 'C05E positive native test' --template empty)"
  POSITIVE_ID="$(jq -r '.config_id' <<<"$CONFIG_JSON")"
  cat > "$TMP/positive.json" <<'JSON'
{"inbounds":[{"tag":"socks-in","listen":"127.0.0.1","port":10808,"protocol":"socks","settings":{}}],"outbounds":[{"tag":"direct","protocol":"freedom","settings":{}}]}
JSON
  PREVIEW="$(xray_configurations_cli preview-edit --config-id "$POSITIVE_ID" --source "$TMP/positive.json")"
  xray_configurations_cli edit --config-id "$POSITIVE_ID" --source "$TMP/positive.json" \
    --expected-sha256 "$(jq -r '.sha256' <<<"$PREVIEW")" \
    --expected-revision "$(jq -r '.current_revision // "none"' <<<"$PREVIEW")" --confirm >/dev/null
  printf '1\n2\ns\n\n0\n' | menu_xray_validation >"$TMP/positive.out" 2>&1
  grep -q '"result": "PASS"' "$TMP/positive.out"
  grep -q '"promoted": true' "$TMP/positive.out"
  grep -q '"configuration_applied": false' "$TMP/positive.out"
  [[ "$(xray_validation_history_cli list --config-id "$POSITIVE_ID" | jq -r '.total')" == 1 ]]
  [[ "$(xray_configurations_cli show --config-id "$POSITIVE_ID" | jq -r '.validation_status')" == valid ]]
fi

# La CLI read-only rechaza un almacén ausente sin crearlo.
[[ "$(python3 "$ROOT/scripts/xray_validation_history.py" --store "$TMP/missing" list | jq -r '.total')" == 0 ]]
[[ ! -e "$TMP/missing" ]]

# Navegación desde el menú de configuraciones y retorno.
printf '2\n0\n0\n' | menu_config_profiles_backups >"$TMP/navigation.out" 2>&1
grep -q 'VALIDACIÓN DE CONFIGURACIONES XRAY' "$TMP/navigation.out"

echo 'PASS: C-05E menú, cancelación, CLI read-only, historial/detalle/comparación y validación positiva con Xray real cuando está disponible.'
