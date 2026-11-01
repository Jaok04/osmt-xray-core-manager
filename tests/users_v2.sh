#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck disable=SC2119
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export APP_ROOT="$ROOT"
source "$ROOT/modules/users_v2.sh"
USERS_V2_DATA_DIR="$TMP/data"
USERS_V2_DATA_FILE="$TMP/data/users.json"
USERS_V2_CONNECTIONS_FILE="$TMP/data/connections.json"
USERS_V2_LOCK="$TMP/run/integrity.lock"
mkdir -p "$TMP/data" "$TMP/run"
cat >"$USERS_V2_CONNECTIONS_FILE" <<'JSON'
[
 {"id":"conn-vless-a","protocol_id":"vless_ws","max_users":3},
 {"id":"conn-vless-b","protocol_id":"vless_tcp_tls","max_users":2},
 {"id":"conn-wg","protocol_id":"wireguard","max_users":4},
 {"id":"conn-cap","protocol_id":"vless_ws","max_users":1}
]
JSON

# shellcheck disable=SC2119
# shellcheck disable=SC2119
ID1="$(users_identity_create)"
# shellcheck disable=SC2119
ID2="$(users_identity_create)"
[[ "$ID1" != "$ID2" ]]
A1="$(users_association_create "$ID1" conn-vless-a Compartido uuid 11111111-1111-4111-8111-111111111111 active unlimited 0 none 0 0 auto)"
A2="$(users_association_create "$ID1" conn-vless-b Compartido uuid 22222222-2222-4222-8222-222222222222 active custom 3 days 0 0 auto)"
A3="$(users_association_create "$ID2" conn-vless-a Compartido uuid 33333333-3333-4333-8333-333333333333 suspended unlimited 0 none 0 0 auto)"
[[ "$A1" != "$A2" && "$A2" != "$A3" ]]
# Minute granularity: create, pause and reactivate with a fresh minute-based period.
A4="$(users_association_create "$ID2" conn-vless-b Minutos uuid 44444444-4444-4444-8444-444444444444 active custom 2 minutes 0 0 auto)"
jq -e --arg id "$A4" 'any(.associations[]; .id==$id and .duration.value==2 and .duration.unit=="minutes" and .expires_at!=null)' "$USERS_V2_DATA_FILE" >/dev/null
users_association_suspend "$A4"
jq -e --arg id "$A4" 'any(.associations[]; .id==$id and .state=="suspended" and .remaining_seconds>0 and .remaining_seconds<=120)' "$USERS_V2_DATA_FILE" >/dev/null
users_association_reactivate "$A4" custom 1 minutes
jq -e --arg id "$A4" 'any(.associations[]; .id==$id and .state=="active" and .duration.value==1 and .duration.unit=="minutes")' "$USERS_V2_DATA_FILE" >/dev/null
jq -e --arg id "$A2" 'any(.associations[]; .id==$id and .duration.kind=="custom" and .expires_at!=null and (.expires_at|fromdateiso8601)>(.created_at|fromdateiso8601))' "$USERS_V2_DATA_FILE" >/dev/null
jq -e --arg i1 "$ID1" --arg i2 "$ID2" '
 .schema_version == 2 and (.identities|length)==2 and (.associations|length)==4 and
 ([.associations[].alias] | unique | length)==2 and ([.associations[] | select(.alias=="Compartido")] | length)==3 and
 ( [.associations[]|select(.identity_id==$i1)]|length)==2 and
 ( [.associations[]|select(.identity_id==$i2)]|length)==2
' "$USERS_V2_DATA_FILE" >/dev/null

if users_association_create "$ID1" conn-vless-a Duplicado uuid 11111111-1111-4111-8111-111111111111 active unlimited 0 none 0 0 auto >/dev/null 2>&1; then
	echo "ERROR: UUID VLESS duplicado aceptado" >&2
	exit 1
fi
# Un mismo usuario no puede tener dos asociaciones genéricas en la misma conexión.
if users_association_create "$ID1" conn-vless-a Otro uuid 44444444-4444-4444-8444-444444444444 active unlimited 0 none 0 0 auto >/dev/null 2>&1; then
	echo "ERROR: duplicación identity+connection VLESS aceptada" >&2
	exit 1
fi

WG1="$(users_association_create "$ID1" conn-wg Peer-1 public_key wg-public-key-1 active unlimited 0 none 0 0 auto)"
WG2="$(users_association_create "$ID1" conn-wg Peer-2 public_key wg-public-key-2 active unlimited 0 none 0 0 auto)"
[[ "$WG1" != "$WG2" ]]
if users_association_create "$ID1" conn-wg Peer-Dup public_key wg-public-key-1 active unlimited 0 none 0 0 auto >/dev/null 2>&1; then
	echo "ERROR: clave pública WireGuard duplicada aceptada" >&2
	exit 1
