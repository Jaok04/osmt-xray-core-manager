#!/usr/bin/env bash
# Dependencias exclusivas de Xray Core Manager.
# No administra actualizaciones generales ni parches de seguridad del SO.

MANAGER_REQUIRED_DEPENDENCIES=(
    "apt-get|apt"
    "dpkg-query|dpkg"
    "pgrep|procps"
    "awk|mawk"
    "grep|grep"
    "curl|curl"
    "jq|jq"
    "python3|python3"
    "python3-cryptography|python3-cryptography|package"
    "tar|tar"
    "gzip|gzip"
    "flock|util-linux"
    "ss|iproute2"
    "sha256sum|coreutils"
    "install|coreutils"
    "uuidgen|uuid-runtime"
    "getent|libc-bin"
    "groupadd|passwd"
    "useradd|passwd"
    "systemctl|systemd"
    "systemd-analyze|systemd"
    "runuser|util-linux"
    "ca-certificates|ca-certificates|package"
)
MANAGER_APT_GET="${MANAGER_APT_GET:-apt-get}"
# shellcheck disable=SC1091
. "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../lib" && pwd)/operation_lock.sh"

manager_dependencies_require_root() {
    if [[ "$EUID" -ne 0 ]]; then
        printf 'Esta operación requiere root. No se intentará autoelevar.\n' >&2
        return 1
    fi
}

manager_dependencies_require_apt() {
    if ! command -v "$MANAGER_APT_GET" >/dev/null 2>&1; then
        printf 'No se encontró apt-get; este gestor solo administra dependencias en Debian/Ubuntu.\n' >&2
        return 1
    fi
    if [[ ! -r /etc/os-release ]] ||
        ! grep -Eiq '^(ID=(ubuntu|debian)|ID_LIKE=.*(ubuntu|debian))' /etc/os-release; then
        printf 'Sistema operativo no compatible con el gestor de dependencias apt.\n' >&2
        return 1
    fi
}

manager_dependencies_packages() {
    local entry package
    for entry in "${MANAGER_REQUIRED_DEPENDENCIES[@]}"; do
        IFS='|' read -r _ package _check_type <<<"$entry"
        printf '%s\n' "$package"
    done | sort -u
}

manager_dependencies_missing_packages() {
    local entry command_name package check_type
    for entry in "${MANAGER_REQUIRED_DEPENDENCIES[@]}"; do
        IFS='|' read -r command_name package check_type <<<"$entry"
        if [[ "$check_type" == package ]]; then
            dpkg-query -s "$package" >/dev/null 2>&1 || printf '%s\n' "$package"
        elif ! command -v "$command_name" >/dev/null 2>&1; then
            printf '%s\n' "$package"
        fi
    done | sort -u
}

manager_dependencies_installed_packages() {
    local package
    while IFS= read -r package; do
        [[ -n "$package" ]] || continue
        # apt/dpkg son infraestructura del gestor de paquetes del SO;
        # su actualización general corresponde a Etapa 6, no a este módulo.
        case "$package" in apt | dpkg) continue ;; esac
        if dpkg-query -s "$package" >/dev/null 2>&1; then
            printf '%s\n' "$package"
        fi
    done < <(manager_dependencies_packages)
}

manager_dependencies_report() {
    local entry command_name package check_type
    ui_clear
    ui_title "COMPROBACIÓN DE DEPENDENCIAS"
    printf 'Dependencias requeridas por el administrador:\n\n'
    for entry in "${MANAGER_REQUIRED_DEPENDENCIES[@]}"; do
        IFS='|' read -r command_name package check_type <<<"$entry"
        if [[ "$check_type" == package ]] && dpkg-query -s "$package" >/dev/null 2>&1; then
            printf '  [OK]       %-16s paquete instalado: %s\n' "$command_name" "$package"
        elif [[ "$check_type" != package ]] && command -v "$command_name" >/dev/null 2>&1; then
            printf '  [OK]       %-16s paquete: %s\n' "$command_name" "$package"
        else
            printf '  [FALTANTE] %-16s paquete: %s\n' "$command_name" "$package"
        fi
    done
    printf '\n'
    if [[ -n "$(manager_dependencies_missing_packages)" ]]; then
        printf 'Hay dependencias faltantes. Usa [2] para instalar solo los paquetes requeridos.\n'
    else
        printf 'Todas las dependencias requeridas están disponibles.\n'
    fi
    printf '\nNo se comprueban ni actualizan aquí los paquetes generales del sistema.\n'
    ui_pause
}

