#!/usr/bin/env bash
# Integración C-05E: presentación del motor C-05C y consultas C-05D.
# No activa Xray ni modifica runtime/servicios.

xray_validation_history_cli() {
    local python="${XRAY_MANAGER_PYTHON:-python3}"
    command -v "$python" >/dev/null 2>&1 || { printf 'No se encuentra Python 3; no se instalaron dependencias.\n' >&2; return 1; }
    command -v jq >/dev/null 2>&1 || { printf 'No se encuentra jq; no se instalaron dependencias.\n' >&2; return 1; }
    [[ "$(id -u)" -eq 0 ]] || { printf 'La consulta del almacén requiere root.\n' >&2; return 1; }
    "$python" "$APP_ROOT/scripts/xray_validation_history.py" --store "${XRAY_MANAGER_VALIDATION_DIR:-/var/lib/xray-manager/validation}" "$@"
}

xray_validation_select_config() {
    local json selection
    local -a ids=() names=() revisions=()
    json="$(xray_configurations_cli list)" || return 1
    mapfile -t ids < <(jq -r '.[].config_id' <<<"$json")
    mapfile -t names < <(jq -r '.[].name' <<<"$json")
    mapfile -t revisions < <(jq -r '.[].current_revision // "sin contenido"' <<<"$json")
    ((${#ids[@]})) || { printf 'No hay configuraciones independientes registradas.\n' >&2; return 1; }
    printf '\nConfiguraciones disponibles:\n' >&2
    local i
    for i in "${!ids[@]}"; do printf '  [%d] %s — %s (%s)\n' "$((i+1))" "${names[i]}" "${revisions[i]}" "${ids[i]}" >&2; done
    ui_read_option "Selecciona una configuración (0 = cancelar): " selection >&2 || return 1
    [[ "$selection" =~ ^[0-9]+$ ]] || return 1
    selection=$((10#$selection))
    ((selection >= 1 && selection <= ${#ids[@]})) || return 1
    printf '%s' "${ids[selection-1]}"
}

xray_validation_show_report() {
    local id json
    id="$1"
    json="$(xray_validation_history_cli show --validation-id "$id")" || return 1
    jq '{validation_id, config_id, revision, created_at, stored_at, validation_type, result, content_sha256, content_size_bytes, xray, checks: [.checks[] | {name, status, errors, warnings, details}]}' <<<"$json"
}

xray_validation_run_saved() {
    local config_id metadata revision result python="${XRAY_MANAGER_PYTHON:-python3}"
    config_id="$(xray_validation_select_config)" || { ui_pause; return 0; }
    metadata="$(xray_configurations_cli show --config-id "$config_id")" || { printf 'No se pudieron consultar los metadatos.\n'; ui_pause; return 1; }
    revision="$(jq -r '.current_revision // empty' <<<"$metadata")"
    if [[ -z "$revision" || "$(jq -r '.config_present' <<<"$metadata")" != true ]]; then
        printf '\nLa configuración seleccionada no tiene una revisión con contenido.\n'
        ui_pause; return 0
    fi
    printf '\nConfiguración: %s\nID: %s\nRevisión exacta: %s\nEstado: %s\n' \
        "$(jq -r '.name' <<<"$metadata")" "$config_id" "$revision" "$(jq -r '.validation_status' <<<"$metadata")"
    printf '\nSe ejecutará validación estática y nativa de esta revisión y se guardará un informe permanente.\n'
    printf 'Esto no aplica la configuración ni inicia/reinicia Xray.\n'
    ui_confirm "¿Validar ahora la revisión $revision?" || { printf 'Operación cancelada; no se creó ningún informe.\n'; ui_pause; return 0; }
    result="$("$python" "$APP_ROOT/scripts/xray_config_promotion.py" \
        --config-store "${XRAY_MANAGER_CONFIGURATIONS_DIR:-/var/lib/xray-manager/configurations}" \
        --master-key "${XRAY_MANAGER_CONFIGURATIONS_MASTER_KEY_FILE:-/etc/xray-manager/keys/master.key}" \
        --validation-store "${XRAY_MANAGER_VALIDATION_DIR:-/var/lib/xray-manager/validation}" \
        validate --config-id "$config_id" --revision "$revision")" || {
        printf '\nLa validación no pudo completarse. No se presenta como válida.\n'; ui_pause; return 1;
    }
    printf '\nResultado persistido:\n'
    jq '{validation_id, config_id, revision, result, promoted, validation_status, last_validated_revision, current_revision, selected_revision_is_current, report_persisted, configuration_applied, service_started}' <<<"$result"
    ui_pause
}

xray_validation_latest_menu() {
    local config_id json choice
    printf '\n[1] Último informe global\n[2] Último informe de una configuración\n[0] Volver\n'
    ui_read_option "Selecciona: " choice || return 0
    case "$choice" in
        1) json="$(xray_validation_history_cli latest)" || { printf 'No se pudo consultar el último informe.\n'; ui_pause; return 1; } ;;
        2) config_id="$(xray_validation_select_config)" || return 0; json="$(xray_validation_history_cli latest --config-id "$config_id")" || { printf 'No se pudo consultar el último informe.\n'; ui_pause; return 1; } ;;
        0) return 0 ;;
        *) printf 'Opción no válida.\n'; ui_pause; return 0 ;;
    esac
    if [[ -z "$json" || "$json" == null ]]; then printf '\nNo hay informes de validación.\n'; else jq '{validation_id, config_id, revision, created_at, result, xray, checks: [.checks[] | {name, status, errors, warnings}]}' <<<"$json"; fi
    ui_pause
}

xray_validation_history_menu() {
    local json total offset page selection id first second config_id filter
    offset=0; page=20; filter=""
    while true; do
        local -a args=(list --limit "$page" --offset "$offset")
        [[ -z "$filter" ]] || args+=(--config-id "$filter")
        json="$(xray_validation_history_cli "${args[@]}")" || { printf 'No se pudo verificar el historial.\n'; ui_pause; return 1; }
        total="$(jq -r '.total' <<<"$json")"
        printf '\nHistorial: %s informe(s), mostrando desde %s\n' "$total" "$((offset+1))"
        jq -r '.reports | to_entries[] | "  [" + ((.key + 1) | tostring) + "] " + .value.created_at + " | " + .value.result + " | " + .value.revision + " | " + .value.validation_id' <<<"$json"
        printf '\n[1] Ver detalle por ID\n[2] Comparar dos informes\n[3] Filtrar por configuración\n[4] Siguiente página\n[5] Página anterior\n[0] Volver\n'
        ui_read_option "Selecciona: " selection || return 0
        case "$selection" in
            1)
                ui_read_option "ID completo del informe: " id || continue
                xray_validation_show_report "$id" || printf 'No se pudo mostrar el informe.\n'
                ui_pause ;;
            2)
                ui_read_option "ID del primer informe: " first || continue
                ui_read_option "ID del segundo informe: " second || continue
                xray_validation_history_cli compare --first "$first" --second "$second" | jq . || printf 'No se pudo comparar (los informes deben pertenecer a la misma configuración).\n'
                ui_pause ;;
            3) config_id="$(xray_validation_select_config)" || continue; filter="$config_id"; offset=0 ;;
            4) ((offset + page < total)) && offset=$((offset + page)) || printf 'No hay más páginas.\n' ;;
            5) offset=$((offset >= page ? offset-page : 0)) ;;
            0) return 0 ;;
            *) printf 'Opción no válida.\n'; ui_pause ;;
        esac
    done
}

menu_xray_validation() {
    local option
    while true; do
        ui_clear; ui_title "VALIDACIÓN DE CONFIGURACIONES XRAY"
        printf '\n  [1] Validar configuración guardada\n  [2] Validar archivo externo (no disponible en esta entrega)\n  [3] Validar configuración activa (no disponible en esta entrega)\n  [4] Ver último informe de validación\n  [5] Consultar historial de validaciones\n  [0] Volver\n\n'
        ui_read_option "Selecciona una opción: " option || return 0
        case "$option" in
            1) xray_validation_run_saved || true ;;
            2) printf '\nLa validación de archivos externos requiere un contrato específico aún no implementado. No se leyó ningún archivo.\n'; ui_pause ;;
            3) printf '\nLa validación de configuración activa no está disponible. No se consultó ni modificó el runtime.\n'; ui_pause ;;
            4) xray_validation_latest_menu || true ;;
            5) xray_validation_history_menu || true ;;
            0) return 0 ;;
            *) printf 'Opción no válida.\n'; ui_pause ;;
        esac
    done
}
