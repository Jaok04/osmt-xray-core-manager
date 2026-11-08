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
import xray_runtime_supervisor_evidence as supervisor_evidence
import xray_runtime_evidence_store as evidence_store


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

    def test_memfd_is_service_owned_and_read_only(self):
        import pwd
        import grp
        import stat
        plan = self.plan()
        try:
            info = os.fstat(plan["fd"])
            account = pwd.getpwnam("nobody")
            group = grp.getgrnam("nogroup")
            self.assertEqual((info.st_uid, info.st_gid), (account.pw_uid, group.gr_gid))
            self.assertEqual(stat.S_IMODE(info.st_mode), 0o400)
            self.assertEqual(plan["fd_metadata"]["mode"], 0o400)
            self.assertEqual(plan["fd_metadata"]["owner_uid"], account.pw_uid)
            self.assertEqual(plan["fd_metadata"]["owner_gid"], group.gr_gid)
        finally:
            launcher.close_fixture_plan(plan)

    def test_rejects_memfd_mode_tampering(self):
        plan = self.plan()
        try:
            os.fchmod(plan["fd"], 0o444)
            with self.assertRaises(launcher.LauncherPrototypeError):
                launcher.run_fixture_xray_validation(
                    plan, xray_binary=pathlib.Path("/usr/local/bin/xray"))
        finally:
            launcher.close_fixture_plan(plan)

    def test_rejects_memfd_owner_tampering(self):
        if os.geteuid() != 0:
            self.skipTest("requiere root para cambiar el propietario del memfd")
        plan = self.plan()
        try:
            os.fchown(plan["fd"], 0, 0)
            with self.assertRaises(launcher.LauncherPrototypeError):
                launcher.run_fixture_xray_validation(
                    plan, xray_binary=pathlib.Path("/usr/local/bin/xray"))
        finally:
            launcher.close_fixture_plan(plan)

    def test_limited_supervisor_capabilities_prepare_private_memfd(self):
        if os.geteuid() != 0:
            self.skipTest("requiere root para simular las capacidades del supervisor")
        code = (
            "import os,pwd,grp,stat; "
            "p=pwd.getpwnam('nobody'); g=grp.getgrnam('nogroup'); "
            "fd=os.memfd_create('b42-limited-supervisor',os.MFD_ALLOW_SEALING); "
            "os.write(fd,b'fixture'); os.fchmod(fd,0o400); "
            "os.fchown(fd,p.pw_uid,g.gr_gid); "
            "import fcntl; fcntl.fcntl(fd,fcntl.F_ADD_SEALS,15); s=os.fstat(fd); "
            "d=dict(x.split(':',1) for x in open('/proc/self/status') if ':' in x); "
            "assert (s.st_uid,s.st_gid,stat.S_IMODE(s.st_mode))==(p.pw_uid,g.gr_gid,0o400); "
            "assert d['CapEff'].strip()=='00000000000004c1'; "
            "assert d['NoNewPrivs'].strip()=='1'; print('B4.2 restricted supervisor PASS')"
        )
        result = subprocess.run([
            "/usr/bin/setpriv", "--no-new-privs",
            "--bounding-set=-all,+chown,+setuid,+setgid,+net_bind_service",
            "--inh-caps=+chown,+setuid,+setgid,+net_bind_service",
            "--ambient-caps=+chown,+setuid,+setgid,+net_bind_service",
            "--", "/usr/bin/python3", "-c", code,
        ], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("B4.2 restricted supervisor PASS", result.stdout)

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


    def _fake_executable(self, name, body):
        path = self.root / name
        path.write_text("#!/bin/sh\n" + body + "\n")
        path.chmod(0o755)
        return path

    def test_rejects_service_uid_tampering_after_plan_creation(self):
        plan = self.plan()
        try:
            plan["service_uid"] = 0
            with self.assertRaises(launcher.LauncherPrototypeError):
                launcher.run_fixture_xray_validation(
                    plan, xray_binary=pathlib.Path("/usr/local/bin/xray"))
        finally:
            launcher.close_fixture_plan(plan)

    def test_rejects_service_gid_tampering_after_plan_creation(self):
        plan = self.plan()
        try:
            plan["service_gid"] = 0
            with self.assertRaises(launcher.LauncherPrototypeError):
                launcher.run_fixture_xray_validation(
                    plan, xray_binary=pathlib.Path("/usr/local/bin/xray"))
        finally:
            launcher.close_fixture_plan(plan)

    def test_rejects_descriptor_content_or_metadata_tampering(self):
        plan = self.plan()
        try:
            plan["fd_metadata"]["sha256"] = "0" * 64
            with self.assertRaises(launcher.LauncherPrototypeError):
                launcher.run_fixture_xray_validation(
                    plan, xray_binary=pathlib.Path("/usr/local/bin/xray"))
        finally:
            launcher.close_fixture_plan(plan)

    def test_rejects_replaced_sealed_descriptor_with_different_bytes(self):
        plan = self.plan()
        replacement = None
        try:
            altered = self.config.replace(b"warning", b"debuggg")
            replacement, metadata = attestation.create_sealed_memfd(
                altered, hashlib.sha256(altered).hexdigest())
            original = plan["fd"]
            plan["fd"] = replacement
            plan["fd_metadata"] = metadata
            with self.assertRaises(launcher.LauncherPrototypeError):
                launcher.run_fixture_xray_validation(
                    plan, xray_binary=pathlib.Path("/usr/local/bin/xray"))
            os.close(original)
            replacement = None
        finally:
            if replacement is not None:
                os.close(replacement)
            launcher.close_fixture_plan(plan)

    def test_rejects_world_writable_executable(self):
        plan = self.plan()
        fake_xray = self._fake_executable("fake-xray-writable", "exit 0")
        fake_xray.chmod(0o777)
        try:
            with self.assertRaises(launcher.LauncherPrototypeError):
                launcher.run_fixture_xray_validation(
                    plan, xray_binary=fake_xray)
        finally:
            launcher.close_fixture_plan(plan)

    def test_rejects_symlink_executable(self):
        plan = self.plan()
        target = self._fake_executable("fake-xray-target", "exit 0")
        link = self.root / "fake-xray-link"
        link.symlink_to(target)
        try:
            with self.assertRaises(launcher.LauncherPrototypeError):
                launcher.run_fixture_xray_validation(
                    plan, xray_binary=link,
                    setpriv_binary=pathlib.Path("/usr/bin/setpriv"))
        finally:
            launcher.close_fixture_plan(plan)

    def test_timeout_terminates_and_reaps_child(self):
        if os.geteuid() != 0:
            self.skipTest("requiere root para ejecutar setpriv")
        plan = self.plan()
        fake_xray = self._fake_executable("fake-xray-sleeper", "sleep 5")
        try:
            started = __import__("time").monotonic()
            result = launcher.run_fixture_xray_validation(
                plan, xray_binary=fake_xray,
                setpriv_binary=pathlib.Path("/usr/bin/setpriv"),
                timeout_seconds=0.2)
            elapsed = __import__("time").monotonic() - started
            self.assertEqual(result.returncode, 124)
            self.assertIn("timeout", result.stderr)
            self.assertLess(elapsed, 2.0)
            with self.assertRaises(ChildProcessError):
                os.waitpid(plan["target_pid"], os.WNOHANG)
        finally:
            launcher.close_fixture_plan(plan)

    def test_persistent_b43_backend_records_blocked_child_before_exec(self):
        if os.geteuid() != 0:
            self.skipTest("requiere root para fixture persistente")
        import json
        import stat
        import xray_runtime_directory_contract as directories
        plan = self.plan()
        try:
            directories.prepare_fixture_layout(self.root, plan["service_gid"])
            fake = self._fake_executable("fake-xray-persistent", "exit 0")
            result = launcher.run_fixture_xray_validation(
                plan, xray_binary=fake, evidence_backend="persistent_b43")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(plan["evidence_backend"], "persistent_b43")
            path = self.root / "var/lib/xray-manager/evidence" / (self.invocation + ".json")
            record = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(record["pid"], plan["target_pid"])
            self.assertEqual(record["evidence_status"], "prepared_before_exec")
            info = path.stat()
            self.assertEqual((info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode)), (0, 0, 0o600))
            denied = subprocess.run(
                ["/usr/bin/setpriv", f"--reuid={plan['service_uid']}",
                 f"--regid={plan['service_gid']}", "--clear-groups",
                 "--", "/usr/bin/test", "-r", str(path)], check=False)
            self.assertNotEqual(denied.returncode, 0, "la identidad de servicio pudo leer evidencia persistente")
            root_fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                self.assertTrue(evidence_store.verify_evidence_from_root_fd(
                    fixture_root_fd=root_fd, service_gid=plan["service_gid"],
                    invocation_id=self.invocation)["verified"])
            finally:
                os.close(root_fd)
        finally:
            launcher.close_fixture_plan(plan)

    def test_persistent_b43_failure_keeps_gate_closed_and_reaps_child(self):
        if os.geteuid() != 0:
            self.skipTest("requiere root para comprobar el gate")
        plan = self.plan()
        marker = pathlib.Path(self.temp.name) / "should-not-exec"
        fake = self._fake_executable("fake-xray-must-not-run", f"touch {marker}; exit 0")
        import xray_runtime_directory_contract as directories
        directories.prepare_fixture_layout(self.root, plan["service_gid"])
        try:
            with unittest.mock.patch.object(
                    supervisor_evidence, "prepare_persistent_evidence",
                    side_effect=supervisor_evidence.SupervisorEvidenceError("injected failure")):
                with self.assertRaises(supervisor_evidence.SupervisorEvidenceError):
                    launcher.run_fixture_xray_validation(
                        plan, xray_binary=fake, evidence_backend="persistent_b43")
            self.assertFalse(marker.exists(), "el hijo ejecutó el binario pese al fallo de evidencia")
            with self.assertRaises(ChildProcessError):
                os.waitpid(plan["target_pid"], os.WNOHANG)
        finally:
            launcher.close_fixture_plan(plan)

    def test_persistent_b43_verification_failure_keeps_gate_closed(self):
        if os.geteuid() != 0:
            self.skipTest("requiere root para comprobar el gate")
        import xray_runtime_directory_contract as directories
        plan = self.plan()
        directories.prepare_fixture_layout(self.root, plan["service_gid"])
        marker = pathlib.Path(self.temp.name) / "verify-failure-exec"
        fake = self._fake_executable("fake-xray-verify-failure", f"touch {marker}; exit 0")
        try:
            with unittest.mock.patch.object(
                    evidence_store, "verify_evidence_from_root_fd",
                    side_effect=evidence_store.EvidenceStoreError("injected verify failure")):
                with self.assertRaises(supervisor_evidence.SupervisorEvidenceError):
                    launcher.run_fixture_xray_validation(
                        plan, xray_binary=fake, evidence_backend="persistent_b43")
            self.assertFalse(marker.exists())
            with self.assertRaises(ChildProcessError):
                os.waitpid(plan["target_pid"], os.WNOHANG)
        finally:
            launcher.close_fixture_plan(plan)

    def test_root_anchor_fd_is_not_inherited_by_execed_child(self):
        if os.geteuid() != 0:
            self.skipTest("requiere root para comprobar herencia de descriptores")
        import xray_runtime_directory_contract as directories
        plan = self.plan()
        directories.prepare_fixture_layout(self.root, plan["service_gid"])
        capture = pathlib.Path(__import__("tempfile").mktemp(prefix="b43-fds-", dir="/tmp"))
        fake = self._fake_executable(
            "fake-xray-fd-audit", f"for f in /proc/self/fd/*; do readlink \"$f\"; done > {capture}; exit 0")
        try:
            result = launcher.run_fixture_xray_validation(
                plan, xray_binary=fake, evidence_backend="persistent_b43")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            links = capture.read_text(encoding="utf-8")
            self.assertNotIn(str(self.root), links)
        finally:
            capture.unlink(missing_ok=True)
            launcher.close_fixture_plan(plan)

    def test_persistent_b43_does_not_fallback_to_legacy_backend(self):
        if os.geteuid() != 0:
            self.skipTest("requiere root para comprobar fallo cerrado")
        plan = self.plan()
        import xray_runtime_directory_contract as directories
        directories.prepare_fixture_layout(self.root, plan["service_gid"])
        try:
            with unittest.mock.patch.object(
                    supervisor_evidence, "prepare_persistent_evidence",
                    side_effect=supervisor_evidence.SupervisorEvidenceError("injected failure")):
                with self.assertRaises(supervisor_evidence.SupervisorEvidenceError):
                    launcher.run_fixture_xray_validation(
                        plan, xray_binary=pathlib.Path("/usr/local/bin/xray"),
                        evidence_backend="persistent_b43")
            self.assertFalse((self.root / "evidence" / (self.invocation + ".json")).exists())
        finally:
            launcher.close_fixture_plan(plan)


if __name__ == "__main__":
    unittest.main()
