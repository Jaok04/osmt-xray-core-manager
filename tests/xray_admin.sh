#!/usr/bin/env bash
# shellcheck disable=SC2218
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_ROOT="$ROOT"
# shellcheck disable=SC1091
source "$ROOT/config/manager.conf"
# shellcheck disable=SC1091
source "$ROOT/config/xray-version.conf"
# shellcheck disable=SC1091
source "$ROOT/modules/xray_admin.sh"
run_lock_mode="$(stat -c %a /run/lock 2>/dev/null || printf unavailable)"

mapfile -t versions < <(xray_admin_compatible_versions)
[[ "${#versions[@]}" -eq 1 ]]
[[ "${versions[0]}" == '26.10.31' ]]
[[ "$(xray_admin_release_asset_name)" == 'Xray-linux-64.zip' ]]
if xray_admin_install_version '26.9.9' install >/dev/null 2>&1; then
	echo 'ERROR: se permitió una versión sin adaptador validado.' >&2
	exit 1
fi
printf '%s\n' 'OK: catálogo de versiones compatibles, arquitectura Linux amd64 y rechazo de versiones sin adaptador.'

ui_clear() { :; }
ui_title() { :; }
ui_pause() { :; }
ui_read_option() { printf -v "$2" '%s' 1; }
ui_confirm() { return 1; }
FETCH_COUNT=0
cancel_output="$(mktemp)"
xray_admin_install_menu_action install >"$cancel_output" 2>&1
grep -q 'Operación cancelada' "$cancel_output"
[[ "$FETCH_COUNT" -eq 0 ]]
rm -f -- "$cancel_output"

# Una falla de instalación debe conservar su código y mostrarse después de la confirmación.
original_install_function="$(declare -f xray_admin_install_version)"
xray_admin_install_version() { return 37; }
ui_confirm() { return 0; }
menu_failure_output="$(mktemp)"
if xray_admin_install_menu_action install >"$menu_failure_output" 2>&1; then
	printf 'ERROR: el menú ocultó una falla simulada de instalación.\n' >&2
	exit 1
else
	menu_failure_rc=$?
fi
[[ "$menu_failure_rc" -eq 37 ]]
grep -Fq 'falló (código 37)' "$menu_failure_output"
grep -Fq 'no se considera instalada' "$menu_failure_output"
rm -f -- "$menu_failure_output"
eval "$original_install_function"
ui_confirm() { return 1; }

# Integración de instalación/rollback con fixtures: nunca usa las rutas reales.
tmp="$(mktemp -d)"
XRAY_MANAGER_LIFECYCLE_LOCK="$tmp/lifecycle.lock"
export XRAY_MANAGER_LIFECYCLE_LOCK
trap 'rm -rf -- "$tmp"' EXIT
XRAY_ADMIN_BIN="$tmp/bin/xray"
XRAY_ADMIN_DATA="$tmp/share"
XRAY_ADMIN_CACHE="$tmp/cache"
XRAY_ADMIN_BACKUPS="$tmp/backups"
XRAY_ADMIN_MANIFEST="$tmp/state/xray-install.json"
mkdir -p "$tmp/state"
chmod 700 "$tmp/state"
XRAY_ADMIN_LOCK="$tmp/xray-admin.lock"
FETCH_COUNT=0
FETCH_FAIL=0
XRAY_ADMIN_TEST_OMIT_GEOSITE=0

# La extracción solo acepta el paquete raíz esperado y rechaza traversal.
mkdir -p "$tmp/valid-work" "$tmp/valid-stage" "$tmp/bad-work" "$tmp/bad-stage"
python3 - "$tmp/valid-work/Xray-linux-64.zip" "$tmp/bad-work/Xray-linux-64.zip" <<'PYZIP'
import sys, zipfile
valid, bad = sys.argv[1:]
script = b"#!/bin/sh\nprintf 'Xray 26.10.31 fixture\n'\n"
with zipfile.ZipFile(valid, 'w', compression=zipfile.ZIP_DEFLATED) as z:
    z.writestr('xray', script)
    z.writestr('geoip.dat', b'geoip')
    z.writestr('geosite.dat', b'geosite')
with zipfile.ZipFile(bad, 'w', compression=zipfile.ZIP_DEFLATED) as z:
    z.writestr('xray', script)
    z.writestr('geoip.dat', b'geoip')
    z.writestr('geosite.dat', b'geosite')
    z.writestr('../escape.txt', b'not allowed')
PYZIP
xray_admin_extract_stage 26.10.31 "$tmp/valid-work" "$tmp/valid-stage" >/dev/null
[[ -x "$tmp/valid-stage/xray" ]]
[[ "$(cat "$tmp/valid-stage/geoip.dat")" == geoip ]]
if xray_admin_extract_stage 26.10.31 "$tmp/bad-work" "$tmp/bad-stage" >/dev/null 2>&1; then
	printf 'ERROR: se aceptó una ruta traversal en el ZIP.\n' >&2
	exit 1
