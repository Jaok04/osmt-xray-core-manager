#!/usr/bin/env python3
"""Valida una revisión exacta de perfil y persiste su informe vinculado."""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any

import xray_config_validator
import xray_profiles
from xray_profile_validation_store import ProfileValidationError, ProfileValidationReportStore

PROFILE_RE = re.compile(r"profile-[0-9a-f]{32}\Z")
REVISION_RE = re.compile(r"r[0-9]{6}\Z")
PASS_RESULTS = {"PASS", "PASS_WITH_WARNINGS"}


class ProfileValidationServiceError(Exception):
    pass


def _fail(message: str) -> None:
    raise ProfileValidationServiceError(message)


def _validate_profile_tree(store: xray_profiles.ProfileStore, profile_id: str, revision: str) -> None:
    if not PROFILE_RE.fullmatch(profile_id) or not REVISION_RE.fullmatch(revision):
        _fail("Identidad de perfil/revisión inválida.")
    profile = store.profiles / profile_id
    revision_dir = profile / "revisions" / revision
    for directory in (store.root, store.profiles, profile, profile / "revisions", revision_dir):
        info = directory.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_gid != 0 or stat.S_IMODE(info.st_mode) != 0o700:
            _fail("Árbol del perfil/revisión inseguro.")
    for file_path in (store.lock_path, store.transaction_path, profile / "metadata.json",
                      revision_dir / "manifest.json", revision_dir / "config.enc.json"):
        if file_path == store.transaction_path and not (file_path.exists() or file_path.is_symlink()):
            continue
        info = file_path.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_gid != 0
                or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600):
            _fail("Archivo del perfil/revisión con permisos o tipo inseguros.")


