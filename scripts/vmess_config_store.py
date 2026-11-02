#!/usr/bin/env python3
"""Almacén VMess versionado, fail-closed y cifrado con AES-256-GCM."""
from __future__ import annotations
import argparse, base64, fcntl, json, os, re, secrets, stat, sys, tempfile
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ID_RE=re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
MODES={
 "vmess_ws":("websocket","none"),"vmess_tcp_tls":("raw","tls"),"vmess_ws_tls":("websocket","tls"),
 "vmess_reality":("raw","reality"),"vmess_grpc":("grpc","none"),"vmess_grpc_tls":("grpc","tls"),
 "vmess_grpc_reality":("grpc","reality"),"vmess_httpupgrade":("httpupgrade","none"),
 "vmess_httpupgrade_tls":("httpupgrade","tls"),"vmess_xhttp":("xhttp","none"),
 "vmess_xhttp_tls":("xhttp","tls"),"vmess_xhttp_reality":("xhttp","reality"),
 "vmess_mkcp":("mkcp","none"),"vmess_mkcp_tls":("mkcp","tls")}
MAX_CONFIG=512*1024; MAX_SECRET=512*1024
class StoreError(Exception): pass
def safe_id(v):
 if not isinstance(v,str) or not ID_RE.fullmatch(v): raise StoreError("ID de conexión no válido")
 return v
def check_dir(path,create=False):
 path=path.absolute(); cur=Path(path.anchor)
 for part in path.parts[1:]:
  cur/=part
  try: st=cur.lstat()
  except FileNotFoundError:
   if not create or cur!=path: raise StoreError("falta directorio padre seguro")
   cur.mkdir(mode=0o700); st=cur.lstat()
  if not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode): raise StoreError("ruta con componente no directorio o symlink")
 st=path.lstat()
 if st.st_uid!=0 or stat.S_IMODE(st.st_mode)!=0o700: raise StoreError("directorio debe ser root:root modo 0700")
def read_regular(path,limit):
 st=path.lstat()
 if not stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode) or st.st_nlink!=1: raise StoreError("archivo no regular o symlink rechazado")
 if st.st_uid!=0 or stat.S_IMODE(st.st_mode)!=0o600 or st.st_size>limit: raise StoreError("propietario, permisos o tamaño no válido")
 fd=os.open(path,os.O_RDONLY|getattr(os,"O_NOFOLLOW",0))
 with os.fdopen(fd,"rb") as f:
  opened=os.fstat(f.fileno())
  if (opened.st_dev,opened.st_ino,opened.st_uid,stat.S_IMODE(opened.st_mode),opened.st_nlink,opened.st_size)!=(st.st_dev,st.st_ino,0,0o600,1,st.st_size):
   raise StoreError("archivo cambió durante apertura")
  data=f.read(limit+1)
 if len(data)!=st.st_size or len(data)>limit: raise StoreError("archivo cambió durante lectura")
 return data
def atomic_write(path,data):
 if path.is_symlink(): raise StoreError("destino symlink rechazado")
 fd,name=tempfile.mkstemp(prefix=".vmess.",dir=path.parent)
 try:
  os.fchown(fd,0,0); os.fchmod(fd,0o600)
  with os.fdopen(fd,"wb") as f: f.write(data); f.flush(); os.fsync(f.fileno())
  os.replace(name,path)
  dfd=os.open(path.parent,os.O_RDONLY|getattr(os,"O_DIRECTORY",0))
  try: os.fsync(dfd)
  finally: os.close(dfd)
 except Exception:
  try: os.unlink(name)
  except FileNotFoundError: pass
  raise
def master_key(path,create):
 p=Path(path).absolute()
 check_dir(p.parent,create=create)
 if p.is_symlink(): raise StoreError("clave maestra symlink rechazada")
 if not p.exists():
  if not create: raise StoreError("clave maestra ausente; no se regenera durante lectura")
  key=secrets.token_bytes(32)
  try:
   fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,"O_NOFOLLOW",0),0o600)
  except FileExistsError:
   fd=None
  if fd is not None:
   try:
    os.fchown(fd,0,0); os.fchmod(fd,0o600)
    view=memoryview(key)
    while view:
     written=os.write(fd,view)
     if written<=0: raise StoreError("escritura incompleta de clave maestra")
     view=view[written:]
    os.fsync(fd)
   finally: os.close(fd)
   dfd=os.open(p.parent,os.O_RDONLY|getattr(os,"O_DIRECTORY",0))
   try: os.fsync(dfd)
   finally: os.close(dfd)
 st=p.lstat()
 if not stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode) or st.st_nlink!=1 or st.st_uid!=0 or stat.S_IMODE(st.st_mode)!=0o600: raise StoreError("clave maestra no segura")
 fd=os.open(p,os.O_RDONLY|getattr(os,"O_NOFOLLOW",0))
 with os.fdopen(fd,"rb") as f:
  opened=os.fstat(f.fileno())
  if opened.st_ino!=st.st_ino or opened.st_dev!=st.st_dev: raise StoreError("clave maestra cambió durante apertura")
  key=f.read(33)
 if len(key)!=32: raise StoreError("clave maestra inválida")
 return key
