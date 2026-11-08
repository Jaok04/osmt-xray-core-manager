from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import xray_runtime_live_journal as live_journal
import xray_runtime_live_publisher as publisher

PROFILE = "profile-" + "a" * 32
REVISION = "r000001"
VALIDATION = "pvalidation-" + "b" * 32
PREVIOUS = b'{"old":true}\n'
CANDIDATE = b'{"new":true}\n'
BINARY_HASH = "c" * 64


class LivePublisherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.root.chmod(0o755)
        self.gid = 65534
        self.uid = 65534
        self.stage_root = self.root / "run" / "xray-manager-runtime-staging"
        self.stage_root.parent.mkdir(parents=True, mode=0o755)
        self.stage_root.mkdir(mode=0o711)
        self.stage_dir = self.stage_root / "live-12345678"
        self.stage_dir.mkdir(mode=0o750)
        os.chown(self.stage_dir, 0, self.gid)
        self.config_dir = self.root / "etc" / "xray"
        self.config_dir.mkdir(parents=True, mode=0o750)
        os.chown(self.config_dir, 0, self.gid)
        self.config_file = self.config_dir / "config.json"
        self.operation_root = self.root / "var" / "lib" / "xray-manager" / "runtime-operations"
        self.operation_root.parent.mkdir(parents=True, mode=0o755)
        self.lock_root = self.root / "run" / "locks"
        self.lock_root.mkdir(mode=0o755)
        self.integrity_root = self.root / "run" / "manager"
        self.integrity_root.mkdir(mode=0o755)
        self.unit_file = self.root / "etc" / "systemd" / "xray.service"
        self.unit_file.parent.mkdir(parents=True, mode=0o755)
        self.unit_file.write_text("fixture")
        self.unit_file.chmod(0o644)

        self.manifest = {
            "schema_version": 1, "environment": "live", "status": "STAGED",
            "profile_id": PROFILE, "revision": REVISION, "validation_id": VALIDATION,
            "profile_content_sha256": hashlib.sha256(b"profile").hexdigest(),
            "mapping_file": "/var/lib/xray-manager/profile-bindings/" + PROFILE + "/" + REVISION + ".json",
            "mapping_sha256": hashlib.sha256(b"mapping").hexdigest(),
            "bindings": [{"inbound_tag": "vless-in", "connection_id": "conn-12345678"}],
            "leases": [{"lease_id": "lease-12345678", "connection_id": "conn-12345678",
                        "protocol": "vless", "certificate_id": "cert-12345678"}],
            "staging_dir": str(self.stage_dir),
            "config_sha256": hashlib.sha256(CANDIDATE).hexdigest(),
            "config_size_bytes": len(CANDIDATE),
            "service_identity": {"user": "xray", "group": "xray", "uid": self.uid, "gid": self.gid},
            "systemd_observation": {
                "unit": "xray.service", "load_state": "loaded", "active_state": "inactive",
                "invocation_id": None, "main_pid": None, "fragment_path": str(self.unit_file),
            },
            "xray_binary": {"path": "/usr/local/bin/xray", "sha256": BINARY_HASH, "size_bytes": 1234},
            "native_validation": "PASS", "runtime_published": False, "service_started": False,
        }
        self._write_owned(self.stage_dir / "config.json", CANDIDATE, 0o640)
        self._write_owned(
            self.stage_dir / "manifest.json",
            (json.dumps(self.manifest, sort_keys=True, separators=(",", ":")) + "\n").encode(),
            0o640,
        )
        self.systemd = {
            "unit": "xray.service", "load_state": "loaded", "active_state": "inactive",
            "main_pid": None, "invocation_id": None, "fragment_path": str(self.unit_file),
            "user": "xray", "group": "xray", "need_daemon_reload": "no",
            "drop_in_paths": "", "service_type": "simple", "read_only": True,
            "sub_state": "dead", "result": "success", "exec_main_status": "0",
            "runtime_config_sha256": None, "unit_file_state": "enabled",
        }
        patches = [
            mock.patch.object(publisher, "CONFIG_FILE", self.config_file),
            mock.patch.object(publisher, "CONFIG_DIR", self.config_dir),
            mock.patch.object(publisher, "UNIT_FILE", self.unit_file),
            mock.patch.object(publisher, "XRAY_BINARY", pathlib.Path("/usr/local/bin/xray")),
            mock.patch.object(publisher, "STAGING_ROOT", self.stage_root),
            mock.patch.object(publisher, "OPERATION_ROOT", self.operation_root),
            mock.patch.object(publisher, "LIFECYCLE_LOCK", self.lock_root / "lifecycle.lock"),
            mock.patch.object(publisher, "INTEGRITY_LOCK", self.integrity_root / "integrity.lock"),
            mock.patch.object(publisher.grp, "getgrnam", return_value=types.SimpleNamespace(gr_gid=self.gid)),
            mock.patch.object(publisher, "_service_identity", return_value=(self.uid, self.gid)),
            mock.patch.object(publisher, "_binary_hash", return_value=BINARY_HASH),
            mock.patch.object(publisher.systemd_adapter, "status", side_effect=lambda **_: dict(self.systemd)),
            mock.patch.object(publisher.staging, "_service_run"),
        ]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_owned(self, path, data, mode):
        path.write_bytes(data)
        os.chown(path, 0, self.gid)
        path.chmod(mode)

    def _journal(self):
        store = live_journal.LiveOperationStore(self.operation_root)
        operations = list(self.operation_root.iterdir())
        self.assertEqual(len(operations), 1)
        return store.load(operations[0].name), store

    def test_publishes_atomically_and_never_starts_service(self):
        self._write_owned(self.config_file, PREVIOUS, 0o640)
        self.systemd["runtime_config_sha256"] = hashlib.sha256(PREVIOUS).hexdigest()
        result = publisher.publish_live(self.stage_dir)
        self.assertEqual(result["status"], "CONFIG_PUBLISHED")
        self.assertTrue(result["runtime_published"])
        self.assertFalse(result["service_action_performed"])
        self.assertFalse(result["service_started"])
        self.assertFalse(result["configuration_loaded"])
        self.assertEqual(self.config_file.read_bytes(), CANDIDATE)
        record, store = self._journal()
        self.assertEqual(record["state"], "config_published")
        self.assertEqual(store.read_snapshot(record["operation_id"]), PREVIOUS)
        self.assertEqual(os.stat(self.config_file).st_mode & 0o777, 0o640)

    def test_first_install_failure_preserves_new_config_and_requires_recovery(self):
        with mock.patch.object(publisher, "_verify_config", side_effect=publisher.LivePublisherError("verify")):
            with self.assertRaises(publisher.LivePublisherError):
                publisher.publish_live(self.stage_dir)
        self.assertEqual(self.config_file.read_bytes(), CANDIDATE)
        record, _ = self._journal()
        self.assertEqual(record["state"], "recovery_required")
        self.assertEqual(record["snapshot"], {"present": False})
        self.assertEqual(record["recovery"]["decision"], "preserve_first_install_config")

    def test_existing_config_is_restored_if_post_rename_verification_fails(self):
        self._write_owned(self.config_file, PREVIOUS, 0o640)
        self.systemd["runtime_config_sha256"] = hashlib.sha256(PREVIOUS).hexdigest()
        real_verify = publisher._verify_config
        calls = {"n": 0}

        def fail_once(digest, gid):
            calls["n"] += 1
            if calls["n"] == 1:
                raise publisher.LivePublisherError("injected verification failure")
            return real_verify(digest, gid)

        with mock.patch.object(publisher, "_verify_config", side_effect=fail_once):
            with self.assertRaises(publisher.LivePublisherError):
                publisher.publish_live(self.stage_dir)
        self.assertEqual(self.config_file.read_bytes(), PREVIOUS)
        record, _ = self._journal()
        self.assertEqual(record["state"], "rolled_back")
        self.assertEqual(record["rollback"]["config_status"], "restored")

    def test_rollback_refuses_to_overwrite_external_config_change(self):
        self._write_owned(self.config_file, PREVIOUS, 0o640)
        self.systemd["runtime_config_sha256"] = hashlib.sha256(PREVIOUS).hexdigest()
        external = b'{"external-change":true}\n'

        def mutate_then_fail(_digest, _gid):
            self._write_owned(self.config_file, external, 0o640)
            raise publisher.LivePublisherError("verification failed after external change")

        with mock.patch.object(publisher, "_verify_config", side_effect=mutate_then_fail):
            with self.assertRaises(publisher.LivePublisherError):
                publisher.publish_live(self.stage_dir)
        self.assertEqual(self.config_file.read_bytes(), external)
        record, _ = self._journal()
        self.assertEqual(record["state"], "recovery_required")
        self.assertEqual(record["recovery"]["decision"], "manual_recovery_required")

    def test_rejects_active_service_before_creating_operation(self):
        self.systemd["active_state"] = "active"
        self.systemd["main_pid"] = 123
        self.systemd["invocation_id"] = "a" * 32
        with self.assertRaises(publisher.LivePublisherError):
            publisher.publish_live(self.stage_dir)
        self.assertFalse(self.operation_root.exists())

    def test_rejects_changed_runtime_config_before_publish(self):
        self._write_owned(self.config_file, PREVIOUS, 0o640)
        self.systemd["runtime_config_sha256"] = hashlib.sha256(b"other").hexdigest()
        with self.assertRaises(publisher.LivePublisherError):
            publisher.publish_live(self.stage_dir)
        self.assertEqual(self.config_file.read_bytes(), PREVIOUS)
        self.assertFalse(self.operation_root.exists())

    def test_cas_detects_config_change_after_snapshot(self):
        self._write_owned(self.config_file, PREVIOUS, 0o640)
        self.systemd["runtime_config_sha256"] = hashlib.sha256(PREVIOUS).hexdigest()
        original_read = publisher._read_optional_config
        calls = {"n": 0}

        def changed_after_snapshot():
            calls["n"] += 1
            if calls["n"] == 1:
                return original_read()
            return b'{"external":true}\n'

        with mock.patch.object(publisher, "_read_optional_config", side_effect=changed_after_snapshot):
            with self.assertRaises(publisher.LivePublisherError):
                publisher.publish_live(self.stage_dir)
        self.assertEqual(self.config_file.read_bytes(), PREVIOUS)
        record, _ = self._journal()
        self.assertEqual(record["state"], "recovery_required")

    def test_rejects_tampered_staged_config(self):
        (self.stage_dir / "config.json").write_bytes(b"tampered")
        with self.assertRaises(publisher.LivePublisherError):
            publisher.publish_live(self.stage_dir)
        self.assertFalse(self.operation_root.exists())

    def test_rejects_non_direct_child_staging_path(self):
        with self.assertRaises(publisher.LivePublisherError):
            publisher.publish_live(self.root / "outside" / self.stage_dir.name)


if __name__ == "__main__":
    unittest.main()
