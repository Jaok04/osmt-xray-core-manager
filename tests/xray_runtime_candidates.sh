#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT

STORE="$TMP/runtime/candidates"
BIN="$TMP/xray"
CANDIDATE="$TMP/config.json"
mkdir -p "$TMP"
cat >"$BIN" <<'XRAY'
#!/usr/bin/env python3
import pathlib, sys
if sys.argv[1:4] != ["run", "-test", "-config"]:
    raise SystemExit(90)
if "reject" in pathlib.Path(sys.argv[4]).read_text():
    raise SystemExit(23)
raise SystemExit(0)
XRAY
chmod 755 "$BIN"
cat >"$CANDIDATE" <<'JSON'
{"log":{"loglevel":"warning"},"inbounds":[],"outbounds":[{"protocol":"freedom","tag":"direct"}]}
JSON

run_stage() {
	python3 "$ROOT/scripts/xray_runtime_candidates.py" stage \
		--candidate "$CANDIDATE" --xray-binary "$BIN" --store "$STORE" \
		--profile-id profile-test --profile-revision r000001
}

result="$(run_stage)"
python3 - "$result" "$STORE" <<'PY'
import hashlib, json, pathlib, stat, sys
result = json.loads(sys.argv[1])
store = pathlib.Path(sys.argv[2])
assert result["status"] == "STAGED"
assert result["runtime_published"] is False
assert result["service_started"] is False
config = pathlib.Path(result["config_path"])
manifest_path = pathlib.Path(result["manifest_path"])
manifest = json.loads(manifest_path.read_text())
data = config.read_bytes()
assert manifest["source"] == {"type":"profile","profile_id":"profile-test","profile_revision":"r000001"}
assert manifest["candidate"]["sha256"] == hashlib.sha256(data).hexdigest()
assert manifest["validation"]["json"] == "pass"
assert manifest["validation"]["xray_native"] == "pass"
assert stat.S_IMODE(config.stat().st_mode) == 0o600
assert stat.S_IMODE(manifest_path.stat().st_mode) == 0o600
assert stat.S_IMODE(config.parent.stat().st_mode) == 0o700
assert stat.S_IMODE(store.stat().st_mode) == 0o700
PY

if run_stage >"$TMP/duplicate.out" 2>&1; then
	echo "ERROR: se sobrescribió una revisión ya almacenada." >&2
	exit 1
fi
grep -q 'ya existe un candidato' "$TMP/duplicate.out"

# JSON malformado se rechaza antes de ejecutar Xray.
printf '{invalid\n' >"$CANDIDATE"
if python3 "$ROOT/scripts/xray_runtime_candidates.py" stage --candidate "$CANDIDATE" \
	--xray-binary "$BIN" --store "$STORE" --profile-id profile-test --profile-revision r000002 \
	>"$TMP/invalid-json.out" 2>&1; then
	echo "ERROR: se aceptó JSON inválido." >&2
	exit 1
fi
grep -q 'JSON válido' "$TMP/invalid-json.out"

# Un JSON válido rechazado por Xray no se almacena.
printf '{"inbounds":[],"outbounds":[],"reject":true}\n' >"$CANDIDATE"
if python3 "$ROOT/scripts/xray_runtime_candidates.py" stage --candidate "$CANDIDATE" \
	--xray-binary "$BIN" --store "$STORE" --profile-id profile-test --profile-revision r000003 \
	>"$TMP/xray-reject.out" 2>&1; then
	echo "ERROR: se almacenó una configuración rechazada por Xray." >&2
	exit 1
fi
grep -q 'Xray rechazó el candidato' "$TMP/xray-reject.out"
[[ ! -e "$STORE/profile-test/r000003" ]]

# El candidato simbólico y el hardlink se rechazan.
ln -s "$CANDIDATE" "$TMP/candidate-link.json"
if python3 "$ROOT/scripts/xray_runtime_candidates.py" stage --candidate "$TMP/candidate-link.json" \
	--xray-binary "$BIN" --store "$STORE" --profile-id profile-test --profile-revision r000004 \
	>"$TMP/symlink.out" 2>&1; then
	echo "ERROR: se aceptó un candidato simbólico." >&2
	exit 1
fi
grep -q 'componente simbólico' "$TMP/symlink.out"

ln "$CANDIDATE" "$TMP/candidate-hardlink.json"
if python3 "$ROOT/scripts/xray_runtime_candidates.py" stage --candidate "$TMP/candidate-hardlink.json" \
	--xray-binary "$BIN" --store "$STORE" --profile-id profile-test --profile-revision r000005 \
	>"$TMP/hardlink.out" 2>&1; then
	echo "ERROR: se aceptó un candidato con hardlink." >&2
	exit 1
fi
grep -q 'hardlinks' "$TMP/hardlink.out"

# Tokens de perfil y revisión no permiten traversal.
if python3 "$ROOT/scripts/xray_runtime_candidates.py" stage --candidate "$CANDIDATE" \
	--xray-binary "$BIN" --store "$STORE" --profile-id ../escape --profile-revision r1 \
	>"$TMP/traversal.out" 2>&1; then
	echo "ERROR: se aceptó traversal en el ID de perfil." >&2
	exit 1
fi
grep -q 'formato no permitido' "$TMP/traversal.out"

printf '%s\n' 'OK: staging privado de perfil, validación JSON/Xray, integridad, no sobrescritura y rechazo de rutas inseguras.'