def aad(cid): return ("xray-manager:vmess-secret:v1:"+safe_id(cid)).encode()
def encrypt(data,key,cid):
 if not data or len(data)>MAX_SECRET: raise StoreError("secreto vacío o demasiado grande")
 nonce=secrets.token_bytes(12); ciphertext=AESGCM(key).encrypt(nonce,data,aad(cid))
 return json.dumps({"version":1,"algorithm":"AES-256-GCM","nonce":base64.b64encode(nonce).decode(),"ciphertext":base64.b64encode(ciphertext).decode()},sort_keys=True,separators=(",",":")).encode()
def decrypt(blob,key,cid):
 try:
  r=json.loads(blob)
  if set(r)!={"version","algorithm","nonce","ciphertext"} or r["version"]!=1 or r["algorithm"]!="AES-256-GCM": raise ValueError()
  nonce=base64.b64decode(r["nonce"],validate=True); ct=base64.b64decode(r["ciphertext"],validate=True)
  if len(nonce)!=12: raise ValueError()
  data=AESGCM(key).decrypt(nonce,ct,aad(cid))
  if not data or len(data)>MAX_SECRET: raise ValueError()
  return data
 except Exception as exc: raise StoreError("no se pudo autenticar o descifrar el secreto") from exc
def validate_users(users,max_users):
 if not isinstance(users,list) or not 1<=len(users)<=min(1000,max_users): raise StoreError("lista de usuarios VMess inválida o excede los slots")
 seen=set(); emails=set()
 for u in users:
  if not isinstance(u,dict) or set(u)!={"id","level","email"}: raise StoreError("estructura de usuario VMess inválida")
  uid=u["id"]
  if not isinstance(uid,str) or not re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89aAbB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}",uid): raise StoreError("UUID VMess inválido")
  if uid.lower() in seen: raise StoreError("UUID VMess duplicado")
  seen.add(uid.lower())
  if isinstance(u["level"],bool) or not isinstance(u["level"],int) or not 0<=u["level"]<=255: raise StoreError("nivel VMess inválido")
  if not isinstance(u["email"],str) or not 1<=len(u["email"])<=255: raise StoreError("email VMess inválido")
  if u["email"] in emails: raise StoreError("email VMess duplicado")
  emails.add(u["email"])
