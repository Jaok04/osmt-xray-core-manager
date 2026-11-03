#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
BASE="$TMP/connections"
mkdir -m 700 "$BASE"
mkdir -m 700 "$BASE/secrets"
mkdir -m 700 "$TMP/run" "$TMP/certificates" "$TMP/certificates/managed" "$TMP/certificates/secrets"
CAT="$BASE/connections.json"
LOCK="$TMP/run/integrity.lock"
printf '%s\n' '[{"id":"conn-test","name":"Test","protocol_id":"vless_ws","port":62001,"max_users":2,"state":"draft","runtime_applied":false,"created_at":"2026-11-02T00:00:00Z"}]' >"$CAT"
chmod 600 "$CAT"
cat >"$TMP/config.json" <<'JSON'
{"schema_version":1,"connection_id":"conn-test","protocol":"vless","mode_id":"vless_ws","transport":"websocket","security":"none","listen_address":"127.0.0.1","listen_port":62001,"transport_options":{"path":"/ws"},"security_options":{}}
JSON
chmod 600 "$TMP/config.json"
openssl rand -out "$TMP/master.key" 32
chmod 600 "$TMP/master.key"
openssl req -x509 -newkey rsa:2048 -nodes -keyout "$TMP/cert.key" -out "$TMP/cert.pem" -days 2 -subj '/CN=localhost' >/dev/null 2>&1
chmod 600 "$TMP/cert.key" "$TMP/cert.pem"
python3 "$ROOT/scripts/certificate_store.py" --base "$TMP/certificates" --catalog "$TMP/certificates/catalog.json" --managed-dir "$TMP/certificates/managed" --secrets-dir "$TMP/certificates/secrets" --master-key "$TMP/master.key" --lock "$TMP/run/certificate.lock" import --storage-type managed --certificate-file "$TMP/cert.pem" --private-key-file "$TMP/cert.key" --certificate-id cert-store-test >/dev/null
store() { python3 "$ROOT/scripts/vless_config_store.py" "$@" --base "$BASE" --catalog "$CAT" --lock "$LOCK" --secrets-dir "$BASE/secrets" --master-key "$TMP/master.key" --certificate-catalog "$TMP/certificates/catalog.json"; }
store store --connection-id conn-test --input "$TMP/config.json" >"$TMP/store.out"
jq -e '.status == "stored" and .revision == 1 and .state == "draft" and .runtime_applied == false' "$TMP/store.out" >/dev/null
jq -e '.[0].configuration_schema_version == 1 and .[0].configuration_revision == 1 and .[0].configuration_ref == "configurations/conn-test.r000001.json" and .[0].state == "draft" and .[0].runtime_applied == false' "$CAT" >/dev/null
store read --connection-id conn-test >"$TMP/read.out"
jq -e '.configuration.transport_options.path == "/ws"' "$TMP/read.out" >/dev/null
# TLS centralizado: solo certificate_id en la revisión; ningún blob por conexión.
jq '. + [{"id":"tls-central","name":"TLS central","protocol_id":"vless_tcp_tls","port":62004,"max_users":1,"state":"draft","runtime_applied":false}]' "$CAT" >"$TMP/catalog.next"
mv "$TMP/catalog.next" "$CAT"; chmod 600 "$CAT"
cat >"$TMP/tls-central.json" <<'JSON'
{"schema_version":1,"connection_id":"tls-central","protocol":"vless","mode_id":"vless_tcp_tls","transport":"raw","security":"tls","listen_address":"127.0.0.1","listen_port":62004,"transport_options":{},"security_options":{"certificate_id":"cert-store-test"}}
JSON
chmod 600 "$TMP/tls-central.json"
store store --connection-id tls-central --input "$TMP/tls-central.json" >"$TMP/tls-store.json"
jq -e '.secret_ref == null and .status == "stored"' "$TMP/tls-store.json" >/dev/null
jq -e '.[1].secret_ref == null' "$CAT" >/dev/null
jq -e '.security_options == {certificate_id:"cert-store-test"}' "$BASE/configurations/tls-central.r000001.json" >/dev/null
[[ ! -e "$BASE/secrets/tls-central.r000001.bin" ]]
store read --connection-id tls-central >"$TMP/tls-read.json"
jq -e '.configuration.security_options.certificate_id == "cert-store-test" and .secret_written == false' "$TMP/tls-read.json" >/dev/null
if store store --connection-id tls-central --input "$TMP/tls-central.json" --secret-input "$TMP/cert.key" --secret-type tls_private_key >/dev/null 2>&1; then
	echo 'ERROR: TLS central aceptó secreto privado por conexión.' >&2; exit 1
fi
jq '.security_options.certificate_id = "cert-does-not-exist"' "$TMP/tls-central.json" >"$TMP/tls-invalid.json"
if store store --connection-id tls-central --input "$TMP/tls-invalid.json" >/dev/null 2>&1; then
	echo 'ERROR: TLS central aceptó un certificado inexistente.' >&2; exit 1
