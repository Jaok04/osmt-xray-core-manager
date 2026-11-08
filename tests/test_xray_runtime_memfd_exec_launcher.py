from __future__ import annotations

import hashlib
import os
import pathlib
import pwd
import grp
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import xray_runtime_memfd_exec_launcher as launcher


class MemfdExecLauncherFixtureTests(unittest.TestCase):
    def setUp(self):
        if os.geteuid() != 0:
            self.skipTest("las pruebas requieren root para lanzar y observar otra identidad")
        self.temp = tempfile.TemporaryDirectory(prefix="xray-memfd-exec-")
        self.root = pathlib.Path(self.temp.name) / "fixture"
        self.root.mkdir(mode=0o711)
        pathlib.Path(self.temp.name).chmod(0o711)
        marker = self.root / ".xray-manager-fixture"
        marker.write_text("fixture-only\n", encoding="ascii")
        marker.chmod(0o600)
        self.config = (b'{"log":{"loglevel":"warning"},"inbounds":[],'
                       b'"outbounds":[{"protocol":"freedom","settings":{}}]}\n')
        self.digest = hashlib.sha256(self.config).hexdigest()
        self.config_path = self.root / "config.source"
        self.config_path.write_bytes(self.config)
        self.config_path.chmod(0o644)
        self.link_dir = self.root / "links"
        self.link_dir.mkdir(mode=0o711)
        self.link = self.link_dir / "config.json"
        self.link.symlink_to("/proc/self/fd/3")
        self.xray = pathlib.Path("/usr/local/bin/xray")
        self.launcher_path = ROOT / "scripts/xray_runtime_memfd_exec_launcher.py"
        self.account = pwd.getpwnam("nobody")
        self.group = grp.getgrnam("nogroup")

    def tearDown(self):
        self.temp.cleanup()

    def _command(self, *, config=None, link=None, digest=None, size=None):
        return [
            "/usr/bin/setpriv", f"--reuid={self.account.pw_uid}",
            f"--regid={self.group.gr_gid}", "--clear-groups", "--no-new-privs", "--",
            sys.executable, str(self.launcher_path),
            "--fixture-root", str(self.root),
            "--config", str(config or self.config_path),
            "--config-link", str(link or self.link),
            "--xray", str(self.xray),
            "--sha256", digest or self.digest,
            "--size", str(size if size is not None else len(self.config)),
        ]

    def _start(self, **kwargs):
        return subprocess.Popen(
            self._command(**kwargs), stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )

    def _stop(self, process):
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
        try:
            output = process.communicate(timeout=4)[0]
        except subprocess.TimeoutExpired:
            process.kill()
            output = process.communicate(timeout=4)[0]
        return output

    def test_real_xray_exec_keeps_same_sealed_descriptor_and_pid(self):
        process = self._start()
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    self.fail("launcher/Xray terminó antes de arrancar: " + process.communicate()[0])
                try:
                    result = launcher.verify_live_descriptor(
                        fixture_root=self.root, pid=process.pid, expected_uid=self.account.pw_uid,
                        expected_gid=self.group.gr_gid, expected_sha256=self.digest,
                        expected_size=len(self.config), xray_binary=self.xray,
                        config_link=self.link,
                    )
                    break
                except launcher.MemfdLauncherError:
                    time.sleep(0.05)
            else:
                self.fail("No apareció el descriptor sellado correlacionado con Xray.")
            self.assertTrue(result["verified"])
            self.assertTrue(result["descriptor_process_bound"])
            self.assertFalse(result["configuration_loaded"])
            self.assertEqual(result["configuration_evidence"], "sealed_memfd_process_bound")
            self.assertEqual(result["pid"], process.pid)
            self.assertEqual(result["seals"], 15)
            self.assertEqual(result["fd"], 3)
            self.assertEqual(result["argv"], (
                str(self.xray), "run", "-config", str(self.link)))
            self.assertIsNone(process.poll(), "Xray no permaneció activo después de exec")
        finally:
            self._stop(process)

    def test_rejects_wrong_expected_hash_before_exec(self):
        result = subprocess.run(self._command(digest="0" * 64), capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("SHA-256", result.stderr)

    def test_rejects_wrong_expected_size_before_exec(self):
        result = subprocess.run(self._command(size=len(self.config) + 1), capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Tamaño", result.stderr)

    def test_rejects_symlink_to_wrong_fd(self):
        wrong = self.link_dir / "wrong.json"
        wrong.symlink_to("/proc/self/fd/4")
        result = subprocess.run(self._command(link=wrong), capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("/proc/self/fd/3", result.stderr)

    def test_rejects_symlink_outside_fixture(self):
        outside = pathlib.Path(self.temp.name) / "outside.json"
        outside.symlink_to("/proc/self/fd/3")
        result = subprocess.run(self._command(link=outside), capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("fuera de la raíz", result.stderr)

    def test_rejects_group_or_world_writable_link_directory(self):
        self.link_dir.chmod(0o733)
        result = subprocess.run(self._command(), capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("directorio", result.stderr)

    def test_rejects_symlinked_ancestor_of_config_link(self):
        outside = pathlib.Path(self.temp.name) / "outside-dir"
        outside.mkdir(mode=0o711)
        (outside / "config.json").symlink_to("/proc/self/fd/3")
        self.link.unlink()
        self.link_dir.rmdir()
        self.link_dir.symlink_to(outside, target_is_directory=True)
        result = subprocess.run(self._command(), capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("directorio antecesor", result.stderr)

    def test_rejects_symlinked_ancestor_of_source_config(self):
        outside = pathlib.Path(self.temp.name) / "outside-source"
        outside.mkdir(mode=0o711)
        (outside / "config.source").write_bytes(self.config)
        (outside / "config.source").chmod(0o644)
        moved = self.root / "source-real"
        self.config_path.rename(moved)
        alias = self.root / "source-alias"
        alias.symlink_to(self.root, target_is_directory=True)
        result = subprocess.run(self._command(config=alias / "source-real"),
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("directorio antecesor", result.stderr)

    def test_rejects_invalid_json_during_same_fd_xray_test(self):
        invalid = self.root / "invalid.source"
        raw = b'{"log":'
        invalid.write_bytes(raw)
        invalid.chmod(0o644)
        result = subprocess.run(self._command(
            config=invalid, digest=hashlib.sha256(raw).hexdigest(), size=len(raw)),
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Xray rechazó", result.stderr)

    def test_verifier_rejects_wrong_identity(self):
        process = self._start()
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                try:
                    launcher.verify_live_descriptor(
                        fixture_root=self.root, pid=process.pid, expected_uid=self.account.pw_uid,
                        expected_gid=self.group.gr_gid, expected_sha256=self.digest,
                        expected_size=len(self.config), xray_binary=self.xray,
                        config_link=self.link,
                    )
                    break
                except launcher.MemfdLauncherError:
                    time.sleep(0.05)
            with self.assertRaises(launcher.MemfdLauncherError):
                launcher.verify_live_descriptor(
                    fixture_root=self.root, pid=process.pid, expected_uid=0, expected_gid=0,
                    expected_sha256=self.digest, expected_size=len(self.config),
                    xray_binary=self.xray, config_link=self.link,
                )
        finally:
            self._stop(process)

    def test_verifier_rejects_wrong_hash(self):
        process = self._start()
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                try:
                    launcher.verify_live_descriptor(
                        fixture_root=self.root, pid=process.pid, expected_uid=self.account.pw_uid,
                        expected_gid=self.group.gr_gid, expected_sha256=self.digest,
                        expected_size=len(self.config), xray_binary=self.xray,
                        config_link=self.link,
                    )
                    break
                except launcher.MemfdLauncherError:
                    time.sleep(0.05)
            with self.assertRaises(launcher.MemfdLauncherError):
                launcher.verify_live_descriptor(
                    fixture_root=self.root, pid=process.pid, expected_uid=self.account.pw_uid,
                    expected_gid=self.group.gr_gid, expected_sha256="0" * 64,
                    expected_size=len(self.config), xray_binary=self.xray,
                    config_link=self.link,
                )
        finally:
            self._stop(process)

    def test_verifier_rejects_missing_descriptor_pid(self):
        with self.assertRaises(launcher.MemfdLauncherError):
            launcher.verify_live_descriptor(
                fixture_root=self.root, pid=99999999, expected_uid=self.account.pw_uid,
                expected_gid=self.group.gr_gid, expected_sha256=self.digest,
                expected_size=len(self.config), xray_binary=self.xray,
                config_link=self.link,
            )

    def test_launcher_refuses_root_identity(self):
        with self.assertRaises(launcher.MemfdLauncherError):
            launcher.launch_fixture(
                fixture_root=self.root, config_path=self.config_path,
                config_link=self.link, xray_binary=self.xray,
                expected_sha256=self.digest, expected_size=len(self.config),
            )


if __name__ == "__main__":
    unittest.main()
