#!/usr/bin/env bash
# Desinstalación centralizada. Solo elimina rutas explícitamente inventariadas.
# El respaldo previo se verifica localmente y puede exportarse por SSH/SCP a otro host.
UNINSTALL_LOCK="${XRAY_MANAGER_UNINSTALL_LOCK:-/run/lock/xray-manager-uninstall.lock}"
UNINSTALL_DATA_LOCK="${XRAY_MANAGER_INTEGRITY_LOCK:-/run/xray-manager/integrity.lock}"
UNINSTALL_XRAY_LOCK="${XRAY_ADMIN_LOCK:-/run/lock/xray-manager-xray-admin.lock}"
UNINSTALL_BACKUP_STAGING_DIR="${UNINSTALL_BACKUP_STAGING_DIR:-/var/backups}"
# shellcheck disable=SC1091
. "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../lib" && pwd)/operation_lock.sh"

uninstall_release_operation_locks() {
	manager_lock_release "$4"
	manager_lock_release "$3"
	manager_lock_release "$2"
	manager_lock_release "$1"
}

uninstall_service_guard() {
	local scope="${1:-both}" unit
	if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet xray.service 2>/dev/null; then
		printf 'Xray está activo. Detén y revisa el servicio por separado antes de desinstalar.\n' >&2
		return 1
	fi
	if command -v pgrep >/dev/null 2>&1 && pgrep -x xray >/dev/null 2>&1; then
		printf 'Se detectó un proceso Xray activo fuera de la comprobación de systemd. La desinstalación se bloquea.\n' >&2
		return 1
	fi
	# Manager-only preserves the Xray binary and unit; removing Xray-core
	# while its unit remains would leave an orphaned systemd unit.
	case "$scope" in
	active | manager) return 0 ;;
	xray | both) ;;
	*)
		printf 'Alcance de desinstalación no válido para la protección del servicio.\n' >&2
		return 1
		;;
	esac
	for unit in xray.service xray@.service; do
		if command -v systemctl >/dev/null 2>&1 &&
			systemctl list-unit-files "$unit" --no-legend 2>/dev/null | grep -q "^$unit"; then
			printf 'Se detectó la unidad systemd %s. No se eliminará Xray-core porque este flujo no modifica ni elimina unidades; usa el alcance Manager si solo deseas retirar el administrador.\n' "$unit" >&2
			return 1
		fi
	done
	return 0
}