fi
[[ ! -e "$tmp/escape.txt" ]]

xray_admin_require_tools() { :; }
xray_admin_fetch_verified_release() {
	((FETCH_COUNT += 1))
	((FETCH_FAIL == 0)) || return 1
	printf '%064d\n' 1 >"$2/package.sha256"
}
xray_admin_extract_stage() {
	local version="$1" stage="$3"
	mkdir -p "$stage"
	cat >"$stage/xray" <<'BIN'
#!/usr/bin/env bash
printf 'Xray 26.10.31 fixture\n'
BIN
	chmod 700 "$stage/xray"
	printf 'geoip-fixture\n' >"$stage/geoip.dat"
	if [[ "$XRAY_ADMIN_TEST_OMIT_GEOSITE" == 0 ]]; then
		printf 'geosite-fixture\n' >"$stage/geosite.dat"
	fi
}

xray_admin_install_version 26.10.31 install >"$tmp/install.out"
[[ -x "$XRAY_ADMIN_BIN" ]]
[[ "$(cat "$XRAY_ADMIN_DATA/geoip.dat")" == geoip-fixture ]]
[[ "$(cat "$XRAY_ADMIN_DATA/geosite.dat")" == geosite-fixture ]]
[[ -z "${XRAY_ADMIN_LOCK_FD:-}" ]]

# Actualizar a la misma versión es no-op y también libera el lock.
fetch_before="$FETCH_COUNT"
xray_admin_install_version 26.10.31 update >"$tmp/noop.out"
[[ "$FETCH_COUNT" == "$fetch_before" ]]
[[ -z "${XRAY_ADMIN_LOCK_FD:-}" ]]

[[ -f "$XRAY_ADMIN_MANIFEST" ]]
[[ "$(stat -c '%a' "$XRAY_ADMIN_MANIFEST")" == 600 ]]
xray_admin_verify_installation >/dev/null

# Una alteración de geodata bloquea el update antes de descargar o sobrescribir.
printf 'tampered\n' >"$XRAY_ADMIN_DATA/geoip.dat"
fetch_before="$FETCH_COUNT"
if xray_admin_install_version 26.10.31 update >"$tmp/tampered-update.out" 2>&1; then
	printf 'ERROR: se aceptó una instalación con geodata alterado.\n' >&2
	exit 1
fi
[[ "$FETCH_COUNT" == "$fetch_before" ]]
grep -q 'no está verificada' "$tmp/tampered-update.out"
xray_admin_install_version 26.10.31 repair >"$tmp/repair.out"
xray_admin_verify_installation >/dev/null

# La alteración del binario, incluso conservando su salida de versión, bloquea update.
printf '# tamper\\n' >>"$XRAY_ADMIN_BIN"
fetch_before="$FETCH_COUNT"
if xray_admin_install_version 26.10.31 update >"$tmp/tampered-binary.out" 2>&1; then
	printf 'ERROR: se aceptó un binario alterado.\\n' >&2
	exit 1
fi
[[ "$FETCH_COUNT" == "$fetch_before" ]]
grep -q 'no está verificada' "$tmp/tampered-binary.out"
xray_admin_install_version 26.10.31 repair >"$tmp/binary-repair.out"
xray_admin_verify_installation >/dev/null

# Un manifiesto con permisos alterados bloquea update, pero repair puede sustituirlo.
chmod 644 "$XRAY_ADMIN_MANIFEST"
fetch_before="$FETCH_COUNT"
if xray_admin_install_version 26.10.31 update >"$tmp/manifest-mode-update.out" 2>&1; then
	printf 'ERROR: se aceptó un manifiesto con permisos abiertos.\\n' >&2
	exit 1
fi
[[ "$FETCH_COUNT" == "$fetch_before" ]]
xray_admin_install_version 26.10.31 repair >"$tmp/manifest-mode-repair.out"
[[ "$(stat -c '%a' "$XRAY_ADMIN_MANIFEST")" == 600 ]]
xray_admin_verify_installation >/dev/null

# Una instalación heredada sin manifiesto queda como no verificada.
mv "$XRAY_ADMIN_MANIFEST" "$XRAY_ADMIN_MANIFEST.saved"
if xray_admin_install_version 26.10.31 update >"$tmp/legacy-update.out" 2>&1; then
	printf 'ERROR: se aceptó una instalación sin manifiesto.\n' >&2
	exit 1
fi
[[ ! -e "$XRAY_ADMIN_MANIFEST" ]]
xray_admin_install_version 26.10.31 repair >"$tmp/legacy-repair.out"
xray_admin_verify_installation >/dev/null

