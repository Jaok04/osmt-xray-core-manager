#!/usr/bin/env python3
"""Convierte modelo/opciones temporales del asistente en esquema persistente neutral."""
import argparse, json, os, re, tempfile
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
    if not isinstance(model, dict) or not isinstance(options, dict): raise ValueError('modelo y opciones deben ser objetos JSON')
    mode=model.get('mode_id'); cid=model.get('connection_id')
    if mode not in MODES or (model.get('transport'),model.get('security')) != MODES[mode]: raise ValueError('modelo VLESS inválido')
    transport={}; security={}; secret=None; secret_type=None
    if mode == 'vless_ws': transport={'path':options['path']}
    elif mode == 'vless_ws_tls':
        transport={'path':options['path']}
        if options.get('host'): transport['host']=options['host']
    elif mode.startswith('vless_xhttp'): transport={'path':options['path'],'mode':options['mode']}
    elif mode.startswith('vless_grpc'): transport={'service_name':options['service_name']}
    if model['security']=='tls':
        transport_keys = {'path', 'mode'} if mode == 'vless_xhttp_tls' else ({'path', 'host', 'client_server_name'} if mode == 'vless_ws_tls' else ({'service_name'} if mode == 'vless_grpc_tls' else set()))
        optional_client_keys = {'host', 'client_server_name'} if mode == 'vless_ws_tls' else set()
        if (set(options) - optional_client_keys != (transport_keys - optional_client_keys) | {'certificate_id'}
                or not isinstance(options.get('certificate_id'), str)
                or not re.fullmatch(r'cert-[A-Za-z0-9][A-Za-z0-9_.-]{0,120}', options['certificate_id'])):
            raise ValueError('TLS requiere un certificate_id central válido y sólo las opciones de transporte de su modalidad')
        security={'certificate_id':options['certificate_id']}
    elif model['security']=='reality':
        security={'target':options['target'],'server_names':options['server_names'],'short_ids':options['short_ids']}
        secret_type='reality_private_key'; secret=options['private_key'].encode()
    client_options={}
    if mode == 'vless_ws_tls':
        if options.get('client_server_name'):
            client_options['tls_server_name']=options['client_server_name']
    schema_version=2 if mode == 'vless_ws_tls' and (transport.get('host') or client_options) else 1
    config={'schema_version':schema_version,'connection_id':cid,'protocol':'vless','mode_id':mode,
            'transport':model['transport'],'security':model['security'],
            'listen_address':model['listen_address'],'listen_port':model['listen_port'],
            'transport_options':transport,'security_options':security}
    if schema_version == 2: config['client_options']=client_options
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
