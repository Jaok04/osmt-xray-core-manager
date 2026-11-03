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
 p.add_argument("--output",required=True); p.add_argument("--secret-output")
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
  certificate_id=options.get("certificate_id")
  if not isinstance(certificate_id,str) or not __import__("re").fullmatch(r"cert-[A-Za-z0-9][A-Za-z0-9_.-]{0,120}",certificate_id):
   raise ValueError("TLS requiere certificate_id del catálogo central")
  if set(options)-({"certificate_id","path","host","service_name","mode","header_type","seed"}):
   raise ValueError("opciones TLS contienen campos no admitidos")
  security={"certificate_id":certificate_id}
 elif model["security"]=="reality":
  if not a.secret_output: raise ValueError("REALITY requiere --secret-output")
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
  if a.secret_output: Path(a.secret_output).unlink(missing_ok=True)
  print(json.dumps({"secret_type":None,"has_secret":False}))
 else:
  private_write(Path(a.secret_output),secret)
  print(json.dumps({"secret_type":secret_type,"has_secret":True}))
if __name__=="__main__":
 try: main()
 except Exception as exc:
  print(f"ERROR: {exc}",file=__import__("sys").stderr); raise SystemExit(1)