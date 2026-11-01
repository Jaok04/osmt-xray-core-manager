#!/usr/bin/env bash

menu_main() {
	local option
	while true; do
		ui_clear
		ui_title "${APP_NAME} - MENÚ PRINCIPAL"
		system_show_header
		ui_line
		printf '\n  ADMINISTRACIÓN\n'
		printf '  [1] Gestión de protocolos y conexiones\n'
		printf '  [2] Gestión de usuarios\n'
		printf '  [3] Certificados SSL/TLS y dominios\n'
		printf '\n  CONFIGURACIÓN\n'
		printf '  [4] Configuraciones, perfiles y respaldos\n'
		printf '\n  SISTEMA\n'
		printf '  [5] Gestión del servicio Xray-core\n'
		printf '  [6] Diagnóstico y registros\n'
		printf '  [7] Seguridad, red y mantenimiento\n'
		printf '  [8] Configuración del sistema y administrador\n'
		printf '  [9] Información y ayuda\n'
		printf '  [0] Salir\n\n'
		ui_read_option "Selecciona una opción: " option
		case "$option" in
		1) connections_menu ;;
		2) users_menu ;;
		3) menu_placeholder "Certificados SSL/TLS y dominios" ;;
		4) menu_placeholder "Configuraciones, perfiles y respaldos" ;;
		5) menu_placeholder "Gestión del servicio Xray-core" ;;
		6) menu_placeholder "Diagnóstico y registros" ;;
		7) menu_placeholder "Seguridad, red y mantenimiento" ;;
		8) menu_system_admin ;;
		9) menu_information ;;
		0)
			if ui_confirm "¿Deseas salir de ${APP_NAME}?"; then
				printf '\nCerrando %s...\n' "$APP_NAME"
				return 0
			fi
			;;
		*)
			printf '\nOpción no válida.\n'
			ui_pause
			;;
		esac
	done
}

menu_system_admin() {
	local option
	while true; do
		ui_clear
		ui_title "CONFIGURACIÓN DEL SISTEMA Y ADMINISTRADOR"
		printf '\n  [1] Administración de Xray-core\n'
		printf '  [2] Dependencias del sistema\n'
		printf '  [3] Configuración del administrador\n'
		printf '  [4] Información de instalación\n'
		printf '  [5] Desinstalar componentes\n'
		printf '  [0] Volver\n\n'
		ui_read_option "Selecciona una opción: " option
		case "$option" in
		1) menu_xray_admin ;;
		2) menu_pending_spec "Dependencias del sistema" ;;
		3) menu_pending_spec "Configuración del administrador" ;;
		4) menu_installation_information ;;
		5) uninstall_menu_action ;;
		0) return 0 ;;
		*)
			printf '\nOpción no válida.\n'
			ui_pause
			;;
		esac
	done
}

menu_xray_admin() {
	local option
	while true; do
		ui_clear
		ui_title "ADMINISTRACIÓN DE XRAY-CORE"
		printf '\n  [1] Instalar Xray-core\n'
		printf '  [2] Actualizar Xray-core\n'
		printf '  [3] Consultar versión instalada\n'
		printf '  [4] Consultar última versión disponible\n'
		printf '  [5] Reinstalar Xray-core\n'
		printf '  [6] Reparar instalación\n'
		printf '  [0] Volver\n\n'
		ui_read_option "Selecciona una opción: " option
		case "$option" in
		1 | 2 | 5 | 6)
			menu_pending_spec "Operación de Xray-core: opción $option"
			;;
		3)
			ui_clear
			ui_title "VERSIÓN INSTALADA DE XRAY-CORE"
			printf '  %s\n' "$(system_xray_version)"
			ui_pause
			;;
		4)
			ui_clear
			ui_title "VERSIÓN DISPONIBLE DE XRAY-CORE"
			printf '  Versión compatible verificada: %s\n' "${XRAY_VERSION:-No definida}"
			printf '  La lista de versiones solo incluirá versiones con adaptador validado.\n'
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

menu_installation_information() {
	ui_clear
	ui_title "INFORMACIÓN DE INSTALACIÓN"
	printf '  Administrador: %s\n' "$APP_NAME"
	printf '  Versión:       %s\n' "$APP_VERSION"
	printf '  Directorio:    %s\n' "$APP_ROOT"
	printf '  Sistema:       %s\n' "$(system_os_name)"
	printf '  Arquitectura:  %s\n' "$(uname -m)"
	printf '  Xray-core:     %s\n' "$(system_xray_version)"
	printf '  Servicio:      %s\n' "$(system_xray_service_state)"
	ui_pause
}

menu_pending_spec() {
	local title="$1"
	ui_clear
	ui_title "$title"
	printf '\nEste apartado está pendiente de implementación o especificación técnica.\n'
	printf 'No se ha modificado ningún servicio ni configuración.\n'
	ui_pause
}

menu_placeholder() {
	menu_pending_spec "$1"
}

menu_information() {
	ui_clear
	ui_title "INFORMACIÓN Y AYUDA"
	printf '  Aplicación:   %s\n' "$APP_NAME"
	printf '  Versión:      %s\n' "$APP_VERSION"
	printf '  Sistema:      %s\n' "$(system_os_name)"
	printf '  Arquitectura: %s\n' "$(uname -m)"
	printf '\n  Las conexiones y usuarios VLESS existentes permanecen como borradores.\n'
	printf '  No se aplican cambios al runtime de Xray-core desde esos módulos.\n'
	ui_pause
}