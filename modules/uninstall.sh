#!/usr/bin/env bash
# Desinstalación centralizada. Solo elimina rutas explícitamente inventariadas.
UNINSTALL_LOCK="${XRAY_MANAGER_UNINSTALL_LOCK:-/run/lock/xray-manager-uninstall.lock}"

uninstall_service_guard() {
	local unit
	for unit in xray.service xray@.service; do
		if systemctl list-unit-files "$unit" --no-legend 2>/dev/null | grep -q "^$unit"; then
			printf 'Se detectó la unidad systemd %s. La desinstalación automática se bloquea porque su propiedad y configuración no están documentadas.\n' "$unit" >&2
			return 1
		fi
	done
	if systemctl is-active --quiet xray.service 2>/dev/null; then
		printf 'Xray está activo. Detén y revisa el servicio por separado antes de desinstalar.\n' >&2
		return 1
	fi
}

uninstall_make_backup() {
	local archive="$1"
	shift
	local -a paths=("$@") relative=()
	local path
	(("${#paths[@]}" > 0)) || return 1
	for path in "${paths[@]}"; do
		[[ "$path" == /* && (-e "$path" || -L "$path") ]] || return 1
		relative+=("${path#/}")
	done
	install -d -m 700 "$(dirname "$archive")"
	tar -czpf "$archive" -C / "${relative[@]}"
	tar -tzf "$archive" >/dev/null
	gzip -t "$archive"
	chmod 600 "$archive"
}

uninstall_menu_action() {
	local scope policy category selected='' path backup_choice export_path
	local timestamp backup_dir archive checksum''
	local -a paths=()
	local fd
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
	if ! uninstall_service_guard; then
		ui_pause
		return 1
	fi
	ui_clear
	ui_title "DESINSTALACIÓN DE COMPONENTES"
	printf '\n  [1] Solo Xray-core\n  [2] Solo Xray Manager\n  [3] Ambos componentes\n  [0] Cancelar\n'
	ui_read_option "Alcance: " scope
	case "$scope" in 1) scope=xray ;; 2) scope=manager ;; 3) scope=both ;; 0) return 0 ;; *)
		printf 'Opción no válida.\n'
		ui_pause
		return 1
		;;
	esac

	printf '\n  [1] Conservar todos los datos\n  [2] Eliminar todos los datos\n  [3] Seleccionar categorías\n'
	ui_read_option "Política de datos: " policy
	case "$policy" in
	1) policy=keep ;;
	2) policy=all ;;
	3)
		policy=selected
		printf '\nCategorías: config, profiles, users, connections, domains, certificates, backups, preferences, logs\n'
		printf 'Introduce identificadores separados por espacios.\n'
		IFS= read -r selected || return 0
		;;
	*)
		printf 'Opción no válida.\n'
		ui_pause
		return 1
		;;
	esac

	# El componente seleccionado siempre se desinstala; la política solo gobierna sus datos.
	case "$scope" in
	xray) paths+=(/usr/local/bin/xray /usr/local/share/xray) ;;
	manager) paths+=(/opt/xray-manager) ;;
	both) paths+=(/usr/local/bin/xray /usr/local/share/xray /opt/xray-manager) ;;
	esac
	if [[ "$policy" == selected ]]; then
		for category in $selected; do
			case "$category" in
			config) [[ "$scope" != manager ]] && paths+=(/etc/xray) ;;
			users) [[ "$scope" != xray ]] && paths+=(/var/lib/xray-manager/users) ;;
			connections) [[ "$scope" != xray ]] && paths+=(/var/lib/xray-manager/connections) ;;
			backups)
				[[ "$scope" == xray ]] && paths+=(/var/backups/xray-manager/xray-core)
				[[ "$scope" == manager ]] && paths+=(/var/backups/xray-manager)
				[[ "$scope" == both ]] && paths+=(/var/backups/xray-manager)
				;;
			preferences) [[ "$scope" != xray ]] && paths+=(/etc/xray-manager) ;;
			logs)
				[[ "$scope" != xray ]] && paths+=(/var/log/xray-manager)
				;;
			profiles) [[ "$scope" != xray ]] && paths+=(/var/lib/xray-manager/profiles) ;;
			domains) [[ "$scope" != xray ]] && paths+=(/var/lib/xray-manager/domains) ;;
			certificates) [[ "$scope" != xray ]] && paths+=(/var/lib/xray-manager/certificates) ;;
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
		xray) paths+=(/etc/xray /var/backups/xray-manager/xray-core) ;;
		manager) paths+=(/etc/xray-manager /var/lib/xray-manager /var/log/xray-manager /var/cache/xray-manager /var/backups/xray-manager) ;;
		both) paths+=(/etc/xray /etc/xray-manager /var/lib/xray-manager /var/log/xray-manager /var/cache/xray-manager /var/backups/xray-manager) ;;
		esac
	fi
	local -a existing=()
	for path in "${paths[@]}"; do
		[[ -n "$path" && (-e "$path" || -L "$path") ]] && existing+=("$path")
	done
	paths=("${existing[@]}")
	if (("${#paths[@]}" == 0)); then
		printf '\nNo se encontraron rutas existentes para el alcance elegido. No hay nada que borrar.\n'
		ui_pause
		return 0
	fi

	backup_choice=n
	if ui_confirm "¿Deseas crear un respaldo previo de las rutas seleccionadas?"; then backup_choice=y; fi
	timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
	backup_dir="/var/backups/xray-manager-uninstall-$timestamp"
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
		if ui_confirm "¿Deseas exportar el respaldo a otra ubicación del servidor?"; then
			printf 'Ruta absoluta de destino (directorio existente y externo a /var/backups/xray-manager): '
			IFS= read -r export_path || return 1
			if [[ "$export_path" != /* || "$export_path" == /var/backups/xray-manager* || ! -d "$export_path" ]]; then
				printf 'Destino inválido. Debe ser un directorio absoluto externo a /var/backups/xray-manager. Cancelado.\n'
				ui_pause
				return 1
			fi
			install -m 600 "$archive" "$export_path/xray-manager-$timestamp.tar.gz"
			(cd "$export_path" && sha256sum "xray-manager-$timestamp.tar.gz" >"xray-manager-$timestamp.sha256")
			chmod 600 "$export_path/xray-manager-$timestamp.sha256"
			(cd "$export_path" && sha256sum -c "xray-manager-$timestamp.sha256" --status) || {
				printf 'Falló la verificación de exportación. Cancelado.\n'
				ui_pause
				return 1
			}
			printf 'Exportación verificada: %s/xray-manager-%s.tar.gz\n' "$export_path" "$timestamp"
		fi
	fi

	printf '\nRESUMEN PREVIO A LA DESINSTALACIÓN\n'
	printf 'Alcance: %s\nPolítica: %s\n' "$scope" "$policy"
	printf 'Rutas que se eliminarán:\n'
	for path in "${paths[@]}"; do printf '  - %s\n' "$path"; done
	if [[ "$policy" == all ]]; then
		printf 'Se eliminarán también los respaldos existentes y el respaldo local recién creado.\n'
		printf 'Solo sobrevivirá una copia que haya sido exportada y verificada fuera de /var/backups/xray-manager.\n'
	elif [[ "$backup_choice" == y ]]; then
		printf 'Respaldo local verificado: %s\n' "$archive"
	else
		printf 'Respaldo previo: no creado.\n'
	fi
	printf 'Los certificados gestionados se almacenan bajo /var/lib/xray-manager/certificates; las referencias externas no autorizan borrar los archivos originales de otros gestores.\n'
	printf 'Historiales no incluidos en respaldos Etapa 5: versiones/modificaciones de perfiles, validaciones, informes de restauración y registros técnicos.\n'
	printf 'La unidad systemd no se elimina ni modifica desde este flujo.\n'
	printf '\n'
	if ! ui_confirm "CONFIRMACIÓN FINAL: ¿ejecutar esta operación irreversible?"; then
		printf 'Operación cancelada. No se eliminó ninguna ruta.\n'
		ui_pause
		return 0
	fi

	exec {fd}>"$UNINSTALL_LOCK"
	if ! flock -n "$fd"; then
		printf 'Ya hay otra operación de desinstalación en curso.\n'
		ui_pause
		return 1
	fi
	# Comprobar nuevamente cada ruta y eliminar únicamente entradas exactas.
	for path in "${paths[@]}"; do
		case "$path" in
		/usr/local/bin/xray | /usr/local/share/xray | /etc/xray | /etc/xray-manager | /opt/xray-manager | /var/lib/xray-manager | /var/log/xray-manager | /var/cache/xray-manager | /var/backups/xray-manager | /var/backups/xray-manager/xray-core) ;;
		*)
			printf 'Ruta fuera de la lista permitida: %s. Se aborta.\n' "$path"
			flock -u "$fd"
			exec {fd}>&-
			ui_pause
			return 1
			;;
		esac
	done
	for path in "${paths[@]}"; do
		[[ -e "$path" || -L "$path" ]] && rm -rf --one-file-system -- "$path"
	done
	if [[ "$policy" == all && "$backup_choice" == y ]]; then
		rm -rf -- "$backup_dir"
	fi
	flock -u "$fd"
	exec {fd}>&-
	printf '\nDesinstalación terminada para las rutas seleccionadas.\n'
	ui_pause
}