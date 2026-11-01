#!/usr/bin/env bash
# shellcheck disable=SC2016
if ! declare -F json_store_commit >/dev/null 2>&1; then
	# shellcheck disable=SC1091
	source "${APP_ROOT:-/opt/xray-manager}/lib/json_store.sh"
fi
# Gestión local de identidades VLESS. No aplica cambios al runtime.

USER_DATA_DIR="${XRAY_MANAGER_USERS_DIR:-/var/lib/xray-manager/users}"
USER_DATA_FILE="${XRAY_MANAGER_USERS_FILE:-/var/lib/xray-manager/users/users.json}"
USER_LOCK="${XRAY_MANAGER_INTEGRITY_LOCK:-${XRAY_MANAGER_USERS_LOCK:-/run/xray-manager/integrity.lock}}"

users_require_tools() {
	command -v jq >/dev/null 2>&1 && command -v flock >/dev/null 2>&1 && command -v uuidgen >/dev/null 2>&1
}

users_lock() {
	local -n fd_ref="$1"
	mkdir -p "$USER_DATA_DIR" "$(dirname "$USER_LOCK")"
	exec {fd_ref}>"$USER_LOCK"
	flock -x "$fd_ref"
	if [[ ! -e "$USER_DATA_FILE" ]]; then
		printf '%s\n' '[]' >"$USER_DATA_FILE"
		chmod 600 "$USER_DATA_FILE"
	fi
	if ! jq -e 'type == "array" and all(.[]; type == "object" and
        (.uuid | type == "string") and (.connection_id | type == "string") and
        (.label | type == "string") and (.state == "draft") and
        (.runtime_applied == false))' "$USER_DATA_FILE" >/dev/null 2>&1; then
		flock -u "$fd_ref"
		exec {fd_ref}>&-
		printf '\nEl registro de usuarios es inválido o contiene un estado no compatible. No se modificó.\n' >&2
		return 1
	fi
}

users_unlock() {
	local fd="$1"
	flock -u "$fd"
	exec {fd}>&-
}

users_atomic_update() {
	local tmp rc
	tmp="$(mktemp "$USER_DATA_DIR/.users.XXXXXX")" || return 1
	if ! jq "$@" "$USER_DATA_FILE" >"$tmp"; then
		rm -f "$tmp"
		return 1
	fi
	if ! jq -e 'type == "array" and all(.[]; type == "object" and
        (.uuid | type == "string" and length > 0) and
        (.connection_id | type == "string" and length > 0) and
        (.label | type == "string" and length > 0) and
        (.state == "draft") and (.runtime_applied == false) and
        (.created_at | type == "string")) and
        ([.[].uuid] | length == (unique | length))' "$tmp" >/dev/null; then
		rm -f "$tmp"
		return 1
	fi
	if json_store_commit "$tmp" "$USER_DATA_FILE" 600; then
		:
	else
		rc=$?
		if ((rc == 3)); then
			printf 'ADVERTENCIA: el usuario quedó guardado, pero no se pudo confirmar la sincronización del directorio.\n' >&2
		else
			rm -f "$tmp"
			return 1
		fi
	fi
}

users_connection_details() {
	local connection_id="$1" file="${CONNECTION_DATA_FILE:-$XRAY_MANAGER_CONNECTIONS_FILE}"
	[[ -r "$file" ]] || return 1
	jq -er --arg id "$connection_id" '
      .[] | select(.id == $id and (.protocol_id | startswith("vless_")) and .state == "draft") |
      [.id,.name,.protocol_id,(.port|tostring),(.max_users|tostring)] | @tsv
    ' "$file"
}

users_menu() {
	local option
	while true; do
		ui_clear
		ui_title "GESTIÓN DE USUARIOS VLESS"
		printf '\n  [1] Crear usuario VLESS (borrador)\n  [2] Consultar usuarios registrados\n  [3] Cambiar etiqueta de usuario\n  [4] Eliminar usuario (borrador)\n  [0] Volver al menú principal\n\n'
		ui_read_option "Selecciona una opción: " option
		case "$option" in
		1) users_create ;;
		2)
			users_list
			ui_pause
			;;
		3) users_edit ;;
		4) users_delete ;;
		0) return 0 ;;
		*)
			printf '\nOpción no válida.\n'
			ui_pause
			;;
		esac
	done
}

