#!/usr/bin/env python3
"""Flujo ACME Certbot controlado para Xray Manager; nunca ejecuta ACME sin confirmación explícita."""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import re
import secrets
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import certificate_store as store

DOMAIN_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
CERT_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DNS_RESOLVERS = ("1.1.1.1", "8.8.8.8", "9.9.9.9")
MAX_CERT_BYTES = 1024 * 1024
MAX_KEY_BYTES = 256 * 1024


class AcmeError(Exception):
    """Error ACME seguro y apto para mostrar al operador."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_domain(value: str, method: str) -> str:
    if not isinstance(value, str):
        raise AcmeError("dominio no válido")
    domain = value.strip().rstrip(".").lower()
    wildcard = domain.startswith("*.")
    base = domain[2:] if wildcard else domain
    if not base or len(base) > 253 or "*" in base:
        raise AcmeError("dominio no válido")
    try:
        ipaddress.ip_address(base)
    except ValueError:
        pass
    else:
        raise AcmeError("se requiere un nombre DNS, no una dirección IP")
    labels = base.split(".")
    if len(labels) < 2 or any(not DOMAIN_LABEL_RE.fullmatch(label) for label in labels):
        raise AcmeError("dominio DNS no válido")
    if wildcard and method != "dns-01":
        raise AcmeError("los certificados wildcard requieren DNS-01")
    return ("*." if wildcard else "") + base


def validate_request(domains: list[str], method: str, email: str) -> list[str]:
    if method not in ("http-01", "dns-01"):
        raise AcmeError("método ACME no admitido")
    if not isinstance(email, str) or not EMAIL_RE.fullmatch(email.strip()):
        raise AcmeError("correo de contacto no válido")
    if not domains:
        raise AcmeError("debe indicarse al menos un dominio")
    normalized = [normalize_domain(x, method) for x in domains]
    if len(normalized) != len(set(normalized)):
        raise AcmeError("hay dominios duplicados")
    return sorted(normalized)


def default_cert_name(domains: list[str]) -> str:
    digest = hashlib.sha256("\n".join(sorted(domains)).encode()).hexdigest()[:12]
    return f"xray-manager-{digest}"


def build_certbot_command(
    *,
    method: str,
    domains: list[str],
    email: str,
    cert_name: str,
    certbot_bin: str = "certbot",
    config_dir: str = "/etc/letsencrypt",
    work_dir: str = "/var/lib/letsencrypt",
    logs_dir: str = "/var/log/letsencrypt",
    auth_hook: str | None = None,
    cleanup_hook: str | None = None,
) -> list[str]:
    domains = validate_request(domains, method, email)
    if not CERT_NAME_RE.fullmatch(cert_name):
        raise AcmeError("nombre de lineage Certbot no válido")
    command = [
        certbot_bin, "certonly",
        "--config-dir", config_dir,
        "--work-dir", work_dir,
        "--logs-dir", logs_dir,
        "--cert-name", cert_name,
        "--agree-tos", "--email", email.strip(),
    ]
    if method == "http-01":
        command += ["--standalone", "--preferred-challenges", "http", "--http-01-port", "80", "--non-interactive"]
    else:
        if not auth_hook or not cleanup_hook:
            raise AcmeError("DNS-01 manual requiere hooks de publicación/verificación y limpieza informativa")
        command += [
            "--manual", "--preferred-challenges", "dns",
            "--manual-auth-hook", auth_hook,
            "--manual-cleanup-hook", cleanup_hook,
        ]
    for domain in domains:
        command += ["-d", domain]
    return command


def safe_private_dir(path: Path, *, create: bool = False) -> None:
    if create and not path.exists() and not path.is_symlink():
        path.mkdir(parents=True, mode=0o700)
        os.chmod(path, 0o700)
    store.safe_dir(path)


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    safe_private_dir(path.parent, create=True)
    data = (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        os.chmod(path, 0o600)
        dfd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def load_request_record(path: Path) -> dict[str, Any]:
    try:
        before = path.lstat()
        if (
            not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
            or before.st_uid != 0 or before.st_gid != 0
            or stat.S_IMODE(before.st_mode) != 0o600
            or before.st_size < 1 or before.st_size > 64 * 1024
        ):
            raise AcmeError("registro de solicitud ACME inseguro")
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "rb") as stream:
            current = os.fstat(stream.fileno())
            if (current.st_dev, current.st_ino, current.st_uid, current.st_gid,
                current.st_nlink, current.st_size, stat.S_IMODE(current.st_mode)) != (
                before.st_dev, before.st_ino, before.st_uid, before.st_gid,
                before.st_nlink, before.st_size, stat.S_IMODE(before.st_mode)
            ):
                raise AcmeError("registro ACME cambió durante su apertura")
            raw = stream.read(64 * 1024 + 1)
        if len(raw) != before.st_size or len(raw) > 64 * 1024:
            raise AcmeError("registro ACME cambió durante su lectura")
        value = json.loads(raw.decode("utf-8"))
    except OSError as exc:
        raise AcmeError("no se pudo leer el registro de solicitud ACME") from exc
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AcmeError("registro de solicitud ACME corrupto") from exc
    if not isinstance(value, dict):
        raise AcmeError("estructura de solicitud ACME no válida")
    return value


def request_record(domains: list[str], method: str, email: str, cert_name: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "certificate_request_id": "acme-" + secrets.token_hex(10),
        "method": method,
        "client": "certbot",
        "challenge_mode": "standalone" if method == "http-01" else "manual",
        "domains": domains,
        "contact_email": email,
        "cert_name": cert_name,
        "status": "requested",
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }


def dig_query(name: str, record_type: str, resolver: str, *, dig_bin: str = "dig") -> set[str]:
    if record_type not in ("A", "AAAA", "TXT"):
        raise AcmeError("tipo DNS no admitido")
    try:
        ipaddress.ip_address(resolver)
    except ValueError as exc:
        raise AcmeError("resolutor DNS no válido") from exc
    if shutil.which(dig_bin) is None:
        raise AcmeError("no está disponible dig; no se instalarán dependencias automáticamente")
    result = subprocess.run(
        [dig_bin, "+time=2", "+tries=1", "+short", record_type, name, "@" + resolver],
        check=False, capture_output=True, text=True, timeout=5,
    )
    if result.returncode not in (0, 9):
        raise AcmeError("falló la consulta DNS")
    values: set[str] = set()
    for line in result.stdout.splitlines():
        item = line.strip().strip('"')
        if item:
            values.add(item)
    return values


def check_txt_visibility(
    record_name: str,
    expected_value: str,
    *,
    resolvers: tuple[str, ...] = DNS_RESOLVERS,
    query: Callable[[str, str, str], set[str]] = dig_query,
) -> dict[str, Any]:
    if not record_name.startswith("_acme-challenge.") or not expected_value:
        raise AcmeError("desafío TXT no válido")
    observations = {resolver: sorted(query(record_name, "TXT", resolver)) for resolver in resolvers}
    visible = [resolver for resolver, values in observations.items() if expected_value in values]
    return {
        "record_name": record_name,
        "expected_value_visible": len(visible) == len(resolvers),
        "visible_resolvers": visible,
        "required_resolvers": list(resolvers),
        "observations": observations,
    }


def check_http_preconditions(
    domains: list[str],
    expected_addresses: list[str],
    *,
    query: Callable[[str, str, str], set[str]] = dig_query,
    port_probe: Callable[[], bool] | None = None,
    resolvers: tuple[str, ...] = DNS_RESOLVERS,
) -> dict[str, Any]:
    if not expected_addresses:
        raise AcmeError("HTTP-01 requiere confirmar la IP pública prevista mediante --expected-address")
    try:
        expected = {str(ipaddress.ip_address(x)) for x in expected_addresses}
    except ValueError as exc:
        raise AcmeError("IP prevista no válida") from exc
    dns: dict[str, dict[str, list[str]]] = {}
    for domain in domains:
        host = domain[2:] if domain.startswith("*.") else domain
        if domain.startswith("*."):
            raise AcmeError("HTTP-01 no admite wildcard")
        found: set[str] = set()
        by_resolver: dict[str, list[str]] = {}
        for resolver in resolvers:
            records = query(host, "A", resolver) | query(host, "AAAA", resolver)
            if not records:
                raise AcmeError(f"el dominio {host} no publica A/AAAA visible en {resolver}")
            unexpected = records - expected
            if unexpected:
                raise AcmeError(f"el dominio {host} resuelve a IP no prevista en {resolver}")
            found.update(records)
            by_resolver[resolver] = sorted(records)
        if not found:
            raise AcmeError(f"el dominio {host} no publica A/AAAA visible")
        dns[host] = by_resolver
    available = (port_probe or port_80_available)()
    if not available:
        raise AcmeError("el puerto TCP 80 está ocupado; no se detendrá ningún servicio")
    return {
        "dns": dns,
        "expected_addresses": sorted(expected),
        "port_80_available": True,
        "external_ca_reachability": "not_verified_until_acme_challenge",
    }


def port_80_available() -> bool:
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        probe.bind(("0.0.0.0", 80))
        return True
    except OSError:
        return False
    finally:
        probe.close()


def dns_hooks_source() -> tuple[str, str]:
    auth = r'''#!/usr/bin/env python3
import os, subprocess, sys
domain = os.environ.get("CERTBOT_DOMAIN", "").lstrip("*.")
token = os.environ.get("CERTBOT_VALIDATION", "")
record = "_acme-challenge." + domain
if not domain or not token:
    print("Desafío Certbot incompleto", file=sys.stderr); raise SystemExit(2)
print("Publica manualmente este registro DNS TXT:")
print("Nombre:", record)
print("Valor:", token)
input("Cuando hayas publicado el TXT, pulsa Enter para comprobar propagación...")
resolvers = os.environ.get("XRAY_MANAGER_DNS_RESOLVERS", "1.1.1.1,8.8.8.8,9.9.9.9").split(",")
missing = []
for resolver in resolvers:
    result = subprocess.run(["dig", "+time=2", "+tries=1", "+short", "TXT", record, "@" + resolver],
                            capture_output=True, text=True, timeout=5)
    values = {line.strip().strip('"') for line in result.stdout.splitlines() if line.strip()}
    if token not in values: missing.append(resolver)
if missing:
    print("TXT todavía no visible en: " + ", ".join(missing), file=sys.stderr)
    raise SystemExit(1)
print("TXT visible en todos los resolutores configurados.")
'''
    cleanup = r'''#!/usr/bin/env python3
import os
domain = os.environ.get("CERTBOT_DOMAIN", "").lstrip("*.")
token = os.environ.get("CERTBOT_VALIDATION", "")
print("Desafío validado. Retira manualmente solo el valor TXT correspondiente:")
print("Nombre: _acme-challenge." + domain)
print("Valor exacto: " + token)
print("No elimines otros valores TXT del mismo nombre.")
'''
    return auth, cleanup


def write_hooks(directory: Path) -> tuple[Path, Path]:
    safe_private_dir(directory, create=True)
    auth_source, cleanup_source = dns_hooks_source()
    auth = directory / "dns-auth-hook.py"
    cleanup = directory / "dns-cleanup-hook.py"
    for path, content in ((auth, auth_source), (cleanup, cleanup_source)):
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o700)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(path, 0o700)
    return auth, cleanup


def safe_certbot_config_dir(path: Path) -> None:
    path = path.absolute()
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            st = current.lstat()
        except OSError as exc:
            raise AcmeError("falta el directorio de configuración de Certbot") from exc
        if not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode):
            raise AcmeError("el directorio de Certbot contiene un componente inseguro")
        if current == path and (st.st_uid != 0 or st.st_gid != 0 or stat.S_IMODE(st.st_mode) & 0o022):
            raise AcmeError("el directorio de configuración de Certbot debe ser root:root y no permitir escritura a grupo/otros")


def _safe_certbot_lineage_dir(path: Path) -> None:
    try:
        st = path.lstat()
    except OSError as exc:
        raise AcmeError("falta un directorio del lineage Certbot") from exc
    if (
        not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode)
        or st.st_uid != 0 or st.st_gid != 0 or stat.S_IMODE(st.st_mode) & 0o022
    ):
        raise AcmeError("directorio del lineage Certbot inseguro")


def _read_certbot_target(path: Path, archive_root: Path, limit: int, *, private: bool) -> bytes:
    try:
        resolved = path.resolve(strict=True)
        archive = archive_root.resolve(strict=True)
        if not resolved.is_relative_to(archive):
            raise AcmeError("Certbot lineage apunta fuera del directorio archive autorizado")
        st = resolved.lstat()
        if (
            not stat.S_ISREG(st.st_mode) or st.st_nlink != 1
            or st.st_uid != 0 or st.st_gid != 0
            or st.st_size < 1 or st.st_size > limit
        ):
            raise AcmeError("archivo emitido por Certbot inseguro")
        if private and stat.S_IMODE(st.st_mode) != 0o600:
            raise AcmeError("la clave privada emitida por Certbot debe tener permisos root-only 0600")
        fd = os.open(resolved, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "rb") as stream:
            current = os.fstat(stream.fileno())
            if (current.st_dev, current.st_ino, current.st_nlink, current.st_size) != (
                st.st_dev, st.st_ino, st.st_nlink, st.st_size
            ):
                raise AcmeError("archivo Certbot cambió durante su lectura")
            data = stream.read(limit + 1)
        if len(data) != st.st_size or len(data) > limit:
            raise AcmeError("archivo Certbot cambió durante su lectura")
        return data
    except OSError as exc:
        raise AcmeError("no se pudo leer el lineage Certbot") from exc


def stage_and_import(
    *,
    config_dir: Path,
    cert_name: str,
    requested_domains: list[str],
    staging_parent: Path,
    store_args: Namespace,
    validated_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    if not CERT_NAME_RE.fullmatch(cert_name):
        raise AcmeError("nombre de lineage Certbot no válido")
    safe_certbot_config_dir(config_dir)
    archive_root = config_dir / "archive"
    live_root = config_dir / "live"
    live = live_root / cert_name
    _safe_certbot_lineage_dir(archive_root)
    _safe_certbot_lineage_dir(live_root)
    _safe_certbot_lineage_dir(live)
    cert_bytes = _read_certbot_target(live / "fullchain.pem", archive_root, MAX_CERT_BYTES, private=False)
    key_bytes = _read_certbot_target(live / "privkey.pem", archive_root, MAX_KEY_BYTES, private=True)
    metadata = store.parse_certificate(cert_bytes, key_bytes)
    missing = sorted(set(requested_domains) - set(metadata.get("sans", [])))
    if missing:
        raise AcmeError("el certificado emitido no cubre todos los dominios solicitados")
    if validated_callback is not None:
        validated_callback(metadata)
    safe_private_dir(staging_parent)
    with tempfile.TemporaryDirectory(prefix="xray-acme-stage-", dir=staging_parent) as temp_name:
        stage = Path(temp_name)
        os.chmod(stage, 0o700)
        cert_path = stage / "fullchain.pem"
        key_path = stage / "privkey.pem"
        for path, data, mode in ((cert_path, cert_bytes, 0o600), (key_path, key_bytes, 0o600)):
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), mode)
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(path, mode)
        args = Namespace(**vars(store_args))
        args.action = "import"
        args.storage_type = "managed"
        args.certificate_file = str(cert_path)
        args.private_key_file = str(key_path)
        result = store.import_certificate(args)
        return {
            "status": "imported",
            "certificate_id": result["certificate_id"],
            "fingerprint_sha256": result["fingerprint_sha256"],
            "sans": result["sans"],
            "revision": result["revision"],
            "storage_type": result["storage_type"],
        }


def run_certbot(command: list[str], *, env: dict[str, str] | None = None) -> int:
    try:
        completed = subprocess.run(command, check=False, env=env)
    except FileNotFoundError as exc:
        raise AcmeError("Certbot no está instalado o no se encuentra en PATH") from exc
    except OSError as exc:
        raise AcmeError("no se pudo ejecutar Certbot") from exc
    return completed.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    plan = sub.add_parser("plan", help="validar y mostrar el comando; no ejecuta Certbot")
    plan.add_argument("--method", choices=("http-01", "dns-01"), required=True)
    plan.add_argument("--domain", action="append", required=True)
    plan.add_argument("--email", required=True)
    plan.add_argument("--cert-name")
    plan.add_argument("--certbot-bin", default="certbot")
    plan.add_argument("--config-dir", default="/etc/letsencrypt")
    plan.add_argument("--work-dir", default="/var/lib/letsencrypt")
    plan.add_argument("--logs-dir", default="/var/log/letsencrypt")
    issue = sub.add_parser("issue", help="solicitar certificado; requiere confirmación explícita")
    for action in (issue,):
        action.add_argument("--method", choices=("http-01", "dns-01"), required=True)
        action.add_argument("--domain", action="append", required=True)
        action.add_argument("--email", required=True)
        action.add_argument("--cert-name")
        action.add_argument("--certbot-bin", default="certbot")
        action.add_argument("--config-dir", default="/etc/letsencrypt")
        action.add_argument("--work-dir", default="/var/lib/letsencrypt")
        action.add_argument("--logs-dir", default="/var/log/letsencrypt")
    issue.add_argument("--expected-address", action="append", default=[])
    issue.add_argument("--state-dir", default="/var/lib/xray-manager/certificates/acme/requests")
    issue.add_argument("--confirm-acme", action="store_true")
    imp = sub.add_parser("import-certbot", help="validar e importar un lineage Certbot al almacén central")
    imp.add_argument("--method", choices=("http-01", "dns-01"), required=True)
    imp.add_argument("--domain", action="append", required=True)
    imp.add_argument("--email", required=True)
    imp.add_argument("--cert-name", required=True)
    imp.add_argument("--request-id", required=True)
    imp.add_argument("--config-dir", default="/etc/letsencrypt")
    imp.add_argument("--staging-parent", default="/run/xray-manager-acme-staging")
    imp.add_argument("--state-dir", default="/var/lib/xray-manager/certificates/acme/requests")
    imp.add_argument("--base", default="/var/lib/xray-manager/certificates")
    imp.add_argument("--catalog", default="/var/lib/xray-manager/certificates/catalog.json")
    imp.add_argument("--managed-dir", default="/var/lib/xray-manager/certificates/managed")
    imp.add_argument("--secrets-dir", default="/var/lib/xray-manager/certificates/secrets")
    imp.add_argument("--master-key", default="/etc/xray-manager/keys/master.key")
    imp.add_argument("--lock", default="/run/xray-manager-certificate-locks/catalog.lock")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        domains = validate_request(args.domain, args.method, args.email)
        cert_name = args.cert_name or default_cert_name(domains)
        if args.action == "import-certbot":
            if os.geteuid() != 0:
                raise AcmeError("la importación al almacén central requiere root")
            if not re.fullmatch(r"acme-[0-9a-f]{20}", args.request_id):
                raise AcmeError("identificador de solicitud ACME no válido")
            state_dir = Path(args.state_dir)
            safe_private_dir(state_dir)
            state_path = state_dir / (args.request_id + ".json")
            record = load_request_record(state_path)
            if record.get("status") != "issued" or record.get("cert_name") != args.cert_name or record.get("domains") != domains or record.get("method") != args.method or record.get("contact_email") != args.email:
                raise AcmeError("el lineage no coincide con una solicitud emitida y registrada")
            staging_parent = Path(args.staging_parent)
            safe_private_dir(staging_parent, create=True)
            store_args = Namespace(
                base=args.base, catalog=args.catalog, managed_dir=args.managed_dir,
                secrets_dir=args.secrets_dir, master_key=args.master_key, lock=args.lock,
                certificate_id=None,
            )
            def mark_validated(_metadata: dict[str, Any]) -> None:
                record["status"] = "validated"
                record["updated_at"] = utc_now()
                atomic_json(state_path, record)

            result = stage_and_import(
                config_dir=Path(args.config_dir), cert_name=args.cert_name,
                requested_domains=domains, staging_parent=staging_parent,
                store_args=store_args, validated_callback=mark_validated,
            )
            record["status"] = "imported"
            record["certificate_id"] = result["certificate_id"]
            record["updated_at"] = utc_now()
            atomic_json(state_path, record)
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            return 0
        if args.action == "plan":
            hooks = ("<temporary>/dns-auth-hook.py", "<temporary>/dns-cleanup-hook.py") if args.method == "dns-01" else (None, None)
            command = build_certbot_command(
                method=args.method, domains=domains, email=args.email, cert_name=cert_name,
                certbot_bin=args.certbot_bin, config_dir=args.config_dir, work_dir=args.work_dir,
                logs_dir=args.logs_dir, auth_hook=hooks[0], cleanup_hook=hooks[1],
            )
            print(json.dumps({"status": "planned", "method": args.method, "client": "certbot",
                              "domains": domains, "cert_name": cert_name, "command": command,
                              "live_operation": False}, ensure_ascii=False, sort_keys=True))
            return 0
        if not args.confirm_acme:
            raise AcmeError("operación bloqueada: falta --confirm-acme")
        if os.geteuid() != 0:
            raise AcmeError("la solicitud ACME requiere privilegios root")
        if shutil.which(args.certbot_bin) is None:
            raise AcmeError("Certbot no está instalado o no se encuentra en PATH; no se instalarán dependencias")
        record = request_record(domains, args.method, args.email, cert_name)
        state_dir = Path(args.state_dir)
        safe_private_dir(state_dir, create=True)
        state_path = state_dir / (record["certificate_request_id"] + ".json")
        if state_path.exists() or state_path.is_symlink():
            raise AcmeError("ya existe una solicitud con el mismo identificador")
        atomic_json(state_path, record)
        hook_tmp = tempfile.TemporaryDirectory(prefix="xray-acme-hooks-") if args.method == "dns-01" else None
        try:
            auth_hook = cleanup_hook = None
            if hook_tmp:
                auth_hook, cleanup_hook = write_hooks(Path(hook_tmp.name))
            if args.method == "http-01":
                try:
                    check_http_preconditions(domains, args.expected_address)
                except AcmeError:
                    record["status"] = "failed"
                    record["failure_stage"] = "preflight"
                    record["updated_at"] = utc_now()
                    atomic_json(state_path, record)
                    raise
            command = build_certbot_command(
                method=args.method, domains=domains, email=args.email, cert_name=cert_name,
                certbot_bin=args.certbot_bin, config_dir=args.config_dir, work_dir=args.work_dir,
                logs_dir=args.logs_dir,
                auth_hook=str(auth_hook) if auth_hook else None,
                cleanup_hook=str(cleanup_hook) if cleanup_hook else None,
            )
            record["status"] = "challenge_pending"
            record["updated_at"] = utc_now()
            atomic_json(state_path, record)
            code = run_certbot(command)
            record["status"] = "issued" if code == 0 else "failed"
            record["updated_at"] = utc_now()
            record["exit_code"] = code
            atomic_json(state_path, record)
            print(json.dumps({"status": record["status"], "certificate_request_id": record["certificate_request_id"],
                              "cert_name": cert_name, "exit_code": code}, sort_keys=True))
            return 0 if code == 0 else 1
        finally:
            if hook_tmp:
                hook_tmp.cleanup()
    except (AcmeError, store.StoreError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
