from __future__ import annotations

import hashlib
import os
import pathlib
import sys
import tempfile
import unittest
from contextlib import nullcontext
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import xray_runtime_live_operation_evidence as evidence

OP = "runtime-op-" + "1" * 32
GEN = "generation-" + "2" * 32
PROFILE = "profile-" + "3" * 32
REVISION = "r000001"
VALIDATION = "pvalidation-" + "4" * 32
CONFIG = b'{"inbounds":[],"outbounds":[]}\n'
DIGEST = hashlib.sha256(CONFIG).hexdigest()


class FakeStore:
    def __init__(self, record):
        self.record = record

    def load(self, operation_id):
        if operation_id != OP:
            raise AssertionError("unexpected operation")
        return self.record


class LiveOperationEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.root.chmod(0o755)
        self.config_dir = self.root / "etc" / "xray"
        self.config_dir.mkdir(parents=True, mode=0o750)
        self.config = self.config_dir / "config.json"
        self.config.write_bytes(CONFIG)
        self.config.chmod(0o640)
        self.gid = os.getgid()
        os.chown(self.config_dir, 0, self.gid)
        os.chown(self.config, 0, self.gid)
        self.record = {
            "environment": "live", "operation_id": OP, "state": "service_action_requested",
            "profile_id": PROFILE, "revision": REVISION, "validation_id": VALIDATION,
            "profile_sha256": "a" * 64, "staged_config_sha256": DIGEST,
            "binary_sha256": "b" * 64,
            "publication": {"status": "published", "target": str(self.config),
                            "config_sha256": DIGEST},
            "service_action": {"action": "start", "status": "requested",
                               "generation_id": GEN, "confirmation": True,
                               "published_config_sha256": DIGEST},
        }
        self.report = {
            "validation_id": VALIDATION, "profile_id": PROFILE, "revision": REVISION,
            "content_sha256": "a" * 64, "result": "PASS",
            "xray": {"binary_sha256": "b" * 64},
            "checks": [{"name": name, "status": "PASS"} for name in evidence.REQUIRED_CHECKS],
        }
        self.reports = mock.Mock()
        self.reports.read_only_locked.return_value = nullcontext()
        self.reports._load_catalog.return_value = {"schema_version": 1, "reports": []}
        self.reports._verify_all.return_value = [self.report]
        self.patches = [
            mock.patch.object(evidence.os, "geteuid", return_value=0),
            mock.patch.object(evidence.grp, "getgrnam", return_value=mock.Mock(gr_gid=self.gid)),
            mock.patch.object(evidence.validation_store_module, "ProfileValidationReportStore",
                              return_value=self.reports),
            mock.patch.object(evidence, "CONFIG_FILE", self.config),
        ]
        for patcher in self.patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    def tearDown(self):
        self.tmp.cleanup()

    def verify(self):
        return evidence.verify_live_operation(
            operation_id=OP, generation_id=GEN, store=FakeStore(self.record),
            validation_store=self.root / "validations", runtime_config_path=self.config,
        )

    def test_verifies_live_operation_chain(self):
        result = self.verify()
        self.assertTrue(result["verified"])
        self.assertEqual(result["environment"], "live")
        self.assertEqual(result["published_config_sha256"], DIGEST)
        self.assertEqual(result["runtime_config_sha256"], DIGEST)
        self.assertEqual(result["action"], "start")

    def test_rejects_fixture_environment(self):
        self.record["environment"] = "fixture"
        with self.assertRaises(evidence.LiveOperationEvidenceError):
            self.verify()

    def test_rejects_wrong_generation(self):
        with self.assertRaises(evidence.LiveOperationEvidenceError):
            evidence.verify_live_operation(operation_id=OP, generation_id="generation-" + "9" * 32,
                                           store=FakeStore(self.record), validation_store=self.root / "v",
                                           runtime_config_path=self.config)

    def test_rejects_unrequested_action(self):
        self.record["state"] = "config_published"
        with self.assertRaises(evidence.LiveOperationEvidenceError):
            self.verify()

    def test_rejects_action_bound_to_another_published_hash(self):
        self.record["service_action"]["published_config_sha256"] = "d" * 64
        with self.assertRaises(evidence.LiveOperationEvidenceError):
            self.verify()

    def test_rejects_missing_confirmation(self):
        self.record["service_action"]["confirmation"] = False
        with self.assertRaises(evidence.LiveOperationEvidenceError):
            self.verify()

    def test_rejects_publication_hash_mismatch(self):
        self.record["publication"]["config_sha256"] = "c" * 64
        with self.assertRaises(evidence.LiveOperationEvidenceError):
            self.verify()

    def test_rejects_runtime_bytes_changed_after_publication(self):
        self.config.write_bytes(b'{"changed":true}\n')
        with self.assertRaises(evidence.LiveOperationEvidenceError):
            self.verify()

    def test_rejects_validation_report_for_other_revision(self):
        self.report["revision"] = "r000002"
        with self.assertRaises(evidence.LiveOperationEvidenceError):
            self.verify()

    def test_rejects_missing_required_validation_check(self):
        self.report["checks"] = self.report["checks"][:-1]
        with self.assertRaises(evidence.LiveOperationEvidenceError):
            self.verify()

    def test_rejects_unsafe_config_mode(self):
        self.config.chmod(0o644)
        with self.assertRaises(evidence.LiveOperationEvidenceError):
            self.verify()


if __name__ == "__main__":
    unittest.main()
