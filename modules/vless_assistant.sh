#!/usr/bin/env bash
# Asistente VLESS: previsualiza, valida, persiste bajo confirmación y recupera borradores.

connections_vless_assistant_read() {
	local prompt="$1" var_name="$2" value
	printf '%s' "$prompt"
	IFS= read -r value || return 1
	[[ -n "$value" ]] || return 1
	printf -v "$var_name" '%s' "$value"
}

# Construye siempre desde Usuarios V2. No existe fallback silencioso al modelo legacy.
connections_vless_assistant_build_model() {
	[[ "$#" -eq 4 ]] || return 2
	local connection_id="$1" mode_id="$2" listen_address="$3" listen_port="$4" clients model
	declare -F users_v2_export_vless_candidate_clients >/dev/null 2>&1 || {
		printf 'El adaptador Usuarios V2 no está cargado; se abortó la generación.\n' >&2
		return 1
	}
	clients="$(users_v2_export_vless_candidate_clients "$connection_id")" || return 1
	model="$(vless_model_build "$connection_id" "$mode_id" "$listen_address" "$listen_port")" || return 1
	jq --argjson users "$clients" '.users = $users' <<<"$model"
}

connections_vless_assistant_read_secret() {
	local prompt="$1" var_name="$2" value
	printf '%s' "$prompt"
	IFS= read -r -s value || return 1
	printf '\n'
	[[ -n "$value" ]] || return 1
	printf -v "$var_name" '%s' "$value"
}

