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
        printf '  [3] Importar lineage emitido por Certbot\n'
        printf '  [0] Volver\n\n'
        ui_read_option "Selecciona una opción: " option || return 0
        case "$option" in
            1) certificates_obtain_menu || true ;;
            2) certificates_list_menu || true ;;
            3) certificates_import_menu || true ;;
            0) return 0 ;;
            *)
                printf '\nOpción no válida.\n'
                ui_pause
                ;;
        esac
    done
}

certificates_obtain_menu() {
    local method_choice method email expected_address
    local -a args=() plan_args=()
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

certificates_import_menu() {
    local method_choice method email cert_name request_id
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
    certificates_domain_args
    args=(import-certbot --method "$method" --email "$email" --cert-name "$cert_name"
        --request-id "$request_id" "${CERTIFICATES_DOMAIN_ARGS[@]}")
    ui_clear
    ui_title "VALIDAR E IMPORTAR CERTIFICADO"
    printf '\nSe validará SAN, vigencia y correspondencia criptográfica antes de importar.\n'
    printf 'El certificado vigente no se sustituye ni se modifican conexiones Xray.\n\n'
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
