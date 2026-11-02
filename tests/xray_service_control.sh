#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT
PREFIX="$TMP/root"
MOCK="$TMP/mock-bin"
mkdir -p "$PREFIX/usr/local/bin" "$PREFIX/etc/xray" "$PREFIX/etc/systemd/system" "$MOCK"
export XRAY_SERVICE_ROOT="$PREFIX"
export XRAY_SERVICE_TEST_MODE=1
export XRAY_SERVICE_TEST_ALLOW_CONTROL=1
export XRAY_ADMIN_BIN=/usr/local/bin/xray
export XRAY_CONFIG_DIR=/etc/xray
export XRAY_CONFIG_FILE=/etc/xray/config.json
export XRAY_MOCK_STATE="$TMP/state"
export XRAY_MOCK_ENABLED="$TMP/enabled"
export XRAY_MOCK_LOG="$TMP/systemctl.log"
export XRAY_TEST_CONFIG_VALID=0
export XRAY_MOCK_FAIL=0
export XRAY_MOCK_STUCK=0
printf 'inactive\n' >"$XRAY_MOCK_STATE"
printf 'disabled\n' >"$XRAY_MOCK_ENABLED"
: >"$XRAY_MOCK_LOG"
printf '{}\n' >"$PREFIX/etc/xray/config.json"
cat >"$PREFIX/usr/local/bin/xray" <<'BIN'
#!/usr/bin/env bash
if [[ "$1 $2" == "run -test" ]]; then
    [[ "$XRAY_TEST_CONFIG_VALID" == 1 ]]
    exit
fi
printf 'Xray fixture\n'
BIN
chmod 755 "$PREFIX/usr/local/bin/xray"

cat >"$MOCK/systemctl" <<'SYSTEMCTL'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"$XRAY_MOCK_LOG"
case "$1" in
    cat) exit 0 ;;
    is-active)
        [[ "$2" == --quiet ]] && unit="$3" || unit="$2"
        state="$(<"$XRAY_MOCK_STATE")"
        if [[ "$state" == active ]]; then
            [[ "$2" == --quiet ]] && exit 0
            printf 'active\n'
            exit 0
        fi
        [[ "$2" == --quiet ]] && exit 3
        printf '%s\n' "$state"
        exit 3
        ;;
    is-enabled)
        [[ "$2" == --quiet ]] && unit="$3" || unit="$2"
        state="$(<"$XRAY_MOCK_ENABLED")"
        if [[ "$state" == enabled ]]; then
            [[ "$2" == --quiet ]] && exit 0
            printf 'enabled\n'
            exit 0
        fi
        [[ "$2" == --quiet ]] && exit 1
        printf '%s\n' "$state"
        exit 1
        ;;
    show)
        property=""
        for arg in "$@"; do
            [[ "$arg" == --property=* ]] && property="${arg#--property=}"
        done
        case "$property" in
            LoadState) printf 'loaded\n' ;;
            SubState) printf '%s\n' "$(<"$XRAY_MOCK_STATE")" ;;
            Result) printf 'success\n' ;;
            ExecMainStatus) printf '0\n' ;;
            ActiveEnterTimestamp) printf 'fixture timestamp\n' ;;
            *) exit 2 ;;
        esac
        ;;
    start|restart)
        [[ "$XRAY_MOCK_FAIL" == 0 ]] || exit 1
        if [[ "$XRAY_MOCK_STUCK" == 0 ]]; then printf 'active\n' >"$XRAY_MOCK_STATE"; fi
        ;;
    stop) printf 'inactive\n' >"$XRAY_MOCK_STATE" ;;
    enable) printf 'enabled\n' >"$XRAY_MOCK_ENABLED" ;;
    disable) printf 'disabled\n' >"$XRAY_MOCK_ENABLED" ;;
    *) exit 2 ;;
esac
SYSTEMCTL
cat >"$MOCK/journalctl" <<'JOURNAL'
#!/usr/bin/env bash
printf '2026-11-01T00:00:00Z xray[123]: fixture log line\n'
JOURNAL
chmod 755 "$MOCK/"*
export PATH="$MOCK:$PATH"

# shellcheck disable=SC1091
source "$ROOT/modules/xray_service.sh"
UNIT="$PREFIX/etc/systemd/system/xray.service"
xray_service_unit_content >"$UNIT"
chmod 644 "$UNIT"

# Invalid config must block start/restart/enable before any mutating systemctl call.
if xray_service_action start >"$TMP/invalid-start.out" 2>&1; then
    echo 'ERROR: start aceptó una configuración inválida.' >&2
    exit 1
