#!/usr/bin/env bash
# Instala Xray Core Manager; Xray-core es una fase opcional explícita.
set -Eeuo pipefail
IFS=$'\n\t'
umask 077

readonly INSTALL_VERSION="1"
readonly DEFAULT_PREFIX="/"
readonly GITHUB_REPOSITORY="Jaok04/xray-core-manager"
readonly GITHUB_BRANCH="design/user-identity-association-v1"
readonly BOOTSTRAP_HELPER_SHA256="85b508da1a94d9ec392d3ac01259bf4326a45df97105b9471aeee2bee470f98d"
PREFIX="${XRAY_MANAGER_INSTALL_PREFIX:-$DEFAULT_PREFIX}"
SKIP_DEPS="${XRAY_MANAGER_SKIP_DEPENDENCIES:-0}"
ACTION="install"
INSTALL_REQUESTED=0
WITH_XRAY=0

usage() {
    cat <<'USAGE'
Uso: sudo ./install.sh [--check | --install [--with-xray]] [--help]

  --check       Comprueba plataforma, privilegios y dependencias; no modifica nada.
  --install     Descarga/verifica el árbol privado si hace falta e instala únicamente Xray Core Manager.
  --with-xray   Añade explícitamente la instalación verificada de Xray-core y
                la preparación de xray.service. Requiere --install.
  --help        Muestra esta ayuda.

Si sólo tienes este archivo, solicita un Fine-grained PAT con Contents: Read-only
para Jaok04/xray-core-manager y descarga/verifica el commit de la rama autorizada.
Por defecto no instala Xray-core, no crea la cuenta xray ni modifica systemd.
Xray-core puede instalarse después desde Administración de Xray-core.
Incluso con --with-xray, el servicio queda detenido y deshabilitado.
USAGE
}

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}
info() { printf '[INFO] %s\n' "$*"; }
ok() { printf '[OK] %s\n' "$*"; }

BOOTSTRAP_DIR=""
APT_UPDATED=0
cleanup_bootstrap() {
    if [[ -n "${BOOTSTRAP_DIR:-}" && -d "$BOOTSTRAP_DIR" ]]; then
        rm -rf -- "$BOOTSTRAP_DIR"
    fi
}

while (($#)); do
    case "$1" in
        --check) ACTION=check ;;
        --install) ACTION=install; INSTALL_REQUESTED=1 ;;
        --with-xray) WITH_XRAY=1 ;;
        --help | -h)
            usage
            exit 0
            ;;
        *) fail "argumento desconocido: $1" ;;
    esac
    shift
done

SOURCE_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
SOURCE_TREE_VALID=0
if [[ -f "$SOURCE_ROOT/bin/xray-manager" && -f "$SOURCE_ROOT/config/paths.sh" &&
    -f "$SOURCE_ROOT/modules/main_menu.sh" && -f "$SOURCE_ROOT/lib/json_store.sh" &&
    -f "$SOURCE_ROOT/lib/operation_lock.sh" && -f "$SOURCE_ROOT/scripts/installer_bootstrap.py" ]]; then
    SOURCE_TREE_VALID=1
fi
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
[[ "$WITH_XRAY" == 0 || ( "$ACTION" == install && "$INSTALL_REQUESTED" == 1 ) ]] ||
    fail "--with-xray requiere --install"
[[ -r /etc/os-release ]] || fail "no se pudo identificar la distribución Linux"
# shellcheck disable=SC1091
. /etc/os-release
if ! grep -Eiq '^(ID=(ubuntu|debian)|ID_LIKE=.*(ubuntu|debian))' /etc/os-release; then
    fail "plataforma no compatible: se requiere Ubuntu o Debian con apt-get"
fi
if [[ "$ACTION" == install && "$EUID" -ne 0 ]]; then
    fail "la instalación requiere root; no se intentará autoelevar"
fi

