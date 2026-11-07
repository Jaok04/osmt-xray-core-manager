#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT
chmod 700 "$TMP"
BASE="$TMP/certificates"; MANAGED="$BASE/managed"; SECRETS="$BASE/secrets"
CATALOG="$BASE/catalog.json"; LOCK="$BASE/catalog.lock"; KEYDIR="$TMP/keys"; MASTER="$KEYDIR/master.key"
mkdir -m 700 "$BASE" "$MANAGED" "$SECRETS" "$KEYDIR"
head -c 32 /dev/urandom >"$MASTER"; chmod 600 "$MASTER"
python3 - "$ROOT" <<'PYLOCK'
import sys
from pathlib import Path
root = Path(sys.argv[1])
sys.path.insert(0, str(root / "scripts"))
import certificate_store
import certificate_resolver
expected = "/run/xray-manager-certificate-locks/catalog.lock"
store_args = certificate_store.build_parser().parse_args(["list"])
resolver_args = certificate_resolver.build_parser().parse_args(["cleanup", "--lease-id", "lease-test"])
assert store_args.lock == expected, store_args.lock
assert resolver_args.certificate_lock == expected, resolver_args.certificate_lock
assert not expected.startswith("/var/lib/xray-manager/certificates/")
print("OK: el lock TLS usa una ruta estable fuera del árbol de datos.")
PYLOCK

STORE=(python3 "$ROOT/scripts/certificate_store.py" --base "$BASE" --catalog "$CATALOG" --managed-dir "$MANAGED" --secrets-dir "$SECRETS" --master-key "$MASTER" --lock "$LOCK")
openssl req -x509 -newkey rsa:2048 -nodes -keyout "$TMP/key1.pem" -out "$TMP/cert1.pem" -days 2 -subj "/CN=managed.test.invalid" -addext "subjectAltName=DNS:managed.test.invalid" >/dev/null 2>&1
chmod 600 "$TMP/key1.pem"; chmod 644 "$TMP/cert1.pem"
"${STORE[@]}" import --storage-type managed --certificate-file "$TMP/cert1.pem" --private-key-file "$TMP/key1.pem" --certificate-id cert-managed >"$TMP/import1.json"
python3 - "$TMP/import1.json" "$CATALOG" "$MANAGED" "$SECRETS" <<'PY'
import json, pathlib, sys
result=json.loads(pathlib.Path(sys.argv[1]).read_text())
catalog=json.loads(pathlib.Path(sys.argv[2]).read_text())
assert result["status"]=="imported" and result["certificate_id"]=="cert-managed"
assert catalog["schema_version"]==2 and len(catalog["certificates"])==1
record=catalog["certificates"][0]
assert record["storage_type"]=="managed"
assert record["certificate_source"]=="managed/cert-managed.r000001.pem"
assert record["secret_ref"]=="secrets/cert-managed.r000001.bin"
assert record["active_revision"]==1 and len(record["revisions"])==1
assert "private_key" not in record and "key_file" not in record
assert pathlib.Path(sys.argv[3],"cert-managed.r000001.pem").is_file()
assert pathlib.Path(sys.argv[4],"cert-managed.r000001.bin").is_file()
assert pathlib.Path(sys.argv[4],"cert-managed.r000001.bin").stat().st_mode & 0o777 == 0o600
assert "BEGIN PRIVATE KEY" not in pathlib.Path(sys.argv[2]).read_text()
PY
echo "PASS: import managed, catálogo sin clave privada y blob cifrado"
"${STORE[@]}" list >"$TMP/list.json"
"${STORE[@]}" show --certificate-id cert-managed >"$TMP/show.json"
"${STORE[@]}" audit >"$TMP/audit1.json"
python3 - "$TMP/audit1.json" <<'PY'
import json,sys
v=json.load(open(sys.argv[1]))
assert v["broken_references"]==[] and v["orphan_secret_files"]==[]
assert v["orphan_managed_files"]==[] and v["unsafe_entries"]==[]
assert v["automatic_deletion"] is False
PY
echo "PASS: list/show/audit íntegros"
if "${STORE[@]}" import --storage-type managed --certificate-file "$TMP/cert1.pem" --private-key-file "$TMP/key1.pem" >/dev/null 2>&1; then
 echo "FAIL: duplicate certificate accepted" >&2; exit 1
