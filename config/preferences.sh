#!/usr/bin/env bash
# shellcheck disable=SC2034
# Carga segura de preferencias del gestor. El archivo usa pares KEY=VALUE;
# nunca se ejecuta como código de shell.

: "${MANAGER_PREFERENCES_FILE:=/etc/xray-manager/preferences.conf}"
XRAY_BIN_PATH="/usr/local/bin/xray"
XRAY_DATA_DIR="/usr/local/share/xray"
XRAY_CONFIG_DIR="/etc/xray"
XRAY_CONFIG_FILE="/etc/xray/config.json"
XRAY_MANAGER_BACKUP_DIR="/var/backups/xray-manager"
APP_EDITOR=""
APP_THEME="cyan"
APP_LANGUAGE="es"
APP_TIMEZONE="America/Bogota"
APP_DATE_FORMAT="dmy"
APP_TIME_FORMAT="24h"
BACKUP_RETENTION="7"
BACKUP_COMPRESSION="gzip"

manager_preferences_valid_path() {
	local value="$1" segment
	local -a _path_segments=()
	[[ "$value" == /* && "$value" != "/" && "$value" != */ &&
		"$value" =~ ^/[A-Za-z0-9._/-]+$ && "$value" != *"//"* ]] || return 1
	IFS='/' read -r -a _path_segments <<<"${value#/}"
	for segment in "${_path_segments[@]}"; do
		[[ -n "$segment" && "$segment" != "." && "$segment" != ".." ]] || return 1
	done
}

manager_preferences_valid_xray_bin() {
	local value="$1"
	manager_preferences_valid_path "$value" &&
		[[ "$value" == /usr/local/bin/xray || "$value" =~ ^/opt/[A-Za-z0-9._-]+/bin/xray$ ]]
}

manager_preferences_valid_xray_data() {
	local value="$1"
	manager_preferences_valid_path "$value" &&
		[[ "$value" == /usr/local/share/xray || "$value" =~ ^/opt/[A-Za-z0-9._-]+/share$ ]]
}

manager_preferences_valid_xray_config_dir() {
	local value="$1"
	manager_preferences_valid_path "$value" &&
		[[ "$value" == /etc/xray || "$value" =~ ^/etc/xray-[A-Za-z0-9._-]+$ ]]
}

manager_preferences_valid_backup_dir() {
	local value="$1"
	manager_preferences_valid_path "$value" &&
		[[ "$value" == /var/backups/xray-manager || "$value" =~ ^/var/backups/xray-manager-[A-Za-z0-9._-]+$ ]]
}

manager_preferences_valid_config_file() {
	local value="$1" directory="$2"
	manager_preferences_valid_path "$value" &&
		[[ "$value" == "$directory/config.json" ]]
}

manager_preferences_path_has_symlink_component() {
	local value="$1" current="" segment
	local -a segments=()
	IFS='/' read -r -a segments <<<"${value#/}"
	for segment in "${segments[@]}"; do
		current+="/$segment"
		[[ ! -L "$current" ]] || return 0
	done
	return 1
}

manager_preferences_routes_valid() {
	manager_preferences_valid_xray_bin "$XRAY_BIN_PATH" &&
		manager_preferences_valid_xray_data "$XRAY_DATA_DIR" &&
		manager_preferences_valid_xray_config_dir "$XRAY_CONFIG_DIR" &&
		manager_preferences_valid_config_file "$XRAY_CONFIG_FILE" "$XRAY_CONFIG_DIR" &&
		manager_preferences_valid_backup_dir "$XRAY_MANAGER_BACKUP_DIR" &&
		! manager_preferences_path_has_symlink_component "$XRAY_BIN_PATH" &&
		! manager_preferences_path_has_symlink_component "$XRAY_DATA_DIR" &&
		! manager_preferences_path_has_symlink_component "$XRAY_CONFIG_DIR" &&
		! manager_preferences_path_has_symlink_component "$XRAY_CONFIG_FILE" &&
		! manager_preferences_path_has_symlink_component "$XRAY_MANAGER_BACKUP_DIR" &&
		[[ "$XRAY_BIN_PATH" != "$XRAY_DATA_DIR/"* ]] &&
		[[ "$XRAY_DATA_DIR" != "$XRAY_BIN_PATH/"* ]] &&
		[[ "$XRAY_CONFIG_DIR" != "$XRAY_DATA_DIR" && "$XRAY_CONFIG_DIR" != "$XRAY_DATA_DIR/"* ]] &&
		[[ "$XRAY_DATA_DIR" != "$XRAY_CONFIG_DIR/"* ]] &&
		[[ "$XRAY_MANAGER_BACKUP_DIR" != "$XRAY_DATA_DIR" && "$XRAY_MANAGER_BACKUP_DIR" != "$XRAY_DATA_DIR/"* ]] &&
		[[ "$XRAY_MANAGER_BACKUP_DIR" != "$XRAY_CONFIG_DIR" && "$XRAY_MANAGER_BACKUP_DIR" != "$XRAY_CONFIG_DIR/"* ]]
}

