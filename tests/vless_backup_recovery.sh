#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
python3 - "$ROOT/scripts/vless_backup.py" "$TMP" <<'PY'
import importlib.util, pathlib, sys, types, secrets, json, os
script,tmp=sys.argv[1:]
spec=importlib.util.spec_from_file_location('vless_backup',script)
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
root=pathlib.Path(tmp); base=root/'connections'; secrets_dir=root/'secrets'; keydir=root/'keys'; backups=root/'backups'
for p in (base,base/'configurations',secrets_dir,keydir,backups): p.mkdir(mode=0o700,parents=True,exist_ok=True); p.chmod(0o700)
mod.LIFECYCLE=root/'lifecycle.lock'; mod.INTEGRITY=root/'integrity.lock'
key=secrets.token_bytes(32); keyfile=keydir/'master.key'; keyfile.write_bytes(key); keyfile.chmod(0o600)
cid='recovery-test'; secret_ref=f'secrets/{cid}.r000001.bin'
import sys as _sys; _sys.path.insert(0,str(pathlib.Path(script).parent)); import vless_crypto
blob=vless_crypto.encrypt_secret(b'PRIVATE-KEY-TEST',key,cid,1)
(secrets_dir/f'{cid}.r000001.bin').write_bytes(blob); (secrets_dir/f'{cid}.r000001.bin').chmod(0o600)
entry={'id':cid,'name':'Recovery test','protocol_id':'vless_reality','port':62003,'max_users':1,'state':'draft','runtime_applied':False,'configuration_revision':1,'configuration_ref':f'configurations/{cid}.r000001.json','secret_ref':secret_ref}
(base/'connections.json').write_text(json.dumps([entry])+'\n'); (base/'connections.json').chmod(0o600)
config={'schema_version':1,'connection_id':cid,'protocol':'vless','mode_id':'vless_reality','transport':'raw','security':'reality','listen_address':'0.0.0.0','listen_port':62003,'transport_options':{},'security_options':{'target':'example.com:443','server_names':['example.com'],'short_ids':['abcd'],'secret_ref':secret_ref}}
(base/'configurations'/f'{cid}.r000001.json').write_text(json.dumps(config)+'\n'); (base/'configurations'/f'{cid}.r000001.json').chmod(0o600)
backup=mod.create_data(types.SimpleNamespace(base=str(base),secrets_dir=str(secrets_dir),backups=str(backups)))
backup_dir=pathlib.Path(backup['path'])
password='LongPassword!123'
old_getpass=mod.getpass.getpass; mod.getpass.getpass=lambda prompt='': password
try:
    recovery=mod.create_recovery(types.SimpleNamespace(master_key=str(keyfile),backups=str(backups),backup_dir=str(backup_dir)))
finally: mod.getpass.getpass=old_getpass
recovery_dir=pathlib.Path(recovery['path'])
# Simular pérdida: la clave original se retira del fixture; el recuperador solo escribe si no existe.
keyfile.unlink()
mod.getpass.getpass=lambda prompt='': 'WrongPassword!123'
try:
    try: mod.recover_key(types.SimpleNamespace(recovery_dir=str(recovery_dir),backups=str(backups),master_key=str(keyfile)))
    except mod.BackupError: pass
    else: raise AssertionError('wrong password was accepted')
    assert not keyfile.exists()
finally: mod.getpass.getpass=old_getpass
mod.getpass.getpass=lambda prompt='': password
try:
    result=mod.recover_key(types.SimpleNamespace(recovery_dir=str(recovery_dir),backups=str(backups),master_key=str(keyfile)))
finally: mod.getpass.getpass=old_getpass
assert result['status']=='recovered'
assert keyfile.read_bytes()==key
assert keyfile.stat().st_mode & 0o777 == 0o600
print('PASS: paquete scrypt/AES-GCM, asociación backup_id y recuperación de clave autenticada')
PY
