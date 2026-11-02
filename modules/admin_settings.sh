#!/usr/bin/env bash
# shellcheck disable=SC2034
# Preferencias persistentes de la interfaz y rutas administradas.
# shellcheck disable=SC1091
. "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../lib" && pwd)/operation_lock.sh"

manager_preferences_directory_is_safe() {
	local directory="$1"
	[[ "$directory" == /etc/xray-manager && "$MANAGER_PREFERENCES_FILE" == "$directory/preferences.conf" && ! -L "$directory" ]]
}

manager_settings_save_unlocked() {
	local directory temporary
	directory="$(dirname "$MANAGER_PREFERENCES_FILE")"
	manager_preferences_directory_is_safe "$directory" || return 1
	install -d -o root -g root -m 700 "$directory" || return 1
	chown root:root "$directory" && chmod 700 "$directory" || return 1
	temporary="$(mktemp "$directory/.preferences.XXXXXX")" || return 1
	{
		printf 'XRAY_BIN_PATH=%s\n' "$XRAY_BIN_PATH"
		printf 'XRAY_DATA_DIR=%s\n' "$XRAY_DATA_DIR"
		printf 'XRAY_CONFIG_DIR=%s\n' "$XRAY_CONFIG_DIR"
		printf 'XRAY_CONFIG_FILE=%s\n' "$XRAY_CONFIG_FILE"
		printf 'XRAY_MANAGER_BACKUP_DIR=%s\n' "$XRAY_MANAGER_BACKUP_DIR"
		printf 'APP_EDITOR=%s\n' "$APP_EDITOR"
		printf 'APP_THEME=%s\n' "$APP_THEME"
		printf 'APP_LANGUAGE=%s\n' "$APP_LANGUAGE"
		printf 'APP_TIMEZONE=%s\n' "$APP_TIMEZONE"
		printf 'APP_DATE_FORMAT=%s\n' "$APP_DATE_FORMAT"
		printf 'APP_TIME_FORMAT=%s\n' "$APP_TIME_FORMAT"
		printf 'BACKUP_RETENTION=%s\n' "$BACKUP_RETENTION"
		printf 'BACKUP_COMPRESSION=%s\n' "$BACKUP_COMPRESSION"
	} >"$temporary" || {
		rm -f -- "$temporary"
		return 1
	}
	if ! chmod 600 "$temporary" ||
		! chown root:root "$temporary" ||
		! mv -f -- "$temporary" "$MANAGER_PREFERENCES_FILE"; then
		rm -f -- "$temporary"
		return 1
	fi
	if [[ -n "$APP_EDITOR" ]]; then
		export EDITOR="$APP_EDITOR" VISUAL="$APP_EDITOR"
	else
		unset EDITOR VISUAL
	fi
}

manager_settings_save() {
	local lifecycle_fd result
	if ! manager_lock_acquire "${XRAY_MANAGER_LIFECYCLE_LOCK:-/run/lock/xray-manager-lifecycle.lock}" lifecycle_fd; then
		printf 'Hay otra operación de ciclo de vida del Manager en curso; no se guardaron las preferencias.\n' >&2
		return 1
	fi
	if manager_settings_save_unlocked; then result=0; else result=$?; fi
	manager_lock_release "$lifecycle_fd"
	return "$result"
}

manager_settings_path_input() {
	local prompt="$1" current="$2" destination="$3" path_answer
	ui_read_option "$prompt [$current]: " path_answer || return 1
	[[ -n "$path_answer" ]] || path_answer="$current"
	printf -v "$destination" '%s' "$path_answer"
}

