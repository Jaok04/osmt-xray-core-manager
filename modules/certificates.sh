#!/usr/bin/env bash

CERTIFICATES_DOMAINS=()

certificates_read_domains() {
    local raw domain
    CERTIFICATES_DOMAINS=()
    printf 'Dominios separados por coma: '
    IFS= read -r raw || return 1
    IFS=',' read -r -a CERTIFICATES_DOMAINS <<<"$raw"
    local -a normalized=()
    for domain in "${CERTIFICATES_DOMAINS[@]}"; do
        domain="${domain#"${domain%%[![:space:]]*}"}"
        domain="${domain%"${domain##*[![:space:]]}"}"
        [[ -n "$domain" ]] || {
            printf 'Dominio vacío; operación cancelada.\n'
            return 1
        }
        normalized+=("$domain")
    done
    CERTIFICATES_DOMAINS=("${normalized[@]}")
}

certificates_domain_args() {
    local domain
    CERTIFICATES_DOMAIN_ARGS=()
    for domain in "${CERTIFICATES_DOMAINS[@]}"; do
        CERTIFICATES_DOMAIN_ARGS+=(--domain "$domain")
    done
}

certificates_menu() {
    local option
    while true; do
        ui_clear
        ui_title "CERTIFICADOS SSL/TLS Y DOMINIOS"
        printf '\n  [1] Obtener certificado nuevo (ACME)\n'
        printf '  [2] Listar certificados del almacén central\n'
        printf '  [3] Importar lineage emitido por Certbot / rotar revisión\n'
        printf '  [4] Auditar integridad del almacén\n'
        printf '  [5] Migrar catálogo schema v1 a v2\n'
        printf '  [6] Activar una revisión anterior (rollback)\n'
        printf '  [0] Volver\n\n'
        ui_read_option "Selecciona una opción: " option || return 0
        case "$option" in
            1) certificates_obtain_menu || true ;;
            2) certificates_list_menu || true ;;
            3) certificates_import_menu || true ;;
            4) certificates_audit_menu || true ;;
            5) certificates_migrate_menu || true ;;
            6) certificates_rollback_menu || true ;;
            0) return 0 ;;
            *)
                printf '\nOpción no válida.\n'
                ui_pause
                ;;
        esac
    done
}

certificates_ensure_certbot() {
    local lifecycle_fd="" apt_get="${MANAGER_APT_GET:-apt-get}"

    if command -v certbot >/dev/null 2>&1; then
        if certbot --version; then
            return 0
        fi
        printf '\nCertbot está presente, pero no pudo ejecutarse. No se continuará con ACME.\n' >&2
        return 1
    fi

    printf '\nCertbot no está instalado. Es necesario para solicitar certificados ACME.\n'
    if ! ui_confirm "¿Deseas instalar Certbot desde los repositorios oficiales de Ubuntu?"; then
        printf '\nInstalación cancelada. No se inició ninguna solicitud ACME.\n'
        return 1
    fi
    if [[ "$EUID" -ne 0 ]]; then
        printf 'La instalación de Certbot requiere root. No se intentó autoelevar.\n' >&2
        return 1
    fi
    if ! command -v "$apt_get" >/dev/null 2>&1; then
        printf 'No se encontró apt-get; no se puede instalar Certbot en este sistema.\n' >&2
        return 1
    fi
    if [[ ! -r /etc/os-release ]] ||
        ! grep -Eiq '^(ID=ubuntu|ID_LIKE=.*ubuntu)' /etc/os-release; then
        printf 'La instalación automática de Certbot está habilitada únicamente para Ubuntu.\n' >&2
        return 1
    fi
    if ! manager_lock_acquire "${XRAY_MANAGER_LIFECYCLE_LOCK:-/run/lock/xray-manager-lifecycle.lock}" lifecycle_fd; then
        printf 'Hay otra operación de ciclo de vida del Manager en curso.\n' >&2
        return 1
    fi

    printf '\nSe actualizarán los índices APT y se instalará únicamente el paquete certbot.\n'
    if ! "$apt_get" update; then
        manager_lock_release "$lifecycle_fd"
        printf 'Falló apt-get update. Certbot no fue instalado.\n' >&2
        return 1
    fi
    if ! "$apt_get" install -y --no-install-recommends certbot; then
        manager_lock_release "$lifecycle_fd"
        printf 'Falló la instalación de Certbot. No se continuará con ACME.\n' >&2
        return 1
    fi
    manager_lock_release "$lifecycle_fd"
    hash -r

    if ! command -v certbot >/dev/null 2>&1 || ! certbot --version; then
        printf 'La instalación terminó, pero Certbot no superó la verificación posterior.\n' >&2
        return 1
    fi
    printf 'Certbot quedó instalado y verificado correctamente.\n'
}

