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
cat >"$XRAY_MANAGER_CONNECTIONS_FILE" <<'JSON'
[
  {"id":"conn-vless","name":"VLESS de prueba","protocol_id":"vless_ws","max_users":3},
  {"id":"conn-wg","name":"WireGuard de prueba","protocol_id":"wireguard","max_users":3},
  {"id":"conn-cap","name":"VLESS capacidad uno","protocol_id":"vless_tcp_tls","max_users":1}
]
JSON
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

# El detalle de asociación muestra los campos administrativos, oculta credenciales
# y no modifica el documento.
cp "$XRAY_MANAGER_USERS_FILE" "$TMP/detail.before"
printf '5\n22222222-2222-4222-8222-222222222222\n\n0\n' | users_v2_menu >"$OUT"
grep -q 'DETALLE DE ASOCIACIÓN' "$OUT"
grep -q 'ID de identidad: 11111111-1111-4111-8111-111111111111' "$OUT"
grep -q 'Alias: Cliente demo' "$OUT"
grep -q 'Runtime: not_applied' "$OUT"
grep -Fq 'Credencial: [oculta]' "$OUT"
if grep -q '33333333-3333-4333-8333-333333333333' "$OUT"; then
	echo 'ERROR: el detalle mostró una credencial sensible.' >&2
	exit 1
fi
cmp -s "$TMP/detail.before" "$XRAY_MANAGER_USERS_FILE"

# Un identificador inexistente se rechaza sin escritura.
if printf '00000000-0000-4000-8000-000000000000\n' | users_v2_menu_association_detail >"$OUT"; then
	echo 'ERROR: el detalle aceptó una asociación inexistente.' >&2
	exit 1
fi
cmp -s "$TMP/detail.before" "$XRAY_MANAGER_USERS_FILE"
grep -q 'asociación indicada no existe' "$OUT"

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

# Creación desde el menú v2: identidad global y asociación VLESS.
rm -f "$XRAY_MANAGER_USERS_FILE"
printf '3\ns\n\n0\n' | users_v2_menu >"$OUT"
IDENTITY_ID="$(sed -n 's/^ID: //p' "$OUT" | tail -n1)"
[[ "$IDENTITY_ID" =~ ^[0-9a-f-]{36}$ ]]
jq -e --arg id "$IDENTITY_ID" 'any(.identities[]; .id==$id) and (.associations|length)==0' "$XRAY_MANAGER_USERS_FILE" >/dev/null

VLESS_SECRET='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
printf '4\n%s\nconn-vless\nCliente desde menú\n%s\nactive\nunlimited\n0\n0\ns\n\n0\n' \
	"$IDENTITY_ID" "$VLESS_SECRET" | users_v2_menu >"$OUT"
VLESS_ASSOC_ID="$(sed -n 's/^ID de asociación: //p' "$OUT" | tail -n1)"
[[ "$VLESS_ASSOC_ID" =~ ^[0-9a-f-]{36}$ ]]
jq -e --arg id "$VLESS_ASSOC_ID" --arg iid "$IDENTITY_ID" --arg secret "$VLESS_SECRET" '
  any(.associations[]; .id==$id and .identity_id==$iid and .connection_id=="conn-vless" and
      .protocol=="vless" and .alias=="Cliente desde menú" and
      .credential.type=="uuid" and .credential.value==$secret and
      .state=="active" and .provisioning_status=="draft" and
      .runtime.status=="not_applied" and .duration.kind=="unlimited")
' "$XRAY_MANAGER_USERS_FILE" >/dev/null
if grep -Fq "$VLESS_SECRET" "$OUT"; then
	echo 'ERROR: el menú imprimió la credencial VLESS.' >&2
	exit 1
fi
grep -q 'Runtime: sin cambios (not_applied)' "$OUT"