fi
echo "PASS: deduplicación por huella"
openssl req -x509 -newkey rsa:2048 -nodes -keyout "$TMP/key2.pem" -out "$TMP/cert2.pem" -days 2 -subj "/CN=reference.test.invalid" -addext "subjectAltName=DNS:reference.test.invalid" >/dev/null 2>&1
chmod 600 "$TMP/key2.pem"; chmod 644 "$TMP/cert2.pem"
"${STORE[@]}" import --storage-type reference --certificate-file "$TMP/cert2.pem" --private-key-file "$TMP/key2.pem" --certificate-id cert-reference >"$TMP/import2.json"
python3 - "$TMP/import2.json" "$CATALOG" "$TMP/cert2.pem" <<'PY'
import json,pathlib,sys
r=json.load(open(sys.argv[1])); c=json.load(open(sys.argv[2]))
entry=next(x for x in c["certificates"] if x["certificate_id"]=="cert-reference")
assert r["storage_type"]=="reference"
assert entry["certificate_source"]==str(pathlib.Path(sys.argv[3]).resolve())
assert pathlib.Path(sys.argv[3]).is_file()
PY
echo "PASS: import reference conserva el certificado externo"
openssl req -x509 -newkey rsa:2048 -nodes -keyout "$TMP/key3.pem" -out "$TMP/cert3.pem" -days 2 -subj "/CN=rotated.test.invalid" -addext "subjectAltName=DNS:rotated.test.invalid" >/dev/null 2>&1
chmod 600 "$TMP/key3.pem"; chmod 644 "$TMP/cert3.pem"
"${STORE[@]}" import --storage-type managed --certificate-file "$TMP/cert3.pem" --private-key-file "$TMP/key3.pem" --certificate-id cert-managed >"$TMP/rotate.json"
python3 - "$CATALOG" "$MANAGED" "$SECRETS" "$TMP/rotate.json" <<'PYROTATE'
import json,pathlib,sys
cat=json.loads(pathlib.Path(sys.argv[1]).read_text())
r=next(x for x in cat['certificates'] if x['certificate_id']=='cert-managed')
assert r['active_revision']==2 and r['revision']==2 and len(r['revisions'])==2
assert r['revisions'][0]['fingerprint_sha256'] != r['revisions'][1]['fingerprint_sha256']
assert pathlib.Path(sys.argv[2],'cert-managed.r000001.pem').is_file()
assert pathlib.Path(sys.argv[2],'cert-managed.r000002.pem').is_file()
assert pathlib.Path(sys.argv[3],'cert-managed.r000001.bin').is_file()
assert pathlib.Path(sys.argv[3],'cert-managed.r000002.bin').is_file()
assert json.loads(pathlib.Path(sys.argv[4]).read_text())['revision']==2
PYROTATE
"${STORE[@]}" audit >"$TMP/audit-rotated.json"
python3 - "$TMP/audit-rotated.json" <<'PYROTATEAUDIT'
import json,sys
v=json.load(open(sys.argv[1])); assert v['broken_references']==[] and v['orphan_secret_files']==[] and v['orphan_managed_files']==[]
PYROTATEAUDIT
echo "PASS: rotación inmutable conserva r000001 y verifica ambas revisiones"
"${STORE[@]}" rollback --certificate-id cert-managed --revision 1 >"$TMP/rollback.json"
python3 - "$CATALOG" "$TMP/rollback.json" <<'PYROLLBACK'
import json,pathlib,sys
c=json.loads(pathlib.Path(sys.argv[1]).read_text()); r=next(x for x in c['certificates'] if x['certificate_id']=='cert-managed')
assert r['active_revision']==1 and r['revision']==1 and len(r['revisions'])==2
assert json.loads(pathlib.Path(sys.argv[2]).read_text())['status']=='rolled_back'
PYROLLBACK
"${STORE[@]}" rollback --certificate-id cert-managed --revision 2 >/dev/null
"${STORE[@]}" audit >"$TMP/audit-after-rollback.json"
python3 - "$TMP/audit-after-rollback.json" <<'PYROLLBACKAUDIT'
import json,sys
v=json.load(open(sys.argv[1])); assert v['broken_references']==[] and v['orphan_secret_files']==[] and v['orphan_managed_files']==[]
PYROLLBACKAUDIT
echo "PASS: rollback cambia sólo la revisión activa y conserva el historial"
if "${STORE[@]}" import --storage-type reference --certificate-file "$TMP/cert1.pem" --private-key-file "$TMP/key2.pem" --certificate-id cert-mismatch >/dev/null 2>&1; then
 echo "FAIL: mismatched private key accepted" >&2; exit 1
