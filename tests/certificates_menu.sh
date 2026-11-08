#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/modules/certificates.sh"

ui_clear() { :; }
ui_title() { :; }
ui_pause() { :; }
MENU_CHOICE=0
ui_read_option() {
    local prompt="$1" destination="$2"
    printf -v "$destination" '%s' "$MENU_CHOICE"
}
ui_confirm() { return 1; }

certificates_read_domains <<< '  example.invalid, www.example.invalid  '
[[ "${#CERTIFICATES_DOMAINS[@]}" == 2 ]]
[[ "${CERTIFICATES_DOMAINS[0]}" == "example.invalid" ]]
[[ "${CERTIFICATES_DOMAINS[1]}" == "www.example.invalid" ]]
certificates_domain_args
[[ "${#CERTIFICATES_DOMAIN_ARGS[@]}" == 4 ]]
[[ "${CERTIFICATES_DOMAIN_ARGS[0]}" == "--domain" ]]
[[ "${CERTIFICATES_DOMAIN_ARGS[1]}" == "example.invalid" ]]

if certificates_read_domains <<< 'example.invalid,,www.example.invalid'; then
    printf 'ERROR: se aceptó un dominio vacío.\n' >&2
    exit 1
fi

MENU_CHOICE=0
certificates_menu

# El plan HTTP no debe recibir argumentos exclusivos de issue ni ejecutar Certbot al cancelar.
FAKEBIN="$ROOT/tests/.certificates-menu-fakebin"
export FAKEBIN
mkdir -p "$FAKEBIN"
trap 'rm -rf -- "$FAKEBIN"; rm -f -- "$ROOT/tests/.certbot-check-output" "$ROOT/tests/.certbot-apt-calls" "$ROOT/tests/.certbot-systemctl-calls" "$ROOT/tests/.certbot-preexisting-timer" "$ROOT/tests/.certbot-installed-timer" "$ROOT/tests/.certbot-confirm-log" "$ROOT/tests/.certificates-menu-args"' EXIT
cat >"$FAKEBIN/python3" <<'PYTHON'
#!/usr/bin/env bash
printf '%s\n' "$@" >"$CERTIFICATES_MENU_ARGS"
exit 0
PYTHON
cat >"$FAKEBIN/certbot" <<'CERTBOT'
#!/usr/bin/env bash
echo 'certbot 2.0.0 (fixture)'
CERTBOT
chmod 700 "$FAKEBIN/python3" "$FAKEBIN/certbot"
APP_ROOT="$ROOT"
CERTIFICATES_MENU_ARGS="$ROOT/tests/.certificates-menu-args"
export CERTIFICATES_MENU_ARGS
PATH="$FAKEBIN:$PATH"
export PATH
SYSTEMCTL_CALLS="$ROOT/tests/.certbot-systemctl-calls"
SYSTEMCTL_PREEXISTING="$ROOT/tests/.certbot-preexisting-timer"
SYSTEMCTL_INSTALLED_TIMER="$ROOT/tests/.certbot-installed-timer"
export SYSTEMCTL_CALLS SYSTEMCTL_PREEXISTING SYSTEMCTL_INSTALLED_TIMER
cat >"$FAKEBIN/systemctl" <<'SYSTEMCTL'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"$SYSTEMCTL_CALLS"
if [[ "$1" == is-enabled && "$3" == snap.certbot.renew.timer && -e "$SYSTEMCTL_PREEXISTING" ]]; then exit 0; fi
if [[ "$1" == is-enabled || "$1" == is-active ]]; then
    if [[ "$3" == certbot.timer && -e "$SYSTEMCTL_INSTALLED_TIMER" ]]; then exit 0; fi
    exit 1
fi
case "$1" in
    show) exit 0 ;;
    disable) rm -f "$SYSTEMCTL_INSTALLED_TIMER"; exit 0 ;;
    *) exit 1 ;;
