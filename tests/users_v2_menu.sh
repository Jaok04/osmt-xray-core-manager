#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
OUT="$TMP/out"
trap 'rm -rf "$TMP"' EXIT
export APP_ROOT="$ROOT"
export XRAY_MANAGER_USERS_DIR="$TMP/data"
export XRAY_MANAGER_USERS_FILE="$TMP/data/users.json"
export XRAY_MANAGER_CONNECTIONS_FILE="$TMP/data/connections.json"
export XRAY_MANAGER_INTEGRITY_LOCK="$TMP/run/integrity.lock"
mkdir -p "$TMP/data" "$TMP/run"
printf '[{"id":"conn-vless","protocol_id":"vless_ws","max_users":3}]\n' >"$XRAY_MANAGER_CONNECTIONS_FILE"
source "$ROOT/lib/ui.sh"
source "$ROOT/modules/users.sh"
source "$ROOT/modules/users_v2.sh"
source "$ROOT/modules/users_v2_menu.sh"

# El arreglo legacy sigue entrando al menú antiguo.
printf '[]\n' >"$XRAY_MANAGER_USERS_FILE"
printf '0\n' | users_menu_dispatch >"$OUT"
grep -q 'GESTIÓN DE USUARIOS VLESS' "$OUT"

# El documento v2 abre su menú y la vista no expone la credencial.
cat >"$XRAY_MANAGER_USERS_FILE" <<'JSON'
{
  "schema_version": 2,
  "identities": [{"id":"11111111-1111-4111-8111-111111111111","created_at":"2026-11-01T00:00:00Z"}],
  "associations": [{
    "id":"22222222-2222-4222-8222-222222222222",
    "identity_id":"11111111-1111-4111-8111-111111111111",
    "connection_id":"conn-vless",
    "alias":"Cliente demo",
    "protocol":"vless",
    "credential":{"type":"uuid","value":"33333333-3333-4333-8333-333333333333"},
    "created_at":"2026-11-01T00:00:00Z",
    "duration":{"kind":"unlimited"},
    "expires_at":null,
    "suspended_at":null,
    "remaining_seconds":null,
    "traffic_limit_bytes":null,
    "simultaneous_connection_limit":null,
    "state":"active",
    "provisioning_status":"draft",
    "runtime":{"status":"not_applied","last_applied_at":null}
  }]
}
JSON
printf '1\n\n0\n' | users_menu_dispatch >"$OUT"
grep -q 'GESTIÓN DE IDENTIDADES Y ASOCIACIONES (V2)' "$OUT"
grep -q 'Cliente demo' "$OUT"
grep -q 'Identidad: 11111111-1111-4111-8111-111111111111' "$OUT"
if grep -q '33333333-3333-4333-8333-333333333333' "$OUT"; then
  echo 'ERROR: la vista mostró una credencial sensible.' >&2
  exit 1
fi

# Resumen correcto, sin escribir en el documento.
printf '2\n\n0\n' | users_menu_dispatch >"$OUT"
grep -q 'Identidades: 1' "$OUT"
grep -q 'Asociaciones: 1' "$OUT"
grep -q 'Activas: 1' "$OUT"
grep -q 'VLESS: 1' "$OUT"

# JSON corrupto y esquema desconocido se bloquean sin alteración.
printf '{invalid json\n' >"$XRAY_MANAGER_USERS_FILE"
cp "$XRAY_MANAGER_USERS_FILE" "$TMP/corrupt.before"
if printf '\n' | users_menu_dispatch >"$OUT" 2>&1; then
  echo 'ERROR: se aceptó un registro corrupto.' >&2
  exit 1
fi
cmp -s "$TMP/corrupt.before" "$XRAY_MANAGER_USERS_FILE"
grep -q 'JSON inválido' "$OUT"

printf '{"schema_version":99}\n' >"$XRAY_MANAGER_USERS_FILE"
cp "$XRAY_MANAGER_USERS_FILE" "$TMP/unknown.before"
if printf '\n' | users_menu_dispatch >"$OUT" 2>&1; then
  echo 'ERROR: se aceptó un esquema desconocido.' >&2
  exit 1
fi
cmp -s "$TMP/unknown.before" "$XRAY_MANAGER_USERS_FILE"
grep -q 'esquema desconocido' "$OUT"

echo 'OK: selector legacy/v2, consulta sin secretos, resumen, bloqueo de JSON corrupto y esquema desconocido.'
