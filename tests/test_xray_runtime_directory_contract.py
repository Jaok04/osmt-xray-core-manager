from __future__ import annotations

import os
import pathlib
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import xray_runtime_directory_contract as contract


class RuntimeDirectoryContractTests(unittest.TestCase):
    def setUp(self):
        if os.geteuid() != 0:
            self.skipTest("los fixtures comprueban ownership root y grupo de servicio")
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name) / "fixture"
        self.root.mkdir(mode=0o700)
        pathlib.Path(self.temp.name).chmod(0o711)
        marker = self.root / ".xray-manager-fixture"
        marker.write_text("fixture-only\n", encoding="utf-8")
        marker.chmod(0o600)
        self.root.chmod(0o711)
        self.gid = 65534

    def tearDown(self):
        self.temp.cleanup()

    def test_contract_separates_service_writable_and_root_only_paths(self):
        value = contract.build_directory_contract(self.gid)
        by_path = {item["path"]: item for item in value["directories"]}
        self.assertEqual(value["systemd"]["User"], "root")
        self.assertEqual(value["systemd"]["Group"], "xray")
        self.assertEqual(value["systemd"]["ProtectSystem"], "strict")
        self.assertEqual(value["systemd"]["NoNewPrivileges"], "true")
        self.assertEqual(by_path[contract.STATE_DIRECTORY]["owner_gid"], self.gid)
        self.assertEqual(by_path[contract.STATE_DIRECTORY]["mode"], 0o770)
        self.assertEqual(by_path[contract.RUNTIME_DIRECTORY]["mode"], 0o770)
        self.assertEqual(by_path[contract.EVIDENCE_DIRECTORY]["owner_gid"], 0)
        self.assertEqual(by_path[contract.EVIDENCE_DIRECTORY]["mode"], 0o700)
        self.assertEqual(value["evidence_file"]["mode"], 0o600)
        self.assertEqual(value["systemd"]["ReadWritePaths"], [
            contract.STATE_DIRECTORY, contract.RUNTIME_DIRECTORY,
            contract.EVIDENCE_DIRECTORY,
        ])

    def test_prepare_and_validate_layout(self):
        result = contract.prepare_fixture_layout(self.root, self.gid)
        self.assertTrue(result["valid"])
        self.assertEqual(result["checked_directories"], 4)
        for item in contract.build_directory_contract(self.gid)["directories"]:
            path = self.root.joinpath(*pathlib.PurePosixPath(item["path"]).parts[1:])
            info = path.stat()
            self.assertEqual((info.st_uid, info.st_gid),
                             (item["owner_uid"], item["owner_gid"]))
            self.assertEqual(stat.S_IMODE(info.st_mode), item["mode"])

    def test_service_identity_can_write_state_runtime_but_not_evidence(self):
        contract.prepare_fixture_layout(self.root, self.gid)
        state = self.root / "var/lib/xray"
        runtime = self.root / "run/xray"
        evidence = self.root / "var/lib/xray-manager/evidence"
        command = [
            "/usr/bin/setpriv", "--reuid=65534", "--regid=65534",
            "--clear-groups", "--", "/bin/sh", "-c",
            'test -w "$1" && test -w "$2" && ! test -r "$3" && ! test -w "$3"',
            "sh", str(state), str(runtime), str(evidence),
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_prepare_is_idempotent_without_repairing_drift(self):
        contract.prepare_fixture_layout(self.root, self.gid)
        contract.prepare_fixture_layout(self.root, self.gid)
        evidence = self.root / "var/lib/xray-manager/evidence"
        evidence.chmod(0o750)
        with self.assertRaises(contract.DirectoryContractError):
            contract.prepare_fixture_layout(self.root, self.gid)

    def test_rejects_symlink_component(self):
        parent = self.root / "var"
        parent.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(contract.DirectoryContractError):
            contract.prepare_fixture_layout(self.root, self.gid)

    def test_rejects_unmarked_root(self):
        other = pathlib.Path(self.temp.name) / "unmarked"
        other.mkdir()
        with self.assertRaises(contract.DirectoryContractError):
            contract.prepare_fixture_layout(other, self.gid)

    def test_rejects_invalid_service_gid(self):
        for gid in (0, -1, True, "65534", None):
            with self.subTest(gid=gid), self.assertRaises(contract.DirectoryContractError):
                contract.build_directory_contract(gid)

    def test_rejects_writable_untrusted_parent(self):
        contract.prepare_fixture_layout(self.root, self.gid)
        parent = self.root / "var/lib"
        parent.chmod(0o777)
        with self.assertRaises(contract.DirectoryContractError):
            contract.validate_fixture_layout(self.root, self.gid)
        with self.assertRaises(contract.DirectoryContractError):
            contract.prepare_fixture_layout(self.root, self.gid)
        self.assertEqual(stat.S_IMODE((self.root / "var/lib/xray-manager/evidence").stat().st_mode), 0o700)

        other = pathlib.Path(self.temp.name) / "unsafe-parent-fixture"
        other.mkdir(mode=0o700)
        marker = other / ".xray-manager-fixture"
        marker.write_text("fixture-only\n", encoding="utf-8")
        marker.chmod(0o600)
        other.chmod(0o711)
        (other / "var").mkdir(mode=0o777)
        (other / "var").chmod(0o777)
        with self.assertRaises(contract.DirectoryContractError):
            contract.prepare_fixture_layout(other, self.gid)
        self.assertFalse((other / "var/lib/xray").exists())

    def test_rejects_owner_mode_or_type_drift(self):
        contract.prepare_fixture_layout(self.root, self.gid)
        state = self.root / "var/lib/xray"
        state.chmod(0o750)
        with self.assertRaises(contract.DirectoryContractError):
            contract.validate_fixture_layout(self.root, self.gid)


if __name__ == "__main__":
    unittest.main()
