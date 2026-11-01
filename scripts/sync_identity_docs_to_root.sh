#!/usr/bin/env bash
set -Eeuo pipefail

SOURCE="/opt/xray-manager/docs/DISENO_IDENTIDADES_ASOCIACIONES_V1.md"
DEST="/root/DISENO_IDENTIDADES_ASOCIACIONES_V1.md"
TMP="${DEST}.tmp.$$"

cleanup() {
  rm -f -- "$TMP"
}
trap cleanup EXIT

if [[ ! -s "$SOURCE" ]]; then
  printf 'ERROR: no existe el documento fuente o está vacío: %s\n' "$SOURCE" >&2
  exit 1
fi

install -o root -g root -m 0600 -- "$SOURCE" "$TMP"
mv -f -- "$TMP" "$DEST"

SOURCE_HASH="$(sha256sum "$SOURCE" | awk '{print $1}')"
DEST_HASH="$(sha256sum "$DEST" | awk '{print $1}')"

if [[ "$SOURCE_HASH" != "$DEST_HASH" ]]; then
  printf 'ERROR: los hashes no coinciden. Fuente=%s Destino=%s\n' "$SOURCE_HASH" "$DEST_HASH" >&2
  exit 1
fi

printf 'OK: documentación sincronizada.\nSHA256: %s\nDestino: %s\n' "$DEST_HASH" "$DEST"