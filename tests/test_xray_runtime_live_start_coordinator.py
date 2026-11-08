from __future__ import annotations

import hashlib
import pathlib
import sys
import tempfile
import unittest
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import xray_runtime_live_journal as journal
import xray_runtime_live_start_coordinator as coordinator

HASH = hashlib.sha256(b"published-config").hexdigest()
PROFILE = "profile-" + "a" * 32
REVISION = "r000001"
VALIDATION = "pvalidation-" + "b" * 32
OPERATION = "runtime-op-" + "1" * 32
GENERATION = "generation-" + "2" * 32


class FakeBackend:
    def __init__(self, *, failure=None):
        self.failure = failure
        self.calls = []

    def start(self, **kwargs):
        self.calls.append(kwargs)
        if self.failure:
            raise self.failure
        return {"result": "accepted_not_verified", "postcondition": "pending_observation",
                "controller_result": {"controller": "modules/xray_service.sh", "returncode": 0}}


class LiveStartCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = journal.LiveOperationStore(pathlib.Path(self.tmp.name) / "runtime-operations")
        self.record = self.store.create(profile_id=PROFILE, revision=REVISION, validation_id=VALIDATION,
                                        profile_sha256=HASH, staged_sha256=HASH, binary_sha256=HASH,
                                        initial_systemd={"unit": "xray.service", "read_only": True},
                                        previous_config=None)
        self.op = self.record["operation_id"]
        self.store.transition(self.op, expected_state="prepared", new_state="validated")
        self.store.transition(self.op, expected_state="validated", new_state="snapshot_saved")
        self.store.transition(self.op, expected_state="snapshot_saved", new_state="publication_requested")
        self.store.transition(self.op, expected_state="publication_requested", new_state="config_published",
                              updates={"publication": {"status": "published", "target": "/etc/xray/config.json",
                                                        "config_sha256": HASH,
                                                        "published_at": "2026-11-08T15:00:00+00:00"}})
        self.backend = FakeBackend()
        self.systemd = {"unit": "xray.service", "load_state": "loaded", "active_state": "active",
                        "sub_state": "running", "result": "success", "exec_main_status": "0",
                        "user": "xray", "group": "xray", "main_pid": 4321,
                        "invocation_id": "b" * 32,
                        "exec_main_start_timestamp": "Sun 2026-11-08 10:00:02 -05",
                        "active_enter_timestamp": "Sun 2026-11-08 10:00:03 -05", "read_only": True}
        self.process = {"pid": 4321, "systemd_main_pid": 4321, "systemd_invocation_id": "b" * 32,
                        "identity_verified": True, "read_only": True, "effective_uid": 991,
                        "effective_gid": 991, "argv": ("/usr/local/bin/xray", "run", "-config", "/etc/xray/config.json"),
                        "executable_path": "/usr/local/bin/xray", "executable_sha256": "c" * 64,
                        "process_starttime_ticks": 12345, "configuration_loaded": False,
                        "configuration_evidence": "not_attested"}

    def tearDown(self):
        self.tmp.cleanup()

    def run_start(self, **overrides):
        args = {"store": self.store, "operation_id": self.op, "generation_id": GENERATION,
                "backend": self.backend, "systemd_observer": lambda: dict(self.systemd),
                "process_observer": lambda: dict(self.process),
                "config_hash_reader": lambda: HASH, "confirmation": True}
        args.update(overrides)
        return coordinator.start_published_operation(**args)

    def test_durable_request_acceptance_and_active_correlation(self):
        result = self.run_start()
        saved = self.store.load(self.op)
        self.assertEqual(result["status"], "SERVICE_ACTIVE_CORRELATED")
        self.assertEqual(saved["state"], "service_observed_active")
        self.assertEqual(saved["service_action"]["status"], "observed_active")
        self.assertEqual(saved["post_systemd"]["main_pid"], 4321)
        self.assertFalse(result["configuration_loaded"])
        self.assertFalse(result["completed"])
        self.assertEqual(len(self.backend.calls), 1)

    def test_controller_timeout_is_persisted_as_recovery_required_without_retry(self):
        self.backend.failure = TimeoutError("timeout")
        with self.assertRaises(coordinator.StartCoordinatorError):
            self.run_start()
        saved = self.store.load(self.op)
        self.assertEqual(saved["state"], "recovery_required")
        self.assertEqual(saved["recovery"]["decision"], "controller_outcome_ambiguous")
        self.assertEqual(len(self.backend.calls), 1)

    def test_post_start_observation_failure_is_recovery_required(self):
        with self.assertRaises(coordinator.StartCoordinatorError):
            self.run_start(process_observer=lambda: {"identity_verified": False})
        saved = self.store.load(self.op)
        self.assertEqual(saved["state"], "recovery_required")
        self.assertEqual(saved["recovery"]["decision"], "post_start_observation_unverified")

    def test_runtime_hash_mismatch_blocks_before_action(self):
        with self.assertRaises(coordinator.StartCoordinatorError):
            self.run_start(config_hash_reader=lambda: "d" * 64)
        self.assertEqual(self.store.load(self.op)["state"], "config_published")
        self.assertEqual(self.backend.calls, [])

    def test_confirmation_required(self):
        with self.assertRaises(coordinator.StartCoordinatorError):
            self.run_start(confirmation=False)
        self.assertEqual(self.store.load(self.op)["state"], "config_published")
        self.assertEqual(self.backend.calls, [])

    def test_rejects_already_requested_or_terminal_operation(self):
        self.store.transition(self.op, expected_state="config_published", new_state="service_action_requested",
                              updates={"service_action": {"status": "requested"}})
        with self.assertRaises(coordinator.StartCoordinatorError):
            self.run_start()
        self.assertEqual(self.backend.calls, [])

    def test_rejects_non_active_post_start_state(self):
        self.systemd["active_state"] = "failed"
        with self.assertRaises(coordinator.StartCoordinatorError):
            self.run_start()
        self.assertEqual(self.store.load(self.op)["state"], "recovery_required")


if __name__ == "__main__":
    unittest.main()
