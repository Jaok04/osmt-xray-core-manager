#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT
PREFIX="$TMP/root"
export XRAY_MANAGER_INSTALL_PREFIX="$PREFIX"
export XRAY_MANAGER_SKIP_DEPENDENCIES=1
export XRAY_MANAGER_SKIP_XRAY_INSTALL=1
mkdir -p "$PREFIX/usr/local/bin" "$PREFIX/usr/local/share/xray"
cat >"$PREFIX/usr/local/bin/xray" <<'BIN'
#!/usr/bin/env bash
printf 'Xray 26.10.31 test fixture\\n'
BIN
chmod 755 "$PREFIX/usr/local/bin/xray"
printf 'geoip fixture\\n' >"$PREFIX/usr/local/share/xray/geoip.dat"
printf 'geosite fixture\\n' >"$PREFIX/usr/local/share/xray/geosite.dat"

bash -n "$ROOT/install.sh"
"$ROOT/install.sh" --help >"$TMP/help.out"
grep -q -- '--check' "$TMP/help.out"
grep -q 'no habilita ni inicia el servicio' "$TMP/help.out"

"$ROOT/install.sh" --install >"$TMP/install.out"
APP="$PREFIX/opt/xray-manager"
[[ -x "$APP/bin/xray-manager" && -x "$APP/install.sh" ]]
[[ -f "$PREFIX/etc/xray-manager/preferences.conf" ]]
[[ -f "$PREFIX/var/lib/xray-manager/connections/connections.json" ]]
[[ -f "$PREFIX/var/lib/xray-manager/state/install.json" ]]
[[ ! -e "$PREFIX/var/lib/xray-manager/users/users.json" ]]
[[ ! -e "$PREFIX/etc/xray/config.json" ]]
[[ -x "$PREFIX/usr/local/bin/xray" ]]
[[ -f "$PREFIX/usr/local/share/xray/geoip.dat" ]]
[[ -f "$PREFIX/usr/local/share/xray/geosite.dat" ]]
[[ -f "$PREFIX/etc/systemd/system/xray.service" ]]
grep -Fq 'User=xray' "$PREFIX/etc/systemd/system/xray.service"
grep -Fq 'ExecStartPre=/usr/local/bin/xray run -test -config /etc/xray/config.json' "$PREFIX/etc/systemd/system/xray.service"
[[ "$(stat -c '%a' "$PREFIX/etc/xray-manager")" == 700 ]]
[[ "$(stat -c '%a' "$PREFIX/etc/xray-manager/preferences.conf")" == 600 ]]
[[ "$(stat -c '%a' "$PREFIX/var/lib/xray-manager/connections/connections.json")" == 600 ]]
jq -e 'type == "array" and length == 0' "$PREFIX/var/lib/xray-manager/connections/connections.json" >/dev/null
jq -e '.manager_installed == true and .xray_installed == true and .service_configured == true' "$PREFIX/var/lib/xray-manager/state/install.json" >/dev/null

printf '[]\n' >"$PREFIX/var/lib/xray-manager/connections/connections.json"
printf 'APP_THEME=green\n' >>"$PREFIX/etc/xray-manager/preferences.conf"
XRAY_MANAGER_INSTALL_PREFIX="$PREFIX" XRAY_MANAGER_SKIP_DEPENDENCIES=1 \
    bash "$APP/install.sh" --install >"$TMP/reinstall.out"
grep -q 'APP_THEME=green' "$PREFIX/etc/xray-manager/preferences.conf"
[[ "$(jq 'length' "$PREFIX/var/lib/xray-manager/connections/connections.json")" == 0 ]]

OTHER="$TMP/other-source"
mkdir -p "$OTHER/opt/xray-manager"
printf 'preserve\n' >"$OTHER/opt/xray-manager/marker"
if XRAY_MANAGER_INSTALL_PREFIX="$OTHER" XRAY_MANAGER_SKIP_DEPENDENCIES=1 \
    "$ROOT/install.sh" --install >"$TMP/collision.out" 2>&1; then
    printf 'ERROR: se permitió sobrescribir un destino preexistente.\n' >&2
    exit 1
fi
grep -q 'no se sobrescribirá una instalación existente' "$TMP/collision.out"
[[ "$(cat "$OTHER/opt/xray-manager/marker")" == preserve ]]