# Los artefactos huérfanos bloquean install y no se sobrescriben.
saved_bin="$XRAY_ADMIN_BIN"
saved_data="$XRAY_ADMIN_DATA"
saved_manifest="$XRAY_ADMIN_MANIFEST"
mkdir -p "$tmp/orphan/bin" "$tmp/orphan/share" "$tmp/orphan/state"
chmod 700 "$tmp/orphan/state"
cp -a "$XRAY_ADMIN_MANIFEST" "$tmp/orphan/state/xray-install.json"
printf 'orphan-geoip\n' >"$tmp/orphan/share/geoip.dat"
chmod 644 "$tmp/orphan/share/geoip.dat"
XRAY_ADMIN_BIN="$tmp/orphan/bin/xray"
XRAY_ADMIN_DATA="$tmp/orphan/share"
XRAY_ADMIN_MANIFEST="$tmp/orphan/state/xray-install.json"
fetch_before="$FETCH_COUNT"
if xray_admin_install_version 26.10.31 install >"$tmp/orphan-install.out" 2>&1; then
	printf 'ERROR: install sobrescribió artefactos huérfanos.\\n' >&2
	exit 1
fi
[[ "$FETCH_COUNT" == "$fetch_before" ]]
[[ "$(cat "$XRAY_ADMIN_DATA/geoip.dat")" == orphan-geoip ]]
XRAY_ADMIN_BIN="$saved_bin"
XRAY_ADMIN_DATA="$saved_data"
XRAY_ADMIN_MANIFEST="$saved_manifest"

exec {busy_fd}>"$XRAY_MANAGER_LIFECYCLE_LOCK"
flock -x "$busy_fd"
if xray_admin_install_version 26.10.31 reinstall >"$tmp/lifecycle-busy.out" 2>&1; then
	printf 'ERROR: administración Xray ignoró el bloqueo de ciclo de vida.\n' >&2
	exit 1
fi
grep -q 'otra operación de ciclo de vida' "$tmp/lifecycle-busy.out"
[[ -x "$XRAY_ADMIN_BIN" ]]
flock -u "$busy_fd"
exec {busy_fd}>&-

# Un fallo antes de iniciar el commit no puede borrar la instalación existente.
cat >"$XRAY_ADMIN_BIN" <<'OLD'
#!/usr/bin/env bash
printf 'Xray 26.10.30 fixture\n'
OLD
chmod 755 "$XRAY_ADMIN_BIN"
printf 'old-geoip\n' >"$XRAY_ADMIN_DATA/geoip.dat"
printf 'old-geosite\n' >"$XRAY_ADMIN_DATA/geosite.dat"
chmod 755 "$XRAY_ADMIN_BIN"
chmod 644 "$XRAY_ADMIN_DATA/geoip.dat" "$XRAY_ADMIN_DATA/geosite.dat"
xray_admin_record_installation 26.10.30 "$(printf '%064d' 2)" >/dev/null
xray_admin_verify_installation >/dev/null
FETCH_FAIL=1
if xray_admin_install_version 26.10.31 repair >"$tmp/fetch-failure.out" 2>&1; then
	printf 'ERROR: se informó éxito pese al fallo de descarga.\n' >&2
	exit 1
fi
[[ "$("$XRAY_ADMIN_BIN" version)" == 'Xray 26.10.30 fixture' ]]
[[ "$(cat "$XRAY_ADMIN_DATA/geoip.dat")" == old-geoip ]]
[[ "$(cat "$XRAY_ADMIN_DATA/geosite.dat")" == old-geosite ]]
[[ -z "${XRAY_ADMIN_LOCK_FD:-}" ]]

# Un fallo después de comenzar el commit debe restaurar binario y ambos geodata.
FETCH_FAIL=0
XRAY_ADMIN_TEST_OMIT_GEOSITE=1
if xray_admin_install_version 26.10.31 update >"$tmp/rollback.out" 2>&1; then
	printf 'ERROR: se informó éxito con un paquete incompleto.\n' >&2
	exit 1
fi
[[ "$("$XRAY_ADMIN_BIN" version)" == 'Xray 26.10.30 fixture' ]]
[[ "$(cat "$XRAY_ADMIN_DATA/geoip.dat")" == old-geoip ]]
[[ "$(cat "$XRAY_ADMIN_DATA/geosite.dat")" == old-geosite ]]
[[ -z "${XRAY_ADMIN_LOCK_FD:-}" ]]
grep -q 'Rollback de binario/geodata completado' "$tmp/rollback.out"
xray_admin_verify_installation >/dev/null

printf 'OK: instalación aislada, no-op, liberación del lock, preservación ante fallo de descarga y rollback ante paquete incompleto.\n'
[[ "$(stat -c %a /run/lock 2>/dev/null || printf unavailable)" == "$run_lock_mode" ]]
