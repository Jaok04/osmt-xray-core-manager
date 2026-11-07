from __future__ import annotations

import fcntl
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import xray_runtime_service_control as control


@unittest.skipUnless(os.geteuid() == 0, "El puente de servicio requiere root")
class RuntimeServiceControlTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = pathlib.Path(self.tmp.name)
        self.lock_path = self.base / "lifecycle.lock"
        self.lock_path.touch(mode=0o600)
        self.lock_path.chmod(0o600)
        self.module = self.base / "xray_service.sh"
        self.module.write_text("# fixture controller\n", encoding="utf-8")
        self.module.chmod(0o644)
        self.fd = os.open(self.lock_path, os.O_RDWR)
        self.addCleanup(os.close, self.fd)
        fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_delegates_only_to_bash_controller_with_inherited_lock_fd(self):
        completed = mock.Mock(returncode=0, stdout="Xray activo\n", stderr="")
        with mock.patch.object(control.subprocess, "run", return_value=completed) as run:
            result = control.run_action(
                "start", lifecycle_lock_fd=self.fd,
                lifecycle_lock_path=self.lock_path, service_module=self.module,
            )
        self.assertEqual(result["result"], "accepted")
        self.assertEqual(result["controller"], "modules/xray_service.sh")
        self.assertEqual(result["lock_handoff"], "inherited_descriptor_verified")
        args, kwargs = run.call_args
        self.assertEqual(args[0][0:2], ["/bin/bash", "-c"])
        self.assertEqual(kwargs["pass_fds"], (self.fd,))
        self.assertEqual(kwargs["env"]["XRAY_MANAGER_LIFECYCLE_LOCK_FD"], str(self.fd))
        self.assertEqual(kwargs["env"]["XRAY_MANAGER_LIFECYCLE_LOCK_OWNER_PID"], str(os.getpid()))
        self.assertIn("xray_service_action_inherited_lock", args[0][2])
        self.assertNotIn("systemctl", " ".join(args[0]))

    def test_rejects_non_string_action_before_subprocess(self):
        with mock.patch.object(control.subprocess, "run") as run:
            with self.assertRaises(control.ServiceControlError):
                control.run_action(
                    ["start"], lifecycle_lock_fd=self.fd,
                    lifecycle_lock_path=self.lock_path, service_module=self.module,
                )
        run.assert_not_called()

    def test_rejects_unsupported_action_before_subprocess(self):
        with mock.patch.object(control.subprocess, "run") as run:
            with self.assertRaises(control.ServiceControlError):
                control.run_action(
                    "enable", lifecycle_lock_fd=self.fd,
                    lifecycle_lock_path=self.lock_path, service_module=self.module,
                )
        run.assert_not_called()

    def test_rejects_unlocked_descriptor_without_acquiring_it(self):
        fcntl.flock(self.fd, fcntl.LOCK_UN)
        with mock.patch.object(control.subprocess, "run") as run:
            with self.assertRaisesRegex(control.ServiceControlError, "no demuestra un FLOCK"):
                control.run_action(
                    "start", lifecycle_lock_fd=self.fd,
                    lifecycle_lock_path=self.lock_path, service_module=self.module,
                )
        run.assert_not_called()
        other_fd = os.open(self.lock_path, os.O_RDWR)
        try:
            fcntl.flock(other_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            fcntl.flock(other_fd, fcntl.LOCK_UN)
            os.close(other_fd)

    def test_fails_closed_when_fdinfo_is_unavailable(self):
        with mock.patch.object(control.Path, "read_text", side_effect=OSError("procfs unavailable")):
            with mock.patch.object(control.subprocess, "run") as run:
                with self.assertRaisesRegex(control.ServiceControlError, "fdinfo"):
                    control.run_action(
                        "start", lifecycle_lock_fd=self.fd,
                        lifecycle_lock_path=self.lock_path, service_module=self.module,
                    )
        run.assert_not_called()

    def test_rejects_lock_record_owned_by_a_different_process_id(self):
        with mock.patch.object(control.os, "getpid", return_value=os.getpid() + 1):
            with mock.patch.object(control.subprocess, "run") as run:
                with self.assertRaisesRegex(control.ServiceControlError, "no demuestra un FLOCK"):
                    control.run_action(
                        "start", lifecycle_lock_fd=self.fd,
                        lifecycle_lock_path=self.lock_path, service_module=self.module,
                    )
        run.assert_not_called()

    def test_rejects_lock_held_on_a_different_descriptor_in_same_process(self):
        fcntl.flock(self.fd, fcntl.LOCK_UN)
        other_fd = os.open(self.lock_path, os.O_RDWR)
        try:
            fcntl.flock(other_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with mock.patch.object(control.subprocess, "run") as run:
                with self.assertRaisesRegex(control.ServiceControlError, "no demuestra un FLOCK"):
                    control.run_action(
                        "start", lifecycle_lock_fd=self.fd,
                        lifecycle_lock_path=self.lock_path, service_module=self.module,
                    )
            run.assert_not_called()
        finally:
            fcntl.flock(other_fd, fcntl.LOCK_UN)
            os.close(other_fd)

    def test_rejects_descriptor_for_different_file(self):
        other = self.base / "other.lock"
        other.touch(mode=0o600)
        other.chmod(0o600)
        with mock.patch.object(control.subprocess, "run") as run:
            with self.assertRaises(control.ServiceControlError):
                control.run_action(
                    "start", lifecycle_lock_fd=self.fd,
                    lifecycle_lock_path=other, service_module=self.module,
                )
        run.assert_not_called()

    def test_rejects_symlinked_lock_path(self):
        link = self.base / "lock-link"
        link.symlink_to(self.lock_path)
        with mock.patch.object(control.subprocess, "run") as run:
            with self.assertRaises(control.ServiceControlError):
                control.run_action(
                    "start", lifecycle_lock_fd=self.fd,
                    lifecycle_lock_path=link, service_module=self.module,
                )
        run.assert_not_called()

    def test_surfaces_controller_failure(self):
        completed = mock.Mock(returncode=1, stdout="", stderr="ERROR: unidad no administrada")
        with mock.patch.object(control.subprocess, "run", return_value=completed):
            with self.assertRaisesRegex(control.ServiceControlError, "unidad no administrada"):
                control.run_action(
                    "restart", lifecycle_lock_fd=self.fd,
                    lifecycle_lock_path=self.lock_path, service_module=self.module,
                )

    def test_python_to_bash_bridge_uses_mocked_systemctl_without_live_system_mutation(self):
        prefix = self.base / "service-root"
        mock_bin = self.base / "mock-bin"
        (prefix / "usr/local/bin").mkdir(parents=True)
        (prefix / "usr/local/share/xray").mkdir(parents=True)
        (prefix / "etc/xray").mkdir(parents=True)
        (prefix / "etc/systemd/system").mkdir(parents=True)
        mock_bin.mkdir()
        config = prefix / "etc/xray/config.json"
        config.write_text('{"inbounds":[]}\n', encoding="utf-8")
        config.chmod(0o640)
        xray_bin = prefix / "usr/local/bin/xray"
        xray_bin.write_text(
            '#!/usr/bin/env bash\n'
            'if [[ "$1 $2" == "run -test" ]]; then exit 0; fi\n'
            'exit 0\n', encoding="utf-8",
        )
        xray_bin.chmod(0o755)
        state = self.base / "mock-state"
        log = self.base / "mock-systemctl.log"
        state.write_text("inactive\n")
        log.write_text("")
        systemctl = mock_bin / "systemctl"
        systemctl.write_text(
            '#!/usr/bin/env bash\n'
            'printf "%s\n" "$*" >>"$MOCK_LOG"\n'
            'case "$1" in\n'
            '  cat) exit 0 ;;\n'
            '  is-active) [[ "$(<"$MOCK_STATE")" == active ]] && exit 0; exit 3 ;;\n'
            '  start) printf "active\n" >"$MOCK_STATE"; exit 0 ;;\n'
            '  restart) printf "active\n" >"$MOCK_STATE"; exit 0 ;;\n'
            '  stop) printf "inactive\n" >"$MOCK_STATE"; exit 0 ;;\n'
            '  *) exit 2 ;;\n'
            'esac\n', encoding="utf-8",
        )
        systemctl.chmod(0o755)
        wrapper = self.base / "controller-wrapper.sh"
        wrapper.write_text(
            'export XRAY_SERVICE_ROOT=' + str(prefix) + '\n'
            'export XRAY_SERVICE_TEST_MODE=1 XRAY_SERVICE_TEST_ALLOW_CONTROL=1\n'
            'export XRAY_ADMIN_BIN=/usr/local/bin/xray XRAY_CONFIG_DIR=/etc/xray XRAY_CONFIG_FILE=/etc/xray/config.json\n'
            'export MOCK_STATE=' + str(state) + ' MOCK_LOG=' + str(log) + '\n'
            'export PATH=' + str(mock_bin) + ':/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\n'
            'source ' + str(ROOT / "modules/xray_service.sh") + '\n'
            'xray_service_unit_content >"$XRAY_SERVICE_ROOT/etc/systemd/system/xray.service"\n'
            'chmod 644 "$XRAY_SERVICE_ROOT/etc/systemd/system/xray.service"\n',
            encoding="utf-8",
        )
        wrapper.chmod(0o644)
        result = control.run_action(
            "start", lifecycle_lock_fd=self.fd,
            lifecycle_lock_path=self.lock_path, service_module=wrapper,
        )
        self.assertEqual(result["result"], "accepted")
        self.assertEqual(state.read_text(), "active\n")
        self.assertIn("start xray.service", log.read_text())

    def test_surfaces_timeout_without_claiming_success(self):
        with mock.patch.object(control.subprocess, "run", side_effect=control.subprocess.TimeoutExpired("bash", 1)):
            with self.assertRaisesRegex(control.ServiceControlError, "antes de reintentar"):
                control.run_action(
                    "restart", lifecycle_lock_fd=self.fd,
                    lifecycle_lock_path=self.lock_path, service_module=self.module,
                )


if __name__ == "__main__":
    unittest.main()
