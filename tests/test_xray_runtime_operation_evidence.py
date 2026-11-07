from __future__ import annotations

import hashlib
import pathlib
import sys
import unittest
from contextlib import nullcontext
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import xray_runtime_operation_evidence as evidence

OP = "runtime-op-" + "1" * 32
GEN = "generation-" + "2" * 32
VALIDATION = "pvalidation-" + "3" * 32
PROFILE = "profile-" + "4" * 32
CONFIG = b'{"inbounds":[],"outbounds":[]}\n'
DIGEST = hashlib.sha256(CONFIG).hexdigest()


class EvidenceReaderTests(unittest.TestCase):
    def setUp(self):
        self.record = {
            "schema_version": 2, "state": "config_published", "operation_id": OP,
            "source": {"validation_id": VALIDATION, "profile_id": PROFILE,
                       "revision": "r000001", "profile_content_sha256": "a" * 64},
            "staging": {"config_sha256": DIGEST},
            "service": {"service_root": "/fixture/service", "gid": 123},
            "publication": {"status": "published", "config_sha256": DIGEST},
            "rollback": {"status": "not_started"},
            "orchestration": {"generation_id": GEN},
        }
        self.manifest = {
            "validation_id": VALIDATION, "profile_id": PROFILE,
            "revision": "r000001", "profile_content_sha256": "a" * 64,
            "native_validation": "PASS", "xray_binary": {"sha256": "b" * 64},
        }
        self.report = {
            "validation_id": VALIDATION, "profile_id": PROFILE,
            "revision": "r000001", "content_sha256": "a" * 64,
            "result": "PASS", "xray": {"binary_sha256": "b" * 64},
            "checks": [{"name": name, "status": "PASS"} for name in (
                "json_syntax", "xray_structure", "required_parameters", "types_values",
                "references_conflicts", "xray_native")],
        }
        self.store = mock.Mock()
        self.store.read_only_locked.return_value = nullcontext()
        self.store._load_catalog.return_value = {"schema_version": 1, "reports": []}
        self.store._verify_all.return_value = [self.report]
        self.patches = [
            mock.patch.object(evidence.journal, "check_operation_store"),
            mock.patch.object(evidence.journal, "read_journal", return_value=self.record),
            mock.patch.object(evidence.publisher, "_validate_stage", return_value=(self.manifest, CONFIG)),
            mock.patch.object(evidence.validation_store_module, "ProfileValidationReportStore", return_value=self.store),
            mock.patch.object(evidence.journal, "read_regular", return_value=CONFIG),
        ]
        for patcher in self.patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    def verify(self):
        return evidence.verify_published_operation(
            operation_store=pathlib.Path("/fixture/operations"), operation_id=OP,
            generation_id=GEN, validation_store=pathlib.Path("/fixture/validations"),
            runtime_config_path=pathlib.Path("/fixture/service/etc/xray/config.json"),
        )

    def test_verifies_complete_chain_but_labels_fixture_only(self):
        result = self.verify()
        self.assertTrue(result["verified"])
        self.assertEqual(result["environment"], "fixture")
        self.assertEqual(result["published_config_sha256"], DIGEST)
        self.assertEqual(result["runtime_config_sha256"], DIGEST)

    def test_rejects_generation_mismatch(self):
        with self.assertRaises(evidence.OperationEvidenceError):
            evidence.verify_published_operation(
                operation_store=pathlib.Path("/fixture/operations"), operation_id=OP,
                generation_id="generation-" + "9" * 32,
                validation_store=pathlib.Path("/fixture/validations"),
                runtime_config_path=pathlib.Path("/fixture/service/etc/xray/config.json"),
            )

    def test_rejects_unpublished_state(self):
        self.record["state"] = "recovery_required"
        with self.assertRaises(evidence.OperationEvidenceError):
            self.verify()

    def test_rejects_rollback_started(self):
        self.record["rollback"]["status"] = "recovery_required"
        with self.assertRaises(evidence.OperationEvidenceError):
            self.verify()

    def test_rejects_staging_publication_hash_mismatch(self):
        self.record["publication"]["config_sha256"] = "f" * 64
        with self.assertRaises(evidence.OperationEvidenceError):
            self.verify()

    def test_rejects_validation_report_for_other_profile(self):
        self.report["profile_id"] = "profile-" + "5" * 32
        with self.assertRaises(evidence.OperationEvidenceError):
            self.verify()

    def test_rejects_missing_required_validation_check(self):
        self.report["checks"] = self.report["checks"][:-1]
        with self.assertRaises(evidence.OperationEvidenceError):
            self.verify()

    def test_rejects_runtime_target_outside_operation(self):
        with self.assertRaises(evidence.OperationEvidenceError):
            evidence.verify_published_operation(
                operation_store=pathlib.Path("/fixture/operations"), operation_id=OP,
                generation_id=GEN, validation_store=pathlib.Path("/fixture/validations"),
                runtime_config_path=pathlib.Path("/other/config.json"),
            )

    def test_rejects_runtime_bytes_not_matching_published_hash(self):
        with mock.patch.object(evidence.journal, "read_regular", return_value=b"{}\n"):
            with self.assertRaises(evidence.OperationEvidenceError):
                self.verify()


if __name__ == "__main__":
    unittest.main()
