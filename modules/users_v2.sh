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
	if [[ ! -r "$USERS_V2_CONNECTIONS_FILE" ]]; then
		flock -u "$fd_ref"
		exec {fd_ref}>&-
		printf 'El catálogo de conexiones no está disponible; no se inicializó el registro v2.\\n' >&2
		return 1
	fi
	if [[ ! -e "$USERS_V2_DATA_FILE" ]]; then
		printf '%s\n' '{"schema_version":2,"identities":[],"associations":[]}' >"$USERS_V2_DATA_FILE"
		chmod 600 "$USERS_V2_DATA_FILE"
	fi
	if ! users_v2_validate_file "$USERS_V2_DATA_FILE"; then
		flock -u "$fd_ref"
		exec {fd_ref}>&-
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
	local document
	document="$(jq -ce '.' "$1")" || return 1
	users_v2_validate_document "$document"
}

# Validador completo con referencias e invariantes cruzadas.
users_v2_validate_document() {
	[[ "$#" -eq 1 ]] || return 2
	local document="$1"
	[[ -r "$USERS_V2_CONNECTIONS_FILE" ]] || return 1
	jq -e --slurpfile connections "$USERS_V2_CONNECTIONS_FILE" '
		def uuid: type == "string" and test("^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$");
		def posnull: . == null or (type == "number" and floor == . and . > 0);
		. as $doc |
		.schema_version == 2 and
		(.identities | type == "array") and (.associations | type == "array") and
		all(.identities[]; (.id | uuid) and (.created_at | type == "string" and length > 0)) and
		all(.associations[]; . as $a | (
			($a.id | uuid) and ($a.identity_id | uuid) and
			any($doc.identities[]; .id == $a.identity_id) and
			($a.connection_id | type == "string" and length > 0) and
			any($connections[0][]; .id == $a.connection_id and
				(if (.protocol_id | startswith("vless_")) then "vless" elif (.protocol_id | startswith("wireguard")) then "wireguard" else .protocol_id end) == $a.protocol) and
			($a.alias | type == "string" and length > 0 and length <= 64) and
			($a.protocol | type == "string" and length > 0) and
			($a.credential.type | type == "string" and length > 0) and
			($a.credential.value | type == "string" and length > 0) and
			($a | has("suspended_at") and has("remaining_seconds")) and
			(($a.duration.kind == "unlimited" and $a.expires_at == null and $a.remaining_seconds == null) or
			 ($a.duration.kind == "custom" and ($a.duration.value | type == "number" and floor == . and . > 0) and
			  ($a.duration.unit == "days" or $a.duration.unit == "hours" or $a.duration.unit == "minutes") and
			  ((($a.state == "suspended") and $a.expires_at == null and ($a.suspended_at | type == "string" and length > 0) and ($a.remaining_seconds | type == "number" and floor == . and . >= 0)) or
			   (($a.state != "suspended") and ($a.expires_at | type == "string" and length > 0) and $a.suspended_at == null and $a.remaining_seconds == null)))) and
			($a.state == "suspended" or $a.suspended_at == null) and
			($a.protocol != "vless" or ($a.credential.type == "uuid" and ($a.credential.value | test("^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")))) and
			($a.protocol != "wireguard" or $a.credential.type == "public_key") and
			($a.traffic_limit_bytes | posnull) and ($a.simultaneous_connection_limit | posnull) and
			($a.state == "active" or $a.state == "suspended" or $a.state == "expired") and
			($a.provisioning_status == "draft" or $a.provisioning_status == "pending" or $a.provisioning_status == "applied" or $a.provisioning_status == "failed") and
			($a.runtime.status == "not_applied" or $a.runtime.status == "applied" or $a.runtime.status == "unknown" or $a.runtime.status == "pending" or $a.runtime.status == "failed") and
			($a.runtime.last_applied_at == null or ($a.runtime.last_applied_at | type == "string"))
		)) and
		([.identities[].id] | length == (unique | length)) and
		([.associations[].id] | length == (unique | length)) and
		([.associations[] | select(.protocol == "vless") | .credential.value | ascii_downcase] | length == (unique | length)) and
		([.associations[] | select(.protocol == "wireguard") | .credential.value] | length == (unique | length)) and
		(all(.associations[]; . as $a | ($a.protocol == "wireguard" or
			([$doc.associations[] | select(.identity_id == $a.identity_id and .connection_id == $a.connection_id)] | length == 1))))
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
	if ! printf '%s\n' "$document" | jq '.' >"$tmp"; then
		rm -f "$tmp"
		return 1
	fi
	if json_store_commit "$tmp" "$USERS_V2_DATA_FILE" 600; then
		return 0
	else
		rc=$?
		if ((rc == 3)); then
			printf 'ADVERTENCIA: documento reemplazado; fsync del directorio falló.\n' >&2
			return 3
		fi
		rm -f "$tmp"
		return 1
	fi
}

