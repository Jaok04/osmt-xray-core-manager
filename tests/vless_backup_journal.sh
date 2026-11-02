#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
python3 - "$ROOT/scripts/vless_backup.py" "$TMP" <<'PY'
import importlib.util, pathlib, sys, types, json
script,tmp=sys.argv[1:]
spec=importlib.util.spec_from_file_location('vless_backup',script); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
root=pathlib.Path(tmp); backup=root/'backups'; base=root/'connections'; secrets=root/'secrets'
for p in (backup,base,secrets): p.mkdir(mode=0o700); p.chmod(0o700)
(base/'connections.json').write_text('ORIGINAL\n'); (base/'connections.json').chmod(0o600)
old_base=root/'.vless-connections-before-test'; base.rename(old_base)
base.mkdir(mode=0o700); (base/'connections.json').write_text('PARTIAL-NEW\n'); (base/'connections.json').chmod(0o600)
stage_base=root/'.vless-restore-connections.stage'; stage_base.mkdir(mode=0o700)
stage_secrets=root/'.vless-restore-secrets.stage'; stage_secrets.mkdir(mode=0o700)
old_secrets=root/'.vless-secrets-before-test'
record={'format':'xray-manager-restore-journal','backup_id':'test-backup','stage_connections':str(stage_base),'stage_secrets':str(stage_secrets),'live_connections':str(base),'live_secrets':str(secrets),'old_connections':str(old_base),'old_secrets':str(old_secrets),'phase':'connections_published'}
mod.atomic_file(backup/'RESTORE_IN_PROGRESS.json',(json.dumps(record)+'\n').encode())
mod.LIFECYCLE=root/'lifecycle.lock'; mod.INTEGRITY=root/'integrity.lock'
result=mod.recover_interrupted_restore(types.SimpleNamespace(backups=str(backup),base=str(base),secrets_dir=str(secrets)))
assert result['status']=='rolled_back'
assert (base/'connections.json').read_text()=='ORIGINAL\n'
assert not (backup/'RESTORE_IN_PROGRESS.json').exists()
assert list(root.glob('.vless-connections-interrupted-*'))
assert list(root.glob('.vless-connections-stage-interrupted-*'))
assert secrets.is_dir(), 'el directorio de secretos original que aún no se había renombrado debe conservarse'

# Compatibilidad con un journal antiguo sin had_connections/had_secrets cuando
# ninguno de los dos directorios existía antes y la interrupción fue temprana.
legacy_root=root/'legacy-absent'; legacy_root.mkdir(mode=0o700)
legacy_backup=legacy_root/'backups'; legacy_backup.mkdir(mode=0o700)
legacy_base=legacy_root/'connections'; legacy_secrets=legacy_root/'secrets'
legacy_stage_base=legacy_root/'.vless-restore-connections.legacy'
legacy_stage_secrets=legacy_root/'.vless-restore-secrets.legacy'
legacy_stage_base.mkdir(mode=0o700); legacy_stage_secrets.mkdir(mode=0o700)
legacy_old_base=legacy_root/'.vless-connections-before-legacy'
legacy_old_secrets=legacy_root/'.vless-secrets-before-legacy'
legacy_record={'format':'xray-manager-restore-journal','backup_id':'legacy-backup','stage_connections':str(legacy_stage_base),'stage_secrets':str(legacy_stage_secrets),'live_connections':str(legacy_base),'live_secrets':str(legacy_secrets),'old_connections':str(legacy_old_base),'old_secrets':str(legacy_old_secrets),'phase':'connections_saved'}
mod.atomic_file(legacy_backup/'RESTORE_IN_PROGRESS.json',(json.dumps(legacy_record)+'\n').encode())
mod.LIFECYCLE=legacy_root/'lifecycle.lock'; mod.INTEGRITY=legacy_root/'integrity.lock'
legacy_result=mod.recover_interrupted_restore(types.SimpleNamespace(backups=str(legacy_backup),base=str(legacy_base),secrets_dir=str(legacy_secrets)))
assert legacy_result['status']=='rolled_back'
assert not legacy_base.exists() and not legacy_secrets.exists()
assert not (legacy_backup/'RESTORE_IN_PROGRESS.json').exists()
assert list(legacy_root.glob('.vless-connections-stage-interrupted-*'))
print('PASS: journal legacy/nuevo, rollback conservador, destino originalmente ausente y cuarentena preservada')
PY