fi
# Segunda revisión inmutable; primera queda huérfana después de cambiar referencia.
store store --connection-id conn-test --input "$TMP/config.json" >/dev/null
store audit >"$TMP/audit.out"
jq -e '.broken_references == [] and (.orphan_files | length) == 1 and .automatic_deletion == false' "$TMP/audit.out" >/dev/null
# Versión desconocida y configuración con campo inesperado fallan sin publicar referencia.
jq '.schema_version = 99' "$TMP/config.json" >"$TMP/bad.json"
if store store --connection-id conn-test --input "$TMP/bad.json" >/dev/null 2>&1; then
	echo 'ERROR: aceptó versión desconocida' >&2
	exit 1
fi
jq '.unexpected = true' "$TMP/config.json" >"$TMP/bad.json"
if store store --connection-id conn-test --input "$TMP/bad.json" >/dev/null 2>&1; then
	echo 'ERROR: aceptó campo desconocido' >&2
	exit 1
fi
# Referencia rota detectada, sin borrar datos.
jq '.[0].configuration_ref = "configurations/missing.r000001.json"' "$CAT" >"$TMP/catbad.json"
cp "$TMP/catbad.json" "$CAT"
store audit >"$TMP/audit-broken.out"
jq -e '(.broken_references | length) == 1 and .automatic_deletion == false' "$TMP/audit-broken.out" >/dev/null
# ID traversal rechazado.
if store read --connection-id '../escape' >/dev/null 2>&1; then
	echo 'ERROR: aceptó ID traversal' >&2
	exit 1
fi
printf 'OK: almacén VLESS versionado, lecturas, revisiones, huérfanos, referencias rotas y fail-closed.\n'
# Simular interrupción antes de publicar el catálogo: queda un huérfano, sin referencia parcial.
mkdir -m 700 "$TMP/fault-base"
mkdir -m 700 "$TMP/fault-base/configurations"
mkdir -m 700 "$TMP/fault-base/secrets"
mkdir -m 700 "$TMP/fault-run"
printf '%s\n' '[{"id":"fault-1","name":"Fault","protocol_id":"vless_ws","port":62002,"max_users":1,"state":"draft","runtime_applied":false,"created_at":"2026-11-02T00:00:00Z"}]' >"$TMP/fault-base/connections.json"
chmod 600 "$TMP/fault-base/connections.json"
cat >"$TMP/fault-config.json" <<'JSON'
{"schema_version":1,"connection_id":"fault-1","protocol":"vless","mode_id":"vless_ws","transport":"websocket","security":"none","listen_address":"127.0.0.1","listen_port":62002,"transport_options":{"path":"/ws"},"security_options":{}}
JSON
chmod 600 "$TMP/fault-config.json"
PYTHONPATH="$ROOT/scripts" python3 - "$TMP" <<'PY'
import argparse, json, sys
from pathlib import Path
import vless_config_store as store
root = Path(sys.argv[1]); catalog = root/'fault-base/connections.json'
original = store.atomic_write
def injected(path, data):
    if Path(path) == catalog:
        raise OSError('fallo simulado antes de publicar catálogo')
    return original(path, data)
store.atomic_write = injected
args = argparse.Namespace(action='store', base=str(root/'fault-base'), catalog=str(catalog), lock=str(root/'fault-run/integrity.lock'), connection_id='fault-1', input=str(root/'fault-config.json'), secrets_dir=str(root/'fault-base/secrets'), master_key=str(root/'fault-master.key'), secret_input=None, secret_type=None, secret_output=None)
try:
    store.run(args)
except OSError:
    pass
else:
    raise SystemExit('el fallo inyectado no fue propagado')
entry = json.loads(catalog.read_text())[0]
assert 'configuration_ref' not in entry
assert (root/'fault-base/configurations/fault-1.r000001.json').is_file()
print('OK: fallo antes de publicar catálogo deja solo un archivo huérfano detectable.')
PY
# Dos escritores concurrentes comparten el bloqueo y reciben revisiones distintas.
mkdir -m 700 "$TMP/race-base"
mkdir -m 700 "$TMP/race-base/configurations"
mkdir -m 700 "$TMP/race-base/secrets"
mkdir -m 700 "$TMP/race-run"
printf '%s\n' '[{"id":"race-1","name":"Race","protocol_id":"vless_ws","port":62003,"max_users":1,"state":"draft","runtime_applied":false,"created_at":"2026-11-02T00:00:00Z"}]' >"$TMP/race-base/connections.json"
chmod 600 "$TMP/race-base/connections.json"
sed 's/conn-test/race-1/g; s/62001/62003/g' "$TMP/config.json" >"$TMP/race-config.json"
chmod 600 "$TMP/race-config.json"
store_race() { python3 "$ROOT/scripts/vless_config_store.py" store --connection-id race-1 --input "$TMP/race-config.json" --base "$TMP/race-base" --catalog "$TMP/race-base/connections.json" --lock "$TMP/race-run/integrity.lock" --secrets-dir "$TMP/race-base/secrets" --master-key "$TMP/race-master.key"; }
store_race >"$TMP/race1.out" &
p1=$!
store_race >"$TMP/race2.out" &
p2=$!
wait "$p1"
wait "$p2"
jq -e '.[0].configuration_revision == 2 and .[0].configuration_ref == "configurations/race-1.r000002.json"' "$TMP/race-base/connections.json" >/dev/null
[[ -f "$TMP/race-base/configurations/race-1.r000001.json" && -f "$TMP/race-base/configurations/race-1.r000002.json" ]]
