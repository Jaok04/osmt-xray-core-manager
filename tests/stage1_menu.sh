#!/usr/bin/env bash
# shellcheck disable=SC2218,SC2120
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
source "$ROOT/config/manager.conf"
source "$ROOT/config/preferences.sh"
source "$ROOT/config/paths.sh"
source "$ROOT/config/xray-version.conf"
source "$ROOT/lib/ui.sh"
source "$ROOT/lib/system.sh"
source "$ROOT/modules/xray_admin.sh"
source "$ROOT/modules/uninstall.sh"
source "$ROOT/modules/system_admin.sh"
source "$ROOT/modules/admin_settings.sh"
source "$ROOT/modules/connections.sh"
source "$ROOT/modules/users.sh"
source "$ROOT/modules/users_v2_menu.sh"
source "$ROOT/modules/xray_service.sh"
source "$ROOT/modules/main_menu.sh"

tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
CALLS="$tmp/calls"

xray_admin_install_menu_action() { printf 'install-action:%s\n' "$1" >>"$CALLS"; }
xray_admin_latest_release() { printf '26.10.31\n'; }
xray_admin_compatible_versions() { printf '26.10.31\n'; }
system_xray_version() { printf 'Xray 26.10.31 (test)\n'; }
uninstall_menu_action() {
    local target=default
    [[ "$#" -gt 0 ]] && target="$1"
    printf 'uninstall-action:%s\n' "$target" >>"$CALLS"
}

printf '1\n2\n3\n\n4\n\n5\n6\n0\n' | menu_xray_admin >"$tmp/xray-menu.out"
grep -Fxq 'install-action:install' "$CALLS"
grep -Fxq 'install-action:update' "$CALLS"
grep -Fxq 'install-action:reinstall' "$CALLS"
grep -Fxq 'install-action:repair' "$CALLS"
if grep -q '^uninstall-action:' "$CALLS"; then
    printf 'ERROR: se encontró una opción de desinstalación duplicada.\\n' >&2
    exit 1
fi
grep -q '\[5\] Reinstalar Xray-core' "$tmp/xray-menu.out"
grep -q '\[6\] Reparar instalación' "$tmp/xray-menu.out"
if grep -q 'Desinstalar Xray-core' "$tmp/xray-menu.out"; then
    printf 'ERROR: el menú Xray contiene una opción de desinstalación duplicada.\\n' >&2
    exit 1
fi
grep -q 'Última versión estable publicada: 26.10.31' "$tmp/xray-menu.out"
grep -q 'Compatibilidad local: disponible' "$tmp/xray-menu.out"

printf '1\n\n2\n\n3\n\n0\n' | menu_installation_information >"$tmp/install-info.out"
grep -q 'RUTAS DE INSTALACIÓN' "$tmp/install-info.out"
grep -q 'ARCHIVOS Y DIRECTORIOS' "$tmp/install-info.out"
grep -q 'INFORMACIÓN DE SYSTEMD' "$tmp/install-info.out"
grep -q 'Esta pantalla es de solo lectura' "$tmp/install-info.out"

# Menú principal: grupos aprobados, opciones y confirmación de salida.
system_show_header() { :; }
printf '0\ns\n' | menu_main >"$tmp/main-menu.out"
for label in 'ADMINISTRACIÓN' 'CONFIGURACIÓN' 'SISTEMA' 'INFORMACIÓN' \
    'Gestión de protocolos y conexiones' 'Gestión de usuarios' \
    'Certificados SSL/TLS y dominios' 'Configuraciones, perfiles y respaldos' \
    'Gestión del servicio Xray-core' 'Diagnóstico y registros' \
    'Seguridad, red y mantenimiento' 'Configuración del sistema y administrador' \
    'Información y ayuda' 'Salir'; do
    grep -Fq "$label" "$tmp/main-menu.out"
done
grep -Fq '¿Deseas salir de Xray Core Manager?' "$tmp/main-menu.out"

