#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT
export APP_ROOT="$ROOT"
source "$ROOT/modules/profiles.sh"
ui_clear() { :; }
ui_title() { :; }
ui_pause() { :; }
ui_read_option() { local prompt="$1" target="$2"; read -r "$target"; }

unset XRAY_RUNTIME_MENU_FIXTURE_MODE
output="$(profiles_apply_fixture_menu)"
grep -q 'deshabilitada en el entorno normal' <<<"$output"
grep -q 'No se ha habilitado aplicación real' <<<"$output"

profiles_apply_fixture_menu() { printf 'FIXTURE_MENU_ROUTE_OK\n'; }
printf '4\n0\n' | menu_config_profiles_backups >"$TMP/menu.out"
grep -q 'FIXTURE_MENU_ROUTE_OK' "$TMP/menu.out"
grep -q 'fixture; no modifica el runtime real' "$TMP/menu.out"

profiles_apply_live_menu() { printf 'LIVE_MENU_ROUTE_OK\n'; }
printf '3\n12\n0\n' | menu_config_profiles_backups >"$TMP/live-menu.out"
grep -q 'LIVE_MENU_ROUTE_OK' "$TMP/live-menu.out"
grep -q 'Aplicar revisión e iniciar Xray REAL' "$TMP/live-menu.out"
source "$ROOT/modules/profiles.sh"
# La opción live exige revisión válida y dos confirmaciones antes de invocar el puente.
profiles_select_id() { printf 'profile-%032d\n' 1; }
profiles_cli() { printf '[{"revision":"r000001","validation":"valid"}]\n'; }
ui_confirm() { local prompt="$1" answer; read -r answer; [[ "$answer" == [sS] || "$answer" == [sS][iI] ]]; }
python3() { printf '%s\n' "$*" >>"$TMP/live-call.log"; printf '{"status":"SERVICE_ACTIVE_CORRELATED","operation_id":"runtime-op-%032d","generation_id":"generation-%032d","profile_id":"profile-%032d","revision":"r000001","runtime_published":true,"service_started":true,"configuration_loaded":false,"completed":false,"journal_state":"service_observed_active","evidence":{}}\n' 2 3 1; }
: >"$TMP/live-call.log"
printf '1\nn\n' | profiles_apply_live_menu >"$TMP/live-cancel.out"
[[ ! -s "$TMP/live-call.log" ]]
grep -q 'Operación cancelada' "$TMP/live-cancel.out"
printf '1\ns\ns\n' | profiles_apply_live_menu >"$TMP/live-run.out"
grep -q -- '--confirm-live' "$TMP/live-call.log"
[[ "$(wc -l <"$TMP/live-call.log")" -eq 1 ]]
grep -q 'SERVICE_ACTIVE_CORRELATED' "$TMP/live-run.out"
grep -q 'configuration_loaded permanece false' "$TMP/live-run.out"
echo 'PASS: menú mantiene fixture separado; live exige revisión válida y doble confirmación.'
