#!/usr/bin/env bash
# Interfaz administrativa del modelo v2. No aplica cambios al runtime Xray.

users_menu_dispatch() {
	local file="${USER_DATA_FILE:-${XRAY_MANAGER_USERS_FILE:-/var/lib/xray-manager/users/users.json}}"

	# Mantiene el comportamiento legacy: si el archivo aún no existe, el
	# menú antiguo conserva la responsabilidad de inicializar su arreglo.
	if [[ ! -e "$file" ]]; then
		users_menu
		return
	fi

	if ! command -v jq >/dev/null 2>&1 || ! jq -e . "$file" >/dev/null 2>&1; then
		ui_clear
		ui_title "GESTIÓN DE USUARIOS"
		printf '\nEl registro de usuarios contiene JSON inválido o no se puede leer.\n'
		printf 'Por seguridad, la gestión quedó bloqueada y el archivo no fue modificado.\n'
		ui_pause
		return 1
	fi

	if jq -e 'type == "array"' "$file" >/dev/null 2>&1; then
		users_menu
		return
	fi

	if jq -e 'type == "object" and .schema_version == 2 and (.identities | type == "array") and (.associations | type == "array")' "$file" >/dev/null 2>&1; then
		users_v2_menu
		return
	fi

	ui_clear
	ui_title "GESTIÓN DE USUARIOS"
	printf '\nEl registro utiliza un esquema desconocido o incompleto.\n'
	printf 'No se seleccionó ningún gestor y no se modificaron los datos.\n'
	ui_pause
	return 1
}

users_v2_menu() {
	local option
	while true; do
		ui_clear
		ui_title "GESTIÓN DE IDENTIDADES Y ASOCIACIONES (V2)"
		printf '\n  [1] Consultar identidades y asociaciones\n'
		printf '  [2] Resumen del registro\n'
		printf '  [3] Crear identidad global\n'
		printf '  [4] Asociar identidad a conexión\n'
		printf '  [5] Consultar detalle de asociación\n'
		printf '  [6] Editar alias y límites de asociación\n'
		printf '  [7] Suspender / reactivar asociación\n'
		printf '  [8] Renovar asociación\n'
		printf '  [9] Modificar duración de asociación\n'
		printf '  [10] Eliminar asociación individual\n'
		printf '  [11] Eliminar identidad y todas sus asociaciones\n'
		printf '  [0] Volver al menú principal\n\n'
		ui_read_option "Selecciona una opción: " option
		case "$option" in
		1)
			users_v2_menu_list
			ui_pause
			;;
		2)
			users_v2_menu_summary
			ui_pause
			;;
		3)
			users_v2_menu_create_identity
			ui_pause
			;;
		4)
			users_v2_menu_create_association
			ui_pause
			;;
		5)
			users_v2_menu_association_detail
			ui_pause
			;;
		6)
			users_v2_menu_association_edit
			ui_pause
			;;
		7)
			users_v2_menu_association_state
			ui_pause
			;;
		8)
			users_v2_menu_association_renew
			ui_pause
			;;
		9)
			users_v2_menu_association_set_duration
			ui_pause
			;;
		10)
			users_v2_menu_association_delete
			ui_pause
			;;
		11)
			users_v2_menu_identity_delete
			ui_pause
			;;
		0) return 0 ;;
		*)
			printf '\nOpción no válida.\n'
			ui_pause
			;;
		esac
	done
}

users_v2_menu_list() {
	local fd
	ui_clear
	ui_title "IDENTIDADES Y ASOCIACIONES"
	if ! users_v2_lock fd; then
		printf '\nNo fue posible validar o bloquear el registro v2.\n'
		return 1
	fi

	printf '\nIDENTIDADES\n'
	if [[ "$(jq '.identities | length' "$USERS_V2_DATA_FILE")" -eq 0 ]]; then
		printf '  No hay identidades registradas.\n'
	else
		jq -r '.identities[] | "  ID: \(.id)\n  Creada: \(.created_at)\n"' "$USERS_V2_DATA_FILE"
	fi

	printf '\nASOCIACIONES\n'
	if [[ "$(jq '.associations | length' "$USERS_V2_DATA_FILE")" -eq 0 ]]; then
		printf '  No hay asociaciones registradas.\n'
	else
		jq -r '.associations[] | "  Asociación: \(.id)\n  Identidad: \(.identity_id)\n  Alias: \(.alias)\n  Protocolo: \(.protocol)\n  Conexión: \(.connection_id)\n  Estado: \(.state)\n  Implementación: \(.provisioning_status)\n  Vencimiento: \(.expires_at // "Sin vencimiento")\n"' "$USERS_V2_DATA_FILE"
	fi
	users_v2_unlock "$fd"
	printf '\nLas credenciales y claves no se muestran en esta vista.\n'
}

