#!/usr/bin/env python3
"""Motor aislado de validación estática y nativa para configuraciones Xray independientes.

No accede al almacén, no carga la clave maestra, no persiste informes y no aplica
configuraciones. El llamador entrega los bytes exactos de una revisión ya verificada.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MAX_CONFIG_BYTES = 16 * 1024 * 1024
MIN_TIMEOUT = 1
MAX_TIMEOUT = 120
VALID_LOGLEVELS = {"debug", "info", "warning", "error", "none"}
VALID_DOMAIN_STRATEGIES = {"AsIs", "IPIfNonMatch", "IPOnDemand"}
ENV = {"PATH": "/usr/bin:/bin", "HOME": "/nonexistent", "LANG": "C", "LC_ALL": "C"}


class ValidationInputError(ValueError):
    """La solicitud al motor no cumple su contrato."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _strict_json(data: bytes) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"clave JSON duplicada: {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise ValueError(f"constante JSON no permitida: {value}")

    text = data.decode("utf-8", errors="strict")
    return json.loads(text, object_pairs_hook=pairs, parse_constant=reject_constant)


def _check(name: str, status: str, errors: list[str] | None = None,
           warnings: list[str] | None = None, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "errors": errors or [],
        "warnings": warnings or [],
        "details": details or {},
    }


def _object_list(value: Any, label: str, errors: list[str]) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        errors.append(f"{label} debe ser un arreglo")
        return []
    result = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(f"{label}[{index}] debe ser un objeto")
        else:
            result.append(item)
    return result


def _static_checks(data: bytes) -> tuple[list[dict[str, Any]], Any | None]:
    checks: list[dict[str, Any]] = []
    try:
        document = _strict_json(data)
    except (UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        checks.append(_check("json_syntax", "FAIL", [str(exc)[:240]]))
        for name in ("xray_structure", "required_parameters", "types_values",
                     "compatibility", "references_conflicts"):
            checks.append(_check(name, "NOT_RUN", ["depende de JSON válido"]))
        return checks, None

    if not isinstance(document, dict):
        checks.append(_check("json_syntax", "FAIL", ["la raíz JSON debe ser un objeto"]))
        for name in ("xray_structure", "required_parameters", "types_values",
                     "compatibility", "references_conflicts"):
            checks.append(_check(name, "NOT_RUN", ["depende de una raíz JSON objeto"]))
        return checks, None
    checks.append(_check("json_syntax", "PASS", details={"root_type": "object"}))

    errors: list[str] = []
    inbound = _object_list(document.get("inbounds"), "inbounds", errors)
    outbound = _object_list(document.get("outbounds"), "outbounds", errors)
    for key, expected in (("routing", dict), ("dns", dict), ("log", dict),
                          ("stats", dict), ("api", dict), ("policy", dict),
                          ("observatory", dict), ("burstObservatory", dict)):
        if key in document and not isinstance(document[key], expected):
            errors.append(f"{key} debe ser un objeto")
    if "routing" in document and isinstance(document["routing"], dict):
        if "rules" in document["routing"] and not isinstance(document["routing"]["rules"], list):
            errors.append("routing.rules debe ser un arreglo")
    if "dns" in document and isinstance(document["dns"], dict):
        if "servers" in document["dns"] and not isinstance(document["dns"]["servers"], list):
            errors.append("dns.servers debe ser un arreglo")
    checks.append(_check("xray_structure", "FAIL" if errors else "PASS", errors))

    required_errors: list[str] = []
    all_endpoints = [("inbounds", item, i) for i, item in enumerate(inbound)]
    all_endpoints += [("outbounds", item, i) for i, item in enumerate(outbound)]
    for section, item, index in all_endpoints:
        protocol = item.get("protocol")
        if not isinstance(protocol, str) or not protocol.strip():
            required_errors.append(f"{section}[{index}].protocol debe ser una cadena no vacía")
        if "settings" in item and not isinstance(item["settings"], dict):
            required_errors.append(f"{section}[{index}].settings debe ser un objeto")
        if "streamSettings" in item and not isinstance(item["streamSettings"], dict):
            required_errors.append(f"{section}[{index}].streamSettings debe ser un objeto")
        if "tag" in item and (not isinstance(item["tag"], str) or not item["tag"]):
            required_errors.append(f"{section}[{index}].tag debe ser una cadena no vacía")
    if not inbound:
        required_errors.append("se requiere al menos un inbound")
    if not outbound:
        required_errors.append("se requiere al menos un outbound")
    checks.append(_check("required_parameters", "FAIL" if required_errors else "PASS", required_errors))

    type_errors: list[str] = []
    log = document.get("log")
    if isinstance(log, dict) and "loglevel" in log:
        level = log["loglevel"]
        if not isinstance(level, str) or level.lower() not in VALID_LOGLEVELS:
            type_errors.append("log.loglevel no pertenece a los valores reconocidos")
    routing = document.get("routing")
    if isinstance(routing, dict) and "domainStrategy" in routing:
        if routing["domainStrategy"] not in VALID_DOMAIN_STRATEGIES:
            type_errors.append("routing.domainStrategy no pertenece a los valores reconocidos")
    for section, endpoints in (("inbounds", inbound), ("outbounds", outbound)):
        for index, item in enumerate(endpoints):
            if "sendThrough" in item and not isinstance(item["sendThrough"], str):
                type_errors.append(f"{section}[{index}].sendThrough debe ser una cadena")
    checks.append(_check("types_values", "FAIL" if type_errors else "PASS", type_errors))

    # No se inventan reglas de compatibilidad por versión: la autoridad final es
    # el parser/validador nativo de la versión instalada.
    checks.append(_check("compatibility", "DEFERRED_TO_NATIVE", details={
        "policy": "sin matriz local de opciones/versiones no sustentada"
    }))

    reference_errors: list[str] = []
    # Los espacios de nombres inbound/outbound se mantienen separados: una
    # etiqueta de entrada no es una referencia de salida y viceversa.
    for section, endpoints in (("inbounds", inbound), ("outbounds", outbound)):
        seen_tags: set[str] = set()
        for index, item in enumerate(endpoints):
            tag = item.get("tag")
            if isinstance(tag, str) and tag:
                if tag in seen_tags:
                    reference_errors.append(f"tag duplicado en {section}: {tag}")
                seen_tags.add(tag)
    outbound_tags = {item.get("tag") for item in outbound if isinstance(item.get("tag"), str)}
    inbound_tags = {item.get("tag") for item in inbound if isinstance(item.get("tag"), str)}
    balancer_tags: set[str] = set()
    if isinstance(routing, dict):
        balancers = routing.get("balancers", [])
        if not isinstance(balancers, list):
            reference_errors.append("routing.balancers debe ser un arreglo")
        else:
            for index, balancer in enumerate(balancers):
                if not isinstance(balancer, dict) or not isinstance(balancer.get("tag"), str) or not balancer["tag"]:
                    reference_errors.append(f"routing.balancers[{index}] requiere tag de cadena no vacía")
                else:
                    if balancer["tag"] in balancer_tags:
                        reference_errors.append(f"tag de balancer duplicado: {balancer['tag']}")
                    balancer_tags.add(balancer["tag"])
        if isinstance(routing.get("rules", []), list):
            for index, rule in enumerate(routing.get("rules", [])):
                if not isinstance(rule, dict):
                    reference_errors.append(f"routing.rules[{index}] debe ser un objeto")
                    continue
                target = rule.get("outboundTag")
                if target is not None and (not isinstance(target, str) or target not in outbound_tags):
                    reference_errors.append(f"routing.rules[{index}].outboundTag no referencia un outbound")
                balancer = rule.get("balancerTag")
                if balancer is not None and (not isinstance(balancer, str) or balancer not in balancer_tags):
                    reference_errors.append(f"routing.rules[{index}].balancerTag no referencia un balancer")
                inbound_ref = rule.get("inboundTag")
                if inbound_ref is not None:
                    refs = [inbound_ref] if isinstance(inbound_ref, str) else inbound_ref
                    if not isinstance(refs, list) or any(not isinstance(tag, str) or tag not in inbound_tags for tag in refs):
                        reference_errors.append(f"routing.rules[{index}].inboundTag no referencia inbound(s)")
    checks.append(_check("references_conflicts", "FAIL" if reference_errors else "PASS", reference_errors))
    return checks, document


def _safe_binary(binary: Path) -> tuple[str, str]:
    if not binary.is_absolute():
        raise OSError("la ruta del binario Xray debe ser absoluta")
    current = Path(binary.anchor)
    for part in binary.parts[1:]:
        current = current / part
        if current.is_symlink():
            raise OSError("la ruta del binario Xray contiene un enlace simbólico")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(binary, flags)
    except OSError as exc:
        raise OSError("no se pudo abrir el binario Xray de forma segura") from exc
    try:
        st = os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or st.st_uid != 0
                or stat.S_IMODE(st.st_mode) & 0o022 or not st.st_mode & 0o111):
            raise OSError("el binario debe ser regular, root-owned, sin hardlinks, no modificable por grupo/otros y ejecutable")
        digest = hashlib.sha256()
        while True:
            block = os.read(fd, 1024 * 1024)
            if not block:
                break
            digest.update(block)
    finally:
        os.close(fd)
    version = subprocess.run(
        [str(binary), "version"], stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=ENV,
        timeout=10, check=False,
    )
    if version.returncode != 0:
        raise OSError("no se pudo obtener la versión del binario Xray")
    first_line = version.stdout.decode("utf-8", "replace").splitlines()
    if not first_line or not first_line[0].startswith("Xray "):
        raise OSError("la salida de versión del binario no tiene el formato esperado")
    return first_line[0][:160], digest.hexdigest()


def _native_check(data: bytes, binary: Path, timeout: int) -> tuple[dict[str, Any], dict[str, str]]:
    metadata: dict[str, str] = {}
    try:
        version, binary_sha256 = _safe_binary(binary)
        metadata = {"version": version, "binary_sha256": binary_sha256, "binary": str(binary)}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return _check("xray_native", "INCOMPLETE", [str(exc)[:240]]), metadata

    try:
        with tempfile.TemporaryDirectory(prefix="xray-validation-") as temp:
            os.chmod(temp, 0o700)
            config = Path(temp) / "config.json"
            fd = os.open(config, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
            except Exception:
                raise
            result = subprocess.run(
                [str(binary), "run", "-test", "-config", str(config)],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, env=ENV, timeout=timeout, check=False,
            )
    except subprocess.TimeoutExpired:
        return _check("xray_native", "INCOMPLETE", ["Xray excedió el tiempo límite"]), metadata
    except OSError as exc:
        return _check("xray_native", "INCOMPLETE", [f"no fue posible ejecutar Xray: {exc.strerror or type(exc).__name__}"]), metadata
    if result.returncode != 0:
        return _check("xray_native", "FAIL", [f"Xray rechazó la configuración (código {result.returncode})"]), metadata
    return _check("xray_native", "PASS"), metadata


def validate_configuration(data: bytes, xray_binary: str | os.PathLike[str] = "/usr/local/bin/xray",
                           timeout: int = 20) -> dict[str, Any]:
    """Valida bytes exactos; no lee almacenes ni persiste resultados."""
    if not isinstance(data, bytes):
        raise ValidationInputError("data debe ser bytes")
    if not 1 <= len(data) <= MAX_CONFIG_BYTES:
        raise ValidationInputError("tamaño de configuración fuera del rango 1..16 MiB")
    if type(timeout) is not int or not MIN_TIMEOUT <= timeout <= MAX_TIMEOUT:
        raise ValidationInputError("timeout debe estar entre 1 y 120 segundos")
    binary = Path(xray_binary)
    checks, _document = _static_checks(data)
    required_static = ("json_syntax", "xray_structure", "required_parameters",
                       "types_values", "references_conflicts")
    static_failed = any(
        next((c["status"] for c in checks if c["name"] == name), "NOT_RUN") != "PASS"
        for name in required_static
    )
    base = {
        "schema_version": 1,
        "created_at": _utc_now(),
        "content_sha256": hashlib.sha256(data).hexdigest(),
        "content_size_bytes": len(data),
        "checks": checks,
        "xray": {},
        "report_persisted": False,
        "configuration_applied": False,
        "service_started": False,
    }
    if static_failed:
        checks.append(_check("xray_native", "NOT_RUN", ["dependencias estáticas no satisfechas"]))
        base["result"] = "FAIL"
        return base

    native, metadata = _native_check(data, binary, timeout)
    checks.append(native)
    base["xray"] = metadata
    if native["status"] == "INCOMPLETE":
        base["result"] = "INCOMPLETE"
    elif native["status"] == "FAIL":
        base["result"] = "FAIL"
    elif any(check["warnings"] for check in checks):
        base["result"] = "PASS_WITH_WARNINGS"
    else:
        base["result"] = "PASS"
    return base
