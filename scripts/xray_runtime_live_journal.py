#!/usr/bin/env python3
"""Journal live mínimo, separado del journal R-05 fixture.

Este módulo sólo persiste/reconcilia metadatos en el almacén live. No publica
configuración, no consulta systemd y no ejecuta acciones de servicio. La ruta
productiva es fija; las pruebas inyectan un directorio temporal.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LIVE_ROOT = Path('/var/lib/xray-manager/runtime-operations')
OP_RE = re.compile(r'runtime-op-[0-9a-f]{32}\Z')
PROFILE_RE = re.compile(r'profile-[0-9a-f]{32}\Z')
REVISION_RE = re.compile(r'r[0-9]{6}\Z')
HASH_RE = re.compile(r'[0-9a-f]{64}\Z')
MAX_JOURNAL = 1024 * 1024
MAX_SNAPSHOT = 16 * 1024 * 1024

class LiveJournalError(Exception):
    pass


def _fail(message: str) -> None:
    raise LiveJournalError(message)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def _strict_json(data: bytes) -> dict[str, Any]:
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError('duplicate')
            out[key] = value
        return out
    try:
        value = json.loads(data.decode('utf-8'), object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError('constant')))
    except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise LiveJournalError('journal JSON inválido o no estricto.') from exc
    if not isinstance(value, dict):
        _fail('journal debe ser un objeto JSON.')
    return value


def _check_components(path: Path, *, allow_missing: bool = False) -> None:
    if not path.is_absolute():
        _fail('La ruta del almacén debe ser absoluta.')
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            if allow_missing:
                continue
            _fail('Falta un componente del almacén live.')
        except OSError as exc:
            raise LiveJournalError('No se pudo inspeccionar el almacén live.') from exc
        if stat.S_ISLNK(info.st_mode):
            _fail('El almacén live contiene un componente symlink.')


def _check_dir(path: Path, mode: int) -> None:
    _check_components(path)
    if path != Path(path.anchor):
        parent = path.parent
        _check_components(parent)
        pst = parent.lstat()
        if (not stat.S_ISDIR(pst.st_mode) or pst.st_uid != 0 or pst.st_gid != 0
                or stat.S_IMODE(pst.st_mode) & 0o022):
            _fail('El directorio padre debe ser root:root y no modificable por grupo/otros.')
    st = path.lstat()
    if (not stat.S_ISDIR(st.st_mode) or st.st_uid != 0 or st.st_gid != 0
            or stat.S_IMODE(st.st_mode) != mode):
        _fail(f'Directorio live inseguro: se requiere root:root {mode:04o}.')


def _read_regular(path: Path, limit: int, mode: int) -> bytes:
    _check_components(path)
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_CLOEXEC', 0) | getattr(os, 'O_NONBLOCK', 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise LiveJournalError('No se pudo abrir un artefacto live.') from exc
    try:
        st = os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_gid != 0
                or st.st_nlink != 1 or stat.S_IMODE(st.st_mode) != mode
                or st.st_size < 1 or st.st_size > limit):
            _fail('Artefacto live con tipo, propietario, permisos o tamaño inseguros.')
        chunks, total = [], 0
        while True:
            part = os.read(fd, min(65536, limit + 1 - total))
            if not part:
                break
            chunks.append(part)
            total += len(part)
            if total > limit:
                _fail('Artefacto live excede el tamaño permitido.')
        data = b''.join(chunks)
        if len(data) != st.st_size:
            _fail('Artefacto live cambió durante su lectura.')
        return data
    finally:
        os.close(fd)


def _atomic_write(directory: Path, name: str, data: bytes, mode: int) -> None:
    _check_dir(directory, 0o700)
    if '/' in name or name in {'', '.', '..'}:
        _fail('Nombre de artefacto inválido.')
    fd, temp_name = tempfile.mkstemp(prefix='.journal-', dir=directory)
    temp = Path(temp_name)
    try:
        os.fchown(fd, 0, 0)
        os.fchmod(fd, mode)
        with os.fdopen(fd, 'wb', closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(fd)
        target = directory / name
        if target.exists() or target.is_symlink():
            st = target.lstat()
            if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_gid != 0 or stat.S_IMODE(st.st_mode) != mode or st.st_nlink != 1:
                _fail('El destino existente del journal es inseguro.')
        os.replace(temp, target)
        dfd = os.open(directory, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0) | getattr(os, 'O_NOFOLLOW', 0))
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
        _read_regular(target, MAX_JOURNAL if name == 'journal.json' else MAX_SNAPSHOT, mode)
    except Exception:
        try:
            temp.unlink()
        except OSError:
            pass
        raise
    finally:
        try:
            os.close(fd)
        except OSError:
            pass


class LiveOperationStore:
    """API interna. En producción usar LIVE_ROOT; root alternativo sólo tests."""
    def __init__(self, root: Path = LIVE_ROOT):
        self.root = Path(root)

    def initialize(self) -> None:
        _check_components(self.root, allow_missing=True)
        if not self.root.exists():
            parent = self.root.parent
            _check_components(parent)
            parent_info = parent.lstat()
            if (not stat.S_ISDIR(parent_info.st_mode) or parent_info.st_uid != 0
                    or parent_info.st_gid != 0 or stat.S_IMODE(parent_info.st_mode) & 0o022):
                _fail('El padre del almacén live debe ser root:root y no modificable por grupo/otros.')
            os.mkdir(self.root, 0o700)
            os.chown(self.root, 0, 0)
            os.chmod(self.root, 0o700)
            pfd = os.open(parent, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
            try:
                os.fsync(pfd)
            finally:
                os.close(pfd)
        _check_dir(self.root, 0o700)

    def create(self, *, profile_id: str, revision: str, validation_id: str,
               profile_sha256: str, staged_sha256: str, binary_sha256: str,
               initial_systemd: dict[str, Any], previous_config: bytes | None) -> dict[str, Any]:
        self.initialize()
        if not isinstance(profile_id, str) or not PROFILE_RE.fullmatch(profile_id):
            _fail('profile_id inválido.')
        if not isinstance(revision, str) or not REVISION_RE.fullmatch(revision):
            _fail('revision inválida.')
        for value in (profile_sha256, staged_sha256, binary_sha256):
            if not isinstance(value, str) or not HASH_RE.fullmatch(value):
                _fail('Hash de operación inválido.')
        if not isinstance(validation_id, str) or not re.fullmatch(r'pvalidation-[0-9a-f]{32}', validation_id):
            _fail('validation_id inválido.')
        if not isinstance(initial_systemd, dict):
            _fail('La observación inicial systemd debe ser un objeto.')
        if previous_config is not None and (not isinstance(previous_config, bytes) or not 1 <= len(previous_config) <= MAX_SNAPSHOT):
            _fail('Snapshot previo inválido o fuera de límite.')
        operation_id = 'runtime-op-' + secrets.token_hex(16)
        operation_dir = self.root / operation_id
        os.mkdir(operation_dir, 0o700)
        os.chown(operation_dir, 0, 0)
        os.chmod(operation_dir, 0o700)
        sfd = os.open(operation_dir, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
        try:
            os.fsync(sfd)
        finally:
            os.close(sfd)
        snapshot_dir = operation_dir / 'snapshot'
        os.mkdir(snapshot_dir, 0o700)
        os.chown(snapshot_dir, 0, 0)
        os.chmod(snapshot_dir, 0o700)
        has_previous = previous_config is not None
        snapshot_meta = {'present': has_previous}
        if has_previous:
            _atomic_write(snapshot_dir, 'config.json', previous_config, 0o600)
            snapshot_meta.update({'sha256': hashlib.sha256(previous_config).hexdigest(), 'size_bytes': len(previous_config),
                                  'uid': 0, 'gid': 0, 'mode': 0o600})
        journal = {
            'schema_version': 1, 'environment': 'live', 'operation_id': operation_id,
            'created_at': _now(), 'updated_at': _now(), 'state': 'prepared',
            'profile_id': profile_id, 'revision': revision, 'validation_id': validation_id,
            'profile_sha256': profile_sha256, 'staged_config_sha256': staged_sha256,
            'binary_sha256': binary_sha256, 'unit': 'xray.service',
            'config_path': '/etc/xray/config.json', 'initial_systemd': initial_systemd,
            'snapshot': snapshot_meta,
            'publication': {'status': 'not_requested'},
            'service_action': {'status': 'not_requested'},
            'post_systemd': None,
            'configuration_evidence': 'not_attested',
            'rollback': {'config_status': 'not_started', 'service_status': 'not_started'},
            'recovery': {'attempts': 0, 'decision': 'none', 'error_code': None},
        }
        self._write(operation_id, journal, create_only=True)
        rootfd = os.open(self.root, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
        try:
            os.fsync(rootfd)
        finally:
            os.close(rootfd)
        return journal

    def _operation_dir(self, operation_id: str) -> Path:
        if not isinstance(operation_id, str) or not OP_RE.fullmatch(operation_id):
            _fail('operation_id inválido.')
        _check_dir(self.root, 0o700)
        path = self.root / operation_id
        _check_dir(path, 0o700)
        return path

    def _write(self, operation_id: str, journal: dict[str, Any], *, create_only: bool = False) -> None:
        directory = self._operation_dir(operation_id)
        if journal.get('operation_id') != operation_id or journal.get('environment') != 'live' or journal.get('schema_version') != 1:
            _fail('Identidad del journal live discordante.')
        data = (json.dumps(journal, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n').encode()
        if len(data) > MAX_JOURNAL:
            _fail('Journal live excede el tamaño permitido.')
        target = directory / 'journal.json'
        if create_only and (target.exists() or target.is_symlink()):
            _fail('La operación ya contiene journal; no se reemplaza al crear.')
        _atomic_write(directory, 'journal.json', data, 0o600)

    def load(self, operation_id: str) -> dict[str, Any]:
        directory = self._operation_dir(operation_id)
        value = _strict_json(_read_regular(directory / 'journal.json', MAX_JOURNAL, 0o600))
        required = {'schema_version', 'environment', 'operation_id', 'created_at', 'updated_at', 'state',
                    'profile_id', 'revision', 'validation_id', 'profile_sha256', 'staged_config_sha256',
                    'binary_sha256', 'unit', 'config_path', 'initial_systemd', 'snapshot', 'publication',
                    'service_action', 'post_systemd', 'configuration_evidence', 'rollback', 'recovery'}
        if set(value) != required or value.get('schema_version') != 1 or value.get('environment') != 'live' or value.get('operation_id') != operation_id:
            _fail('Esquema o identidad del journal live inválido.')
        if value.get('unit') != 'xray.service' or value.get('config_path') != '/etc/xray/config.json':
            _fail('Destino del journal live no permitido.')
        if value.get('configuration_evidence') not in {'not_attested', 'pending', 'attested', 'contradicted'}:
            _fail('Estado de evidencia de configuración inválido.')
        if value.get('state') not in {
            'prepared', 'validated', 'snapshot_saved', 'publication_requested', 'config_published',
            'published_pending_start', 'service_action_requested', 'service_action_accepted',
            'service_observed_active', 'configuration_attested', 'completed', 'rollback_started',
            'rollback_config_restored', 'rollback_service_restored', 'rolled_back', 'recovery_required'
        }:
            _fail('Estado del journal live desconocido.')
        for key in ('profile_sha256', 'staged_config_sha256', 'binary_sha256'):
            if not isinstance(value.get(key), str) or not HASH_RE.fullmatch(value[key]):
                _fail('Hash del journal live inválido.')
        if (not isinstance(value.get('profile_id'), str) or not PROFILE_RE.fullmatch(value['profile_id'])
                or not isinstance(value.get('revision'), str) or not REVISION_RE.fullmatch(value['revision'])
                or not isinstance(value.get('validation_id'), str)
                or not re.fullmatch(r'pvalidation-[0-9a-f]{32}', value['validation_id'])):
            _fail('Identidad perfil/revisión/validación del journal inválida.')
        snapshot = value.get('snapshot')
        if not isinstance(snapshot, dict) or type(snapshot.get('present')) is not bool:
            _fail('Metadatos de snapshot inválidos.')
        if snapshot['present']:
            if (set(snapshot) != {'present', 'sha256', 'size_bytes', 'uid', 'gid', 'mode'}
                    or not isinstance(snapshot.get('sha256'), str) or not HASH_RE.fullmatch(snapshot['sha256'])
                    or type(snapshot.get('size_bytes')) is not int
                    or not 1 <= snapshot['size_bytes'] <= MAX_SNAPSHOT
                    or snapshot.get('uid') != 0 or snapshot.get('gid') != 0
                    or snapshot.get('mode') != 0o600):
                _fail('Metadatos de snapshot previo inválidos.')
        elif set(snapshot) != {'present'}:
            _fail('Snapshot ausente no puede contener metadatos adicionales.')
        for key in ('initial_systemd', 'publication', 'service_action', 'rollback', 'recovery'):
            if not isinstance(value.get(key), dict):
                _fail(f'Campo {key} del journal live debe ser objeto.')
        if value['state'] in {'configuration_attested', 'completed'} and value['configuration_evidence'] != 'attested':
            _fail('Estado final contradice la evidencia de configuración.')
        snapshot_dir = directory / 'snapshot'
        _check_dir(snapshot_dir, 0o700)
        snapshot_file = snapshot_dir / 'config.json'
        if snapshot['present']:
            raw_snapshot = _read_regular(snapshot_file, MAX_SNAPSHOT, 0o600)
            if (hashlib.sha256(raw_snapshot).hexdigest() != snapshot['sha256']
                    or len(raw_snapshot) != snapshot['size_bytes']):
                _fail('Snapshot live no coincide con el hash/tamaño del journal.')
        elif snapshot_file.exists() or snapshot_file.is_symlink():
            _fail('Existe un snapshot no declarado por el journal live.')
        return value

    def transition(self, operation_id: str, *, expected_state: str, new_state: str,
                   updates: dict[str, Any] | None = None) -> dict[str, Any]:
        allowed = {
            'prepared': {'validated', 'recovery_required'},
            'validated': {'snapshot_saved', 'recovery_required'},
            'snapshot_saved': {'publication_requested', 'rollback_started', 'recovery_required'},
            'publication_requested': {'config_published', 'rollback_started', 'recovery_required'},
            'config_published': {'service_action_requested', 'published_pending_start', 'rollback_started', 'recovery_required'},
            'published_pending_start': {'service_action_requested', 'rollback_started', 'recovery_required'},
            'service_action_requested': {'service_action_accepted', 'rollback_started', 'recovery_required'},
            'service_action_accepted': {'service_observed_active', 'rollback_started', 'recovery_required'},
            'service_observed_active': {'configuration_attested', 'rollback_started', 'recovery_required'},
            'configuration_attested': {'completed', 'rollback_started', 'recovery_required'},
            'rollback_started': {'rollback_config_restored', 'recovery_required'},
            'rollback_config_restored': {'rollback_service_restored', 'rolled_back', 'recovery_required'},
            'rollback_service_restored': {'rolled_back', 'recovery_required'},
        }
        journal = self.load(operation_id)
        if journal['state'] != expected_state or new_state not in allowed.get(expected_state, set()):
            _fail('Transición de estado no permitida o estado esperado discordante.')
        if updates is not None:
            if not isinstance(updates, dict) or set(updates) - {'publication', 'service_action', 'post_systemd', 'configuration_evidence', 'rollback', 'recovery'}:
                _fail('Actualización contiene campos no permitidos.')
            for key, value in updates.items():
                if not isinstance(value, dict) and key not in {'post_systemd', 'configuration_evidence'}:
                    _fail('Actualización de journal inválida.')
                journal[key] = value
        if new_state == 'configuration_attested' and journal['configuration_evidence'] != 'attested':
            _fail('No se puede atestar configuración sin evidencia específica.')
        if new_state == 'completed' and journal['configuration_evidence'] != 'attested':
            _fail('No se puede completar sin atestación de configuración.')
        if new_state == 'rollback_config_restored' and not journal['snapshot'].get('present'):
            _fail('Sin configuración previa no se restaura ni elimina la configuración nueva; requiere recovery_required.')
        if new_state == 'rolled_back' and not journal['snapshot'].get('present'):
            _fail('No se puede declarar rollback sin configuración previa; requiere recovery_required.')
        if new_state == 'rolled_back' and journal['rollback'].get('config_status') != 'restored':
            _fail('Rollback no puede finalizar sin restauración verificada de configuración.')
        if new_state == 'rolled_back' and journal['rollback'].get('service_status') not in {'restored', 'not_required'}:
            _fail('Rollback no puede finalizar sin resolución verificada del estado del servicio.')
        journal['state'] = new_state
        journal['updated_at'] = _now()
        self._write(operation_id, journal)
        return journal

    def read_snapshot(self, operation_id: str) -> bytes | None:
        journal = self.load(operation_id)
        if not journal['snapshot'].get('present'):
            return None
        data = _read_regular(self._operation_dir(operation_id) / 'snapshot' / 'config.json', MAX_SNAPSHOT, 0o600)
        if hashlib.sha256(data).hexdigest() != journal['snapshot'].get('sha256') or len(data) != journal['snapshot'].get('size_bytes'):
            _fail('Snapshot live no coincide con el hash/tamaño del journal.')
        return data
