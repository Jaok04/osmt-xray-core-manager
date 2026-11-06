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
        self.config_gid = self.config_file.stat().st_gid
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
            "NeedDaemonReload": "no",
            "DropInPaths": "",
            "Type": "simple",
            "ExecStartPre": "{ path=/usr/local/bin/xray ; argv[]=/usr/local/bin/xray run -test -config /etc/xray/config.json ; }",
            "ExecStart": "{ path=/usr/local/bin/xray ; argv[]=/usr/local/bin/xray run -config /etc/xray/config.json ; }",
        }

    def tearDown(self):
        self.tmp.cleanup()

    def observe(self):
        group = mock.Mock(gr_gid=self.config_gid)
        with mock.patch.object(adapter, "_systemctl_show", return_value=dict(self.values)), \
                mock.patch.object(adapter.grp, "getgrnam", return_value=group):
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

    def test_observation_includes_effective_unit_contract(self):
        value = self.observe()
        self.assertEqual(value["need_daemon_reload"], "no")
        self.assertEqual(value["drop_in_paths"], "")
        self.assertEqual(value["service_type"], "simple")

    def test_rejects_pending_daemon_reload(self):
        self.values["NeedDaemonReload"] = "yes"
        with self.assertRaises(adapter.SystemdAdapterError):
            self.observe()

    def test_rejects_drop_in_override(self):
        self.values["DropInPaths"] = "/etc/systemd/system/xray.service.d/override.conf"
        with self.assertRaises(adapter.SystemdAdapterError):
            self.observe()

    def test_rejects_wrong_effective_execstart(self):
        self.values["ExecStart"] = "{ path=/bin/false ; argv[]=/bin/false ; }"
        with self.assertRaises(adapter.SystemdAdapterError):
            self.observe()

    def test_rejects_wrong_effective_execstartpre(self):
        self.values["ExecStartPre"] = "{ path=/bin/true ; argv[]=/bin/true ; }"
        with self.assertRaises(adapter.SystemdAdapterError):
            self.observe()

    def test_rejects_unexpected_execstart_arguments(self):
        self.values["ExecStart"] = (
            "{ path=/usr/local/bin/xray ; argv[]=/usr/local/bin/xray run "
            "-config /etc/xray/config.json -confdir /tmp/extra ; }"
        )
        with self.assertRaises(adapter.SystemdAdapterError):
            self.observe()

    def test_rejects_non_simple_service_type(self):
        self.values["Type"] = "notify"
        with self.assertRaises(adapter.SystemdAdapterError):
            self.observe()

    def test_rejects_config_with_wrong_group(self):
        group = mock.Mock(gr_gid=self.config_gid + 1)
        with mock.patch.object(adapter, "_systemctl_show", return_value=dict(self.values)), \
                mock.patch.object(adapter.grp, "getgrnam", return_value=group):
            with self.assertRaises(adapter.SystemdAdapterError):
                adapter.status(unit_file=self.unit_file, config_file=self.config_file)

    def test_systemctl_query_requests_effective_unit_properties(self):
        values = [
            "loaded", "active", "running", "success", "0", "1234",
            "Thu 2026-11-05 18:00:00 -05", "Thu 2026-11-05 18:00:00 -05",
            "a" * 32, str(self.unit_file), "xray", "xray", "disabled",
            "no", "", "simple",
            "{ path=/usr/local/bin/xray ; argv[]=/usr/local/bin/xray run -test -config /etc/xray/config.json ; }",
            "{ path=/usr/local/bin/xray ; argv[]=/usr/local/bin/xray run -config /etc/xray/config.json ; }",
        ]
        completed = mock.Mock(returncode=0, stdout="\n".join(values) + "\n")
        with mock.patch.object(adapter.subprocess, "run", return_value=completed) as run:
            result = adapter._systemctl_show()
        self.assertEqual(result["NeedDaemonReload"], "no")
        self.assertEqual(result["DropInPaths"], "")
        self.assertEqual(result["Type"], "simple")
        self.assertEqual(result["ExecStart"].split()[1], "path=/usr/local/bin/xray")
        command = run.call_args.args[0]
        self.assertIn("NeedDaemonReload", command[3])
        self.assertIn("ExecStart", command[3])
        self.assertNotIn("shell", command)


if __name__ == "__main__":
    unittest.main()
