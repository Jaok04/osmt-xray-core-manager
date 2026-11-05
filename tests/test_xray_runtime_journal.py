from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import xray_runtime_journal as journal


class RuntimeJournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = pathlib.Path(self.tmp.name)
        self.base.chmod(0o755)
        r02_marker = self.base / ".xray-manager-r02-fixture"
        r02_marker.write_text(json.dumps({
            "schema_version": 1, "purpose": "xray-runtime-r02-isolated-fixture"
        }, sort_keys=True, separators=(",", ":")) + "\n")
        r02_marker.chmod(0o600)
        self.service_uid = 65534
        self.service_gid = 65534
        self.binary = self.base / "xray-fixture"
        self.binary.write_text("#!/bin/sh\nexit 0\n")
        self.binary.chmod(0o755)
        self.binary_hash = hashlib.sha256(self.binary.read_bytes()).hexdigest()

        self.service_root = self.base / "service-root"
        self.service_root.mkdir(mode=0o711)
        marker = self.service_root / ".xray-manager-fixture"
        marker.write_text(json.dumps({
            "schema_version": 1, "purpose": "xray-runtime-isolated-fixture"
        }))
        marker.chmod(0o600)
        etc = self.service_root / "etc"
        etc.mkdir(mode=0o755)
        xray_dir = etc / "xray"
        xray_dir.mkdir(mode=0o750)
        os.chown(xray_dir, 0, self.service_gid)
        self.previous_config = xray_dir / "config.json"
        self.previous_bytes = b'{"inbounds":[],"outbounds":[{"protocol":"freedom"}]}\n'
        self.write_service_config(self.previous_bytes)

        self.service_state = self.base / "service-state.json"
        self.write_service_fixture()

        self.staging_dir = self.base / "staging"
        self.staging_dir.mkdir(mode=0o750)
        os.chown(self.staging_dir, 0, self.service_gid)
        self.lease_root = self.base / "leases"
        self.lease_root.mkdir(mode=0o750)
        os.chown(self.lease_root, 0, self.service_gid)
        lease_marker = self.lease_root / ".xray-manager-r02-leases-fixture"
        lease_marker.write_text(json.dumps({
            "schema_version": 1, "purpose": "xray-runtime-r02-isolated-leases"
        }, sort_keys=True, separators=(",", ":")) + "\n")
        os.chown(lease_marker, 0, self.service_gid)
        lease_marker.chmod(0o640)
        self.lease_id = "resolve-" + "b" * 32
        self.lease_dir = self.lease_root / self.lease_id
        self.lease_dir.mkdir(mode=0o750)
        os.chown(self.lease_dir, 0, self.service_gid)
        self.write_lease_file("certificate.pem", b"-----BEGIN CERTIFICATE-----\nsynthetic\n")
        self.write_lease_file("private-key.pem", b"-----BEGIN PRIVATE KEY-----\nsynthetic\n")
        self.lease_manifest = {
            "lease_id": self.lease_id,
            "connection_id": "vless-tls-01",
            "protocol": "vless",
            "certificate_id": "cert-synthetic",
            "certificate_revision": 1,
            "certificate_fingerprint_sha256": "f" * 64,
            "service_uid": self.service_uid,
            "service_gid": self.service_gid,
        }
        self.write_lease_file("manifest.json", journal.json_bytes(self.lease_manifest))

        self.staged_config = {
            "log": {"loglevel": "warning"},
            "inbounds": [{
                "tag": "tls-in",
                "streamSettings": {"security": "tls", "tlsSettings": {
                    "certificates": [{
                        "certificateFile": str(self.lease_dir / "certificate.pem"),
                        "keyFile": str(self.lease_dir / "private-key.pem"),
                    }]
                }},
            }],
            "outbounds": [{"protocol": "freedom", "tag": "direct"}],
        }
        self.staged_bytes = journal.json_bytes(self.staged_config)
        self.write_staging_file("config.json", self.staged_bytes)
        self.staging_manifest = {
            "schema_version": 1,
            "status": "STAGED",
            "fixture_root": str(self.base),
            "staging_dir": str(self.staging_dir),
            "lease_root": str(self.lease_root),
            "profile_id": "profile-" + "a" * 32,
            "revision": "r000001",
            "validation_id": "pvalidation-" + "c" * 32,
            "profile_content_sha256": "d" * 64,
            "bindings_sha256": "e" * 64,
            "bindings": [{"inbound_tag": "tls-in", "connection_id": "vless-tls-01"}],
            "leases": [{
                "lease_id": self.lease_id,
                "connection_id": "vless-tls-01",
                "protocol": "vless",
                "certificate_id": "cert-synthetic",
            }],
            "staged_config_sha256": hashlib.sha256(self.staged_bytes).hexdigest(),
            "staged_config_size_bytes": len(self.staged_bytes),
            "service_identity": {"uid": self.service_uid, "gid": self.service_gid},
            "xray_binary": {
                "path": str(self.binary), "sha256": self.binary_hash,
                "size_bytes": self.binary.stat().st_size,
            },
            "native_validation": "PASS",
            "runtime_published": False,
            "service_started": False,
        }
        self.write_staging_file("manifest.json", journal.json_bytes(self.staging_manifest))

        self.operation_store = self.base / "operations"
        self.operation_store.mkdir(mode=0o700)
        operation_marker = self.operation_store / ".xray-manager-r03-operations-fixture"
        operation_marker.write_text(json.dumps({
            "schema_version": 1, "purpose": "xray-runtime-r03-isolated-operations"
        }, sort_keys=True, separators=(",", ":")) + "\n")
        operation_marker.chmod(0o600)
        self.lock_dir = self.operation_store / "locks"
        self.lock_dir.mkdir(mode=0o700)
        self.lifecycle_lock = self.lock_dir / "lifecycle.lock"
        self.application_lock = self.lock_dir / "application.lock"

    def tearDown(self):
        self.tmp.cleanup()

    def write_service_config(self, data):
        self.previous_config.write_bytes(data)
        os.chown(self.previous_config, 0, self.service_gid)
        self.previous_config.chmod(0o640)

    def write_service_fixture(self, **changes):
        value = {
            "unit": "xray.service", "load_state": "loaded",
            "active_state": "active", "sub_state": "running",
            "user": "xray", "group": "xray", "binary_path": str(self.binary),
        }
        value.update(changes)
        self.service_state.write_text(json.dumps(value, sort_keys=True))
        self.service_state.chmod(0o600)

    def write_lease_file(self, name, data):
        path = self.lease_dir / name
        path.write_bytes(data)
        os.chown(path, 0, self.service_gid)
        path.chmod(0o640)

    def write_staging_file(self, name, data):
        path = self.staging_dir / name
        path.write_bytes(data)
        os.chown(path, 0, self.service_gid)
        path.chmod(0o640)

    def prepare(self, **changes):
        args = {
            "staging_dir": self.staging_dir,
            "service_root": self.service_root,
            "service_state": self.service_state,
            "operation_store": self.operation_store,
            "lifecycle_lock": self.lifecycle_lock,
            "application_lock": self.application_lock,
            "lease_root": self.lease_root,
            "service_uid": self.service_uid,
            "service_gid": self.service_gid,
        }
        args.update(changes)
        return journal.prepare_operation(**args)

    def recover(self):
        return journal.recover_store(
            self.operation_store, self.lifecycle_lock, self.application_lock
        )

    def test_snapshot_and_journal_capture_exact_profile_and_previous_runtime(self):
        result = self.prepare()
        self.assertEqual(result["status"], "SNAPSHOT_SAVED")
        self.assertEqual(result["previous_config"], "saved")
        self.assertEqual(result["previous_service_state"], "active")
        self.assertFalse(result["runtime_published"])
        self.assertFalse(result["service_action_performed"])
        op = pathlib.Path(result["operation_dir"])
        record = journal.read_journal(op)
        self.assertEqual(record["state"], "snapshot_saved")
        self.assertEqual(record["source"]["profile_id"], self.staging_manifest["profile_id"])
        self.assertEqual(record["source"]["revision"], "r000001")
        self.assertEqual(record["source"]["validation_id"], self.staging_manifest["validation_id"])
        snap = json.loads((op / "snapshot.json").read_text())
        self.assertEqual((op / "snapshot/config.json").read_bytes(), self.previous_bytes)
        self.assertEqual(snap["previous_config"]["sha256"], hashlib.sha256(self.previous_bytes).hexdigest())
        self.assertEqual(self.previous_config.read_bytes(), self.previous_bytes)

    def test_no_previous_config_is_explicit_and_never_creates_placeholder(self):
        self.previous_config.unlink()
        result = self.prepare()
        op = pathlib.Path(result["operation_dir"])
        snap = json.loads((op / "snapshot.json").read_text())
        self.assertEqual(result["previous_config"], "no_previous_config")
        self.assertTrue(snap["no_previous_config"])
        self.assertFalse((op / "snapshot/config.json").exists())
        self.assertFalse(self.previous_config.exists())

    def test_second_nonterminal_operation_is_blocked(self):
        first = self.prepare()
        with self.assertRaises(journal.RuntimeJournalError):
            self.prepare()
        operations = list((self.operation_store / "operations").iterdir())
        self.assertEqual(len(operations), 1)
        self.assertEqual(journal.read_journal(operations[0])["operation_id"], first["operation_id"])

    def test_inspect_is_read_only(self):
        result = self.prepare()
        before = (pathlib.Path(result["operation_dir"]) / "journal.json").read_bytes()
        inspected = journal.inspect_operation(self.operation_store, result["operation_id"])
        after = (pathlib.Path(result["operation_dir"]) / "journal.json").read_bytes()
        self.assertEqual(inspected["state"], "snapshot_saved")
        self.assertEqual(before, after)

    def test_recovery_crash_matrix_is_idempotent(self):
        for point, expected in (
            ("after_prepared", "aborted"),
            ("after_snapshot_dir", "aborted"),
            ("after_validated", "aborted"),
            ("after_snapshot_config", "aborted"),
            ("after_snapshot_metadata", "snapshot_saved"),
            ("after_snapshot_saved", "snapshot_saved"),
        ):
            with self.subTest(point=point):
                self.operation_store = self.base / ("operations-" + point)
                self.operation_store.mkdir(mode=0o700)
                marker = self.operation_store / ".xray-manager-r03-operations-fixture"
                marker.write_text(json.dumps({
                    "schema_version": 1, "purpose": "xray-runtime-r03-isolated-operations"
                }, sort_keys=True, separators=(",", ":")) + "\n")
                marker.chmod(0o600)
                self.lock_dir = self.operation_store / "locks"
                self.lock_dir.mkdir(mode=0o700)
                self.lifecycle_lock = self.lock_dir / "lifecycle.lock"
                self.application_lock = self.lock_dir / "application.lock"
                with self.assertRaises(journal.SimulatedCrash):
                    self.prepare(crash_at=point)
                first = self.recover()
                state = first["operations"][0]["state"]
                self.assertEqual(state, expected)
                second = self.recover()
                self.assertEqual(second["operations"][0]["state"], expected)
                self.assertIn(second["operations"][0]["action"], {"no_op", "verified_no_op"})

    def test_corrupt_saved_snapshot_is_preserved_as_recovery_required(self):
        result = self.prepare()
        snapshot = pathlib.Path(result["operation_dir"]) / "snapshot/config.json"
        snapshot.write_bytes(b"tampered")
        snapshot.chmod(0o600)
        recovery = self.recover()
        self.assertEqual(recovery["operations"][0]["state"], "recovery_required")
        record = journal.read_journal(pathlib.Path(result["operation_dir"]))
        self.assertEqual(record["recovery"]["last_action"], "snapshot_integrity_failure")

    def test_staged_config_hash_mismatch_fails_before_operation(self):
        self.write_staging_file("config.json", b'{"changed":true}\n')
        with self.assertRaises(journal.RuntimeJournalError):
            self.prepare()
        self.assertEqual(list((self.operation_store / "operations").iterdir()), [])

    def test_missing_lease_fails_closed(self):
        import shutil
        shutil.rmtree(self.lease_dir)
        with self.assertRaises(journal.RuntimeJournalError):
            self.prepare()
        self.assertEqual(list((self.operation_store / "operations").iterdir()), [])

    def test_operation_store_without_fixture_marker_is_rejected(self):
        (self.operation_store / ".xray-manager-r03-operations-fixture").unlink()
        with self.assertRaises(journal.RuntimeJournalError):
            self.prepare()
        self.assertFalse((self.operation_store / "operations").exists())

    def test_lock_paths_outside_operation_store_are_rejected(self):
        self.lifecycle_lock = self.base / "outside-lifecycle.lock"
        with self.assertRaises(journal.RuntimeJournalError):
            self.prepare()
        self.assertFalse((self.operation_store / "operations").exists())

    def test_service_root_without_fixture_marker_is_rejected(self):
        marker = self.service_root / ".xray-manager-fixture"
        marker.unlink()
        with self.assertRaises(journal.RuntimeJournalError):
            self.prepare()
        self.assertFalse((self.operation_store / "operations").exists())

    def test_service_fixture_binary_mismatch_is_rejected(self):
        self.write_service_fixture(binary_path="/wrong/xray")
        with self.assertRaises(Exception):
            self.prepare()
        self.assertEqual(list((self.operation_store / "operations").iterdir()), [])

    def test_symlink_previous_config_is_rejected(self):
        self.previous_config.unlink()
        self.previous_config.symlink_to(self.base / "outside.json")
        with self.assertRaises(journal.RuntimeJournalError):
            self.prepare()

    def test_hardlinked_previous_config_is_rejected(self):
        hardlink = self.base / "previous-hardlink"
        os.link(self.previous_config, hardlink)
        with self.assertRaises(journal.RuntimeJournalError):
            self.prepare()

    def test_staging_paths_must_match_r02_fixture_root(self):
        self.staging_manifest["staging_dir"] = str(self.base / "outside-stage")
        self.write_staging_file("manifest.json", journal.json_bytes(self.staging_manifest))
        with self.assertRaises(journal.RuntimeJournalError):
            self.prepare()
        self.assertEqual(list((self.operation_store / "operations").iterdir()), [])

    def test_staging_manifest_connection_binding_mismatch_is_rejected(self):
        self.staging_manifest["bindings"][0]["connection_id"] = "different-connection"
        self.write_staging_file("manifest.json", journal.json_bytes(self.staging_manifest))
        with self.assertRaises(journal.RuntimeJournalError):
            self.prepare()

    def test_binary_changed_after_staging_is_rejected(self):
        self.binary.write_text("#!/bin/sh\necho changed\n")
        self.binary.chmod(0o755)
        with self.assertRaises(journal.RuntimeJournalError):
            self.prepare()

    def test_lock_contention_fails_without_creating_operation(self):
        fd = journal.acquire_lock(self.lifecycle_lock)
        try:
            with self.assertRaises(journal.RuntimeJournalError):
                self.prepare()
        finally:
            os.close(fd)
        self.assertFalse((self.operation_store / "operations").exists())

    def test_recovery_without_operations_is_empty_and_read_only(self):
        result = self.recover()
        self.assertEqual(result, {
            "status": "RECOVERY_COMPLETE", "operations": [], "runtime_modified": False
        })
        self.assertFalse((self.operation_store / "operations").exists())

    def test_orphan_operation_directory_without_journal_is_removed_safely(self):
        operations = self.operation_store / "operations"
        operations.mkdir(mode=0o700)
        orphan = operations / ("runtime-op-" + "a" * 32)
        orphan.mkdir(mode=0o700)
        temp_file = orphan / (".tmp-" + "b" * 32)
        temp_file.write_bytes(b"partial journal")
        temp_file.chmod(0o600)
        result = self.recover()
        self.assertEqual(result["operations"][0]["action"], "removed_empty_orphan")
        self.assertFalse(orphan.exists())

    def test_orphan_operation_with_unexpected_artifact_is_preserved(self):
        operations = self.operation_store / "operations"
        operations.mkdir(mode=0o700)
        orphan = operations / ("runtime-op-" + "c" * 32)
        orphan.mkdir(mode=0o700)
        unexpected = orphan / "unexpected.bin"
        unexpected.write_bytes(b"evidence")
        unexpected.chmod(0o600)
        with self.assertRaises(journal.RuntimeJournalError):
            self.recover()
        self.assertTrue(unexpected.exists())

    def test_failed_service_state_is_recorded_without_service_action(self):
        self.write_service_fixture(active_state="failed", sub_state="failed")
        result = self.prepare()
        self.assertEqual(result["previous_service_state"], "failed")
        record = journal.read_journal(pathlib.Path(result["operation_dir"]))
        self.assertEqual(record["service"]["active_state"], "failed")


if __name__ == "__main__":
    unittest.main()
