#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT
BASE="$TMP/certificates"
KEYS="$TMP/keys"
RUN="$TMP/run"
mkdir -m 700 -p "$BASE/managed" "$BASE/secrets" "$KEYS" "$RUN"
chmod 700 "$TMP" "$BASE" "$BASE/managed" "$BASE/secrets" "$KEYS" "$RUN"
openssl rand -out "$KEYS/master.key" 32
chmod 600 "$KEYS/master.key"
openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout "$TMP/tls.key" -out "$TMP/tls.pem" -days 2 \
    -subj '/CN=pruebas.tvrc.me' \
    -addext 'subjectAltName=DNS:pruebas.tvrc.me' >/dev/null 2>&1
chmod 600 "$TMP/tls.key" "$TMP/tls.pem"

export APP_ROOT="$ROOT"
export XRAY_MANAGER_CERTIFICATES_DIR="$BASE"
export XRAY_MANAGER_CERTIFICATES_CATALOG_FILE="$BASE/catalog.json"
export XRAY_MANAGER_CERTIFICATES_MANAGED_DIR="$BASE/managed"
export XRAY_MANAGER_CERTIFICATES_SECRETS_DIR="$BASE/secrets"
export XRAY_MANAGER_CERTIFICATES_LOCK="$RUN/certificate.lock"
export XRAY_MANAGER_MASTER_KEY_FILE="$KEYS/master.key"
export XRAY_MANAGER_INTEGRITY_LOCK="$RUN/integrity.lock"

source "$ROOT/modules/vless_assistant.sh"

ui_confirm() {
    local answer
    IFS= read -r answer || return 1
    [[ "$answer" == s ]]
}

GUIDED_MARKER="$TMP/guided-workflow"
certificates_obtain_menu() {
    [[ "$1" == vless-ws-tls ]] || return 1
    printf '%s\n' "$1" >"$GUIDED_MARKER"
    python3 "$ROOT/scripts/certificate_store.py" \
        --base "$BASE" --catalog "$BASE/catalog.json" \
        --managed-dir "$BASE/managed" --secrets-dir "$BASE/secrets" \
        --master-key "$KEYS/master.key" --lock "$RUN/certificate.lock" \
        import --storage-type managed --certificate-file "$TMP/tls.pem" \
        --private-key-file "$TMP/tls.key" --certificate-id cert-guided >/dev/null
}

selected="$(printf 's\n1\n' | connections_vless_assistant_select_certificate)"
[[ "$selected" == cert-guided ]]
[[ "$(cat "$GUIDED_MARKER")" == vless-ws-tls ]]
jq -e '.certificates | length == 1 and .[0].certificate_id == "cert-guided"' "$BASE/catalog.json" >/dev/null
printf '%s\n' 'PASS: sin certificado, el asistente inicia ACME guiado para VLESS-WS-TLS, vuelve al catálogo y permite seleccionar el certificado importado.'
