#!/usr/bin/env bash
# Modelo v2 de identidades y asociaciones. No aplica cambios al runtime.
# Requiere jq, flock, uuidgen y lib/json_store.sh.
if ! declare -F json_store_commit >/dev/null 2>&1; then
	# shellcheck disable=SC1091
	source "${APP_ROOT:-/opt/xray-manager}/lib/json_store.sh"
fi

USERS_V2_DATA_DIR="${XRAY_MANAGER_USERS_DIR:-/var/lib/xray-manager/users}"
USERS_V2_DATA_FILE="${XRAY_MANAGER_USERS_FILE:-/var/lib/xray-manager/users/users.json}"
USERS_V2_CONNECTIONS_FILE="${XRAY_MANAGER_CONNECTIONS_FILE:-/var/lib/xray-manager/connections/connections.json}"
USERS_V2_LOCK="${XRAY_MANAGER_INTEGRITY_LOCK:-/run/xray-manager/integrity.lock}"

users_v2_require_tools() {
	command -v jq >/dev/null 2>&1 && command -v flock >/dev/null 2>&1 && command -v uuidgen >/dev/null 2>&1
}

users_v2_uuid() { uuidgen | tr '[:upper:]' '[:lower:]'; }
users_v2_now() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }

users_v2_lock() {
	local -n fd_ref="$1"
	users_v2_require_tools || return 1
	mkdir -p "$USERS_V2_DATA_DIR" "$(dirname "$USERS_V2_LOCK")"
	exec {fd_ref}>"$USERS_V2_LOCK"
	flock -x "$fd_ref"
	if [[ ! -e "$USERS_V2_DATA_FILE" ]]; then
		printf '%s\n' '{"schema_version":2,"identities":[],"associations":[]}' >"$USERS_V2_DATA_FILE"
		chmod 600 "$USERS_V2_DATA_FILE"
	fi
	if ! users_v2_validate_file "$USERS_V2_DATA_FILE"; then
		flock -u "$fd_ref"; exec {fd_ref}>&-
		printf 'El documento v2 es inválido; no se modificó.\n' >&2
		return 1
	fi
}

users_v2_unlock() {
	local fd="$1"
	flock -u "$fd"
	exec {fd}>&-
}

users_v2_validate_file() {
	[[ "$#" -eq 1 && -r "$1" ]] || return 1
	jq -e --slurpfile connections "$USERS_V2_CONNECTIONS_FILE" '
		def uuid: type == "string" and test("^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$");
		def positive_or_null: . == null or (type == "number" and floor == . and . > 0);
		(schema_version == 2) and
		(identities | type == "array") and (associations | type == "array") and
		all(.identities[]; type == "object" and (.id | uuid) and (.created_at | type == "string" and length > 0)) and
		all(.associations[];
			type == "object" and
			(.id | uuid) and (.identity_id | uuid) and
			(.connection_id | type == "string" and length > 0) and
			(.alias | type == "string" and length > 0 and length <= 64) and
			(.protocol | type == "string" and length > 0) and
			(.credential | type == "object" and (.type | type == "string" and length > 0) and (.value | type == "string" and length > 0)) and
			(.created_at | type == "string" and length > 0) and
			(.duration | type == "object" and (.kind == "unlimited" or (.kind == "custom" and (.value | type == "number" and floor == . and . > 0) and (.unit == "days" or .unit == "hours" or .unit == "minutes")))) and
			(.expires_at == null or (.expires_at | type == "string" and length > 0)) and
			(.traffic_limit_bytes | positive_or_null) and
			(.simultaneous_connection_limit | positive_or_null) and
			(.state == "active" or .state == "suspended" or .state == "expired") and
			(.provisioning_status == "draft" or .provisioning_status == "pending" or .provisioning_status == "applied" or .provisioning_status == "failed") and
			(.runtime | type == "object" and (.status == "not_applied" or .status == "applied" or .status == "unknown" or .status == "pending" or .status == "failed") and (.last_applied_at == null or (.last_applied_at | type == "string")))
		) and
		([.identities[].id] | length == (unique | length)) and
		([.associations[].id] | length == (unique | length)) and
		all(.associations[]; .identity_id as $iid | any($document.identities[]?; .id == $iid))
	' "$1" >/dev/null 2>&1
}