certificates_obtain_menu() {
    local method_choice method email expected_address
    local -a args=() plan_args=()
    ui_clear
    ui_title "OBTENER CERTIFICADO ACME"
    if ! certificates_ensure_certbot; then
        ui_pause
        return 1
    fi
    ui_clear
    ui_title "OBTENER CERTIFICADO ACME"
    printf '\n  [1] HTTP-01 (Certbot standalone, puerto 80)\n'
    printf '  [2] DNS-01 (Certbot manual, registro TXT)\n'
    printf '  [0] Cancelar\n\n'
    ui_read_option "Método: " method_choice || return 0
    case "$method_choice" in
        1) method=http-01 ;;
        2) method=dns-01 ;;
        0) return 0 ;;
        *) printf '\nMétodo no válido.\n'; ui_pause; return 1 ;;
    esac
    certificates_read_domains || { ui_pause; return 1; }
    printf 'Correo de contacto ACME: '
    IFS= read -r email || return 1
    [[ -n "$email" ]] || { printf 'Correo obligatorio.\n'; ui_pause; return 1; }
    args=(--method "$method" --email "$email")
    certificates_domain_args
    args+=("${CERTIFICATES_DOMAIN_ARGS[@]}")
    plan_args=("${args[@]}")
    if [[ "$method" == http-01 ]]; then
        printf 'IP pública prevista del servidor (A/AAAA): '
        IFS= read -r expected_address || return 1
        [[ -n "$expected_address" ]] || { printf 'La IP prevista es obligatoria para HTTP-01.\n'; ui_pause; return 1; }
        args+=(--expected-address "$expected_address")
    fi
    ui_clear
    ui_title "REVISIÓN DE SOLICITUD ACME"
    printf '\nSe validará el formato de los dominios y se mostrará el plan. Los prerrequisitos se comprobarán antes de ejecutar Certbot.\n\n'
    if ! python3 "$APP_ROOT/scripts/certificate_acme.py" plan "${plan_args[@]}"; then
        ui_pause
        return 1
    fi
    printf '\nLa siguiente confirmación iniciará una solicitud real a la autoridad ACME.\n'
    if ! ui_confirm "¿Autorizas solicitar el certificado para los dominios indicados?"; then
        printf '\nSolicitud cancelada; no se ejecutó Certbot.\n'
        ui_pause
        return 0
    fi
    if python3 "$APP_ROOT/scripts/certificate_acme.py" issue "${args[@]}" --confirm-acme; then
        printf '\nLa solicitud ACME terminó. Revisa el estado y luego importa el lineage emitido.\n'
    else
        printf '\nLa solicitud ACME falló o quedó bloqueada. No se modificó el almacén central.\n'
    fi
    ui_pause
}

certificates_list_menu() {
    ui_clear
    ui_title "CERTIFICADOS REGISTRADOS"
    python3 "$APP_ROOT/scripts/certificate_store.py" list || printf '\nNo fue posible consultar el almacén central.\n'
    ui_pause
}

certificates_store_audit_clean() {
    local output
    if ! output="$(python3 "$APP_ROOT/scripts/certificate_store.py" audit 2>&1)"; then
        printf '%s\n' "$output" >&2
        return 1
    fi
    printf '%s\n' "$output"
    if ! printf '%s' "$output" | python3 -c 'import json,sys; d=json.load(sys.stdin); sys.exit(0 if not d.get("broken_references") and not d.get("unsafe_entries") else 1)'; then
        printf 'La auditoría detectó referencias rotas o entradas inseguras; operación bloqueada.\n' >&2
        return 1
    fi
    if printf '%s' "$output" | python3 -c 'import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get("orphan_secret_files") or d.get("orphan_managed_files") else 1)'; then
        printf 'ADVERTENCIA: existen archivos huérfanos; se conservarán, no se borrarán automáticamente.\n'
    fi
}

certificates_audit_menu() {
    ui_clear
    ui_title "AUDITORÍA DEL ALMACÉN TLS"
    certificates_store_audit_clean || printf '\nLa auditoría no quedó limpia. Revisa el detalle antes de continuar.\n'
    ui_pause
}

certificates_migrate_menu() {
    local output
    ui_clear
    ui_title "MIGRACIÓN DEL CATÁLOGO TLS V1 A V2"
    printf '\nLa migración crea copias versionadas de certificados managed y conmuta el catálogo atómicamente.\n'
    printf 'Los archivos legacy y secretos existentes se conservan; no se eliminan huérfanos.\n\n'
    if ! certificates_store_audit_clean; then
        ui_pause
        return 1
    fi
    if ! ui_confirm "¿Autorizas migrar ahora el catálogo de certificados v1 a v2?"; then
        printf '\nMigración cancelada; no se modificó el catálogo.\n'
        ui_pause
        return 0
    fi
    if output="$(python3 "$APP_ROOT/scripts/certificate_store.py" migrate-v1 2>&1)"; then
        printf '\n%s\n' "$output"
        printf '\nAuditoría posterior:\n'
        certificates_store_audit_clean || printf 'ADVERTENCIA: revisa la auditoría posterior.\n'
    else
        printf '\nMigración fallida; revisa el estado y los archivos huérfanos detectados.\n%s\n' "$output"
    fi
    ui_pause
}