users_identity_create() {
	[[ "$#" -eq 0 ]] || return 2
	local fd id now document
	users_v2_lock fd || return 1
	id="$(users_v2_uuid)" || {
		users_v2_unlock "$fd"
		return 1
	}
	now="$(users_v2_now)"
	document="$(jq --arg id "$id" --arg now "$now" '.identities += [{id:$id,created_at:$now}]' "$USERS_V2_DATA_FILE")" || {
		users_v2_unlock "$fd"
		return 1
	}
	if ! users_v2_commit_document "$document"; then
		users_v2_unlock "$fd"
		return 1
	fi
	users_v2_unlock "$fd"
	printf '%s\n' "$id"
}

# Return a UTC expiration timestamp from a captured UTC timestamp.
users_v2_expiration_from() {
	[[ "$#" -eq 3 && "$2" =~ ^[1-9][0-9]*$ && ("$3" == days || "$3" == hours || "$3" == minutes) ]] || return 2
	date -u -d "$1 + $2 $3" '+%Y-%m-%dT%H:%M:%SZ'
}

users_v2_duration_seconds() {
	case "$2" in
		days) printf '%s\n' "$(($1 * 86400))" ;;
		hours) printf '%s\n' "$(($1 * 3600))" ;;
		minutes) printf '%s\n' "$(($1 * 60))" ;;
		*) return 2 ;;
	esac
}

