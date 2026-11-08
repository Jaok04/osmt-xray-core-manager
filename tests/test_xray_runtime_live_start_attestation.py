from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import xray_runtime_live_start_attestation as attestation

HASH = "a" * 64


class LiveStartAttestationTests(unittest.TestCase):
    def setUp(self):
        self.publication = {"status": "published", "operation_id": "runtime-op-" + "1" * 32,
                            "config_sha256": HASH, "published_at": "2026-11-08T15:00:00+00:00"}
        self.systemd = {"unit": "xray.service", "load_state": "loaded", "active_state": "active",
                        "sub_state": "running", "result": "success", "exec_main_status": "0",
                        "user": "xray", "group": "xray", "main_pid": 4321,
                        "invocation_id": "b" * 32,
                        "exec_main_start_timestamp": "Sun 2026-11-08 10:00:02 -05",
                        "active_enter_timestamp": "Sun 2026-11-08 10:00:03 -05", "read_only": True}
        self.process = {"pid": 4321, "systemd_main_pid": 4321, "systemd_invocation_id": "b" * 32,
                        "identity_verified": True, "read_only": True, "effective_uid": 991,
                        "effective_gid": 991, "argv": ("/usr/local/bin/xray", "run", "-config", "/etc/xray/config.json"),
                        "executable_path": "/usr/local/bin/xray",
                        "executable_sha256": "c" * 64, "process_starttime_ticks": 12345,
                        "configuration_loaded": False, "configuration_evidence": "not_attested"}

    def run_attestation(self):
        return attestation.attest_start(publication=self.publication, systemd=self.systemd,
                                        process=self.process, config_sha256_before=HASH,
                                        config_sha256_after=HASH)

    def test_correlates_publication_service_and_process_without_claiming_loaded(self):
        result = self.run_attestation()
        self.assertTrue(result["verified"])
        self.assertEqual(result["evidence_level"], "launch_correlated_file_unchanged")
        self.assertFalse(result["configuration_loaded"])
        self.assertEqual(result["configuration_evidence"], "launch_correlated_only")

    def test_rejects_file_hash_drift(self):
        with self.assertRaises(attestation.StartAttestationError):
            attestation.attest_start(publication=self.publication, systemd=self.systemd,
                                     process=self.process, config_sha256_before=HASH,
                                     config_sha256_after="d" * 64)

    def test_rejects_invocation_mismatch(self):
        self.process["systemd_invocation_id"] = "e" * 32
        with self.assertRaises(attestation.StartAttestationError):
            self.run_attestation()

    def test_rejects_start_before_publication(self):
        self.systemd["exec_main_start_timestamp"] = "Sun 2026-11-08 09:59:59 -05"
        with self.assertRaises(attestation.StartAttestationError):
            self.run_attestation()

    def test_rejects_non_active_service(self):
        self.systemd["active_state"] = "failed"
        with self.assertRaises(attestation.StartAttestationError):
            self.run_attestation()

    def test_rejects_process_with_wrong_argv(self):
        self.process["argv"] = ("/usr/local/bin/xray", "run", "-config", "/tmp/other.json")
        with self.assertRaises(attestation.StartAttestationError):
            self.run_attestation()

    def test_never_accepts_claim_that_process_attested_loaded_config(self):
        self.process["configuration_loaded"] = True
        with self.assertRaises(attestation.StartAttestationError):
            self.run_attestation()


if __name__ == "__main__":
    unittest.main()