manager_dependencies_install_missing() {
    local packages lifecycle_fd
    manager_dependencies_require_root || return 1
    manager_dependencies_require_apt || return 1
    packages="$(manager_dependencies_missing_packages)"
    if [[ -z "$packages" ]]; then
        printf 'No hay dependencias faltantes.\n'
        ui_pause
        return 0
    fi
    printf 'Se instalarán únicamente estos paquetes requeridos:\n%s\n' "$packages"
    printf 'No se ejecutará apt upgrade ni se actualizarán paquetes ajenos al administrador.\n'
    if ! ui_confirm "¿Confirmas actualizar índices e instalar estas dependencias?"; then
        printf 'Operación cancelada; no se modificó el sistema.\n'
        ui_pause
        return 0
    fi
    if ! manager_lock_acquire "${XRAY_MANAGER_LIFECYCLE_LOCK:-/run/lock/xray-manager-lifecycle.lock}" lifecycle_fd; then
        printf 'Hay otra operación de ciclo de vida del Manager en curso.\n' >&2
        ui_pause
        return 1
    fi
    if ! "$MANAGER_APT_GET" update; then
        manager_lock_release "$lifecycle_fd"
        printf 'Falló apt-get update. No se instalaron dependencias.\n' >&2
        ui_pause
        return 1
    fi
    local -a package_array=()
    mapfile -t package_array <<<"$packages"
    if ! "$MANAGER_APT_GET" install -y --no-install-recommends "${package_array[@]}"; then
        manager_lock_release "$lifecycle_fd"
        printf 'Falló la instalación de dependencias. Comprueba el estado del gestor de paquetes.\n' >&2
        ui_pause
        return 1
    fi
    manager_lock_release "$lifecycle_fd"
    printf '\nComprobación posterior:\n'
    manager_dependencies_report
}

manager_dependencies_update() {
    local packages lifecycle_fd
    manager_dependencies_require_root || return 1
    manager_dependencies_require_apt || return 1
    packages="$(manager_dependencies_installed_packages)"
    if [[ -z "$packages" ]]; then
        printf 'No hay paquetes requeridos instalados que puedan actualizarse.\n'
        printf 'Usa [2] para instalar las dependencias faltantes.\n'
        ui_pause
        return 0
    fi
    printf 'Solo se actualizarán paquetes de esta lista:\n%s\n' "$packages"
    printf 'No se ejecutará apt upgrade, full-upgrade ni una actualización general del sistema.\n'
    if ! ui_confirm "¿Confirmas actualizar estos paquetes específicos?"; then
        printf 'Operación cancelada; no se modificó el sistema.\n'
        ui_pause
        return 0
    fi
    if ! manager_lock_acquire "${XRAY_MANAGER_LIFECYCLE_LOCK:-/run/lock/xray-manager-lifecycle.lock}" lifecycle_fd; then
        printf 'Hay otra operación de ciclo de vida del Manager en curso.\n' >&2
        ui_pause
        return 1
    fi
    if ! "$MANAGER_APT_GET" update; then
        manager_lock_release "$lifecycle_fd"
        printf 'Falló apt-get update. No se actualizaron paquetes.\n' >&2
        ui_pause
        return 1
    fi
    local -a package_array=()
    mapfile -t package_array <<<"$packages"
    if ! "$MANAGER_APT_GET" install --only-upgrade -y --no-install-recommends "${package_array[@]}"; then
        manager_lock_release "$lifecycle_fd"
        printf 'Falló la actualización de dependencias requeridas.\n' >&2
        ui_pause
        return 1
    fi
    manager_lock_release "$lifecycle_fd"
    printf '\nActualización de dependencias terminada.\n'
    manager_dependencies_report
}

manager_dependencies_menu() {
    local option
    while true; do
        ui_clear
        ui_title "DEPENDENCIAS DEL SISTEMA"
        printf '\n  [1] Comprobar dependencias\n'
        printf '  [2] Instalar dependencias faltantes\n'
        printf '  [3] Actualizar dependencias del administrador\n'
        printf '  [0] Volver\n\n'
        ui_read_option "Selecciona una opción: " option
        case "$option" in
            1) manager_dependencies_report ;;
            2) manager_dependencies_install_missing ;;
            3) manager_dependencies_update ;;
            0) return 0 ;;
            *)
                printf '\nOpción no válida.\n'
                ui_pause
                ;;
        esac
    done
}
