#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
python3 - "$ROOT/scripts/vless_backup.py" "$TMP" <<'PY'
import builtins, importlib.util, json, multiprocessing, os, pathlib, shutil, sys, types
script, tmp = sys.argv[1:]
spec = importlib.util.spec_from_file_location('vless_backup', script)
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
root = pathlib.Path(tmp)
source_base = root/'source-connections'; source_secrets = root/'source-secrets'; source_backups = root/'source-backups'
for path in (source_base, source_secrets, source_backups): path.mkdir(mode=0o700); path.chmod(0o700)
(source_base/'connections.json').write_text('[]\n'); (source_base/'connections.json').chmod(0o600)
mod.LIFECYCLE = root/'source-lifecycle.lock'; mod.INTEGRITY = root/'source-integrity.lock'
backup = mod.create_data(types.SimpleNamespace(base=str(source_base), secrets_dir=str(source_secrets), backups=str(source_backups)))
source_snapshot = pathlib.Path(backup['path'])

class TTY:
    def isatty(self): return True

def crash_restore(case_base, case_secrets, case_backups, snapshot, lock_root, event):
    sys.stdin = TTY(); builtins.input = lambda prompt='': 'RESTAURAR'
    mod.LIFECYCLE = lock_root/'lifecycle.lock'; mod.INTEGRITY = lock_root/'integrity.lock'
    original_atomic = mod.atomic_file
    original_replace = os.replace
    def atomic(path, data, mode=0o600):
        original_atomic(path, data, mode)
        if pathlib.Path(path).name == 'RESTORE_IN_PROGRESS.json':
            phase = json.loads(data.decode())['phase']
            if event == 'phase:' + phase: os._exit(88)
    def replace(src, dst):
        original_replace(src, dst)
        srcp, dstp = pathlib.Path(src), pathlib.Path(dst)
        hit = ((event == 'rename:connections' and srcp == case_base and dstp.name.startswith('.vless-connections-before-')) or
               (event == 'rename:secrets' and srcp == case_secrets and dstp.name.startswith('.vless-secrets-before-')) or
               (event == 'publish:connections' and srcp.name.startswith('.vless-restore-connections.') and dstp == case_base) or
               (event == 'publish:secrets' and srcp.name.startswith('.vless-restore-secrets.') and dstp == case_secrets))
        if hit: os._exit(88)
    mod.atomic_file = atomic; os.replace = replace
    args = types.SimpleNamespace(base=str(case_base), secrets_dir=str(case_secrets), master_key=str(lock_root/'missing-master.key'), backups=str(case_backups), backup_dir=str(snapshot))
    mod.restore_data(args)

events = ['phase:prepared', 'phase:connections_saved', 'phase:old_data_saved',
          'publish:connections', 'phase:connections_published', 'publish:secrets', 'phase:published']
ctx = multiprocessing.get_context('fork')
count = 0
for had_connections in (False, True):
  for had_secrets in (False, True):
    scenario = f'c{int(had_connections)}s{int(had_secrets)}'
    scenario_events = list(events)
    if had_connections: scenario_events.append('rename:connections')
    if had_secrets: scenario_events.append('rename:secrets')
    for event in scenario_events:
      case = root/f'{scenario}-{event.replace(":", "_")}'
      case.mkdir(mode=0o700)
      case_base = case/'connections'; case_secrets = case/'secrets'; case_backups = case/'backups'
      case_backups.mkdir(mode=0o700)
      if had_connections:
        case_base.mkdir(mode=0o700)
        original_catalog='[{"id":"original-vmess","name":"Original VMess","protocol_id":"vmess_ws","port":62000,"max_users":1,"state":"draft","runtime_applied":false}]\n'
        (case_base/'connections.json').write_text(original_catalog); (case_base/'connections.json').chmod(0o600)
      if had_secrets:
        case_secrets.mkdir(mode=0o700); (case_secrets/'original.bin').write_text('ORIGINAL-SECRETS\n'); (case_secrets/'original.bin').chmod(0o600)
      snapshot = case_backups/'snapshot'; shutil.copytree(source_snapshot, snapshot)
      for p in snapshot.rglob('*'):
        if p.is_dir(): p.chmod(0o700)
        else: p.chmod(0o600)
      snapshot.chmod(0o700)
      proc = ctx.Process(target=crash_restore, args=(case_base, case_secrets, case_backups, snapshot, case, event))
      proc.start(); proc.join(20)
      if proc.is_alive(): proc.kill(); proc.join(); raise AssertionError(f'timeout: {scenario} {event}')
      if proc.exitcode != 88: raise AssertionError(f'crash hook no alcanzado: {scenario} {event}, exit={proc.exitcode}')
      mod.LIFECYCLE = case/'recover-lifecycle.lock'; mod.INTEGRITY = case/'recover-integrity.lock'
      result = mod.recover_interrupted_restore(types.SimpleNamespace(backups=str(case_backups), base=str(case_base), secrets_dir=str(case_secrets)))
      assert result['status'] == 'rolled_back', (scenario, event, result)
      assert not (case_backups/'RESTORE_IN_PROGRESS.json').exists(), (scenario, event, 'journal persistente')
      if had_connections:
        assert case_base.is_dir() and (case_base/'connections.json').read_text() == original_catalog, (scenario, event, 'catálogo original no restaurado')
      else:
        assert not case_base.exists(), (scenario, event, 'directorio nuevo no fue retirado a cuarentena')
      if had_secrets:
        assert case_secrets.is_dir() and (case_secrets/'original.bin').read_text() == 'ORIGINAL-SECRETS\n', (scenario, event, 'secretos originales no restaurados')
      else:
        assert not case_secrets.exists(), (scenario, event, 'directorio nuevo de secretos no fue retirado a cuarentena')
      count += 1
print(f'PASS: {count} interrupciones abruptas recuperadas; fases del journal, renombrados, publicación y 4 combinaciones de existencia previa')
PY
