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

# U-01: proyectar una asociación V2 active/draft al modelo y validar el cliente real con Xray.
export APP_ROOT="$ROOT"
export XRAY_MANAGER_USERS_DIR="$TMP/users"
export XRAY_MANAGER_USERS_FILE="$TMP/users/users.json"
export XRAY_MANAGER_CONNECTIONS_FILE="$TMP/users-connections.json"
export XRAY_MANAGER_INTEGRITY_LOCK="$TMP/u01-integrity.lock"
printf '[{"id":"u01-vless","protocol_id":"vless_ws","max_users":3}]\n' >"$XRAY_MANAGER_CONNECTIONS_FILE"
source "$ROOT/modules/users_v2.sh"
source "$ROOT/modules/vless_assistant.sh"
U01_ID="$(users_identity_create)"
U01_ASSOC="$(users_association_create "$U01_ID" u01-vless 'Cliente U-01' uuid aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa active unlimited 0 none 0 0 auto)"
connections_vless_assistant_build_model u01-vless vless_ws 127.0.0.1 62010 >"$TMP/u01-model.json"
jq -e --arg assoc "$U01_ASSOC" '.users == [{id:"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",email:("assoc:"+$assoc)}]' "$TMP/u01-model.json" >/dev/null
printf '{"path":"/u01-test"}\n' >"$TMP/u01-options.json"
vless_xray_26_10_31_build "$TMP/u01-model.json" "$TMP/u01-options.json" - >"$TMP/u01-xray.json"
"$XRAY" run -test -config "$TMP/u01-xray.json"
printf 'PASS: U-01 Usuarios V2 -> modelo VLESS -> Xray 26.10.31 con asociación active/draft.\n'

openssl req -x509 -newkey rsa:2048 -nodes -keyout "$TMP/tls.key" -out "$TMP/tls.crt" -days 1 -subj '/CN=localhost' -addext 'subjectAltName=DNS:localhost' >/dev/null 2>&1
KEY_OUTPUT="$("$XRAY" x25519)"
REALITY_KEY="$(sed -n 's/^PrivateKey: //p' <<<"$KEY_OUTPUT")"
[[ -n "$REALITY_KEY" ]] || {
	echo 'No se pudo generar la clave efímera de prueba REALITY.' >&2
	exit 1
}