BAD="$TMP/bad"
mkdir -p "$BAD/var/lib/xray-manager/connections"
printf '{invalid\n' >"$BAD/var/lib/xray-manager/connections/connections.json"
if XRAY_MANAGER_INSTALL_PREFIX="$BAD" XRAY_MANAGER_SKIP_DEPENDENCIES=1 \
    "$APP/install.sh" --install >"$TMP/bad.out" 2>&1; then
    printf 'ERROR: se aceptó un registro de conexiones inválido.\n' >&2
    exit 1
fi
grep -q 'no es un arreglo JSON' "$TMP/bad.out"
[[ "$(cat "$BAD/var/lib/xray-manager/connections/connections.json")" == '{invalid' ]]

BAD_STATE="$TMP/bad-state"
mkdir -p "$BAD_STATE/var/lib/xray-manager/state"
printf '{invalid' >"$BAD_STATE/var/lib/xray-manager/state/install.json"
if XRAY_MANAGER_INSTALL_PREFIX="$BAD_STATE" XRAY_MANAGER_SKIP_DEPENDENCIES=1 XRAY_MANAGER_SKIP_XRAY_INSTALL=1 "$ROOT/install.sh" --install >"$TMP/bad-state.out" 2>&1; then
    echo "ERROR: se aceptó un registro de instalación inválido." >&2
    exit 1
fi
grep -q 'no es un objeto JSON válido' "$TMP/bad-state.out"
[[ ! -e "$BAD_STATE/opt/xray-manager" ]]

LINKED="$TMP/linked"
OUTSIDE="$TMP/outside"
mkdir -p "$LINKED/var/lib" "$OUTSIDE"
ln -s "$OUTSIDE" "$LINKED/var/lib/xray-manager"
if XRAY_MANAGER_INSTALL_PREFIX="$LINKED" XRAY_MANAGER_SKIP_DEPENDENCIES=1 \
    "$ROOT/install.sh" --install >"$TMP/symlink.out" 2>&1; then
    printf 'ERROR: se aceptó un componente simbólico en rutas persistentes.\n' >&2
    exit 1
fi
grep -q 'componente simbólico' "$TMP/symlink.out"
[[ ! -e "$LINKED/opt/xray-manager" ]]
[[ -z "$(find "$OUTSIDE" -mindepth 1 -print -quit)" ]]

printf '%s\n' 'OK: instalador, despliegue aislado, permisos, idempotencia, protección de datos, colisiones y rutas simbólicas.'

# Un despliegue concurrente debe abortar antes de crear rutas o datos.
LOCKED="$TMP/locked-install"
LIFECYCLE_LOCK="$TMP/installer-lifecycle.lock"
exec {busy_fd}>"$LIFECYCLE_LOCK"
flock -x "$busy_fd"
if XRAY_MANAGER_INSTALL_PREFIX="$LOCKED" XRAY_MANAGER_LIFECYCLE_LOCK="$LIFECYCLE_LOCK" \
    XRAY_MANAGER_SKIP_DEPENDENCIES=1 XRAY_MANAGER_SKIP_XRAY_INSTALL=1 \
    "$ROOT/install.sh" --install >"$TMP/locked-install.out" 2>&1; then
    printf 'ERROR: se permitió un instalador concurrente.\n' >&2
    exit 1
fi
grep -q 'operación de ciclo de vida' "$TMP/locked-install.out"
[[ ! -e "$LOCKED/opt/xray-manager" ]]
flock -u "$busy_fd"
exec {busy_fd}>&-

DATA_LOCKED="$TMP/data-locked-install"
DATA_LOCK="$TMP/installer-data.lock"
exec {busy_data_fd}>"$DATA_LOCK"
flock -x "$busy_data_fd"
if XRAY_MANAGER_INSTALL_PREFIX="$DATA_LOCKED" XRAY_MANAGER_LIFECYCLE_LOCK="$TMP/data-case-lifecycle.lock" \
    XRAY_MANAGER_INTEGRITY_LOCK="$DATA_LOCK" XRAY_MANAGER_SKIP_DEPENDENCIES=1 \
    XRAY_MANAGER_SKIP_XRAY_INSTALL=1 "$ROOT/install.sh" --install >"$TMP/locked-data-install.out" 2>&1; then
    printf 'ERROR: el instalador ignoró el bloqueo de usuarios/conexiones.\n' >&2
    exit 1
fi
grep -q 'operación de usuarios/conexiones' "$TMP/locked-data-install.out"
[[ ! -e "$DATA_LOCKED/opt/xray-manager" ]]
flock -u "$busy_data_fd"
exec {busy_data_fd}>&-