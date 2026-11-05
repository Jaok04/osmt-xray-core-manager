#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
APP_ROOT="$ROOT"
source "$ROOT/config/manager.conf"
source "$ROOT/config/xray-version.conf"
source "$ROOT/modules/xray_admin.sh"
source "$ROOT/modules/xray_service.sh"

tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
XRAY_ADMIN_BIN="$tmp/bin/xray"
XRAY_ADMIN_DATA="$tmp/share"
XRAY_ADMIN_MANIFEST="$tmp/state/xray-install.json"
XRAY_MANAGER_LIFECYCLE_LOCK="$tmp/lifecycle.lock"
mkdir -p "$tmp/bin" "$tmp/share" "$tmp/state"
chmod 700 "$tmp/state"
cat >"$XRAY_ADMIN_BIN" <<'BIN'
#!/usr/bin/env bash
printf 'Xray 26.10.31 fixture\n'
BIN
chmod 755 "$XRAY_ADMIN_BIN"
printf 'geoip-fixture\n' >"$XRAY_ADMIN_DATA/geoip.dat"
printf 'geosite-fixture\n' >"$XRAY_ADMIN_DATA/geosite.dat"
chmod 644 "$XRAY_ADMIN_DATA/"*
xray_admin_record_installation 26.10.31 "$(printf '%064d' 1)" >/dev/null

ui_clear() { :; }
ui_title() { :; }
ui_pause() { :; }
CONFIRM=1
ui_confirm() { [[ "$CONFIRM" == 1 ]]; }
PREPARE_COUNT=0
xray_service_prepare() {
    ((PREPARE_COUNT += 1))
}

# Integridad correcta y confirmación explícita: se invoca una sola vez.
xray_admin_prepare_service_menu_action >"$tmp/valid.out"
[[ "$PREPARE_COUNT" == 1 ]]
grep -q 'Xray 26.10.31 íntegro' "$tmp/valid.out"
grep -q 'No iniciará ni habilitará' "$tmp/valid.out"

# Cancelar no invoca la preparación.
CONFIRM=0
xray_admin_prepare_service_menu_action >"$tmp/cancel.out"
[[ "$PREPARE_COUNT" == 1 ]]
grep -q 'cancelada' "$tmp/cancel.out"

CONFIRM=1
# El bloqueo de ciclo de vida ocupado impide ejecutar la preparación.
exec {busy_fd}>"$XRAY_MANAGER_LIFECYCLE_LOCK"
flock -x "$busy_fd"
if xray_admin_prepare_service_menu_action >"$tmp/busy.out" 2>&1; then
    printf 'ERROR: preparación ignoró el bloqueo de ciclo de vida.\\n' >&2
    exit 1
fi
[[ "$PREPARE_COUNT" == 1 ]]
grep -q 'otra operación de ciclo de vida' "$tmp/busy.out"
flock -u "$busy_fd"
exec {busy_fd}>&-

# Cualquier alteración bloquea el flujo antes de pedir/ejecutar preparación.
CONFIRM=1
printf 'tampered\n' >>"$XRAY_ADMIN_DATA/geosite.dat"
if xray_admin_prepare_service_menu_action >"$tmp/tampered.out" 2>&1; then
    printf 'ERROR: se permitió preparar servicio con geodata alterado.\n' >&2
    exit 1
fi
[[ "$PREPARE_COUNT" == 1 ]]
grep -q 'no está verificada' "$tmp/tampered.out"

# Una instalación heredada sin manifiesto también queda bloqueada.
mv "$XRAY_ADMIN_MANIFEST" "$XRAY_ADMIN_MANIFEST.saved"
if xray_admin_prepare_service_menu_action >"$tmp/legacy.out" 2>&1; then
    printf 'ERROR: se permitió preparar servicio sin manifiesto.\n' >&2
    exit 1
fi
[[ "$PREPARE_COUNT" == 1 ]]
grep -q 'no está verificada' "$tmp/legacy.out"

printf '%s\n' 'OK: preparación del servicio protegida por integridad, confirmación y cancelación.'
