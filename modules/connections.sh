#!/usr/bin/env bash
# shellcheck disable=SC2016,SC2034
if ! declare -F json_store_commit >/dev/null 2>&1; then
	# shellcheck disable=SC1091
	source "${APP_ROOT:-/opt/xray-manager}/lib/json_store.sh"
fi
CONNECTION_CATALOG="${APP_ROOT:-/opt/xray-manager}/config/protocols.tsv"
CONNECTION_DATA_DIR="${XRAY_MANAGER_CONNECTIONS_DIR:-/var/lib/xray-manager/connections}"
CONNECTION_DATA_FILE="${XRAY_MANAGER_CONNECTIONS_FILE:-/var/lib/xray-manager/connections/connections.json}"
CONNECTION_LOCK="${XRAY_MANAGER_INTEGRITY_LOCK:-${XRAY_MANAGER_CONNECTIONS_LOCK:-/run/xray-manager/integrity.lock}}"

connections_menu() {
	local option
	while true; do
		ui_clear
		ui_title "GESTIÓN DE PROTOCOLOS Y CONEXIONES"
		printf '\n  PROTOCOLOS PRINCIPALES\n  [1] VLESS\n  [2] VMess\n  [3] Trojan\n  [4] Shadowsocks\n  [5] Hysteria2\n'
		printf '\n  PROTOCOLOS OPCIONALES\n  [6] Protocolos opcionales\n  [0] Volver al menú principal\n\n'
		ui_read_option "Selecciona una opción: " option
		case "$option" in
			1) connections_family_menu vless ;;
			2) connections_family_menu vmess ;;
			3) connections_family_menu trojan ;;
			4) connections_family_menu shadowsocks ;;
			5) connections_family_menu hysteria2 ;;
			6) connections_optional_menu ;;
			0) return 0 ;;
			*) printf '\nOpción no válida.\n'; ui_pause ;;
		esac
	done
}
connections_family_menu() {
	local family="$1" option
	while true; do
		ui_clear
		case "$family" in
			vless)
				ui_title "ADMINISTRAR VLESS"
				printf '\n  [1] VLESS-WS (Sin TLS)\n  [2] VLESS-TLS (RAW/TCP + TLS)\n  [3] VLESS-WS-TLS\n  [4] VLESS-REALITY (RAW/TCP + REALITY)\n  [5] VLESS-GRPC (TLS o REALITY)\n  [6] VLESS-XHTTP (Sin TLS)\n  [7] VLESS-XHTTP-TLS\n  [8] VLESS-XHTTP-REALITY\n'
				;;
			vmess)
				ui_title "ADMINISTRAR VMESS"
				printf '\n  PRINCIPALES\n  [1] VMess-WS\n  [2] VMess-TLS\n  [3] VMess-WS-TLS\n  [4] VMess-REALITY\n  [5] VMess-GRPC\n  ADICIONALES\n  [6] VMess-HTTPUpgrade\n  [7] VMess-XHTTP\n  [8] VMess-mKCP\n'
				;;
			trojan)
				ui_title "ADMINISTRAR TROJAN"
				printf '\n  PRINCIPALES\n  [1] Trojan-TLS\n  [2] Trojan-WS-TLS\n  [3] Trojan-GRPC-TLS\n  ADICIONALES\n  [4] Trojan-XHTTP-TLS\n  [5] Trojan-HTTPUpgrade-TLS\n'
				;;
			shadowsocks)
				ui_title "ADMINISTRAR SHADOWSOCKS"
				printf '\n  [1] Shadowsocks-TCP\n  [2] Shadowsocks-UDP\n  [3] Shadowsocks-TCP-UDP\n  OFUSCACIÓN / PLUGINS\n  [4] Shadowsocks + OBFS\n  [5] Shadowsocks + V2Ray-Plugin\n'
				;;
			hysteria2)
				ui_title "ADMINISTRAR HYSTERIA 2"
				printf '\n  [1] Hysteria2-QUIC (UDP + TLS)\n'
				;;
			*) printf '\nFamilia desconocida.\n'; return 1 ;;
		esac
		printf '  [0] Volver\n\n'
		ui_read_option "Selecciona una modalidad: " option
		[[ "$option" == 0 ]] && return 0
		case "$family:$option" in
			vless:1) connections_manage_mode vless_ws ;;
			vless:2) connections_manage_mode vless_tcp_tls ;;
			vless:3) connections_manage_mode vless_ws_tls ;;
			vless:4) connections_manage_mode vless_reality ;;
			vless:5) connections_manage_mode vless_grpc ;;
			vless:6) connections_manage_mode vless_xhttp ;;
			vless:7) connections_manage_mode vless_xhttp_tls ;;
			vless:8) connections_manage_mode vless_xhttp_reality ;;
			vmess:1) connections_manage_mode vmess_ws ;;
			vmess:2) connections_manage_mode vmess_tcp_tls ;;
			vmess:3) connections_manage_mode vmess_ws_tls ;;
			vmess:4) connections_manage_mode vmess_reality ;;
			vmess:5) connections_manage_mode vmess_grpc ;;
			vmess:6) connections_manage_mode vmess_httpupgrade ;;
			vmess:7) connections_manage_mode vmess_xhttp ;;
			vmess:8) connections_manage_mode vmess_mkcp ;;
			trojan:1) connections_manage_mode trojan_tcp_tls ;;
			trojan:2) connections_manage_mode trojan_ws_tls ;;
			trojan:3) connections_manage_mode trojan_grpc_tls ;;
			trojan:4) connections_manage_mode trojan_xhttp_tls ;;
			trojan:5) connections_manage_mode trojan_httpupgrade_tls ;;
			shadowsocks:1) connections_manage_mode shadowsocks_tcp ;;
			shadowsocks:2) connections_manage_mode shadowsocks_udp ;;
			shadowsocks:3) connections_manage_mode shadowsocks_tcp_udp ;;
			shadowsocks:4) connections_shadowsocks_obfs_menu ;;
			shadowsocks:5) connections_manage_mode shadowsocks_v2ray_plugin ;;
			hysteria2:1) connections_manage_mode hysteria2_quic_tls ;;
			*) printf '\nOpción no válida.\n'; ui_pause ;;
		esac
	done
}
connections_shadowsocks_obfs_menu() {
	local option
	while true; do
		ui_clear
		ui_title "SHADOWSOCKS - OBFS"
		printf '\n  [1] OBFS-HTTP (plugin externo)\n  [2] OBFS-TLS (plugin externo)\n  [0] Volver\n\n'
		ui_read_option "Selecciona una opción: " option
		case "$option" in
			1) connections_manage_mode shadowsocks_obfs_http ;;
			2) connections_manage_mode shadowsocks_obfs_tls ;;
			0) return 0 ;;
			*) printf '\nOpción no válida.\n'; ui_pause ;;
		esac
	done
}
connections_optional_menu() {
	local option
	while true; do
		ui_clear
		ui_title "PROTOCOLOS OPCIONALES"
		printf '\n  PROXIES AUXILIARES\n  [1] SOCKS\n  [2] HTTP Proxy\n'
		printf '\n  TÚNELES Y REDES\n  [3] WireGuard\n  [0] Volver\n\n'
		ui_read_option "Selecciona un protocolo: " option
		case "$option" in
			1) connections_manage_mode socks_tcp ;;
			2) connections_manage_mode http_tcp ;;
			3) connections_manage_mode wireguard_udp ;;
			0) return 0 ;;
			*) printf '\nOpción no válida.\n'; ui_pause ;;
		esac
	done
}
connections_mode_label() {
	case "$1" in
		vless_ws) printf 'VLESS-WS (Sin TLS)' ;;
		vless_tcp_tls) printf 'VLESS-TLS (RAW/TCP + TLS)' ;;
		vless_ws_tls) printf 'VLESS-WS-TLS' ;;
		vless_reality) printf 'VLESS-REALITY' ;;
		vless_grpc_tls) printf 'VLESS-GRPC-TLS' ;;
		vless_grpc_reality) printf 'VLESS-GRPC-REALITY' ;;
		vless_grpc) printf 'VLESS-GRPC' ;;
		vless_xhttp) printf 'VLESS-XHTTP (Sin TLS)' ;;
		vless_xhttp_tls) printf 'VLESS-XHTTP-TLS' ;;
		vless_xhttp_reality) printf 'VLESS-XHTTP-REALITY' ;;
		vmess_ws) printf 'VMess-WS' ;;
		vmess_tcp_tls) printf 'VMess-TLS' ;;
		vmess_ws_tls) printf 'VMess-WS-TLS' ;;
		vmess_reality) printf 'VMess-REALITY' ;;
		vmess_grpc) printf 'VMess-GRPC (selección de seguridad)' ;;
		vmess_grpc_tls) printf 'VMess-GRPC-TLS' ;;
		vmess_grpc_reality) printf 'VMess-GRPC-REALITY' ;;
		vmess_httpupgrade) printf 'VMess-HTTPUpgrade sin TLS' ;;
		vmess_httpupgrade_tls) printf 'VMess-HTTPUpgrade-TLS' ;;
		vmess_xhttp) printf 'VMess-XHTTP (selección de seguridad)' ;;
		vmess_xhttp_tls) printf 'VMess-XHTTP-TLS' ;;
		vmess_xhttp_reality) printf 'VMess-XHTTP-REALITY' ;;
		vmess_mkcp) printf 'VMess-mKCP sin TLS' ;;
		vmess_mkcp_tls) printf 'VMess-mKCP-TLS' ;;
		trojan_tcp_tls) printf 'Trojan-TLS' ;;
		trojan_ws_tls) printf 'Trojan-WS-TLS' ;;
		trojan_grpc_tls) printf 'Trojan-GRPC-TLS' ;;
		trojan_xhttp_tls) printf 'Trojan-XHTTP-TLS' ;;
		trojan_httpupgrade_tls) printf 'Trojan-HTTPUpgrade-TLS' ;;
		shadowsocks_tcp) printf 'Shadowsocks-TCP' ;;
		shadowsocks_udp) printf 'Shadowsocks-UDP' ;;
		shadowsocks_tcp_udp) printf 'Shadowsocks-TCP-UDP' ;;
		shadowsocks_obfs_http) printf 'Shadowsocks + OBFS-HTTP' ;;
		shadowsocks_obfs_tls) printf 'Shadowsocks + OBFS-TLS' ;;
		shadowsocks_v2ray_plugin) printf 'Shadowsocks + V2Ray-Plugin' ;;
		hysteria2_quic_tls) printf 'Hysteria2-QUIC (UDP + TLS)' ;;
		socks_tcp) printf 'SOCKS' ;;
		http_tcp) printf 'HTTP Proxy' ;;
		wireguard_udp) printf 'WireGuard' ;;
		*) printf '%s' "$1" ;;
	esac
}
connections_resolve_mode() {
	local mode_key="$1" option
	# shellcheck disable=SC2034
	local -n result_ref="$2"
	case "$mode_key" in
		vless_grpc)
			printf '\nSeguridad VLESS-GRPC:\n  [1] TLS\n  [2] REALITY\n  [0] Cancelar\n'
			ui_read_option "Selecciona seguridad: " option
			case "$option" in 1) result_ref=vless_grpc_tls ;; 2) result_ref=vless_grpc_reality ;; *) return 1 ;; esac
			;;
		vmess_grpc)
			printf '\nSeguridad VMess-GRPC:\n  [1] Sin TLS\n  [2] TLS\n  [3] REALITY\n  [0] Cancelar\n'
			ui_read_option "Selecciona seguridad: " option
			case "$option" in 1) result_ref=vmess_grpc ;; 2) result_ref=vmess_grpc_tls ;; 3) result_ref=vmess_grpc_reality ;; *) return 1 ;; esac
			;;
		vmess_xhttp)
			printf '\nSeguridad VMess-XHTTP:\n  [1] Sin TLS\n  [2] TLS\n  [3] REALITY\n  [0] Cancelar\n'
			ui_read_option "Selecciona seguridad: " option
			case "$option" in 1) result_ref=vmess_xhttp ;; 2) result_ref=vmess_xhttp_tls ;; 3) result_ref=vmess_xhttp_reality ;; *) return 1 ;; esac
			;;
		vmess_mkcp)
			printf '\nSeguridad VMess-mKCP:\n  [1] Sin TLS\n  [2] TLS\n  [0] Cancelar\n'
			ui_read_option "Selecciona seguridad: " option
			case "$option" in 1) result_ref=vmess_mkcp ;; 2) result_ref=vmess_mkcp_tls ;; *) return 1 ;; esac
			;;
		*) result_ref="$mode_key" ;;
	esac
}
connections_manage_mode() {
	local selected="$1" resolved option
	if ! connections_resolve_mode "$selected" resolved; then return 0; fi
	while true; do
		ui_clear
		ui_title "ADMINISTRAR $(connections_mode_label "$resolved")"
		printf '\n  [1] Crear una configuración nueva\n  [2] Administrar configuraciones existentes\n  [0] Volver\n\n'
		ui_read_option "Selecciona una opción: " option
		case "$option" in
			1) connections_create_draft "$resolved" || true ;;
			2) connections_manage_existing "$resolved" || true ;;
			0) return 0 ;;
			*) printf '\nOpción no válida.\n'; ui_pause ;;
		esac
	done
}
connections_manage_existing() {
	local protocol_id="$1" fd list_json option selected_id
	if ! connections_require_storage_tools || ! connections_lock fd; then
		printf '\nNo fue posible consultar las conexiones.\n'
		ui_pause
		return 1
	fi
	list_json="$(jq --arg p "$protocol_id" '[.[] | select(.protocol_id == $p)]' "$CONNECTION_DATA_FILE")"
	connections_unlock "$fd"
	if [[ "$(jq 'length' <<<"$list_json")" -eq 0 ]]; then
		printf '\nNo hay configuraciones disponibles para este protocolo o modalidad.\n'
		printf '[0] Volver\n'
		ui_pause
		return 0
	fi
	while true; do
		ui_clear
		ui_title "CONEXIONES $(connections_mode_label "$protocol_id")"
		jq -r 'to_entries[] | "[\(.key + 1)] \(.value.name) - puerto \(.value.port) [\(.value.state)]"' <<<"$list_json"
		printf '\n[0] Volver\n'
		ui_read_option "Selecciona una conexión: " option
		if [[ "$option" == 0 ]]; then return 0; fi
		if [[ ! "$option" =~ ^[0-9]+$ ]] || ((10#$option < 1 || 10#$option > $(jq 'length' <<<"$list_json"))); then
			printf '\nSelección no válida.\n'
			ui_pause
			continue
		fi
		selected_id="$(jq -r --argjson idx "$((10#$option-1))" '.[$idx].id' <<<"$list_json")"
		connections_existing_menu "$selected_id"
		if ! connections_require_storage_tools || ! connections_lock fd; then return 1; fi
		list_json="$(jq --arg p "$protocol_id" '[.[] | select(.protocol_id == $p)]' "$CONNECTION_DATA_FILE")"
		connections_unlock "$fd"
		if [[ "$(jq 'length' <<<"$list_json")" -eq 0 ]]; then
			printf '\nNo quedan configuraciones para esta modalidad.\n'
			ui_pause
			return 0
		fi
	done
}
connections_existing_menu() {
	local id="$1" option fd state name protocol_id port has_configuration
	while true; do
		if ! connections_require_storage_tools || ! connections_lock fd; then
			printf '\nNo fue posible consultar la conexión.\n'
			ui_pause
			return 1
		fi
		if ! jq -e --arg id "$id" 'any(.[]; .id == $id)' "$CONNECTION_DATA_FILE" >/dev/null; then
			connections_unlock "$fd"
			printf '\nLa conexión ya no existe.\n'
			ui_pause
			return 0
		fi
		state="$(jq -r --arg id "$id" '.[] | select(.id == $id) | .state' "$CONNECTION_DATA_FILE")"
		name="$(jq -r --arg id "$id" '.[] | select(.id == $id) | .name' "$CONNECTION_DATA_FILE")"
		protocol_id="$(jq -r --arg id "$id" '.[] | select(.id == $id) | .protocol_id' "$CONNECTION_DATA_FILE")"
		port="$(jq -r --arg id "$id" '.[] | select(.id == $id) | .port' "$CONNECTION_DATA_FILE")"
		has_configuration="$(jq -r --arg id "$id" 'any(.[]; .id == $id and (.configuration_ref | type == "string"))' "$CONNECTION_DATA_FILE")"
		connections_unlock "$fd"
		ui_clear
		ui_title "ADMINISTRAR CONEXIÓN"
		printf '\nNombre: %s\nID: %s\nModalidad: %s\nPuerto: %s\nEstado: %s\n' "$name" "$id" "$protocol_id" "$port" "$state"
		printf '\n  [1] Consultar detalles\n'
		if [[ "$state" == draft ]]; then
			printf '  [2] Editar borrador\n  [3] Eliminar borrador\n'
			if [[ "$has_configuration" == true ]]; then printf '  [4] Recuperar y validar configuración guardada\n'; fi
		fi
		printf '  [0] Volver\n\n'
		ui_read_option "Selecciona una opción: " option
		case "$option" in
			1) connections_show_existing_detail "$id" ;;
			2)
				if [[ "$state" == draft ]]; then connections_edit_draft "$id" || true; else printf '\nOperación no disponible.\n'; ui_pause; fi
				;;
			3)
				if [[ "$state" == draft ]]; then connections_delete_draft "$id" || true; else printf '\nOperación no disponible.\n'; ui_pause; fi
				return 0
				;;
			4)
				if [[ "$state" == draft && "$has_configuration" == true ]] && declare -F connections_vless_assistant_restore >/dev/null 2>&1; then
					connections_vless_assistant_restore "$id" "$protocol_id" || true
				else printf '\nNo hay una configuración VLESS recuperable.\n'; ui_pause; fi
				;;
			0) return 0 ;;
			*) printf '\nOpción no válida.\n'; ui_pause ;;
		esac
	done
}
connections_show_existing_detail() {
	local id="$1" fd
	if ! connections_require_storage_tools || ! connections_lock fd; then
		printf '\nNo fue posible consultar la conexión.\n'
		ui_pause
		return 1
	fi
	jq -r --arg id "$id" '.[] | select(.id == $id) | "Nombre: \(.name)\nID: \(.id)\nModalidad: \(.protocol_id)\nPuerto: \(.port)\nSlots: \(.max_users)\nEstado: \(.state)\nAplicada a runtime: \(.runtime_applied)\nRevisión guardada: \(.configuration_revision // "ninguna")\nReferencia de configuración: \(.configuration_ref // "ninguna")\nReferencia de secreto: \(.secret_ref // "ninguna")\nCreada: \(.created_at)"' "$CONNECTION_DATA_FILE"
	connections_unlock "$fd"
	ui_pause
}
connections_show_catalog() {
	local id name detail
	ui_clear
	ui_title "CATÁLOGO DE PROTOCOLOS"
	printf '%-28s | %-42s | %s\n' "IDENTIFICADOR" "MODALIDAD" "TRANSPORTE / SEGURIDAD"
	ui_line
	while IFS='|' read -r id name detail; do
		[[ -z "$id" || "$id" == \#* ]] && continue
		printf '%-28s | %-42s | %s\n' "$id" "$name" "$detail"
	done <"$CONNECTION_CATALOG"
	printf '\nNota: el catálogo expresa modalidades previstas; no confirma que Xray esté instalado ni que estén aplicadas.\n'
	printf 'Los plugins externos de Shadowsocks requieren instalación y validación independiente.\n'
}
connections_valid_protocol() {
	local wanted="$1" id name detail
	while IFS='|' read -r id name detail; do [[ "$id" == "$wanted" ]] && return 0; done <"$CONNECTION_CATALOG"
	return 1
}
connections_trim_name() {
	local value="$1"
	value="${value#"${value%%[![:space:]]*}"}"
	value="${value%"${value##*[![:space:]]}"}"
	printf '%s' "$value"
}
connections_require_storage_tools() { command -v jq >/dev/null 2>&1 && command -v flock >/dev/null 2>&1 && command -v ss >/dev/null 2>&1; }
connections_port_in_use() {
	local port="$1"
	ss -H -lntu 2>/dev/null | awk -v p="$port" '$5 ~ ":" p "$" { found = 1 } END { exit !found }'
}
connections_lock() {
	local -n fd_ref="$1"
	mkdir -p "$CONNECTION_DATA_DIR" "$(dirname "$CONNECTION_LOCK")"
	exec {fd_ref}>"$CONNECTION_LOCK"
	flock -x "$fd_ref"
	if [[ ! -e "$CONNECTION_DATA_FILE" ]]; then
		printf '%s\n' '[]' >"$CONNECTION_DATA_FILE"
		chmod 600 "$CONNECTION_DATA_FILE"
	fi
	if ! jq -e 'type == "array"' "$CONNECTION_DATA_FILE" >/dev/null 2>&1; then
		flock -u "$fd_ref"
		exec {fd_ref}>&-
		printf '\nEl archivo de conexiones no contiene un arreglo JSON válido. No se sobrescribió.\n' >&2
		return 1
	fi
}
connections_unlock() {
	local fd="$1"
	flock -u "$fd"
	exec {fd}>&-
}
connections_atomic_update() {
	local fd="$1" tmp rc
	shift
	tmp="$(mktemp "$CONNECTION_DATA_DIR/.connections.XXXXXX")" || return 1
	if ! jq "$@" "$CONNECTION_DATA_FILE" >"$tmp"; then
		rm -f "$tmp"
		return 1
	fi
	if ! jq -e 'type == "array" and all(.[]; type == "object" and
        (.id | type == "string" and length > 0) and
        (.name | type == "string" and length > 0) and
        (.protocol_id | type == "string" and length > 0) and
        (.port | type == "number" and floor == . and . >= 1 and . <= 65535) and
        (.max_users | type == "number" and floor == . and . >= 1 and . <= 100000) and
        (.state | type == "string" and length > 0) and
        (.runtime_applied | type == "boolean") and
        (.created_at | type == "string")) and
        ([.[].id] | length == (unique | length)) and
        ([.[].port] | length == (unique | length))' "$tmp" >/dev/null; then
		rm -f "$tmp"
		return 1
	fi
	if json_store_commit "$tmp" "$CONNECTION_DATA_FILE" 600; then
		:
	else
		rc=$?
		if ((rc == 3)); then
			printf 'ADVERTENCIA: la conexión quedó guardada, pero no se pudo confirmar la sincronización del directorio.\n' >&2
		else
			rm -f "$tmp"
			return 1
		fi
	fi
}
connections_create_draft() {
	local name protocol_id="${1:-}" port max_users id created_at fd
	ui_clear
	ui_title "REGISTRAR CONEXIÓN - BORRADOR"
	printf '\nEste registro no configura Xray ni abre puertos.\n\nNombre descriptivo: '
	IFS= read -r name || return 0
	name="$(connections_trim_name "$name")"
	if [[ -z "$name" || "${#name}" -gt 64 ]]; then
		printf '\nNombre vacío o demasiado largo (máximo 64).\n'
		ui_pause
		return 1
	fi
	if [[ -z "$protocol_id" ]]; then
		printf '\nIdentificadores disponibles:\n'
		connections_show_catalog
		printf '\nIdentificador exacto de modalidad: '
		IFS= read -r protocol_id || return 0
	fi
	if ! connections_valid_protocol "$protocol_id"; then
		printf '\nModalidad no reconocida.\n'
		ui_pause
		return 1
	fi
	printf 'Puerto previsto (1-65535): '
	IFS= read -r port || return 0
	if [[ ! "$port" =~ ^[0-9]{1,5}$ ]] || ((10#$port < 1 || 10#$port > 65535)); then
		printf '\nPuerto inválido.\n'
		ui_pause
		return 1
	fi
	port=$((10#$port))
	printf 'Límite máximo de usuarios/slots (1-100000): '
	IFS= read -r max_users || return 0
	if [[ ! "$max_users" =~ ^[0-9]{1,6}$ ]] || ((10#$max_users < 1 || 10#$max_users > 100000)); then
		printf '\nLímite inválido.\n'
		ui_pause
		return 1
	fi
	max_users=$((10#$max_users))
	if ! connections_require_storage_tools; then
		printf '\nSe requieren jq y flock.\n'
		ui_pause
		return 1
	fi
	if ! connections_lock fd; then
		ui_pause
		return 1
	fi
	if connections_port_in_use "$port"; then
		connections_unlock "$fd"
		printf '\nEl puerto ya está ocupado por un socket TCP/UDP del sistema.\n'
		ui_pause
		return 1
	fi
	if jq -e --argjson port "$port" '.[] | select(.port == $port)' "$CONNECTION_DATA_FILE" >/dev/null; then
		connections_unlock "$fd"
		printf '\nPuerto ya reservado en el registro.\n'
		ui_pause
		return 1
	fi
	id="conn-$(date +%s)-$$"
	created_at="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
	if ! connections_atomic_update "$fd" --arg id "$id" --arg name "$name" --arg protocol_id "$protocol_id" --argjson port "$port" --argjson max_users "$max_users" --arg created_at "$created_at" '. + [{id:$id,name:$name,protocol_id:$protocol_id,port:$port,max_users:$max_users,state:"draft",runtime_applied:false,created_at:$created_at}]'; then
		connections_unlock "$fd"
		printf '\nError al guardar el registro.\n'
		ui_pause
		return 1
	fi
	connections_unlock "$fd"
	printf '\nConexión registrada como borrador.\nID: %s\nNombre: %s\nModalidad: %s\nPuerto: %s\nSlots: %s\n' "$id" "$name" "$protocol_id" "$port" "$max_users"
	printf '\nNo se aplicó ningún cambio a Xray ni al sistema.\n'
	if [[ "$protocol_id" == vless_* ]] && declare -F connections_vless_assistant >/dev/null 2>&1; then
		connections_vless_assistant "$id" "$protocol_id" || true
	fi
	ui_pause
}
connections_list() {
	local fd
	ui_clear
	ui_title "CONEXIONES REGISTRADAS"
	if ! connections_require_storage_tools || ! connections_lock fd; then
		printf '\nNo fue posible consultar el registro.\n'
		return 1
	fi
	if [[ "$(jq 'length' "$CONNECTION_DATA_FILE")" -eq 0 ]]; then
		printf '\nTodavía no hay conexiones registradas.\n'
		connections_unlock "$fd"
		return 0
	fi
	jq -r '.[] | "ID: \(.id)\nNombre: \(.name)\nModalidad: \(.protocol_id)\nPuerto: \(.port)\nSlots: \(.max_users)\nEstado: \(.state)\nAplicada a runtime: \(.runtime_applied)\n"' "$CONNECTION_DATA_FILE"
	connections_unlock "$fd"
}
connections_edit_draft() {
	local id="${1:-}" name protocol_id port max_users fd state
	ui_clear
	ui_title "EDITAR CONEXIÓN - BORRADOR"
	if [[ -z "$id" ]]; then
		printf '\nID exacto: '
		IFS= read -r id || return 0
	fi
	if ! connections_require_storage_tools || ! connections_lock fd; then
		printf '\nNo fue posible acceder al registro.\n'
		ui_pause
		return 1
	fi
	state="$(jq -r --arg id "$id" '.[] | select(.id == $id) | .state' "$CONNECTION_DATA_FILE")"
	if [[ "$state" != "draft" ]]; then
		connections_unlock "$fd"
		printf '\nNo existe o no está en estado draft; no se modifica.\n'
		ui_pause
		return 1
	fi
	printf 'Nuevo nombre (vacío conserva): '
	IFS= read -r name || {
		connections_unlock "$fd"
		return 0
	}
	printf 'Nuevo ID de modalidad (vacío conserva): '
	IFS= read -r protocol_id || {
		connections_unlock "$fd"
		return 0
	}
	printf 'Nuevo puerto (vacío conserva): '
	IFS= read -r port || {
		connections_unlock "$fd"
		return 0
	}
	printf 'Nuevo límite de slots (vacío conserva): '
	IFS= read -r max_users || {
		connections_unlock "$fd"
		return 0
	}
	name="$(connections_trim_name "$name")"
	if [[ -n "$name" && "${#name}" -gt 64 ]]; then
		connections_unlock "$fd"
		printf '\nNombre demasiado largo.\n'
		ui_pause
		return 1
	fi
	if [[ -n "$protocol_id" ]] && ! connections_valid_protocol "$protocol_id"; then
		connections_unlock "$fd"
		printf '\nModalidad no reconocida.\n'
		ui_pause
		return 1
	fi
	if [[ -n "$port" ]]; then
		if [[ ! "$port" =~ ^[0-9]{1,5}$ ]] || ((10#$port < 1 || 10#$port > 65535)); then
			connections_unlock "$fd"
			printf '\nPuerto inválido.\n'
			ui_pause
			return 1
		fi
		port=$((10#$port))
		if connections_port_in_use "$port"; then
			connections_unlock "$fd"
			printf '\nEl puerto está ocupado por un socket TCP/UDP del sistema.\n'
			ui_pause
			return 1
		fi
		if jq -e --arg id "$id" --argjson port "$port" '.[] | select(.id != $id and .port == $port)' "$CONNECTION_DATA_FILE" >/dev/null; then
			connections_unlock "$fd"
			printf '\nPuerto reservado por otra conexión.\n'
			ui_pause
			return 1
		fi
	fi
	if [[ -n "$max_users" ]]; then
		if [[ ! "$max_users" =~ ^[0-9]{1,6}$ ]] || ((10#$max_users < 1 || 10#$max_users > 100000)); then
			connections_unlock "$fd"
			printf '\nLímite inválido.\n'
			ui_pause
			return 1
		fi
		max_users=$((10#$max_users))
	fi
	if ! connections_atomic_update "$fd" --arg id "$id" --arg name "$name" --arg protocol_id "$protocol_id" --arg port "$port" --arg max_users "$max_users" 'map(if .id == $id and .state == "draft" then . + (if $name == "" then {} else {name:$name} end) + (if $protocol_id == "" then {} else {protocol_id:$protocol_id} end) + (if $port == "" then {} else {port:($port|tonumber)} end) + (if $max_users == "" then {} else {max_users:($max_users|tonumber)} end) else . end)'; then
		connections_unlock "$fd"
		printf '\nNo se pudo guardar la edición.\n'
		ui_pause
		return 1
	fi
	connections_unlock "$fd"
	printf '\nBorrador actualizado. Runtime sin cambios.\n'
	ui_pause
}
connections_delete_draft() {
	local id="${1:-}" confirmation fd state users_file
	users_file="${USER_DATA_FILE:-${XRAY_MANAGER_USERS_FILE:-/var/lib/xray-manager/users/users.json}}"
	ui_clear
	ui_title "ELIMINAR CONEXIÓN - BORRADOR"
	if [[ -z "$id" ]]; then
		printf '\nID exacto: '
		IFS= read -r id || return 0
	fi
	if ! connections_require_storage_tools || ! connections_lock fd; then
		printf '\nNo fue posible acceder al registro.\n'
		ui_pause
		return 1
	fi
	state="$(jq -r --arg id "$id" '.[] | select(.id == $id) | .state' "$CONNECTION_DATA_FILE")"
	if [[ "$state" != "draft" ]]; then
		connections_unlock "$fd"
		printf '\nNo existe o no está en estado draft; no se elimina.\n'
		ui_pause
		return 1
	fi
	if [[ -e "$users_file" ]]; then
		if ! jq -e 'type == "array"' "$users_file" >/dev/null 2>&1; then
			connections_unlock "$fd"
			printf '\nEl registro de usuarios no es válido; se bloqueó la eliminación para evitar perder asociaciones.\n'
			ui_pause
			return 1
		fi
		if jq -e --arg id "$id" 'any(.[]; .connection_id == $id)' "$users_file" >/dev/null; then
			connections_unlock "$fd"
			printf '\nNo se puede eliminar: la conexión tiene usuarios asociados. Elimina primero esos usuarios.\n'
			ui_pause
			return 1
		fi
	fi
	printf 'Para confirmar, escribe ELIMINAR: '
	IFS= read -r confirmation || {
		connections_unlock "$fd"
		return 0
	}
	if [[ "$confirmation" != "ELIMINAR" ]]; then
		connections_unlock "$fd"
		printf '\nOperación cancelada.\n'
		ui_pause
		return 0
	fi
	if ! connections_atomic_update "$fd" --arg id "$id" 'map(select(.id != $id))'; then
		connections_unlock "$fd"
		printf '\nNo se pudo eliminar el borrador.\n'
		ui_pause
		return 1
	fi
	connections_unlock "$fd"
	printf '\nBorrador eliminado. Xray y el sistema no fueron modificados.\n'
	ui_pause
}