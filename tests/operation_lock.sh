#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/lib/operation_lock.sh"
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
lock="$tmp/lifecycle.lock"
first_fd='' second_fd='' unsafe_fd=''
manager_lock_acquire "$lock" first_fd
[[ "$(stat -c '%a' "$lock")" == 600 ]]
if manager_lock_acquire "$lock" second_fd; then
    printf 'ERROR: se adquirió dos veces el mismo bloqueo exclusivo.\n' >&2
    exit 1
fi
manager_lock_release "$first_fd"
manager_lock_acquire "$lock" second_fd
manager_lock_release "$second_fd"
mkdir -p "$tmp/target"
ln -s "$tmp/target" "$tmp/symlink"
if manager_lock_acquire "$tmp/symlink/unsafe.lock" unsafe_fd; then
    printf 'ERROR: se aceptó una ruta de bloqueo con componente simbólico.\n' >&2
    exit 1
fi
[[ -z "$unsafe_fd" ]]
printf 'OK: bloqueo exclusivo no bloqueante, liberación, permisos privados y rechazo de rutas simbólicas.\n'
