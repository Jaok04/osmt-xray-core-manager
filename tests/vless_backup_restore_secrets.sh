#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
python3 - "$ROOT/scripts/vless_backup.py" "$ROOT/scripts" "$TMP" <<'PY'
import importlib.util, pathlib, sys, types, builtins, secrets, json
script,scripts,tmp=sys.argv[1:]
spec=importlib.util.spec_from_file_location('vless_backup',script); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
sys.path.insert(0,scripts); import vless_crypto
root=pathlib.Path(tmp); base=root/'connections'; secret_dir=root/'secrets'; keydir=root/'keys'; backups=root/'backups'
for p in (base,base/'configurations',secret_dir,keydir,backups): p.mkdir(mode=0o700,parents=True,exist_ok=True); p.chmod(0o700)
key=secrets.token_bytes(32); keyfile=keydir/'master.key'; keyfile.write_bytes(key); keyfile.chmod(0o600)
entries=[]; plaintexts={}
for cid,mode,transport,security,port,secret_type in (
    ('restore-reality','vless_reality','raw','reality',62101,b'REALITY-PRIVATE-KEY'),
    ('restore-tls','vless_tcp_tls','raw','tls',62102,b'TLS-PRIVATE-KEY')):
    ref=f'secrets/{cid}.r000001.bin'; plain=secret_type; plaintexts[cid]=plain
    blob=vless_crypto.encrypt_secret(plain,key,cid,1); bp=secret_dir/f'{cid}.r000001.bin'; bp.write_bytes(blob); bp.chmod(0o600)
    if security=='reality': sec={'target':'example.com:443','server_names':['example.com'],'short_ids':['abcd'],'secret_ref':ref}
    else: sec={'certificate_file':'/etc/ssl/private/external-test.crt','secret_ref':ref}
    cfg={'schema_version':1,'connection_id':cid,'protocol':'vless','mode_id':mode,'transport':transport,'security':security,'listen_address':'0.0.0.0','listen_port':port,'transport_options':{},'security_options':sec}
    cp=base/'configurations'/f'{cid}.r000001.json'; cp.write_text(json.dumps(cfg)+'\n'); cp.chmod(0o600)
    entries.append({'id':cid,'name':cid,'protocol_id':mode,'port':port,'max_users':1,'state':'draft','runtime_applied':False,'configuration_revision':1,'configuration_ref':f'configurations/{cid}.r000001.json','secret_ref':ref})
cat=base/'connections.json'; cat.write_text(json.dumps(entries)+'\n'); cat.chmod(0o600)
mod.LIFECYCLE=root/'lifecycle.lock'; mod.INTEGRITY=root/'integrity.lock'
backup=mod.create_data(types.SimpleNamespace(base=str(base),secrets_dir=str(secret_dir),backups=str(backups)))
backup_dir=pathlib.Path(backup['path'])
# Alterar el estado live para comprobar que el restore vuelve al snapshot.
cat.write_text('[]\n'); cat.chmod(0o600)
old_stdin=sys.stdin
class TTY:
    def isatty(self): return True
sys.stdin=TTY(); old_input=builtins.input; builtins.input=lambda prompt='': 'RESTAURAR'
try:
    result=mod.restore_data(types.SimpleNamespace(base=str(base),secrets_dir=str(secret_dir),master_key=str(keyfile),backups=str(backups),backup_dir=str(backup_dir)))
finally:
    sys.stdin=old_stdin; builtins.input=old_input
assert result['status']=='restored' and result['connections']==2
assert len(result['external_tls_dependencies'])==1
for cid,plain in plaintexts.items():
    blob=(secret_dir/f'{cid}.r000001.bin').read_bytes()
    assert vless_crypto.decrypt_secret(blob,key,cid,1)==plain
assert len(list(secret_dir.glob('*.bin')))==2
print('PASS: restore end-to-end de blobs REALITY/TLS, autenticación AES-GCM y dependencia TLS externa documentada')
PY
