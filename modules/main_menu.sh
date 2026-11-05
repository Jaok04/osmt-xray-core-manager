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
        printf '\n  INFORMACIÓN\n'
        printf '  [9] Información y ayuda\n'
        printf '  [0] Salir\n\n'
        ui_read_option "Selecciona una opción: " option || return 0
        case "$option" in
            1) connections_menu || true ;;
            2) users_menu_dispatch || true ;;
            3) certificates_menu || true ;;
            4) menu_config_profiles_backups || true ;;
            5) menu_xray_service || true ;;
            6) menu_placeholder "Diagnóstico y registros" || true ;;
            7) menu_placeholder "Seguridad, red y mantenimiento" || true ;;
            8) menu_system_admin || true ;;
            9) menu_information || true ;;
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

menu_xray_service() {
    local option action label
    while true; do
        ui_clear
        ui_title "GESTIÓN DEL SERVICIO XRAY-CORE"
        printf '\n  Estado actual: %s\n' "$(system_xray_service_state)"
        printf '  Inicio automático: %s\n\n' "$(system_xray_autostart)"
        printf '  [1] Estado y diagnóstico\n'
        printf '  [2] Iniciar Xray\n'
        printf '  [3] Detener Xray\n'
        printf '  [4] Reiniciar Xray\n'
        printf '  [5] Habilitar inicio automático\n'
        printf '  [6] Deshabilitar inicio automático\n'
        printf '  [7] Consultar registros (journal)\n'
        printf '  [0] Volver\n\n'
        ui_read_option "Selecciona una opción: " option || return 0
        case "$option" in
            1)
                ui_clear
                ui_title "ESTADO Y DIAGNÓSTICO DE XRAY"
                if ! xray_service_status; then
                    printf '\nNo fue posible obtener el estado completo.\n'
                fi
                ui_pause
                ;;
            2 | 3 | 4 | 5 | 6)
                case "$option" in
                    2)
                        action=start
                        label="iniciar Xray"
                        ;;
                    3)
                        action=stop
                        label="detener Xray"
                        ;;
                    4)
                        action=restart
                        label="reiniciar Xray"
                        ;;
                    5)
                        action=enable
                        label="habilitar el inicio automático de Xray"
                        ;;
                    6)
                        action=disable
                        label="deshabilitar el inicio automático de Xray"
                        ;;
                esac
                ui_clear
                ui_title "CONFIRMAR OPERACIÓN"
                printf '\nOperación solicitada: %s\n' "$label"
                case "$action" in
                    start | restart | enable)
                        printf 'Se comprobará config.json con Xray como usuario de servicio antes de continuar.\n'
                        ;;
                    stop)
                        printf 'Las conexiones que dependan de Xray se interrumpirán.\n'
                        ;;
                    disable)
                        printf 'Xray no se iniciará automáticamente en el próximo arranque.\n'
                        ;;
                esac
                if ui_confirm "¿Confirmas que deseas $label?"; then
                    if ! xray_service_action "$action"; then
                        printf '\nLa operación no se completó. Revisa el diagnóstico y los registros.\n'
                    fi
                else
                    printf '\nOperación cancelada; no se modificó el servicio.\n'
                fi
                ui_pause
                ;;
            7)
                ui_clear
                ui_title "REGISTROS DE XRAY-CORE"
                if ! xray_service_show_logs 50; then
                    printf '\nNo fue posible consultar los registros.\n'
                fi
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
        ui_read_option "Selecciona una opción: " option || return 0
        case "$option" in
            1) menu_xray_admin || true ;;
            2) manager_dependencies_menu || true ;;
            3) manager_settings_menu || true ;;
            4) menu_installation_information || true ;;
            5) uninstall_menu_action || true ;;
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
        printf '  [7] Preparar servicio (verifica integridad)\n'
        printf '  [0] Volver\n\n'
        ui_read_option "Selecciona una opción: " option || return 0
        case "$option" in
            1) xray_admin_install_menu_action install || true ;;
            2) xray_admin_install_menu_action update || true ;;
            3)
                ui_clear
                ui_title "VERSIÓN INSTALADA DE XRAY-CORE"
                printf '  %s\n' "$(system_xray_version)"
                ui_pause
                ;;
            4) menu_xray_latest_release || true ;;
            5) xray_admin_install_menu_action reinstall || true ;;
            6) xray_admin_install_menu_action repair || true ;;
            7) xray_admin_prepare_service_menu_action || true ;;
            0) return 0 ;;
            *)
                printf '\nOpción no válida.\n'
                ui_pause
                ;;
        esac
    done
}

