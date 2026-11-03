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
expect_adapter_reject() {
    local label="$1" mode="$2" options="$3"
    vmess_model_build "negative-$label" "$mode" 127.0.0.1 62002 "$TMP/users.json" >"$TMP/negative-model.json"
    if vmess_xray_26_10_31_build "$TMP/negative-model.json" "$options" >"$TMP/negative-config.json" 2>/dev/null; then
        printf 'ERROR: el adaptador aceptó un caso inválido: %s\n' "$label" >&2
        exit 1
    fi
    printf 'PASS rechazo %s\n' "$label"
}

# TLS debe rechazar material incompleto, enlaces simbólicos y certificados ilegibles.
jq -n --arg certificate_file "$TMP/tls.crt" '{certificate_file:$certificate_file}' >"$TMP/tls-missing-key.json"
expect_adapter_reject tls_missing_key vmess_tcp_tls "$TMP/tls-missing-key.json"
ln -s "$TMP/tls.key" "$TMP/tls-key-link"
jq -n --arg certificate_file "$TMP/tls.crt" --arg key_file "$TMP/tls-key-link" '{certificate_file:$certificate_file,key_file:$key_file}' >"$TMP/tls-symlink.json"
expect_adapter_reject tls_symlink_key vmess_tcp_tls "$TMP/tls-symlink.json"
printf 'not-a-certificate\n' >"$TMP/invalid.crt"
jq -n --arg certificate_file "$TMP/invalid.crt" --arg key_file "$TMP/tls.key" '{certificate_file:$certificate_file,key_file:$key_file}' >"$TMP/tls-invalid-cert.json"
vmess_model_build negative_tls_cert vmess_tcp_tls 127.0.0.1 62002 "$TMP/users.json" >"$TMP/negative-model.json"
if vmess_xray_26_10_31_build "$TMP/negative-model.json" "$TMP/tls-invalid-cert.json" >"$TMP/negative-config.json" 2>/dev/null; then
    echo 'ERROR: el adaptador aceptó un certificado TLS inválido.' >&2
    exit 1
fi
echo 'PASS rechazo certificado TLS inválido por el adaptador'
openssl req -x509 -newkey rsa:2048 -nodes -keyout "$TMP/other.key" -out "$TMP/other.crt" -days 1 -subj '/CN=other' >/dev/null 2>&1
jq -n --arg certificate_file "$TMP/tls.crt" --arg key_file "$TMP/other.key" '{certificate_file:$certificate_file,key_file:$key_file}' >"$TMP/tls-mismatched-pair.json"
expect_adapter_reject tls_certificate_key_mismatch vmess_tcp_tls "$TMP/tls-mismatched-pair.json"

# Private TLS keys must be root:root 0600, with no group/other access.
for unsafe_mode in 644 640 400; do
    chmod "$unsafe_mode" "$TMP/tls.key"
    jq -n --arg certificate_file "$TMP/tls.crt" --arg key_file "$TMP/tls.key" '{certificate_file:$certificate_file,key_file:$key_file}' >"$TMP/tls-unsafe-mode.json"
    expect_adapter_reject "tls_key_mode_$unsafe_mode" vmess_tcp_tls "$TMP/tls-unsafe-mode.json"
done
chmod 600 "$TMP/tls.key"
if [[ "$(id -u)" -eq 0 ]] && chgrp 65534 "$TMP/tls.key" 2>/dev/null; then
    jq -n --arg certificate_file "$TMP/tls.crt" --arg key_file "$TMP/tls.key" '{certificate_file:$certificate_file,key_file:$key_file}' >"$TMP/tls-nonroot-group.json"
    expect_adapter_reject tls_key_nonroot_group vmess_tcp_tls "$TMP/tls-nonroot-group.json"
    chgrp 0 "$TMP/tls.key"
fi
vmess_model_build prepare_tls_permissions vmess_tcp_tls 127.0.0.1 62003 "$TMP/users.json" >"$TMP/prepare-model.json"
mkdir -m 700 "$TMP/certificate-store"
head -c 32 /dev/urandom >"$TMP/certificate-store.master"
chmod 600 "$TMP/certificate-store.master"
python3 "$ROOT/scripts/certificate_store.py" --base "$TMP/certificate-store" --catalog "$TMP/certificate-store/catalog.json" --managed-dir "$TMP/certificate-store/managed" --secrets-dir "$TMP/certificate-store/secrets" --master-key "$TMP/certificate-store.master" --lock "$TMP/certificate-store/catalog.lock" import --storage-type managed --certificate-file "$TMP/tls.crt" --private-key-file "$TMP/tls.key" >"$TMP/certificate-import.json"
CERTIFICATE_ID="$(jq -er '.certificate_id' "$TMP/certificate-import.json")"
jq -n --arg certificate_id "$CERTIFICATE_ID" '{certificate_id:$certificate_id}' >"$TMP/central-tls-options.json"
# The preparer must reject path-based TLS input and emit only the central reference.
if python3 "$ROOT/scripts/vmess_prepare_config.py" --model "$TMP/prepare-model.json" --options "$TMP/tcp-tls.json" --output "$TMP/legacy-path-prepared.json" >/dev/null 2>&1; then
    echo 'ERROR: prepare_config aceptó rutas TLS libres.' >&2
    exit 1
