#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, pathlib, sys, tempfile, threading, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import xray_validation_store as storemod
import xray_validation_history as historymod

A, B = "config-" + "1"*32, "config-" + "2"*32
def report(result="PASS", created="2026-11-04T18:00:00Z", checks=None, digest="a"*64, version="Xray 26.10.31"):
    return {"schema_version":1,"created_at":created,"content_sha256":digest,"content_size_bytes":10,
      "checks":checks or [{"name":"json_syntax","status":"PASS","errors":[],"warnings":[],"details":{}},
                          {"name":"xray_native","status":"PASS","errors":[],"warnings":[],"details":{}}],
      "xray":{"version":version,"binary_sha256":"b"*64},"result":result}
class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=pathlib.Path(self.tmp.name)/"validation"
        self.store=storemod.ValidationReportStore(self.root); self.svc=historymod.ValidationHistoryService(store=self.store)
    def tearDown(self): self.tmp.cleanup()
    def save(self, cid=A, rev="r000001", **kw): return self.store.save_report(cid,rev,report(**kw))
    def test_h01_empty(self): self.assertEqual(self.svc.list_history()["total"],0)
    def test_h02_multiple(self): self.save(); self.save(rev="r000002"); self.assertEqual(self.svc.list_history()["total"],2)
    def test_h03_filter_config(self): self.save(); self.save(B); self.assertEqual(self.svc.list_history(config_id=A)["total"],1)
    def test_h04_filter_revision(self): self.save(rev="r000001"); self.save(rev="r000002"); self.assertEqual(self.svc.list_history(revision="r000002")["total"],1)
    def test_h05_date_from(self): self.save(created="2026-11-03T18:00:00Z"); self.save(created="2026-11-04T18:00:00Z"); self.assertEqual(self.svc.list_history(date_from="2026-11-04T00:00:00Z")["total"],1)
    def test_h06_date_to(self): self.save(created="2026-11-03T18:00:00Z"); self.save(created="2026-11-04T18:00:00Z"); self.assertEqual(self.svc.list_history(date_to="2026-11-03T23:59:59Z")["total"],1)
    def test_h07_date_interval(self): self.save(created="2026-11-02T00:00:00Z"); self.save(created="2026-11-03T12:00:00Z"); self.save(created="2026-11-04T00:00:00Z"); self.assertEqual(self.svc.list_history(date_from="2026-11-03T00:00:00Z",date_to="2026-11-03T23:59:59Z")["total"],1)
    def test_h08_type(self): self.save(); self.assertEqual(self.svc.list_history(validation_type="static_and_native")["total"],1)
    def test_h09_result(self): self.save(result="FAIL"); self.save(result="PASS"); self.assertEqual(self.svc.list_history(result="FAIL")["total"],1)
    def test_h10_order(self): self.save(created="2026-11-03T00:00:00Z"); self.save(created="2026-11-04T00:00:00Z"); rows=self.svc.list_history()["reports"]; self.assertGreater(rows[0]["created_at"],rows[1]["created_at"])
    def test_h11_pagination(self):
        for n in range(3): self.save(rev=f"r{n+1:06d}",created=f"2026-11-0{n+1}T00:00:00Z")
        self.assertEqual(len(self.svc.list_history(limit=1,offset=1)["reports"]),1)
    def test_h12_limit_bounds(self):
        with self.assertRaises(historymod.ValidationHistoryError): self.svc.list_history(limit=1001)
    def test_h13_invalid_date(self):
        with self.assertRaises(historymod.ValidationHistoryError): self.svc.list_history(date_from="not-a-date")
    def test_h14_missing_report(self):
        with self.assertRaises(historymod.ValidationHistoryError): self.svc.get_report_detail("validation-"+"f"*32)
    def test_h15_detail(self): saved=self.save(); self.assertEqual(self.svc.get_report_detail(saved["validation_id"])["result"],"PASS")
    def test_h16_deleted_config_independent(self): saved=self.save(); self.assertEqual(self.svc.get_report_detail(saved["validation_id"])["config_id"],A)
    def test_h17_errors(self):
        c=[{"name":"json_syntax","status":"FAIL","errors":["bad"],"warnings":[],"details":{}}]
        saved=self.save(checks=c); self.assertEqual(self.svc.get_report_detail(saved["validation_id"])["checks"][0]["errors"],["bad"])
    def test_h18_warnings(self):
        c=[{"name":"json_syntax","status":"PASS","errors":[],"warnings":["notice"],"details":{}}]
        saved=self.save(checks=c); self.assertEqual(self.svc.get_report_detail(saved["validation_id"])["checks"][0]["warnings"],["notice"])
    def test_h19_identical_compare(self):
        a=self.save(); b=self.save(); diff=self.svc.compare_reports(a["validation_id"],b["validation_id"]); self.assertFalse(diff["summary"]["result_changed"])
    def test_h20_results_differ(self):
        a=self.save(result="PASS"); b=self.save(result="FAIL"); self.assertTrue(self.svc.compare_reports(a["validation_id"],b["validation_id"])["summary"]["result_changed"])
    def test_h21_check_added(self):
        a=self.save(); c=report()["checks"]+[{"name":"extra","status":"PASS","errors":[],"warnings":[],"details":{}}]; b=self.save(checks=c)
        self.assertEqual(self.svc.compare_reports(a["validation_id"],b["validation_id"])["summary"]["checks_added"],["extra"])
    def test_h22_check_removed(self):
        a=self.save(); c=report()["checks"][:1]; b=self.save(checks=c)
        self.assertEqual(self.svc.compare_reports(a["validation_id"],b["validation_id"])["summary"]["checks_removed"],["xray_native"])
    def test_h23_status_changed(self):
        c=[{"name":"json_syntax","status":"PASS","errors":[],"warnings":[],"details":{}}]; a=self.save(checks=c)
        c2=[{"name":"json_syntax","status":"FAIL","errors":[],"warnings":[],"details":{}}]; b=self.save(checks=c2)
        self.assertIn("status",self.svc.compare_reports(a["validation_id"],b["validation_id"])["summary"]["checks_changed"][0]["fields"])
    def test_h24_errors_changed(self):
        a=self.save(checks=[{"name":"json_syntax","status":"FAIL","errors":["a"],"warnings":[],"details":{}}])
        b=self.save(checks=[{"name":"json_syntax","status":"FAIL","errors":["b"],"warnings":[],"details":{}}])
        self.assertIn("errors",self.svc.compare_reports(a["validation_id"],b["validation_id"])["summary"]["checks_changed"][0]["fields"])
    def test_h25_warnings_changed(self):
        a=self.save(checks=[{"name":"json_syntax","status":"PASS","errors":[],"warnings":["a"],"details":{}}])
        b=self.save(checks=[{"name":"json_syntax","status":"PASS","errors":[],"warnings":["b"],"details":{}}])
        self.assertIn("warnings",self.svc.compare_reports(a["validation_id"],b["validation_id"])["summary"]["checks_changed"][0]["fields"])
    def test_h26_hash_changed(self):
        a=self.save(digest="a"*64); b=self.save(digest="c"*64)
        self.assertTrue(self.svc.compare_reports(a["validation_id"],b["validation_id"])["summary"]["content_changed"])
    def test_h27_xray_changed(self):
        a=self.save(version="Xray old"); b=self.save(version="Xray new")
        self.assertTrue(self.svc.compare_reports(a["validation_id"],b["validation_id"])["summary"]["xray_version_changed"])
    def test_h28_different_config_rejected(self):
        a=self.save(A); b=self.save(B)
        with self.assertRaises(historymod.ValidationHistoryError): self.svc.compare_reports(a["validation_id"],b["validation_id"])
    def test_h29_bad_id(self):
        with self.assertRaises(historymod.ValidationHistoryError): self.svc.get_report_detail("../bad")
    def test_h30_tampered_report(self):
        saved=self.save(); p=self.root/"reports"/(saved["validation_id"]+".json"); p.write_text("{}\n"); p.chmod(0o600)
        with self.assertRaises(storemod.ValidationStoreError): self.svc.list_history()
    def test_h31_tampered_catalog(self):
        self.save(); p=self.root/"catalog.json"; p.write_text("{}\n"); p.chmod(0o600)
        with self.assertRaises(storemod.ValidationStoreError): self.svc.list_history()
    def test_h32_unexpected_file(self):
        self.save(); p=self.root/"reports"/"unexpected.json"; p.write_text("{}\n"); p.chmod(0o600)
        with self.assertRaises(storemod.ValidationStoreError): self.svc.list_history()
    def test_h33_symlink_directory(self):
        self.store.prepare(); d=self.root/"reports"; d.rmdir(); other=pathlib.Path(self.tmp.name)/"other"; other.mkdir(mode=0o700); d.symlink_to(other,target_is_directory=True)
        with self.assertRaises(storemod.ValidationStoreError): self.svc.list_history()
    def test_h34_pending_wal_recovery(self):
        import os, signal, subprocess
        code = r"""
import os, pathlib, signal, sys
sys.path.insert(0, sys.argv[1] + "/scripts")
import xray_validation_store as m
root = pathlib.Path(sys.argv[2])
original = m._atomic_write
def crash(path, data, **kwargs):
    result = original(path, data, **kwargs)
    if pathlib.Path(path) == root / "catalog.json":
        os.kill(os.getpid(), signal.SIGKILL)
    return result
m._atomic_write = crash
s = m.ValidationReportStore(root)
s.save_report("config-" + "1"*32, "r000001", {
 "schema_version":1,"created_at":"2026-11-04T18:00:00Z",
 "content_sha256":"a"*64,"content_size_bytes":1,"result":"PASS",
 "checks":[{"name":"json_syntax","status":"PASS","errors":[],"warnings":[],"details":{}}],"xray":{}
})
"""
        proc=subprocess.run([sys.executable,"-c",code,str(ROOT),str(self.root)])
        self.assertEqual(proc.returncode,-signal.SIGKILL)
        self.assertTrue(self.store.wal_path.exists())
        self.assertEqual(self.svc.list_history()["total"],0)
        self.assertFalse(self.store.wal_path.exists())
    def test_h35_concurrent_reads(self):
        self.save(); errors=[]
        def read():
            try: self.svc.list_history()
            except Exception as exc: errors.append(exc)
        threads=[threading.Thread(target=read) for _ in range(6)]
        [t.start() for t in threads]; [t.join() for t in threads]; self.assertEqual(errors,[])
    def test_h36_secrets_sanitized(self):
        a=self.save(checks=[{"name":"json_syntax","status":"PASS","errors":[],"warnings":["token=syntheticsecret"],"details":{}}])
        value=self.svc.get_report_detail(a["validation_id"])["checks"][0]["warnings"][0]
        self.assertNotIn("syntheticsecret",value)
    def test_h37_read_only(self):
        self.save(); before={p.name:p.read_bytes() for p in self.root.iterdir() if p.is_file()}
        self.svc.list_history()
        after={p.name:p.read_bytes() for p in self.root.iterdir() if p.is_file()}
        self.assertEqual(before,after)
    def test_h38_restart_process(self):
        self.save(); other=historymod.ValidationHistoryService(str(self.root))
        self.assertEqual(other.list_history()["total"],1)
if __name__=="__main__": unittest.main(verbosity=2)
