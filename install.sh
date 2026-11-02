#!/usr/bin/env bash
# Instala Xray Core Manager y prepara Xray-core sin activar el servicio.
set -Eeuo pipefail
IFS=$'\n\t'
umask 077

readonly INSTALL_VERSION="1"
readonly DEFAULT_PREFIX="/"
PREFIX="${XRAY_MANAGER_INSTALL_PREFIX:-$DEFAULT_PREFIX}"
SKIP_DEPS="${XRAY_MANAGER_SKIP_DEPENDENCIES:-0}"
ACTION="install"

usage() {
    cat <<'USAGE'
Uso: sudo ./install.sh [--check | --install] [--help]

  --check    Comprueba plataforma, privilegios y dependencias; no modifica nada.
  --install  Instala las dependencias faltantes y despliega Xray Core Manager.
  --help     Muestra esta ayuda.

La instalación prepara Xray-core y xray.service, pero no habilita ni inicia el servicio.
USAGE
}

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}
info() { printf '[INFO] %s\n' "$*"; }
ok() { printf '[OK] %s\n' "$*"; }

while (($#)); do
    case "$1" in
        --check) ACTION=check ;;
        --install) ACTION=install ;;
        --help | -h)
            usage
            exit 0
            ;;
        *) fail "argumento desconocido: $1" ;;
    esac
    shift
done

