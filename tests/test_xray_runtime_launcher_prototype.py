from __future__ import annotations

import hashlib
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import xray_runtime_launcher_prototype as launcher
import xray_runtime_config_attestation as attestation


class LauncherPrivilegePrototypeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name) / "fixture"
        self.root.mkdir(mode=0o700)
        pathlib.Path(self.temp.name).chmod(0o711)
        marker = self.root / ".xray-manager-fixture"
        marker.write_text("fixture-only\n")
        marker.chmod(0o600)
        self.root.chmod(0o711)  # traversal permitido; listado/evidencia siguen privados
        self.config = b'{"log":{"loglevel":"warning"},"inbounds":[],"outbounds":[]}\n'
        self.digest = hashlib.sha256(self.config).hexdigest()
        self.invocation = "c" * 32

    def tearDown(self):
        self.temp.cleanup()

    def plan(self):
        return launcher.prepare_fixture_launch(
            fixture_root=self.root, config=self.config,
            expected_sha256=self.digest, invocation_id=self.invocation,
        )

    def test_plan_is_fixture_only_and_descriptor_is_sealed(self):
        plan = self.plan()
        try:
            self.assertEqual(plan["environment"], "fixture")
            self.assertTrue(os.get_inheritable(plan["fd"]))
            self.assertEqual(
                plan["fd_metadata"]["seals"] & attestation.REQUIRED_SEALS,
                attestation.REQUIRED_SEALS,
            )
            self.assertEqual(os.readlink(plan["config_link"]), f"/proc/self/fd/{plan['fd']}")
        finally:
            launcher.close_fixture_plan(plan)

    def test_evidence_is_not_writable_by_service_identity(self):
        if os.geteuid() != 0:
            self.skipTest("requiere root para comprobar separación de propietario")
        plan = self.plan()
        try:
            launched = launcher.run_fixture_xray_validation(
                plan, xray_binary=pathlib.Path("/usr/local/bin/xray"),
            )
            self.assertEqual(launched.returncode, 0, launched.stdout + launched.stderr)
            self.assertEqual(plan["evidence_path"].stat().st_mode & 0o777, 0o600)
            result = subprocess.run(
                ["/usr/bin/setpriv", f"--reuid={plan['service_uid']}",
                 f"--regid={plan['service_gid']}", "--clear-groups", "--",
                 "/usr/bin/test", "-w", str(plan["evidence_path"])],
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
        finally:
            launcher.close_fixture_plan(plan)

    def test_rejects_unmarked_root(self):
        other = pathlib.Path(self.temp.name) / "unmarked"
        other.mkdir()
        with self.assertRaises(launcher.LauncherPrototypeError):
            launcher.prepare_fixture_launch(
                fixture_root=other, config=self.config,
                expected_sha256=self.digest, invocation_id=self.invocation,
            )

    def test_rejects_root_service_identity(self):
        with self.assertRaises(launcher.LauncherPrototypeError):
            launcher.prepare_fixture_launch(
                fixture_root=self.root, config=self.config,
                expected_sha256=self.digest, invocation_id=self.invocation,
                service_user="root", service_group="root",
            )


    def test_rejects_invalid_invocation_id(self):
        with self.assertRaises(launcher.LauncherPrototypeError):
            launcher.prepare_fixture_launch(
                fixture_root=self.root, config=self.config,
                expected_sha256=self.digest, invocation_id="../escape",
            )

    def test_rejects_hash_mismatch(self):
        with self.assertRaises(launcher.LauncherPrototypeError):
            launcher.prepare_fixture_launch(
                fixture_root=self.root, config=self.config,
                expected_sha256="0" * 64, invocation_id=self.invocation,
            )

    def test_xray_reads_sealed_descriptor_after_privilege_drop(self):
        if os.geteuid() != 0:
            self.skipTest("requiere root para probar setpriv con capacidades")
        xray = pathlib.Path("/usr/local/bin/xray")
        setpriv = pathlib.Path("/usr/bin/setpriv")
        if not xray.is_file() or not setpriv.is_file():
            self.skipTest("Xray o setpriv no está instalado en desarrollo")
        plan = self.plan()
        try:
            result = launcher.run_fixture_xray_validation(
                plan, xray_binary=xray, setpriv_binary=setpriv,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertIn("Configuration OK", result.stdout + result.stderr)
            import json
            record = json.loads(plan["evidence_path"].read_text())
            self.assertEqual(record["pid"], plan["target_pid"])
            attested = attestation.verify_invocation_evidence(
                evidence_path=plan["evidence_path"], fixture_root=self.root,
                expected_sha256=self.digest, expected_size=len(self.config),
                main_pid=record["pid"], invocation_id=self.invocation,
            )
            self.assertTrue(attested["verified"])
        finally:
            launcher.close_fixture_plan(plan)


    def test_setpriv_keeps_only_bind_capability_and_no_new_privs(self):
        if os.geteuid() != 0:
            self.skipTest("requiere root para comprobar el descenso de capacidades")
        plan = self.plan()
        try:
            command = [
                "/usr/bin/setpriv", f"--reuid={plan['service_uid']}",
                f"--regid={plan['service_gid']}", "--clear-groups", "--no-new-privs",
                "--bounding-set=-all,+net_bind_service", "--inh-caps=+net_bind_service",
                "--ambient-caps=+net_bind_service", "--", "/bin/sh", "-c",
                "grep -E '^(Uid|Gid|Cap(Inh|Prm|Eff|Bnd|Amb)|NoNewPrivs):' /proc/self/status",
            ]
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            values = dict(line.split(":", 1) for line in result.stdout.splitlines())
            for key in ("CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb"):
                self.assertEqual(values[key].strip(), "0000000000000400")
            self.assertEqual(values["NoNewPrivs"].strip(), "1")
            self.assertIn(str(plan["service_uid"]), values["Uid"])
            self.assertIn(str(plan["service_gid"]), values["Gid"])
        finally:
            launcher.close_fixture_plan(plan)

    def test_rejects_non_fixture_plan(self):
        with self.assertRaises(launcher.LauncherPrototypeError):
            launcher.run_fixture_xray_validation(
                {"environment": "live", "fd": 5},
                xray_binary=pathlib.Path("/usr/local/bin/xray"),
            )


if __name__ == "__main__":
    unittest.main()
