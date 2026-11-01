#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
PREFS="$tmp/preferences.conf"
cat >"$PREFS" <<'PREF'
XRAY_BIN_PATH=/opt/custom-xray/bin/xray
XRAY_DATA_DIR=/opt/custom-xray/share
XRAY_CONFIG_DIR=/etc/xray-custom
XRAY_CONFIG_FILE=/etc/xray-custom/config.json
XRAY_MANAGER_BACKUP_DIR=/var/backups/xray-manager-custom
APP_THEME=green
APP_LANGUAGE=en
APP_TIMEZONE=UTC
APP_DATE_FORMAT=ymd
APP_TIME_FORMAT=12h
BACKUP_RETENTION=999
BACKUP_COMPRESSION=gzip
APP_EDITOR=editor-that-does-not-exist
PREF
chmod 600 "$PREFS"
MANAGER_PREFERENCES_FILE="$PREFS" bash -s -- "$ROOT" "$tmp" <<'BASH'
	set -Eeuo pipefail
	ROOT="$1"
	source "$ROOT/config/manager.conf"
	source "$ROOT/config/preferences.sh"
	source "$ROOT/config/paths.sh"
	source "$ROOT/lib/ui.sh"
	source "$ROOT/lib/system.sh"
	source "$ROOT/modules/system_admin.sh"
	source "$ROOT/modules/admin_settings.sh"
	[[ "$XRAY_BIN_PATH" == /opt/custom-xray/bin/xray ]]
	[[ "$XRAY_ADMIN_BIN" == /opt/custom-xray/bin/xray ]]
	[[ "$XRAY_ADMIN_DATA" == /opt/custom-xray/share ]]
	[[ "$XRAY_CONFIG_DIR" == /etc/xray-custom ]]
	[[ "$XRAY_CONFIG_FILE" == /etc/xray-custom/config.json ]]
	[[ "$XRAY_MANAGER_BACKUP_DIR" == /var/backups/xray-manager-custom ]]
	[[ "$APP_THEME" == green ]]
	[[ "$APP_LANGUAGE" == es ]]
	[[ "$APP_TIMEZONE" == UTC ]]
	[[ "$APP_DATE_FORMAT" == ymd ]]
	[[ "$APP_TIME_FORMAT" == 12h ]]
	[[ "$BACKUP_RETENTION" == 7 ]]
	[[ -z "$APP_EDITOR" ]]
	manager_preferences_valid_path /opt/a-b_c.1/xray
	! manager_preferences_valid_path relative/path
	! manager_preferences_valid_path /
	! manager_preferences_valid_path /opt/../etc
	manager_preferences_valid_xray_bin /opt/custom-xray/bin/xray
	! manager_preferences_valid_xray_bin /bin/bash
	manager_preferences_valid_xray_data /opt/custom-xray/share
	! manager_preferences_valid_xray_data /usr/local
	manager_preferences_valid_xray_config_dir /etc/xray-custom
	! manager_preferences_valid_xray_config_dir /etc
	manager_preferences_valid_backup_dir /var/backups/xray-manager-custom
	! manager_preferences_valid_backup_dir /var/backups
	! manager_preferences_valid_config_file /etc/passwd /etc/xray-custom
	mkdir -p "$2/symlink-target"
	ln -s "$2/symlink-target" "$2/symlink"
	manager_preferences_path_has_symlink_component "$2/symlink/child"
	! manager_preferences_path_has_symlink_component "$2/nonexistent/child"
	MANAGER_PREFERENCES_FILE="$2/saved.conf"
	manager_preferences_directory_is_safe() { [[ "$1" == "$(dirname "$MANAGER_PREFERENCES_FILE")" ]]; }
	manager_preferences_directory_is_safe "$2"
	manager_settings_save
	[[ "$(stat -c %a "$MANAGER_PREFERENCES_FILE")" == 600 ]]
	grep -Fxq "XRAY_BIN_PATH=/opt/custom-xray/bin/xray" "$MANAGER_PREFERENCES_FILE"
	# Simular una edición de rutas con confirmación, sin mover archivos.
	ui_confirm() { return 0; }
	ui_pause() { :; }
	printf '%s\n' /opt/new-xray/bin/xray /opt/new-xray/share /etc/xray-new-xray /etc/xray-new-xray/config.json >"$2/path-input"
	manager_settings_path_input() {
		case "$3" in
		new_bin) printf -v "$3" '%s' /opt/new-xray/bin/xray ;;
		new_data) printf -v "$3" '%s' /opt/new-xray/share ;;
		new_config_dir) printf -v "$3" '%s' /etc/xray-new-xray ;;
		new_config_file) printf -v "$3" '%s' /etc/xray-new-xray/config.json ;;
		esac
	}
	manager_settings_paths_menu >/dev/null
	[[ "$XRAY_ADMIN_BIN" == /opt/new-xray/bin/xray ]]
	[[ "$XRAY_CONFIG_FILE" == /etc/xray-new-xray/config.json ]]
	grep -Fxq "XRAY_BIN_PATH=/opt/new-xray/bin/xray" "$MANAGER_PREFERENCES_FILE"
	# Cambiar tema y verificar persistencia.
	printf '2\n' >"$2/theme-input"
	ui_read_option() { printf -v "$2" '%s' 2; }
	APP_THEME=cyan
	manager_settings_theme_menu >/dev/null
	[[ "$APP_THEME" == green ]]
	grep -Fxq "APP_THEME=green" "$MANAGER_PREFERENCES_FILE"
	# Un fallo de persistencia no debe dejar preferencias nuevas solo en memoria.
	manager_settings_save() { return 1; }
	command() {
		if [[ "$1" == -v && "$2" == nano ]]; then return 0; fi
		builtin command "$@"
	}
	ui_read_option() { printf -v "$2" '%s' 1; }
	APP_EDITOR=editor-anterior
	if manager_settings_editor_menu >/dev/null; then
		printf "ERROR: se informó éxito al guardar un editor con persistencia fallida.\n" >&2
		exit 1
	fi
	[[ "$APP_EDITOR" == editor-anterior ]]
	# El encabezado respeta formato, zona horaria y tolera fuentes no disponibles.
	system_public_ip() { printf "203.0.113.10"; }
	system_xray_version() { printf "No instalado"; }
	system_xray_service_state() { printf "No instalado"; }
	system_xray_autostart() { printf "No configurado"; }
	system_active_profile() { printf "Ninguno"; }
	out="$(system_show_header)"
	grep -q "Fecha:.*$(TZ=UTC date "+%Y-%m-%d")" <<<"$out"
	grep -Eq "Hora:.*([0-9]{2}:[0-9]{2}:[0-9]{2} (AM|PM) UTC)" <<<"$out"
