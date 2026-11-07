#!/usr/bin/env python3
from __future__ import annotations

import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
import base64
import re
import sys
from urllib.error import HTTPError
from unittest.mock import patch

from scripts import installer_bootstrap as bootstrap


FILES = {
    "install.sh": (b"#!/usr/bin/env bash\necho install\n", "100755"),
    "bin/xray-manager": (b"#!/usr/bin/env bash\necho manager\n", "100755"),
    "config/paths.sh": (b"APP_ROOT=/opt/xray-manager\n", "100644"),
    "modules/main_menu.sh": (b"main_menu() { :; }\n", "100644"),
    "lib/json_store.sh": (b"json_store() { :; }\n", "100644"),
    "lib/operation_lock.sh": (b"manager_lock_acquire() { :; }\n", "100644"),
    "README.md": (b"Manager readme\n", "100644"),
}


def make_tree(files=FILES, *, truncated=False):
    entries = [
        {
            "path": path,
            "mode": mode,
            "type": "blob",
            "sha": bootstrap.git_blob_sha1(data),
            "size": len(data),
        }
        for path, (data, mode) in sorted(files.items())
    ]
    return {"sha": "a" * 40, "truncated": truncated, "tree": entries}


def make_tar(files=FILES, *, root="Jaok04-xray-core-manager-deadbeef", extras=None):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        root_info = tarfile.TarInfo(root + "/")
        root_info.type = tarfile.DIRTYPE
        root_info.mode = 0o755
        archive.addfile(root_info)
        for path, (data, mode) in sorted(files.items()):
            info = tarfile.TarInfo(root + "/" + path)
            info.size = len(data)
            info.mode = 0o755 if mode == "100755" else 0o644
            archive.addfile(info, io.BytesIO(data))
        for name, kind in extras or []:
            info = tarfile.TarInfo(name)
            if kind == "symlink":
                info.type = tarfile.SYMTYPE
                info.linkname = "../../etc/passwd"
            elif kind == "hardlink":
                info.type = tarfile.LNKTYPE
                info.linkname = root + "/README.md"
            elif kind == "directory":
                info.type = tarfile.DIRTYPE
            archive.addfile(info)
    return buffer.getvalue()


class InstallerBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.destination = Path(self.temp.name) / "source"
        self.destination.mkdir(mode=0o700)

    def tearDown(self):
        self.temp.cleanup()

    def test_extracts_exact_verified_tree_and_preserves_executable_modes(self):
        count = bootstrap.extract_verified_tarball(make_tar(), make_tree(), self.destination)
        self.assertEqual(count, len(FILES))
        for path, (data, mode) in FILES.items():
            target = self.destination / path
            self.assertEqual(target.read_bytes(), data)
            self.assertEqual(target.stat().st_mode & 0o777, 0o755 if mode == "100755" else 0o644)
        self.assertFalse((self.destination / ".git").exists())

    def test_rejects_blob_corruption(self):
        altered = dict(FILES)
        altered["README.md"] = (FILES["README.md"][0].replace(b"readme", b"README"), "100644")
        with self.assertRaisesRegex(bootstrap.BootstrapError, "integridad Git"):
            bootstrap.extract_verified_tarball(make_tar(altered), make_tree(), self.destination)

    def test_rejects_missing_file(self):
        subset = dict(FILES)
        subset.pop("README.md")
        with self.assertRaisesRegex(bootstrap.BootstrapError, "está incompleto"):
            bootstrap.extract_verified_tarball(make_tar(subset), make_tree(), self.destination)

    def test_rejects_unexpected_file(self):
        extra = dict(FILES)
        extra["evil.sh"] = (b"bad", "100644")
        with self.assertRaisesRegex(bootstrap.BootstrapError, "no versionado"):
            bootstrap.extract_verified_tarball(make_tar(extra), make_tree(), self.destination)

    def test_rejects_path_traversal(self):
        malicious = dict(FILES)
        malicious["../outside"] = (b"bad", "100644")
        with self.assertRaisesRegex(bootstrap.BootstrapError, "ruta insegura"):
            bootstrap.extract_verified_tarball(make_tar(malicious), make_tree(malicious), self.destination)

    def test_rejects_symlink_and_hardlink_members(self):
        for kind in ("symlink", "hardlink"):
            with self.subTest(kind=kind):
                fresh = Path(self.temp.name) / ("dest-" + kind)
                fresh.mkdir(mode=0o700)
                archive = make_tar(extras=[("Jaok04-xray-core-manager-deadbeef/link", kind)])
                with self.assertRaisesRegex(bootstrap.BootstrapError, "symlink, hardlink"):
                    bootstrap.extract_verified_tarball(archive, make_tree(), fresh)

    def test_rejects_duplicate_members(self):
        archive = make_tar()
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
            root = tarfile.TarInfo("repo/")
            root.type = tarfile.DIRTYPE
            tar.addfile(root)
            for path, (data, mode) in sorted(FILES.items()):
                info = tarfile.TarInfo("repo/" + path)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
            info = tarfile.TarInfo("repo/README.md")
            info.size = len(FILES["README.md"][0])
            tar.addfile(info, io.BytesIO(FILES["README.md"][0]))
        with self.assertRaisesRegex(bootstrap.BootstrapError, "duplicados"):
            bootstrap.extract_verified_tarball(buffer.getvalue(), make_tree(), self.destination)

    def test_rejects_truncated_tree(self):
        with self.assertRaisesRegex(bootstrap.BootstrapError, "truncado"):
            bootstrap.extract_verified_tarball(make_tar(), make_tree(truncated=True), self.destination)

    def test_rejects_symlink_blob_mode_in_git_tree(self):
        tree = make_tree()
        tree["tree"].append({"path": "link", "mode": "120000", "type": "blob", "sha": "b" * 40, "size": 4})
        with self.assertRaisesRegex(bootstrap.BootstrapError, "symlink, submódulo"):
            bootstrap.extract_verified_tarball(make_tar(), tree, self.destination)

    def test_rejects_tree_sha_mismatch_before_network(self):
        with self.assertRaisesRegex(bootstrap.BootstrapError, "no coincide"):
            bootstrap.download_snapshot(
                repo="Jaok04/xray-core-manager",
                commit="c" * 40,
                tree_sha="d" * 40,
                tree=make_tree(),
                token="not-a-real-token",
                destination=self.destination,
            )

    def test_download_uses_authenticated_commit_archive_endpoint(self):
        archive = make_tar()
        requests = []

        class Response:
            def __init__(self, data):
                self.data = data

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, _limit=-1):
                return self.data

        def opener(request, timeout=90):
            requests.append(request)
            self.assertEqual(request.get_header("Authorization"), "Bearer test-token")
            self.assertNotIn("test-token", request.full_url)
            self.assertIn("/tarball/" + "c" * 40, request.full_url)
            return Response(archive)

        count = bootstrap.download_snapshot(
            repo="Jaok04/xray-core-manager",
            commit="c" * 40,
            tree_sha="a" * 40,
            tree=make_tree(),
            token="test-token",
            destination=self.destination,
            opener=opener,
        )
        self.assertEqual(count, len(FILES))
        self.assertEqual(len(requests), 1)


    def test_rejects_github_authentication_failure_without_leaking_token(self):
        def opener(request, timeout=90):
            self.assertEqual(request.get_header("Authorization"), "Bearer secret-token")
            self.assertNotIn("secret-token", request.full_url)
            raise HTTPError(request.full_url, 401, "Unauthorized", {}, None)

        with self.assertRaisesRegex(bootstrap.BootstrapError, "PAT y Contents: Read-only") as caught:
            bootstrap.download_snapshot(
                repo="Jaok04/xray-core-manager",
                commit="c" * 40,
                tree_sha="a" * 40,
                tree=make_tree(),
                token="secret-token",
                destination=self.destination,
                opener=opener,
            )
        self.assertNotIn("secret-token", str(caught.exception))

    def test_rejects_git_tree_with_unsafe_directory_path(self):
        tree = make_tree()
        tree["tree"].append({"path": "../escape", "mode": "040000", "type": "tree", "sha": "d" * 40})
        with self.assertRaisesRegex(bootstrap.BootstrapError, "ruta insegura"):
            bootstrap.extract_verified_tarball(make_tar(), tree, self.destination)

    def test_rejects_tree_without_required_manager_files(self):
        incomplete = {"README.md": FILES["README.md"]}
        with self.assertRaisesRegex(bootstrap.BootstrapError, "archivos esenciales"):
            bootstrap.extract_verified_tarball(make_tar(incomplete), make_tree(incomplete), self.destination)


    def test_install_sh_bootstrap_fetches_helper_from_pinned_commit_and_verifies_sha(self):
        repo_root = Path(__file__).resolve().parents[1]
        installer_text = (repo_root / "install.sh").read_text(encoding="utf-8")
        match = re.search(r"<<'PYBOOTSTRAP'\n(.*?)\nPYBOOTSTRAP", installer_text, re.DOTALL)
        self.assertIsNotNone(match)
        helper_source = (repo_root / "scripts/installer_bootstrap.py").read_bytes()
        helper_blob_sha = bootstrap.git_blob_sha1(helper_source)
        helper_sha256 = __import__("hashlib").sha256(helper_source).hexdigest()
        pin_match = re.search(r'BOOTSTRAP_HELPER_SHA256="([0-9a-f]{64})"', installer_text)
        self.assertIsNotNone(pin_match)
        self.assertEqual(pin_match.group(1), helper_sha256)
        commit_sha = "c" * 40
        tree_sha = "d" * 40
        responses = {
            f"https://api.github.com/repos/Jaok04/xray-core-manager/commits/design%2Fuser-identity-association-v1": {
                "sha": commit_sha,
                "commit": {"tree": {"sha": tree_sha}},
            },
            f"https://api.github.com/repos/Jaok04/xray-core-manager/git/trees/{tree_sha}?recursive=1": {
                "sha": tree_sha,
                "truncated": False,
                "tree": [{"path": "scripts/installer_bootstrap.py", "type": "blob", "mode": "100644", "sha": helper_blob_sha}],
            },
            f"https://api.github.com/repos/Jaok04/xray-core-manager/git/blobs/{helper_blob_sha}": {
                "encoding": "base64",
                "content": base64.b64encode(helper_source).decode("ascii"),
            },
        }

        class Response:
            def __init__(self, data):
                self.data = json.dumps(data).encode("utf-8")
            def __enter__(self): return self
            def __exit__(self, *_args): return False
            def read(self, _limit=-1): return self.data

        def opener(request, timeout=45):
            self.assertEqual(request.get_header("Authorization"), "Bearer unit-test-token")
            self.assertNotIn("unit-test-token", request.full_url)
            if request.full_url not in responses:
                raise AssertionError("Unexpected API URL: " + request.full_url)
            return Response(responses[request.full_url])

        destination = Path(self.temp.name)
        old_argv = sys.argv
        old_token = __import__("os").environ.get("XRAY_MANAGER_GITHUB_TOKEN")
        sys.argv = ["install.sh", "Jaok04/xray-core-manager", "design/user-identity-association-v1", helper_sha256, str(destination), ""]
        __import__("os").environ["XRAY_MANAGER_GITHUB_TOKEN"] = "unit-test-token"
        try:
            with patch("urllib.request.urlopen", side_effect=opener):
                exec(compile(match.group(1), "install.sh:PYBOOTSTRAP", "exec"), {})
        finally:
            sys.argv = old_argv
            if old_token is None:
                __import__("os").environ.pop("XRAY_MANAGER_GITHUB_TOKEN", None)
            else:
                __import__("os").environ["XRAY_MANAGER_GITHUB_TOKEN"] = old_token
        self.assertEqual((destination / "installer_bootstrap.py").read_bytes(), helper_source)
        self.assertEqual(json.loads((destination / "revision.json").read_text()), {"commit": commit_sha, "tree": tree_sha})

    def test_install_sh_bootstrap_rejects_helper_sha_mismatch(self):
        repo_root = Path(__file__).resolve().parents[1]
        installer_text = (repo_root / "install.sh").read_text(encoding="utf-8")
        match = re.search(r"<<'PYBOOTSTRAP'\n(.*?)\nPYBOOTSTRAP", installer_text, re.DOTALL)
        helper_source = (repo_root / "scripts/installer_bootstrap.py").read_bytes()
        helper_blob_sha = bootstrap.git_blob_sha1(helper_source)
        commit_sha = "c" * 40
        tree_sha = "d" * 40
        responses = {
            f"https://api.github.com/repos/Jaok04/xray-core-manager/commits/design%2Fuser-identity-association-v1": {"sha": commit_sha, "commit": {"tree": {"sha": tree_sha}}},
            f"https://api.github.com/repos/Jaok04/xray-core-manager/git/trees/{tree_sha}?recursive=1": {"sha": tree_sha, "truncated": False, "tree": [{"path": "scripts/installer_bootstrap.py", "type": "blob", "mode": "100644", "sha": helper_blob_sha}]},
            f"https://api.github.com/repos/Jaok04/xray-core-manager/git/blobs/{helper_blob_sha}": {"encoding": "base64", "content": base64.b64encode(helper_source).decode("ascii")},
        }
        class Response:
            def __init__(self, data): self.data = json.dumps(data).encode("utf-8")
            def __enter__(self): return self
            def __exit__(self, *_args): return False
            def read(self, _limit=-1): return self.data
        def opener(request, timeout=45): return Response(responses[request.full_url])
        destination = Path(self.temp.name)
        old_argv = sys.argv
        old_token = __import__("os").environ.get("XRAY_MANAGER_GITHUB_TOKEN")
        sys.argv = ["install.sh", "Jaok04/xray-core-manager", "design/user-identity-association-v1", "0" * 64, str(destination), ""]
        __import__("os").environ["XRAY_MANAGER_GITHUB_TOKEN"] = "unit-test-token"
        try:
            with patch("urllib.request.urlopen", side_effect=opener):
                with self.assertRaisesRegex(SystemExit, "integridad del helper"):
                    exec(compile(match.group(1), "install.sh:PYBOOTSTRAP", "exec"), {})
        finally:
            sys.argv = old_argv
            if old_token is None:
                __import__("os").environ.pop("XRAY_MANAGER_GITHUB_TOKEN", None)
            else:
                __import__("os").environ["XRAY_MANAGER_GITHUB_TOKEN"] = old_token
        self.assertFalse((destination / "installer_bootstrap.py").exists())

    def test_rejects_nonempty_destination(self):
        (self.destination / "marker").write_text("preserve")
        with self.assertRaisesRegex(bootstrap.BootstrapError, "no está vacío"):
            bootstrap.extract_verified_tarball(make_tar(), make_tree(), self.destination)

    def test_git_blob_sha_uses_git_object_header(self):
        self.assertEqual(
            bootstrap.git_blob_sha1(b"abc"),
            "f2ba8f84ab5c1bce84a7b441cb1959cfc7093b7f",
        )


if __name__ == "__main__":
    unittest.main()
