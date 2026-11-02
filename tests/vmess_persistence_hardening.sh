#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
python3 - "$ROOT/scripts/vmess_config_store.py" "$TMP" <<'PY'
import base64, fcntl, importlib.util, json, os, pathlib, subprocess, sys
script, tmp_arg = sys.argv[1:]
tmp=pathlib.Path(tmp_arg)
base=tmp/'vmess'; conf=base/'configurations'; sec=base/'secrets'; catalog=tmp/'connections.json'; lock=tmp/'run'/'integrity.lock'; key=tmp/'keys'/'master.key'
for d in (tmp,base,conf,sec,tmp/'run',tmp/'keys'):
    d.mkdir(mode=0o700,parents=True,exist_ok=True); d.chmod(0o700)

def write(path,data,mode=0o600):
    path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    path.write_bytes(data if isinstance(data,bytes) else data.encode())
    path.chmod(mode)

def entry(cid,mode,port):
    return {'id':cid,'name':cid,'protocol_id':mode,'port':port,'max_users':5,'state':'draft','runtime_applied':False}

def config(cid,mode,port):
    if mode=='vmess_tcp_tls':
        return {'schema_version':1,'connection_id':cid,'protocol':'vmess','mode_id':mode,'transport':'raw','security':'tls','listen_address':'127.0.0.1','listen_port':port,'transport_options':{},'security_options':{'certificate_file':'/etc/ssl/test.crt'},'users':[{'id':'123e4567-e89b-42d3-a456-426614174000','level':0,'email':cid+'@test.invalid'}]}
    return {'schema_version':1,'connection_id':cid,'protocol':'vmess','mode_id':mode,'transport':'websocket','security':'none','listen_address':'127.0.0.1','listen_port':port,'transport_options':{'path':'/ws','host':''},'security_options':{},'users':[{'id':'123e4567-e89b-42d3-a456-426614174001','level':0,'email':cid+'@test.invalid'}]}

def save_config(cid,mode,port):
    path=tmp/f'{cid}.input.json'; write(path,json.dumps(config(cid,mode,port),separators=(',',':'))+'\n'); return path

def cli(action,cid=None,input_path=None,secret_input=None,secret_type=None,secret_output=None):
    args=[sys.executable,script,action,'--base',str(base),'--catalog',str(catalog),'--lock',str(lock),'--secrets-dir',str(sec),'--master-key',str(key)]
    if cid: args += ['--connection-id',cid]
    if input_path: args += ['--input',str(input_path)]
    if secret_input: args += ['--secret-input',str(secret_input)]
    if secret_type: args += ['--secret-type',secret_type]
    if secret_output: args += ['--secret-output',str(secret_output)]
    return subprocess.run(args,text=True,capture_output=True)

catalog.write_text(json.dumps([entry('vmess-tls','vmess_tcp_tls',64001),entry('vmess-ws-a','vmess_ws',64002),entry('vmess-ws-b','vmess_ws',64003),entry('vmess-ws-same','vmess_ws',64004),entry('vmess-badkey','vmess_tcp_tls',64005),entry('vmess-partial','vmess_tcp_tls',64006)])+'\n'); catalog.chmod(0o600)
plain=b'TLS-PRIVATE-KEY-TEST-MATERIAL-NOT-TO-LEAK'
plain_path=tmp/'tls.plain'; write(plain_path,plain)

# Successful TLS store/read, AES-256-GCM envelope and permissions.
tls_input=save_config('vmess-tls','vmess_tcp_tls',64001)
r=cli('store','vmess-tls',tls_input,plain_path,'tls_private_key')
assert r.returncode==0, r.stderr
assert key.is_file() and key.stat().st_mode & 0o777 == 0o600 and len(key.read_bytes())==32
blob_path=sec/'vmess-tls.r000001.bin'; original_blob=blob_path.read_bytes()
blob=json.loads(original_blob); assert blob['version']==1 and blob['algorithm']=='AES-256-GCM'
assert plain not in original_blob
out=tmp/'tls.recovered'
r=cli('read','vmess-tls',secret_output=out)
assert r.returncode==0, r.stderr
assert out.read_bytes()==plain and out.stat().st_mode & 0o777 == 0o600
print('PASS: store/read TLS AES-256-GCM, AAD, permisos y recuperación del secreto')

# Catalog revision/schema and versioned references must match the stored document.
good_catalog=catalog.read_bytes()
good_config=(conf/'vmess-tls.r000001.json').read_bytes()
good_entry=json.loads(good_catalog)
def entry_vm(data):
    return next(e for e in data if e['id']=='vmess-tls')
def assert_catalog_incoherence(label):
    r=cli('read','vmess-tls')
    assert r.returncode!=0, (label,r.stdout,r.stderr)
    r=cli('audit')
    assert r.returncode==0, (label,r.stderr)
    report=json.loads(r.stdout)
    assert any(x['id']=='vmess-tls' for x in report['broken_references']), (label,report)
    print('PASS: read/audit rechazan incoherencia '+label)

