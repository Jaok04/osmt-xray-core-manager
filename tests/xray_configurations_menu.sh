#!/usr/bin/env bash
# shellcheck disable=SC1091
set -Eeuo pipefail
umask 077
ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
[[ "$(id -u)" -eq 0 ]] || { echo "SKIP: requiere root para el almacén temporal" >&2; exit 77; }
command -v jq >/dev/null
command -v python3 >/dev/null

TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT
KEY="$TMP/master.key"
dd if=/dev/urandom of="$KEY" bs=32 count=1 status=none
chmod 600 "$KEY"
chown root:root "$KEY"

export APP_ROOT="$ROOT"
export XRAY_MANAGER_CONFIGURATIONS_DIR="$TMP/store"
export XRAY_MANAGER_CONFIGURATIONS_MASTER_KEY_FILE="$KEY"
source "$ROOT/config/manager.conf"
source "$ROOT/config/paths.sh"
source "$ROOT/lib/ui.sh"
source "$ROOT/modules/profiles.sh"
source "$ROOT/modules/xray_configurations_menu.sh"
source "$ROOT/modules/main_menu.sh"
system_show_header() { :; }

# Crear desde plantilla mínima y comprobar que no activa Xray.
printf 'Menu test A\n2\ns\n\n' | xray_configurations_create_menu >"$TMP/create.out" 2>&1
grep -q '"name": "Menu test A"' "$TMP/create.out"
ID_A="$(xray_configurations_cli list | jq -r '.[0].config_id')"
[[ "$ID_A" =~ ^config-[0-9a-f]{32}$ ]]

# Importar una configuración externa conservando el origen.
printf '{"log":{"loglevel":"warning"},"outbounds":[]}\n' >"$TMP/import.json"
printf '%s\nMenu test B\ns\n\n' "$TMP/import.json" | xray_configurations_import_menu >"$TMP/import.out" 2>&1
grep -q '"imported_as": "draft"' "$TMP/import.out"
ID_B="$(xray_configurations_cli list | jq -r '.[1].config_id')"
[[ "$ID_B" =~ ^config-[0-9a-f]{32}$ ]]

# Editar crea revisión nueva y conserva la revisión anterior.
printf '{"log":{"loglevel":"error"},"outbounds":[]}\n' >"$TMP/edit.json"
printf '1\n%s\ns\n\n' "$TMP/edit.json" | xray_configurations_edit_menu >"$TMP/edit.out" 2>&1
grep -q '"created_revision": "r000002"' "$TMP/edit.out"
[[ "$(xray_configurations_cli revisions --config-id "$ID_A" | jq '.revisions | length')" -eq 2 ]]

# Consultar muestra metadatos; el contenido sólo se muestra tras confirmación.
printf '1\ns\n\n' | xray_configurations_show_menu >"$TMP/show.out" 2>&1
grep -q 'JSON de la revisión' "$TMP/show.out"
grep -q '"loglevel":"error"' "$TMP/show.out"

# Exportación individual y verificación byte a byte.
printf '1\n1\n\n%s\ns\n\n0\n' "$TMP/one.json" | xray_configurations_export_menu >"$TMP/export-one.out" 2>&1
cmp -s "$TMP/edit.json" "$TMP/one.json"
[[ "$(stat -c '%a' "$TMP/one.json")" == 600 ]]

# Exportación múltiple: preview, dos hashes y confirmación.
jq -n --arg a "$ID_A" --arg b "$ID_B" --arg da "$TMP/batch-a.json" --arg db "$TMP/batch-b.json" \
  '{schema_version:1,exports:[
    {config_id:$a,revision:null,destination:$da,overwrite:false},
    {config_id:$b,revision:null,destination:$db,overwrite:false}
  ]}' >"$TMP/manifest.json"
chmod 600 "$TMP/manifest.json"
chown root:root "$TMP/manifest.json"
printf '%s\ns\n\n' "$TMP/manifest.json" | xray_configurations_export_batch_menu >"$TMP/export-batch.out" 2>&1
cmp -s "$TMP/edit.json" "$TMP/batch-a.json"
cmp -s "$TMP/import.json" "$TMP/batch-b.json"
grep -q '"exported": 2' "$TMP/export-batch.out"

# Comparación de dos configuraciones y consulta de revisiones.
printf '1\n2\n\n\n' | xray_configurations_compare_menu >"$TMP/compare.out" 2>&1
grep -q '"secret_values_in_diff": false' "$TMP/compare.out"
printf '1\n\n' | xray_configurations_revisions_menu >"$TMP/revisions.out" 2>&1
grep -q '"revision": "r000002"' "$TMP/revisions.out"

# Eliminación requiere dos confirmaciones y sólo toca el objeto independiente temporal.
printf '1\ns\ns\n\n' | xray_configurations_delete_menu >"$TMP/delete.out" 2>&1
grep -q '"deleted": true' "$TMP/delete.out"
[[ "$(xray_configurations_cli list | jq 'length')" -eq 1 ]]

# Integración del menú normativo: [1] abre el gestor y [0] retorna correctamente.
printf '1\n0\n0\n' | menu_config_profiles_backups >"$TMP/navigation.out" 2>&1
grep -q 'GESTIONAR CONFIGURACIONES DE XRAY' "$TMP/navigation.out"
grep -q 'Validar archivos de configuración' "$TMP/navigation.out"

# Recorrido desde el menú principal hasta el gestor y retorno completo, sin acciones live.
printf '4\n1\n0\n0\n0\ns\n' | menu_main >"$TMP/main-navigation.out" 2>&1
grep -q 'GESTIONAR CONFIGURACIONES DE XRAY' "$TMP/main-navigation.out"
grep -q 'Cerrando Xray Core Manager' "$TMP/main-navigation.out"

echo "PASS: C-04C menú: crear, consultar, editar, importar, exportar individual/lote, comparar, revisiones, eliminar y navegación completa."
