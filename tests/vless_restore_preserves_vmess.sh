#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
python3 - "$ROOT" "$TMP" <<'PY'
import builtins, hashlib, importlib.util, json, pathlib, sys, types
root, tmp = map(pathlib.Path, sys.argv[1:])
spec = importlib.util.spec_from_file_location('vless_backup_restore_vmess', root/'scripts/vless_backup.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
mod.LIFECYCLE = tmp/'lifecycle.lock'; mod.INTEGRITY = tmp/'integrity.lock'


def write(path, data, mode=0o600):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else data.encode())
    path.chmod(mode)


def vless(cid, port):
    return {'id':cid,'name':cid,'protocol_id':'vless_ws','port':port,'max_users':1,'state':'draft','runtime_applied':False}


def vmess(cid, port, with_config=True):
    entry={'id':cid,'name':cid,'protocol_id':'vmess_ws','port':port,'max_users':1,'state':'draft','runtime_applied':False}
    if with_config:
        entry.update({'vmess_configuration_schema_version':1,'vmess_configuration_revision':1,'vmess_configuration_ref':f'configurations/{cid}.r000001.json','vmess_secret_ref':None})
        config={'schema_version':1,'connection_id':cid,'protocol':'vmess','mode_id':'vmess_ws','transport':'websocket','security':'none','listen_address':'127.0.0.1','listen_port':port,'transport_options':{'path':'/ws','host':''},'security_options':{},'users':[{'id':'123e4567-e89b-42d3-a456-426614174000','level':0,'email':cid+'@test.invalid'}]}
        entry['_test_config'] = config
    return entry


def vmess_tls(cid, port):
    entry={'id':cid,'name':cid,'protocol_id':'vmess_tcp_tls','port':port,'max_users':1,'state':'draft','runtime_applied':False,
           'vmess_configuration_schema_version':1,'vmess_configuration_revision':1,
           'vmess_configuration_ref':f'configurations/{cid}.r000001.json','vmess_secret_ref':f'secrets/{cid}.r000001.bin'}
    config={'schema_version':1,'connection_id':cid,'protocol':'vmess','mode_id':'vmess_tcp_tls','transport':'raw','security':'tls',
            'listen_address':'127.0.0.1','listen_port':port,'transport_options':{},
            'security_options':{'certificate_file':'/etc/ssl/test.crt','secret_ref':entry['vmess_secret_ref']},
            'users':[{'id':'123e4567-e89b-42d3-a456-426614174001','level':0,'email':cid+'@test.invalid'}]}
    entry['_test_config']=config; entry['_test_secret']=b'vmess-encrypted-secret-fixture'
    return entry


def install_vmess_config(case, entry):
    config=entry.pop('_test_config', None); secret=entry.pop('_test_secret', None)
    if config is not None:
        write(case/'vmess'/'configurations'/f"{entry['id']}.r000001.json",json.dumps(config)+'\n')
    if secret is not None:
        write(case/'vmess'/'secrets'/f"{entry['id']}.r000001.bin",secret)

def setup(name, catalog):
    case=tmp/name; case.mkdir(mode=0o700,parents=True,exist_ok=True); case.chmod(0o700); base=case/'connections'; secrets=case/'secrets'; backups=case/'backups'; vmess_root=case/'vmess'
    for d in (base,base/'configurations',secrets,backups,vmess_root,vmess_root/'configurations',vmess_root/'secrets'):
        d.mkdir(mode=0o700,parents=True,exist_ok=True); d.chmod(0o700)
    write(base/'connections.json',json.dumps(catalog)+'\n')
    for entry in catalog:
        if entry['protocol_id'].startswith('vless_'):
            cfg={'schema_version':1,'connection_id':entry['id'],'protocol':'vless','mode_id':entry['protocol_id'],'transport':'websocket','security':'none','listen_address':'127.0.0.1','listen_port':entry['port'],'transport_options':{'path':'/ws'},'security_options':{}}
            write(base/'configurations'/f"{entry['id']}.r000001.json",json.dumps(cfg)+'\n')
        elif entry['protocol_id'].startswith('vmess_') and '_test_config' in entry:
            cfg=entry.pop('_test_config')
            write(vmess_root/'configurations'/f"{entry['id']}.r000001.json",json.dumps(cfg)+'\n')
    return case,base,secrets,backups


def backup(base,secrets,backups):
    return mod.create_data(types.SimpleNamespace(base=str(base),secrets_dir=str(secrets),master_key=str(tmp/'unused.key'),backups=str(backups)))


def restore(base,secrets,backups,backup_path, fail_atomic=None):
    original_atomic=mod.atomic_file
    if fail_atomic is not None: mod.atomic_file=fail_atomic
    old_stdin=sys.stdin; old_input=builtins.input
    class TTY:
        def isatty(self): return True
    sys.stdin=TTY(); builtins.input=lambda prompt='': 'RESTAURAR'
    try:
        return mod.restore_data(types.SimpleNamespace(base=str(base),secrets_dir=str(secrets),master_key=str(tmp/'unused.key'),backups=str(backups),backup_dir=str(backup_path)))
    finally:
        sys.stdin=old_stdin; builtins.input=old_input; mod.atomic_file=original_atomic


def read_catalog(base): return json.loads((base/'connections.json').read_text())