# WireGuard selecciona automáticamente public_key y admite múltiples peers.
WG_SECRET='wireguard-public-key-fixture'
printf '4\n%s\nconn-wg\nPeer de prueba\n%s\nsuspended\ncustom\n2\nhours\n4096\n2\ns\n\n0\n' \
	"$IDENTITY_ID" "$WG_SECRET" | users_v2_menu >"$OUT"
WG_ASSOC_ID="$(sed -n 's/^ID de asociación: //p' "$OUT" | tail -n1)"
[[ "$WG_ASSOC_ID" =~ ^[0-9a-f-]{36}$ ]]
jq -e --arg id "$WG_ASSOC_ID" --arg secret "$WG_SECRET" '
  any(.associations[]; .id==$id and .protocol=="wireguard" and
      .credential.type=="public_key" and .credential.value==$secret and
      .state=="suspended" and .duration.kind=="custom" and
      .duration.value==2 and .duration.unit=="hours" and
      .remaining_seconds==7200 and .traffic_limit_bytes==4096 and
      .simultaneous_connection_limit==2 and .runtime.status=="not_applied")
' "$XRAY_MANAGER_USERS_FILE" >/dev/null
if grep -Fq "$WG_SECRET" "$OUT"; then
	echo 'ERROR: el menú imprimió la clave pública WireGuard.' >&2
	exit 1
fi

# Identidad inexistente: aborta antes de solicitar credenciales o modificar datos.
cp "$XRAY_MANAGER_USERS_FILE" "$TMP/before-invalid-identity"
if printf '00000000-0000-4000-8000-000000000000\n' | users_v2_menu_create_association >"$OUT"; then
	echo 'ERROR: se aceptó una identidad inexistente.' >&2
	exit 1
fi
cmp -s "$TMP/before-invalid-identity" "$XRAY_MANAGER_USERS_FILE"
grep -q 'identidad indicada no existe' "$OUT"

# Conexión inexistente: aborta sin alterar el registro.
cp "$XRAY_MANAGER_USERS_FILE" "$TMP/before-invalid-connection"
if printf '%s\nno-existe\n' "$IDENTITY_ID" | users_v2_menu_create_association >"$OUT"; then
	echo 'ERROR: se aceptó una conexión inexistente.' >&2
	exit 1
fi
cmp -s "$TMP/before-invalid-connection" "$XRAY_MANAGER_USERS_FILE"
grep -q 'conexión indicada no existe' "$OUT"

# La validación del dominio sigue rechazando UUID VLESS duplicados.
if printf '%s\nconn-vless\nUUID duplicado\n%s\nactive\nunlimited\n0\n0\ns\n' \
	"$IDENTITY_ID" "$VLESS_SECRET" | users_v2_menu_create_association >"$OUT"; then
	echo 'ERROR: el menú aceptó un UUID VLESS duplicado.' >&2
	exit 1
fi
[[ "$(jq '[.associations[]]|length' "$XRAY_MANAGER_USERS_FILE")" -eq 2 ]]

# La capacidad de la conexión se respeta en el alta desde el menú.
CAP_ID="$(users_identity_create)"
printf '%s\nconn-cap\nPrimer slot\ncccccccc-cccc-4ccc-8ccc-cccccccccccc\nactive\nunlimited\n0\n0\ns\n' \
	"$CAP_ID" | users_v2_menu_create_association >"$OUT"
if printf '%s\nconn-cap\nSlot excedido\ndddddddd-dddd-4ddd-8ddd-dddddddddddd\nactive\nunlimited\n0\n0\ns\n' \
	"$CAP_ID" | users_v2_menu_create_association >"$OUT"; then
	echo 'ERROR: el menú permitió superar max_users.' >&2
	exit 1
fi
[[ "$(jq '[.associations[]|select(.connection_id=="conn-cap")]|length' "$XRAY_MANAGER_USERS_FILE")" -eq 1 ]]

# El flujo de opciones [3] y [4] está conectado al menú principal v2.
printf '0\n' | users_v2_menu >"$OUT"
grep -q 'Crear identidad global' "$OUT"
grep -q 'Asociar identidad a conexión' "$OUT"
grep -q 'Consultar detalle de asociación' "$OUT"
grep -q 'Editar alias y límites de asociación' "$OUT"
grep -q 'Suspender / reactivar asociación' "$OUT"