users_v2_duration_args() {
	[[ "$#" -eq 3 ]] || return 2
	if [[ "$1" == unlimited ]]; then [[ "$2" == 0 && "$3" == none ]] || return 2
	else [[ "$1" == custom && "$2" =~ ^[1-9][0-9]*$ && ("$3" == days || "$3" == hours || "$3" == minutes) ]] || return 2; fi
}
# users_association_create identity_id connection_id alias credential_type credential_value state duration_kind duration_value duration_unit traffic_limit simultaneous_limit
users_association_create() {
	[[ "$#" -eq 12 ]] || {
		printf 'Uso: users_association_create <identity_id> <connection_id> <alias> <credential_type> <credential_value> <state> <duration_kind> <duration_value> <duration_unit> <traffic_limit|0> <simultaneous_limit|0> <protocol_override|auto>\n' >&2
		return 2
	}
	local identity_id="$1" connection_id="$2" alias="$3" ctype="$4" cvalue="$5" state="$6"
	local dkind="$7" dvalue="$8" dunit="$9" traffic="${10}" simultaneous="${11}" override="${12}"
	local fd connection protocol id now expires="" document max_users slots remaining=0 suspended_at=""
	[[ "$alias" == "$(printf '%s' "$alias" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')" && -n "$alias" && "${#alias}" -le 64 ]] || return 2
	[[ "$state" == active || "$state" == suspended || "$state" == expired ]] || return 2
	[[ "$dkind" == unlimited || "$dkind" == custom ]] || return 2
	if [[ "$dkind" == custom ]]; then
		[[ "$dvalue" =~ ^[1-9][0-9]*$ && ("$dunit" == days || "$dunit" == hours || "$dunit" == minutes) ]] || return 2
		:
	else
		dvalue=0
		dunit=none
	fi
	[[ "$traffic" == 0 || "$traffic" =~ ^[1-9][0-9]*$ ]] || return 2
	[[ "$simultaneous" == 0 || "$simultaneous" =~ ^[1-9][0-9]*$ ]] || return 2
	users_v2_lock fd || return 1
	connection="$(jq -ce --arg id "$connection_id" '.[] | select(.id == $id)' "$USERS_V2_CONNECTIONS_FILE")" || {
		users_v2_unlock "$fd"
		return 1
	}
	protocol="$(jq -r '.protocol_id' <<<"$connection")"
	if [[ "$protocol" == vless_* ]]; then protocol=vless; elif [[ "$protocol" == wireguard* ]]; then protocol=wireguard; fi
	[[ "$override" == auto ]] || protocol="$override"
	jq -e --arg id "$identity_id" 'any(.identities[]; .id == $id)' "$USERS_V2_DATA_FILE" >/dev/null || {
		users_v2_unlock "$fd"
		return 1
	}
	if [[ "$protocol" == vless ]]; then
		[[ "$ctype" == uuid && "$cvalue" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89aAbB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$ ]] || {
			users_v2_unlock "$fd"
			return 2
		}
		if jq -e --arg value "$cvalue" 'any(.associations[]; .protocol == "vless" and (.credential.value | ascii_downcase) == ($value | ascii_downcase))' "$USERS_V2_DATA_FILE" >/dev/null; then
			users_v2_unlock "$fd"
			return 1
		fi
	fi
	if [[ "$protocol" != wireguard ]] && jq -e --arg iid "$identity_id" --arg cid "$connection_id" 'any(.associations[]; .identity_id == $iid and .connection_id == $cid)' "$USERS_V2_DATA_FILE" >/dev/null; then
		users_v2_unlock "$fd"
		return 1
	fi
	max_users="$(jq -r '.max_users' <<<"$connection")"
	slots="$(jq --arg cid "$connection_id" '[.associations[] | select(.connection_id == $cid)] | length' "$USERS_V2_DATA_FILE")"
	((slots < max_users)) || {
		users_v2_unlock "$fd"
		return 1
	}
	id="$(users_v2_uuid)" || {
		users_v2_unlock "$fd"
		return 1
	}
	now="$(users_v2_now)"
	if [[ "$dkind" == custom ]]; then
		expires="$(users_v2_expiration_from "$now" "$dvalue" "$dunit")" || { users_v2_unlock "$fd"; return 2; }
		if [[ "$state" == suspended ]]; then
			remaining="$(users_v2_duration_seconds "$dvalue" "$dunit")" || { users_v2_unlock "$fd"; return 2; }
			suspended_at="$now"
			expires=""
		fi
	fi
	document="$(jq --arg id "$id" --arg iid "$identity_id" --arg cid "$connection_id" --arg alias "$alias" --arg protocol "$protocol" --arg ctype "$ctype" --arg cvalue "$cvalue" --arg now "$now" --arg state "$state" --arg dkind "$dkind" --argjson dvalue "$dvalue" --arg dunit "$dunit" --arg expires "$expires" --arg suspended_at "$suspended_at" --argjson remaining "$remaining" --argjson traffic "$traffic" --argjson simultaneous "$simultaneous" '
		.associations += [{
			id:$id,identity_id:$iid,connection_id:$cid,alias:$alias,protocol:$protocol,
			credential:{type:$ctype,value:$cvalue},created_at:$now,
			duration:(if $dkind == "unlimited" then {kind:"unlimited"} else {kind:"custom",value:$dvalue,unit:$dunit} end),
			expires_at:(if $expires == "" then null else $expires end),suspended_at:(if $suspended_at == "" then null else $suspended_at end),remaining_seconds:(if $dkind == "unlimited" then null elif $state == "suspended" then $remaining else null end),traffic_limit_bytes:(if $traffic == 0 then null else $traffic end),
			simultaneous_connection_limit:(if $simultaneous == 0 then null else $simultaneous end),
			state:$state,provisioning_status:"draft",runtime:{status:"not_applied",last_applied_at:null}
		}]' "$USERS_V2_DATA_FILE")" || {
		users_v2_unlock "$fd"
		return 1
	}
	if ! users_v2_commit_document "$document"; then
		users_v2_unlock "$fd"
		return 1
	fi
	users_v2_unlock "$fd"
	printf '%s\n' "$id"
}

