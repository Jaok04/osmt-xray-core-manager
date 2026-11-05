from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import certificate_store
import vless_config_store
import xray_profiles
import vless_ws_tls_composer as composer
import xray_runtime_staging


class VlessWsTlsComposerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = pathlib.Path(self.tmp.name)
        self.base.chmod(0o700)
        self.run_dir = self.base / "run"
        self.run_dir.mkdir(mode=0o700)
        self.key = self.base / "master.key"
        self.key.write_bytes(b"K" * 32)
        self.key.chmod(0o600)

        self.connections_base = self.base / "connections"
        self.connections_base.mkdir(mode=0o700)
        self.secrets = self.connections_base / "secrets"
        self.secrets.mkdir(mode=0o700)
        self.connections_catalog = self.connections_base / "connections.json"
        self.connection = {
            "id": "conn-ws-tls", "name": "Fixture VLESS WS TLS",
            "protocol_id": "vless_ws_tls", "port": 443,
            "max_users": 10, "state": "draft", "runtime_applied": False,
        }
        self.write_json(self.connections_catalog, [self.connection])
        self.connection_lock = self.run_dir / "connections.lock"

        self.certs = self.base / "certificates"
        (self.certs / "managed").mkdir(parents=True, mode=0o700)
        self.certs.chmod(0o700)
        (self.certs / "managed").chmod(0o700)
        (self.certs / "secrets").mkdir(mode=0o700)
        (self.certs / "secrets").chmod(0o700)
        self.cert_catalog = self.certs / "catalog.json"
        self.cert_key = self.base / "cert.key"
        self.cert_pem = self.base / "cert.pem"
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(self.cert_key), "-out", str(self.cert_pem),
            "-days", "2", "-subj", "/CN=i01-fixture.invalid",
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.cert_key.chmod(0o600)
        self.cert_pem.chmod(0o600)
        cert_args = Namespace(
            base=str(self.certs), catalog=str(self.cert_catalog),
            managed_dir=str(self.certs / "managed"),
            secrets_dir=str(self.certs / "secrets"),
            master_key=str(self.key), lock=str(self.run_dir / "cert.lock"),
            action="import", storage_type="managed",
            certificate_file=str(self.cert_pem), private_key_file=str(self.cert_key),
            certificate_id="cert-i01-fixture",
        )
        certificate_store.import_certificate(cert_args)

        self.vless_input = self.base / "vless.json"
        self.write_json(self.vless_input, {
            "schema_version": 1, "connection_id": "conn-ws-tls",
            "protocol": "vless", "mode_id": "vless_ws_tls",
            "transport": "websocket", "security": "tls",
            "listen_address": "127.0.0.1", "listen_port": 443,
            "transport_options": {"path": "/ws"},
            "security_options": {"certificate_id": "cert-i01-fixture"},
        })
        store_args = Namespace(
            action="store", base=str(self.connections_base),
            catalog=str(self.connections_catalog), lock=str(self.connection_lock),
            secrets_dir=str(self.secrets), master_key=str(self.key),
            certificate_catalog=str(self.cert_catalog),
            connection_id="conn-ws-tls", input=str(self.vless_input),
            secret_input=None, secret_type=None, secret_output=None,
        )
        vless_config_store.run(store_args)

        self.users_dir = self.base / "users"
        self.users_dir.mkdir(mode=0o700)
        self.users_file = self.users_dir / "users.json"
        self.users_lock = self.run_dir / "users.lock"
        env = os.environ.copy()
        env.update({
            "APP_ROOT": str(ROOT),
            "XRAY_MANAGER_USERS_DIR": str(self.users_dir),
            "XRAY_MANAGER_USERS_FILE": str(self.users_file),
            "XRAY_MANAGER_CONNECTIONS_FILE": str(self.connections_catalog),
            "XRAY_MANAGER_INTEGRITY_LOCK": str(self.users_lock),
        })
        create_users = (
            'source "$APP_ROOT/modules/users_v2.sh" || exit 1; '
            'i1="$(users_identity_create)" || exit 2; '
            'users_association_create "$i1" conn-ws-tls "Activo" uuid '
            '"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" active unlimited 0 none 0 0 auto || exit 3; '
            'i2="$(users_identity_create)" || exit 4; '
            'users_association_create "$i2" conn-ws-tls "Suspendido" uuid '
            '"bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb" suspended unlimited 0 none 0 0 auto || exit 5'
        )
        subprocess.run(["bash", "-c", create_users], env=env, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

        self.profile_store = self.base / "profiles"
        self.profiles = xray_profiles.ProfileStore(str(self.profile_store), str(self.key))
        initial = {
            "log": {"loglevel": "warning"},
            "inbounds": [],
            "outbounds": [{"tag": "direct", "protocol": "freedom", "settings": {}}],
        }
        created = self.profiles.create(
            "I-01 fixture",
            config_data=(json.dumps(initial, sort_keys=True, separators=(",", ":")) + "\n").encode(),
        )
        self.profile_id = created["profile_id"]
        self.revision = created["current_revision"]
        self.mapping_root = self.base / "profile-bindings"
        self.mapping_root.mkdir(mode=0o700)

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def write_json(path: pathlib.Path, value):
        path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
        path.chmod(0o600)

    def args(self, **overrides):
        values = dict(
            profile_store=str(self.profile_store), master_key=str(self.key),
            profile_id=self.profile_id, expected_revision=self.revision,
            connection_id="conn-ws-tls",
            connections_catalog=str(self.connections_catalog),
            connections_base=str(self.connections_base),
            connection_lock=str(self.connection_lock),
            users_file=str(self.users_file), users_lock=str(self.users_lock),
            secrets_dir=str(self.secrets), certificate_catalog=str(self.cert_catalog),
            mapping_root=str(self.mapping_root), existing_bindings=None,
        )
        values.update(overrides)
        return Namespace(**values)

    def test_composes_ws_tls_with_active_users_and_private_mapping(self):
        result = composer.compose(self.args())
        self.assertEqual(result["status"], "COMPOSED")
        self.assertFalse(result["runtime_changed"])
        self.assertFalse(result["service_started"])
        self.assertEqual(result["clients"], 1)
        self.assertEqual(result["source_revision"], self.revision)
        new_revision = result["revision"]
        data, manifest = self.profiles.read_revision_config(self.profile_id, new_revision)
        config = json.loads(data)
        inbound = config["inbounds"][0]
        self.assertEqual(inbound["tag"], "vless-conn-ws-tls")
        self.assertEqual(inbound["protocol"], "vless")
        self.assertEqual(inbound["streamSettings"]["network"], "ws")
        self.assertEqual(inbound["streamSettings"]["security"], "tls")
        self.assertEqual(inbound["streamSettings"]["wsSettings"], {"path": "/ws"})
        self.assertEqual(inbound["streamSettings"]["tlsSettings"], {"certificates": []})
        active_association = next(
            item for item in json.loads(self.users_file.read_text())["associations"]
            if item["state"] == "active"
        )
        self.assertEqual(inbound["settings"]["clients"], [{
            "id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            "email": "assoc:" + active_association["id"],
        }])
        self.assertEqual(manifest["validation"]["status"], "pending")
        mapping = pathlib.Path(result["mapping_file"])
        self.assertEqual(json.loads(mapping.read_text()), {
            "schema_version": 1,
            "bindings": [{"inbound_tag": "vless-conn-ws-tls", "connection_id": "conn-ws-tls"}],
        })
        self.assertEqual(mapping.stat().st_mode & 0o777, 0o600)
        normalized, _raw = xray_runtime_staging._read_mapping(mapping)
        self.assertEqual(normalized, [{"inbound_tag": "vless-conn-ws-tls", "connection_id": "conn-ws-tls"}])
        self.assertEqual(mapping.parent.stat().st_mode & 0o777, 0o700)
        old_data, _ = self.profiles.read_revision_config(self.profile_id, self.revision)
        self.assertEqual(json.loads(old_data)["inbounds"], [])

    def test_composes_websocket_host_and_keeps_client_sni_separate(self):
        config = {
            "schema_version": 2, "connection_id": "conn-ws-tls",
            "protocol": "vless", "mode_id": "vless_ws_tls",
            "transport": "websocket", "security": "tls",
            "listen_address": "127.0.0.1", "listen_port": 443,
            "transport_options": {"path": "/ws", "host": "ws.example.invalid"},
            "security_options": {"certificate_id": "cert-i01-fixture"},
            "client_options": {"tls_server_name": "sni.example.invalid"},
        }
        self.write_json(self.vless_input, config)
        vless_config_store.run(Namespace(
            action="store", base=str(self.connections_base), catalog=str(self.connections_catalog),
            lock=str(self.connection_lock), secrets_dir=str(self.secrets), master_key=str(self.key),
            certificate_catalog=str(self.cert_catalog), connection_id="conn-ws-tls",
            input=str(self.vless_input), secret_input=None, secret_type=None, secret_output=None,
        ))
        self.revision = "r000001"
        result = composer.compose(self.args())
        data, _ = self.profiles.read_revision_config(self.profile_id, result["revision"])
        inbound = json.loads(data)["inbounds"][0]
        self.assertEqual(inbound["streamSettings"]["wsSettings"], {
            "path": "/ws", "host": "ws.example.invalid"
        })
        self.assertNotIn("tls_server_name", inbound["streamSettings"]["tlsSettings"])
        stored = json.loads((self.connections_base / "configurations/conn-ws-tls.r000002.json").read_text())
        self.assertEqual(stored["client_options"], {"tls_server_name": "sni.example.invalid"})

    def test_preserves_existing_inbounds_and_tls_bindings(self):
        original = {
            "log": {"loglevel": "warning"},
            "inbounds": [{
                "tag": "vmess-tls-in", "listen": "127.0.0.1", "port": 8443,
                "protocol": "vmess", "settings": {"clients": []},
                "streamSettings": {"network": "tcp", "security": "tls",
                                   "tlsSettings": {"certificates": []}},
            }],
            "outbounds": [{"tag": "direct", "protocol": "freedom", "settings": {}}],
        }
        updated = self.profiles.update(
            self.profile_id,
            config_data=(json.dumps(original, sort_keys=True, separators=(",", ":")) + "\n").encode(),
        )
        self.revision = updated["current_revision"]
        binding_file = self.base / "old-bindings.json"
        self.write_json(binding_file, {
            "schema_version": 1,
            "bindings": [{"inbound_tag": "vmess-tls-in", "connection_id": "vmess-fixture"}],
        })
        result = composer.compose(self.args(existing_bindings=str(binding_file)))
        data, _ = self.profiles.read_revision_config(self.profile_id, result["revision"])
        composed = json.loads(data)
        self.assertEqual([x["tag"] for x in composed["inbounds"]],
                         ["vmess-tls-in", "vless-conn-ws-tls"])
        mapping = json.loads(pathlib.Path(result["mapping_file"]).read_text())
        self.assertEqual(len(mapping["bindings"]), 2)

    def test_rejects_stale_revision_without_mutating_profile(self):
        current_bytes, _ = self.profiles.read_revision_config(self.profile_id, self.revision)
        self.profiles.update(self.profile_id, config_data=current_bytes)
        before = self.profiles.load_metadata(self.profile_id)["current_revision"]
        with self.assertRaises(composer.ComposerError):
            composer.compose(self.args())
        self.assertEqual(self.profiles.load_metadata(self.profile_id)["current_revision"], before)

    def test_rejects_port_conflict(self):
        original = {
            "log": {"loglevel": "warning"},
            "inbounds": [{
                "tag": "occupied", "listen": "127.0.0.1", "port": 443,
                "protocol": "socks", "settings": {},
                "streamSettings": {"network": "tcp", "security": "none"},
            }],
            "outbounds": [{"tag": "direct", "protocol": "freedom", "settings": {}}],
        }
        updated = self.profiles.update(
            self.profile_id,
            config_data=(json.dumps(original, sort_keys=True, separators=(",", ":")) + "\n").encode(),
        )
        self.revision = updated["current_revision"]
        with self.assertRaises(composer.ComposerError):
            composer.compose(self.args())
        self.assertEqual(self.profiles.load_metadata(self.profile_id)["current_revision"], self.revision)

    def test_rejects_missing_previous_tls_mapping(self):
        original = {
            "log": {"loglevel": "warning"},
            "inbounds": [{
                "tag": "tls-existing", "listen": "127.0.0.1", "port": 8443,
                "protocol": "vmess", "settings": {"clients": []},
                "streamSettings": {"network": "tcp", "security": "tls",
                                   "tlsSettings": {"certificates": []}},
            }],
            "outbounds": [{"tag": "direct", "protocol": "freedom", "settings": {}}],
        }
        updated = self.profiles.update(
            self.profile_id,
            config_data=(json.dumps(original, sort_keys=True, separators=(",", ":")) + "\n").encode(),
        )
        self.revision = updated["current_revision"]
        with self.assertRaises(composer.ComposerError):
            composer.compose(self.args())
        self.assertEqual(self.profiles.load_metadata(self.profile_id)["current_revision"], self.revision)


    def test_rejects_missing_or_invalid_central_certificate(self):
        self.cert_catalog.write_text('{invalid')
        self.cert_catalog.chmod(0o600)
        with self.assertRaises(composer.ComposerError):
            composer.compose(self.args())
        self.assertEqual(self.profiles.load_metadata(self.profile_id)["current_revision"], self.revision)

    def test_rejects_empty_active_candidate_set(self):
        document = json.loads(self.users_file.read_text())
        for association in document["associations"]:
            association["state"] = "suspended"
        self.write_json(self.users_file, document)
        with self.assertRaises(composer.ComposerError):
            composer.compose(self.args())
        self.assertEqual(self.profiles.load_metadata(self.profile_id)["current_revision"], self.revision)

    def test_rejects_uuid_already_present_in_profile(self):
        original = {
            "log": {"loglevel": "warning"},
            "inbounds": [{
                "tag": "existing-vless", "listen": "127.0.0.1", "port": 8443,
                "protocol": "vless",
                "settings": {"clients": [{"id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"}]},
                "streamSettings": {"network": "ws", "security": "none"},
            }],
            "outbounds": [{"tag": "direct", "protocol": "freedom", "settings": {}}],
        }
        updated = self.profiles.update(
            self.profile_id,
            config_data=(json.dumps(original, sort_keys=True, separators=(",", ":")) + "\n").encode(),
        )
        self.revision = updated["current_revision"]
        with self.assertRaises(composer.ComposerError):
            composer.compose(self.args())
        self.assertEqual(self.profiles.load_metadata(self.profile_id)["current_revision"], self.revision)

    def test_rejects_malformed_persisted_vless_configuration(self):
        config_path = self.connections_base / "configurations/conn-ws-tls.r000001.json"
        broken = json.loads(config_path.read_text())
        broken["listen_port"] = 444
        self.write_json(config_path, broken)
        with self.assertRaises(composer.ComposerError):
            composer.compose(self.args())
        self.assertEqual(self.profiles.load_metadata(self.profile_id)["current_revision"], self.revision)


    def test_rejects_symlink_ancestor_in_catalog_path(self):
        link = self.base / "connections-link"
        link.symlink_to(self.connections_base, target_is_directory=True)
        args = self.args(connections_catalog=str(link / "connections.json"))
        with self.assertRaises(xray_profiles.ProfileError):
            composer.compose(args)
        self.assertEqual(self.profiles.load_metadata(self.profile_id)["current_revision"], self.revision)


if __name__ == "__main__":
    unittest.main()
