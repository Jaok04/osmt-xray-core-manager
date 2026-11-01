#!/usr/bin/env bash
# shellcheck disable=SC2016
CONNECTION_CATALOG="$APP_ROOT/config/protocols.tsv"
CONNECTION_DATA_DIR="/var/lib/xray-manager"
CONNECTION_DATA_FILE="$CONNECTION_DATA_DIR/connections.json"
CONNECTION_LOCK="/run/xray-manager/connections.lock"

connections_menu() {
    local option
    while true; do
        ui_clear
        ui_title "GESTIÓN DE PROTOCOLOS Y CONEXIONES"
        printf '\n  [1] Consultar catálogo de protocolos y modalidades\n  [2] Registrar una conexión (borrador)\n  [3] Consultar conexiones registradas\n  [4] Editar una conexión (solo borradores)\n  [5] Eliminar una conexión (solo borradores)\n  [0] Volver al menú principal\n\n'
        ui_read_option "Selecciona una opción: " option
        case "$option" in
            1)
                connections_show_catalog
                ui_pause
                ;;
            2) connections_create_draft ;;
            3)
                connections_list
                ui_pause
                ;;
            4) connections_edit_draft ;;
            5) connections_delete_draft ;;
            0) return 0 ;;
            *)
                printf '\nOpción no válida.\n'
                ui_pause
                ;;
        esac
    done
}
connections_show_catalog() {
    local id name detail
    ui_clear
    ui_title "CATÁLOGO DE PROTOCOLOS"
    printf '%-28s | %-42s | %s\n' "IDENTIFICADOR" "MODALIDAD" "TRANSPORTE / SEGURIDAD"
    ui_line
    while IFS='|' read -r id name detail; do
        [[ -z "$id" || "$id" == \#* ]] && continue
        printf '%-28s | %-42s | %s\n' "$id" "$name" "$detail"
    done <"$CONNECTION_CATALOG"
    printf '\nNota: el catálogo expresa modalidades previstas; no confirma que Xray esté instalado ni que estén aplicadas.\n'
    printf 'Los plugins externos de Shadowsocks requieren instalación y validación independiente.\n'
}
connections_valid_protocol() {
    local wanted="$1" id name detail
    while IFS='|' read -r id name detail; do [[ "$id" == "$wanted" ]] && return 0; done <"$CONNECTION_CATALOG"
    return 1
}
connections_trim_name() {
    local value="$1"
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"
    printf '%s' "$value"
}
connections_require_storage_tools() { command -v jq >/dev/null 2>&1 && command -v flock >/dev/null 2>&1 && command -v ss >/dev/null 2>&1; }
connections_port_in_use() {
    local port="$1"
    ss -H -lntu 2>/dev/null | awk -v p="$port" '$5 ~ ":" p "$" { found = 1 } END { exit !found }'
}
connections_lock() {
    local -n fd_ref="$1"
    mkdir -p "$CONNECTION_DATA_DIR" "$(dirname "$CONNECTION_LOCK")"
    exec {fd_ref}>"$CONNECTION_LOCK"
    flock -x "$fd_ref"
    if [[ ! -e "$CONNECTION_DATA_FILE" ]]; then
        printf '%s\n' '[]' >"$CONNECTION_DATA_FILE"
        chmod 600 "$CONNECTION_DATA_FILE"
    fi
    if ! jq -e 'type == "array"' "$CONNECTION_DATA_FILE" >/dev/null 2>&1; then
        flock -u "$fd_ref"
        exec {fd_ref}>&-
        printf '\nEl archivo de conexiones no contiene un arreglo JSON válido. No se sobrescribió.\n' >&2
        return 1
    fi
}
connections_unlock() {
    local fd="$1"
    flock -u "$fd"
    exec {fd}>&-
}
connections_atomic_update() {
    local fd="$1" tmp
    shift
    tmp="$(mktemp "$CONNECTION_DATA_DIR/.connections.XXXXXX")" || return 1
    if ! jq "$@" "$CONNECTION_DATA_FILE" >"$tmp"; then
        rm -f "$tmp"
        return 1
    fi
    chmod 600 "$tmp"
    if ! mv -f "$tmp" "$CONNECTION_DATA_FILE"; then
        rm -f "$tmp"
        return 1
    fi
}
connections_create_draft() {
    local name protocol_id port max_users id created_at fd
    ui_clear
    ui_title "REGISTRAR CONEXIÓN - BORRADOR"
    printf '\nEste registro no configura Xray ni abre puertos.\n\nNombre descriptivo: '
    IFS= read -r name || return 0
    name="$(connections_trim_name "$name")"
    if [[ -z "$name" || "${#name}" -gt 64 ]]; then
        printf '\nNombre vacío o demasiado largo (máximo 64).\n'
        ui_pause
        return 1
    fi
    printf '\nIdentificadores disponibles:\n'
    connections_show_catalog
    printf '\nIdentificador exacto de modalidad: '
    IFS= read -r protocol_id || return 0
    if ! connections_valid_protocol "$protocol_id"; then
        printf '\nModalidad no reconocida.\n'
        ui_pause
        return 1
    fi
    printf 'Puerto previsto (1-65535): '
    IFS= read -r port || return 0
    if [[ ! "$port" =~ ^[0-9]{1,5}$ ]] || ((10#$port < 1 || 10#$port > 65535)); then
        printf '\nPuerto inválido.\n'
        ui_pause
        return 1
    fi
    port=$((10#$port))
    printf 'Límite máximo de usuarios/slots (1-100000): '
    IFS= read -r max_users || return 0
    if [[ ! "$max_users" =~ ^[0-9]{1,6}$ ]] || ((10#$max_users < 1 || 10#$max_users > 100000)); then
        printf '\nLímite inválido.\n'
        ui_pause
        return 1
    fi
    max_users=$((10#$max_users))
    if ! connections_require_storage_tools; then
        printf '\nSe requieren jq y flock.\n'
        ui_pause
        return 1
    fi
    if ! connections_lock fd; then
        ui_pause
        return 1
    fi
    if connections_port_in_use "$port"; then
        connections_unlock "$fd"
        printf '\nEl puerto ya está ocupado por un socket TCP/UDP del sistema.\n'
        ui_pause
        return 1
    fi
    if jq -e --argjson port "$port" '.[] | select(.port == $port)' "$CONNECTION_DATA_FILE" >/dev/null; then
        connections_unlock "$fd"
        printf '\nPuerto ya reservado en el registro.\n'
        ui_pause
        return 1
    fi
    id="conn-$(date +%s)-$$"
    created_at="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    if ! connections_atomic_update "$fd" --arg id "$id" --arg name "$name" --arg protocol_id "$protocol_id" --argjson port "$port" --argjson max_users "$max_users" --arg created_at "$created_at" '. + [{id:$id,name:$name,protocol_id:$protocol_id,port:$port,max_users:$max_users,state:"draft",runtime_applied:false,created_at:$created_at}]'; then
        connections_unlock "$fd"
        printf '\nError al guardar el registro.\n'
        ui_pause
        return 1
    fi
    connections_unlock "$fd"
    printf '\nConexión registrada como borrador.\nID: %s\nNombre: %s\nModalidad: %s\nPuerto: %s\nSlots: %s\n' "$id" "$name" "$protocol_id" "$port" "$max_users"
    printf '\nNo se aplicó ningún cambio a Xray ni al sistema.\n'
    ui_pause
}
connections_list() {
    local fd
    ui_clear
    ui_title "CONEXIONES REGISTRADAS"
    if ! connections_require_storage_tools || ! connections_lock fd; then
        printf '\nNo fue posible consultar el registro.\n'
        return 1
    fi
    if [[ "$(jq 'length' "$CONNECTION_DATA_FILE")" -eq 0 ]]; then
        printf '\nTodavía no hay conexiones registradas.\n'
        connections_unlock "$fd"
        return 0
    fi
    jq -r '.[] | "ID: \(.id)\nNombre: \(.name)\nModalidad: \(.protocol_id)\nPuerto: \(.port)\nSlots: \(.max_users)\nEstado: \(.state)\nAplicada a runtime: \(.runtime_applied)\n"' "$CONNECTION_DATA_FILE"
    connections_unlock "$fd"
}
connections_edit_draft() {
    local id name protocol_id port max_users fd state
    ui_clear
    ui_title "EDITAR CONEXIÓN - BORRADOR"
    printf '\nID exacto: '
    IFS= read -r id || return 0
    if ! connections_require_storage_tools || ! connections_lock fd; then
        printf '\nNo fue posible acceder al registro.\n'
        ui_pause
        return 1
    fi
    state="$(jq -r --arg id "$id" '.[] | select(.id == $id) | .state' "$CONNECTION_DATA_FILE")"
    if [[ "$state" != "draft" ]]; then
        connections_unlock "$fd"
        printf '\nNo existe o no está en estado draft; no se modifica.\n'
        ui_pause
        return 1
    fi
    printf 'Nuevo nombre (vacío conserva): '
    IFS= read -r name || {
        connections_unlock "$fd"
        return 0
    }
    printf 'Nuevo ID de modalidad (vacío conserva): '
    IFS= read -r protocol_id || {
        connections_unlock "$fd"
        return 0
    }
    printf 'Nuevo puerto (vacío conserva): '
    IFS= read -r port || {
        connections_unlock "$fd"
        return 0
    }
    printf 'Nuevo límite de slots (vacío conserva): '
    IFS= read -r max_users || {
        connections_unlock "$fd"
        return 0
    }
    name="$(connections_trim_name "$name")"
    if [[ -n "$name" && "${#name}" -gt 64 ]]; then
        connections_unlock "$fd"
        printf '\nNombre demasiado largo.\n'
        ui_pause
        return 1
    fi
    if [[ -n "$protocol_id" ]] && ! connections_valid_protocol "$protocol_id"; then
        connections_unlock "$fd"
        printf '\nModalidad no reconocida.\n'
        ui_pause
        return 1
    fi
    if [[ -n "$port" ]]; then
        if [[ ! "$port" =~ ^[0-9]{1,5}$ ]] || ((10#$port < 1 || 10#$port > 65535)); then
            connections_unlock "$fd"
            printf '\nPuerto inválido.\n'
            ui_pause
            return 1
        fi
        port=$((10#$port))
        if connections_port_in_use "$port"; then
            connections_unlock "$fd"
            printf '\nEl puerto está ocupado por un socket TCP/UDP del sistema.\n'
            ui_pause
            return 1
        fi
        if jq -e --arg id "$id" --argjson port "$port" '.[] | select(.id != $id and .port == $port)' "$CONNECTION_DATA_FILE" >/dev/null; then
            connections_unlock "$fd"
            printf '\nPuerto reservado por otra conexión.\n'
            ui_pause
            return 1
        fi
    fi
    if [[ -n "$max_users" ]]; then
        if [[ ! "$max_users" =~ ^[0-9]{1,6}$ ]] || ((10#$max_users < 1 || 10#$max_users > 100000)); then
            connections_unlock "$fd"
            printf '\nLímite inválido.\n'
            ui_pause
            return 1
        fi
        max_users=$((10#$max_users))
    fi
    if ! connections_atomic_update "$fd" --arg id "$id" --arg name "$name" --arg protocol_id "$protocol_id" --arg port "$port" --arg max_users "$max_users" 'map(if .id == $id and .state == "draft" then . + (if $name == "" then {} else {name:$name} end) + (if $protocol_id == "" then {} else {protocol_id:$protocol_id} end) + (if $port == "" then {} else {port:($port|tonumber)} end) + (if $max_users == "" then {} else {max_users:($max_users|tonumber)} end) else . end)'; then
        connections_unlock "$fd"
        printf '\nNo se pudo guardar la edición.\n'
        ui_pause
        return 1
    fi
    connections_unlock "$fd"
    printf '\nBorrador actualizado. Runtime sin cambios.\n'
    ui_pause
}
connections_delete_draft() {
    local id confirmation fd state
    ui_clear
    ui_title "ELIMINAR CONEXIÓN - BORRADOR"
    printf '\nID exacto: '
    IFS= read -r id || return 0
    if ! connections_require_storage_tools || ! connections_lock fd; then
        printf '\nNo fue posible acceder al registro.\n'
        ui_pause
        return 1
    fi
    state="$(jq -r --arg id "$id" '.[] | select(.id == $id) | .state' "$CONNECTION_DATA_FILE")"
    if [[ "$state" != "draft" ]]; then
        connections_unlock "$fd"
        printf '\nNo existe o no está en estado draft; no se elimina.\n'
        ui_pause
        return 1
    fi
    printf 'Para confirmar, escribe ELIMINAR: '
    IFS= read -r confirmation || {
        connections_unlock "$fd"
        return 0
    }
    if [[ "$confirmation" != "ELIMINAR" ]]; then
        connections_unlock "$fd"
        printf '\nOperación cancelada.\n'
        ui_pause
        return 0
    fi
    if ! connections_atomic_update "$fd" --arg id "$id" 'map(select(.id != $id))'; then
        connections_unlock "$fd"
        printf '\nNo se pudo eliminar el borrador.\n'
        ui_pause
        return 1
    fi
    connections_unlock "$fd"
    printf '\nBorrador eliminado. Xray y el sistema no fueron modificados.\n'
    ui_pause
}