# Preflight de rutas y archivos persistentes antes de apt-get o del despliegue.
parent="$(dirname -- "$APP_ROOT")"
for candidate in \
    "$APP_ROOT" "$parent" \
    "$(path /etc/xray-manager)" \
    "$(path /etc/xray-manager/keys)" \
    "$(path /var/lib/xray-manager)" \
    "$(path /var/lib/xray-manager/users)" \
    "$(path /var/lib/xray-manager/connections)" \
    "$(path /var/lib/xray-manager/connections/configurations)" \
    "$(path /var/lib/xray-manager/secrets)" \
    "$(path /var/lib/xray-manager/profiles)" \
    "$(path /var/lib/xray-manager/domains)" \
    "$(path /var/lib/xray-manager/certificates)" \
    "$(path /var/lib/xray-manager/history)" \
    "$(path /var/lib/xray-manager/state)" \
    "$(path /var/log/xray-manager)" \
    "$(path /var/cache/xray-manager)" \
    "$(path /var/backups/xray-manager)" \
    "$(path /var/lib/xray-manager/connections/connections.json)" \
    "$(path /etc/xray-manager/preferences.conf)" \
    "$(path /var/lib/xray-manager/state/install.json)"; do
    assert_no_symlink_components "$candidate"
done
if [[ "$WITH_XRAY" == 1 ]]; then
    for candidate in \
        "$(path /var/lib/xray)" \
        "$(path /etc/xray)" \
        "$(path /usr/local/bin/xray)" \
        "$(path /usr/local/share/xray)" \
        "$(path /etc/systemd/system)" \
        "$(path /etc/systemd/system/xray.service)"; do
        assert_no_symlink_components "$candidate"
    done
fi
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

# Bootstrap: cuando se ejecuta el único install.sh descargado, obtiene el
# helper autenticado y el árbol completo de un commit inmutable de GitHub.
if [[ "$SOURCE_TREE_VALID" != 1 ]]; then
    [[ "$ACTION" == install ]] ||
        fail "--check requiere el árbol del proyecto; use --install para descargarlo desde GitHub"
    [[ ! -e "$APP_ROOT" && ! -L "$APP_ROOT" ]] ||
        fail "ya existe $APP_ROOT; ejecute el instalador desde esa instalación para evitar sobrescrituras"

    if ! command -v python3 >/dev/null 2>&1 || ! dpkg-query -s ca-certificates >/dev/null 2>&1; then
        info "Preparando únicamente Python 3 y certificados CA para autenticar la descarga inicial."
        DEBIAN_FRONTEND=noninteractive apt-get update
        DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3 ca-certificates
        APT_UPDATED=1
    fi
    command -v python3 >/dev/null 2>&1 || fail "Python 3 no está disponible para verificar la distribución"

    if [[ -z "${XRAY_MANAGER_GITHUB_TOKEN:-}" ]]; then
        [[ -t 0 ]] || fail "falta XRAY_MANAGER_GITHUB_TOKEN; ejecútelo en una terminal interactiva o proporciónelo por entorno"
        read -r -s -p "Fine-grained GitHub PAT (Contents: Read-only): " XRAY_MANAGER_GITHUB_TOKEN
        printf '\n'
    fi
    [[ -n "${XRAY_MANAGER_GITHUB_TOKEN:-}" ]] || fail "el token de GitHub está vacío"
    export XRAY_MANAGER_GITHUB_TOKEN

    [[ ! -L /var/tmp ]] || fail "/var/tmp no puede ser un enlace simbólico durante el bootstrap"
    BOOTSTRAP_DIR="$(mktemp -d /var/tmp/xray-manager-bootstrap.XXXXXX)"
    chmod 700 "$BOOTSTRAP_DIR"
    trap cleanup_bootstrap EXIT
    info "Autenticando con GitHub y resolviendo una revisión inmutable de $GITHUB_REPOSITORY."
    python3 - "$GITHUB_REPOSITORY" "$GITHUB_BRANCH" "$BOOTSTRAP_HELPER_SHA256" "$BOOTSTRAP_DIR" "${XRAY_MANAGER_GITHUB_COMMIT_SHA:-}" <<'PYBOOTSTRAP'
import base64
import hashlib
import json
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

repo, ref, expected_helper_sha256, destination, pinned_commit = sys.argv[1:]
token = os.environ.get("XRAY_MANAGER_GITHUB_TOKEN", "")
if not token:
    raise SystemExit("ERROR: no se recibió el token de GitHub.")
api = "https://api.github.com"
headers = {
    "Authorization": "Bearer " + token,
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "xray-core-manager-installer",
}
def get_json(url):
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=45) as response:
            raw = response.read(32 * 1024 * 1024 + 1)
    except HTTPError as exc:
        if exc.code in (401, 403, 404):
            raise SystemExit("ERROR: GitHub rechazó el acceso. Verifique el PAT y Contents: Read-only para Jaok04/xray-core-manager.")
        raise SystemExit("ERROR: GitHub respondió HTTP " + str(exc.code) + ".")
    except (URLError, TimeoutError, OSError):
        raise SystemExit("ERROR: no se pudo conectar con GitHub.")
    if len(raw) > 32 * 1024 * 1024:
        raise SystemExit("ERROR: respuesta API demasiado grande.")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise SystemExit("ERROR: GitHub devolvió JSON inválido.")
    if not isinstance(value, dict):
        raise SystemExit("ERROR: estructura API inesperada.")
    return value

