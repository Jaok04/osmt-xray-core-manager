#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/modules/vmess_model.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
printf '%s\n' '[{"id":"11111111-1111-4111-8111-111111111111","level":0,"email":"one@example.test"}]' >"$TMP/users.json"
while IFS='|' read -r mode transport security; do
    vmess_model_build conn-test "$mode" 127.0.0.1 443 "$TMP/users.json" >"$TMP/model.json"
    jq -e --arg mode "$mode" --arg transport "$transport" --arg security "$security" '.protocol=="vmess" and .mode_id==$mode and .transport==$transport and .security==$security and .listen_port==443 and (.users|length)==1' "$TMP/model.json" >/dev/null
done <<'MODES'
vmess_ws|websocket|none
vmess_tcp_tls|raw|tls
vmess_ws_tls|websocket|tls
vmess_reality|raw|reality
vmess_grpc|grpc|none
vmess_grpc_tls|grpc|tls
vmess_grpc_reality|grpc|reality
vmess_httpupgrade|httpupgrade|none
vmess_httpupgrade_tls|httpupgrade|tls
vmess_xhttp|xhttp|none
vmess_xhttp_tls|xhttp|tls
vmess_xhttp_reality|xhttp|reality
vmess_mkcp|mkcp|none
vmess_mkcp_tls|mkcp|tls
MODES
for invalid in vmess_ws_reality vless_ws '' unknown; do
    if vmess_model_build conn-test "$invalid" 127.0.0.1 443 "$TMP/users.json" >/dev/null 2>&1; then exit 1; fi
done
for port in 0 65536 abc; do
    if vmess_model_build conn-test vmess_ws 127.0.0.1 "$port" "$TMP/users.json" >/dev/null 2>&1; then exit 1; fi
done
printf '%s\n' '[{"id":"11111111-1111-4111-8111-111111111111","level":0,"email":"a"},{"id":"11111111-1111-4111-8111-111111111111","level":0,"email":"b"}]' >"$TMP/duplicate.json"
if vmess_model_build conn-test vmess_ws 127.0.0.1 443 "$TMP/duplicate.json" >/dev/null 2>&1; then exit 1; fi
echo 'OK: modelo VMess valida las 14 modalidades y rechaza UUID/puertos/modalidades inválidos.'