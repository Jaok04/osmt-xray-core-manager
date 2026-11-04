#!/usr/bin/env python3
"""Almacén independiente, versionado y cifrado de configuraciones JSON Xray."""
from __future__ import annotations
import argparse, base64, binascii, contextlib, datetime as dt, fcntl, hashlib, json, os, pathlib, re, secrets, shutil, stat, sys
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from certificate_crypto import CertificateCryptoError, load_master_key

DEFAULT_STORE = "/var/lib/xray-manager/configurations"
DEFAULT_MASTER_KEY = "/etc/xray-manager/keys/master.key"
MAX_CONFIG = 16 * 1024 * 1024
MAX_BLOB = 24 * 1024 * 1024
MAX_CATALOG = 10000
VERSION = 1
NONCE_BYTES = 12
ID_RE = re.compile(r"config-[0-9a-f]{32}\Z")
REV_RE = re.compile(r"r[0-9]{6}\Z")
NAME_RE = re.compile(r"[^\w .()\-]", re.UNICODE)

class ConfigurationError(Exception): pass

def fail(message): raise ConfigurationError(message)
def now(): return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
def json_bytes(value): return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
def strict_json(data, label):
    try:
        def pairs(items):
            out = {}
            for key, value in items:
                if key in out: fail(f"{label}: clave duplicada: {key}")
                out[key] = value
            return out
        return json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=lambda x: fail(f"{label}: constante no válida"))
    except (UnicodeError, json.JSONDecodeError) as exc: fail(f"{label}: JSON inválido: {exc}")

def safe_components(path):
    if not path.is_absolute(): fail("La ruta debe ser absoluta.")
    cur = pathlib.Path("/")
    for part in path.parts[1:]:
        cur /= part
        try: info = cur.lstat()
        except FileNotFoundError: continue
        if stat.S_ISLNK(info.st_mode): fail(f"Componente simbólico no permitido: {cur}")

def check_dir(path, create=False):
    safe_components(path)
    if create: path.mkdir(mode=0o700, parents=True, exist_ok=True)
    try: st = path.lstat()
    except FileNotFoundError: fail(f"Falta directorio: {path}")
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != 0 or st.st_gid != 0 or stat.S_IMODE(st.st_mode) != 0o700:
        fail(f"Directorio inseguro (se conserva sin reparar): {path}")

def check_file(path, limit=4*1024*1024, required=True):
    try: st = path.lstat()
    except FileNotFoundError:
        if required: fail(f"Falta archivo: {path.name}")
        return None
    if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_gid != 0 or st.st_nlink != 1 or stat.S_IMODE(st.st_mode) != 0o600 or st.st_size > limit:
        fail(f"Archivo inseguro o fuera de límite: {path}")
    return st

def read_file(path, limit=4*1024*1024):
    st = check_file(path, limit)
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        opened = os.fstat(fd)
        if (opened.st_dev, opened.st_ino, opened.st_uid, opened.st_gid, opened.st_nlink, opened.st_size) != (st.st_dev, st.st_ino, st.st_uid, st.st_gid, st.st_nlink, st.st_size): fail("El archivo cambió durante su apertura.")
        data = bytearray()
        while True:
            block = os.read(fd, min(1024*1024, limit+1-len(data)))
            if not block: break
            data.extend(block)
            if len(data) > limit: fail("Archivo excede el límite permitido.")
        return bytes(data)
    finally: os.close(fd)

def fsync_dir(path):
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try: os.fsync(fd)
    finally: os.close(fd)

def atomic_write(path, data):
    check_dir(path.parent)
    if path.exists() or path.is_symlink(): check_file(path, max(len(data), 4*1024*1024))
    temp = path.parent / f".{path.name}.{secrets.token_hex(8)}.tmp"
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        os.fchown(fd, 0, 0); os.fchmod(fd, 0o600)
        view = memoryview(data)
        while view:
            n = os.write(fd, view)
            if n <= 0: raise OSError("Escritura incompleta")
            view = view[n:]
        os.fsync(fd)
    except Exception:
        os.close(fd)
        with contextlib.suppress(OSError): temp.unlink()
        raise
    else: os.close(fd)
    try:
        os.replace(temp, path); fsync_dir(path.parent)
    finally:
        with contextlib.suppress(FileNotFoundError): temp.unlink()