fi
jq -e --arg id "$ID1" '[.associations[]|select(.identity_id==$id and .protocol=="wireguard" and .connection_id=="conn-wg")]|length==2' "$USERS_V2_DATA_FILE" >/dev/null

# Dos altas concurrentes no pueden consumir el mismo último slot.
# shellcheck disable=SC2119
CAP_ID="$(users_identity_create)"
create_cap_race() {
	users_association_create "$CAP_ID" conn-cap "$1" uuid "$2" active unlimited 0 none 0 0 auto >/dev/null
}
create_cap_race Cap-A aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa &
P1=$!
create_cap_race Cap-B bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb &
P2=$!
SUCCESS=0
if wait "$P1"; then SUCCESS=$((SUCCESS + 1)); fi
if wait "$P2"; then SUCCESS=$((SUCCESS + 1)); fi
[[ "$SUCCESS" -eq 1 ]]
jq -e '[.associations[]|select(.connection_id=="conn-cap")]|length==1' "$USERS_V2_DATA_FILE" >/dev/null

users_association_set_alias "$A1" Renombrado
jq -e --arg id "$A1" 'any(.associations[]; .id==$id and .alias=="Renombrado" and .credential.value=="11111111-1111-4111-8111-111111111111")' "$USERS_V2_DATA_FILE" >/dev/null
# Suspension stores remaining time and removes the running expiry.
users_association_suspend "$A2"
jq -e --arg id "$A2" 'any(.associations[]; .id==$id and .state=="suspended" and .expires_at==null and .suspended_at!=null and .remaining_seconds>0)' "$USERS_V2_DATA_FILE" >/dev/null
users_association_set_duration "$A2" custom 7 hours
jq -e --arg id "$A2" 'any(.associations[]; .id==$id and .state=="suspended" and .duration.value==7 and .remaining_seconds==25200 and .expires_at==null)' "$USERS_V2_DATA_FILE" >/dev/null
# Reactivation discards the paused remainder and starts a fresh period.
users_association_reactivate "$A2" custom 2 hours
jq -e --arg id "$A2" 'any(.associations[]; .id==$id and .state=="active" and .duration.value==2 and .duration.unit=="hours" and .remaining_seconds==null and .suspended_at==null and .expires_at!=null)' "$USERS_V2_DATA_FILE" >/dev/null
# Duration modification and renewal both start from the operation time.
users_association_set_duration "$A2" custom 4 hours
users_association_renew "$A2" custom 5 hours
jq -e --arg id "$A2" 'any(.associations[]; .id==$id and .state=="active" and .duration.value==5 and .duration.unit=="hours")' "$USERS_V2_DATA_FILE" >/dev/null
# Force a past expiration through the validated store and exercise the periodic/startup hook.
DOC="$(jq --arg id "$A2" '(.associations[] | select(.id==$id)).expires_at = "2000-01-01T00:00:00Z"' "$USERS_V2_DATA_FILE")"
users_v2_commit_document "$DOC"
# shellcheck disable=SC2119
[[ "$(users_v2_expire_due)" == 1 ]]
# A second sweep is idempotent and leaves suspended associations untouched.
# shellcheck disable=SC2119
[[ "$(users_v2_expire_due)" == 0 ]]
jq -e --arg id "$A2" --arg wg "$A3" 'any(.associations[]; .id==$id and .state=="expired") and any(.associations[]; .id==$wg and .state=="suspended")' "$USERS_V2_DATA_FILE" >/dev/null
if users_association_reactivate "$A2" custom 999999999999999999999 days >/dev/null 2>&1; then
	echo "ERROR: duración fuera de rango aceptada" >&2
	exit 1
