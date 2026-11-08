from __future__ import annotations

import json
import os
import pathlib
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import xray_runtime_directory_contract as directories
import xray_runtime_evidence_store as evidence


class RuntimeEvidenceStoreTests(unittest.TestCase):
    def setUp(self):
        if os.geteuid() != 0:
            self.skipTest("los fixtures requieren ownership root y setpriv")
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name) / "fixture"
        self.root.mkdir(mode=0o700)
        pathlib.Path(self.temp.name).chmod(0o711)
        marker = self.root / ".xray-manager-fixture"
        marker.write_text("fixture-only\n", encoding="utf-8")
        marker.chmod(0o600)
        self.root.chmod(0o711)
        self.gid = 65534
        directories.prepare_fixture_layout(self.root, self.gid)
        self.evidence_dir = self.root / "var/lib/xray-manager/evidence"
        self.invocation = "0123456789abcdef0123456789abcdef"
        self.metadata = {
            "pid": 4242,
            "config_sha256": "a" * 64,
            "config_size_bytes": 1234,
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_atomic_creation_and_root_only_metadata(self):
        path = evidence.create_evidence(
            fixture_root=self.root, service_gid=self.gid,
            invocation_id=self.invocation, metadata=self.metadata,
        )
        info = path.lstat()
        self.assertTrue(stat.S_ISREG(info.st_mode))
        self.assertEqual((info.st_uid, info.st_gid), (0, 0))
        self.assertEqual(stat.S_IMODE(info.st_mode), 0o600)
        self.assertEqual(info.st_nlink, 1)
        record = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(record["config_sha256"], "a" * 64)
        self.assertFalse({"config", "config_bytes", "uuid", "password", "pem", "secret"} & set(record))
        self.assertEqual(list(self.evidence_dir.glob(".pending-*.tmp")), [])

    def test_persists_across_fixture_restart_simulation(self):
        evidence.create_evidence(
            fixture_root=self.root, service_gid=self.gid,
            invocation_id=self.invocation, metadata=self.metadata,
        )
        result = evidence.verify_evidence(
            fixture_root=pathlib.Path(str(self.root)), service_gid=self.gid,
            invocation_id=self.invocation,
        )
        self.assertTrue(result["verified"])
        self.assertTrue(result["persistent"])
        self.assertEqual(result["record"]["pid"], 4242)

    def test_service_identity_cannot_traverse_or_read_evidence(self):
        path = evidence.create_evidence(
            fixture_root=self.root, service_gid=self.gid,
            invocation_id=self.invocation, metadata=self.metadata,
        )
        parent = self.root / "var/lib/xray-manager"
        command = [
            "/usr/bin/setpriv", "--reuid=65534", "--regid=65534",
            "--clear-groups", "--", "/bin/sh", "-c",
            '! test -x "$1" && ! test -r "$2" && ! test -w "$2"',
            "sh", str(parent), str(path),
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_duplicate_invocation_without_overwrite(self):
        path = evidence.create_evidence(
            fixture_root=self.root, service_gid=self.gid,
            invocation_id=self.invocation, metadata=self.metadata,
        )
        before = path.read_bytes()
        with self.assertRaises(evidence.EvidenceStoreError):
            evidence.create_evidence(
                fixture_root=self.root, service_gid=self.gid,
                invocation_id=self.invocation, metadata=self.metadata,
            )
        self.assertEqual(path.read_bytes(), before)

    def test_rejects_symlink_at_target(self):
        target = self.evidence_dir / (self.invocation + ".json")
        target.symlink_to("/etc/passwd")
        with self.assertRaises(evidence.EvidenceStoreError):
            evidence.create_evidence(
                fixture_root=self.root, service_gid=self.gid,
                invocation_id=self.invocation, metadata=self.metadata,
            )
        self.assertTrue(target.is_symlink())

    def test_verifier_rejects_hardlink(self):
        path = evidence.create_evidence(
            fixture_root=self.root, service_gid=self.gid,
            invocation_id=self.invocation, metadata=self.metadata,
        )
        os.link(path, self.evidence_dir / "alias.json")
        with self.assertRaises(evidence.EvidenceStoreError):
            evidence.verify_evidence(
                fixture_root=self.root, service_gid=self.gid,
                invocation_id=self.invocation,
            )

    def test_rejects_symlinked_evidence_directory(self):
        evidence_path = self.root / "var/lib/xray-manager/evidence"
        evidence_path.rename(self.root / "var/lib/xray-manager/evidence.real")
        evidence_path.symlink_to(self.root / "var/lib/xray-manager/evidence.real",
                                 target_is_directory=True)
        with self.assertRaises(evidence.EvidenceStoreError):
            evidence.verify_evidence(
                fixture_root=self.root, service_gid=self.gid,
                invocation_id=self.invocation,
            )

    def test_rejects_symlinked_parent_component(self):
        parent = self.root / "var/lib/xray-manager"
        parent.rename(self.root / "var/lib/xray-manager.real")
        parent.symlink_to(self.root / "var/lib/xray-manager.real", target_is_directory=True)
        with self.assertRaises(evidence.EvidenceStoreError):
            evidence.verify_evidence(
                fixture_root=self.root, service_gid=self.gid,
                invocation_id=self.invocation,
            )

    def test_rejects_secret_or_config_fields(self):
        for key in ("config", "config_bytes", "uuid", "password", "private_key", "pem", "secret"):
            payload = dict(self.metadata)
            payload[key] = "must-not-be-stored"
            with self.subTest(key=key), self.assertRaises(evidence.EvidenceStoreError):
                evidence.create_evidence(
                    fixture_root=self.root, service_gid=self.gid,
                    invocation_id=self.invocation, metadata=payload,
                )

    def test_rejects_noncanonical_invocation_ids(self):
        for value in ("../" + self.invocation, self.invocation.upper(), "f" * 31, "g" * 32):
            with self.subTest(value=value), self.assertRaises(evidence.EvidenceStoreError):
                evidence.create_evidence(
                    fixture_root=self.root, service_gid=self.gid,
                    invocation_id=value, metadata=self.metadata,
                )

    def test_cleans_temporary_file_after_publication_failure(self):
        with mock.patch.object(evidence.os, "link", side_effect=OSError("injected link failure")):
            with self.assertRaises(evidence.EvidenceStoreError):
                evidence.create_evidence(
                    fixture_root=self.root, service_gid=self.gid,
                    invocation_id=self.invocation, metadata=self.metadata,
                )
        self.assertEqual(list(self.evidence_dir.iterdir()), [])

    def test_rejects_corrupted_json_after_persistence(self):
        path = evidence.create_evidence(
            fixture_root=self.root, service_gid=self.gid,
            invocation_id=self.invocation, metadata=self.metadata,
        )
        path.write_text("{broken", encoding="utf-8")
        with self.assertRaises(evidence.EvidenceStoreError):
            evidence.verify_evidence(
                fixture_root=self.root, service_gid=self.gid,
                invocation_id=self.invocation,
            )

    def _root_fd(self):
        return os.open(self.root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))

    def test_fd_api_creates_and_verifies_persistent_record(self):
        root_fd = self._root_fd()
        try:
            name = evidence.create_evidence_from_root_fd(
                fixture_root_fd=root_fd, service_gid=self.gid,
                invocation_id=self.invocation, metadata=self.metadata)
            self.assertEqual(name, self.invocation + ".json")
            result = evidence.verify_evidence_from_root_fd(
                fixture_root_fd=root_fd, service_gid=self.gid, invocation_id=self.invocation)
            self.assertTrue(result["verified"])
            self.assertEqual(result["record"]["evidence_status"], "prepared_before_exec")
        finally:
            os.close(root_fd)

    def test_fd_api_remains_anchored_after_root_path_replacement(self):
        root_fd = self._root_fd()
        moved = self.root.with_name("fixture-original")
        try:
            self.root.rename(moved)
            self.root.mkdir(mode=0o711)
            marker = self.root / ".xray-manager-fixture"
            marker.write_text("fixture-only\n", encoding="utf-8")
            marker.chmod(0o600)
            self.root.chmod(0o711)
            directories.prepare_fixture_layout(self.root, self.gid)
            evidence.create_evidence_from_root_fd(
                fixture_root_fd=root_fd, service_gid=self.gid,
                invocation_id=self.invocation, metadata=self.metadata)
            self.assertTrue((moved / "var/lib/xray-manager/evidence" / (self.invocation + ".json")).is_file())
            self.assertFalse((self.root / "var/lib/xray-manager/evidence" / (self.invocation + ".json")).exists())
            self.assertTrue(evidence.verify_evidence_from_root_fd(
                fixture_root_fd=root_fd, service_gid=self.gid, invocation_id=self.invocation)["verified"])
        finally:
            os.close(root_fd)

    def test_fd_api_rejects_closed_descriptor(self):
        root_fd = self._root_fd()
        os.close(root_fd)
        with self.assertRaises(evidence.EvidenceStoreError):
            evidence.verify_evidence_from_root_fd(
                fixture_root_fd=root_fd, service_gid=self.gid, invocation_id=self.invocation)

    def test_fd_api_rejects_layout_mode_drift(self):
        target = self.root / "var/lib/xray-manager/evidence"
        target.chmod(0o710)
        root_fd = self._root_fd()
        try:
            with self.assertRaises(evidence.EvidenceStoreError):
                evidence.verify_evidence_from_root_fd(
                    fixture_root_fd=root_fd, service_gid=self.gid, invocation_id=self.invocation)
        finally:
            os.close(root_fd)

    def test_fd_api_rejects_duplicate_invocation(self):
        root_fd = self._root_fd()
        try:
            evidence.create_evidence_from_root_fd(
                fixture_root_fd=root_fd, service_gid=self.gid,
                invocation_id=self.invocation, metadata=self.metadata)
            with self.assertRaises(evidence.EvidenceStoreError):
                evidence.create_evidence_from_root_fd(
                    fixture_root_fd=root_fd, service_gid=self.gid,
                    invocation_id=self.invocation, metadata=self.metadata)
        finally:
            os.close(root_fd)

    def test_fd_api_rejects_symlinked_layout_component(self):
        target = self.root / "var/lib/xray-manager/evidence"
        target.rename(target.with_name("evidence.real"))
        target.symlink_to(target.with_name("evidence.real"), target_is_directory=True)
        root_fd = self._root_fd()
        try:
            with self.assertRaises(evidence.EvidenceStoreError):
                evidence.verify_evidence_from_root_fd(
                    fixture_root_fd=root_fd, service_gid=self.gid, invocation_id=self.invocation)
        finally:
            os.close(root_fd)


if __name__ == "__main__":
    unittest.main()
