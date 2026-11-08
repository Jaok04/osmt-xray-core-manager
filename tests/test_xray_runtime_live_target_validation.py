from __future__ import annotations

import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import xray_runtime_live_apply_bridge as bridge

PROFILE = "profile-" + "1" * 32
REVISION = "r000001"
CONNECTION = "vless-first-server"
TAG = "vless-first-in"
LEASE = "resolve-" + "a" * 32
CERT = "cert-first-server"


class LiveFirstServerTargetValidationTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {
            "profile_id": PROFILE, "revision": REVISION,
            "bindings": [{"inbound_tag": TAG, "connection_id": CONNECTION}],
            "leases": [{"lease_id": LEASE, "connection_id": CONNECTION,
                        "certificate_id": CERT}],
        }
        self.config = {
            "inbounds": [{
                "tag": TAG, "listen": "0.0.0.0", "port": 443, "protocol": "vless",
                "settings": {"clients": [{"id": "11111111-1111-4111-8111-111111111111"}]},
                "streamSettings": {
                    "network": "ws", "security": "tls",
                    "wsSettings": {"path": "/edge", "host": "ws.pruebas.tvrc.me"},
                    "tlsSettings": {"certificates": [{
                        "certificateFile": str(bridge.live_staging.LEASE_ROOT / LEASE / "certificate.pem"),
                        "keyFile": str(bridge.live_staging.LEASE_ROOT / LEASE / "private-key.pem"),
                    }]},
                },
            }],
            "outbounds": [{"protocol": "freedom"}],
        }
        self.source = {
            "schema_version": 2, "connection_id": CONNECTION,
            "mode_id": "vless_ws_tls", "transport": "websocket", "security": "tls",
            "listen_address": "0.0.0.0", "listen_port": 443,
            "transport_options": {"path": "/edge", "host": "ws.pruebas.tvrc.me"},
            "security_options": {"certificate_id": CERT},
            "client_options": {"tls_server_name": "sni.pruebas.tvrc.me"},
        }
        self.patches = [
            mock.patch.object(bridge.live_publisher, "_read_stage",
                              side_effect=lambda _path: (self.manifest, json.dumps(self.config).encode())),
            mock.patch.object(bridge.certificate_resolver, "_load_connections",
                              return_value=[{"id": CONNECTION, "protocol_id": "vless_ws_tls"}]),
            mock.patch.object(bridge.certificate_resolver, "_connection_config",
                              return_value=(self.source, "vless")),
            mock.patch.object(bridge.vless_client_export, "validate_certificate_sni"),
        ]
        self.mocks = [patcher.start() for patcher in self.patches]
        for patcher in self.patches:
            self.addCleanup(patcher.stop)

    def validate(self):
        return bridge._validate_first_server_profile(
            pathlib.Path("/run/xray-manager-runtime-staging/live-test"), PROFILE, REVISION,
        )

    def test_accepts_public_vless_ws_tls_443_and_checks_endpoint_plus_sni(self):
        result = self.validate()
        self.assertEqual(result["domain"], "pruebas.tvrc.me")
        self.assertEqual(result["listen"], "0.0.0.0")
        self.assertEqual(result["port"], 443)
        self.assertEqual(self.mocks[3].call_count, 2)
        endpoint_config = self.mocks[3].call_args_list[0].args[0]
        sni_config = self.mocks[3].call_args_list[1].args[0]
        self.assertEqual(endpoint_config["client_options"], {})
        self.assertEqual(sni_config["client_options"]["tls_server_name"], "sni.pruebas.tvrc.me")

    def test_rejects_loopback_listener(self):
        self.config["inbounds"][0]["listen"] = "127.0.0.1"
        self.mocks[0].return_value = (self.manifest, json.dumps(self.config).encode())
        with self.assertRaises(bridge.LiveApplyBridgeError):
            self.validate()
        self.mocks[1].assert_not_called()

    def test_rejects_non_443_inbound(self):
        self.config["inbounds"][0]["port"] = 8443
        self.mocks[0].return_value = (self.manifest, json.dumps(self.config).encode())
        with self.assertRaises(bridge.LiveApplyBridgeError):
            self.validate()

    def test_rejects_wrong_transport_or_security(self):
        self.config["inbounds"][0]["streamSettings"]["security"] = "none"
        self.mocks[0].return_value = (self.manifest, json.dumps(self.config).encode())
        with self.assertRaises(bridge.LiveApplyBridgeError):
            self.validate()

    def test_rejects_certificate_that_does_not_cover_domain_or_sni(self):
        self.mocks[3].side_effect = bridge.vless_client_export.ExportError("SAN mismatch")
        with self.assertRaisesRegex(bridge.LiveApplyBridgeError, "SAN mismatch"):
            self.validate()

    def test_rejects_profile_revision_mismatch(self):
        self.manifest["revision"] = "r000002"
        with self.assertRaises(bridge.LiveApplyBridgeError):
            self.validate()

    def test_rejects_lease_not_bound_to_connection(self):
        self.manifest["leases"][0]["connection_id"] = "other-connection"
        with self.assertRaises(bridge.LiveApplyBridgeError):
            self.validate()

    def test_rejects_certificate_paths_outside_the_operation_lease(self):
        self.config["inbounds"][0]["streamSettings"]["tlsSettings"]["certificates"][0]["keyFile"] = "/tmp/private-key.pem"
        self.mocks[0].return_value = (self.manifest, json.dumps(self.config).encode())
        with self.assertRaises(bridge.LiveApplyBridgeError):
            self.validate()


class UnpublishedStageCleanupTests(unittest.TestCase):
    def test_removes_stage_and_cleans_its_tls_lease(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            root.chmod(0o755)
            stage = root / "live-test"
            stage.mkdir(mode=0o750)
            os.chown(stage, 0, os.getgid())
            manifest = {"service_identity": {"gid": os.getgid()},
                        "leases": [{"lease_id": LEASE}]}
            with mock.patch.object(bridge.live_staging, "STAGING_ROOT", root), \
                 mock.patch.object(bridge.live_publisher, "_read_stage", return_value=(manifest, b"{}")), \
                 mock.patch.object(bridge.certificate_resolver, "cleanup", return_value={"status": "cleaned"}) as cleanup:
                bridge._discard_unpublished_stage(stage)
            self.assertFalse(stage.exists())
            cleanup.assert_called_once_with(bridge.live_staging.LEASE_ROOT, LEASE, os.getgid())

    def test_refuses_stage_outside_managed_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage = pathlib.Path(tmp) / "live-test"
            stage.mkdir(mode=0o750)
            manifest = {"service_identity": {"gid": os.getgid()}, "leases": []}
            with mock.patch.object(bridge.live_publisher, "_read_stage", return_value=(manifest, b"{}")):
                with self.assertRaises(bridge.LiveApplyBridgeError):
                    bridge._discard_unpublished_stage(stage)
            self.assertTrue(stage.exists())


if __name__ == "__main__":
    unittest.main()
