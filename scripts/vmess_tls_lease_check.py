#!/usr/bin/env python3
"""Validación estructural de un lease TLS VMess emitido por el resolutor."""
import json
import os
import re
import stat
import sys


def main() -> int:
    if len(sys.argv) != 6:
        return 2
    root, lease, cert, key, connection_id = sys.argv[1:]
    if not re.fullmatch(r"resolve-[a-f0-9]{32}", lease):
        return 1
    root = os.path.abspath(root)
    lease_dir = os.path.join(root, lease)
    expected_cert = os.path.join(lease_dir, "certificate.pem")
    expected_key = os.path.join(lease_dir, "private-key.pem")
    if cert != expected_cert or key != expected_key:
        return 1
    root_stat = os.lstat(root)
    lease_stat = os.lstat(lease_dir)
    if (not stat.S_ISDIR(root_stat.st_mode) or root_stat.st_uid != 0
            or stat.S_ISLNK(root_stat.st_mode) or root_stat.st_gid <= 0
            or stat.S_IMODE(root_stat.st_mode) != 0o750):
        return 1
    if (not stat.S_ISDIR(lease_stat.st_mode) or lease_stat.st_uid != 0
            or lease_stat.st_gid <= 0 or stat.S_IMODE(lease_stat.st_mode) != 0o750):
        return 1
    manifest_path = os.path.join(lease_dir, "manifest.json")
    manifest_stat = os.lstat(manifest_path)
    if (not stat.S_ISREG(manifest_stat.st_mode) or manifest_stat.st_size > 16 * 1024 or manifest_stat.st_uid != 0
            or manifest_stat.st_gid != lease_stat.st_gid
            or stat.S_IMODE(manifest_stat.st_mode) != 0o640 or manifest_stat.st_nlink != 1):
        return 1
    with open(manifest_path, "r", encoding="utf-8") as stream:
        manifest = json.load(stream)
    if not isinstance(manifest, dict):
        return 1
    gid = manifest.get("service_gid")
    if (set(manifest) != {"lease_id", "connection_id", "protocol", "certificate_id", "certificate_revision", "certificate_fingerprint_sha256", "service_uid", "service_gid"}
            or not isinstance(manifest.get("certificate_id"), str)
            or not re.fullmatch(r"cert-[A-Za-z0-9][A-Za-z0-9_.-]{0,120}", manifest["certificate_id"])
            or type(manifest.get("certificate_revision")) is not int or manifest["certificate_revision"] < 1
            or not isinstance(manifest.get("certificate_fingerprint_sha256"), str)
            or not re.fullmatch(r"[a-f0-9]{64}", manifest["certificate_fingerprint_sha256"])
            or manifest.get("lease_id") != lease or manifest.get("connection_id") != connection_id
            or manifest.get("protocol") != "vmess" or type(manifest.get("service_uid")) is not int
            or manifest["service_uid"] <= 0 or type(gid) is not int or gid <= 0
            or gid != lease_stat.st_gid or gid != root_stat.st_gid):
        return 1
    for path in (expected_cert, expected_key):
        item = os.lstat(path)
        if (not stat.S_ISREG(item.st_mode) or item.st_uid != 0 or item.st_gid != gid
                or stat.S_IMODE(item.st_mode) != 0o640 or item.st_nlink != 1):
            return 1
    print(gid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