users_v2_menu_summary() {
	local fd
	ui_clear
	ui_title "RESUMEN DEL REGISTRO V2"
	if ! users_v2_lock fd; then
		printf '\nNo fue posible validar o bloquear el registro v2.\n'
		return 1
	fi
	jq -r '
		"Identidades: " + ((.identities | length) | tostring),
		"Asociaciones: " + ((.associations | length) | tostring),
		"Activas: " + ([.associations[] | select(.state == "active")] | length | tostring),
		"Suspensas: " + ([.associations[] | select(.state == "suspended")] | length | tostring),
		"Vencidas: " + ([.associations[] | select(.state == "expired")] | length | tostring),
		"VLESS: " + ([.associations[] | select(.protocol == "vless")] | length | tostring),
		"WireGuard: " + ([.associations[] | select(.protocol == "wireguard")] | length | tostring)
	' "$USERS_V2_DATA_FILE"
	users_v2_unlock "$fd"
	printf '\nEl estado funcional y el estado de implementación se contabilizan por separado.\n'
}

# Crea una identidad global sin asociarla automáticamente a ninguna conexión.
users_v2_menu_create_identity() {
	local id
	ui_clear
	ui_title "CREAR IDENTIDAD GLOBAL"
	printf '\nSe creará una identidad independiente de cualquier alias o protocolo.\n'
	if ! ui_confirm "¿Crear una nueva identidad?"; then
		printf '\nOperación cancelada.\n'
		return 0
	fi
	if ! id="$(users_identity_create)"; then
		printf '\nNo fue posible crear la identidad. Revisa el registro y sus dependencias.\n'
		return 1
	fi
	printf '\nIdentidad creada correctamente.\nID: %s\n' "$id"
	printf '\nGuarda este ID: se utiliza para agregar asociaciones posteriormente.\n'
}

