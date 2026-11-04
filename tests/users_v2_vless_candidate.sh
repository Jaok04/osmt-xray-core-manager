#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export APP_ROOT="$ROOT"
export XRAY_MANAGER_USERS_DIR="$TMP/users"
export XRAY_MANAGER_USERS_FILE="$TMP/users/users.json"
export XRAY_MANAGER_CONNECTIONS_FILE="$TMP/connections.json"
export XRAY_MANAGER_INTEGRITY_LOCK="$TMP/run/integrity.lock"
mkdir -p "$TMP/run"
cat >"$XRAY_MANAGER_CONNECTIONS_FILE" <<'JSON'
[
 {"id":"vless-a","protocol_id":"vless_ws","max_users":8},
 {"id":"vless-b","protocol_id":"vless_tcp_tls","max_users":8},
 {"id":"wg-a","protocol_id":"wireguard","max_users":8}
]
JSON
source "$ROOT/modules/users_v2.sh"
# El exportador de candidatos no debe inicializar un almacén ausente.
if users_v2_export_vless_candidate_clients vless-a >/dev/null 2>&1; then
	echo 'ERROR: se exportó un almacén inexistente.' >&2
	exit 1
fi
[[ ! -e "$XRAY_MANAGER_USERS_FILE" ]]
I1="$(users_identity_create)"
I2="$(users_identity_create)"
A_ACTIVE="$(users_association_create "$I1" vless-a 'Alias repetido' uuid aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa active unlimited 0 none 0 0 auto)"
A_SUSP="$(users_association_create "$I2" vless-a 'Alias repetido' uuid bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb suspended unlimited 0 none 0 0 auto)"
A_EXPIRED_ID="$(users_identity_create)"
A_EXPIRED="$(users_association_create "$A_EXPIRED_ID" vless-a 'Expired' uuid eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee expired unlimited 0 none 0 0 auto)"
A_OTHER="$(users_association_create "$I1" vless-b 'Otra conexión' uuid CCCCCCCC-CCCC-4CCC-8CCC-CCCCCCCCCCCC active unlimited 0 none 0 0 auto)"
jq -e --arg id "$A_OTHER" 'any(.associations[]; .id==$id and .credential.value=="cccccccc-cccc-4ccc-8ccc-cccccccccccc")' "$XRAY_MANAGER_USERS_FILE" >/dev/null
A_WG="$(users_association_create "$I2" wg-a 'Peer' public_key test-public-key active unlimited 0 none 0 0 auto)"
# Estado active con vencimiento pasado se excluye aunque aún no haya corrido el barrido.
DOC="$(jq --arg id "$A_ACTIVE" '(.associations[]|select(.id==$id)).duration={kind:"custom",value:1,unit:"days"} | (.associations[]|select(.id==$id)).expires_at="2000-01-01T00:00:00Z"' "$XRAY_MANAGER_USERS_FILE")"
users_v2_commit_document "$DOC"
I3="$(users_identity_create)"
A_FRESH="$(users_association_create "$I3" vless-a 'Fresh draft' uuid dddddddd-dddd-4ddd-8ddd-dddddddddddd active unlimited 0 none 0 0 auto)"
CANDIDATE="$(users_v2_export_vless_candidate_clients vless-a)"
jq -e --arg fresh dddddddd-dddd-4ddd-8ddd-dddddddddddd --arg assoc "$A_FRESH" 'length==1 and .[0].id==$fresh and .[0].email==("assoc:"+$assoc)' <<<"$CANDIDATE" >/dev/null
RUNTIME="$(users_v2_export_vless_clients vless-a)"
[[ "$RUNTIME" == '[]' ]]
# provisioning/runtime fallidos no impiden regenerar candidato desde estado funcional.
DOC="$(jq --arg id "$A_FRESH" '(.associations[]|select(.id==$id)).provisioning_status="failed" | (.associations[]|select(.id==$id)).runtime.status="failed"' "$XRAY_MANAGER_USERS_FILE")"
users_v2_commit_document "$DOC"
CANDIDATE="$(users_v2_export_vless_candidate_clients vless-a)"
jq -e --arg assoc "$A_FRESH" 'length==1 and .[0].email==("assoc:"+$assoc)' <<<"$CANDIDATE" >/dev/null
# La vista runtime solo incorpora asociaciones activas/aplicadas.
DOC="$(jq --arg id "$A_FRESH" '(.associations[]|select(.id==$id)).provisioning_status="applied" | (.associations[]|select(.id==$id)).runtime.status="applied"' "$XRAY_MANAGER_USERS_FILE")"
users_v2_commit_document "$DOC"
RUNTIME="$(users_v2_export_vless_clients vless-a)"
jq -e --arg assoc "$A_FRESH" 'length==1 and .[0].email==("assoc:"+$assoc)' <<<"$RUNTIME" >/dev/null
if users_v2_export_vless_candidate_clients missing >/dev/null 2>&1; then exit 1; fi
cp "$XRAY_MANAGER_USERS_FILE" "$TMP/valid.json"
DOC="$(jq --arg id "$A_FRESH" '(.associations[]|select(.id==$id)).duration={kind:"custom",value:1,unit:"days"} | (.associations[]|select(.id==$id)).expires_at="not-a-date"' "$XRAY_MANAGER_USERS_FILE")"
users_v2_commit_document "$DOC"
if users_v2_export_vless_candidate_clients vless-a >/dev/null 2>&1; then
	echo 'ERROR: se exportó un vencimiento inválido.' >&2
	exit 1
fi
cp "$TMP/valid.json" "$XRAY_MANAGER_USERS_FILE"
printf '{invalid\\n' >"$XRAY_MANAGER_USERS_FILE"
if users_v2_export_vless_candidate_clients vless-a >/dev/null 2>&1; then
	echo 'ERROR: se exportó un almacén corrupto.' >&2
	exit 1
fi
grep -q '{invalid' "$XRAY_MANAGER_USERS_FILE"
echo 'PASS: candidato VLESS desde V2 incluye active draft, excluye suspended/expirados/vencidos/otras conexiones/protocolos, separa runtime y falla cerrado sin inicializar almacén.'