menu_xray_latest_release() {
    local latest compatible
    ui_clear
    ui_title "ÚLTIMA VERSIÓN DISPONIBLE DE XRAY-CORE"
    if ! latest="$(xray_admin_latest_release)"; then
        printf '\nNo fue posible consultar el último release estable oficial.\n'
        printf 'Comprueba la conectividad y las dependencias curl/jq.\n'
        ui_pause
        return 1
    fi
    printf '\nÚltima versión estable publicada: %s\n' "$latest"
    compatible="$(xray_admin_compatible_versions || true)"
    if grep -Fxq "$latest" <<<"$compatible"; then
        printf 'Compatibilidad local: disponible (adaptador y pruebas presentes).\n'
    else
        printf 'Compatibilidad local: todavía no habilitada.\n'
        printf 'No se permitirá instalarla hasta incorporar y validar su adaptador.\n'
    fi
    printf '\nVersiones habilitadas para instalación:\n'
    if [[ -n "$compatible" ]]; then
        while IFS= read -r version; do
            [[ -n "$version" ]] && printf '  - %s\n' "$version"
        done <<<"$compatible"
    else
        printf '  Ninguna\n'
    fi
    ui_pause
}

menu_installation_information() {
    local option
    while true; do
        ui_clear
        ui_title "INFORMACIÓN DE INSTALACIÓN"
        printf '
  [1] Rutas de instalación
'
        printf '  [2] Archivos y directorios
'
        printf '  [3] Información de systemd
'
        printf '  [0] Volver

'
        ui_read_option "Selecciona una opción: " option || return 0
        case "$option" in
            1) menu_installation_paths || true ;;
            2) menu_installation_files || true ;;
            3) menu_installation_systemd || true ;;
            0) return 0 ;;
            *)
                printf '
Opción no válida.
'
                ui_pause
                ;;
        esac
    done
}

menu_installation_paths() {
    ui_clear
    ui_title "RUTAS DE INSTALACIÓN"
    printf '  Administrador:       %s
' "$APP_ROOT"
    printf '  Configuración gestor: %s
' "$XRAY_MANAGER_CONFIG_DIR"
    printf '  Binario Xray:        %s
' "$XRAY_ADMIN_BIN"
    printf '  Datos Xray:          %s
' "$XRAY_ADMIN_DATA"
    printf '  Configuración Xray:  %s
' "$XRAY_CONFIG_DIR"
    printf '  Archivo principal:   %s
' "$XRAY_CONFIG_FILE"
    printf '  Datos del gestor:    %s
' "$XRAY_MANAGER_DATA_DIR"
    printf '  Usuarios:            %s
' "$XRAY_MANAGER_USERS_DIR"
    printf '  Conexiones:          %s
' "$XRAY_MANAGER_CONNECTIONS_DIR"
    printf '  Perfiles:            %s
' "$XRAY_MANAGER_PROFILES_DIR"
    printf '  Dominios:            %s
' "$XRAY_MANAGER_DOMAINS_DIR"
    printf '  Certificados:        %s
' "$XRAY_MANAGER_CERTIFICATES_DIR"
    printf '  Historiales:         %s
' "$XRAY_MANAGER_HISTORY_DIR"
    printf '  Registros:           %s
' "$XRAY_MANAGER_LOG_DIR"
    printf '  Caché:               %s
' "$XRAY_MANAGER_CACHE_DIR"
    printf '  Respaldos:           %s
' "$XRAY_MANAGER_BACKUP_DIR"
    printf '  Temporales:          %s
' "$XRAY_MANAGER_RUNTIME_DIR"
    ui_pause
}

menu_installation_path_status() {
    local path="$1" kind metadata
    if [[ -L "$path" ]]; then
        kind="enlace -> $(readlink -- "$path")"
    elif [[ -f "$path" ]]; then
        kind="archivo"
    elif [[ -d "$path" ]]; then
        kind="directorio"
    else
        printf '  AUSENTE  %s
' "$path"
        return 0
    fi
    metadata="$(stat -c '%A %U:%G %s bytes' -- "$path" 2>/dev/null || printf 'metadatos no disponibles')"
    printf '  %-18s %s (%s)
' "$kind" "$path" "$metadata"
}