# Editar alias y límites desde menú: modifica solo los tres campos solicitados.
cp "$XRAY_MANAGER_USERS_FILE" "$TMP/edit.before"
printf '6\n%s\nCliente editado\n8192\n4\ns\n\n0\n' "$VLESS_ASSOC_ID" | users_v2_menu >"$OUT"
grep -q 'EDITAR ALIAS Y LÍMITES' "$OUT"
grep -q 'Asociación actualizada correctamente' "$OUT"
jq -e --arg id "$VLESS_ASSOC_ID" --arg secret "$VLESS_SECRET" '
  any(.associations[]; .id==$id and .alias=="Cliente editado" and
      .traffic_limit_bytes==8192 and .simultaneous_connection_limit==4 and
      .credential.value==$secret and .state=="active" and
      .duration.kind=="unlimited" and .provisioning_status=="draft" and
      .runtime.status=="not_applied")
' "$XRAY_MANAGER_USERS_FILE" >/dev/null
[[ "$(jq '[.associations[]|select(.id==$id)]|length' --arg id "$VLESS_ASSOC_ID" "$XRAY_MANAGER_USERS_FILE")" -eq 1 ]]

# El cero elimina ambos límites (null) y se permiten alias repetidos.
users_association_update "$VLESS_ASSOC_ID" "Alias repetible" 0 0
jq -e --arg id "$VLESS_ASSOC_ID" '
  any(.associations[]; .id==$id and .alias=="Alias repetible" and
      .traffic_limit_bytes==null and .simultaneous_connection_limit==null)
' "$XRAY_MANAGER_USERS_FILE" >/dev/null
users_association_update "$WG_ASSOC_ID" "Alias repetible" 0 0
[[ "$(jq '[.associations[]|select(.alias=="Alias repetible")]|length' "$XRAY_MANAGER_USERS_FILE")" -eq 2 ]]

# Entradas inválidas o asociación inexistente se rechazan sin escribir.
cp "$XRAY_MANAGER_USERS_FILE" "$TMP/edit.invalid.before"
if users_association_update "$VLESS_ASSOC_ID" " alias con espacios " 100 2; then
	echo 'ERROR: se aceptó un alias con espacios externos.' >&2
	exit 1
fi
if users_association_update "$VLESS_ASSOC_ID" "Alias" -1 2; then
	echo 'ERROR: se aceptó un límite negativo.' >&2
	exit 1
fi
if users_association_update "$VLESS_ASSOC_ID" "Alias" 100 1.5; then
	echo 'ERROR: se aceptó un límite no entero.' >&2
	exit 1
fi
if users_association_update "$VLESS_ASSOC_ID" "Alias" 9007199254740992 2; then
	echo 'ERROR: se aceptó un límite fuera del rango entero seguro.' >&2
	exit 1
fi
if users_association_update "00000000-0000-4000-8000-000000000000" "Alias" 100 2; then
	echo 'ERROR: se actualizó una asociación inexistente.' >&2
	exit 1
fi
cmp -s "$TMP/edit.invalid.before" "$XRAY_MANAGER_USERS_FILE"

# Cancelación del menú conserva el registro byte a byte.
cp "$XRAY_MANAGER_USERS_FILE" "$TMP/edit.cancel.before"
printf '6\n%s\nNo guardar\n500\n3\nn\n\n0\n' "$VLESS_ASSOC_ID" | users_v2_menu >"$OUT"
cmp -s "$TMP/edit.cancel.before" "$XRAY_MANAGER_USERS_FILE"