uninstall_make_backup() {
	local archive="$1"
	shift
	local -a paths=("$@") relative=()
	local path
	(("${#paths[@]}" > 0)) || return 1
	for path in "${paths[@]}"; do
		[[ "$path" == /* && "$path" != "/" && (-e "$path" || -L "$path") ]] || return 1
		relative+=("${path#/}")
	done
	install -d -m 700 "$(dirname "$archive")"
	tar -czpf "$archive" -C / "${relative[@]}" || return 1
	tar -tzf "$archive" >/dev/null || return 1
	gzip -t "$archive" || return 1
	chmod 600 "$archive"
}

uninstall_export_remote() {
	local archive="$1" target="$2" userhost remote_dir remote_file local_hash remote_hash
	if ! command -v scp >/dev/null 2>&1 || ! command -v ssh >/dev/null 2>&1; then
		printf 'Se requieren ssh y scp para exportar el respaldo fuera del servidor.\n' >&2
		return 1
	fi
	if [[ ! "$target" =~ ^([A-Za-z0-9._-]+@[A-Za-z0-9.-]+):(/[A-Za-z0-9._/-]+)$ ]]; then
		printf 'Destino remoto inválido. Usa usuario@host:/directorio sin espacios ni segmentos ..\n' >&2
		return 1
	fi
	userhost="${BASH_REMATCH[1]}"
	remote_dir="${BASH_REMATCH[2]}"
	[[ "$remote_dir" != *".."* && "$remote_dir" != *"//"* ]] || {
		printf 'La ruta remota contiene segmentos no permitidos.\n' >&2
		return 1
	}
	remote_file="${remote_dir%/}/$(basename "$archive")"
	printf 'Copiando respaldo al host remoto %s...\n' "$userhost"
	if ! scp -p -o BatchMode=yes -o StrictHostKeyChecking=yes "$archive" "$userhost:$remote_file"; then
		printf 'Falló SCP. Comprueba la clave SSH, known_hosts y permisos remotos.\n' >&2
		return 1
	fi
	local_hash="$(sha256sum "$archive" | awk '{print $1}')"
	remote_hash="$(ssh -o BatchMode=yes -o StrictHostKeyChecking=yes "$userhost" "sha256sum -- '$remote_file'" 2>/dev/null | awk 'NR==1 {print $1}')" || return 1
	[[ "$local_hash" =~ ^[a-f0-9]{64}$ && "$remote_hash" == "$local_hash" ]] || {
		printf 'La verificación SHA-256 de la copia remota falló.\n' >&2
		return 1
	}
	printf 'Exportación remota verificada por SHA-256: %s:%s\n' "$userhost" "$remote_file"
}

uninstall_menu_action() {
	local scope policy category selected='' path backup_choice export_target export_status="No solicitada"
	local backup_dir archive checksum certificate_deletion=0
	local lifecycle_fd fd data_fd xray_fd
	local -a paths=() selected_categories=() existing=()
	local -A seen_paths=()
	if [[ "$EUID" -ne 0 ]]; then
		printf '\nEsta operación requiere root.\n'
		ui_pause
		return 1
	fi
	if ! command -v tar >/dev/null 2>&1 || ! command -v sha256sum >/dev/null 2>&1 || ! command -v flock >/dev/null 2>&1; then
		printf '\nFaltan herramientas requeridas (tar, sha256sum o flock).\n'
		ui_pause
		return 1
	fi
	if ! uninstall_service_guard active; then
		ui_pause
		return 1
	fi

	if [[ "${1:-}" == xray ]]; then
		scope=xray
		printf '\nAlcance preseleccionado: solo Xray-core.\n'
	else
		ui_clear
		ui_title "DESINSTALACIÓN DE COMPONENTES"
		printf '\n  [1] Solo Xray-core\n  [2] Solo Xray Manager\n  [3] Ambos componentes\n  [0] Cancelar\n'
		ui_read_option "Alcance: " scope || return 0
		case "$scope" in
		1) scope=xray ;;
		2) scope=manager ;;
		3) scope=both ;;
		0) return 0 ;;
		*)
			printf 'Opción no válida.\n'
			ui_pause
			return 1
			;;
		esac
	fi
	if ! uninstall_service_guard "$scope"; then
		ui_pause
		return 1
	fi

	printf '\n  [1] Conservar todos los datos\n  [2] Eliminar todos los datos\n  [3] Seleccionar categorías\n'
	ui_read_option "Política de datos: " policy || return 0
	case "$policy" in
	1) policy=keep ;;
	2) policy=all ;;
	3)
		policy=selected
		printf '\nCategorías: xray-config, profiles, users, connections, domains, certificates, backups, preferences, logs\n'
		printf 'Introduce identificadores separados por espacios o comas.\n'
		IFS= read -r selected || return 0
		IFS=', ' read -r -a selected_categories <<<"$selected"
		;;
	*)
		printf 'Opción no válida.\n'
		ui_pause
		return 1
		;;
	esac

	# El componente seleccionado siempre se desinstala; la política gobierna sus datos.
	case "$scope" in
	xray) paths+=("$XRAY_ADMIN_BIN" "$XRAY_ADMIN_DATA") ;;
	manager) paths+=("$APP_ROOT") ;;
	both) paths+=("$XRAY_ADMIN_BIN" "$XRAY_ADMIN_DATA" "$APP_ROOT") ;;
	esac

	if [[ "$policy" == selected ]]; then
		for category in "${selected_categories[@]}"; do
			case "$category" in
			xray-config)
				[[ "$scope" != manager ]] || {
					printf 'La categoría xray-config no aplica al alcance manager.\n'
					ui_pause
					return 1
				}
				paths+=("$XRAY_CONFIG_DIR")
				;;
			users)
				[[ "$scope" != xray ]] || {
					printf 'La categoría users no aplica al alcance xray.\n'
					ui_pause
					return 1
				}
				paths+=("$XRAY_MANAGER_USERS_DIR")
				;;
			connections)
				[[ "$scope" != xray ]] || {
					printf 'La categoría connections no aplica al alcance xray.\n'
					ui_pause
					return 1
				}
				paths+=("$XRAY_MANAGER_CONNECTIONS_DIR")
				;;
			backups)
				if [[ "$scope" == xray ]]; then
					paths+=("$XRAY_MANAGER_BACKUP_DIR/xray-core")
				else
					paths+=("$XRAY_MANAGER_BACKUP_DIR")
				fi
				;;
			preferences | profiles | domains | certificates | logs)
				[[ "$scope" != xray ]] || {
					printf 'La categoría %s no aplica al alcance xray.\n' "$category"
					ui_pause
					return 1
				}
				case "$category" in
				preferences) paths+=("$XRAY_MANAGER_CONFIG_DIR") ;;
				profiles) paths+=("$XRAY_MANAGER_PROFILES_DIR") ;;
				domains) paths+=("$XRAY_MANAGER_DOMAINS_DIR") ;;
				certificates)
					paths+=("$XRAY_MANAGER_CERTIFICATES_DIR")
					certificate_deletion=1
					;;
				logs) paths+=("$XRAY_MANAGER_LOG_DIR" "$XRAY_MANAGER_HISTORY_DIR") ;;
				esac
				;;
			'') ;;
			*)
				printf 'Categoría desconocida: %s. Cancelando.\n' "$category"
				ui_pause
				return 1
				;;
			esac
		done
	fi
	if [[ "$policy" == all ]]; then
		case "$scope" in
		xray)
			paths+=("$XRAY_CONFIG_DIR" "$XRAY_MANAGER_BACKUP_DIR/xray-core")
			;;
		manager)
			paths+=("$XRAY_MANAGER_CONFIG_DIR" "$XRAY_MANAGER_DATA_DIR" "$XRAY_MANAGER_LOG_DIR" "$XRAY_MANAGER_CACHE_DIR" "$XRAY_MANAGER_BACKUP_DIR" "$XRAY_MANAGER_STATE_DIR")
			certificate_deletion=1
			;;
		both)
			paths+=("$XRAY_CONFIG_DIR" "$XRAY_MANAGER_CONFIG_DIR" "$XRAY_MANAGER_DATA_DIR" "$XRAY_MANAGER_LOG_DIR" "$XRAY_MANAGER_CACHE_DIR" "$XRAY_MANAGER_BACKUP_DIR" "$XRAY_MANAGER_STATE_DIR")
			certificate_deletion=1
			;;
		esac
	fi

	for path in "${paths[@]}"; do
		if [[ -n "$path" && (-e "$path" || -L "$path") && -z "${seen_paths[$path]:-}" ]]; then
			existing+=("$path")
			seen_paths[$path]=1
		fi
	done
	paths=("${existing[@]}")
	if ! uninstall_paths_are_allowed "${paths[@]}"; then
		ui_pause
		return 1
	fi

	if (("${#paths[@]}" == 0)); then
		printf '\nNo se encontraron rutas existentes para el alcance elegido. No hay nada que borrar.\n'
		ui_pause
		return 0
	fi

	# Adquirir todos los bloqueos antes de crear el respaldo. Así el snapshot
	# y la eliminación representan el mismo estado y no compiten con escrituras.
	if ! manager_lock_acquire "${XRAY_MANAGER_LIFECYCLE_LOCK:-/run/lock/xray-manager-lifecycle.lock}" lifecycle_fd; then
		printf 'Hay otra operación de ciclo de vida del Manager en curso.\n' >&2
		ui_pause
		return 1
	fi
	if ! manager_lock_acquire "$UNINSTALL_LOCK" fd; then
		manager_lock_release "$lifecycle_fd"
		printf 'Ya hay otra operación de desinstalación en curso.\n'
		ui_pause
		return 1
	fi
	if ! manager_lock_acquire "$UNINSTALL_DATA_LOCK" data_fd; then
		uninstall_release_operation_locks "$lifecycle_fd" "$fd" '' ''
		printf 'Hay una operación de usuarios o conexiones en curso. La desinstalación se cancela.\n'
		ui_pause
		return 1
	fi
	if ! manager_lock_acquire "$UNINSTALL_XRAY_LOCK" xray_fd; then
		uninstall_release_operation_locks "$lifecycle_fd" "$fd" "$data_fd" ''
		printf 'Hay una operación de administración de Xray-core en curso. La desinstalación se cancela.\n'
		ui_pause
		return 1
	fi
	trap 'uninstall_release_operation_locks "$lifecycle_fd" "$fd" "$data_fd" "$xray_fd"; trap - RETURN' RETURN
	if ! uninstall_service_guard "$scope" || ! uninstall_paths_are_allowed "${paths[@]}"; then
		printf 'El estado del servicio o el inventario de rutas cambió; se cancela la desinstalación.\n' >&2
		ui_pause
		return 1
	fi

	if ((certificate_deletion)); then
		printf '\nADVERTENCIA: la selección incluye certificados y claves privadas. Su eliminación es irreversible y puede afectar otros servicios que los utilicen.\n'
		if ! ui_confirm "¿Confirmas que deseas eliminar también certificados y claves privadas?"; then
			printf 'Operación cancelada.\n'
			ui_pause
			return 0
		fi
	fi

	printf '\nAVISO: las rutas seleccionadas pueden contener credenciales, claves privadas, certificados y configuración sensible.\n'
	printf 'Los respaldos locales se crean con permisos restrictivos (600); conserva y transporta el archivo de forma segura.\n'
	backup_choice=n
	if ui_confirm "¿Deseas crear un respaldo previo de las rutas seleccionadas?"; then backup_choice=y; fi
	if uninstall_path_has_symlink_component "$UNINSTALL_BACKUP_STAGING_DIR" ||
		[[ ! -d "$(dirname "$UNINSTALL_BACKUP_STAGING_DIR")" ]]; then
		printf 'El directorio de staging de respaldos no es seguro o su padre no existe.\n' >&2
		return 1
	fi
	install -d -m 700 "$UNINSTALL_BACKUP_STAGING_DIR" || return 1
	backup_dir="$(mktemp -d "$UNINSTALL_BACKUP_STAGING_DIR/xray-manager-uninstall.XXXXXX")" || return 1
	archive="$backup_dir/pre-uninstall.tar.gz"
	if [[ "$backup_choice" == y ]]; then
		if ! uninstall_make_backup "$archive" "${paths[@]}"; then
			printf '\nFalló la creación o verificación del respaldo. Se cancela la desinstalación.\n'
			rm -rf -- "$backup_dir"
			ui_pause
			return 1
		fi
		checksum="$(sha256sum "$archive")"
		printf '\nRespaldo verificado: %s\n%s\n' "$archive" "$checksum"
		if ui_confirm "¿Deseas exportar el respaldo a otro servidor por SSH/SCP?"; then
			printf 'Destino remoto (usuario@host:/directorio): '
			IFS= read -r export_target || {
				rm -rf -- "$backup_dir"
				return 1
			}
			if ! uninstall_export_remote "$archive" "$export_target"; then
				printf 'No se confirmó una copia externa válida. Se cancela la desinstalación.\n'
				rm -rf -- "$backup_dir"
				ui_pause
				return 1
			fi
			export_status="Verificada por SHA-256 en $export_target"
		fi
	fi

	printf '\nRESUMEN PREVIO A LA DESINSTALACIÓN\n'
	printf 'Alcance: %s\nPolítica: %s\n' "$scope" "$policy"
	printf 'Categorías de datos:\n'
	case "$policy" in
	keep)
		printf '  Se conservan todos los datos persistentes; solo se retira el componente del alcance elegido.\n'
		;;
	all)
		printf '  Se eliminan todos los datos del alcance elegido; los componentes fuera de ese alcance se conservan.\n'
		;;
	selected)
		printf '  Seleccionadas para eliminar: %s\n' "${selected_categories[*]}"
		printf '  Las demás categorías de datos se conservan.\n'
		;;
	esac
	printf 'Rutas que se eliminarán:\n'
	for path in "${paths[@]}"; do printf '  - %s\n' "$path"; done
	if [[ "$policy" == all ]]; then
		printf 'Se eliminarán también los respaldos locales existentes y el respaldo temporal de esta operación.\n'
		printf 'Solo sobrevivirá una copia que haya sido exportada y verificada en otro servidor.\n'
	elif [[ "$backup_choice" == y ]]; then
		printf 'Respaldo temporal verificado: %s\n' "$archive"
	else
		printf 'Respaldo previo: no creado.\n'
	fi
	printf 'Exportación externa: %s\n' "$export_status"
	printf 'Las unidades systemd no se eliminan ni modifican desde este flujo. Si existe una unidad Xray, la operación se bloquea.\n'
	printf 'ADVERTENCIA: los respaldos de Etapa 5 no incluyen ni permiten recuperar estos datos:\n'
	printf '  - Historial de versiones/modificaciones de perfiles\n'
	printf '  - Historial de validaciones\n'
	printf '  - Informes de restauración\n'
	printf '  - Registros técnicos y logs\n'
	printf '\n'
	if ! ui_confirm "CONFIRMACIÓN FINAL: ¿ejecutar esta operación irreversible?"; then
		printf 'Operación cancelada. No se eliminó ninguna ruta.\n'
		rm -rf -- "$backup_dir"
		ui_pause
		return 0
	fi

	# Los bloqueos lifecycle/uninstall/data/Xray ya están adquiridos desde antes del respaldo.
	local deletion_failed=0
	for path in "${paths[@]}"; do
		if [[ -e "$path" || -L "$path" ]]; then
			if ! rm -rf --one-file-system -- "$path"; then
				printf 'ERROR: no se pudo eliminar %s. Se detuvo el borrado; revisa el estado parcial.\n' "$path" >&2
				deletion_failed=1
				break
			fi
		fi
	done
	if ((deletion_failed)); then
		if [[ "$backup_choice" == y ]]; then
			printf 'El respaldo se conserva para recuperación: %s\n' "$archive"
		else
			rm -rf -- "$backup_dir"
			printf 'No se creó respaldo previo; la operación quedó parcialmente aplicada.\n'
		fi
		ui_pause
		return 1
	fi
	if [[ "$policy" == all || "$backup_choice" == n ]]; then
		rm -rf -- "$backup_dir"
	else
		printf 'Respaldo temporal conservado en: %s\n' "$backup_dir"
	fi
	printf '\nDesinstalación terminada para las rutas seleccionadas.\n'
	ui_pause
}

# Verifica que cada destino coincida exactamente con una ruta del inventario.
uninstall_path_has_symlink_component() {
	local path="$1" current="" segment
	local -a segments=()
	[[ "$path" == /* && "$path" != "/" && "$path" != */ && "$path" != *"//"* ]] || return 0
	IFS="/" read -r -a segments <<<"${path#/}"
	for segment in "${segments[@]}"; do
		[[ -n "$segment" && "$segment" != "." && "$segment" != ".." ]] || return 0
		current+="/$segment"
		[[ ! -L "$current" ]] || return 0
	done
	return 1
}