# Crea una asociación sobre una identidad y una conexión ya registradas.
# Las credenciales se leen sin eco y nunca se imprimen en pantalla.
users_v2_menu_create_association() {
	local fd identity_id connection_id protocol_id protocol name capacity
	local alias credential_type credential_value state duration_kind duration_value duration_unit
	local traffic simultaneous association_id
	ui_clear
	ui_title "ASOCIAR IDENTIDAD A CONEXIÓN"

	if ! users_v2_lock fd; then
		printf '\nNo fue posible bloquear y validar los registros.\n'
		return 1
	fi
	if [[ "$(jq '.identities | length' "$USERS_V2_DATA_FILE")" -eq 0 ]]; then
		users_v2_unlock "$fd"
		printf '\nNo hay identidades. Crea primero una identidad global.\n'
		return 1
	fi
	printf '\nIDENTIDADES DISPONIBLES\n'
	jq -r '.identities[] | "  " + .id + "  (creada: " + .created_at + ")"' "$USERS_V2_DATA_FILE"
	printf '\nID exacto de identidad: '
	IFS= read -r identity_id || {
		users_v2_unlock "$fd"
		return 0
	}
	if ! jq -e --arg id "$identity_id" 'any(.identities[]; .id == $id)' "$USERS_V2_DATA_FILE" >/dev/null; then
		users_v2_unlock "$fd"
		printf '\nLa identidad indicada no existe.\n'
		return 1
	fi

	if ! jq -e 'type == "array"' "$USERS_V2_CONNECTIONS_FILE" >/dev/null 2>&1; then
		users_v2_unlock "$fd"
		printf '\nEl catálogo de conexiones no es válido.\n'
		return 1
	fi
	if [[ "$(jq 'length' "$USERS_V2_CONNECTIONS_FILE")" -eq 0 ]]; then
		users_v2_unlock "$fd"
		printf '\nNo hay conexiones registradas. Crea primero una conexión en borrador.\n'
		return 1
	fi
	printf '\nCONEXIONES DISPONIBLES\n'
	jq -r '.[] | "  ID: " + .id + "\n  Nombre: " + .name + "\n  Modalidad: " + .protocol_id + "\n  Capacidad: " + (.max_users|tostring) + "\n"' "$USERS_V2_CONNECTIONS_FILE"
	printf 'ID exacto de conexión: '
	IFS= read -r connection_id || {
		users_v2_unlock "$fd"
		return 0
	}
	connection_id="$(jq -r --arg id "$connection_id" '.[] | select(.id == $id) | .id' "$USERS_V2_CONNECTIONS_FILE")"
	if [[ -z "$connection_id" ]]; then
		users_v2_unlock "$fd"
		printf '\nLa conexión indicada no existe.\n'
		return 1
	fi
	protocol_id="$(jq -r --arg id "$connection_id" '.[] | select(.id == $id) | .protocol_id' "$USERS_V2_CONNECTIONS_FILE")"
	name="$(jq -r --arg id "$connection_id" '.[] | select(.id == $id) | .name' "$USERS_V2_CONNECTIONS_FILE")"
	capacity="$(jq -r --arg id "$connection_id" '.[] | select(.id == $id) | .max_users' "$USERS_V2_CONNECTIONS_FILE")"
	if [[ "$protocol_id" == vless_* ]]; then
		protocol=vless
		credential_type=uuid
	elif [[ "$protocol_id" == wireguard* ]]; then
		protocol=wireguard
		credential_type=public_key
	else
		users_v2_unlock "$fd"
		printf '\nLa modalidad %s todavía no admite asociaciones en el modelo v2.\n' "$protocol_id"
		return 1
	fi
	users_v2_unlock "$fd"

	printf '\nConexión: %s (%s)\nProtocolo: %s\nCapacidad configurada: %s\n' "$name" "$connection_id" "$protocol" "$capacity"
	printf '\nAlias de esta asociación (máximo 64 caracteres): '
	IFS= read -r alias || return 0
	printf 'Credencial (%s): ' "$credential_type"
	IFS= read -r -s credential_value || {
		printf '\n'
		return 0
	}
	printf '\n'
	if [[ -z "$credential_value" ]]; then
		printf '\nLa credencial no puede estar vacía.\n'
		return 1
	fi

	printf '\nEstado inicial [active/suspended]: '
	IFS= read -r state || return 0
	if [[ "$state" != active && "$state" != suspended ]]; then
		printf '\nEstado no válido.\n'
		return 1
	fi
	printf 'Duración [unlimited/custom]: '
	IFS= read -r duration_kind || return 0
	case "$duration_kind" in
	unlimited)
		duration_value=0
		duration_unit=none
		;;
	custom)
		printf 'Cantidad (entero positivo): '
		IFS= read -r duration_value || return 0
		printf 'Unidad [days/hours/minutes]: '
		IFS= read -r duration_unit || return 0
		;;
	*)
		printf '\nTipo de duración no válido.\n'
		return 1
		;;
	esac
	printf 'Límite de tráfico en bytes (0 = sin límite): '
	IFS= read -r traffic || return 0
	printf 'Límite de conexiones simultáneas (0 = sin límite): '
	IFS= read -r simultaneous || return 0
	if [[ ! "$traffic" =~ ^[0-9]+$ || ! "$simultaneous" =~ ^[0-9]+$ ]]; then
		printf '\nLos límites deben ser enteros no negativos.\n'
		return 1
	fi

	printf '\nRESUMEN (la credencial se mantiene oculta)\n'
	printf 'Identidad: %s\nConexión: %s\nModalidad: %s\nAlias: %s\nCredencial: %s\nEstado: %s\nDuración: %s %s\nLímite de tráfico: %s bytes\nConexiones simultáneas: %s\n' \
		"$identity_id" "$connection_id" "$protocol_id" "$alias" "$credential_type" "$state" "$duration_value" "$duration_unit" "$traffic" "$simultaneous"
	if ! ui_confirm "¿Confirmas la creación de esta asociación?"; then
		printf '\nOperación cancelada; no se guardaron cambios.\n'
		return 0
	fi
	if ! association_id="$(users_association_create "$identity_id" "$connection_id" "$alias" "$credential_type" "$credential_value" "$state" "$duration_kind" "$duration_value" "$duration_unit" "$traffic" "$simultaneous" auto)"; then
		printf '\nNo se pudo crear la asociación. Puede existir un conflicto de credencial, capacidad o datos.\n'
		return 1
	fi
	printf '\nAsociación creada correctamente.\nID de asociación: %s\nProvisioning: draft\nRuntime: sin cambios (not_applied).\n' "$association_id"
}

