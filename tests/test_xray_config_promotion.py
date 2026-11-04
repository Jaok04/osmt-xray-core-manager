#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import xray_config_promotion as promotion
import xray_configurations as configurations
import xray_validation_store as validation_store


CONFIG_BYTES = json.dumps({
    "inbounds": [{
        "tag": "socks-in", "listen": "127.0.0.1", "port": 10808,
        "protocol": "socks", "settings": {}
    }],
    "outbounds": [{"tag": "direct", "protocol": "freedom", "settings": {}}],
}, separators=(",", ":")).encode()


def validation_result(data: bytes, result: str = "PASS", warning: bool = False) -> dict:
    checks = [
        {"name": name, "status": "PASS", "errors": [], "warnings": [], "details": {}}
        for name in (
            "json_syntax", "xray_structure", "required_parameters", "types_values",
            "references_conflicts",
        )
    ]
    checks.append({
        "name": "compatibility", "status": "DEFERRED_TO_NATIVE",
        "errors": [], "warnings": [], "details": {},
    })
    native_status = "FAIL" if result == "FAIL" else "PASS"
    checks.append({
        "name": "xray_native", "status": native_status,
        "errors": ["native rejection"] if native_status == "FAIL" else [],
        "warnings": [], "details": {},
    })
    if warning:
        checks[0]["warnings"] = ["compatibility advisory"]
    return {
        "schema_version": 1,
        "created_at": "2026-11-04T18:00:00Z",
        "content_sha256": hashlib.sha256(data).hexdigest(),
        "content_size_bytes": len(data),
        "checks": checks,
        "xray": {"version": "Xray 26.10.31", "binary_sha256": "a" * 64},
        "result": result,
        "report_persisted": False,
        "configuration_applied": False,
        "service_started": False,
    }


class PromotionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = pathlib.Path(self.tmp.name)
        self.config_root = base / "configurations"
        self.validation_root = base / "validation"
        self.key_path = base / "synthetic.key"
        self.key_path.write_bytes(b"S" * 32)
        self.key_path.chmod(0o600)
        self.configs = configurations.ConfigurationStore(self.config_root, self.key_path)
        self.reports = validation_store.ValidationReportStore(self.validation_root)
        self.config = self.configs.create("C05C test", "empty")
        self.config_id = self.config["config_id"]
        self.source = base / "configuration.json"
        self.source.write_bytes(CONFIG_BYTES)
        preview = self.configs.preview_edit(self.config_id, str(self.source))
        self.configs.edit(
            self.config_id, str(self.source), preview["sha256"],
            preview["current_revision"],
        )
        self.service = promotion.ValidationPromotionService(
            self.config_root, self.key_path, self.validation_root,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def run_validation(self, result="PASS", warning=False, revision=None):
        with mock.patch.object(
            promotion.validator, "validate_configuration",
            side_effect=lambda data, **kwargs: validation_result(data, result, warning),
        ):
            return self.service.validate(self.config_id, revision=revision)

    def test_pass_promotes_current_revision_and_persists_report(self):
        result = self.run_validation()
        self.assertTrue(result["promoted"])
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["validation_status"], "valid")
        self.assertEqual(result["last_validated_revision"], "r000001")
        report = self.reports.get_report(result["validation_id"])
        self.assertEqual(report["content_sha256"], hashlib.sha256(CONFIG_BYTES).hexdigest())
        self.assertEqual(report["revision"], "r000001")
        self.assertEqual(self.configs.show(self.config_id)["validation_status"], "valid")

    def test_pass_with_warnings_promotes(self):
        result = self.run_validation("PASS_WITH_WARNINGS", warning=True)
        self.assertTrue(result["promoted"])
        self.assertEqual(result["validation_status"], "valid")

    def test_fail_is_persisted_but_not_promoted(self):
        result = self.run_validation("FAIL")
        self.assertFalse(result["promoted"])
        self.assertEqual(result["validation_status"], "not_validated")
        self.assertEqual(self.reports.get_report(result["validation_id"])["result"], "FAIL")

    def test_incomplete_is_persisted_but_not_promoted(self):
        report = validation_result(CONFIG_BYTES, "INCOMPLETE")
        report["checks"][-1]["status"] = "INCOMPLETE"
        with mock.patch.object(promotion.validator, "validate_configuration", return_value=report):
            result = self.service.validate(self.config_id)
        self.assertFalse(result["promoted"])
        self.assertEqual(result["validation_status"], "not_validated")
        self.assertEqual(self.reports.get_report(result["validation_id"])["result"], "INCOMPLETE")

    def test_missing_required_check_never_promotes(self):
        report = validation_result(CONFIG_BYTES)
        report["checks"] = [item for item in report["checks"] if item["name"] != "references_conflicts"]
        with mock.patch.object(promotion.validator, "validate_configuration", return_value=report):
            with self.assertRaises(promotion.PromotionError):
                self.service.validate(self.config_id)
        self.assertEqual(self.reports.list_reports(), [])
        self.assertEqual(self.configs.show(self.config_id)["validation_status"], "not_validated")

    def test_historical_revision_is_recorded_without_marking_current_valid(self):
        first = "r000001"
        self.source.write_bytes(CONFIG_BYTES + b" ")
        preview = self.configs.preview_edit(self.config_id, str(self.source))
        self.configs.edit(
            self.config_id, str(self.source), preview["sha256"],
            preview["current_revision"],
        )
        result = self.run_validation(revision=first)
        self.assertTrue(result["promoted"])
        self.assertEqual(result["current_revision"], "r000002")
        self.assertFalse(result["selected_revision_is_current"])
        self.assertEqual(result["last_validated_revision"], first)
        self.assertEqual(result["validation_status"], "not_validated")

    def test_edit_after_validation_creates_draft_and_preserves_validated_pointer(self):
        result = self.run_validation()
        self.assertTrue(result["promoted"])
        self.source.write_bytes(CONFIG_BYTES + b" ")
        preview = self.configs.preview_edit(self.config_id, str(self.source))
        edited = self.configs.edit(
            self.config_id, str(self.source), preview["sha256"],
            preview["current_revision"],
        )
        metadata = self.configs.show(self.config_id)
        self.assertEqual(edited["created_revision"], "r000002")
        self.assertEqual(metadata["validation_status"], "not_validated")
        self.assertEqual(metadata["last_validated_revision"], "r000001")

    @unittest.skipUnless(
        os.geteuid() == 0 and pathlib.Path("/usr/local/bin/xray").is_file(),
        "requiere Xray real en /usr/local/bin/xray y ejecución root",
    )
    def test_real_xray_binary_end_to_end(self):
        result = self.service.validate(
            self.config_id, xray_binary="/usr/local/bin/xray", timeout=20,
        )
        self.assertTrue(result["promoted"])
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["validation_status"], "valid")
        stored = self.reports.get_report(result["validation_id"])
        native = next(item for item in stored["checks"] if item["name"] == "xray_native")
        self.assertEqual(native["status"], "PASS")
        self.assertTrue(stored["xray_version"].startswith("Xray "))
        self.assertEqual(stored["content_sha256"], hashlib.sha256(CONFIG_BYTES).hexdigest())

    def test_metadata_rejects_inconsistent_or_unknown_validation_states(self):
        path = self.configs.items / self.config_id / "metadata.json"
        original = json.loads(path.read_text())
        for value in ([], "unknown", "valid"):
            changed = dict(original)
            changed["validation_status"] = value
            path.write_text(json.dumps(changed))
            path.chmod(0o600)
            with self.assertRaises(configurations.ConfigurationError):
                self.configs.load_metadata(self.config_id)
        path.write_text(json.dumps(original))
        path.chmod(0o600)
        self.assertEqual(self.configs.load_metadata(self.config_id)["validation_status"], "not_validated")

    def test_rejects_hash_mismatch_from_validator(self):
        report = validation_result(CONFIG_BYTES)
        report["content_sha256"] = "f" * 64
        with mock.patch.object(promotion.validator, "validate_configuration", return_value=report):
            with self.assertRaises(promotion.PromotionError):
                self.service.validate(self.config_id)
        self.assertEqual(self.reports.list_reports(), [])

    def test_prepared_transaction_rolls_back_after_sigkill(self):
        code = r'''
import os, pathlib, signal, sys
root, key, validation = map(pathlib.Path, sys.argv[1:4])
sys.path.insert(0, sys.argv[4] + "/scripts")
import xray_config_promotion as p
import xray_validation_store as v
data = pathlib.Path(sys.argv[5]).read_bytes()
def fake(data, **kwargs):
    import hashlib
    names = ("json_syntax","xray_structure","required_parameters","types_values","references_conflicts")
    checks = [{"name":n,"status":"PASS","errors":[],"warnings":[],"details":{}} for n in names]
    checks += [{"name":"compatibility","status":"DEFERRED_TO_NATIVE","errors":[],"warnings":[],"details":{}},
               {"name":"xray_native","status":"PASS","errors":[],"warnings":[],"details":{}}]
    return {"schema_version":1,"created_at":"2026-11-04T18:00:00Z",
      "content_sha256":hashlib.sha256(data).hexdigest(),"content_size_bytes":len(data),
      "checks":checks,"xray":{"version":"Xray test","binary_sha256":"a"*64},"result":"PASS"}
p.validator.validate_configuration = fake
original = v._atomic_write
def crash(path, content, **kwargs):
    result = original(path, content, **kwargs)
    if pathlib.Path(path) == validation / "catalog.json":
        os.kill(os.getpid(), signal.SIGKILL)
    return result
v._atomic_write = crash
service = p.ValidationPromotionService(root, key, validation)
service.validate(sys.argv[6])
'''
        proc = subprocess.run([
            sys.executable, "-c", code, str(self.config_root), str(self.key_path),
            str(self.validation_root), str(ROOT), str(self.source), self.config_id,
        ])
        self.assertEqual(proc.returncode, -signal.SIGKILL)
        with self.configs.locked():
            with self.reports.locked():
                self.service._recover_unlocked()
        self.assertEqual(self.reports.list_reports(), [])
        metadata = self.configs.show(self.config_id)
        self.assertEqual(metadata["validation_status"], "not_validated")
        self.assertFalse(self.service.wal_path.exists())

    def test_prepared_transaction_restores_metadata_after_sigkill(self):
        code = r'''
import os, pathlib, signal, sys
root, key, validation = map(pathlib.Path, sys.argv[1:4])
sys.path.insert(0, sys.argv[4] + "/scripts")
import xray_config_promotion as p
import xray_configurations as c
data = pathlib.Path(sys.argv[5]).read_bytes()
def fake(data, **kwargs):
    import hashlib
    names = ("json_syntax","xray_structure","required_parameters","types_values","references_conflicts")
    checks = [{"name":n,"status":"PASS","errors":[],"warnings":[],"details":{}} for n in names]
    checks += [{"name":"compatibility","status":"DEFERRED_TO_NATIVE","errors":[],"warnings":[],"details":{}},
               {"name":"xray_native","status":"PASS","errors":[],"warnings":[],"details":{}}]
    return {"schema_version":1,"created_at":"2026-11-04T18:00:00Z",
      "content_sha256":hashlib.sha256(data).hexdigest(),"content_size_bytes":len(data),
      "checks":checks,"xray":{"version":"Xray test","binary_sha256":"a"*64},"result":"PASS"}
p.validator.validate_configuration = fake
original = c.atomic_write
def crash(path, content):
    result = original(path, content)
    if pathlib.Path(path).name == "metadata.json":
        os.kill(os.getpid(), signal.SIGKILL)
    return result
c.atomic_write = crash
service = p.ValidationPromotionService(root, key, validation)
service.validate(sys.argv[6])
'''
        proc = subprocess.run([
            sys.executable, "-c", code, str(self.config_root), str(self.key_path),
            str(self.validation_root), str(ROOT), str(self.source), self.config_id,
        ])
        self.assertEqual(proc.returncode, -signal.SIGKILL)
        with self.configs.locked():
            with self.reports.locked():
                self.service._recover_unlocked()
        self.assertEqual(self.reports.list_reports(), [])
        metadata = self.configs.show(self.config_id)
        self.assertEqual(metadata["validation_status"], "not_validated")
        self.assertIsNone(metadata["last_validated_revision"])
        self.assertFalse(self.service.wal_path.exists())

    def test_committed_transaction_finishes_after_sigkill(self):
        code = r'''
import os, pathlib, signal, sys
root, key, validation = map(pathlib.Path, sys.argv[1:4])
sys.path.insert(0, sys.argv[4] + "/scripts")
import xray_config_promotion as p
import xray_validation_store as v
data = pathlib.Path(sys.argv[5]).read_bytes()
def fake(data, **kwargs):
    import hashlib
    names = ("json_syntax","xray_structure","required_parameters","types_values","references_conflicts")
    checks = [{"name":n,"status":"PASS","errors":[],"warnings":[],"details":{}} for n in names]
    checks += [{"name":"compatibility","status":"DEFERRED_TO_NATIVE","errors":[],"warnings":[],"details":{}},
               {"name":"xray_native","status":"PASS","errors":[],"warnings":[],"details":{}}]
    return {"schema_version":1,"created_at":"2026-11-04T18:00:00Z",
      "content_sha256":hashlib.sha256(data).hexdigest(),"content_size_bytes":len(data),
      "checks":checks,"xray":{"version":"Xray test","binary_sha256":"a"*64},"result":"PASS"}
p.validator.validate_configuration = fake
service = p.ValidationPromotionService(root, key, validation)
original = service._write_wal
def crash(journal, **kwargs):
    original(journal, **kwargs)
    if journal["state"] == "committed":
        os.kill(os.getpid(), signal.SIGKILL)
service._write_wal = crash
service.validate(sys.argv[6])
'''
        proc = subprocess.run([
            sys.executable, "-c", code, str(self.config_root), str(self.key_path),
            str(self.validation_root), str(ROOT), str(self.source), self.config_id,
        ])
        self.assertEqual(proc.returncode, -signal.SIGKILL)
        with self.configs.locked():
            with self.reports.locked():
                self.service._recover_unlocked()
        reports = self.reports.list_reports()
        self.assertEqual(len(reports), 1)
        metadata = self.configs.show(self.config_id)
        self.assertEqual(metadata["validation_status"], "valid")
        self.assertEqual(metadata["last_validated_revision"], "r000001")
        self.assertFalse(self.service.wal_path.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
