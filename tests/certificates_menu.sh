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
mkdir -p "$FAKEBIN"
trap 'rm -rf -- "$FAKEBIN"' EXIT
cat >"$FAKEBIN/python3" <<'PYTHON'
#!/usr/bin/env bash
printf '%s\n' "$@" >"$CERTIFICATES_MENU_ARGS"
exit 0
PYTHON
chmod 700 "$FAKEBIN/python3"
APP_ROOT="$ROOT"
CERTIFICATES_MENU_ARGS="$ROOT/tests/.certificates-menu-args"
export CERTIFICATES_MENU_ARGS
PATH="$FAKEBIN:$PATH"
export PATH
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
