from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import xray_config_validator
import xray_profiles
from xray_profile_validation import ProfileValidationService
from xray_profile_validation_store import ProfileValidationReportStore
import xray_runtime_preflight as runtime_preflight


VALID_CONFIG = json.dumps({
    "inbounds": [{
        "tag": "socks-in", "listen": "127.0.0.1", "port": 10808,
        "protocol": "socks", "settings": {}
    }],
    "outbounds": [{"tag": "direct", "protocol": "freedom", "settings": {}}],
}, separators=(",", ":")).encode()

INVALID_CONFIG = json.dumps({
    "inbounds": [],
    "outbounds": [],
}, separators=(",", ":")).encode()


class ProfileValidationIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = pathlib.Path(self.tmp.name)
        self.profile_root = self.base / "profiles"
        self.validation_root = self.base / "profile-validations"
        self.key = self.base / "master.key"
        self.key.write_bytes(b"P" * 32)
        self.key.chmod(0o600)
        self.profiles = xray_profiles.ProfileStore(str(self.profile_root), str(self.key))
        created = self.profiles.create("Perfil validación", config_data=VALID_CONFIG)
        self.profile_id = created["profile_id"]
        self.revision = created["current_revision"]
        self.binary = self.base / "xray-fixture"
        self.binary.write_text(
            "#!/bin/sh\n"
            "if [ \"$1\" = version ]; then printf 'Xray fixture-1\\n'; exit 0; fi\n"
            "if [ \"$1\" = run ] && [ \"$2\" = -test ]; then exit 0; fi\n"
            "exit 1\n"
        )
        self.binary.chmod(0o755)
        self.service_state = self.base / "service-state.json"
        self.write_service_fixture()
        self.service = ProfileValidationService(
            str(self.profile_root), str(self.key), str(self.validation_root)
        )
        self.reports = ProfileValidationReportStore(self.validation_root)

    def tearDown(self):
        self.tmp.cleanup()

    def write_service_fixture(self):
        self.service_state.write_text(json.dumps({
            "unit": "xray.service",
            "load_state": "loaded",
            "active_state": "inactive",
            "sub_state": "dead",
            "user": "xray",
            "group": "xray",
            "binary_path": str(self.binary),
        }, sort_keys=True))
        self.service_state.chmod(0o600)

    def run_preflight(self, revision=None):
        return runtime_preflight.preflight(
            str(self.profile_root), str(self.key), str(self.validation_root),
            self.profile_id, revision or self.revision,
            str(self.binary), str(self.service_state),
        )

    def test_pass_persists_profile_bound_report_and_preflight_accepts(self):
        result = self.service.validate(self.profile_id, self.revision, str(self.binary))
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["validation_status"], "valid")
        self.assertTrue(result["report_persisted"])
        self.assertFalse(result["configuration_applied"])
        self.assertFalse(result["service_started"])
        report = self.reports.get_report(result["validation_id"])
        self.assertEqual(report["profile_id"], self.profile_id)
        self.assertEqual(report["revision"], self.revision)
        self.assertEqual(report["content_sha256"], hashlib.sha256(VALID_CONFIG).hexdigest())
        self.assertEqual(self.run_preflight()["status"], "PREFLIGHT_PASS")

    def test_pass_with_warnings_remains_preflight_eligible(self):
        original = xray_config_validator.validate_configuration

        def warning(data, **kwargs):
            report = original(data, **kwargs)
            report["checks"][0]["warnings"] = ["aviso de compatibilidad documentado"]
            report["result"] = "PASS_WITH_WARNINGS"
            return report

        with mock.patch.object(xray_config_validator, "validate_configuration", side_effect=warning):
            result = self.service.validate(self.profile_id, self.revision, str(self.binary))
        self.assertEqual(result["result"], "PASS_WITH_WARNINGS")
        self.assertEqual(self.run_preflight()["status"], "PREFLIGHT_PASS")

    def test_historical_revision_can_be_validated_after_current_moves(self):
        updated = self.profiles.update(self.profile_id, config_data=VALID_CONFIG + b" ")
        new_revision = updated["current_revision"]
        self.assertEqual(new_revision, "r000002")
        result = self.service.validate(self.profile_id, self.revision, str(self.binary))
        self.assertEqual(result["current_revision"], new_revision)
        self.assertFalse(result["selected_revision_is_current"])
        self.assertIsNone(result["last_validated_revision"])
        self.assertEqual(result["profile_validation_status"], "not_validated")
        self.assertEqual(self.run_preflight(self.revision)["status"], "PREFLIGHT_PASS")

    def test_update_after_validation_resets_current_summary_but_keeps_old_revision_valid(self):
        self.service.validate(self.profile_id, self.revision, str(self.binary))
        updated = self.profiles.update(self.profile_id, config_data=VALID_CONFIG + b" ")
        current = updated["current_revision"]
        metadata = self.profiles.load_metadata(self.profile_id)
        self.assertEqual(metadata["validation_status"], "not_validated")
        self.assertIsNone(metadata["last_validated_revision"])
        self.assertEqual(self.run_preflight(self.revision)["status"], "PREFLIGHT_PASS")
        with self.assertRaises(runtime_preflight.RuntimePreflightError):
            self.run_preflight(current)

    def test_restore_after_validation_clears_current_validation_pointer(self):
        self.service.validate(self.profile_id, self.revision, str(self.binary))
        restored = self.profiles.restore(self.profile_id, self.revision)
        metadata = self.profiles.load_metadata(self.profile_id)
        self.assertEqual(metadata["current_revision"], restored["current_revision"])
        self.assertEqual(metadata["validation_status"], "not_validated")
        self.assertIsNone(metadata["last_validated_revision"])
        self.assertEqual(self.run_preflight(self.revision)["status"], "PREFLIGHT_PASS")

    def test_static_failure_persists_invalid_state_and_preflight_rejects(self):
        updated = self.profiles.update(self.profile_id, config_data=INVALID_CONFIG)
        revision = updated["current_revision"]
        result = self.service.validate(self.profile_id, revision, str(self.binary))
        self.assertEqual(result["result"], "FAIL")
        self.assertEqual(result["validation_status"], "invalid")
        report = self.reports.get_report(result["validation_id"])
        self.assertEqual(report["result"], "FAIL")
        with self.assertRaises(runtime_preflight.RuntimePreflightError):
            self.run_preflight(revision)

    def test_native_unavailable_persists_incomplete_pending_state(self):
        result = self.service.validate(
            self.profile_id, self.revision, str(self.base / "missing-xray")
        )
        self.assertEqual(result["result"], "INCOMPLETE")
        self.assertEqual(result["validation_status"], "pending")
        self.assertIsNone(result["last_validated_revision"])
        with self.assertRaises(runtime_preflight.RuntimePreflightError):
            self.run_preflight()

    def test_manifest_metadata_transaction_rolls_back_as_one_unit(self):
        manifest_path = self.profile_root / "profiles" / self.profile_id / "revisions" / self.revision / "manifest.json"
        metadata_path = self.profile_root / "profiles" / self.profile_id / "metadata.json"
        before_manifest = manifest_path.read_bytes()
        before_metadata = metadata_path.read_bytes()
        original = xray_profiles.atomic_write
        failed = {"once": False}

        def interrupt(path, data):
            if pathlib.Path(path) == metadata_path and not failed["once"]:
                failed["once"] = True
                raise OSError("injected failure after manifest update")
            return original(path, data)

        with mock.patch.object(xray_profiles, "atomic_write", side_effect=interrupt):
            with self.assertRaises(OSError):
                self.service.validate(self.profile_id, self.revision, str(self.binary))
        self.assertEqual(manifest_path.read_bytes(), before_manifest)
        self.assertEqual(metadata_path.read_bytes(), before_metadata)
        self.assertFalse(self.profiles.transaction_path.exists())
        self.assertEqual(len(self.reports.list_reports()), 1)
        with self.assertRaises(runtime_preflight.RuntimePreflightError):
            self.run_preflight()

    def test_report_without_profile_state_commit_is_not_preflight_eligible(self):
        with mock.patch.object(self.service.profiles, "commit_transaction", side_effect=OSError("simulated transaction failure")):
            with self.assertRaises(OSError):
                self.service.validate(self.profile_id, self.revision, str(self.binary))
        reports = self.reports.list_reports()
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]["result"], "PASS")
        with self.assertRaises(runtime_preflight.RuntimePreflightError):
            self.run_preflight()

    def test_validation_refuses_profile_revision_changed_before_commit(self):
        original = xray_config_validator.validate_configuration

        def advance_revision(data, **kwargs):
            result = original(data, **kwargs)
            self.profiles.update(self.profile_id, config_data=VALID_CONFIG + b" ")
            return result

        with mock.patch.object(xray_config_validator, "validate_configuration", side_effect=advance_revision):
            result = self.service.validate(self.profile_id, self.revision, str(self.binary))
        self.assertEqual(result["result"], "PASS")
        self.assertFalse(result["selected_revision_is_current"])
        self.assertEqual(self.run_preflight(self.revision)["status"], "PREFLIGHT_PASS")


if __name__ == "__main__":
    unittest.main()
