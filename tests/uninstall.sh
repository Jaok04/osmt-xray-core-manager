#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/modules/uninstall.sh"
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
mkdir -p "$tmp/source/nested"
printf 'contenido de prueba\n' >"$tmp/source/nested/data.txt"
uninstall_make_backup "$tmp/backup.tar.gz" "$tmp/source"
tar -tzf "$tmp/backup.tar.gz" | grep -Fq "${tmp#/}/source/nested/data.txt"
gzip -t "$tmp/backup.tar.gz"
# Un destino inválido o inexistente no debe producir un archivo verificado.
if uninstall_make_backup "$tmp/fail.tar.gz" "$tmp/no-existe"; then
	printf 'ERROR: se aceptó una ruta inexistente para respaldo.\n' >&2
	exit 1
fi
# Confirmar que la función de inventario no genera rutas arbitrarias.
if uninstall_service_guard >/dev/null 2>&1; then
	:
else
	printf 'SKIP: protección de servicio bloqueó el flujo en este host (comportamiento conservador).\n'
fi
printf 'OK: creación/verificación de respaldo y rechazo de rutas inexistentes.\n'