# Suspender una asociación activa conserva estado funcional separado del runtime.
cp "$XRAY_MANAGER_USERS_FILE" "$TMP/state.before-suspend"
printf '7\n%s\ns\n\n0\n' "$VLESS_ASSOC_ID" | users_v2_menu >"$OUT"
grep -q 'Asociación suspendida' "$OUT"
jq -e --arg id "$VLESS_ASSOC_ID" --arg secret "$VLESS_SECRET" '
  any(.associations[]; .id==$id and .state=="suspended" and
      .suspended_at!=null and .remaining_seconds==null and .expires_at==null and
      .credential.value==$secret and .runtime.status=="not_applied" and
      .provisioning_status=="draft")
' "$XRAY_MANAGER_USERS_FILE" >/dev/null

# Reactivar una asociación suspendida requiere nueva duración y la calcula desde ahora.
printf '7\n%s\ncustom\n3\ndays\ns\n\n0\n' "$WG_ASSOC_ID" | users_v2_menu >"$OUT"
grep -q 'Asociación reactivada correctamente' "$OUT"
jq -e --arg id "$WG_ASSOC_ID" --arg secret "$WG_SECRET" '
  any(.associations[]; .id==$id and .state=="active" and
      .duration.kind=="custom" and .duration.value==3 and .duration.unit=="days" and
      .expires_at!=null and .suspended_at==null and .remaining_seconds==null and
      .credential.value==$secret and .runtime.status=="not_applied")
' "$XRAY_MANAGER_USERS_FILE" >/dev/null

# Al suspender una duración limitada se pausa el tiempo restante y se borra expires_at.
printf '7\n%s\ns\n\n0\n' "$WG_ASSOC_ID" | users_v2_menu >"$OUT"
grep -q 'tiempo restante quedó pausado' "$OUT"
jq -e --arg id "$WG_ASSOC_ID" '
  any(.associations[]; .id==$id and .state=="suspended" and
      .duration.kind=="custom" and .remaining_seconds>0 and
      .expires_at==null and .suspended_at!=null)
' "$XRAY_MANAGER_USERS_FILE" >/dev/null

# Cancelar suspensión/reactivación o introducir duración inválida no escribe.
cp "$XRAY_MANAGER_USERS_FILE" "$TMP/state.cancel.before"
printf '7\n%s\nunlimited\nn\n\n0\n' "$VLESS_ASSOC_ID" | users_v2_menu >"$OUT"
cmp -s "$TMP/state.cancel.before" "$XRAY_MANAGER_USERS_FILE"
if printf '%s\nbogus\n' "$WG_ASSOC_ID" | users_v2_menu_association_state >"$OUT"; then
	echo 'ERROR: se aceptó una duración inválida al reactivar.' >&2
	exit 1
fi
cmp -s "$TMP/state.cancel.before" "$XRAY_MANAGER_USERS_FILE"

# Asociación inexistente y estado vencido no se reactivan por este flujo.
if printf '00000000-0000-4000-8000-000000000000\n' | users_v2_menu_association_state >"$OUT"; then
	echo 'ERROR: se aceptó una asociación inexistente para cambio de estado.' >&2
	exit 1
fi
cp "$XRAY_MANAGER_USERS_FILE" "$TMP/state.expired.before"
jq --arg id "$VLESS_ASSOC_ID" '(.associations[]|select(.id==$id)) |= (.state="expired" | .suspended_at=null | .remaining_seconds=null)' "$XRAY_MANAGER_USERS_FILE" >"$TMP/state.expired"
mv "$TMP/state.expired" "$XRAY_MANAGER_USERS_FILE"
cp "$XRAY_MANAGER_USERS_FILE" "$TMP/state.expired.expected"
if printf '%s\n' "$VLESS_ASSOC_ID" | users_v2_menu_association_state >"$OUT"; then
	echo 'ERROR: se intentó reactivar una asociación vencida desde el flujo de suspensión.' >&2
	exit 1
fi
cmp -s "$TMP/state.expired.expected" "$XRAY_MANAGER_USERS_FILE"

echo 'OK: selector legacy/v2, consultas protegidas, creación, edición, suspensión/reactivación, duración pausada, validaciones y runtime sin cambios.'