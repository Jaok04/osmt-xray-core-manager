#!/usr/bin/env python3
"""Almacén versionado y fail-closed de configuraciones neutrales VLESS."""
from __future__ import annotations
import argparse, fcntl, json, os, re, stat, sys, tempfile
from pathlib import Path

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
MODES = {
    "vless_ws": ("websocket", "none"), "vless_tcp_tls": ("raw", "tls"),
    "vless_ws_tls": ("websocket", "tls"), "vless_reality": ("raw", "reality"),
    "vless_grpc_tls": ("grpc", "tls"), "vless_grpc_reality": ("grpc", "reality"),
    "vless_xhttp": ("xhttp", "none"), "vless_xhttp_tls": ("xhttp", "tls"),
    "vless_xhttp_reality": ("xhttp", "reality"),
}
MAX_CONFIG = 256 * 1024

class StoreError(Exception):
    pass

def safe_id(value: object) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise StoreError("ID de conexión no válido")
    return value

def check_dir(path: Path, create: bool = False) -> None:
    path = path.absolute()
    cur = Path(path.anchor)
    for part in path.parts[1:]:
        cur /= part
        try: st = cur.lstat()
        except FileNotFoundError:
            if not create or cur != path: raise StoreError("falta un directorio padre")
            cur.mkdir(mode=0o700)
            st = cur.lstat()
        if not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode):
            raise StoreError("ruta con componente no directorio o symlink")
    st = path.lstat()
    if st.st_uid != 0 or stat.S_IMODE(st.st_mode) != 0o700:
        raise StoreError("directorio debe ser root:root modo 0700")

def read_regular(path: Path, limit: int) -> bytes:
    try: st = path.lstat()
    except OSError as exc: raise StoreError("archivo requerido ausente") from exc
    if not stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode) or st.st_nlink != 1:
        raise StoreError("archivo no regular o symlink rechazado")
    if st.st_uid != 0 or stat.S_IMODE(st.st_mode) != 0o600 or st.st_size > limit:
        raise StoreError("propietario, permisos o tamaño de archivo no válido")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as stream: data = stream.read(limit + 1)
    if len(data) != st.st_size or len(data) > limit: raise StoreError("archivo cambió durante lectura")
    return data

def atomic_write(path: Path, data: bytes) -> None:
    if path.is_symlink(): raise StoreError("destino symlink rechazado")
    fd, name = tempfile.mkstemp(prefix=".vless-config.", dir=path.parent)
    tmp = Path(name)
    try:
        os.fchown(fd, 0, 0); os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.replace(tmp, path)
        dfd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try: os.fsync(dfd)
        finally: os.close(dfd)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise

def validate_config(config: object, connection: dict) -> dict:
    if not isinstance(config, dict): raise StoreError("configuración debe ser objeto JSON")
    required = {"schema_version", "connection_id", "protocol", "mode_id", "transport", "security", "listen_address", "listen_port", "transport_options", "security_options"}
    if set(config) != required: raise StoreError("campos ausentes o no permitidos en configuración")
    cid = safe_id(config["connection_id"])
    if config["schema_version"] != 1 or isinstance(config["schema_version"], bool): raise StoreError("versión de esquema desconocida")
    mode = config["mode_id"]
    if cid != connection["id"] or config["protocol"] != "vless" or connection.get("protocol_id") != mode:
        raise StoreError("identidad o modalidad no coincide con catálogo")
    if mode not in MODES or (config["transport"], config["security"]) != MODES[mode]:
        raise StoreError("combinación de transporte/seguridad no admitida")
    addr, port = config["listen_address"], config["listen_port"]
    if not isinstance(addr, str) or not addr or len(addr) > 255 or any(c.isspace() for c in addr):
        raise StoreError("dirección de escucha inválida")
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise StoreError("puerto de escucha inválido")
    if port != connection.get("port"): raise StoreError("puerto no coincide con borrador")
    if not isinstance(config["transport_options"], dict) or not isinstance(config["security_options"], dict):
        raise StoreError("opciones deben ser objetos JSON")
    sec = config["security_options"]
    if not isinstance(sec, dict): raise StoreError("opciones de seguridad deben ser objeto JSON")
    t = config["transport_options"]
    if mode in ("vless_ws", "vless_ws_tls"):
        if set(t) != {"path"} or not isinstance(t["path"], str) or not t["path"].startswith("/"):
            raise StoreError("opciones WebSocket inválidas")
    elif mode.startswith("vless_xhttp"):
        if set(t) != {"path", "mode"} or not isinstance(t["path"], str) or not t["path"].startswith("/") or t["mode"] not in ("auto", "packet-up", "stream-up", "stream-one"):
            raise StoreError("opciones XHTTP inválidas")
    elif mode.startswith("vless_grpc"):
        if set(t) != {"service_name"} or not isinstance(t["service_name"], str) or not t["service_name"]:
            raise StoreError("opciones gRPC inválidas")
    elif t:
        raise StoreError("esta modalidad no admite opciones de transporte")
    if security := MODES[mode][1]:
        if security == "tls":
            if set(sec) != {"certificate_file", "key_file"}: raise StoreError("TLS requiere referencias de certificado y clave")
            for field in ("certificate_file", "key_file"):
                value = sec[field]
                if not isinstance(value, str) or not value.startswith("/") or len(value) > 4096:
                    raise StoreError("referencia TLS debe ser una ruta absoluta")
        elif security == "reality":
            if set(sec) != {"target", "server_names", "short_ids"}: raise StoreError("REALITY requiere metadatos públicos; la clave privada se integra en P3")
            if not isinstance(sec["target"], str) or not sec["target"] or len(sec["target"]) > 255:
                raise StoreError("target REALITY inválido")
            if not isinstance(sec["server_names"], list) or not sec["server_names"] or not all(isinstance(x, str) and x for x in sec["server_names"]):
                raise StoreError("server names REALITY inválidos")
            if not isinstance(sec["short_ids"], list) or not all(isinstance(x, str) and re.fullmatch(r"[0-9a-fA-F]{0,16}", x) for x in sec["short_ids"]):
                raise StoreError("short IDs REALITY inválidos")
        elif sec:
            raise StoreError("esta modalidad no admite opciones de seguridad")
    elif sec:
        raise StoreError("esta modalidad sin TLS/REALITY no admite opciones de seguridad")
    return config

