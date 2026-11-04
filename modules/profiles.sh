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
    local name description notes source path profile_id json
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
    printf '\nOrigen:\n  [1] Crear desde cero (sin JSON)\n  [2] Copiar desde archivo JSON\n  [3] Copiar desde otro perfil\n  [0] Cancelar\n'
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

menu_profiles() {
    local option
    while true; do
        ui_clear
        ui_title "GESTIONAR PERFILES"
        printf '\n  [1] Crear perfil\n  [2] Consultar perfiles\n  [3] Modificar perfil\n  [4] Duplicar perfil\n  [5] Renombrar perfil\n'
        printf '  [6] Eliminar perfil (pendiente de protección de dependencias)\n  [7] Historial y restaurar versión\n'
        printf '  [8] Validar revisión del perfil (estática + Xray; no aplica runtime)\n  [0] Volver\n\n'
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
        printf '  PERFILES\n  [3] Gestionar perfiles\n  [4] Cambiar perfil activo (pendiente de integración runtime)\n'
        printf '  RESPALDOS\n  [5] Crear respaldo (pendiente)\n  [6] Gestionar respaldos (pendiente)\n  [7] Restaurar respaldo (pendiente)\n  [0] Volver\n\n'
        ui_read_option "Selecciona una opción: " option || return 0
        case "$option" in
            1) menu_independent_configurations || true ;;
            3) menu_profiles || true ;;
            0) return 0 ;;
            2) menu_xray_validation || true ;;
            4 | 5 | 6 | 7)
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