data=json.loads(good_catalog); entry_vm(data)['vmess_configuration_revision']=99
write(catalog,json.dumps(data)+'\n'); assert_catalog_incoherence('revision catálogo/referencia')
r=cli('store','vmess-tls',tls_input,plain_path,'tls_private_key')
assert r.returncode!=0, 'store debe rechazar revisión previa inconsistente'
write(catalog,good_catalog)

data=json.loads(good_catalog); entry_vm(data)['vmess_configuration_schema_version']=99
write(catalog,json.dumps(data)+'\n'); assert_catalog_incoherence('schema catálogo')
write(catalog,good_catalog)

doc=json.loads(good_config); doc['schema_version']=2
write(conf/'vmess-tls.r000001.json',json.dumps(doc,separators=(',',':'))+'\n')
assert_catalog_incoherence('schema documento/catálogo')
write(conf/'vmess-tls.r000001.json',good_config)

data=json.loads(good_catalog); entry_vm(data)['vmess_secret_ref']='secrets/vmess-tls.r000002.bin'
write(catalog,json.dumps(data)+'\n'); assert_catalog_incoherence('revision referencia de secreto')
write(catalog,good_catalog)

data=json.loads(good_catalog)
data.append({'id':'vmess-partialmeta','name':'partial','protocol_id':'vmess_ws','port':64007,'max_users':5,'state':'draft','runtime_applied':False,'vmess_configuration_revision':1})
write(catalog,json.dumps(data)+'\n')
r=cli('audit'); report=json.loads(r.stdout)
assert any(x['id']=='vmess-partialmeta' and x['issue']=='partial_catalog_metadata' for x in report['broken_references'])
write(catalog,good_catalog)
print('PASS: audit detecta metadatos VMess parciales sin referencia')

# Missing master key during read fails closed and is not regenerated.
key_bytes=key.read_bytes(); key.unlink(); out_missing=tmp/'missing.recovered'
r=cli('read','vmess-tls',secret_output=out_missing)
assert r.returncode!=0 and not key.exists() and not out_missing.exists()
write(key,key_bytes)
print('PASS: clave maestra ausente durante read; no se regenera ni se escribe secreto')

# Invalid master key blocks read and store without creating revisions/blobs.
write(key,b'not-a-32-byte-master-key')
out_invalid=tmp/'invalid.recovered'
r=cli('read','vmess-tls',secret_output=out_invalid)
assert r.returncode!=0 and not out_invalid.exists()
before_catalog=catalog.read_bytes(); badkey_input=save_config('vmess-badkey','vmess_tcp_tls',64005)
r=cli('store','vmess-badkey',badkey_input,plain_path,'tls_private_key')
assert r.returncode!=0 and catalog.read_bytes()==before_catalog and plain.decode() not in r.stderr
assert not (conf/'vmess-badkey.r000001.json').exists() and not (sec/'vmess-badkey.r000001.bin').exists()
write(key,key_bytes)
print('PASS: clave maestra inválida rechaza read/store sin publicar referencias ni archivos')

# Ciphertext authentication: a modified GCM tag must not produce plaintext.
blob=json.loads(original_blob); ct=bytearray(base64.b64decode(blob['ciphertext'])); ct[-1]^=1; blob['ciphertext']=base64.b64encode(ct).decode()
write(blob_path,json.dumps(blob,separators=(',',':')))
out_tampered=tmp/'tampered.recovered'; r=cli('read','vmess-tls',secret_output=out_tampered)
assert r.returncode!=0 and not out_tampered.exists() and plain not in (r.stdout+r.stderr).encode()
write(blob_path,original_blob)
print('PASS: ciphertext/tag alterado rechazado por AES-256-GCM sin entregar plaintext')

# Broken references are reported by audit; no automatic repair/deletion.
saved_catalog=catalog.read_bytes(); data=json.loads(saved_catalog)
next(e for e in data if e['id']=='vmess-tls')['vmess_configuration_ref']='configurations/missing.r000001.json'
write(catalog,json.dumps(data)+'\n')
r=cli('audit'); assert r.returncode==0, r.stderr
report=json.loads(r.stdout); assert any(x['id']=='vmess-tls' for x in report['broken_references']) and report['automatic_deletion'] is False
write(catalog,saved_catalog)
print('PASS: referencia de configuración rota detectada por audit sin reparación automática')

# Missing encrypted secret referenced by a valid configuration is also broken.
secret_bytes=blob_path.read_bytes(); blob_path.unlink()
r=cli('audit'); assert r.returncode==0, r.stderr
report=json.loads(r.stdout); assert any(x['id']=='vmess-tls' for x in report['broken_references'])
write(blob_path,secret_bytes)
print('PASS: referencia a secreto ausente detectada por audit')

