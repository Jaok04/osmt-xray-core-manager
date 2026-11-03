#!/usr/bin/env python3
"""Orquestador de snapshot compartido v1; no incluye secretos ni aplica runtime."""
from __future__ import annotations

import argparse
import copy
import fcntl
import getpass
import hashlib
import io
import json
import math
import os
import re
import shutil
import stat
import struct
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import certificate_store
import shared_backup_format as crypto
import shared_backup_zip as package_zip
import vmess_config_store
import vless_config_store

MAX_JSON_BYTES = 4 * 1024 * 1024
MAX_CONFIG_BYTES = 512 * 1024
MAX_CERTIFICATE_BYTES = 4 * 1024 * 1024
MAX_SAFE_INTEGER = (1 << 53) - 1
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
SUPPORTED_CATEGORIES = {
    "connections.vless", "connections.vmess", "identities", "certificates.tls"
}
DEFAULT_CATEGORIES = sorted(SUPPORTED_CATEGORIES)
SENSITIVE_KEYS = {
    "uuid", "password", "private_key", "privatekey", "secret", "secret_value",
    "token", "api_key", "access_token", "refresh_token", "preshared_key",
    "pre_shared_key", "presharedkey", "psk", "peer_private_key",
    "wireguard_private_key", "wg_private_key", "peer_key",
}


class SnapshotError(Exception):
    """Fallo operativo o de validación del snapshot."""


class SnapshotBlocked(SnapshotError):
    """Preflight fail-closed: no debe publicarse ningún paquete."""


@dataclass(frozen=True)
class SnapshotPaths:
    connections_root: Path = Path("/var/lib/xray-manager/connections")
    users_root: Path = Path("/var/lib/xray-manager/users")
    vmess_root: Path = Path("/var/lib/xray-manager/vmess")
    certificates_root: Path = Path("/var/lib/xray-manager/certificates")
    lifecycle_lock: Path = Path("/run/lock/xray-manager-lifecycle.lock")
    integrity_lock: Path = Path("/run/xray-manager/integrity.lock")
    catalog_lock: Path = Path("/run/xray-manager-certificate-locks/catalog.lock")

    @property
    def connections_catalog(self) -> Path:
        return self.connections_root / "connections.json"

    @property
    def users_catalog(self) -> Path:
        return self.users_root / "users.json"

    @property
    def certificates_catalog(self) -> Path:
        return self.certificates_root / "catalog.json"

    @property
    def certificates_managed(self) -> Path:
        return self.certificates_root / "managed"


DEFAULT_PATHS = SnapshotPaths()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("clave JSON duplicada")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"constante JSON no permitida: {value}")


