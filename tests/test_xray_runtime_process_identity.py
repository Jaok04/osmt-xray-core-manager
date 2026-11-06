from __future__ import annotations

import hashlib
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import xray_runtime_process_identity as identity


class RuntimeProcessIdentityTests(unittest.TestCase):
    PID = 4242
    UID = 991
    GID = 991
    ARGV = ("/usr/local/bin/xray", "run", "-config", "/etc/xray/config.json")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = pathlib.Path(self.tmp.name)
        self.proc = self.base / "proc"
        self.proc.mkdir()
        (self.proc / ".xray-manager-proc-fixture").write_text(
            "xray-manager-proc-fixture-v1\n", encoding="ascii"
        )
        self.process = self.proc / str(self.PID)
        self.process.mkdir(parents=True)
        self.binary = self.base / "xray"
        self.binary.write_bytes(b"fixture-xray-executable\x00" * 32)
        self.binary.chmod(0o755)
        self.exe = self.process / "exe"
        self.exe.symlink_to(self.binary)
        self.write_stat(100)
        self.write_status(self.UID, self.GID)
        self.write_cmdline(self.ARGV)

    def tearDown(self):
        self.tmp.cleanup()

    def write_stat(self, starttime, state="S"):
        # comm incluye paréntesis y espacios para verificar el parser correcto.
        fields = [state] + ["0"] * 18 + [str(starttime)] + ["0"] * 5
        (self.process / "stat").write_text(
            f"{self.PID} (xray worker (main)) " + " ".join(fields), encoding="ascii"
        )

    def write_status(self, uid, gid):
        (self.process / "status").write_text(
            f"Name:\txray\nUid:\t{uid} {uid} {uid} {uid}\n"
            f"Gid:\t{gid} {gid} {gid} {gid}\n", encoding="ascii"
        )

    def write_cmdline(self, argv):
        (self.process / "cmdline").write_bytes(b"\0".join(
            arg.encode() for arg in argv
        ) + b"\0")

    def inspect(self):
        return identity.inspect_process(
            self.PID, expected_uid=self.UID, expected_gid=self.GID,
            expected_argv=self.ARGV, proc_root=self.proc,
            expected_executable=str(self.binary),
        )

    def test_verifies_process_identity_and_executable_hash(self):
        result = self.inspect()
        self.assertTrue(result["identity_verified"])
        self.assertEqual(result["pid"], self.PID)
        self.assertEqual(result["process_starttime_ticks"], 100)
        self.assertEqual(result["effective_uid"], self.UID)
        self.assertEqual(result["effective_gid"], self.GID)
        self.assertEqual(result["executable_sha256"],
                         hashlib.sha256(self.binary.read_bytes()).hexdigest())
        self.assertEqual(result["argv"], self.ARGV)
        self.assertFalse(result["configuration_loaded"])
        self.assertEqual(result["configuration_evidence"], "not_attested")
        self.assertTrue(result["read_only"])

    def test_rejects_pid_zero_one_and_non_integer(self):
        for pid in (0, 1, -1, True, "4242"):
            with self.subTest(pid=pid), self.assertRaises(identity.ProcessIdentityError):
                identity.inspect_process(pid, expected_uid=self.UID, expected_gid=self.GID,
                                          expected_argv=self.ARGV, proc_root=self.proc)

    def test_rejects_relative_proc_root(self):
        with self.assertRaises(identity.ProcessIdentityError):
            identity.inspect_process(self.PID, expected_uid=self.UID, expected_gid=self.GID,
                                      expected_argv=self.ARGV, proc_root=pathlib.Path("proc"))

    def test_rejects_alternate_proc_root_without_fixture_marker(self):
        other = self.base / "unmarked-proc"
        other.mkdir()
        with self.assertRaises(identity.ProcessIdentityError):
            identity.inspect_process(self.PID, expected_uid=self.UID, expected_gid=self.GID,
                                      expected_argv=self.ARGV, proc_root=other)

    def test_rejects_missing_process(self):
        (self.process / "stat").unlink()
        with self.assertRaises(identity.ProcessIdentityError):
            self.inspect()

    def test_rejects_malformed_stat(self):
        (self.process / "stat").write_text("bad", encoding="ascii")
        with self.assertRaises(identity.ProcessIdentityError):
            self.inspect()

    def test_rejects_stat_for_different_pid(self):
        (self.process / "stat").write_text("999 (xray) " + " ".join(["S"] + ["0"] * 24))
        with self.assertRaises(identity.ProcessIdentityError):
            self.inspect()

    def test_rejects_zombie_or_dead_process_state(self):
        self.write_stat(100, state="Z")
        with self.assertRaises(identity.ProcessIdentityError):
            self.inspect()

    def test_rejects_wrong_effective_uid(self):
        self.write_status(self.UID + 1, self.GID)
        with self.assertRaises(identity.ProcessIdentityError):
            self.inspect()

    def test_rejects_wrong_effective_gid(self):
        self.write_status(self.UID, self.GID + 1)
        with self.assertRaises(identity.ProcessIdentityError):
            self.inspect()

    def test_rejects_malformed_status_ids(self):
        (self.process / "status").write_text("Uid:\t1 2\nGid:\t1 1 1 1\n")
        with self.assertRaises(identity.ProcessIdentityError):
            self.inspect()

    def test_rejects_unexpected_cmdline_arguments(self):
        self.write_cmdline(self.ARGV + ("-confdir", "/tmp"))
        with self.assertRaises(identity.ProcessIdentityError):
            self.inspect()

    def test_rejects_empty_or_truncated_cmdline(self):
        (self.process / "cmdline").write_bytes(b"")
        with self.assertRaises(identity.ProcessIdentityError):
            self.inspect()
        (self.process / "cmdline").write_bytes(b"/usr/local/bin/xray")
        with self.assertRaises(identity.ProcessIdentityError):
            self.inspect()

    def test_rejects_invalid_utf8_cmdline(self):
        (self.process / "cmdline").write_bytes(b"/usr/local/bin/xray\0\xff\0")
        with self.assertRaises(identity.ProcessIdentityError):
            self.inspect()

    def test_rejects_wrong_executable_target(self):
        other = self.base / "other-xray"
        other.write_bytes(b"other")
        other.chmod(0o755)
        self.exe.unlink()
        self.exe.symlink_to(other)
        with self.assertRaises(identity.ProcessIdentityError):
            self.inspect()

    def test_rejects_deleted_executable(self):
        self.exe.unlink()
        self.exe.symlink_to(str(self.binary) + " (deleted)")
        with self.assertRaises(identity.ProcessIdentityError):
            self.inspect()

    def test_rejects_executable_with_unsafe_permissions(self):
        self.binary.chmod(0o777)
        with self.assertRaises(identity.ProcessIdentityError):
            self.inspect()

    def test_rejects_executable_hardlink(self):
        second = self.base / "second-link"
        second.hardlink_to(self.binary)
        with self.assertRaises(identity.ProcessIdentityError):
            self.inspect()

    def test_detects_pid_reuse_during_inspection(self):
        original = identity._read_bounded
        calls = {"stat": 0}

        def changing_read(path, limit):
            if pathlib.Path(path).name == "stat":
                calls["stat"] += 1
                if calls["stat"] == 2:
                    self.write_stat(101)
            return original(path, limit)

        with mock.patch.object(identity, "_read_bounded", side_effect=changing_read):
            with self.assertRaises(identity.ProcessIdentityError):
                self.inspect()

    def test_rejects_cmdline_change_during_inspection(self):
        original = identity._read_bounded
        calls = {"cmdline": 0}
        def changing_read(path, limit):
            if pathlib.Path(path).name == "cmdline":
                calls["cmdline"] += 1
                if calls["cmdline"] == 2:
                    self.write_cmdline(self.ARGV + ("--changed",))
            return original(path, limit)
        with mock.patch.object(identity, "_read_bounded", side_effect=changing_read):
            with self.assertRaises(identity.ProcessIdentityError):
                self.inspect()

    def test_rejects_effective_uid_change_during_inspection(self):
        original = identity._read_bounded
        calls = {"status": 0}
        def changing_read(path, limit):
            if pathlib.Path(path).name == "status":
                calls["status"] += 1
                if calls["status"] == 2:
                    self.write_status(self.UID + 1, self.GID)
            return original(path, limit)
        with mock.patch.object(identity, "_read_bounded", side_effect=changing_read):
            with self.assertRaises(identity.ProcessIdentityError):
                self.inspect()

    def test_rejects_executable_change_during_hash(self):
        original = identity.os.fstat
        calls = {"count": 0}

        def changed_fstat(fd):
            info = original(fd)
            calls["count"] += 1
            if calls["count"] == 2:
                # Simula mutación detectable de metadatos durante la lectura.
                return mock.Mock(
                    st_dev=info.st_dev, st_ino=info.st_ino, st_size=info.st_size,
                    st_mtime_ns=info.st_mtime_ns + 1, st_mode=info.st_mode,
                    st_uid=info.st_uid, st_nlink=info.st_nlink,
                )
            return info

        with mock.patch.object(identity.os, "fstat", side_effect=changed_fstat):
            with self.assertRaises(identity.ProcessIdentityError):
                self.inspect()


if __name__ == "__main__":
    unittest.main()