uninstall_path_is_allowed() {
	local path="$1"
	case "$path" in
	"$XRAY_ADMIN_BIN" | "$XRAY_ADMIN_DATA" | "$XRAY_CONFIG_DIR" | \
		"$XRAY_MANAGER_CONFIG_DIR" | "$APP_ROOT" | "$XRAY_MANAGER_DATA_DIR" | \
		"$XRAY_MANAGER_USERS_DIR" | "$XRAY_MANAGER_CONNECTIONS_DIR" | \
		"$XRAY_MANAGER_PROFILES_DIR" | "$XRAY_MANAGER_DOMAINS_DIR" | \
		"$XRAY_MANAGER_CERTIFICATES_DIR" | "$XRAY_MANAGER_HISTORY_DIR" | \
		"$XRAY_MANAGER_STATE_DIR" | "$XRAY_MANAGER_LOG_DIR" | \
		"$XRAY_MANAGER_CACHE_DIR" | "$XRAY_MANAGER_BACKUP_DIR" | \
		"$XRAY_MANAGER_BACKUP_DIR/xray-core")
		return 0
		;;
	*) return 1 ;;
	esac
}

uninstall_paths_are_allowed() {
	local path
	for path in "$@"; do
		uninstall_path_is_allowed "$path" || {
			printf 'Ruta fuera de la lista permitida: %s. Se aborta.\n' "$path" >&2
			return 1
		}
		if uninstall_path_has_symlink_component "$path"; then
			printf 'La ruta contiene un enlace simbólico o un componente no válido: %s. Se aborta.\n' "$path" >&2
			return 1
		fi
	done
}
