#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT
chmod 700 "$TMP"
CERT_BASE="$TMP/certificates"
MANAGED="$CERT_BASE/managed"
CERT_SECRETS="$CERT_BASE/secrets"
CERT_CATALOG="$CERT_BASE/catalog.json"
CERT_LOCK="$CERT_BASE/catalog.lock"
KEYDIR="$TMP/keys"
MASTER="$KEYDIR/master.key"
CONN_BASE="$TMP/connections"
VMESS_BASE="$TMP/vmess"
RUN_BASE="$TMP/run"
LOCK_DIR="$RUN_BASE/locks"
mkdir -m 700 "$CERT_BASE" "$MANAGED" "$CERT_SECRETS" "$KEYDIR" "$CONN_BASE" "$VMESS_BASE" "$RUN_BASE" "$LOCK_DIR"
mkdir -m 700 "$CONN_BASE/configurations" "$VMESS_BASE/configurations"
head -c 32 /dev/urandom >"$MASTER"; chmod 600 "$MASTER"
openssl req -x509 -newkey rsa:2048 -nodes -keyout "$TMP/private.pem" -out "$TMP/certificate.pem" -days 2 -subj "/CN=resolver.test.invalid" -addext "subjectAltName=DNS:resolver.test.invalid" >/dev/null 2>&1
chmod 600 "$TMP/private.pem"; chmod 644 "$TMP/certificate.pem"
python3 "$ROOT/scripts/certificate_store.py" --base "$CERT_BASE" --catalog "$CERT_CATALOG" --managed-dir "$MANAGED" --secrets-dir "$CERT_SECRETS" --master-key "$MASTER" --lock "$CERT_LOCK" import --storage-type managed --certificate-file "$TMP/certificate.pem" --private-key-file "$TMP/private.pem" --certificate-id cert-resolver >/dev/null
openssl req -x509 -newkey rsa:2048 -nodes -keyout "$TMP/private-r2.pem" -out "$TMP/certificate-r2.pem" -days 2 -subj "/CN=resolver-r2.test.invalid" -addext "subjectAltName=DNS:resolver-r2.test.invalid" >/dev/null 2>&1
chmod 600 "$TMP/private-r2.pem"; chmod 644 "$TMP/certificate-r2.pem"
python3 "$ROOT/scripts/certificate_store.py" --base "$CERT_BASE" --catalog "$CERT_CATALOG" --managed-dir "$MANAGED" --secrets-dir "$CERT_SECRETS" --master-key "$MASTER" --lock "$CERT_LOCK" import --storage-type managed --certificate-file "$TMP/certificate-r2.pem" --private-key-file "$TMP/private-r2.pem" --certificate-id cert-resolver >/dev/null
openssl req -x509 -newkey rsa:2048 -nodes -keyout "$TMP/reference-key.pem" -out "$TMP/reference-cert.pem" -days 2 -subj "/CN=reference-resolver.test.invalid" -addext "subjectAltName=DNS:reference-resolver.test.invalid" >/dev/null 2>&1
chmod 600 "$TMP/reference-key.pem"; chmod 644 "$TMP/reference-cert.pem"
python3 "$ROOT/scripts/certificate_store.py" --base "$CERT_BASE" --catalog "$CERT_CATALOG" --managed-dir "$MANAGED" --secrets-dir "$CERT_SECRETS" --master-key "$MASTER" --lock "$CERT_LOCK" import --storage-type reference --certificate-file "$TMP/reference-cert.pem" --private-key-file "$TMP/reference-key.pem" --certificate-id cert-reference >/dev/null
printf '%s\n' '[{"id":"vless-authorized","name":"VLESS authorized","protocol_id":"vless_ws_tls","port":63001,"max_users":1,"state":"draft","runtime_applied":false,"configuration_schema_version":1,"configuration_revision":1,"configuration_ref":"configurations/vless-authorized.r000001.json"},{"id":"vmess-authorized","name":"VMess authorized","protocol_id":"vmess_ws_tls","port":63002,"max_users":1,"state":"draft","runtime_applied":false,"vmess_configuration_schema_version":1,"vmess_configuration_revision":1,"vmess_configuration_ref":"configurations/vmess-authorized.r000001.json"},{"id":"vless-reference","name":"VLESS reference","protocol_id":"vless_ws_tls","port":63003,"max_users":1,"state":"draft","runtime_applied":false,"configuration_schema_version":1,"configuration_revision":1,"configuration_ref":"configurations/vless-reference.r000001.json"}]' >"$CONN_BASE/connections.json"
chmod 600 "$CONN_BASE/connections.json"
python3 - "$CONN_BASE" "$VMESS_BASE" <<'PY'
import json,pathlib,sys
v=pathlib.Path(sys.argv[1])/'configurations'/'vless-authorized.r000001.json'
vr=pathlib.Path(sys.argv[1])/'configurations'/'vless-reference.r000001.json'
m=pathlib.Path(sys.argv[2])/'configurations'/'vmess-authorized.r000001.json'
base={'schema_version':1,'protocol':'vless','mode_id':'vless_ws_tls','transport':'websocket','security':'tls','listen_address':'0.0.0.0','listen_port':63001,'transport_options':{'path':'/ws'},'security_options':{'certificate_id':'cert-resolver'}}
v.write_text(json.dumps(base|{'connection_id':'vless-authorized'},separators=(',',':'))+'\n'); v.chmod(0o600)
vr.write_text(json.dumps(base|{'connection_id':'vless-reference','listen_port':63003,'security_options':{'certificate_id':'cert-reference'}},separators=(',',':'))+'\n'); vr.chmod(0o600)
base={'schema_version':1,'protocol':'vmess','mode_id':'vmess_ws_tls','transport':'websocket','security':'tls','listen_address':'0.0.0.0','listen_port':63002,'transport_options':{'path':'/ws','host':''},'security_options':{'certificate_id':'cert-resolver'},'users':[]}
m.write_text(json.dumps(base|{'connection_id':'vmess-authorized'},separators=(',',':'))+'\n'); m.chmod(0o600)
PY
python3 - "$ROOT/scripts" "$TMP" <<'PY'
import json,pathlib,sys
sys.path.insert(0,sys.argv[1])
import certificate_resolver as r
tmp=pathlib.Path(sys.argv[2])
kw=dict(
 connections_catalog=tmp/'connections/connections.json',
 connections_base=tmp/'connections', vmess_base=tmp/'vmess',
 connection_lock=tmp/'run/locks/connections.lock',
 certificate_catalog=tmp/'certificates/catalog.json',
 certificate_base=tmp/'certificates', managed_dir=tmp/'certificates/managed',
 certificate_secrets_dir=tmp/'certificates/secrets',
 certificate_lock=tmp/'certificates/catalog.lock',
 master_key_file=tmp/'keys/master.key', runtime_root=tmp/'run/certificates',
 service_uid=1, service_gid=1,
)
for cid, certid in (('vless-authorized','cert-resolver'),('vmess-authorized','cert-resolver'),('vless-reference','cert-reference')):
 result=r.prepare(connection_id=cid,certificate_id=certid,**kw)
 assert result['status']=='prepared' and result['protocol']==cid.split('-')[0]
 if cid=='vless-authorized':
  manifest=json.loads((pathlib.Path(result['certificate_file']).parent/'manifest.json').read_text())
  assert manifest['certificate_revision']==2
 cert=pathlib.Path(result['certificate_file']); key=pathlib.Path(result['key_file'])
 assert cert.read_bytes().startswith(b'-----BEGIN CERTIFICATE-----')
 assert key.read_bytes().startswith(b'-----BEGIN PRIVATE KEY-----')
 for p in (cert,key):
  st=p.stat(); assert st.st_uid==0 and st.st_gid==1 and st.st_mode & 0o777==0o640
 d=cert.parent; st=d.stat(); assert st.st_uid==0 and st.st_gid==1 and st.st_mode & 0o777==0o750
 assert r.cleanup(kw['runtime_root'],result['lease_id'],1)['status']=='cleaned'
 assert not d.exists()
