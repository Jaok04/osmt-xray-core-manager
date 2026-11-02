#!/usr/bin/env bash
# Asistente de previsualización/validación VLESS. No persiste secretos ni aplica runtime.

connections_vless_assistant_read() {
	local prompt="$1" var_name="$2" value
	printf '%s' "$prompt"
	IFS= read -r value || return 1
	[[ -n "$value" ]] || return 1
	printf -v "$var_name" '%s' "$value"
}

connections_vless_assistant_read_secret() {
	local prompt="$1" var_name="$2" value
	printf '%s' "$prompt"
	IFS= read -r -s value || return 1
	printf '\n'
	[[ -n "$value" ]] || return 1
	printf -v "$var_name" '%s' "$value"
}

connections_vless_assistant() (
	[[ "$#" -eq 2 ]] || return 2
	local connection_id="$1" mode_id="$2" listen_address listen_port options_file model_file config_file tmp
	local path service_name tls_cert tls_key reality_target reality_private reality_names reality_ids xhttp_mode
	local users_json='[]' xray_bin="${XRAY_VALIDATION_BINARY:-/var/cache/xray-manager/validation/v26.10.31/xray}"
	command -v jq >/dev/null 2>&1 || {
		printf '\nSe requiere jq; no se generó configuración.\n'
		return 1
	}
	if ! command -v vless_model_build >/dev/null 2>&1 || ! command -v vless_xray_26_10_31_build >/dev/null 2>&1; then
		printf '\nEl modelo o adaptador VLESS no está cargado.\n'
		return 1
	fi
	printf '\n--- ASISTENTE VLESS: PREVISUALIZACIÓN ---\n'
	printf 'La configuración se construirá temporalmente; no se guardarán claves ni se aplicará al servicio.\n'
	connections_vless_assistant_read 'Dirección de escucha (ej. 127.0.0.1): ' listen_address || return 1
	listen_port="$(jq -r --arg id "$connection_id" '.[] | select(.id == $id) | .port' "$CONNECTION_DATA_FILE")" || return 1
	tmp="$(mktemp -d "${TMPDIR:-/tmp}/xray-vless-assistant.XXXXXX")" || return 1
	chmod 700 "$tmp"
	trap 'rm -rf "$tmp"' EXIT
	model_file="$tmp/model.json"
	options_file="$tmp/options.json"
	config_file="$tmp/xray.json"
	if declare -F users_build_vless_model >/dev/null 2>&1; then
		users_json="$(users_build_vless_model "$connection_id" "$listen_address")" || return 1
		printf '%s\n' "$users_json" >"$model_file"
	else
		vless_model_build "$connection_id" "$mode_id" "$listen_address" "$listen_port" >"$model_file" || return 1
	fi
	case "$mode_id" in
	vless_ws)
		connections_vless_assistant_read 'Ruta WebSocket (debe iniciar con /): ' path || return 1
		jq -n --arg path "$path" '{path:$path}' >"$options_file"
		;;
	vless_xhttp)
		connections_vless_assistant_read 'Ruta XHTTP (debe iniciar con /): ' path || return 1
		connections_vless_assistant_read 'Modo XHTTP (auto, packet-up, stream-up, stream-one): ' xhttp_mode || return 1
		jq -n --arg path "$path" --arg mode "$xhttp_mode" '{path:$path,mode:$mode}' >"$options_file"
		;;
	vless_tcp_tls | vless_ws_tls | vless_xhttp_tls | vless_grpc_tls)
		if [[ "$mode_id" == vless_xhttp_tls ]]; then
			connections_vless_assistant_read 'Ruta XHTTP: ' path || return 1
			connections_vless_assistant_read 'Modo XHTTP (auto, packet-up, stream-up, stream-one): ' xhttp_mode || return 1
		elif [[ "$mode_id" == vless_ws_tls ]]; then
			connections_vless_assistant_read 'Ruta WebSocket: ' path || return 1
		elif [[ "$mode_id" == vless_grpc_tls ]]; then
			connections_vless_assistant_read 'Nombre del servicio gRPC: ' service_name || return 1
		fi
		connections_vless_assistant_read 'Ruta del certificado TLS (archivo existente): ' tls_cert || return 1
		connections_vless_assistant_read 'Ruta de la clave privada TLS (archivo existente): ' tls_key || return 1
		case "$mode_id" in
		vless_xhttp_tls) jq -n --arg path "$path" --arg mode "$xhttp_mode" --arg certificate_file "$tls_cert" --arg key_file "$tls_key" '{path:$path,mode:$mode,certificate_file:$certificate_file,key_file:$key_file}' >"$options_file" ;;
		vless_ws_tls) jq -n --arg path "$path" --arg certificate_file "$tls_cert" --arg key_file "$tls_key" '{path:$path,certificate_file:$certificate_file,key_file:$key_file}' >"$options_file" ;;
		vless_grpc_tls) jq -n --arg service_name "$service_name" --arg certificate_file "$tls_cert" --arg key_file "$tls_key" '{service_name:$service_name,certificate_file:$certificate_file,key_file:$key_file}' >"$options_file" ;;
		*) jq -n --arg certificate_file "$tls_cert" --arg key_file "$tls_key" '{certificate_file:$certificate_file,key_file:$key_file}' >"$options_file" ;;
		esac
		;;
	vless_reality | vless_grpc_reality | vless_xhttp_reality)
		if [[ "$mode_id" == vless_grpc_reality ]]; then connections_vless_assistant_read 'Nombre del servicio gRPC: ' service_name || return 1; fi
		if [[ "$mode_id" == vless_xhttp_reality ]]; then
			connections_vless_assistant_read 'Ruta XHTTP: ' path || return 1
			connections_vless_assistant_read 'Modo XHTTP (auto, packet-up, stream-up, stream-one): ' xhttp_mode || return 1
		fi
		connections_vless_assistant_read 'Target REALITY (host:puerto): ' reality_target || return 1
		connections_vless_assistant_read_secret 'Private key REALITY (entrada oculta): ' reality_private || return 1
		connections_vless_assistant_read 'Server names (separados por comas): ' reality_names || return 1
		connections_vless_assistant_read 'Short IDs hexadecimales (separados por comas): ' reality_ids || return 1
		jq -n --arg target "$reality_target" --arg private_key "$reality_private" --arg names "$reality_names" --arg ids "$reality_ids" --arg service_name "$service_name" --arg path "$path" --arg mode "$xhttp_mode" '
				{target:$target,private_key:$private_key,server_names:($names|split(",")),short_ids:($ids|split(","))} +
				(if $service_name != "" then {service_name:$service_name} else {} end) +
				(if $path != "" then {path:$path,mode:$mode} else {} end)' >"$options_file"
		;;
	*)
		printf '\nModalidad VLESS no compatible con este asistente.\n'
		return 1
		;;
	esac
	if ! vless_xray_26_10_31_build "$model_file" "$options_file" >"$config_file"; then
		printf '\nNo se pudo construir la configuración. Revisa las opciones; el borrador se conserva.\n'
		return 1
	fi
	if [[ -x "$xray_bin" ]]; then
		if ! "$xray_bin" run -test -config "$config_file"; then
			printf '\nXray rechazó la configuración. El borrador se conserva y no se aplicó nada.\n'
			return 1
		fi
		printf '\nVALIDACIÓN CORRECTA: Xray aceptó la configuración temporal.\n'
	else
		printf '\nVALIDACIÓN PARCIAL: el adaptador generó la configuración, pero no se encontró el binario de validación: %s\n' "$xray_bin"
	fi
	printf 'El resultado y los secretos temporales se eliminarán al salir del asistente.\n'
	printf 'El registro continúa en estado draft; runtime_applied permanece false.\n'
	ui_pause
)