def strict_json_loads(raw: bytes) -> Any:
    try:
        return json.loads(
            raw.decode("utf-8", "strict"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise SnapshotBlocked("JSON de origen inválido, duplicado o no UTF-8") from exc


def _validate_json_value(value: Any, depth: int = 0) -> None:
    if depth > 100:
        raise SnapshotBlocked("estructura JSON excede la profundidad permitida")
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        if not -MAX_SAFE_INTEGER <= value <= MAX_SAFE_INTEGER:
            raise SnapshotBlocked("entero JSON fuera del rango interoperable v1")
        return
    if isinstance(value, str):
        try:
            value.encode("utf-8", "strict")
        except UnicodeError as exc:
            raise SnapshotBlocked("string JSON contiene Unicode inválido") from exc
        return
    if isinstance(value, list):
        for item in value:
            _validate_json_value(item, depth + 1)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise SnapshotBlocked("clave JSON no textual")
            _validate_json_value(key, depth + 1)
            _validate_json_value(item, depth + 1)
        return
    raise SnapshotBlocked("tipo JSON no admitido por canonicalización v1")


def canonical_json(value: Any) -> bytes:
    _validate_json_value(value)
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8", "strict")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise SnapshotBlocked("no fue posible canonicalizar JSON v1") from exc


def _path_exists(path: Path) -> bool:
    try:
        path.lstat()
        return True
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise SnapshotBlocked("no se pudo inspeccionar un recurso de origen") from exc


def _read_json(path: Path, root: Path, limit: int) -> tuple[Any, bytes]:
    try:
        raw = package_zip.read_root_regular(path, root, limit=limit)
    except package_zip.SharedBackupZipError as exc:
        raise SnapshotBlocked("archivo de origen ausente o inseguro") from exc
    return strict_json_loads(raw), raw


def _check_sensitive_keys(value: Any, *, context: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key.casefold() in SENSITIVE_KEYS:
                raise SnapshotBlocked(f"campo sensible no saneado en {context}")
            _check_sensitive_keys(item, context=context)
    elif isinstance(value, list):
        for item in value:
            _check_sensitive_keys(item, context=context)


def _safe_connection_id(value: Any) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise SnapshotBlocked("ID de conexión inválido")
    return value


def _catalog_entry_protocol(entry: dict[str, Any]) -> str | None:
    protocol_id = entry.get("protocol_id")
    if not isinstance(protocol_id, str):
        raise SnapshotBlocked("modalidad de conexión inválida")
    if protocol_id in vless_config_store.MODES:
        return "vless"
    if protocol_id in vmess_config_store.MODES:
        return "vmess"
    if protocol_id.startswith("vless_") or protocol_id.startswith("vmess_"):
        raise SnapshotBlocked("modalidad VLESS/VMess no registrada en su adaptador")
    return None


def _validate_connection_catalog(value: Any) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    if not isinstance(value, list):
        raise SnapshotBlocked("catálogo de conexiones no es un arreglo")
    entries: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    for item in value:
        if not isinstance(item, dict):
            raise SnapshotBlocked("registro de conexión no es objeto")
        cid = _safe_connection_id(item.get("id"))
        if cid in by_id:
            raise SnapshotBlocked("ID de conexión duplicado")
        if not isinstance(item.get("name"), str) or not item["name"]:
            raise SnapshotBlocked("nombre de conexión inválido")
        if type(item.get("port")) is not int or not 1 <= item["port"] <= 65535:
            raise SnapshotBlocked("puerto de conexión inválido")
        if type(item.get("max_users")) is not int or item["max_users"] < 1:
            raise SnapshotBlocked("capacidad de conexión inválida")
        if not isinstance(item.get("state"), str) or type(item.get("runtime_applied")) is not bool:
            raise SnapshotBlocked("estado/runtime de conexión inválido")
        by_id[cid] = item
        entries.append(item)
    return entries, by_id


def _validate_vless_reference(entry: dict[str, Any]) -> tuple[str | None, int | None]:
    cid = _safe_connection_id(entry["id"])
    ref = entry.get("configuration_ref")
    secret_ref = entry.get("secret_ref")
    metadata = ("configuration_schema_version", "configuration_revision", "configuration_ref", "secret_ref")
    if ref is None:
        if any(key in entry and entry.get(key) is not None for key in metadata):
            raise SnapshotBlocked("metadatos VLESS parciales sin configuración referenciada")
        return None, None
    match = re.fullmatch(rf"configurations/{re.escape(cid)}\.r([0-9]{{6}})\.json", ref if isinstance(ref, str) else "")
    if not match:
        raise SnapshotBlocked("referencia de configuración VLESS inválida")
    revision = int(match.group(1))
    if type(entry.get("configuration_revision")) is not int or entry["configuration_revision"] != revision:
        raise SnapshotBlocked("revisión VLESS no coincide con su referencia")
    if type(entry.get("configuration_schema_version")) is not int or entry["configuration_schema_version"] != 1:
        raise SnapshotBlocked("schema VLESS no admitido")
    if secret_ref is not None and not isinstance(secret_ref, str):
        raise SnapshotBlocked("referencia de secreto VLESS inválida")
    return ref, revision


def _load_protocol_config(
    protocol: str, entry: dict[str, Any], paths: SnapshotPaths
) -> tuple[dict[str, Any] | None, Path | None, str | None, int | None]:
    cid = _safe_connection_id(entry["id"])
    if protocol == "vless":
        ref, revision = _validate_vless_reference(entry)
        secret_ref = entry.get("secret_ref")
        root = paths.connections_root
        store = vless_config_store
    else:
        ref = entry.get("vmess_configuration_ref")
        secret_ref = entry.get("vmess_secret_ref")
        root = paths.vmess_root
        store = vmess_config_store
        metadata = (
            "vmess_configuration_ref", "vmess_configuration_revision",
            "vmess_configuration_schema_version", "vmess_secret_ref",
        )
        if ref is None:
            if any(key in entry and entry.get(key) is not None for key in metadata):
                raise SnapshotBlocked("metadatos VMess parciales sin configuración referenciada")
            if secret_ref is not None:
                raise SnapshotBlocked("secreto VMess sin configuración referenciada")
            return None, None, None, None
        match = re.fullmatch(rf"configurations/{re.escape(cid)}\.r([0-9]{{6}})\.json", ref if isinstance(ref, str) else "")
        if not match:
            raise SnapshotBlocked("referencia de configuración VMess inválida")
        revision = int(match.group(1))
        if type(entry.get("vmess_configuration_revision")) is not int or entry["vmess_configuration_revision"] != revision:
            raise SnapshotBlocked("revisión VMess no coincide con su referencia")
        if type(entry.get("vmess_configuration_schema_version")) is not int or entry["vmess_configuration_schema_version"] != 1:
            raise SnapshotBlocked("schema VMess no admitido")
        if secret_ref is not None and not isinstance(secret_ref, str):
            raise SnapshotBlocked("referencia de secreto VMess inválida")
    if ref is None:
        if secret_ref is not None:
            raise SnapshotBlocked("secreto de conexión sin configuración")
        return None, None, None, None
    config_path = root / ref
    config_limit = store.MAX_CONFIG
    config, _ = _read_json(config_path, root, config_limit)
    if not isinstance(config, dict):
        raise SnapshotBlocked("configuración de protocolo no es objeto")
    try:
        if protocol == "vless":
            store.validate_config(config, entry, secret_ref, allow_legacy_tls=True)
        else:
            store.validate_catalog_metadata(entry, ref, config, secret_ref)
            store.validate(config, entry, secret_ref, allow_legacy_tls=True)
    except Exception as exc:
        raise SnapshotBlocked(f"configuración {protocol.upper()} inválida o referencia incoherente") from exc
    return config, config_path, secret_ref, revision


def _sanitize_protocol_config(
    protocol: str, config: dict[str, Any], entry: dict[str, Any], secret_ref: str | None
) -> tuple[dict[str, Any], list[tuple[str, str]], list[tuple[str, str, str | None]]]:
    sanitized = copy.deepcopy(config)
    security_options = sanitized.get("security_options")
    if not isinstance(security_options, dict):
        raise SnapshotBlocked("security_options inválido")
    exclusions: list[tuple[str, str]] = []
    dependencies: list[tuple[str, str, str | None]] = []
    security = sanitized.get("security")
    if security == "reality":
        security_options.pop("secret_ref", None)
        secret_class = f"{protocol}_reality_private_key"
        exclusions.append((secret_class, "excluded_by_default"))
    elif security == "tls" and "certificate_file" in security_options:
        security_options.pop("certificate_file", None)
        security_options.pop("secret_ref", None)
        security_options["certificate_reference_required"] = True
        secret_class = f"{protocol}_tls_private_key"
        exclusions.append((secret_class, "excluded_by_default"))
        dependencies.append(("tls_legacy_reference", f"legacy:{entry['id']}", None))
    elif security == "tls" and "certificate_id" in security_options:
        certificate_id = security_options["certificate_id"]
        if not isinstance(certificate_id, str) or not certificate_store.ID_RE.fullmatch(certificate_id):
            raise SnapshotBlocked("certificate_id TLS central inválido")
        dependencies.append(("tls_certificate", certificate_id, None))
    if protocol == "vmess":
        users = sanitized.get("users")
        if not isinstance(users, list):
            raise SnapshotBlocked("usuarios VMess inválidos")
        for user in users:
            if not isinstance(user, dict) or "id" not in user:
                raise SnapshotBlocked("registro de usuario VMess sin UUID")
            user.pop("id", None)
        if users:
            exclusions.append(("vmess_uuid", "excluded_by_default"))
    _check_sensitive_keys(sanitized, context=f"configuración {protocol}")
    return sanitized, exclusions, dependencies


def _validate_identity_catalog(
    value: Any, connections_by_id: dict[str, dict[str, Any]]
) -> tuple[dict[str, Any], list[tuple[str, str, str, str, str]]]:
    """Exporta sólo metadatos permitidos; peers WireGuard/protocolos ajenos a v1 se excluyen."""
    if value == []:
        return {"schema_version": 2, "identities": [], "associations": []}, []
    if not isinstance(value, dict) or set(value) != {"schema_version", "identities", "associations"} or value.get("schema_version") != 2:
        raise SnapshotBlocked("catálogo de identidades no usa el esquema v2 admitido")
    identities = value.get("identities")
    associations = value.get("associations")
    if not isinstance(identities, list) or not isinstance(associations, list):
        raise SnapshotBlocked("identities/associations deben ser arreglos")

    identity_fields = {"id", "created_at"}
    association_fields = {
        "id", "identity_id", "connection_id", "alias", "protocol", "credential",
        "created_at", "duration", "expires_at", "suspended_at", "remaining_seconds",
        "traffic_limit_bytes", "simultaneous_connection_limit", "state",
        "provisioning_status", "runtime",
    }
    identity_ids: set[str] = set()
    clean_identities: list[dict[str, Any]] = []
    for identity in identities:
        if not isinstance(identity, dict) or set(identity) != identity_fields:
            raise SnapshotBlocked("identidad contiene campos no permitidos o estructura incompleta")
        if not isinstance(identity.get("id"), str) or not UUID_RE.fullmatch(identity["id"]):
            raise SnapshotBlocked("ID de identidad inválido")
        if identity["id"] in identity_ids or not isinstance(identity.get("created_at"), str) or not identity["created_at"]:
            raise SnapshotBlocked("identidad duplicada o metadatos inválidos")
        identity_ids.add(identity["id"])
        clean_identities.append({"id": identity["id"], "created_at": identity["created_at"]})

    association_ids: set[str] = set()
    seen_identity_connection: set[tuple[str, str]] = set()
    sanitized_associations: list[dict[str, Any]] = []
    exclusions: list[tuple[str, str, str, str, str]] = []
    for original in associations:
        if not isinstance(original, dict) or not set(original).issubset(association_fields):
            raise SnapshotBlocked("asociación contiene campos no permitidos; se bloquea para evitar fuga de credenciales")
        required = {"id", "identity_id", "connection_id", "alias", "protocol", "credential", "created_at"}
        if not required.issubset(original):
            raise SnapshotBlocked("asociación incompleta")
        aid, iid, cid = original["id"], original["identity_id"], original["connection_id"]
        protocol, credential = original["protocol"], original["credential"]
        if not isinstance(aid, str) or not UUID_RE.fullmatch(aid) or aid in association_ids:
            raise SnapshotBlocked("ID de asociación inválido o duplicado")
        if not isinstance(iid, str) or iid not in identity_ids or not isinstance(cid, str) or cid not in connections_by_id:
            raise SnapshotBlocked("asociación referencia identidad/conexión inexistente")
        if not isinstance(original["alias"], str) or not original["alias"] or len(original["alias"]) > 64:
            raise SnapshotBlocked("alias de asociación inválido")
        if not isinstance(original["created_at"], str) or not original["created_at"]:
            raise SnapshotBlocked("fecha de creación de asociación inválida")
        if not isinstance(protocol, str) or not isinstance(credential, dict) or set(credential) != {"type", "value"}:
            raise SnapshotBlocked("credencial/asociación inválida")
        if not isinstance(credential.get("type"), str) or not credential["type"] or not isinstance(credential.get("value"), str) or not credential["value"]:
            raise SnapshotBlocked("valor de credencial de asociación inválido")

        protocol_id = connections_by_id[cid].get("protocol_id")
        if isinstance(protocol_id, str) and protocol_id.startswith("vless_"):
            expected_protocol = "vless"
        elif isinstance(protocol_id, str) and protocol_id.startswith("wireguard"):
            expected_protocol = "wireguard"
        else:
            expected_protocol = protocol_id
        if protocol != expected_protocol:
            raise SnapshotBlocked("protocolo de asociación no coincide con la conexión")

        if "duration" in original:
            duration = original["duration"]
            if not isinstance(duration, dict) or duration.get("kind") not in ("unlimited", "custom"):
                raise SnapshotBlocked("duración de asociación inválida")
            if set(duration) - {"kind", "value", "unit"}:
                raise SnapshotBlocked("duración contiene campos no permitidos")
            if duration["kind"] == "custom" and (
                type(duration.get("value")) is not int or duration["value"] <= 0
                or duration.get("unit") not in ("days", "hours", "minutes")
                or set(duration) != {"kind", "value", "unit"}
            ):
                raise SnapshotBlocked("duración personalizada inválida")
            if duration["kind"] == "unlimited" and set(duration) != {"kind"}:
                raise SnapshotBlocked("duración ilimitada inválida")
        for field in ("expires_at", "suspended_at"):
            if field in original and original[field] is not None and not isinstance(original[field], str):
                raise SnapshotBlocked(f"{field} inválido")
        if "remaining_seconds" in original and original["remaining_seconds"] is not None and (
            type(original["remaining_seconds"]) is not int or original["remaining_seconds"] < 0
        ):
            raise SnapshotBlocked("remaining_seconds inválido")
        for field in ("traffic_limit_bytes", "simultaneous_connection_limit"):
            if field in original and original[field] is not None and (
                type(original[field]) is not int or original[field] <= 0
            ):
                raise SnapshotBlocked(f"{field} inválido")
        if "state" in original and original["state"] not in ("active", "suspended", "expired"):
            raise SnapshotBlocked("estado de asociación inválido")
        if "provisioning_status" in original and original["provisioning_status"] not in ("draft", "pending", "applied", "failed"):
            raise SnapshotBlocked("provisioning_status inválido")
        if "runtime" in original:
            runtime = original["runtime"]
            if (
                not isinstance(runtime, dict) or set(runtime) != {"status", "last_applied_at"}
                or runtime.get("status") not in ("not_applied", "applied", "unknown", "pending", "failed")
                or (runtime.get("last_applied_at") is not None and not isinstance(runtime["last_applied_at"], str))
            ):
                raise SnapshotBlocked("metadatos runtime de asociación inválidos")

        association_ids.add(aid)
        key = (iid, cid)
        if protocol != "wireguard" and key in seen_identity_connection:
            raise SnapshotBlocked("asociación identidad/conexión duplicada")
        seen_identity_connection.add(key)

        supported = protocol == "vless" or (
            protocol.startswith("vmess_") and protocol_id in vmess_config_store.MODES
        )
        if protocol == "wireguard" or not supported:
            secret_class = "wireguard_peer_keys" if protocol == "wireguard" else "unsupported_association"
            exclusions.append((aid, secret_class, "unsupported_protocol", cid, iid))
            continue

        if credential["type"] != "uuid":
            raise SnapshotBlocked("tipo de credencial no admitido para asociación VLESS/VMess")
        clean_assoc = {key: copy.deepcopy(item) for key, item in original.items() if key != "credential"}
        clean_assoc["credential_type"] = credential["type"]
        _check_sensitive_keys(clean_assoc, context="asociación")
        sanitized_associations.append(clean_assoc)
        exclusions.append((aid, "vless_uuid" if protocol == "vless" else "vmess_uuid", "excluded_by_default", cid, iid))

    sanitized = {
        "schema_version": 2,
        "identities": clean_identities,
        "associations": sanitized_associations,
    }
    _check_sensitive_keys(sanitized, context="catálogo de identidades")
    return sanitized, exclusions


def _certificate_public_metadata(certificate_bytes: bytes) -> dict[str, Any]:
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        certificate = x509.load_pem_x509_certificate(certificate_bytes)
        public_der = certificate.public_key().public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        try:
            sans = sorted(set(certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.DNSName)))
        except x509.ExtensionNotFound:
            sans = []
        return {
            "fingerprint_sha256": certificate.fingerprint(hashes.SHA256()).hex(),
            "public_key_fingerprint_sha256": hashlib.sha256(public_der).hexdigest(),
            "subject": certificate.subject.rfc4514_string(),
            "issuer": certificate.issuer.rfc4514_string(),
            "sans": sans,
            "not_before": certificate.not_valid_before.replace(tzinfo=timezone.utc).isoformat(),
            "not_after": certificate.not_valid_after.replace(tzinfo=timezone.utc).isoformat(),
        }
    except Exception as exc:
        raise SnapshotBlocked("certificado público PEM inválido") from exc


def _add_exclusion(
    exclusions: dict[str, dict[str, Any]], resource_id: str, secret_class: str,
    reason: str, *, token: str | None = None,
    association_id: str | None = None, identity_id: str | None = None,
    connection_id: str | None = None,
) -> str:
    exclusion_id = f"exclude:{resource_id}:{secret_class}" + (f":{token}" if token else "")
    existing = exclusions.get(exclusion_id)
    record = {
        "exclusion_id": exclusion_id,
        "resource_id": resource_id,
        "secret_class": secret_class,
        "reason": reason,
    }
    if association_id is not None:
        record["association_id"] = association_id
    if identity_id is not None:
        record["identity_id"] = identity_id
    if connection_id is not None:
        record["connection_id"] = connection_id
    if existing is not None and existing != record:
        raise SnapshotBlocked("colisión de ID de exclusión")
    exclusions[exclusion_id] = record
    return exclusion_id


def _add_dependency(
    dependencies: dict[str, dict[str, Any]],
    dependency_id: str,
    dependency_type: str,
    resource_id: str,
    fingerprint: str | None,
    validation: str,
    *, dependent_connection: str | None = None,
) -> str:
    record = {
        "dependency_id": dependency_id,
        "dependency_type": dependency_type,
        "resource_id": resource_id,
        "fingerprint_sha256": fingerprint,
        "required": True,
        "validation": validation,
        "dependent_connections": [dependent_connection] if dependent_connection else [],
    }
    existing = dependencies.get(dependency_id)
    if existing is not None and existing != record:
        # Un mismo certificado puede aparecer en varias conexiones; su metadata
        # y resultado de validación deben ser idénticos.
        if (
            existing["resource_id"] != resource_id
            or existing["fingerprint_sha256"] != fingerprint
            or existing["dependency_type"] != dependency_type
        ):
            raise SnapshotBlocked("dependencia duplicada con metadatos incompatibles")
        existing["dependent_connections"] = sorted(set(
            existing.get("dependent_connections", [])
            + ([dependent_connection] if dependent_connection else [])
        ))
        if existing["validation"] != validation:
            priority = {"included": 0, "pending_restore_preflight": 1, "not_included": 2, "missing_source_resource": 3}
            if priority.get(validation, 9) > priority.get(existing["validation"], 9):
                existing["validation"] = validation
        return dependency_id
    dependencies[dependency_id] = record
    return dependency_id


def _new_resource(
    resource_id: str,
    resource_type: str,
    protocol: str | None,
    member_ids: list[str] | None = None,
    dependency_ids: list[str] | None = None,
    exclusion_ids: list[str] | None = None,
    completeness: str = "COMPLETE",
) -> dict[str, Any]:
    return {
        "resource_id": resource_id,
        "resource_type": resource_type,
        "protocol": protocol,
        "completeness": completeness,
        "member_ids": sorted(set(member_ids or [])),
        "dependency_ids": sorted(set(dependency_ids or [])),
        "exclusion_ids": sorted(set(exclusion_ids or [])),
    }


def _validate_destination_parent(parent: Path) -> None:
    """Valida toda la cadena; sólo admite ancestros modificables con sticky bit.

    El directorio final debe ser root-only 0700. Un ancestro root-owned 0755
    es seguro; group/world-writable sólo se admite con sticky bit (p. ej. /tmp).
    """
    parent = Path(parent).absolute()
    if ".." in parent.parts:
        raise SnapshotBlocked("directorio destino no normalizado")
    current = Path(parent.anchor)
    for index, part in enumerate(parent.parts[1:]):
        current /= part
        try:
            st = current.lstat()
        except OSError as exc:
            raise SnapshotBlocked("directorio destino ausente o inseguro") from exc
        if not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode) or st.st_uid != 0 or st.st_gid != 0:
            raise SnapshotBlocked("directorio destino y antecesores deben ser root:root sin symlinks")
        mode = stat.S_IMODE(st.st_mode)
        sticky = bool(st.st_mode & stat.S_ISVTX)
        is_final = index == len(parent.parts[1:]) - 1
        if is_final:
            if mode != 0o700 or sticky:
                raise SnapshotBlocked("directorio destino debe tener modo 0700")
        elif mode & 0o022 and not sticky:
            raise SnapshotBlocked("antecesor del destino permite escritura grupal/mundial sin sticky bit")


def _open_lock_file(path: Path) -> int:
    path = Path(path).absolute()
    if ".." in path.parts or not path.name:
        raise SnapshotBlocked("ruta de lock no normalizada")
    dir_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    directory_fd = os.open(path.anchor, dir_flags)
    try:
        for part in path.parts[1:-1]:
            try:
                next_fd = os.open(part, dir_flags, dir_fd=directory_fd)
            except FileNotFoundError as exc:
                # El backup nunca crea directorios operativos para hacer posible
                # la captura: los locks deben existir previamente.
                raise SnapshotBlocked("directorio padre de lock ausente") from exc
            st = os.fstat(next_fd)
            mode = stat.S_IMODE(st.st_mode)
            sticky = bool(st.st_mode & stat.S_ISVTX)
            if (
                not stat.S_ISDIR(st.st_mode)
                or st.st_uid != 0 or st.st_gid != 0
                or (mode & 0o022 and not sticky)
            ):
                os.close(next_fd)
                raise SnapshotBlocked("directorio padre de lock inseguro")
            os.close(directory_fd)
            directory_fd = next_fd
        try:
            before = os.stat(path.name, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            before = None
        if before is not None and (
            not stat.S_ISREG(before.st_mode) or stat.S_ISLNK(before.st_mode)
            or before.st_uid != 0 or before.st_gid != 0
            or stat.S_IMODE(before.st_mode) != 0o600 or before.st_nlink != 1
        ):
            raise SnapshotBlocked("archivo de lock inseguro")
        fd = os.open(
            path.name,
            os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=directory_fd,
        )
        opened = os.fstat(fd)
        if (
            not stat.S_ISREG(opened.st_mode) or opened.st_uid != 0 or opened.st_gid != 0
            or opened.st_nlink != 1
            or (before is not None and (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino))
        ):
            os.close(fd)
            raise SnapshotBlocked("archivo de lock no regular")
        os.fchown(fd, 0, 0)
        os.fchmod(fd, 0o600)
        return fd
    finally:
        os.close(directory_fd)


@contextmanager
def acquire_snapshot_locks(paths: SnapshotPaths, timeout: float = 30.0) -> Iterator[None]:
    if timeout < 0:
        raise SnapshotBlocked("timeout de locks inválido")
    deadline = time.monotonic() + timeout
    acquired: list[int] = []
    try:
        for lock_path in (paths.lifecycle_lock, paths.integrity_lock, paths.catalog_lock):
            fd = _open_lock_file(lock_path)
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired.append(fd)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        os.close(fd)
                        raise SnapshotBlocked("timeout esperando locks del snapshot")
                    time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
                except OSError as exc:
                    os.close(fd)
                    raise SnapshotBlocked("no fue posible adquirir lock del snapshot") from exc
        yield
    finally:
        for fd in reversed(acquired):
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)


def _member_record(member: package_zip.ZipMember, category: str) -> dict[str, Any]:
    return {
        "member_id": "sha256:" + member.sha256,
        "logical_path": member.name,
        "category": category,
        "media_type": "application/json" if member.name.endswith(".json") else "application/x-pem-file",
        "size_bytes": member.size,
        "sha256": member.sha256,
    }


def _register_member(
    member: package_zip.ZipMember,
    category: str,
    members_by_hash: dict[str, package_zip.ZipMember],
    categories_by_hash: dict[str, str],
) -> str:
    digest = member.sha256
    existing = members_by_hash.get(digest)
    if existing is None:
        members_by_hash[digest] = member
        categories_by_hash[digest] = category
    elif existing.size != member.size:
        raise SnapshotBlocked("colisión SHA-256 con tamaños incompatibles")
    return "sha256:" + digest



def _external_dependencies_member(
    dependencies: dict[str, dict[str, Any]],
    cert_records: dict[str, dict[str, Any]],
) -> package_zip.ZipMember:
    """Build the protected dependency index for externally managed certificates."""
    external_by_id: dict[str, dict[str, Any]] = {}
    for dependency in dependencies.values():
        if dependency["dependency_type"] != "tls_reference":
            continue
        dependency_id = dependency["dependency_id"]
        certificate_id = dependency_id.removeprefix("tls:")
        record = cert_records.get(certificate_id)
        if record is None or record.get("storage_type") != "reference":
            continue
        item = external_by_id.setdefault(certificate_id, {
            "certificate_id": certificate_id,
            "fingerprint_sha256": record["fingerprint_sha256"],
            "expected_path": record["certificate_source"],
            "dependent_connections": [],
            "validation_required": "regular_file_no_symlink_no_hardlink_fingerprint_and_key_pair",
        })
        if item["fingerprint_sha256"] != record["fingerprint_sha256"] or item["expected_path"] != record["certificate_source"]:
            raise SnapshotBlocked("referencia TLS externa duplicada con metadatos incompatibles")
        item["dependent_connections"].extend(dependency.get("dependent_connections", []))
    external_items = []
    for certificate_id in sorted(external_by_id):
        item = external_by_id[certificate_id]
        item["dependent_connections"] = sorted(set(item["dependent_connections"]))
        external_items.append(item)
    return package_zip.ZipMember.from_bytes(
        "external-dependencies.json",
        canonical_json({"schema_version": 1, "dependencies": external_items}),
    )

def _build_snapshot_members(
    paths: SnapshotPaths,
    requested: list[str],
    selection_mode: str,
) -> tuple[list[package_zip.ZipMember], dict[str, Any]]:
    connections_catalog_present = _path_exists(paths.connections_catalog)
    if not connections_catalog_present:
        if "connections.vless" in requested or "connections.vmess" in requested or "identities" in requested:
            raise SnapshotBlocked("catálogo compartido de conexiones ausente")
        connections_raw = b"[]"
        connection_entries: list[dict[str, Any]] = []
        connections_by_id: dict[str, dict[str, Any]] = {}
    else:
        connection_value, connections_raw = _read_json(paths.connections_catalog, paths.connections_root, MAX_JSON_BYTES)
        connection_entries, connections_by_id = _validate_connection_catalog(connection_value)

    cert_catalog_raw = b""
    if _path_exists(paths.certificates_catalog):
        try:
            cert_catalog_value, cert_catalog_raw = _read_json(
                paths.certificates_catalog, paths.certificates_root, MAX_JSON_BYTES
            )
            cert_catalog = certificate_store.load_catalog(paths.certificates_catalog)
            if cert_catalog_value != cert_catalog:
                raise SnapshotBlocked("catálogo TLS cambia entre validaciones")
        except SnapshotError:
            raise
        except Exception as exc:
            raise SnapshotBlocked("catálogo TLS central inválido") from exc
    else:
        cert_catalog = {"schema_version": 1, "revision": 0, "certificates": []}
    cert_records = {item["certificate_id"]: item for item in cert_catalog["certificates"]}

    requested_set = set(requested)
    unsupported = {category for category in requested_set if category not in SUPPORTED_CATEGORIES}
    protocols = {cid: _catalog_entry_protocol(entry) for cid, entry in connections_by_id.items()}
    if selection_mode == "all_available" and any(protocol is None for protocol in protocols.values()):
        requested_set.add("connections.other")
        unsupported.add("connections.other")
    requested = sorted(requested_set)

    members_by_hash: dict[str, package_zip.ZipMember] = {}
    categories_by_hash: dict[str, str] = {}
    resources: dict[str, dict[str, Any]] = {}
    exclusions: dict[str, dict[str, Any]] = {}
    dependencies: dict[str, dict[str, Any]] = {}
    source_catalogs: list[dict[str, Any]] = []
    source_catalogs.append({
        "catalog_id": "certificates.tls",
        "schema_version": cert_catalog["schema_version"],
        "revision": cert_catalog["revision"],
        "sha256": hashlib.sha256(cert_catalog_raw).hexdigest(),
        "present": bool(cert_catalog_raw),
    })
    reasons: set[str] = set()
    included = sorted(requested_set & SUPPORTED_CATEGORIES)

    if connections_catalog_present:
        source_catalogs.append({
            "catalog_id": "connections.shared",
            "schema_version": None,
            "revision": None,
            "sha256": hashlib.sha256(connections_raw).hexdigest(),
            "present": True,
        })

    connection_catalog_member_id: str | None = None
    if "connections.vless" in included or "connections.vmess" in included:
        sanitized_entries: list[dict[str, Any]] = []
        selected_connections: dict[str, dict[str, Any]] = {}
        for entry in sorted(connection_entries, key=lambda item: item["id"]):
            protocol = protocols[entry["id"]]
            if protocol not in ("vless", "vmess") or f"connections.{protocol}" not in included:
                continue
            cid = entry["id"]
            config, config_path, secret_ref, revision = _load_protocol_config(protocol, entry, paths)
            sanitized_entry = copy.deepcopy(entry)
            sanitized_entry.pop("secret_ref", None)
            sanitized_entry.pop("vmess_secret_ref", None)
            config_member_id: str | None = None
            resource_id = f"{protocol}:connection:{cid}"
            resource_exclusions: list[str] = []
            resource_dependencies: list[str] = []
            if config is not None and config_path is not None:
                sanitized_config, secret_classes, config_dependencies = _sanitize_protocol_config(protocol, config, entry, secret_ref)
                for secret_class, reason in secret_classes:
                    resource_exclusions.append(_add_exclusion(exclusions, resource_id, secret_class, reason))
                    reasons.add("secret_excluded")
                for dep_type, dep_target, fingerprint in config_dependencies:
                    if dep_type == "tls_certificate":
                        dep_id = f"tls:{dep_target}"
                        cert_record = cert_records.get(dep_target)
                        fingerprint = cert_record["fingerprint_sha256"] if cert_record else None
                        cert_resource_id = f"certificate:{dep_target}"
                        if cert_resource_id not in resources:
                            resources[cert_resource_id] = _new_resource(cert_resource_id, "certificate", "tls", completeness="PARTIAL")
                        validation = "pending_restore_preflight" if "certificates.tls" in included else "not_included"
                        if cert_record is None:
                            validation = "missing_source_resource"
                        dependency_type = (
                            "tls_reference" if cert_record and cert_record["storage_type"] == "reference"
                            else "tls_certificate"
                        )
                        _add_dependency(
                            dependencies, dep_id, dependency_type, cert_resource_id,
                            fingerprint, validation, dependent_connection=entry["id"],
                        )
                        resource_dependencies.append(dep_id)
                        reasons.add("dependency_pending")
                    elif dep_type == "tls_legacy_reference":
                        dep_id = f"tls-legacy:{entry['id']}"
                        cert_resource_id = f"certificate:legacy:{entry['id']}"
                        resources.setdefault(cert_resource_id, _new_resource(cert_resource_id, "certificate_reference", "tls", completeness="PARTIAL"))
                        _add_dependency(dependencies, dep_id, dep_type, cert_resource_id, fingerprint, "pending_restore_preflight")
                        resource_dependencies.append(dep_id)
                        reasons.add("dependency_pending")
                # Factory re-reads, revalidates and re-sanitizes the source on ZIP emission.
                def open_sanitized_config(
                    protocol: str = protocol,
                    entry: dict[str, Any] = copy.deepcopy(entry),
                    config_path: Path = config_path,
                    paths: SnapshotPaths = paths,
                ) -> io.BytesIO:
                    fresh, _, fresh_secret, _ = _load_protocol_config(protocol, entry, paths)
                    if fresh is None:
                        raise SnapshotBlocked("configuración desapareció durante el snapshot")
                    clean, _, _ = _sanitize_protocol_config(protocol, fresh, entry, fresh_secret)
                    return io.BytesIO(canonical_json(clean))
                config_name = (
                    f"connections/{protocol}/{entry['configuration_ref'] if protocol == 'vless' else entry['vmess_configuration_ref']}"
                )
                config_member = package_zip.ZipMember.from_factory(config_name, open_sanitized_config, max_size=MAX_CONFIG_BYTES)
                config_member_id = _register_member(config_member, f"connections.{protocol}", members_by_hash, categories_by_hash)
            sanitized_entries.append(sanitized_entry)
            selected_connections[cid] = entry
            member_ids = [config_member_id] if config_member_id else []
            resources[resource_id] = _new_resource(
                resource_id, "connection", protocol, member_ids,
                resource_dependencies, resource_exclusions,
                "PARTIAL" if resource_exclusions or resource_dependencies else "COMPLETE",
            )
        _check_sensitive_keys(sanitized_entries, context="catálogo de conexiones")
        catalog_member = package_zip.ZipMember.from_bytes(
            "connections/catalog.json", canonical_json(sanitized_entries)
        )
        connection_catalog_member_id = _register_member(
            catalog_member, "connections.shared", members_by_hash, categories_by_hash
        )
        for resource in resources.values():
            if resource["resource_type"] == "connection":
                resource["member_ids"].append(connection_catalog_member_id)
                resource["member_ids"] = sorted(set(resource["member_ids"]))

    # Identities are globally represented, but every credential value is removed.
    if "identities" in included:
        if _path_exists(paths.users_catalog):
            users_value, users_raw = _read_json(paths.users_catalog, paths.users_root, MAX_JSON_BYTES)
            source_catalogs.append({
                "catalog_id": "identities",
                "schema_version": 2 if isinstance(users_value, dict) else None,
                "revision": None,
                "sha256": hashlib.sha256(users_raw).hexdigest(),
                "present": True,
            })
        else:
            raise SnapshotBlocked("catálogo de identidades ausente; no se asumirá una colección vacía")
        sanitized_users, identity_exclusions = _validate_identity_catalog(users_value, connections_by_id)
        identity_member = package_zip.ZipMember.from_bytes("users/identities.json", canonical_json(sanitized_users))
        identity_member_id = _register_member(identity_member, "identities", members_by_hash, categories_by_hash)
        identity_resource_id = "identities:global"
        identity_exclusion_ids: list[str] = []
        identity_dependency_ids: list[str] = []
        for assoc_id, secret_class, reason, connection_id, identity_id in identity_exclusions:
            association_resource_id = f"identity-association:{assoc_id}"
            exclusion_id = _add_exclusion(
                exclusions, association_resource_id, secret_class, reason,
                token=assoc_id, association_id=assoc_id,
                identity_id=identity_id, connection_id=connection_id,
            )
            identity_exclusion_ids.append(exclusion_id)
            if reason == "unsupported_protocol":
                reasons.add("unsupported_association_protocol")
            else:
                reasons.add("secret_excluded")
            connection_entry = connections_by_id[connection_id]
            protocol = _catalog_entry_protocol(connection_entry)
            connection_resource_id = f"{protocol}:connection:{connection_id}" if protocol else f"connection:{connection_id}"
            dependency_id = f"connection:{connection_id}"
            included_connection = connection_resource_id in resources and resources[connection_resource_id]["resource_type"] == "connection"
            if connection_resource_id not in resources:
                resources[connection_resource_id] = _new_resource(connection_resource_id, "connection_reference", protocol, completeness="PARTIAL")
            _add_dependency(
                dependencies, dependency_id, "connection_reference", connection_resource_id,
                None, "included" if included_connection else "pending_restore_preflight",
            )
            identity_dependency_ids.append(dependency_id)
            resources[association_resource_id] = _new_resource(
                association_resource_id, "identity_association", protocol,
                [identity_member_id], [dependency_id], [exclusion_id], "PARTIAL",
            )
            if not included_connection:
                reasons.add("dependency_pending")
        resources[identity_resource_id] = _new_resource(
            identity_resource_id, "identity_catalog", "global", [identity_member_id],
            identity_dependency_ids, identity_exclusion_ids,
            "PARTIAL" if identity_exclusion_ids or identity_dependency_ids else "COMPLETE",
        )

    # Load the central TLS catalog without opening/decrypting any private-key blob.
    cert_catalog_member_id: str | None = None
    if "certificates.tls" in included:
        sanitized_certificates: list[dict[str, Any]] = []
        for item in cert_catalog["certificates"]:
            cid = item["certificate_id"]
            resource_id = f"certificate:{cid}"
            sanitized = copy.deepcopy(item)
            sanitized.pop("secret_ref", None)
            if item["storage_type"] == "reference":
                sanitized["certificate_source"] = None
            else:
                cert_path = paths.certificates_managed / f"{cid}.pem"
                try:
                    cert_bytes = package_zip.read_root_regular(
                        cert_path, paths.certificates_managed, limit=MAX_CERTIFICATE_BYTES
                    )
                except package_zip.SharedBackupZipError as exc:
                    raise SnapshotBlocked("certificado público managed ausente o inseguro") from exc
                metadata = _certificate_public_metadata(cert_bytes)
                for field in ("fingerprint_sha256", "public_key_fingerprint_sha256", "subject", "issuer", "sans", "not_before", "not_after"):
                    if metadata[field] != item[field]:
                        raise SnapshotBlocked("metadatos del certificado público no coinciden con el catálogo")
                cert_member = package_zip.ZipMember.from_path(
                    f"certificates/managed/{cid}.pem", cert_path,
                    allowed_root=paths.certificates_managed,
                )
                cert_member_id = _register_member(cert_member, "certificates.tls", members_by_hash, categories_by_hash)
                resources[resource_id] = _new_resource(resource_id, "certificate", "tls", [cert_member_id], completeness="PARTIAL")
            exclusion_id = _add_exclusion(exclusions, resource_id, "tls_private_key", "excluded_by_default")
            if resource_id not in resources:
                resources[resource_id] = _new_resource(resource_id, "certificate", "tls", completeness="PARTIAL")
            resources[resource_id]["exclusion_ids"].append(exclusion_id)
            resources[resource_id]["exclusion_ids"] = sorted(set(resources[resource_id]["exclusion_ids"]))
            sanitized_certificates.append(sanitized)
            reasons.add("secret_excluded")
            if item["storage_type"] == "reference":
                dep_id = f"tls:{cid}"
                _add_dependency(dependencies, dep_id, "tls_reference", resource_id, item["fingerprint_sha256"], "pending_restore_preflight")
                resources[resource_id]["dependency_ids"].append(dep_id)
                resources[resource_id]["dependency_ids"] = sorted(set(resources[resource_id]["dependency_ids"]))
                reasons.add("dependency_pending")
        cert_snapshot = {
            "schema_version": cert_catalog["schema_version"],
            "revision": cert_catalog["revision"],
            "certificates": sanitized_certificates,
        }
        cert_member = package_zip.ZipMember.from_bytes("certificates/catalog.json", canonical_json(cert_snapshot))
        cert_catalog_member_id = _register_member(cert_member, "certificates.tls", members_by_hash, categories_by_hash)
        for resource in resources.values():
            if resource["resource_type"] == "certificate":
                resource["member_ids"].append(cert_catalog_member_id)
                resource["member_ids"] = sorted(set(resource["member_ids"]))

    # Resolve central TLS dependencies discovered while processing connection configs.
    for dependency in list(dependencies.values()):
        if dependency["dependency_type"] not in ("tls_certificate", "tls_reference"):
            continue
        cert_id = dependency["dependency_id"].removeprefix("tls:")
        record = cert_records.get(cert_id)
        resource_id = dependency["resource_id"]
        if record is not None and "certificates.tls" not in included:
            if resource_id not in resources:
                resources[resource_id] = _new_resource(resource_id, "certificate_reference", "tls", completeness="PARTIAL")
            dependency["validation"] = "not_included"
            reasons.add("dependency_pending")
        elif record is None:
            if resource_id not in resources:
                resources[resource_id] = _new_resource(resource_id, "certificate_reference", "tls", completeness="PARTIAL")
            dependency["validation"] = "missing_source_resource"
            reasons.add("dependency_pending")
        elif record["storage_type"] == "managed":
            # La clave privada se excluye aunque el certificado público se incluya.
            dependency["validation"] = "pending_restore_preflight"
            reasons.add("dependency_pending")
        else:
            dependency["validation"] = "pending_restore_preflight"
            reasons.add("dependency_pending")

    external_member = _external_dependencies_member(dependencies, cert_records)
    _register_member(external_member, "dependencies", members_by_hash, categories_by_hash)

    # Include unsupported request categories explicitly; never silently omit them.
    if unsupported:
        reasons.add("unsupported_category")

    # Add data members in stable logical-path order; same bytes share one content ID.
    unique_members = sorted(members_by_hash.values(), key=lambda member: member.name)
    member_records = [
        _member_record(member, categories_by_hash[member.sha256])
        for member in unique_members
    ]
    index_records = [
        {
            "member_id": "sha256:" + member.sha256,
            "logical_path": member.name,
            "size_bytes": member.size,
            "sha256": member.sha256,
            "crc32": member.crc32,
        }
        for member in unique_members
    ]
    index_bytes = canonical_json({
        "index_format": "xray-manager-shared-snapshot-index",
        "index_version": 1,
        "members": index_records,
    })
    manifest_resources = sorted(resources.values(), key=lambda item: item["resource_id"])
    for resource in manifest_resources:
        resource["member_ids"] = sorted(set(resource["member_ids"]))
        resource["dependency_ids"] = sorted(set(resource["dependency_ids"]))
        resource["exclusion_ids"] = sorted(set(resource["exclusion_ids"]))
        unresolved_dependencies = any(
            dependencies[dependency_id]["validation"] != "included"
            for dependency_id in resource["dependency_ids"]
        )
        if resource["exclusion_ids"] or unresolved_dependencies:
            resource["completeness"] = "PARTIAL"
    complete_count = sum(1 for item in manifest_resources if item["completeness"] == "COMPLETE")
    partial_count = len(manifest_resources) - complete_count
    overall = "PARTIAL" if partial_count or unsupported else "COMPLETE"
    manifest = {
        "manifest_format": "xray-manager-shared-snapshot",
        "manifest_version": 1,
        "backup_id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source": {"manager_version": None, "xray_version": None},
        "request": {
            "selection_mode": selection_mode,
            "requested_categories": requested,
        },
        "categories": {
            "included": included,
            "unsupported": sorted(unsupported),
        },
        "resources": manifest_resources,
        "members": member_records,
        "exclusions": sorted(exclusions.values(), key=lambda item: item["exclusion_id"]),
        "dependencies": sorted(dependencies.values(), key=lambda item: item["dependency_id"]),
        "source_snapshot": {"catalogs": sorted(source_catalogs, key=lambda item: item["catalog_id"])},
        "completeness": {
            "status": overall,
            "reasons": sorted(reasons),
            "complete_resources": complete_count,
            "partial_resources": partial_count,
        },
    }
    _validate_manifest_contract(manifest)
    manifest_bytes = canonical_json(manifest)
    data_members = [
        package_zip.ZipMember.from_bytes("manifest.json", manifest_bytes),
        package_zip.ZipMember.from_bytes("index.json", index_bytes),
        *unique_members,
    ]
    return data_members, manifest


def _validate_manifest_contract(manifest: dict[str, Any]) -> None:
    required_top_level = {
        "manifest_format", "manifest_version", "backup_id", "created_at", "source",
        "request", "categories", "resources", "members", "exclusions", "dependencies",
        "source_snapshot", "completeness",
    }
    if not isinstance(manifest, dict) or set(manifest) != required_top_level:
        raise SnapshotBlocked("estructura raíz del manifiesto inválida")
    if manifest["manifest_format"] != "xray-manager-shared-snapshot":
        raise SnapshotBlocked("formato de manifiesto desconocido")
    if type(manifest["manifest_version"]) is not int or manifest["manifest_version"] != 1:
        raise SnapshotBlocked("sólo se admite manifest_version 1")
    backup_id = manifest["backup_id"]
    try:
        parsed_backup_id = uuid.UUID(backup_id)
    except (ValueError, TypeError, AttributeError) as exc:
        raise SnapshotBlocked("backup_id no es UUID válido") from exc
    if str(parsed_backup_id) != backup_id or parsed_backup_id.version != 4 or parsed_backup_id.variant != uuid.RFC_4122:
        raise SnapshotBlocked("backup_id debe ser UUID v4 canónico")
    created_at = manifest["created_at"]
    if not isinstance(created_at, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z", created_at):
        raise SnapshotBlocked("created_at debe ser timestamp UTC RFC 3339 terminado en Z")
    try:
        parsed_created_at = datetime.fromisoformat(created_at[:-1] + "+00:00")
    except ValueError as exc:
        raise SnapshotBlocked("created_at contiene una fecha/hora inválida") from exc
    if parsed_created_at.utcoffset() != timezone.utc.utcoffset(parsed_created_at):
        raise SnapshotBlocked("created_at no está expresado en UTC")

    source = manifest["source"]
    if not isinstance(source, dict) or set(source) != {"manager_version", "xray_version"} or any(
        value is not None and not isinstance(value, str) for value in source.values()
    ):
        raise SnapshotBlocked("metadatos source inválidos")
    request = manifest["request"]
    if not isinstance(request, dict) or set(request) != {"selection_mode", "requested_categories"}:
        raise SnapshotBlocked("request del manifiesto inválido")
    if request["selection_mode"] not in ("selective", "all_available"):
        raise SnapshotBlocked("selection_mode del manifiesto inválido")
    requested_categories = request["requested_categories"]
    if (
        not isinstance(requested_categories, list) or not requested_categories
        or any(not isinstance(item, str) or not item or item.strip() != item for item in requested_categories)
        or len(set(requested_categories)) != len(requested_categories)
    ):
        raise SnapshotBlocked("requested_categories debe ser una lista no vacía y sin duplicados")

    categories = manifest["categories"]
    if not isinstance(categories, dict) or set(categories) != {"included", "unsupported"}:
        raise SnapshotBlocked("categories del manifiesto inválido")
    for field in ("included", "unsupported"):
        values = categories[field]
        if (
            not isinstance(values, list)
            or any(not isinstance(item, str) or not item or item.strip() != item for item in values)
            or len(set(values)) != len(values)
        ):
            raise SnapshotBlocked(f"categories.{field} inválido o duplicado")

    for field in ("resources", "members", "exclusions", "dependencies"):
        if not isinstance(manifest[field], list):
            raise SnapshotBlocked(f"{field} debe ser una lista")

    resource_fields = {"resource_id", "resource_type", "protocol", "completeness", "member_ids", "dependency_ids", "exclusion_ids"}
    for item in manifest["resources"]:
        if (
            not isinstance(item, dict) or set(item) != resource_fields
            or not isinstance(item.get("resource_id"), str) or not item["resource_id"]
            or not isinstance(item.get("resource_type"), str) or not item["resource_type"]
            or (item.get("protocol") is not None and not isinstance(item["protocol"], str))
            or item.get("completeness") not in ("COMPLETE", "PARTIAL")
        ):
            raise SnapshotBlocked("objeto resource incompleto o inválido")
        for field in ("member_ids", "dependency_ids", "exclusion_ids"):
            values = item[field]
            if not isinstance(values, list) or any(not isinstance(v, str) or not v for v in values) or len(values) != len(set(values)):
                raise SnapshotBlocked(f"{field} de recurso inválidos o duplicados")

    member_fields = {"member_id", "logical_path", "category", "media_type", "size_bytes", "sha256"}
    for item in manifest["members"]:
        if (
            not isinstance(item, dict) or set(item) != member_fields
            or any(not isinstance(item.get(field), str) or not item[field] for field in (
                "member_id", "logical_path", "category", "media_type", "sha256"
            ))
            or type(item.get("size_bytes")) is not int or item["size_bytes"] < 0
        ):
            raise SnapshotBlocked("objeto member incompleto o inválido")

    exclusion_required = {"exclusion_id", "resource_id", "secret_class", "reason"}
    exclusion_allowed = exclusion_required | {"association_id", "identity_id", "connection_id"}
    for item in manifest["exclusions"]:
        if (
            not isinstance(item, dict) or not exclusion_required.issubset(item)
            or not set(item).issubset(exclusion_allowed)
            or any(not isinstance(item.get(field), str) or not item[field] for field in exclusion_required)
        ):
            raise SnapshotBlocked("objeto exclusion incompleto o inválido")

    dependency_fields = {"dependency_id", "dependency_type", "resource_id", "fingerprint_sha256", "required", "validation", "dependent_connections"}
    for item in manifest["dependencies"]:
        if (
            not isinstance(item, dict) or set(item) != dependency_fields
            or any(not isinstance(item.get(field), str) or not item[field] for field in (
                "dependency_id", "dependency_type", "resource_id", "validation"
            ))
            or (item.get("fingerprint_sha256") is not None and not isinstance(item["fingerprint_sha256"], str))
            or item.get("required") is not True
            or not isinstance(item.get("dependent_connections"), list)
            or any(not isinstance(cid, str) or not cid for cid in item["dependent_connections"])
            or len(item["dependent_connections"]) != len(set(item["dependent_connections"]))
        ):
            raise SnapshotBlocked("objeto dependency incompleto o inválido")

    source_snapshot = manifest["source_snapshot"]
    if not isinstance(source_snapshot, dict) or set(source_snapshot) != {"catalogs"} or not isinstance(source_snapshot["catalogs"], list):
        raise SnapshotBlocked("source_snapshot inválido")
    completeness = manifest["completeness"]
    if not isinstance(completeness, dict) or set(completeness) != {"status", "reasons", "complete_resources", "partial_resources"}:
        raise SnapshotBlocked("completeness del manifiesto inválido")
    if completeness["status"] not in ("COMPLETE", "PARTIAL"):
        raise SnapshotBlocked("estado global de completitud inválido")
    if (
        not isinstance(completeness["reasons"], list)
        or any(not isinstance(item, str) or not item for item in completeness["reasons"])
        or len(set(completeness["reasons"])) != len(completeness["reasons"])
    ):
        raise SnapshotBlocked("razones de completitud inválidas")
    for field in ("complete_resources", "partial_resources"):
        if type(completeness[field]) is not int or completeness[field] < 0:
            raise SnapshotBlocked("contadores de completitud inválidos")

    resources, members = manifest["resources"], manifest["members"]
    exclusions, dependencies = manifest["exclusions"], manifest["dependencies"]
    resource_map = {item["resource_id"]: item for item in resources}
    member_map = {item["member_id"]: item for item in members}
    exclusion_map = {item["exclusion_id"]: item for item in exclusions}
    dependency_map = {item["dependency_id"]: item for item in dependencies}
    if len(resource_map) != len(resources) or len(member_map) != len(members):
        raise SnapshotBlocked("IDs duplicados en recursos/miembros del manifiesto")
    if len(exclusion_map) != len(exclusions) or len(dependency_map) != len(dependencies):
        raise SnapshotBlocked("IDs duplicados en exclusiones/dependencias del manifiesto")

    logical_paths: set[str] = set()
    for member in members:
        digest = member["sha256"]
        if not re.fullmatch(r"[0-9a-f]{64}", digest) or member["member_id"] != "sha256:" + digest:
            raise SnapshotBlocked("SHA-256/member_id de miembro inválido")
        if not re.fullmatch(r"[A-Za-z0-9_.:-]+", member["category"]):
            raise SnapshotBlocked("categoría de miembro inválida")
        if member["media_type"] not in ("application/json", "application/x-pem-file"):
            raise SnapshotBlocked("media_type de miembro no admitido")
        try:
            package_zip.validate_logical_path(member["logical_path"])
        except package_zip.SharedBackupZipError as exc:
            raise SnapshotBlocked("logical_path de miembro inválido") from exc
        if member["logical_path"] in logical_paths:
            raise SnapshotBlocked("logical_path duplicado en manifiesto")
        logical_paths.add(member["logical_path"])
    if "external-dependencies.json" not in logical_paths:
        raise SnapshotBlocked("falta external-dependencies.json dentro del paquete protegido")

    for resource in resources:
        for field, lookup in (("member_ids", member_map), ("dependency_ids", dependency_map), ("exclusion_ids", exclusion_map)):
            if any(value not in lookup for value in resource[field]):
                raise SnapshotBlocked(f"{field} referencia objeto inexistente")
        if resource["completeness"] == "COMPLETE" and (
            resource["exclusion_ids"] or any(dependency_map[item]["validation"] != "included" for item in resource["dependency_ids"])
        ):
            raise SnapshotBlocked("recurso con exclusiones/dependencias pendientes no puede ser COMPLETE")

    for exclusion in exclusions:
        if exclusion["resource_id"] not in resource_map:
            raise SnapshotBlocked("exclusión referencia recurso inexistente")
        for field, pattern in (("association_id", UUID_RE), ("identity_id", UUID_RE), ("connection_id", ID_RE)):
            if field in exclusion and (not isinstance(exclusion[field], str) or not pattern.fullmatch(exclusion[field])):
                raise SnapshotBlocked(f"exclusión referencia {field} inválido")

    for dependency in dependencies:
        if dependency["resource_id"] not in resource_map:
            raise SnapshotBlocked("dependencia referencia recurso inexistente")
        if dependency["dependency_type"] not in ("connection_reference", "tls_certificate", "tls_reference", "tls_legacy_reference"):
            raise SnapshotBlocked("tipo de dependencia no admitido")
        if dependency["validation"] not in ("included", "pending_restore_preflight", "not_included", "missing_source_resource"):
            raise SnapshotBlocked("estado de validación de dependencia inválido")
        fingerprint = dependency["fingerprint_sha256"]
        if fingerprint is not None and not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
            raise SnapshotBlocked("fingerprint de dependencia inválido")
        if any(not ID_RE.fullmatch(cid) for cid in dependency["dependent_connections"]):
            raise SnapshotBlocked("conexión dependiente inválida")
        if dependency["dependency_type"] == "tls_reference" and fingerprint is None:
            raise SnapshotBlocked("dependencia TLS reference sin fingerprint")

    requested, included, unsupported = set(requested_categories), set(categories["included"]), set(categories["unsupported"])
    if included & unsupported or included | unsupported != requested:
        raise SnapshotBlocked("included/unsupported deben resolver exactamente las categorías solicitadas")
    if included - SUPPORTED_CATEGORIES or unsupported & SUPPORTED_CATEGORIES:
        raise SnapshotBlocked("categorías incluidas/no soportadas no coinciden con el catálogo de soporte v1")
    if completeness["status"] == "COMPLETE" and (unsupported or exclusions or any(
        dependency["validation"] != "included" for dependency in dependencies
    )):
        raise SnapshotBlocked("COMPLETE no admite categorías omitidas, exclusiones ni dependencias pendientes")
    complete_count = sum(item["completeness"] == "COMPLETE" for item in resources)
    partial_count = len(resources) - complete_count
    if completeness["complete_resources"] != complete_count or completeness["partial_resources"] != partial_count:
        raise SnapshotBlocked("contadores de completitud incoherentes")
    expected = "PARTIAL" if partial_count or unsupported else "COMPLETE"
    if completeness["status"] != expected:
        raise SnapshotBlocked("estado global de completitud incoherente")

    catalog_fields = {"catalog_id", "schema_version", "revision", "sha256", "present"}
    catalog_ids: set[str] = set()
    for catalog in source_snapshot["catalogs"]:
        if (
            not isinstance(catalog, dict) or set(catalog) != catalog_fields
            or not isinstance(catalog.get("catalog_id"), str) or not catalog["catalog_id"]
            or not isinstance(catalog.get("present"), bool)
            or not isinstance(catalog.get("sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", catalog["sha256"])
        ):
            raise SnapshotBlocked("metadatos incompletos o inválidos de source_snapshot")
        if catalog["catalog_id"] in catalog_ids:
            raise SnapshotBlocked("catálogo duplicado en source_snapshot")
        catalog_ids.add(catalog["catalog_id"])
        for field in ("schema_version", "revision"):
            value = catalog[field]
            if value is not None and (type(value) is not int or value < 0):
                raise SnapshotBlocked("schema/revision inválida en source_snapshot")

    _check_sensitive_keys(manifest, context="manifiesto")
    def reject_absolute(value: Any) -> None:
        if isinstance(value, str) and value.startswith("/"):
            raise SnapshotBlocked("ruta absoluta no permitida en manifiesto")
        if isinstance(value, dict):
            for item in value.values():
                reject_absolute(item)
        elif isinstance(value, list):
            for item in value:
                reject_absolute(item)
    reject_absolute(manifest)



def _acquire_coordination_lock(parent: Path, timeout: float) -> int:
    lock_path = parent / ".xrm-coordination.lock"
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    created = False
    try:
        # O_EXCL garantiza que el inode recién creado no sea un hardlink previo.
        fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_EXCL | nofollow, 0o600)
        created = True
    except FileExistsError:
        # No modificar metadatos de un archivo preexistente hasta demostrar que
        # es el lock regular esperado, root:root 0600 y con un único hardlink.
        try:
            before = lock_path.lstat()
        except OSError as exc:
            raise SnapshotBlocked("bloqueo de coordinación ausente o inaccesible") from exc
        if (
            not stat.S_ISREG(before.st_mode) or stat.S_ISLNK(before.st_mode)
            or before.st_uid != 0 or before.st_gid != 0
            or stat.S_IMODE(before.st_mode) != 0o600 or before.st_nlink != 1
        ):
            raise SnapshotBlocked("bloqueo de coordinación inseguro")
        try:
            fd = os.open(lock_path, os.O_RDWR | nofollow)
        except OSError as exc:
            raise SnapshotBlocked("no se pudo abrir el bloqueo de coordinación sin seguir enlaces") from exc
        opened = os.fstat(fd)
        if (
            opened.st_dev != before.st_dev or opened.st_ino != before.st_ino
            or not stat.S_ISREG(opened.st_mode) or opened.st_uid != 0 or opened.st_gid != 0
            or stat.S_IMODE(opened.st_mode) != 0o600 or opened.st_nlink != 1
        ):
            os.close(fd)
            raise SnapshotBlocked("bloqueo de coordinación cambió durante su apertura")
    try:
        if created:
            os.fchown(fd, 0, 0)
            os.fchmod(fd, 0o600)
        st = os.fstat(fd)
        if (
            not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_gid != 0
            or stat.S_IMODE(st.st_mode) != 0o600 or st.st_nlink != 1
        ):
            raise SnapshotBlocked("bloqueo de coordinación inseguro")
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return fd
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise SnapshotBlocked("timeout del bloqueo de coordinación")
                time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
    except Exception:
        os.close(fd)
        raise


def _validate_staging_directory(path: Path) -> None:
    st = path.lstat()
    if (
        not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode)
        or st.st_uid != 0 or st.st_gid != 0 or stat.S_IMODE(st.st_mode) != 0o700
    ):
        raise SnapshotBlocked("directorio temporal con tipo, propietario o permisos inseguros")


def _validate_staging_file(path: Path) -> None:
    st = path.lstat()
    if (
        not stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode)
        or st.st_uid != 0 or st.st_gid != 0 or stat.S_IMODE(st.st_mode) != 0o600
        or st.st_nlink != 1
    ):
        raise SnapshotBlocked("archivo temporal con tipo, propietario o permisos inseguros")


