#!/usr/bin/env bash
# Adaptador estricto VMess -> Xray-core v26.10.31.
vmess_xray_26_10_31_validate_tls_pair() {
    [[ $# -eq 2 ]] || return 2
    python3 - "$1" "$2" <<'PY'
import os
import stat
import sys
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

def read_regular(path):
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    fd = os.open(path, flags)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise ValueError("not a regular file")
        with os.fdopen(fd, "rb") as stream:
            fd = -1
            return stream.read(4 * 1024 * 1024 + 1)
    finally:
        if fd >= 0:
            os.close(fd)

try:
    certificate_data = read_regular(sys.argv[1])
    private_key_data = read_regular(sys.argv[2])
    if len(certificate_data) > 4 * 1024 * 1024 or len(private_key_data) > 4 * 1024 * 1024:
        raise ValueError("file too large")
    certificate = x509.load_pem_x509_certificate(certificate_data)
    private_key = serialization.load_pem_private_key(private_key_data, password=None)
    cert_public = certificate.public_key().public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)
    key_public = private_key.public_key().public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)
    if cert_public != key_public:
        raise ValueError("certificate and private key do not match")
except Exception:
    raise SystemExit(1)
PY
}

vmess_xray_26_10_31_build() {
    [[ $# -eq 2 ]] || {
        printf 'Uso: vmess_xray_26_10_31_build <modelo.json> <opciones.json>\n' >&2
        return 2
    }
    local model_file="$1" options_file="$2" mode transport security cert key
    command -v jq >/dev/null 2>&1 || return 1
    [[ -r "$model_file" && -r "$options_file" ]] || return 2
    jq -e 'type=="object" and .schema_version==1 and .protocol=="vmess" and
		(.connection_id|type=="string" and length>0) and
		(.listen_address|type=="string" and length>0) and
		(.listen_port|type=="number" and floor==. and .>=1 and .<=65535) and
		(.users|type=="array") and (.transport_options|type=="object") and (.security_options|type=="object")' "$model_file" >/dev/null || return 2
    mode="$(jq -r '.mode_id' "$model_file")"
    transport="$(jq -r '.transport' "$model_file")"
    security="$(jq -r '.security' "$model_file")"
    case "$mode:$transport:$security" in
    vmess_ws:websocket:none | vmess_tcp_tls:raw:tls | vmess_ws_tls:websocket:tls | vmess_reality:raw:reality | vmess_grpc:grpc:none | vmess_grpc_tls:grpc:tls | vmess_grpc_reality:grpc:reality | vmess_httpupgrade:httpupgrade:none | vmess_httpupgrade_tls:httpupgrade:tls | vmess_xhttp:xhttp:none | vmess_xhttp_tls:xhttp:tls | vmess_xhttp_reality:xhttp:reality | vmess_mkcp:mkcp:none | vmess_mkcp_tls:mkcp:tls) ;;
    *)
        printf 'Combinación VMess no admitida.\n' >&2
        return 2
        ;;
    esac
    jq -e '.users | type == "array" and length >= 1 and length <= 1000 and all(.[]; type == "object" and (keys - ["id","level","email"] | length) == 0 and (.id | type == "string" and test("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89aAbB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$")) and (.level | type == "number" and floor == . and . >= 0 and . <= 255) and (.email | type == "string" and length >= 1 and length <= 255)) and ([.[].id | ascii_downcase] | length == (unique | length))' "$model_file" >/dev/null || {
        printf 'Usuarios VMess inválidos.\n' >&2
        return 2
    }
    jq -e 'type=="object"' "$options_file" >/dev/null || return 2
    case "$transport" in
    websocket | httpupgrade)
        jq -e '(keys - ["path","host","certificate_file","key_file","private_key","target","server_names","short_ids"] | length)==0 and has("path") and has("host") and (.path|type=="string" and startswith("/") and length<=2048) and (.host|type=="string" and length<=255)' "$options_file" >/dev/null || {
            printf 'Path/host de transporte inválidos.\n' >&2
            return 2
        }
        ;;
    grpc)
        jq -e '(keys - ["service_name","certificate_file","key_file","private_key","target","server_names","short_ids"] | length)==0 and has("service_name") and (.service_name|type=="string" and length>0 and length<=255)' "$options_file" >/dev/null || {
            printf 'service_name gRPC inválido.\n' >&2
            return 2
        }
        ;;
    xhttp)
        jq -e '(keys - ["mode","path","certificate_file","key_file","private_key","target","server_names","short_ids"] | length)==0 and has("mode") and has("path") and (.path|type=="string" and startswith("/") and length<=2048) and (.mode|IN("auto","packet-up","stream-up","stream-one"))' "$options_file" >/dev/null || {
            printf 'Opciones XHTTP inválidas.\n' >&2
            return 2
        }
        ;;
    mkcp)
        jq -e '(keys - ["header_type","seed","certificate_file","key_file"] | length)==0 and has("header_type") and has("seed") and (.header_type|IN("none","srtp","utp","wechat-video","dtls","wireguard")) and (.seed|type=="string" and length<=30)' "$options_file" >/dev/null || {
            printf 'Opciones mKCP inválidas.\n' >&2
            return 2
        }
        ;;
    raw) jq -e '(keys - ["certificate_file","key_file","private_key","target","server_names","short_ids"] | length)==0' "$options_file" >/dev/null || return 2 ;;
    esac
    case "$security" in
    none) jq -e '(has("certificate_file")|not) and (has("key_file")|not) and (has("private_key")|not) and (has("target")|not) and (has("server_names")|not) and (has("short_ids")|not)' "$options_file" >/dev/null || {
        printf 'Esta modalidad no admite opciones de seguridad.\n' >&2
        return 2
    } ;;
    tls)
        jq -e 'has("certificate_file") and has("key_file") and (has("private_key")|not) and (has("target")|not) and (has("server_names")|not) and (has("short_ids")|not) and (.certificate_file|type=="string" and startswith("/")) and (.key_file|type=="string" and startswith("/"))' "$options_file" >/dev/null || return 2
        cert="$(jq -r '.certificate_file' "$options_file")"
        key="$(jq -r '.key_file' "$options_file")"
        [[ -f "$cert" && -r "$cert" && ! -L "$cert" && -f "$key" && -r "$key" && ! -L "$key" ]] || {
            printf 'Certificado/clave TLS no legibles o no regulares.\n' >&2
            return 2
        }
        vmess_xray_26_10_31_validate_tls_pair "$cert" "$key" >/dev/null 2>&1 || {
            printf 'Certificado TLS o clave privada PEM inválidos, o no corresponden entre sí.\n' >&2
            return 2
        }
        ;;
    reality)
        jq -e 'has("target") and has("private_key") and has("server_names") and has("short_ids") and (has("certificate_file")|not) and (has("key_file")|not) and
				(.target|type=="string" and test("^.+:[0-9]{1,5}$") and ((capture(":(?<p>[0-9]{1,5})$").p|tonumber)>=1 and (capture(":(?<p>[0-9]{1,5})$").p|tonumber)<=65535)) and
				(.private_key|type=="string" and length>0) and
				(.server_names|type=="array" and length>0 and all(.[];type=="string" and length>0)) and
				(.short_ids|type=="array" and length>0 and all(.[];type=="string" and length<=16 and test("^[0-9a-fA-F]*$")))' "$options_file" >/dev/null || {
            printf 'Opciones REALITY inválidas.\n' >&2
            return 2
        }
        ;;
    esac
    jq -n --slurpfile m "$model_file" --slurpfile o "$options_file" '
		($m[0]) as $m | ($o[0]) as $o |
		{
			log:{loglevel:"warning"},
			inbounds:[{
				tag:("vmess-" + $m.connection_id),listen:$m.listen_address,port:$m.listen_port,protocol:"vmess",
				settings:{users:[$m.users[] | {id:.id,alterId:0,security:"auto",level:.level,email:.email}]},
				streamSettings:(
					{network:$m.transport,security:$m.security} +
					(if $m.transport=="websocket" then {wsSettings:{path:$o.path,headers:(if $o.host!="" then {Host:$o.host} else {} end)}} else {} end) +
					(if $m.transport=="httpupgrade" then {httpupgradeSettings:{path:$o.path,host:$o.host}} else {} end) +
					(if $m.transport=="grpc" then {grpcSettings:{serviceName:$o.service_name}} else {} end) +
					(if $m.transport=="xhttp" then {xhttpSettings:{path:$o.path,mode:$o.mode}} else {} end) +
					(if $m.transport=="mkcp" then {kcpSettings:({header:{type:$o.header_type}} + (if $o.seed!="" then {seed:$o.seed} else {} end))} else {} end) +
					(if $m.security=="tls" then {tlsSettings:{certificates:[{certificateFile:$o.certificate_file,keyFile:$o.key_file}]}} else {} end) +
					(if $m.security=="reality" then {realitySettings:{target:$o.target,type:"tcp",serverNames:$o.server_names,privateKey:$o.private_key,shortIds:$o.short_ids}} else {} end)
				)
			}],
			outbounds:[{tag:"direct",protocol:"freedom",settings:{}}]
		}'
}
