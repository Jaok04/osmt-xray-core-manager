#!/usr/bin/env python3
"""Prepara el esquema neutral persistente VMess y separa secretos."""
from __future__ import annotations
import argparse, json, os, stat, tempfile
from pathlib import Path

MODES = {
 "vmess_ws":("websocket","none"), "vmess_tcp_tls":("raw","tls"),
 "vmess_ws_tls":("websocket","tls"), "vmess_reality":("raw","reality"),
 "vmess_grpc":("grpc","none"), "vmess_grpc_tls":("grpc","tls"),
 "vmess_grpc_reality":("grpc","reality"), "vmess_httpupgrade":("httpupgrade","none"),
 "vmess_httpupgrade_tls":("httpupgrade","tls"), "vmess_xhttp":("xhttp","none"),
 "vmess_xhttp_tls":("xhttp","tls"), "vmess_xhttp_reality":("xhttp","reality"),
 "vmess_mkcp":("mkcp","none"), "vmess_mkcp_tls":("mkcp","tls"),
}
def private_write(path: Path, data: bytes) -> None:
 fd,name=tempfile.mkstemp(prefix=".vmess-prepare.",dir=path.parent)
 try:
  os.fchmod(fd,0o600)
  with os.fdopen(fd,"wb") as stream: stream.write(data); stream.flush(); os.fsync(stream.fileno())
  os.replace(name,path)
 except Exception:
  try: os.unlink(name)
  except FileNotFoundError: pass
  raise
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--model",required=True); p.add_argument("--options",required=True)
 p.add_argument("--output",required=True); p.add_argument("--secret-output",required=True)
 a=p.parse_args()
 model=json.loads(Path(a.model).read_text()); options=json.loads(Path(a.options).read_text())
 mode=model.get("mode_id")
 if mode not in MODES or (model.get("transport"),model.get("security"))!=MODES[mode]: raise ValueError("modelo VMess inválido")
 transport={}; security={}; secret=None; secret_type=None
 t=model["transport"]
 if t in ("websocket","httpupgrade"): transport={"path":options["path"],"host":options.get("host","")}
 elif t=="grpc": transport={"service_name":options["service_name"]}
 elif t=="xhttp": transport={"path":options["path"],"mode":options["mode"]}
 elif t=="mkcp": transport={"header_type":options["header_type"],"seed":options.get("seed","")}
 if model["security"]=="tls":
  cert=options["certificate_file"]; key_path=Path(options["key_file"])
  if not isinstance(cert,str) or not cert.startswith("/") or not key_path.is_absolute(): raise ValueError("rutas TLS deben ser absolutas")
  fd=os.open(key_path,os.O_RDONLY|getattr(os,"O_NOFOLLOW",0)|getattr(os,"O_CLOEXEC",0))
  try:
   st=os.fstat(fd)
   if not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_gid!=0 or stat.S_IMODE(st.st_mode)!=0o600 or st.st_nlink!=1: raise ValueError("la clave TLS debe ser archivo regular root:root, modo 0600 y un solo enlace duro")
   with os.fdopen(fd,"rb") as stream:
    fd=-1; secret=stream.read(512*1024+1)
   if len(secret)>512*1024: raise ValueError("clave TLS supera el tamaño permitido")
  finally:
   if fd>=0: os.close(fd)
  if not secret: raise ValueError("clave TLS vacía")
  security={"certificate_file":cert}; secret_type="tls_private_key"
 elif model["security"]=="reality":
  secret=options["private_key"].encode()
  if not secret or len(secret)>512*1024: raise ValueError("clave REALITY vacía o demasiado grande")
  security={"target":options["target"],"server_names":options["server_names"],"short_ids":options["short_ids"]}
  secret_type="reality_private_key"
 config={"schema_version":1,"connection_id":model["connection_id"],"protocol":"vmess","mode_id":mode,
         "transport":t,"security":model["security"],"listen_address":model["listen_address"],
         "listen_port":model["listen_port"],"transport_options":transport,"security_options":security,
         "users":model["users"]}
 private_write(Path(a.output),(json.dumps(config,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode())
 if secret is None:
  Path(a.secret_output).unlink(missing_ok=True)
  print(json.dumps({"secret_type":None,"has_secret":False}))
 else:
  private_write(Path(a.secret_output),secret)
  print(json.dumps({"secret_type":secret_type,"has_secret":True}))
if __name__=="__main__":
 try: main()
 except Exception as exc:
  print(f"ERROR: {exc}",file=__import__("sys").stderr); raise SystemExit(1)