def run(args: argparse.Namespace) -> dict:
    if os.geteuid() != 0: raise StoreError("el almacén requiere root")
    base = Path(args.base).absolute(); cat = Path(args.catalog).absolute(); lock = Path(args.lock).absolute()
    configs = base / "configurations"
    check_dir(base); check_dir(configs, create=True)
    if cat.is_symlink() or lock.is_symlink(): raise StoreError("symlink en catálogo o bloqueo")
    lock.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(lock, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        os.fchmod(fd, 0o600); fcntl.flock(fd, fcntl.LOCK_EX)
        raw = read_regular(cat, 4 * 1024 * 1024)
        catalog = json.loads(raw)
        if not isinstance(catalog, list): raise StoreError("catálogo no es arreglo JSON")
        ids = [x.get("id") for x in catalog if isinstance(x, dict)]
        if len(ids) != len(catalog) or len(ids) != len(set(ids)): raise StoreError("catálogo contiene registros inválidos o IDs duplicados")
        if args.action == "store":
            cid = safe_id(args.connection_id)
            matches = [x for x in catalog if x.get("id") == cid]
            if len(matches) != 1: raise StoreError("conexión no existe")
            entry = matches[0]
            if entry.get("state") != "draft" or entry.get("runtime_applied") is not False:
                raise StoreError("solo se pueden guardar borradores no aplicados")
            config = json.loads(read_regular(Path(args.input), MAX_CONFIG))
            validate_config(config, entry)
            current = entry.get("configuration_revision", 0)
            if isinstance(current, bool) or not isinstance(current, int) or current < 0: raise StoreError("revisión de catálogo inválida")
            revision = current + 1
            filename = f"{cid}.r{revision:06d}.json"
            destination = configs / filename
            if destination.exists() or destination.is_symlink(): raise StoreError("colisión de revisión; no se sobrescribe")
            payload = (json.dumps(config, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
            atomic_write(destination, payload)
            # Verificar el artefacto durable antes de publicar su referencia.
            if read_regular(destination, MAX_CONFIG) != payload:
                destination.unlink(missing_ok=True)
                raise StoreError("falló la verificación posterior a escritura")
            entry["configuration_schema_version"] = 1
            entry["configuration_revision"] = revision
            entry["configuration_ref"] = f"configurations/{filename}"
            entry.setdefault("secret_ref", None)
            updated = (json.dumps(catalog, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
            atomic_write(cat, updated)
            return {"status": "stored", "connection_id": cid, "revision": revision, "configuration_ref": entry["configuration_ref"], "state": "draft", "runtime_applied": False}
        if args.action == "read":
            cid = safe_id(args.connection_id)
            matches = [x for x in catalog if x.get("id") == cid]
            if len(matches) != 1: raise StoreError("conexión no existe")
            ref = matches[0].get("configuration_ref")
            expected = re.fullmatch(rf"configurations/{re.escape(cid)}\.r([0-9]{{6}})\.json", ref or "")
            if not expected: raise StoreError("referencia de configuración inválida")
            data = read_regular(configs / f"{cid}.r{int(expected.group(1)):06d}.json", MAX_CONFIG)
            config = json.loads(data)
            validate_config(config, matches[0])
            return {"status": "ok", "configuration": config}
        if args.action == "audit":
            referenced, broken = set(), []
            for entry in catalog:
                ref = entry.get("configuration_ref")
                if ref is None: continue
                cid = safe_id(entry.get("id"))
                match = re.fullmatch(rf"configurations/{re.escape(cid)}\.r([0-9]{{6}})\.json", ref if isinstance(ref, str) else "")
                if not match: broken.append({"id": cid, "issue": "invalid_reference"}); continue
                filename = f"{cid}.r{int(match.group(1)):06d}.json"; referenced.add(filename)
                try:
                    config = json.loads(read_regular(configs / filename, MAX_CONFIG)); validate_config(config, entry)
                except Exception: broken.append({"id": cid, "issue": "missing_or_invalid_reference"})
            orphans = sorted(p.name for p in configs.iterdir() if p.is_file() and not p.is_symlink() and p.name.endswith(".json") and p.name not in referenced)
            return {"status": "audit", "broken_references": broken, "orphan_files": orphans, "automatic_deletion": False}
        raise StoreError("acción desconocida")
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN); os.close(fd)

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=("store", "read", "audit"))
    p.add_argument("--base", default="/var/lib/xray-manager/connections")
    p.add_argument("--catalog", default="/var/lib/xray-manager/connections/connections.json")
    p.add_argument("--lock", default="/run/xray-manager/integrity.lock")
    p.add_argument("--connection-id")
    p.add_argument("--input")
    a = p.parse_args()
    if a.action in ("store", "read") and not a.connection_id: p.error("--connection-id requerido")
    if a.action == "store" and not a.input: p.error("--input requerido")
    try: print(json.dumps(run(a), ensure_ascii=False, separators=(",", ":"))); return 0
    except (StoreError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr); return 1

if __name__ == "__main__": raise SystemExit(main())