esac
SYSTEMCTL
chmod 700 "$FAKEBIN/systemctl"
# La comprobación de Certbot ocurre antes de pedir dominio/correo.
CERTBOT_CHECK_OUTPUT="$ROOT/tests/.certbot-check-output"
export CERTBOT_CHECK_OUTPUT
cat >"$FAKEBIN/certbot" <<'CERTBOT'
#!/usr/bin/env bash
echo called >>"$CERTBOT_CHECK_OUTPUT"
echo 'certbot 2.0.0 (fixture)'
CERTBOT
chmod 700 "$FAKEBIN/certbot"
ui_confirm() { return 1; }
if ! certificates_ensure_certbot; then
    printf 'ERROR: Certbot disponible fue rechazado inesperadamente.\n' >&2
    exit 1
fi
[[ "$(wc -l <"$CERTBOT_CHECK_OUTPUT")" == 1 ]]
rm -f "$CERTBOT_CHECK_OUTPUT"
# Un Certbot ya instalado tampoco puede operar si un scheduler de renovación está activo.
touch "$SYSTEMCTL_PREEXISTING"
if certificates_ensure_certbot; then
    printf 'ERROR: se aceptó continuar con Certbot y un timer de renovación activo.\n' >&2
    exit 1
fi
rm -f "$SYSTEMCTL_PREEXISTING"

# Certbot ausente: solicita consentimiento; la instalación se simula con apt-get.
mv "$FAKEBIN/certbot" "$FAKEBIN/certbot.fixture"
hash -r
APT_CALLS="$ROOT/tests/.certbot-apt-calls"
export APT_CALLS
manager_lock_acquire() { printf 'locked\n' >>"$APT_CALLS"; printf -v "$2" '%s' 9; }
manager_lock_release() { printf 'released\n' >>"$APT_CALLS"; }
cat >"$FAKEBIN/apt-get" <<'APT'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"$APT_CALLS"
if [[ "$1" == install ]]; then
    touch "$SYSTEMCTL_INSTALLED_TIMER"
    cat >"$FAKEBIN/certbot" <<'CERTBOT'
#!/usr/bin/env bash
echo 'certbot 2.0.0 (installed fixture)'
CERTBOT
    chmod 700 "$FAKEBIN/certbot"
fi
APT
chmod 700 "$FAKEBIN/apt-get"
MANAGER_APT_GET="$FAKEBIN/apt-get"
export MANAGER_APT_GET
ui_confirm() { return 0; }
if ! certificates_ensure_certbot; then
    printf 'ERROR: la instalación fixture de Certbot no se verificó.\n' >&2
    exit 1
fi
grep -Fxq 'update' "$APT_CALLS"
grep -Fxq 'install -y --no-install-recommends certbot' "$APT_CALLS"
grep -Fxq 'disable --now certbot.timer' "$SYSTEMCTL_CALLS"
[[ ! -e "$SYSTEMCTL_INSTALLED_TIMER" ]]
rm -f "$APT_CALLS"
# Si ya existía un timer habilitado, el Manager no lo toca ni instala encima.
mv "$FAKEBIN/certbot" "$FAKEBIN/certbot.installed"
mv "$FAKEBIN/certbot.fixture" "$FAKEBIN/certbot"
mv "$FAKEBIN/certbot" "$FAKEBIN/certbot.fixture"
touch "$SYSTEMCTL_PREEXISTING"
: >"$APT_CALLS"
if certificates_ensure_certbot; then
    printf 'ERROR: se aceptó instalar sobre un certbot.timer preexistente.\n' >&2
    exit 1
fi
[[ ! -s "$APT_CALLS" ]]
rm -f "$SYSTEMCTL_PREEXISTING"
mv "$FAKEBIN/certbot.fixture" "$FAKEBIN/certbot"

MENU_CHOICE=1
ui_confirm() { return 1; }
printf 'example.invalid\nops@example.invalid\n203.0.113.10\n' | certificates_obtain_menu
 grep -Fxq 'plan' "$CERTIFICATES_MENU_ARGS"
 grep -Fxq -- '--method' "$CERTIFICATES_MENU_ARGS"