def normalize_name(value):
    if not isinstance(value, str): fail("Nombre no válido.")
    value = " ".join(value.strip().split())
    if not value or len(value) > 80 or any(not c.isprintable() for c in value) or NAME_RE.search(value): fail("Nombre vacío o con caracteres no permitidos (máximo 80).")
    return value

class ConfigurationStore:
    def __init__(self, store=None, master_key=None):
        self.root = pathlib.Path(store or os.environ.get("XRAY_MANAGER_CONFIGURATIONS_DIR", DEFAULT_STORE)).absolute()
        self.key_path = pathlib.Path(master_key or os.environ.get("XRAY_MANAGER_MASTER_KEY_FILE", DEFAULT_MASTER_KEY)).absolute()
        self.items = self.root / "items"
        self.catalog_path = self.root / "catalog.json"
        self.lock_path = self.root / ".configurations.lock"
        self.wal_path = self.root / ".configurations.transaction.json"
        self._key = None

    def key(self):
        if self._key is None:
            try: self._key = load_master_key(self.key_path)
            except CertificateCryptoError as exc: fail(f"No se pudo cargar la clave maestra existente: {exc}")
        return self._key

    def aad(self, cid, rev):
        if not ID_RE.fullmatch(cid) or not REV_RE.fullmatch(rev): fail("ID/revisión inválidos para AAD.")
        return f"xray-manager:independent-config:v{VERSION}:{cid}:{rev}".encode()

    def encrypt(self, plain, cid, rev):
        if not isinstance(plain, bytes) or len(plain) > MAX_CONFIG: fail("Contenido superior a 16 MiB.")
        nonce = secrets.token_bytes(NONCE_BYTES)
        ct = AESGCM(self.key()).encrypt(nonce, plain, self.aad(cid, rev))
        return json_bytes({"format_version": VERSION, "algorithm": "AES-256-GCM", "config_id": cid, "revision": rev, "nonce": base64.b64encode(nonce).decode(), "ciphertext": base64.b64encode(ct).decode()})

    def decrypt(self, blob, cid, rev):
        if not 1 <= len(blob) <= MAX_BLOB: fail("Blob cifrado vacío o demasiado grande.")
        try:
            e = strict_json(blob, "Sobre cifrado")
            if not isinstance(e, dict) or set(e) != {"format_version", "algorithm", "config_id", "revision", "nonce", "ciphertext"}: raise ValueError()
            if type(e["format_version"]) is not int or e["format_version"] != VERSION or e["algorithm"] != "AES-256-GCM" or e["config_id"] != cid or e["revision"] != rev: raise ValueError()
            nonce = base64.b64decode(e["nonce"], validate=True); ct = base64.b64decode(e["ciphertext"], validate=True)
            if len(nonce) != NONCE_BYTES or len(ct) < 16: raise ValueError()
            plain = AESGCM(self.key()).decrypt(nonce, ct, self.aad(cid, rev))
        except (ValueError, TypeError, KeyError, binascii.Error, InvalidTag, UnicodeError, json.JSONDecodeError): fail("No se pudo autenticar o descifrar la configuración.")
        if len(plain) > MAX_CONFIG: fail("Contenido descifrado fuera de límite.")
        return plain

    def prepare(self):
        if os.geteuid() != 0: fail("El almacén requiere ejecución como root.")
        check_dir(self.root, True)
        if not self.items.exists(): self.items.mkdir(mode=0o700)
        check_dir(self.items)
        if not self.lock_path.exists() and not self.lock_path.is_symlink():
            fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
            os.fchown(fd, 0, 0); os.fchmod(fd, 0o600); os.fsync(fd); os.close(fd); fsync_dir(self.root)
        check_file(self.lock_path, 0)

    @contextlib.contextmanager
    def locked(self):
        self.prepare(); fd = os.open(self.lock_path, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_gid != 0 or st.st_nlink != 1 or stat.S_IMODE(st.st_mode) != 0o600: fail("Lock inseguro.")
            fcntl.flock(fd, fcntl.LOCK_EX); self.recover()
            yield
        finally:
            with contextlib.suppress(OSError): fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def rel(self, path):
        try: rel = path.relative_to(self.root).as_posix()
        except ValueError: fail("Ruta fuera del almacén.")
        return rel

    def resolve(self, rel):
        p = pathlib.PurePosixPath(rel)
        if p.is_absolute() or ".." in p.parts or not p.parts: fail("Ruta WAL inválida.")
        return self.root.joinpath(*p.parts)

    def recover(self):
        if not self.wal_path.exists() and not self.wal_path.is_symlink(): return
        journal = strict_json(read_file(self.wal_path, 32*1024*1024), "Journal")
        if (not isinstance(journal, dict) or set(journal) != {"schema_version", "changes", "remove_dirs"}
                or type(journal["schema_version"]) is not int or journal["schema_version"] != 1
                or not isinstance(journal["changes"], list) or not 1 <= len(journal["changes"]) <= 2
                or not isinstance(journal["remove_dirs"], list) or len(journal["remove_dirs"]) > 2):
            fail("Journal inválido; se conserva para inspección.")
        changes = []
        seen_targets = set()
        allowed = re.compile(r"(?:catalog\.json|items/config-[0-9a-f]{32}/metadata\.json)\Z")
        for item in journal["changes"]:
            if (not isinstance(item, dict) or set(item) != {"path", "old"}
                    or not isinstance(item["path"], str) or not allowed.fullmatch(item["path"])
                    or item["path"] in seen_targets): fail("Destino no permitido o duplicado en journal.")
            seen_targets.add(item["path"])
            old = item["old"]
            if old is not None:
                if not isinstance(old, str): fail("Snapshot WAL inválido.")
                try: old = base64.b64decode(old, validate=True)
                except binascii.Error: fail("Snapshot WAL corrupto.")
                if len(old) > 4 * 1024 * 1024: fail("Snapshot WAL excede el límite.")
            changes.append((self.resolve(item["path"]), old))
        dirs = []
        seen_dirs = set()
        for rel in journal["remove_dirs"]:
            if (not isinstance(rel, str) or rel in seen_dirs
                    or not (re.fullmatch(r"items/config-[0-9a-f]{32}", rel) or re.fullmatch(r"items/\.stage-[0-9a-f]{16}", rel))): fail("Directorio WAL no permitido o duplicado.")
            seen_dirs.add(rel)
            dirs.append(self.resolve(rel))
        if any(target == directory or directory in target.parents for target, _ in changes for directory in dirs): fail("Journal contiene destinos solapados con directorios de rollback.")
        for target, old in changes:
            if old is None:
                if target.exists() or target.is_symlink():
                    check_file(target, 32*1024*1024); target.unlink(); fsync_dir(target.parent)
            else: atomic_write(target, old)
        for directory in dirs:
            if directory.exists():
                check_dir(directory); shutil.rmtree(directory); fsync_dir(directory.parent)
        self.wal_path.unlink(); fsync_dir(self.root)

    def transact(self, changes, remove_dirs=(), publish_dirs=()):
        if self.wal_path.exists() or self.wal_path.is_symlink(): fail("Hay una transacción pendiente.")
        entries = []
        for target, new in changes.items():
            rel = self.rel(target)
            if rel != "catalog.json" and not re.fullmatch(r"items/config-[0-9a-f]{32}/metadata\.json", rel): fail("Destino transaccional no permitido.")
            old = base64.b64encode(read_file(target, 4*1024*1024)).decode() if target.exists() else None
            entries.append({"path": rel, "old": old, "new": base64.b64encode(new).decode()})
        removals = [self.rel(x) for x in remove_dirs]
        for rel in removals:
            if not (re.fullmatch(r"items/config-[0-9a-f]{32}", rel) or re.fullmatch(r"items/\.stage-[0-9a-f]{16}", rel)): fail("Rollback fuera de alcance.")
        publications = []
        for source, destination in publish_dirs:
            source_rel, destination_rel = self.rel(source), self.rel(destination)
            if not re.fullmatch(r"items/\.stage-[0-9a-f]{16}", source_rel) or not re.fullmatch(r"items/config-[0-9a-f]{32}", destination_rel): fail("Publicación de directorio fuera de alcance.")
            check_dir(source)
            if destination.exists() or destination.is_symlink(): fail("El destino de publicación ya existe.")
            publications.append((source, destination))
        journal = {"schema_version": 1, "changes": [{"path": x["path"], "old": x["old"]} for x in entries], "remove_dirs": removals}
        atomic_write(self.wal_path, json_bytes(journal))
        try:
            for source, destination in publications:
                os.rename(source, destination)
                fsync_dir(self.items)
            for entry in entries: atomic_write(self.resolve(entry["path"]), base64.b64decode(entry["new"], validate=True))
        except Exception:
            self.recover(); raise
        try: self.wal_path.unlink(); fsync_dir(self.root)
        except Exception:
            if not self.wal_path.exists(): atomic_write(self.wal_path, json_bytes(journal))
            self.recover(); raise

    def load_catalog(self):
        if not self.catalog_path.exists(): return {"schema_version": 1, "configurations": []}
        value = strict_json(read_file(self.catalog_path), "Catálogo")
        if not isinstance(value, dict) or set(value) != {"schema_version", "configurations"} or type(value["schema_version"]) is not int or value["schema_version"] != 1 or not isinstance(value["configurations"], list) or len(value["configurations"]) > MAX_CATALOG: fail("Contrato de catálogo inválido.")
        ids, names = set(), set()
        for entry in value["configurations"]:
            if not isinstance(entry, dict) or set(entry) != {"config_id", "name", "created_at", "modified_at"}: fail("Registro de catálogo inválido.")
            cid = entry["config_id"]
            if not isinstance(cid, str) or not ID_RE.fullmatch(cid): fail("ID de catálogo inválido.")
            name = normalize_name(entry["name"])
            for field in ("created_at", "modified_at"):
                v = entry[field]
                if not isinstance(v, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", v): fail("Fecha de catálogo inválida.")
                try: dt.datetime.strptime(v, "%Y-%m-%dT%H:%M:%SZ")
                except ValueError: fail("Fecha inexistente en catálogo.")
            if entry["modified_at"] < entry["created_at"] or cid in ids or name.casefold() in names: fail("Duplicados o fechas incoherentes en catálogo.")
            ids.add(cid); names.add(name.casefold())
        return value

    def load_metadata(self, cid):
        if not isinstance(cid, str) or not ID_RE.fullmatch(cid): fail("ID de configuración inválido.")
        directory = self.items / cid; check_dir(directory)
        meta = strict_json(read_file(directory / "metadata.json"), "Metadatos")
        fields = {"schema_version", "config_id", "name", "created_at", "modified_at", "current_revision", "last_validated_revision", "validation_status", "config_present"}
        if not isinstance(meta, dict) or set(meta) != fields or type(meta["schema_version"]) is not int or meta["schema_version"] != 1 or meta["config_id"] != cid: fail("Contrato de metadatos inválido.")
        if normalize_name(meta["name"]) != meta["name"]: fail("Nombre de metadatos no normalizado.")
        parsed_dates = []
        for field in ("created_at", "modified_at"):
            if not isinstance(meta[field], str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", meta[field]): fail("Fecha de metadatos inválida.")
            try: parsed_dates.append(dt.datetime.strptime(meta[field], "%Y-%m-%dT%H:%M:%SZ"))
            except ValueError: fail("Fecha inexistente en metadatos.")
        if parsed_dates[1] < parsed_dates[0]: fail("modified_at es anterior a created_at.")
        rev = meta["current_revision"]
        if rev is not None and (not isinstance(rev, str) or not REV_RE.fullmatch(rev)): fail("Puntero de revisión inválido.")
        last = meta["last_validated_revision"]
        if last is not None and (not isinstance(last, str) or not REV_RE.fullmatch(last)): fail("Puntero validado inválido.")
        if type(meta["config_present"]) is not bool or meta["config_present"] != (rev is not None) or meta["validation_status"] != "not_validated" or last is not None: fail("Estado de metadatos incoherente para C-01.")
        return meta

    def verify_revision(self, cid, rev):
        if not isinstance(rev, str) or not REV_RE.fullmatch(rev): fail("Revisión inválida.")
        revdir = self.items / cid / "revisions" / rev; check_dir(revdir)
        if {entry.name for entry in revdir.iterdir()} != {"config.enc.json", "manifest.json"}: fail("Contenido de revisión inesperado.")
        blob = read_file(revdir / "config.enc.json", MAX_BLOB)
        manifest = strict_json(read_file(revdir / "manifest.json"), "Manifiesto")
        fields = {"schema_version", "config_id", "revision", "created_at", "config", "source", "validation"}
        cf = {"file", "plaintext_size_bytes", "stored_size_bytes", "ciphertext_sha256", "storage", "crypto_format_version"}
        if not isinstance(manifest, dict) or set(manifest) != fields or type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1 or manifest["config_id"] != cid or manifest["revision"] != rev: fail("Contrato de manifiesto inválido.")
        stamp = manifest["created_at"]
        if not isinstance(stamp, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", stamp): fail("Fecha de manifiesto inválida.")
        try: dt.datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError: fail("Fecha inexistente en manifiesto.")
        c = manifest["config"]
        if not isinstance(c, dict) or set(c) != cf or c["file"] != "config.enc.json" or c["storage"] != "aes-256-gcm" or type(c["crypto_format_version"]) is not int or c["crypto_format_version"] != 1 or type(c["plaintext_size_bytes"]) is not int or not 0 <= c["plaintext_size_bytes"] <= MAX_CONFIG or type(c["stored_size_bytes"]) is not int or c["stored_size_bytes"] != len(blob) or not isinstance(c["ciphertext_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", c["ciphertext_sha256"]): fail("Metadatos de contenido en manifiesto inválidos.")
        if hashlib.sha256(blob).hexdigest() != c["ciphertext_sha256"]: fail("Hash del ciphertext no coincide.")
        if manifest["source"] not in ("template_empty", "template_minimal", "import"): fail("Origen de revisión no permitido.")
        if manifest["validation"] != {"json_syntax": "not_run", "xray_static": "not_run", "status": "pending"}: fail("Estado de validación del manifiesto incoherente.")
        plain = self.decrypt(blob, cid, rev)
        if len(plain) != c["plaintext_size_bytes"]: fail("Tamaño de contenido no coincide.")
        return plain, manifest

    def _read_import_source(self, source):
        path = pathlib.Path(source)
        if not path.is_absolute(): fail("La ruta de importación debe ser absoluta.")
        safe_components(path)
        try: before = path.lstat()
        except OSError as exc: fail(f"No se puede inspeccionar el archivo de origen: {exc}")
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > MAX_CONFIG:
            fail("El origen debe ser archivo regular, sin hardlinks y de hasta 16 MiB.")
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
        try:
            opened = os.fstat(fd)
            identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns, before.st_nlink)
            current = (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns, opened.st_nlink)
            if not stat.S_ISREG(opened.st_mode) or current != identity: fail("El archivo de origen cambió antes de abrirse.")
            chunks = bytearray()
            while True:
                block = os.read(fd, min(1024 * 1024, MAX_CONFIG + 1 - len(chunks)))
                if not block: break
                chunks.extend(block)
                if len(chunks) > MAX_CONFIG: fail("El archivo de origen excede 16 MiB.")
            after = os.fstat(fd)
            final = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns, after.st_nlink)
            if final != current or len(chunks) != opened.st_size: fail("El archivo de origen cambió durante la lectura.")
            return path, bytes(chunks)
        finally: os.close(fd)

    def _summarize_import(self, path, data):
        try: decoded = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc: fail(f"El archivo no es UTF-8 válido; no se importó: {exc}")
        has_bom = data.startswith(b"\xef\xbb\xbf")
        parsed, json_valid, diagnostic = None, False, None
        if not data:
            diagnostic = "El archivo está vacío; se puede conservar como Borrador."
        else:
            try:
                parsed = strict_json(decoded.encode("utf-8"), "JSON importado")
                json_valid = True
                if not isinstance(parsed, dict): diagnostic = "La raíz JSON no es un objeto; se conservará como Borrador."
            except ConfigurationError as exc:
                diagnostic = str(exc)
        sections = [key for key in ("inbounds", "outbounds", "routing", "dns") if isinstance(parsed, dict) and key in parsed]
        return {"source": str(path), "source_name": path.name, "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "utf8_valid": True, "utf8_bom": has_bom, "json_valid": json_valid, "root_type": type(parsed).__name__ if parsed is not None else None, "sections_detected": sections, "diagnostic": diagnostic, "will_be_saved_as": "draft", "source_modified": False}

    def preview_import(self, source):
        path, data = self._read_import_source(source)
        return self._summarize_import(path, data)

    def _create_content(self, name, plain, source):
        name = normalize_name(name)
        if plain is not None and (not isinstance(plain, bytes) or len(plain) > MAX_CONFIG): fail("Contenido superior a 16 MiB.")
        if source not in ("template_empty", "template_minimal", "import"): fail("Origen de revisión no permitido.")
        with self.locked():
            catalog = self.load_catalog()
            if any(x["name"].casefold() == name.casefold() for x in catalog["configurations"]): fail("Ya existe una configuración con ese nombre; elige otro.")
            if len(catalog["configurations"]) >= MAX_CATALOG: fail("Catálogo lleno.")
            cid = "config-" + secrets.token_hex(16); created = now(); rev = "r000001" if plain is not None else None
            final = self.items / cid; stage = self.items / (".stage-" + secrets.token_hex(8))
            stage.mkdir(mode=0o700); os.chown(stage, 0, 0); os.chmod(stage, 0o700)
            try:
                if plain is not None:
                    revdir = stage / "revisions" / rev; revdir.mkdir(mode=0o700, parents=True); os.chown(stage / "revisions", 0, 0); os.chmod(stage / "revisions", 0o700); os.chown(revdir, 0, 0); os.chmod(revdir, 0o700)
                    blob = self.encrypt(plain, cid, rev); atomic_write(revdir / "config.enc.json", blob)
                    manifest = {"schema_version": 1, "config_id": cid, "revision": rev, "created_at": created, "config": {"file": "config.enc.json", "plaintext_size_bytes": len(plain), "stored_size_bytes": len(blob), "ciphertext_sha256": hashlib.sha256(blob).hexdigest(), "storage": "aes-256-gcm", "crypto_format_version": 1}, "source": source, "validation": {"json_syntax": "not_run", "xray_static": "not_run", "status": "pending"}}
                    atomic_write(revdir / "manifest.json", json_bytes(manifest)); fsync_dir(revdir); fsync_dir(revdir.parent)
                meta = {"schema_version": 1, "config_id": cid, "name": name, "created_at": created, "modified_at": created, "current_revision": rev, "last_validated_revision": None, "validation_status": "not_validated", "config_present": plain is not None}
                atomic_write(stage / "metadata.json", json_bytes(meta)); fsync_dir(stage)
                catalog["configurations"].append({"config_id": cid, "name": name, "created_at": created, "modified_at": created})
                self.transact({self.catalog_path: json_bytes(catalog)}, remove_dirs=[final, stage], publish_dirs=[(stage, final)])
            except Exception:
                if stage.exists():
                    shutil.rmtree(stage); fsync_dir(self.items)
                if final.exists() and not self.wal_path.exists():
                    check_dir(final)
                    expected = {"metadata.json"} if plain is None else {"metadata.json", "revisions"}
                    actual = {entry.name for entry in final.iterdir()}
                    if actual == expected:
                        check_file(final / "metadata.json")
                        if plain is not None:
                            check_dir(final / "revisions")
                            revdir = final / "revisions" / "r000001"
                            check_dir(revdir)
                            check_file(revdir / "config.enc.json", MAX_BLOB)
                            check_file(revdir / "manifest.json")
                        shutil.rmtree(final); fsync_dir(self.items)
                raise
            return self.show_unlocked(cid)

    def create(self, name, template="empty"):
        if template not in ("empty", "minimal"): fail("Plantilla no reconocida.")
        plain = None if template == "empty" else b'{"log":{"loglevel":"warning"}}\n'
        return self._create_content(name, plain, "template_empty" if plain is None else "template_minimal")

    def import_file(self, name, source, expected_sha256, accept_invalid=False):
        path, data = self._read_import_source(source)
        preview = self._summarize_import(path, data)
        if not isinstance(expected_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256) or preview["sha256"] != expected_sha256:
            fail("El SHA-256 del origen cambió desde la vista previa; vuelve a previsualizar.")
        if not preview["json_valid"] and not accept_invalid:
            fail("El archivo no es JSON válido; revisa la vista previa y confirma expresamente su conservación como Borrador con --accept-invalid.")
        result = self._create_content(name, data, "import")
        return {"preview": preview, "configuration": result, "imported_as": "draft", "source_modified": False}

    def export_file(self, cid, destination, revision=None, overwrite=False):
        if not isinstance(destination, str) or not destination: fail("Destino de exportación vacío.")
        target = pathlib.Path(destination)
        if not target.is_absolute() or target.name in ("", ".", ".."): fail("El destino debe ser una ruta absoluta a un archivo.")
        safe_components(target)
        parent = target.parent
        try: parent_stat = parent.lstat()
        except OSError as exc: fail(f"No existe el directorio de destino: {exc}")
        if not stat.S_ISDIR(parent_stat.st_mode): fail("El directorio de destino no es un directorio real.")
        with self.locked():
            meta = self.load_metadata(cid)
            if not any(x["config_id"] == cid and x["name"] == meta["name"] for x in self.load_catalog()["configurations"]): fail("Objeto no registrado en catálogo.")
            selected = revision or meta["current_revision"]
            if selected is None: fail("La configuración no tiene contenido para exportar.")
            plain, manifest = self.verify_revision(cid, selected)
        existing = None
        try: existing = target.lstat()
        except FileNotFoundError: pass
        if existing is not None:
            if not stat.S_ISREG(existing.st_mode) or existing.st_nlink != 1: fail("El destino existente debe ser archivo regular sin hardlinks.")
            if not overwrite: fail("El destino ya existe; confirma la sobrescritura explícitamente con --overwrite.")
        temp = parent / f".{target.name}.{secrets.token_hex(8)}.tmp"
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            os.fchown(fd, 0, 0); os.fchmod(fd, 0o600)
            view = memoryview(plain)
            while view:
                written = os.write(fd, view)
                if written <= 0: raise OSError("Escritura de exportación incompleta")
                view = view[written:]
            os.fsync(fd)
        except Exception:
            os.close(fd)
            with contextlib.suppress(OSError): temp.unlink()
            raise
        else: os.close(fd)
        try:
            try: current = target.lstat()
            except FileNotFoundError: current = None
            if existing is None:
                if current is not None: fail("El destino apareció durante la exportación; no se sobrescribió.")
                os.link(temp, target, follow_symlinks=False)
                temp.unlink()
            else:
                if current is None or (current.st_dev, current.st_ino) != (existing.st_dev, existing.st_ino): fail("El destino cambió durante la exportación; no se sobrescribió.")
                os.replace(temp, target)
            fsync_dir(parent)
            out_fd = os.open(target, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            try:
                out_stat = os.fstat(out_fd)
                if not stat.S_ISREG(out_stat.st_mode) or out_stat.st_nlink != 1 or stat.S_IMODE(out_stat.st_mode) != 0o600 or out_stat.st_uid != 0 or out_stat.st_gid != 0: fail("Los permisos del archivo exportado no son seguros.")
                exported = bytearray()
                while True:
                    block = os.read(out_fd, 1024 * 1024)
                    if not block: break
                    exported.extend(block)
            finally: os.close(out_fd)
            if bytes(exported) != plain: fail("La verificación byte a byte de la exportación falló.")
            return {"config_id": cid, "revision": selected, "destination": str(target), "size_bytes": len(plain), "sha256": hashlib.sha256(plain).hexdigest(), "verified_byte_for_byte": True, "mode": "0600", "plaintext_warning": "El archivo exportado está en claro y puede contener credenciales o claves."}
        finally:
            with contextlib.suppress(FileNotFoundError): temp.unlink()

    def show_unlocked(self, cid):
        meta = self.load_metadata(cid); catalog = self.load_catalog()
        if not any(x["config_id"] == cid and x["name"] == meta["name"] for x in catalog["configurations"]): fail("Objeto no registrado en catálogo.")
        summary = {"config_id": cid, **meta, "activation_status": "not_managed_by_independent_configurations"}
        if meta["current_revision"]:
            plain, manifest = self.verify_revision(cid, meta["current_revision"])
            summary["revision_manifest"] = manifest
            summary["content_size_bytes"] = len(plain)
        return summary

    def show(self, cid):
        with self.locked(): return self.show_unlocked(cid)

    def list(self):
        with self.locked():
            catalog = self.load_catalog(); result = []
            for item in catalog["configurations"]:
                meta = self.load_metadata(item["config_id"])
                if meta["name"] != item["name"]: fail("Nombre catálogo/metadatos no coincide.")
                if meta["current_revision"]: self.verify_revision(item["config_id"], meta["current_revision"])
                result.append({"config_id": item["config_id"], "name": meta["name"], "created_at": meta["created_at"], "modified_at": meta["modified_at"], "current_revision": meta["current_revision"], "validation_status": meta["validation_status"], "activation_status": "not_managed_by_independent_configurations"})
            return result

def build_parser():
    p = argparse.ArgumentParser(description="Gestor de configuraciones Xray independientes.")
    p.add_argument("--store"); p.add_argument("--master-key")
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("create"); c.add_argument("--name", required=True); c.add_argument("--template", choices=("empty", "minimal"), default="empty")
    sub.add_parser("list")
    s = sub.add_parser("show"); s.add_argument("--config-id", required=True)
    pi = sub.add_parser("preview-import"); pi.add_argument("--source", required=True)
    im = sub.add_parser("import"); im.add_argument("--source", required=True); im.add_argument("--name", required=True); im.add_argument("--expected-sha256", required=True); im.add_argument("--confirm", action="store_true"); im.add_argument("--accept-invalid", action="store_true")
    ex = sub.add_parser("export"); ex.add_argument("--config-id", required=True); ex.add_argument("--revision"); ex.add_argument("--destination", required=True); ex.add_argument("--overwrite", action="store_true")
    return p

def main():
    args = build_parser().parse_args()
    try:
        store = ConfigurationStore(args.store, args.master_key)
        if args.command == "create": result = store.create(args.name, args.template)
        elif args.command == "list": result = store.list()
        elif args.command == "show": result = store.show(args.config_id)
        elif args.command == "preview-import": result = store.preview_import(args.source)
        elif args.command == "import":
            if not args.confirm: fail("La importación requiere --confirm después de revisar preview-import.")
            result = store.import_file(args.name, args.source, args.expected_sha256, args.accept_invalid)
        else: result = store.export_file(args.config_id, args.destination, args.revision, args.overwrite)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True)); return 0
    except (ConfigurationError, OSError, ValueError, CertificateCryptoError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr); return 1

if __name__ == "__main__": raise SystemExit(main())
