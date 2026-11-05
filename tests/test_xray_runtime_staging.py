from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import tempfile
import unittest
from argparse import Namespace
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import xray_profiles
import xray_runtime_staging as staging
import xray_runtime_journal as runtime_journal
import xray_runtime_publisher as runtime_publisher


class RuntimeStagingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = pathlib.Path(self.tmp.name)
        self.base.chmod(0o755)
        marker = self.base / ".xray-manager-r02-fixture"
        marker.write_text(json.dumps({
            "schema_version": 1, "purpose": "xray-runtime-r02-isolated-fixture"
        }))
        marker.chmod(0o600)
        self.profile_root = self.base / "profiles"
        self.keydir = self.base / "keys"
        self.keydir.mkdir(mode=0o700)
        self.master = self.keydir / "profile-master.key"
        self.master.write_bytes(b"P" * 32)
        self.master.chmod(0o600)
        self.profiles = xray_profiles.ProfileStore(str(self.profile_root), str(self.master))
        self.config = {
            "log": {"loglevel": "warning"},
            "inbounds": [{
                "tag": "vless-ws-tls-in",
                "listen": "0.0.0.0",
                "port": 443,
                "protocol": "vless",
                "settings": {"clients": [], "decryption": "none"},
                "streamSettings": {"network": "ws", "security": "tls", "tlsSettings": {}},
            }],
            "outbounds": [{"protocol": "freedom", "tag": "direct"}],
        }
        self.content = (json.dumps(self.config, sort_keys=True, separators=(",", ":")) + "\n").encode()
        created = self.profiles.create("R02 staging fixture", config_data=self.content)
        self.profile_id = created["profile_id"]
        self.revision = created["current_revision"]
        self._mark_valid()
        self.mapping = self.base / "bindings.json"
        self.write_mapping([{"inbound_tag": "vless-ws-tls-in", "connection_id": "vless-tls-01"}])
        self.staging_root = self.base / "staging"
        self.lease_root = self.base / "leases"
        self.staging_root.mkdir(mode=0o711)
        self.lease_root.mkdir(mode=0o750)
        os.chown(self.lease_root, 0, 65534)
        os.chmod(self.lease_root, 0o750)
        self.args = Namespace(
            fixture_root=str(self.base),
            timeout=20, service_uid=65534, service_gid=65534,
            profile_store=str(self.profile_root), master_key=str(self.master),
            validation_store=str(self.base / "validation"), profile_id=self.profile_id,
            revision=self.revision, xray_binary="/fixture/xray",
            service_state=str(self.base / "service.json"), bindings_file=str(self.mapping),
            staging_root=str(self.staging_root), lease_root=str(self.lease_root),
            connections_catalog=str(self.base / "connections.json"), connections_base=str(self.base / "connections"),
            vmess_base=str(self.base / "vmess"), connection_lock=str(self.base / "locks/connections.lock"),
            certificate_catalog=str(self.base / "certificates/catalog.json"),
            certificate_base=str(self.base / "certificates"), managed_dir=str(self.base / "certificates/managed"),
            certificate_secrets_dir=str(self.base / "certificates/secrets"),
            certificate_lock=str(self.base / "certificates.lock"), certificate_master_key=str(self.base / "cert.key"),
        )
        self.validation_patch = mock.patch.object(
            staging.xray_runtime_preflight, "preflight",
            return_value={
                "validation_id": "pvalidation-" + "a" * 32,
                "content_sha256": hashlib.sha256(self.content).hexdigest(),
                "xray": {"path": "/fixture/xray", "sha256": "d" * 64, "size_bytes": 4096},
            },
        )
        self.validation_patch.start()
        self.addCleanup(self.validation_patch.stop)

    def tearDown(self):
        self.tmp.cleanup()

    def _mark_valid(self):
        manifest_path = self.profile_root / "profiles" / self.profile_id / "revisions" / self.revision / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["validation"] = {"json_syntax": "pass", "xray_static": "pass", "status": "valid"}
        manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n")
        manifest_path.chmod(0o600)
        metadata_path = self.profile_root / "profiles" / self.profile_id / "metadata.json"
        metadata = json.loads(metadata_path.read_text())
        metadata["validation_status"] = "valid"
        metadata["last_validated_revision"] = self.revision
        metadata_path.write_text(json.dumps(metadata, sort_keys=True, separators=(",", ":")) + "\n")
        metadata_path.chmod(0o600)

    def write_mapping(self, bindings):
        self.mapping.write_text(json.dumps({"schema_version": 1, "bindings": bindings}) + "\n")
        self.mapping.chmod(0o600)

    def fake_lease(self, **kwargs):
        lease_id = "resolve-" + "b" * 32
        return {
            "status": "prepared", "lease_id": lease_id,
            "connection_id": kwargs["connection_id"], "protocol": "vless",
            "certificate_id": kwargs["certificate_id"],
            "certificate_file": str(self.lease_root / lease_id / "certificate.pem"),
            "key_file": str(self.lease_root / lease_id / "private-key.pem"),
        }

    def patch_resolver(self):
        return (
            mock.patch.object(staging, "_connection_certificate_id", return_value=("cert-central-01", "vless")),
            mock.patch.object(staging.certificate_resolver, "prepare", side_effect=self.fake_lease),
            mock.patch.object(staging, "_service_run"),
        )

    def test_stages_profile_and_records_exact_binding_and_validation(self):
        patches = self.patch_resolver()
        with patches[0], patches[1] as prepare, patches[2]:
            result = staging.stage(self.args)
        self.assertEqual(result["status"], "STAGED")
        self.assertFalse(result["runtime_published"])
        self.assertFalse(result["service_started"])
        prepare.assert_called_once()
        config = json.loads(pathlib.Path(result["config_path"]).read_text())
        cert = config["inbounds"][0]["streamSettings"]["tlsSettings"]["certificates"][0]
        self.assertTrue(cert["certificateFile"].endswith("/certificate.pem"))
        self.assertTrue(cert["keyFile"].endswith("/private-key.pem"))
        manifest = json.loads(pathlib.Path(result["manifest_path"]).read_text())
        self.assertEqual(manifest["profile_id"], self.profile_id)
        self.assertEqual(manifest["revision"], self.revision)
        self.assertEqual(manifest["validation_id"], "pvalidation-" + "a" * 32)
        self.assertEqual(manifest["bindings"], [
            {"inbound_tag": "vless-ws-tls-in", "connection_id": "vless-tls-01"}
        ])
        self.assertEqual(manifest["leases"][0]["certificate_id"], "cert-central-01")
        self.assertEqual(manifest["xray_binary"]["path"], "/fixture/xray")
        self.assertEqual(pathlib.Path(result["config_path"]).stat().st_mode & 0o777, 0o640)

    def test_duplicate_or_unknown_inbound_binding_fails_before_lease(self):
        self.write_mapping([
            {"inbound_tag": "vless-ws-tls-in", "connection_id": "vless-tls-01"},
            {"inbound_tag": "missing-inbound", "connection_id": "vless-tls-02"},
        ])
        patches = self.patch_resolver()
        with patches[0], patches[1] as prepare, patches[2]:
            with self.assertRaises(staging.StagingError):
                staging.stage(self.args)
        prepare.assert_not_called()
        self.assertEqual(list(self.staging_root.iterdir()), [])

    def test_duplicate_connection_and_duplicate_tag_are_rejected(self):
        self.write_mapping([
            {"inbound_tag": "vless-ws-tls-in", "connection_id": "vless-tls-01"},
            {"inbound_tag": "other-inbound", "connection_id": "vless-tls-01"},
        ])
        with self.assertRaises(staging.StagingError):
            staging._read_mapping(self.mapping)
        self.write_mapping([
            {"inbound_tag": "vless-ws-tls-in", "connection_id": "vless-tls-01"},
            {"inbound_tag": "vless-ws-tls-in", "connection_id": "vless-tls-02"},
        ])
        with self.assertRaises(staging.StagingError):
            staging._read_mapping(self.mapping)

    def test_cleanup_is_attempted_if_native_validation_fails(self):
        patches = self.patch_resolver()
        with patches[0], patches[1], mock.patch.object(
            staging, "_service_run", side_effect=staging.StagingError("fixture rejection")
        ), mock.patch.object(staging.certificate_resolver, "cleanup") as cleanup:
            with self.assertRaises(staging.StagingError):
                staging.stage(self.args)
        cleanup.assert_called_once()
        self.assertEqual(list(self.staging_root.iterdir()), [])

    def test_profile_or_validation_change_during_lease_resolution_aborts(self):
        self.validation_patch.stop()
        first = {
            "validation_id": "pvalidation-" + "a" * 32,
            "content_sha256": hashlib.sha256(self.content).hexdigest(),
            "xray": {"path": "/fixture/xray", "sha256": "d" * 64, "size_bytes": 4096},
        }
        second = dict(first, content_sha256="e" * 64)
        patches = self.patch_resolver()
        with mock.patch.object(
            staging.xray_runtime_preflight, "preflight", side_effect=[first, second]
        ), patches[0], patches[1], patches[2], mock.patch.object(
            staging.certificate_resolver, "cleanup"
        ) as cleanup:
            with self.assertRaises(staging.StagingError):
                staging.stage(self.args)
        cleanup.assert_called_once()
        self.assertEqual(list(self.staging_root.iterdir()), [])

    def test_fixture_root_marker_is_mandatory(self):
        marker = self.base / ".xray-manager-r02-fixture"
        marker.unlink()
        patches = self.patch_resolver()
        with patches[0], patches[1] as prepare, patches[2]:
            with self.assertRaises(staging.StagingError):
                staging.stage(self.args)
        prepare.assert_not_called()

    def test_all_data_paths_must_remain_inside_fixture_root(self):
        self.args.certificate_master_key = "/etc/xray-manager/keys/master.key"
        patches = self.patch_resolver()
        with patches[0], patches[1] as prepare, patches[2]:
            with self.assertRaises(staging.StagingError):
                staging.stage(self.args)
        prepare.assert_not_called()

    def test_staging_root_symlink_ancestor_is_rejected(self):
        link = self.base / "staging-link"
        link.symlink_to(self.staging_root, target_is_directory=True)
        self.args.staging_root = str(link / "nested")
        patches = self.patch_resolver()
        with patches[0], patches[1] as prepare, patches[2]:
            with self.assertRaises(staging.StagingError):
                staging.stage(self.args)
        prepare.assert_not_called()
        self.assertFalse((self.staging_root / "nested").exists())

    def test_mapping_requires_root_private_regular_file(self):
        self.mapping.chmod(0o644)
        with self.assertRaises(staging.StagingError):
            staging._read_mapping(self.mapping)

    def test_service_identity_can_read_staged_config_and_tls_lease(self):
        operation_root = self.base / "identity-stage"
        operation_root.mkdir(mode=0o711)
        operation = operation_root / "operation"
        operation.mkdir(mode=0o750)
        os.chown(operation, 0, 65534)
        lease_root = self.base / "identity-leases"
        lease_root.mkdir(mode=0o750)
        os.chown(lease_root, 0, 65534)
        lease_dir = lease_root / ("resolve-" + "c" * 32)
        lease_dir.mkdir(mode=0o750)
        os.chown(lease_dir, 0, 65534)
        cert = lease_dir / "certificate.pem"
        key = lease_dir / "private-key.pem"
        cert.write_text("synthetic certificate\n")
        key.write_text("synthetic private key\n")
        for item in (cert, key):
            os.chown(item, 0, 65534)
            item.chmod(0o640)
        config = operation / "config.json"
        config.write_text(json.dumps({
            "inbounds": [{
                "streamSettings": {"tlsSettings": {"certificates": [{
                    "certificateFile": str(cert), "keyFile": str(key)
                }]}}
            }]
        }))
        os.chown(config, 0, 65534)
        config.chmod(0o640)
        binary = self.base / "xray-identity-fixture"
        binary.write_text(
            "#!/usr/bin/python3\nimport json, pathlib, sys\n"
            "cfg=json.loads(pathlib.Path(sys.argv[4]).read_text())\n"
            "item=cfg['inbounds'][0]['streamSettings']['tlsSettings']['certificates'][0]\n"
            "assert pathlib.Path(item['certificateFile']).read_text()\n"
            "assert pathlib.Path(item['keyFile']).read_text()\n"
        )
        binary.chmod(0o755)
        staging._service_run(binary, config, 65534, 65534, 10)

    def test_actual_central_resolver_lease_is_staged_and_readable_by_service(self):
        import subprocess

        cert_base = self.base / "certificates"
        managed = cert_base / "managed"
        secrets = cert_base / "secrets"
        for directory in (cert_base, managed, secrets):
            directory.mkdir(mode=0o700)
        cert_keydir = self.base / "certificate-keys"
        cert_keydir.mkdir(mode=0o700)
        cert_master = cert_keydir / "master.key"
        cert_master.write_bytes(b"C" * 32)
        cert_master.chmod(0o600)
        cert = self.base / "central-cert.pem"
        private = self.base / "central-key.pem"
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(private), "-out", str(cert), "-days", "2",
            "-subj", "/CN=stage.test.invalid",
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        private.chmod(0o600)
        cert.chmod(0o644)
        cert_catalog = cert_base / "catalog.json"
        cert_lock = cert_base / "catalog.lock"
        subprocess.run([
            sys.executable, str(ROOT / "scripts/certificate_store.py"),
            "--base", str(cert_base), "--catalog", str(cert_catalog),
            "--managed-dir", str(managed), "--secrets-dir", str(secrets),
            "--master-key", str(cert_master), "--lock", str(cert_lock),
            "import", "--storage-type", "managed", "--certificate-file", str(cert),
            "--private-key-file", str(private), "--certificate-id", "cert-stage-test",
        ], check=True, stdout=subprocess.DEVNULL)

        conn_base = self.base / "connections"
        conn_configs = conn_base / "configurations"
        conn_configs.mkdir(parents=True, mode=0o700)
        conn_base.chmod(0o700)
        connection_id = "vless-stage-test"
        connection_config = {
            "schema_version": 1, "connection_id": connection_id, "protocol": "vless",
            "mode_id": "vless_ws_tls", "transport": "websocket", "security": "tls",
            "listen_address": "0.0.0.0", "listen_port": 443,
            "transport_options": {"path": "/ws"},
            "security_options": {"certificate_id": "cert-stage-test"},
        }
        config_file = conn_configs / f"{connection_id}.r000001.json"
        config_file.write_text(json.dumps(connection_config, sort_keys=True, separators=(",", ":")) + "\n")
        config_file.chmod(0o600)
        connections_catalog = conn_base / "connections.json"
        connections_catalog.write_text(json.dumps([{
            "id": connection_id, "protocol_id": "vless_ws_tls", "port": 443,
            "state": "draft", "runtime_applied": False,
            "configuration_schema_version": 1, "configuration_revision": 1,
            "configuration_ref": f"configurations/{connection_id}.r000001.json",
        }]))
        connections_catalog.chmod(0o600)
        locks = self.base / "locks"
        locks.mkdir(mode=0o700)
        run_root = self.base / "run"
        run_root.mkdir(mode=0o755)
        lease_root = run_root / "certificates"
        staging_root = self.base / "staging-real"
        staging_root.mkdir(mode=0o711)

        real_xray = pathlib.Path("/usr/local/bin/xray")
        if real_xray.is_file() and os.access(real_xray, os.X_OK):
            binary = real_xray
        else:
            binary = self.base / "xray-central-fixture"
            binary.write_text(
                "#!/usr/bin/python3\nimport json, pathlib, sys\n"
                "cfg=json.loads(pathlib.Path(sys.argv[4]).read_text())\n"
                "item=cfg['inbounds'][0]['streamSettings']['tlsSettings']['certificates'][0]\n"
                "assert pathlib.Path(item['certificateFile']).read_text().startswith('-----BEGIN CERTIFICATE-----')\n"
                "assert pathlib.Path(item['keyFile']).read_text().startswith('-----BEGIN PRIVATE KEY-----')\n"
            )
            binary.chmod(0o755)
        mapping = self.base / "real-bindings.json"
        mapping.write_text(json.dumps({
            "schema_version": 1,
            "bindings": [{"inbound_tag": "vless-ws-tls-in", "connection_id": connection_id}],
        }) + "\n")
        mapping.chmod(0o600)

        args = Namespace(**vars(self.args))
        args.bindings_file = str(mapping)
        args.xray_binary = str(binary)
        args.staging_root = str(staging_root)
        args.lease_root = str(lease_root)
        args.connections_catalog = str(connections_catalog)
        args.connections_base = str(conn_base)
        args.vmess_base = str(self.base / "vmess")
        args.connection_lock = str(locks / "connections.lock")
        args.certificate_base = str(cert_base)
        args.certificate_catalog = str(cert_catalog)
        args.managed_dir = str(managed)
        args.certificate_secrets_dir = str(secrets)
        args.certificate_lock = str(cert_lock)
        args.certificate_master_key = str(cert_master)

        binary_info = {
            "path": str(binary),
            "sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
            "size_bytes": binary.stat().st_size,
        }
        with mock.patch.object(
            staging.xray_runtime_preflight, "preflight",
            return_value={
                "validation_id": "pvalidation-" + "a" * 32,
                "content_sha256": hashlib.sha256(self.content).hexdigest(),
                "xray": binary_info,
            },
        ):
            result = staging.stage(args)
        self.assertEqual(result["status"], "STAGED")
        manifest = json.loads(pathlib.Path(result["manifest_path"]).read_text())
        self.assertEqual(manifest["leases"][0]["certificate_id"], "cert-stage-test")
        staged = json.loads(pathlib.Path(result["config_path"]).read_text())
        tls_cert = staged["inbounds"][0]["streamSettings"]["tlsSettings"]["certificates"][0]
        self.assertTrue(pathlib.Path(tls_cert["certificateFile"]).is_file())
        self.assertTrue(pathlib.Path(tls_cert["keyFile"]).is_file())
        self.assertEqual(pathlib.Path(tls_cert["keyFile"]).stat().st_mode & 0o777, 0o640)
        # Integración R-02 → R-03: el journal sólo acepta el staging y lease
        # vinculados al mismo fixture R-02 y opera sobre XRAY_SERVICE_ROOT temporal.
        service_root = self.base / "service-root-r03"
        service_root.mkdir(mode=0o711)
        service_marker = service_root / ".xray-manager-fixture"
        service_marker.write_text(json.dumps({
            "schema_version": 1, "purpose": "xray-runtime-isolated-fixture"
        }, sort_keys=True, separators=(",", ":")) + "\n")
        service_marker.chmod(0o600)
        etc_dir = service_root / "etc"
        etc_dir.mkdir(mode=0o755)
        xray_dir = etc_dir / "xray"
        xray_dir.mkdir(mode=0o750)
        os.chown(xray_dir, 0, 65534)
        previous_config = xray_dir / "config.json"
        previous_bytes = b'{"inbounds":[],"outbounds":[{"protocol":"freedom"}]}\n'
        previous_config.write_bytes(previous_bytes)
        os.chown(previous_config, 0, 65534)
        previous_config.chmod(0o640)

        service_state = self.base / "service-state-r03.json"
        service_state.write_text(json.dumps({
            "unit": "xray.service", "load_state": "loaded",
            "active_state": "active", "sub_state": "running",
            "user": "xray", "group": "xray", "binary_path": str(binary),
        }, sort_keys=True))
        service_state.chmod(0o600)
        operation_store = self.base / "operations-r03"
        operation_store.mkdir(mode=0o700)
        operation_marker = operation_store / ".xray-manager-r03-operations-fixture"
        operation_marker.write_text(json.dumps({
            "schema_version": 1, "purpose": "xray-runtime-r03-isolated-operations"
        }, sort_keys=True, separators=(",", ":")) + "\n")
        operation_marker.chmod(0o600)
        operation_locks = operation_store / "locks"
        operation_locks.mkdir(mode=0o700)

        operation = runtime_journal.prepare_operation(
            staging_dir=pathlib.Path(result["staging_dir"]),
            service_root=service_root,
            service_state=service_state,
            operation_store=operation_store,
            lifecycle_lock=operation_locks / "lifecycle.lock",
            application_lock=operation_locks / "application.lock",
            lease_root=lease_root,
            service_uid=65534,
            service_gid=65534,
        )
        self.assertEqual(operation["status"], "SNAPSHOT_SAVED")
        journal_record = runtime_journal.read_journal(pathlib.Path(operation["operation_dir"]))
        self.assertEqual(journal_record["source"]["profile_id"], self.profile_id)
        self.assertEqual(journal_record["source"]["revision"], self.revision)
        self.assertEqual(
            (pathlib.Path(operation["operation_dir"]) / "snapshot/config.json").read_bytes(),
            previous_bytes,
        )
        self.assertEqual(previous_config.read_bytes(), previous_bytes)
        self.assertFalse(operation["runtime_published"])

        published = runtime_publisher.publish_operation(
            operation_store, operation["operation_id"],
            operation_locks / "lifecycle.lock", operation_locks / "application.lock",
        )
        self.assertEqual(published["status"], "CONFIG_PUBLISHED")
        self.assertEqual(previous_config.read_bytes(), pathlib.Path(result["config_path"]).read_bytes())
        published_record = runtime_journal.read_journal(pathlib.Path(operation["operation_dir"]))
        self.assertEqual(published_record["state"], "config_published")
        self.assertFalse(published["service_action_performed"])

        rolled_back = runtime_publisher.rollback_operation(
            operation_store, operation["operation_id"],
            operation_locks / "lifecycle.lock", operation_locks / "application.lock",
        )
        self.assertEqual(rolled_back["status"], "ROLLBACK_CONFIG_RESTORED")
        self.assertEqual(previous_config.read_bytes(), previous_bytes)
        rollback_record = runtime_journal.read_journal(pathlib.Path(operation["operation_dir"]))
        self.assertEqual(rollback_record["state"], "rollback_config_restored")
        self.assertEqual(rollback_record["rollback"]["validation"], "PASS")

        self.assertEqual(
            staging.certificate_resolver.cleanup(lease_root, result["lease_ids"][0], 65534)["status"],
            "cleaned",
        )


if __name__ == "__main__":
    unittest.main()
