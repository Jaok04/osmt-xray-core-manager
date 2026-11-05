#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
BASE="$TMP/connections"; SECRETS="$TMP/secrets"; BACKUPS="$TMP/backups"; CERTS="$TMP/certificates"; KEYDIR="$TMP/keys"; KEY="$KEYDIR/master.key"
mkdir -m 700 "$BASE" "$BASE/configurations" "$SECRETS" "$BACKUPS" "$CERTS" "$CERTS/managed" "$CERTS/secrets" "$KEYDIR"
openssl rand -out "$KEY" 32; chmod 600 "$KEY"
openssl req -x509 -newkey rsa:2048 -nodes -keyout "$TMP/cert.key" -out "$TMP/cert.pem" -days 2 -subj '/CN=localhost' >/dev/null 2>&1
chmod 600 "$TMP/cert.key" "$TMP/cert.pem"
python3 "$ROOT/scripts/certificate_store.py" --base "$CERTS" --catalog "$CERTS/catalog.json" --managed-dir "$CERTS/managed" --secrets-dir "$CERTS/secrets" --master-key "$KEY" --lock "$TMP/cert.lock" import --storage-type managed --certificate-file "$TMP/cert.pem" --private-key-file "$TMP/cert.key" --certificate-id cert-backup-test >/dev/null
cat > "$BASE/connections.json" <<'JSON'
[{"id":"tls-backup","name":"TLS backup","protocol_id":"vless_tcp_tls","port":62100,"max_users":1,"state":"draft","runtime_applied":false,"configuration_schema_version":1,"configuration_revision":1,"configuration_ref":"configurations/tls-backup.r000001.json","secret_ref":null},{"id":"ws-tls-backup","name":"WS TLS backup","protocol_id":"vless_ws_tls","port":62101,"max_users":1,"state":"draft","runtime_applied":false,"configuration_schema_version":2,"configuration_revision":1,"configuration_ref":"configurations/ws-tls-backup.r000001.json","secret_ref":null}]
JSON
cat > "$BASE/configurations/tls-backup.r000001.json" <<'JSON'
{"schema_version":1,"connection_id":"tls-backup","protocol":"vless","mode_id":"vless_tcp_tls","transport":"raw","security":"tls","listen_address":"127.0.0.1","listen_port":62100,"transport_options":{},"security_options":{"certificate_id":"cert-backup-test"}}
JSON
cat > "$BASE/configurations/ws-tls-backup.r000001.json" <<'JSON'
{"schema_version":2,"connection_id":"ws-tls-backup","protocol":"vless","mode_id":"vless_ws_tls","transport":"websocket","security":"tls","listen_address":"127.0.0.1","listen_port":62101,"transport_options":{"path":"/backup","host":"ws.example.invalid"},"security_options":{"certificate_id":"cert-backup-test"},"client_options":{"tls_server_name":"sni.example.invalid"}}
JSON
chmod 600 "$BASE/connections.json" "$BASE/configurations/tls-backup.r000001.json" "$BASE/configurations/ws-tls-backup.r000001.json"
OUT="$(python3 "$ROOT/scripts/vless_backup.py" backup-data --base "$BASE" --secrets-dir "$SECRETS" --master-key "$KEY" --backups "$BACKUPS")"
ID="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["backup_id"])' "$OUT")"
DIR="$BACKUPS/data/$ID"
python3 "$ROOT/scripts/vless_backup.py" verify-data --backup-dir "$DIR" >/dev/null
python3 - "$ROOT/scripts/vless_backup.py" "$BASE" "$SECRETS" "$BACKUPS" "$KEY" "$DIR" "$TMP" <<'PY'
import importlib.util, pathlib, sys, types, builtins, json
script,base,secrets_dir,backups,key,backup_dir,tmp=sys.argv[1:]
spec=importlib.util.spec_from_file_location('vless_backup',script)
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
mod.LIFECYCLE=pathlib.Path(tmp)/'lifecycle.lock'; mod.INTEGRITY=pathlib.Path(tmp)/'integrity.lock'
pathlib.Path(base,'connections.json').write_text('[]\n'); pathlib.Path(base,'connections.json').chmod(0o600)
old_stdin=sys.stdin
class TTY:
    def isatty(self): return True
sys.stdin=TTY(); old_input=builtins.input; builtins.input=lambda prompt='': 'RESTAURAR'
try:
    result=mod.restore_data(types.SimpleNamespace(base=base,secrets_dir=secrets_dir,master_key=key,backups=backups,backup_dir=backup_dir))
finally:
    sys.stdin=old_stdin; builtins.input=old_input
assert result['status']=='restored' and result['vless_connections_restored']==2
restored=json.loads(pathlib.Path(base,'connections.json').read_text())
assert restored[0]['secret_ref'] is None
cfg=json.loads(pathlib.Path(base,'configurations/tls-backup.r000001.json').read_text())
assert cfg['security_options']=={'certificate_id':'cert-backup-test'}
ws_cfg=json.loads(pathlib.Path(base,'configurations/ws-tls-backup.r000001.json').read_text())
assert ws_cfg['transport_options']=={'path':'/backup','host':'ws.example.invalid'}
assert ws_cfg['client_options']=={'tls_server_name':'sni.example.invalid'}
manifest=json.loads((pathlib.Path(backup_dir)/'manifest.json').read_text())
assert manifest['external_dependencies']['tls_certificates']==[
    {'connection_id':'tls-backup','certificate_id':'cert-backup-test','source':'central_certificate_catalog','included':False},
    {'connection_id':'ws-tls-backup','certificate_id':'cert-backup-test','source':'central_certificate_catalog','included':False},
]
# Un restore no puede publicar una conexión que dependa de un certificado central ausente.
cert_catalog=pathlib.Path(base).parent/'certificates'/'catalog.json'
hidden=cert_catalog.with_suffix('.catalog-hidden')
original_catalog=cert_catalog.read_bytes(); original_connections=pathlib.Path(base,'connections.json').read_bytes()
cert_catalog.rename(hidden)
try:
    try:
        mod.restore_data(types.SimpleNamespace(base=base,secrets_dir=secrets_dir,master_key=key,backups=backups,backup_dir=backup_dir))
    except Exception:
        pass
    else:
        raise AssertionError('restore aceptó referencia sin catálogo central')
finally:
    hidden.rename(cert_catalog)
assert pathlib.Path(base,'connections.json').read_bytes()==original_connections
assert cert_catalog.read_bytes()==original_catalog
print('PASS: backup/restore conserva esquemas VLESS 1/2, Host/SNI, certificate_id central y rechaza catálogo ausente')
PY
