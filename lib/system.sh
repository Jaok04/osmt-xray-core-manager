#!/usr/bin/env bash

system_os_name() {
    if [[ -r /etc/os-release ]]; then
        # shellcheck disable=SC1091
        . /etc/os-release
        printf '%s' "${PRETTY_NAME:-Linux}"
    else
        printf '%s' "Linux"
    fi
}

system_public_ip() {
    local result=""
    local url="${PUBLIC_IP_URL:-https://api.ipify.org}"
    local timeout="${PUBLIC_IP_TIMEOUT:-2}"
    if command -v curl >/dev/null 2>&1; then
        result="$(curl -4fsS --connect-timeout "$timeout" --max-time "$timeout" "$url" 2>/dev/null || true)"
    fi
    if [[ "$result" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
        printf '%s' "$result"
    else
        printf '%s' "No disponible"
    fi
}

system_xray_version() {
    if command -v xray >/dev/null 2>&1; then
        xray version 2>/dev/null | head -n 1 || printf '%s' "instalado (versión no detectada)"
    else
        printf '%s' "No instalado"
    fi
}

system_xray_service_state() {
    if ! command -v systemctl >/dev/null 2>&1; then
        printf '%s' "systemd no disponible"
    elif systemctl is-active --quiet xray.service; then
        printf '%s' "Activo"
    elif systemctl is-failed --quiet xray.service; then
        printf '%s' "Fallido"
    else
        printf '%s' "Inactivo / no instalado"
    fi
}

system_xray_autostart() {
    if command -v systemctl >/dev/null 2>&1 && systemctl is-enabled --quiet xray.service 2>/dev/null; then
        printf '%s' "Habilitado"
    else
        printf '%s' "No habilitado"
    fi
}

system_active_profile() {
    local profile_file="/var/lib/xray-manager/active-profile"
    if [[ -r "$profile_file" ]]; then
        local profile
        IFS= read -r profile <"$profile_file" || true
        printf '%s' "${profile:-Ninguno}"
    else
        printf '%s' "Ninguno"
    fi
}

system_show_header() {
    local public_ip xray_version service_state autostart profile now
    public_ip="$(system_public_ip)"
    xray_version="$(system_xray_version)"
    service_state="$(system_xray_service_state)"
    autostart="$(system_xray_autostart)"
    profile="$(system_active_profile)"
    now="$(TZ="${APP_TIMEZONE:-UTC}" date '+%Y-%m-%d %H:%M:%S %Z')"
    printf '  IP pública:        %s\n' "$public_ip"
    printf '  Xray-core:         %s\n' "$xray_version"
    printf '  Servicio:          %s\n' "$service_state"
    printf '  Inicio automático: %s\n' "$autostart"
    printf '  Perfil activo:     %s\n' "$profile"
    printf '  Fecha/hora VPS:    %s\n' "$now"
}