fi
ln -s "$TMP/key1.pem" "$TMP/key-link.pem"
if "${STORE[@]}" import --storage-type reference --certificate-file "$TMP/cert1.pem" --private-key-file "$TMP/key-link.pem" --certificate-id cert-symlink >/dev/null 2>&1; then
 echo "FAIL: symlink private key accepted" >&2; exit 1
fi
echo "PASS: rechazo de clave no coincidente y symlink"
cp "$SECRETS/cert-managed.r000001.bin" "$TMP/good.blob"
python3 - "$SECRETS/cert-managed.r000001.bin" <<'PY'
import json,pathlib,sys,base64
p=pathlib.Path(sys.argv[1]); r=json.loads(p.read_text())
b=bytearray(base64.b64decode(r["ciphertext"])); b[-1]^=1
r["ciphertext"]=base64.b64encode(b).decode()
p.write_text(json.dumps(r,separators=(",",":"),sort_keys=True)+"\n"); p.chmod(0o600)
PY
"${STORE[@]}" audit >"$TMP/audit-tampered.json"
python3 - "$TMP/audit-tampered.json" <<'PY'
import json,sys
v=json.load(open(sys.argv[1]))
assert any(x["certificate_id"]=="cert-managed" for x in v["broken_references"])
PY
mv "$TMP/good.blob" "$SECRETS/cert-managed.r000001.bin"; chmod 600 "$SECRETS/cert-managed.r000001.bin"
echo "PASS: ciphertext alterado detectado por auditoría"
mv "$MASTER" "$MASTER.saved"
if "${STORE[@]}" audit >/dev/null 2>&1; then
 echo "FAIL: audit accepted missing master key" >&2; exit 1
fi
test ! -e "$MASTER"; mv "$MASTER.saved" "$MASTER"
echo "PASS: clave maestra ausente rechazada sin regeneración"
echo "OK: certificado centralizado managed/reference, AES-256-GCM, deduplicación, auditoría y negativos."

# Explicit v1->v2 migration: versioned copy is verified and legacy source is retained.
MIG="$TMP/migration"; mkdir -m 700 "$MIG" "$MIG/managed" "$MIG/secrets"
cp "$MANAGED/cert-managed.r000002.pem" "$MIG/managed/cert-legacy.pem"; chmod 600 "$MIG/managed/cert-legacy.pem"
cp "$SECRETS/cert-managed.r000002.bin" "$MIG/secrets/cert-legacy.r000001.bin"; chmod 600 "$MIG/secrets/cert-legacy.r000001.bin"
python3 - "$CATALOG" "$MIG/catalog.json" <<'PYMIG'
import json,pathlib,sys
cat=json.loads(pathlib.Path(sys.argv[1]).read_text()); item=next(x for x in cat['certificates'] if x['certificate_id']=='cert-managed')
item={k:v for k,v in item.items() if k not in ('active_revision','revisions')}
item['certificate_id']='cert-legacy'; item['revision']=1; item['certificate_source']='managed/cert-legacy.pem'; item['secret_ref']='secrets/cert-legacy.r000001.bin'
cat={'schema_version':1,'revision':7,'certificates':[item]}
pathlib.Path(sys.argv[2]).write_text(json.dumps(cat)+'\n'); pathlib.Path(sys.argv[2]).chmod(0o600)
PYMIG
python3 "$ROOT/scripts/certificate_store.py" --base "$MIG" --catalog "$MIG/catalog.json" --managed-dir "$MIG/managed" --secrets-dir "$MIG/secrets" --master-key "$MASTER" --lock "$MIG/catalog.lock" migrate-v1 >"$TMP/migrate.json"
python3 - "$MIG" "$TMP/migrate.json" <<'PYMIGCHECK'
import json,pathlib,sys
base=pathlib.Path(sys.argv[1]); c=json.loads((base/'catalog.json').read_text()); r=c['certificates'][0]
assert c['schema_version']==2 and r['active_revision']==1 and len(r['revisions'])==1
assert r['certificate_source']=='managed/cert-legacy.r000001.pem'
assert (base/'managed/cert-legacy.pem').is_file() and (base/'managed/cert-legacy.r000001.pem').is_file()
assert json.loads(pathlib.Path(sys.argv[2]).read_text())['legacy_files_preserved'] is True
PYMIGCHECK
echo "PASS: migración v1→v2 explícita y no destructiva"

