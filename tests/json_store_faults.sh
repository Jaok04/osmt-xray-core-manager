#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
REAL_PYTHON="$(command -v python3)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$TMP/bin" "$TMP/store"
cat >"$TMP/bin/python3" <<'WRAPPER'
#!/usr/bin/env bash
set -eu
script="$(mktemp "${TMPDIR:-/tmp}/json-store-python.XXXXXX")"
trap 'rm -f "$script"' EXIT
cat >"$script"
{
  cat <<'PATCH'
import os, sys, time
sys.excepthook = lambda *_: None
_real_fsync = os.fsync
_fsync_count = 0
def _controlled_fsync(fd):
    global _fsync_count
    _fsync_count += 1
    fail_at = os.environ.get('JSON_STORE_FAIL_FSYNC')
    if fail_at and _fsync_count == int(fail_at):
        raise OSError(5, 'injected fsync failure')
    pause_at = os.environ.get('JSON_STORE_PAUSE_FSYNC')
    if pause_at and _fsync_count == int(pause_at):
        with open(os.environ['JSON_STORE_MARKER'], 'w') as marker:
            marker.write(str(os.getpid()))
        while True:
            time.sleep(1)
    return _real_fsync(fd)
os.fsync = _controlled_fsync
_real_replace = os.replace
def _controlled_replace(src, dst):
    pause = os.environ.get('JSON_STORE_PAUSE_REPLACE')
    if pause:
        with open(os.environ['JSON_STORE_MARKER'], 'w') as marker:
            marker.write(str(os.getpid()))
        while True:
            time.sleep(1)
    return _real_replace(src, dst)
os.replace = _controlled_replace
PATCH
  cat "$script"
} | "${JSON_STORE_REAL_PYTHON:?}" "$@"
WRAPPER
chmod 700 "$TMP/bin/python3"
export JSON_STORE_REAL_PYTHON="$REAL_PYTHON"

new_tmp() {
	local name="$1"
	printf '%s\n' "$name" >"$TMP/store/$name.tmp"
	printf '%s.tmp\n' "$name"
}
commit_with() {
	local temp="$1"
	shift
	# shellcheck disable=SC2016
	PATH="$TMP/bin:$PATH" "$@" bash -c 'source "$1/lib/json_store.sh"; json_store_commit "$2" "$3" 600' _ "$ROOT" "$TMP/store/$temp" "$TMP/store/data.json"
}

# 1) Fallo en fsync del temporal: no debe sustituir el destino anterior.
printf '%s\n' '{"generation":"old"}' >"$TMP/store/data.json"
printf '%s\n' '{"generation":"new"}' >"$TMP/store/file-fsync.tmp"
if JSON_STORE_FAIL_FSYNC=1 commit_with file-fsync.tmp; then
	echo 'ERROR: se esperaba fallo inyectado en fsync del archivo.' >&2
	exit 1
fi
jq -e '.generation == "old"' "$TMP/store/data.json" >/dev/null
[[ -f "$TMP/store/file-fsync.tmp" ]]

# 2) Fallo en fsync del directorio: rename ya ocurrió; se informa fallo,
#    pero el nuevo destino queda visible. No se afirma rollback.
printf '%s\n' '{"generation":"new"}' >"$TMP/store/dir-fsync.tmp"
set +e
JSON_STORE_FAIL_FSYNC=2 commit_with dir-fsync.tmp
rc=$?
set -e
[[ "$rc" == 3 ]] || {
	echo "ERROR: se esperaba código 3 para reemplazo aplicado sin fsync de directorio (recibido $rc)." >&2
	exit 1
}
jq -e '.generation == "new"' "$TMP/store/data.json" >/dev/null

# 3) Muerte antes del replace: debe permanecer el destino anterior.
printf '%s\n' '{"generation":"old"}' >"$TMP/store/data.json"
printf '%s\n' '{"generation":"new"}' >"$TMP/store/pre-replace.tmp"
JSON_STORE_MARKER="$TMP/pre-replace.pid" JSON_STORE_PAUSE_REPLACE=1 PATH="$TMP/bin:$PATH" bash -c 'source "$1/lib/json_store.sh"; json_store_commit "$2" "$3" 600' _ "$ROOT" "$TMP/store/pre-replace.tmp" "$TMP/store/data.json" >/dev/null 2>&1 &
worker=$!
for _ in $(seq 1 500); do
	[[ -s "$TMP/pre-replace.pid" ]] && break
	sleep 0.01
done
[[ -s "$TMP/pre-replace.pid" ]] || {
	echo 'ERROR: no se alcanzó barrera pre-replace.' >&2
	exit 1
}
python_pid="$(<"$TMP/pre-replace.pid")"
kill -KILL "$python_pid"
wait "$worker" 2>/dev/null || true
jq -e '.generation == "old"' "$TMP/store/data.json" >/dev/null

# 4) Muerte después del replace y antes del fsync del directorio: el nuevo
#    archivo debe estar visible; su durabilidad ante pérdida eléctrica no
#    puede deducirse de una prueba de proceso.
printf '%s\n' '{"generation":"new"}' >"$TMP/store/post-replace.tmp"
JSON_STORE_MARKER="$TMP/post-replace.pid" JSON_STORE_PAUSE_FSYNC=2 PATH="$TMP/bin:$PATH" bash -c 'source "$1/lib/json_store.sh"; json_store_commit "$2" "$3" 600' _ "$ROOT" "$TMP/store/post-replace.tmp" "$TMP/store/data.json" >/dev/null 2>&1 &
worker=$!
for _ in $(seq 1 500); do
	[[ -s "$TMP/post-replace.pid" ]] && break
	sleep 0.01
done
[[ -s "$TMP/post-replace.pid" ]] || {
	echo 'ERROR: no se alcanzó barrera post-replace.' >&2
	exit 1
}
python_pid="$(<"$TMP/post-replace.pid")"
kill -KILL "$python_pid"
wait "$worker" 2>/dev/null || true
jq -e '.generation == "new"' "$TMP/store/data.json" >/dev/null

# El destino final debe ser JSON válido y privado.
jq -e . "$TMP/store/data.json" >/dev/null
[[ "$(stat -c '%a' "$TMP/store/data.json")" == 600 ]]
echo 'OK: fallos de fsync y terminación abrupta antes/después del replace; estado visible coherente y sin JSON parcial.'