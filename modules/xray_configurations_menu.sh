#!/usr/bin/env bash
# Interfaz del almacén independiente de configuraciones Xray.
# No activa configuraciones ni modifica runtime/servicios.

xray_configurations_cli() {
    local python="${XRAY_MANAGER_PYTHON:-python3}"
    command -v "$python" >/dev/null 2>&1 || {
        printf 'No se encuentra Python 3. No se instalaron dependencias.\n' >&2
        return 1
    }
    command -v jq >/dev/null 2>&1 || {
        printf 'No se encuentra jq. No se instalaron dependencias.\n' >&2
        return 1
    }
    [[ "$(id -u)" -eq 0 ]] || {
        printf 'El gestor de configuraciones requiere ejecución como root.\n' >&2
        return 1
    }
    "$python" "$APP_ROOT/scripts/xray_configurations.py" \
        --store "${XRAY_MANAGER_CONFIGURATIONS_DIR:-/var/lib/xray-manager/configurations}" \
        --master-key "${XRAY_MANAGER_CONFIGURATIONS_MASTER_KEY_FILE:-/etc/xray-manager/keys/master.key}" \
        "$@"
}

xray_configurations_pause_error() {
    printf '\nNo se pudo completar la operación. Revisa el mensaje anterior.\n'
    ui_pause
}

xray_configurations_select_id() {
    local json selection index
    local -a ids=() names=() revisions=()
    json="$(xray_configurations_cli list)" || return 1
    mapfile -t ids < <(jq -r '.[].config_id' <<<"$json")
    mapfile -t names < <(jq -r '.[].name' <<<"$json")
    mapfile -t revisions < <(jq -r '.[].current_revision // "sin contenido"' <<<"$json")
    if (("${#ids[@]}" == 0)); then
        printf 'No hay configuraciones independientes registradas.\n' >&2
        return 1
    fi
    printf '\nConfiguraciones disponibles:\n' >&2
    for index in "${!ids[@]}"; do
        printf '  [%d] %s — %s (%s)\n' "$((index + 1))" "${names[index]}" "${revisions[index]}" "${ids[index]}" >&2
    done
    ui_read_option "Selecciona una configuración (número, 0 = cancelar): " selection >&2 || return 1
    [[ "$selection" =~ ^[0-9]+$ ]] || {
        printf 'Selección no válida.\n' >&2
        return 1
    }
    selection=$((10#$selection))
    ((selection == 0)) && return 1
    ((selection >= 1 && selection <= ${#ids[@]})) || {
        printf 'Selección fuera de rango.\n' >&2
        return 1
    }
    printf '%s' "${ids[selection - 1]}"
}

xray_configurations_show_menu() {
    local config_id json temp_dir
    ui_clear
    ui_title "CONSULTAR CONFIGURACIÓN INDEPENDIENTE"
    config_id="$(xray_configurations_select_id)" || {
        ui_pause
        return 0
    }
    json="$(xray_configurations_cli show --config-id "$config_id")" || {
        xray_configurations_pause_error
        return 1
    }
    printf '\nMetadatos y estado:\n'
    jq '{
        config_id, name, created_at, modified_at, current_revision,
        validation_status, config_present, activation_status,
        revision_manifest, content_size_bytes
    } | with_entries(select(.value != null))' <<<"$json"
    if [[ "$(jq -r '.current_revision // empty' <<<"$json")" ]]; then
        printf '\nEl contenido puede incluir credenciales, UUID o claves privadas.\n'
        if ui_confirm "¿Deseas mostrar el JSON descifrado en esta terminal?"; then
            temp_dir="$(mktemp -d "${TMPDIR:-/tmp}/xray-config-view.XXXXXX")" || {
                xray_configurations_pause_error
                return 1
            }
            chmod 700 "$temp_dir"
            if xray_configurations_cli export --config-id "$config_id" \
                --revision "$(jq -r '.current_revision' <<<"$json")" \
                --destination "$temp_dir/config.json" >/dev/null; then
                printf '\n--- JSON de la revisión ---\n'
                cat -- "$temp_dir/config.json"
                printf '\n--- Fin del JSON ---\n'
            else
                printf '\nNo fue posible obtener el contenido de forma segura.\n'
            fi
            rm -rf -- "$temp_dir"
        fi
    else
        printf '\nLa configuración todavía no tiene contenido ni revisión.\n'
    fi
    ui_pause
}

xray_configurations_create_menu() {
    local name template choice json
    ui_clear
    ui_title "CREAR CONFIGURACIÓN INDEPENDIENTE"
    ui_read_option "Nombre de la configuración: " name || return 0
    [[ -n "$name" ]] || {
        printf 'El nombre no puede estar vacío.\n'
        ui_pause
        return 1
    }
    printf '\nPlantilla inicial:\n  [1] Vacía (sin contenido)\n  [2] Mínima (JSON de ejemplo)\n  [0] Cancelar\n'
    ui_read_option "Selecciona una plantilla: " choice || return 0
    case "$choice" in
        1) template=empty ;;
        2) template=minimal ;;
        0) return 0 ;;
        *)
            printf 'Opción no válida.\n'
            ui_pause
            return 1
            ;;
    esac
    printf '\nSe creará una configuración independiente como Borrador.\n'
    printf 'No se modificará ni activará la configuración de Xray en uso.\n'
    ui_confirm "¿Crear la configuración $name?" || return 0
    json="$(xray_configurations_cli create --name "$name" --template "$template")" || {
        xray_configurations_pause_error
        return 1
    }
    printf '\nConfiguración creada:\n'
    jq '{config_id, name, current_revision, validation_status, config_present}' <<<"$json"
    ui_pause
}

