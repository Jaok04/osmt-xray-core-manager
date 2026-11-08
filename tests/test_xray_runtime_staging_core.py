from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import xray_runtime_staging_core as core


class RuntimeStagingCoreTests(unittest.TestCase):
    def setUp(self):
        self.document = {
            "inbounds": [
                {
                    "tag": "vless-ws-tls-in",
                    "streamSettings": {
                        "network": "ws",
                        "security": "tls",
                        "tlsSettings": {},
                    },
                },
                {
                    "tag": "plain-in",
                    "streamSettings": {"network": "tcp", "security": "none"},
                },
            ],
            "outbounds": [{"protocol": "freedom"}],
        }
        self.bindings = [
            {"inbound_tag": "vless-ws-tls-in", "connection_id": "vless-tls-01"}
        ]
        self.lease = {
            "status": "prepared",
            "lease_id": "resolve-" + "a" * 32,
            "connection_id": "vless-tls-01",
            "protocol": "vless",
            "certificate_id": "cert-central-01",
            "certificate_file": "/var/lib/xray-manager/certificates/lease/certificate.pem",
            "key_file": "/var/lib/xray-manager/certificates/lease/private-key.pem",
        }

    def test_validates_exact_tls_coverage_and_returns_tag_index(self):
        result = core.validate_profile_bindings(self.document, self.bindings)
        self.assertEqual(set(result), {"vless-ws-tls-in"})
        self.assertIs(result["vless-ws-tls-in"], self.document["inbounds"][0])

    def test_rejects_missing_tls_binding(self):
        with self.assertRaises(core.StagingCoreError):
            core.validate_profile_bindings(self.document, [])

    def test_rejects_extra_binding_for_non_tls_inbound(self):
        bindings = self.bindings + [
            {"inbound_tag": "plain-in", "connection_id": "plain-01"}
        ]
        with self.assertRaises(core.StagingCoreError):
            core.validate_profile_bindings(self.document, bindings)

    def test_rejects_duplicate_inbound_tags(self):
        document = copy.deepcopy(self.document)
        document["inbounds"].append(copy.deepcopy(document["inbounds"][0]))
        with self.assertRaises(core.StagingCoreError):
            core.validate_profile_bindings(document, self.bindings)

    def test_rejects_reused_connection_id(self):
        document = copy.deepcopy(self.document)
        document["inbounds"].append({
            "tag": "second-tls",
            "streamSettings": {"security": "tls", "tlsSettings": {}},
        })
        bindings = self.bindings + [
            {"inbound_tag": "second-tls", "connection_id": "vless-tls-01"}
        ]
        with self.assertRaises(core.StagingCoreError):
            core.validate_profile_bindings(document, bindings)

    def test_rejects_embedded_certificate_paths(self):
        document = copy.deepcopy(self.document)
        document["inbounds"][0]["streamSettings"]["tlsSettings"]["certificates"] = [
            {"certificateFile": "/arbitrary/cert.pem", "keyFile": "/arbitrary/key.pem"}
        ]
        with self.assertRaises(core.StagingCoreError):
            core.validate_profile_bindings(document, self.bindings)

    def test_injects_only_the_matching_prepared_lease(self):
        document = copy.deepcopy(self.document)
        core.inject_tls_lease(document, "vless-ws-tls-in", "vless-tls-01", "cert-central-01", "vless", self.lease)
        certs = document["inbounds"][0]["streamSettings"]["tlsSettings"]["certificates"]
        self.assertEqual(certs, [{
            "certificateFile": self.lease["certificate_file"],
            "keyFile": self.lease["key_file"],
        }])

    def test_rejects_lease_for_different_connection(self):
        lease = dict(self.lease, connection_id="other-connection")
        with self.assertRaises(core.StagingCoreError):
            core.inject_tls_lease(self.document, "vless-ws-tls-in", "vless-tls-01", "cert-central-01", "vless", lease)

    def test_rejects_malformed_lease_id(self):
        lease = dict(self.lease, lease_id="../outside")
        with self.assertRaises(core.StagingCoreError):
            core.inject_tls_lease(self.document, "vless-ws-tls-in", "vless-tls-01", "cert-central-01", "vless", lease)

    def test_rejects_lease_for_different_certificate_or_protocol(self):
        with self.assertRaises(core.StagingCoreError):
            core.inject_tls_lease(self.document, "vless-ws-tls-in", "vless-tls-01", "cert-other", "vless", self.lease)
        with self.assertRaises(core.StagingCoreError):
            core.inject_tls_lease(self.document, "vless-ws-tls-in", "vless-tls-01", "cert-central-01", "vmess", self.lease)

    def test_rejects_relative_certificate_paths(self):
        lease = dict(self.lease, certificate_file="cert.pem")
        with self.assertRaises(core.StagingCoreError):
            core.inject_tls_lease(self.document, "vless-ws-tls-in", "vless-tls-01", "cert-central-01", "vless", lease)


if __name__ == "__main__":
    unittest.main()
