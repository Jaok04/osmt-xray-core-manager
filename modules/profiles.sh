#!/usr/bin/env bash
# Gestión inicial de perfiles y revisiones; no activa ni publica configuraciones.
profiles_cli() {
    python3 "$APP_ROOT/scripts/xray_profiles.py" \
        --store "$XRAY_MANAGER_PROFILES_DIR" \
        --master-key "$XRAY_MANAGER_MASTER_KEY_FILE" "$@"
}
profiles_validation_cli() {
    python3 "$APP_ROOT/scripts/xray_profile_validation.py" \
        --profile-store "$XRAY_MANAGER_PROFILES_DIR" \
        --master-key "$XRAY_MANAGER_MASTER_KEY_FILE" \
        --validation-store "$XRAY_MANAGER_PROFILE_VALIDATIONS_DIR" \
        --xray-binary "$XRAY_BIN_PATH" "$@"
}
profiles_list_json() { profiles_cli list; }
profiles_select_id() {
    local answer json i
    local -a ids=() names=()
    json="$(profiles_list_json)" || return 1
    mapfile -t ids < <(jq -r '.[].profile_id' <<<"$json")
    mapfile -t names < <(jq -r '.[].name' <<<"$json")
    if ((${#ids[@]} == 0)); then
        printf 'No hay perfiles registrados.\n' >&2
        return 1
    fi
    printf '\nPerfiles disponibles:\n' >&2
    for i in "${!ids[@]}"; do printf '  [%d] %s (%s)\n' "$((i + 1))" "${names[i]}" "${ids[i]}"; done >&2
    ui_read_option "Selecciona un perfil: " answer >&2 || return 1
    if [[ ! "$answer" =~ ^[0-9]+$ ]] || ((answer < 1 || answer > ${#ids[@]})); then
        printf 'Selección no válida.\n' >&2
        return 1
    fi
    printf '%s' "${ids[answer - 1]}"
}
profiles_create_menu() {
    local name description notes source path profile_id json base_config
    ui_clear
    ui_title "CREAR PERFIL"
    ui_read_option "Nombre del perfil: " name || return 0
    [[ -n "$name" ]] || {
        printf 'El nombre no puede estar vacío.\n'
        ui_pause
        return 1
    }
    ui_read_option "Descripción (opcional): " description || return 0
    ui_read_option "Notas (opcional): " notes || return 0
    printf '\nOrigen:\n  [1] Crear desde cero (sin JSON)\n  [2] Copiar desde archivo JSON\n  [3] Copiar desde otro perfil\n  [4] Crear perfil base para VLESS-WS-TLS\n  [0] Cancelar\n'
    ui_read_option "Selecciona el origen: " source || return 0
    case "$source" in
        1)
            printf '\nSe creará un perfil Borrador sin configuración asociada.\n'
            ui_confirm "¿Crear el perfil?" || return 0
            json="$(profiles_cli create --name "$name" --description "$description" --notes "$notes")" || {
                printf 'No se pudo crear el perfil.\n'
                ui_pause
                return 1
            }
            ;;
        2)
            ui_read_option "Ruta absoluta del archivo JSON: " path || return 0
            [[ -n "$path" ]] || {
                printf 'La ruta no puede estar vacía.\n'
                ui_pause
                return 1
            }
            printf '\nEl archivo se copiará al almacén; el original no se modificará.\n'
            ui_confirm "¿Crear el perfil con esta copia?" || return 0
            json="$(profiles_cli create --name "$name" --description "$description" --notes "$notes" --config-file "$path")" || {
                printf 'No se pudo crear el perfil. Comprueba el JSON y la ruta.\n'
                ui_pause
                return 1
            }
            ;;
        3)
            profile_id="$(profiles_select_id)" || {
                ui_pause
                return 1
            }
            printf '\nSe creará una copia independiente del perfil seleccionado.\n'
            ui_confirm "¿Crear el perfil?" || return 0
            json="$(profiles_cli duplicate --profile-id "$profile_id" --name "$name" --description "$description" --notes "$notes")" || {
                printf 'No se pudo duplicar el perfil.\n'
                ui_pause
                return 1
            }
            ;;
        4)
            printf '\nSe creará una base mínima de Xray para componer después un inbound VLESS-WS-TLS.\n'
            printf 'Incluye log warning, inbounds vacío y outbound freedom etiquetado direct.\n'
            printf 'No contiene usuarios, certificados ni configuración de runtime.\n'
            ui_confirm "¿Crear el perfil base VLESS-WS-TLS?" || return 0
            base_config="$(mktemp "${TMPDIR:-/run}/xray-manager-profile-base.XXXXXX")" || {
                printf 'No se pudo crear el archivo temporal de perfil.\n'
                ui_pause
                return 1
            }
            chmod 600 "$base_config"
            if ! jq -n '{log:{loglevel:"warning"},inbounds:[],outbounds:[{tag:"direct",protocol:"freedom",settings:{}}]}' >"$base_config"; then
                rm -f -- "$base_config"
                return 1
            fi
            if json="$(profiles_cli create --name "$name" --description "$description" --notes "$notes" --config-file "$base_config")"; then
                rm -f -- "$base_config"
            else
                rm -f -- "$base_config"
                printf 'No se pudo crear el perfil base.\n'
                ui_pause
                return 1
            fi
            ;;
        0) return 0 ;;
        *)
            printf 'Opción no válida.\n'
            ui_pause
            return 1
            ;;
    esac
    printf '\nPerfil creado:\n'
    jq -r '"  Nombre: " + .name + "\n  ID: " + .profile_id + "\n  Revisión: " + (.current_revision // "sin configuración")' <<<"$json"
    printf 'Estado: Borrador / no activado.\n'
    ui_pause
}
profiles_consult_menu() {
    local json profile_id
    ui_clear
    ui_title "CONSULTAR PERFILES"
    json="$(profiles_list_json)" || {
        printf 'No se pudo consultar el almacén.\n'
        ui_pause
        return 1
    }
    if [[ "$(jq 'length' <<<"$json")" -eq 0 ]]; then
        printf '\nNo hay perfiles registrados.\n'
        ui_pause
        return 0
    fi
    printf '\n'
    jq -r '.[] | "• " + .name + "\n  ID: " + .profile_id + "\n  Configuración: " + (if .config_present then (.current_revision // "no disponible") else "ausente" end) + "\n  Validación: " + .validation_status + "\n  Estado activo: " + (if .active_status == "not_integrated" then "no determinado (activación pendiente)" else .active_status end) + "\n  Modificado: " + .modified_at + "\n"' <<<"$json"
    if ui_confirm "¿Consultar detalles y versiones de un perfil?"; then
        profile_id="$(profiles_select_id)" || {
            ui_pause
            return 1
        }
        printf '\nDetalles:\n'
        profiles_cli show --profile-id "$profile_id" | jq .
        printf '\nVersiones:\n'
        profiles_cli versions --profile-id "$profile_id" | jq .
    fi
    ui_pause
}
profiles_modify_menu() {
    local profile_id name description notes path json
    ui_clear
    ui_title "MODIFICAR PERFIL"
    profile_id="$(profiles_select_id)" || {
        ui_pause
        return 1
    }
    printf '\nDeja un campo vacío para conservar su valor actual.\n'
    ui_read_option "Nuevo nombre (opcional): " name || return 0
    ui_read_option "Nueva descripción (opcional): " description || return 0
    ui_read_option "Nuevas notas (opcional): " notes || return 0
    ui_read_option "Ruta de nuevo JSON (vacío = no cambiar configuración): " path || return 0
    [[ -n "$name$description$notes$path" ]] || {
        printf 'No se indicaron cambios.\n'
        ui_pause
        return 0
    }
    printf '\nCambiar el JSON crea una revisión nueva; las anteriores se conservan.\n'
    ui_confirm "¿Guardar los cambios?" || return 0
    local -a args=(update --profile-id "$profile_id")
    [[ -z "$name" ]] || args+=(--name "$name")
    [[ -z "$description" ]] || args+=(--description "$description")
    [[ -z "$notes" ]] || args+=(--notes "$notes")
    [[ -z "$path" ]] || args+=(--config-file "$path")
    json="$(profiles_cli "${args[@]}")" || {
        printf 'No se pudieron guardar los cambios.\n'
        ui_pause
        return 1
    }
    printf '\nCambios guardados. El perfil no se ha activado.\n'
    jq . <<<"$json"
    ui_pause
}
profiles_duplicate_menu() {
    local profile_id name json
    ui_clear
    ui_title "DUPLICAR PERFIL"
    profile_id="$(profiles_select_id)" || {
        ui_pause
        return 1
    }
    ui_read_option "Nombre para la copia: " name || return 0
    [[ -n "$name" ]] || {
        printf 'El nombre no puede estar vacío.\n'
        ui_pause
        return 1
    }
    ui_confirm "¿Crear una copia independiente?" || return 0
    json="$(profiles_cli duplicate --profile-id "$profile_id" --name "$name")" || {
        printf 'No se pudo duplicar el perfil.\n'
        ui_pause
        return 1
    }
    printf '\nCopia creada:\n'
    jq . <<<"$json"
    ui_pause
}
profiles_rename_menu() {
    local profile_id name json
    ui_clear
    ui_title "RENOMBRAR PERFIL"
    profile_id="$(profiles_select_id)" || {
        ui_pause
        return 1
    }
    ui_read_option "Nuevo nombre: " name || return 0
    [[ -n "$name" ]] || {
        printf 'El nombre no puede estar vacío.\n'
        ui_pause
        return 1
    }
    ui_confirm "¿Renombrar el perfil?" || return 0
    json="$(profiles_cli rename --profile-id "$profile_id" --name "$name")" || {
        printf 'No se pudo renombrar el perfil.\n'
        ui_pause
        return 1
    }
    printf '\nPerfil renombrado. El JSON y las revisiones no se modificaron.\n'
    jq . <<<"$json"
    ui_pause
}
profiles_versions_menu() {
    local profile_id revision json
    ui_clear
    ui_title "HISTORIAL DE VERSIONES"
    profile_id="$(profiles_select_id)" || {
        ui_pause
        return 1
    }
    json="$(profiles_cli versions --profile-id "$profile_id")" || {
        printf 'No se pudo consultar el historial.\n'
        ui_pause
        return 1
    }
    jq . <<<"$json"
    ui_read_option "ID de revisión para restaurar (vacío = volver): " revision || return 0
    [[ -n "$revision" ]] || return 0
    printf '\nRestaurar crea una revisión nueva; no sobrescribe la actual.\n'
    ui_confirm "¿Restaurar $revision como nueva revisión?" || return 0
    profiles_cli restore --profile-id "$profile_id" --revision "$revision" | jq .
    ui_pause
}
profiles_compose_vless_ws_tls_menu() {
    local profile_id profile_json revision connections_json answer connection_id mapping_root mapping_file result connection_config_json
    local connections_file="${XRAY_MANAGER_CONNECTIONS_FILE:-/var/lib/xray-manager/connections/connections.json}"
    local connections_base="${XRAY_MANAGER_CONNECTIONS_DIR:-/var/lib/xray-manager/connections}"
    local users_file="${XRAY_MANAGER_USERS_FILE:-/var/lib/xray-manager/users/users.json}"
    local users_lock="${XRAY_MANAGER_INTEGRITY_LOCK:-/run/xray-manager/integrity.lock}"
    local certificate_catalog="${XRAY_MANAGER_CERTIFICATES_CATALOG_FILE:-/var/lib/xray-manager/certificates/catalog.json}"
    local -a ids=() names=() ports=() args=()
    mapping_root="${XRAY_MANAGER_PROFILE_BINDINGS_DIR:-/var/lib/xray-manager/profile-bindings}"

    ui_clear
    ui_title "COMPONER VLESS-WS-TLS EN PERFIL"
    profile_id="$(profiles_select_id)" || { ui_pause; return 1; }
    profile_json="$(profiles_cli show --profile-id "$profile_id")" || { printf '
No se pudo consultar el perfil.
'; ui_pause; return 1; }
    revision="$(jq -er '.metadata.current_revision | select(type == "string" and length > 0)' <<<"$profile_json")" || {
        printf '
El perfil no tiene una revisión actual con configuración.
'; ui_pause; return 1;
    }
    jq -e '.metadata.config_present == true' <<<"$profile_json" >/dev/null || {
        printf '\nEl perfil no contiene una configuración para componer.\n'; ui_pause; return 1;
    }
    [[ -r "$connections_file" ]] || { printf '
No se puede leer el catálogo de conexiones.
'; ui_pause; return 1; }
    connections_json="$(jq -c '[.[] | select(.protocol_id == "vless_ws_tls" and .state == "draft" and .runtime_applied == false)]' "$connections_file")" || return 1
    mapfile -t ids < <(jq -r '.[].id' <<<"$connections_json")
    mapfile -t names < <(jq -r '.[].name // .id' <<<"$connections_json")
    mapfile -t ports < <(jq -r '.[].port | tostring' <<<"$connections_json")
    (("${#ids[@]}" > 0)) || { printf '
No hay conexiones VLESS-WS-TLS elegibles en draft.
'; ui_pause; return 0; }
    printf '
Perfil: %s
Revisión origen: %s
Conexiones elegibles:
' "$profile_id" "$revision"
    local i
    for i in "${!ids[@]}"; do printf '  [%d] %s | %s | puerto %s
' "$((i + 1))" "${names[i]}" "${ids[i]}" "${ports[i]}"; done
    ui_read_option "Selecciona la conexión (0 = cancelar): " answer || return 0
    [[ "$answer" =~ ^[0-9]+$ ]] || { printf 'Selección no válida.
'; ui_pause; return 1; }
    answer=$((10#$answer))
    ((answer >= 1 && answer <= ${#ids[@]})) || return 0
    connection_id="${ids[answer-1]}"
    mapping_file="$mapping_root/$profile_id/$revision.json"
    connection_config_json="$(python3 "$APP_ROOT/scripts/vless_config_store.py" read --connection-id "$connection_id" --base "$connections_base" --catalog "$connections_file" --lock "$users_lock" --secrets-dir "${XRAY_MANAGER_CONNECTION_SECRETS_DIR:-$connections_base/secrets}" --master-key "$XRAY_MANAGER_MASTER_KEY_FILE" --certificate-catalog "$certificate_catalog")" || {
        printf '\nNo se pudo leer y validar la configuración persistida de la conexión.\n'; ui_pause; return 1;
    }

    printf '
Previsualización:
'
    printf '  Perfil: %s
  Revisión origen: %s
  Conexión: %s (%s)
  Puerto: %s
'         "$profile_id" "$revision" "${names[answer-1]}" "$connection_id" "${ports[answer-1]}"
    printf '  WebSocket path: %s\n' "$(jq -r '.configuration.transport_options.path' <<<"$connection_config_json")"
    printf '  Host HTTP WebSocket: %s\n' "$(jq -r '.configuration.transport_options.host // "(no configurado)"' <<<"$connection_config_json")"
    printf '  SNI/serverName del cliente: %s\n' "$(jq -r '.configuration.client_options.tls_server_name // "(no configurado)"' <<<"$connection_config_json")"
    printf '  Certificado TLS del servidor: %s\n' "$(jq -r '.configuration.security_options.certificate_id' <<<"$connection_config_json")"
    printf '  Se creará una revisión nueva, inmutable y pendiente de validación.
'
    printf '  No se activará el perfil ni se modificará Xray/systemd.
'
    ui_confirm "¿Componer la conexión en una revisión nueva?" || { printf 'Operación cancelada.
'; ui_pause; return 0; }

    args=(
        --profile-store "$XRAY_MANAGER_PROFILES_DIR" --master-key "$XRAY_MANAGER_MASTER_KEY_FILE"
        --profile-id "$profile_id" --expected-revision "$revision" --connection-id "$connection_id"
        --connections-catalog "$connections_file" --connections-base "$connections_base"
        --connection-lock "$users_lock" --users-file "$users_file" --users-lock "$users_lock"
        --certificate-catalog "$certificate_catalog" --mapping-root "$mapping_root"
    )
    if [[ -e "$mapping_file" || -L "$mapping_file" ]]; then args+=(--existing-bindings "$mapping_file"); fi
    result="$(python3 "$APP_ROOT/scripts/vless_ws_tls_composer.py" "${args[@]}")" || {
        printf '
El compositor rechazó la operación. No continuar a R-02.
'; ui_pause; return 1;
    }
    printf '
Composición completada:
'
    jq '{status,profile_id,source_revision,revision,inbound_tag,connection_id,clients,mapping_file,validation_status,runtime_changed,service_started}' <<<"$result"
    printf '
La nueva revisión requiere validación; no está activa ni aplicada.
'
    ui_pause
}

profiles_export_vless_clients_menu() {
    local profile_id versions answer revision address port output result mapping_root
    local index
    local -a revisions=() states=() current=() args=()
    local connections_file="${XRAY_MANAGER_CONNECTIONS_FILE:-/var/lib/xray-manager/connections/connections.json}"
    local connections_base="${XRAY_MANAGER_CONNECTIONS_DIR:-/var/lib/xray-manager/connections}"
    local connections_lock="${XRAY_MANAGER_INTEGRITY_LOCK:-/run/xray-manager/integrity.lock}"
    local connections_secrets="${XRAY_MANAGER_CONNECTION_SECRETS_DIR:-$connections_base/secrets}"
    local certificate_catalog="${XRAY_MANAGER_CERTIFICATES_CATALOG_FILE:-/var/lib/xray-manager/certificates/catalog.json}"
    mapping_root="${XRAY_MANAGER_PROFILE_BINDINGS_DIR:-/var/lib/xray-manager/profile-bindings}"
    address="${XRAY_MANAGER_VLESS_PUBLIC_ADDRESS:-pruebas.tvrc.me}"
    port="${XRAY_MANAGER_VLESS_PUBLIC_PORT:-443}"

    ui_clear
    ui_title "EXPORTAR CLIENTES VLESS-WS-TLS"
    profile_id="$(profiles_select_id)" || { ui_pause; return 1; }
    versions="$(profiles_cli versions --profile-id "$profile_id")" || {
        printf '\nNo se pudo consultar el historial de revisiones.\n'; ui_pause; return 1;
    }
    mapfile -t revisions < <(jq -r '.[].revision' <<<"$versions")
    mapfile -t states < <(jq -r '.[].validation' <<<"$versions")
    mapfile -t current < <(jq -r '.[].current' <<<"$versions")
    (( ${#revisions[@]} > 0 )) || { printf '\nEl perfil no contiene revisiones.\n'; ui_pause; return 0; }
    printf '\nSelecciona la revisión exacta que contiene el inbound VLESS-WS-TLS:\n'
    for index in "${!revisions[@]}"; do
        printf '  [%d] %s | validación: %s%s\n' \
            "$((index + 1))" "${revisions[index]}" "${states[index]}" \
            "$([[ ${current[index]} == true ]] && printf ' | actual' || true)"
    done
    ui_read_option "Revisión a exportar (0 = cancelar): " answer || return 0
    [[ "$answer" =~ ^[0-9]+$ ]] || { printf 'Selección no válida.\n'; ui_pause; return 1; }
    answer=$((10#$answer))
    ((answer >= 1 && answer <= ${#revisions[@]})) || return 0
    revision="${revisions[answer-1]}"
    printf '\nEndpoint público: %s:%s\nPerfil: %s\nRevisión exacta: %s\n' "$address" "$port" "$profile_id" "$revision"
    printf 'Se generará un URI por cada UUID del inbound VLESS-WS-TLS.\n'
    printf 'Host WebSocket y SNI se leerán de la configuración guardada; no se inferirán del endpoint.\n'
    printf 'Los URI contienen credenciales de acceso. No se activará el perfil ni se tocará Xray/systemd, DNS o firewall.\n'
    ui_read_option "Ruta de archivo TXT privado (vacío = mostrar URI en pantalla): " output || return 0
    ui_confirm "¿Exportar los clientes de esta revisión?" || return 0
    args=(
        --profile-store "$XRAY_MANAGER_PROFILES_DIR" --master-key "$XRAY_MANAGER_MASTER_KEY_FILE"
        --profile-id "$profile_id" --revision "$revision" --mapping-root "$mapping_root"
        --connections-base "$connections_base" --connections-catalog "$connections_file"
        --connection-lock "$connections_lock" --connection-secrets "$connections_secrets"
        --certificate-catalog "$certificate_catalog" --address "$address" --port "$port"
    )
    [[ -z "$output" ]] || args+=(--output "$output")
    result="$(python3 "$APP_ROOT/scripts/vless_client_export.py" "${args[@]}")" || {
        printf '\nExportación rechazada. No se generó un perfil parcial.\n'; ui_pause; return 1;
    }
    printf '\nExportación completada:\n'
    jq '{status,endpoint,profile_id,revision,validation_status,clients,output_file,output_mode,uri_sha256,runtime_changed,service_started,dns_changed,firewall_changed}' <<<"$result"
    if [[ -z "$output" ]]; then
        printf '\nURI para importar en NetMod (cada URI corresponde a un usuario):\n\n'
        jq -r '.uris[]' <<<"$result"
    else
        printf '\nArchivo privado creado. Transfiérelo de forma segura; contiene UUID de acceso.\n'
    fi
    ui_pause
}

profiles_validate_revision_menu() {
    local profile_id versions answer revision result index
    local -a revisions=() states=() current=()
    ui_clear
    ui_title "VALIDAR REVISIÓN DE PERFIL"
    profile_id="$(profiles_select_id)" || {
        ui_pause
        return 1
    }
    versions="$(profiles_cli versions --profile-id "$profile_id")" || {
        printf 'No se pudo consultar el historial de revisiones.\n'
        ui_pause
        return 1
    }
    mapfile -t revisions < <(jq -r '.[].revision' <<<"$versions")
    mapfile -t states < <(jq -r '.[].validation' <<<"$versions")
    mapfile -t current < <(jq -r '.[].current' <<<"$versions")
    ((${#revisions[@]})) || {
        printf '\nEl perfil no contiene revisiones para validar.\n'
        ui_pause
        return 0
    }
    printf '\nSelecciona la revisión exacta; no se sustituirá automáticamente por current_revision:\n'
    for index in "${!revisions[@]}"; do
        printf '  [%d] %s | validación: %s%s\n' \
            "$((index + 1))" "${revisions[index]}" "${states[index]}" \
            "$([[ ${current[index]} == true ]] && printf ' | actual' || true)"
    done
    ui_read_option "Revisión a validar (0 = cancelar): " answer || return 0
    [[ "$answer" =~ ^[0-9]+$ ]] || {
        printf 'Selección no válida.\n'
        ui_pause
        return 1
    }
    answer=$((10#$answer))
    ((answer >= 1 && answer <= ${#revisions[@]})) || return 0
    revision="${revisions[answer-1]}"
    printf '\nPerfil: %s\nRevisión exacta: %s\n' "$profile_id" "$revision"
    printf 'Se ejecutará validación estática y nativa y se guardará un informe ligado a esta revisión.\n'
    printf 'No se publicará configuración ni se iniciará/reiniciará Xray.\n'
    ui_confirm "¿Validar el perfil $profile_id, revisión $revision?" || {
        printf 'Operación cancelada.\n'
        ui_pause
        return 0
    }
    result="$(profiles_validation_cli --profile-id "$profile_id" --revision "$revision")" || {
        printf '\nLa validación no pudo completarse o no se pudo persistir de forma coherente.\n'
        ui_pause
        return 1
    }
    printf '\nResultado persistido:\n'
    jq '{validation_id, profile_id, revision, result, validation_status, profile_validation_status, last_validated_revision, current_revision, selected_revision_is_current, report_persisted, configuration_applied, service_started}' <<<"$result"
    ui_pause
}

profiles_apply_fixture_menu() {
    local profile_id versions answer revision result confirm_restart=0 index
    local -a revisions=() validations=() args=()
    local -a required_env=(
        XRAY_RUNTIME_FIXTURE_ROOT XRAY_RUNTIME_PROFILE_STORE XRAY_RUNTIME_MASTER_KEY
        XRAY_RUNTIME_VALIDATION_STORE XRAY_RUNTIME_XRAY_BINARY XRAY_RUNTIME_SERVICE_STATE
        XRAY_RUNTIME_BINDINGS_FILE XRAY_RUNTIME_STAGING_ROOT XRAY_RUNTIME_LEASE_ROOT
        XRAY_RUNTIME_CONNECTIONS_CATALOG XRAY_RUNTIME_CONNECTIONS_BASE XRAY_RUNTIME_VMESS_BASE
        XRAY_RUNTIME_CONNECTION_LOCK XRAY_RUNTIME_CERTIFICATE_BASE XRAY_RUNTIME_CERTIFICATE_CATALOG
        XRAY_RUNTIME_CERTIFICATE_MANAGED_DIR XRAY_RUNTIME_CERTIFICATE_SECRETS_DIR
        XRAY_RUNTIME_CERTIFICATE_LOCK XRAY_RUNTIME_CERTIFICATE_MASTER_KEY XRAY_RUNTIME_SERVICE_ROOT
        XRAY_RUNTIME_OPERATION_STORE XRAY_RUNTIME_LIFECYCLE_LOCK XRAY_RUNTIME_APPLICATION_LOCK
        XRAY_RUNTIME_ADAPTER_ROOT XRAY_RUNTIME_ACTIVE_PROFILE_STORE
        XRAY_RUNTIME_SERVICE_UID XRAY_RUNTIME_SERVICE_GID
    )
    local key value

    ui_clear
    ui_title "CAMBIAR PERFIL ACTIVO — ENTORNO FIXTURE"
    if [[ "${XRAY_RUNTIME_MENU_FIXTURE_MODE:-0}" != 1 ]]; then
        printf '\nEsta operación está deshabilitada en el entorno normal.\n'
        printf 'H6-D solo permite ejecutar el flujo R-05 dentro de un fixture aislado.\n'
        printf 'No se ha habilitado aplicación real, systemd ni Xray.\n'
        ui_pause
        return 0
    fi
    for key in "${required_env[@]}"; do
        value="${!key:-}"
        if [[ -z "$value" ]]; then
            printf '\nFalta la variable fixture requerida: %s\n' "$key"
            ui_pause
            return 1
        fi
    done
    if [[ "${XRAY_MANAGER_PROFILES_DIR:-}" != "$XRAY_RUNTIME_PROFILE_STORE" ||
          "${XRAY_MANAGER_MASTER_KEY_FILE:-}" != "$XRAY_RUNTIME_MASTER_KEY" ]]; then
        printf '\nEl almacén/clave seleccionados por el menú no coinciden con el fixture runtime.\n'
        printf 'Configura ambos apuntando al mismo almacén fixture antes de continuar.\n'
        ui_pause
        return 1
    fi
    profile_id="$(profiles_select_id)" || { ui_pause; return 1; }
    versions="$(profiles_cli versions --profile-id "$profile_id")" || {
        printf '\nNo se pudo consultar el historial del perfil.\n'; ui_pause; return 1;
    }
    mapfile -t revisions < <(jq -r '.[].revision' <<<"$versions")
    mapfile -t validations < <(jq -r '.[].validation' <<<"$versions")
    ((${#revisions[@]})) || { printf '\nEl perfil no tiene revisiones.\n'; ui_pause; return 0; }
    printf '\nSelecciona la revisión exacta que se enviará al flujo R-05 fixture:\n'
    for index in "${!revisions[@]}"; do
        printf '  [%d] %s | validación: %s\n' "$((index + 1))" "${revisions[index]}" "${validations[index]}"
    done
    ui_read_option "Revisión (0 = cancelar): " answer || return 0
    [[ "$answer" =~ ^[0-9]+$ ]] || { printf 'Selección no válida.\n'; ui_pause; return 1; }
    answer=$((10#$answer))
    ((answer >= 1 && answer <= ${#revisions[@]})) || return 0
    revision="${revisions[answer-1]}"
    [[ "${validations[answer-1]}" == valid ]] || {
        printf '\nLa revisión seleccionada no está validada. No se ejecutará R-05.\n'; ui_pause; return 1;
    }
    printf '\nPerfil: %s\nRevisión: %s\n' "$profile_id" "$revision"
    printf 'Alcance: exclusivamente fixture aislado; el adaptador predeterminado es R-05 simulado.\n'
    printf 'No se invocará systemctl real ni se modificará /etc/xray.\n'
    if ui_confirm "¿Autorizar restart SIMULADO si el fixture está active?"; then confirm_restart=1; fi
    ui_confirm "¿Ejecutar la aplicación de esta revisión en el fixture?" || {
        printf 'Operación cancelada; no se modificó el fixture.\n'; ui_pause; return 0;
    }
    args=(
        --fixture-root "$XRAY_RUNTIME_FIXTURE_ROOT"
        --profile-store "$XRAY_RUNTIME_PROFILE_STORE" --master-key "$XRAY_RUNTIME_MASTER_KEY"
        --validation-store "$XRAY_RUNTIME_VALIDATION_STORE" --xray-binary "$XRAY_RUNTIME_XRAY_BINARY"
        --service-state "$XRAY_RUNTIME_SERVICE_STATE" --bindings-file "$XRAY_RUNTIME_BINDINGS_FILE"
        --staging-root "$XRAY_RUNTIME_STAGING_ROOT" --lease-root "$XRAY_RUNTIME_LEASE_ROOT"
        --connections-catalog "$XRAY_RUNTIME_CONNECTIONS_CATALOG" --connections-base "$XRAY_RUNTIME_CONNECTIONS_BASE"
        --vmess-base "$XRAY_RUNTIME_VMESS_BASE" --connection-lock "$XRAY_RUNTIME_CONNECTION_LOCK"
        --certificate-base "$XRAY_RUNTIME_CERTIFICATE_BASE" --certificate-catalog "$XRAY_RUNTIME_CERTIFICATE_CATALOG"
        --managed-dir "$XRAY_RUNTIME_CERTIFICATE_MANAGED_DIR"
        --certificate-secrets-dir "$XRAY_RUNTIME_CERTIFICATE_SECRETS_DIR"
        --certificate-lock "$XRAY_RUNTIME_CERTIFICATE_LOCK"
        --certificate-master-key "$XRAY_RUNTIME_CERTIFICATE_MASTER_KEY"
        --service-root "$XRAY_RUNTIME_SERVICE_ROOT" --operation-store "$XRAY_RUNTIME_OPERATION_STORE"
        --lifecycle-lock "$XRAY_RUNTIME_LIFECYCLE_LOCK" --application-lock "$XRAY_RUNTIME_APPLICATION_LOCK"
        --adapter-root "$XRAY_RUNTIME_ADAPTER_ROOT" --profile-id "$profile_id" --revision "$revision"
        --service-uid "$XRAY_RUNTIME_SERVICE_UID" --service-gid "$XRAY_RUNTIME_SERVICE_GID"
    )
    args+=(--active-profile-store "$XRAY_RUNTIME_ACTIVE_PROFILE_STORE")
    ((confirm_restart == 0)) || args+=(--confirm-restart)
    result="$(python3 "$APP_ROOT/scripts/xray_runtime_menu_bridge.py" "${args[@]}")" || {
        printf '\nR-05 no confirmó la operación fixture. No se declarará el perfil aplicado.\n'
        ui_pause
        return 1
    }
    printf '\nResultado R-05 fixture:\n'
    jq '{status, operation_id, generation_id, profile_id, revision, runtime_published,
         service_action_performed, service_started, execution_scope, real_systemd_invoked,
         real_xray_modified}' <<<"$result"
    printf '\nEste resultado pertenece al fixture y no acredita aplicación en el servidor real.\n'
    ui_pause
}


profiles_apply_live_menu() {
    local profile_id versions answer revision result index
    local -a revisions=() validations=()

    ui_clear
    ui_title "APLICAR REVISIÓN Y ARRANCAR XRAY REAL"
    printf '\nEsta acción publica la configuración en /etc/xray/config.json y solicita el primer start de xray.service.\n'
    printf 'Sólo se permite si xray.service está instalado, validado e inactive. No ejecuta restart.\n'
    printf 'Si el resultado del arranque es ambiguo, se conserva la operación para recuperación; no se reintenta automáticamente.\n'
    profile_id="$(profiles_select_id)" || { ui_pause; return 1; }
    versions="$(profiles_cli versions --profile-id "$profile_id")" || {
        printf '\nNo se pudo consultar el historial del perfil.\n'; ui_pause; return 1;
    }
    mapfile -t revisions < <(jq -r '.[].revision' <<<"$versions")
    mapfile -t validations < <(jq -r '.[].validation' <<<"$versions")
    ((${#revisions[@]})) || { printf '\nEl perfil no tiene revisiones.\n'; ui_pause; return 0; }
    printf '\nSelecciona la revisión exacta que se publicará:\n'
    for index in "${!revisions[@]}"; do
        printf '  [%d] %s | validación: %s\n' "$((index + 1))" "${revisions[index]}" "${validations[index]}"
    done
    ui_read_option "Revisión (0 = cancelar): " answer || return 0
    [[ "$answer" =~ ^[0-9]+$ ]] || { printf 'Selección no válida.\n'; ui_pause; return 1; }
    answer=$((10#$answer))
    ((answer >= 1 && answer <= ${#revisions[@]})) || return 0
    revision="${revisions[answer-1]}"
    [[ "${validations[answer-1]}" == valid ]] || {
        printf '\nLa revisión seleccionada no está validada. No se publicará ni iniciará Xray.\n'; ui_pause; return 1;
    }
    printf '\nPerfil: %s\nRevisión: %s\n' "$profile_id" "$revision"
    printf 'Objetivo: VLESS + WS + TLS público en pruebas.tvrc.me:443.\n'
    printf 'El puente rechazará perfiles loopback, puertos distintos o certificados sin SAN válido para el dominio/SNI.\n'
    ui_confirm "¿Autorizar publicación REAL y primer start de xray.service?" || {
        printf 'Operación cancelada; no se ejecutó staging.\n'; ui_pause; return 0;
    }
    ui_confirm "CONFIRMACIÓN FINAL: ¿publicar esta revisión e iniciar Xray en este VPS?" || {
        printf 'Operación cancelada; no se ejecutó staging.\n'; ui_pause; return 0;
    }
    result="$(python3 "$APP_ROOT/scripts/xray_runtime_live_apply_bridge.py" \
        --profile-id "$profile_id" --revision "$revision" --confirm-live)" || {
        printf '\nLa operación live no quedó confirmada:\n%s\n' "$result"
        printf 'Si se indica un operation_id, inspecciona su journal antes de reintentar.\n'
        ui_pause
        return 1
    }
    printf '\nResultado de aplicación live:\n'
    jq '{status, operation_id, generation_id, profile_id, revision, runtime_published,
         service_started, configuration_loaded, completed, journal_state, evidence}' <<<"$result"
    printf '\nLa evidencia de arranque es correlativa; configuration_loaded permanece false.\n'
    ui_pause
}

menu_profiles() {
    local option
    while true; do
        ui_clear
        ui_title "GESTIONAR PERFILES"
        printf '\n  [1] Crear perfil\n  [2] Consultar perfiles\n  [3] Modificar perfil\n  [4] Duplicar perfil\n  [5] Renombrar perfil\n'
        printf '  [6] Eliminar perfil (pendiente de protección de dependencias)\n  [7] Historial y restaurar versión\n'
        printf '  [8] Validar revisión del perfil (estática + Xray; no aplica runtime)\n'
        printf '  [11] Cambiar perfil activo (solo fixture)\n'
        printf '  [12] Aplicar revisión e iniciar Xray REAL (requiere doble confirmación)\n'
        printf '  [9] Componer conexión VLESS-WS-TLS en una revisión nueva\n  [10] Exportar clientes VLESS-WS-TLS para NetMod\n  [0] Volver\n\n'
        ui_read_option "Selecciona una opción: " option || return 0
        case "$option" in
            1) profiles_create_menu || true ;;
            2) profiles_consult_menu || true ;;
            3) profiles_modify_menu || true ;;
            4) profiles_duplicate_menu || true ;;
            5) profiles_rename_menu || true ;;
            6)
                printf '\nLa eliminación permanece deshabilitada hasta integrar y verificar el registro de perfil activo y las dependencias.\n'
                ui_pause
                ;;
            7) profiles_versions_menu || true ;;
            8) profiles_validate_revision_menu || true ;;
            9) profiles_compose_vless_ws_tls_menu || true ;;
            10) profiles_export_vless_clients_menu || true ;;
            11) profiles_apply_fixture_menu || true ;;
            12) profiles_apply_live_menu || true ;;
            0) return 0 ;;
            *)
                printf 'Opción no válida.\n'
                ui_pause
                ;;
        esac
    done
}
menu_config_profiles_backups() {
    local option
    while true; do
        ui_clear
        ui_title "CONFIGURACIONES, PERFILES Y RESPALDOS"
        printf '\n  CONFIGURACIONES\n  [1] Gestionar configuraciones de Xray\n  [2] Validar archivos de configuración\n'
        printf '  PERFILES\n  [3] Gestionar perfiles\n  [4] Cambiar perfil activo (fixture; no modifica el runtime real)\n'
        printf '  RESPALDOS\n  [5] Crear respaldo (pendiente)\n  [6] Gestionar respaldos (pendiente)\n  [7] Restaurar respaldo (pendiente)\n  [0] Volver\n\n'
        ui_read_option "Selecciona una opción: " option || return 0
        case "$option" in
            1) menu_independent_configurations || true ;;
            3) menu_profiles || true ;;
            0) return 0 ;;
            2) menu_xray_validation || true ;;
            4) profiles_apply_fixture_menu || true ;;
            5 | 6 | 7)
                printf '\nEste apartado todavía no está implementado. No se modificó ninguna configuración ni servicio.\n'
                ui_pause
                ;;
            *)
                printf 'Opción no válida.\n'
                ui_pause
                ;;
        esac
    done
}