# Validador completo con referencias e invariantes cruzadas.
users_v2_validate_document() {
	[[ "$#" -eq 1 ]] || return 2
	local document="$1"
	jq -e --argfile connections "$USERS_V2_CONNECTIONS_FILE" '
		def uuid: type == "string" and test("^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$");
		def posnull: . == null or (type == "number" and floor == . and . > 0);
		.schema_version == 2 and
		(.identities | type == "array") and (.associations | type == "array") and
		all(.identities[]; (.id | uuid) and (.created_at | type == "string" and length > 0)) and
		all(.associations[];
			(.id | uuid) and (.identity_id | uuid) and
			any($document.identities[]; .id == .identity_id) and
			(.connection_id | type == "string" and length > 0) and
			any($connections[]; .id == .connection_id) and
			(.alias | type == "string" and length > 0 and length <= 64) and
			(.protocol | type == "string" and length > 0) and
			(.credential.type | type == "string" and length > 0) and
			(.credential.value | type == "string" and length > 0) and
			(.duration.kind == "unlimited" or (.duration.kind == "custom" and .duration.value > 0 and (.duration.unit == "days" or .duration.unit == "hours" or .duration.unit == "minutes"))) and
			(.traffic_limit_bytes | posnull) and (.simultaneous_connection_limit | posnull) and
			(.state == "active" or .state == "suspended" or .state == "expired") and
			(.provisioning_status == "draft" or .provisioning_status == "pending" or .provisioning_status == "applied" or .provisioning_status == "failed") and
			(.runtime.status == "not_applied" or .runtime.status == "applied" or .runtime.status == "unknown" or .runtime.status == "pending" or .runtime.status == "failed")
		) and
		([.identities[].id] | length == (unique | length)) and
		([.associations[].id] | length == (unique | length)) and
		([.associations[] | select(.protocol == "vless") | .credential.value] | length == (unique | length)) and
		(all(.associations[] as $a; ($a.protocol == "wireguard") or
			([.associations[] | select(.identity_id == $a.identity_id and .connection_id == $a.connection_id)] | length == 1)))
	' <<<"$document" >/dev/null 2>&1
}

users_v2_commit_document() {
	[[ "$#" -eq 1 ]] || return 2
	local document="$1" tmp rc
	users_v2_validate_document "$document" || {
		printf 'El documento propuesto no supera las invariantes v2.\n' >&2
		return 1
	}
	tmp="$(mktemp "$USERS_V2_DATA_DIR/.users-v2.XXXXXX")" || return 1
	if ! printf '%s\n' "$document" | jq '.' >"$tmp"; then rm -f "$tmp"; return 1; fi
	if json_store_commit "$tmp" "$USERS_V2_DATA_FILE" 600; then
		return 0
	else
		rc=$?
		if ((rc == 3)); then
			printf 'ADVERTENCIA: documento reemplazado; fsync del directorio falló.\n' >&2
			return 3
		fi
		rm -f "$tmp"; return 1
	fi
}

users_identity_create() {
	[[ "$#" -eq 0 ]] || return 2
	local fd id now document
	users_v2_lock fd || return 1
	id="$(users_v2_uuid)" || { users_v2_unlock "$fd"; return 1; }
	now="$(users_v2_now)"
	document="$(jq --arg id "$id" --arg now "$now" '.identities += [{id:$id,created_at:$now}]' "$USERS_V2_DATA_FILE")" || { users_v2_unlock "$fd"; return 1; }
	if ! users_v2_commit_document "$document"; then users_v2_unlock "$fd"; return 1; fi
	users_v2_unlock "$fd"
	printf '%s\n' "$id"
}

