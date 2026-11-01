#!/usr/bin/env bash
# Sustitución durable de JSON ya generado y validado en un temporal del mismo directorio.
json_store_commit() {
	[[ "$#" -eq 3 ]] || return 2
	local tmp="$1" destination="$2" mode="$3"
	command -v python3 >/dev/null 2>&1 || return 1
	python3 - "$tmp" "$destination" "$mode" <<'PY'
import os, stat, sys
src, dst, mode = sys.argv[1:]
parent = os.path.dirname(os.path.abspath(dst))
if os.path.dirname(os.path.abspath(src)) != parent:
    raise SystemExit('temporal y destino deben estar en el mismo directorio')
if os.path.islink(dst) or not stat.S_ISREG(os.stat(src, follow_symlinks=False).st_mode):
    raise SystemExit('origen/destino no es un archivo regular seguro')
fd = os.open(src, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
try:
    os.fchmod(fd, int(mode, 8))
    os.fsync(fd)
finally:
    os.close(fd)
os.replace(src, dst)
dirfd = os.open(parent, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
try:
    try:
        os.fsync(dirfd)
    except OSError as exc:
        print(f'JSON reemplazado, pero falló fsync del directorio: {exc}', file=sys.stderr)
        raise SystemExit(3)
finally:
    os.close(dirfd)
PY
}
