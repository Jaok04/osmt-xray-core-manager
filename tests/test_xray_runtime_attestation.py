from __future__ import annotations
import hashlib, pathlib, sys, tempfile, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import xray_runtime_attestation as att

class AttestationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.base=pathlib.Path(self.tmp.name)
        self.root=self.base/"store"; self.root.mkdir(mode=0o700); self.root.chmod(0o700)
        self.unit=self.base/"xray.service"; self.unit.write_text("[Unit]\n[Service]\nUser=xray\n"); self.unit.chmod(0o644)
        self.hash=hashlib.sha256(b"config").hexdigest()
        self.opid="runtime-op-"+"1"*32; self.gen="generation-"+"2"*32
        self.old="a"*32; self.new="b"*32
        self.op={"operation_id":self.opid,"state":"service_restart_requested",
          "publication":{"status":"published","config_sha256":self.hash},
          "orchestration":{"generation_id":self.gen,"phase":"restart_requested","confirmation":"accepted",
            "initial_service":{"active_state":"active"},
            "request":{"generation_id":self.gen,"action":"restart","requested_at":"2026-11-06T00:00:00Z","result":"accepted"}}}
        self.before=self.obs(self.old,"active"); self.after=self.obs(self.new,"active"); self.confirmed=dict(self.after)
        self.store=att.AttestationStore(self.root)
    def tearDown(self): self.tmp.cleanup()
    def obs(self,inv,state):
        value = {"load_state":"loaded","active_state":state,"sub_state":"running","result":"success",
          "exec_main_status":"0","main_pid":1234,"user":"xray","group":"xray","fragment_path":str(self.unit),
          "runtime_config_sha256":self.hash,"invocation_id":inv,"active_enter_timestamp":"Thu 2026-11-05 18:00:00 -05"}
        if state == "active":
            value["process_identity"] = {
                "pid":1234,"process_starttime_ticks":45678,
                "executable_path":"/usr/local/bin/xray","executable_sha256":"c"*64,
                "effective_uid":991,"effective_gid":991,
                "argv":["/usr/local/bin/xray","run","-config","/etc/xray/config.json"],
                "identity_verified":True,"read_only":True,
                "configuration_loaded":False,"configuration_evidence":"not_attested"
            }
        return value
    def build(self): return att.build_attestation(self.op,self.before,self.after,self.confirmed,self.unit)
    def test_build_and_hash_unit(self):
        value=self.build()
        self.assertEqual(value["config_sha256"],self.hash)
        self.assertEqual(value["unit_fragment_sha256"],hashlib.sha256(self.unit.read_bytes()).hexdigest())
        self.assertEqual(value["invocation_id"],self.new)
        self.assertEqual(value["schema_version"],2)
        self.assertEqual(value["process_identity"]["pid"],1234)
        self.assertEqual(value["process_identity"]["starttime_ticks"],45678)
    def test_persist_read_and_mode(self):
        result=self.store.record(self.op,self.before,self.after,self.confirmed,self.unit)
        self.assertEqual(result["status"],"ATTESTED")
        path=self.root/(self.opid+".json")
        self.assertEqual(path.stat().st_mode&0o777,0o600)
        self.assertEqual(self.store.read(self.opid),result["attestation"])
    def test_rejects_unaccepted_operation(self):
        self.op["orchestration"]["confirmation"]="pending"
        with self.assertRaises(att.AttestationError): self.build()
    def test_rejects_wrong_phase(self):
        self.op["orchestration"]["phase"]="completed"
        with self.assertRaises(att.AttestationError): self.build()
    def test_rejects_hash_before_and_after(self):
        self.before["runtime_config_sha256"]="0"*64
        with self.assertRaises(att.AttestationError): self.build()
        self.before=self.obs(self.old,"active"); self.after["runtime_config_sha256"]="0"*64
        with self.assertRaises(att.AttestationError): self.build()
    def test_rejects_invocation_not_changed_or_unstable(self):
        self.after["invocation_id"]=self.old; self.confirmed=dict(self.after)
        with self.assertRaises(att.AttestationError): self.build()
        self.after=self.obs(self.new,"active"); self.confirmed=dict(self.after); self.confirmed["invocation_id"]="c"*32
        with self.assertRaises(att.AttestationError): self.build()
    def test_rejects_timestamp_instability(self):
        self.confirmed["active_enter_timestamp"]="different"
        with self.assertRaises(att.AttestationError): self.build()
    def test_rejects_missing_process_identity(self):
        self.after.pop("process_identity")
        with self.assertRaises(att.AttestationError): self.build()

    def test_rejects_process_pid_mismatch(self):
        self.after["process_identity"]["pid"] = 9876
        self.confirmed = dict(self.after)
        with self.assertRaises(att.AttestationError): self.build()

    def test_rejects_process_identity_change_after_confirmed(self):
        self.confirmed["process_identity"] = dict(self.confirmed["process_identity"],
                                                  process_starttime_ticks=45679)
        with self.assertRaises(att.AttestationError): self.build()

    def test_rejects_inactive_post_transition(self):
        self.after["active_state"]="failed"
        with self.assertRaises(att.AttestationError): self.build()
    def test_rejects_unit_path_mismatch(self):
        self.after["fragment_path"]="/run/systemd/generator/xray.service"
        with self.assertRaises(att.AttestationError): self.build()
    def test_rejects_unit_symlink_and_permissions(self):
        target=self.base/"target"; target.write_text("unit"); target.chmod(0o644)
        self.unit.unlink(); self.unit.symlink_to(target)
        with self.assertRaises(att.AttestationError): self.build()
    def test_start_path(self):
        op={"operation_id":self.opid,"state":"service_start_requested",
          "publication":{"status":"published","config_sha256":self.hash},
          "orchestration":{"generation_id":self.gen,"phase":"start_requested","confirmation":"accepted",
            "initial_service":{"active_state":"inactive"},
            "request":{"generation_id":self.gen,"action":"start","requested_at":"now","result":"accepted"}}}
        before=self.obs("","inactive"); after=self.obs(self.new,"active")
        value=att.build_attestation(op,before,after,dict(after),self.unit)
        self.assertEqual(value["invocation_id"],self.new)
        self.assertEqual(value["schema_version"],2)
        self.assertEqual(value["process_identity"]["pid"],1234)
        self.assertEqual(value["process_identity"]["starttime_ticks"],45678)
    def test_rejects_symlink_store(self):
        other=self.base/"other"; other.mkdir(mode=0o700)
        link=self.base/"link"; link.symlink_to(other,target_is_directory=True)
        with self.assertRaises(att.AttestationError): att.AttestationStore(link).read(self.opid)

if __name__=="__main__": unittest.main()
