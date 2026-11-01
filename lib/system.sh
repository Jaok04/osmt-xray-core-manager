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
	local xray_bin=""
	if command -v xray >/dev/null 2>&1; then
		xray_bin="$(command -v xray)"
	elif [[ -x /usr/local/bin/xray ]]; then
		xray_bin="/usr/local/bin/xray"
	fi

	if [[ -n "$xray_bin" ]]; then
		"$xray_bin" version 2>/dev/null | head -n 1 || printf '%s' "instalado (versión no detectada)"
	else
		printf '%s' "No instalado"
	fi
}

system_xray_service_state() {
	if [[ ! -x /usr/local/bin/xray ]] && ! command -v xray >/dev/null 2>&1; then
		printf '%s' "No instalado"
	elif ! command -v systemctl >/dev/null 2>&1; then
		printf '%s' "systemd no disponible"
	elif ! systemctl cat xray.service >/dev/null 2>&1; then
		printf '%s' "Instalado / servicio no configurado"
	elif systemctl is-active --quiet xray.service; then
		printf '%s' "Activo"
	elif systemctl is-failed --quiet xray.service; then
		printf '%s' "Fallido"
	else
		printf '%s' "Detenido"
	fi
}

system_xray_autostart() {
	if ! command -v systemctl >/dev/null 2>&1; then
		printf '%s' "No disponible"
	elif ! systemctl cat xray.service >/dev/null 2>&1; then
		printf '%s' "No configurado"
	elif systemctl is-enabled --quiet xray.service 2>/dev/null; then
		printf '%s' "Habilitado"
	else
		printf '%s' "Deshabilitado"
	fi
}

system_active_profile() {
	local profile_file="${XRAY_MANAGER_PROFILES_DIR:-/var/lib/xray-manager/profiles}/active/active-profile"
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