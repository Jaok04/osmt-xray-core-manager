#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
python3 - "$ROOT" <<'PY'
import json
import struct
import sys
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root / "scripts"))
import shared_backup_format as fmt

password = "Correct horse battery staple 2026"
payload = b"XRAY-MANAGER-SHARED-SNAPSHOT\x00" + bytes(range(256)) * 8
package = fmt.encrypt_payload(payload, password)
assert package.startswith(fmt.MAGIC)
assert fmt.decrypt_payload(package, password) == payload
assert package != fmt.encrypt_payload(payload, password), "salt/nonce deben ser aleatorios"

def must_fail(candidate, phrase=password):
    try:
        fmt.decrypt_payload(candidate, phrase)
    except fmt.SharedBackupFormatError:
        return
    raise AssertionError("se aceptó paquete o contraseña inválidos")

must_fail(package, "Wrong password that is long enough")
must_fail(package[:-1])
tampered = bytearray(package)
tampered[-1] ^= 1
must_fail(bytes(tampered))
tampered_header = bytearray(package)
tampered_header[fmt.MAGIC.__len__() + 4 + 5] ^= 1
must_fail(bytes(tampered_header))
must_fail(b"NOTXRAY!" + package[len(fmt.MAGIC):])
must_fail(package + b"trailing-data")
# Parámetros KDF alterados en una cabecera canónica deben rechazarse antes de
# ejecutar scrypt, incluso si el atacante actualiza la longitud de cabecera.
header_len = struct.unpack(">I", package[len(fmt.MAGIC):len(fmt.MAGIC) + 4])[0]
header_start = len(fmt.MAGIC) + 4
header_end = header_start + header_len
header = json.loads(package[header_start:header_end])
header["kdf_params"]["n"] = 2**14
header_bytes = json.dumps(header, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
forged = fmt.MAGIC + struct.pack(">I", len(header_bytes)) + header_bytes + package[header_end:]
must_fail(forged)
for invalid in ["", "short", "x" * 11, "nul\x00character-passphrase"]:
    try:
        fmt.encrypt_payload(payload, invalid)
    except fmt.SharedBackupFormatError:
        pass
    else:
        raise AssertionError("se aceptó contraseña débil/no válida")
for invalid_payload in [b"", "not bytes", None]:
    try:
        fmt.encrypt_payload(invalid_payload, password)
    except fmt.SharedBackupFormatError:
        pass
    else:
        raise AssertionError("se aceptó payload inválido")

print("PASS: formato v1, scrypt perfil fijo, AES-256-GCM, AAD, aleatoriedad, límites y fail-closed.")
PY