users_create() {
	local connection_id label details connection_name limit fd count uuid created_at
	ui_clear
	ui_title "CREAR USUARIO VLESS - BORRADOR"
	printf '\nEste usuario queda registrado; no se añade a Xray en ejecución.\n'
	printf 'ID de conexión VLESS (conn-...): '
	IFS= read -r connection_id || return 0
	if ! details="$(users_connection_details "$connection_id")"; then
		printf '\nLa conexión no existe, no es VLESS o no está en estado draft.\n'
		ui_pause
		return 1
	fi
	IFS=$'\t' read -r _ connection_name _ _ limit <<<"$details"
	printf 'Etiqueta descriptiva del usuario: '
	IFS= read -r label || return 0
	label="$(connections_trim_name "$label")"
	if [[ -z "$label" || "${#label}" -gt 64 ]]; then
		printf '\nEtiqueta vacía o demasiado larga (máximo 64).\n'
		ui_pause
		return 1
	fi
	if ! users_require_tools || ! users_lock fd; then
		printf '\nNo fue posible abrir el registro de usuarios.\n'
		ui_pause
		return 1
	fi
	# Revalidar bajo el bloqueo compartido: evita crear usuarios asociados
	# a una conexión eliminada o modificada mientras se solicitaba la etiqueta.
	if ! details="$(users_connection_details "$connection_id")"; then
		users_unlock "$fd"
		printf '\nLa conexión dejó de estar disponible; no se creó el usuario.\n'
		ui_pause
		return 1
	fi
	IFS=$'\t' read -r _ connection_name _ _ limit <<<"$details"
	count="$(jq --arg id "$connection_id" '[.[] | select(.connection_id == $id and .state == "draft")] | length' "$USER_DATA_FILE")"
	if ((count >= limit)); then
		users_unlock "$fd"
		printf '\nLa conexión "%s" alcanzó su límite de %s usuarios.\n' "$connection_name" "$limit"
		ui_pause
		return 1
	fi
	uuid="$(uuidgen | tr '[:upper:]' '[:lower:]')"
	if jq -e --arg uuid "$uuid" '.[] | select(.uuid == $uuid)' "$USER_DATA_FILE" >/dev/null; then
		users_unlock "$fd"
		printf '\nColisión inesperada de UUID; no se guardó el usuario.\n'
		ui_pause
		return 1
	fi
	created_at="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
	if ! users_atomic_update --arg uuid "$uuid" --arg connection_id "$connection_id" --arg label "$label" --arg created_at "$created_at" '. + [{uuid:$uuid,connection_id:$connection_id,label:$label,state:"draft",runtime_applied:false,created_at:$created_at}]'; then
		users_unlock "$fd"
		printf '\nNo se pudo guardar el usuario.\n'
		ui_pause
		return 1
	fi
	users_unlock "$fd"
	printf '\nUsuario registrado.\nConexión: %s\nEtiqueta: %s\nUUID: %s\nEstado: draft\n' "$connection_name" "$label" "$uuid"
	printf '\nGuarda el UUID en un lugar seguro; no se ha aplicado a Xray.\n'
	ui_pause
}

users_list() {
	local fd
	ui_clear
	ui_title "USUARIOS VLESS REGISTRADOS"
	if ! users_require_tools || ! users_lock fd; then
		printf '\nNo fue posible consultar el registro.\n'
		return 1
	fi
	if [[ "$(jq 'length' "$USER_DATA_FILE")" -eq 0 ]]; then
		printf '\nTodavía no hay usuarios registrados.\n'
	else
		jq -r '.[] | "UUID: \(.uuid)\nConexión: \(.connection_id)\nEtiqueta: \(.label)\nEstado: \(.state)\nAplicado a runtime: \(.runtime_applied)\n"' "$USER_DATA_FILE"
	fi
	users_unlock "$fd"
}