manager_settings_paths_menu() {
	local new_bin new_data new_config_dir new_config_file
	manager_settings_path_input "Ruta del binario Xray" "$XRAY_BIN_PATH" new_bin || return 0
	manager_settings_path_input "Directorio de datos Xray" "$XRAY_DATA_DIR" new_data || return 0
	manager_settings_path_input "Directorio de configuración Xray" "$XRAY_CONFIG_DIR" new_config_dir || return 0
	manager_settings_path_input "Archivo principal de configuración" "$XRAY_CONFIG_FILE" new_config_file || return 0
	if ! manager_preferences_valid_xray_bin "$new_bin" ||
		! manager_preferences_valid_xray_data "$new_data" ||
		! manager_preferences_valid_xray_config_dir "$new_config_dir" ||
		! manager_preferences_valid_config_file "$new_config_file" "$new_config_dir" ||
		manager_preferences_path_has_symlink_component "$new_config_file" ||
		manager_preferences_path_has_symlink_component "$new_bin" ||
		manager_preferences_path_has_symlink_component "$new_data" ||
		manager_preferences_path_has_symlink_component "$new_config_dir"; then
		printf 'Ruta no permitida. Usa ubicaciones dedicadas para Xray; no se aceptan rutas de sistema generales.\n'
		ui_pause
		return 1
	fi
	if [[ "$new_bin" == "$new_data/"* || "$new_data" == "$new_bin/"* ||
		"$new_data" == "$new_config_dir" || "$new_config_dir" == "$new_data/"* ||
		"$new_data" == "$new_config_dir/"* ]]; then
		printf 'Las rutas del binario, datos y configuración no pueden solaparse.\n'
		ui_pause
		return 1
	fi
	printf '\nNuevas rutas propuestas:\n'
	printf '  Binario:       %s\n  Datos:         %s\n  Configuración: %s\n  Archivo:       %s\n' "$new_bin" "$new_data" "$new_config_dir" "$new_config_file"
	printf 'El cambio modifica las rutas que utilizarán las operaciones futuras; no mueve archivos existentes.\n'
	if ! ui_confirm "¿Guardar estas rutas?"; then
		printf 'Cambios cancelados.\n'
		ui_pause
		return 0
	fi
	local old_bin="$XRAY_BIN_PATH" old_data="$XRAY_DATA_DIR"
	local old_config_dir="$XRAY_CONFIG_DIR" old_config_file="$XRAY_CONFIG_FILE"
	XRAY_BIN_PATH="$new_bin"
	XRAY_DATA_DIR="$new_data"
	XRAY_CONFIG_DIR="$new_config_dir"
	XRAY_CONFIG_FILE="$new_config_file"
	XRAY_ADMIN_BIN="$new_bin"
	XRAY_ADMIN_DATA="$new_data"
	if ! manager_settings_save; then
		XRAY_BIN_PATH="$old_bin"
		XRAY_DATA_DIR="$old_data"
		XRAY_CONFIG_DIR="$old_config_dir"
		XRAY_CONFIG_FILE="$old_config_file"
		XRAY_ADMIN_BIN="$old_bin"
		XRAY_ADMIN_DATA="$old_data"
		printf 'No se pudieron guardar las preferencias. Se restauró la configuración en memoria.\n'
		ui_pause
		return 1
	fi
	printf 'Rutas guardadas. Los archivos existentes no se han movido.\n'
	ui_pause
}

manager_settings_editor_menu() {
	local editor option index=1
	local -a editors=()
	ui_clear
	ui_title "SELECCIONAR EDITOR DE TEXTO"
	for editor in nano vim vi mcedit micro; do
		if command -v "$editor" >/dev/null 2>&1; then
			editors+=("$editor")
		fi
	done
	if (("${#editors[@]}" == 0)); then
		printf 'No se detectaron editores compatibles instalados.\n'
		ui_pause
		return 0
	fi
	printf 'Editor actual: %s\n\n' "${APP_EDITOR:-Automático/no definido}"
	for editor in "${editors[@]}"; do
		printf '  [%s] %s\n' "$index" "$editor"
		((index += 1))
	done
	printf '  [0] Volver\n'
	ui_read_option "Selecciona el editor: " option || return 0
	[[ "$option" =~ ^[0-9]+$ ]] || {
		printf 'Selección no válida.\n'
		ui_pause
		return 1
	}
	((option == 0)) && return 0
	((option >= 1 && option <= ${#editors[@]})) || {
		printf 'Selección fuera de rango.\n'
		ui_pause
		return 1
	}
	local previous="$APP_EDITOR"
	APP_EDITOR="${editors[option - 1]}"
	if manager_settings_save; then
		printf 'Editor guardado: %s\n' "$APP_EDITOR"
	else
		APP_EDITOR="$previous"
		printf 'No se pudo guardar el editor; se conserva la preferencia anterior.\n'
		return 1
	fi
	ui_pause
}

manager_settings_theme_menu() {
	local option theme
	ui_clear
	ui_title "COLORES DEL MENÚ"
	printf 'Tema actual: %s\n\n' "$APP_THEME"
	printf '  [1] Cian\n  [2] Verde\n  [3] Azul\n  [4] Magenta\n  [5] Sin color\n  [0] Volver\n'
	ui_read_option "Selecciona el tema: " option || return 0
	case "$option" in
	1) theme=cyan ;;
	2) theme=green ;;
	3) theme=blue ;;
	4) theme=magenta ;;
	5) theme=none ;;
	0) return 0 ;;
	*)
		printf 'Selección no válida.\n'
		ui_pause
		return 1
		;;
	esac
	local previous="$APP_THEME"
	APP_THEME="$theme"
	if manager_settings_save; then
		printf 'Tema guardado: %s\n' "$APP_THEME"
	else
		APP_THEME="$previous"
		printf 'No se pudo guardar el tema.\n'
	fi
	ui_pause
}