# Consulta el detalle administrativo de una asociación sin revelar credenciales.
users_v2_menu_association_detail() {
	local fd association_id
	ui_clear
	ui_title "DETALLE DE ASOCIACIÓN"

	if ! users_v2_lock fd; then
		printf '\nNo fue posible validar o bloquear el registro v2.\n'
		return 1
	fi
	if [[ "$(jq '.associations | length' "$USERS_V2_DATA_FILE")" -eq 0 ]]; then
		users_v2_unlock "$fd"
		printf '\nNo hay asociaciones registradas.\n'
		return 0
	fi

	printf '\nASOCIACIONES DISPONIBLES\n'
	jq -r '.associations[] | "  " + .id + "  | " + .alias + "  | " + .protocol + "  | " + .connection_id' "$USERS_V2_DATA_FILE"
	printf '\nID exacto de asociación: '
	IFS= read -r association_id || {
		users_v2_unlock "$fd"
		return 0
	}
	if ! jq -e --arg id "$association_id" 'any(.associations[]; .id == $id)' "$USERS_V2_DATA_FILE" >/dev/null; then
		users_v2_unlock "$fd"
		printf '\nLa asociación indicada no existe. No se modificaron datos.\n'
		return 1
	fi

	jq -r --arg id "$association_id" '
		.associations[] | select(.id == $id) |
		"ID de asociación: " + .id,
		"ID de identidad: " + .identity_id,
		"Alias: " + .alias,
		"Protocolo: " + .protocol,
		"ID de conexión: " + .connection_id,
		"Credencial: [oculta]",
		"Creada: " + .created_at,
		"Duración: " + (if .duration.kind == "unlimited" then "Ilimitada" else ((.duration.value|tostring) + " " + .duration.unit) end),
		"Vencimiento: " + (.expires_at // "Sin vencimiento activo"),
		"Estado funcional: " + .state,
		"Provisioning: " + .provisioning_status,
		"Runtime: " + .runtime.status,
		"Última aplicación: " + (.runtime.last_applied_at // "Nunca"),
		"Límite de tráfico: " + (if .traffic_limit_bytes == null then "Sin límite" else ((.traffic_limit_bytes|tostring) + " bytes") end),
		"Conexiones simultáneas: " + (if .simultaneous_connection_limit == null then "Sin límite" else (.simultaneous_connection_limit|tostring) end),
		"Suspensión iniciada: " + (.suspended_at // "No"),
		"Tiempo restante pausado: " + (if .remaining_seconds == null then "No aplica" else ((.remaining_seconds|tostring) + " segundos") end)
	' "$USERS_V2_DATA_FILE"
	users_v2_unlock "$fd"
	printf '\nLas credenciales y claves permanecen ocultas. Esta consulta no modifica el registro ni el runtime.\n'
}

# Edit alias and limits for one association; credentials and runtime stay untouched.
users_v2_menu_association_edit() {
	local fd association_id current_alias current_traffic current_simultaneous
	local alias traffic simultaneous
	ui_clear
	ui_title "EDITAR ALIAS Y LÍMITES"
	if ! users_v2_lock fd; then
		printf '\nNo fue posible validar o bloquear el registro v2.\n'
		return 1
	fi
	if [[ "$(jq '.associations | length' "$USERS_V2_DATA_FILE")" -eq 0 ]]; then
		users_v2_unlock "$fd"
		printf '\nNo hay asociaciones registradas.\n'
		return 0
	fi
	printf '\nASOCIACIONES DISPONIBLES\n'
	jq -r '.associations[] | "  " + .id + "  | " + .alias + "  | " + .protocol + "  | " + .connection_id' "$USERS_V2_DATA_FILE"
	printf '\nID exacto de asociación: '
	IFS= read -r association_id || {
		users_v2_unlock "$fd"
		return 0
	}
	if ! jq -e --arg id "$association_id" 'any(.associations[]; .id == $id)' "$USERS_V2_DATA_FILE" >/dev/null; then
		users_v2_unlock "$fd"
		printf '\nLa asociación indicada no existe. No se modificaron datos.\n'
		return 1
	fi
	current_alias="$(jq -r --arg id "$association_id" '.associations[] | select(.id == $id) | .alias' "$USERS_V2_DATA_FILE")"
	current_traffic="$(jq -r --arg id "$association_id" '.associations[] | select(.id == $id) | .traffic_limit_bytes // 0' "$USERS_V2_DATA_FILE")"
	current_simultaneous="$(jq -r --arg id "$association_id" '.associations[] | select(.id == $id) | .simultaneous_connection_limit // 0' "$USERS_V2_DATA_FILE")"
	users_v2_unlock "$fd"

	printf '\nAlias actual: %s\n' "$current_alias"
	printf 'Nuevo alias (1-64 caracteres, sin espacios externos): '
	IFS= read -r alias || return 0
	printf 'Límite de tráfico actual: %s bytes (0 = sin límite)\n' "$current_traffic"
	printf 'Nuevo límite de tráfico en bytes (0 = sin límite): '
	IFS= read -r traffic || return 0
	printf 'Límite simultáneo actual: %s (0 = sin límite)\n' "$current_simultaneous"
	printf 'Nuevo límite de conexiones simultáneas (0 = sin límite): '
	IFS= read -r simultaneous || return 0

	if [[ -z "$alias" || "${#alias}" -gt 64 || "$alias" != "$(printf '%s' "$alias" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')" ]]; then
		printf '\nEl alias debe tener entre 1 y 64 caracteres y no llevar espacios externos.\n'
		return 2
	fi
	if [[ ! "$traffic" =~ ^(0|[1-9][0-9]*)$ || ! "$simultaneous" =~ ^(0|[1-9][0-9]*)$ ]]; then
		printf '\nLos límites deben ser enteros no negativos; usa 0 para quitar el límite.\n'
		return 2
	fi
	printf '\nRESUMEN DE CAMBIOS\nAlias: %s\nLímite de tráfico: %s bytes\nConexiones simultáneas: %s\n' "$alias" "$traffic" "$simultaneous"
	if ! ui_confirm "¿Confirmas los cambios de esta asociación?"; then
		printf '\nOperación cancelada; no se guardaron cambios.\n'
		return 0
	fi
	if ! users_association_update "$association_id" "$alias" "$traffic" "$simultaneous"; then
		printf '\nNo se pudo actualizar la asociación. Revisa el ID, los límites y el registro.\n'
		return 1
	fi
	printf '\nAsociación actualizada correctamente.\nCredencial, duración, estado funcional y runtime: sin cambios.\n'
}

# Toggle only the functional state; reactivation explicitly starts a new duration.
users_v2_menu_association_state() {
	local fd association_id state alias duration_kind duration_value duration_unit
	ui_clear
	ui_title "SUSPENDER / REACTIVAR ASOCIACIÓN"
	if ! users_v2_lock fd; then
		printf '\nNo fue posible validar o bloquear el registro v2.\n'
		return 1
	fi
	if [[ "$(jq '.associations | length' "$USERS_V2_DATA_FILE")" -eq 0 ]]; then
		users_v2_unlock "$fd"
		printf '\nNo hay asociaciones registradas.\n'
		return 0
	fi
	printf '\nASOCIACIONES DISPONIBLES\n'
	jq -r '.associations[] | "  " + .id + "  | " + .alias + "  | " + .state + "  | " + .protocol' "$USERS_V2_DATA_FILE"
	printf '\nID exacto de asociación: '
	IFS= read -r association_id || {
		users_v2_unlock "$fd"
		return 0
	}
	if ! jq -e --arg id "$association_id" 'any(.associations[]; .id == $id)' "$USERS_V2_DATA_FILE" >/dev/null; then
		users_v2_unlock "$fd"
		printf '\nLa asociación indicada no existe. No se modificaron datos.\n'
		return 1
	fi
	state="$(jq -r --arg id "$association_id" '.associations[] | select(.id == $id) | .state' "$USERS_V2_DATA_FILE")"
	alias="$(jq -r --arg id "$association_id" '.associations[] | select(.id == $id) | .alias' "$USERS_V2_DATA_FILE")"
	users_v2_unlock "$fd"

	case "$state" in
	active)
		printf '\nAsociación: %s\nEstado actual: activa\n' "$alias"
		if ! ui_confirm "¿Suspender esta asociación?"; then
			printf '\nOperación cancelada; no se guardaron cambios.\n'
			return 0
		fi
		if ! users_association_suspend "$association_id"; then
			printf '\nNo se pudo suspender. La asociación pudo haber vencido o cambiado de estado; vuelve a consultar su detalle.\n'
			return 1
		fi
		printf '\nAsociación suspendida. Su tiempo restante quedó pausado cuando tenía duración limitada.\n'
		;;
	suspended)
		printf '\nAsociación: %s\nEstado actual: suspendida\n' "$alias"
		printf 'La reactivación inicia una duración nueva; no recupera automáticamente el tiempo restante anterior.\n'
		printf 'Duración nueva [unlimited/custom]: '
		IFS= read -r duration_kind || return 0
		case "$duration_kind" in
		unlimited)
			duration_value=0
			duration_unit=none
			;;
		custom)
			printf 'Cantidad (entero positivo): '
			IFS= read -r duration_value || return 0
			printf 'Unidad [days/hours/minutes]: '
			IFS= read -r duration_unit || return 0
			;;
		*)
			printf '\nTipo de duración no válido. No se modificaron datos.\n'
			return 2
			;;
		esac
		if ! users_v2_duration_args "$duration_kind" "$duration_value" "$duration_unit"; then
			printf '\nDuración no válida. No se modificaron datos.\n'
			return 2
		fi
		printf '\nNueva duración: %s %s\n' "$duration_value" "$duration_unit"
		if ! ui_confirm "¿Reactivar esta asociación con la duración indicada?"; then
			printf '\nOperación cancelada; no se guardaron cambios.\n'
			return 0
		fi
		if ! users_association_reactivate "$association_id" "$duration_kind" "$duration_value" "$duration_unit"; then
			printf '\nNo se pudo reactivar. La asociación pudo haber cambiado de estado; vuelve a consultar su detalle.\n'
			return 1
		fi
		printf '\nAsociación reactivada correctamente. La duración comienza desde ahora.\n'
		;;
	expired)
		printf '\nLa asociación está vencida. Esta operación no la reactiva; utiliza la renovación cuando esté disponible.\n'
		return 1
		;;
	*)
		printf '\nEstado desconocido. No se modificaron datos.\n'
		return 1
		;;
	esac
}

