#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
CUTOVER="$ROOT/scripts/users_v2_cutover.py"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export USERS_V2_CUTOVER_USERS_FILE="$TMP/users/users.json"
export USERS_V2_CUTOVER_CONNECTIONS_FILE="$TMP/connections/connections.json"
export USERS_V2_CUTOVER_LOCK_FILE="$TMP/run/integrity.lock"
export USERS_V2_CUTOVER_BACKUP_ROOT="$TMP/backups"
mkdir -p "$TMP/users" "$TMP/connections" "$TMP/run" "$TMP/backups"

write_fixture() {
	cat >"$USERS_V2_CUTOVER_USERS_FILE" <<'JSON'
[
  {"uuid":"11111111-1111-4111-8111-111111111111","connection_id":"conn-vless-test","label":"Fixture user","state":"draft","runtime_applied":false,"created_at":"2026-11-01T00:00:00Z"}
]
JSON
	cat >"$USERS_V2_CUTOVER_CONNECTIONS_FILE" <<'JSON'
[
  {"id":"conn-vless-test","protocol_id":"vless_ws","max_users":2}
]
JSON
}

write_fixture
ORIGINAL_SHA="$(sha256sum "$USERS_V2_CUTOVER_USERS_FILE" | awk '{print $1}')"
DRY="$("$CUTOVER" --dry-run --state active)"
[[ "$(sha256sum "$USERS_V2_CUTOVER_USERS_FILE" | awk '{print $1}')" == "$ORIGINAL_SHA" ]]
APPLY_TOKEN="$(sed -n 's/^Token para aplicar: //p' <<<"$DRY")"
[[ -n "$APPLY_TOKEN" ]]
APPLIED="$("$CUTOVER" --apply --state active --confirm "$APPLY_TOKEN")"
BACKUP="$(sed -n 's/^Backup: //p' <<<"$APPLIED")"
jq -e '.schema_version == 2 and (.identities|length)==1 and (.associations|length)==1 and .associations[0].provisioning_status=="draft"' "$USERS_V2_CUTOVER_USERS_FILE" >/dev/null
ROLLBACK_INFO="$("$CUTOVER" --rollback "$BACKUP")"
ROLLBACK_TOKEN="$(sed -n 's/.*Token requerido: //p' <<<"$ROLLBACK_INFO")"
"$CUTOVER" --rollback "$BACKUP" --confirm "$ROLLBACK_TOKEN" >/dev/null
[[ "$(sha256sum "$USERS_V2_CUTOVER_USERS_FILE" | awk '{print $1}')" == "$ORIGINAL_SHA" ]]

# A changed live document must never be overwritten by rollback.
APPLIED="$("$CUTOVER" --apply --state active --confirm "$APPLY_TOKEN")"
BACKUP="$(sed -n 's/^Backup: //p' <<<"$APPLIED")"
ROLLBACK_INFO="$("$CUTOVER" --rollback "$BACKUP")"
ROLLBACK_TOKEN="$(sed -n 's/.*Token requerido: //p' <<<"$ROLLBACK_INFO")"
printf '\n' >>"$USERS_V2_CUTOVER_USERS_FILE"
if "$CUTOVER" --rollback "$BACKUP" --confirm "$ROLLBACK_TOKEN" >/dev/null 2>&1; then
	echo "ERROR: rollback sobrescribió cambios posteriores" >&2
	exit 1
fi

# Capacity violations fail during dry-run and leave legacy input untouched.
cat >"$USERS_V2_CUTOVER_USERS_FILE" <<'JSON'
[
  {"uuid":"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa","connection_id":"conn-vless-test","label":"One","state":"draft","runtime_applied":false,"created_at":"2026-11-01T00:00:00Z"},
  {"uuid":"bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb","connection_id":"conn-vless-test","label":"Two","state":"draft","runtime_applied":false,"created_at":"2026-11-01T00:00:00Z"}
]
JSON
sed -i 's/"max_users":2/"max_users":1/' "$USERS_V2_CUTOVER_CONNECTIONS_FILE"
BEFORE="$(sha256sum "$USERS_V2_CUTOVER_USERS_FILE" | awk '{print $1}')"
if "$CUTOVER" --dry-run --state active >/dev/null 2>&1; then
	echo "ERROR: migración sobre capacidad fue aceptada" >&2
	exit 1
fi
[[ "$(sha256sum "$USERS_V2_CUTOVER_USERS_FILE" | awk '{print $1}')" == "$BEFORE" ]]
echo "OK: cutover dry-run, apply, rollback, protección ante cambios posteriores y límite de capacidad."