manager_settings_language_date_menu() {
	local option answer timezone date_format time_format
	while true; do
		ui_clear
		ui_title "IDIOMA Y FECHA"
		printf '  Idioma:             Español (único idioma disponible)\n'
		printf '  Zona horaria:       %s\n' "$APP_TIMEZONE"
		printf '  Formato de fecha:   %s\n' "$APP_DATE_FORMAT"
		printf '  Formato de hora:    %s\n' "$APP_TIME_FORMAT"
		printf '\n  [1] Confirmar idioma español\n'
		printf '  [2] Cambiar zona horaria\n'
		printf '  [3] Formato de fecha\n'
		printf '  [4] Formato de hora\n'
		printf '  [0] Volver\n\n'
		ui_read_option "Selecciona una opción: " option || return 0
		case "$option" in
		1)
			local previous="$APP_LANGUAGE"
			APP_LANGUAGE=es
			if manager_settings_save; then
				printf 'Idioma español guardado.\n'
			else
				APP_LANGUAGE="$previous"
				printf 'No se pudo guardar el idioma.\n'
			fi
			ui_pause
			;;
		2)
			ui_read_option "Zona horaria IANA [$APP_TIMEZONE]: " timezone || return 0
			[[ -n "$timezone" ]] || timezone="$APP_TIMEZONE"
			if [[ "$timezone" == *".."* || ! -f "/usr/share/zoneinfo/$timezone" ]]; then
				printf 'Zona horaria no válida o no instalada.\n'
			else
				local previous="$APP_TIMEZONE"
				APP_TIMEZONE="$timezone"
				if manager_settings_save; then printf 'Zona horaria guardada.\n'; else APP_TIMEZONE="$previous"; fi
			fi
			ui_pause
			;;
		3)
			printf '  [1] DD/MM/AAAA\n  [2] AAAA-MM-DD\n'
			ui_read_option "Formato: " answer || return 0
			case "$answer" in 1) date_format=dmy ;; 2) date_format=ymd ;; *) date_format='' ;; esac
			if [[ -n "$date_format" ]]; then
				local previous="$APP_DATE_FORMAT"
				APP_DATE_FORMAT="$date_format"
				if manager_settings_save; then printf 'Formato de fecha guardado.\n'; else APP_DATE_FORMAT="$previous"; fi
			else
				printf 'Selección no válida.\n'
			fi
			ui_pause
			;;
		4)
			printf '  [1] 24 horas\n  [2] 12 horas\n'
			ui_read_option "Formato: " answer || return 0
			case "$answer" in 1) time_format=24h ;; 2) time_format=12h ;; *) time_format='' ;; esac
			if [[ -n "$time_format" ]]; then
				local previous="$APP_TIME_FORMAT"
				APP_TIME_FORMAT="$time_format"
				if manager_settings_save; then printf 'Formato de hora guardado.\n'; else APP_TIME_FORMAT="$previous"; fi
			else
				printf 'Selección no válida.\n'
			fi
			ui_pause
			;;
		0) return 0 ;;
		*)
			printf 'Opción no válida.\n'
			ui_pause
			;;
		esac
	done
}