# Renewal and duration editing are separate domain operations with distinct
# state rules. Both identify records by immutable association ID.
users_v2_menu_association_duration() {
	[[ "$#" -eq 1 && ("$1" == renew || "$1" == set) ]] || return 2
	local operation="$1" fd association_id state alias duration_kind duration_value duration_unit
	local action_label
	ui_clear
	if [[ "$operation" == renew ]]; then
		ui_title "RENOVAR ASOCIACIÓN"
		action_label="renovación"
	else
		ui_title "MODIFICAR DURACIÓN DE ASOCIACIÓN"
		action_label="modificación de duración"
	fi
	if ! users_v2_lock fd; then
		printf '\nNo fue posible validar o bloquear el registro v2.\n'
		return 1
	fi
	if [[ "$(jq '.associations | length' "$USERS_V2_DATA_FILE")" -eq 0 ]]; then
		users_v2_unlock "$fd"
		printf '\nNo hay asociaciones registradas.\n'
		return 0
	fi
	printf '\nASOCIACIONES DISPONIBLES\n'
	jq -r '.associations[] | "  " + .id + "  | " + .alias + "  | " + .state + "  | " + .protocol' "$USERS_V2_DATA_FILE"
	printf '\nID exacto de asociación: '
	IFS= read -r association_id || {
		users_v2_unlock "$fd"
		return 0
	}
	local assoc
	assoc="$(jq -ce --arg id "$association_id" '.associations[] | select(.id == $id)' "$USERS_V2_DATA_FILE")" || {
		users_v2_unlock "$fd"
		printf '\nLa asociación indicada no existe. No se modificaron datos.\n'
		return 1
	}
	state="$(jq -r '.state' <<<"$assoc")"
	alias="$(jq -r '.alias' <<<"$assoc")"
	users_v2_unlock "$fd"

	if [[ "$operation" == renew ]]; then
		if [[ "$state" != active && "$state" != expired ]]; then
			printf '\nNo se puede renovar una asociación %s. La renovación admite estados active o expired.\n' "$state"
			return 1
		fi
		printf '\nLa renovación inicia el nuevo periodo desde ahora y reemplaza el vencimiento anterior.\n'
	else
		if [[ "$state" != active && "$state" != suspended ]]; then
			printf '\nNo se puede modificar la duración de una asociación %s. Usa renovación para una asociación vencida.\n' "$state"
			return 1
		fi
		if [[ "$state" == suspended ]]; then
			printf '\nLa asociación está suspendida: la duración nueva actualizará el tiempo restante pausado, sin reactivarla.\n'
		else
			printf '\nLa duración nueva se calculará desde ahora.\n'
		fi
	fi
	printf '\nAsociación: %s\nEstado actual: %s\n' "$alias" "$state"
	printf 'Duración nueva [unlimited/custom]: '
	IFS= read -r duration_kind || return 0
	case "$duration_kind" in
	unlimited)
		duration_value=0
		duration_unit=none
		;;
	custom)
		printf 'Cantidad (entero positivo): '
		IFS= read -r duration_value || return 0
		printf 'Unidad [days/hours/minutes]: '
		IFS= read -r duration_unit || return 0
		;;
	*)
		printf '\nTipo de duración no válido. No se modificaron datos.\n'
		return 2
		;;
	esac
	if ! users_v2_duration_args "$duration_kind" "$duration_value" "$duration_unit"; then
		printf '\nDuración no válida. No se modificaron datos.\n'
		return 2
	fi
	printf '\nRESUMEN DE %s\nAsociación: %s\nNueva duración: %s %s\n' "$action_label" "$alias" "$duration_value" "$duration_unit"
	if ! ui_confirm "¿Confirmas la $action_label de esta asociación?"; then
		printf '\nOperación cancelada; no se guardaron cambios.\n'
		return 0
	fi
	if [[ "$operation" == renew ]]; then
		if ! users_association_renew "$association_id" "$duration_kind" "$duration_value" "$duration_unit"; then
			printf '\nNo se pudo renovar. La asociación pudo haber cambiado de estado; vuelve a consultar su detalle.\n'
			return 1
		fi
		printf '\nAsociación renovada correctamente. El nuevo periodo comienza desde ahora; el estado funcional queda active.\n'
	else
		if ! users_association_set_duration "$association_id" "$duration_kind" "$duration_value" "$duration_unit"; then
			printf '\nNo se pudo modificar la duración. La asociación pudo haber cambiado de estado; vuelve a consultar su detalle.\n'
			return 1
		fi
		if [[ "$state" == suspended ]]; then
			printf '\nDuración modificada. La asociación continúa suspendida y el nuevo tiempo permanece pausado.\n'
		else
			printf '\nDuración modificada correctamente. El nuevo periodo comienza desde ahora.\n'
		fi
	fi
	printf 'Credenciales, límites, provisioning y runtime: sin cambios.\n'
}

