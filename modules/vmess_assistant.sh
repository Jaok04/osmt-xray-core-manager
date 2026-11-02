#!/usr/bin/env bash
# Asistente VMess: crea, valida, guarda y recupera borradores sin activar runtime.
connections_vmess_read() {
    local prompt="$1" target_name="$2" read_value
    printf '%s' "$prompt"
    IFS= read -r read_value || return 1
    printf -v "$target_name" '%s' "$read_value"
}
connections_vmess_read_required() {
    local prompt="$1" target_name="$2" read_value
    printf '%s' "$prompt"
    IFS= read -r read_value || return 1
    [[ -n "$read_value" ]] || return 1
    printf -v "$target_name" '%s' "$read_value"
}
connections_vmess_read_secret() {
    local prompt="$1" target_name="$2" read_value
    printf '%s' "$prompt"
    IFS= read -r -s read_value || return 1
    printf '\n'
    [[ -n "$read_value" ]] || return 1
    printf -v "$target_name" '%s' "$read_value"
}
connections_vmess_show_warnings() {
    [[ $# -eq 1 ]] || return 2
    local mode="$1"
    printf '\nADVERTENCIA OPERATIVA VMESS\n'
    printf 'Los relojes del cliente y del servidor deben estar sincronizados. El desfase no debe superar 120 segundos; verifica NTP antes de utilizar la conexión.\n'
    case "$mode" in
    vmess_ws | vmess_ws_tls)
        printf '\nADVERTENCIA WEBSOCKET\n'
        printf 'Xray marca WebSocket como obsoleto/no recomendado en la versión objetivo y recomienda migrar a XHTTP H2/H3. Este transporte también puede presentar patrones de tráfico identificables. Se conserva por compatibilidad y porque forma parte del alcance aprobado.\n'
        ;;
    vmess_httpupgrade | vmess_httpupgrade_tls)
        printf '\nADVERTENCIA HTTPUPGRADE\n'
        printf 'Xray marca HTTPUpgrade como obsoleto/no recomendado, advierte que podría retirarlo y recomienda migrar a XHTTP H2/H3. Este transporte también puede presentar patrones de tráfico identificables. Se conserva porque forma parte del alcance aprobado.\n'
        ;;
    esac
}
connections_vmess_print_review() {
    [[ $# -eq 15 ]] || return 2
    local cid="$1" mode="$2" address="$3" port="$4" count="$5" max_users="$6" model="$7" users="$8" options="$9"
    local cert="${10}" key="${11}" target="${12}" names="${13}" ids="${14}" secret_present="${15}"
    local name transport security
    name="$(jq -r --arg id "$cid" '.[]|select(.id==$id)|(.name // .id)' "$CONNECTION_DATA_FILE")" || return 1
    transport="$(jq -er '.transport' "$model")" || return 1
    security="$(jq -er '.security' "$model")" || return 1
    printf '\n========== RESUMEN DE LA CONEXIÓN VMESS ==========\n'
    printf 'Nombre: %s\n' "$name"
    printf 'ID de conexión: %s\n' "$cid"
    printf 'Dirección de escucha: %s\n' "$address"
    printf 'Puerto: %s\n' "$port"
    printf 'Modalidad: %s\n' "$mode"
    printf 'Transporte: %s\n' "$transport"
    if [[ "$security" == none ]]; then
        if [[ "$mode" == vmess_ws ]]; then
            printf 'Seguridad de transporte: sin TLS adicional (VMess conserva su cifrado propio)\n'
        else
            printf 'Seguridad de transporte: sin TLS adicional\n'
        fi
    else
        printf 'Seguridad de transporte: %s\n' "$security"
    fi
    printf 'Usuarios: %s de %s slots máximos\n' "$count" "$max_users"
    jq -r 'to_entries[] | "  - Usuario \(.key + 1): UUID=\(.value.id), nivel=\(.value.level), email/etiqueta=\(.value.email)"' "$users" || return 1
    printf 'Parámetros del transporte:\n'
    case "$transport" in
    websocket | httpupgrade)
        printf '  Path: %s\n' "$(jq -r '.path' "$options")"
        printf '  Host HTTP: %s\n' "$(jq -r '.host' "$options")"
        ;;
    grpc)
        printf '  Nombre del servicio gRPC: %s\n' "$(jq -r '.service_name' "$options")"
        ;;
    xhttp)
        printf '  Path: %s\n' "$(jq -r '.path' "$options")"
        printf '  Modo XHTTP: %s\n' "$(jq -r '.mode' "$options")"
        ;;
    mkcp)
        printf '  Header mKCP: %s\n' "$(jq -r '.header_type' "$options")"
        printf '  Seed mKCP: %s\n' "$(jq -r '.seed' "$options")"
        ;;
    raw) printf '  Sin parámetros adicionales de transporte.\n' ;;
    *) return 1 ;;
    esac
    case "$security" in
    tls)
        printf 'Parámetros TLS:\n'
        printf '  Certificado: %s\n' "$cert"
        printf '  Clave privada: %s (contenido no mostrado; si guardas el borrador, se almacenará cifrado).\n' "$key"
        ;;
    reality)
        printf 'Parámetros REALITY:\n'
        printf '  Target: %s\n' "$target"
        printf '  Server names: %s\n' "$names"
        printf '  Short IDs: %s\n' "$ids"
        if [[ "$secret_present" == true ]]; then
            printf '  Clave privada: presente (contenido oculto; si guardas el borrador, se almacenará cifrado).\n'
        else
            return 1
        fi
        ;;
    esac
    printf 'Estado: borrador; no se aplicará al runtime ni se abrirán puertos.\n'
    printf '==================================================\n'
}
connections_vmess_users_json() {
    local count="$1" tmp="$2" i uuid email level
    printf '[]\n' >"$tmp"
    for ((i = 1; i <= count; i++)); do
        printf '\nUsuario VMess %s de %s\n' "$i" "$count"
        connections_vmess_read 'UUID (vacío para generar uno): ' uuid || return 1
        if [[ -z "$uuid" ]]; then uuid="$(uuidgen | tr '[:upper:]' '[:lower:]')" || return 1; fi
        [[ "$uuid" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89aAbB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$ ]] || return 1
        connections_vmess_read_required 'Email/etiqueta única: ' email || return 1
        connections_vmess_read 'Nivel (0-255, predeterminado 0): ' level || return 1
        [[ -n "$level" ]] || level=0
        [[ "$level" =~ ^[0-9]{1,3}$ ]] && ((10#$level <= 255)) || return 1
        printf '%s' "$uuid" >"$tmp.uuid"
        chmod 600 "$tmp.uuid"
        jq --rawfile id "$tmp.uuid" --arg email "$email" --argjson level "$((10#$level))" '. + [{id:$id,level:$level,email:$email}]' "$tmp" >"$tmp.next" || return 1
        rm -f "$tmp.uuid"
        mv "$tmp.next" "$tmp"
        chmod 600 "$tmp"
    done
    vmess_model_validate_users "$tmp"
}
connections_vmess_assistant() (
    [[ $# -eq 2 ]] || return 2
    local cid="$1" mode="$2" address port max_users count tmp model options config users
    local path='' host='' service='' xmode='' header_type='none' seed='' cert='' key='' target='' names='' ids='' private=''
    local prepared secret meta secret_type choice secret_present=false xray_bin="${XRAY_VALIDATION_BINARY:-/var/cache/xray-manager/validation/v26.10.31/xray}"
    local -a store_args=()
    command -v jq >/dev/null 2>&1 && command -v uuidgen >/dev/null 2>&1 || {
        printf 'Se requieren jq y uuidgen.\n'
        return 1
    }
    declare -F vmess_model_build >/dev/null && declare -F vmess_xray_26_10_31_build >/dev/null || {
        printf 'Modelo/adaptador VMess no cargado.\n'
        return 1
    }
    port="$(jq -er --arg id "$cid" '.[]|select(.id==$id)|.port' "$CONNECTION_DATA_FILE")" || return 1
    max_users="$(jq -er --arg id "$cid" '.[]|select(.id==$id)|.max_users' "$CONNECTION_DATA_FILE")" || return 1
    printf '\n--- ASISTENTE VMESS ---\n'
    printf 'Se generará un borrador temporal. No se activa ni modifica Xray.\n'
    connections_vmess_show_warnings "$mode" || return 1
    connections_vmess_read_required 'Dirección de escucha (ej. 127.0.0.1): ' address || return 1
    connections_vmess_read "Cantidad de usuarios VMess (1-$max_users, predeterminado 1): " count || return 1
    [[ -n "$count" ]] || count=1
    [[ "$count" =~ ^[0-9]{1,4}$ ]] && ((10#$count >= 1 && 10#$count <= max_users && 10#$count <= 1000)) || {
        printf 'Cantidad fuera del límite de slots o del máximo 1000.\n'
        return 1
    }
    tmp="$(mktemp -d "${TMPDIR:-/tmp}/xray-vmess.XXXXXX")" || return 1
    chmod 700 "$tmp"
    trap 'rm -rf "$tmp"' EXIT
    model="$tmp/model.json"
    options="$tmp/options.json"
    config="$tmp/xray.json"
    users="$tmp/users.json"
    connections_vmess_users_json "$((10#$count))" "$users" || {
        printf 'Usuarios inválidos o duplicados.\n'
        return 1
    }
    case "$mode" in
    vmess_ws | vmess_ws_tls | vmess_httpupgrade | vmess_httpupgrade_tls)
        connections_vmess_read_required 'Path (comienza con /): ' path || return 1
        connections_vmess_read 'Host HTTP (opcional): ' host || return 1
        ;;
    vmess_grpc | vmess_grpc_tls | vmess_grpc_reality)
        connections_vmess_read_required 'Nombre del servicio gRPC: ' service || return 1
        ;;
    vmess_xhttp | vmess_xhttp_tls | vmess_xhttp_reality)
        connections_vmess_read_required 'Path XHTTP (comienza con /): ' path || return 1
        connections_vmess_read 'Modo XHTTP (auto, packet-up, stream-up, stream-one; predeterminado auto): ' xmode || return 1
        [[ -n "$xmode" ]] || xmode=auto
        ;;
    vmess_mkcp | vmess_mkcp_tls)
        connections_vmess_read 'Header mKCP (none, srtp, utp, wechat-video, dtls, wireguard; predeterminado none): ' header_type || return 1
        [[ -n "$header_type" ]] || header_type=none
        connections_vmess_read 'Seed mKCP (opcional): ' seed || return 1
        ;;
    vmess_tcp_tls | vmess_reality) ;;
    *) return 2 ;;
    esac
    case "$mode" in
    vmess_tcp_tls | vmess_ws_tls | vmess_grpc_tls | vmess_httpupgrade_tls | vmess_xhttp_tls | vmess_mkcp_tls)
        connections_vmess_read_required 'Ruta absoluta del certificado TLS: ' cert || return 1
        connections_vmess_read_required 'Ruta absoluta de la clave privada TLS: ' key || return 1
        ;;
    vmess_reality | vmess_grpc_reality | vmess_xhttp_reality)
        connections_vmess_read_required 'Target REALITY (host:puerto): ' target || return 1
        connections_vmess_read_secret 'Private key REALITY (entrada oculta): ' private || return 1
        connections_vmess_read_required 'Server names separados por coma: ' names || return 1
        connections_vmess_read_required 'Short IDs hexadecimales separados por coma: ' ids || return 1
        ;;
    esac
    case "$mode" in
    vmess_ws | vmess_ws_tls | vmess_httpupgrade | vmess_httpupgrade_tls)
        jq -n --arg path "$path" --arg host "$host" '{path:$path,host:$host}' >"$options"
        ;;
    vmess_grpc | vmess_grpc_tls | vmess_grpc_reality)
        jq -n --arg service_name "$service" '{service_name:$service_name}' >"$options"
        ;;
    vmess_xhttp | vmess_xhttp_tls | vmess_xhttp_reality)
        jq -n --arg path "$path" --arg mode "$xmode" '{path:$path,mode:$mode}' >"$options"
        ;;
    vmess_mkcp | vmess_mkcp_tls)
        jq -n --arg header_type "$header_type" --arg seed "$seed" '{header_type:$header_type,seed:$seed}' >"$options"
        ;;
    *) jq -n '{}' >"$options" ;;
    esac
    case "$mode" in
    *_tls)
        jq --arg certificate_file "$cert" --arg key_file "$key" '. + {certificate_file:$certificate_file,key_file:$key_file}' "$options" >"$options.next" && mv "$options.next" "$options"
        ;;
    vmess_reality | vmess_grpc_reality | vmess_xhttp_reality)
        printf '%s' "$private" >"$tmp/reality.private"
        chmod 600 "$tmp/reality.private"
        unset private
        jq --rawfile private_key "$tmp/reality.private" --arg target "$target" --arg names "$names" --arg ids "$ids" '. + {private_key:$private_key,target:$target,server_names:($names|split(",")|map(gsub("^\\s+|\\s+$";""))),short_ids:($ids|split(",")|map(gsub("^\\s+|\\s+$";"")))}' "$options" >"$options.next" && mv "$options.next" "$options"
        ;;
    esac
    chmod 600 "$options" "$users"
    vmess_model_build "$cid" "$mode" "$address" "$port" "$users" >"$model" || return 1
    vmess_xray_26_10_31_build "$model" "$options" >"$config" || {
        printf 'No se pudo construir configuración VMess.\n'
        return 1
    }
    if [[ -x "$xray_bin" ]]; then
        "$xray_bin" run -test -config "$config" || {
            printf 'Xray rechazó el borrador temporal.\n'
            return 1
        }
        printf '\nVALIDACIÓN CORRECTA: Xray aceptó la configuración temporal.\n'
    else
        printf 'No se encontró el binario de validación: %s\n' "$xray_bin"
        return 1
    fi
    [[ -s "$tmp/reality.private" ]] && secret_present=true
    connections_vmess_print_review "$cid" "$mode" "$address" "$port" "$count" "$max_users" "$model" "$users" "$options" "$cert" "$key" "$target" "$names" "$ids" "$secret_present" || {
        printf 'No se pudo generar el resumen de revisión. No se guardó la configuración.\n'
        return 1
    }
    printf '\n¿Guardar el borrador revisado y cifrar la clave privada si aplica? [s/N]: '
    IFS= read -r choice || choice=''
    case "$choice" in
    [sS] | [sS][iI])
        prepared="$tmp/persistent.json"
        secret="$tmp/secret.bin"
        meta="$tmp/meta.json"
        python3 "$APP_ROOT/scripts/vmess_prepare_config.py" --model "$model" --options "$options" --output "$prepared" --secret-output "$secret" >"$meta" || return 1
        secret_type="$(jq -r '.secret_type // empty' "$meta")"
        store_args=(store --connection-id "$cid" --input "$prepared" --base "${XRAY_MANAGER_VMESS_DIR:-/var/lib/xray-manager/vmess}" --catalog "$CONNECTION_DATA_FILE" --lock "$CONNECTION_LOCK" --secrets-dir "${XRAY_MANAGER_VMESS_SECRETS_DIR:-${XRAY_MANAGER_VMESS_DIR:-/var/lib/xray-manager/vmess}/secrets}" --master-key "${XRAY_MANAGER_MASTER_KEY_FILE:-/etc/xray-manager/keys/master.key}")
        if [[ -n "$secret_type" ]]; then store_args+=(--secret-input "$secret" --secret-type "$secret_type"); fi
        python3 "$APP_ROOT/scripts/vmess_config_store.py" "${store_args[@]}" || {
            printf 'No se pudo guardar.\n'
            return 1
        }
        printf '\nConfiguración VMess guardada como borrador. Runtime intacto.\n'
        ;;
    *) printf '\nNo se guardó la configuración.\n'; ui_pause; return 3 ;;
    esac
    ui_pause
)
connections_vmess_assistant_restore() (
    [[ $# -eq 2 ]] || return 2
    local cid="$1" mode="$2" tmp persisted secret model options config address port security path host service xmode seed cert target names ids xray_bin
    tmp="$(mktemp -d "${TMPDIR:-/tmp}/xray-vmess-restore.XXXXXX")" || return 1
    chmod 700 "$tmp"
    trap 'rm -rf "$tmp"' EXIT
    persisted="$tmp/persisted.json"
    secret="$tmp/secret.bin"
    model="$tmp/model.json"
    options="$tmp/options.json"
    config="$tmp/xray.json"
    python3 "$APP_ROOT/scripts/vmess_config_store.py" read --connection-id "$cid" --base "${XRAY_MANAGER_VMESS_DIR:-/var/lib/xray-manager/vmess}" --catalog "$CONNECTION_DATA_FILE" --lock "$CONNECTION_LOCK" --secrets-dir "${XRAY_MANAGER_VMESS_SECRETS_DIR:-${XRAY_MANAGER_VMESS_DIR:-/var/lib/xray-manager/vmess}/secrets}" --master-key "${XRAY_MANAGER_MASTER_KEY_FILE:-/etc/xray-manager/keys/master.key}" --secret-output "$secret" >"$persisted" || {
        printf 'No se pudo recuperar configuración VMess.\n'
        return 1
    }
    address="$(jq -r '.configuration.listen_address' "$persisted")"
    port="$(jq -r '.configuration.listen_port' "$persisted")"
    security="$(jq -r '.configuration.security' "$persisted")"
    [[ "$(jq -r '.configuration.mode_id' "$persisted")" == "$mode" ]] || return 1
    jq '.configuration.users' "$persisted" >"$tmp/users.json"
    vmess_model_build "$cid" "$mode" "$address" "$port" "$tmp/users.json" >"$model" || return 1
    jq '.configuration.transport_options' "$persisted" >"$options"
    case "$security" in
    tls)
        cert="$(jq -r '.configuration.security_options.certificate_file' "$persisted")"
        jq --arg certificate_file "$cert" --arg key_file "$secret" '. + {certificate_file:$certificate_file,key_file:$key_file}' "$options" >"$options.next" && mv "$options.next" "$options"
        ;;
    reality)
        jq -r '.configuration.security_options.target' "$persisted" >"$tmp/target"
        jq -c '.configuration.security_options.server_names' "$persisted" >"$tmp/names"
        jq -c '.configuration.security_options.short_ids' "$persisted" >"$tmp/ids"
        jq --rawfile private_key "$secret" --rawfile target "$tmp/target" --slurpfile server_names "$tmp/names" --slurpfile short_ids "$tmp/ids" '. + {private_key:$private_key,target:($target|rtrimstr("\n")),server_names:$server_names[0],short_ids:$short_ids[0]}' "$options" >"$options.next" && mv "$options.next" "$options"
        ;;
    esac
    vmess_xray_26_10_31_build "$model" "$options" >"$config" || return 1
    xray_bin="${XRAY_VALIDATION_BINARY:-/var/cache/xray-manager/validation/v26.10.31/xray}"
    "$xray_bin" run -test -config "$config" || return 1
    printf 'Configuración VMess recuperada y validada; catálogo y runtime no fueron modificados.\n'
    ui_pause
)