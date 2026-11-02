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
	elif [[ -x "${XRAY_ADMIN_BIN:-/usr/local/bin/xray}" ]]; then
		xray_bin="${XRAY_ADMIN_BIN:-/usr/local/bin/xray}"
	fi
	if [[ -n "$xray_bin" ]]; then
		local version_output
		if version_output="$("$xray_bin" version 2>/dev/null)"; then
			printf '%s\n' "$version_output" | head -n 1
		else
			printf '%s' "instalado (versión no detectada)"
		fi
	else
		printf '%s' "No instalado"
	fi
}

system_xray_service_state() {
	if [[ ! -x "${XRAY_ADMIN_BIN:-/usr/local/bin/xray}" ]] && ! command -v xray >/dev/null 2>&1; then
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
	local state
	if ! command -v systemctl >/dev/null 2>&1; then
		printf '%s' "No disponible"
	elif ! systemctl cat xray.service >/dev/null 2>&1; then
		printf '%s' "No configurado"
	elif state="$(systemctl is-enabled xray.service 2>/dev/null)"; then
		case "$state" in
		enabled | enabled-runtime) printf '%s' "Habilitado" ;;
		disabled) printf '%s' "Deshabilitado" ;;
		masked | masked-runtime) printf '%s' "Enmascarado" ;;
		static | indirect | generated | transient) printf '%s' "No aplica ($state)" ;;
		*) printf '%s' "No disponible" ;;
		esac
	else
		case "$state" in
		disabled) printf '%s' "Deshabilitado" ;;
		masked | masked-runtime) printf '%s' "Enmascarado" ;;
		static | indirect | generated | transient) printf '%s' "No aplica ($state)" ;;
		*) printf '%s' "No disponible" ;;
		esac
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
	local public_ip xray_version service_state autostart profile date_part time_part
	public_ip="$(system_public_ip 2>/dev/null)" || public_ip="No disponible"
	xray_version="$(system_xray_version 2>/dev/null)" || xray_version="No disponible"
	service_state="$(system_xray_service_state 2>/dev/null)" || service_state="No disponible"
	autostart="$(system_xray_autostart 2>/dev/null)" || autostart="No disponible"
	profile="$(system_active_profile 2>/dev/null)" || profile="No disponible"
	case "${APP_DATE_FORMAT:-dmy}" in
	dmy) date_part="$(TZ="${APP_TIMEZONE:-UTC}" date '+%d/%m/%Y' 2>/dev/null)" || date_part="No disponible" ;;
	ymd) date_part="$(TZ="${APP_TIMEZONE:-UTC}" date '+%Y-%m-%d' 2>/dev/null)" || date_part="No disponible" ;;
	*) date_part="$(TZ="${APP_TIMEZONE:-UTC}" date '+%d/%m/%Y' 2>/dev/null)" || date_part="No disponible" ;;
	esac
	case "${APP_TIME_FORMAT:-24h}" in
	12h) time_part="$(TZ="${APP_TIMEZONE:-UTC}" date '+%I:%M:%S %p %Z' 2>/dev/null)" || time_part="No disponible" ;;
	*) time_part="$(TZ="${APP_TIMEZONE:-UTC}" date '+%H:%M:%S %Z' 2>/dev/null)" || time_part="No disponible" ;;
	esac
	[[ -n "$public_ip" ]] || public_ip="No disponible"
	[[ -n "$xray_version" ]] || xray_version="No disponible"
	[[ -n "$service_state" ]] || service_state="No disponible"
	[[ -n "$autostart" ]] || autostart="No disponible"
	[[ -n "$profile" ]] || profile="No disponible"
	[[ -n "$date_part" ]] || date_part="No disponible"
	[[ -n "$time_part" ]] || time_part="No disponible"
	printf '  IP pública:        %s\n' "$public_ip"
	printf '  Xray-core:         %s\n' "$xray_version"
	printf '  Estado:            %s\n' "$service_state"
	printf '  Servicio:          %s\n' "$autostart"
	printf '  Perfil activo:     %s\n' "$profile"
	printf '  Fecha:             %s\n' "$date_part"
	printf '  Hora:              %s\n' "$time_part"
}