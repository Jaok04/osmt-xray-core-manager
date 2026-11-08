#!/usr/bin/env python3
"""Lógica pura compartida para asociar inbounds TLS con leases centrales.

Este módulo no accede al filesystem, no resuelve certificados y no ejecuta
Xray. Las envolturas fixture/live conservan sus propias políticas de rutas,
permisos, locks y autorización.
"""
from __future__ import annotations

import re
from typing import Any

TAG_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
CONNECTION_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
LEASE_RE = re.compile(r"resolve-[0-9a-f]{32}\Z")


class StagingCoreError(ValueError):
    """El perfil, el mapping o la asociación de lease no son coherentes."""


def validate_profile_bindings(document: Any, bindings: Any) -> dict[str, dict[str, Any]]:
    """Valida cobertura exacta y devuelve inbound TLS por tag."""
    if not isinstance(document, dict) or not isinstance(document.get("inbounds"), list):
        raise StagingCoreError("El perfil debe contener un arreglo inbounds.")
    if not isinstance(bindings, list) or not bindings:
        raise StagingCoreError("El mapa debe contener al menos una asociación.")

    inbound_by_tag: dict[str, dict[str, Any]] = {}
    tls_inbound_tags: set[str] = set()
    for inbound in document["inbounds"]:
        if not isinstance(inbound, dict):
            raise StagingCoreError("El perfil contiene un inbound que no es objeto.")
        tag = inbound.get("tag")
        stream = inbound.get("streamSettings")
        is_tls = isinstance(stream, dict) and stream.get("security") == "tls"
        if is_tls and (not isinstance(tag, str) or not TAG_RE.fullmatch(tag)):
            raise StagingCoreError("Todo inbound TLS debe tener un tag válido para asociar su conexión central.")
        if isinstance(tag, str):
            if tag in inbound_by_tag:
                raise StagingCoreError("El perfil contiene inbound tags duplicados.")
            inbound_by_tag[tag] = inbound
            if is_tls:
                tls_inbound_tags.add(tag)

    binding_tags: set[str] = set()
    binding_connections: set[str] = set()
    for item in bindings:
        if not isinstance(item, dict) or set(item) != {"inbound_tag", "connection_id"}:
            raise StagingCoreError("Cada asociación requiere exactamente inbound_tag y connection_id.")
        tag, connection_id = item["inbound_tag"], item["connection_id"]
        if not isinstance(tag, str) or not TAG_RE.fullmatch(tag):
            raise StagingCoreError("inbound_tag inválido en el mapa.")
        if not isinstance(connection_id, str) or not CONNECTION_RE.fullmatch(connection_id):
            raise StagingCoreError("connection_id inválido en el mapa.")
        if tag in binding_tags:
            raise StagingCoreError("Un inbound tag no puede tener más de una asociación.")
        if connection_id in binding_connections:
            raise StagingCoreError("Una conexión central no puede reutilizarse en dos inbounds del mismo staging.")
        binding_tags.add(tag)
        binding_connections.add(connection_id)

    if binding_tags != tls_inbound_tags:
        raise StagingCoreError("El mapa debe asociar exactamente todos los inbounds TLS del perfil, sin omisiones ni extras.")

    for tag in tls_inbound_tags:
        stream = inbound_by_tag[tag]["streamSettings"]
        tls = stream.get("tlsSettings")
        if not isinstance(tls, dict):
            raise StagingCoreError("El inbound TLS asociado debe contener tlsSettings.")
        certificates = tls.get("certificates", [])
        if not isinstance(certificates, list) or certificates:
            raise StagingCoreError("El perfil debe dejar tlsSettings.certificates vacío; las rutas se inyectan desde leases.")
    return {tag: inbound_by_tag[tag] for tag in tls_inbound_tags}


def inject_tls_lease(document: dict[str, Any], inbound_tag: str,
                     connection_id: str, certificate_id: str,
                     protocol: str, lease: dict[str, Any]) -> None:
    """Inyecta únicamente rutas devueltas por un lease central preparado."""
    if not isinstance(lease, dict):
        raise StagingCoreError("El resolutor no devolvió un lease estructurado.")
    if (lease.get("status") != "prepared"
            or not isinstance(lease.get("lease_id"), str)
            or not LEASE_RE.fullmatch(lease["lease_id"])
            or lease.get("connection_id") != connection_id
            or lease.get("protocol") != protocol
            or lease.get("certificate_id") != certificate_id):
        raise StagingCoreError("El lease central no corresponde a la asociación solicitada.")
    certificate_file, key_file = lease.get("certificate_file"), lease.get("key_file")
    if (not isinstance(certificate_file, str) or not certificate_file.startswith("/")
            or not isinstance(key_file, str) or not key_file.startswith("/")):
        raise StagingCoreError("El lease central no contiene rutas absolutas de certificado y clave.")
    inbounds = document.get("inbounds")
    matches = [item for item in inbounds if isinstance(item, dict) and item.get("tag") == inbound_tag]
    if len(matches) != 1:
        raise StagingCoreError("El inbound del lease no existe exactamente una vez.")
    stream = matches[0].get("streamSettings")
    tls = stream.get("tlsSettings") if isinstance(stream, dict) else None
    if (not isinstance(stream, dict) or stream.get("security") != "tls"
            or not isinstance(tls, dict) or tls.get("certificates", []) != []):
        raise StagingCoreError("El inbound ya no cumple el contrato TLS validado antes de resolver el lease.")
    tls["certificates"] = [{"certificateFile": certificate_file, "keyFile": key_file}]
