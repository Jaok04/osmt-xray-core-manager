#!/usr/bin/env bash
# shellcheck disable=SC2218,SC2120
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
source "$ROOT/config/manager.conf"
source "$ROOT/config/paths.sh"
source "$ROOT/config/xray-version.conf"
source "$ROOT/lib/ui.sh"
source "$ROOT/lib/system.sh"
source "$ROOT/modules/xray_admin.sh"
source "$ROOT/modules/uninstall.sh"
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

printf 'OK: navegación y conexión del menú de administración Xray; consulta de release; rutas, inventario y systemd de solo lectura.\n'
