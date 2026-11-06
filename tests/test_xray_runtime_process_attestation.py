from __future__ import annotations

import pathlib
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import xray_runtime_process_attestation as attestation
import xray_runtime_process_identity as process_identity


class RuntimeProcessAttestationTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = {
            "active_state": "active", "sub_state": "running", "result": "success",
            "exec_main_status": "0", "user": "xray", "group": "xray",
            "main_pid": 4321, "invocation_id": "a" * 32,
            "active_enter_timestamp": "Thu 2026-11-06 10:00:00 -05",
            "fragment_path": "/etc/systemd/system/xray.service",
            "read_only": True,
        }
        self.process = {
            "pid": 4321, "process_starttime_ticks": 98765,
            "executable_path": "/usr/local/bin/xray",
            "executable_sha256": "b" * 64,
            "argv": attestation.EXPECTED_ARGV,
            "effective_uid": 991, "effective_gid": 991,
            "identity_verified": True, "read_only": True,
            "configuration_loaded": False,
            "configuration_evidence": "not_attested",
        }
        self.observations = [dict(self.snapshot), dict(self.snapshot)]

    def observe(self, **kwargs):
        calls = {"index": 0}

        def systemd():
            value = self.observations[calls["index"]]
            calls["index"] += 1
            return dict(value)

        def process(pid, **arguments):
            self.assertEqual(pid, 4321)
            self.assertEqual(arguments["expected_uid"], 991)
            self.assertEqual(arguments["expected_gid"], 991)
            self.assertEqual(arguments["expected_argv"], attestation.EXPECTED_ARGV)
            return dict(self.process)

        with mock.patch.object(attestation.pwd, "getpwnam", return_value=SimpleNamespace(pw_uid=991)), \
                mock.patch.object(attestation.grp, "getgrnam", return_value=SimpleNamespace(gr_gid=991)):
            return attestation.observe_process_identity(
                systemd_observer=systemd, process_observer=process, **kwargs
            )

    def test_correlates_mainpid_process_and_stable_invocation(self):
        result = self.observe()
        self.assertEqual(result["pid"], 4321)
        self.assertEqual(result["systemd_main_pid"], 4321)
        self.assertEqual(result["systemd_invocation_id"], "a" * 32)
        self.assertEqual(result["process_starttime_ticks"], 98765)
        self.assertEqual(result["executable_sha256"], "b" * 64)
        self.assertFalse(result["configuration_loaded"])
        self.assertEqual(result["configuration_evidence"], "not_attested")

    def test_rejects_inactive_service(self):
        self.snapshot["active_state"] = "inactive"
        self.observations = [dict(self.snapshot), dict(self.snapshot)]
        with self.assertRaises(attestation.ProcessAttestationError):
            self.observe()

    def test_rejects_missing_or_invalid_mainpid(self):
        self.snapshot["main_pid"] = 0
        self.observations = [dict(self.snapshot), dict(self.snapshot)]
        with self.assertRaises(attestation.ProcessAttestationError):
            self.observe()

    def test_rejects_invalid_invocation_id(self):
        self.snapshot["invocation_id"] = "invalid"
        self.observations = [dict(self.snapshot), dict(self.snapshot)]
        with self.assertRaises(attestation.ProcessAttestationError):
            self.observe()

    def test_rejects_invalid_active_enter_timestamp(self):
        self.snapshot["active_enter_timestamp"] = "n/a"
        self.observations = [dict(self.snapshot), dict(self.snapshot)]
        with self.assertRaises(attestation.ProcessAttestationError):
            self.observe()

    def test_rejects_mainpid_change_during_inspection(self):
        self.observations[1]["main_pid"] = 4322
        with self.assertRaises(attestation.ProcessAttestationError):
            self.observe()

    def test_rejects_invocation_change_during_inspection(self):
        self.observations[1]["invocation_id"] = "c" * 32
        with self.assertRaises(attestation.ProcessAttestationError):
            self.observe()

    def test_rejects_active_enter_timestamp_change(self):
        self.observations[1]["active_enter_timestamp"] = "Thu 2026-11-06 10:01:00 -05"
        with self.assertRaises(attestation.ProcessAttestationError):
            self.observe()

    def test_rejects_wrong_process_executable(self):
        self.process["executable_path"] = "/bin/false"
        with self.assertRaises(attestation.ProcessAttestationError):
            self.observe()

    def test_rejects_wrong_process_argv(self):
        self.process["argv"] = self.process["argv"] + ("--unexpected",)
        with self.assertRaises(attestation.ProcessAttestationError):
            self.observe()

    def test_rejects_wrong_effective_process_ids(self):
        self.process["effective_uid"] = 0
        with self.assertRaises(attestation.ProcessAttestationError):
            self.observe()

    def test_rejects_process_pid_not_equal_to_mainpid(self):
        self.process["pid"] = 9999
        with self.assertRaises(attestation.ProcessAttestationError):
            self.observe()

    def test_rejects_process_without_identity_evidence(self):
        self.process["identity_verified"] = False
        with self.assertRaises(attestation.ProcessAttestationError):
            self.observe()

    def test_rejects_process_claiming_loaded_configuration(self):
        self.process["configuration_loaded"] = True
        with self.assertRaises(attestation.ProcessAttestationError):
            self.observe()

    def test_rejects_missing_xray_account(self):
        with mock.patch.object(attestation.pwd, "getpwnam", side_effect=KeyError):
            with self.assertRaises(attestation.ProcessAttestationError):
                attestation.observe_process_identity(
                    systemd_observer=lambda: dict(self.snapshot),
                    process_observer=lambda *a, **k: dict(self.process),
                )

    def test_default_observers_are_h6a_and_procfs(self):
        with mock.patch.object(attestation.systemd_adapter, "status",
                               side_effect=[dict(self.snapshot), dict(self.snapshot)]) as systemd, \
                mock.patch.object(attestation.process_identity, "inspect_process",
                                  return_value=dict(self.process)) as process, \
                mock.patch.object(attestation.pwd, "getpwnam", return_value=SimpleNamespace(pw_uid=991)), \
                mock.patch.object(attestation.grp, "getgrnam", return_value=SimpleNamespace(gr_gid=991)):
            result = attestation.observe_process_identity()
        self.assertEqual(systemd.call_count, 2)
        self.assertEqual(process.call_args.args[0], 4321)
        self.assertEqual(process.call_args.kwargs["proc_root"], pathlib.Path("/proc"))
        self.assertTrue(result["identity_verified"])


if __name__ == "__main__":
    unittest.main()