# users_association_create identity_id connection_id alias credential_type credential_value state duration_kind duration_value duration_unit traffic_limit simultaneous_limit
users_association_create() {
	[[ "$#" -eq 12 ]] || { printf 'Uso: users_association_create <identity_id> <connection_id> <alias> <credential_type> <credential_value> <state> <duration_kind> <duration_value> <duration_unit> <traffic_limit|0> <simultaneous_limit|0> <protocol_override|auto>\n' >&2; return 2; }
	local identity_id="$1" connection_id="$2" alias="$3" ctype="$4" cvalue="$5" state="$6"
	local dkind="$7" dvalue="$8" dunit="$9" traffic="${10}" simultaneous="${11}" override="${12}"
	local fd connection protocol id now expires=null document max_users slots
	[[ "$alias" == "$(printf '%s' "$alias" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')" && -n "$alias" && "${#alias}" -le 64 ]] || return 2
	[[ "$state" == active || "$state" == suspended || "$state" == expired ]] || return 2
	[[ "$dkind" == unlimited || "$dkind" == custom ]] || return 2
	if [[ "$dkind" == custom ]]; then
		[[ "$dvalue" =~ ^[1-9][0-9]*$ && ( "$dunit" == days || "$dunit" == hours || "$dunit" == minutes ) ]] || return 2
		case "$dunit" in days) expires="$(date -u -d "+$dvalue days" '+%Y-%m-%dT%H:%M:%SZ')" ;; hours) expires="$(date -u -d "+$dvalue hours" '+%Y-%m-%dT%H:%M:%SZ')" ;; minutes) expires="$(date -u -d "+$dvalue minutes" '+%Y-%m-%dT%H:%M:%SZ')" ;; esac
	else dvalue=0; dunit=none; fi
	[[ "$traffic" == 0 || "$traffic" =~ ^[1-9][0-9]*$ ]] || return 2
	[[ "$simultaneous" == 0 || "$simultaneous" =~ ^[1-9][0-9]*$ ]] || return 2
	users_v2_lock fd || return 1
	connection="$(jq -ce --arg id "$connection_id" '.[] | select(.id == $id)' "$USERS_V2_CONNECTIONS_FILE")" || { users_v2_unlock "$fd"; return 1; }
	protocol="$(jq -r '.protocol_id' <<<"$connection")"
	[[ "$override" == auto ]] || protocol="$override"
	jq -e --arg id "$identity_id" 'any(.identities[]; .id == $id)' "$USERS_V2_DATA_FILE" >/dev/null || { users_v2_unlock "$fd"; return 1; }
	if [[ "$protocol" == vless ]]; then
		[[ "$ctype" == uuid && "$cvalue" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89aAbB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$ ]] || { users_v2_unlock "$fd"; return 2; }
		if jq -e --arg value "$cvalue" 'any(.associations[]; .protocol == "vless" and (.credential.value | ascii_downcase) == ($value | ascii_downcase))' "$USERS_V2_DATA_FILE" >/dev/null; then users_v2_unlock "$fd"; return 1; fi
	fi
	if [[ "$protocol" != wireguard ]] && jq -e --arg iid "$identity_id" --arg cid "$connection_id" 'any(.associations[]; .identity_id == $iid and .connection_id == $cid)' "$USERS_V2_DATA_FILE" >/dev/null; then users_v2_unlock "$fd"; return 1; fi
	max_users="$(jq -r '.max_users' <<<"$connection")"
	slots="$(jq --arg cid "$connection_id" '[.associations[] | select(.connection_id == $cid)] | length' "$USERS_V2_DATA_FILE")"
	((slots < max_users)) || { users_v2_unlock "$fd"; return 1; }
	id="$(users_v2_uuid)" || { users_v2_unlock "$fd"; return 1; }
	now="$(users_v2_now)"
	document="$(jq --arg id "$id" --arg iid "$identity_id" --arg cid "$connection_id" --arg alias "$alias" --arg protocol "$protocol" --arg ctype "$ctype" --arg cvalue "$cvalue" --arg now "$now" --arg state "$state" --arg dkind "$dkind" --argjson dvalue "$dvalue" --arg dunit "$dunit" --argjson expires "$expires" --argjson traffic "$traffic" --argjson simultaneous "$simultaneous" '
		.associations += [{
			id:$id,identity_id:$iid,connection_id:$cid,alias:$alias,protocol:$protocol,
			credential:{type:$ctype,value:$cvalue},created_at:$now,
			duration:(if $dkind == "unlimited" then {kind:"unlimited"} else {kind:"custom",value:$dvalue,unit:$dunit} end),
			expires_at:$expires,traffic_limit_bytes:(if $traffic == 0 then null else $traffic end),
			simultaneous_connection_limit:(if $simultaneous == 0 then null else $simultaneous end),
			state:$state,provisioning_status:"draft",runtime:{status:"not_applied",last_applied_at:null}
		}]' "$USERS_V2_DATA_FILE")" || { users_v2_unlock "$fd"; return 1; }
	if ! users_v2_commit_document "$document"; then users_v2_unlock "$fd"; return 1; fi
	users_v2_unlock "$fd"
	printf '%s\n' "$id"
}

users_association_set_state() {
	[[ "$#" -eq 2 && ( "$2" == active || "$2" == suspended || "$2" == expired ) ]] || return 2
	local fd document
	users_v2_lock fd || return 1
	jq -e --arg id "$1" 'any(.associations[]; .id == $id)' "$USERS_V2_DATA_FILE" >/dev/null || { users_v2_unlock "$fd"; return 1; }
	document="$(jq --arg id "$1" --arg state "$2" '(.associations[] | select(.id == $id)).state = $state' "$USERS_V2_DATA_FILE")"
	if ! users_v2_commit_document "$document"; then users_v2_unlock "$fd"; return 1; fi
	users_v2_unlock "$fd"
}

