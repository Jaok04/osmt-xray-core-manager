#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
XRAY="${XRAY_BIN:-/var/cache/xray-manager/validation/v26.10.31/xray}"
[[ -x "$XRAY" ]] || {
    echo "No existe Xray de validación: $XRAY" >&2
    exit 1
}
source "$ROOT/modules/vmess_model.sh"
source "$ROOT/modules/vmess_xray_26_10_31.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
openssl req -x509 -newkey rsa:2048 -nodes -keyout "$TMP/tls.key" -out "$TMP/tls.crt" -days 1 -subj '/CN=localhost' >/dev/null 2>&1
chmod 600 "$TMP/tls.key"
REALITY_KEY="$("$XRAY" x25519 | sed -n 's/^PrivateKey: //p')"
printf '%s\n' '[{"id":"11111111-1111-4111-8111-111111111111","level":0,"email":"vmess-test@example.test"}]' >"$TMP/users.json"
validate() {
    local mode="$1" options="$2"
    vmess_model_build "test-$mode" "$mode" 127.0.0.1 62001 "$TMP/users.json" >"$TMP/model.json"
    vmess_xray_26_10_31_build "$TMP/model.json" "$options" >"$TMP/config.json"
    "$XRAY" run -test -config "$TMP/config.json" >/dev/null
    printf 'PASS %s\n' "$mode"
}
jq -n '{path:"/ws",host:""}' >"$TMP/ws.json"
jq -n --arg certificate_file "$TMP/tls.crt" --arg key_file "$TMP/tls.key" '{path:"/ws",host:"",certificate_file:$certificate_file,key_file:$key_file}' >"$TMP/ws-tls.json"
jq -n --arg certificate_file "$TMP/tls.crt" --arg key_file "$TMP/tls.key" '{certificate_file:$certificate_file,key_file:$key_file}' >"$TMP/tcp-tls.json"
jq -n --arg target "localhost:443" --arg private_key "$REALITY_KEY" '{target:$target,private_key:$private_key,server_names:["example.com"],short_ids:["0123456789abcdef"]}' >"$TMP/reality.json"
jq -n '{service_name:"svc"}' >"$TMP/grpc.json"
jq -n --arg certificate_file "$TMP/tls.crt" --arg key_file "$TMP/tls.key" '{service_name:"svc",certificate_file:$certificate_file,key_file:$key_file}' >"$TMP/grpc-tls.json"
jq -n --arg target "localhost:443" --arg private_key "$REALITY_KEY" '{service_name:"svc",target:$target,private_key:$private_key,server_names:["example.com"],short_ids:["0123456789abcdef"]}' >"$TMP/grpc-reality.json"
jq -n '{path:"/upgrade",host:""}' >"$TMP/httpupgrade.json"
jq -n --arg certificate_file "$TMP/tls.crt" --arg key_file "$TMP/tls.key" '{path:"/upgrade",host:"",certificate_file:$certificate_file,key_file:$key_file}' >"$TMP/httpupgrade-tls.json"
jq -n '{path:"/xhttp",mode:"auto"}' >"$TMP/xhttp.json"
jq -n --arg certificate_file "$TMP/tls.crt" --arg key_file "$TMP/tls.key" '{path:"/xhttp",mode:"auto",certificate_file:$certificate_file,key_file:$key_file}' >"$TMP/xhttp-tls.json"
jq -n --arg target "localhost:443" --arg private_key "$REALITY_KEY" '{path:"/xhttp",mode:"auto",target:$target,private_key:$private_key,server_names:["example.com"],short_ids:["0123456789abcdef"]}' >"$TMP/xhttp-reality.json"
jq -n '{header_type:"none",seed:""}' >"$TMP/mkcp.json"
jq -n --arg certificate_file "$TMP/tls.crt" --arg key_file "$TMP/tls.key" '{header_type:"none",seed:"",certificate_file:$certificate_file,key_file:$key_file}' >"$TMP/mkcp-tls.json"
validate vmess_ws "$TMP/ws.json"
validate vmess_tcp_tls "$TMP/tcp-tls.json"
validate vmess_ws_tls "$TMP/ws-tls.json"
validate vmess_reality "$TMP/reality.json"
validate vmess_grpc "$TMP/grpc.json"
validate vmess_grpc_tls "$TMP/grpc-tls.json"
validate vmess_grpc_reality "$TMP/grpc-reality.json"
validate vmess_httpupgrade "$TMP/httpupgrade.json"
validate vmess_httpupgrade_tls "$TMP/httpupgrade-tls.json"
validate vmess_xhttp "$TMP/xhttp.json"
validate vmess_xhttp_tls "$TMP/xhttp-tls.json"
validate vmess_xhttp_reality "$TMP/xhttp-reality.json"
validate vmess_mkcp "$TMP/mkcp.json"
validate vmess_mkcp_tls "$TMP/mkcp-tls.json"
echo 'OK: Xray-core 26.10.31 validó las 14 combinaciones, incluida HTTPUpgrade-TLS.'