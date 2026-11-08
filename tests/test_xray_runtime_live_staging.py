from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import xray_runtime_live_staging as live

REAL_SERVICE_IDENTITY = live._service_identity


class LiveStagingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = pathlib.Path(self.tmp.name)
        self.base.chmod(0o755)
        self.run_dir = self.base / "run"
        self.run_dir.mkdir(mode=0o755)
        self.state = self.base / "state"
        self.state.mkdir(mode=0o700)
        self.bindings_root = self.state / "profile-bindings"
        self.bindings_root.mkdir(mode=0o700)
        self.profile_id = "profile-" + "a" * 32
        self.revision = "r000001"
        self.profile_dir = self.bindings_root / self.profile_id
        self.profile_dir.mkdir(mode=0o700)
        self.mapping = self.profile_dir / (self.revision + ".json")
        self.binding_doc = {
            "schema_version": 1,
            "bindings": [{"inbound_tag": "vless-ws-tls-in", "connection_id": "conn-live-01"}],
        }
        self.mapping_bytes = (json.dumps(self.binding_doc, sort_keys=True, separators=(",", ":")) + "\n").encode()
        self.mapping.write_bytes(self.mapping_bytes)
        self.mapping.chmod(0o600)
        self.profile_content = (json.dumps({
            "inbounds": [{
                "tag": "vless-ws-tls-in", "listen": "0.0.0.0", "port": 443,
                "protocol": "vless", "settings": {"clients": [], "decryption": "none"},
                "streamSettings": {"network": "ws", "security": "tls", "tlsSettings": {}},
            }],
            "outbounds": [{"tag": "direct", "protocol": "freedom", "settings": {}}],
        }, sort_keys=True, separators=(",", ":")) + "\n").encode()
        self.validation = {
            "status": "PROFILE_PREFLIGHT_PASS", "profile_id": self.profile_id,
            "revision": self.revision, "validation_id": "pvalidation-" + "b" * 32,
            "content_sha256": hashlib.sha256(self.profile_content).hexdigest(),
            "profile_content": self.profile_content,
            "xray": {"path": "/usr/local/bin/xray", "sha256": "c" * 64, "size_bytes": 1234},
        }
        self.systemd = {
            "unit": "xray.service", "load_state": "loaded", "active_state": "inactive",
            "fragment_path": "/etc/systemd/system/xray.service", "user": "xray", "group": "xray",
            "read_only": True, "need_daemon_reload": "no", "drop_in_paths": "",
            "service_type": "simple", "unit_file_state": "enabled",
            "result": "success", "exec_main_status": "0",
            "invocation_id": None, "main_pid": None,
            "runtime_config_sha256": None, "generation_evidence": "not_attested",
            "loaded_generation_id": None,
        }
        self.lease_root = self.run_dir / "leases"
        self.staging_root = self.run_dir / "staging"
        self.lock_file = self.run_dir / "stage.lock"
        self.patches = [
            mock.patch.object(live, "PROFILE_STORE", self.state / "profiles"),
            mock.patch.object(live, "MASTER_KEY", self.state / "master.key"),
            mock.patch.object(live, "VALIDATION_STORE", self.state / "validations"),
            mock.patch.object(live, "BINDINGS_ROOT", self.bindings_root),
            mock.patch.object(live, "CONNECTIONS_CATALOG", self.state / "connections.json"),
            mock.patch.object(live, "CONNECTIONS_BASE", self.state / "connections"),
            mock.patch.object(live, "VMESS_BASE", self.state / "vmess"),
            mock.patch.object(live, "CONNECTION_LOCK", self.run_dir / "connections.lock"),
            mock.patch.object(live, "CERTIFICATE_BASE", self.state / "certificates"),
            mock.patch.object(live, "CERTIFICATE_CATALOG", self.state / "certificates/catalog.json"),
            mock.patch.object(live, "CERTIFICATE_MANAGED", self.state / "certificates/managed"),
            mock.patch.object(live, "CERTIFICATE_SECRETS", self.state / "certificates/secrets"),
            mock.patch.object(live, "CERTIFICATE_LOCK", self.run_dir / "certificates.lock"),
            mock.patch.object(live, "CERTIFICATE_MASTER_KEY", self.state / "master.key"),
            mock.patch.object(live, "LEASE_ROOT", self.lease_root),
            mock.patch.object(live, "STAGING_ROOT", self.staging_root),
            mock.patch.object(live, "LOCK_FILE", self.lock_file),
            mock.patch.object(live, "XRAY_BINARY", pathlib.Path("/usr/local/bin/xray")),
            mock.patch.object(live, "UNIT_FILE", pathlib.Path("/etc/systemd/system/xray.service")),
            mock.patch.object(live, "CONFIG_FILE", pathlib.Path("/etc/xray/config.json")),
            mock.patch.object(live.xray_runtime_preflight, "preflight_profile", return_value=self.validation),
            mock.patch.object(live.xray_runtime_systemd_adapter, "status", return_value=self.systemd),
            mock.patch.object(live, "_service_identity", return_value=(65534, 65534)),
            mock.patch.object(live.staging_fixture, "_connection_certificate_id", return_value=("cert-central-01", "vless")),
            mock.patch.object(live.staging_fixture, "_service_run"),
        ]
        for patcher in self.patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    def tearDown(self):
        self.tmp.cleanup()

    def fake_prepare(self, **kwargs):
        lease_id = "resolve-" + "d" * 32
        return {
            "status": "prepared", "lease_id": lease_id,
            "connection_id": kwargs["connection_id"], "protocol": "vless",
            "certificate_id": kwargs["certificate_id"],
            "certificate_file": str(self.lease_root / lease_id / "certificate.pem"),
            "key_file": str(self.lease_root / lease_id / "private-key.pem"),
        }

    def test_live_staging_prepares_config_without_publishing_or_starting(self):
        with mock.patch.object(live.certificate_resolver, "prepare", side_effect=self.fake_prepare) as prepare:
            result = live.stage_live(self.profile_id, self.revision)
        self.assertEqual(result["status"], "STAGED")
        self.assertFalse(result["runtime_published"])
        self.assertFalse(result["service_started"])
        prepare.assert_called_once()
        config = json.loads(pathlib.Path(result["config_path"]).read_text())
        cert = config["inbounds"][0]["streamSettings"]["tlsSettings"]["certificates"][0]
        self.assertTrue(cert["certificateFile"].endswith("/certificate.pem"))
        manifest = json.loads(pathlib.Path(result["manifest_path"]).read_text())
        self.assertEqual(manifest["environment"], "live")
        self.assertEqual(manifest["service_identity"], {
            "user": "xray", "group": "xray", "uid": 65534, "gid": 65534,
        })
        self.assertEqual(manifest["native_validation"], "PASS")
        self.assertEqual(pathlib.Path(result["config_path"]).stat().st_mode & 0o777, 0o640)

    def test_rejects_active_service_without_process_attestation(self):
        active = dict(self.systemd, active_state="active", main_pid=None, invocation_id=None)
        with mock.patch.object(live, "_service_identity", side_effect=REAL_SERVICE_IDENTITY):
            with self.assertRaises(live.LiveStagingError):
                live._service_identity(active)

    def test_rejects_unloaded_or_unmanaged_systemd_before_preflight(self):
        bad = dict(self.systemd, load_state="not-found")
        with mock.patch.object(live.xray_runtime_systemd_adapter, "status", return_value=bad), \
             mock.patch.object(live, "_service_identity", side_effect=REAL_SERVICE_IDENTITY), \
             mock.patch.object(live.xray_runtime_preflight, "preflight_profile") as preflight:
            with self.assertRaises(live.LiveStagingError):
                live.stage_live(self.profile_id, self.revision)
        preflight.assert_not_called()

    def test_mapping_change_during_staging_aborts_and_cleans_lease(self):
        original = live._read_bindings
        changed = self.mapping_bytes + b" "
        calls = {"count": 0}

        def read_mapping(*args):
            calls["count"] += 1
            result = original(*args)
            if calls["count"] == 2:
                return result[0], changed, result[2]
            return result

        with mock.patch.object(live, "_read_bindings", side_effect=read_mapping), \
             mock.patch.object(live.certificate_resolver, "prepare", side_effect=self.fake_prepare), \
             mock.patch.object(live.certificate_resolver, "cleanup") as cleanup:
            with self.assertRaises(live.LiveStagingError):
                live.stage_live(self.profile_id, self.revision)
        cleanup.assert_called_once()
        self.assertFalse(self.staging_root.exists() and list(self.staging_root.iterdir()))

    def test_service_uid_gid_change_during_staging_aborts_and_cleans_lease(self):
        with mock.patch.object(live, "_service_identity", side_effect=[(65534, 65534), (65535, 65535)]), \
             mock.patch.object(live.certificate_resolver, "prepare", side_effect=self.fake_prepare), \
             mock.patch.object(live.certificate_resolver, "cleanup") as cleanup:
            with self.assertRaises(live.LiveStagingError):
                live.stage_live(self.profile_id, self.revision)
        cleanup.assert_called_once()

    def test_native_validation_failure_cleans_staging_and_lease(self):
        with mock.patch.object(live.certificate_resolver, "prepare", side_effect=self.fake_prepare), \
             mock.patch.object(live.staging_fixture, "_service_run", side_effect=live.staging_fixture.StagingError("bad config")), \
             mock.patch.object(live.certificate_resolver, "cleanup") as cleanup:
            with self.assertRaises(live.staging_fixture.StagingError):
                live.stage_live(self.profile_id, self.revision)
        cleanup.assert_called_once()
        self.assertFalse(self.staging_root.exists() and list(self.staging_root.iterdir()))

    def test_invalid_mapping_permissions_fail_before_lease(self):
        self.mapping.chmod(0o644)
        with mock.patch.object(live.certificate_resolver, "prepare") as prepare:
            with self.assertRaises(live.LiveStagingError):
                live.stage_live(self.profile_id, self.revision)
        prepare.assert_not_called()


if __name__ == "__main__":
    unittest.main()
