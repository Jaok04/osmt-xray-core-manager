from __future__ import annotations

import hashlib
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import xray_runtime_systemd_adapter as adapter


class RuntimeSystemdReadOnlyAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = pathlib.Path(self.tmp.name)
        self.unit_file = self.base / "etc/systemd/system/xray.service"
        self.config_file = self.base / "etc/xray/config.json"
        self.unit_file.parent.mkdir(parents=True)
        self.config_file.parent.mkdir(parents=True)
        self.unit_file.write_text(
            "[Unit]\nDescription=Xray-core Service\n"
            "[Service]\nUser=xray\nGroup=xray\n"
            "ExecStartPre=/usr/local/bin/xray run -test -config /etc/xray/config.json\n"
            "ExecStart=/usr/local/bin/xray run -config /etc/xray/config.json\n"
            "NoNewPrivileges=true\nProtectSystem=strict\n",
            encoding="utf-8",
        )
        self.unit_file.chmod(0o644)
        self.config_file.write_text('{"log":{"loglevel":"warning"}}\n', encoding="utf-8")
        self.config_file.chmod(0o640)
        self.values = {
            "LoadState": "loaded",
            "ActiveState": "active",
            "SubState": "running",
            "Result": "success",
            "ExecMainStatus": "0",
            "MainPID": "1234",
            "ExecMainStartTimestamp": "Thu 2026-11-05 18:00:00 -05",
            "ActiveEnterTimestamp": "Thu 2026-11-05 18:00:00 -05",
            "InvocationID": "a" * 32,
            "FragmentPath": str(self.unit_file),
            "User": "xray",
            "Group": "xray",
            "UnitFileState": "disabled",
        }

    def tearDown(self):
        self.tmp.cleanup()

    def observe(self):
        with mock.patch.object(adapter, "_systemctl_show", return_value=dict(self.values)):
            return adapter.status(unit_file=self.unit_file, config_file=self.config_file)

    def test_status_is_read_only_and_does_not_infer_generation(self):
        value = self.observe()
        self.assertEqual(value["active_state"], "active")
        self.assertEqual(value["main_pid"], 1234)
        self.assertEqual(value["invocation_id"], "a" * 32)
        self.assertEqual(value["runtime_config_sha256"],
                         hashlib.sha256(self.config_file.read_bytes()).hexdigest())
        self.assertIsNone(value["loaded_generation_id"])
        self.assertIsNone(value["loaded_config_sha256"])
        self.assertEqual(value["generation_evidence"], "not_attested")
        self.assertTrue(value["read_only"])

    def test_missing_config_is_reported_without_failing_service_observation(self):
        self.config_file.unlink()
        value = self.observe()
        self.assertIsNone(value["runtime_config_sha256"])

    def test_rejects_unmanaged_unit_content(self):
        self.unit_file.write_text("[Unit]\n[Service]\nExecStart=/bin/false\n")
        with self.assertRaises(adapter.SystemdAdapterError):
            self.observe()

    def test_rejects_unit_symlink(self):
        target = self.base / "other.service"
        target.write_text(self.unit_file.read_text())
        self.unit_file.unlink()
        self.unit_file.symlink_to(target)
        with self.assertRaises(adapter.SystemdAdapterError):
            self.observe()

    def test_rejects_insecure_unit_permissions(self):
        self.unit_file.chmod(0o666)
        with self.assertRaises(adapter.SystemdAdapterError):
            self.observe()

    def test_rejects_wrong_fragment_path(self):
        self.values["FragmentPath"] = "/run/systemd/generator/xray.service"
        with self.assertRaises(adapter.SystemdAdapterError):
            self.observe()

    def test_rejects_wrong_service_identity(self):
        self.values["User"] = "root"
        with self.assertRaises(adapter.SystemdAdapterError):
            self.observe()

    def test_rejects_invalid_invocation_id(self):
        self.values["InvocationID"] = "not-an-id"
        with self.assertRaises(adapter.SystemdAdapterError):
            self.observe()

    def test_rejects_invalid_pid(self):
        self.values["MainPID"] = "12x"
        with self.assertRaises(adapter.SystemdAdapterError):
            self.observe()

    def test_rejects_symlinked_config(self):
        target = self.base / "elsewhere.json"
        target.write_text("{}")
        target.chmod(0o640)
        self.config_file.unlink()
        self.config_file.symlink_to(target)
        with self.assertRaises(adapter.SystemdAdapterError):
            self.observe()

    def test_rejects_config_hardlink(self):
        target = self.base / "other.json"
        target.write_text("{}")
        target.chmod(0o640)
        self.config_file.unlink()
        self.config_file.hardlink_to(target)
        with self.assertRaises(adapter.SystemdAdapterError):
            self.observe()


if __name__ == "__main__":
    unittest.main()