certificates_rollback_menu() {
    local certificate_id revision output
    ui_clear
    ui_title "ROLLBACK DE CERTIFICADO TLS"
    certificates_store_audit_clean || { ui_pause; return 1; }
    printf '\nID central exacto (cert-...): '
    IFS= read -r certificate_id || return 1
    [[ "$certificate_id" =~ ^cert-[A-Za-z0-9][A-Za-z0-9_.-]{0,120}$ ]] || {
        printf 'ID de certificado no válido.\n'; ui_pause; return 1;
    }
    printf 'Número de revisión objetivo: '
    IFS= read -r revision || return 1
    [[ "$revision" =~ ^[1-9][0-9]{0,5}$ ]] || {
        printf 'Número de revisión no válido.\n'; ui_pause; return 1;
    }
    printf '\nSe verificará el blob cifrado, la pareja certificado/clave, huellas y vigencia antes de cambiar la revisión activa.\n'
    if ! ui_confirm "¿Autorizas activar ${certificate_id} revisión ${revision}?"; then
        printf '\nRollback cancelado; no se modificó el catálogo.\n'
        ui_pause
        return 0
    fi
    if output="$(python3 "$APP_ROOT/scripts/certificate_store.py" rollback --certificate-id "$certificate_id" --revision "$revision" 2>&1)"; then
        printf '\n%s\n' "$output"
        printf '\nAuditoría posterior:\n'
        certificates_store_audit_clean || printf 'ADVERTENCIA: revisa la auditoría posterior.\n'
    else
        printf '\nRollback rechazado; la revisión activa no se cambió.\n%s\n' "$output"
    fi
    ui_pause
}

certificates_import_menu() {
    local method_choice method email cert_name request_id certificate_id
    local -a args=()
    ui_clear
    ui_title "IMPORTAR CERTIFICADO EMITIDO POR CERTBOT"
    printf '\n  [1] HTTP-01\n'
    printf '  [2] DNS-01\n'
    printf '  [0] Cancelar\n\n'
    ui_read_option "Método de la solicitud: " method_choice || return 0
    case "$method_choice" in
        1) method=http-01 ;;
        2) method=dns-01 ;;
        0) return 0 ;;
        *) printf '\nMétodo no válido.\n'; ui_pause; return 1 ;;
    esac
    certificates_read_domains || { ui_pause; return 1; }
    printf 'Correo de contacto usado en la solicitud: '
    IFS= read -r email || return 1
    printf 'Nombre del lineage Certbot: '
    IFS= read -r cert_name || return 1
    printf 'ID de solicitud ACME (acme-...): '
    IFS= read -r request_id || return 1
    printf 'ID central existente para rotar (vacío = certificado nuevo): '
    IFS= read -r certificate_id || return 1
    certificates_domain_args
    args=(import-certbot --method "$method" --email "$email" --cert-name "$cert_name"
        --request-id "$request_id" "${CERTIFICATES_DOMAIN_ARGS[@]}")
    if [[ -n "$certificate_id" ]]; then
        [[ "$certificate_id" =~ ^cert-[A-Za-z0-9][A-Za-z0-9_.-]{0,120}$ ]] || {
            printf 'ID de certificado no válido.\n'; ui_pause; return 1;
        }
        if ! certificates_store_audit_clean; then
            ui_pause
            return 1
        fi
        if ! python3 "$APP_ROOT/scripts/certificate_store.py" show --certificate-id "$certificate_id"; then
            printf 'El certificate_id indicado no existe en el almacén central; no se iniciará una rotación.\n' >&2
            ui_pause
            return 1
        fi
        args+=(--certificate-id "$certificate_id")
    fi
    ui_clear
    ui_title "VALIDAR E IMPORTAR CERTIFICADO"
    printf '\nSe validará SAN, vigencia y correspondencia criptográfica antes de importar.\n'
    if [[ -n "$certificate_id" ]]; then
        printf 'Se creará una revisión managed inmutable para %s; las conexiones conservarán su certificate_id.\n' "$certificate_id"
        printf 'La revisión no se aplicará al runtime Xray automáticamente.\n\n'
    else
        printf 'Se creará un certificate_id nuevo; no se modifican conexiones Xray.\n\n'
    fi
    if ui_confirm "¿Deseas importar este lineage al almacén central?"; then
        if python3 "$APP_ROOT/scripts/certificate_acme.py" "${args[@]}"; then
            printf '\nCertificado importado y asociado a un certificate_id.\n'
        else
            printf '\nImportación rechazada. El almacén vigente permanece sin cambios.\n'
        fi
    else
        printf '\nImportación cancelada.\n'
    fi
    ui_pause
}
