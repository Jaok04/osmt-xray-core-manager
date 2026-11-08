from __future__ import annotations

import pathlib
import sys
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import xray_runtime_live_apply_bridge as bridge

PROFILE = "profile-" + "1" * 32
REVISION = "r000001"
OP = "runtime-op-" + "2" * 32


class FakeBackend:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class LiveApplyBridgeTests(unittest.TestCase):
    def setUp(self):
        self.patches = [
            mock.patch.object(bridge.os, "geteuid", return_value=0),
            mock.patch.object(bridge.systemd_adapter, "status", return_value={
                "unit": "xray.service", "load_state": "loaded", "active_state": "inactive",
                "main_pid": 0, "invocation_id": None, "runtime_config_sha256": None,
            }),
            mock.patch.object(bridge.live_publisher, "_read_optional_config", return_value=None),
            mock.patch.object(bridge.live_staging, "stage_live", return_value={
                "status": "STAGED", "runtime_published": False, "service_started": False,
                "staging_dir": "/run/xray-manager-runtime-staging/live-test", "lease_ids": ["resolve-" + "a" * 32],
            }),
            mock.patch.object(bridge.live_publisher, "publish_live", return_value={
                "status": "CONFIG_PUBLISHED", "operation_id": OP, "runtime_published": True,
                "service_action_performed": False, "service_started": False,
            }),
            mock.patch.object(bridge.live_journal, "LiveOperationStore", return_value=mock.sentinel.store),
            mock.patch.object(bridge.live_publisher, "_acquire_one", return_value=77),
            mock.patch.object(bridge.live_publisher, "_release_locks"),
            mock.patch.object(bridge.live_backend, "LiveRuntimeBackend", side_effect=lambda **kw: FakeBackend(**kw)),
            mock.patch.object(bridge.start_coordinator, "start_published_operation", return_value={
                "status": "SERVICE_ACTIVE_CORRELATED", "journal_state": "service_observed_active",
                "evidence": {"configuration_loaded": False},
            }),
        ]
        self.mocks = [patcher.start() for patcher in self.patches]
        for patcher in self.patches:
            self.addCleanup(patcher.stop)
        self.target_validation_patcher = mock.patch.object(
            bridge, "_validate_first_server_profile",
            return_value={"domain": "pruebas.tvrc.me", "port": 443},
        )
        self.target_validation = self.target_validation_patcher.start()
        self.addCleanup(self.target_validation_patcher.stop)

    def test_refuses_active_service_before_staging(self):
        self.mocks[1].return_value = {
            "unit": "xray.service", "load_state": "loaded", "active_state": "active",
            "main_pid": 1234, "invocation_id": "a" * 32, "runtime_config_sha256": None,
        }
        with self.assertRaises(bridge.LiveApplyBridgeError):
            bridge.apply_live(PROFILE, REVISION, confirmation=True)
        self.mocks[3].assert_not_called()

    def test_refuses_preexisting_runtime_config_until_restore_is_implemented(self):
        self.mocks[2].return_value = b'{"existing":true}\n'
        with self.assertRaisesRegex(bridge.LiveApplyBridgeError, "no sobrescribe"):
            bridge.apply_live(PROFILE, REVISION, confirmation=True)
        self.mocks[3].assert_not_called()

    def test_requires_confirmation_before_any_operation(self):
        with self.assertRaises(bridge.LiveApplyBridgeError):
            bridge.apply_live(PROFILE, REVISION, confirmation=False)
        self.mocks[3].assert_not_called()
        self.mocks[4].assert_not_called()

    def test_stages_publishes_then_starts_once_and_reports_limited_evidence(self):
        with mock.patch.object(bridge.secrets, "token_hex", return_value="3" * 32):
            result = bridge.apply_live(PROFILE, REVISION, confirmation=True)
        self.assertEqual(result["status"], "SERVICE_ACTIVE_CORRELATED")
        self.assertEqual(result["operation_id"], OP)
        self.assertEqual(result["generation_id"], "generation-" + "3" * 32)
        self.assertTrue(result["runtime_published"])
        self.assertTrue(result["service_started"])
        self.assertFalse(result["configuration_loaded"])
        self.assertFalse(result["completed"])
        self.mocks[3].assert_called_once_with(PROFILE, REVISION)
        self.target_validation.assert_called_once_with(
            pathlib.Path("/run/xray-manager-runtime-staging/live-test"), PROFILE, REVISION,
        )
        self.mocks[4].assert_called_once()
        self.mocks[7].assert_called_once_with([77])
        coordinator_args = self.mocks[9].call_args.kwargs
        self.assertEqual(coordinator_args["operation_id"], OP)
        self.assertEqual(coordinator_args["generation_id"], result["generation_id"])
        self.assertIs(coordinator_args["store"], mock.sentinel.store)
        backend = coordinator_args["backend"]
        self.assertIsInstance(backend, FakeBackend)
        self.assertEqual(backend.kwargs["lifecycle_lock_fd"], 77)

    def test_refuses_unconfirmed_publication_result_before_start(self):
        self.mocks[4].return_value = {"status": "CONFIG_PUBLISHED", "operation_id": OP,
                                      "runtime_published": True, "service_action_performed": True,
                                      "service_started": False}
        with self.assertRaises(bridge.LiveApplyBridgeError):
            bridge.apply_live(PROFILE, REVISION, confirmation=True)
        self.mocks[9].assert_not_called()

    def test_start_failure_keeps_operation_id_and_releases_lock(self):
        self.mocks[9].side_effect = RuntimeError("ambiguous start")
        with self.assertRaisesRegex(bridge.LiveApplyBridgeError, OP):
            bridge.apply_live(PROFILE, REVISION, confirmation=True)
        self.mocks[7].assert_called_once_with([77])

    def test_rejects_staging_result_that_claims_publication(self):
        self.mocks[3].return_value = {"status": "STAGED", "runtime_published": True,
                                      "service_started": False, "staging_dir": "/tmp/stage"}
        with self.assertRaises(bridge.LiveApplyBridgeError):
            bridge.apply_live(PROFILE, REVISION, confirmation=True)
        self.mocks[4].assert_not_called()


if __name__ == "__main__":
    unittest.main()