@contextlib.contextmanager
def _locked_profiles(store: xray_profiles.ProfileStore):
    if os.geteuid() != 0:
        _fail("La validación de perfiles requiere root.")
    for path in (store.root, store.profiles, store.lock_path):
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            _fail("Ruta simbólica en el almacén de perfiles.")
    for path in (store.root, store.profiles):
        info = path.stat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_gid != 0
                or stat.S_IMODE(info.st_mode) != 0o700):
            _fail("Directorio del almacén de perfiles inseguro.")
    lock_info = store.lock_path.stat()
    if (not stat.S_ISREG(lock_info.st_mode) or lock_info.st_uid != 0 or lock_info.st_gid != 0
            or lock_info.st_nlink != 1 or stat.S_IMODE(lock_info.st_mode) != 0o600):
        _fail("Lock del almacén de perfiles inseguro.")
    fd = os.open(store.lock_path, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_gid != 0 or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600:
            _fail("Lock del almacén de perfiles inseguro.")
        fcntl.flock(fd, fcntl.LOCK_EX)
        store.recover_transaction()
        yield
    finally:
        with contextlib.suppress(OSError):
            fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


class ProfileValidationService:
    def __init__(self, profile_root: str, master_key: str, validation_root: str):
        self.profiles = xray_profiles.ProfileStore(profile_root, master_key)
        self.reports = ProfileValidationReportStore(validation_root)

    def validate(self, profile_id: str, revision: str, xray_binary: str,
                 timeout: int = 20) -> dict[str, Any]:
        if not PROFILE_RE.fullmatch(profile_id) or not REVISION_RE.fullmatch(revision):
            _fail("Identidad de perfil/revisión inválida.")

        # Primera lectura bajo lock exclusivo: no se usa ProfileStore.locked(),
        # porque ese wrapper también limpia artefactos ajenos a esta operación.
        with _locked_profiles(self.profiles):
            _validate_profile_tree(self.profiles, profile_id, revision)
            self.profiles.load_metadata(profile_id)
            content, _manifest = self.profiles.read_revision_config(profile_id, revision)
            content_hash = hashlib.sha256(content).hexdigest()

        report = xray_config_validator.validate_configuration(
            content, xray_binary=xray_binary, timeout=timeout
        )
        if (report.get("content_sha256") != content_hash
                or report.get("content_size_bytes") != len(content)):
            _fail("El validador no devolvió la identidad/hash de los bytes exactos.")

        result = report.get("result")
        if not isinstance(result, str) or result not in {"PASS", "PASS_WITH_WARNINGS", "FAIL", "INCOMPLETE"}:
            _fail("El motor devolvió un resultado desconocido.")
        checks = report.get("checks")
        if not isinstance(checks, list):
            _fail("El motor devolvió un informe sin comprobaciones.")
        xray = report.get("xray", {})
        if not isinstance(xray, dict):
            _fail("Metadatos Xray del informe inválidos.")

        persisted = self.reports.save_report(profile_id, revision, {
            "schema_version": 1,
            "content_sha256": content_hash,
            "content_size_bytes": len(content),
            "created_at": report["created_at"],
            "validator_version": "xray_config_validator/profile-v1",
            "result": result,
            "checks": checks,
            "xray": xray,
        })

        # Segunda lectura y commit transaccional: si la revisión fue alterada o
        # desapareció entre validación y persistencia, no se marca como válida.
        with _locked_profiles(self.profiles):
            _validate_profile_tree(self.profiles, profile_id, revision)
            current_metadata = self.profiles.load_metadata(profile_id)
            current_content, current_manifest = self.profiles.read_revision_config(profile_id, revision)
            if hashlib.sha256(current_content).hexdigest() != content_hash or current_content != content:
                _fail("La revisión cambió entre validación y commit; el perfil no se marca como validado.")

            check_map = {item.get("name"): item for item in checks if isinstance(item, dict)}
            json_check = check_map.get("json_syntax", {})
            if json_check.get("status") != "PASS":
                _fail("El validador contradice la lectura JSON estricta del almacén de perfiles.")
            json_status = "pass"
            if result in PASS_RESULTS:
                xray_status, validation_status, last_validated = "pass", "valid", revision
            elif result == "FAIL":
                xray_status, validation_status, last_validated = "fail", "invalid", revision
            else:
                xray_status, validation_status, last_validated = "not_run", "pending", None

            updated_manifest = dict(current_manifest)
            updated_manifest["validation"] = {
                "json_syntax": json_status,
                "xray_static": xray_status,
                "status": {"pass": "valid", "fail": "invalid", "not_run": "pending"}[xray_status],
            }
            changes = {
                self.profiles.profiles / profile_id / "revisions" / revision / "manifest.json":
                    xray_profiles.json_bytes(updated_manifest),
            }
            # metadata.json resume el estado de la revisión actual, no de una
            # revisión histórica seleccionada explícitamente.
            if revision == current_metadata["current_revision"]:
                updated_metadata = dict(current_metadata)
                updated_metadata["validation_status"] = validation_status
                updated_metadata["last_validated_revision"] = last_validated
                changes[self.profiles.profiles / profile_id / "metadata.json"] = xray_profiles.json_bytes(updated_metadata)
            self.profiles.commit_transaction(changes)

        return {
            "validation_id": persisted["validation_id"],
            "profile_id": profile_id,
            "revision": revision,
            "content_sha256": content_hash,
            "result": result,
            "validation_status": validation_status,
            "last_validated_revision": current_metadata["last_validated_revision"],
            "profile_validation_status": current_metadata["validation_status"],
            "current_revision": current_metadata["current_revision"],
            "selected_revision_is_current": revision == current_metadata["current_revision"],
            "report_persisted": True,
            "configuration_applied": False,
            "service_started": False,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida una revisión exacta de perfil sin aplicar runtime.")
    parser.add_argument("--profile-store", required=True)
    parser.add_argument("--master-key", required=True)
    parser.add_argument("--validation-store", required=True)
    parser.add_argument("--profile-id", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--xray-binary", required=True)
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args()
    try:
        service = ProfileValidationService(args.profile_store, args.master_key, args.validation_store)
        result = service.validate(args.profile_id, args.revision, args.xray_binary, args.timeout)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (ProfileValidationServiceError, xray_profiles.ProfileError,
            ProfileValidationError, xray_config_validator.ValidationInputError,
            OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
