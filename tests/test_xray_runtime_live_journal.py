#!/usr/bin/env python3
"""Pruebas aisladas del journal live mínimo; no usan /var/lib ni systemd."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

import xray_runtime_live_journal as journal

PROFILE = 'profile-' + 'a' * 32
REVISION = 'r000001'
VALIDATION = 'pvalidation-' + 'b' * 32
HASH = hashlib.sha256(b'fixture').hexdigest()
SYSTEMD = {'unit': 'xray.service', 'active_state': 'inactive', 'sub_state': 'dead', 'read_only': True}


class LiveJournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / 'runtime-operations'
        self.store = journal.LiveOperationStore(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def create(self, previous=b'previous-config'):
        return self.store.create(
            profile_id=PROFILE, revision=REVISION, validation_id=VALIDATION,
            profile_sha256=HASH, staged_sha256=HASH, binary_sha256=HASH,
            initial_systemd=SYSTEMD, previous_config=previous,
        )

    def test_create_load_and_exact_snapshot(self):
        record = self.create()
        self.assertEqual(record['environment'], 'live')
        self.assertEqual(record['state'], 'prepared')
        self.assertEqual(self.store.load(record['operation_id']), record)
        self.assertEqual(self.store.read_snapshot(record['operation_id']), b'previous-config')
        op = self.root / record['operation_id']
        self.assertEqual(os.stat(self.root).st_mode & 0o777, 0o700)
        self.assertEqual(os.stat(op).st_mode & 0o777, 0o700)
        self.assertEqual(os.stat(op / 'journal.json').st_mode & 0o777, 0o600)

    def test_no_previous_config_is_explicit(self):
        record = self.create(previous=None)
        self.assertEqual(record['snapshot'], {'present': False})
        self.assertIsNone(self.store.read_snapshot(record['operation_id']))

    def test_invalid_identity_rejected(self):
        with self.assertRaises(journal.LiveJournalError):
            self.store.create(profile_id='../../etc', revision=REVISION, validation_id=VALIDATION,
                              profile_sha256=HASH, staged_sha256=HASH, binary_sha256=HASH,
                              initial_systemd=SYSTEMD, previous_config=None)

    def test_invalid_hash_rejected(self):
        with self.assertRaises(journal.LiveJournalError):
            self.store.create(profile_id=PROFILE, revision=REVISION, validation_id=VALIDATION,
                              profile_sha256='bad', staged_sha256=HASH, binary_sha256=HASH,
                              initial_systemd=SYSTEMD, previous_config=None)

    def test_state_transition_requires_expected_state(self):
        record = self.create()
        op = record['operation_id']
        with self.assertRaises(journal.LiveJournalError):
            self.store.transition(op, expected_state='validated', new_state='snapshot_saved')

    def test_state_transition_is_monotonic(self):
        record = self.create()
        op = record['operation_id']
        updated = self.store.transition(op, expected_state='prepared', new_state='validated')
        self.assertEqual(updated['state'], 'validated')
        with self.assertRaises(journal.LiveJournalError):
            self.store.transition(op, expected_state='validated', new_state='prepared')

    def test_completed_requires_configuration_attestation(self):
        record = self.create()
        op = record['operation_id']
        record = self.store.transition(op, expected_state='prepared', new_state='validated')
        for old, new in [('validated', 'snapshot_saved'), ('snapshot_saved', 'publication_requested'),
                         ('publication_requested', 'config_published'), ('config_published', 'service_action_requested'),
                         ('service_action_requested', 'service_action_accepted'), ('service_action_accepted', 'service_observed_active')]:
            record = self.store.transition(op, expected_state=old, new_state=new)
        with self.assertRaises(journal.LiveJournalError):
            self.store.transition(op, expected_state='service_observed_active', new_state='configuration_attested')

    def test_attested_operation_can_complete(self):
        record = self.create()
        op = record['operation_id']
        states = ['validated', 'snapshot_saved', 'publication_requested', 'config_published',
                  'service_action_requested', 'service_action_accepted', 'service_observed_active']
        old = 'prepared'
        for new in states:
            self.store.transition(op, expected_state=old, new_state=new)
            old = new
        self.store.transition(op, expected_state=old, new_state='configuration_attested',
                              updates={'configuration_evidence': 'attested'})
        done = self.store.transition(op, expected_state='configuration_attested', new_state='completed')
        self.assertEqual(done['state'], 'completed')

    def test_first_install_can_complete_after_attestation(self):
        record = self.create(previous=None)
        op = record['operation_id']
        states = ['validated', 'snapshot_saved', 'publication_requested', 'config_published',
                  'service_action_requested', 'service_action_accepted', 'service_observed_active']
        old = 'prepared'
        for new in states:
            self.store.transition(op, expected_state=old, new_state=new)
            old = new
        self.store.transition(op, expected_state=old, new_state='configuration_attested',
                              updates={'configuration_evidence': 'attested'})
        done = self.store.transition(op, expected_state='configuration_attested', new_state='completed')
        self.assertEqual(done['state'], 'completed')

    def test_rollback_completion_requires_config_and_service_resolution(self):
        record = self.create()
        op = record['operation_id']
        for old, new in [('prepared', 'validated'), ('validated', 'snapshot_saved'),
                         ('snapshot_saved', 'publication_requested'), ('publication_requested', 'config_published'),
                         ('config_published', 'rollback_started'), ('rollback_started', 'rollback_config_restored')]:
            self.store.transition(op, expected_state=old, new_state=new,
                                  updates={'rollback': {'config_status': 'restored', 'service_status': 'not_started'}}
                                  if new == 'rollback_config_restored' else None)
        with self.assertRaises(journal.LiveJournalError):
            self.store.transition(op, expected_state='rollback_config_restored', new_state='rolled_back')
        done = self.store.transition(op, expected_state='rollback_config_restored', new_state='rolled_back',
                                     updates={'rollback': {'config_status': 'restored', 'service_status': 'not_required'}})
        self.assertEqual(done['state'], 'rolled_back')

    def test_no_prior_config_cannot_be_declared_rolled_back(self):
        record = self.create(previous=None)
        op = record['operation_id']
        self.store.transition(op, expected_state='prepared', new_state='validated')
        self.store.transition(op, expected_state='validated', new_state='snapshot_saved')
        self.store.transition(op, expected_state='snapshot_saved', new_state='publication_requested')
        self.store.transition(op, expected_state='publication_requested', new_state='config_published')
        self.store.transition(op, expected_state='config_published', new_state='rollback_started')
        with self.assertRaises(journal.LiveJournalError):
            self.store.transition(op, expected_state='rollback_started', new_state='rollback_config_restored')

    def test_snapshot_tampering_detected(self):
        record = self.create()
        path = self.root / record['operation_id'] / 'snapshot' / 'config.json'
        path.write_bytes(b'altered')
        os.chmod(path, 0o600)
        with self.assertRaises(journal.LiveJournalError):
            self.store.read_snapshot(record['operation_id'])

    def test_symlink_journal_rejected(self):
        record = self.create()
        path = self.root / record['operation_id'] / 'journal.json'
        path.unlink()
        path.symlink_to('/etc/passwd')
        with self.assertRaises(journal.LiveJournalError):
            self.store.load(record['operation_id'])

    def test_unknown_journal_fields_rejected(self):
        record = self.create()
        path = self.root / record['operation_id'] / 'journal.json'
        value = json.loads(path.read_text())
        value['extra'] = True
        path.write_text(json.dumps(value))
        os.chmod(path, 0o600)
        with self.assertRaises(journal.LiveJournalError):
            self.store.load(record['operation_id'])

    def test_fixture_environment_rejected(self):
        record = self.create()
        path = self.root / record['operation_id'] / 'journal.json'
        value = json.loads(path.read_text())
        value['environment'] = 'fixture'
        path.write_text(json.dumps(value))
        os.chmod(path, 0o600)
        with self.assertRaises(journal.LiveJournalError):
            self.store.load(record['operation_id'])

    def test_snapshot_metadata_must_match_presence(self):
        record = self.create(previous=None)
        path = self.root / record['operation_id'] / 'journal.json'
        value = json.loads(path.read_text())
        value['snapshot'] = {'present': True, 'sha256': HASH, 'size_bytes': 7, 'uid': 0, 'gid': 0, 'mode': 0o600}
        path.write_text(json.dumps(value))
        os.chmod(path, 0o600)
        with self.assertRaises(journal.LiveJournalError):
            self.store.load(record['operation_id'])


if __name__ == '__main__':
    unittest.main()