users_v2_menu_association_renew() {
	users_v2_menu_association_duration renew
}

users_v2_menu_association_set_duration() {
	users_v2_menu_association_duration set
}

# Delete one association only. Its global identity and sibling associations remain.
users_v2_menu_association_delete() {
	local fd association_id assoc alias identity_id protocol connection_id state provisioning runtime
	ui_clear
	ui_title "ELIMINAR ASOCIACIÓN INDIVIDUAL"
	if ! users_v2_lock fd; then
		printf '\nNo fue posible validar o bloquear el registro v2.\n'
		return 1
	fi
	if [[ "$(jq '.associations | length' "$USERS_V2_DATA_FILE")" -eq 0 ]]; then
		users_v2_unlock "$fd"
		printf '\nNo hay asociaciones para eliminar.\n'
		return 0
	fi
	printf '\nASOCIACIONES DISPONIBLES\n'
	jq -r '.associations[] | "  " + .id + "  | " + .alias + "  | " + .protocol + "  | " + .state' "$USERS_V2_DATA_FILE"
	printf '\nID exacto de asociación que deseas eliminar: '
	IFS= read -r association_id || {
		users_v2_unlock "$fd"
		return 0
	}
	assoc="$(jq -ce --arg id "$association_id" '.associations[] | select(.id == $id)' "$USERS_V2_DATA_FILE")" || {
		users_v2_unlock "$fd"
		printf '\nLa asociación indicada no existe. No se modificaron datos.\n'
		return 1
	}
	alias="$(jq -r '.alias' <<<"$assoc")"
	identity_id="$(jq -r '.identity_id' <<<"$assoc")"
	protocol="$(jq -r '.protocol' <<<"$assoc")"
	connection_id="$(jq -r '.connection_id' <<<"$assoc")"
	state="$(jq -r '.state' <<<"$assoc")"
	provisioning="$(jq -r '.provisioning_status' <<<"$assoc")"
	runtime="$(jq -r '.runtime.status' <<<"$assoc")"
	users_v2_unlock "$fd"

	printf '\nRESUMEN DE ELIMINACIÓN\n'
	printf 'ID de asociación: %s\nAlias: %s\nIdentidad global: %s\nProtocolo: %s\nConexión: %s\nEstado: %s\nProvisioning: %s\nRuntime: %s\n' \
		"$association_id" "$alias" "$identity_id" "$protocol" "$connection_id" "$state" "$provisioning" "$runtime"
	printf '\nSe eliminará únicamente esta asociación del registro administrativo.\n'
	printf 'La identidad global y sus demás asociaciones se conservarán.\n'
	printf 'Esta operación no revoca clientes ni peers en el runtime Xray.\n'
	if ! ui_confirm "¿Confirmas eliminar definitivamente esta asociación?"; then
		printf '\nOperación cancelada; no se guardaron cambios.\n'
		return 0
	fi
	if ! users_association_delete "$association_id"; then
		printf '\nNo se pudo eliminar. La asociación pudo haber cambiado o desaparecido; vuelve a consultar el registro.\n'
		return 1
	fi
	printf '\nAsociación eliminada del registro administrativo. La identidad y las demás asociaciones permanecen intactas.\n'
	printf 'Runtime y provisioning no fueron modificados.\n'
}

