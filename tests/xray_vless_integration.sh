#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
XRAY="${XRAY_BIN:-/var/cache/xray-manager/validation/v26.10.31/xray}"
[[ -x "$XRAY" ]] || {
    printf 'No se encuentra el binario Xray de validación: %s\n' "$XRAY" >&2
    exit 1
}
source "$ROOT/modules/vless_model.sh"
source "$ROOT/modules/vless_xray_26_10_31.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
openssl req -x509 -newkey rsa:2048 -nodes -keyout "$TMP/tls.key" -out "$TMP/tls.crt" -days 1 -subj '/CN=localhost' -addext 'subjectAltName=DNS:localhost' >/dev/null 2>&1
KEY_OUTPUT="$("$XRAY" x25519)"
REALITY_KEY="$(sed -n 's/^PrivateKey: //p' <<<"$KEY_OUTPUT")"
[[ -n "$REALITY_KEY" ]] || {
    echo 'No se pudo generar la clave efímera de prueba REALITY.' >&2
    exit 1
}

validate_mode() {
    local mode="$1" opts="$2" model config
    model="$TMP/$mode.model.json"
    config="$TMP/$mode.xray.json"
    vless_model_build "test-$mode" "$mode" 127.0.0.1 62001 >"$model"
    vless_xray_26_10_31_build "$model" "$opts" >"$config"
    "$XRAY" run -test -config "$config"
    printf 'OK: %s\n' "$mode"
}
printf '{"path":"/test-ws"}\n' >"$TMP/ws.json"
printf '{"certificate_file":"%s","key_file":"%s"}\n' "$TMP/tls.crt" "$TMP/tls.key" >"$TMP/tls.json"
printf '{"certificate_file":"%s","key_file":"%s","service_name":"test-grpc"}\n' "$TMP/tls.crt" "$TMP/tls.key" >"$TMP/grpc-tls.json"
printf '{"private_key":"%s","server_names":["example.com"],"short_ids":["0123456789abcdef"],"target":"localhost:443"}\n' "$REALITY_KEY" >"$TMP/reality.json"
printf '{"private_key":"%s","server_names":["example.com"],"service_name":"test-grpc","short_ids":["0123456789abcdef"],"target":"localhost:443"}\n' "$REALITY_KEY" >"$TMP/grpc-reality.json"
printf '{}\n' >"$TMP/none.json"
validate_mode vless_ws "$TMP/ws.json"
validate_mode vless_tcp_tls "$TMP/tls.json"
validate_mode vless_ws_tls "$TMP/tls.json"
validate_mode vless_reality "$TMP/reality.json"
validate_mode vless_grpc_tls "$TMP/grpc-tls.json"
validate_mode vless_grpc_reality "$TMP/grpc-reality.json"
# El adaptador debe rechazar opciones faltantes y opciones desconocidas.
if vless_xray_26_10_31_build "$TMP/vless_ws.model.json" "$TMP/none.json" >/dev/null 2>&1; then
    echo 'ERROR: se aceptaron opciones WebSocket incompletas.' >&2
    exit 1
fi
echo 'OK: rechazo de opciones incompletas.'