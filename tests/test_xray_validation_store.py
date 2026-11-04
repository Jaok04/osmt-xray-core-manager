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

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import xray_validation_store as storemod


def sample_report(result="PASS"):
    return {
        "schema_version": 1,
        "created_at": "2026-11-04T18:00:00Z",
        "content_sha256": hashlib.sha256(b'{"inbounds":[],"outbounds":[]}').hexdigest(),
        "content_size_bytes": 29,
        "checks": [
            {"name": "json_syntax", "status": "PASS", "errors": [], "warnings": [], "details": {}},
            {"name": "xray_native", "status": "PASS", "errors": [], "warnings": [], "details": {}},
        ],
        "xray": {"version": "Xray 26.10.31", "binary_sha256": "a" * 64, "binary": "/usr/local/bin/xray"},
        "result": result,
    }


class ValidationStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name) / "validation"
        self.store = storemod.ValidationReportStore(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_save_and_read_report_with_exact_identity(self):
        saved = self.store.save_report("config-" + "1" * 32, "r000001", sample_report())
        self.assertEqual(saved["result"], "PASS")
        self.assertEqual(saved["revision"], "r000001")
        self.assertEqual(saved["config_id"], "config-" + "1" * 32)
        self.assertEqual(self.store.get_report(saved["validation_id"]), saved)
        self.assertEqual(len(self.store.list_reports()), 1)
        path = self.root / "reports" / (saved["validation_id"] + ".json")
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.root.stat().st_mode & 0o777, 0o700)

    def test_reports_are_append_only_and_diagnostics_sanitized(self):
        report = sample_report("PASS_WITH_WARNINGS")
        report["checks"][0]["warnings"] = ["token=supersecret password:abc123"]
        first = self.store.save_report("config-" + "2" * 32, "r000003", report)
        second = self.store.save_report("config-" + "2" * 32, "r000003", report)
        self.assertNotEqual(first["validation_id"], second["validation_id"])
        self.assertEqual(len(self.store.list_reports()), 2)
        warning = self.store.get_report(first["validation_id"])["checks"][0]["warnings"][0]
        self.assertNotIn("supersecret", warning)
        self.assertNotIn("abc123", warning)

    def test_reject_invalid_identity_or_report(self):
        with self.assertRaises(storemod.ValidationStoreError):
            self.store.save_report("invalid", "r000001", sample_report())
        bad = sample_report()
        bad["result"] = "VALIDATED"
        with self.assertRaises(storemod.ValidationStoreError):
            self.store.save_report("config-" + "3" * 32, "r000001", bad)

    def test_tampered_report_is_detected(self):
        saved = self.store.save_report("config-" + "4" * 32, "r000001", sample_report())
        path = self.root / "reports" / (saved["validation_id"] + ".json")
        path.write_text("{}\\n")
        os.chmod(path, 0o600)
        with self.assertRaises(storemod.ValidationStoreError):
            self.store.list_reports()

    def test_symlink_report_directory_rejected(self):
        self.store.prepare()
        reports = self.root / "reports"
        reports.rmdir()
        target = pathlib.Path(self.tmp.name) / "elsewhere"
        target.mkdir(mode=0o700)
        reports.symlink_to(target, target_is_directory=True)
        with self.assertRaises(storemod.ValidationStoreError):
            self.store.list_reports()

    def test_unexpected_report_file_rejected(self):
        self.store.save_report("config-" + "5" * 32, "r000001", sample_report())
        extra = self.root / "reports" / "unexpected.json"
        extra.write_text("{}\\n")
        os.chmod(extra, 0o600)
        with self.assertRaises(storemod.ValidationStoreError):
            self.store.list_reports()

    def test_prepared_wal_rolls_back_after_sigkill(self):
        code = r'''
import os, pathlib, signal, sys
sys.path.insert(0, sys.argv[1] + "/scripts")
import xray_validation_store as m
root = pathlib.Path(sys.argv[2])
original = m._atomic_write
def crash(path, data, **kwargs):
    original(path, data, **kwargs)
    if pathlib.Path(path) == root / "catalog.json":
        os.kill(os.getpid(), signal.SIGKILL)
m._atomic_write = crash
s = m.ValidationReportStore(root)
s.save_report("config-" + "6" * 32, "r000001", {
 "schema_version":1,"created_at":"2026-11-04T18:00:00Z",
 "content_sha256":"b"*64,"content_size_bytes":1,"result":"PASS",
 "checks":[{"name":"json_syntax","status":"PASS","errors":[],"warnings":[],"details":{}}],
 "xray":{}
})
'''
        proc = subprocess.run([sys.executable, "-c", code, str(ROOT), str(self.root)])
        self.assertEqual(proc.returncode, -signal.SIGKILL)
        self.assertTrue((self.root / "transaction.json").exists())
        self.assertEqual(self.store.list_reports(), [])
        self.assertFalse((self.root / "transaction.json").exists())
        self.assertEqual(list((self.root / "reports").iterdir()), [])

    def test_committed_wal_completes_after_sigkill(self):
        code = r'''
import os, pathlib, signal, sys
sys.path.insert(0, sys.argv[1] + "/scripts")
import xray_validation_store as m
root = pathlib.Path(sys.argv[2])
original = pathlib.Path.unlink
def crash(path, *args, **kwargs):
    if pathlib.Path(path) == root / "transaction.json":
        os.kill(os.getpid(), signal.SIGKILL)
    return original(path, *args, **kwargs)
pathlib.Path.unlink = crash
s = m.ValidationReportStore(root)
s.save_report("config-" + "7" * 32, "r000001", {
 "schema_version":1,"created_at":"2026-11-04T18:00:00Z",
 "content_sha256":"c"*64,"content_size_bytes":1,"result":"PASS",
 "checks":[{"name":"json_syntax","status":"PASS","errors":[],"warnings":[],"details":{}}],
 "xray":{}
})
'''
        proc = subprocess.run([sys.executable, "-c", code, str(ROOT), str(self.root)])
        self.assertEqual(proc.returncode, -signal.SIGKILL)
        self.assertTrue((self.root / "transaction.json").exists())
        reports = self.store.list_reports()
        self.assertEqual(len(reports), 1)
        self.assertFalse((self.root / "transaction.json").exists())
        self.assertTrue((self.root / "reports" / (reports[0]["validation_id"] + ".json")).is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
