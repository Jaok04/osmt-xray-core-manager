#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
python3 - "$ROOT" <<'PY'
import io
import os
import stat
import sys
import tempfile
import zipfile
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root / "scripts"))
import shared_backup_zip as z
import shared_backup_format as crypto


def entries(data=b"payload"):
    return [
        z.ZipMember.from_bytes("manifest.json", b'{"manifest":1}'),
        z.ZipMember.from_bytes("index.json", b'{"index":1}'),
        z.ZipMember.from_bytes("connections/a.json", data),
        z.ZipMember.from_bytes("connections/z.bin", b"\x00\x01\xff"),
    ]


members = entries()
out = io.BytesIO()
size = z.write_zip_stream(members, out, chunk_size=2)
archive = out.getvalue()
assert size == len(archive)
assert size == z._validate_members(members)[1]
reader = z.ZipStream(members, chunk_size=11)
first = reader.read(7)
rest = reader.read()
assert len(first) + len(rest) == reader.size
assert first + rest == archive
with zipfile.ZipFile(io.BytesIO(archive), "r") as package:
    assert package.namelist() == ["manifest.json", "index.json", "connections/a.json", "connections/z.bin"]
    assert all(info.compress_type == zipfile.ZIP_STORED for info in package.infolist())
    assert all(info.file_size == info.compress_size for info in package.infolist())
    assert package.read("connections/a.json") == b"payload"
    assert package.read("connections/z.bin") == b"\x00\x01\xff"
    assert package.testzip() is None

again = io.BytesIO()
assert z.write_zip_stream(members, again, chunk_size=7) == size
assert again.getvalue() == archive, "ZIP debe ser determinista"

# El ZIP determinista puede cifrarse y verificarse sin materializar otro ZIP.
password = "Correct horse battery staple 2026"
encrypted = io.BytesIO()
zip_source = z.ZipStream(members, chunk_size=13)
assert zip_source.size == len(archive)
assert crypto.encrypt_payload_stream(zip_source, encrypted, zip_source.size, password, chunk_size=17) == len(encrypted.getvalue())
assert crypto.verify_package_stream(io.BytesIO(encrypted.getvalue()), password) == len(encrypted.getvalue())
restored_zip = crypto.decrypt_payload(encrypted.getvalue(), password)
with zipfile.ZipFile(io.BytesIO(restored_zip), "r") as package:
    assert package.testzip() is None
    assert package.read("connections/a.json") == b"payload"

for bad in ("/absolute", "../escape", "a/../b", "a\\b", "C:/drive", "a//b", "a/./b", "bad\x00name", "cafe\u0301"):
    try:
        z.ZipMember.from_bytes(bad, b"x")
    except z.SharedBackupZipError:
        pass
    else:
        raise AssertionError(f"ruta insegura aceptada: {bad!r}")

# Colisiones exactas y case-folded.
for duplicate_set in (
    [z.ZipMember.from_bytes("manifest.json", b"{}"), z.ZipMember.from_bytes("index.json", b"{}"), z.ZipMember.from_bytes("a", b"1"), z.ZipMember.from_bytes("a", b"2")],
    [z.ZipMember.from_bytes("manifest.json", b"{}"), z.ZipMember.from_bytes("index.json", b"{}"), z.ZipMember.from_bytes("A", b"1"), z.ZipMember.from_bytes("a", b"2")],
):
    try:
        z.write_zip_stream(duplicate_set, io.BytesIO())
    except z.SharedBackupZipError:
        pass
    else:
        raise AssertionError("se aceptó nombre duplicado/colisión")

# Fuentes regenerables permiten transformar JSON sin acumular todos los miembros.
factory_state = [b"generated-v1"]
factory_member = z.ZipMember.from_factory("generated/config.json", lambda: io.BytesIO(factory_state[0]))
factory_zip = io.BytesIO()
z.write_zip_stream([z.ZipMember.from_bytes("manifest.json", b"{}"), z.ZipMember.from_bytes("index.json", b"{}"), factory_member], factory_zip)
with zipfile.ZipFile(io.BytesIO(factory_zip.getvalue())) as package:
    assert package.read("generated/config.json") == b"generated-v1"
factory_state[0] = b"generated-v2-different"
try:
    z.write_zip_stream([z.ZipMember.from_bytes("manifest.json", b"{}"), z.ZipMember.from_bytes("index.json", b"{}"), factory_member], io.BytesIO())
except z.SharedBackupZipError:
    pass
else:
    raise AssertionError("se aceptó factory regenerable que cambió tras el preflight")

