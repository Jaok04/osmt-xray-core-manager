from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import xray_profiles
from xray_profile_validation_store import ProfileValidationReportStore, ProfileValidationError
import xray_profile_validation_store as profile_validation_store
import xray_runtime_preflight as preflight


CONFIG = json.dumps({
    "log": {"loglevel": "warning"},
    "inbounds": [],
    "outbounds": [{"protocol": "freedom", "tag": "direct"}],
}, sort_keys=True, separators=(",", ":")).encode()
CHECKS = [
    {"name": name, "status": "PASS", "errors": [], "warnings": [], "details": {}}
    for name in ("json_syntax", "xray_structure", "required_parameters",
                 "types_values", "references_conflicts", "xray_native")
]


class RuntimePreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = pathlib.Path(self.tmp.name)
        self.profile_root = self.base / "profiles"
        self.key = self.base / "master.key"
        self.key.write_bytes(b"K" * 32)
        self.key.chmod(0o600)
        self.profiles = xray_profiles.ProfileStore(str(self.profile_root), str(self.key))
        self.created = self.profiles.create("Perfil R01", config_data=CONFIG)
        self.profile_id = self.created["profile_id"]
        self.revision = self.created["current_revision"]
        self.validation_root = self.base / "profile-validations"
        self.reports = ProfileValidationReportStore(self.validation_root)
        self.binary = self.base / "xray-fixture"
        self.binary.write_text("#!/bin/sh\nexit 0\n")
        self.binary.chmod(0o755)
        self.binary_hash = hashlib.sha256(self.binary.read_bytes()).hexdigest()
        self.service_state = self.base / "service-state.json"
        self.write_service_fixture()
        self.mark_revision_valid(self.revision)
        self.save_report(self.revision, CONFIG)

    def tearDown(self):
        self.tmp.cleanup()

    def write_service_fixture(self, **changes):
        value = {
            "unit": "xray.service", "load_state": "loaded",
            "active_state": "inactive", "sub_state": "dead",
            "user": "xray", "group": "xray", "binary_path": str(self.binary),
        }
        value.update(changes)
        self.service_state.write_text(json.dumps(value, sort_keys=True))
        self.service_state.chmod(0o600)

    def mark_revision_valid(self, revision):
        path = self.profile_root / "profiles" / self.profile_id / "revisions" / revision / "manifest.json"
        manifest = json.loads(path.read_text())
        manifest["validation"] = {"json_syntax": "pass", "xray_static": "pass", "status": "valid"}
        path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n")
        path.chmod(0o600)
        metadata_path = self.profile_root / "profiles" / self.profile_id / "metadata.json"
        metadata = json.loads(metadata_path.read_text())
        metadata["last_validated_revision"] = revision
        metadata["validation_status"] = "valid"
        metadata_path.write_text(json.dumps(metadata, sort_keys=True, separators=(",", ":")) + "\n")
        metadata_path.chmod(0o600)

    def save_report(self, revision, data, result="PASS", digest=None, binary_hash=None):
        return self.reports.save_report(self.profile_id, revision, {
            "schema_version": 1,
            "content_sha256": digest or hashlib.sha256(data).hexdigest(),
            "content_size_bytes": len(data),
            "created_at": "2026-11-04T20:00:00Z",
            "validator_version": "test/v1",
            "result": result,
            "checks": CHECKS,
            "xray": {"version": "Xray test fixture", "binary_sha256": binary_hash or self.binary_hash},
        })

    def run_preflight(self, revision=None):
        return preflight.preflight(
            str(self.profile_root), str(self.key), str(self.validation_root),
            self.profile_id, revision or self.revision, str(self.binary), str(self.service_state),
        )


    def test_prepared_report_transaction_recovers_by_rollback(self):
        original = profile_validation_store._atomic_write
        crashed = {"value": False}

        def interrupt(path, data, exclusive=False):
            result = original(path, data, exclusive=exclusive)
            candidate = pathlib.Path(path)
            if candidate.parent == self.reports.reports and candidate.name.startswith("pvalidation-") and not crashed["value"]:
                crashed["value"] = True
                raise OSError("injected interruption after report write")
            return result

        with mock.patch.object(profile_validation_store, "_atomic_write", side_effect=interrupt):
            with self.assertRaises(OSError):
                self.save_report("r000002", CONFIG)
        self.reports.list_reports()  # recuperación explícita en operación de escritura/gestión
        with self.assertRaises(ProfileValidationError):
            self.reports.latest_for_revision(self.profile_id, "r000002")
        self.assertFalse(self.reports.wal.exists())
        remaining = list(self.reports.reports.iterdir())
        self.assertEqual(len(remaining), 1)
        self.assertTrue(remaining[0].name.startswith("pvalidation-"))

    def test_committed_report_transaction_recovers_by_roll_forward(self):
        original = profile_validation_store._atomic_write
        crashed = {"value": False}

        def interrupt(path, data, exclusive=False):
            result = original(path, data, exclusive=exclusive)
            if pathlib.Path(path) == self.reports.wal and not crashed["value"]:
                try:
                    state = json.loads(data).get("state")
                except Exception:
                    state = None
                if state == "committed":
                    crashed["value"] = True
                    raise OSError("injected interruption after committed journal")
            return result

        with mock.patch.object(profile_validation_store, "_atomic_write", side_effect=interrupt):
            with self.assertRaises(OSError):
                self.save_report("r000002", CONFIG)
        self.reports.list_reports()  # recupera el WAL committed antes de lectura pura
        recovered = self.reports.latest_for_revision(self.profile_id, "r000002")
        self.assertEqual(recovered["result"], "PASS")
        self.assertFalse(self.reports.wal.exists())

    def test_valid_profile_revision_passes_without_runtime_side_effects(self):
        result = self.run_preflight()
        self.assertEqual(result["status"], "PREFLIGHT_PASS")
        self.assertEqual(result["profile_id"], self.profile_id)
        self.assertEqual(result["revision"], self.revision)
        self.assertFalse(result["runtime_published"])
        self.assertFalse(result["service_action_performed"])

    def test_historical_revision_remains_selectable_after_current_revision_moves(self):
        updated = self.base / "updated.json"
        updated.write_bytes(CONFIG + b" ")
        result = self.profiles.update(self.profile_id, config_data=updated.read_bytes())
        self.assertEqual(result["current_revision"], "r000002")
        self.mark_revision_valid(self.revision)
        result = self.run_preflight(self.revision)
        self.assertEqual(result["revision"], "r000001")

    def test_missing_report_fails_closed(self):
        self.validation_root = self.base / "empty-validation-store"
        self.reports = ProfileValidationReportStore(self.validation_root)
        with self.assertRaises(preflight.RuntimePreflightError):
            self.run_preflight()

    def test_report_content_hash_mismatch_fails_closed(self):
        self.save_report(self.revision, CONFIG, digest="f" * 64)
        with self.assertRaises(preflight.RuntimePreflightError):
            self.run_preflight()

    def test_report_non_pass_fails_closed(self):
        self.save_report(self.revision, CONFIG, result="FAIL")
        with self.assertRaises(preflight.RuntimePreflightError):
            self.run_preflight()

    def test_report_wrong_binary_fails_closed(self):
        self.save_report(self.revision, CONFIG, binary_hash="a" * 64)
        with self.assertRaises(preflight.RuntimePreflightError):
            self.run_preflight()

    def test_metadata_revision_mismatch_fails_closed(self):
        metadata = self.profiles.load_metadata(self.profile_id)
        metadata["last_validated_revision"] = None
        metadata["validation_status"] = "not_validated"
        self.profiles.save_metadata(self.profile_id, metadata)
        with self.assertRaises(preflight.RuntimePreflightError):
            self.run_preflight()

    def test_manifest_invalid_fails_closed(self):
        path = self.profile_root / "profiles" / self.profile_id / "revisions" / self.revision / "manifest.json"
        manifest = json.loads(path.read_text())
        manifest["validation"]["xray_static"] = "not_run"
        manifest["validation"]["status"] = "pending"
        path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n")
        path.chmod(0o600)
        with self.assertRaises(preflight.RuntimePreflightError):
            self.run_preflight()

    def test_preflight_is_read_only_for_profile_and_report_stores(self):
        paths = [
            self.profile_root / "profiles" / self.profile_id / "metadata.json",
            self.profile_root / "profiles" / self.profile_id / "revisions" / self.revision / "manifest.json",
            self.validation_root / "catalog.json",
        ]
        before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in paths}
        result = self.run_preflight()
        after = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in paths}
        self.assertEqual(result["status"], "PREFLIGHT_PASS")
        self.assertEqual(before, after)

    def test_unknown_service_state_is_valid_evidence_for_r05_fail_closed(self):
        self.write_service_fixture(active_state="unknown", sub_state="unknown")
        result = self.run_preflight()
        self.assertEqual(result["status"], "PREFLIGHT_PASS")
        self.assertEqual(result["service_fixture"]["active_state"], "unknown")

    def test_untyped_service_state_fails_closed(self):
        self.write_service_fixture(active_state=[])
        with self.assertRaises(preflight.RuntimePreflightError):
            self.run_preflight()

    def test_wrong_service_identity_fails_closed(self):
        self.write_service_fixture(user="root")
        with self.assertRaises(preflight.RuntimePreflightError):
            self.run_preflight()

    def test_wrong_service_binary_fails_closed(self):
        self.write_service_fixture(binary_path="/usr/bin/other")
        with self.assertRaises(preflight.RuntimePreflightError):
            self.run_preflight()

    def test_service_fixture_invalid_state_combination_fails_closed(self):
        self.write_service_fixture(active_state="active", sub_state="dead")
        with self.assertRaises(preflight.RuntimePreflightError):
            self.run_preflight()

    def test_symlink_service_fixture_fails_closed(self):
        link = self.base / "service-link.json"
        link.symlink_to(self.service_state)
        with self.assertRaises(preflight.RuntimePreflightError):
            preflight._validate_service_fixture(link, str(self.binary))

    def test_symlink_ancestor_service_fixture_fails_closed(self):
        parent = self.base / "fixture-parent"
        parent.mkdir()
        link_parent = self.base / "fixture-parent-link"
        link_parent.symlink_to(parent, target_is_directory=True)
        linked_file = link_parent / "state.json"
        linked_file.write_bytes(self.service_state.read_bytes())
        linked_file.chmod(0o600)
        with self.assertRaises(preflight.RuntimePreflightError):
            preflight._validate_service_fixture(linked_file, str(self.binary))

    def test_profile_revision_corruption_fails_closed(self):
        blob = self.profile_root / "profiles" / self.profile_id / "revisions" / self.revision / "config.enc.json"
        value = json.loads(blob.read_text())
        value["ciphertext"] = value["ciphertext"][:-4] + "AAAA"
        blob.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")))
        blob.chmod(0o600)
        with self.assertRaises(xray_profiles.ProfileError):
            self.run_preflight()


if __name__ == "__main__":
    unittest.main()