# El submenú de sistema expone y enruta las cuatro áreas de Etapa 1.
menu_xray_admin() {
    printf 'xray-admin\n' >>"$CALLS"
    return 1
}
manager_dependencies_menu() {
    printf 'dependencies\n' >>"$CALLS"
    return 1
}
manager_settings_menu() {
    printf 'settings\n' >>"$CALLS"
    return 1
}
menu_installation_information() {
    printf 'information\n' >>"$CALLS"
    return 1
}
uninstall_menu_action() {
    printf 'uninstall:%s\n' "${1:-default}" >>"$CALLS"
    return 1
}
printf '1\n2\n3\n4\n5\n0\n' | menu_system_admin >/dev/null
grep -Fxq 'xray-admin' "$CALLS"
grep -Fxq 'dependencies' "$CALLS"
grep -Fxq 'settings' "$CALLS"
grep -Fxq 'information' "$CALLS"
grep -Fxq 'uninstall:default' "$CALLS"

# La ayuda muestra versiones, rutas y documentación local/oficial.
ui_pause() { :; }
menu_information >"$tmp/help.out"
grep -q 'Versión del gestor' "$tmp/help.out"
grep -q 'Binario Xray' "$tmp/help.out"
grep -q 'Documentación local' "$tmp/help.out"
grep -q 'https://xtls.github.io/' "$tmp/help.out"

# Al regresar desde un submenú, el encabezado debe consultarse de nuevo.
HEADER_CALLS="$tmp/header-calls"
system_show_header() { printf 'header\n' >>"$HEADER_CALLS"; }
ui_confirm() { return 0; }
printf '8\n0\n0\n' | menu_main >"$tmp/header-refresh.out"
[[ "$(wc -l <"$HEADER_CALLS")" -eq 2 ]]

printf 'OK: navegación, recuperación de errores, retorno al menú principal y refresco del encabezado.\n'

# Regresos desde todas las entradas principales y refresco del encabezado.
TOP_LEVEL_CALLS="$tmp/top-level-calls"
HEADER_CALLS="$tmp/all-header-calls"
system_show_header() { printf 'header\n' >>"$HEADER_CALLS"; }
connections_menu() {
    echo connections >>"$TOP_LEVEL_CALLS"
    return 1
}
users_menu_dispatch() {
    echo users >>"$TOP_LEVEL_CALLS"
    return 1
}
menu_placeholder() {
    echo placeholder >>"$TOP_LEVEL_CALLS"
    return 1
}
menu_xray_service() {
    echo xray-service >>"$TOP_LEVEL_CALLS"
    return 1
}
menu_system_admin() {
    echo system-admin >>"$TOP_LEVEL_CALLS"
    return 1
}
menu_information() {
    echo information >>"$TOP_LEVEL_CALLS"
    return 1
}
ui_confirm() { return 0; }
printf '1\n2\n3\n4\n5\n6\n7\n8\n9\n0\n' | menu_main >"$tmp/all-main-returns.out"
[[ "$(wc -l <"$TOP_LEVEL_CALLS")" -eq 9 ]]
[[ "$(wc -l <"$HEADER_CALLS")" -eq 10 ]]

# Restaurar implementaciones reales después de los stubs del bloque de enrutamiento.
source "$ROOT/modules/connections.sh"
source "$ROOT/modules/users.sh"
source "$ROOT/modules/users_v2_menu.sh"

source "$ROOT/modules/system_admin.sh"
source "$ROOT/modules/admin_settings.sh"
source "$ROOT/modules/main_menu.sh"

