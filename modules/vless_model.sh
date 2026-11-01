#!/usr/bin/env bash
# Modelo neutral VLESS: validación pura, sin serializar configuración Xray.

vless_model_resolve_mode() {
    local mode_id="$1"
    case "$mode_id" in
        vless_ws) printf '%s|%s\n' 'websocket' 'none' ;;
        vless_tcp_tls) printf '%s|%s\n' 'raw' 'tls' ;;
        vless_ws_tls) printf '%s|%s\n' 'websocket' 'tls' ;;
        vless_reality) printf '%s|%s\n' 'raw' 'reality' ;;
        vless_grpc_tls) printf '%s|%s\n' 'grpc' 'tls' ;;
        vless_grpc_reality) printf '%s|%s\n' 'grpc' 'reality' ;;
        *) return 1 ;;
    esac
}

# Uso: vless_model_build <connection_id> <mode_id> <listen_address> <listen_port>
# Emite el modelo neutral JSON por stdout. No crea archivos ni modifica el sistema.
vless_model_build() {
    local connection_id="$1" mode_id="$2" listen_address="$3" listen_port="$4"
    local resolved transport security

    if [[ -z "$connection_id" || "${#connection_id}" -gt 128 || "$connection_id" == *$'\n'* ]]; then
        printf 'ID de conexión vacío o inválido.\n' >&2
        return 2
    fi
    if ! resolved="$(vless_model_resolve_mode "$mode_id")"; then
        printf 'Modalidad VLESS no admitida: %s\n' "$mode_id" >&2
        return 2
    fi
    IFS='|' read -r transport security <<<"$resolved"
    if [[ -z "$listen_address" || "${#listen_address}" -gt 255 || "$listen_address" =~ [[:space:]] ]]; then
        printf 'La dirección de escucha debe ser explícita, no vacía y sin espacios.\n' >&2
        return 2
    fi
    if [[ ! "$listen_port" =~ ^[0-9]{1,5}$ ]] || ((10#$listen_port < 1 || 10#$listen_port > 65535)); then
        printf 'Puerto de escucha inválido (rango permitido: 1-65535).\n' >&2
        return 2
    fi
    if ! command -v jq >/dev/null 2>&1; then
        printf 'Se requiere jq para representar el modelo neutral.\n' >&2
        return 1
    fi

    jq -n \
        --arg schema_version '1' \
        --arg connection_id "$connection_id" \
        --arg protocol 'vless' \
        --arg mode_id "$mode_id" \
        --arg transport "$transport" \
        --arg security "$security" \
        --arg listen_address "$listen_address" \
        --argjson listen_port "$((10#$listen_port))" \
        '{schema_version:$schema_version,connection_id:$connection_id,protocol:$protocol,mode_id:$mode_id,transport:$transport,security:$security,listen_address:$listen_address,listen_port:$listen_port,transport_options:{},security_options:{},users:[]}'
}