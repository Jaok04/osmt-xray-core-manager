#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_ROOT="$ROOT"
export APP_ROOT
source "$ROOT/lib/ui.sh"
source "$ROOT/modules/connections.sh"
ui_clear() { :; }
ui_title() { printf '%s\n' "$1"; }
ui_pause() { :; }
CALLS="$(mktemp)"
trap 'rm -f "$CALLS"' EXIT
connections_create_draft() {
    printf '%s\n' "$1" >>"$CALLS"
    return 1
}
connections_manage_existing() { printf 'EXISTING:%s\n' "$1" >>"$CALLS"; }
printf '1\n1\n1\n0\n0\n0\n' | connections_menu >/dev/null
grep -Fxq 'vless_ws' "$CALLS"
: >"$CALLS"
printf '1\n6\n1\n1\n0\n0\n0\n' | connections_menu >/dev/null
grep -Fxq 'vless_xhttp' "$CALLS"
: >"$CALLS"
printf '1\n5\n2\n1\n0\n0\n0\n' | connections_menu >/dev/null
grep -Fxq 'vless_grpc_reality' "$CALLS"
: >"$CALLS"
printf '2\n5\n2\n1\n0\n0\n0\n' | connections_menu >/dev/null
grep -Fxq 'vmess_grpc_tls' "$CALLS"
: >"$CALLS"
printf '2\n6\n2\n1\n0\n0\n0\n' | connections_menu >/dev/null
grep -Fxq 'vmess_httpupgrade_tls' "$CALLS"
: >"$CALLS"
printf '2\n6\n1\n1\n0\n0\n0\n' | connections_menu >/dev/null
grep -Fxq 'vmess_httpupgrade' "$CALLS"
: >"$CALLS"
printf '3\n1\n1\n0\n0\n0\n' | connections_menu >/dev/null
grep -Fxq 'trojan_tcp_tls' "$CALLS"
: >"$CALLS"
printf '4\n4\n2\n1\n0\n0\n0\n0\n' | connections_menu >/dev/null
grep -Fxq 'shadowsocks_obfs_tls' "$CALLS"
: >"$CALLS"
printf '6\n3\n1\n0\n0\n0\n' | connections_menu >/dev/null
grep -Fxq 'wireguard_udp' "$CALLS"
# Recorrer individualmente las 14 combinaciones VMess y sus selectores de seguridad.
run_vmess_case() {
    local menu_key="$1" security="$2" expected="$3"
    : >"$CALLS"
    if [[ "$security" == '-' ]]; then
        printf '2\n%s\n1\n0\n0\n0\n' "$menu_key" | connections_menu >/dev/null
    else
        printf '2\n%s\n%s\n1\n0\n0\n0\n' "$menu_key" "$security" | connections_menu >/dev/null
    fi
    if ! grep -Fxq "$expected" "$CALLS"; then
        printf 'ERROR: navegación VMess no resolvió %s (opción %s, seguridad %s).\n' "$expected" "$menu_key" "$security" >&2
        exit 1
    fi
    printf 'PASS navegación %s\n' "$expected"
}
run_vmess_case 1 - vmess_ws
run_vmess_case 2 - vmess_tcp_tls
run_vmess_case 3 - vmess_ws_tls
run_vmess_case 4 - vmess_reality
run_vmess_case 5 1 vmess_grpc
run_vmess_case 5 2 vmess_grpc_tls
run_vmess_case 5 3 vmess_grpc_reality
run_vmess_case 6 1 vmess_httpupgrade
run_vmess_case 6 2 vmess_httpupgrade_tls
run_vmess_case 7 1 vmess_xhttp
run_vmess_case 7 2 vmess_xhttp_tls
run_vmess_case 7 3 vmess_xhttp_reality
run_vmess_case 8 1 vmess_mkcp
run_vmess_case 8 2 vmess_mkcp_tls
printf 'OK: navegación de las 14 combinaciones VMess, familias, modalidades, seguridad seleccionable y protocolos opcionales.\n'
