from __future__ import annotations

import fcntl
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import xray_runtime_config_attestation as attestation


class ConfigAttestationFixtureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name) / "fixture"
        self.root.mkdir(mode=0o700)
        marker = self.root / ".xray-manager-fixture"
        marker.write_text("fixture-only\n")
        marker.chmod(0o600)
        self.evidence_dir = self.root / "evidence"
        self.config = b'{"log":{"loglevel":"warning"},"inbounds":[],"outbounds":[]}\n'
        self.digest = hashlib.sha256(self.config).hexdigest()
        self.invocation = "a" * 32

    def tearDown(self):
        self.temp.cleanup()

    def descriptor(self):
        return attestation.create_sealed_memfd(self.config, self.digest)

    def test_memfd_exact_bytes_sealed_and_inheritable(self):
        fd, meta = self.descriptor()
        try:
            self.assertEqual(os.read(fd, len(self.config)), self.config)
            self.assertEqual(meta["sha256"], self.digest)
            self.assertTrue(meta["inheritable"])
            self.assertEqual(meta["seals"] & attestation.REQUIRED_SEALS,
                             attestation.REQUIRED_SEALS)
        finally:
            os.close(fd)

    def test_kernel_rejects_write_truncate_and_grow(self):
        fd, _ = self.descriptor()
        try:
            with self.assertRaises(OSError):
                os.write(fd, b"x")
            with self.assertRaises(OSError):
                os.ftruncate(fd, len(self.config) + 1)
            with self.assertRaises(OSError):
                fcntl.fcntl(fd, fcntl.F_ADD_SEALS, fcntl.F_SEAL_GROW)
        finally:
            os.close(fd)

    def test_descriptor_survives_exec_and_child_reads_exact_bytes(self):
        fd, meta = self.descriptor()
        try:
            code = (
                "import hashlib,os,sys; "
                "d=os.read(int(sys.argv[1]), 1048576); "
                "print(hashlib.sha256(d).hexdigest()); "
                "sys.exit(0 if d==" + repr(self.config) + " else 9)"
            )
            completed = subprocess.run(
                [sys.executable, "-c", code, str(fd)],
                pass_fds=(fd,), capture_output=True, text=True, check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stdout.strip(), self.digest)
            self.assertEqual(meta["sha256"], self.digest)
        finally:
            os.close(fd)

    def test_evidence_is_atomic_private_and_correlated(self):
        fd, meta = self.descriptor()
        try:
            evidence = attestation.write_invocation_evidence(
                fixture_root=self.root, evidence_dir=self.evidence_dir,
                fd_metadata=meta, pid=os.getpid(), invocation_id=self.invocation,
            )
            self.assertEqual(evidence.stat().st_mode & 0o777, 0o600)
            result = attestation.verify_invocation_evidence(
                evidence_path=evidence, fixture_root=self.root,
                expected_sha256=self.digest, expected_size=len(self.config),
                main_pid=os.getpid(), invocation_id=self.invocation,
            )
            self.assertTrue(result["verified"])
            self.assertEqual(result["environment"], "fixture")
            self.assertTrue(result["configuration_loaded"])
        finally:
            os.close(fd)

    def test_rejects_wrong_pid(self):
        fd, meta = self.descriptor()
        try:
            evidence = attestation.write_invocation_evidence(
                fixture_root=self.root, evidence_dir=self.evidence_dir,
                fd_metadata=meta, pid=os.getpid(), invocation_id=self.invocation,
            )
            with self.assertRaises(attestation.ConfigAttestationError):
                attestation.verify_invocation_evidence(
                    evidence_path=evidence, fixture_root=self.root,
                    expected_sha256=self.digest, expected_size=len(self.config),
                    main_pid=os.getpid() + 1, invocation_id=self.invocation,
                )
        finally:
            os.close(fd)

    def test_rejects_wrong_invocation_id(self):
        fd, meta = self.descriptor()
        try:
            evidence = attestation.write_invocation_evidence(
                fixture_root=self.root, evidence_dir=self.evidence_dir,
                fd_metadata=meta, pid=os.getpid(), invocation_id=self.invocation,
            )
            with self.assertRaises(attestation.ConfigAttestationError):
                attestation.verify_invocation_evidence(
                    evidence_path=evidence, fixture_root=self.root,
                    expected_sha256=self.digest, expected_size=len(self.config),
                    main_pid=os.getpid(), invocation_id="b" * 32,
                )
        finally:
            os.close(fd)

    def test_rejects_wrong_config_hash_and_size(self):
        fd, meta = self.descriptor()
        try:
            evidence = attestation.write_invocation_evidence(
                fixture_root=self.root, evidence_dir=self.evidence_dir,
                fd_metadata=meta, pid=os.getpid(), invocation_id=self.invocation,
            )
            for kwargs in (
                {"expected_sha256": "b" * 64, "expected_size": len(self.config)},
                {"expected_sha256": self.digest, "expected_size": len(self.config) + 1},
            ):
                with self.subTest(kwargs=kwargs):
                    with self.assertRaises(attestation.ConfigAttestationError):
                        attestation.verify_invocation_evidence(
                            evidence_path=evidence, fixture_root=self.root,
                            main_pid=os.getpid(), invocation_id=self.invocation,
                            **kwargs,
                        )
        finally:
            os.close(fd)

    def test_rejects_replay_same_invocation(self):
        fd, meta = self.descriptor()
        try:
            attestation.write_invocation_evidence(
                fixture_root=self.root, evidence_dir=self.evidence_dir,
                fd_metadata=meta, pid=os.getpid(), invocation_id=self.invocation,
            )
            with self.assertRaises(attestation.ConfigAttestationError):
                attestation.write_invocation_evidence(
                    fixture_root=self.root, evidence_dir=self.evidence_dir,
                    fd_metadata=meta, pid=os.getpid(), invocation_id=self.invocation,
                )
        finally:
            os.close(fd)

    def test_rejects_unmarked_fixture_root(self):
        fd, meta = self.descriptor()
        try:
            other = pathlib.Path(self.temp.name) / "unmarked"
            other.mkdir()
            with self.assertRaises(attestation.ConfigAttestationError):
                attestation.write_invocation_evidence(
                    fixture_root=other, evidence_dir=other / "evidence",
                    fd_metadata=meta, pid=os.getpid(), invocation_id=self.invocation,
                )
        finally:
            os.close(fd)

    def test_rejects_wrong_input_hash(self):
        with self.assertRaises(attestation.ConfigAttestationError):
            attestation.create_sealed_memfd(self.config, "0" * 64)


if __name__ == "__main__":
    unittest.main()