# Pause an active association and preserve its remaining seconds.
users_association_suspend() {
	[[ "$#" -eq 1 ]] || return 2
	local fd id="$1" now now_epoch expires expiry_epoch remaining=null document assoc
	users_v2_lock fd || return 1
	assoc="$(jq -ce --arg id "$id" '.associations[] | select(.id == $id)' "$USERS_V2_DATA_FILE")" || { users_v2_unlock "$fd"; return 1; }
	[[ "$(jq -r '.state' <<<"$assoc")" == active ]] || { users_v2_unlock "$fd"; return 1; }
	now="$(users_v2_now)"
	now_epoch="$(date -u -d "$now" +%s)" || { users_v2_unlock "$fd"; return 1; }
	expires="$(jq -r '.expires_at // empty' <<<"$assoc")"
	if [[ -n "$expires" ]]; then
		expiry_epoch="$(date -u -d "$expires" +%s)" || { users_v2_unlock "$fd"; return 1; }
		if ((expiry_epoch <= now_epoch)); then
			document="$(jq --arg id "$id" '(.associations[] | select(.id == $id)).state = "expired"' "$USERS_V2_DATA_FILE")"
			users_v2_commit_document "$document" || { users_v2_unlock "$fd"; return 1; }
			users_v2_unlock "$fd"
			return 1
		fi
		remaining=$((expiry_epoch - now_epoch))
	fi
	document="$(jq --arg id "$id" --arg now "$now" --argjson remaining "$remaining" '
		(.associations[] | select(.id == $id)) |= (.state = "suspended" | .suspended_at = $now | .remaining_seconds = $remaining | .expires_at = null)
	' "$USERS_V2_DATA_FILE")" || { users_v2_unlock "$fd"; return 1; }
	if ! users_v2_commit_document "$document"; then users_v2_unlock "$fd"; return 1; fi
	users_v2_unlock "$fd"
}

# Reactivation starts a fresh duration; the previous remainder is not carried over.
users_association_reactivate() {
	[[ "$#" -eq 4 ]] || return 2
	local id="$1" kind="$2" value="$3" unit="$4" fd now expires="" document
	users_v2_duration_args "$kind" "$value" "$unit" || return 2
	users_v2_lock fd || return 1
	jq -e --arg id "$id" 'any(.associations[]; .id == $id and .state == "suspended")' "$USERS_V2_DATA_FILE" >/dev/null || { users_v2_unlock "$fd"; return 1; }
	now="$(users_v2_now)"
	if [[ "$kind" == custom ]]; then
		expires="$(users_v2_expiration_from "$now" "$value" "$unit")" || { users_v2_unlock "$fd"; return 2; }
	fi
	document="$(jq --arg id "$id" --arg kind "$kind" --arg unit "$unit" --arg expires "$expires" --argjson value "$value" '
		(.associations[] | select(.id == $id)) |= (
			.state = "active" |
			.duration = (if $kind == "unlimited" then {kind:"unlimited"} else {kind:"custom",value:$value,unit:$unit} end) |
			.expires_at = (if $expires == "" then null else $expires end) |
			.suspended_at = null | .remaining_seconds = null
		)
	' "$USERS_V2_DATA_FILE")" || { users_v2_unlock "$fd"; return 1; }
	if ! users_v2_commit_document "$document"; then users_v2_unlock "$fd"; return 1; fi
	users_v2_unlock "$fd"
}

# Renewal begins now, replaces the previous expiry and can reactivate an expired association.
users_association_renew() {
	[[ "$#" -eq 4 ]] || return 2
	local id="$1" kind="$2" value="$3" unit="$4" fd now expires="" document
	users_v2_duration_args "$kind" "$value" "$unit" || return 2
	users_v2_lock fd || return 1
	jq -e --arg id "$id" 'any(.associations[]; .id == $id and (.state == "active" or .state == "expired"))' "$USERS_V2_DATA_FILE" >/dev/null || { users_v2_unlock "$fd"; return 1; }
	now="$(users_v2_now)"
	if [[ "$kind" == custom ]]; then
		expires="$(users_v2_expiration_from "$now" "$value" "$unit")" || { users_v2_unlock "$fd"; return 2; }
	fi
	document="$(jq --arg id "$id" --arg kind "$kind" --arg unit "$unit" --arg expires "$expires" --argjson value "$value" '
		(.associations[] | select(.id == $id)) |= (
			.state = "active" |
			.duration = (if $kind == "unlimited" then {kind:"unlimited"} else {kind:"custom",value:$value,unit:$unit} end) |
			.expires_at = (if $expires == "" then null else $expires end) |
			.suspended_at = null | .remaining_seconds = null
		)
	' "$USERS_V2_DATA_FILE")" || { users_v2_unlock "$fd"; return 1; }
	if ! users_v2_commit_document "$document"; then users_v2_unlock "$fd"; return 1; fi
	users_v2_unlock "$fd"
}

