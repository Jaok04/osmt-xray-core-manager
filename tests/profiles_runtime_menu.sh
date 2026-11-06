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
grep -q 'integración fixture; live no autorizado' "$TMP/menu.out"
echo 'PASS: menú enruta a aplicación fixture y permanece bloqueado en modo normal.'
