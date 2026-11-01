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
 {"id":"conn-wg","protocol_id":"wireguard","max_users":4}
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
jq -e --arg id "$A2" 'any(.associations[]; .id==$id and .duration.kind=="custom" and .expires_at!=null and (.expires_at|fromdateiso8601)>(.created_at|fromdateiso8601))' "$USERS_V2_DATA_FILE" >/dev/null
jq -e --arg i1 "$ID1" --arg i2 "$ID2" '
 .schema_version == 2 and (.identities|length)==2 and (.associations|length)==3 and
 ([.associations[].alias] | unique | length)==1 and
 ( [.associations[]|select(.identity_id==$i1)]|length)==2 and
 ( [.associations[]|select(.identity_id==$i2)]|length)==1
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

users_association_set_alias "$A1" Renombrado
jq -e --arg id "$A1" 'any(.associations[]; .id==$id and .alias=="Renombrado" and .credential.value=="11111111-1111-4111-8111-111111111111")' "$USERS_V2_DATA_FILE" >/dev/null
users_association_set_state "$A3" expired
jq -e --arg id "$A3" 'any(.associations[]; .id==$id and .state=="expired")' "$USERS_V2_DATA_FILE" >/dev/null
# Eliminar una asociación conserva la identidad y las otras asociaciones.
users_association_delete "$A2"
jq -e --arg id "$ID1" 'any(.identities[];.id==$id) and ( [.associations[]|select(.identity_id==$id)]|length)==3' "$USERS_V2_DATA_FILE" >/dev/null
# Eliminar identidad elimina todas sus asociaciones y peers.
users_identity_delete "$ID1"
jq -e --arg id "$ID1" '(any(.identities[];.id==$id)|not) and (any(.associations[];.identity_id==$id)|not) and (.identities|length)==1' "$USERS_V2_DATA_FILE" >/dev/null
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
 all(.associations[];.state=="suspended" and .provisioning_status=="draft" and .runtime.status=="not_applied") and
 ([.associations[].alias]|unique|length)==1 and
 ([.associations[].credential.value]|unique|length)==2
' "$TMP/migrated.json" >/dev/null
[[ "$(jq -r '.associations[0].credential.value' "$TMP/migrated.json")" == "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" ]]
# Migración debe abortar si la cantidad legacy excede la capacidad de la conexión.
jq '. + [.[0], .[0], .[0]]' "$TMP/legacy.json" >"$TMP/legacy-over-capacity.json"
if users_v2_migrate_legacy "$TMP/legacy-over-capacity.json" "$USERS_V2_CONNECTIONS_FILE" "$TMP/over-capacity.json" active >/dev/null 2>&1; then
	echo "ERROR: migración superó max_users" >&2
	exit 1
fi
[[ ! -e "$TMP/over-capacity.json" ]]
echo "OK: modelo v2, identidad global, alias duplicados, unicidad UUID, WireGuard peers, CRUD, estados separados, corrupción y migración aislada."