manager_preferences_load_file() {
	local key value directory
	directory="$(dirname "$MANAGER_PREFERENCES_FILE")"
	[[ -d "$directory" && ! -L "$directory" ]] || return 0
	[[ "$(stat -c '%u:%a' "$directory" 2>/dev/null)" == 0:700 ]] || return 0
	[[ -f "$MANAGER_PREFERENCES_FILE" && ! -L "$MANAGER_PREFERENCES_FILE" ]] || return 0
	[[ "$(stat -c '%u' "$MANAGER_PREFERENCES_FILE" 2>/dev/null)" == 0 ]] || return 0
	[[ "$(stat -c '%a' "$MANAGER_PREFERENCES_FILE" 2>/dev/null)" == 600 ]] || return 0
	while IFS='=' read -r key value || [[ -n "$key" ]]; do
		case "$key" in
		XRAY_BIN_PATH)
			manager_preferences_valid_xray_bin "$value" && XRAY_BIN_PATH="$value"
			;;
		XRAY_DATA_DIR)
			manager_preferences_valid_xray_data "$value" && XRAY_DATA_DIR="$value"
			;;
		XRAY_CONFIG_DIR)
			manager_preferences_valid_xray_config_dir "$value" && XRAY_CONFIG_DIR="$value"
			;;
		XRAY_CONFIG_FILE)
			manager_preferences_valid_config_file "$value" "$XRAY_CONFIG_DIR" && XRAY_CONFIG_FILE="$value"
			;;
		XRAY_MANAGER_BACKUP_DIR)
			manager_preferences_valid_backup_dir "$value" && XRAY_MANAGER_BACKUP_DIR="$value"
			;;
		APP_EDITOR)
			case "$value" in nano | vim | vi | mcedit | micro)
				command -v "$value" >/dev/null 2>&1 && APP_EDITOR="$value"
				;;
			esac
			;;
		APP_THEME)
			case "$value" in cyan | green | blue | magenta | none) APP_THEME="$value" ;; esac
			;;
		APP_LANGUAGE)
			[[ "$value" == es ]] && APP_LANGUAGE="$value"
			;;
		APP_TIMEZONE)
			if [[ "$value" != *".."* && -f "/usr/share/zoneinfo/$value" ]]; then APP_TIMEZONE="$value"; fi
			;;
		APP_DATE_FORMAT)
			case "$value" in dmy | ymd) APP_DATE_FORMAT="$value" ;; esac
			;;
		APP_TIME_FORMAT)
			case "$value" in 24h | 12h) APP_TIME_FORMAT="$value" ;; esac
			;;
		BACKUP_RETENTION)
			[[ "$value" =~ ^([1-9]|[1-9][0-9]|100)$ ]] && BACKUP_RETENTION="$value"
			;;
		BACKUP_COMPRESSION)
			[[ "$value" == gzip ]] && BACKUP_COMPRESSION="$value"
			;;
		esac
	done <"$MANAGER_PREFERENCES_FILE"
	# El archivo no puede dejar rutas internas incoherentes.
	if ! manager_preferences_routes_valid; then
		XRAY_BIN_PATH="/usr/local/bin/xray"
		XRAY_DATA_DIR="/usr/local/share/xray"
		XRAY_CONFIG_DIR="/etc/xray"
		XRAY_CONFIG_FILE="/etc/xray/config.json"
		XRAY_MANAGER_BACKUP_DIR="/var/backups/xray-manager"
	fi
	XRAY_ADMIN_BIN="$XRAY_BIN_PATH"
	XRAY_ADMIN_DATA="$XRAY_DATA_DIR"
	XRAY_ADMIN_BACKUPS="$XRAY_MANAGER_BACKUP_DIR/xray-core"
	if [[ -n "$APP_EDITOR" ]]; then
		export EDITOR="$APP_EDITOR" VISUAL="$APP_EDITOR"
	fi
}

manager_preferences_load_file
