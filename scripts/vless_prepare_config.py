#!/usr/bin/env python3
"""Convierte modelo/opciones temporales del asistente en esquema persistente neutral."""
import argparse, json, os, stat, tempfile
from pathlib import Path

MODES = {
    "vless_ws": ("websocket", "none"), "vless_tcp_tls": ("raw", "tls"),
    "vless_ws_tls": ("websocket", "tls"), "vless_reality": ("raw", "reality"),
    "vless_grpc_tls": ("grpc", "tls"), "vless_grpc_reality": ("grpc", "reality"),
    "vless_xhttp": ("xhttp", "none"), "vless_xhttp_tls": ("xhttp", "tls"),
    "vless_xhttp_reality": ("xhttp", "reality"),
}

def private_write(path: Path, data: bytes) -> None:
    fd, tmp_name = tempfile.mkstemp(prefix=".vless-prepare.", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try: os.unlink(tmp_name)
        except FileNotFoundError: pass
        raise

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--model', required=True); p.add_argument('--options', required=True)
    p.add_argument('--output', required=True); p.add_argument('--secret-output', required=True)
    a=p.parse_args()
    model=json.loads(Path(a.model).read_text()); options=json.loads(Path(a.options).read_text())
    mode=model.get('mode_id'); cid=model.get('connection_id')
    if mode not in MODES or (model.get('transport'),model.get('security')) != MODES[mode]: raise ValueError('modelo VLESS inválido')
    transport={}; security={}; secret=None; secret_type=None
    if mode in ('vless_ws','vless_ws_tls'): transport={'path':options['path']}
    elif mode.startswith('vless_xhttp'): transport={'path':options['path'],'mode':options['mode']}
    elif mode.startswith('vless_grpc'): transport={'service_name':options['service_name']}
    if model['security']=='tls':
        security={'certificate_file':options['certificate_file']}
        secret_type='tls_private_key'
        key_path=Path(options['key_file'])
        fd=os.open(key_path, os.O_RDONLY | getattr(os, 'O_CLOEXEC', 0))
        try:
            st=os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o022:
                raise ValueError('la clave TLS debe ser archivo regular de root y no permitir escritura a grupo/otros')
            with os.fdopen(fd, 'rb') as stream:
                fd=-1
                secret=stream.read(512 * 1024 + 1)
            if len(secret) > 512 * 1024: raise ValueError('clave TLS supera el tamaño permitido')
        finally:
            if fd >= 0: os.close(fd)
    elif model['security']=='reality':
        security={'target':options['target'],'server_names':options['server_names'],'short_ids':options['short_ids']}
        secret_type='reality_private_key'; secret=options['private_key'].encode()
    config={'schema_version':1,'connection_id':cid,'protocol':'vless','mode_id':mode,
            'transport':model['transport'],'security':model['security'],
            'listen_address':model['listen_address'],'listen_port':model['listen_port'],
            'transport_options':transport,'security_options':security}
    private_write(Path(a.output),(json.dumps(config,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode())
    if secret is not None:
        if not secret: raise ValueError('secreto vacío')
        private_write(Path(a.secret_output),secret)
        print(json.dumps({'secret_type':secret_type,'has_secret':True}))
    else:
        Path(a.secret_output).unlink(missing_ok=True)
        print(json.dumps({'secret_type':None,'has_secret':False}))

if __name__=='__main__':
    try: main()
    except Exception as exc:
        print(f'ERROR: {exc}',file=__import__('sys').stderr); raise SystemExit(1)