# Duration modification recalculates from modification time; suspended time stays paused.
users_association_set_duration() {
	[[ "$#" -eq 4 ]] || return 2
	local id="$1" kind="$2" value="$3" unit="$4" fd now expires="" remaining=null state document assoc
	users_v2_duration_args "$kind" "$value" "$unit" || return 2
	users_v2_lock fd || return 1
	assoc="$(jq -ce --arg id "$id" '.associations[] | select(.id == $id)' "$USERS_V2_DATA_FILE")" || { users_v2_unlock "$fd"; return 1; }
	state="$(jq -r '.state' <<<"$assoc")"
	[[ "$state" == active || "$state" == suspended ]] || { users_v2_unlock "$fd"; return 1; }
	now="$(users_v2_now)"
	if [[ "$kind" == custom ]]; then
		if [[ "$state" == suspended ]]; then
			remaining="$(users_v2_duration_seconds "$value" "$unit")" || { users_v2_unlock "$fd"; return 2; }
		else
			expires="$(users_v2_expiration_from "$now" "$value" "$unit")" || { users_v2_unlock "$fd"; return 2; }
		fi
	fi
	document="$(jq --arg id "$id" --arg kind "$kind" --arg unit "$unit" --arg expires "$expires" --argjson value "$value" --argjson remaining "$remaining" '
		(.associations[] | select(.id == $id)) |= (
			.duration = (if $kind == "unlimited" then {kind:"unlimited"} else {kind:"custom",value:$value,unit:$unit} end) |
			.expires_at = (if $expires == "" then null else $expires end) |
			.remaining_seconds = (if $kind == "unlimited" then null elif .state == "suspended" then $remaining else null end)
		)
	' "$USERS_V2_DATA_FILE")" || { users_v2_unlock "$fd"; return 1; }
	if ! users_v2_commit_document "$document"; then users_v2_unlock "$fd"; return 1; fi
	users_v2_unlock "$fd"
}

# Called periodically and at manager/service startup. Optional epoch supports deterministic tests.
users_v2_expire_due() {
	[[ "$#" -le 1 ]] || return 2
	local fd now_epoch now document before after count
	now_epoch="${1:-$(date -u +%s)}"
	[[ "$now_epoch" =~ ^[0-9]+$ ]] || return 2
	now="$(date -u -d "@$now_epoch" '+%Y-%m-%dT%H:%M:%SZ')" || return 2
	users_v2_lock fd || return 1
	before="$(jq '[.associations[] | select(.state == "expired")] | length' "$USERS_V2_DATA_FILE")"
	document="$(jq --arg now "$now" '
		.associations |= map(if .state == "active" and .duration.kind == "custom" and .expires_at <= $now then .state = "expired" else . end)
	' "$USERS_V2_DATA_FILE")" || { users_v2_unlock "$fd"; return 1; }
	after="$(jq '[.associations[] | select(.state == "expired")] | length' <<<"$document")"
	count=$((after - before))
	if [[ "$document" != "$(cat "$USERS_V2_DATA_FILE")" ]]; then
		if ! users_v2_commit_document "$document"; then users_v2_unlock "$fd"; return 1; fi
	fi
	users_v2_unlock "$fd"
	printf '%s\n' "$count"
}

users_association_set_alias() {
	[[ "$#" -eq 2 && -n "$2" && "${#2}" -le 64 ]] || return 2
	local fd document
	users_v2_lock fd || return 1
	jq -e --arg id "$1" 'any(.associations[]; .id == $id)' "$USERS_V2_DATA_FILE" >/dev/null || {
		users_v2_unlock "$fd"
		return 1
	}
	document="$(jq --arg id "$1" --arg alias "$2" '(.associations[] | select(.id == $id)).alias = $alias' "$USERS_V2_DATA_FILE")"
	if ! users_v2_commit_document "$document"; then
		users_v2_unlock "$fd"
		return 1
	fi
	users_v2_unlock "$fd"
}

users_association_delete() {
	[[ "$#" -eq 1 ]] || return 2
	local fd document
	users_v2_lock fd || return 1
	jq -e --arg id "$1" 'any(.associations[]; .id == $id)' "$USERS_V2_DATA_FILE" >/dev/null || {
		users_v2_unlock "$fd"
		return 1
	}
	document="$(jq --arg id "$1" '.associations |= map(select(.id != $id))' "$USERS_V2_DATA_FILE")"
	if ! users_v2_commit_document "$document"; then
		users_v2_unlock "$fd"
		return 1
	fi
	users_v2_unlock "$fd"
}