# 1. Backup snapshot contains one VMess entry; a second VMess entry is created later.
old = vmess('vmess-before', 63001)
stale = vmess('vmess-stale', 63004)
case,base,secrets,backups=setup('success',[vless('vless-snapshot',63000),old,stale])
created=backup(base,secrets,backups); backup_dir=pathlib.Path(created['path'])
manifest=mod.verify_data_dir(backup_dir)
archive=mod._read_archive_members((backup_dir/'backup.tar.gz').read_bytes(),manifest,retain=True)
assert not any('/vmess/' in p or p.startswith('vmess/') for p in archive)
assert json.loads(archive['connections/connections.json'])[1]['protocol_id']=='vmess_ws'

new=vmess_tls('vmess-after',63002)
install_vmess_config(case,new)
current=[vless('vless-after',63003),old,new]
write(base/'connections.json',json.dumps(current)+'\n')
vmess_files={p:str(hashlib.sha256(p.read_bytes()).hexdigest()) for p in (case/'vmess').rglob('*') if p.is_file()}
result=restore(base,secrets,backups,backup_dir)
final=read_catalog(base)
assert {e['id'] for e in final}=={'vless-snapshot','vmess-before','vmess-after'}
assert all(e['id']!='vmess-stale' for e in final), 'no debe revivir una entrada VMess eliminada después del backup'
assert result['vless_connections_restored']==1 and result['vmess_connections_preserved']==2 and result['connections']==3
assert all(e['id']!='vless-after' for e in final)
assert {p:str(hashlib.sha256(p.read_bytes()).hexdigest()) for p in (case/'vmess').rglob('*') if p.is_file()}==vmess_files
assert next(e for e in final if e['id']=='vmess-before')['vmess_configuration_ref']=='configurations/vmess-before.r000001.json'
assert next(e for e in final if e['id']=='vmess-after')['vmess_configuration_ref']=='configurations/vmess-after.r000001.json'
assert next(e for e in final if e['id']=='vmess-after')['vmess_secret_ref']=='secrets/vmess-after.r000001.bin'
print('PASS: restaura VLESS, conserva VMess vigentes anteriores/posteriores, no revive VMess histórico eliminado y mantiene refs/almacén intactos')

# 2. Duplicate IDs between restored VLESS and current VMess fail before publication.
case,base,secrets,backups=setup('duplicate',[vless('collision',63100)])
created=backup(base,secrets,backups); backup_dir=pathlib.Path(created['path'])
conflict=vmess('collision',63101)
install_vmess_config(case,conflict)
write(base/'connections.json',json.dumps([conflict])+'\n')
before=(base/'connections.json').read_bytes()
try: restore(base,secrets,backups,backup_dir)
except mod.BackupError as exc: assert 'conflicto de IDs' in str(exc)
else: raise AssertionError('debió rechazar IDs duplicados')
assert (base/'connections.json').read_bytes()==before and not (backups/'RESTORE_IN_PROGRESS.json').exists()
print('PASS: conflicto de IDs rechazado sin modificar catálogo ni publicar journal')

# 3. A corrupt current catalog fails closed.
case,base,secrets,backups=setup('corrupt',[vless('safe',63200)])
created=backup(base,secrets,backups); backup_dir=pathlib.Path(created['path'])
write(base/'connections.json','{not-json')
before=(base/'connections.json').read_bytes()
try: restore(base,secrets,backups,backup_dir)
except (mod.BackupError, json.JSONDecodeError): pass
else: raise AssertionError('debió rechazar catálogo corrupto')
assert (base/'connections.json').read_bytes()==before
print('PASS: catálogo actual corrupto rechazado sin alteración')

# 4. A broken current VMess reference fails closed.
case,base,secrets,backups=setup('broken-ref',[vless('safe-ref',63300)])
created=backup(base,secrets,backups); backup_dir=pathlib.Path(created['path'])
broken=vmess('broken-vmess',63301)
install_vmess_config(case,broken)
broken['vmess_configuration_ref']='configurations/missing.r000001.json'
write(base/'connections.json',json.dumps([broken])+'\n')
before=(base/'connections.json').read_bytes()
try: restore(base,secrets,backups,backup_dir)
except (mod.BackupError, FileNotFoundError): pass
else: raise AssertionError('debió rechazar referencia VMess rota')
assert (base/'connections.json').read_bytes()==before
print('PASS: referencias VMess rotas rechazadas sin modificar catálogo')

# 5. Failure writing the merged staging catalog leaves the live catalog untouched.
case,base,secrets,backups=setup('write-failure',[vless('safe-write',63400)])
created=backup(base,secrets,backups); backup_dir=pathlib.Path(created['path'])
write(base/'connections.json',json.dumps([vless('current-write',63401)])+'\n')
before=(base/'connections.json').read_bytes()
def failing_atomic(path,data,mode=0o600):
    if pathlib.Path(path).name=='connections.json' and pathlib.Path(path).parent.name.startswith('.vless-restore-connections.'):
        raise OSError('fallo de escritura simulado')
    return original_atomic(path,data,mode)
original_atomic=mod.atomic_file
try: restore(base,secrets,backups,backup_dir,fail_atomic=failing_atomic)
except OSError as exc: assert 'simulado' in str(exc)
else: raise AssertionError('debió fallar la escritura staging')
assert (base/'connections.json').read_bytes()==before and not (backups/'RESTORE_IN_PROGRESS.json').exists()
print('PASS: fallo de escritura del catálogo combinado no modifica el catálogo activo')
PY
