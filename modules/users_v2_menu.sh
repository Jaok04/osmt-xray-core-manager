#!/usr/bin/env bash
# Interfaz inicial de consulta para el modelo v2. No modifica datos ni runtime.

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
		printf '  [0] Volver al menú principal\n\n'
		ui_read_option "Selecciona una opción: " option
		case "$option" in
		1) users_v2_menu_list; ui_pause ;;
		2) users_v2_menu_summary; ui_pause ;;
		3) users_v2_menu_create_identity; ui_pause ;;
		4) users_v2_menu_create_association; ui_pause ;;
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
	IFS= read -r identity_id || { users_v2_unlock "$fd"; return 0; }
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
	IFS= read -r connection_id || { users_v2_unlock "$fd"; return 0; }
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
	IFS= read -r -s credential_value || { printf '\n'; return 0; }
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
		unlimited) duration_value=0; duration_unit=none ;;
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