fi
jq -n --arg certificate_id "$CERTIFICATE_ID" --arg certificate_file "$TMP/tls.crt" '{certificate_id:$certificate_id,certificate_file:$certificate_file}' >"$TMP/tls-path-injection.json"
if python3 "$ROOT/scripts/vmess_prepare_config.py" --model "$TMP/prepare-model.json" --options "$TMP/tls-path-injection.json" --output "$TMP/path-injection-prepared.json" >/dev/null 2>&1; then
    echo 'ERROR: prepare_config aceptó inyección de ruta TLS.' >&2
    exit 1
fi
python3 "$ROOT/scripts/vmess_prepare_config.py" --model "$TMP/prepare-model.json" --options "$TMP/central-tls-options.json" --output "$TMP/safe-prepared.json" >"$TMP/prepare-meta.json"
[[ -s "$TMP/safe-prepared.json" && ! -e "$TMP/safe-secret.bin" ]]
jq -e --arg certificate_id "$CERTIFICATE_ID" '.security_options=={certificate_id:$certificate_id}' "$TMP/safe-prepared.json" >/dev/null
jq -e '.has_secret==false and .secret_type==null' "$TMP/prepare-meta.json" >/dev/null
echo 'PASS prepare_config emite certificate_id, no crea secreto TLS y rechaza rutas/inyección'

# The adapter independently rejects duplicate emails even if a model file is supplied directly.
vmess_model_build duplicate_email_adapter vmess_ws 127.0.0.1 62004 "$TMP/users.json" >"$TMP/duplicate-email-model.json"
jq '.users[0].email="duplicate@example.test" | .users += [(.users[0] | .id="22222222-2222-4222-8222-222222222222")]' "$TMP/duplicate-email-model.json" >"$TMP/duplicate-email-model-bad.json"
if vmess_xray_26_10_31_build "$TMP/duplicate-email-model-bad.json" "$TMP/ws.json" >/dev/null 2>&1; then
    echo 'ERROR: el adaptador aceptó emails VMess duplicados.' >&2
    exit 1
fi
echo 'PASS rechazo de email duplicado por el adaptador'

# REALITY exige target, clave, server names y short IDs válidos.
jq -n --arg target 'localhost:443' '{target:$target,server_names:["example.com"],short_ids:["0123456789abcdef"]}' >"$TMP/reality-missing-key.json"
expect_adapter_reject reality_missing_key vmess_reality "$TMP/reality-missing-key.json"
jq -n --arg target 'localhost:443' --arg private_key "$REALITY_KEY" '{target:$target,private_key:$private_key,server_names:["example.com"],short_ids:["not-hex"]}' >"$TMP/reality-invalid-short-id.json"
expect_adapter_reject reality_invalid_short_id vmess_reality "$TMP/reality-invalid-short-id.json"
jq -n --arg target 'localhost:443' '{target:$target,private_key:"not-a-real-x25519-key",server_names:["example.com"],short_ids:["0123456789abcdef"]}' >"$TMP/reality-invalid-key.json"
vmess_model_build negative_reality_key vmess_reality 127.0.0.1 62002 "$TMP/users.json" >"$TMP/negative-model.json"
vmess_xray_26_10_31_build "$TMP/negative-model.json" "$TMP/reality-invalid-key.json" >"$TMP/negative-config.json"
if "$XRAY" run -test -config "$TMP/negative-config.json" >/dev/null 2>&1; then
    echo 'ERROR: Xray aceptó una clave privada REALITY inválida.' >&2
    exit 1
fi
echo 'PASS rechazo clave privada REALITY inválida por Xray'

# Seguridad y transporte deben respetar estrictamente la modalidad del modelo.
jq -n --arg path '/ws' --arg certificate_file "$TMP/tls.crt" --arg key_file "$TMP/tls.key" '{path:$path,host:"",certificate_file:$certificate_file,key_file:$key_file}' >"$TMP/none-with-tls.json"
expect_adapter_reject none_with_tls_fields vmess_ws "$TMP/none-with-tls.json"
jq -n '{path:"/ws",host:"",unexpected:true}' >"$TMP/unknown-transport-field.json"
expect_adapter_reject unknown_transport_field vmess_ws "$TMP/unknown-transport-field.json"
vmess_model_build negative_mode vmess_ws 127.0.0.1 62002 "$TMP/users.json" >"$TMP/negative-model.json"
jq '.security="tls"' "$TMP/negative-model.json" >"$TMP/negative-mismatch.json"
if vmess_xray_26_10_31_build "$TMP/negative-mismatch.json" "$TMP/ws.json" >/dev/null 2>&1; then
    echo 'ERROR: el adaptador aceptó una combinación modelo/transporte/seguridad inconsistente.' >&2
    exit 1
fi
echo 'PASS rechazo combinación modelo/seguridad inconsistente'
echo 'OK: Xray-core 26.10.31 validó las 14 combinaciones y rechazó los casos negativos TLS/REALITY/transporte.'
