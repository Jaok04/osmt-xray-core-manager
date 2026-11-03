#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -m 700 "$TMP/bin" "$TMP/certificates" "$TMP/keys" "$TMP/runtime" "$TMP/vmess"
mkdir -m 700 "$TMP/certificates/managed" "$TMP/certificates/secrets"
head -c 32 /dev/urandom >"$TMP/keys/master.key"; chmod 600 "$TMP/keys/master.key"
openssl req -x509 -newkey rsa:2048 -nodes -keyout "$TMP/tls.key" -out "$TMP/tls.crt" -days 1 -subj '/CN=assistant.test.invalid' >/dev/null 2>&1
chmod 600 "$TMP/tls.key"; chmod 644 "$TMP/tls.crt"
chgrp 65534 "$TMP/runtime"; chmod 750 "$TMP/runtime"
python3 "$ROOT/scripts/certificate_store.py" --base "$TMP/certificates" --catalog "$TMP/certificates/catalog.json" --managed-dir "$TMP/certificates/managed" --secrets-dir "$TMP/certificates/secrets" --master-key "$TMP/keys/master.key" --lock "$TMP/certificates/catalog.lock" import --storage-type managed --certificate-file "$TMP/tls.crt" --private-key-file "$TMP/tls.key" --certificate-id cert-assistant-test >"$TMP/cert-import.json"
cat >"$TMP/connections.json" <<'JSON'
[{"id":"vmess-tls-restore","name":"VMess TLS restore","protocol_id":"vmess_tcp_tls","port":64101,"max_users":2,"state":"draft","runtime_applied":false}]
JSON
chmod 600 "$TMP/connections.json"
printf '%s\n' '[{"id":"123e4567-e89b-42d3-a456-426614174000","level":0,"email":"restore@test.invalid"}]' >"$TMP/users.json"
source "$ROOT/modules/vmess_model.sh"
vmess_model_build vmess-tls-restore vmess_tcp_tls 127.0.0.1 64101 "$TMP/users.json" >"$TMP/model.json"
jq -n --arg certificate_id cert-assistant-test '{certificate_id:$certificate_id}' >"$TMP/options.json"
python3 "$ROOT/scripts/vmess_prepare_config.py" --model "$TMP/model.json" --options "$TMP/options.json" --output "$TMP/prepared.json" >"$TMP/meta.json"
python3 "$ROOT/scripts/vmess_config_store.py" store --connection-id vmess-tls-restore --input "$TMP/prepared.json" --base "$TMP/vmess" --catalog "$TMP/connections.json" --lock "$TMP/integrity.lock" --secrets-dir "$TMP/vmess/secrets" --master-key "$TMP/keys/master.key" --certificate-catalog "$TMP/certificates/catalog.json" >/dev/null

cat >"$TMP/bin/python3" <<'MOCKPY'
#!/usr/bin/env bash
set -Eeuo pipefail
if [[ "${1:-}" == "$APP_ROOT/scripts/certificate_resolver.py" ]]; then
    shift
    action=''; runtime=''; connection=''; certificate=''; lease=''
    while (($#)); do
        case "$1" in
            prepare|cleanup) action="$1"; shift ;;
            --runtime-root|--connection-id|--certificate-id|--lease-id)
                flag="$1"; value="$2"; shift 2
                case "$flag" in
                    --runtime-root) runtime="$value" ;;
                    --connection-id) connection="$value" ;;
                    --certificate-id) certificate="$value" ;;
                    --lease-id) lease="$value" ;;
                esac
                ;;
            *) shift ;;
        esac
    done
    if [[ "$action" == prepare ]]; then
        lease=resolve-11111111111111111111111111111111
        dir="$runtime/$lease"
        mkdir "$dir"; chgrp 65534 "$dir"; chmod 750 "$dir"
        cp "$MOCK_CERTIFICATE" "$dir/certificate.pem"
        cp "$MOCK_PRIVATE_KEY" "$dir/private-key.pem"
        chgrp 65534 "$dir/certificate.pem" "$dir/private-key.pem"
        chmod 640 "$dir/certificate.pem" "$dir/private-key.pem"
        jq -n --arg lease_id "$lease" --arg connection_id "$connection" --arg certificate_id "$certificate" '{lease_id:$lease_id,connection_id:$connection_id,protocol:"vmess",certificate_id:$certificate_id,certificate_revision:1,certificate_fingerprint_sha256:("a"*64),service_uid:1,service_gid:65534}' >"$dir/manifest.json"
        chgrp 65534 "$dir/manifest.json"; chmod 640 "$dir/manifest.json"
        jq -n --arg lease_id "$lease" --arg cert "$dir/certificate.pem" --arg key "$dir/private-key.pem" '{status:"prepared",lease_id:$lease_id,certificate_file:$cert,key_file:$key}'
        exit 0
    elif [[ "$action" == cleanup ]]; then
        rm -rf -- "$runtime/$lease"
        printf '{"status":"cleaned"}\n'
        exit 0
    fi
    exit 2
fi
exec /usr/bin/python3 "$@"
MOCKPY
chmod 700 "$TMP/bin/python3"
cat >"$TMP/xray" <<'XRAY'
#!/usr/bin/env bash
[[ "$1" == run && "$2" == -test && "$3" == -config && -s "$4" ]]
[[ "${MOCK_XRAY_FAIL:-0}" != 1 ]]
XRAY
chmod 700 "$TMP/xray"
export APP_ROOT="$ROOT" CONNECTION_DATA_FILE="$TMP/connections.json" CONNECTION_LOCK="$TMP/integrity.lock"
export XRAY_MANAGER_VMESS_DIR="$TMP/vmess" XRAY_MANAGER_VMESS_SECRETS_DIR="$TMP/vmess/secrets"
export XRAY_MANAGER_MASTER_KEY_FILE="$TMP/keys/master.key" XRAY_MANAGER_CERTIFICATES_CATALOG_FILE="$TMP/certificates/catalog.json"
export XRAY_MANAGER_CERTIFICATES_RUNTIME_DIR="$TMP/runtime" XRAY_VALIDATION_BINARY="$TMP/xray"
export MOCK_CERTIFICATE="$TMP/tls.crt" MOCK_PRIVATE_KEY="$TMP/tls.key"
export PATH="$TMP/bin:$PATH"
source "$ROOT/modules/vmess_xray_26_10_31.sh"
source "$ROOT/modules/vmess_assistant.sh"
ui_pause() { :; }
connections_vmess_assistant_restore vmess-tls-restore vmess_tcp_tls >"$TMP/restore-success.log"
[[ -z "$(find "$TMP/runtime" -mindepth 1 -maxdepth 1 -print -quit)" ]]
grep -F 'recuperada y validada' "$TMP/restore-success.log" >/dev/null
echo 'PASS: recuperación TLS central prepara lease, valida configuración y limpia tras éxito'
if MOCK_XRAY_FAIL=1 connections_vmess_assistant_restore vmess-tls-restore vmess_tcp_tls >"$TMP/restore-failure.log" 2>&1; then
    echo 'ERROR: restauración debe fallar si Xray rechaza el borrador.' >&2
    exit 1
fi
[[ -z "$(find "$TMP/runtime" -mindepth 1 -maxdepth 1 -print -quit)" ]]
echo 'PASS: recuperación TLS central limpia lease también cuando Xray falla'
