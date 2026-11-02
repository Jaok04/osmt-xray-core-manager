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
printf '3\n1\n1\n0\n0\n0\n' | connections_menu >/dev/null
grep -Fxq 'trojan_tcp_tls' "$CALLS"
: >"$CALLS"
printf '4\n4\n2\n1\n0\n0\n0\n0\n' | connections_menu >/dev/null
grep -Fxq 'shadowsocks_obfs_tls' "$CALLS"
: >"$CALLS"
printf '6\n3\n1\n0\n0\n0\n' | connections_menu >/dev/null
grep -Fxq 'wireguard_udp' "$CALLS"
printf 'OK: navegación de familias, modalidades, seguridad seleccionable y protocolos opcionales.\n'