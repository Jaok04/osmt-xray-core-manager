#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
BASE="$TMP/connections"; SECRETS="$TMP/secrets"; BACKUPS="$TMP/backups"; KEY="$TMP/keys/master.key"
mkdir -m 700 -p "$BASE/configurations" "$SECRETS" "$BACKUPS" "$TMP/keys"
chmod 700 "$BASE" "$BASE/configurations" "$SECRETS" "$BACKUPS" "$TMP/keys"
printf '%s\n' '[{"id":"restore-test","name":"Restore test","protocol_id":"vless_ws","port":62002,"max_users":1,"state":"draft","runtime_applied":false,"configuration_revision":1,"configuration_ref":"configurations/restore-test.r000001.json","secret_ref":null}]' > "$BASE/connections.json"
printf '%s\n' '{"schema_version":1,"connection_id":"restore-test","protocol":"vless","mode_id":"vless_ws","transport":"websocket","security":"none","listen_address":"127.0.0.1","listen_port":62002,"transport_options":{"path":"/ws"},"security_options":{}}' > "$BASE/configurations/restore-test.r000001.json"
chmod 600 "$BASE/connections.json" "$BASE/configurations/restore-test.r000001.json"
OUT="$(python3 "$ROOT/scripts/vless_backup.py" backup-data --base "$BASE" --secrets-dir "$SECRETS" --master-key "$KEY" --backups "$BACKUPS")"
ID="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["backup_id"])' "$OUT")"
python3 - "$ROOT/scripts/vless_backup.py" "$BASE" "$SECRETS" "$BACKUPS" "$KEY" "$BACKUPS/data/$ID" "$TMP" <<'PY'
import importlib.util, pathlib, sys, types, builtins
script,base,secrets_dir,backups,key,backup_dir,tmp=sys.argv[1:]
spec=importlib.util.spec_from_file_location('vless_backup',script)
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
mod.LIFECYCLE=pathlib.Path(tmp)/'lifecycle.lock'
mod.INTEGRITY=pathlib.Path(tmp)/'integrity.lock'
pathlib.Path(base,'connections.json').write_text('[]\n')
pathlib.Path(base,'connections.json').chmod(0o600)
old_stdin=sys.stdin
class TTY:
    def isatty(self): return True
sys.stdin=TTY(); old_input=builtins.input; builtins.input=lambda prompt='': 'RESTAURAR'
try:
    result=mod.restore_data(types.SimpleNamespace(base=base,secrets_dir=secrets_dir,master_key=key,backups=backups,backup_dir=backup_dir))
finally:
    sys.stdin=old_stdin; builtins.input=old_input
assert result['status']=='restored'
assert result['connections']==1
assert result['previous_data_preserved'] is True
assert 'restore-test' in pathlib.Path(base,'connections.json').read_text()
assert pathlib.Path(result['previous_connections_path']).exists()
print('PASS: restauración aislada, confirmación, validación y conservación de estado previo')
PY