users_identity_delete() {
	[[ "$#" -eq 1 ]] || return 2
	local fd document
	users_v2_lock fd || return 1
	jq -e --arg id "$1" 'any(.identities[]; .id == $id)' "$USERS_V2_DATA_FILE" >/dev/null || {
		users_v2_unlock "$fd"
		return 1
	}
	document="$(jq --arg id "$1" '{schema_version,identities:(.identities | map(select(.id != $id))),associations:(.associations | map(select(.identity_id != $id)))}' "$USERS_V2_DATA_FILE")"
	if ! users_v2_commit_document "$document"; then
		users_v2_unlock "$fd"
		return 1
	fi
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

# Migración pura sobre rutas explícitas; exige estado funcional elegido por el administrador.
# users_v2_migrate_legacy <legacy_json> <connections_json> <output_json> <confirmed_functional_state>
users_v2_migrate_legacy() {
	[[ "$#" -eq 4 && ("$4" == active || "$4" == suspended || "$4" == expired) ]] || return 2
	local legacy="$1" connections="$2" output="$3" state="$4"
	[[ -r "$legacy" && -r "$connections" && ! -e "$output" ]] || return 1
	python3 - "$legacy" "$connections" "$output" "$state" <<'PY'
import json, os, sys, uuid, tempfile
legacy_path, connections_path, output_path, state = sys.argv[1:]
with open(legacy_path, encoding="utf-8") as f:
    legacy = json.load(f)
with open(connections_path, encoding="utf-8") as f:
    connections = json.load(f)
if not isinstance(legacy, list) or not isinstance(connections, list):
    raise SystemExit("legacy/connections debe ser un arreglo JSON")
by_id = {c.get("id"): c for c in connections if isinstance(c, dict)}
seen = set()
identities, associations = [], []
for old in legacy:
    if not isinstance(old, dict) or set(old) != {"uuid", "connection_id", "label", "state", "runtime_applied", "created_at"} or old.get("state") != "draft" or old.get("runtime_applied") is not False:
        raise SystemExit("registro legacy no compatible o con campos inesperados; migración cancelada")
    for key in ("uuid", "connection_id", "label", "created_at"):
        if not isinstance(old.get(key), str) or not old[key]:
            raise SystemExit("campo legacy faltante o inválido: " + key)
    if len(old["label"]) > 64:
        raise SystemExit("alias legacy supera 64 caracteres")
    conn = by_id.get(old["connection_id"])
    if not conn:
        raise SystemExit("conexión inexistente: " + old["connection_id"])
    mode = conn.get("protocol_id", "")
    if not mode.startswith("vless_"):
        raise SystemExit("solo se migra el esquema legacy VLESS; protocolo no compatible")
    try:
        cred = str(uuid.UUID(old["uuid"]))
    except (ValueError, AttributeError):
        raise SystemExit("UUID VLESS legacy inválido")
    if cred in seen:
        raise SystemExit("UUID VLESS duplicado en legacy")
    seen.add(cred)
    protocol = "vless"
    identity_id, association_id = str(uuid.uuid4()), str(uuid.uuid4())
    identities.append({"id": identity_id, "created_at": old["created_at"]})
    associations.append({
        "id": association_id, "identity_id": identity_id,
        "connection_id": old["connection_id"], "alias": old["label"],
        "protocol": protocol,
        "credential": {"type": "uuid" if protocol == "vless" else "legacy", "value": cred},
        "created_at": old["created_at"],
        "duration": {"kind": "unlimited"}, "expires_at": None,
        "suspended_at": old["created_at"] if state == "suspended" else None,
        "remaining_seconds": None, "traffic_limit_bytes": None, "simultaneous_connection_limit": None,
        "state": state, "provisioning_status": "draft",
        "runtime": {"status": "not_applied", "last_applied_at": None}
    })
result = {"schema_version": 2, "identities": identities, "associations": associations}
directory = os.path.dirname(os.path.abspath(output_path))
fd, tmp = tempfile.mkstemp(prefix=".users-v2-migration-", dir=directory)
try:
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.chmod(tmp, 0o600)
    os.replace(tmp, output_path)
    dfd = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try: os.fsync(dfd)
    finally: os.close(dfd)
except Exception:
    try: os.unlink(tmp)
    except FileNotFoundError: pass
    raise
PY
}