#!/usr/bin/env bash
# Bloqueos no bloqueantes para coordinar operaciones de ciclo de vida del Manager.

manager_lock_path_is_safe() {
    local path="$1" current="" segment
    local -a parts=()
    [[ "$path" == /* && "$path" != "/" && "$path" != *"/../"* && "$path" != */.. ]] || return 1
    IFS='/' read -r -a parts <<<"${path#/}"
    for segment in "${parts[@]}"; do
        [[ -n "$segment" ]] || continue
        current+="/$segment"
        [[ ! -L "$current" ]] || return 1
    done
}

manager_lock_acquire() {
    local lock_path="$1" fd_name="$2" lock_dir
    local -n fd_ref="$fd_name"
    command -v flock >/dev/null 2>&1 || return 1
    manager_lock_path_is_safe "$lock_path" || return 1
    lock_dir="$(dirname -- "$lock_path")"
    mkdir -p -- "$lock_dir" || return 1
    manager_lock_path_is_safe "$lock_path" || return 1
    if [[ -e "$lock_path" && ! -f "$lock_path" ]]; then
        printf 'La ruta de bloqueo no es un archivo regular: %s\n' "$lock_path" >&2
        return 1
    fi
    (
        umask 077
        : >>"$lock_path"
    ) || return 1
    chmod 600 "$lock_path" || return 1
    exec {fd_ref}>>"$lock_path" || return 1
    if ! flock -n "$fd_ref"; then
        exec {fd_ref}>&-
        return 1
    fi
}

manager_lock_release() {
    local fd="$1"
    [[ "$fd" =~ ^[0-9]+$ ]] || return 0
    flock -u "$fd" 2>/dev/null || true
    exec {fd}>&- 2>/dev/null || true
    return 0
}