fi
grep -q 'no supera la validación' "$TMP/invalid-start.out"
if grep -Eq '^(start|restart|enable) ' "$XRAY_MOCK_LOG"; then
    echo 'ERROR: systemctl recibió una operación mutante antes de validar la configuración.' >&2
    exit 1
fi

# Valid config permits start, and status reports systemd details.
XRAY_TEST_CONFIG_VALID=1
xray_service_action start >"$TMP/start.out"
grep -q 'quedó iniciado y activo' "$TMP/start.out"
[[ "$(<"$XRAY_MOCK_STATE")" == active ]]
xray_service_status >"$TMP/status.out"
grep -q 'Estado:.*active' "$TMP/status.out"
grep -q 'Inicio automático:.*disabled' "$TMP/status.out"
grep -q 'Resultado último:.*success' "$TMP/status.out"
grep -q 'Configuración:.*válida' "$TMP/status.out"
XRAY_TEST_CONFIG_VALID=0
xray_service_status >"$TMP/status-invalid.out" 2>"$TMP/status-invalid.err"
grep -q 'Configuración:.*INVÁLIDA' "$TMP/status-invalid.out"
XRAY_TEST_CONFIG_VALID=1

# Las preferencias no pueden desviar la validación de la ruta real usada por la unidad.
XRAY_CONFIG_FILE=/etc/xray-alt/config.json
if xray_service_action start >"$TMP/mismatched-path.out" 2>&1; then
    echo 'ERROR: se aceptó validar una ruta distinta de la usada por xray.service.' >&2
    exit 1
fi
grep -q 'no coinciden con las rutas fijadas' "$TMP/mismatched-path.out"
XRAY_CONFIG_FILE=/etc/xray/config.json

# Restart failure is surfaced; successful stop does not alter autostart.
XRAY_MOCK_FAIL=1
if xray_service_action restart >"$TMP/restart-fail.out" 2>&1; then
    echo 'ERROR: se ocultó el fallo de systemctl restart.' >&2
    exit 1
fi
grep -q 'no pudo reiniciar Xray' "$TMP/restart-fail.out"
XRAY_MOCK_FAIL=0
xray_service_action stop >"$TMP/stop.out"
[[ "$(<"$XRAY_MOCK_STATE")" == inactive ]]
[[ "$(<"$XRAY_MOCK_ENABLED")" == disabled ]]

# A start command that exits successfully but does not activate is rejected.
XRAY_MOCK_STUCK=1
if xray_service_action start >"$TMP/stuck.out" 2>&1; then
    echo 'ERROR: se informó éxito sin confirmar estado active.' >&2
    exit 1
fi
grep -q 'no confirmó que Xray quedó activo' "$TMP/stuck.out"
XRAY_MOCK_STUCK=0

# Enabling requires a valid config, enables only autostart, and does not start Xray.
XRAY_TEST_CONFIG_VALID=0
if xray_service_action enable >"$TMP/invalid-enable.out" 2>&1; then
    echo 'ERROR: se habilitó autostart con config inválida.' >&2
    exit 1
fi
XRAY_TEST_CONFIG_VALID=1
xray_service_action enable >"$TMP/enable.out"
[[ "$(<"$XRAY_MOCK_ENABLED")" == enabled ]]
[[ "$(<"$XRAY_MOCK_STATE")" == inactive ]]
xray_service_action disable >"$TMP/disable.out"
[[ "$(<"$XRAY_MOCK_ENABLED")" == disabled ]]

# Journal query is bounded; invalid limits and foreign/tampered units are rejected.
xray_service_show_logs 50 >"$TMP/logs.out"
grep -q 'fixture log line' "$TMP/logs.out"
if xray_service_show_logs 201 >/dev/null 2>&1; then
    echo 'ERROR: se aceptó un límite excesivo de journal.' >&2
    exit 1
fi
printf '[Unit]\nDescription=foreign unit\n' >"$UNIT"
if xray_service_action stop >"$TMP/foreign.out" 2>&1; then
    echo 'ERROR: se permitió operar sobre una unidad no administrada.' >&2
    exit 1
fi
grep -q 'no coincide con la unidad administrada' "$TMP/foreign.out"

# The control module never creates config.json.
rm -f "$PREFIX/etc/xray/config.json"
if xray_service_action start >"$TMP/missing-config.out" 2>&1; then
    echo 'ERROR: se inició Xray sin config.json.' >&2
    exit 1
fi
[[ ! -e "$PREFIX/etc/xray/config.json" ]]

printf '%s\n' 'OK: control aislado start/stop/restart/enable/disable, validación previa, estado, logs y bloqueos de seguridad.'