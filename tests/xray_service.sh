#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT
PREFIX="$TMP/root"
mkdir -p "$PREFIX/usr/local/bin" "$PREFIX/usr/local/share/xray"
cat >"$PREFIX/usr/local/bin/xray" <<'BIN'
#!/usr/bin/env bash
if [[ "$1 $2" == "run -test" ]]; then
    if [[ "${XRAY_TEST_CONFIG_VALID:-0}" == 1 ]]; then
        exit 0
    else
        exit 1
    fi
fi
printf 'Xray 26.10.31 test fixture\n'
BIN
chmod 755 "$PREFIX/usr/local/bin/xray"
printf 'geoip\n' >"$PREFIX/usr/local/share/xray/geoip.dat"
printf 'geosite\n' >"$PREFIX/usr/local/share/xray/geosite.dat"

export XRAY_SERVICE_ROOT="$PREFIX"
export XRAY_SERVICE_TEST_MODE=1
export XRAY_ADMIN_BIN=/usr/local/bin/xray
export XRAY_ADMIN_DATA=/usr/local/share/xray
export XRAY_CONFIG_DIR=/etc/xray
export XRAY_CONFIG_FILE=/etc/xray/config.json
# shellcheck disable=SC1091
source "$ROOT/modules/xray_service.sh"

xray_service_prepare >"$TMP/prepare.out"
UNIT="$PREFIX/etc/systemd/system/xray.service"
[[ -f "$UNIT" ]]
[[ "$(stat -c '%a' "$UNIT")" == 644 ]]
[[ "$(stat -c '%a' "$PREFIX/etc/xray")" == 750 ]]
[[ "$(stat -c '%a' "$PREFIX/var/lib/xray")" == 750 ]]
grep -Fq 'User=xray' "$UNIT"
grep -Fq 'ConditionPathExists=/etc/xray/config.json' "$UNIT"
grep -Fq 'Group=xray' "$UNIT"
grep -Fq 'ExecStartPre=/usr/local/bin/xray run -test -config /etc/xray/config.json' "$UNIT"
grep -Fq 'ExecStart=/usr/local/bin/xray run -config /etc/xray/config.json' "$UNIT"
grep -Fq 'NoNewPrivileges=true' "$UNIT"
grep -Fq 'ProtectSystem=strict' "$UNIT"
grep -Fq 'AmbientCapabilities=CAP_NET_BIND_SERVICE' "$UNIT"
grep -Fq 'WantedBy=multi-user.target' "$UNIT"
if grep -Eq 'systemctl (enable|start|restart)' "$UNIT"; then exit 1; fi
grep -Fq 'permanece detenido y no se habilitó' "$TMP/prepare.out"

before="$(sha256sum "$UNIT" | awk '{print $1}')"
xray_service_prepare >"$TMP/prepare-again.out"
after="$(sha256sum "$UNIT" | awk '{print $1}')"
[[ "$before" == "$after" ]]

printf '[Unit]\nDescription=foreign unit\n' >"$UNIT"
if xray_service_prepare >"$TMP/collision.out" 2>&1; then
    printf 'ERROR: se sobrescribió una unidad systemd preexistente.\n' >&2
    exit 1
fi
grep -q 'unidad xray.service diferente' "$TMP/collision.out"
grep -q 'Description=foreign unit' "$UNIT"

rm -f "$UNIT"
mkdir -p "$PREFIX/etc/xray"
printf '{"invalid":true}\n' >"$PREFIX/etc/xray/config.json"
if xray_service_prepare >"$TMP/invalid-config.out" 2>&1; then
    printf 'ERROR: se aceptó una configuración que Xray rechazó.\n' >&2
    exit 1
fi
grep -q 'no supera la validación' "$TMP/invalid-config.out"
[[ ! -e "$UNIT" ]]
[[ "$(stat -c '%a' "$PREFIX/etc/xray/config.json")" == 640 ]]

rm -rf "$PREFIX/etc/xray" "$PREFIX/etc/systemd"
mkdir -p "$PREFIX/etc"
ln -s "$TMP" "$PREFIX/etc/systemd"
if xray_service_prepare >"$TMP/symlink.out" 2>&1; then
    printf 'ERROR: se aceptó un directorio systemd simbólico.\n' >&2
    exit 1
fi
grep -q 'componente simbólico' "$TMP/symlink.out"

# La creación/validación de cuenta usa comandos simulados; nunca modifica /etc/passwd.
MOCK_BIN="$TMP/mock-bin"
mkdir -p "$MOCK_BIN"
export XRAY_MOCK_LOG="$TMP/account.log"
export XRAY_MOCK_ACCOUNT=missing
export XRAY_MOCK_PRIMARY_GROUP=xray
export XRAY_MOCK_UID=995
cat >"$MOCK_BIN/getent" <<'MOCK'
#!/usr/bin/env bash
if [[ "$XRAY_MOCK_ACCOUNT" == existing ]]; then
    case "$1:$2" in
        group:xray) printf 'xray:x:995:\n'; exit 0 ;;
        passwd:xray) printf 'xray:x:995:995::/var/lib/xray:/usr/sbin/nologin\n'; exit 0 ;;
    esac
fi
exit 2
MOCK
cat >"$MOCK_BIN/groupadd" <<'MOCK'
#!/usr/bin/env bash
printf 'groupadd %s\n' "$*" >>"$XRAY_MOCK_LOG"
MOCK
cat >"$MOCK_BIN/useradd" <<'MOCK'
#!/usr/bin/env bash
printf 'useradd %s\n' "$*" >>"$XRAY_MOCK_LOG"
MOCK
cat >"$MOCK_BIN/id" <<'MOCK'
#!/usr/bin/env bash
case "$1" in
    -gn) printf '%s\n' "$XRAY_MOCK_PRIMARY_GROUP" ;;
    -u) printf '%s\n' "$XRAY_MOCK_UID" ;;
    *) exit 2 ;;
esac
MOCK
chmod 755 "$MOCK_BIN/"*
old_path="$PATH"
PATH="$MOCK_BIN:$PATH"
export PATH
: >"$XRAY_MOCK_LOG"
xray_service_ensure_account
grep -Fq 'groupadd --system xray' "$XRAY_MOCK_LOG"
grep -Fq -- '--gid xray' "$XRAY_MOCK_LOG"

XRAY_MOCK_ACCOUNT=existing
: >"$XRAY_MOCK_LOG"
xray_service_ensure_account
[[ ! -s "$XRAY_MOCK_LOG" ]]

XRAY_MOCK_PRIMARY_GROUP=users
if xray_service_ensure_account >"$TMP/account-mismatch.out" 2>&1; then
    printf 'ERROR: se aceptó un usuario xray con grupo primario incorrecto.\n' >&2
    exit 1
fi
grep -q 'grupo primario esperado' "$TMP/account-mismatch.out"
PATH="$old_path"
export PATH

if command -v systemd-analyze >/dev/null 2>&1; then
    VERIFY_UNIT="$TMP/verify-xray.service"
    xray_service_unit_content >"$VERIFY_UNIT"
    sed -i \
        -e 's|/usr/local/bin/xray run -test -config /etc/xray/config.json|/usr/bin/true|' \
        -e 's|/usr/local/bin/xray run -config /etc/xray/config.json|/usr/bin/true|' \
        -e 's|WorkingDirectory=/var/lib/xray|WorkingDirectory=/tmp|' \
        "$VERIFY_UNIT"
    systemd-analyze verify "$VERIFY_UNIT"
fi

printf '%s\n' 'OK: unidad endurecida, identidad aislada, idempotencia, colisiones, validación de configuración y rutas simbólicas.'