menu_installation_files() {
    local path
    ui_clear
    ui_title "ARCHIVOS Y DIRECTORIOS"
    printf '
Componentes del administrador:
'
    for path in \
        "$APP_ROOT/bin/xray-manager" \
        "$APP_ROOT/config/manager.conf" \
        "$APP_ROOT/config/paths.sh" \
        "$APP_ROOT/modules/main_menu.sh" \
        "$APP_ROOT/modules/xray_admin.sh" \
        "$APP_ROOT/modules/uninstall.sh" \
        "$APP_ROOT/lib/system.sh" \
        "$APP_ROOT/lib/ui.sh"; do
        menu_installation_path_status "$path"
    done
    printf '
Componentes Xray-core y configuración:
'
    for path in \
        "$XRAY_ADMIN_BIN" \
        "$XRAY_ADMIN_DATA/geoip.dat" \
        "$XRAY_ADMIN_DATA/geosite.dat" \
        "$XRAY_CONFIG_FILE"; do
        menu_installation_path_status "$path"
    done
    printf '
Directorios persistentes y operativos:
'
    for path in \
        "$XRAY_MANAGER_CONFIG_DIR" \
        "$XRAY_MANAGER_DATA_DIR" \
        "$XRAY_MANAGER_PROFILES_DIR" \
        "$XRAY_MANAGER_CERTIFICATES_DIR" \
        "$XRAY_MANAGER_LOG_DIR" \
        "$XRAY_MANAGER_CACHE_DIR" \
        "$XRAY_MANAGER_BACKUP_DIR" \
        "$XRAY_MANAGER_RUNTIME_DIR"; do
        menu_installation_path_status "$path"
    done
    ui_pause
}

menu_installation_systemd() {
    ui_clear
    ui_title "INFORMACIÓN DE SYSTEMD"
    if ! command -v systemctl >/dev/null 2>&1; then
        printf '
systemctl no está disponible en este sistema.
'
        ui_pause
        return 0
    fi
    if ! systemctl show xray.service --property=LoadState --value >/dev/null 2>&1; then
        printf '
No fue posible consultar xray.service.
'
        ui_pause
        return 0
    fi
    printf '
Unidad: xray.service
'
    if ! systemctl show xray.service --no-pager \
        --property=LoadState,ActiveState,SubState,UnitFileState,FragmentPath,DropInPaths,User,Group,MainPID; then
        printf 'No se pudieron obtener todos los metadatos de la unidad.\n'
    fi
    printf '
Estado de habilitación: '
    systemctl is-enabled xray.service 2>/dev/null || true
    printf '
Esta pantalla es de solo lectura; no modifica unidades ni servicios.
'
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
    printf '  Aplicación:          %s\n' "$APP_NAME"
    printf '  Versión del gestor:  %s\n' "$APP_VERSION"
    printf '  Sistema operativo:   %s\n' "$(system_os_name)"
    printf '  Arquitectura:        %s\n' "$(uname -m)"
    printf '  Xray-core:           %s\n' "$(system_xray_version)"
    printf '  Estado del servicio: %s\n' "$(system_xray_service_state)"
    printf '  Inicio automático:   %s\n' "$(system_xray_autostart)"
    printf '\nRutas principales:\n'
    printf '  Administrador:       %s\n' "$APP_ROOT"
    printf '  Binario Xray:        %s\n' "$XRAY_ADMIN_BIN"
    printf '  Configuración Xray:  %s\n' "$XRAY_CONFIG_FILE"
    printf '\nDocumentación local:\n'
    printf '  %s/README.md\n' "$APP_ROOT"
    printf '  %s/docs/ETAPA_1_ADMIN_XRAY_IMPLEMENTACION.md\n' "$APP_ROOT"
    printf '  %s/docs/ARQUITECTURA_RUTAS_Y_ALMACENAMIENTO.md\n' "$APP_ROOT"
    printf '\nDocumentación oficial de Xray-core: https://xtls.github.io/\n'
    printf '\nLas conexiones y usuarios VLESS existentes permanecen como borradores.\n'
    printf 'No se aplican cambios al runtime de Xray-core desde esos módulos.\n'
    ui_pause
}
