#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
python3 - "$ROOT/scripts/vless_backup.py" "$TMP" <<'PY'
import importlib.util, pathlib, sys, types, json
script,tmp=sys.argv[1:]
spec=importlib.util.spec_from_file_location('vless_backup_isolation',script)
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
root=pathlib.Path(tmp); base=root/'connections'; secrets_dir=root/'secrets'; backups=root/'backups'; vmess=root/'vmess'
for d in (base,base/'configurations',secrets_dir,backups,vmess,vmess/'configurations',vmess/'secrets'):
    d.mkdir(mode=0o700,parents=True,exist_ok=True); d.chmod(0o700)
keydir=root/'keys'; keydir.mkdir(mode=0o700); key=keydir/'master.key'; key.write_bytes(b'K'*32); key.chmod(0o600)
(base/'connections.json').write_text(json.dumps([
 {'id':'vless-test','protocol_id':'vless_ws','port':62010,'max_users':1,'state':'draft','runtime_applied':False,'configuration_revision':1,'configuration_ref':'configurations/vless-test.r000001.json','secret_ref':None},
 {'id':'vmess-test','protocol_id':'vmess_httpupgrade_tls','port':62011,'max_users':1,'state':'draft','runtime_applied':False,'vmess_configuration_schema_version':1,'vmess_configuration_revision':1,'vmess_configuration_ref':'configurations/vmess-test.r000001.json','vmess_secret_ref':'secrets/vmess-test.r000001.bin'}])+'\n'); (base/'connections.json').chmod(0o600)
cfg={'schema_version':1,'connection_id':'vless-test','protocol':'vless','mode_id':'vless_ws','transport':'websocket','security':'none','listen_address':'127.0.0.1','listen_port':62010,'transport_options':{'path':'/ws'},'security_options':{}}
(base/'configurations'/'vless-test.r000001.json').write_text(json.dumps(cfg)+'\n'); (base/'configurations'/'vless-test.r000001.json').chmod(0o600)
vmcfg=vmess/'configurations'/'vmess-test.r000001.json'; vmcfg.write_text('{"protocol":"vmess"}\n'); vmcfg.chmod(0o600)
vmsecret=vmess/'secrets'/'vmess-test.r000001.bin'; vmsecret.write_bytes(b'ciphertext'); vmsecret.chmod(0o600)
args=types.SimpleNamespace(base=str(base),secrets_dir=str(secrets_dir),master_key=str(key),backups=str(backups))
result=mod.create_data(args); manifest=mod.verify_data_dir(pathlib.Path(result['path']))
paths={f['path'] for f in manifest['files']}
assert 'connections/connections.json' in paths
assert 'connections/configurations/vless-test.r000001.json' in paths
assert not any('vmess' in name for name in paths)
assert vmcfg.read_text()=='{"protocol":"vmess"}\n' and vmsecret.read_bytes()==b'ciphertext'
print('PASS: backup VLESS valida catálogo mixto, incluye solo datos VLESS y no incorpora el almacén VMess externo')
PY