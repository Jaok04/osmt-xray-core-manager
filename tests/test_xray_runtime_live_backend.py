from __future__ import annotations

import pathlib
import sys
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import xray_runtime_live_backend as live


HASH = "a" * 64
OP = "runtime-op-" + "1" * 32
GEN = "generation-" + "2" * 32


class LiveRuntimeBackendContractTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = {
            "unit": "xray.service", "load_state": "loaded",
            "active_state": "inactive", "sub_state": "dead", "result": "success",
            "main_pid": 0, "invocation_id": None, "active_enter_timestamp": "",
            "fragment_path": "/etc/systemd/system/xray.service",
            "runtime_config_sha256": HASH, "loaded_generation_id": None,
            "loaded_config_sha256": None, "read_only": True,
        }
        self.process = {
            "pid": 4321, "systemd_main_pid": 4321,
            "systemd_invocation_id": "b" * 32,
            "identity_verified": True, "read_only": True,
            "configuration_loaded": False, "configuration_evidence": "not_attested",
        }
        self.calls = []
        self.evidence = {
            "verified": True, "environment": "live", "operation_id": OP,
            "generation_id": GEN, "published_config_sha256": HASH,
            "publication_status": "published", "validation_result": "PASS",
        }
        self.backend = live.LiveRuntimeBackend(
            lifecycle_lock_fd=9, lifecycle_lock_path=pathlib.Path("/tmp/lifecycle.lock"),
            systemd_observer=lambda: dict(self.snapshot),
            process_observer=lambda: dict(self.process),
            action_runner=self.action,
            operation_evidence_reader=lambda operation_id, generation_id: dict(self.evidence),
        )

    def action(self, action, **kwargs):
        self.calls.append((action, kwargs))
        return {"action": action, "result": "accepted"}

    def make_active(self):
        self.snapshot.update({
            "active_state": "active", "sub_state": "running", "main_pid": 4321,
            "invocation_id": "b" * 32,
            "active_enter_timestamp": "Thu 2026-11-06 12:00:00 -05",
        })

    def test_status_separates_runtime_hash_from_loaded_evidence(self):
        result = self.backend.status()
        self.assertEqual(result["runtime_config_sha256"], HASH)
        self.assertIsNone(result["published_config_sha256"])
        self.assertIsNone(result["loaded_config_sha256"])
        self.assertFalse(result["configuration_loaded"])
        self.assertIsNone(result["process_identity"])

    def test_rejects_inactive_snapshot_with_main_pid(self):
        self.snapshot["main_pid"] = 4321
        with self.assertRaises(live.LiveBackendError):
            self.backend.status()
        self.assertEqual(self.calls, [])

    def test_rejects_inactive_snapshot_with_invocation_id(self):
        self.snapshot["invocation_id"] = "b" * 32
        with self.assertRaises(live.LiveBackendError):
            self.backend.status()
        self.assertEqual(self.calls, [])

    def test_rejects_active_snapshot_without_valid_process_metadata(self):
        invalid_snapshots = (
            {"main_pid": 0},
            {"main_pid": 1},
            {"invocation_id": None},
            {"invocation_id": "invalid"},
            {"sub_state": "start"},
            {"result": "exit-code"},
        )
        for change in invalid_snapshots:
            with self.subTest(change=change):
                self.make_active()
                self.snapshot.update(change)
                with self.assertRaises(live.LiveBackendError):
                    self.backend.status()

    def test_start_only_from_inactive_and_returns_unverified_acceptance(self):
        result = self.backend.start(operation_id=OP, generation_id=GEN, confirmation=True)
        self.assertEqual(result["result"], "accepted_not_verified")
        self.assertEqual(result["postcondition"], "pending_observation")
        self.assertEqual(self.calls[0][0], "start")
        self.assertFalse(result["configuration_loaded"])

    def test_start_rejects_active(self):
        self.make_active()
        with self.assertRaises(live.LiveBackendError):
            self.backend.start(operation_id=OP, generation_id=GEN, confirmation=True)
        self.assertEqual(self.calls, [])

    def test_restart_requires_active_and_correlated_process(self):
        self.make_active()
        result = self.backend.restart(operation_id=OP, generation_id=GEN, confirmation=True)
        self.assertEqual(result["result"], "accepted_not_verified")
        self.assertEqual(self.calls[0][0], "restart")

    def test_stop_requires_reason_and_process_identity(self):
        self.make_active()
        with self.assertRaises(live.LiveBackendError):
            self.backend.stop(operation_id=OP, generation_id=GEN, confirmation=True, recovery_reason="")
        self.assertEqual(self.calls, [])
        result = self.backend.stop(operation_id=OP, generation_id=GEN, confirmation=True,
                                   recovery_reason="recuperación de operación interrumpida")
        self.assertEqual(result["result"], "accepted_not_verified")
        self.assertEqual(self.calls[-1][0], "stop")

    def test_mutations_require_explicit_confirmation(self):
        with self.assertRaises(live.LiveBackendError):
            self.backend.start(operation_id=OP, generation_id=GEN, confirmation=False)
        self.assertEqual(self.calls, [])

    def test_rejects_runtime_hash_mismatch(self):
        self.evidence["published_config_sha256"] = "c" * 64
        with self.assertRaises(live.LiveBackendError):
            self.backend.start(operation_id=OP, generation_id=GEN, confirmation=True)
        self.assertEqual(self.calls, [])

    def test_reobserves_and_rejects_external_change_before_mutation(self):
        observations = [dict(self.snapshot), dict(self.snapshot)]
        observations[1]["runtime_config_sha256"] = "c" * 64
        backend = live.LiveRuntimeBackend(
            lifecycle_lock_fd=9, lifecycle_lock_path=pathlib.Path("/tmp/lifecycle.lock"),
            systemd_observer=lambda: observations.pop(0),
            action_runner=self.action,
            operation_evidence_reader=lambda operation_id, generation_id: dict(self.evidence),
        )
        with self.assertRaises(live.LiveBackendError):
            backend.start(operation_id=OP, generation_id=GEN, confirmation=True)
        self.assertEqual(self.calls, [])

    def test_reports_failed_or_unknown_but_blocks_mutation(self):
        for state in ("failed", "unknown"):
            self.snapshot["active_state"] = state
            self.assertEqual(self.backend.status()["active_state"], state)
            with self.assertRaises(live.LiveBackendError):
                self.backend.start(operation_id=OP, generation_id=GEN, confirmation=True)
        self.assertEqual(self.calls, [])

    def test_rejects_unattested_loaded_config_claim(self):
        self.snapshot["loaded_config_sha256"] = HASH
        with self.assertRaises(live.LiveBackendError):
            self.backend.status()

    def test_rejects_process_invocation_mismatch(self):
        self.make_active()
        self.process["systemd_invocation_id"] = "c" * 32
        with self.assertRaises(live.LiveBackendError):
            self.backend.status()

    def test_controller_timeout_or_failure_is_not_success(self):
        self.backend._action_runner = mock.Mock(side_effect=RuntimeError("timeout"))
        with self.assertRaises(RuntimeError):
            self.backend.start(operation_id=OP, generation_id=GEN, confirmation=True)

    def test_rejects_fixture_evidence_for_live_mutation(self):
        self.evidence["environment"] = "fixture"
        with self.assertRaises(live.LiveBackendError):
            self.backend.start(operation_id=OP, generation_id=GEN, confirmation=True)
        self.assertEqual(self.calls, [])

    def test_rejects_evidence_for_different_operation_or_generation(self):
        for field, value in (("operation_id", "runtime-op-" + "3" * 32),
                             ("generation_id", "generation-" + "4" * 32)):
            with self.subTest(field=field):
                self.evidence[field] = value
                with self.assertRaises(live.LiveBackendError):
                    self.backend.start(operation_id=OP, generation_id=GEN, confirmation=True)
                self.evidence[field] = OP if field == "operation_id" else GEN
        self.assertEqual(self.calls, [])

    def test_rejects_missing_evidence_reader_and_no_free_hash_parameter(self):
        backend = live.LiveRuntimeBackend(
            lifecycle_lock_fd=9, lifecycle_lock_path=pathlib.Path("/tmp/lifecycle.lock"),
            systemd_observer=lambda: dict(self.snapshot), action_runner=self.action,
        )
        with self.assertRaises(live.LiveBackendError):
            backend.start(operation_id=OP, generation_id=GEN, confirmation=True)
        with self.assertRaises(TypeError):
            self.backend.start(expected_runtime_config_sha256=HASH, confirmation=True)
        self.assertEqual(self.calls, [])

    def test_restore_fails_closed_until_atomic_runtime_recovery_exists(self):
        with self.assertRaises(live.LiveBackendError):
            self.backend.restore()

    def test_transient_state_is_rejected(self):
        self.snapshot["active_state"] = "activating"
        with self.assertRaises(live.LiveBackendError):
            self.backend.status()


if __name__ == "__main__":
    unittest.main()
