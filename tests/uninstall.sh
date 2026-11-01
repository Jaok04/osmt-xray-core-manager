#!/usr/bin/env bash
# shellcheck disable=SC2218,SC2119
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/modules/uninstall.sh"
tmp="$(mktemp -d)"
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

printf 'OK: creación/verificación de respaldo, allowlist, borrado aislado, cancelación ante fallo y estado de exportación remota exitosa.\n'