connections_vless_assistant() (
	[[ "$#" -eq 2 ]] || return 2
	local connection_id="$1" mode_id="$2" listen_address listen_port options_file model_file config_file tmp
	local path='' service_name='' certificate_id='' tls_cert='' tls_key='' reality_target='' reality_private='' reality_names='' reality_ids='' xhttp_mode='' lease_id='' resolve_result=''
	local save_choice='' prepared_file='' secret_file='' secret_meta='' secret_type=''
	local runtime_root="${XRAY_MANAGER_CERTIFICATES_RUNTIME_DIR:-/run/xray-manager-certificates}"
	local -a store_args=()
	local xray_bin="${XRAY_VALIDATION_BINARY:-/var/cache/xray-manager/validation/v26.10.31/xray}"
	command -v jq >/dev/null 2>&1 || {
		printf '\nSe requiere jq; no se generó configuración.\n'
		return 1
	}
	if ! command -v vless_model_build >/dev/null 2>&1 || ! command -v vless_xray_26_10_31_build >/dev/null 2>&1; then
		printf '\nEl modelo o adaptador VLESS no está cargado.\n'
		return 1
	fi
	printf '\n--- ASISTENTE VLESS: PREVISUALIZACIÓN ---\n'
	printf 'La configuración se construirá temporalmente. Solo se guardará si confirmas; nunca se aplicará al servicio.\n'
	connections_vless_assistant_read 'Dirección de escucha (ej. 127.0.0.1): ' listen_address || return 1
	listen_port="$(jq -r --arg id "$connection_id" '.[] | select(.id == $id) | .port' "$CONNECTION_DATA_FILE")" || return 1
	tmp="$(mktemp -d "${TMPDIR:-/tmp}/xray-vless-assistant.XXXXXX")" || return 1
	chmod 700 "$tmp"
	connections_vless_assistant_cleanup() {
		if [[ -n "${lease_id:-}" ]]; then
			python3 "${APP_ROOT:-/opt/xray-manager}/scripts/certificate_resolver.py" --runtime-root "$runtime_root" cleanup --lease-id "$lease_id" >/dev/null 2>&1 || true
			lease_id=''
		fi
		rm -rf "$tmp"
	}
	trap connections_vless_assistant_cleanup EXIT
	model_file="$tmp/model.json"
	options_file="$tmp/options.json"
	config_file="$tmp/xray.json"
	if ! connections_vless_assistant_build_model "$connection_id" "$mode_id" "$listen_address" "$listen_port" >"$model_file"; then
		printf '\nNo se pudo obtener una instantánea válida de Usuarios V2. No se utilizará el registro legacy.\n'
		return 1
	fi
	case "$mode_id" in
	vless_ws)
		connections_vless_assistant_read 'Ruta WebSocket (debe iniciar con /): ' path || return 1
		jq -n --arg path "$path" '{path:$path}' >"$options_file"
		;;
	vless_xhttp)
		connections_vless_assistant_read 'Ruta XHTTP (debe iniciar con /): ' path || return 1
		connections_vless_assistant_read 'Modo XHTTP (auto, packet-up, stream-up, stream-one): ' xhttp_mode || return 1
		jq -n --arg path "$path" --arg mode "$xhttp_mode" '{path:$path,mode:$mode}' >"$options_file"
		;;
	vless_tcp_tls | vless_ws_tls | vless_xhttp_tls | vless_grpc_tls)
		if [[ "$mode_id" == vless_xhttp_tls ]]; then
			connections_vless_assistant_read 'Ruta XHTTP: ' path || return 1
			connections_vless_assistant_read 'Modo XHTTP (auto, packet-up, stream-up, stream-one): ' xhttp_mode || return 1
		elif [[ "$mode_id" == vless_ws_tls ]]; then
			connections_vless_assistant_read 'Ruta WebSocket: ' path || return 1
		elif [[ "$mode_id" == vless_grpc_tls ]]; then
			connections_vless_assistant_read 'Nombre del servicio gRPC: ' service_name || return 1
		fi
		connections_vless_assistant_read 'ID del certificado TLS central (cert-...): ' certificate_id || return 1
		case "$mode_id" in
		vless_xhttp_tls) jq -n --arg path "$path" --arg mode "$xhttp_mode" --arg certificate_id "$certificate_id" '{path:$path,mode:$mode,certificate_id:$certificate_id}' >"$options_file" ;;
		vless_ws_tls) jq -n --arg path "$path" --arg certificate_id "$certificate_id" '{path:$path,certificate_id:$certificate_id}' >"$options_file" ;;
		vless_grpc_tls) jq -n --arg service_name "$service_name" --arg certificate_id "$certificate_id" '{service_name:$service_name,certificate_id:$certificate_id}' >"$options_file" ;;
		*) jq -n --arg certificate_id "$certificate_id" '{certificate_id:$certificate_id}' >"$options_file" ;;
		esac
		;;
	vless_reality | vless_grpc_reality | vless_xhttp_reality)
		if [[ "$mode_id" == vless_grpc_reality ]]; then connections_vless_assistant_read 'Nombre del servicio gRPC: ' service_name || return 1; fi
		if [[ "$mode_id" == vless_xhttp_reality ]]; then
			connections_vless_assistant_read 'Ruta XHTTP: ' path || return 1
			connections_vless_assistant_read 'Modo XHTTP (auto, packet-up, stream-up, stream-one): ' xhttp_mode || return 1
		fi
		connections_vless_assistant_read 'Target REALITY (host:puerto): ' reality_target || return 1
		connections_vless_assistant_read_secret 'Private key REALITY (entrada oculta): ' reality_private || return 1
		connections_vless_assistant_read 'Server names (separados por comas): ' reality_names || return 1
		connections_vless_assistant_read 'Short IDs hexadecimales (separados por comas): ' reality_ids || return 1
		printf '%s' "$reality_private" >"$tmp/reality.private"
		chmod 600 "$tmp/reality.private"
		unset reality_private
		jq -n --rawfile private_key "$tmp/reality.private" --arg target "$reality_target" --arg names "$reality_names" --arg ids "$reality_ids" --arg service_name "$service_name" --arg path "$path" --arg mode "$xhttp_mode" '
				{target:$target,private_key:$private_key,server_names:($names|split(",")),short_ids:($ids|split(","))} +
				(if $service_name != "" then {service_name:$service_name} else {} end) +
				(if $path != "" then {path:$path,mode:$mode} else {} end)' >"$options_file"
		;;
	*)
		printf '\nModalidad VLESS no compatible con este asistente.\n'
		return 1
		;;
	esac
	chmod 600 "$options_file"
	if [[ "$mode_id" == vless_tcp_tls || "$mode_id" == vless_ws_tls || "$mode_id" == vless_xhttp_tls || "$mode_id" == vless_grpc_tls ]]; then
		printf '\nTLS utiliza el catálogo central. Para validar Xray se guardará primero el borrador y se preparará un lease temporal autorizado.\n'
		printf '¿Deseas guardar este borrador y continuar con la validación TLS? [s/N]: '
		IFS= read -r save_choice || save_choice=''
		case "$save_choice" in [sS] | [sS][iI]) ;; *)
			printf '\nNo se guardó la configuración.\n'
			ui_pause
			return 0
			;;
		esac
		prepared_file="$tmp/persistent-config.json"
		secret_file="$tmp/private-secret.bin"
		secret_meta="$tmp/secret-meta.json"
		python3 "${APP_ROOT:-/opt/xray-manager}/scripts/vless_prepare_config.py" --model "$model_file" --options "$options_file" --output "$prepared_file" --secret-output "$secret_file" >"$secret_meta" || return 1
		store_args=(store --connection-id "$connection_id" --input "$prepared_file" --base "${XRAY_MANAGER_CONNECTIONS_DIR:-$CONNECTION_DATA_DIR}" --catalog "$CONNECTION_DATA_FILE" --lock "$CONNECTION_LOCK" --secrets-dir "${XRAY_MANAGER_SECRETS_DIR:-/var/lib/xray-manager/secrets}" --master-key "${XRAY_MANAGER_MASTER_KEY_FILE:-/etc/xray-manager/keys/master.key}" --certificate-catalog "${XRAY_MANAGER_CERTIFICATES_CATALOG_FILE:-/var/lib/xray-manager/certificates/catalog.json}")
		python3 "${APP_ROOT:-/opt/xray-manager}/scripts/vless_config_store.py" "${store_args[@]}" || return 1
		resolve_result="$tmp/resolve.json"
		python3 "${APP_ROOT:-/opt/xray-manager}/scripts/certificate_resolver.py" --connections-catalog "$CONNECTION_DATA_FILE" --connections-base "${XRAY_MANAGER_CONNECTIONS_DIR:-$CONNECTION_DATA_DIR}" --vmess-base "${XRAY_MANAGER_VMESS_DIR:-/var/lib/xray-manager/vmess}" --connection-lock "$CONNECTION_LOCK" --certificate-base "${XRAY_MANAGER_CERTIFICATES_DIR:-/var/lib/xray-manager/certificates}" --certificate-catalog "${XRAY_MANAGER_CERTIFICATES_CATALOG_FILE:-/var/lib/xray-manager/certificates/catalog.json}" --managed-dir "${XRAY_MANAGER_CERTIFICATES_MANAGED_DIR:-/var/lib/xray-manager/certificates/managed}" --certificate-secrets-dir "${XRAY_MANAGER_CERTIFICATES_SECRETS_DIR:-/var/lib/xray-manager/certificates/secrets}" --certificate-lock "${XRAY_MANAGER_CERTIFICATES_LOCK:-/run/xray-manager-certificate-locks/catalog.lock}" --master-key "${XRAY_MANAGER_MASTER_KEY_FILE:-/etc/xray-manager/keys/master.key}" --runtime-root "$runtime_root" prepare --connection-id "$connection_id" --certificate-id "$certificate_id" >"$resolve_result" || {
			printf '\nEl borrador quedó guardado, pero el resolutor TLS no pudo preparar un lease. No se modificó runtime.\n'
			return 1
		}
		lease_id="$(jq -er '.lease_id' "$resolve_result")" || return 1
		tls_cert="$(jq -er '.certificate_file' "$resolve_result")" || return 1
		tls_key="$(jq -er '.key_file' "$resolve_result")" || return 1
		jq --arg certificate_file "$tls_cert" --arg key_file "$tls_key" 'del(.certificate_id) + {certificate_file:$certificate_file,key_file:$key_file}' "$options_file" >"$tmp/resolved-options.json" || return 1
		if ! vless_xray_26_10_31_build "$model_file" "$tmp/resolved-options.json" "$lease_id" >"$config_file"; then
			printf '\nNo se pudo construir la configuración Xray con el lease TLS. El borrador persiste; no se aplicó runtime.\n'
			return 1
		fi
		if [[ -x "$xray_bin" ]]; then
			"$xray_bin" run -test -config "$config_file" || {
				printf '\nXray rechazó la configuración TLS. El borrador persiste y no se aplicó runtime.\n'
				return 1
			}
			printf '\nVALIDACIÓN CORRECTA: Xray aceptó la configuración con el lease TLS central.\n'
		else
			printf '\nVALIDACIÓN PARCIAL: configuración generada con lease; no existe binario Xray de validación: %s\n' "$xray_bin"
		fi
		python3 "${APP_ROOT:-/opt/xray-manager}/scripts/certificate_resolver.py" --runtime-root "$runtime_root" cleanup --lease-id "$lease_id" >/dev/null || return 1
		lease_id=''
		printf 'El borrador quedó guardado; Xray no fue modificado.\n'
		ui_pause
		return 0
	fi
	if ! vless_xray_26_10_31_build "$model_file" "$options_file" - >"$config_file"; then
		printf '\nNo se pudo construir la configuración. Revisa las opciones; el borrador se conserva.\n'
		return 1
	fi
	if [[ -x "$xray_bin" ]]; then
		if ! "$xray_bin" run -test -config "$config_file"; then
			printf '\nXray rechazó la configuración. El borrador se conserva y no se aplicó nada.\n'
			return 1
		fi
		printf '\nVALIDACIÓN CORRECTA: Xray aceptó la configuración temporal.\n'
	else
		printf '\nVALIDACIÓN PARCIAL: el adaptador generó la configuración, pero no se encontró el binario de validación: %s\n' "$xray_bin"
	fi
	printf 'El resultado y los secretos temporales se eliminarán al salir del asistente.\n'
	printf 'El registro continúa en estado draft; runtime_applied permanece false.\n'
	printf '\n¿Deseas guardar esta configuración de forma persistente y cifrar su clave privada? [s/N]: '
	IFS= read -r save_choice || save_choice=''
	case "$save_choice" in
	[sS] | [sS][iI])
		prepared_file="$tmp/persistent-config.json"
		secret_file="$tmp/private-secret.bin"
		secret_meta="$tmp/secret-meta.json"
		if ! python3 "${APP_ROOT:-/opt/xray-manager}/scripts/vless_prepare_config.py" --model "$model_file" --options "$options_file" --output "$prepared_file" --secret-output "$secret_file" >"$secret_meta"; then
			printf '\nNo se pudo preparar el almacenamiento persistente. No se guardó la configuración.\n'
			ui_pause
			return 1
		fi
		secret_type="$(jq -r '.secret_type // empty' "$secret_meta")"
		store_args=(store --connection-id "$connection_id" --input "$prepared_file" --base "${XRAY_MANAGER_CONNECTIONS_DIR:-$CONNECTION_DATA_DIR}" --catalog "$CONNECTION_DATA_FILE" --lock "$CONNECTION_LOCK" --secrets-dir "${XRAY_MANAGER_SECRETS_DIR:-/var/lib/xray-manager/secrets}" --master-key "${XRAY_MANAGER_MASTER_KEY_FILE:-/etc/xray-manager/keys/master.key}" --certificate-catalog "${XRAY_MANAGER_CERTIFICATES_CATALOG_FILE:-/var/lib/xray-manager/certificates/catalog.json}")
		if [[ -n "$secret_type" ]]; then store_args+=(--secret-input "$secret_file" --secret-type "$secret_type"); fi
		if python3 "${APP_ROOT:-/opt/xray-manager}/scripts/vless_config_store.py" "${store_args[@]}"; then
			printf '\nConfiguración guardada. La conexión continúa como borrador; Xray no fue modificado.\n'
		else
			printf '\nNo se pudo guardar la configuración. No se activó runtime.\n'
			ui_pause
			return 1
		fi
		;;
	*) printf '\nNo se guardó la configuración.\n' ;;
	esac
	ui_pause
)