# Matriz de retorno [0] en submenús funcionales de Etapa 1.
# Se ejecutan solo rutas de navegación; no se invocan operaciones del sistema.
ui_pause() { :; }
system_xray_service_state() { printf 'inactive'; }
system_xray_autostart() { printf 'disabled'; }
printf '0\n' | connections_menu >"$tmp/connections-back.out"
printf '0\n' | users_menu >"$tmp/users-back.out"
printf '0\n' | users_v2_menu >"$tmp/users-v2-back.out"
printf '0\n' | manager_dependencies_menu >"$tmp/dependencies-back.out"
printf '0\n' | manager_settings_menu >"$tmp/settings-back.out"
printf '0\n' | manager_settings_language_date_menu >"$tmp/settings-language-back.out"
printf '0\n' | manager_settings_backup_menu >"$tmp/settings-backup-back.out"
printf '0\n' | manager_settings_theme_menu >"$tmp/settings-theme-back.out"
printf '0\n' | manager_settings_editor_menu >"$tmp/settings-editor-back.out"
printf '0\n' | menu_xray_service >"$tmp/xray-service-back.out"
printf '0\n' | menu_xray_admin >"$tmp/xray-admin-back.out"
for output in connections-back users-back users-v2-back dependencies-back settings-back \
    settings-language-back settings-backup-back settings-theme-back settings-editor-back \
    xray-service-back xray-admin-back; do
    [[ -f "$tmp/$output.out" ]]
done
grep -q '\[0\] Volver' "$tmp/connections-back.out"
grep -q '\[0\] Volver' "$tmp/users-back.out"
grep -q '\[0\] Volver al menú principal' "$tmp/users-v2-back.out"
grep -q '\[0\] Volver' "$tmp/dependencies-back.out"
grep -q '\[0\] Volver' "$tmp/settings-back.out"
grep -q '\[0\] Volver' "$tmp/settings-language-back.out"
grep -q '\[0\] Volver' "$tmp/settings-backup-back.out"
grep -q '\[0\] Volver' "$tmp/settings-theme-back.out"
grep -q '\[0\] Volver' "$tmp/xray-service-back.out"
grep -q '\[0\] Volver' "$tmp/xray-admin-back.out"

# Fallos inyectados en acciones de submenús: el bucle debe seguir disponible
# y aceptar [0] sin cerrar el gestor ni repetir la operación fallida.
ACTION_CALLS="$tmp/nested-action-calls"
connections_create_draft() {
    echo connection-create >>"$ACTION_CALLS"
    return 1
}
printf '2\n0\n' | connections_menu >"$tmp/connections-action-error.out" || true
grep -Fxq connection-create "$ACTION_CALLS"
[[ "$(grep -c 'GESTIÓN DE PROTOCOLOS Y CONEXIONES' "$tmp/connections-action-error.out")" -ge 2 ]]

users_create() {
    echo user-create >>"$ACTION_CALLS"
    return 1
}
printf '1\n0\n' | users_menu >"$tmp/users-action-error.out" || true
grep -Fxq user-create "$ACTION_CALLS"
[[ "$(grep -c 'GESTIÓN DE USUARIOS VLESS' "$tmp/users-action-error.out")" -ge 2 ]]

users_v2_menu_list() {
    echo users-v2-list >>"$ACTION_CALLS"
    return 1
}
printf '1\n0\n' | users_v2_menu >"$tmp/users-v2-action-error.out" || true
grep -Fxq users-v2-list "$ACTION_CALLS"
[[ "$(grep -c 'GESTIÓN DE IDENTIDADES Y ASOCIACIONES (V2)' "$tmp/users-v2-action-error.out")" -ge 2 ]]

manager_settings_paths_menu() {
    echo settings-paths >>"$ACTION_CALLS"
    return 1
}
printf '1\n0\n' | manager_settings_menu >"$tmp/settings-action-error.out" || true
grep -Fxq settings-paths "$ACTION_CALLS"
[[ "$(grep -c 'CONFIGURACIÓN DEL ADMINISTRADOR' "$tmp/settings-action-error.out")" -ge 2 ]]

manager_dependencies_report() {
    echo dependencies-report >>"$ACTION_CALLS"
    return 1
}
printf '1\n0\n' | manager_dependencies_menu >"$tmp/dependencies-action-error.out" || true
grep -Fxq dependencies-report "$ACTION_CALLS"
[[ "$(grep -c 'DEPENDENCIAS DEL SISTEMA' "$tmp/dependencies-action-error.out")" -ge 2 ]]

printf 'OK: matriz de [0] Volver en submenús funcionales y recuperación tras fallos inyectados.\n'