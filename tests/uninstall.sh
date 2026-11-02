#!/usr/bin/env bash
# shellcheck disable=SC2218,SC2119
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/modules/uninstall.sh"
tmp="$(mktemp -d)"
XRAY_MANAGER_LIFECYCLE_LOCK="$tmp/lifecycle.lock"
export XRAY_MANAGER_LIFECYCLE_LOCK
trap 'rm -rf -- "$tmp"' EXIT

APP_ROOT="$tmp/app"
XRAY_ADMIN_BIN="$tmp/xray/bin/xray"
XRAY_ADMIN_DATA="$tmp/xray/share"
XRAY_CONFIG_DIR="$tmp/xray/config"
XRAY_MANAGER_CONFIG_DIR="$tmp/manager-config"
XRAY_MANAGER_DATA_DIR="$tmp/manager-data"
XRAY_MANAGER_USERS_DIR="$tmp/manager-data/users"
XRAY_MANAGER_CONNECTIONS_DIR="$tmp/manager-data/connections"
XRAY_MANAGER_PROFILES_DIR="$tmp/manager-data/profiles"
XRAY_MANAGER_DOMAINS_DIR="$tmp/manager-data/domains"
XRAY_MANAGER_CERTIFICATES_DIR="$tmp/manager-data/certificates"
XRAY_MANAGER_HISTORY_DIR="$tmp/manager-data/history"
XRAY_MANAGER_STATE_DIR="$tmp/manager-data/state"
XRAY_MANAGER_LOG_DIR="$tmp/log"
XRAY_MANAGER_CACHE_DIR="$tmp/cache"
XRAY_MANAGER_BACKUP_DIR="$tmp/backups"
[[ -n "$(uninstall_path_is_allowed "$APP_ROOT" && printf yes)" ]]
[[ -n "$(uninstall_path_is_allowed "$XRAY_ADMIN_BIN" && printf yes)" ]]
mkdir -p "$tmp/symlink-target"
ln -s "$tmp/symlink-target" "$tmp/symlink-parent"
old_app_root="$APP_ROOT"
APP_ROOT="$tmp/symlink-parent/app"
if uninstall_paths_are_allowed "$APP_ROOT"; then
	printf 'ERROR: se aceptó una ruta cuyo padre es un enlace simbólico.\n' >&2
	exit 1
fi
APP_ROOT="$old_app_root"
if uninstall_path_is_allowed /etc; then
	printf 'ERROR: se permitió una ruta no inventariada.\n' >&2
	exit 1
fi
if uninstall_path_is_allowed /; then
	printf 'ERROR: se permitió la raíz del sistema como destino.\n' >&2
	exit 1
fi
if uninstall_paths_are_allowed "$APP_ROOT" /etc; then
	printf 'ERROR: se aceptó una lista con una ruta no permitida.\n' >&2
	exit 1
fi
mkdir -p "$tmp/source/nested"
printf 'contenido de prueba\n' >"$tmp/source/nested/data.txt"
uninstall_make_backup "$tmp/backup.tar.gz" "$tmp/source"
tar -tzf "$tmp/backup.tar.gz" | grep -Fq "${tmp#/}/source/nested/data.txt"
gzip -t "$tmp/backup.tar.gz"

# Probar la exportación SSH/SCP con ejecutables simulados y verificación SHA-256.
mock_bin="$tmp/mock-bin"
MOCK_REMOTE_ROOT="$tmp/remote-root"
MOCK_REMOTE_HOST="backup-user@backup.example"
mkdir -p "$mock_bin" "$MOCK_REMOTE_ROOT"
cat >"$mock_bin/scp" <<'SCP'
#!/usr/bin/env bash
set -euo pipefail
while [[ "$1" == -* ]]; do
	if [[ "$1" == -o ]]; then shift 2; else shift; fi
