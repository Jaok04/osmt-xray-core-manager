from __future__ import annotations

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
import xray_runtime_menu_bridge as bridge
import xray_runtime_service_adapter as fixture_adapter


class RuntimeMenuBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name) / "fixture"
        self.root.mkdir(mode=0o700)
        (self.root / ".xray-manager-r02-fixture").write_text(json.dumps({
            "schema_version": 1, "purpose": "xray-runtime-r02-isolated-fixture"
        }))
        (self.root / ".xray-manager-r02-fixture").chmod(0o600)
        self.paths = {name: str(self.root / name) for name in (
            "profile_store", "master_key", "validation_store", "xray_binary", "service_state",
            "bindings_file", "staging_root", "lease_root", "connections_catalog", "connections_base",
            "vmess_base", "connection_lock", "certificate_base", "certificate_catalog", "managed_dir",
            "certificate_secrets_dir", "certificate_lock", "certificate_master_key", "service_root",
            "operation_store", "lifecycle_lock", "application_lock", "adapter_root",
        )}

    def args(self, **changes):
        values = dict(fixture_root=str(self.root), profile_id="profile-test", revision="r000001",
                      service_uid=65534, service_gid=65534, timeout=20, confirm_restart=True,
                      active_profile_store=str(self.root / "active-profile-store"), **self.paths)
        values.update(changes)
        return Namespace(**values)

    @unittest.skipUnless(os.geteuid() == 0, "R-05 fixture bridge requires root")
    def test_menu_bridge_calls_only_default_fixture_backend(self):
        expected = {"status": "PUBLISHED_PENDING_START", "operation_id": "runtime-op-test"}
        with mock.patch.object(bridge.orchestrator, "apply_operation", return_value=expected) as apply:
            result = bridge.apply_from_menu(self.args())
        self.assertEqual(result["execution_scope"], "fixture_only")
        self.assertFalse(result["real_systemd_invoked"])
        self.assertFalse(result["real_xray_modified"])
        kwargs = apply.call_args.kwargs
        self.assertIs(kwargs["service_backend"], fixture_adapter)
        self.assertEqual(kwargs["staging_args"].profile_id, "profile-test")
        self.assertEqual(kwargs["staging_args"].revision, "r000001")

    @unittest.skipUnless(os.geteuid() == 0, "R-05 fixture bridge requires root")
    def test_rejects_any_path_outside_fixture_before_orchestration(self):
        outside = pathlib.Path(self.tmp.name) / "outside"
        with mock.patch.object(bridge.orchestrator, "apply_operation") as apply:
            with self.assertRaises(bridge.MenuBridgeError):
                bridge.apply_from_menu(self.args(service_root=str(outside)))
        apply.assert_not_called()

    @unittest.skipUnless(os.geteuid() == 0, "R-05 fixture bridge requires root")
    def test_requires_active_profile_store_inside_fixture(self):
        with mock.patch.object(bridge.orchestrator, "apply_operation") as apply:
            with self.assertRaises(bridge.MenuBridgeError):
                bridge.apply_from_menu(self.args(active_profile_store=None))
        apply.assert_not_called()

    @unittest.skipUnless(os.geteuid() == 0, "R-05 fixture bridge requires root")
    def test_rejects_fixture_without_exact_marker(self):
        (self.root / ".xray-manager-r02-fixture").write_text('{"schema_version":1,"purpose":"other"}')
        with mock.patch.object(bridge.orchestrator, "apply_operation") as apply:
            with self.assertRaises(bridge.MenuBridgeError):
                bridge.apply_from_menu(self.args())
        apply.assert_not_called()


if __name__ == "__main__":
    unittest.main()
