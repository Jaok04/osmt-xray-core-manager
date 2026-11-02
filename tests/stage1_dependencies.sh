#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
source "$ROOT/config/manager.conf"
source "$ROOT/config/paths.sh"
source "$ROOT/lib/ui.sh"
source "$ROOT/modules/system_admin.sh"

tmp="$(mktemp -d)"
XRAY_MANAGER_LIFECYCLE_LOCK="$tmp/lifecycle.lock"
export XRAY_MANAGER_LIFECYCLE_LOCK
trap 'rm -rf -- "$tmp"' EXIT
MANAGER_APT_GET="$tmp/apt-get"
cat >"$MANAGER_APT_GET" <<'STUB'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"$APT_CALL_LOG"
STUB
chmod 700 "$MANAGER_APT_GET"
APT_CALL_LOG="$tmp/apt.log"
export APT_CALL_LOG

expected="$(printf '%s\n' apt ca-certificates coreutils curl dpkg grep gzip iproute2 jq mawk procps python3 tar util-linux uuid-runtime libc-bin passwd systemd | sort -u)"
actual="$(manager_dependencies_packages)"
[[ "$actual" == "$expected" ]]

# apt y dpkg son infraestructura del SO: no deben actualizarse desde Etapa 1.
cat >"$tmp/dpkg-query" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
chmod 700 "$tmp/dpkg-query"
old_path="$PATH"
PATH="$tmp:$PATH"
upgrade_packages="$(manager_dependencies_installed_packages)"
PATH="$old_path"
if grep -Fxq apt <<<"$upgrade_packages"; then
    printf 'ERROR: Etapa 1 intentaría actualizar apt.\\n' >&2
    exit 1
fi
if grep -Fxq dpkg <<<"$upgrade_packages"; then
    printf 'ERROR: Etapa 1 intentaría actualizar dpkg.\\n' >&2
    exit 1
fi
grep -Fxq curl <<<"$upgrade_packages"

printf '1\n\n0\n' | manager_dependencies_menu >"$tmp/menu.out"
grep -q 'COMPROBACIÓN DE DEPENDENCIAS' "$tmp/menu.out"
grep -q 'No se comprueban ni actualizan aquí los paquetes generales del sistema' "$tmp/menu.out"

manager_dependencies_missing_packages() { printf 'fake-required-package\n'; }
ui_confirm() { return 1; }
printf '\n' | manager_dependencies_install_missing >"$tmp/install-cancel.out"
grep -q 'Operación cancelada' "$tmp/install-cancel.out"
[[ ! -s "$APT_CALL_LOG" ]]

manager_dependencies_installed_packages() { printf 'curl\njq\n'; }
printf '\n' | manager_dependencies_update >"$tmp/update-cancel.out"
grep -q 'Operación cancelada' "$tmp/update-cancel.out"
[[ ! -s "$APT_CALL_LOG" ]]

exec {busy_fd}>"$XRAY_MANAGER_LIFECYCLE_LOCK"
flock -x "$busy_fd"
ui_confirm() { return 0; }
if printf '\n' | manager_dependencies_install_missing >"$tmp/install-lock-busy.out" 2>&1; then
    printf 'ERROR: dependencias ignoró el bloqueo de ciclo de vida.\n' >&2
    exit 1
fi
grep -q 'otra operación de ciclo de vida' "$tmp/install-lock-busy.out"
[[ ! -s "$APT_CALL_LOG" ]]
flock -u "$busy_fd"
exec {busy_fd}>&-

manager_dependencies_require_root() { :; }
manager_dependencies_require_apt() { :; }
manager_dependencies_missing_packages() { printf 'fake-required-package\n'; }
ui_confirm() { return 0; }
manager_dependencies_report() { :; }
printf '\n' | manager_dependencies_install_missing >"$tmp/install.out"
grep -Fxq 'update' "$APT_CALL_LOG"
grep -Fxq 'install -y --no-install-recommends fake-required-package' "$APT_CALL_LOG"
: >"$APT_CALL_LOG"
manager_dependencies_installed_packages() { printf 'curl\njq\n'; }
printf '\n' | manager_dependencies_update >"$tmp/update.out"
grep -Fxq 'update' "$APT_CALL_LOG"
grep -Fxq 'install --only-upgrade -y --no-install-recommends curl jq' "$APT_CALL_LOG"

printf 'OK: catálogo de dependencias, comprobación, delimitación de paquetes y cancelación sin ejecutar apt-get.\n'
