from __future__ import annotations

import hashlib
import json
import os
import shutil
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import xray_runtime_journal as journal
import xray_runtime_publisher as publisher


class RuntimePublisherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = pathlib.Path(self.tmp.name)
        self.base.chmod(0o755)
        self.service_uid = 65534
        self.service_gid = 65534

        self.r02_marker = self.base / ".xray-manager-r02-fixture"
        self.r02_marker.write_text(json.dumps({
            "schema_version": 1, "purpose": "xray-runtime-r02-isolated-fixture"
        }, sort_keys=True, separators=(",", ":")) + "\n")
        self.r02_marker.chmod(0o600)

        self.binary = self.base / "xray-fixture"
        self.binary.write_text(
            "#!/usr/bin/python3\n"
            "import pathlib,sys\n"
            "if sys.argv[1:4] != ['run','-test','-config']: raise SystemExit(90)\n"
            "data=pathlib.Path(sys.argv[4]).read_text()\n"
            "if 'reject' in data: raise SystemExit(23)\n"
            "raise SystemExit(0)\n"
        )
        self.binary.chmod(0o755)
        self.binary_hash = hashlib.sha256(self.binary.read_bytes()).hexdigest()

        self.service_root = self.base / "service-root"
        self.service_root.mkdir(mode=0o711)
        self.write_marker(self.service_root / ".xray-manager-fixture", {
            "schema_version": 1, "purpose": "xray-runtime-isolated-fixture"
        }, 0, 0, 0o600)
        etc = self.service_root / "etc"
        etc.mkdir(mode=0o755)
        self.config_dir = etc / "xray"
        self.config_dir.mkdir(mode=0o750)
        os.chown(self.config_dir, 0, self.service_gid)
        self.target = self.config_dir / "config.json"
        self.previous_bytes = journal.json_bytes({
            "log": {"loglevel": "warning"},
            "inbounds": [],
            "outbounds": [{"protocol": "freedom", "tag": "direct"}],
        })
        self.write_target(self.previous_bytes)

        self.service_state = self.base / "service-state.json"
        self.service_state.write_text(json.dumps({
            "unit": "xray.service", "load_state": "loaded",
            "active_state": "active", "sub_state": "running",
            "user": "xray", "group": "xray", "binary_path": str(self.binary),
        }, sort_keys=True))
        self.service_state.chmod(0o600)

        self.staging_dir = self.base / "staging"
        self.staging_dir.mkdir(mode=0o750)
        os.chown(self.staging_dir, 0, self.service_gid)
        self.lease_root = self.base / "leases"
        self.lease_root.mkdir(mode=0o750)
        os.chown(self.lease_root, 0, self.service_gid)
        self.write_marker(
            self.lease_root / ".xray-manager-r02-leases-fixture",
            {"schema_version": 1, "purpose": "xray-runtime-r02-isolated-leases"},
            0, self.service_gid, 0o640,
        )
        self.lease_id = "resolve-" + "b" * 32
        self.lease_dir = self.lease_root / self.lease_id
        self.lease_dir.mkdir(mode=0o750)
        os.chown(self.lease_dir, 0, self.service_gid)
        self.write_lease_file("certificate.pem", b"-----BEGIN CERTIFICATE-----\nfixture\n")
        self.write_lease_file("private-key.pem", b"-----BEGIN PRIVATE KEY-----\nfixture\n")
        self.lease_manifest = {
            "lease_id": self.lease_id, "connection_id": "vless-tls-01",
            "protocol": "vless", "certificate_id": "cert-fixture",
            "certificate_revision": 1, "certificate_fingerprint_sha256": "f" * 64,
            "service_uid": self.service_uid, "service_gid": self.service_gid,
        }
        self.write_lease_file("manifest.json", journal.json_bytes(self.lease_manifest))

        self.config = {
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
        self.staged_bytes = journal.json_bytes(self.config)
        self.write_stage_file("config.json", self.staged_bytes)
        self.staging_manifest = {
            "schema_version": 1, "status": "STAGED",
            "fixture_root": str(self.base), "staging_dir": str(self.staging_dir),
            "lease_root": str(self.lease_root),
            "profile_id": "profile-" + "a" * 32, "revision": "r000001",
            "validation_id": "pvalidation-" + "c" * 32,
            "profile_content_sha256": "d" * 64, "bindings_sha256": "e" * 64,
            "bindings": [{"inbound_tag": "tls-in", "connection_id": "vless-tls-01"}],
            "leases": [{
                "lease_id": self.lease_id, "connection_id": "vless-tls-01",
                "protocol": "vless", "certificate_id": "cert-fixture",
            }],
            "staged_config_sha256": hashlib.sha256(self.staged_bytes).hexdigest(),
            "staged_config_size_bytes": len(self.staged_bytes),
            "service_identity": {"uid": self.service_uid, "gid": self.service_gid},
            "xray_binary": {
                "path": str(self.binary), "sha256": self.binary_hash,
                "size_bytes": self.binary.stat().st_size,
            },
            "native_validation": "PASS", "runtime_published": False,
            "service_started": False,
        }
        self.write_stage_file("manifest.json", journal.json_bytes(self.staging_manifest))

        self.operation_store = self.base / "operation-store"
        self.operation_store.mkdir(mode=0o700)
        self.write_marker(self.operation_store / ".xray-manager-r03-operations-fixture", {
            "schema_version": 1, "purpose": "xray-runtime-r03-isolated-operations"
        }, 0, 0, 0o600)
        self.lock_dir = self.operation_store / "locks"
        self.lock_dir.mkdir(mode=0o700)
        self.lifecycle_lock = self.lock_dir / "lifecycle.lock"
        self.application_lock = self.lock_dir / "application.lock"
        self.operation = self.prepare_operation()

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def write_marker(path, value, uid, gid, mode):
        path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
        os.chown(path, uid, gid)
        path.chmod(mode)

    def write_target(self, data):
        self.target.write_bytes(data)
        os.chown(self.target, 0, self.service_gid)
        self.target.chmod(0o640)

    def write_lease_file(self, name, data):
        path = self.lease_dir / name
        path.write_bytes(data)
        os.chown(path, 0, self.service_gid)
        path.chmod(0o640)

    def write_stage_file(self, name, data):
        path = self.staging_dir / name
        path.write_bytes(data)
        os.chown(path, 0, self.service_gid)
        path.chmod(0o640)

    def prepare_operation(self):
        return journal.prepare_operation(
            staging_dir=self.staging_dir, service_root=self.service_root,
            service_state=self.service_state, operation_store=self.operation_store,
            lifecycle_lock=self.lifecycle_lock, application_lock=self.application_lock,
            lease_root=self.lease_root, service_uid=self.service_uid, service_gid=self.service_gid,
        )

    def publish(self, **kwargs):
        return publisher.publish_operation(
            self.operation_store, self.operation["operation_id"],
            self.lifecycle_lock, self.application_lock, **kwargs,
        )

    def rollback(self, **kwargs):
        return publisher.rollback_operation(
            self.operation_store, self.operation["operation_id"],
            self.lifecycle_lock, self.application_lock, **kwargs,
        )

    def recover(self):
        return publisher.recover_publications(
            self.operation_store, self.lifecycle_lock, self.application_lock,
        )

    def test_atomic_publish_and_config_rollback(self):
        result = self.publish()
        self.assertEqual(result["status"], "CONFIG_PUBLISHED")
        self.assertEqual(self.target.read_bytes(), self.staged_bytes)
        info = self.target.stat()
        self.assertEqual((info.st_uid, info.st_gid, info.st_mode & 0o777),
                         (0, self.service_gid, 0o640))
        record = journal.read_journal(pathlib.Path(self.operation["operation_dir"]))
        self.assertEqual(record["state"], "config_published")
        self.assertEqual(record["publication"]["config_sha256"], hashlib.sha256(self.staged_bytes).hexdigest())
        self.assertEqual(self.publish()["status"], "ALREADY_PUBLISHED")

        rolled = self.rollback()
        self.assertEqual(rolled["status"], "ROLLBACK_CONFIG_RESTORED")
        self.assertEqual(self.target.read_bytes(), self.previous_bytes)
        record = journal.read_journal(pathlib.Path(self.operation["operation_dir"]))
        self.assertEqual(record["state"], "rollback_config_restored")
        self.assertEqual(record["rollback"]["validation"], "PASS")
        self.assertEqual(self.rollback()["status"], "ALREADY_RESTORED")

    def test_no_previous_config_is_never_deleted_automatically(self):
        import shutil
        shutil.rmtree(self.operation["operation_dir"])
        self.target.unlink()
        self.operation = self.prepare_operation()
        self.assertEqual(self.operation["previous_config"], "no_previous_config")
        self.publish()
        result = self.rollback()
        self.assertEqual(result["status"], "RECOVERY_REQUIRED")
        self.assertEqual(self.target.read_bytes(), self.staged_bytes)
        record = journal.read_journal(pathlib.Path(self.operation["operation_dir"]))
        self.assertEqual(record["state"], "recovery_required")

    def test_crash_after_first_publish_without_previous_config_requires_intervention(self):
        import shutil
        shutil.rmtree(self.operation["operation_dir"])
        self.target.unlink()
        self.operation = self.prepare_operation()
        with self.assertRaises(journal.SimulatedCrash):
            self.publish(crash_at="after_rename")
        self.assertEqual(self.target.read_bytes(), self.staged_bytes)
        result = self.recover()
        self.assertEqual(result["operations"][0]["status"], "RECOVERY_REQUIRED")
        self.assertEqual(self.target.read_bytes(), self.staged_bytes)
        record = journal.read_journal(pathlib.Path(self.operation["operation_dir"]))
        self.assertEqual(record["state"], "recovery_required")

    def test_destination_toctou_aborts_without_overwrite(self):
        changed = b'{"changed_by_external_actor":true}\n'
        self.write_target(changed)
        with self.assertRaises(journal.RuntimeJournalError):
            self.publish()
        self.assertEqual(self.target.read_bytes(), changed)
        self.assertEqual(journal.read_journal(pathlib.Path(self.operation["operation_dir"]))["state"],
                         "snapshot_saved")

    def test_symlink_destination_is_rejected(self):
        self.target.unlink()
        outside = self.base / "outside.json"
        outside.write_bytes(self.previous_bytes)
        self.target.symlink_to(outside)
        with self.assertRaises(journal.RuntimeJournalError):
            self.publish()
        self.assertTrue(self.target.is_symlink())
        self.assertEqual(outside.read_bytes(), self.previous_bytes)

    def test_hardlink_destination_is_rejected(self):
        hardlink = self.base / "config-hardlink"
        os.link(self.target, hardlink)
        with self.assertRaises(journal.RuntimeJournalError):
            self.publish()
        self.assertEqual(self.target.read_bytes(), self.previous_bytes)

    def test_xray_rejects_candidate_before_publication(self):
        rejected = journal.json_bytes(self.config | {"reject": True})
        self.write_stage_file("config.json", rejected)
        self.staging_manifest["staged_config_sha256"] = hashlib.sha256(rejected).hexdigest()
        self.staging_manifest["staged_config_size_bytes"] = len(rejected)
        self.write_stage_file("manifest.json", journal.json_bytes(self.staging_manifest))
        # La primera operación del setUp es un fixture independiente; se elimina
        # sólo dentro del directorio temporal de esta prueba negativa.
        shutil.rmtree(self.operation["operation_dir"])
        self.operation = self.prepare_operation()
        with self.assertRaises(Exception):
            self.publish()
        self.assertEqual(self.target.read_bytes(), self.previous_bytes)
        self.assertEqual(journal.read_journal(pathlib.Path(self.operation["operation_dir"]))["state"],
                         "snapshot_saved")

    def test_crash_before_rename_leaves_previous_config_and_recovery_cleans_temp(self):
        with self.assertRaises(journal.SimulatedCrash):
            self.publish(crash_at="before_rename")
        self.assertEqual(self.target.read_bytes(), self.previous_bytes)
        self.assertTrue(any(p.name.startswith(".config.json.r04tmp-") for p in self.config_dir.iterdir()))
        result = self.recover()
        self.assertEqual(result["operations"][0]["status"], "NOT_PUBLISHED")
        self.assertEqual(self.target.read_bytes(), self.previous_bytes)
        self.assertFalse(any(p.name.startswith(".config.json.r04tmp-") for p in self.config_dir.iterdir()))

    def test_crash_after_rename_is_detected_and_rolled_back(self):
        with self.assertRaises(journal.SimulatedCrash):
            self.publish(crash_at="after_rename")
        self.assertEqual(self.target.read_bytes(), self.staged_bytes)
        result = self.recover()
        self.assertEqual(result["operations"][0]["status"], "ROLLBACK_CONFIG_RESTORED")
        self.assertEqual(self.target.read_bytes(), self.previous_bytes)
        record = journal.read_journal(pathlib.Path(self.operation["operation_dir"]))
        self.assertEqual(record["state"], "rollback_config_restored")

    def test_crash_after_rollback_rename_is_recovered_idempotently(self):
        self.publish()
        with self.assertRaises(journal.SimulatedCrash):
            self.rollback(crash_at="after_rollback_rename")
        self.assertEqual(self.target.read_bytes(), self.previous_bytes)
        record = journal.read_journal(pathlib.Path(self.operation["operation_dir"]))
        self.assertEqual(record["state"], "rollback_started")
        result = self.recover()
        self.assertEqual(result["operations"][0]["status"], "ROLLBACK_CONFIG_RESTORED")
        self.assertEqual(journal.read_journal(pathlib.Path(self.operation["operation_dir"]))["state"],
                         "rollback_config_restored")

    def test_rollback_refuses_external_runtime_drift_without_overwrite(self):
        self.publish()
        external = b'{"external_actor":true,"must_preserve":true}\n'
        self.write_target(external)
        result = self.rollback()
        self.assertEqual(result["status"], "RECOVERY_REQUIRED")
        self.assertEqual(self.target.read_bytes(), external)
        record = journal.read_journal(pathlib.Path(self.operation["operation_dir"]))
        self.assertEqual(record["state"], "recovery_required")
        self.assertIn("no coincide", record["rollback"]["last_error"])

    def test_rollback_refuses_corrupted_snapshot_without_overwrite(self):
        self.publish()
        snapshot = pathlib.Path(self.operation["operation_dir"]) / "snapshot/config.json"
        snapshot.write_bytes(b'{"tampered_snapshot":true}\n')
        snapshot.chmod(0o600)
        staged = self.target.read_bytes()
        result = self.rollback()
        self.assertEqual(result["status"], "RECOVERY_REQUIRED")
        self.assertEqual(self.target.read_bytes(), staged)
        record = journal.read_journal(pathlib.Path(self.operation["operation_dir"]))
        self.assertEqual(record["state"], "recovery_required")
        self.assertIn("Snapshot inválido", record["rollback"]["last_error"])

    def test_recovery_after_rollback_rename_preserves_external_drift(self):
        self.publish()
        with self.assertRaises(journal.SimulatedCrash):
            self.rollback(crash_at="after_rollback_rename")
        external = b'{"external_after_crash":true}\n'
        self.write_target(external)
        result = self.recover()
        self.assertEqual(result["operations"][0]["status"], "RECOVERY_REQUIRED")
        self.assertEqual(self.target.read_bytes(), external)
        record = journal.read_journal(pathlib.Path(self.operation["operation_dir"]))
        self.assertEqual(record["state"], "recovery_required")

    def test_repeated_recovery_after_rollback_is_read_only_and_idempotent(self):
        self.publish()
        with self.assertRaises(journal.SimulatedCrash):
            self.rollback(crash_at="after_rollback_rename")
        first = self.recover()
        self.assertEqual(first["operations"][0]["status"], "ROLLBACK_CONFIG_RESTORED")
        journal_path = pathlib.Path(self.operation["operation_dir"]) / "journal.json"
        journal_bytes = journal_path.read_bytes()
        config_bytes = self.target.read_bytes()
        second = self.recover()
        self.assertEqual(second["operations"][0]["status"], "ROLLBACK_CONFIG_RESTORED")
        self.assertEqual(journal_path.read_bytes(), journal_bytes)
        self.assertEqual(self.target.read_bytes(), config_bytes)

    def test_recovery_marks_corrupted_snapshot_recovery_required_without_overwrite(self):
        self.publish()
        snapshot = pathlib.Path(self.operation["operation_dir"]) / "snapshot/config.json"
        snapshot.write_bytes(b'{"tampered_during_recovery":true}\n')
        snapshot.chmod(0o600)
        staged = self.target.read_bytes()
        result = self.recover()
        self.assertEqual(result["operations"][0]["status"], "RECOVERY_REQUIRED")
        self.assertEqual(self.target.read_bytes(), staged)
        record = journal.read_journal(pathlib.Path(self.operation["operation_dir"]))
        self.assertEqual(record["state"], "recovery_required")
        self.assertIn("Snapshot inválido", record["rollback"]["last_error"])

    def test_snapshot_corruption_blocks_publication(self):
        snapshot = pathlib.Path(self.operation["operation_dir"]) / "snapshot/config.json"
        snapshot.write_bytes(b"corrupt")
        snapshot.chmod(0o600)
        with self.assertRaises(journal.RuntimeJournalError):
            self.publish()
        self.assertEqual(self.target.read_bytes(), self.previous_bytes)

    def test_nested_transaction_context_reuses_one_lock_owner(self):
        with publisher.transaction_locks(
            self.operation_store, self.lifecycle_lock, self.application_lock
        ):
            self.assertEqual(
                publisher._acquire(self.operation_store, self.lifecycle_lock, self.application_lock),
                [],
            )
            with publisher.transaction_locks(
                self.operation_store, self.lifecycle_lock, self.application_lock
            ):
                self.assertEqual(
                    publisher._acquire(self.operation_store, self.lifecycle_lock, self.application_lock),
                    [],
                )
            with self.assertRaises(journal.RuntimeJournalError):
                publisher._acquire(
                    self.operation_store, self.lifecycle_lock,
                    self.lock_dir / "different-application.lock",
                )
        fd = journal.acquire_lock(self.lifecycle_lock)
        journal.release_locks([fd])

    def test_lock_contention_blocks_publication(self):
        fd = journal.acquire_lock(self.lifecycle_lock)
        try:
            with self.assertRaises(journal.RuntimeJournalError):
                self.publish()
        finally:
            os.close(fd)
        self.assertEqual(self.target.read_bytes(), self.previous_bytes)


if __name__ == "__main__":
    unittest.main()
