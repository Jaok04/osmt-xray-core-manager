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
trap 'rm -rf -- "$FAKEBIN"; rm -f -- "$ROOT/tests/.certbot-check-output" "$ROOT/tests/.certbot-apt-calls" "$ROOT/tests/.certificates-menu-args"' EXIT
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
rm -f "$APT_CALLS"

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