# Recupera una revisión guardada y la valida sin modificar catálogo ni runtime.
connections_vless_assistant_restore() (
	[[ "$#" -eq 2 ]] || return 2
	local connection_id="$1" mode_id="$2" tmp persisted secret model options xray_config secret_type lease_id='' resolve_result='' certificate_id='' runtime_root="${XRAY_MANAGER_CERTIFICATES_RUNTIME_DIR:-/run/xray-manager-certificates}"
	local -a read_args=()
	command -v jq >/dev/null 2>&1 || return 1
	tmp="$(mktemp -d "${TMPDIR:-/tmp}/xray-vless-restore.XXXXXX")" || return 1
	chmod 700 "$tmp"
	connections_vless_restore_cleanup() {
		if [[ -n "${lease_id:-}" ]]; then
			python3 "${APP_ROOT:-/opt/xray-manager}/scripts/certificate_resolver.py" --runtime-root "$runtime_root" cleanup --lease-id "$lease_id" >/dev/null 2>&1 || true
			lease_id=''
		fi
		rm -rf "$tmp"
	}
	trap connections_vless_restore_cleanup EXIT
	persisted="$tmp/persisted.json"
	secret="$tmp/private.secret"
	model="$tmp/model.json"
	options="$tmp/options.json"
	xray_config="$tmp/xray.json"
	read_args=(read --connection-id "$connection_id" --base "${XRAY_MANAGER_CONNECTIONS_DIR:-$CONNECTION_DATA_DIR}" --catalog "$CONNECTION_DATA_FILE" --lock "$CONNECTION_LOCK" --secrets-dir "${XRAY_MANAGER_SECRETS_DIR:-/var/lib/xray-manager/secrets}" --master-key "${XRAY_MANAGER_MASTER_KEY_FILE:-/etc/xray-manager/keys/master.key}" --certificate-catalog "${XRAY_MANAGER_CERTIFICATES_CATALOG_FILE:-/var/lib/xray-manager/certificates/catalog.json}" --secret-output "$secret")
	if ! python3 "${APP_ROOT:-/opt/xray-manager}/scripts/vless_config_store.py" "${read_args[@]}" >"$persisted"; then
		printf '\nNo fue posible recuperar la configuración o autenticar su secreto.\n'
		return 1
	fi
	local actual_mode address port
	actual_mode="$(jq -r '.configuration.mode_id' "$persisted")"
	address="$(jq -r '.configuration.listen_address' "$persisted")"
	port="$(jq -r '.configuration.listen_port' "$persisted")"
	[[ "$actual_mode" == "$mode_id" ]] || {
		printf '\nLa modalidad guardada no coincide con la seleccionada.\n'
		return 1
	}
	connections_vless_assistant_build_model "$connection_id" "$mode_id" "$address" "$port" >"$model" || {
		printf '\nNo se pudo reconstruir el modelo desde Usuarios V2.\n'
		return 1
	}
	local security
	security="$(jq -r '.configuration.security' "$persisted")"
	case "$security" in
	none)
		jq -c '.configuration.transport_options' "$persisted" >"$options"
		;;
	tls)
		certificate_id="$(jq -r '.configuration.security_options.certificate_id // empty' "$persisted")"
		if [[ -z "$certificate_id" ]]; then
			printf '\nLa revisión TLS es histórica y conserva una clave por conexión. Su migración debe realizarse mediante el procedimiento controlado; no se resolverá con rutas libres.\n'
			return 1
		fi
		resolve_result="$tmp/resolve.json"
		python3 "${APP_ROOT:-/opt/xray-manager}/scripts/certificate_resolver.py" --connections-catalog "$CONNECTION_DATA_FILE" --connections-base "${XRAY_MANAGER_CONNECTIONS_DIR:-$CONNECTION_DATA_DIR}" --vmess-base "${XRAY_MANAGER_VMESS_DIR:-/var/lib/xray-manager/vmess}" --connection-lock "$CONNECTION_LOCK" --certificate-base "${XRAY_MANAGER_CERTIFICATES_DIR:-/var/lib/xray-manager/certificates}" --certificate-catalog "${XRAY_MANAGER_CERTIFICATES_CATALOG_FILE:-/var/lib/xray-manager/certificates/catalog.json}" --managed-dir "${XRAY_MANAGER_CERTIFICATES_MANAGED_DIR:-/var/lib/xray-manager/certificates/managed}" --certificate-secrets-dir "${XRAY_MANAGER_CERTIFICATES_SECRETS_DIR:-/var/lib/xray-manager/certificates/secrets}" --certificate-lock "${XRAY_MANAGER_CERTIFICATES_LOCK:-/run/xray-manager-certificate-locks/catalog.lock}" --master-key "${XRAY_MANAGER_MASTER_KEY_FILE:-/etc/xray-manager/keys/master.key}" --runtime-root "$runtime_root" prepare --connection-id "$connection_id" --certificate-id "$certificate_id" >"$resolve_result" || return 1
		lease_id="$(jq -er '.lease_id' "$resolve_result")" || return 1
		tls_cert="$(jq -er '.certificate_file' "$resolve_result")" || return 1
		tls_key="$(jq -er '.key_file' "$resolve_result")" || return 1
		jq -n --arg certificate_file "$tls_cert" --arg key_file "$tls_key" --argjson transport "$(jq -c '.configuration.transport_options' "$persisted")" '$transport + {certificate_file:$certificate_file,key_file:$key_file}' >"$options"
		;;
	reality)
		jq -n --rawfile private_key "$secret" --arg target "$(jq -r '.configuration.security_options.target' "$persisted")" --argjson server_names "$(jq -c '.configuration.security_options.server_names' "$persisted")" --argjson short_ids "$(jq -c '.configuration.security_options.short_ids' "$persisted")" --arg service_name "$(jq -r '.configuration.transport_options.service_name // empty' "$persisted")" --arg path "$(jq -r '.configuration.transport_options.path // empty' "$persisted")" --arg mode "$(jq -r '.configuration.transport_options.mode // empty' "$persisted")" '{target:$target,private_key:$private_key,server_names:$server_names,short_ids:$short_ids} + (if $service_name != "" then {service_name:$service_name} else {} end) + (if $path != "" then {path:$path,mode:$mode} else {} end)' >"$options"
		;;
	*)
		printf '\nSeguridad guardada desconocida.\n'
		return 1
		;;
	esac
	chmod 600 "$options"
	if ! vless_xray_26_10_31_build "$model" "$options" "${lease_id:--}" >"$xray_config"; then
		printf '\nNo se pudo reconstruir la configuración Xray.\n'
		return 1
	fi
	local xray_bin="${XRAY_VALIDATION_BINARY:-/var/cache/xray-manager/validation/v26.10.31/xray}"
	if [[ -x "$xray_bin" ]]; then
		"$xray_bin" run -test -config "$xray_config" || {
			printf '\nXray rechazó la revisión recuperada.\n'
			return 1
		}
		printf '\nRevisión recuperada y validada correctamente por Xray.\n'
	else
		printf '\nRevisión recuperada y reconstruida; no hay binario Xray de validación disponible.\n'
	fi
	if [[ -n "$lease_id" ]]; then
		python3 "${APP_ROOT:-/opt/xray-manager}/scripts/certificate_resolver.py" --runtime-root "$runtime_root" cleanup --lease-id "$lease_id" >/dev/null || return 1
		lease_id=''
	fi
	printf 'No se modificó el catálogo ni el runtime. Los secretos temporales se eliminarán al salir.\n'
	ui_pause
)