manager_settings_backup_menu() {
	local option new_dir retention compression
	while true; do
		ui_clear
		ui_title "PREFERENCIAS DE RESPALDOS"
		printf '  Directorio:        %s\n' "$XRAY_MANAGER_BACKUP_DIR"
		printf '  Retención:         %s respaldos/versiones\n' "$BACKUP_RETENTION"
		printf '  Compresión:        %s\n' "$BACKUP_COMPRESSION"
		printf '\n  [1] Cambiar directorio\n'
		printf '  [2] Cambiar retención\n'
		printf '  [3] Seleccionar compresión\n'
		printf '  [0] Volver\n\n'
		ui_read_option "Selecciona una opción: " option || return 0
		case "$option" in
		1)
			manager_settings_path_input "Directorio de respaldos" "$XRAY_MANAGER_BACKUP_DIR" new_dir || return 0
			if ! manager_preferences_valid_backup_dir "$new_dir" ||
				manager_preferences_path_has_symlink_component "$new_dir"; then
				printf 'Ruta inválida o con componentes simbólicos. Usa una ubicación dedicada y segura.\n'
			elif [[ -e "$new_dir" && ! -d "$new_dir" ]]; then
				printf 'La ruta existe y no es un directorio.\n'
			elif [[ ! -d "$(dirname "$new_dir")" ]]; then
				printf 'El directorio padre debe existir.\n'
			else
				local previous="$XRAY_MANAGER_BACKUP_DIR"
				XRAY_MANAGER_BACKUP_DIR="$new_dir"
				XRAY_ADMIN_BACKUPS="$new_dir/xray-core"
				if manager_settings_save; then printf 'Directorio de respaldos guardado. No se han movido archivos.\n'; else
					XRAY_MANAGER_BACKUP_DIR="$previous"
					XRAY_ADMIN_BACKUPS="$previous/xray-core"
				fi
			fi
			ui_pause
			;;
		2)
			ui_read_option "Retención (1-100) [$BACKUP_RETENTION]: " retention || return 0
			[[ -n "$retention" ]] || retention="$BACKUP_RETENTION"
			if [[ "$retention" =~ ^([1-9]|[1-9][0-9]|100)$ ]]; then
				local previous="$BACKUP_RETENTION"
				BACKUP_RETENTION="$retention"
				if manager_settings_save; then printf 'Retención guardada.\n'; else BACKUP_RETENTION="$previous"; fi
			else
				printf 'Valor inválido; usa un entero entre 1 y 100.\n'
			fi
			ui_pause
			;;
		3)
			printf 'Compresión disponible: gzip\n'
			ui_read_option "Selecciona gzip [1] o volver [0]: " compression || return 0
			case "$compression" in
			1)
				local previous="$BACKUP_COMPRESSION"
				BACKUP_COMPRESSION=gzip
				if manager_settings_save; then
					printf 'Compresión gzip guardada.\n'
				else
					BACKUP_COMPRESSION="$previous"
					printf 'No se pudo guardar la compresión.\n'
				fi
				;;
			0) ;;
			*) printf 'Selección no válida.\n' ;;
			esac
			ui_pause
			;;
		0) return 0 ;;
		*)
			printf 'Opción no válida.\n'
			ui_pause
			;;
		esac
	done
}

manager_settings_menu() {
	local option
	while true; do
		ui_clear
		ui_title "CONFIGURACIÓN DEL ADMINISTRADOR"
		printf '\n  [1] Configurar rutas de Xray\n'
		printf '  [2] Seleccionar editor de texto\n'
		printf '  [3] Configurar colores del menú\n'
		printf '  [4] Configurar idioma y fecha\n'
		printf '  [5] Preferencias de respaldos\n'
		printf '  [0] Volver\n\n'
		ui_read_option "Selecciona una opción: " option || return 0
		case "$option" in
		1) manager_settings_paths_menu ;;
		2) manager_settings_editor_menu ;;
		3) manager_settings_theme_menu ;;
		4) manager_settings_language_date_menu ;;
		5) manager_settings_backup_menu ;;
		0) return 0 ;;
		*)
			printf '\nOpción no válida.\n'
			ui_pause
			;;
		esac
	done
}
