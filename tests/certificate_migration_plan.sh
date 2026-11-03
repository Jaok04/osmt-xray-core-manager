#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT
chmod 700 "$TMP"
mkdir -m 700 "$TMP/connections" "$TMP/connections/configurations" "$TMP/vmess" "$TMP/vmess/configurations" "$TMP/vless-secrets" "$TMP/vmess-secrets"
mkdir -m 700 "$TMP/keys"
head -c 32 /dev/urandom >"$TMP/keys/master.key"
chmod 600 "$TMP/keys/master.key"
openssl req -x509 -newkey rsa:2048 -nodes -keyout "$TMP/key.pem" -out "$TMP/cert.pem" -days 3 -subj '/CN=migration.test.invalid' >/dev/null 2>&1
chmod 600 "$TMP/key.pem"
chmod 644 "$TMP/cert.pem"
python3 - "$ROOT" "$TMP" <<'PY'
import json, pathlib, sys, uuid
root, tmp = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
sys.path.insert(0, str(root/'scripts'))
import vless_crypto, vmess_config_store
master=(tmp/'keys/master.key').read_bytes()
key=(tmp/'key.pem').read_bytes()
cert_path=str(tmp/'cert.pem')
entries=[]
# VLESS historical TLS record.
cid='vless-old'
vless_config={
 'schema_version':1,'connection_id':cid,'protocol':'vless','mode_id':'vless_tcp_tls',
 'transport':'raw','security':'tls','listen_address':'127.0.0.1','listen_port':41001,
 'transport_options':{},'security_options':{'certificate_file':cert_path,'secret_ref':f'secrets/{cid}.r000001.bin'}}
(tmp/f'connections/configurations/{cid}.r000001.json').write_text(json.dumps(vless_config,separators=(',',':'))+'\n')
(tmp/f'connections/configurations/{cid}.r000001.json').chmod(0o600)
(tmp/f'vless-secrets/{cid}.r000001.bin').write_bytes(vless_crypto.encrypt_secret(key,master,cid,1))
(tmp/f'vless-secrets/{cid}.r000001.bin').chmod(0o600)
entries.append({'id':cid,'name':'Fixture VLESS','protocol_id':'vless_tcp_tls','port':41001,'max_users':1,'state':'draft','runtime_applied':False,'configuration_schema_version':1,'configuration_revision':1,'configuration_ref':f'configurations/{cid}.r000001.json','secret_ref':f'secrets/{cid}.r000001.bin'})
# VMess historical TLS record with its distinct envelope/AAD.
cid='vmess-old'
vmess_config={
 'schema_version':1,'connection_id':cid,'protocol':'vmess','mode_id':'vmess_tcp_tls',
 'transport':'raw','security':'tls','listen_address':'127.0.0.1','listen_port':41002,
 'transport_options':{},'security_options':{'certificate_file':cert_path,'secret_ref':f'secrets/{cid}.r000001.bin'},
 'users':[{'id':str(uuid.uuid4()),'level':0,'email':'fixture@test.invalid'}]}
(tmp/f'vmess/configurations/{cid}.r000001.json').write_text(json.dumps(vmess_config,separators=(',',':'))+'\n')
(tmp/f'vmess/configurations/{cid}.r000001.json').chmod(0o600)
(tmp/f'vmess-secrets/{cid}.r000001.bin').write_bytes(vmess_config_store.encrypt(key,master,cid))
(tmp/f'vmess-secrets/{cid}.r000001.bin').chmod(0o600)
entries.append({'id':cid,'name':'Fixture VMess','protocol_id':'vmess_tcp_tls','port':41002,'max_users':1,'state':'draft','runtime_applied':False,'vmess_configuration_schema_version':1,'vmess_configuration_revision':1,'vmess_configuration_ref':f'configurations/{cid}.r000001.json','vmess_secret_ref':f'secrets/{cid}.r000001.bin'})
# Non-TLS REALITY-like mode is intentionally not considered.
entries.append({'id':'non-tls','name':'No TLS','protocol_id':'vless_ws','port':41003,'max_users':1,'state':'draft','runtime_applied':False})
catalog=tmp/'connections/connections.json'
catalog.write_text(json.dumps(entries,separators=(',',':'))+'\n')
catalog.chmod(0o600)
PY
PLAN=("$ROOT/scripts/certificate_migration.py" plan --protocol all
 --connections "$TMP/connections" --vmess "$TMP/vmess"
 --vless-secrets "$TMP/vless-secrets" --vmess-secrets "$TMP/vmess-secrets"
 --catalog "$TMP/connections/connections.json" --master-key "$TMP/keys/master.key"
 --integrity-lock "$TMP/missing-integrity.lock"
 --certificate-catalog "$TMP/missing-cert-catalog.json")
sha_before="$(find "$TMP" -type f -print0 | sort -z | xargs -0 sha256sum)"
"${PLAN[@]}" >"$TMP/plan.json"
sha_after="$(find "$TMP" -type f ! -name plan.json -print0 | sort -z | xargs -0 sha256sum)"
[[ "$sha_before" == "$sha_after" ]]
python3 - "$TMP/plan.json" <<'PY'
import json,sys
p=json.load(open(sys.argv[1]))
assert p['read_only'] is True and p['writes_performed'] is False
assert p['automatic_migration'] is False and p['automatic_deletion'] is False
assert p['summary']['tls_candidates']==2
assert p['summary']['ready']==2 and p['summary']['blocked']==0
assert p['summary']['deduplication_groups']==1
assert p['deduplication_groups']['group-0001']==['vless-old','vmess-old']
assert {x['protocol'] for x in p['records']}=={'vless','vmess'}
assert all('private' not in json.dumps(x).lower() for x in p['records'])
PY
echo "PASS: preflight VLESS/VMess, descifrado por backend, fingerprint y deduplicación"
# Alterar un blob debe bloquear sólo el candidato afectado sin revelar material.
python3 - "$TMP/vless-secrets/vless-old.r000001.bin" <<'PY'
import pathlib,sys
p=pathlib.Path(sys.argv[1]); b=bytearray(p.read_bytes()); b[-3]^=1; p.write_bytes(b); p.chmod(0o600)
PY
"${PLAN[@]}" >"$TMP/plan-tampered.json"
python3 - "$TMP/plan-tampered.json" <<'PY'
import json,sys
p=json.load(open(sys.argv[1]))
r={x['connection_id']:x for x in p['records']}
assert r['vless-old']['status']=='BLOCKED'
assert r['vmess-old']['status']=='READY'
assert p['summary']['blocked']==1
PY
echo "PASS: blob alterado bloqueado sin impedir el análisis del otro protocolo"
echo "OK: certificate_migration.py plan es de solo lectura y falla cerrado."
