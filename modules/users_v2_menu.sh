#!/usr/bin/env bash
# Interfaz inicial de consulta para el modelo v2. No modifica datos ni runtime.

users_menu_dispatch() {
	local file="${USER_DATA_FILE:-${XRAY_MANAGER_USERS_FILE:-/var/lib/xray-manager/users/users.json}}"
	local schema

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
		printf '  [0] Volver al menú principal\n'
		printf '\n  Esta primera integración es de consulta; no modifica credenciales ni runtime.\n\n'
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