fi
# Renewal of an expired association begins a new period from now.
users_association_renew "$A2" custom 1 days
jq -e --arg id "$A2" 'any(.associations[]; .id==$id and .state=="active" and .duration.value==1 and .duration.unit=="days")' "$USERS_V2_DATA_FILE" >/dev/null
# A3 se creó suspendida y sin vencimiento: registra inicio y reactiva sin expiración.
jq -e --arg id "$A3" 'any(.associations[]; .id==$id and .state=="suspended" and .duration.kind=="unlimited" and .suspended_at!=null and .remaining_seconds==null)' "$USERS_V2_DATA_FILE" >/dev/null
users_association_reactivate "$A3" unlimited 0 none
jq -e --arg id "$A3" 'any(.associations[]; .id==$id and .state=="active" and .duration.kind=="unlimited" and .suspended_at==null and .expires_at==null)' "$USERS_V2_DATA_FILE" >/dev/null
# Eliminar una asociación conserva la identidad y las otras asociaciones.
users_association_delete "$A4"
users_association_delete "$A2"
jq -e --arg id "$ID1" 'any(.identities[];.id==$id) and ( [.associations[]|select(.identity_id==$id)]|length)==3' "$USERS_V2_DATA_FILE" >/dev/null
# Eliminar identidad elimina todas sus asociaciones y peers.
users_identity_delete "$ID1"
jq -e --arg id "$ID1" '(any(.identities[];.id==$id)|not) and (any(.associations[];.identity_id==$id)|not) and (.identities|length)==2' "$USERS_V2_DATA_FILE" >/dev/null
[[ "$(stat -c '%a' "$USERS_V2_DATA_FILE")" == 600 ]]

# La corrupción no se autocorrige ni se sobrescribe.
cp "$USERS_V2_DATA_FILE" "$TMP/before"
printf '{corrupto\n' >"$USERS_V2_DATA_FILE"
if users_v2_lock lockfd >/dev/null 2>&1; then
	echo "ERROR: JSON corrupto aceptado" >&2
	exit 1
fi
grep -q 'corrupto' "$USERS_V2_DATA_FILE"

# Migración aislada: conserva UUID/alias/connection, crea una identidad por fila y exige estado explícito.
cat >"$TMP/legacy.json" <<'JSON'
[
 {"uuid":"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa","connection_id":"conn-vless-a","label":"Igual","state":"draft","runtime_applied":false,"created_at":"2026-10-01T00:00:00Z"},
 {"uuid":"bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb","connection_id":"conn-vless-b","label":"Igual","state":"draft","runtime_applied":false,"created_at":"2026-10-02T00:00:00Z"}
]
JSON
if users_v2_migrate_legacy "$TMP/legacy.json" "$USERS_V2_CONNECTIONS_FILE" "$TMP/no-state.json" invalid >/dev/null 2>&1; then
	echo "ERROR: migración sin estado confirmado aceptada" >&2
	exit 1
fi
users_v2_migrate_legacy "$TMP/legacy.json" "$USERS_V2_CONNECTIONS_FILE" "$TMP/migrated.json" suspended
jq -e '
 .schema_version==2 and (.identities|length)==2 and (.associations|length)==2 and
 ([.identities[].id]|unique|length)==2 and
 all(.associations[];.state=="suspended" and .suspended_at!=null and .remaining_seconds==null and .provisioning_status=="draft" and .runtime.status=="not_applied") and
 ([.associations[].alias]|unique|length)==1 and
 ([.associations[].credential.value]|unique|length)==2
' "$TMP/migrated.json" >/dev/null
users_v2_validate_file "$TMP/migrated.json"
[[ "$(jq -r '.associations[0].credential.value' "$TMP/migrated.json")" == "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" ]]
# Migración debe abortar si la cantidad legacy excede la capacidad de la conexión.
jq '. + [
 {uuid:"cccccccc-cccc-4ccc-8ccc-cccccccccccc",connection_id:"conn-vless-a",label:"Extra-1",state:"draft",runtime_applied:false,created_at:"2026-10-03T00:00:00Z"},
 {uuid:"dddddddd-dddd-4ddd-8ddd-dddddddddddd",connection_id:"conn-vless-a",label:"Extra-2",state:"draft",runtime_applied:false,created_at:"2026-10-04T00:00:00Z"},
 {uuid:"eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",connection_id:"conn-vless-a",label:"Extra-3",state:"draft",runtime_applied:false,created_at:"2026-10-05T00:00:00Z"}
]' "$TMP/legacy.json" >"$TMP/legacy-over-capacity.json"
if users_v2_migrate_legacy "$TMP/legacy-over-capacity.json" "$USERS_V2_CONNECTIONS_FILE" "$TMP/over-capacity.json" active >"$TMP/migration-error.log" 2>&1; then
	echo "ERROR: migración superó max_users" >&2
	exit 1
fi
grep -q 'capacidad insuficiente' "$TMP/migration-error.log"
[[ ! -e "$TMP/over-capacity.json" ]]
echo "OK: modelo v2, identidades, asociaciones, unicidad de credenciales, WireGuard peers, pausa/reactivación, modificación/renovación, vencimiento idempotente, corrupción y migración."