users_edit() {
	local uuid label fd
	ui_clear
	ui_title "CAMBIAR ETIQUETA DE USUARIO"
	printf '\nUUID exacto: '
	IFS= read -r uuid || return 0
	printf 'Nueva etiqueta: '
	IFS= read -r label || return 0
	label="$(connections_trim_name "$label")"
	if [[ -z "$label" || "${#label}" -gt 64 ]]; then
		printf '\nEtiqueta inválida.\n'
		ui_pause
		return 1
	fi
	if ! users_require_tools || ! users_lock fd; then
		printf '\nNo fue posible acceder al registro.\n'
		ui_pause
		return 1
	fi
	if ! jq -e --arg uuid "$uuid" 'any(.[]; .uuid == $uuid and .state == "draft")' "$USER_DATA_FILE" >/dev/null; then
		users_unlock "$fd"
		printf '\nNo existe un usuario borrador con ese UUID.\n'
		ui_pause
		return 1
	fi
	if ! users_atomic_update --arg uuid "$uuid" --arg label "$label" 'map(if .uuid == $uuid and .state == "draft" then .label = $label else . end)'; then
		users_unlock "$fd"
		printf '\nNo se pudo actualizar la etiqueta.\n'
		ui_pause
		return 1
	fi
	users_unlock "$fd"
	printf '\nEtiqueta actualizada. El UUID no cambió y runtime permanece intacto.\n'
	ui_pause
}

users_delete() {
	local uuid confirmation fd
	ui_clear
	ui_title "ELIMINAR USUARIO VLESS"
	printf '\nUUID exacto: '
	IFS= read -r uuid || return 0
	if ! users_require_tools || ! users_lock fd; then
		printf '\nNo fue posible acceder al registro.\n'
		ui_pause
		return 1
	fi
	if ! jq -e --arg uuid "$uuid" 'any(.[]; .uuid == $uuid and .state == "draft")' "$USER_DATA_FILE" >/dev/null; then
		users_unlock "$fd"
		printf '\nNo existe un usuario borrador con ese UUID.\n'
		ui_pause
		return 1
	fi
	printf 'Para confirmar, escribe ELIMINAR: '
	IFS= read -r confirmation || {
		users_unlock "$fd"
		return 0
	}
	if [[ "$confirmation" != "ELIMINAR" ]]; then
		users_unlock "$fd"
		printf '\nOperación cancelada.\n'
		ui_pause
		return 0
	fi
	if ! users_atomic_update --arg uuid "$uuid" 'map(select(.uuid != $uuid))'; then
		users_unlock "$fd"
		printf '\nNo se pudo eliminar el usuario.\n'
		ui_pause
		return 1
	fi
	users_unlock "$fd"
	printf '\nUsuario eliminado del registro. Xray no fue modificado.\n'
	ui_pause
}

# Exporta exclusivamente los clientes VLESS de una conexión para el adaptador.
# Salida: arreglo JSON [{id,email}]. No persiste ni aplica la configuración.
users_export_clients() {
	[[ "$#" -eq 1 ]] || return 2
	local connection_id="$1" fd
	users_require_tools && users_lock fd || return 1
	jq --arg id "$connection_id" '[.[] | select(.connection_id == $id and .state == "draft") | {id:.uuid,email:.label}]' "$USER_DATA_FILE"
	users_unlock "$fd"
}

# Construye el modelo neutral para una conexión VLESS registrada y le adjunta
# las identidades locales en el formato clients esperado por vless_model.
users_build_vless_model() {
	[[ "$#" -eq 2 ]] || {
		printf 'Uso: users_build_vless_model <connection_id> <listen_address>\n' >&2
		return 2
	}
	local connection_id="$1" listen_address="$2" details protocol_id port clients
	details="$(users_connection_details "$connection_id")" || {
		printf 'La conexión no está disponible como borrador VLESS.\n' >&2
		return 1
	}
	IFS=$'\t' read -r _ _ protocol_id port _ <<<"$details"
	command -v vless_model_build >/dev/null 2>&1 || {
		printf 'El modelo neutral VLESS no está cargado.\n' >&2
		return 1
	}
	clients="$(users_export_clients "$connection_id")" || return 1
	vless_model_build "$connection_id" "$protocol_id" "$listen_address" "$port" |
		jq --argjson clients "$clients" '.users = $clients'
}