BASH
# Un archivo con rutas peligrosas no debe alterar los valores predeterminados.
mkdir -m 700 "$tmp/bad-preferences-dir"
cat >"$tmp/bad-preferences-dir/preferences.conf" <<'BAD'
XRAY_BIN_PATH=/bin/bash
XRAY_DATA_DIR=/etc
XRAY_CONFIG_DIR=/etc
XRAY_CONFIG_FILE=/etc/passwd
XRAY_MANAGER_BACKUP_DIR=/var/backups
BAD
chmod 600 "$tmp/bad-preferences-dir/preferences.conf"
MANAGER_PREFERENCES_FILE="$tmp/bad-preferences-dir/preferences.conf" bash -c '
	ROOT="$1"
	source "$ROOT/config/preferences.sh"
	[[ "$XRAY_BIN_PATH" == /usr/local/bin/xray ]]
	[[ "$XRAY_DATA_DIR" == /usr/local/share/xray ]]
	[[ "$XRAY_CONFIG_DIR" == /etc/xray ]]
	[[ "$XRAY_CONFIG_FILE" == /etc/xray/config.json ]]
	[[ "$XRAY_MANAGER_BACKUP_DIR" == /var/backups/xray-manager ]]
' _ "$ROOT"

printf 'OK: carga validada de preferencias, persistencia atómica 600, rutas, tema, validaciones y formato de fecha/hora.\n'
