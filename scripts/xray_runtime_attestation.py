from __future__ import annotations
"""Persistent Xray generation attestation; no service actions are performed."""
import fcntl, hashlib, json, os, re, secrets, stat
from datetime import datetime, timezone
from pathlib import Path

OP_RE = re.compile(r"runtime-op-[0-9a-f]{32}\Z")
GEN_RE = re.compile(r"generation-[0-9a-f]{32}\Z")
SHA_RE = re.compile(r"[0-9a-f]{64}\Z")
INV_RE = re.compile(r"[0-9a-fA-F]{32}\Z")
DEFAULT_ROOT = Path("/var/lib/xray-manager/attestations")
MAX_BYTES = 16384
FIELDS = {"schema_version","operation_id","generation_id","config_sha256","invocation_id",
          "active_enter_timestamp","unit_fragment_sha256","attested_at","service_unit"}

class AttestationError(Exception):
    pass

def fail(message):
    raise AttestationError(message)

def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")

def strict_json(data):
    def pairs(items):
        result = {}
        for k,v in items:
            if k in result: raise ValueError("duplicate")
            result[k] = v
        return result
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError("constant")))
    except (UnicodeError, ValueError, json.JSONDecodeError):
        fail("La atestación no contiene JSON estricto.")
    if not isinstance(value, dict): fail("La atestación debe ser un objeto JSON.")
    return value

def validate(value):
    if set(value) != FIELDS or type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        fail("Esquema de atestación inválido.")
    if not isinstance(value["operation_id"],str) or not OP_RE.fullmatch(value["operation_id"]): fail("operation_id inválido.")
    if not isinstance(value["generation_id"],str) or not GEN_RE.fullmatch(value["generation_id"]): fail("generation_id inválido.")
    for key in ("config_sha256","unit_fragment_sha256"):
        if not isinstance(value[key],str) or not SHA_RE.fullmatch(value[key]): fail(key+" inválido.")
    if not isinstance(value["invocation_id"],str) or not INV_RE.fullmatch(value["invocation_id"]): fail("InvocationID inválido.")
    if value["service_unit"] != "xray.service": fail("Unidad no permitida.")
    for key in ("active_enter_timestamp","attested_at"):
        if not isinstance(value[key],str) or not value[key].strip(): fail(key+" ausente.")
    try: parsed = datetime.fromisoformat(value["attested_at"].replace("Z","+00:00"))
    except ValueError: fail("Fecha de atestación inválida.")
    if parsed.tzinfo is None: fail("La fecha de atestación debe incluir zona horaria.")
    return value

def check_components(path):
    if not path.is_absolute(): fail("La ruta debe ser absoluta.")
    current = Path("/")
    for part in path.parts[1:]:
        current /= part
        try: info = current.lstat()
        except FileNotFoundError: continue
        if stat.S_ISLNK(info.st_mode): fail("Ruta con symlink no permitida.")

def unit_hash(path):
    check_components(path.parent)
    try: fd = os.open(path,os.O_RDONLY|getattr(os,"O_NOFOLLOW",0)|getattr(os,"O_CLOEXEC",0))
    except OSError: fail("No se pudo abrir la unidad administrada.")
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_gid != 0 or st.st_nlink != 1 or stat.S_IMODE(st.st_mode) != 0o644 or not 0 < st.st_size <= 1048576:
            fail("Unidad con tipo, propietario, enlaces, permisos o tamaño inseguros.")
        digest = hashlib.sha256(); total = 0
        while True:
            block = os.read(fd,65536)
            if not block: break
            total += len(block)
            if total > 1048576: fail("Unidad demasiado grande.")
            digest.update(block)
        if total != st.st_size: fail("La unidad cambió durante su lectura.")
        return digest.hexdigest()
    finally: os.close(fd)