def _recover_orphan_staging(parent: Path) -> int:
    recovered = 0
    for entry in os.scandir(parent):
        if not entry.name.startswith(".xrm-snapshot-"):
            continue
        path = Path(entry.path)
        _validate_staging_directory(path)
        owner_path = path / "owner.lock"
        package_path = path / "package.tmp"
        names = {child.name for child in os.scandir(path)}
        if not names:
            path.rmdir()
            recovered += 1
            continue
        if "owner.lock" not in names or names - {"owner.lock", "package.tmp"}:
            raise SnapshotBlocked("temporal abandonado con estructura inesperada; se conserva")
        _validate_staging_file(owner_path)
        owner_fd = os.open(owner_path, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
        try:
            _validate_staging_file(owner_path)
            try:
                fcntl.flock(owner_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                continue
            if "package.tmp" in names:
                _validate_staging_file(package_path)
                package_path.unlink()
            owner_path.unlink()
            path.rmdir()
            recovered += 1
        finally:
            os.close(owner_fd)
    return recovered


def _prepare_snapshot_staging(parent: Path, timeout: float) -> tuple[Path, int]:
    coordination_fd = _acquire_coordination_lock(parent, timeout)
    staging_dir: Path | None = None
    owner_fd: int | None = None
    try:
        _recover_orphan_staging(parent)
        staging_dir = Path(tempfile.mkdtemp(prefix=".xrm-snapshot-", dir=parent))
        os.chown(staging_dir, 0, 0)
        os.chmod(staging_dir, 0o700)
        owner_path = staging_dir / "owner.lock"
        owner_fd = os.open(
            owner_path,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        os.fchown(owner_fd, 0, 0)
        os.fchmod(owner_fd, 0o600)
        _validate_staging_file(owner_path)
        fcntl.flock(owner_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = (staging_dir, owner_fd)
        staging_dir = None
        owner_fd = None
        return result
    finally:
        cleanup_errors: list[OSError] = []
        if owner_fd is not None:
            try:
                os.close(owner_fd)
            except OSError as exc:
                cleanup_errors.append(exc)
        if staging_dir is not None:
            try:
                shutil.rmtree(staging_dir)
            except OSError as exc:
                cleanup_errors.append(exc)
        try:
            os.close(coordination_fd)
        except OSError as exc:
            cleanup_errors.append(exc)
        if cleanup_errors:
            raise SnapshotError(
                "falló la limpieza/cierre de staging durante la preparación; "
                "el temporal se conserva para recuperación segura"
            ) from cleanup_errors[0]



def _cleanup_snapshot_staging(
    parent: Path, staging_dir: Path, staging_file: Path | None,
    owner_fd: int, timeout: float,
) -> None:
    """Limpia staging bajo coordinación y siempre consume/cierra owner_fd."""
    coordination_fd: int | None = None
    owner_closed = False
    try:
        coordination_fd = _acquire_coordination_lock(parent, timeout)
        if staging_file is not None:
            staging_file.unlink(missing_ok=True)
        os.close(owner_fd)
        owner_closed = True
        (staging_dir / "owner.lock").unlink(missing_ok=True)
        staging_dir.rmdir()
        parent_fd = os.open(
            parent,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
        )
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    finally:
        close_errors: list[OSError] = []
        if not owner_closed:
            try:
                os.close(owner_fd)
            except OSError as exc:
                close_errors.append(exc)
        if coordination_fd is not None:
            try:
                os.close(coordination_fd)
            except OSError as exc:
                close_errors.append(exc)
        if close_errors:
            raise close_errors[0]


def create_snapshot(
    destination: Path,
    passphrase: str | None,
    *,
    paths: SnapshotPaths = DEFAULT_PATHS,
    selection_mode: str = "all_available",
    requested_categories: list[str] | None = None,
    lock_timeout: float = 30.0,
) -> dict[str, Any]:
    if os.geteuid() != 0:
        raise SnapshotBlocked("la creación de snapshot requiere root")
    if selection_mode not in ("selective", "all_available"):
        raise SnapshotBlocked("selection_mode inválido")
    if selection_mode == "selective" and requested_categories is None:
        raise SnapshotBlocked("selection_mode selective requiere categorías explícitas")
    if selection_mode == "all_available" and requested_categories is not None:
        raise SnapshotBlocked("selection_mode all_available no admite una lista selectiva de categorías")
    raw_requested = requested_categories if requested_categories is not None else DEFAULT_CATEGORIES
    if not isinstance(raw_requested, list) or not raw_requested or any(
        not isinstance(item, str) or not item or len(item) > 128 or item.strip() != item
        for item in raw_requested
    ):
        raise SnapshotBlocked("categorías solicitadas inválidas")
    if len(set(raw_requested)) != len(raw_requested):
        raise SnapshotBlocked("categorías solicitadas duplicadas")
    requested = sorted(raw_requested)
    if (
        isinstance(lock_timeout, bool)
        or not isinstance(lock_timeout, (int, float))
        or not math.isfinite(lock_timeout)
        or lock_timeout < 0
    ):
        raise SnapshotBlocked("timeout de locks inválido")

    destination = Path(destination).absolute()
    if not destination.name or destination.name in (".", "..") or "/" in destination.name or "\x00" in destination.name:
        raise SnapshotBlocked("nombre de destino inválido")
    _validate_destination_parent(destination.parent)
    if _path_exists(destination):
        raise SnapshotBlocked("el destino ya existe; no se sobrescribe")

    staging_dir: Path | None = None
    staging_file: Path | None = None
    owner_fd: int | None = None
    published = False
    try:
        # La contraseña se valida antes de crear temporales. La coordinación
        # serializa recuperación y creación; owner.lock protege cada proceso activo.
        if passphrase is None:
            password = getpass.getpass("Contraseña del backup compartido: ")
            confirmation = getpass.getpass("Confirma la contraseña: ")
            if password != confirmation:
                raise SnapshotBlocked("las contraseñas no coinciden")
            passphrase = password
        try:
            crypto.validate_passphrase(passphrase)
        except crypto.SharedBackupFormatError as exc:
            raise SnapshotBlocked("contraseña no cumple la política criptográfica v1") from exc

        staging_dir, owner_fd = _prepare_snapshot_staging(destination.parent, lock_timeout)
        staging_file = staging_dir / "package.tmp"

        with acquire_snapshot_locks(paths, lock_timeout):
            try:
                members, manifest = _build_snapshot_members(paths, requested, selection_mode)
                zip_source = package_zip.ZipStream(members)
            except package_zip.SharedBackupZipError as exc:
                raise SnapshotBlocked("origen o estructura ZIP no cumple el contrato v1") from exc
            fd = os.open(
                staging_file,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
            os.fchown(fd, 0, 0)
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb") as output:
                try:
                    written = crypto.encrypt_payload_stream(
                        zip_source, output, zip_source.size, passphrase
                    )
                except package_zip.SharedBackupZipError as exc:
                    raise SnapshotBlocked("un miembro de origen cambió o incumple la validación ZIP") from exc
                except crypto.SharedBackupFormatError as exc:
                    raise SnapshotBlocked("flujo ZIP excede límites o no cumple el formato cifrado v1") from exc
                output.flush()
                os.fsync(output.fileno())
            if written > crypto.MAX_PACKAGE_BYTES:
                raise SnapshotBlocked("paquete cifrado excede el límite v1")
        # El artefacto cifrado inmutable se verifica después de liberar locks.
        st = staging_file.lstat()
        if (
            not stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode)
            or st.st_uid != 0 or st.st_gid != 0 or stat.S_IMODE(st.st_mode) != 0o600
            or st.st_nlink != 1 or st.st_size != written
        ):
            raise SnapshotError("artefacto cifrado de staging no cumple permisos/tamaño")
        with staging_file.open("rb") as package_stream:
            try:
                crypto.verify_package_stream(package_stream, passphrase)
            except crypto.SharedBackupFormatError as exc:
                raise SnapshotBlocked("el contenedor cifrado no superó la verificación v1") from exc
        # La creación exclusiva del hard-link es el punto de commit atómico.
        os.link(staging_file, destination, follow_symlinks=False)
        published = True
        parent_fd = os.open(destination.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
        staging_file.unlink()
        staging_file = None
        return {
            "status": "CREATED_COMPLETE" if manifest["completeness"]["status"] == "COMPLETE" else "CREATED_PARTIAL",
            "backup_id": manifest["backup_id"],
            "path": str(destination),
            "package_size_bytes": written,
            "resources": len(manifest["resources"]),
            "members": len(manifest["members"]),
            "exclusions": len(manifest["exclusions"]),
            "dependencies": len(manifest["dependencies"]),
            "completeness": manifest["completeness"]["status"],
        }
    except SnapshotError:
        raise
    except FileExistsError as exc:
        raise SnapshotBlocked("el destino apareció durante la publicación; no se sobrescribió") from exc
    except Exception as exc:
        if published:
            raise SnapshotError("el paquete fue publicado, pero falló una operación posterior de sincronización/limpieza") from exc
        raise SnapshotError("fallo operativo durante creación del snapshot; no se publicó paquete") from exc
    finally:
        if staging_dir is not None and owner_fd is not None:
            cleanup_fd = owner_fd
            owner_fd = None
            try:
                _cleanup_snapshot_staging(
                    destination.parent, staging_dir, staging_file, cleanup_fd, lock_timeout
                )
            except Exception as cleanup_exc:
                publication_state = "el paquete fue publicado" if published else "no se publicó paquete"
                raise SnapshotError(
                    f"{publication_state}, pero falló la limpieza del staging; "
                    "el residuo se conserva privado para recuperación segura"
                ) from cleanup_exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Crear snapshot compartido cifrado Xray Manager v1")
    parser.add_argument("--destination", required=True, help="archivo de salida dentro de directorio root:root 0700")
    parser.add_argument("--selection-mode", choices=("selective", "all_available"), default="all_available")
    parser.add_argument("--category", action="append", dest="categories", help="categoría a incluir; repetible")
    parser.add_argument("--lock-timeout", type=float, default=30.0)
    args = parser.parse_args()
    if args.selection_mode == "selective" and not args.categories:
        parser.error("--selection-mode selective requiere al menos un --category explícito")
    if args.selection_mode == "all_available" and args.categories:
        parser.error("--category sólo se admite con --selection-mode selective")
    try:
        result = create_snapshot(
            Path(args.destination), None,
            selection_mode=args.selection_mode,
            requested_categories=args.categories if args.selection_mode == "selective" else None,
            lock_timeout=args.lock_timeout,
        )
    except SnapshotBlocked as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2
    except SnapshotError as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())