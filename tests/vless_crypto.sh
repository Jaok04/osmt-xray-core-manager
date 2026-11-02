#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT
python3 - "$ROOT" "$TMP" <<'PY'
import importlib.util, os, stat, sys
from pathlib import Path
root, temp = map(Path, sys.argv[1:])
spec = importlib.util.spec_from_file_location("vless_crypto", root / "scripts/vless_crypto.py")
vault = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = vault
spec.loader.exec_module(vault)
base = temp / "keys"
key_path = base / "master.key"
vault.ensure_master_key(key_path)
key = vault.load_master_key(key_path)
assert len(key) == 32
assert stat.S_IMODE(base.stat().st_mode) == 0o700
assert stat.S_IMODE(key_path.stat().st_mode) == 0o600
assert vault.ensure_master_key(key_path) == key_path
assert vault.load_master_key(key_path) == key
secret = b"private-reality-key-NEVER-LOG"
blob = vault.encrypt_secret(secret, key, "conn-test", 3)
assert vault.decrypt_secret(blob, key, "conn-test", 3) == secret
assert blob != vault.encrypt_secret(secret, key, "conn-test", 3)
for args in [(blob,key,"other-connection",3),(blob,key,"conn-test",4),
             (blob[:-1]+bytes([blob[-1]^1]),key,"conn-test",3),
             (blob,bytes([key[0]^1])+key[1:],"conn-test",3)]:
    try: vault.decrypt_secret(*args)
    except vault.VaultError: pass
    else: raise AssertionError("blob manipulado aceptado")
for bad_id in ["","../escape","conn/test","x"*129]:
    try: vault.encrypt_secret(secret,key,bad_id)
    except vault.VaultError: pass
    else: raise AssertionError(f"ID inválido aceptado: {bad_id!r}")
blob_dir=temp/"blobs"; blob_dir.mkdir(mode=0o700)
vault.write_encrypted_blob(blob_dir/"conn-test.json",blob)
saved=blob_dir/"conn-test.json"
assert stat.S_IMODE(saved.stat().st_mode)==0o600
assert vault.decrypt_secret(vault.read_encrypted_blob(saved),key,"conn-test",3)==secret
link=blob_dir/"link.json"; link.symlink_to(saved)
try: vault.read_encrypted_blob(link)
except vault.VaultError: pass
else: raise AssertionError("se aceptó symlink")
os.chmod(saved,0o644)
try: vault.read_encrypted_blob(saved)
except vault.VaultError: pass
else: raise AssertionError("se aceptó blob con permisos 0644")
missing=base/"missing.key"
try: vault.load_master_key(missing)
except vault.VaultError: pass
else: raise AssertionError("se aceptó clave ausente")
assert not missing.exists()
os.chmod(key_path,0o644)
try: vault.ensure_master_key(key_path)
except vault.VaultError: pass
else: raise AssertionError("se aceptó clave maestra 0644")
print("OK: AES-256-GCM, autenticación AAD/tag, nonce aleatorio, clave idempotente, fail-closed, escritura atómica y permisos.")
PY
