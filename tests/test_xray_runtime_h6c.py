from __future__ import annotations
import hashlib, json, pathlib, sys, tempfile, unittest
from argparse import Namespace
from unittest import mock

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts")); sys.path.insert(0,str(ROOT/"tests"))
import test_xray_runtime_journal as journal_helpers
import xray_runtime_attestation as attestation
import xray_runtime_journal as journal
import xray_runtime_journal as journal
import xray_runtime_orchestrator as orchestrator
import xray_runtime_service_adapter as fixture_adapter

class MockRuntimeBackend:
    RUNTIME_BACKEND_TEST_ONLY=True
    ServiceAdapterError=fixture_adapter.ServiceAdapterError
    def __init__(self, store, unit_file):
        self.attestation_store=store; self.attestation_unit_file=unit_file
        self.snapshots=[]
    def status(self,*args,**kwargs): return fixture_adapter.status(*args,**kwargs)
    def start(self,*args,**kwargs): return fixture_adapter.start(*args,**kwargs)
    def restart(self,*args,**kwargs): return fixture_adapter.restart(*args,**kwargs)
    def restore(self,*args,**kwargs): return fixture_adapter.restore(*args,**kwargs)
    def attestation_snapshot(self,stage,record):
        gen=record["orchestration"]["generation_id"]
        digest=record["publication"]["config_sha256"]
        initial=record["orchestration"]["initial_service"]["active_state"]
        if stage=="before":
            invocation="a"*32 if initial=="active" else None
            state=initial
        else:
            invocation="b"*32
            state="active"
        value={
            "load_state":"loaded","active_state":state,
            "sub_state":"running" if state=="active" else "dead",
            "result":"success" if state=="active" else "success",
            "exec_main_status":"0","main_pid":4321 if state=="active" else 0,
            "user":"xray","group":"xray","fragment_path":str(self.attestation_unit_file),
            "runtime_config_sha256":digest,"invocation_id":invocation,
            "active_enter_timestamp":"Thu 2026-11-05 18:00:00 -05" if state=="active" else "n/a"
        }
        self.snapshots.append((stage,value))
        return value

