import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from scripts.xray_config_validator import validate_configuration

VALID = json.dumps({
    "log": {"loglevel": "warning"},
    "inbounds": [{"listen": "127.0.0.1", "port": 10808, "protocol": "socks", "settings": {"udp": True}}],
    "outbounds": [{"protocol": "freedom", "tag": "direct"}],
}).encode()


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.binary = self.root / "xray-fake"
        self.mode = self.root / "mode"
        self.write_binary("pass")

    def tearDown(self):
        self.temp.cleanup()

    def write_binary(self, mode):
        self.mode.write_text(mode)
        self.binary.write_text(
            "#!/bin/sh\n"
            'if [ "$1" = version ]; then echo "Xray test-build"; exit 0; fi\n'
            f'mode="$(cat "{self.mode}")"\n'
            'if [ "$mode" = timeout ]; then exec sleep 3; fi\n'
            'if [ "$mode" = reject ]; then exit 7; fi\n'
            'exit 0\n'
        )
        self.binary.chmod(0o755)

    def validate(self, data=VALID, timeout=2, binary=None):
        return validate_configuration(data, binary or self.binary, timeout)

    def test_valid_configuration_passes_and_hashes_exact_bytes(self):
        result = self.validate()
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["content_sha256"], hashlib.sha256(VALID).hexdigest())
        self.assertEqual(result["checks"][-1]["status"], "PASS")
        self.assertFalse(result["report_persisted"])
        self.assertFalse(result["configuration_applied"])
        self.assertFalse(result["service_started"])

    def test_invalid_json_skips_native(self):
        result = self.validate(b'{"inbounds":')
        self.assertEqual(result["result"], "FAIL")
        self.assertEqual(result["checks"][-1]["name"], "xray_native")
        self.assertEqual(result["checks"][-1]["status"], "NOT_RUN")

    def test_duplicate_keys_fail(self):
        data = b'{"inbounds":[],"inbounds":[],"outbounds":[]}'
        self.assertEqual(self.validate(data)["result"], "FAIL")

    def test_non_object_root_fails(self):
        self.assertEqual(self.validate(b'[]')["result"], "FAIL")

    def test_missing_required_section_fails(self):
        data = b'{"inbounds":[]}'
        result = self.validate(data)
        self.assertEqual(result["result"], "FAIL")
        self.assertEqual(result["checks"][-1]["status"], "NOT_RUN")

    def test_missing_protocol_fails(self):
        data = b'{"inbounds":[{}],"outbounds":[{"protocol":"freedom"}]}'
        self.assertEqual(self.validate(data)["result"], "FAIL")

    def test_same_tag_in_inbound_and_outbound_namespaces_is_not_false_positive(self):
        data = json.dumps({
            "inbounds": [{"protocol": "socks", "tag": "shared"}],
            "outbounds": [{"protocol": "freedom", "tag": "shared"}],
        }).encode()
        result = self.validate(data)
        check = next(x for x in result["checks"] if x["name"] == "references_conflicts")
        self.assertEqual(check["status"], "PASS")

    def test_duplicate_tags_within_same_namespace_fail(self):
        data = json.dumps({
            "inbounds": [{"protocol": "socks", "tag": "same"}, {"protocol": "http", "tag": "same"}],
            "outbounds": [{"protocol": "freedom", "tag": "direct"}],
        }).encode()
        result = self.validate(data)
        check = next(x for x in result["checks"] if x["name"] == "references_conflicts")
        self.assertEqual(check["status"], "FAIL")

    def test_unknown_inbound_reference_fails(self):
        data = json.dumps({
            "inbounds": [{"protocol": "socks", "tag": "local"}],
            "outbounds": [{"protocol": "freedom", "tag": "direct"}],
            "routing": {"rules": [{"inboundTag": ["missing"], "outboundTag": "direct"}]},
        }).encode()
        result = self.validate(data)
        check = next(x for x in result["checks"] if x["name"] == "references_conflicts")
        self.assertEqual(check["status"], "FAIL")

    def test_unknown_outbound_reference_fails(self):
        data = json.dumps({
            "inbounds": [{"protocol": "socks"}],
            "outbounds": [{"protocol": "freedom", "tag": "direct"}],
            "routing": {"rules": [{"type": "field", "outboundTag": "missing"}]},
        }).encode()
        result = self.validate(data)
        self.assertEqual(result["result"], "FAIL")
        check = next(x for x in result["checks"] if x["name"] == "references_conflicts")
        self.assertEqual(check["status"], "FAIL")

    def test_native_rejection_fails(self):
        self.write_binary("reject")
        result = self.validate()
        self.assertEqual(result["result"], "FAIL")
        self.assertEqual(result["checks"][-1]["status"], "FAIL")

    def test_native_timeout_is_incomplete(self):
        self.write_binary("timeout")
        result = self.validate(timeout=1)
        self.assertEqual(result["result"], "INCOMPLETE")

    def test_unsafe_binary_is_incomplete(self):
        self.binary.chmod(0o777)
        result = self.validate()
        self.assertEqual(result["result"], "INCOMPLETE")

    def test_missing_binary_is_incomplete(self):
        result = self.validate(binary=self.root / "absent")
        self.assertEqual(result["result"], "INCOMPLETE")

    def test_symlink_binary_is_incomplete(self):
        link = self.root / "xray-link"
        link.symlink_to(self.binary)
        result = self.validate(binary=link)
        self.assertEqual(result["result"], "INCOMPLETE")

    def test_hardlinked_binary_is_incomplete(self):
        linked = self.root / "xray-hardlink"
        os.link(self.binary, linked)
        result = self.validate(binary=linked)
        self.assertEqual(result["result"], "INCOMPLETE")

    def test_invalid_size_and_timeout_rejected(self):
        with self.assertRaises(ValueError):
            validate_configuration(b"", self.binary)
        with self.assertRaises(ValueError):
            validate_configuration(VALID, self.binary, 0)


if __name__ == "__main__":
    unittest.main()