SOURCE_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
prefix_path() {
    if [[ "$PREFIX" == "/" ]]; then printf '%s' "$1"; else printf '%s%s' "${PREFIX%/}" "$1"; fi
}
APP_ROOT="$(prefix_path /opt/xray-manager)"
path() { prefix_path "$1"; }
assert_no_symlink_components() {
    local value="$1" current="" segment
    local -a parts=()
    IFS='/' read -r -a parts <<<"${value#/}"
    for segment in "${parts[@]}"; do
        [[ -n "$segment" ]] || continue
        current+="/$segment"
        [[ ! -L "$current" ]] || fail "se detectó un componente simbólico en la ruta: $current"
    done
}
[[ "$PREFIX" == "/" || "$PREFIX" == /* ]] || fail "el prefijo de instalación debe ser absoluto"
[[ -f "$SOURCE_ROOT/bin/xray-manager" && -f "$SOURCE_ROOT/config/paths.sh" &&
    -f "$SOURCE_ROOT/modules/main_menu.sh" && -f "$SOURCE_ROOT/lib/json_store.sh" ]] ||
    fail "el directorio de origen no contiene un árbol válido de Xray Core Manager"

[[ -r /etc/os-release ]] || fail "no se pudo identificar la distribución Linux"
# shellcheck disable=SC1091
. /etc/os-release
if ! grep -Eiq '^(ID=(ubuntu|debian)|ID_LIKE=.*(ubuntu|debian))' /etc/os-release; then
    fail "plataforma no compatible: se requiere Ubuntu o Debian con apt-get"
fi

# Preflight de rutas y archivos persistentes antes de apt-get o del despliegue.
parent="$(dirname -- "$APP_ROOT")"
for candidate in \
    "$APP_ROOT" "$parent" \
    "$(path /etc/xray-manager)" \
    "$(path /var/lib/xray-manager)" \
    "$(path /var/lib/xray-manager/users)" \
    "$(path /var/lib/xray-manager/connections)" \
    "$(path /var/lib/xray-manager/profiles)" \
    "$(path /var/lib/xray-manager/domains)" \
    "$(path /var/lib/xray-manager/certificates)" \
    "$(path /var/lib/xray-manager/history)" \
    "$(path /var/lib/xray-manager/state)" \
    "$(path /var/log/xray-manager)" \
    "$(path /var/cache/xray-manager)" \
    "$(path /var/backups/xray-manager)" \
    "$(path /var/lib/xray)" \
    "$(path /etc/xray)" \
    "$(path /usr/local/bin/xray)" \
    "$(path /usr/local/share/xray)" \
    "$(path /etc/systemd/system)" \
    "$(path /etc/systemd/system/xray.service)" \
    "$(path /var/lib/xray-manager/connections/connections.json)" \
    "$(path /etc/xray-manager/preferences.conf)" \
    "$(path /var/lib/xray-manager/state/install.json)"; do
    assert_no_symlink_components "$candidate"
done
connections_preflight="$(path /var/lib/xray-manager/connections/connections.json)"
if [[ -e "$connections_preflight" ]]; then
    [[ -f "$connections_preflight" ]] || fail "el registro de conexiones existente no es un archivo regular"
    if command -v jq >/dev/null 2>&1; then
        jq -e 'type == "array"' "$connections_preflight" >/dev/null ||
            fail "el registro de conexiones existente no es un arreglo JSON; no se modificó"
    elif command -v python3 >/dev/null 2>&1; then
        python3 -c 'import json,sys; value=json.load(open(sys.argv[1])); sys.exit(0 if isinstance(value,list) else 1)' "$connections_preflight" ||
            fail "el registro de conexiones existente no es un arreglo JSON; no se modificó"
    else
        fail "no se puede validar el registro de conexiones antes de instalar dependencias"
    fi
fi
for candidate in "$(path /etc/xray-manager/preferences.conf)" "$(path /var/lib/xray-manager/state/install.json)"; do
    [[ ! -e "$candidate" || -f "$candidate" ]] ||
        fail "un archivo de estado/preferencias existente no es regular: $candidate"
done
state_preflight="$(path /var/lib/xray-manager/state/install.json)"
if [[ -e "$state_preflight" ]]; then
    if command -v jq >/dev/null 2>&1; then
        jq -e 'type == "object"' "$state_preflight" >/dev/null ||
            fail "el registro de instalación existente no es un objeto JSON válido; no se modificó"
    elif command -v python3 >/dev/null 2>&1; then
        python3 -c 'import json,sys; value=json.load(open(sys.argv[1])); sys.exit(0 if isinstance(value,dict) else 1)' "$state_preflight" ||
            fail "el registro de instalación existente no es un objeto JSON válido; no se modificó"
    else
        fail "no se puede validar el registro de instalación antes de instalar dependencias"
    fi
fi
command -v apt-get >/dev/null 2>&1 || fail "apt-get no está disponible"
command -v dpkg-query >/dev/null 2>&1 || fail "dpkg-query no está disponible"

if [[ "$ACTION" == install && "$EUID" -ne 0 ]]; then
    fail "la instalación requiere root; no se intentará autoelevar"
fi

REQUIRED_PACKAGES=(ca-certificates coreutils curl grep gzip iproute2 jq libc-bin mawk passwd procps python3 systemd tar util-linux uuid-runtime)
REQUIRED_COMMANDS=(apt-get cut dpkg-query awk curl flock getent grep groupadd gzip id install jq python3 sha256sum sort ss systemctl systemd-analyze tar useradd uuidgen)
missing=()
for package in "${REQUIRED_PACKAGES[@]}"; do
    dpkg-query -s "$package" >/dev/null 2>&1 || missing+=("$package")
done
for command_name in "${REQUIRED_COMMANDS[@]}"; do
    command -v "$command_name" >/dev/null 2>&1 || {
        case "$command_name" in
            apt-get | dpkg-query) ;;
            cut | id) missing+=(coreutils) ;;
            getent) missing+=(libc-bin) ;;
            groupadd | useradd) missing+=(passwd) ;;
            systemctl | systemd-analyze) missing+=(systemd) ;;
            awk) missing+=(mawk) ;;
            curl) missing+=(curl) ;;
            flock) missing+=(util-linux) ;;
            grep) missing+=(grep) ;;
            gzip) missing+=(gzip) ;;
            install | sha256sum | sort) missing+=(coreutils) ;;
            jq) missing+=(jq) ;;
            python3) missing+=(python3) ;;
            ss) missing+=(iproute2) ;;
            tar) missing+=(tar) ;;
            uuidgen) missing+=(uuid-runtime) ;;
        esac
    }
done
if (("${#missing[@]}")); then
    mapfile -t missing < <(printf '%s\n' "${missing[@]}" | sort -u)
fi

info "Plataforma: ${PRETTY_NAME:-$ID}"
info "Arquitectura: $(dpkg --print-architecture 2>/dev/null || uname -m)"
info "Directorio de destino: $APP_ROOT"
if (("${#missing[@]}")); then
    printf 'Dependencias faltantes:\n'
    printf '  - %s\n' "${missing[@]}"
else
    ok "Todas las dependencias requeridas están instaladas"
fi

if [[ "$ACTION" == check ]]; then
    if (("${#missing[@]}")); then
        printf 'CHECK: faltan dependencias; no se modificó el sistema.\n'
        exit 2
    fi
    ok "Comprobación completada; no se modificó el sistema"
    exit 0
fi

if [[ "$SKIP_DEPS" != 1 && "${#missing[@]}" -gt 0 ]]; then
    info "Se actualizarán índices e instalarán únicamente los paquetes faltantes; no se ejecutará apt upgrade."
    DEBIAN_FRONTEND=noninteractive apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${missing[@]}"
fi

for command_name in "${REQUIRED_COMMANDS[@]}"; do
    command -v "$command_name" >/dev/null 2>&1 || fail "dependencia no disponible después de la instalación: $command_name"
done

if [[ -e "$APP_ROOT" || -L "$APP_ROOT" ]]; then
    [[ -d "$APP_ROOT" && ! -L "$APP_ROOT" ]] || fail "el destino existe y no es un directorio seguro: $APP_ROOT"
    if [[ "$(realpath -e -- "$SOURCE_ROOT")" != "$(realpath -e -- "$APP_ROOT")" ]]; then
        fail "el destino ya existe y el origen es distinto; no se sobrescribirá una instalación existente"
    fi
    info "El código ya está ubicado en el destino; se conserva sin sobrescribirlo"
else
    parent="$(dirname -- "$APP_ROOT")"
    install -d -o root -g root -m 755 "$parent"
    [[ ! -L "$parent" ]] || fail "el directorio padre del destino es un enlace simbólico"
    stage="$(mktemp -d "$parent/.xray-manager-install.XXXXXX")"
    cleanup() { [[ -z "${stage:-}" ]] || rm -rf -- "$stage"; }
    trap cleanup EXIT
    cp -a -- "$SOURCE_ROOT/." "$stage/"
    chown -R root:root "$stage"
    find "$stage" -type d -exec chmod 755 {} +
    find "$stage" -type f -exec chmod go-w {} +
    chmod 755 "$stage/install.sh" "$stage/bin/xray-manager"
    mv -- "$stage" "$APP_ROOT"
    stage=""
    trap - EXIT
    ok "Código desplegado en $APP_ROOT"
fi

# Crear exclusivamente directorios del Manager. No tocar /etc/xray ni Xray-core.
install -d -o root -g root -m 700 \
    "$(path /etc/xray-manager)" \
    "$(path /var/lib/xray-manager)" \
    "$(path /var/lib/xray-manager/users)" \
    "$(path /var/lib/xray-manager/connections)" \
    "$(path /var/lib/xray-manager/profiles)" \
    "$(path /var/lib/xray-manager/domains)" \
    "$(path /var/lib/xray-manager/certificates)" \
    "$(path /var/lib/xray-manager/history)" \
    "$(path /var/lib/xray-manager/state)" \
    "$(path /var/log/xray-manager)" \
    "$(path /var/cache/xray-manager)" \
    "$(path /var/backups/xray-manager)"
for directory in \
    "$(path /etc/xray-manager)" \
    "$(path /var/lib/xray-manager)" \
    "$(path /var/lib/xray-manager/users)" \
    "$(path /var/lib/xray-manager/connections)" \
    "$(path /var/lib/xray-manager/profiles)" \
    "$(path /var/lib/xray-manager/domains)" \
    "$(path /var/lib/xray-manager/certificates)" \
    "$(path /var/lib/xray-manager/history)" \
    "$(path /var/lib/xray-manager/state)" \
    "$(path /var/log/xray-manager)" \
    "$(path /var/cache/xray-manager)" \
    "$(path /var/backups/xray-manager)"; do
    chown root:root "$directory"
    chmod 700 "$directory"
done
connections_file="$(path /var/lib/xray-manager/connections/connections.json)"
if [[ ! -e "$connections_file" ]]; then
    printf '[]\n' >"$connections_file"
    chown root:root "$connections_file"
    chmod 600 "$connections_file"
else
    [[ -f "$connections_file" && ! -L "$connections_file" ]] || fail "el registro de conexiones existente no es un archivo regular"
    jq -e 'type == "array"' "$connections_file" >/dev/null || fail "el registro de conexiones existente no es un arreglo JSON; no se modificó"
    chown root:root "$connections_file"
    chmod 600 "$connections_file"
fi

preferences_file="$(path /etc/xray-manager/preferences.conf)"
if [[ ! -e "$preferences_file" ]]; then
    cat >"$preferences_file" <<'PREFS'
XRAY_BIN_PATH=/usr/local/bin/xray
XRAY_DATA_DIR=/usr/local/share/xray
XRAY_CONFIG_DIR=/etc/xray
XRAY_CONFIG_FILE=/etc/xray/config.json
XRAY_MANAGER_BACKUP_DIR=/var/backups/xray-manager
APP_EDITOR=
APP_THEME=cyan
APP_LANGUAGE=es
APP_TIMEZONE=America/Bogota
APP_DATE_FORMAT=dmy
APP_TIME_FORMAT=24h
BACKUP_RETENTION=7
BACKUP_COMPRESSION=gzip
PREFS
    chown root:root "$preferences_file"
    chmod 600 "$preferences_file"
else
    [[ -f "$preferences_file" && ! -L "$preferences_file" ]] || fail "el archivo de preferencias existente no es regular; no se modificó"
    chown root:root "$preferences_file"
    chmod 600 "$preferences_file"
fi

state_file="$(path /var/lib/xray-manager/state/install.json)"
if [[ ! -e "$state_file" ]]; then
    printf '{"manager_installed":true,"installer_version":"%s","installed_at":"%s","xray_installed":false,"service_configured":false}\n' \
        "$INSTALL_VERSION" "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >"$state_file"
    chown root:root "$state_file"
    chmod 600 "$state_file"
else
    [[ -f "$state_file" && ! -L "$state_file" ]] || fail "el registro de instalación existente no es regular; no se modificó"
    chown root:root "$state_file"
    chmod 600 "$state_file"
fi

ok "Directorios, permisos y archivos iniciales del Manager verificados"

# Fase B: instalar el core verificado y preparar su unidad, sin habilitarla ni iniciarla.
XRAY_ADMIN_BIN="/usr/local/bin/xray"
XRAY_ADMIN_DATA="/usr/local/share/xray"
XRAY_MANAGER_CACHE_DIR="$(path /var/cache/xray-manager)"
XRAY_MANAGER_BACKUP_DIR="$(path /var/backups/xray-manager)"
XRAY_CONFIG_DIR="/etc/xray"
XRAY_CONFIG_FILE="/etc/xray/config.json"
XRAY_SERVICE_ROOT="$PREFIX"
if [[ "$PREFIX" != "/" ]]; then
    [[ "${XRAY_MANAGER_SKIP_XRAY_INSTALL:-0}" == 1 && "$SKIP_DEPS" == 1 ]] ||
        fail "el prefijo aislado requiere XRAY_MANAGER_SKIP_XRAY_INSTALL=1 y XRAY_MANAGER_SKIP_DEPENDENCIES=1"
    XRAY_SERVICE_TEST_MODE=1
fi
export APP_ROOT XRAY_ADMIN_BIN XRAY_ADMIN_DATA XRAY_MANAGER_CACHE_DIR
export XRAY_MANAGER_BACKUP_DIR XRAY_CONFIG_DIR XRAY_CONFIG_FILE XRAY_SERVICE_ROOT XRAY_SERVICE_TEST_MODE
# shellcheck disable=SC1091
. "$APP_ROOT/config/xray-version.conf"
# shellcheck disable=SC1091
. "$APP_ROOT/modules/xray_admin.sh"
# shellcheck disable=SC1091
. "$APP_ROOT/modules/xray_service.sh"
xray_service_preflight || fail "las condiciones previas del servicio Xray no son seguras"
if [[ "${XRAY_MANAGER_SKIP_XRAY_INSTALL:-0}" == 1 ]]; then
    [[ "$PREFIX" != "/" && -x "$(path /usr/local/bin/xray)" && -d "$(path /usr/local/share/xray)" ]] ||
        fail "el modo de pruebas requiere un binario Xray ficticio y geodata en el prefijo aislado"
    info "Modo de pruebas: se omite la descarga real de Xray-core"
else
    if [[ -x "$(path /usr/local/bin/xray)" ]]; then
        if [[ -f "$(path /usr/local/share/xray/geoip.dat)" && -f "$(path /usr/local/share/xray/geosite.dat)" ]]; then
            info "Actualizando/verificando Xray-core ${XRAY_VERSION} con verificación SHA-256 y rollback"
            xray_admin_install_version "$XRAY_VERSION" update ||
                fail "falló la actualización/verificación de Xray-core"
        else
            info "Reparando Xray-core ${XRAY_VERSION}: falta binario/geodata íntegro"
            xray_admin_install_version "$XRAY_VERSION" repair ||
                fail "falló la reparación verificada de Xray-core"
        fi
    else
        info "Instalando Xray-core ${XRAY_VERSION} con verificación SHA-256 y rollback"
        xray_admin_install_version "$XRAY_VERSION" install ||
            fail "falló la instalación verificada de Xray-core"
    fi
fi
xray_service_prepare || fail "no se pudo preparar la identidad/unidad systemd de Xray-core"

state_tmp="$(mktemp "$(dirname "$state_file")/.install-state.XXXXXX")"
jq -e 'type == "object"' "$state_file" >/dev/null ||
    fail "el registro de instalación no es un objeto JSON válido"
jq '.xray_installed = true | .service_configured = true' "$state_file" >"$state_tmp" ||
    fail "no se pudo actualizar el registro de instalación"
chown root:root "$state_tmp"
chmod 600 "$state_tmp"
mv -f -- "$state_tmp" "$state_file"

printf '\nINSTALACIÓN DEL MANAGER Y PREPARACIÓN DE XRAY COMPLETADAS\n'
printf '  Código:       %s\n' "$APP_ROOT"
printf '  Conexiones:   %s\n' "$connections_file"
printf '  Preferencias: %s\n' "$preferences_file"
printf '  Estado:       %s\n' "$state_file"
printf '\nXray-core quedó instalado; xray.service está detenido y deshabilitado.\n'
printf 'El registro de usuarios no se inicializó ni migró.\n'