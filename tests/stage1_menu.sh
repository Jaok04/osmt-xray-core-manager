#!/usr/bin/env bash
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

printf '1\n2\n3\n\n4\n\n5\n6\n7\n0\n' | menu_xray_admin >"$tmp/xray-menu.out"
grep -Fxq 'install-action:install' "$CALLS"
grep -Fxq 'install-action:update' "$CALLS"
grep -Fxq 'install-action:reinstall' "$CALLS"
grep -Fxq 'install-action:repair' "$CALLS"
grep -Fxq 'uninstall-action:xray' "$CALLS"
grep -q 'Última versión estable publicada: 26.10.31' "$tmp/xray-menu.out"
grep -q 'Compatibilidad local: disponible' "$tmp/xray-menu.out"

printf '1\n\n2\n\n3\n\n0\n' | menu_installation_information >"$tmp/install-info.out"
grep -q 'RUTAS DE INSTALACIÓN' "$tmp/install-info.out"
grep -q 'ARCHIVOS Y DIRECTORIOS' "$tmp/install-info.out"
grep -q 'INFORMACIÓN DE SYSTEMD' "$tmp/install-info.out"
grep -q 'Esta pantalla es de solo lectura' "$tmp/install-info.out"

printf 'OK: navegación y conexión del menú de administración Xray; consulta de release; rutas, inventario y systemd de solo lectura.\n'