# Delete a global identity and every association that belongs to it.
# The association-ID snapshot prevents a concurrent new peer from being
# silently included after the administrator reviewed the deletion preview.
users_v2_menu_identity_delete() {
	local fd identity_id identity created_at association_ids association_count confirmation
	ui_clear
	ui_title "ELIMINAR IDENTIDAD GLOBAL"
	if ! users_v2_lock fd; then
		printf '\nNo fue posible validar o bloquear el registro v2.\n'
		return 1
	fi
	if [[ "$(jq '.identities | length' "$USERS_V2_DATA_FILE")" -eq 0 ]]; then
		users_v2_unlock "$fd"
		printf '\nNo hay identidades para eliminar.\n'
		return 0
	fi
	printf '\nIDENTIDADES DISPONIBLES (ID inmutable)\n'
	jq -r '.identities[] | "  " + .id + "  | creada: " + .created_at' "$USERS_V2_DATA_FILE"
	printf '\nID exacto de identidad que deseas eliminar: '
	IFS= read -r identity_id || {
		users_v2_unlock "$fd"
		return 0
	}
	identity="$(jq -ce --arg id "$identity_id" '.identities[] | select(.id == $id)' "$USERS_V2_DATA_FILE")" || {
		users_v2_unlock "$fd"
		printf '\nLa identidad indicada no existe. No se modificaron datos.\n'
		return 1
	}
	created_at="$(jq -r '.created_at' <<<"$identity")"
	association_ids="$(jq -c --arg id "$identity_id" '[.associations[] | select(.identity_id == $id) | .id] | sort' "$USERS_V2_DATA_FILE")" || {
		users_v2_unlock "$fd"
		return 1
	}
	association_count="$(jq 'length' <<<"$association_ids")"
	printf '\nASOCIACIONES QUE SE ELIMINARÁN\n'
	if [[ "$association_count" -eq 0 ]]; then
		printf '  Esta identidad no tiene asociaciones.\n'
	else
		jq -r --arg id "$identity_id" '.associations[] | select(.identity_id == $id) | "  ID: " + .id + "\n  Alias: " + .alias + "\n  Protocolo: " + .protocol + "\n  Conexión: " + .connection_id + "\n  Estado: " + .state + "\n  Provisioning: " + .provisioning_status + "\n  Runtime: " + .runtime.status + "\n"' "$USERS_V2_DATA_FILE"
	fi
	users_v2_unlock "$fd"

	printf '\nRESUMEN DE ELIMINACIÓN DEFINITIVA\n'
	printf 'ID de identidad: %s\nCreada: %s\nAsociaciones incluidas: %s\n' "$identity_id" "$created_at" "$association_count"
	printf '\nSe eliminará la identidad global y TODAS las asociaciones/peers vinculados a ella.\n'
	printf 'Las demás identidades y sus asociaciones no se modificarán.\n'
	printf 'Esta operación solo afecta el registro administrativo; NO revoca clientes/peers del runtime Xray.\n'
	if ! ui_confirm "¿Deseas continuar con esta eliminación permanente?"; then
		printf '\nOperación cancelada; no se guardaron cambios.\n'
		return 0
	fi
	printf 'Para confirmar, escribe exactamente el ID de la identidad: '
	IFS= read -r confirmation || return 0
	if [[ "$confirmation" != "$identity_id" ]]; then
		printf '\nEl ID de confirmación no coincide. No se modificaron datos.\n'
		return 1
	fi
	if users_identity_delete "$identity_id" "$association_ids"; then
		printf '\nIdentidad y %s asociación(es) eliminadas del registro administrativo.\n' "$association_count"
		printf 'Las demás identidades permanecen. Runtime y provisioning no fueron modificados.\n'
	else
		local rc=$?
		if ((rc == 3)); then
			printf '\nEl conjunto de asociaciones cambió después de la vista previa. No se eliminó nada; vuelve a consultar la identidad.\n'
		else
			printf '\nNo se pudo eliminar la identidad. No se confirmó el cambio; revisa el registro.\n'
		fi
		return 1
	fi
}