xray_configurations_import_menu() {
    local source name preview digest accept_invalid=0 json
    ui_clear
    ui_title "IMPORTAR CONFIGURACIÓN DESDE ARCHIVO"
    ui_read_option "Ruta absoluta del archivo JSON: " source || return 0
    [[ "$source" == /* ]] || {
        printf 'La ruta debe ser absoluta.\n'
        ui_pause
        return 1
    }
    preview="$(xray_configurations_cli preview-import --source "$source")" || {
        xray_configurations_pause_error
        return 1
    }
    printf '\nVista previa (el archivo fuente no se modifica):\n'
    jq '{source, source_name, size_bytes, sha256, utf8_valid, utf8_bom, json_valid, root_type, sections_detected, diagnostic, will_be_saved_as, source_modified}' <<<"$preview"
    digest="$(jq -r '.sha256' <<<"$preview")"
    ui_read_option $'\nNombre para la nueva configuración: ' name || return 0
    [[ -n "$name" ]] || {
        printf 'El nombre no puede estar vacío.\n'
        ui_pause
        return 1
    }
    if [[ "$(jq -r '.json_valid' <<<"$preview")" != true ]]; then
        printf '\nEl contenido no es JSON válido. Sólo se puede conservar como Borrador.\n'
        ui_confirm "¿Aceptas expresamente importar estos bytes como Borrador inválido?" || return 0
        accept_invalid=1
    fi
    printf '\nLa importación crea una configuración independiente; no activa ni modifica Xray.\n'
    ui_confirm "¿Importar $name usando el SHA-256 revisado?" || return 0
    if ((accept_invalid)); then
        json="$(xray_configurations_cli import --source "$source" --name "$name" \
            --expected-sha256 "$digest" --confirm --accept-invalid)" || {
            xray_configurations_pause_error
            return 1
        }
    else
        json="$(xray_configurations_cli import --source "$source" --name "$name" \
            --expected-sha256 "$digest" --confirm)" || {
            xray_configurations_pause_error
            return 1
        }
    fi
    printf '\nImportación completada:\n'
    jq '{imported_as, source_modified, configuration: {config_id: .configuration.config_id, name: .configuration.name, current_revision: .configuration.current_revision, validation_status: .configuration.validation_status}}' <<<"$json"
    ui_pause
}

xray_configurations_edit_menu() {
    local config_id source preview digest revision accept_invalid=0 json
    ui_clear
    ui_title "EDITAR CONFIGURACIÓN INDEPENDIENTE"
    config_id="$(xray_configurations_select_id)" || {
        ui_pause
        return 0
    }
    ui_read_option "Ruta absoluta del JSON propuesto: " source || return 0
    [[ "$source" == /* ]] || {
        printf 'La ruta debe ser absoluta.\n'
        ui_pause
        return 1
    }
    preview="$(xray_configurations_cli preview-edit --config-id "$config_id" --source "$source")" || {
        xray_configurations_pause_error
        return 1
    }
    printf '\nVista previa de edición:\n'
    jq '{config_id, current_revision, source, size_bytes, sha256, proposed, diff, will_be_saved_as, previous_revision_unchanged, secret_values_in_diff}' <<<"$preview"
    digest="$(jq -r '.sha256' <<<"$preview")"
    revision="$(jq -r '.current_revision // "none"' <<<"$preview")"
    if [[ "$(jq -r '.proposed.json_valid' <<<"$preview")" != true ]]; then
        printf '\nEl documento propuesto no es JSON válido; sólo se puede conservar como Borrador.\n'
        ui_confirm "¿Aceptas expresamente guardar este contenido inválido?" || return 0
        accept_invalid=1
    fi
    printf '\nLa edición crea una revisión nueva e inmutable; no aplica cambios a Xray.\n'
    ui_confirm "¿Crear la nueva revisión a partir del SHA-256 revisado?" || return 0
    if ((accept_invalid)); then
        json="$(xray_configurations_cli edit --config-id "$config_id" --source "$source" \
            --expected-sha256 "$digest" --expected-revision "$revision" --confirm --accept-invalid)" || {
            xray_configurations_pause_error
            return 1
        }
    else
        json="$(xray_configurations_cli edit --config-id "$config_id" --source "$source" \
            --expected-sha256 "$digest" --expected-revision "$revision" --confirm)" || {
            xray_configurations_pause_error
            return 1
        }
    fi
    printf '\nEdición completada:\n'
    jq '{created_revision, previous_revision, saved_as, previous_revision_unchanged, validation_status, diff}' <<<"$json"
    ui_pause
}

xray_configurations_export_one_menu() {
    local config_id revision target_path result
    local -a args=()
    ui_clear
    ui_title "EXPORTAR UNA CONFIGURACIÓN"
    config_id="$(xray_configurations_select_id)" || {
        ui_pause
        return 0
    }
    ui_read_option "Revisión (vacío = actual): " revision || return 0
    ui_read_option "Ruta absoluta del archivo destino: " target_path || return 0
    [[ "$target_path" == /* ]] || {
        printf 'El destino debe ser una ruta absoluta.\n'
        ui_pause
        return 1
    }
    if [[ -n "$revision" ]]; then
        args+=(--revision "$revision")
    fi
    if [[ -e "$target_path" || -L "$target_path" ]]; then
        printf '\nEl destino ya existe. La sobrescritura requiere confirmación explícita.\n'
        ui_confirm "¿Permitir sobrescribir exactamente este archivo?" || return 0
        args+=(--overwrite)
    fi
    printf '\nLa exportación escribe JSON en claro con permisos root:root 0600.\n'
    ui_confirm "¿Exportar la configuración seleccionada?" || return 0
    result="$(xray_configurations_cli export --config-id "$config_id" \
        --destination "$target_path" "${args[@]}")" || {
        xray_configurations_pause_error
        return 1
    }
    printf '\nExportación completada:\n'
    jq . <<<"$result"
    ui_pause
}

xray_configurations_export_batch_menu() {
    local manifest preview manifest_hash preview_hash result
    ui_clear
    ui_title "EXPORTAR MÚLTIPLES CONFIGURACIONES"
    ui_read_option "Ruta absoluta del manifiesto JSON: " manifest || return 0
    [[ "$manifest" == /* ]] || {
        printf 'La ruta del manifiesto debe ser absoluta.\n'
        ui_pause
        return 1
    }
    preview="$(xray_configurations_cli preview-export-batch --manifest "$manifest")" || {
        xray_configurations_pause_error
        return 1
    }
    printf '\nVista previa de exportación múltiple:\n'
    jq '{manifest_sha256, preview_sha256, total, ready, errors, exports, plaintext_warning, confirmation_required}' <<<"$preview"
    manifest_hash="$(jq -r '.manifest_sha256' <<<"$preview")"
    preview_hash="$(jq -r '.preview_sha256' <<<"$preview")"
    [[ "$manifest_hash" =~ ^[0-9a-f]{64}$ && "$preview_hash" =~ ^[0-9a-f]{64}$ ]] || {
        printf 'La vista previa no devolvió hashes válidos; no se exportó nada.\n'
        ui_pause
        return 1
    }
    (( $(jq -r '.ready' <<<"$preview") > 0 )) || {
        printf 'No hay exportaciones listas para ejecutar.\n'
        ui_pause
        return 1
    }
    printf '\nLos archivos exportados quedan en claro; los errores individuales no detienen el lote.\n'
    ui_confirm "¿Ejecutar exactamente esta vista previa?" || return 0
    result="$(xray_configurations_cli export-batch --manifest "$manifest" \
        --expected-manifest-sha256 "$manifest_hash" \
        --expected-preview-sha256 "$preview_hash" --confirm)" || {
        xray_configurations_pause_error
        return 1
    }
    printf '\nResultado de exportación múltiple:\n'
    jq . <<<"$result"
    ui_pause
}

xray_configurations_export_menu() {
    local option
    while true; do
        ui_clear
        ui_title "EXPORTAR CONFIGURACIONES"
        printf '\n  [1] Exportar una configuración\n'
        printf '  [2] Exportar múltiples configuraciones (manifiesto)\n'
        printf '  [0] Volver\n\n'
        ui_read_option "Selecciona una opción: " option || return 0
        case "$option" in
            1) xray_configurations_export_one_menu || true ;;
            2) xray_configurations_export_batch_menu || true ;;
            0) return 0 ;;
            *)
                printf 'Opción no válida.\n'
                ui_pause
                ;;
        esac
    done
}

xray_configurations_compare_menu() {
    local first second first_revision second_revision result
    local -a args=(compare)
    ui_clear
    ui_title "COMPARAR CONFIGURACIONES"
    printf 'Primera configuración:\n'
    first="$(xray_configurations_select_id)" || {
        ui_pause
        return 0
    }
    printf '\nSegunda configuración:\n'
    second="$(xray_configurations_select_id)" || {
        ui_pause
        return 0
    }
    ui_read_option "Revisión de la primera (vacío = actual): " first_revision || return 0
    ui_read_option "Revisión de la segunda (vacío = actual): " second_revision || return 0
    args+=(--first "$first" --second "$second")
    [[ -n "$first_revision" ]] && args+=(--first-revision "$first_revision")
    [[ -n "$second_revision" ]] && args+=(--second-revision "$second_revision")
    result="$(xray_configurations_cli "${args[@]}")" || {
        xray_configurations_pause_error
        return 1
    }
    printf '\nComparación de solo lectura (los valores secretos no se muestran):\n'
    jq . <<<"$result"
    ui_pause
}

xray_configurations_revisions_menu() {
    local config_id result
    ui_clear
    ui_title "HISTORIAL DE REVISIONES"
    config_id="$(xray_configurations_select_id)" || {
        ui_pause
        return 0
    }
    result="$(xray_configurations_cli revisions --config-id "$config_id")" || {
        xray_configurations_pause_error
        return 1
    }
    printf '\nRevisiones inmutables:\n'
    jq . <<<"$result"
    ui_pause
}

xray_configurations_delete_menu() {
    local config_id preview name result
    ui_clear
    ui_title "ELIMINAR CONFIGURACIÓN INDEPENDIENTE"
    config_id="$(xray_configurations_select_id)" || {
        ui_pause
        return 0
    }
    preview="$(xray_configurations_cli preview-delete --config-id "$config_id")" || {
        xray_configurations_pause_error
        return 1
    }
    printf '\nVista previa de eliminación:\n'
    jq . <<<"$preview"
    name="$(jq -r '.name' <<<"$preview")"
    printf '\nATENCIÓN: el almacén independiente no puede verificar si una configuración se usa fuera de él.\n'
    printf 'No se eliminará ninguna copia de perfil ni respaldo.\n'
    ui_confirm "¿Confirmas que $name NO está aplicada ni en uso?" || return 0
    ui_confirm "¿Eliminar definitivamente sólo esta configuración independiente?" || return 0
    result="$(xray_configurations_cli delete --config-id "$config_id" \
        --expected-name "$name" --confirm --assert-not-active)" || {
        xray_configurations_pause_error
        return 1
    }
    printf '\nEliminación completada:\n'
    jq . <<<"$result"
    ui_pause
}

menu_independent_configurations() {
    local option
    while true; do
        ui_clear
        ui_title "GESTIONAR CONFIGURACIONES DE XRAY"
        printf '\n  [1] Ver configuración guardada\n'
        printf '  [2] Crear configuración nueva\n'
        printf '  [3] Editar configuración\n'
        printf '  [4] Importar configuración desde archivo\n'
        printf '  [5] Exportar configuración (individual o múltiple)\n'
        printf '  [6] Comparar configuraciones\n'
        printf '  [7] Eliminar configuración\n'
        printf '  [8] Consultar revisiones\n'
        printf '  [0] Volver\n\n'
        ui_read_option "Selecciona una opción: " option || return 0
        case "$option" in
            1) xray_configurations_show_menu || true ;;
            2) xray_configurations_create_menu || true ;;
            3) xray_configurations_edit_menu || true ;;
            4) xray_configurations_import_menu || true ;;
            5) xray_configurations_export_menu || true ;;
            6) xray_configurations_compare_menu || true ;;
            7) xray_configurations_delete_menu || true ;;
            8) xray_configurations_revisions_menu || true ;;
            0) return 0 ;;
            *)
                printf 'Opción no válida.\n'
                ui_pause
                ;;
        esac
    done
}