class H6CIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.fx=journal_helpers.RuntimeJournalTests("test_snapshot_and_journal_capture_exact_profile_and_previous_runtime")
        self.fx.setUp()
        self.addCleanup(self.fx.tearDown)
        self.adapter_root=self.fx.base/"r05-adapter"
        self.staging_args=Namespace(
            profile_store="/fixture/profiles",master_key="/fixture/key",
            validation_store="/fixture/validation",profile_id=self.fx.staging_manifest["profile_id"],
            revision=self.fx.staging_manifest["revision"],xray_binary=str(self.fx.binary),
            service_state=str(self.fx.service_state),timeout=20)
        self.patches=[]
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base=pathlib.Path(self.temp.name)
        self.store_root=base/"attestations"; self.store_root.mkdir(mode=0o700); self.store_root.chmod(0o700)
        self.unit=base/"xray.service"
        self.unit.write_text("[Unit]\\n[Service]\\nUser=xray\\nGroup=xray\\n"
            "ExecStartPre=/usr/local/bin/xray run -test -config /etc/xray/config.json\\n"
            "ExecStart=/usr/local/bin/xray run -config /etc/xray/config.json\\n"
            "NoNewPrivileges=true\\nProtectSystem=strict\\n",encoding="utf-8")
        self.unit.chmod(0o644)
        self.store=attestation.AttestationStore(self.store_root)
        self.backend=MockRuntimeBackend(self.store,self.unit)
    def tearDown(self):
        for patcher in reversed(self.patches): patcher.stop()
    def configure(self,state):
        sub={"active":"running","inactive":"dead"}[state]
        self.fx.write_service_fixture(active_state=state,sub_state=sub)
        previous_hash=hashlib.sha256(self.fx.previous_bytes).hexdigest() if state=="active" else None
        fixture_adapter.create_fixture(self.adapter_root,active_state=state,sub_state=sub,
            loaded_generation_id=None,loaded_config_sha256=previous_hash)
    def patch_pipeline(self):
        def preflight(*args): return {"service_fixture":json.loads(self.fx.service_state.read_text())}
        for patcher in [
            mock.patch.object(orchestrator.preflight,"preflight",side_effect=preflight),
            mock.patch.object(orchestrator.staging,"stage",return_value={"status":"STAGED","staging_dir":str(self.fx.staging_dir)})
        ]:
            patcher.start(); self.patches.append(patcher)
    def apply(self,state,confirm=True,crash_at=None):
        self.configure(state); self.patch_pipeline()
        return orchestrator.apply_operation(
            staging_args=self.staging_args,service_root=self.fx.service_root,
            operation_store=self.fx.operation_store,lifecycle_lock=self.fx.lifecycle_lock,
            application_lock=self.fx.application_lock,lease_root=self.fx.lease_root,
            service_uid=self.fx.service_uid,service_gid=self.fx.service_gid,
            adapter_root=self.adapter_root,confirm_restart=confirm,crash_at=crash_at,
            service_backend=self.backend)
    def record(self,result):
        return orchestrator.inspect_operation(self.fx.operation_store,result["operation_id"])
    def test_restart_uses_injected_backend_and_persists_h6b_attestation(self):
        result=self.apply("active")
        self.assertEqual(result["status"],"COMPLETED")
        self.assertEqual(result["runtime_attestation"]["status"],"ATTESTED")
        evidence=result["runtime_attestation"]["attestation"]
        self.assertEqual(evidence["operation_id"],result["operation_id"])
        self.assertEqual(evidence["generation_id"],result["generation_id"])
        self.assertEqual(evidence["config_sha256"],result["config_sha256"])
        self.assertEqual([x[0] for x in self.backend.snapshots],["before","after","confirmed"])
        self.assertEqual(self.store.read(result["operation_id"]),evidence)
    def test_attestation_divergence_causes_fail_closed_rollback(self):
        original=self.backend.attestation_snapshot
        def divergent(stage,record):
            value=original(stage,record)
            if stage=="confirmed": value=dict(value,invocation_id="c"*32)
            return value
        self.backend.attestation_snapshot=divergent
        result=self.apply("active")
        self.assertEqual(result["status"],"ROLLED_BACK")
        self.assertIsNone(self.store.read(result["operation_id"]))
        state=fixture_adapter.status(self.adapter_root)
        self.assertEqual(state["loaded_config_sha256"],hashlib.sha256(self.fx.previous_bytes).hexdigest())
    def test_start_path_attests_only_after_explicit_confirmation(self):
        pending=self.apply("inactive")
        self.assertEqual(pending["status"],"PUBLISHED_PENDING_START")
        self.assertEqual(self.backend.snapshots,[])
        result=orchestrator.start_pending_operation(
            operation_store=self.fx.operation_store,operation_id=pending["operation_id"],
            lifecycle_lock=self.fx.lifecycle_lock,application_lock=self.fx.application_lock,
            adapter_root=self.adapter_root,confirm_start=True,service_backend=self.backend)
        self.assertEqual(result["status"],"COMPLETED")
        self.assertEqual(result["runtime_attestation"]["status"],"ATTESTED")
        self.assertEqual([x[0] for x in self.backend.snapshots],["before","after","confirmed"])
    def test_recovery_after_attestation_persisted_is_idempotent(self):
        with self.assertRaises(journal.SimulatedCrash):
            self.apply("active",crash_at="after_service_verified")
        result=orchestrator.recover_operations(operation_store=self.fx.operation_store,
            lifecycle_lock=self.fx.lifecycle_lock,application_lock=self.fx.application_lock,
            adapter_root=self.adapter_root,service_backend=self.backend)
        recovered=result["operations"][0]
        self.assertEqual(recovered["status"],"COMPLETED")
        self.assertEqual(recovered["runtime_attestation"]["status"],"ATTESTED_RECOVERED")
    def test_recovery_without_attestation_fails_closed(self):
        with self.assertRaises(journal.SimulatedCrash):
            self.apply("active",crash_at="after_restart_transition")
        result=orchestrator.recover_operations(operation_store=self.fx.operation_store,
            lifecycle_lock=self.fx.lifecycle_lock,application_lock=self.fx.application_lock,
            adapter_root=self.adapter_root,service_backend=self.backend)
        recovered=result["operations"][0]
        self.assertEqual(recovered["status"],"RECOVERY_REQUIRED")
        self.assertIn("sin atestación",recovered["reason"])
    def test_backend_context_is_reset_after_call(self):
        self.apply("active")
        self.assertIs(orchestrator._service_backend(),fixture_adapter)
    def test_unmarked_backend_is_rejected_before_execution(self):
        class Untrusted:
            status=fixture_adapter.status
            start=fixture_adapter.start
            restart=fixture_adapter.restart
            restore=fixture_adapter.restore
            ServiceAdapterError=fixture_adapter.ServiceAdapterError
        self.configure("active")
        with self.assertRaises(orchestrator.RuntimeOrchestrationError):
            orchestrator.recover_operations(operation_store=self.fx.operation_store,
                lifecycle_lock=self.fx.lifecycle_lock,application_lock=self.fx.application_lock,
                adapter_root=self.adapter_root,service_backend=Untrusted())

if __name__=="__main__": unittest.main()