if grep -Fxq -- '--expected-address' "$CERTIFICATES_MENU_ARGS"; then
    printf 'ERROR: plan recibió --expected-address exclusivo de issue.\n' >&2
    exit 1
fi
if grep -Fxq 'issue' "$CERTIFICATES_MENU_ARGS"; then
    printf 'ERROR: se ejecutó issue después de cancelar.\n' >&2
    exit 1
fi
rm -f "$CERTIFICATES_MENU_ARGS"
printf '%s\n' 'OK: menú de certificados, captura, plan aislado y cancelación sin ACME.'

# Recorrido guiado: issue devuelve el request_id y la UI lo reutiliza para importar sin volver a pedir datos.
cat >"$FAKEBIN/python3" <<'PYTHON'
#!/usr/bin/env bash
if [[ "$1" == -c ]]; then exec /usr/bin/python3 "$@"; fi
printf '%s\n' "$@" >>"$CERTIFICATES_MENU_ARGS"
case "$2" in
    plan) printf '%s\n' '{"status":"planned","live_operation":false}' ;;
    issue) printf '%s\n' '{"status":"issued","certificate_request_id":"acme-0123456789abcdefabcd","cert_name":"xray-manager-fixture","exit_code":0}' ;;
    audit) printf '%s\n' '{"status":"audit","broken_references":[],"unsafe_entries":[],"orphan_secret_files":[],"orphan_managed_files":[]}' ;;
    import-certbot) printf '%s\n' '{"status":"imported","certificate_id":"cert-guided","revision":1}' ;;
    *) exit 1 ;;
esac
PYTHON
chmod 700 "$FAKEBIN/python3"
: >"$CERTIFICATES_MENU_ARGS"
MENU_CHOICE=1
ui_confirm() { return 0; }
printf 'example.invalid\nops@example.invalid\n203.0.113.10\n' | certificates_obtain_menu
grep -Fxq 'issue' "$CERTIFICATES_MENU_ARGS"
grep -Fxq 'import-certbot' "$CERTIFICATES_MENU_ARGS"
grep -Fxq 'acme-0123456789abcdefabcd' "$CERTIFICATES_MENU_ARGS"
grep -Fxq 'xray-manager-fixture' "$CERTIFICATES_MENU_ARGS"
grep -Fxq 'example.invalid' "$CERTIFICATES_MENU_ARGS"
printf '%s\n' 'OK: el flujo guiado reutiliza el request_id y el lineage emitido para importar tras una segunda confirmación.'

# La emisión y la importación requieren confirmaciones distintas; rechazar la segunda conserva el lineage emitido.
: >"$CERTIFICATES_MENU_ARGS"
MENU_CHOICE=1
CONFIRM_LOG="$ROOT/tests/.certbot-confirm-log"
export CONFIRM_LOG
: >"$CONFIRM_LOG"
ui_confirm() {
    printf 'confirm\n' >>"$CONFIRM_LOG"
    [[ "$(wc -l <"$CONFIRM_LOG")" -eq 1 ]]
}
printf 'example.invalid\nops@example.invalid\n203.0.113.10\n' | certificates_obtain_menu
[[ "$(wc -l <"$CONFIRM_LOG")" -eq 2 ]]
grep -Fxq 'issue' "$CERTIFICATES_MENU_ARGS"
if grep -Fxq 'import-certbot' "$CERTIFICATES_MENU_ARGS"; then
    printf 'ERROR: se importó el certificado sin la segunda confirmación.\n' >&2
    exit 1
fi
printf '%s\n' 'OK: rechazar la importación no deshace ni importa la solicitud ACME emitida.'