ref_value = pinned_commit if pinned_commit else ref
commit_data = get_json(f"{api}/repos/{repo}/commits/{quote(ref_value, safe='')}")
commit_sha = commit_data.get("sha")
tree_sha = (commit_data.get("commit") or {}).get("tree", {}).get("sha")
if not isinstance(commit_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", commit_sha):
    raise SystemExit("ERROR: SHA de commit inválido.")
if pinned_commit and commit_sha != pinned_commit:
    raise SystemExit("ERROR: GitHub no confirmó el commit fijado por el bootstrap.")
if not isinstance(tree_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", tree_sha):
    raise SystemExit("ERROR: SHA de árbol Git inválido.")
tree = get_json(f"{api}/repos/{repo}/git/trees/{tree_sha}?recursive=1")
if tree.get("sha") != tree_sha or tree.get("truncated") is not False:
    raise SystemExit("ERROR: árbol Git inconsistente o truncado.")
entries = tree.get("tree")
if not isinstance(entries, list):
    raise SystemExit("ERROR: árbol Git inválido.")
helper = next((item for item in entries if item.get("path") == "scripts/installer_bootstrap.py"), None)
if not isinstance(helper, dict) or helper.get("type") != "blob" or helper.get("mode") != "100644":
    raise SystemExit("ERROR: no se encontró el helper de bootstrap esperado.")
blob_sha = helper.get("sha")
if not isinstance(blob_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", blob_sha):
    raise SystemExit("ERROR: SHA del helper inválido.")
blob = get_json(f"{api}/repos/{repo}/git/blobs/{blob_sha}")
if blob.get("encoding") != "base64" or not isinstance(blob.get("content"), str):
    raise SystemExit("ERROR: GitHub no entregó el helper como blob base64.")
try:
    helper_bytes = base64.b64decode("".join(blob["content"].split()), validate=True)
except (ValueError, TypeError):
    raise SystemExit("ERROR: contenido base64 del helper inválido.")
git_sha = hashlib.sha1(b"blob " + str(len(helper_bytes)).encode("ascii") + b"\0" + helper_bytes).hexdigest()
sha256 = hashlib.sha256(helper_bytes).hexdigest()
if git_sha != blob_sha or sha256 != expected_helper_sha256:
    raise SystemExit("ERROR: la integridad del helper de bootstrap no coincide.")
with open(os.path.join(destination, "installer_bootstrap.py"), "xb") as output:
    output.write(helper_bytes)
with open(os.path.join(destination, "tree.json"), "x", encoding="utf-8") as output:
    json.dump(tree, output, separators=(",", ":"))
with open(os.path.join(destination, "revision.json"), "x", encoding="utf-8") as output:
    json.dump({"commit": commit_sha, "tree": tree_sha}, output)
print("[OK] Helper verificado; revisión GitHub: " + commit_sha)
PYBOOTSTRAP
    python3 "$BOOTSTRAP_DIR/installer_bootstrap.py" \
        --repo "$GITHUB_REPOSITORY" \
        --commit "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["commit"])' "$BOOTSTRAP_DIR/revision.json")" \
        --tree-sha "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["tree"])' "$BOOTSTRAP_DIR/revision.json")" \
        --tree-file "$BOOTSTRAP_DIR/tree.json" \
        --destination "$BOOTSTRAP_DIR/source"
    unset XRAY_MANAGER_GITHUB_TOKEN
    SOURCE_ROOT="$BOOTSTRAP_DIR/source"
    SOURCE_TREE_VALID=1
fi

[[ -f "$SOURCE_ROOT/bin/xray-manager" && -f "$SOURCE_ROOT/config/paths.sh" &&
    -f "$SOURCE_ROOT/modules/main_menu.sh" && -f "$SOURCE_ROOT/lib/json_store.sh" &&
    -f "$SOURCE_ROOT/lib/operation_lock.sh" && -f "$SOURCE_ROOT/scripts/installer_bootstrap.py" ]] ||
    fail "el origen no contiene un árbol válido de Xray Core Manager"

REQUIRED_PACKAGES=(ca-certificates coreutils curl grep gzip iproute2 jq libc-bin mawk passwd procps python3 python3-cryptography systemd tar util-linux uuid-runtime)
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

# Serializa el despliegue completo frente a otras operaciones de ciclo de vida.
. "$SOURCE_ROOT/lib/operation_lock.sh"
lifecycle_fd='' data_fd=''
lifecycle_lock="${XRAY_MANAGER_LIFECYCLE_LOCK:-$(path /run/lock/xray-manager-lifecycle.lock)}"
if ! manager_lock_acquire "$lifecycle_lock" lifecycle_fd; then
    fail "ya hay otra operación de ciclo de vida del Manager en curso o no se pudo adquirir su bloqueo"
fi
data_lock="${XRAY_MANAGER_INTEGRITY_LOCK:-$(path /run/xray-manager/integrity.lock)}"
if ! manager_lock_acquire "$data_lock" data_fd; then
    printf 'ERROR: hay una operación de usuarios/conexiones en curso o no se pudo adquirir su bloqueo.\n' >&2
    manager_lock_release "$lifecycle_fd"
    exit 1
fi
trap 'manager_lock_release "$data_fd"; manager_lock_release "$lifecycle_fd"; cleanup_bootstrap' EXIT

if [[ "$SKIP_DEPS" != 1 && "${#missing[@]}" -gt 0 ]]; then
    info "Se actualizarán índices e instalarán únicamente los paquetes faltantes; no se ejecutará apt upgrade."
    if [[ "$APT_UPDATED" != 1 ]]; then
        DEBIAN_FRONTEND=noninteractive apt-get update
    fi
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
    cleanup_stage() { [[ -z "${stage:-}" ]] || rm -rf -- "$stage"; }
    trap 'cleanup_stage; manager_lock_release "$data_fd"; manager_lock_release "$lifecycle_fd"; cleanup_bootstrap' EXIT
    cp -a -- "$SOURCE_ROOT/." "$stage/"
    chown -R root:root "$stage"
    find "$stage" -type d -exec chmod 755 {} +
    find "$stage" -type f -exec chmod go-w {} +
    chmod 755 "$stage/install.sh" "$stage/bin/xray-manager"
    mv -- "$stage" "$APP_ROOT"
    stage=""
    ok "Código desplegado en $APP_ROOT"
fi

# Crear exclusivamente directorios del Manager. No tocar /etc/xray ni Xray-core.
install -d -o root -g root -m 700 \
    "$(path /etc/xray-manager)" \
    "$(path /etc/xray-manager/keys)" \
    "$(path /var/lib/xray-manager)" \
    "$(path /var/lib/xray-manager/users)" \
    "$(path /var/lib/xray-manager/connections)" \
    "$(path /var/lib/xray-manager/connections/configurations)" \
    "$(path /var/lib/xray-manager/secrets)" \
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
    "$(path /etc/xray-manager/keys)" \
    "$(path /var/lib/xray-manager)" \
    "$(path /var/lib/xray-manager/users)" \
    "$(path /var/lib/xray-manager/connections)" \
    "$(path /var/lib/xray-manager/connections/configurations)" \
    "$(path /var/lib/xray-manager/secrets)" \
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

if [[ "$WITH_XRAY" == 1 ]]; then
# Fase B: instalar el core verificado y preparar su unidad, sin habilitarla ni iniciarla.
XRAY_ADMIN_BIN="/usr/local/bin/xray"
XRAY_ADMIN_DATA="/usr/local/share/xray"
XRAY_ADMIN_MANIFEST="$(path /var/lib/xray-manager/state/xray-install.json)"
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
export XRAY_MANAGER_LIFECYCLE_LOCK_HELD=1 XRAY_MANAGER_LIFECYCLE_LOCK="$lifecycle_lock"
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

else
    printf '\nINSTALACIÓN DE XRAY CORE MANAGER COMPLETADA\n'
    printf '  Código:       %s\n' "$APP_ROOT"
    printf '  Conexiones:   %s\n' "$connections_file"
    printf '  Preferencias: %s\n' "$preferences_file"
    printf '  Estado:       %s\n' "$state_file"
    printf '\nXray-core no fue instalado y xray.service no fue creado ni modificado.\n'
    printf 'Usa Administración de Xray-core → Instalar Xray-core cuando quieras instalarlo.\n'
fi