# Orphan config/secret files and symlinks are reported and never auto-deleted.
orphan_cfg=conf/'orphan.r000001.json'; orphan_sec=sec/'orphan.r000001.bin'
write(orphan_cfg,'{}\n'); write(orphan_sec,b'orphan-ciphertext')
symlink_cfg=conf/'rogue.json'; symlink_cfg.symlink_to(conf/'vmess-tls.r000001.json')
symlink_sec=sec/'rogue.bin'; symlink_sec.symlink_to(blob_path)
r=cli('audit'); assert r.returncode==0, r.stderr
report=json.loads(r.stdout)
assert 'orphan.r000001.json' in report['orphan_files'] and 'orphan.r000001.bin' in report['orphan_secret_files']
assert 'configurations/rogue.json' in report['unsafe_entries'] and 'secrets/rogue.bin' in report['unsafe_entries']
assert report['automatic_deletion'] is False and orphan_cfg.exists() and orphan_sec.exists()
symlink_cfg.unlink(); symlink_sec.unlink(); orphan_cfg.unlink(); orphan_sec.unlink()
print('PASS: audit detecta huérfanos/symlinks y no borra automáticamente')

# Failure after writing secret/config but before catalog publication leaves detectable orphans.
partial_input=save_config('vmess-partial','vmess_tcp_tls',64006)
spec=importlib.util.spec_from_file_location('vmess_store_fault_test',script); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
args=type('Args',(),{'action':'store','base':str(base),'catalog':str(catalog),'lock':str(lock),'secrets_dir':str(sec),'master_key':str(key),'connection_id':'vmess-partial','input':str(partial_input),'secret_input':str(plain_path),'secret_type':'tls_private_key','secret_output':None})()
original_atomic=mod.atomic_write
def fail_catalog(path,data):
    if pathlib.Path(path)==catalog: raise OSError('fallo de catálogo inyectado')
    return original_atomic(path,data)
mod.atomic_write=fail_catalog
try:
    try: mod.run(args)
    except OSError as exc: assert 'inyectado' in str(exc)
    else: raise AssertionError('el fallo de publicación debía propagarse')
finally: mod.atomic_write=original_atomic
assert catalog.read_bytes()==saved_catalog
assert (conf/'vmess-partial.r000001.json').is_file() and (sec/'vmess-partial.r000001.bin').is_file()
r=cli('audit'); report=json.loads(r.stdout)
assert 'vmess-partial.r000001.json' in report['orphan_files'] and 'vmess-partial.r000001.bin' in report['orphan_secret_files']
(conf/'vmess-partial.r000001.json').unlink(); (sec/'vmess-partial.r000001.bin').unlink()
print('PASS: fallo antes de publicar catálogo no altera referencias y deja artefactos huérfanos detectables')

# Two simultaneous writers on distinct IDs must not lose catalog updates.
inputs=[save_config('vmess-ws-a','vmess_ws',64002),save_config('vmess-ws-b','vmess_ws',64003)]
def cmd_store(cid,path):
    return [sys.executable,script,'store','--connection-id',cid,'--input',str(path),'--base',str(base),'--catalog',str(catalog),'--lock',str(lock),'--secrets-dir',str(sec),'--master-key',str(key)]
holder=os.open(lock,os.O_CREAT|os.O_RDWR,0o600); fcntl.flock(holder,fcntl.LOCK_EX)
procs=[subprocess.Popen(cmd_store(cid,path),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for cid,path in zip(('vmess-ws-a','vmess-ws-b'),inputs)]
fcntl.flock(holder,fcntl.LOCK_UN); os.close(holder)
results=[p.communicate(timeout=20)+(p.returncode,) for p in procs]
assert all(rc==0 for _,_,rc in results), results
current=json.loads(catalog.read_text())
assert all(next(e for e in current if e['id']==cid).get('vmess_configuration_revision')==1 for cid in ('vmess-ws-a','vmess-ws-b'))
print('PASS: escritores concurrentes conservan ambas actualizaciones del catálogo')

# Two simultaneous revisions of the same connection serialize to r1 and r2.
same_input=save_config('vmess-ws-same','vmess_ws',64004)
holder=os.open(lock,os.O_CREAT|os.O_RDWR,0o600); fcntl.flock(holder,fcntl.LOCK_EX)
procs=[subprocess.Popen(cmd_store('vmess-ws-same',same_input),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for _ in range(2)]
fcntl.flock(holder,fcntl.LOCK_UN); os.close(holder)
results=[p.communicate(timeout=20)+(p.returncode,) for p in procs]
assert all(rc==0 for _,_,rc in results), results
current=json.loads(catalog.read_text()); same=next(e for e in current if e['id']=='vmess-ws-same')
assert same['vmess_configuration_revision']==2 and (conf/'vmess-ws-same.r000001.json').is_file() and (conf/'vmess-ws-same.r000002.json').is_file()
print('PASS: dos escrituras concurrentes sobre la misma conexión serializan revisiones r1/r2')
PY