# El asistente VLESS fija el dominio del primer lanzamiento y mantiene DNS-01 manual.
: >"$CERTIFICATES_MENU_ARGS"
MENU_CHOICE=2
ui_confirm() { return 0; }
printf 'ops@example.invalid\n' | certificates_obtain_menu vless-ws-tls
grep -Fxq 'dns-01' "$CERTIFICATES_MENU_ARGS"
grep -Fxq 'pruebas.tvrc.me' "$CERTIFICATES_MENU_ARGS"
grep -Fxq 'import-certbot' "$CERTIFICATES_MENU_ARGS"
if grep -Fxq -- '--expected-address' "$CERTIFICATES_MENU_ARGS"; then
    printf 'ERROR: DNS-01 recibió un parámetro exclusivo de HTTP-01.\\n' >&2
    exit 1
fi
printf '%s\n' 'OK: el flujo VLESS-WS-TLS usa pruebas.tvrc.me y conserva DNS-01 manual.'

# Integración fixture: auditoría limpia, migración explícita y rollback confirmado.
cat >"$FAKEBIN/python3" <<'PYTHON'
#!/usr/bin/env bash
if [[ "${1:-}" == -c ]]; then exec /usr/bin/python3 "$@"; fi
printf '%s\n' "$@" >>"$CERTIFICATES_MENU_ARGS"
case "${2:-}" in
    audit)
        printf '%s\n' '{"status":"audit","broken_references":[],"unsafe_entries":[],"orphan_secret_files":[],"orphan_managed_files":[]}'
        ;;
    migrate-v1)
        printf '%s\n' '{"status":"migrated","schema_version":2}'
        ;;
    rollback)
        printf '%s\n' '{"status":"rolled_back","active_revision":1}'
        ;;
    *) exit 0 ;;
esac
PYTHON
chmod 700 "$FAKEBIN/python3"
ui_confirm() { return 0; }
certificates_migrate_menu
 grep -Fxq 'migrate-v1' "$CERTIFICATES_MENU_ARGS"
# La auditoría posterior se ejecuta después de migrar.
certificates_rollback_menu <<'INPUT'
cert-example123
1
INPUT
grep -Fxq 'rollback' "$CERTIFICATES_MENU_ARGS"
grep -Fxq -- '--certificate-id' "$CERTIFICATES_MENU_ARGS"
grep -Fxq 'cert-example123' "$CERTIFICATES_MENU_ARGS"
grep -Fxq -- '--revision' "$CERTIFICATES_MENU_ARGS"
grep -Fxq '1' "$CERTIFICATES_MENU_ARGS"
printf '%s\n' 'OK: menú schema v2 incluye auditoría previa/posterior, migración confirmada y rollback validado.'

# Rotación desde el menú transmite el ID existente y exige auditoría limpia.
cat >"$FAKEBIN/python3" <<'PYTHON'
#!/usr/bin/env bash
if [[ "${1:-}" == -c ]]; then exec /usr/bin/python3 "$@"; fi
printf '%s\n' "$@" >>"$CERTIFICATES_MENU_ARGS"
case "${2:-}" in
    audit) printf '%s\n' '{"status":"audit","broken_references":[],"unsafe_entries":[],"orphan_secret_files":[],"orphan_managed_files":[]}' ;;
    show) printf '%s\n' '{"status":"ok","certificate":{"certificate_id":"cert-existing"}}' ;;
    import-certbot) printf '%s\n' '{"status":"imported","certificate_id":"cert-existing","revision":2}' ;;
esac
PYTHON
chmod 700 "$FAKEBIN/python3"
: > "$CERTIFICATES_MENU_ARGS"
ui_confirm() { return 0; }
printf 'example.invalid\nops@example.invalid\nlineage-example\nacme-0123456789abcdefabcd\ncert-existing\n' | certificates_import_menu
grep -Fxq 'show' "$CERTIFICATES_MENU_ARGS"
grep -Fxq 'import-certbot' "$CERTIFICATES_MENU_ARGS"
grep -Fxq -- '--certificate-id' "$CERTIFICATES_MENU_ARGS"
grep -Fxq 'cert-existing' "$CERTIFICATES_MENU_ARGS"
printf '%s\n' 'OK: el menú de importación pasa el certificate_id explícito para rotación y mantiene la confirmación.'
