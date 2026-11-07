from __future__ import annotations
import json, os, pathlib, subprocess, sys, tempfile, unittest
from argparse import Namespace

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import certificate_acme as acme
import certificate_store
import certificate_resolver


class CertificateAcmeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = pathlib.Path(self.tmp.name)
        self.base.chmod(0o700)

    def tearDown(self):
        self.tmp.cleanup()

    def make_certificate(self, domain="fixture.example.invalid"):
        cert, key = self.base / "source-cert.pem", self.base / "source-key.pem"
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(key), "-out", str(cert), "-days", "3",
            "-subj", f"/CN={domain}", "-addext", f"subjectAltName=DNS:{domain}",
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cert.chmod(0o600); key.chmod(0o600)
        return cert, key

    def test_domain_validation_and_wildcard_policy(self):
        self.assertEqual(
            acme.validate_request(["WWW.Example.invalid.", "example.invalid"], "http-01", "ops@example.invalid"),
            ["example.invalid", "www.example.invalid"],
        )
        self.assertEqual(
            acme.validate_request(["*.example.invalid"], "dns-01", "ops@example.invalid"),
            ["*.example.invalid"],
        )
        for domains, method in [(["*.example.invalid"], "http-01"), (["example.invalid", "EXAMPLE.invalid"], "dns-01"), (["127.0.0.1"], "http-01")]:
            with self.assertRaises(acme.AcmeError):
                acme.validate_request(domains, method, "ops@example.invalid")

    def test_certbot_commands_are_method_specific(self):
        http = acme.build_certbot_command(
            method="http-01", domains=["example.invalid"], email="ops@example.invalid",
            cert_name="xray-test", certbot_bin="/fixture/certbot",
        )
        self.assertIn("--standalone", http)
        self.assertIn("--http-01-port", http)
        self.assertIn("--non-interactive", http)
        self.assertNotIn("--manual", http)
        dns = acme.build_certbot_command(
            method="dns-01", domains=["*.example.invalid"], email="ops@example.invalid",
            cert_name="xray-test", auth_hook="/tmp/auth.py", cleanup_hook="/tmp/cleanup.py",
        )
        self.assertIn("--manual", dns)
        self.assertIn("--manual-auth-hook", dns)
        self.assertIn("--manual-cleanup-hook", dns)
        self.assertNotIn("--non-interactive", dns)
        self.assertNotIn("--dns-cloudflare", dns)
        with self.assertRaises(acme.AcmeError):
            acme.build_certbot_command(method="dns-01", domains=["example.invalid"], email="ops@example.invalid", cert_name="xray-test")

    def test_http_preflight_requires_matching_dns_and_free_port(self):
        def query(domain, kind, resolver):
            return {"198.51.100.20"} if kind == "A" else set()
        result = acme.check_http_preconditions(
            ["example.invalid"], ["198.51.100.20"], query=query,
            port_probe=lambda: True, resolvers=("192.0.2.53",),
        )
        self.assertTrue(result["port_80_available"])
        self.assertEqual(result["external_ca_reachability"], "not_verified_until_acme_challenge")
        with self.assertRaises(acme.AcmeError):
            acme.check_http_preconditions(["example.invalid"], [], query=query, port_probe=lambda: True)
        def divergent(domain, kind, resolver):
            return {"198.51.100.20", "203.0.113.9"} if kind == "A" else set()
        with self.assertRaises(acme.AcmeError):
            acme.check_http_preconditions(
                ["example.invalid"], ["198.51.100.20"], query=divergent,
                port_probe=lambda: True, resolvers=("192.0.2.53",),
            )
        with self.assertRaises(acme.AcmeError):
            acme.check_http_preconditions(["example.invalid"], ["198.51.100.20"], query=query, port_probe=lambda: False, resolvers=("192.0.2.53",))

    def test_dns_txt_visibility_requires_every_resolver(self):
        def query(name, kind, resolver):
            return {"challenge-token"} if resolver == "192.0.2.1" else set()
        result = acme.check_txt_visibility(
            "_acme-challenge.example.invalid", "challenge-token",
            resolvers=("192.0.2.1", "192.0.2.2"), query=query,
        )
        self.assertFalse(result["expected_value_visible"])
        self.assertEqual(result["visible_resolvers"], ["192.0.2.1"])
        with self.assertRaises(acme.AcmeError):
            acme.check_txt_visibility("example.invalid", "challenge-token", query=query)

    def test_dns_hooks_show_exact_value_and_never_delete_records(self):
        hooks_dir = self.base / "hooks"; hooks_dir.mkdir(mode=0o700)
        auth, cleanup = acme.write_hooks(hooks_dir)
        fakebin = self.base / "bin"; fakebin.mkdir(mode=0o700)
        dig = fakebin / "dig"
        dig.write_text("#!/bin/sh\nprintf '%s\\n' \"$TEST_DNS_VALUE\"\n")
        dig.chmod(0o700)
        env = os.environ | {
            "PATH": str(fakebin) + os.pathsep + os.environ.get("PATH", ""),
            "CERTBOT_DOMAIN": "example.invalid", "CERTBOT_VALIDATION": "challenge-token",
            "TEST_DNS_VALUE": "challenge-token", "XRAY_MANAGER_DNS_RESOLVERS": "192.0.2.1,192.0.2.2",
        }
        result = subprocess.run([str(auth)], input="\n", text=True, capture_output=True, env=env, check=True)
        self.assertIn("_acme-challenge.example.invalid", result.stdout)
        self.assertIn("TXT visible", result.stdout)
        clean = subprocess.run([str(cleanup)], text=True, capture_output=True, env=env, check=True)
        self.assertIn("No elimines otros valores TXT", clean.stdout)
        self.assertNotIn("unlink", cleanup.read_text())

    def test_certbot_symlink_lineage_is_staged_and_imported(self):
        cert, key = self.make_certificate()
        config = self.base / "letsencrypt"
        archive = config / "archive" / "xray-fixture"
        live = config / "live" / "xray-fixture"
        archive.mkdir(parents=True, mode=0o700); live.mkdir(parents=True, mode=0o700)
        config.chmod(0o700)
        (archive / "fullchain1.pem").write_bytes(cert.read_bytes())
        (archive / "privkey1.pem").write_bytes(key.read_bytes())
        (archive / "fullchain1.pem").chmod(0o600); (archive / "privkey1.pem").chmod(0o600)
        (live / "fullchain.pem").symlink_to("../../archive/xray-fixture/fullchain1.pem")
        (live / "privkey.pem").symlink_to("../../archive/xray-fixture/privkey1.pem")
        store_base = self.base / "store"
        managed = store_base / "managed"; secrets = store_base / "secrets"
        managed.mkdir(parents=True, mode=0o700); secrets.mkdir(mode=0o700); store_base.chmod(0o700)
        master = self.base / "master.key"; master.write_bytes(b"K" * 32); master.chmod(0o600)
        staging = self.base / "staging"; staging.mkdir(mode=0o700)
        args = Namespace(
            base=str(store_base), catalog=str(store_base / "catalog.json"),
            managed_dir=str(managed), secrets_dir=str(secrets), master_key=str(master),
            lock=str(self.base / "store.lock"), certificate_id="cert-acme-fixture",
        )
        result = acme.stage_and_import(
            config_dir=config, cert_name="xray-fixture",
            requested_domains=["fixture.example.invalid"], staging_parent=staging, store_args=args,
        )
        self.assertEqual(result["status"], "imported")
        self.assertEqual(result["certificate_id"], "cert-acme-fixture")
        self.assertIn("fixture.example.invalid", result["sans"])
        catalog = json.loads((store_base / "catalog.json").read_text())
        self.assertEqual(len(catalog["certificates"]), 1)
        self.assertEqual(catalog["certificates"][0]["storage_type"], "managed")
        self.assertEqual(list(staging.iterdir()), [])
        with self.assertRaises(acme.AcmeError):
            acme.stage_and_import(
                config_dir=config, cert_name="xray-fixture",
                requested_domains=["other.example.invalid"], staging_parent=staging, store_args=args,
            )

    def test_rotation_rejects_certificate_that_drops_historical_sans(self):
        old_cert_source, old_key_source = self.make_certificate("old.example.invalid")
        old_cert, old_key = self.base / "old-cert.pem", self.base / "old-key.pem"
        old_cert.write_bytes(old_cert_source.read_bytes()); old_key.write_bytes(old_key_source.read_bytes())
        old_cert.chmod(0o600); old_key.chmod(0o600)
        new_cert, new_key = self.make_certificate("new.example.invalid")
        store_base = self.base / "rotation-store"
        managed = store_base / "managed"; secrets = store_base / "secrets"
        managed.mkdir(parents=True, mode=0o700); secrets.mkdir(mode=0o700); store_base.chmod(0o700)
        master = self.base / "rotation-master.key"; master.write_bytes(b"S" * 32); master.chmod(0o600)
        store_args = Namespace(
            base=str(store_base), catalog=str(store_base / "catalog.json"),
            managed_dir=str(managed), secrets_dir=str(secrets), master_key=str(master),
            lock=str(store_base / "catalog.lock"), certificate_id="cert-rotation-sans",
        )
        import_args = Namespace(**vars(store_args), storage_type="managed",
                                certificate_file=str(old_cert), private_key_file=str(old_key))
        certificate_store.import_certificate(import_args)
        config = self.base / "rotation-letsencrypt"
        archive = config / "archive" / "rotation-fixture"
        live = config / "live" / "rotation-fixture"
        archive.mkdir(parents=True, mode=0o700); live.mkdir(parents=True, mode=0o700); config.chmod(0o700)
        (archive / "fullchain1.pem").write_bytes(new_cert.read_bytes())
        (archive / "privkey1.pem").write_bytes(new_key.read_bytes())
        (archive / "fullchain1.pem").chmod(0o600); (archive / "privkey1.pem").chmod(0o600)
        (live / "fullchain.pem").symlink_to("../../archive/rotation-fixture/fullchain1.pem")
        (live / "privkey.pem").symlink_to("../../archive/rotation-fixture/privkey1.pem")
        staging = self.base / "rotation-staging"; staging.mkdir(mode=0o700)
        with self.assertRaisesRegex(acme.AcmeError, "no conserva todos los SAN"):
            acme.stage_and_import(
                config_dir=config, cert_name="rotation-fixture",
                requested_domains=["new.example.invalid"], staging_parent=staging, store_args=store_args,
            )
        catalog = certificate_store.load_catalog(pathlib.Path(store_args.catalog))
        record = catalog["certificates"][0]
        self.assertEqual(record["active_revision"], 1)
        self.assertEqual(len(record["revisions"]), 1)
        self.assertEqual(list(staging.iterdir()), [])

    def test_imported_certificate_is_usable_by_tls_resolver_fixture(self):
        cert, key = self.make_certificate()
        config = self.base / "letsencrypt"
        archive = config / "archive" / "resolver-fixture"
        live = config / "live" / "resolver-fixture"
        archive.mkdir(parents=True, mode=0o700); live.mkdir(parents=True, mode=0o700); config.chmod(0o700)
        (archive / "fullchain1.pem").write_bytes(cert.read_bytes())
        (archive / "privkey1.pem").write_bytes(key.read_bytes())
        (archive / "fullchain1.pem").chmod(0o600); (archive / "privkey1.pem").chmod(0o600)
        (live / "fullchain.pem").symlink_to("../../archive/resolver-fixture/fullchain1.pem")
        (live / "privkey.pem").symlink_to("../../archive/resolver-fixture/privkey1.pem")
        store_base = self.base / "certificates"
        managed = store_base / "managed"; secrets = store_base / "secrets"
        managed.mkdir(parents=True, mode=0o700); secrets.mkdir(mode=0o700); store_base.chmod(0o700)
        master = self.base / "master.key"; master.write_bytes(b"R" * 32); master.chmod(0o600)
        staging = self.base / "staging"; staging.mkdir(mode=0o700)
        store_args = Namespace(
            base=str(store_base), catalog=str(store_base / "catalog.json"),
            managed_dir=str(managed), secrets_dir=str(secrets), master_key=str(master),
            lock=str(store_base / "catalog.lock"), certificate_id="cert-resolver-acme",
        )
        imported = acme.stage_and_import(
            config_dir=config, cert_name="resolver-fixture",
            requested_domains=["fixture.example.invalid"], staging_parent=staging, store_args=store_args,
        )
        conn_base = self.base / "connections"
        (conn_base / "configurations").mkdir(parents=True, mode=0o700)
        conn_base.chmod(0o700)
        vmess_base = self.base / "vmess"; vmess_base.mkdir(mode=0o700)
        run_dir = self.base / "run"; run_dir.mkdir(mode=0o700)
        (run_dir / "locks").mkdir(mode=0o700)
        connection = {
            "id": "conn-acme", "name": "ACME resolver fixture", "protocol_id": "vless_ws_tls",
            "port": 443, "max_users": 1, "state": "draft", "runtime_applied": False,
            "configuration_schema_version": 1, "configuration_revision": 1,
            "configuration_ref": "configurations/conn-acme.r000001.json",
        }
        catalog_path = conn_base / "connections.json"
        catalog_path.write_text(json.dumps([connection]) + "\n"); catalog_path.chmod(0o600)
        config_value = {
            "schema_version": 1, "connection_id": "conn-acme", "protocol": "vless",
            "mode_id": "vless_ws_tls", "transport": "websocket", "security": "tls",
            "listen_address": "0.0.0.0", "listen_port": 443,
            "transport_options": {"path": "/ws"},
            "security_options": {"certificate_id": imported["certificate_id"]},
        }
        config_file = conn_base / "configurations" / "conn-acme.r000001.json"
        config_file.write_text(json.dumps(config_value) + "\n"); config_file.chmod(0o600)
        runtime_root = run_dir / "leases"
        prepared = certificate_resolver.prepare(
            connection_id="conn-acme", certificate_id=imported["certificate_id"],
            connections_catalog=catalog_path, connections_base=conn_base, vmess_base=vmess_base,
            connection_lock=run_dir / "locks" / "connections.lock",
            certificate_catalog=store_base / "catalog.json", certificate_base=store_base,
            managed_dir=managed, certificate_secrets_dir=secrets,
            certificate_lock=store_base / "catalog.lock", master_key_file=master,
            runtime_root=runtime_root, service_uid=1, service_gid=1,
        )
        self.assertEqual(prepared["status"], "prepared")
        self.assertTrue(pathlib.Path(prepared["certificate_file"]).is_file())
        self.assertTrue(pathlib.Path(prepared["key_file"]).is_file())
        self.assertEqual(certificate_resolver.cleanup(runtime_root, prepared["lease_id"], 1)["status"], "cleaned")

    def test_certbot_lineage_rejects_escape_from_archive(self):
        cert, key = self.make_certificate()
        config = self.base / "letsencrypt"
        archive = config / "archive" / "lineage"; live = config / "live" / "lineage"
        archive.mkdir(parents=True, mode=0o700); live.mkdir(parents=True, mode=0o700); config.chmod(0o700)
        outside = self.base / "outside.pem"; outside.write_bytes(cert.read_bytes())
        (live / "fullchain.pem").symlink_to(outside)
        with self.assertRaises(acme.AcmeError):
            acme._read_certbot_target(live / "fullchain.pem", archive, acme.MAX_CERT_BYTES, private=False)

    def test_issue_requires_explicit_confirmation_before_side_effects(self):
        state_dir = self.base / "requests"
        result = subprocess.run([
            sys.executable, str(ROOT / "scripts" / "certificate_acme.py"), "issue",
            "--method", "dns-01", "--domain", "example.invalid",
            "--email", "ops@example.invalid", "--certbot-bin", "/missing/certbot",
            "--state-dir", str(state_dir),
        ], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--confirm-acme", result.stderr)
        self.assertFalse(state_dir.exists())

    def test_staging_path_is_separate_from_resolver_runtime(self):
        args = acme.build_parser().parse_args([
            "import-certbot", "--method", "dns-01", "--domain", "example.invalid",
            "--email", "ops@example.invalid", "--cert-name", "xray-test", "--request-id",
            "acme-0123456789abcdef0123",
        ])
        self.assertEqual(args.staging_parent, "/run/xray-manager-acme-staging")
        self.assertFalse(args.staging_parent.startswith("/run/xray-manager-certificates/"))

    def test_plan_never_executes_certbot(self):
        result = subprocess.run([
            sys.executable, str(ROOT / "scripts" / "certificate_acme.py"), "plan",
            "--method", "http-01", "--domain", "example.invalid", "--email", "ops@example.invalid",
            "--certbot-bin", "/does/not/run/certbot",
        ], check=True, text=True, capture_output=True)
        data = json.loads(result.stdout)
        self.assertEqual(data["status"], "planned")
        self.assertFalse(data["live_operation"])
        self.assertEqual(data["command"][0], "/does/not/run/certbot")


if __name__ == "__main__":
    unittest.main()
