#!/usr/bin/env bash
# Modelo neutral VMess. No genera ni aplica configuración Xray.
vmess_model_resolve_mode() {
    [[ $# -eq 1 ]] || return 1
    case "$1" in
    vmess_ws) printf 'websocket|none\n' ;;
    vmess_tcp_tls) printf 'raw|tls\n' ;;
    vmess_ws_tls) printf 'websocket|tls\n' ;;
    vmess_reality) printf 'raw|reality\n' ;;
    vmess_grpc) printf 'grpc|none\n' ;;
    vmess_grpc_tls) printf 'grpc|tls\n' ;;
    vmess_grpc_reality) printf 'grpc|reality\n' ;;
    vmess_httpupgrade) printf 'httpupgrade|none\n' ;;
    vmess_httpupgrade_tls) printf 'httpupgrade|tls\n' ;;
    vmess_xhttp) printf 'xhttp|none\n' ;;
    vmess_xhttp_tls) printf 'xhttp|tls\n' ;;
    vmess_xhttp_reality) printf 'xhttp|reality\n' ;;
    vmess_mkcp) printf 'mkcp|none\n' ;;
    vmess_mkcp_tls) printf 'mkcp|tls\n' ;;
    *) return 1 ;;
    esac
}
vmess_model_validate_users() {
    [[ $# -eq 1 ]] || return 2
    command -v jq >/dev/null 2>&1 || return 1
    [[ -r "$1" ]] || return 1
    jq -e '
		type == "array" and length >= 1 and length <= 1000 and
		all(.[]; type == "object" and
			(keys - ["id","level","email"] | length) == 0 and
			(.id | type == "string" and test("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89aAbB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$")) and
			(.level | type == "number" and floor == . and . >= 0 and . <= 255) and
			(.email | type == "string" and length >= 1 and length <= 255)
		) and ([.[].id | ascii_downcase] | length == (unique | length))
	' "$1" >/dev/null
}
# Uso: vmess_model_build <connection_id> <mode_id> <listen_address> <listen_port> <users.json>
vmess_model_build() {
    [[ $# -eq 5 ]] || {
        printf 'Uso: vmess_model_build <connection_id> <mode_id> <listen_address> <listen_port> <users.json>\n' >&2
        return 2
    }
    local cid="$1" mode="$2" address="$3" port="$4" users_file="$5" resolved transport security
    [[ "$cid" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$ ]] || return 2
    [[ -n "$address" && ${#address} -le 255 && ! "$address" =~ [[:space:]] ]] || return 2
    [[ "$port" =~ ^[0-9]{1,5}$ ]] && ((10#$port >= 1 && 10#$port <= 65535)) || return 2
    resolved="$(vmess_model_resolve_mode "$mode")" || {
        printf 'Modalidad VMess no admitida.\n' >&2
        return 2
    }
    IFS='|' read -r transport security <<<"$resolved"
    [[ -r "$users_file" ]] && vmess_model_validate_users "$users_file" || {
        printf 'Lista de usuarios VMess inválida.\n' >&2
        return 2
    }
    jq -n --arg cid "$cid" --arg mode "$mode" --arg transport "$transport" --arg security "$security" --arg address "$address" --argjson port "$((10#$port))" --slurpfile users "$users_file" '
		{schema_version:1,connection_id:$cid,protocol:"vmess",mode_id:$mode,transport:$transport,security:$security,
		 listen_address:$address,listen_port:$port,transport_options:{},security_options:{},users:$users[0]}
	'
}