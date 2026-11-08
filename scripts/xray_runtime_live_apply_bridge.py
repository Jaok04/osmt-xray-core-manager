#!/usr/bin/env python3
"""Puente del menú: staging live → publicación → primer start correlacionado.

La llamada requiere confirmación explícita (--confirm-live en CLI) y sólo
admite el primer start desde xray.service inactive. No realiza restart/stop ni
declara que Xray haya cargado criptográficamente los bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shutil
import stat
import sys
from pathlib import Path
from typing import Any

import certificate_resolver
import vless_client_export
import xray_runtime_live_backend as live_backend
import xray_runtime_live_journal as live_journal
import xray_runtime_live_operation_evidence as live_evidence
import xray_runtime_live_publisher as live_publisher
import xray_runtime_live_staging as live_staging
import xray_runtime_live_start_coordinator as start_coordinator
import xray_runtime_process_attestation as process_attestation
import xray_runtime_systemd_adapter as systemd_adapter


TARGET_DOMAIN = "pruebas.tvrc.me"
TARGET_PORT = 443


class LiveApplyBridgeError(Exception):
    pass


def _fail(message: str) -> None:
    raise LiveApplyBridgeError(message)


def _runtime_config_hash() -> str:
    data = live_publisher._read_optional_config()
    if data is None:
        _fail("La configuración publicada desapareció antes de start.")
    return hashlib.sha256(data).hexdigest()


def _validate_first_server_profile(staging_dir: Path, profile_id: str, revision: str) -> dict[str, Any]:
    """Valida el endpoint externo concreto antes de publicar la configuración."""
    manifest, config_bytes = live_publisher._read_stage(staging_dir)
    if manifest.get("profile_id") != profile_id or manifest.get("revision") != revision:
        _fail("El staging no corresponde al perfil/revisión seleccionados.")
    try:
        config = live_staging.staging_fixture._strict_json(config_bytes, "La configuración live staged")
    except Exception as exc:
        raise LiveApplyBridgeError("La configuración staged no es JSON estricto.") from exc
    inbounds = config.get("inbounds") if isinstance(config, dict) else None
    bindings = manifest.get("bindings")
    if not isinstance(inbounds, list) or not isinstance(bindings, list) or len(bindings) != 1:
        _fail("El primer servidor requiere exactamente un mapping TLS y una lista de inbounds válida.")
    binding = bindings[0]
    if (not isinstance(binding, dict) or set(binding) != {"inbound_tag", "connection_id"}
            or not isinstance(binding.get("inbound_tag"), str)
            or not isinstance(binding.get("connection_id"), str)):
        _fail("El mapping del primer servidor es inválido.")
    public_port = [item for item in inbounds if isinstance(item, dict) and item.get("port") == TARGET_PORT]
    if len(public_port) != 1:
        _fail("El perfil debe contener exactamente un inbound en TCP/443.")
    inbound = public_port[0]
    tag = binding["inbound_tag"]
    if (inbound.get("tag") != tag or inbound.get("listen") != "0.0.0.0"
            or inbound.get("protocol") != "vless"):
        _fail("El inbound de 443 debe ser VLESS y escuchar públicamente en 0.0.0.0.")
    stream = inbound.get("streamSettings")
    ws = stream.get("wsSettings") if isinstance(stream, dict) else None
    tls = stream.get("tlsSettings") if isinstance(stream, dict) else None
    certificates = tls.get("certificates") if isinstance(tls, dict) else None
    clients = inbound.get("settings", {}).get("clients") if isinstance(inbound.get("settings"), dict) else None
    if (not isinstance(stream, dict) or stream.get("network") != "ws" or stream.get("security") != "tls"
            or not isinstance(ws, dict) or not isinstance(ws.get("path"), str) or not ws["path"].startswith("/")
            or not isinstance(certificates, list) or len(certificates) != 1
            or not isinstance(clients, list) or not clients):
        _fail("El inbound de 443 no cumple VLESS + WebSocket + TLS o no contiene clientes.")
    certificate = certificates[0]
    leases = manifest.get("leases")
    if (not isinstance(certificate, dict) or not isinstance(leases, list) or len(leases) != 1
            or not isinstance(leases[0], dict)
            or not isinstance(leases[0].get("lease_id"), str)
            or not certificate_resolver.LEASE_RE.fullmatch(leases[0]["lease_id"])):
        _fail("La referencia TLS/lease del inbound es inválida.")
    lease_root = live_staging.LEASE_ROOT
    lease_dir = lease_root / leases[0]["lease_id"]
    for field, filename in (("certificateFile", "certificate.pem"), ("keyFile", "private-key.pem")):
        value = certificate.get(field)
        if (not isinstance(value, str) or Path(value).parent != lease_dir
                or Path(value).name != filename):
            _fail("El inbound debe usar exclusivamente el lease TLS central de esta operación.")

    connections = certificate_resolver._load_connections(live_staging.CONNECTIONS_CATALOG)
    entries = [item for item in connections if item.get("id") == binding["connection_id"]]
    if len(entries) != 1:
        _fail("La conexión TLS asociada al inbound no existe de forma inequívoca.")
    source, protocol = certificate_resolver._connection_config(
        entries[0], binding["connection_id"], live_staging.CONNECTIONS_BASE, live_staging.VMESS_BASE,
    )
    transport = source.get("transport_options") if isinstance(source, dict) else None
    if (protocol != "vless" or source.get("mode_id") != "vless_ws_tls"
            or source.get("transport") != "websocket" or source.get("security") != "tls"
            or source.get("listen_address") != "0.0.0.0" or source.get("listen_port") != TARGET_PORT
            or not isinstance(transport, dict) or transport.get("path") != ws["path"]
            or transport.get("host") != ws.get("host")):
        _fail("La conexión central no coincide con VLESS-WS-TLS público en pruebas.tvrc.me:443.")
    if (leases[0].get("connection_id") != binding["connection_id"]
            or leases[0].get("certificate_id") != source.get("security_options", {}).get("certificate_id")):
        _fail("El lease TLS no corresponde a la conexión/certificado asociados al inbound.")
    # Validar tanto el dominio de conexión como el SNI elegido. Host WS permanece
    # independiente y no se fuerza a coincidir con SNI.
    endpoint_config = dict(source)
    endpoint_config["client_options"] = {}
    try:
        vless_client_export.validate_certificate_sni(
            endpoint_config, str(live_staging.CERTIFICATE_CATALOG), tag, TARGET_DOMAIN,
        )
        vless_client_export.validate_certificate_sni(
            source, str(live_staging.CERTIFICATE_CATALOG), tag, TARGET_DOMAIN,
        )
    except vless_client_export.ExportError as exc:
        raise LiveApplyBridgeError(str(exc)) from exc
    return {"inbound_tag": tag, "connection_id": binding["connection_id"],
            "listen": "0.0.0.0", "port": TARGET_PORT, "domain": TARGET_DOMAIN,
            "transport": "ws", "security": "tls", "clients": len(clients)}


def _discard_unpublished_stage(staging_dir: Path) -> None:
    """Elimina staging/leases sólo antes de cualquier intento de publicación."""
    manifest, _ = live_publisher._read_stage(staging_dir)
    if staging_dir.parent != live_staging.STAGING_ROOT:
        _fail("No se puede limpiar un staging fuera de la raíz administrada.")
    info = staging_dir.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != 0
            or info.st_gid != manifest["service_identity"]["gid"]
            or stat.S_IMODE(info.st_mode) != 0o750):
        _fail("El staging no tiene ownership/permisos esperados para limpieza segura.")
    shutil.rmtree(staging_dir)
    failures = []
    for lease in reversed(manifest.get("leases", [])):
        lease_id = lease.get("lease_id") if isinstance(lease, dict) else None
        try:
            certificate_resolver.cleanup(live_staging.LEASE_ROOT, lease_id,
                                         manifest["service_identity"]["gid"])
        except Exception:
            failures.append(str(lease_id))
    if failures:
        _fail("La validación del perfil falló y quedaron leases por limpiar: " + ", ".join(failures))


def apply_live(profile_id: str, revision: str, *, confirmation: bool) -> dict[str, Any]:
    """Aplica una revisión validada y solicita el primer start live.

    La unidad debe existir y estar inactive; stage/publisher verifican identidad,
    configuración, certificados, locks y estado antes de publicar. Un resultado
    ambiguo se conserva en recovery_required y nunca se reintenta aquí.
    """
    if os.geteuid() != 0:
        _fail("La aplicación live requiere root.")
    if confirmation is not True:
        _fail("La aplicación live requiere confirmación explícita.")

    # Esta primera integración sólo admite primer despliegue. No sustituye una
    # configuración preexistente porque restore live aún falla cerrado.
    initial = systemd_adapter.status(
        unit_file=live_publisher.UNIT_FILE, config_file=live_publisher.CONFIG_FILE,
    )
    if (not isinstance(initial, dict) or initial.get("unit") != "xray.service"
            or initial.get("load_state") != "loaded"
            or initial.get("active_state") != "inactive"
            or initial.get("main_pid") not in (None, 0)
            or initial.get("invocation_id") not in (None, "")
            or initial.get("runtime_config_sha256") is not None):
        _fail("El primer despliegue requiere xray.service cargado e inactive, sin proceso ni config runtime.")
    if live_publisher._read_optional_config() is not None:
        _fail("Ya existe /etc/xray/config.json; el puente inicial no sobrescribe configuraciones hasta implementar restore live.")

    staged = live_staging.stage_live(profile_id, revision)
    if (not isinstance(staged, dict) or staged.get("status") != "STAGED"
            or staged.get("runtime_published") is not False
            or staged.get("service_started") is not False
            or not isinstance(staged.get("staging_dir"), str)):
        _fail("El staging live no devolvió un resultado íntegro; no se publicará.")
    staging_dir = Path(staged["staging_dir"])
    try:
        target = _validate_first_server_profile(staging_dir, profile_id, revision)
    except Exception as exc:
        try:
            _discard_unpublished_stage(staging_dir)
        except Exception as cleanup_exc:
            raise LiveApplyBridgeError(
                "El perfil no cumple el objetivo y la limpieza compensatoria no quedó completa; "
                "revisar staging/leases antes de continuar."
            ) from cleanup_exc
        if isinstance(exc, LiveApplyBridgeError):
            raise
        raise LiveApplyBridgeError("El perfil staged no superó la validación del primer servidor.") from exc

    publication = live_publisher.publish_live(staging_dir)
    operation_id = publication.get("operation_id") if isinstance(publication, dict) else None
    if (not isinstance(publication, dict) or publication.get("status") != "CONFIG_PUBLISHED"
            or publication.get("runtime_published") is not True
            or publication.get("service_action_performed") is not False
            or publication.get("service_started") is not False
            or not isinstance(operation_id, str)
            or not live_journal.OP_RE.fullmatch(operation_id)):
        _fail("El publicador no confirmó una publicación live utilizable; no se iniciará Xray.")

    generation_id = "generation-" + secrets.token_hex(16)
    store = live_journal.LiveOperationStore()
    lifecycle_fd = None
    try:
        lifecycle_fd = live_publisher._acquire_one(live_publisher.LIFECYCLE_LOCK)
        backend = live_backend.LiveRuntimeBackend(
            lifecycle_lock_fd=lifecycle_fd,
            lifecycle_lock_path=live_publisher.LIFECYCLE_LOCK,
            operation_evidence_reader=lambda op, gen: live_evidence.verify_live_operation(
                operation_id=op, generation_id=gen, store=store,
            ),
        )
        result = start_coordinator.start_published_operation(
            store=store, operation_id=operation_id, generation_id=generation_id,
            backend=backend,
            systemd_observer=lambda: systemd_adapter.status(
                unit_file=live_publisher.UNIT_FILE, config_file=live_publisher.CONFIG_FILE,
            ),
            process_observer=process_attestation.observe_process_identity,
            config_hash_reader=_runtime_config_hash,
            confirmation=True,
        )
    except Exception as exc:
        raise LiveApplyBridgeError(
            f"La configuración se publicó, pero el start no quedó verificado. "
            f"Operación {operation_id}; revisar journal/recovery antes de reintentar."
        ) from exc
    finally:
        if lifecycle_fd is not None:
            live_publisher._release_locks([lifecycle_fd])

    return {
        "status": result.get("status"), "operation_id": operation_id,
        "generation_id": generation_id, "profile_id": profile_id, "revision": revision,
        "runtime_published": True, "service_started": result.get("status") == "SERVICE_ACTIVE_CORRELATED",
        "configuration_loaded": False, "completed": False,
        "journal_state": result.get("journal_state"),
        "evidence": result.get("evidence"),
        "staging_dir": staged["staging_dir"],
        "lease_ids": staged.get("lease_ids", []), "target": target,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-id", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--confirm-live", action="store_true", required=True,
                        help="Confirma explícitamente publicación y primer start live.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = apply_live(args.profile_id, args.revision, confirmation=args.confirm_live)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (LiveApplyBridgeError, live_staging.LiveStagingError,
            live_publisher.LivePublisherError, live_backend.LiveBackendError,
            start_coordinator.StartCoordinatorError, live_evidence.LiveOperationEvidenceError,
            live_journal.LiveJournalError, certificate_resolver.ResolverError,
            vless_client_export.ExportError, systemd_adapter.SystemdAdapterError,
            OSError, ValueError, TypeError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