def valid_observation(value, expected_hash, unit_path):
    expected = {"load_state":"loaded","active_state":"active","sub_state":"running","result":"success",
                "exec_main_status":"0","user":"xray","group":"xray","fragment_path":unit_path,
                "runtime_config_sha256":expected_hash}
    for key,wanted in expected.items():
        if value.get(key) != wanted: fail("Observación no verificable: "+key+".")
    if type(value.get("main_pid")) is not int or value["main_pid"] <= 0: fail("MainPID inválido.")
    if not isinstance(value.get("invocation_id"),str) or not INV_RE.fullmatch(value["invocation_id"]): fail("InvocationID inválido.")
    ts = value.get("active_enter_timestamp")
    if not isinstance(ts,str) or not ts.strip() or ts in {"n/a","0"}: fail("ActiveEnterTimestamp inválido.")

def build_attestation(operation,before,after,confirmed,unit_file):
    if not isinstance(operation,dict): fail("Falta journal R-05.")
    op_id = operation.get("operation_id"); orch = operation.get("orchestration"); pub = operation.get("publication")
    if not isinstance(op_id,str) or not OP_RE.fullmatch(op_id) or not isinstance(orch,dict) or not isinstance(pub,dict):
        fail("Identidad o metadatos R-05 inválidos.")
    req = orch.get("request"); gen = orch.get("generation_id"); config_hash = pub.get("config_sha256")
    if not isinstance(req,dict): fail("Falta solicitud R-05.")
    action = req.get("action")
    expected_state = "service_start_requested" if action == "start" else "service_restart_requested"
    expected_phase = "start_requested" if action == "start" else "restart_requested"
    if (operation.get("state") != expected_state or orch.get("phase") != expected_phase
        or orch.get("confirmation") != "accepted" or action not in {"start","restart"}
        or req.get("generation_id") != gen or req.get("result") != "accepted"
        or not isinstance(req.get("requested_at"),str) or pub.get("status") != "published"):
        fail("La operación no es una petición start/restart aceptada y publicada.")
    if not isinstance(gen,str) or not GEN_RE.fullmatch(gen) or not isinstance(config_hash,str) or not SHA_RE.fullmatch(config_hash):
        fail("generation_id o SHA-256 publicado inválido.")
    initial = orch.get("initial_service")
    if not isinstance(initial,dict): fail("Falta snapshot inicial.")
    if action == "start":
        prev_invocation = before.get("invocation_id")
        if (initial.get("active_state") != "inactive" or before.get("active_state") != "inactive"
            or (prev_invocation not in (None,"") and (not isinstance(prev_invocation,str) or not INV_RE.fullmatch(prev_invocation)))):
            fail("start requiere estado inicial inactive y, si existe, InvocationID previo válido.")
    else:
        old = before.get("invocation_id")
        if initial.get("active_state") != "active" or not isinstance(old,str) or not INV_RE.fullmatch(old):
            fail("restart requiere InvocationID previo válido y servicio active.")
    unit_file = Path(unit_file)
    if not unit_file.is_absolute(): fail("Ruta de unidad no absoluta.")
    unit_path = str(unit_file); digest = unit_hash(unit_file)
    if before.get("runtime_config_sha256") != config_hash or before.get("fragment_path") != unit_path:
        fail("Hash/unidad previos no coinciden con la publicación.")
    valid_observation(after,config_hash,unit_path)
    valid_observation(confirmed,config_hash,unit_path)
    if after["invocation_id"] != confirmed["invocation_id"] or after["active_enter_timestamp"] != confirmed["active_enter_timestamp"]:
        fail("La invocación o ActiveEnterTimestamp no permanecen estables.")
    if after["invocation_id"] == before.get("invocation_id"):
        fail("La transición no produjo una nueva invocación systemd.")
    record = {"schema_version":1,"operation_id":op_id,"generation_id":gen,"config_sha256":config_hash,
              "invocation_id":after["invocation_id"].lower(),"active_enter_timestamp":after["active_enter_timestamp"],
              "unit_fragment_sha256":digest,"attested_at":now(),"service_unit":"xray.service"}
    return validate(record)