def validate(config,entry,secret_ref):
 required={"schema_version","connection_id","protocol","mode_id","transport","security","listen_address","listen_port","transport_options","security_options","users"}
 if not isinstance(config,dict) or set(config)!=required: raise StoreError("esquema VMess incompleto o con campos desconocidos")
 cid=safe_id(config["connection_id"]); mode=config["mode_id"]
 if config["schema_version"]!=1 or isinstance(config["schema_version"],bool) or cid!=entry["id"] or config["protocol"]!="vmess" or entry.get("protocol_id")!=mode: raise StoreError("identidad o modalidad no coincide con catálogo")
 if mode not in MODES or (config["transport"],config["security"])!=MODES[mode]: raise StoreError("combinación VMess no admitida")
 if not isinstance(config["listen_address"],str) or not config["listen_address"] or len(config["listen_address"])>255 or any(c.isspace() for c in config["listen_address"]): raise StoreError("dirección de escucha inválida")
 port=config["listen_port"]
 if isinstance(port,bool) or not isinstance(port,int) or not 1<=port<=65535 or port!=entry.get("port"): raise StoreError("puerto no coincide con borrador")
 validate_users(config["users"],entry.get("max_users",0)); t=config["transport_options"]; s=config["security_options"]
 if not isinstance(t,dict) or not isinstance(s,dict): raise StoreError("opciones deben ser objetos")
 transport=config["transport"]
 if transport in ("websocket","httpupgrade"):
  if set(t)!={"path","host"} or not isinstance(t["path"],str) or not t["path"].startswith("/") or len(t["path"])>2048 or not isinstance(t["host"],str) or len(t["host"])>255: raise StoreError("opciones de transporte inválidas")
 elif transport=="grpc":
  if set(t)!={"service_name"} or not isinstance(t["service_name"],str) or not t["service_name"]: raise StoreError("service_name inválido")
 elif transport=="xhttp":
  if set(t)!={"path","mode"} or not isinstance(t["path"],str) or not t["path"].startswith("/") or t["mode"] not in ("auto","packet-up","stream-up","stream-one"): raise StoreError("opciones XHTTP inválidas")
 elif transport=="mkcp":
  if set(t)!={"header_type","seed"} or t["header_type"] not in ("none","srtp","utp","wechat-video","dtls","wireguard") or not isinstance(t["seed"],str) or len(t["seed"])>30: raise StoreError("opciones mKCP inválidas")
 elif transport=="raw" and t: raise StoreError("RAW no admite opciones")
 sec=MODES[mode][1]
 if sec=="tls":
  if set(s)!={"certificate_file","secret_ref"} or not isinstance(s["certificate_file"],str) or not s["certificate_file"].startswith("/") or s["secret_ref"]!=secret_ref or not isinstance(secret_ref,str): raise StoreError("referencia TLS inválida")
 elif sec=="reality":
  if set(s)!={"target","server_names","short_ids","secret_ref"} or not isinstance(s["target"],str) or not re.fullmatch(r".+:[0-9]{1,5}",s["target"]) or not 1<=int(s["target"].rsplit(":",1)[1])<=65535 or not isinstance(s["server_names"],list) or not s["server_names"] or not all(isinstance(x,str) and x for x in s["server_names"]) or not isinstance(s["short_ids"],list) or not s["short_ids"] or not all(isinstance(x,str) and re.fullmatch(r"[0-9a-fA-F]{0,16}",x) for x in s["short_ids"]) or s["secret_ref"]!=secret_ref or not isinstance(secret_ref,str): raise StoreError("referencia REALITY inválida")
 elif s or secret_ref is not None: raise StoreError("modalidad sin secreto contiene referencia")
def validate_catalog_metadata(entry, config_ref, config=None, secret_ref=None):
 cid=safe_id(entry.get("id"))
 match=re.fullmatch(rf"configurations/{re.escape(cid)}\.r([0-9]{{6}})\.json",config_ref if isinstance(config_ref,str) else "")
 if not match: raise StoreError("referencia de configuración inválida")
 ref_revision=int(match.group(1))
 catalog_revision=entry.get("vmess_configuration_revision")
 catalog_schema=entry.get("vmess_configuration_schema_version")
 if isinstance(catalog_revision,bool) or not isinstance(catalog_revision,int) or catalog_revision!=ref_revision:
  raise StoreError("revisión del catálogo no coincide con la referencia")
 if isinstance(catalog_schema,bool) or not isinstance(catalog_schema,int) or catalog_schema!=1:
  raise StoreError("versión de esquema del catálogo inválida")
 if config is not None:
  schema=config.get("schema_version") if isinstance(config,dict) else None
  if isinstance(schema,bool) or not isinstance(schema,int) or schema!=catalog_schema:
   raise StoreError("versión de esquema del documento no coincide con el catálogo")
  mode=config.get("mode_id")
  security=MODES.get(mode,(None,None))[1]
  if security in ("tls","reality"):
   sm=re.fullmatch(rf"secrets/{re.escape(cid)}\.r([0-9]{{6}})\.bin",secret_ref if isinstance(secret_ref,str) else "")
   if not sm or int(sm.group(1))!=ref_revision:
    raise StoreError("revisión de referencia de secreto no coincide")
  elif secret_ref is not None:
   raise StoreError("modalidad sin secreto contiene referencia")
 return ref_revision