try:
 r.prepare(connection_id='vless-authorized',certificate_id='cert-other',**kw)
except r.ResolverError as exc:
 assert 'autorizada' in str(exc)
else: raise AssertionError('accepted unauthorized certificate id')
cat=kw['connections_catalog']; data=json.loads(cat.read_text()); data[0]['state']='draft'; cat.write_text(json.dumps(data)+'\n'); cat.chmod(0o600)
config=kw['connections_base']/'configurations/vless-authorized.r000001.json'
obj=json.loads(config.read_text()); obj['security_options']={'certificate_id':'cert-other'}
config.write_text(json.dumps(obj)+'\n'); config.chmod(0o600)
try:
 r.prepare(connection_id='vless-authorized',certificate_id='cert-resolver',**kw)
except r.ResolverError: pass
else: raise AssertionError('accepted mismatched connection association')
data[0]['protocol_id']='wireguard'; cat.write_text(json.dumps(data)+'\n'); cat.chmod(0o600)
try:
 r.prepare(connection_id='vless-authorized',certificate_id='cert-resolver',**kw)
except r.ResolverError: pass
else: raise AssertionError('accepted unsupported protocol')
# Catalog SAN metadata must be checked against the actual PEM, not trusted alone.
# Restore the source fixture after the unsupported-protocol negative case.
conn_catalog=kw['connections_catalog']
conn_data=json.loads(conn_catalog.read_text())
conn_data[0]['protocol_id']='vless_ws_tls'
conn_catalog.write_text(json.dumps(conn_data)+'\n'); conn_catalog.chmod(0o600)
conn_config=kw['connections_base']/'configurations/vless-authorized.r000001.json'
conn_obj=json.loads(conn_config.read_text())
conn_obj['security_options']={'certificate_id':'cert-resolver'}
conn_config.write_text(json.dumps(conn_obj)+'\n'); conn_config.chmod(0o600)
cat=kw['certificate_catalog']
catalog=json.loads(cat.read_text())
record=next(x for x in catalog['certificates'] if x['certificate_id']=='cert-resolver')
record['sans']=['forged.test.invalid']
if 'revisions' in record:
    active=next(x for x in record['revisions'] if x['revision']==record['active_revision'])
    active['sans']=['forged.test.invalid']
cat.write_text(json.dumps(catalog)+'\n'); cat.chmod(0o600)
try:
    r.prepare(connection_id='vless-authorized',certificate_id='cert-resolver',**kw)
except r.ResolverError as exc:
    assert 'SAN/validez' in str(exc)
else:
    raise AssertionError('trusted catalog SAN values without matching PEM metadata')
print('PASS: VMess/VLESS authorization, ephemeral files, ownership/modes, cleanup, PEM SAN integrity and fail-closed cases')
PY
echo "OK: resolutor TLS aislado."