users_association_set_alias() {
	[[ "$#" -eq 2 && -n "$2" && "${#2}" -le 64 ]] || return 2
	local fd document
	users_v2_lock fd || return 1
	jq -e --arg id "$1" 'any(.associations[]; .id == $id)' "$USERS_V2_DATA_FILE" >/dev/null || { users_v2_unlock "$fd"; return 1; }
	document="$(jq --arg id "$1" --arg alias "$2" '(.associations[] | select(.id == $id)).alias = $alias' "$USERS_V2_DATA_FILE")"
	if ! users_v2_commit_document "$document"; then users_v2_unlock "$fd"; return 1; fi
	users_v2_unlock "$fd"
}

users_association_delete() {
	[[ "$#" -eq 1 ]] || return 2
	local fd document
	users_v2_lock fd || return 1
	jq -e --arg id "$1" 'any(.associations[]; .id == $id)' "$USERS_V2_DATA_FILE" >/dev/null || { users_v2_unlock "$fd"; return 1; }
	document="$(jq --arg id "$1" '.associations |= map(select(.id != $id))' "$USERS_V2_DATA_FILE")"
	if ! users_v2_commit_document "$document"; then users_v2_unlock "$fd"; return 1; fi
	users_v2_unlock "$fd"
}

users_identity_delete() {
	[[ "$#" -eq 1 ]] || return 2
	local fd document
	users_v2_lock fd || return 1
	jq -e --arg id "$1" 'any(.identities[]; .id == $id)' "$USERS_V2_DATA_FILE" >/dev/null || { users_v2_unlock "$fd"; return 1; }
	document="$(jq --arg id "$1" '{schema_version,identities:(.identities | map(select(.id != $id))),associations:(.associations | map(select(.identity_id != $id)))}' "$USERS_V2_DATA_FILE")"
	if ! users_v2_commit_document "$document"; then users_v2_unlock "$fd"; return 1; fi
	users_v2_unlock "$fd"
}

# Adaptador neutral de salida VLESS: solo asociaciones activas y aplicadas.
users_v2_export_vless_clients() {
	[[ "$#" -eq 1 ]] || return 2
	local fd
	users_v2_lock fd || return 1
	jq --arg cid "$1" '[.associations[] | select(.connection_id == $cid and .protocol == "vless" and .state == "active" and .provisioning_status == "applied" and .runtime.status == "applied") | {id:.credential.value,email:("assoc:" + .id)}]' "$USERS_V2_DATA_FILE"
	users_v2_unlock "$fd"
}

# Migración pura sobre rutas explícitas; nunca cambia el archivo legacy ni el destino por sí sola.
# users_v2_migrate_legacy <legacy_json> <connections_json> <output_json> <confirmed_functional_state>
users_v2_migrate_legacy() {
	[[ "$#" -eq 4 && ( "$4" == active || "$4" == suspended || "$4" == expired ) ]] || return 2
	local legacy="$1" connections="$2" output="$3" state="$4" now
	[[ -r "$legacy" && -r "$connections" && ! -e "$output" ]] || return 1
	jq -e --slurpfile c "$connections" 'type == "array" and all(.[]; type == "object" and (.uuid|type=="string" and length>0) and (.connection_id|type=="string" and length>0) and (.label|type=="string" and length>0) and .state=="draft" and .runtime_applied==false and (.created_at|type=="string") and any($c[]; .id == .connection_id)) and ([.[].uuid|ascii_downcase] | length == (unique|length))' "$legacy" >/dev/null || return 1
	now="$(users_v2_now)"
	jq --arg state "$state" --arg now "$now" '
		{schema_version:2,identities:[],associations:[]} |
		. as $empty |
		$empty
	' </dev/null >/dev/null 2>&1 || :
	jq --slurpfile conns "$connections" --arg state "$state" '
		{schema_version:2,identities:[],associations:[]} as $base |
		reduce .[] as $old ($base;
			(old.uuid | ascii_downcase) as $cred |
			(old.connection_id) as $cid |
			($conns[0][] | select(.id == $cid) | .protocol_id) as $mode |
			($mode | if startswith("vless_") then "vless" elif startswith("wireguard") then "wireguard" else . end) as $protocol |
			(old.created_at) as $created |
			(uuidgen_placeholder) as $unused |
			.
		)
	' "$legacy" >/dev/null 2>&1
	return 1
}