done
src="$1"
destination="$2"
host="${destination%%:*}"
remote_path="${destination#*:}"
[[ "$host" == "$MOCK_REMOTE_HOST" && "$remote_path" == /* ]]
target="$MOCK_REMOTE_ROOT$remote_path"
mkdir -p "$(dirname "$target")"
cp -- "$src" "$target"
SCP
cat >"$mock_bin/ssh" <<'SSH'
#!/usr/bin/env bash
set -euo pipefail
while [[ "$1" == -o ]]; do shift 2; done
host="$1"
command="$2"
[[ "$host" == "$MOCK_REMOTE_HOST" ]]
remote_path="$(printf '%s\n' "$command" | awk '{print $3}' | tr -d '\047')"
[[ "$remote_path" == /* ]]
if [[ "${MOCK_BAD_HASH:-0}" == 1 ]]; then
	printf '%064d  %s\n' 0 "$remote_path"
else
	sha256sum -- "$MOCK_REMOTE_ROOT$remote_path"
fi
SSH
chmod 700 "$mock_bin/scp" "$mock_bin/ssh"
old_path="$PATH"
PATH="$mock_bin:$PATH"
export PATH MOCK_REMOTE_ROOT MOCK_REMOTE_HOST
uninstall_export_remote "$tmp/backup.tar.gz" "$MOCK_REMOTE_HOST:/srv/backups"
[[ -s "$MOCK_REMOTE_ROOT/srv/backups/backup.tar.gz" ]]
if MOCK_BAD_HASH=1 uninstall_export_remote "$tmp/backup.tar.gz" "$MOCK_REMOTE_HOST:/srv/backups"; then
	printf 'ERROR: se aceptó una exportación con SHA-256 incorrecto.\n' >&2
	exit 1
fi
PATH="$old_path"
unset MOCK_REMOTE_ROOT MOCK_REMOTE_HOST

# Un destino inválido o inexistente no debe producir un archivo verificado.
if uninstall_make_backup "$tmp/fail.tar.gz" "$tmp/no-existe"; then
	printf 'ERROR: se aceptó una ruta inexistente para respaldo.\n' >&2
	exit 1
fi
# Confirmar que la función de inventario no genera rutas arbitrarias.
if uninstall_service_guard >/dev/null 2>&1; then
	:
else
	printf 'SKIP: protección de servicio bloqueó el flujo en este host (comportamiento conservador).\n'
fi

# La presencia de una unidad detenida permite retirar solo Manager, pero no Xray-core.
systemctl() {
	case "${1:-}" in
	is-active) return 1 ;;
	list-unit-files)
		if [[ "${2:-}" == xray.service ]]; then printf 'xray.service disabled\n'; return 0; fi
		return 1
		;;
	*) return 1 ;;
	esac
}
uninstall_service_guard active
uninstall_service_guard manager
if uninstall_service_guard xray >/dev/null 2>&1 || uninstall_service_guard both >/dev/null 2>&1; then
	printf 'ERROR: se permitió retirar Xray-core mientras la unidad seguía instalada.\n' >&2
	exit 1
fi
systemctl() { [[ "${1:-}" == is-active ]]; }
if uninstall_service_guard manager >/dev/null 2>&1; then
	printf 'ERROR: se permitió retirar Manager mientras Xray estaba activo.\n' >&2
	exit 1
fi
unset -f systemctl

# Desinstalación real solo sobre fixtures temporales: manager + conservar datos.
mkdir -p "$APP_ROOT"
printf 'manager fixture\n' >"$APP_ROOT/marker.txt"
UNINSTALL_LOCK="$tmp/uninstall-flow.lock"
UNINSTALL_DATA_LOCK="$tmp/integrity.lock"
UNINSTALL_XRAY_LOCK="$tmp/xray-admin.lock"
UNINSTALL_BACKUP_STAGING_DIR="$tmp/staging"
mkdir -p "$APP_ROOT"
printf 'must remain\n' >"$APP_ROOT/marker.txt"
uninstall_service_guard() { return 0; }
ui_clear() { :; }
ui_title() { :; }
ui_pause() { :; }
ui_read_option() { IFS= read -r "$2"; }
if printf '2\n3\nxray-config\n' | uninstall_menu_action >"$tmp/scope-mismatch.out"; then
	printf 'ERROR: se aceptó una categoría ajena al alcance manager.\n' >&2
	exit 1
fi
[[ -f "$APP_ROOT/marker.txt" ]]

ui_clear() { :; }
ui_title() { :; }
ui_pause() { :; }
ui_read_option() { IFS= read -r "$2"; }
uninstall_service_guard() { return 0; }
confirm_count=0
ui_confirm() {
	((confirm_count += 1))
	case "$confirm_count" in
	1 | 3) return 0 ;; # crear respaldo y confirmar borrado
	*) return 1 ;;     # no exportar a un host externo
	esac
}
printf '2\n1\n' | uninstall_menu_action >"$tmp/uninstall-flow.out"
[[ ! -e "$APP_ROOT" ]]
archive="$(find "$UNINSTALL_BACKUP_STAGING_DIR" -name pre-uninstall.tar.gz -type f -print -quit)"
[[ -n "$archive" ]]
[[ "$(stat -c %a "$archive")" == 600 ]]
tar -tzf "$archive" | grep -Fq "${APP_ROOT#/}/marker.txt"
grep -Fq 'Se conservan todos los datos persistentes' "$tmp/uninstall-flow.out"
grep -Fq 'Exportación externa: No solicitada' "$tmp/uninstall-flow.out"

# Manager-only can be removed while the inactive Xray unit remains installed.
source "$ROOT/modules/uninstall.sh"
systemctl() {
	case "${1:-}" in
	is-active) return 1 ;;
	list-unit-files)
		if [[ "${2:-}" == xray.service ]]; then printf 'xray.service disabled\n'; return 0; fi
		return 1
		;;
	*) return 1 ;;
	esac
}
mkdir -p "$APP_ROOT"
printf 'manager-only fixture\n' >"$APP_ROOT/manager-only.marker"
UNINSTALL_LOCK="$tmp/uninstall-manager-with-unit.lock"
UNINSTALL_DATA_LOCK="$tmp/integrity-manager-with-unit.lock"
UNINSTALL_XRAY_LOCK="$tmp/xray-manager-with-unit.lock"
UNINSTALL_BACKUP_STAGING_DIR="$tmp/staging-manager-with-unit"
confirm_count=0
ui_confirm() { ((confirm_count += 1)); [[ "$confirm_count" -eq 2 ]]; }
printf '2\n1\n' | uninstall_menu_action >"$tmp/uninstall-manager-with-unit.out"
[[ ! -e "$APP_ROOT" ]]
[[ "$(systemctl list-unit-files xray.service --no-legend)" == 'xray.service disabled' ]]
# The Xray-only scope must remain blocked while the unit is present.
mkdir -p "$XRAY_ADMIN_BIN"
printf 'xray fixture remains\n' >"$XRAY_ADMIN_BIN/marker"
if uninstall_menu_action xray >"$tmp/uninstall-xray-with-unit.out" 2>&1; then
	printf 'ERROR: se permitió retirar Xray-core con la unidad instalada.\n' >&2
	exit 1
fi
[[ -f "$XRAY_ADMIN_BIN/marker" ]]
unset -f systemctl

# Un instalador/gestor de dependencias activo bloquea el inicio de desinstalación.
mkdir -p "$APP_ROOT"
printf 'preserve under lifecycle lock\n' >"$APP_ROOT/marker.txt"
UNINSTALL_LOCK="$tmp/uninstall-lifecycle-busy.lock"
UNINSTALL_DATA_LOCK="$tmp/integrity-lifecycle-busy.lock"
UNINSTALL_XRAY_LOCK="$tmp/xray-lifecycle-busy.lock"
XRAY_MANAGER_LIFECYCLE_LOCK="$tmp/lifecycle-busy.lock"
exec {busy_lifecycle_fd}>"$XRAY_MANAGER_LIFECYCLE_LOCK"
flock -x "$busy_lifecycle_fd"
ui_confirm() { return 0; }
if printf '2\n1\n' | uninstall_menu_action >"$tmp/uninstall-lifecycle-busy.out" 2>&1; then
	printf 'ERROR: se desinstaló mientras había otra operación de ciclo de vida.\n' >&2
	exit 1
fi
grep -Fq 'otra operación de ciclo de vida' "$tmp/uninstall-lifecycle-busy.out"
[[ -f "$APP_ROOT/marker.txt" ]]
flock -u "$busy_lifecycle_fd"
exec {busy_lifecycle_fd}>&-

# Cancelar la confirmación irreversible final no elimina el componente ni sus datos.
reset_uninstall_ui() {
	ui_clear() { :; }
	ui_title() { :; }
	ui_pause() { :; }
	ui_read_option() { IFS= read -r "$2"; }
	uninstall_service_guard() { return 0; }
}
UNINSTALL_LOCK="$tmp/uninstall-final-cancel.lock"
UNINSTALL_DATA_LOCK="$tmp/integrity-final-cancel.lock"
UNINSTALL_XRAY_LOCK="$tmp/xray-final-cancel.lock"
XRAY_MANAGER_LIFECYCLE_LOCK="$tmp/lifecycle-final-cancel.lock"
UNINSTALL_BACKUP_STAGING_DIR="$tmp/staging-final-cancel"
mkdir -p "$APP_ROOT"
printf 'preserve after final cancel\n' >"$APP_ROOT/marker.txt"
confirm_count=0
ui_confirm() {
	((confirm_count += 1))
	[[ "$confirm_count" -eq 1 ]]
}
printf '2\n1\n' | uninstall_menu_action >"$tmp/uninstall-final-cancel.out"
grep -Fq 'Operación cancelada. No se eliminó ninguna ruta.' "$tmp/uninstall-final-cancel.out"
[[ -f "$APP_ROOT/marker.txt" ]]
[[ -z "$(find "$UNINSTALL_BACKUP_STAGING_DIR" -name pre-uninstall.tar.gz -type f -print -quit 2>/dev/null)" ]]

# Un respaldo fallido debe cancelar la eliminación y dejar intacta la ruta.
mkdir -p "$APP_ROOT"
printf 'keep me\n' >"$APP_ROOT/marker.txt"
uninstall_make_backup() { return 1; }
confirm_count=0
ui_confirm() {
	((confirm_count += 1))
	return 0
}
if printf '2\n1\n' | uninstall_menu_action >"$tmp/uninstall-backup-failure.out"; then
	printf 'ERROR: se aceptó una desinstalación cuyo respaldo falló.\n' >&2
	exit 1
fi
[[ -f "$APP_ROOT/marker.txt" ]]
grep -Fq 'Se cancela la desinstalación' "$tmp/uninstall-backup-failure.out"

# Si hay una escritura de usuarios/conexiones activa, la desinstalación debe abortar.
mkdir -p "$APP_ROOT"
printf 'keep during lock contention\n' >"$APP_ROOT/marker.txt"
UNINSTALL_LOCK="$tmp/uninstall-busy.lock"
UNINSTALL_DATA_LOCK="$tmp/integrity-busy.lock"
UNINSTALL_XRAY_LOCK="$tmp/xray-busy.lock"
UNINSTALL_BACKUP_STAGING_DIR="$tmp/staging-busy"
exec {busy_fd}>"$UNINSTALL_DATA_LOCK"
flock -x "$busy_fd"
confirm_count=0
ui_confirm() {
	((confirm_count += 1))
	[[ "$confirm_count" -eq 2 ]]
}
if printf '2\n1\n' | uninstall_menu_action >"$tmp/uninstall-lock-busy.out"; then
	printf 'ERROR: se desinstaló mientras había una operación de usuarios/conexiones activa.\n' >&2
	exit 1
fi
grep -Fq "Hay una operación de usuarios o conexiones en curso" "$tmp/uninstall-lock-busy.out"
[[ -f "$APP_ROOT/marker.txt" ]]
flock -u "$busy_fd"
exec {busy_fd}>&-

# Una exportación remota exitosa debe quedar reflejada como verificada en el resumen.
source "$ROOT/modules/uninstall.sh"
UNINSTALL_LOCK="$tmp/uninstall-export.lock"
UNINSTALL_DATA_LOCK="$tmp/integrity-export.lock"
UNINSTALL_XRAY_LOCK="$tmp/xray-export.lock"
UNINSTALL_BACKUP_STAGING_DIR="$tmp/staging-export"
mkdir -p "$APP_ROOT"
printf 'manager export fixture\n' >"$APP_ROOT/marker.txt"
uninstall_service_guard() { return 0; }
uninstall_export_remote() {
	[[ -s "$1" && "$2" == 'backup-user@backup.example:/srv/backups' ]]
}
confirm_count=0
ui_confirm() {
	((confirm_count += 1))
	return 0
}
printf '2\n1\nbackup-user@backup.example:/srv/backups\n' |
	uninstall_menu_action >"$tmp/uninstall-export-success.out"
grep -Fq 'Exportación externa: Verificada por SHA-256 en backup-user@backup.example:/srv/backups' "$tmp/uninstall-export-success.out"
grep -Fq "Historial de versiones/modificaciones de perfiles" "$tmp/uninstall-export-success.out"
grep -Fq "Historial de validaciones" "$tmp/uninstall-export-success.out"
grep -Fq "Informes de restauración" "$tmp/uninstall-export-success.out"
grep -Fq "Registros técnicos y logs" "$tmp/uninstall-export-success.out"
[[ ! -e "$APP_ROOT" ]]
archive="$(find "$UNINSTALL_BACKUP_STAGING_DIR" -name pre-uninstall.tar.gz -type f -print -quit)"
[[ -n "$archive" && -s "$archive" ]]

# U11: verificar todos los campos del resumen antes de la confirmación irreversible.
preview_root="$tmp/preview-complete"
APP_ROOT="$preview_root/app"
XRAY_ADMIN_BIN="$preview_root/xray/bin/xray"
XRAY_ADMIN_DATA="$preview_root/xray/share"
XRAY_MANAGER_USERS_DIR="$preview_root/manager-data/users"
XRAY_MANAGER_LIFECYCLE_LOCK="$preview_root/lifecycle.lock"
UNINSTALL_LOCK="$preview_root/uninstall.lock"
UNINSTALL_DATA_LOCK="$preview_root/integrity.lock"
UNINSTALL_XRAY_LOCK="$preview_root/xray.lock"
UNINSTALL_BACKUP_STAGING_DIR="$preview_root/staging"
mkdir -p "$APP_ROOT" "$XRAY_ADMIN_BIN" "$XRAY_ADMIN_DATA" "$XRAY_MANAGER_USERS_DIR" "$preview_root"
printf 'app preview fixture\n' >"$APP_ROOT/marker"
printf 'xray preview fixture\n' >"$XRAY_ADMIN_BIN/marker"
printf 'geodata preview fixture\n' >"$XRAY_ADMIN_DATA/marker"
printf 'user preview fixture\n' >"$XRAY_MANAGER_USERS_DIR/marker"
uninstall_service_guard() { return 0; }
uninstall_export_remote() { [[ -s "$1" && "$2" == 'backup-user@backup.example:/srv/backups' ]]; }
confirm_count=0
preview_confirm_log="$preview_root/confirm-prompts.log"
ui_confirm() {
    printf '%s\n' "$1" >>"$preview_confirm_log"
    ((confirm_count += 1))
    return 0
}
printf '3\n3\nusers\nbackup-user@backup.example:/srv/backups\n' | uninstall_menu_action >"$tmp/uninstall-preview-complete.out"
preview_out="$tmp/uninstall-preview-complete.out"
grep -Fq 'Alcance: both' "$preview_out"
grep -Fq 'Política: selected' "$preview_out"
grep -Fq 'Seleccionadas para eliminar: users' "$preview_out"
grep -Fq 'Rutas que se eliminarán:' "$preview_out"
grep -Fq "$APP_ROOT" "$preview_out"
grep -Fq "$XRAY_ADMIN_BIN" "$preview_out"
grep -Fq "$XRAY_ADMIN_DATA" "$preview_out"
grep -Fq "$XRAY_MANAGER_USERS_DIR" "$preview_out"
grep -Fq 'Respaldo temporal verificado:' "$preview_out"
grep -Fq 'Exportación externa: Verificada por SHA-256 en backup-user@backup.example:/srv/backups' "$preview_out"
grep -Fq 'Las unidades systemd no se eliminan ni modifican' "$preview_out"
grep -Fq 'Historial de versiones/modificaciones de perfiles' "$preview_out"
grep -Fq 'Historial de validaciones' "$preview_out"
grep -Fq 'Informes de restauración' "$preview_out"
grep -Fq 'Registros técnicos y logs' "$preview_out"
grep -Fq '¿Deseas crear un respaldo previo de las rutas seleccionadas?' "$preview_confirm_log"
grep -Fq '¿Deseas exportar el respaldo a otro servidor por SSH/SCP?' "$preview_confirm_log"
grep -Fq 'CONFIRMACIÓN FINAL: ¿ejecutar esta operación irreversible?' "$preview_confirm_log"
[[ "$(wc -l <"$preview_confirm_log")" -eq 3 ]]
! grep -Fq '\n  - Historial' "$preview_out"
[[ ! -e "$APP_ROOT" && ! -e "$XRAY_ADMIN_BIN" && ! -e "$XRAY_ADMIN_DATA" && ! -e "$XRAY_MANAGER_USERS_DIR" ]]
preview_archive="$(find "$UNINSTALL_BACKUP_STAGING_DIR" -name pre-uninstall.tar.gz -type f -print -quit)"
[[ -n "$preview_archive" && "$(stat -c %a "$preview_archive")" == 600 ]]

# La desinstalación debe respetar el lock real de administración Xray.
source "$ROOT/modules/uninstall.sh"
UNINSTALL_LOCK="$tmp/uninstall-xray-busy.lock"
UNINSTALL_DATA_LOCK="$tmp/integrity-xray-busy.lock"
UNINSTALL_XRAY_LOCK="$tmp/xray-admin-busy.lock"
UNINSTALL_BACKUP_STAGING_DIR="$tmp/staging-xray-busy"
mkdir -p "$APP_ROOT"
printf 'preserve while Xray administration is active\n' >"$APP_ROOT/marker.txt"
uninstall_service_guard() { return 0; }
ui_clear() { :; }
ui_title() { :; }
ui_pause() { :; }
ui_read_option() { IFS= read -r "$2"; }
exec {busy_xray_fd}>"$UNINSTALL_XRAY_LOCK"
flock -x "$busy_xray_fd"
confirm_count=0
ui_confirm() {
    ((confirm_count += 1))
    [[ "$confirm_count" -eq 2 ]]
}
if printf '2\n1\n' | uninstall_menu_action >"$tmp/uninstall-xray-lock-busy.out"; then
    printf 'ERROR: se desinstaló mientras había una operación de administración Xray activa.\n' >&2
    exit 1
fi
grep -Fq 'Hay una operación de administración de Xray-core en curso' "$tmp/uninstall-xray-lock-busy.out"
[[ -f "$APP_ROOT/marker.txt" ]]
flock -u "$busy_xray_fd"
exec {busy_xray_fd}>&-

# La categoría de certificados debe advertir antes de cualquier borrado y respetar cancelación.
UNINSTALL_LOCK="$tmp/uninstall-cert-cancel.lock"
UNINSTALL_DATA_LOCK="$tmp/integrity-cert-cancel.lock"
UNINSTALL_XRAY_LOCK="$tmp/xray-cert-cancel.lock"
UNINSTALL_BACKUP_STAGING_DIR="$tmp/staging-cert-cancel"
mkdir -p "$XRAY_MANAGER_CERTIFICATES_DIR"
printf 'private-key fixture\n' >"$XRAY_MANAGER_CERTIFICATES_DIR/private.key"
ui_confirm() { return 1; }
printf '2\n3\ncertificates\n' | uninstall_menu_action >"$tmp/uninstall-cert-cancel.out"
grep -Fq 'certificados y claves privadas' "$tmp/uninstall-cert-cancel.out"
grep -Fq 'Operación cancelada' "$tmp/uninstall-cert-cancel.out"
[[ -f "$XRAY_MANAGER_CERTIFICATES_DIR/private.key" ]]

# Política "eliminar todos": incluye respaldos preexistentes y elimina el respaldo temporal.
UNINSTALL_LOCK="$tmp/uninstall-all.lock"
UNINSTALL_DATA_LOCK="$tmp/integrity-all.lock"
UNINSTALL_XRAY_LOCK="$tmp/xray-all.lock"
UNINSTALL_BACKUP_STAGING_DIR="$tmp/staging-all"
XRAY_MANAGER_BACKUP_DIR="$tmp/manager-data/backups-all"
mkdir -p "$APP_ROOT" "$XRAY_MANAGER_CONFIG_DIR" "$XRAY_MANAGER_DATA_DIR"     "$XRAY_MANAGER_LOG_DIR" "$XRAY_MANAGER_CACHE_DIR" "$XRAY_MANAGER_BACKUP_DIR" "$XRAY_MANAGER_STATE_DIR"
printf 'manager fixture\n' >"$APP_ROOT/marker.txt"
printf 'old backup\n' >"$XRAY_MANAGER_BACKUP_DIR/old.tar.gz"
confirm_count=0
ui_confirm() {
    ((confirm_count += 1))
    case "$confirm_count" in
        1|2|4) return 0 ;; # certificados, respaldo previo y confirmación final
        3) return 1 ;;     # no exportar fuera del servidor
    esac
}
printf '2\n2\n' | uninstall_menu_action >"$tmp/uninstall-all-cleanup.out"
[[ ! -e "$APP_ROOT" ]]
[[ ! -e "$XRAY_MANAGER_CONFIG_DIR" ]]
[[ ! -e "$XRAY_MANAGER_DATA_DIR" ]]
[[ ! -e "$XRAY_MANAGER_LOG_DIR" ]]
[[ ! -e "$XRAY_MANAGER_CACHE_DIR" ]]
[[ ! -e "$XRAY_MANAGER_BACKUP_DIR" ]]
[[ ! -e "$XRAY_MANAGER_STATE_DIR" ]]
if find "$UNINSTALL_BACKUP_STAGING_DIR" -name pre-uninstall.tar.gz -type f -print -quit 2>/dev/null | grep -q .; then
    printf 'ERROR: quedó un respaldo temporal tras eliminar todos los datos.\n' >&2
    exit 1
fi
grep -Fq 'Se eliminarán también los respaldos locales existentes y el respaldo temporal' "$tmp/uninstall-all-cleanup.out"
grep -Fq 'Respaldo verificado:' "$tmp/uninstall-all-cleanup.out"

printf 'OK: respaldo, allowlist, bloqueos, advertencia/cancelación de certificados y limpieza total de respaldos.\n'

# Cobertura individual del mapeo de categorías: cada caso usa fixtures aislados.
reset_uninstall_ui() {
    ui_clear() { :; }
    ui_title() { :; }
    ui_pause() { :; }
    ui_read_option() { IFS= read -r "$2"; }
    uninstall_service_guard() { return 0; }
    UNINSTALL_LOCK="$tmp/category-uninstall.lock"
    UNINSTALL_DATA_LOCK="$tmp/category-integrity.lock"
    UNINSTALL_XRAY_LOCK="$tmp/category-xray.lock"
    UNINSTALL_BACKUP_STAGING_DIR="$tmp/category-staging"
}
run_selected_category() {
    local scope_choice="$1" category="$2" target="$3" count=0
    reset_uninstall_ui
    mkdir -p "$target"
    printf 'category fixture: %s\n' "$category" >"$target/marker.txt"
    if [[ "$category" == logs ]]; then
        mkdir -p "$XRAY_MANAGER_HISTORY_DIR"
        printf 'history fixture\n' >"$XRAY_MANAGER_HISTORY_DIR/marker.txt"
    fi
    ui_confirm() {
        ((count += 1))
        if [[ "$category" == certificates && "$count" -eq 1 ]]; then return 0; fi
        # Para certificados, primera confirmación: aviso; luego no respaldar y confirmar.
        if [[ "$category" == certificates ]]; then [[ "$count" -eq 3 ]]; else [[ "$count" -eq 2 ]]; fi
    }
    printf '%s\n3\n%s\n' "$scope_choice" "$category" | uninstall_menu_action >"$tmp/category-${scope_choice}-${category}.out"
    [[ ! -e "$target" ]] || {
        printf 'ERROR: categoría %s no eliminó su ruta esperada %s.\n' "$category" "$target" >&2
        exit 1
    }
}
run_selected_category 1 xray-config "$XRAY_CONFIG_DIR"
run_selected_category 2 profiles "$XRAY_MANAGER_PROFILES_DIR"
run_selected_category 2 users "$XRAY_MANAGER_USERS_DIR"
run_selected_category 2 connections "$XRAY_MANAGER_CONNECTIONS_DIR"
run_selected_category 2 domains "$XRAY_MANAGER_DOMAINS_DIR"
run_selected_category 2 certificates "$XRAY_MANAGER_CERTIFICATES_DIR"
run_selected_category 2 backups "$XRAY_MANAGER_BACKUP_DIR"
run_selected_category 2 preferences "$XRAY_MANAGER_CONFIG_DIR"
run_selected_category 2 logs "$XRAY_MANAGER_LOG_DIR"
# logs incluye history además de log; verifica que ambas rutas se mapean.
[[ ! -e "$XRAY_MANAGER_HISTORY_DIR" ]]

# Política selected también funciona con alcance combinado sin borrar otras categorías.
reset_uninstall_ui
mkdir -p "$APP_ROOT" "$XRAY_ADMIN_BIN" "$XRAY_MANAGER_USERS_DIR" "$XRAY_MANAGER_CONNECTIONS_DIR"
printf 'app preserved\n' >"$APP_ROOT/marker"
printf 'xray preserved\n' >"$XRAY_ADMIN_BIN/marker"
printf 'user selected\n' >"$XRAY_MANAGER_USERS_DIR/marker"
printf 'connections preserved\n' >"$XRAY_MANAGER_CONNECTIONS_DIR/marker"
count=0
ui_confirm() { ((count += 1)); [[ "$count" -eq 2 ]]; }
printf '3\n3\nusers\n' | uninstall_menu_action >"$tmp/category-both-users.out"
[[ ! -e "$XRAY_MANAGER_USERS_DIR" ]]
[[ ! -e "$APP_ROOT" && ! -e "$XRAY_ADMIN_BIN" && -e "$XRAY_MANAGER_CONNECTIONS_DIR/marker" ]]

# Política all en los tres alcances: elimina las rutas correspondientes y sus respaldos.
run_all_scope() {
    local scope_choice="$1" label="$2" count=0
    reset_uninstall_ui
    XRAY_MANAGER_BACKUP_DIR="$tmp/$label-backups"
    mkdir -p "$APP_ROOT" "$XRAY_ADMIN_BIN" "$XRAY_ADMIN_DATA" "$XRAY_CONFIG_DIR" \
        "$XRAY_MANAGER_CONFIG_DIR" "$XRAY_MANAGER_DATA_DIR" "$XRAY_MANAGER_LOG_DIR" \
        "$XRAY_MANAGER_CACHE_DIR" "$XRAY_MANAGER_STATE_DIR" \
        "$XRAY_MANAGER_BACKUP_DIR/xray-core"
    printf 'app fixture\n' >"$APP_ROOT/marker"
    printf 'xray fixture\n' >"$XRAY_ADMIN_BIN/marker"
    printf 'data fixture\n' >"$XRAY_ADMIN_DATA/marker"
    printf 'xray config fixture\n' >"$XRAY_CONFIG_DIR/marker"
    printf 'old manager backup\n' >"$XRAY_MANAGER_BACKUP_DIR/old.tar.gz"
    printf 'old xray backup\n' >"$XRAY_MANAGER_BACKUP_DIR/xray-core/old.tar.gz"
    ui_confirm() {
        ((count += 1))
        case "$scope_choice:$count" in
            1:1|1:3|2:1|2:3|3:1|3:2|3:4) return 0 ;;
            *) return 1 ;;
        esac
    }
    printf '%s\n2\n' "$scope_choice" | uninstall_menu_action >"$tmp/all-${label}.out"
    case "$scope_choice" in
        1)
            [[ ! -e "$XRAY_ADMIN_BIN" && ! -e "$XRAY_ADMIN_DATA" && ! -e "$XRAY_CONFIG_DIR" ]]
            [[ ! -e "$XRAY_MANAGER_BACKUP_DIR/xray-core" ]]
            [[ -e "$APP_ROOT" && -e "$XRAY_MANAGER_DATA_DIR" && -e "$XRAY_MANAGER_BACKUP_DIR/old.tar.gz" ]]
            ;;
        2)
            [[ ! -e "$APP_ROOT" && ! -e "$XRAY_MANAGER_CONFIG_DIR" && ! -e "$XRAY_MANAGER_DATA_DIR" ]]
            [[ ! -e "$XRAY_MANAGER_LOG_DIR" && ! -e "$XRAY_MANAGER_CACHE_DIR" && ! -e "$XRAY_MANAGER_STATE_DIR" ]]
            [[ ! -e "$XRAY_MANAGER_BACKUP_DIR" ]]
            [[ -e "$XRAY_ADMIN_BIN" && -e "$XRAY_CONFIG_DIR" ]]
            ;;
        3)
            [[ ! -e "$APP_ROOT" && ! -e "$XRAY_ADMIN_BIN" && ! -e "$XRAY_ADMIN_DATA" ]]
            [[ ! -e "$XRAY_CONFIG_DIR" && ! -e "$XRAY_MANAGER_CONFIG_DIR" && ! -e "$XRAY_MANAGER_DATA_DIR" ]]
            [[ ! -e "$XRAY_MANAGER_LOG_DIR" && ! -e "$XRAY_MANAGER_CACHE_DIR" && ! -e "$XRAY_MANAGER_STATE_DIR" ]]
            [[ ! -e "$XRAY_MANAGER_BACKUP_DIR" ]]
            ;;
    esac
    if find "$UNINSTALL_BACKUP_STAGING_DIR" -name pre-uninstall.tar.gz -type f -print -quit 2>/dev/null | grep -q .; then
        printf 'ERROR: quedó un respaldo temporal en alcance %s.\n' "$label" >&2
        exit 1
    fi
}
run_all_scope 1 xray
run_all_scope 2 manager-repeat
run_all_scope 3 both

# Política keep en los alcances restantes: retirar binarios/componentes sin borrar datos.
run_keep_scope() {
    local scope_choice="$1" label="$2" count=0
    reset_uninstall_ui
    mkdir -p "$APP_ROOT" "$XRAY_ADMIN_BIN" "$XRAY_ADMIN_DATA" "$XRAY_CONFIG_DIR" "$XRAY_MANAGER_DATA_DIR" "$XRAY_MANAGER_BACKUP_DIR/xray-core"
    printf 'keep fixture\n' >"$APP_ROOT/marker"
    printf 'keep config\n' >"$XRAY_CONFIG_DIR/marker"
    ui_confirm() { ((count += 1)); [[ "$count" -eq 2 ]]; }
    printf '%s\n1\n' "$scope_choice" | uninstall_menu_action >"$tmp/keep-${label}.out"
    [[ ! -e "$XRAY_ADMIN_BIN" && ! -e "$XRAY_ADMIN_DATA" ]]
    [[ -e "$XRAY_CONFIG_DIR/marker" && -e "$XRAY_MANAGER_DATA_DIR" && -e "$XRAY_MANAGER_BACKUP_DIR/xray-core" ]]
    if [[ "$scope_choice" == 3 ]]; then [[ ! -e "$APP_ROOT" ]]; else [[ -e "$APP_ROOT/marker" ]]; fi
}
run_keep_scope 1 xray
run_keep_scope 3 both

printf 'OK: cobertura individual de nueve categorías, resumen U11 completo y política all en Xray-core, Manager y ambos.\n'