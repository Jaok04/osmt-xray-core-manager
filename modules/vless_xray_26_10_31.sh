#!/usr/bin/env bash
# Adaptador estricto VLESS -> Xray-core v26.10.31.
# Entrada: modelo neutral JSON y opciones explícitas JSON. Salida: config completa.
# No escribe archivos, no genera credenciales y no aplica configuraciones.

vless_xray_26_10_31_build() {
	[[ "$#" -eq 2 ]] || {
		printf 'Uso: vless_xray_26_10_31_build <modelo.json> <opciones.json>\n' >&2
		return 2
	}
	local model_file="$1" options_file="$2" mode transport security
	command -v jq >/dev/null 2>&1 || {
		printf 'Se requiere jq.\n' >&2
		return 1
	}
	[[ -r "$model_file" && -r "$options_file" ]] || {
		printf 'No se pueden leer los archivos de entrada.\n' >&2
		return 2
	}
	jq -e 'type == "object" and .protocol == "vless" and
        (.schema_version == "1") and (.connection_id | type == "string" and length > 0) and
        (.mode_id | type == "string") and (.listen_address | type == "string" and length > 0) and
        (.listen_port | type == "number" and floor == . and . >= 1 and . <= 65535) and
        (.users | type == "array") and (.transport_options == {}) and
        (.security_options == {})' "$model_file" >/dev/null || {
		printf 'El modelo neutral no cumple el esquema esperado.\n' >&2
		return 2
	}
	mode="$(jq -r '.mode_id' "$model_file")"
	transport="$(jq -r '.transport' "$model_file")"
	security="$(jq -r '.security' "$model_file")"
	case "$mode:$transport:$security" in
	vless_ws:websocket:none | vless_tcp_tls:raw:tls | vless_ws_tls:websocket:tls | vless_reality:raw:reality | vless_grpc_tls:grpc:tls | vless_grpc_reality:grpc:reality | vless_xhttp:xhttp:none | vless_xhttp_tls:xhttp:tls | vless_xhttp_reality:xhttp:reality) ;;
	*)
		printf 'La modalidad, transporte y seguridad no coinciden con el catálogo.\n' >&2
		return 2
		;;
	esac
	jq -e 'type == "object"' "$options_file" >/dev/null || {
		printf 'Las opciones deben ser un objeto JSON.\n' >&2
		return 2
	}

	case "$mode" in
	vless_ws)
		jq -e 'keys == ["path"] and (.path | type == "string" and startswith("/") and length > 1)' "$options_file" >/dev/null || {
			printf 'WebSocket requiere únicamente path explícito que comience por /.\n' >&2
			return 2
		}
		;;
	vless_xhttp)
		jq -e 'keys == ["mode","path"] and
                (.path | type == "string" and startswith("/") and length > 1) and
                (.mode | type == "string" and (IN("auto","packet-up","stream-up","stream-one")))' "$options_file" >/dev/null || {
			printf 'XHTTP requiere path y mode válidos.\n' >&2
			return 2
		}
		;;
	vless_xhttp_tls)
		jq -e 'keys == ["certificate_file","key_file","mode","path"] and
                (.path | type == "string" and startswith("/") and length > 1) and
                (.mode | type == "string" and (IN("auto","packet-up","stream-up","stream-one"))) and
                (.certificate_file | type == "string" and length > 0) and
                (.key_file | type == "string" and length > 0)' "$options_file" >/dev/null || {
			printf 'XHTTP+TLS requiere path, mode, certificate_file y key_file válidos.\n' >&2
			return 2
		}
		local cert key
		cert="$(jq -r '.certificate_file' "$options_file")"
		key="$(jq -r '.key_file' "$options_file")"
		[[ -r "$cert" && -r "$key" ]] || {
			printf 'No se puede leer el certificado o la clave TLS.\n' >&2
			return 2
		}
		;;
	vless_xhttp_reality)
		jq -e 'keys == ["mode","path","private_key","server_names","short_ids","target"] and
                (.path | type == "string" and startswith("/") and length > 1) and
                (.mode | type == "string" and (IN("auto","packet-up","stream-up","stream-one"))) and
                (.private_key | type == "string" and length > 0) and
                (.server_names | type == "array" and length > 0 and all(.[]; type == "string" and length > 0)) and
                (.short_ids | type == "array" and length > 0 and all(.[]; type == "string" and length <= 16 and test("^[0-9a-fA-F]*$"))) and
                (.target | type == "string" and length > 0 and test("^.+:[0-9]{1,5}$") and
                    ((capture(":(?<p>[0-9]{1,5})$").p | tonumber) >= 1 and
                     (capture(":(?<p>[0-9]{1,5})$").p | tonumber) <= 65535))' "$options_file" >/dev/null || {
			printf 'XHTTP+REALITY requiere path, mode y parámetros REALITY válidos.\n' >&2
			return 2
		}
		;;
	vless_tcp_tls | vless_ws_tls)
		jq -e 'keys == ["certificate_file","key_file"] and
                (.certificate_file | type == "string" and length > 0) and
                (.key_file | type == "string" and length > 0)' "$options_file" >/dev/null || {
			printf 'TLS requiere certificate_file y key_file explícitos.\n' >&2
			return 2
		}
		local cert key
		cert="$(jq -r '.certificate_file' "$options_file")"
		key="$(jq -r '.key_file' "$options_file")"
		[[ -r "$cert" && -r "$key" ]] || {
			printf 'No se puede leer el certificado o la clave TLS.\n' >&2
			return 2
		}
		;;
	vless_grpc_tls)
		jq -e 'keys == ["certificate_file","key_file","service_name"] and
                (.certificate_file | type == "string" and length > 0) and
                (.key_file | type == "string" and length > 0) and
                (.service_name | type == "string" and length > 0)' "$options_file" >/dev/null || {
			printf 'gRPC+TLS requiere service_name, certificate_file y key_file explícitos.\n' >&2
			return 2
		}
		local cert key
		cert="$(jq -r '.certificate_file' "$options_file")"
		key="$(jq -r '.key_file' "$options_file")"
		[[ -r "$cert" && -r "$key" ]] || {
			printf 'No se puede leer el certificado o la clave TLS.\n' >&2
			return 2
		}
		;;
	vless_grpc_reality | vless_reality)
		local required_keys
		if [[ "$mode" == "vless_grpc_reality" ]]; then
			required_keys='["private_key","server_names","service_name","short_ids","target"]'
		else
			required_keys='["private_key","server_names","short_ids","target"]'
		fi
		jq -e --argjson required "$required_keys" 'keys == $required and
                (.private_key | type == "string" and length > 0) and
                (.server_names | type == "array" and length > 0 and all(.[]; type == "string" and length > 0)) and
                (.short_ids | type == "array" and length > 0 and all(.[]; type == "string" and length <= 16 and test("^[0-9a-fA-F]*$"))) and
                (.target | type == "string" and length > 0 and test("^.+:[0-9]{1,5}$") and
                    ((capture(":(?<p>[0-9]{1,5})$").p | tonumber) >= 1 and
                     (capture(":(?<p>[0-9]{1,5})$").p | tonumber) <= 65535)) and
                (if has("service_name") then (.service_name | type == "string" and length > 0) else true end)' "$options_file" >/dev/null || {
			printf 'REALITY requiere parámetros válidos; gRPC también requiere service_name.\n' >&2
			return 2
		}
		;;
	esac

	jq -n --slurpfile m "$model_file" --slurpfile o "$options_file" '
      ($m[0]) as $m | ($o[0]) as $o |
      {
        log:{loglevel:"warning"},
        inbounds:[{
          tag:("vless-" + $m.connection_id),
          listen:$m.listen_address,
          port:$m.listen_port,
          protocol:"vless",
          settings:{clients:$m.users,decryption:"none"},
          streamSettings:(
            {method:$m.transport,security:$m.security} +
            (if $m.transport == "websocket" then {wsSettings:{path:$o.path}} else {} end) +
            (if $m.transport == "xhttp" then {xhttpSettings:{path:$o.path,mode:$o.mode}} else {} end) +
            (if $m.transport == "grpc" then {grpcSettings:{serviceName:$o.service_name}} else {} end) +
            (if $m.security == "tls" then {tlsSettings:{certificates:[{certificateFile:$o.certificate_file,keyFile:$o.key_file}]}} else {} end) +
            (if $m.security == "reality" then {realitySettings:{
              target:$o.target,type:"tcp",serverNames:$o.server_names,
              privateKey:$o.private_key,shortIds:$o.short_ids
            }} else {} end)
          )
        }],
        outbounds:[{tag:"direct",protocol:"freedom",settings:{}}]
      }'
}