class AttestationStore:
    """Append-only por operation_id; almacén root-only separado del fixture B4."""
    def __init__(self,root=DEFAULT_ROOT):
        self.root = Path(root); self.lock_path = self.root/".attestation.lock"
    def lock(self):
        check_components(self.root)
        try: st = self.root.lstat()
        except OSError: fail("El directorio de atestaciones debe existir previamente.")
        if not stat.S_ISDIR(st.st_mode) or st.st_uid != 0 or st.st_gid != 0 or stat.S_IMODE(st.st_mode) != 0o700:
            fail("Almacén debe ser directorio root:root 0700.")
        try: fd = os.open(self.lock_path,os.O_RDWR|os.O_CREAT|getattr(os,"O_NOFOLLOW",0),0o600)
        except OSError: fail("No se pudo abrir lock de atestaciones.")
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_gid != 0 or st.st_nlink != 1 or stat.S_IMODE(st.st_mode) != 0o600:
            os.close(fd); fail("Lock de atestaciones inseguro.")
        try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: os.close(fd); fail("Almacén de atestaciones ocupado.")
        cur = self.lock_path.lstat()
        if (cur.st_dev,cur.st_ino) != (st.st_dev,st.st_ino):
            fcntl.flock(fd,fcntl.LOCK_UN); os.close(fd); fail("Identidad del lock cambió.")
        return fd
    @staticmethod
    def release(fd):
        try: fcntl.flock(fd,fcntl.LOCK_UN)
        finally: os.close(fd)
    def read(self,operation_id):
        if not isinstance(operation_id,str) or not OP_RE.fullmatch(operation_id): fail("operation_id inválido.")
        fd = self.lock()
        try:
            path = self.root/(operation_id+".json")
            if not path.exists() and not path.is_symlink(): return None
            try: f = os.open(path,os.O_RDONLY|getattr(os,"O_NOFOLLOW",0))
            except OSError: fail("No se pudo leer atestación.")
            try:
                st = os.fstat(f)
                if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_gid != 0 or st.st_nlink != 1 or stat.S_IMODE(st.st_mode) != 0o600 or not 0 < st.st_size <= MAX_BYTES:
                    fail("Archivo de atestación inseguro.")
                data = os.read(f,MAX_BYTES+1)
                if len(data) != st.st_size: fail("Atestación cambió durante lectura.")
            finally: os.close(f)
            value = validate(strict_json(data))
            if value["operation_id"] != operation_id: fail("Nombre e identidad de atestación no coinciden.")
            return dict(value)
        finally: self.release(fd)
    def record(self,operation,before,after,confirmed,unit_file):
        value = build_attestation(operation,before,after,confirmed,unit_file)
        fd = self.lock()
        try:
            path = self.root/(value["operation_id"]+".json")
            if path.exists() or path.is_symlink():
                current = self.read_unlocked(path)
                if {k:v for k,v in current.items() if k != "attested_at"} == {k:v for k,v in value.items() if k != "attested_at"}: return {"status":"ALREADY_RECORDED","attestation":dict(current)}
                fail("Atestación existente distinta; no se sobrescribe.")
            temp = self.root/(".tmp-"+secrets.token_hex(16))
            out = os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,"O_NOFOLLOW",0),0o600)
            try:
                os.fchown(out,0,0); os.fchmod(out,0o600)
                data = json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()+b"\n"
                view = memoryview(data)
                while view:
                    n = os.write(out,view)
                    if n <= 0: fail("Escritura incompleta.")
                    view = view[n:]
                os.fsync(out)
            finally: os.close(out)
            try: os.link(temp,path,follow_symlinks=False)
            except FileExistsError: fail("Atestación concurrente detectada.")
            finally:
                try: temp.unlink()
                except FileNotFoundError: pass
            dfd = os.open(self.root,os.O_RDONLY|getattr(os,"O_DIRECTORY",0))
            try: os.fsync(dfd)
            finally: os.close(dfd)
            return {"status":"ATTESTED","attestation":dict(value)}
        finally: self.release(fd)
    @staticmethod
    def read_unlocked(path):
        fd = os.open(path,os.O_RDONLY|getattr(os,"O_NOFOLLOW",0))
        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_gid != 0 or st.st_nlink != 1 or stat.S_IMODE(st.st_mode) != 0o600 or not 0 < st.st_size <= MAX_BYTES:
                fail("Atestación persistida insegura.")
            data = os.read(fd,MAX_BYTES+1)
            if len(data) != st.st_size: fail("Atestación cambió durante lectura.")
        finally: os.close(fd)
        return validate(strict_json(data))