def run(a):
 if os.geteuid()!=0: raise StoreError("el almacén requiere root")
 base=Path(a.base).absolute(); cat=Path(a.catalog).absolute(); lock=Path(a.lock).absolute(); conf=base/"configurations"; secdir=Path(a.secrets_dir).absolute()
 check_dir(base,True); check_dir(conf,True); check_dir(secdir,True)
 if cat.is_symlink() or lock.is_symlink(): raise StoreError("symlink en catálogo/bloqueo")
 lock.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
 fd=os.open(lock,os.O_CREAT|os.O_RDWR|getattr(os,"O_NOFOLLOW",0),0o600)
 try:
  os.fchmod(fd,0o600); fcntl.flock(fd,fcntl.LOCK_EX)
  raw=read_regular(cat,4*1024*1024); catalog=json.loads(raw)
  if not isinstance(catalog,list): raise StoreError("catálogo inválido")
  ids=[e.get("id") for e in catalog if isinstance(e,dict)]
  if len(ids)!=len(catalog) or len(ids)!=len(set(ids)): raise StoreError("IDs de catálogo duplicados/inválidos")
  if a.action=="store":
   cid=safe_id(a.connection_id); matches=[e for e in catalog if e.get("id")==cid]
   if len(matches)!=1: raise StoreError("conexión no existe")
   entry=matches[0]
   if entry.get("state")!="draft" or entry.get("runtime_applied") is not False: raise StoreError("solo se guardan borradores no aplicados")
   config=json.loads(read_regular(Path(a.input),MAX_CONFIG))
   existing_ref=entry.get("vmess_configuration_ref")
   metadata_keys=("vmess_configuration_ref","vmess_configuration_revision","vmess_configuration_schema_version","vmess_secret_ref")
   if existing_ref is None:
    if any(k in entry for k in metadata_keys): raise StoreError("metadatos VMess parciales sin referencia de configuración")
    current=0
   else:
    existing_match=re.fullmatch(rf"configurations/{re.escape(cid)}\.r([0-9]{{6}})\.json",existing_ref if isinstance(existing_ref,str) else "")
    if not existing_match: raise StoreError("referencia de configuración previa inválida")
    current=validate_catalog_metadata(entry,existing_ref)
    previous=json.loads(read_regular(conf/f"{cid}.r{current:06d}.json",MAX_CONFIG))
    previous_secret=entry.get("vmess_secret_ref")
    validate_catalog_metadata(entry,existing_ref,previous,previous_secret)
    validate(previous,entry,previous_secret)
   revision=current+1; cfgname=f"{cid}.r{revision:06d}.json"; cfgpath=conf/cfgname
   secret_ref=None; secret_path=secdir/f"{cid}.r{revision:06d}.bin"
   security=MODES.get(config.get("mode_id"),(None,None))[1]; plain=None
   if security in ("tls","reality"):
    if not a.secret_input or a.secret_type!=("tls_private_key" if security=="tls" else "reality_private_key"): raise StoreError("secreto requerido o tipo incorrecto")
    if secret_path.exists() or secret_path.is_symlink(): raise StoreError("colisión de blob; no se sobrescribe")
    plain=read_regular(Path(a.secret_input),MAX_SECRET); secret_ref=f"secrets/{cid}.r{revision:06d}.bin"
    config["security_options"]["secret_ref"]=secret_ref
   elif a.secret_input or a.secret_type: raise StoreError("modalidad sin TLS/REALITY no admite secreto")
   validate(config,entry,secret_ref)
   if plain is not None:
    key=master_key(a.master_key,True); atomic_write(secret_path,encrypt(plain,key,cid))
   if cfgpath.exists() or cfgpath.is_symlink(): raise StoreError("colisión de revisión")
   payload=(json.dumps(config,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode()
   atomic_write(cfgpath,payload)
   if read_regular(cfgpath,MAX_CONFIG)!=payload: raise StoreError("falló verificación posterior")
   entry["vmess_configuration_schema_version"]=1; entry["vmess_configuration_revision"]=revision
   entry["vmess_configuration_ref"]=f"configurations/{cfgname}"; entry["vmess_secret_ref"]=secret_ref
   atomic_write(cat,(json.dumps(catalog,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode())
   return {"status":"stored","connection_id":cid,"revision":revision,"state":"draft","runtime_applied":False}
  if a.action=="read":
   cid=safe_id(a.connection_id); matches=[e for e in catalog if e.get("id")==cid]
   if len(matches)!=1: raise StoreError("conexión no existe")
   entry=matches[0]; ref=entry.get("vmess_configuration_ref")
   m=re.fullmatch(rf"configurations/{re.escape(cid)}\.r([0-9]{{6}})\.json",ref if isinstance(ref,str) else "")
   if not m: raise StoreError("referencia de configuración inválida")
   config=json.loads(read_regular(conf/f"{cid}.r{int(m.group(1)):06d}.json",MAX_CONFIG))
   secret_ref=entry.get("vmess_secret_ref")
   validate_catalog_metadata(entry,ref,config,secret_ref)
   validate(config,entry,secret_ref); written=False
   if secret_ref is not None:
    sm=re.fullmatch(rf"secrets/{re.escape(cid)}\.r([0-9]{{6}})\.bin",secret_ref)
    if not sm: raise StoreError("referencia de secreto inválida")
    plain=decrypt(read_regular(secdir/f"{cid}.r{int(sm.group(1)):06d}.bin",1024*1024),master_key(a.master_key,False),cid)
    if a.secret_output:
     out=Path(a.secret_output).absolute()
     if out.exists() or out.is_symlink(): raise StoreError("destino de secreto ya existe")
     atomic_write(out,plain); written=True
   elif a.secret_output and MODES[config["mode_id"]][1] in ("tls","reality"): raise StoreError("secreto ausente")
   return {"status":"ok","configuration":config,"secret_written":written}
  if a.action=="audit":
   referenced=set(); secret_refs=set(); broken=[]
   for entry in catalog:
    ref=entry.get("vmess_configuration_ref")
    metadata_keys=("vmess_configuration_ref","vmess_configuration_revision","vmess_configuration_schema_version","vmess_secret_ref")
    if ref is None:
     if any(k in entry for k in metadata_keys): broken.append({"id":entry.get("id"),"issue":"partial_catalog_metadata"})
     continue
    cid=safe_id(entry.get("id")); m=re.fullmatch(rf"configurations/{re.escape(cid)}\.r([0-9]{{6}})\.json",ref if isinstance(ref,str) else "")
    if not m: broken.append({"id":cid,"issue":"invalid_reference"}); continue
    fn=f"{cid}.r{int(m.group(1)):06d}.json"; referenced.add(fn)
    try:
     sr=entry.get("vmess_secret_ref"); config=json.loads(read_regular(conf/fn,MAX_CONFIG))
     validate_catalog_metadata(entry,ref,config,sr)
     validate(config,entry,sr)
     if sr:
      sm=re.fullmatch(rf"secrets/{re.escape(cid)}\.r([0-9]{{6}})\.bin",sr)
      if not sm: raise StoreError("referencia secreta inválida")
      sf=f"{cid}.r{int(sm.group(1)):06d}.bin"; secret_refs.add(sf)
      decrypt(read_regular(secdir/sf,1024*1024),master_key(a.master_key,False),cid)
    except Exception: broken.append({"id":cid,"issue":"missing_or_invalid_reference"})
   orphans=[]; secret_orphans=[]; unsafe_entries=[]
   for directory,label,suffix,known in ((conf,"configurations",".json",referenced),(secdir,"secrets",".bin",secret_refs)):
    for path in directory.iterdir():
     st=path.lstat()
     if not stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode) or st.st_nlink!=1 or st.st_uid!=0 or stat.S_IMODE(st.st_mode)!=0o600:
      unsafe_entries.append(f"{label}/{path.name}"); continue
     if path.name.endswith(suffix) and path.name not in known:
      (orphans if label=="configurations" else secret_orphans).append(path.name)
   return {"status":"audit","broken_references":broken,"orphan_files":sorted(orphans),"orphan_secret_files":sorted(secret_orphans),"unsafe_entries":sorted(unsafe_entries),"automatic_deletion":False}
  raise StoreError("acción desconocida")
 finally:
  fcntl.flock(fd,fcntl.LOCK_UN); os.close(fd)
def main():
 p=argparse.ArgumentParser(); p.add_argument("action",choices=("store","read","audit"))
 p.add_argument("--base",default="/var/lib/xray-manager/vmess"); p.add_argument("--catalog",default="/var/lib/xray-manager/connections/connections.json")
 p.add_argument("--lock",default="/run/xray-manager/integrity.lock"); p.add_argument("--connection-id"); p.add_argument("--input")
 p.add_argument("--secret-input"); p.add_argument("--secret-type",choices=("tls_private_key","reality_private_key")); p.add_argument("--secret-output")
 p.add_argument("--secrets-dir",default="/var/lib/xray-manager/vmess/secrets"); p.add_argument("--master-key",default="/etc/xray-manager/keys/master.key")
 a=p.parse_args()
 if a.action in ("store","read") and not a.connection_id: p.error("--connection-id requerido")
 if a.action=="store" and not a.input: p.error("--input requerido")
 try: print(json.dumps(run(a),ensure_ascii=False,separators=(",",":"))); return 0
 except (StoreError,OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as exc:
  print(f"ERROR: {exc}",file=sys.stderr); return 1
if __name__=="__main__": raise SystemExit(main())