# Límites de entrada: 10.000 totales sí; 10.001 no.
maximum = [z.ZipMember.from_bytes("manifest.json", b"{}"), z.ZipMember.from_bytes("index.json", b"{}")]
maximum.extend(z.ZipMember.from_bytes(f"members/{i:05d}", b"") for i in range(z.MAX_ENTRIES - 2))
max_out = io.BytesIO()
assert z.write_zip_stream(maximum, max_out) <= z.MAX_ZIP_BYTES
assert len(max_out.getvalue()) == z._validate_members(maximum)[1]
excess = maximum + [z.ZipMember.from_bytes("zz-extra", b"")]
untouched = io.BytesIO()
try:
    z.write_zip_stream(excess, untouched)
except z.SharedBackupZipError:
    pass
else:
    raise AssertionError("se aceptaron más de 10.000 entradas")
assert untouched.getvalue() == b"", "fallo de preflight no debe escribir bytes"

# Tamaño ZIP total incluye headers y directorio central.
oversized = [z.ZipMember.from_bytes("manifest.json", b"{}"), z.ZipMember.from_bytes("index.json", b"{}"), z.ZipMember(
    "large/member", z.MAX_ZIP_BYTES, 0, "0" * 64, b"", None
)]
try:
    z.write_zip_stream(oversized, io.BytesIO())
except z.SharedBackupZipError:
    pass
else:
    raise AssertionError("se aceptó ZIP que excede 512 MiB incluyendo overhead")

# Origen en disco: root:root 0600, sin symlink/hardlink, estable entre preflight y emisión.
with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    source = base / "source.bin"
    source.write_bytes(b"first version")
    source.chmod(0o600)
    prepared = z.ZipMember.from_path("data/source.bin", source, allowed_root=base)
    file_members = [z.ZipMember.from_bytes("manifest.json", b"{}"), z.ZipMember.from_bytes("index.json", b"{}"), prepared]
    file_out = io.BytesIO()
    z.write_zip_stream(file_members, file_out)
    with zipfile.ZipFile(io.BytesIO(file_out.getvalue())) as package:
        assert package.read("data/source.bin") == b"first version"

    changed = z.ZipMember.from_path("data/changed.bin", source, allowed_root=base)
    source.write_bytes(b"second version")
    source.chmod(0o600)
    try:
        z.write_zip_stream([z.ZipMember.from_bytes("manifest.json", b"{}"), z.ZipMember.from_bytes("index.json", b"{}"), changed], io.BytesIO())
    except z.SharedBackupZipError:
        pass
    else:
        raise AssertionError("se aceptó origen cambiado después del preflight")

    linked_parent = base / "linked-parent"
    linked_parent.symlink_to(base, target_is_directory=True)
    try:
        z.ZipMember.from_path("data/parent-link.bin", linked_parent / "source.bin", allowed_root=base)
    except z.SharedBackupZipError:
        pass
    else:
        raise AssertionError("se aceptó componente padre symlink")

    outside = Path(tmp).parent / (Path(tmp).name + "-outside")
    outside.write_bytes(b"outside")
    outside.chmod(0o600)
    try:
        z.ZipMember.from_path("data/outside.bin", outside, allowed_root=base)
    except z.SharedBackupZipError:
        pass
    else:
        raise AssertionError("se aceptó origen fuera del directorio autorizado")
    finally:
        outside.unlink(missing_ok=True)

    link = base / "link.bin"
    link.symlink_to(source)
    try:
        z.ZipMember.from_path("data/link.bin", link, allowed_root=base)
    except z.SharedBackupZipError:
        pass
    else:
        raise AssertionError("se aceptó symlink")

    hard = base / "hard.bin"
    os.link(source, hard)
    try:
        z.ZipMember.from_path("data/hard.bin", hard, allowed_root=base)
    except z.SharedBackupZipError:
        pass
    else:
        raise AssertionError("se aceptó hardlink")

    unsafe_dir = base / "unsafe"
    unsafe_dir.mkdir()
    unsafe_dir.chmod(0o700)
    unsafe_file = unsafe_dir / "data.bin"
    unsafe_file.write_bytes(b"x")
    unsafe_file.chmod(0o644)
    try:
        z.ZipMember.from_path("data/unsafe.bin", unsafe_file, allowed_root=base)
    except z.SharedBackupZipError:
        pass
    else:
        raise AssertionError("se aceptó archivo con permisos no seguros")

print("PASS: ZIP_STORED determinista, paths seguros, hashes/CRC, 10.000 entradas, 512 MiB, TOCTOU, symlink y hardlink.")
PY