validate_mode() {
	local mode="$1" opts="$2" model config lease_id='-' resolved_opts
	resolved_opts="$TMP/$mode.resolved.json"
	model="$TMP/$mode.model.json"
	config="$TMP/$mode.xray.json"
	vless_model_build "test-$mode" "$mode" 127.0.0.1 62001 >"$model"
	if [[ "$mode" == *_tls ]]; then
		local gid=33 runtime="$TMP/runtime"
		lease_id="resolve-$(printf '%s' "$mode" | sha256sum | cut -c1-32)"
		mkdir -p "$runtime/$lease_id"
		chown root:"$gid" "$runtime" "$runtime/$lease_id"
		chmod 750 "$runtime" "$runtime/$lease_id"
		cp "$TMP/tls.crt" "$runtime/$lease_id/certificate.pem"
		cp "$TMP/tls.key" "$runtime/$lease_id/private-key.pem"
		chown root:"$gid" "$runtime/$lease_id/certificate.pem" "$runtime/$lease_id/private-key.pem"
		chmod 640 "$runtime/$lease_id/certificate.pem" "$runtime/$lease_id/private-key.pem"
		python3 -c 'import json,os,sys; p,l,c,g=sys.argv[1:]; d={"lease_id":l,"connection_id":c,"protocol":"vless","certificate_id":"cert-fixture","certificate_revision":1,"certificate_fingerprint_sha256":"a"*64,"service_uid":1000,"service_gid":int(g)}; open(p,"w").write(json.dumps(d)); os.chown(p,0,int(g)); os.chmod(p,0o640)' "$runtime/$lease_id/manifest.json" "$lease_id" "test-$mode" "$gid"
		jq --arg certificate_file "$runtime/$lease_id/certificate.pem" --arg key_file "$runtime/$lease_id/private-key.pem" 'del(.certificate_id) + {certificate_file:$certificate_file,key_file:$key_file}' "$opts" >"$resolved_opts"
	else
		cp "$opts" "$resolved_opts"
	fi
	XRAY_MANAGER_CERTIFICATES_RUNTIME_DIR="${TMP:-/tmp}/runtime" vless_xray_26_10_31_build "$model" "$resolved_opts" "$lease_id" >"$config"
	"$XRAY" run -test -config "$config"
	printf 'OK: %s\n' "$mode"
}
printf '{"path":"/test-ws"}\n' >"$TMP/ws.json"
printf '{"certificate_id":"cert-fixture"}\n' >"$TMP/tls.json"
printf '{"certificate_id":"cert-fixture","service_name":"test-grpc"}\n' >"$TMP/grpc-tls.json"
printf '{"private_key":"%s","server_names":["example.com"],"short_ids":["0123456789abcdef"],"target":"localhost:443"}\n' "$REALITY_KEY" >"$TMP/reality.json"
printf '{"private_key":"%s","server_names":["example.com"],"service_name":"test-grpc","short_ids":["0123456789abcdef"],"target":"localhost:443"}\n' "$REALITY_KEY" >"$TMP/grpc-reality.json"
printf '{"mode":"auto","path":"/test-xhttp"}\n' >"$TMP/xhttp.json"
printf '{"private_key":"%s","server_names":["example.com"],"short_ids":["0123456789abcdef"],"target":"localhost:443"}\n' "$REALITY_KEY" >"$TMP/reality-xhttp-base.json"
printf '{"certificate_id":"cert-fixture","mode":"auto","path":"/test-xhttp"}\n' >"$TMP/xhttp-tls.json"
jq '. + {mode:"auto",path:"/test-xhttp"}' "$TMP/reality-xhttp-base.json" >"$TMP/reality-xhttp.json"
printf '{}\n' >"$TMP/none.json"
validate_mode vless_ws "$TMP/ws.json"
validate_mode vless_tcp_tls "$TMP/tls.json"
jq ' . + {path:"/test-ws-tls"} ' "$TMP/tls.json" >"$TMP/ws-tls.json"
validate_mode vless_ws_tls "$TMP/ws-tls.json"
validate_mode vless_reality "$TMP/reality.json"
validate_mode vless_grpc_tls "$TMP/grpc-tls.json"
validate_mode vless_grpc_reality "$TMP/grpc-reality.json"
validate_mode vless_xhttp "$TMP/xhttp.json"
validate_mode vless_xhttp_tls "$TMP/xhttp-tls.json"
validate_mode vless_xhttp_reality "$TMP/reality-xhttp.json"

# Validaciones negativas: XHTTP no admite opciones incompletas ni modos desconocidos.
if vless_xray_26_10_31_build "$TMP/vless_xhttp.model.json" "$TMP/none.json" >/dev/null 2>&1; then
	echo 'ERROR: se aceptaron opciones XHTTP incompletas.' >&2
	exit 1
fi
printf '{"mode":"unknown","path":"/invalid"}\n' >"$TMP/xhttp-invalid.json"
if vless_xray_26_10_31_build "$TMP/vless_xhttp.model.json" "$TMP/xhttp-invalid.json" >/dev/null 2>&1; then
	echo 'ERROR: se aceptó un modo XHTTP desconocido.' >&2
	exit 1
fi
echo 'OK: rechazo de opciones XHTTP incompletas y modo desconocido.'
# TLS no puede construirse sin un lease, aunque se proporcionen rutas legibles.
vless_model_build test-no-lease vless_tcp_tls 127.0.0.1 62002 >"$TMP/no-lease.model.json"
if vless_xray_26_10_31_build "$TMP/no-lease.model.json" "$TMP/tls.json" - >/dev/null 2>&1; then
	echo 'ERROR: se aceptó TLS sin lease central.' >&2
	exit 1
fi
