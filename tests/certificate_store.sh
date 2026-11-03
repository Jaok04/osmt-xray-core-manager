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
assert catalog["schema_version"]==1 and len(catalog["certificates"])==1
record=catalog["certificates"][0]
assert record["storage_type"]=="managed"
assert record["certificate_source"]=="managed/cert-managed.pem"
assert record["secret_ref"]=="secrets/cert-managed.r000001.bin"
assert "private_key" not in record and "key_file" not in record
assert pathlib.Path(sys.argv[3],"cert-managed.pem").is_file()
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
