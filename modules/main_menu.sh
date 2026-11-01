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
            8) menu_placeholder "Configuración del sistema y administrador" ;;
            9) menu_information ;;
            0)
                printf '\nCerrando %s...\n' "$APP_NAME"
                return 0
                ;;
            *)
                printf '\nOpción no válida.\n'
                ui_pause
                ;;
        esac
    done
}

menu_placeholder() {
    local title="$1"
    ui_clear
    ui_title "$title"
    printf '\nEste módulo todavía no está implementado.\n'
    printf 'No se ha modificado ningún servicio ni configuración.\n'
    ui_pause
}

menu_information() {
    ui_clear
    ui_title "INFORMACIÓN Y AYUDA"
    printf '  Aplicación:   %s\n' "$APP_NAME"
    printf '  Versión:      %s\n' "$APP_VERSION"
    printf '  Sistema:      %s\n' "$(system_os_name)"
    printf '  Arquitectura: %s\n' "$(uname -m)"
    printf '\n  Estado: etapa 3 en implementación (conexiones y usuarios VLESS en borrador).\n'
    printf '  Las conexiones registradas todavía no se aplican al runtime.\n'
    ui_pause
}