# Unreferenced managed files and encrypted blobs are reported, never deleted.
printf 'orphan-ciphertext' >"$SECRETS/orphan.r000001.bin"
printf 'orphan-certificate' >"$MANAGED/orphan.pem"
chmod 600 "$SECRETS/orphan.r000001.bin" "$MANAGED/orphan.pem"
"${STORE[@]}" audit >"$TMP/audit-orphans.json"
python3 - "$TMP/audit-orphans.json" <<'PY'
import json,sys
v=json.load(open(sys.argv[1]))
assert 'orphan.r000001.bin' in v['orphan_secret_files']
assert 'orphan.pem' in v['orphan_managed_files']
assert v['automatic_deletion'] is False
PY
echo "PASS: detección de huérfanos sin borrado automático"

# No se permite reutilizar una huella que ya existe en una revisión histórica.
python3 - "$CATALOG" "$TMP/catalog-duplicate-history.json" <<'PYHISTORY'
import json,pathlib,sys
value=json.loads(pathlib.Path(sys.argv[1]).read_text())
record=next(x for x in value['certificates'] if x['certificate_id']=='cert-managed')
record['revisions'][1]['fingerprint_sha256']=record['revisions'][0]['fingerprint_sha256']
for field in ('fingerprint_sha256',): record[field]=record['revisions'][1][field]
path=pathlib.Path(sys.argv[2]); path.write_text(json.dumps(value)+'\n'); path.chmod(0o600)
PYHISTORY
if python3 "$ROOT/scripts/certificate_store.py" --base "$BASE" --catalog "$TMP/catalog-duplicate-history.json" --managed-dir "$MANAGED" --secrets-dir "$SECRETS" --master-key "$MASTER" --lock "$LOCK" list >/dev/null 2>&1; then
    echo 'FAIL: se aceptó una huella repetida en el historial' >&2; exit 1
fi
echo 'PASS: rechazo de huellas duplicadas entre revisiones históricas'

# Una colisión de destino versionado incorrecto bloquea migración y preserva catálogo v1.
MIG_BAD="$TMP/migration-collision"; mkdir -m 700 "$MIG_BAD" "$MIG_BAD/managed" "$MIG_BAD/secrets"
cp "$MANAGED/cert-managed.r000002.pem" "$MIG_BAD/managed/cert-collision.pem"; chmod 600 "$MIG_BAD/managed/cert-collision.pem"
cp "$SECRETS/cert-managed.r000002.bin" "$MIG_BAD/secrets/cert-collision.r000001.bin"; chmod 600 "$MIG_BAD/secrets/cert-collision.r000001.bin"
printf 'different certificate bytes' > "$MIG_BAD/managed/cert-collision.r000001.pem"; chmod 600 "$MIG_BAD/managed/cert-collision.r000001.pem"
python3 - "$CATALOG" "$MIG_BAD/catalog.json" <<'PYCOLLISION'
import json,pathlib,sys
cat=json.loads(pathlib.Path(sys.argv[1]).read_text()); item=next(x for x in cat['certificates'] if x['certificate_id']=='cert-managed')
item={k:v for k,v in item.items() if k not in ('active_revision','revisions')}
item['certificate_id']='cert-collision'; item['revision']=1; item['certificate_source']='managed/cert-collision.pem'; item['secret_ref']='secrets/cert-collision.r000001.bin'
p=pathlib.Path(sys.argv[2]); p.write_text(json.dumps({'schema_version':1,'revision':2,'certificates':[item]})+'\n'); p.chmod(0o600)
PYCOLLISION
if python3 "$ROOT/scripts/certificate_store.py" --base "$MIG_BAD" --catalog "$MIG_BAD/catalog.json" --managed-dir "$MIG_BAD/managed" --secrets-dir "$MIG_BAD/secrets" --master-key "$MASTER" --lock "$MIG_BAD/catalog.lock" migrate-v1 >/dev/null 2>&1; then
    echo 'FAIL: migración aceptó destino versionado conflictivo' >&2; exit 1
fi
python3 - "$MIG_BAD/catalog.json" <<'PYCOLLISIONCHECK'
import json,pathlib,sys
assert json.loads(pathlib.Path(sys.argv[1]).read_text())['schema_version']==1
PYCOLLISIONCHECK
echo 'PASS: colisión de destino migrado bloqueada sin cambiar catálogo legacy'
