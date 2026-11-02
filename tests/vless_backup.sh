#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
BASE="$TMP/connections"; SECRETS="$TMP/secrets"; BACKUPS="$TMP/backups"; KEYDIR="$TMP/keys"
mkdir -m 700 "$BASE" "$BASE/configurations" "$SECRETS" "$BACKUPS" "$KEYDIR"
KEY="$KEYDIR/master.key"
python3 - "$KEY" <<'PY'
import os,sys,secrets
fd=os.open(sys.argv[1],os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
os.write(fd,secrets.token_bytes(32)); os.close(fd)
PY
chmod 600 "$KEY"
printf '%s\n' '[{"id":"backup-test","name":"Backup test","protocol_id":"vless_ws","port":62001,"max_users":1,"state":"draft","runtime_applied":false,"configuration_revision":1,"configuration_ref":"configurations/backup-test.r000001.json","secret_ref":null}]' > "$BASE/connections.json"
chmod 600 "$BASE/connections.json"
printf '%s\n' '{"schema_version":1,"connection_id":"backup-test","protocol":"vless","mode_id":"vless_ws","transport":"websocket","security":"none","listen_address":"0.0.0.0","listen_port":62001,"transport_options":{"path":"/ws"},"security_options":{}}' > "$BASE/configurations/backup-test.r000001.json"
chmod 600 "$BASE/configurations/backup-test.r000001.json"
OUT="$(python3 "$ROOT/scripts/vless_backup.py" backup-data --base "$BASE" --secrets-dir "$SECRETS" --master-key "$KEY" --backups "$BACKUPS")"
ID="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["backup_id"])' "$OUT")"
DIR="$BACKUPS/data/$ID"
python3 "$ROOT/scripts/vless_backup.py" verify-data --backup-dir "$DIR" >/dev/null
python3 - "$DIR" <<'PY'
import json,sys,pathlib
p=pathlib.Path(sys.argv[1])/'manifest.json'; m=json.loads(p.read_text())
assert m['contains_master_key'] is False
assert m['connection_count']==1
assert m['encrypted_secret_blob_count']==0
PY
# Manipulación del manifiesto debe invalidar SHA256SUMS.
printf '\n' >> "$DIR/manifest.json"
if python3 "$ROOT/scripts/vless_backup.py" verify-data --backup-dir "$DIR" >/dev/null 2>&1; then
  echo 'ERROR: se aceptó un manifiesto manipulado' >&2; exit 1
fi
printf '%s\n' 'PASS: backup de datos, verificación e integridad ante manipulación'
