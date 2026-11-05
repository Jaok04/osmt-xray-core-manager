from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest
from argparse import Namespace
from urllib.parse import parse_qs, urlsplit

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import certificate_store
import vless_config_store
import xray_profiles
import vless_client_export as exporter


class VlessClientExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = pathlib.Path(self.tmp.name)
        self.base.chmod(0o700)
        self.key = self.base / "master.key"
        self.key.write_bytes(b"E" * 32)
        self.key.chmod(0o600)

        self.connections = self.base / "connections"
        (self.connections / "configurations").mkdir(parents=True, mode=0o700)
        (self.connections / "secrets").mkdir(mode=0o700)
        self.connections.chmod(0o700)
        self.catalog = self.connections / "connections.json"
        self.connection = {
            "id": "conn-export", "name": "VLESS export fixture",
            "protocol_id": "vless_ws_tls", "port": 443, "max_users": 4,
            "state": "draft", "runtime_applied": False,
        }
        self.write_json(self.catalog, [self.connection])
        self.connection_lock = self.base / "run" / "connections.lock"
        self.connection_lock.parent.mkdir(mode=0o700)

        self.certs = self.base / "certificates"
        (self.certs / "managed").mkdir(parents=True, mode=0o700)
        (self.certs / "secrets").mkdir(mode=0o700)
        self.certs.chmod(0o700)
        self.cert_pem = self.base / "cert.pem"
        self.cert_key = self.base / "cert.key"
        import subprocess
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(self.cert_key), "-out", str(self.cert_pem),
            "-days", "2", "-subj", "/CN=fixture.invalid",
            "-addext", "subjectAltName=DNS:sni.example.invalid,DNS:sni.menu.invalid,DNS:hellen.tvrc.me",
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.cert_pem.chmod(0o600)
        self.cert_key.chmod(0o600)
        self.cert_catalog = self.certs / "catalog.json"
        certificate_store.import_certificate(Namespace(
            base=str(self.certs), catalog=str(self.cert_catalog),
            managed_dir=str(self.certs / "managed"), secrets_dir=str(self.certs / "secrets"),
            master_key=str(self.key), lock=str(self.base / "run" / "cert.lock"),
            action="import", storage_type="managed", certificate_file=str(self.cert_pem),
            private_key_file=str(self.cert_key), certificate_id="cert-export-fixture",
        ))

        config = {
            "schema_version": 2, "connection_id": "conn-export",
            "protocol": "vless", "mode_id": "vless_ws_tls",
            "transport": "websocket", "security": "tls",
            "listen_address": "127.0.0.1", "listen_port": 443,
            "transport_options": {"path": "/ws path", "host": "ws.example.invalid"},
            "security_options": {"certificate_id": "cert-export-fixture"},
            "client_options": {"tls_server_name": "sni.example.invalid"},
        }
        config_file = self.base / "vless.json"
        self.write_json(config_file, config)
        vless_config_store.run(Namespace(
            action="store", base=str(self.connections), catalog=str(self.catalog),
            lock=str(self.connection_lock), secrets_dir=str(self.connections / "secrets"),
            master_key=str(self.key), certificate_catalog=str(self.cert_catalog),
            connection_id="conn-export", input=str(config_file), secret_input=None,
            secret_type=None, secret_output=None,
        ))

        self.profile_root = self.base / "profiles"
        self.profiles = xray_profiles.ProfileStore(str(self.profile_root), str(self.key))
        initial = {
            "log": {"loglevel": "warning"},
            "inbounds": [{
                "tag": "vless-conn-export", "listen": "0.0.0.0", "port": 443,
                "protocol": "vless",
                "settings": {"clients": [
                    {"id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "email": "assoc:one"},
                    {"id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", "email": "assoc:two"},
                ], "decryption": "none"},
                "streamSettings": {
                    "network": "ws", "security": "tls",
                    "wsSettings": {"path": "/ws path", "host": "ws.example.invalid"},
                    "tlsSettings": {"certificates": []},
                },
            }],
            "outbounds": [{"tag": "direct", "protocol": "freedom", "settings": {}}],
        }
        created = self.profiles.create(
            "Export fixture",
            config_data=(json.dumps(initial, sort_keys=True, separators=(",", ":")) + "\n").encode(),
        )
        self.profile_id = created["profile_id"]
        self.revision = created["current_revision"]
        self.mapping_root = self.base / "bindings"
        self.mapping_profile = self.mapping_root / self.profile_id
        self.mapping_profile.mkdir(parents=True, mode=0o700)
        self.write_json(self.mapping_profile / f"{self.revision}.json", {
            "schema_version": 1,
            "bindings": [{"inbound_tag": "vless-conn-export", "connection_id": "conn-export"}],
        })
        self.mark_validated(self.revision)

    def mark_validated(self, revision):
        revision_dir = self.profiles.profile_dir(self.profile_id) / "revisions" / revision
        manifest_path = revision_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["validation"] = {"json_syntax": "pass", "xray_static": "pass", "status": "valid"}
        self.write_json(manifest_path, manifest)
        metadata_path = self.profiles.profile_dir(self.profile_id) / "metadata.json"
        metadata = json.loads(metadata_path.read_text())
        metadata["validation_status"] = "valid"
        metadata["last_validated_revision"] = revision
        self.write_json(metadata_path, metadata)

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def write_json(path: pathlib.Path, value):
        path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
        path.chmod(0o600)

    def args(self, **overrides):
        values = dict(
            profile_store=str(self.profile_root), master_key=str(self.key),
            profile_id=self.profile_id, revision=self.revision,
            mapping_root=str(self.mapping_root), connections_base=str(self.connections),
            connections_catalog=str(self.catalog), connection_lock=str(self.connection_lock),
            connection_secrets=str(self.connections / "secrets"),
            certificate_catalog=str(self.cert_catalog), address="hellen.tvrc.me", port=443,
            output=None,
        )
        values.update(overrides)
        return Namespace(**values)

    def test_exports_one_uri_per_client_with_distinct_host_and_sni(self):
        result = exporter.export_profile(self.args())
        self.assertEqual(result["status"], "EXPORTED")
        self.assertEqual(result["endpoint"], "hellen.tvrc.me:443")
        self.assertEqual(result["clients"], 2)
        parsed = urlsplit(result["uris"][0])
        self.assertEqual(parsed.scheme, "vless")
        self.assertEqual(parsed.hostname, "hellen.tvrc.me")
        self.assertEqual(parsed.port, 443)
        self.assertEqual(parse_qs(parsed.query), {
            "encryption": ["none"], "security": ["tls"], "sni": ["sni.example.invalid"],
            "type": ["ws"], "host": ["ws.example.invalid"], "path": ["/ws path"],
        })
        self.assertIn("runtime_changed", result)
        self.assertFalse(result["runtime_changed"])

    def test_omits_sni_and_host_when_not_configured(self):
        stored = json.loads((self.connections / "configurations/conn-export.r000001.json").read_text())
        stored["transport_options"] = {"path": "/ws"}
        stored["client_options"] = {}
        self.write_json(self.connections / "configurations/conn-export.r000001.json", stored)
        profile_data, _ = self.profiles.read_revision_config(self.profile_id, self.revision)
        profile = json.loads(profile_data)
        profile["inbounds"][0]["streamSettings"]["wsSettings"] = {"path": "/ws"}
        updated = self.profiles.update(
            self.profile_id,
            config_data=(json.dumps(profile, sort_keys=True, separators=(",", ":")) + "\n").encode(),
        )
        self.revision = updated["current_revision"]
        self.mark_validated(self.revision)
        self.mapping_profile.mkdir(mode=0o700, exist_ok=True)
        self.write_json(self.mapping_profile / f"{self.revision}.json", {
            "schema_version": 1,
            "bindings": [{"inbound_tag": "vless-conn-export", "connection_id": "conn-export"}],
        })
        result = exporter.export_profile(self.args())
        query = parse_qs(urlsplit(result["uris"][0]).query)
        self.assertNotIn("sni", query)
        self.assertNotIn("host", query)

    def test_rejects_unvalidated_revision(self):
        revision_dir = self.profiles.profile_dir(self.profile_id) / "revisions" / self.revision
        manifest_path = revision_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["validation"] = {"json_syntax": "pass", "xray_static": "not_run", "status": "pending"}
        self.write_json(manifest_path, manifest)
        with self.assertRaisesRegex(exporter.ExportError, "validación Xray satisfactoria"):
            exporter.export_profile(self.args())

    def test_rejects_endpoint_not_covered_when_sni_is_omitted(self):
        stored = json.loads((self.connections / "configurations/conn-export.r000001.json").read_text())
        stored["client_options"] = {}
        self.write_json(self.connections / "configurations/conn-export.r000001.json", stored)
        with self.assertRaisesRegex(exporter.ExportError, "no está cubierto por los SAN"):
            exporter.export_profile(self.args(address="uncovered.example.invalid"))

    def test_rejects_sni_not_covered_by_certificate_san(self):
        stored = json.loads((self.connections / "configurations/conn-export.r000001.json").read_text())
        stored["client_options"]["tls_server_name"] = "wrong.example.invalid"
        self.write_json(self.connections / "configurations/conn-export.r000001.json", stored)
        with self.assertRaisesRegex(exporter.ExportError, "no está cubierto por los SAN"):
            exporter.export_profile(self.args())

    def test_wildcard_san_matches_only_one_label(self):
        self.assertTrue(exporter.certificate_covers_server_name(
            {"sans": ["*.example.invalid"]}, "node.example.invalid"))
        self.assertFalse(exporter.certificate_covers_server_name(
            {"sans": ["*.example.invalid"]}, "deep.node.example.invalid"))

    def test_rejects_public_port_mismatch(self):
        with self.assertRaises(exporter.ExportError):
            exporter.export_profile(self.args(port=8443))

    def test_rejects_mapping_missing_binding(self):
        self.write_json(self.mapping_profile / f"{self.revision}.json", {
            "schema_version": 1, "bindings": [],
        })
        with self.assertRaises(exporter.ExportError):
            exporter.export_profile(self.args())

    def test_rejects_mapping_with_extra_binding(self):
        self.write_json(self.mapping_profile / f"{self.revision}.json", {
            "schema_version": 1,
            "bindings": [
                {"inbound_tag": "vless-conn-export", "connection_id": "conn-export"},
                {"inbound_tag": "unknown-tls", "connection_id": "conn-unknown"},
            ],
        })
        with self.assertRaises(exporter.ExportError):
            exporter.export_profile(self.args())

    def test_rejects_invalid_uuid(self):
        raw, _ = self.profiles.read_revision_config(self.profile_id, self.revision)
        profile = json.loads(raw)
        profile["inbounds"][0]["settings"]["clients"][0]["id"] = "not-a-uuid"
        updated = self.profiles.update(
            self.profile_id,
            config_data=(json.dumps(profile, sort_keys=True, separators=(",", ":")) + "\n").encode(),
        )
        self.revision = updated["current_revision"]
        self.mark_validated(self.revision)
        self.mapping_profile.mkdir(mode=0o700, exist_ok=True)
        self.write_json(self.mapping_profile / f"{self.revision}.json", {
            "schema_version": 1,
            "bindings": [{"inbound_tag": "vless-conn-export", "connection_id": "conn-export"}],
        })
        with self.assertRaises(exporter.ExportError):
            exporter.export_profile(self.args())

    def test_private_output_file_no_overwrite(self):
        output_dir = self.base / "out"
        output_dir.mkdir(mode=0o700)
        output = output_dir / "clients.txt"
        result = exporter.export_profile(self.args(output=str(output)))
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        self.assertEqual(output.read_text().splitlines(), result["uris"])
        with self.assertRaises(exporter.ExportError):
            exporter.export_profile(self.args(output=str(output)))


if __name__ == "__main__":
    unittest.main()
