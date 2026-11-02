#!/usr/bin/env bash
# Pruebas aisladas del encabezado; no consultan servicios ni red reales.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
source "$ROOT/config/manager.conf"
source "$ROOT/config/preferences.sh"
source "$ROOT/lib/system.sh"
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
XRAY_MANAGER_PROFILES_DIR="$tmp/no-profiles"
XRAY_ADMIN_BIN="$tmp/no-xray"

mock_bin="$tmp/bin"
mkdir -p "$mock_bin"
cat >"$mock_bin/curl" <<'CURL'
#!/usr/bin/env bash
if [[ "${MOCK_CURL_SUCCESS:-0}" == 1 ]]; then
  printf '203.0.113.10'
  exit 0
fi
exit 22
CURL
cat >"$mock_bin/systemctl" <<'SYSTEMCTL'
#!/usr/bin/env bash
case "${1:-}" in
  cat) [[ "${MOCK_SYSTEMD_CONFIGURED:-0}" == 1 ]] ;;
  is-active) [[ "${MOCK_SYSTEMD_ACTIVE:-0}" == 1 ]] ;;
  is-failed) exit 1 ;;
  is-enabled)
    if [[ "${MOCK_SYSTEMD_ENABLED:-0}" == 1 ]]; then printf 'enabled\n'; else printf 'disabled\n'; exit 1; fi
    ;;
  *) exit 1 ;;
esac
SYSTEMCTL
chmod 700 "$mock_bin/curl" "$mock_bin/systemctl"
old_path="$PATH"
PATH="$mock_bin:/usr/bin:/bin"
export PATH
PUBLIC_IP_TIMEOUT=1

[[ "$(system_public_ip)" == 'No disponible' ]]
MOCK_CURL_SUCCESS=1
export MOCK_CURL_SUCCESS
[[ "$(system_public_ip)" == '203.0.113.10' ]]
unset MOCK_CURL_SUCCESS
[[ "$(system_xray_version)" == 'No instalado' ]]
[[ "$(system_xray_service_state)" == 'No instalado' ]]
[[ "$(system_xray_autostart)" == 'No configurado' ]]
[[ "$(system_active_profile)" == 'Ninguno' ]]

# M04: una unidad instalada pero deshabilitada debe indicarse explícitamente.
MOCK_SYSTEMD_CONFIGURED=1 MOCK_SYSTEMD_ACTIVE=0 MOCK_SYSTEMD_ENABLED=0
export MOCK_SYSTEMD_CONFIGURED MOCK_SYSTEMD_ACTIVE MOCK_SYSTEMD_ENABLED
[[ "$(system_xray_autostart)" == 'Deshabilitado' ]]
MOCK_SYSTEMD_CONFIGURED=0
export MOCK_SYSTEMD_CONFIGURED

output="$tmp/header.out"
system_show_header >"$output"
for expected in \
	'IP pública:        No disponible' \
	'Xray-core:         No instalado' \
	'Estado:            No instalado' \
	'Servicio:          No configurado' \
	'Perfil activo:     Ninguno' \
	'Fecha:' 'Hora:'; do
	grep -Fq "$expected" "$output"
done

# Con binario presente pero unidad ausente, el encabezado conserva un estado legible.
cat >"$tmp/xray" <<'XRAY'
#!/usr/bin/env bash
printf 'Xray 26.10.31 test\n'
XRAY
chmod 700 "$tmp/xray"
XRAY_ADMIN_BIN="$tmp/xray"
[[ "$(system_xray_version)" == 'Xray 26.10.31 test' ]]
[[ "$(system_xray_service_state)" == 'Instalado / servicio no configurado' ]]
[[ "$(system_xray_autostart)" == 'No configurado' ]]
mkdir -p "$XRAY_MANAGER_PROFILES_DIR/active"
printf 'perfil-pruebas\n' >"$XRAY_MANAGER_PROFILES_DIR/active/active-profile"
MOCK_SYSTEMD_CONFIGURED=1 MOCK_SYSTEMD_ACTIVE=1 MOCK_SYSTEMD_ENABLED=1
export MOCK_SYSTEMD_CONFIGURED MOCK_SYSTEMD_ACTIVE MOCK_SYSTEMD_ENABLED
[[ "$(system_xray_service_state)" == 'Activo' ]]
[[ "$(system_xray_autostart)" == 'Habilitado' ]]
[[ "$(system_active_profile)" == 'perfil-pruebas' ]]

# M06: cada proveedor puede fallar independientemente sin ocultar el resto del encabezado.
(
	system_public_ip() { return 1; }
	out="$(system_show_header)"
	grep -Fq 'IP pública:        No disponible' <<<"$out"
	grep -Fq 'Xray-core:         Xray 26.10.31 test' <<<"$out"
	grep -Fq 'Perfil activo:     perfil-pruebas' <<<"$out"
)
(
	system_xray_version() { return 1; }
	out="$(system_show_header)"
	grep -Fq 'Xray-core:         No disponible' <<<"$out"
	grep -Fq 'IP pública:        No disponible' <<<"$out"
	grep -Fq 'Estado:' <<<"$out"
)
(
	system_xray_service_state() { return 1; }
	out="$(system_show_header)"
	grep -Fq 'Estado:            No disponible' <<<"$out"
	grep -Fq 'Servicio:          Habilitado' <<<"$out"
)
(
	system_xray_autostart() { return 1; }
	out="$(system_show_header)"
	grep -Fq 'Servicio:          No disponible' <<<"$out"
	grep -Fq 'Estado:            Activo' <<<"$out"
)
(
	system_active_profile() { return 1; }
	out="$(system_show_header)"
	grep -Fq 'Perfil activo:     No disponible' <<<"$out"
	grep -Fq 'Xray-core:         Xray 26.10.31 test' <<<"$out"
)
(
	date() { return 1; }
	out="$(system_show_header)"
	grep -Fq 'Fecha:             No disponible' <<<"$out"
	grep -Fq 'Hora:              No disponible' <<<"$out"
	grep -Fq 'IP pública:' <<<"$out"
)
PATH="$old_path"
printf 'OK: M04 diferencia autostart habilitado/deshabilitado y M06 aísla fallos de IP, versión, servicio, autostart, perfil y fecha/hora.\n'
