#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
python3 - "$ROOT/scripts/vless_backup.py" <<'PY'
import hashlib, importlib.util, io, pathlib, sys, tarfile
spec=importlib.util.spec_from_file_location('vless_backup',sys.argv[1]); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
mod.MAX_TOTAL_UNCOMPRESSED=6
mod.MAX_MEMBER=8

def archive(entries):
    out=io.BytesIO()
    with tarfile.open(fileobj=out,mode='w:gz') as tar:
        for name,data,kind in entries:
            info=tarfile.TarInfo(name); info.mode=0o600
            if kind=='file':
                info.size=len(data); tar.addfile(info,io.BytesIO(data))
            else:
                info.type=tarfile.SYMTYPE; info.linkname='connections/connections.json'; tar.addfile(info)
    return out.getvalue()

def manifest(items):
    return {'files':[{'path':n,'size':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in items]}

items=[('connections/a',b'1234'),('secrets/b',b'5678')]
try:
    mod._read_archive_members(archive([(n,b,'file') for n,b in items]),manifest(items),retain=True)
    raise AssertionError('se aceptó tamaño agregado superior al límite')
except mod.BackupError as e:
    assert 'agregado' in str(e)

# La ruta traversal se rechaza de forma autónoma, sin depender de verify_data_dir.
items=[('connections/../outside',b'x')]
try:
    mod._read_archive_members(archive([(n,b,'file') for n,b in items]),manifest(items),retain=True)
    raise AssertionError('se aceptó ruta traversal')
except mod.BackupError: pass

# Enlaces simbólicos y hardlinks no son miembros regulares aceptables.
items=[('connections/link',b'',)]
try:
    mod._read_archive_members(archive([('connections/link',b'','symlink')]),manifest([('connections/link',b'')]),retain=True)
    raise AssertionError('se aceptó symlink')
except mod.BackupError: pass

# El flujo normal y el hash individual siguen funcionando.
mod.MAX_TOTAL_UNCOMPRESSED=16
items=[('connections/connections.json',b'[]')]
result=mod._read_archive_members(archive([(n,b,'file') for n,b in items]),manifest(items),retain=True)
assert result=={'connections/connections.json':b'[]'}
print('PASS: límite agregado, rechazo autónomo de traversal/symlink y validación positiva')
PY
