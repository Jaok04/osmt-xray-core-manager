from __future__ import annotations

import hashlib
import multiprocessing
import json
import pathlib
import sys
import unittest
from argparse import Namespace
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import test_xray_runtime_journal as journal_test_helpers
import xray_runtime_journal as journal
import xray_runtime_orchestrator as orchestrator
import xray_runtime_service_adapter as adapter
import xray_runtime_active_profile as active_profiles


def _concurrent_restart_worker(root, barrier, output, generation_id, config_sha256,
                               expected_generation_id, expected_config_sha256):
    try:
        barrier.wait(timeout=15)
        result = adapter.restart(
            pathlib.Path(root), generation_id=generation_id,
            config_sha256=config_sha256,
            expected_generation_id=expected_generation_id,
            expected_config_sha256=expected_config_sha256,
        )
        output.put(("restart", result))
    except BaseException as exc:
        output.put(("error", repr(exc)))
        raise


def _concurrent_restore_worker(root, barrier, output, generation_id,
                               expected_current_generation_id, previous_generation_id,
                               previous_config_sha256):
    try:
        barrier.wait(timeout=15)
        result = adapter.restore(
            pathlib.Path(root), generation_id=generation_id,
            expected_current_generation_id=expected_current_generation_id,
            previous_state="active", previous_generation_id=previous_generation_id,
            previous_config_sha256=previous_config_sha256,
        )
        output.put(("restore", result))
    except BaseException as exc:
        output.put(("error", repr(exc)))
        raise


def _concurrent_status_worker(root, barrier, output):
    try:
        barrier.wait(timeout=15)
        result = adapter.status(pathlib.Path(root))
        output.put(("status", result["active_state"]))
    except BaseException as exc:
        output.put(("error", repr(exc)))
        raise



class RuntimeOrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.fx = journal_test_helpers.RuntimeJournalTests("test_snapshot_and_journal_capture_exact_profile_and_previous_runtime")
        self.fx.setUp()
        self.addCleanup(self.fx.tearDown)
        self.adapter_root = self.fx.base / "r05-adapter"
        self.staging_args = Namespace(
            profile_store="/fixture/profiles", master_key="/fixture/key",
            validation_store="/fixture/validation", profile_id=self.fx.staging_manifest["profile_id"],
            revision=self.fx.staging_manifest["revision"], xray_binary=str(self.fx.binary),
            service_state=str(self.fx.service_state), timeout=20,
        )
        self._patches = []

    def tearDown(self):
        for patcher in reversed(self._patches):
            patcher.stop()

    def configure(self, active_state="active", *, loaded_generation_id=None,
                  loaded_config_sha256=None):
        sub_state = {
            "active": "running", "inactive": "dead", "failed": "failed", "unknown": "unknown"
        }[active_state]
        self.fx.write_service_fixture(active_state=active_state, sub_state=sub_state)
        if active_state == "active" and loaded_config_sha256 is None:
            loaded_config_sha256 = hashlib.sha256(self.fx.previous_bytes).hexdigest()
        adapter.create_fixture(
            self.adapter_root, active_state=active_state, sub_state=sub_state,
            loaded_generation_id=loaded_generation_id,
            loaded_config_sha256=loaded_config_sha256,
        )

    def patch_pipeline(self):
        def fake_preflight(*args):
            return {"service_fixture": json.loads(self.fx.service_state.read_text())}
        patches = [
            mock.patch.object(orchestrator.preflight, "preflight", side_effect=fake_preflight),
            mock.patch.object(orchestrator.staging, "stage", return_value={
                "status": "STAGED", "staging_dir": str(self.fx.staging_dir)
            }),
        ]
        for item in patches:
            item.start()
            self._patches.append(item)

    def apply(self, *, active_state="active", confirm_restart=True,
              restart_outcome="success", restore_outcome="success", crash_at=None,
              loaded_generation_id=None, loaded_config_sha256=None):
        self.configure(
            active_state, loaded_generation_id=loaded_generation_id,
            loaded_config_sha256=loaded_config_sha256,
        )
        self.patch_pipeline()
        return orchestrator.apply_operation(
            staging_args=self.staging_args,
            service_root=self.fx.service_root,
            operation_store=self.fx.operation_store,
            lifecycle_lock=self.fx.lifecycle_lock,
            application_lock=self.fx.application_lock,
            lease_root=self.fx.lease_root,
            service_uid=self.fx.service_uid,
            service_gid=self.fx.service_gid,
            adapter_root=self.adapter_root,
            confirm_restart=confirm_restart,
            restart_outcome=restart_outcome,
            restore_outcome=restore_outcome,
            crash_at=crash_at,
        )

    def record(self, result):
        return journal.read_journal(
            self.fx.operation_store / "operations" / result["operation_id"]
        )

    def recover(self):
        return orchestrator.recover_operations(
            operation_store=self.fx.operation_store,
            lifecycle_lock=self.fx.lifecycle_lock,
            application_lock=self.fx.application_lock,
            adapter_root=self.adapter_root,
        )

    def test_active_confirmed_restart_verifies_generation_and_hash(self):
        result = self.apply()
        self.assertEqual(result["status"], "COMPLETED")
        record = self.record(result)
        self.assertEqual(record["schema_version"], 2)
        self.assertEqual(record["state"], "completed")
        self.assertTrue(record["orchestration"]["generation_id"].startswith("generation-"))
        self.assertEqual(record["orchestration"]["request"]["generation_id"],
                         record["orchestration"]["generation_id"])
        self.assertEqual(record["orchestration"]["verification"]["status"], "pass")
        state = adapter.status(self.adapter_root)
        self.assertEqual(state["loaded_generation_id"], record["orchestration"]["generation_id"])
        self.assertEqual(state["loaded_config_sha256"], record["publication"]["config_sha256"])

    def test_active_confirmation_rejected_publishes_pending_apply_without_restart(self):
        result = self.apply(confirm_restart=False)
        self.assertEqual(result["status"], "PUBLISHED_PENDING_APPLY")
        record = self.record(result)
        self.assertEqual(record["state"], "published_pending_apply")
        self.assertEqual(record["orchestration"]["confirmation"], "rejected")
        self.assertEqual(record["orchestration"]["request"]["action"], "none")
        events = adapter.audit_events(self.adapter_root)
        self.assertFalse(any(event["action"] == "restart" for event in events))
        self.assertEqual(adapter.status(self.adapter_root)["loaded_config_sha256"],
                         hashlib.sha256(self.fx.previous_bytes).hexdigest())

    def test_inactive_publishes_pending_start_and_never_starts(self):
        result = self.apply(active_state="inactive")
        self.assertEqual(result["status"], "PUBLISHED_PENDING_START")
        record = self.record(result)
        self.assertEqual(record["state"], "published_pending_start")
        self.assertFalse(result["service_started"])
        self.assertEqual(adapter.status(self.adapter_root)["active_state"], "inactive")
        self.assertFalse(any(event["action"] in {"restart", "start"} for event in adapter.audit_events(self.adapter_root)))

    def test_failed_state_fails_closed_without_publication_or_restart(self):
        result = self.apply(active_state="failed")
        self.assertEqual(result["status"], "RECOVERY_REQUIRED")
        record = self.record(result)
        self.assertEqual(record["state"], "recovery_required")
        self.assertEqual(record["publication"]["status"], "not_published")
        self.assertFalse(any(event["action"] == "restart" for event in adapter.audit_events(self.adapter_root)))

    def test_unknown_state_fails_closed_without_publication_or_restart(self):
        result = self.apply(active_state="unknown")
        self.assertEqual(result["status"], "RECOVERY_REQUIRED")
        record = self.record(result)
        self.assertEqual(record["state"], "recovery_required")
        self.assertEqual(record["publication"]["status"], "not_published")
        self.assertFalse(any(event["action"] == "restart" for event in adapter.audit_events(self.adapter_root)))

    def test_initial_active_loaded_hash_mismatch_fails_closed(self):
        result = self.apply(loaded_config_sha256="a" * 64)
        self.assertEqual(result["status"], "RECOVERY_REQUIRED")
        record = self.record(result)
        self.assertEqual(record["publication"]["status"], "not_published")

    def test_service_change_during_staging_blocks_before_publication(self):
        self.configure("active")
        self.patch_pipeline()
        original_status = adapter.status
        altered = {
            "schema_version": 1, "unit": "xray.service", "load_state": "loaded",
            "active_state": "active", "sub_state": "running",
            "loaded_generation_id": "generation-" + "e" * 32,
            "loaded_config_sha256": "a" * 64,
        }
        with mock.patch.object(adapter, "status", side_effect=[original_status(self.adapter_root), altered]):
            result = orchestrator.apply_operation(
                staging_args=self.staging_args, service_root=self.fx.service_root,
                operation_store=self.fx.operation_store, lifecycle_lock=self.fx.lifecycle_lock,
                application_lock=self.fx.application_lock, lease_root=self.fx.lease_root,
                service_uid=self.fx.service_uid, service_gid=self.fx.service_gid,
                adapter_root=self.adapter_root, confirm_restart=True,
            )
        self.assertEqual(result["status"], "RECOVERY_REQUIRED")
        self.assertEqual(self.record(result)["publication"]["status"], "not_published")

    def test_restart_compare_and_swap_rejects_change_between_status_and_request(self):
        self.configure("active")
        self.patch_pipeline()
        original_restart = adapter.restart
        def race_before_restart(root, *, generation_id, config_sha256,
                                expected_generation_id, expected_config_sha256,
                                outcome="success"):
            original_restart(
                root, generation_id="generation-" + "e" * 32,
                config_sha256="a" * 64,
                expected_generation_id=expected_generation_id,
                expected_config_sha256=expected_config_sha256,
            )
            return original_restart(
                root, generation_id=generation_id, config_sha256=config_sha256,
                expected_generation_id=expected_generation_id,
                expected_config_sha256=expected_config_sha256, outcome=outcome,
            )
        with mock.patch.object(adapter, "restart", side_effect=race_before_restart):
            result = orchestrator.apply_operation(
                staging_args=self.staging_args, service_root=self.fx.service_root,
                operation_store=self.fx.operation_store, lifecycle_lock=self.fx.lifecycle_lock,
                application_lock=self.fx.application_lock, lease_root=self.fx.lease_root,
                service_uid=self.fx.service_uid, service_gid=self.fx.service_gid,
                adapter_root=self.adapter_root, confirm_restart=True,
            )
        self.assertEqual(result["status"], "RECOVERY_REQUIRED")
        record = self.record(result)
        self.assertEqual(record["orchestration"]["request"]["result"], "rejected")
        self.assertEqual(adapter.status(self.adapter_root)["loaded_generation_id"], "generation-" + "e" * 32)
        self.assertEqual(self.fx.previous_config.read_bytes(), self.fx.previous_bytes)

    def test_v2_journal_rejects_generation_mismatch_between_request_and_operation(self):
        result = self.apply()
        path = self.fx.operation_store / "operations" / result["operation_id"]
        journal_path = path / "journal.json"
        record = json.loads(journal_path.read_text())
        record["orchestration"]["request"]["generation_id"] = "generation-" + "f" * 32
        journal_path.write_text(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
        journal_path.chmod(0o600)
        with self.assertRaises(journal.RuntimeJournalError):
            journal.read_journal(path)

    def test_external_service_change_after_publish_is_not_overwritten(self):
        self.configure("active")
        self.patch_pipeline()
        original_publish = orchestrator.publisher.publish_operation
        def publish_then_external_change(*args, **kwargs):
            result = original_publish(*args, **kwargs)
            adapter.restart(
                self.adapter_root,
                generation_id="generation-" + "e" * 32,
                config_sha256="a" * 64,
                expected_generation_id=None,
                expected_config_sha256=hashlib.sha256(self.fx.previous_bytes).hexdigest(),
            )
            return result
        with mock.patch.object(orchestrator.publisher, "publish_operation", side_effect=publish_then_external_change):
            result = orchestrator.apply_operation(
                staging_args=self.staging_args, service_root=self.fx.service_root,
                operation_store=self.fx.operation_store, lifecycle_lock=self.fx.lifecycle_lock,
                application_lock=self.fx.application_lock, lease_root=self.fx.lease_root,
                service_uid=self.fx.service_uid, service_gid=self.fx.service_gid,
                adapter_root=self.adapter_root, confirm_restart=True,
            )
        self.assertEqual(result["status"], "RECOVERY_REQUIRED")
        record = self.record(result)
        self.assertEqual(record["state"], "recovery_required")
        self.assertEqual(self.fx.previous_config.read_bytes(), self.fx.previous_bytes)
        self.assertEqual(adapter.status(self.adapter_root)["loaded_generation_id"], "generation-" + "e" * 32)
        events = adapter.audit_events(self.adapter_root)
        self.assertFalse(any(event["action"] == "restart" and event.get("generation_id") == result["generation_id"] for event in events))

    def test_restart_rejection_rolls_back_config_and_preserves_previous_active_service(self):
        result = self.apply(restart_outcome="reject")
        self.assertEqual(result["status"], "ROLLED_BACK")
        record = self.record(result)
        self.assertEqual(record["state"], "rolled_back")
        self.assertEqual(record["rollback"]["status"], "rolled_back")
        self.assertEqual(self.fx.previous_config.read_bytes(), self.fx.previous_bytes)
        state = adapter.status(self.adapter_root)
        self.assertEqual(state["active_state"], "active")
        self.assertEqual(state["loaded_config_sha256"], hashlib.sha256(self.fx.previous_bytes).hexdigest())

    def test_timeout_before_transition_rolls_back(self):
        result = self.apply(restart_outcome="timeout_before")
        self.assertEqual(result["status"], "ROLLED_BACK")
        self.assertEqual(self.record(result)["state"], "rolled_back")

    def test_restart_exception_before_transition_rolls_back(self):
        result = self.apply(restart_outcome="exception_before")
        self.assertEqual(result["status"], "ROLLED_BACK")
        self.assertEqual(self.record(result)["state"], "rolled_back")

    def test_service_becoming_inactive_after_restart_is_not_verified(self):
        result = self.apply(restart_outcome="inactive_after")
        self.assertEqual(result["status"], "ROLLED_BACK")
        state = adapter.status(self.adapter_root)
        self.assertEqual(state["active_state"], "active")
        self.assertEqual(state["loaded_config_sha256"], hashlib.sha256(self.fx.previous_bytes).hexdigest())

    def test_service_becoming_unknown_after_restart_requires_verified_rollback(self):
        result = self.apply(restart_outcome="unknown_after")
        self.assertEqual(result["status"], "ROLLED_BACK")
        self.assertEqual(adapter.status(self.adapter_root)["active_state"], "active")

    def test_active_without_previous_config_fails_closed_before_publish(self):
        self.fx.previous_config.unlink()
        self.configure("active", loaded_config_sha256=hashlib.sha256(self.fx.previous_bytes).hexdigest())
        self.patch_pipeline()
        result = orchestrator.apply_operation(
            staging_args=self.staging_args, service_root=self.fx.service_root,
            operation_store=self.fx.operation_store, lifecycle_lock=self.fx.lifecycle_lock,
            application_lock=self.fx.application_lock, lease_root=self.fx.lease_root,
            service_uid=self.fx.service_uid, service_gid=self.fx.service_gid,
            adapter_root=self.adapter_root, confirm_restart=True,
        )
        self.assertEqual(result["status"], "RECOVERY_REQUIRED")
        record = self.record(result)
        self.assertEqual(record["publication"]["status"], "not_published")

    def test_timeout_after_transition_is_reconciled_as_success_by_generation(self):
        result = self.apply(restart_outcome="timeout_after")
        self.assertEqual(result["status"], "COMPLETED")
        record = self.record(result)
        self.assertEqual(record["orchestration"]["request"]["result"], "timeout")
        self.assertEqual(record["orchestration"]["verification"]["status"], "pass")

    def test_lost_response_after_transition_is_reconciled_as_success(self):
        result = self.apply(restart_outcome="response_lost_after")
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(self.record(result)["orchestration"]["request"]["result"], "response_lost")

    def test_stale_generation_response_is_rejected_without_overwriting_external_state(self):
        result = self.apply(restart_outcome="wrong_generation")
        self.assertEqual(result["status"], "RECOVERY_REQUIRED")
        record = self.record(result)
        self.assertEqual(record["orchestration"]["verification"]["status"], "fail")
        self.assertEqual(record["state"], "recovery_required")
        self.assertEqual(self.fx.previous_config.read_bytes(), self.fx.previous_bytes)
        self.assertNotEqual(adapter.status(self.adapter_root)["loaded_generation_id"], result["generation_id"])

    def test_wrong_config_hash_is_rejected_and_rolled_back(self):
        result = self.apply(restart_outcome="wrong_hash")
        self.assertEqual(result["status"], "ROLLED_BACK")
        self.assertEqual(self.record(result)["state"], "rolled_back")

    def test_failed_post_restart_restores_previous_active_service(self):
        result = self.apply(restart_outcome="failed_after")
        self.assertEqual(result["status"], "ROLLED_BACK")
        state = adapter.status(self.adapter_root)
        self.assertEqual(state["active_state"], "active")
        self.assertEqual(state["loaded_config_sha256"], hashlib.sha256(self.fx.previous_bytes).hexdigest())

    def test_r04_config_rollback_failure_is_reported_without_claiming_restore(self):
        self.configure("active")
        self.patch_pipeline()
        with mock.patch.object(orchestrator.publisher, "_rollback_locked",
                               return_value={"status": "RECOVERY_REQUIRED", "reason": "fixture rollback failure"}):
            result = orchestrator.apply_operation(
                staging_args=self.staging_args, service_root=self.fx.service_root,
                operation_store=self.fx.operation_store, lifecycle_lock=self.fx.lifecycle_lock,
                application_lock=self.fx.application_lock, lease_root=self.fx.lease_root,
                service_uid=self.fx.service_uid, service_gid=self.fx.service_gid,
                adapter_root=self.adapter_root, confirm_restart=True, restart_outcome="reject",
            )
        self.assertEqual(result["status"], "RECOVERY_REQUIRED")
        record = self.record(result)
        self.assertEqual(record["orchestration"]["rollback"]["config_status"], "failed")
        self.assertNotEqual(self.fx.previous_config.read_bytes(), self.fx.previous_bytes)

    def test_service_lock_contention_prevents_restart_and_recovery_resumes(self):
        self.configure("active")
        self.patch_pipeline()
        original_acquire = orchestrator.publisher._acquire
        calls = {"count": 0}
        def lock_gate(*args, **kwargs):
            calls["count"] += 1
            if calls["count"] == 2:
                raise journal.RuntimeJournalError("fixture lock busy")
            return original_acquire(*args, **kwargs)
        with mock.patch.object(orchestrator.publisher, "_acquire", side_effect=lock_gate):
            with self.assertRaises(journal.RuntimeJournalError):
                orchestrator.apply_operation(
                    staging_args=self.staging_args, service_root=self.fx.service_root,
                    operation_store=self.fx.operation_store, lifecycle_lock=self.fx.lifecycle_lock,
                    application_lock=self.fx.application_lock, lease_root=self.fx.lease_root,
                    service_uid=self.fx.service_uid, service_gid=self.fx.service_gid,
                    adapter_root=self.adapter_root, confirm_restart=True,
                )
        record = journal.read_journal(next((self.fx.operation_store / "operations").iterdir()))
        self.assertEqual(record["state"], "config_published")
        self.assertFalse(any(event["action"] == "restart" for event in adapter.audit_events(self.adapter_root)))
        self.recover()
        final = journal.read_journal(next((self.fx.operation_store / "operations").iterdir()))
        self.assertEqual(final["state"], "completed")

    def test_service_restore_failure_leaves_recovery_required(self):
        result = self.apply(restart_outcome="failed_after", restore_outcome="fail")
        self.assertEqual(result["status"], "RECOVERY_REQUIRED")
        record = self.record(result)
        self.assertEqual(record["state"], "recovery_required")
        self.assertEqual(record["orchestration"]["rollback"]["config_status"], "restored")
        self.assertEqual(record["orchestration"]["rollback"]["service_status"], "failed")

    def test_crash_after_r04_rename_before_journal_commit_is_reconciled(self):
        self.configure("active")
        self.patch_pipeline()
        original_publish = orchestrator.publisher.publish_operation
        def crash_after_rename(*args, **kwargs):
            return original_publish(*args, **kwargs, crash_at="after_rename")
        with mock.patch.object(orchestrator.publisher, "publish_operation", side_effect=crash_after_rename):
            with self.assertRaises(journal.SimulatedCrash):
                orchestrator.apply_operation(
                    staging_args=self.staging_args, service_root=self.fx.service_root,
                    operation_store=self.fx.operation_store, lifecycle_lock=self.fx.lifecycle_lock,
                    application_lock=self.fx.application_lock, lease_root=self.fx.lease_root,
                    service_uid=self.fx.service_uid, service_gid=self.fx.service_gid,
                    adapter_root=self.adapter_root, confirm_restart=True,
                )
        first = journal.read_journal(next((self.fx.operation_store / "operations").iterdir()))
        self.assertEqual(first["state"], "snapshot_saved")
        self.recover()
        final = journal.read_journal(next((self.fx.operation_store / "operations").iterdir()))
        self.assertEqual(final["state"], "completed")
        self.assertEqual(sum(event["action"] == "restart" for event in adapter.audit_events(self.adapter_root)), 1)

    def test_crash_before_r04_rename_aborts_without_publishing_and_cleans_temp(self):
        self.configure("active")
        self.patch_pipeline()
        original_publish = orchestrator.publisher.publish_operation
        def crash_before_rename(*args, **kwargs):
            return original_publish(*args, **kwargs, crash_at="before_rename")
        with mock.patch.object(orchestrator.publisher, "publish_operation", side_effect=crash_before_rename):
            with self.assertRaises(journal.SimulatedCrash):
                orchestrator.apply_operation(
                    staging_args=self.staging_args, service_root=self.fx.service_root,
                    operation_store=self.fx.operation_store, lifecycle_lock=self.fx.lifecycle_lock,
                    application_lock=self.fx.application_lock, lease_root=self.fx.lease_root,
                    service_uid=self.fx.service_uid, service_gid=self.fx.service_gid,
                    adapter_root=self.adapter_root, confirm_restart=True,
                )
        self.recover()
        final = journal.read_journal(next((self.fx.operation_store / "operations").iterdir()))
        self.assertEqual(final["state"], "aborted")
        self.assertEqual(self.fx.previous_config.read_bytes(), self.fx.previous_bytes)
        self.assertFalse(any(item.name.startswith(".tmp-") for item in self.fx.previous_config.parent.iterdir()))
        self.assertFalse(any(event["action"] == "restart" for event in adapter.audit_events(self.adapter_root)))

    def test_crash_after_publish_recovers_with_persisted_confirmation(self):
        with self.assertRaises(journal.SimulatedCrash):
            self.apply(crash_at="after_published")
        result = self.recover()
        self.assertEqual(result["status"], "RECOVERY_COMPLETE")
        record = journal.read_journal(next((self.fx.operation_store / "operations").iterdir()))
        self.assertEqual(record["state"], "completed")
        self.assertEqual(sum(event["action"] == "restart" for event in adapter.audit_events(self.adapter_root)), 1)

    def test_crash_after_restart_request_rolls_back_without_blind_retry(self):
        with self.assertRaises(journal.SimulatedCrash):
            self.apply(crash_at="after_restart_request")
        result = self.recover()
        record = journal.read_journal(next((self.fx.operation_store / "operations").iterdir()))
        self.assertEqual(record["state"], "rolled_back")
        self.assertFalse(any(event["action"] == "restart" for event in adapter.audit_events(self.adapter_root)))

    def test_crash_after_transition_is_reconciled_without_second_restart(self):
        with self.assertRaises(journal.SimulatedCrash):
            self.apply(crash_at="after_restart_transition")
        self.recover()
        record = journal.read_journal(next((self.fx.operation_store / "operations").iterdir()))
        self.assertEqual(record["state"], "completed")
        self.assertEqual(sum(event["action"] == "restart" for event in adapter.audit_events(self.adapter_root)), 1)

    def test_crash_after_verification_finishes_idempotently(self):
        with self.assertRaises(journal.SimulatedCrash):
            self.apply(crash_at="after_service_verified")
        self.recover()
        first = journal.read_journal(next((self.fx.operation_store / "operations").iterdir()))
        self.assertEqual(first["state"], "completed")
        second = self.recover()
        self.assertEqual(second["operations"][0]["status"], "NO_OP")

    def test_crash_after_r04_rollback_rename_is_recovered_idempotently(self):
        self.configure("active")
        self.patch_pipeline()
        original_rollback = orchestrator.publisher._rollback_locked
        def crash_after_rollback_rename(*args, **kwargs):
            kwargs["crash_at"] = "after_rollback_rename"
            return original_rollback(*args, **kwargs)
        with mock.patch.object(orchestrator.publisher, "_rollback_locked", side_effect=crash_after_rollback_rename):
            with self.assertRaises(journal.SimulatedCrash):
                orchestrator.apply_operation(
                    staging_args=self.staging_args, service_root=self.fx.service_root,
                    operation_store=self.fx.operation_store, lifecycle_lock=self.fx.lifecycle_lock,
                    application_lock=self.fx.application_lock, lease_root=self.fx.lease_root,
                    service_uid=self.fx.service_uid, service_gid=self.fx.service_gid,
                    adapter_root=self.adapter_root, confirm_restart=True,
                    restart_outcome="reject",
                )
        first = journal.read_journal(next((self.fx.operation_store / "operations").iterdir()))
        self.assertEqual(first["state"], "rollback_started")
        self.assertEqual(self.fx.previous_config.read_bytes(), self.fx.previous_bytes)
        self.recover()
        final = journal.read_journal(next((self.fx.operation_store / "operations").iterdir()))
        self.assertEqual(final["state"], "rolled_back")

    def test_crash_after_config_rollback_resumes_service_reconciliation(self):
        with self.assertRaises(journal.SimulatedCrash):
            self.apply(restart_outcome="failed_after", crash_at="after_rollback_config")
        first = journal.read_journal(next((self.fx.operation_store / "operations").iterdir()))
        self.assertEqual(first["state"], "rollback_config_restored")
        self.recover()
        final = journal.read_journal(next((self.fx.operation_store / "operations").iterdir()))
        self.assertEqual(final["state"], "rolled_back")
        self.assertEqual(adapter.status(self.adapter_root)["active_state"], "active")

    def test_crash_after_service_restore_is_idempotently_finalized(self):
        with self.assertRaises(journal.SimulatedCrash):
            self.apply(restart_outcome="failed_after", crash_at="after_service_restore")
        self.recover()
        final = journal.read_journal(next((self.fx.operation_store / "operations").iterdir()))
        self.assertEqual(final["state"], "rolled_back")
        self.assertEqual(final["orchestration"]["rollback"]["service_status"], "unchanged")

    def test_r03_and_r04_recovery_defer_schema_v2_to_r05(self):
        result = self.apply(confirm_restart=False)
        op_dir = self.fx.operation_store / "operations" / result["operation_id"]
        before = (op_dir / "journal.json").read_bytes()
        r03_result = self.fx.recover()
        r04_result = orchestrator.publisher.recover_publications(
            self.fx.operation_store, self.fx.lifecycle_lock, self.fx.application_lock
        )
        after = (op_dir / "journal.json").read_bytes()
        self.assertEqual(before, after)
        self.assertEqual(r03_result["operations"][0]["action"], "deferred_to_R04_R05_recovery")
        self.assertEqual(r04_result["operations"][0]["action"], "deferred_to_R05_recovery")
        self.assertEqual(journal.read_journal(op_dir)["state"], "published_pending_apply")

    def test_recovery_of_legacy_v1_journal_skips_without_rewriting(self):
        prepared = self.fx.prepare()
        path = pathlib.Path(prepared["operation_dir"]) / "journal.json"
        before = path.read_bytes()
        result = self.recover()
        after = path.read_bytes()
        self.assertEqual(result["operations"], [])
        self.assertEqual(before, after)
        self.assertEqual(journal.read_journal(path.parent)["schema_version"], 1)

    def test_generation_id_is_unique_across_terminal_journals(self):
        result = self.apply()
        record = self.record(result)
        with self.assertRaises(journal.RuntimeJournalError):
            journal.ensure_generation_unique(
                self.fx.operation_store / "operations",
                record["orchestration"]["generation_id"],
            )

    def test_v2_journal_rejects_untyped_orchestration_values(self):
        result = self.apply()
        path = self.fx.operation_store / "operations" / result["operation_id"]
        journal_path = path / "journal.json"
        record = json.loads(journal_path.read_text())
        record["orchestration"]["verification"]["status"] = []
        journal_path.write_text(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
        journal_path.chmod(0o600)
        with self.assertRaises(journal.RuntimeJournalError):
            journal.read_journal(path)

    def test_adapter_rejects_untyped_service_state(self):
        self.configure("active")
        state = adapter._read_regular(self.adapter_root / adapter.STATE_FILE)
        state["active_state"] = []
        adapter._atomic_write(self.adapter_root / adapter.STATE_FILE, state)
        with self.assertRaises(adapter.ServiceAdapterError):
            adapter.status(self.adapter_root)

    def test_adapter_rejects_symlinked_fixture_root(self):
        link = self.fx.base / "adapter-link"
        link.symlink_to(self.adapter_root, target_is_directory=True)
        with self.assertRaises(adapter.ServiceAdapterError):
            adapter.status(link)

    def test_adapter_serializes_concurrent_restart_and_audit_transactions(self):
        previous_generation = "generation-" + "a" * 32
        self.configure("active", loaded_generation_id=previous_generation)
        previous_hash = hashlib.sha256(self.fx.previous_bytes).hexdigest()
        context = multiprocessing.get_context("fork")
        worker_count = 6
        barrier = context.Barrier(worker_count)
        output = context.Queue()
        processes = []
        for suffix in ("b", "c"):
            generation = "generation-" + suffix * 32
            process = context.Process(
                target=_concurrent_restart_worker,
                args=(str(self.adapter_root), barrier, output, generation,
                      hashlib.sha256(("config-" + suffix).encode()).hexdigest(),
                      previous_generation, previous_hash),
            )
            processes.append(process)
        for _ in range(4):
            processes.append(context.Process(
                target=_concurrent_status_worker,
                args=(str(self.adapter_root), barrier, output),
            ))
        for process in processes:
            process.start()
        for process in processes:
            process.join(20)
            self.assertFalse(process.is_alive(), "worker concurrente quedó bloqueado")
            self.assertEqual(process.exitcode, 0)
        results = [output.get(timeout=5) for _ in range(worker_count)]
        self.assertFalse(any(kind == "error" for kind, _ in results), results)
        restart_results = [value["result"] for kind, value in results if kind == "restart"]
        self.assertCountEqual(restart_results, ["accepted", "rejected"])
        events = adapter.audit_events(self.adapter_root)
        self.assertEqual(len(events), worker_count)
        restart_events = [event for event in events if event["action"] == "restart"]
        self.assertCountEqual(
            [event["result"] for event in restart_events],
            ["accepted", "rejected_precondition"],
        )
        final_state = adapter.status(self.adapter_root)
        self.assertIn(final_state["loaded_generation_id"], {
            "generation-" + "b" * 32, "generation-" + "c" * 32,
        })

    def test_adapter_serializes_concurrent_restore_compare_and_swap(self):
        current_generation = "generation-" + "f" * 32
        current_hash = hashlib.sha256(b"published-config").hexdigest()
        previous_hash = hashlib.sha256(b"previous-config").hexdigest()
        self.configure("active", loaded_generation_id=current_generation,
                       loaded_config_sha256=current_hash)
        context = multiprocessing.get_context("fork")
        barrier = context.Barrier(2)
        output = context.Queue()
        processes = []
        for suffix in ("d", "e"):
            processes.append(context.Process(
                target=_concurrent_restore_worker,
                args=(str(self.adapter_root), barrier, output, current_generation,
                      current_generation, "generation-" + suffix * 32, previous_hash),
            ))
        for process in processes:
            process.start()
        for process in processes:
            process.join(20)
            self.assertFalse(process.is_alive(), "restore concurrente quedó bloqueado")
            self.assertEqual(process.exitcode, 0)
        results = [output.get(timeout=5) for _ in processes]
        self.assertFalse(any(kind == "error" for kind, _ in results), results)
        self.assertCountEqual(
            [value["result"] for kind, value in results if kind == "restore"],
            ["restored", "failed"],
        )
        events = [event for event in adapter.audit_events(self.adapter_root)
                  if event["action"] == "restore"]
        self.assertCountEqual(
            [event["result"] for event in events],
            ["restored", "rejected_precondition"],
        )
        final_generation = adapter.status(self.adapter_root)["loaded_generation_id"]
        self.assertIn(final_generation, {"generation-" + "d" * 32,
                                         "generation-" + "e" * 32})

    def test_adapter_rejects_symlinked_lock_file(self):
        self.configure("active")
        lock_path = self.adapter_root / adapter.LOCK_FILE
        lock_path.unlink()
        lock_path.symlink_to(self.adapter_root / adapter.MARKER)
        with self.assertRaises(adapter.ServiceAdapterError):
            adapter.status(self.adapter_root)

    def test_adapter_audit_is_generation_bound_and_contains_no_real_service_command(self):
        result = self.apply()
        events = adapter.audit_events(self.adapter_root)
        gen = result["generation_id"]
        restart_events = [event for event in events if event["action"] == "restart"]
        self.assertEqual(len(restart_events), 1)
        self.assertEqual(restart_events[0]["generation_id"], gen)
        self.assertNotIn("subprocess", adapter.__dict__)
        self.assertTrue(all(event["action"] in {"status", "start", "restart", "restore"} for event in events))


    def _apply_with_active_register(self, *, active_state="active", confirm_restart=True,
                                    restart_outcome="success", crash_at=None):
        self.configure(active_state)
        self.patch_pipeline()
        return orchestrator.apply_operation(
            staging_args=self.staging_args,
            service_root=self.fx.service_root,
            operation_store=self.fx.operation_store,
            lifecycle_lock=self.fx.lifecycle_lock,
            application_lock=self.fx.application_lock,
            lease_root=self.fx.lease_root,
            service_uid=self.fx.service_uid,
            service_gid=self.fx.service_gid,
            adapter_root=self.adapter_root,
            confirm_restart=confirm_restart,
            restart_outcome=restart_outcome,
            crash_at=crash_at,
            active_profile_store=self.fx.base / "active-profile-store",
        )

    def _seed_active_register(self):
        store = active_profiles.ActiveProfileStore(self.fx.base / "active-profile-store")
        record = {
            "schema_version": 1,
            "profile_id": "profile-" + "9" * 32,
            "revision": "r000009",
            "validation_id": "pvalidation-" + "8" * 32,
            "generation_id": "generation-" + "7" * 32,
            "config_sha256": "6" * 64,
            "operation_id": "runtime-op-" + "5" * 32,
            "applied_at": journal.now(),
            "service_unit": "xray.service",
            "service_state": "active",
            "config_target": "etc/xray/config.json",
        }
        store.set_active(record)
        return store, record

    def test_b4_active_register_written_only_after_verified_restart(self):
        result = self._apply_with_active_register()
        self.assertEqual(result["status"], "COMPLETED")
        record = active_profiles.ActiveProfileStore(
            self.fx.base / "active-profile-store"
        ).read()
        operation = self.record(result)
        self.assertEqual(record["profile_id"], operation["source"]["profile_id"])
        self.assertEqual(record["revision"], operation["source"]["revision"])
        self.assertEqual(record["validation_id"], operation["source"]["validation_id"])
        self.assertEqual(record["generation_id"], operation["orchestration"]["generation_id"])
        self.assertEqual(record["config_sha256"], operation["publication"]["config_sha256"])
        self.assertEqual(record["service_state"], "active")
        self.assertEqual(record["config_target"], "etc/xray/config.json")
        self.assertEqual(result["active_profile_record"]["status"], "ACTIVE_PROFILE_RECORDED")

    def test_b4_pending_apply_preserves_previous_active_register(self):
        store, previous = self._seed_active_register()
        result = self._apply_with_active_register(confirm_restart=False)
        self.assertEqual(result["status"], "PUBLISHED_PENDING_APPLY")
        self.assertEqual(store.read(), previous)

    def test_b4_inactive_pending_start_preserves_previous_active_register(self):
        store, previous = self._seed_active_register()
        result = self._apply_with_active_register(active_state="inactive")
        self.assertEqual(result["status"], "PUBLISHED_PENDING_START")
        self.assertEqual(store.read(), previous)
        self.assertFalse(any(event["action"] == "restart" for event in adapter.audit_events(self.adapter_root)))

    def test_b4_failed_restart_and_rollback_preserve_previous_active_register(self):
        store, previous = self._seed_active_register()
        result = self._apply_with_active_register(restart_outcome="reject")
        self.assertEqual(result["status"], "ROLLED_BACK")
        self.assertEqual(store.read(), previous)

    def test_b4_recovery_after_verified_service_transition_updates_register(self):
        with self.assertRaises(journal.SimulatedCrash):
            self._apply_with_active_register(crash_at="after_service_verified")
        self.assertIsNone(active_profiles.ActiveProfileStore(
            self.fx.base / "active-profile-store"
        ).read())
        recovered = orchestrator.recover_operations(
            operation_store=self.fx.operation_store,
            lifecycle_lock=self.fx.lifecycle_lock,
            application_lock=self.fx.application_lock,
            adapter_root=self.adapter_root,
            active_profile_store=self.fx.base / "active-profile-store",
        )
        self.assertEqual(recovered["operations"][0]["status"], "COMPLETED")
        record = active_profiles.ActiveProfileStore(
            self.fx.base / "active-profile-store"
        ).read()
        operation = journal.read_journal(next((self.fx.operation_store / "operations").iterdir()))
        self.assertEqual(record["generation_id"], operation["orchestration"]["generation_id"])
        self.assertEqual(record["config_sha256"], operation["publication"]["config_sha256"])

    def test_b4_recovery_reconciles_completed_journal_with_missing_register(self):
        result = self.apply()
        self.assertEqual(result["status"], "COMPLETED")
        recovered = orchestrator.recover_operations(
            operation_store=self.fx.operation_store,
            lifecycle_lock=self.fx.lifecycle_lock,
            application_lock=self.fx.application_lock,
            adapter_root=self.adapter_root,
            active_profile_store=self.fx.base / "active-profile-store",
        )
        self.assertEqual(recovered["operations"][0]["status"], "NO_OP")
        record = active_profiles.ActiveProfileStore(
            self.fx.base / "active-profile-store"
        ).read()
        self.assertEqual(record["generation_id"], result["generation_id"])

    def test_b4_active_register_rejects_symlinked_active_file(self):
        root = self.fx.base / "active-profile-store"
        store = active_profiles.ActiveProfileStore(root)
        store.prepare()
        target = self.fx.base / "outside-active.json"
        target.write_text("{}")
        target.chmod(0o600)
        (root / active_profiles.ACTIVE_FILE).symlink_to(target)
        with self.assertRaises(active_profiles.ActiveProfileError):
            store.read()

    def test_b4_completed_recovery_is_idempotent_for_active_register(self):
        result = self._apply_with_active_register()
        store = active_profiles.ActiveProfileStore(self.fx.base / "active-profile-store")
        first = store.read()
        recovered = orchestrator.recover_operations(
            operation_store=self.fx.operation_store,
            lifecycle_lock=self.fx.lifecycle_lock,
            application_lock=self.fx.application_lock,
            adapter_root=self.adapter_root,
            active_profile_store=self.fx.base / "active-profile-store",
        )
        second = store.read()
        self.assertEqual(first, second)
        self.assertEqual(recovered["operations"][0]["active_profile_record"]["status"], "ALREADY_RECORDED")
        self.assertEqual(result["status"], "COMPLETED")

    def test_b4_invalid_active_store_fails_before_publication_or_service_action(self):
        root = self.fx.base / "active-profile-store"
        root.mkdir(mode=0o700)
        marker = root / active_profiles.MARKER
        marker.write_text('{"schema_version":1,"purpose":"not-the-b4-fixture"}\\n')
        marker.chmod(0o600)
        self.configure("active")
        self.patch_pipeline()
        with self.assertRaises(active_profiles.ActiveProfileError):
            orchestrator.apply_operation(
                staging_args=self.staging_args, service_root=self.fx.service_root,
                operation_store=self.fx.operation_store, lifecycle_lock=self.fx.lifecycle_lock,
                application_lock=self.fx.application_lock, lease_root=self.fx.lease_root,
                service_uid=self.fx.service_uid, service_gid=self.fx.service_gid,
                adapter_root=self.adapter_root, confirm_restart=True,
                active_profile_store=root,
            )
        self.assertEqual(self.fx.previous_config.read_bytes(), self.fx.previous_bytes)
        self.assertFalse(any(event["action"] == "restart" for event in adapter.audit_events(self.adapter_root)))

    def _publish_inactive_for_b4_start(self):
        result = self.apply(active_state="inactive")
        self.assertEqual(result["status"], "PUBLISHED_PENDING_START")
        return result

    def test_b4_explicit_start_after_pending_start_verifies_and_records_profile(self):
        pending = self._publish_inactive_for_b4_start()
        result = orchestrator.start_pending_operation(
            operation_store=self.fx.operation_store,
            operation_id=pending["operation_id"],
            lifecycle_lock=self.fx.lifecycle_lock,
            application_lock=self.fx.application_lock,
            adapter_root=self.adapter_root,
            confirm_start=True,
            active_profile_store=self.fx.base / "active-profile-store",
        )
        self.assertEqual(result["status"], "COMPLETED")
        self.assertTrue(result["service_started"])
        state = adapter.status(self.adapter_root)
        self.assertEqual(state["active_state"], "active")
        self.assertEqual(state["loaded_generation_id"], pending["generation_id"])
        record = active_profiles.ActiveProfileStore(
            self.fx.base / "active-profile-store"
        ).read()
        self.assertEqual(record["generation_id"], pending["generation_id"])
        self.assertEqual(record["profile_id"], self.fx.staging_manifest["profile_id"])

    def test_b4_explicit_start_requires_confirmation_and_leaves_pending_state(self):
        pending = self._publish_inactive_for_b4_start()
        result = orchestrator.start_pending_operation(
            operation_store=self.fx.operation_store,
            operation_id=pending["operation_id"],
            lifecycle_lock=self.fx.lifecycle_lock,
            application_lock=self.fx.application_lock,
            adapter_root=self.adapter_root,
            confirm_start=False,
            active_profile_store=self.fx.base / "active-profile-store",
        )
        self.assertEqual(result["status"], "START_CONFIRMATION_REQUIRED")
        self.assertEqual(journal.read_journal(
            self.fx.operation_store / "operations" / pending["operation_id"]
        )["state"], "published_pending_start")
        self.assertEqual(adapter.status(self.adapter_root)["active_state"], "inactive")
        self.assertFalse(any(event["action"] == "start" for event in adapter.audit_events(self.adapter_root)))

    def test_b4_rejected_explicit_start_rolls_back_config_and_keeps_service_inactive(self):
        pending = self._publish_inactive_for_b4_start()
        result = orchestrator.start_pending_operation(
            operation_store=self.fx.operation_store,
            operation_id=pending["operation_id"],
            lifecycle_lock=self.fx.lifecycle_lock,
            application_lock=self.fx.application_lock,
            adapter_root=self.adapter_root,
            confirm_start=True,
            start_outcome="reject",
            active_profile_store=self.fx.base / "active-profile-store",
        )
        self.assertEqual(result["status"], "ROLLED_BACK")
        self.assertEqual(self.fx.previous_config.read_bytes(), self.fx.previous_bytes)
        self.assertEqual(adapter.status(self.adapter_root)["active_state"], "inactive")
        self.assertIsNone(active_profiles.ActiveProfileStore(
            self.fx.base / "active-profile-store"
        ).read())

    def test_b4_start_recovery_after_transition_does_not_start_twice(self):
        pending = self._publish_inactive_for_b4_start()
        with self.assertRaises(journal.SimulatedCrash):
            orchestrator.start_pending_operation(
                operation_store=self.fx.operation_store,
                operation_id=pending["operation_id"],
                lifecycle_lock=self.fx.lifecycle_lock,
                application_lock=self.fx.application_lock,
                adapter_root=self.adapter_root,
                confirm_start=True,
                active_profile_store=self.fx.base / "active-profile-store",
                crash_at="after_start_transition",
            )
        recovered = orchestrator.recover_operations(
            operation_store=self.fx.operation_store,
            lifecycle_lock=self.fx.lifecycle_lock,
            application_lock=self.fx.application_lock,
            adapter_root=self.adapter_root,
            active_profile_store=self.fx.base / "active-profile-store",
        )
        self.assertEqual(recovered["operations"][0]["status"], "COMPLETED")
        starts = [event for event in adapter.audit_events(self.adapter_root)
                  if event["action"] == "start"]
        self.assertEqual(len(starts), 1)
        record = active_profiles.ActiveProfileStore(
            self.fx.base / "active-profile-store"
        ).read()
        self.assertEqual(record["generation_id"], pending["generation_id"])

    def test_b4_start_requested_journal_is_deferred_to_r05_by_r03_and_r04(self):
        pending = self._publish_inactive_for_b4_start()
        with self.assertRaises(journal.SimulatedCrash):
            orchestrator.start_pending_operation(
                operation_store=self.fx.operation_store,
                operation_id=pending["operation_id"],
                lifecycle_lock=self.fx.lifecycle_lock,
                application_lock=self.fx.application_lock,
                adapter_root=self.adapter_root,
                confirm_start=True,
                crash_at="after_start_transition",
            )
        op_dir = self.fx.operation_store / "operations" / pending["operation_id"]
        before = (op_dir / "journal.json").read_bytes()
        r03_result = self.fx.recover()
        r04_result = orchestrator.publisher.recover_publications(
            self.fx.operation_store, self.fx.lifecycle_lock, self.fx.application_lock
        )
        after = (op_dir / "journal.json").read_bytes()
        self.assertEqual(before, after)
        self.assertEqual(r03_result["operations"][0]["action"], "deferred_to_R04_R05_recovery")
        self.assertEqual(r04_result["operations"][0]["action"], "deferred_to_R05_recovery")
        self.assertEqual(journal.read_journal(op_dir)["state"], "service_start_requested")
        self.recover()
        self.assertEqual(journal.read_journal(op_dir)["state"], "completed")

    def test_b4_start_failure_after_transition_fails_closed_without_active_record(self):
        pending = self._publish_inactive_for_b4_start()
        result = orchestrator.start_pending_operation(
            operation_store=self.fx.operation_store,
            operation_id=pending["operation_id"],
            lifecycle_lock=self.fx.lifecycle_lock,
            application_lock=self.fx.application_lock,
            adapter_root=self.adapter_root,
            confirm_start=True,
            start_outcome="failed_after",
            active_profile_store=self.fx.base / "active-profile-store",
        )
        self.assertEqual(result["status"], "RECOVERY_REQUIRED")
        self.assertEqual(self.fx.previous_config.read_bytes(), self.fx.previous_bytes)
        self.assertEqual(adapter.status(self.adapter_root)["active_state"], "failed")
        self.assertIsNone(active_profiles.ActiveProfileStore(
            self.fx.base / "active-profile-store"
        ).read())

    def test_b4_active_register_rejects_inactive_or_unverified_claim(self):
        store = active_profiles.ActiveProfileStore(self.fx.base / "active-profile-store")
        value = {
            "schema_version": 1,
            "profile_id": "profile-" + "a" * 32,
            "revision": "r000001",
            "validation_id": "pvalidation-" + "b" * 32,
            "generation_id": "generation-" + "c" * 32,
            "config_sha256": "d" * 64,
            "operation_id": "runtime-op-" + "e" * 32,
            "applied_at": journal.now(),
            "service_unit": "xray.service",
            "service_state": "inactive",
            "config_target": "etc/xray/config.json",
        }
        with self.assertRaises(active_profiles.ActiveProfileError):
            store.set_active(value)

if __name__ == "__main__":
    unittest.main()
