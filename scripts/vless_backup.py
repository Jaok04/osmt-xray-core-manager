#!/usr/bin/env python3
"""Backup y recuperación protegida del almacén persistente VLESS.

Las operaciones toman siempre lifecycle.lock y después integrity.lock.
Los backups de datos nunca contienen la clave maestra. La recuperación de
clave se cifra por separado con scrypt + AES-256-GCM.
"""
from __future__ import annotations
import argparse, fcntl, getpass, hashlib, hmac, io, json, os, re, secrets, stat, sys, tarfile, tempfile, time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

DEFAULT_BASE = Path('/var/lib/xray-manager/connections')
DEFAULT_SECRETS = Path('/var/lib/xray-manager/secrets')
DEFAULT_KEY = Path('/etc/xray-manager/keys/master.key')
DEFAULT_BACKUPS = Path('/var/backups/xray-manager/vless')
LIFECYCLE = Path('/run/lock/xray-manager-lifecycle.lock')
INTEGRITY = Path('/run/xray-manager/integrity.lock')
RECOVERY_N = 2**15
RECOVERY_R = 8
RECOVERY_P = 1
MAX_ARCHIVE = 512 * 1024 * 1024
MAX_FILES = 20000
MAX_MEMBER = 64 * 1024 * 1024
MAX_TOTAL_UNCOMPRESSED = 512 * 1024 * 1024
ID_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$')

class BackupError(Exception):
    pass

def require_root():
    if os.geteuid() != 0:
        raise BackupError('la operación requiere root')

def safe_dir(path: Path, create=False):
    path = path.absolute()
    cur = Path(path.anchor)
    for part in path.parts[1:]:
        cur /= part
        try: st = cur.lstat()
        except FileNotFoundError:
            if not create or cur != path: raise BackupError(f'directorio requerido ausente: {cur}')
            cur.mkdir(mode=0o700)
            st = cur.lstat()
        if not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode):
            raise BackupError(f'componente de ruta no seguro: {cur}')
    st = path.lstat()
    if st.st_uid != 0 or stat.S_IMODE(st.st_mode) != 0o700:
        raise BackupError(f'directorio debe ser root:root modo 0700: {path}')

def safe_regular(path: Path, max_size=MAX_MEMBER):
    st = path.lstat()
    if not stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode) or st.st_nlink != 1:
        raise BackupError(f'archivo no regular o symlink rechazado: {path}')
    if st.st_uid != 0 or stat.S_IMODE(st.st_mode) != 0o600 or st.st_size > max_size:
        raise BackupError(f'propietario, permisos o tamaño no válido: {path}')
    return st

def lock_pair():
    fds=[]
    try:
        for path in (LIFECYCLE, INTEGRITY):
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            if path.is_symlink(): raise BackupError('symlink en ruta de bloqueo')
            fd=os.open(path, os.O_CREAT|os.O_RDWR|getattr(os,'O_NOFOLLOW',0), 0o600)
            os.fchmod(fd,0o600)
            fcntl.flock(fd, fcntl.LOCK_EX)
            fds.append(fd)
        return fds
    except Exception:
        for fd in reversed(fds):
            fcntl.flock(fd, fcntl.LOCK_UN); os.close(fd)
        raise

def unlock_pair(fds):
    for fd in reversed(fds):
        fcntl.flock(fd, fcntl.LOCK_UN); os.close(fd)

def fsync_dir(path: Path):
    fd=os.open(path,os.O_RDONLY|getattr(os,'O_DIRECTORY',0))
    try: os.fsync(fd)
    finally: os.close(fd)

def utc_now():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')

def atomic_file(path: Path, data: bytes, mode=0o600):
    fd,name=tempfile.mkstemp(prefix='.vless-backup.', dir=path.parent)
    tmp=Path(name)
    try:
        os.fchown(fd,0,0); os.fchmod(fd,mode)
        with os.fdopen(fd,'wb') as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,path)
        dfd=os.open(path.parent,os.O_RDONLY|getattr(os,'O_DIRECTORY',0))
        try: os.fsync(dfd)
        finally: os.close(dfd)
    except Exception:
        tmp.unlink(missing_ok=True); raise

def sha(data: bytes): return hashlib.sha256(data).hexdigest()

def collect_files(base: Path, secrets_dir: Path):
    items=[]
    total_size=0
    for root, prefix in ((base,'connections'),(secrets_dir,'secrets')):
        if not root.exists(): continue
        safe_dir(root)
        for p in sorted(root.rglob('*')):
            st=p.lstat()
            rel=p.relative_to(root).as_posix()
            if stat.S_ISDIR(st.st_mode):
                if stat.S_IMODE(st.st_mode)!=0o700 or st.st_uid!=0: raise BackupError(f'directorio interno inseguro: {p}')
                continue
            if not stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode) or st.st_nlink!=1:
                raise BackupError(f'entrada no regular rechazada: {p}')
            safe_regular(p)
            total_size += st.st_size
            if total_size > MAX_TOTAL_UNCOMPRESSED: raise BackupError('el almacén excede el límite agregado sin comprimir')
            items.append((p, f'{prefix}/{rel}'))
            if len(items)>MAX_FILES: raise BackupError('demasiados archivos en almacén')
    return items

def inspect_catalog(base: Path):
    cat=base/'connections.json'
    if not cat.exists(): raise BackupError('catálogo de conexiones ausente')
    safe_regular(cat,4*1024*1024)
    data=json.loads(cat.read_text(encoding='utf-8'))
    if not isinstance(data,list): raise BackupError('catálogo no es arreglo JSON')
    ids=[]; revisions=[]; certs=[]; refs=[]
    for e in data:
        if not isinstance(e,dict) or not isinstance(e.get('id'),str) or not ID_RE.fullmatch(e['id']): raise BackupError('entrada de catálogo inválida')
        ids.append(e['id'])
        if e.get('configuration_ref'):
            refs.append(e['configuration_ref'])
            m=re.fullmatch(r'configurations/([A-Za-z0-9_.-]+)\.r([0-9]{6})\.json',e['configuration_ref'])
            if not m or m.group(1)!=e['id']: raise BackupError('referencia de configuración insegura')
            revisions.append({'id':e['id'],'revision':int(m.group(2))})
            cfg=base/e['configuration_ref']
            safe_regular(cfg,256*1024)
            c=json.loads(cfg.read_text(encoding='utf-8'))
            cert=c.get('security_options',{}).get('certificate_file')
            if isinstance(cert,str) and cert.startswith('/'):
                certs.append({'connection_id':e['id'],'certificate_path':cert,'included':False})
    if len(ids)!=len(set(ids)): raise BackupError('IDs duplicados en catálogo')
    return data, revisions, certs

def build_manifest(files, base, secrets_dir, backup_id, archive_bytes):
    catalog,revisions,certs=inspect_catalog(base)
    entries=[]
    for p, rel in files:
        b=p.read_bytes()
        entries.append({'path':rel,'size':len(b),'sha256':sha(b)})
    secret_count=sum(1 for _,rel in files if rel.startswith('secrets/'))
    return {'format':'xray-manager-vless-data-backup','format_version':1,'backup_id':backup_id,
            'created_at':datetime.now(timezone.utc).isoformat(),'manager_version':read_version(),
            'schema_versions':[1],'crypto_formats':[1] if secret_count else [],
            'files':entries,'connection_count':len(catalog),'connection_ids':sorted(e['id'] for e in catalog),
            'configuration_revisions':revisions,'encrypted_secret_blob_count':secret_count,
            'contains_master_key':False,'external_dependencies':{'tls_certificates':certs},
            'archive_sha256':sha(archive_bytes)}

def read_version():
    return 'unknown'

def make_archive(files):
    total_size=0
    buf=io.BytesIO()
    with tarfile.open(fileobj=buf,mode='w:gz',format=tarfile.PAX_FORMAT) as tar:
        for path, rel in files:
            data=path.read_bytes()
            total_size += len(data)
            if total_size > MAX_TOTAL_UNCOMPRESSED: raise BackupError('el almacén excede el límite agregado sin comprimir')
            info=tarfile.TarInfo(rel); info.size=len(data); info.mode=0o600; info.uid=0; info.gid=0; info.uname='root'; info.gname='root'; info.mtime=0
            tar.addfile(info,io.BytesIO(data))
    return buf.getvalue()

def sha_sums(directory: Path, names):
    lines=[]
    for name in names:
        data=(directory/name).read_bytes(); lines.append(f'{sha(data)}  {name}')
    return ('\n'.join(lines)+'\n').encode()

def _safe_member_name(name: str):
    if not isinstance(name,str) or not name or '\\' in name or '\x00' in name:
        raise BackupError('nombre de miembro no válido')
    raw_parts=name.split('/')
    p=PurePosixPath(name)
    if p.is_absolute() or not p.parts or any(part in ('','.', '..') for part in raw_parts) or p.parts[0] not in ('connections','secrets'):
        raise BackupError('ruta no segura en archivo')
    if len(p.parts)<2:
        raise BackupError('ruta de miembro incompleta')
    return p

def _read_archive_members(archive: bytes, manifest: dict, retain=True):
    if not isinstance(archive,bytes) or len(archive)>MAX_ARCHIVE:
        raise BackupError('archivo comprimido excede el límite o no es válido')
    extracted={}; seen=set(); total=0; metadata={}
    files=manifest.get('files')
    if not isinstance(files,list) or len(files)>MAX_FILES:
        raise BackupError('lista de archivos del manifiesto no válida')
    for item in files:
        if not isinstance(item,dict) or not isinstance(item.get('path'),str):
            raise BackupError('entrada de manifiesto inválida')
        name=item['path']; _safe_member_name(name)
        if name in metadata: raise BackupError('ruta duplicada en manifiesto')
        size=item.get('size'); digest=item.get('sha256')
        if not isinstance(size,int) or isinstance(size,bool) or size<0 or size>MAX_MEMBER or not isinstance(digest,str) or not re.fullmatch(r'[0-9a-f]{64}',digest):
            raise BackupError('metadatos de archivo no válidos en manifiesto')
        metadata[name]=(size,digest)
    try:
        with tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz') as tar:
            for member in tar:
                name=member.name; _safe_member_name(name)
                if name in seen or len(seen)>=MAX_FILES or not member.isfile() or member.issym() or member.islnk():
                    raise BackupError('tipo, duplicado o cantidad no permitida en archivo')
                if member.mode & 0o077 or member.size<0 or member.size>MAX_MEMBER:
                    raise BackupError('permisos o tamaño no permitido en miembro de archivo')
                total += member.size
                if total > MAX_TOTAL_UNCOMPRESSED:
                    raise BackupError('el archivo excede el límite agregado sin comprimir')
                if name not in metadata or metadata[name][0] != member.size:
                    raise BackupError('contenido del archivo no coincide con manifiesto')
                stream=tar.extractfile(member)
                if stream is None: raise BackupError('miembro ilegible')
                chunks=[]; digest=hashlib.sha256(); remaining=member.size
                while remaining:
                    chunk=stream.read(min(1024*1024,remaining))
                    if not chunk: raise BackupError('miembro truncado')
                    digest.update(chunk); remaining-=len(chunk)
                    if retain: chunks.append(chunk)
                if stream.read(1): raise BackupError('miembro excede el tamaño declarado')
                if not hmac.compare_digest(digest.hexdigest(),metadata[name][1]):
                    raise BackupError(f'hash interno incorrecto: {name}')
                if retain: extracted[name]=b''.join(chunks)
                seen.add(name)
    except (tarfile.TarError, OSError, EOFError) as exc:
        raise BackupError('archivo tar.gz corrupto o no válido') from exc
    if seen != set(metadata): raise BackupError('contenido del archivo no coincide con manifiesto')
    return extracted

def verify_data_dir(directory: Path):
    safe_dir(directory)
    for name in ('backup.tar.gz','manifest.json','SHA256SUMS'):
        safe_regular(directory/name,MAX_ARCHIVE if name=='backup.tar.gz' else 16*1024*1024)
    expected={}
    for line in (directory/'SHA256SUMS').read_text().splitlines():
        m=re.fullmatch(r'([0-9a-f]{64})  (backup\.tar\.gz|manifest\.json)',line)
        if not m or m.group(2) in expected: raise BackupError('SHA256SUMS inválido')
        expected[m.group(2)]=m.group(1)
    if set(expected)!= {'backup.tar.gz','manifest.json'}: raise BackupError('SHA256SUMS incompleto')
    for name,digest in expected.items():
        if not hmac.compare_digest(sha((directory/name).read_bytes()),digest): raise BackupError(f'hash incorrecto: {name}')
    manifest=json.loads((directory/'manifest.json').read_text())
    if manifest.get('format')!='xray-manager-vless-data-backup' or manifest.get('format_version')!=1 or manifest.get('contains_master_key') is not False: raise BackupError('manifiesto no compatible o inseguro')
    archive=(directory/'backup.tar.gz').read_bytes()
    if not hmac.compare_digest(sha(archive),manifest.get('archive_sha256','')): raise BackupError('hash de archivo no coincide con manifiesto')
    _read_archive_members(archive,manifest,retain=False)
    return manifest

def create_data(args):
    require_root(); base=Path(args.base); secrets_dir=Path(args.secrets_dir); root=Path(args.backups)
    safe_dir(base); safe_dir(root,create=True)
    fds=lock_pair()
    try:
        files=collect_files(base,secrets_dir)
        backup_id=utc_now()
        archive=make_archive(files)
        if len(archive)>MAX_ARCHIVE: raise BackupError('archivo comprimido excede el límite')
        manifest=build_manifest(files,base,secrets_dir,backup_id,archive)
        target=root/'data'/backup_id
        (root/'data').mkdir(mode=0o700,exist_ok=True); safe_dir(root/'data')
        target.mkdir(mode=0o700)
        atomic_file(target/'backup.tar.gz',archive)
        atomic_file(target/'manifest.json',(json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode())
        atomic_file(target/'SHA256SUMS',sha_sums(target,('backup.tar.gz','manifest.json')))
        verify_data_dir(target)
        dfd=os.open(target.parent,os.O_RDONLY|getattr(os,'O_DIRECTORY',0)); os.fsync(dfd); os.close(dfd)
        return {'status':'created','backup_id':backup_id,'path':str(target),'connections':manifest['connection_count'],'secret_blobs':manifest['encrypted_secret_blob_count'],'verified':True}
    finally: unlock_pair(fds)

def derive(password: str, salt: bytes):
    if len(password)<12: raise BackupError('la contraseña debe tener al menos 12 caracteres')
    return Scrypt(salt=salt,length=32,n=RECOVERY_N,r=RECOVERY_R,p=RECOVERY_P).derive(password.encode('utf-8'))

def _create_recovery_locked(args):
    require_root(); key_path=Path(args.master_key); root=Path(args.backups)
    safe_dir(key_path.parent); safe_regular(key_path,32)
    key=key_path.read_bytes()
    if len(key)!=32: raise BackupError('clave maestra no tiene 32 bytes')
    # Confirmar existencia de backup de datos al que quedará ligada la recuperación.
    data_root=root/'data'
    if not data_root.is_dir(): raise BackupError('primero debe existir un backup de datos')
    candidates=sorted(p for p in data_root.iterdir() if p.is_dir())
    if not candidates: raise BackupError('no existe backup de datos para asociar')
    selected=Path(args.backup_dir).absolute() if args.backup_dir else candidates[-1]
    manifest=verify_data_dir(selected)
    if manifest.get('encrypted_secret_blob_count',0)<1: raise BackupError('el backup seleccionado no contiene secretos cifrados; recuperación de clave no es necesaria')
    password=getpass.getpass('Contraseña nueva para el archivo de recuperación: ')
    confirm=getpass.getpass('Confirma la contraseña: ')
    if not hmac.compare_digest(password,confirm): raise BackupError('las contraseñas no coinciden')
    salt=secrets.token_bytes(16); nonce=secrets.token_bytes(12); derived=derive(password,salt)
    header={'format':'xray-manager-vless-key-recovery','format_version':1,'backup_id':manifest['backup_id'],'kdf':'scrypt','n':RECOVERY_N,'r':RECOVERY_R,'p':RECOVERY_P,'salt':salt.hex(),'nonce':nonce.hex(),'algorithm':'AES-256-GCM'}
    aad=json.dumps(header,sort_keys=True,separators=(',',':')).encode()
    payload={'header':header,'ciphertext':AESGCM(derived).encrypt(nonce,key,aad).hex()}
    outroot=root/'recovery'; outroot.mkdir(mode=0o700,exist_ok=True); safe_dir(outroot)
    target=outroot/manifest['backup_id']
    if target.exists() or target.is_symlink(): raise BackupError('ya existe un paquete de recuperación para este backup; no se sobrescribe')
    target.mkdir(mode=0o700)
    atomic_file(target/'master-key.recovery',(json.dumps(payload,sort_keys=True,separators=(',',':'))+'\n').encode())
    rec_manifest={'format':'xray-manager-vless-key-recovery-manifest','format_version':1,'backup_id':manifest['backup_id'],'created_at':datetime.now(timezone.utc).isoformat(),'kdf':'scrypt','algorithm':'AES-256-GCM','contains_plaintext_key':False}
    atomic_file(target/'manifest.json',(json.dumps(rec_manifest,sort_keys=True,indent=2)+'\n').encode())
    atomic_file(target/'SHA256SUMS',sha_sums(target,('master-key.recovery','manifest.json')))
    return {'status':'created','backup_id':manifest['backup_id'],'path':str(target),'verified':True,'warning':'copie este paquete fuera de la VPS; la contraseña no se almacena'}

def create_recovery(args):
    require_root()
    fds=lock_pair()
    try: return _create_recovery_locked(args)
    finally: unlock_pair(fds)

def verify_recovery(directory: Path):
    safe_dir(directory)
    for n in ('master-key.recovery','manifest.json','SHA256SUMS'): safe_regular(directory/n,2*1024*1024)
    expected={}
    for line in (directory/'SHA256SUMS').read_text().splitlines():
        m=re.fullmatch(r'([0-9a-f]{64})  (master-key\.recovery|manifest\.json)',line)
        if not m or m.group(2) in expected: raise BackupError('SHA256SUMS recuperación inválido')
        expected[m.group(2)]=m.group(1)
    if set(expected)!={'master-key.recovery','manifest.json'}: raise BackupError('SHA256SUMS recuperación incompleto')
    for n,h in expected.items():
        if not hmac.compare_digest(sha((directory/n).read_bytes()),h): raise BackupError('hash incorrecto en recuperación')
    rec=json.loads((directory/'manifest.json').read_text()); payload=json.loads((directory/'master-key.recovery').read_text())
    header=payload.get('header',{})
    if rec.get('format')!='xray-manager-vless-key-recovery-manifest' or rec.get('contains_plaintext_key') is not False: raise BackupError('manifiesto recuperación no válido')
    if header.get('format')!='xray-manager-vless-key-recovery' or header.get('format_version')!=1 or header.get('backup_id')!=rec.get('backup_id') or header.get('kdf')!='scrypt' or header.get('algorithm')!='AES-256-GCM': raise BackupError('formato de clave recuperación no compatible')
    if header.get('n')!=RECOVERY_N or header.get('r')!=RECOVERY_R or header.get('p')!=RECOVERY_P: raise BackupError('parámetros scrypt no admitidos')
    return payload

def validate_payload(archive: bytes, manifest: dict, key: bytes):
    """Valida rutas, tipos, tamaños, hashes y catálogo antes de publicar."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import vless_crypto as crypto
    if not isinstance(key,bytes) or len(key)!=32: raise BackupError('clave maestra inválida')
    extracted=_read_archive_members(archive,manifest,retain=True)
    cat_bytes=extracted.get('connections/connections.json')
    if cat_bytes is None: raise BackupError('backup sin catálogo de conexiones')
    catalog=json.loads(cat_bytes)
    if not isinstance(catalog,list): raise BackupError('catálogo restaurado inválido')
    seen=set()
    for e in catalog:
        if not isinstance(e,dict) or not isinstance(e.get('id'),str) or not ID_RE.fullmatch(e['id']) or e['id'] in seen:
            raise BackupError('registro de conexión inválido o duplicado')
        seen.add(e['id'])
        if e.get('state')!='draft' or e.get('runtime_applied') is not False:
            raise BackupError('backup contiene una conexión fuera del estado draft esperado')
        ref=e.get('configuration_ref')
        if ref is None: continue
        m=re.fullmatch(r'configurations/([A-Za-z0-9_.-]+)\.r([0-9]{6})\.json',ref if isinstance(ref,str) else '')
        if not m or m.group(1)!=e['id']: raise BackupError('referencia de configuración inválida')
        name='connections/'+ref
        raw=extracted.get(name)
        if raw is None: raise BackupError('configuración referenciada ausente')
        cfg=json.loads(raw)
        if not isinstance(cfg,dict) or cfg.get('connection_id')!=e['id'] or cfg.get('protocol')!='vless' or cfg.get('schema_version')!=1:
            raise BackupError('configuración neutral no válida')
        sec=cfg.get('security_options',{})
        if not isinstance(sec,dict): raise BackupError('opciones de seguridad no válidas')
        secret_ref=e.get('secret_ref')
        if secret_ref is not None:
            sm=re.fullmatch(r'secrets/([A-Za-z0-9_.-]+)\.r([0-9]{6})\.bin',secret_ref if isinstance(secret_ref,str) else '')
            if not sm or sm.group(1)!=e['id']: raise BackupError('referencia de secreto inválida')
            blob=extracted.get(secret_ref)
            if blob is None: raise BackupError('blob cifrado referenciado ausente')
            crypto.decrypt_secret(blob,key,e['id'],1)
            if sec.get('secret_ref')!=secret_ref: raise BackupError('referencia de secreto no coincide con configuración')
        elif cfg.get('security') in ('tls','reality'):
            raise BackupError('configuración TLS/REALITY sin secreto cifrado')
    manifest_ids=manifest.get('connection_ids',[])
    if sorted(e['id'] for e in catalog)!=manifest_ids: raise BackupError('IDs de catálogo no coinciden con manifiesto')
    return extracted

def merge_current_vmess_entries(stage_base: Path, live_base: Path):
    """Combina VLESS del backup con las entradas VMess vigentes.

    El catálogo es compartido, pero el almacén VMess vive en el directorio
    hermano ``vmess``. Esta operación solo preserva registros y referencias;
    nunca copia, modifica ni incorpora archivos del almacén VMess al backup.
    Debe ejecutarse bajo lifecycle.lock e integrity.lock.
    """
    restored_path = stage_base / 'connections.json'
    safe_regular(restored_path, 4 * 1024 * 1024)
    restored = json.loads(restored_path.read_text(encoding='utf-8'))
    if not isinstance(restored, list):
        raise BackupError('catálogo VLESS preparado inválido')

    vless_entries = []
    restored_ids = set()
    for entry in restored:
        if not isinstance(entry, dict) or not isinstance(entry.get('id'), str) or not ID_RE.fullmatch(entry['id']):
            raise BackupError('registro restaurado inválido durante combinación')
        protocol_id = entry.get('protocol_id')
        if isinstance(protocol_id, str) and protocol_id.startswith('vmess_'):
            # Un backup histórico VLESS puede contener el catálogo compartido
            # de aquella fecha. Esas entradas nunca prevalecen sobre VMess vivo.
            continue
        if not isinstance(protocol_id, str) or not protocol_id.startswith('vless_'):
            raise BackupError('el backup contiene un protocolo ajeno a VLESS/VMess')
        if entry['id'] in restored_ids:
            raise BackupError('IDs duplicados en catálogo VLESS restaurado')
        restored_ids.add(entry['id'])
        vless_entries.append(entry)

    current_vmess = []
    if live_base.is_symlink():
        raise BackupError('symlink en el directorio del catálogo actual')
    if live_base.exists():
        safe_dir(live_base)
        live_catalog_path = live_base / 'connections.json'
        if not live_catalog_path.exists():
            raise BackupError('catálogo actual ausente; no es posible proteger entradas VMess')
        safe_regular(live_catalog_path, 4 * 1024 * 1024)
        live_catalog = json.loads(live_catalog_path.read_text(encoding='utf-8'))
        if not isinstance(live_catalog, list):
            raise BackupError('catálogo actual inválido; restauración detenida')
        all_current_ids = set()
        vmess_root = live_base.parent / 'vmess'
        vmess_store = None
        for entry in live_catalog:
            if not isinstance(entry, dict) or not isinstance(entry.get('id'), str) or not ID_RE.fullmatch(entry['id']):
                raise BackupError('registro inválido en catálogo actual')
            cid = entry['id']
            if cid in all_current_ids:
                raise BackupError('IDs duplicados en catálogo actual')
            all_current_ids.add(cid)
            protocol_id = entry.get('protocol_id')
            if not isinstance(protocol_id, str) or not (protocol_id.startswith('vless_') or protocol_id.startswith('vmess_')):
                raise BackupError('el catálogo actual contiene un protocolo no cubierto por la restauración VLESS')
            if protocol_id.startswith('vmess_'):
                if vmess_store is None:
                    import importlib
                    sys.path.insert(0, str(Path(__file__).resolve().parent))
                    vmess_store = importlib.import_module('vmess_config_store')
                if protocol_id not in vmess_store.MODES:
                    raise BackupError('modalidad VMess desconocida en catálogo actual')
                config_ref = entry.get('vmess_configuration_ref')
                secret_ref = entry.get('vmess_secret_ref')
                if config_ref is None:
                    if secret_ref is not None or entry.get('vmess_configuration_schema_version') not in (None, 0) or entry.get('vmess_configuration_revision') not in (None, 0):
                        raise BackupError('referencias VMess incompletas en catálogo actual')
                else:
                    config_match = re.fullmatch(rf'configurations/{re.escape(cid)}\.r([0-9]{{6}})\.json', config_ref if isinstance(config_ref, str) else '')
                    if (not config_match or type(entry.get('vmess_configuration_schema_version')) is not int or
                            entry.get('vmess_configuration_schema_version') != 1 or
                            type(entry.get('vmess_configuration_revision')) is not int or
                            entry.get('vmess_configuration_revision') != int(config_match.group(1))):
                        raise BackupError('referencia de configuración VMess inválida')
                    config_dir = vmess_root / 'configurations'
                    safe_dir(vmess_root); safe_dir(config_dir)
                    config_path = config_dir / f'{cid}.r{int(config_match.group(1)):06d}.json'
                    safe_regular(config_path, vmess_store.MAX_CONFIG)
                    config = json.loads(config_path.read_text(encoding='utf-8'))
                    try:
                        vmess_store.validate(config, entry, secret_ref, allow_legacy_tls=True)
                    except Exception as exc:
                        raise BackupError('configuración VMess actual inválida') from exc
                    if secret_ref is not None:
                        secret_match = re.fullmatch(rf'secrets/{re.escape(cid)}\.r([0-9]{{6}})\.bin', secret_ref if isinstance(secret_ref, str) else '')
                        if not secret_match or int(secret_match.group(1)) != int(config_match.group(1)):
                            raise BackupError('referencia de secreto VMess inválida')
                        secret_dir = vmess_root / 'secrets'
                        safe_dir(secret_dir)
                        encrypted_limit = ((vmess_store.MAX_SECRET + 28 + 2) // 3) * 4 + 4096
                        safe_regular(secret_dir / f'{cid}.r{int(secret_match.group(1)):06d}.bin', encrypted_limit)
                current_vmess.append(entry)

    conflicts = restored_ids.intersection(entry['id'] for entry in current_vmess)
    if conflicts:
        raise BackupError('conflicto de IDs entre VLESS del backup y VMess actuales: ' + ', '.join(sorted(conflicts)))

    merged = vless_entries + current_vmess
    if len({entry['id'] for entry in merged}) != len(merged):
        raise BackupError('IDs duplicados en catálogo combinado')
    payload = (json.dumps(merged, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode()
    atomic_file(restored_path, payload)
    if restored_path.read_bytes() != payload:
        raise BackupError('falló la verificación del catálogo combinado')
    return {'vless_restored': len(vless_entries), 'vmess_preserved': len(current_vmess), 'total': len(merged)}


def restore_data(args):
    require_root()
    root=Path(args.backups).absolute(); base=Path(args.base).absolute(); secrets_dir=Path(args.secrets_dir).absolute(); key_path=Path(args.master_key).absolute()
    safe_dir(root)
    fds=lock_pair()
    stage_base=None; stage_secrets=None; old_base=None; old_secrets=None; swapped=[]
    try:
        # Toda lectura y validación efectiva del backup se realiza bajo los locks.
        if root.joinpath('RESTORE_IN_PROGRESS.json').exists(): raise BackupError('hay una restauración interrumpida; se requiere recuperación manual del journal')
        backup_dir=Path(args.backup_dir).absolute(); safe_dir(backup_dir)
        manifest=verify_data_dir(backup_dir)
        if key_path.exists():
            safe_dir(key_path.parent); safe_regular(key_path,32); key=key_path.read_bytes()
            if len(key)!=32: raise BackupError('clave maestra local inválida')
        elif manifest.get('encrypted_secret_blob_count',0):
            raise BackupError('falta clave maestra; use recuperación de clave antes de restaurar datos')
        else: key=None
        archive=(backup_dir/'backup.tar.gz').read_bytes()
        if not hmac.compare_digest(sha(archive),manifest.get('archive_sha256','')):
            raise BackupError('el archivo cambió durante la validación del backup')
        extracted=validate_payload(archive,manifest,key) if key is not None else validate_payload_no_secrets(archive,manifest)
        base_parent=base.parent; secrets_parent=secrets_dir.parent
        safe_dir(base_parent); safe_dir(secrets_parent)
        stage_base=Path(tempfile.mkdtemp(prefix='.vless-restore-connections.',dir=base_parent)); os.chmod(stage_base,0o700)
        stage_secrets=Path(tempfile.mkdtemp(prefix='.vless-restore-secrets.',dir=secrets_parent)); os.chmod(stage_secrets,0o700)
        for name,data in extracted.items():
            if name.startswith('connections/'):
                rel=PurePosixPath(name).relative_to('connections')
                dest=stage_base.joinpath(*rel.parts)
            elif name.startswith('secrets/'):
                rel=PurePosixPath(name).relative_to('secrets')
                dest=stage_secrets.joinpath(*rel.parts)
            else: raise BackupError('ruta inesperada durante preparación')
            dest.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
            fd=os.open(dest,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
            with os.fdopen(fd,'wb') as f: f.write(data); f.flush(); os.fsync(f.fileno())
        if not (stage_base/'connections.json').is_file(): raise BackupError('el backup no contiene catálogo')
        # El catálogo compartido se reconstruye con VLESS del backup y VMess
        # vigentes; los archivos VMess permanecen en su almacén independiente.
        merge_counts = merge_current_vmess_entries(stage_base, base)
        # Confirmación explícita: CLI interactiva; no acepta confirmación implícita.
        if not sys.stdin.isatty(): raise BackupError('restauración requiere terminal interactiva para confirmación')
        print(f"Se restaurarán {merge_counts['vless_restored']} conexiones VLESS y se conservarán {merge_counts['vmess_preserved']} conexiones VMess actuales desde {manifest['backup_id']}.")
        answer=input('Esto reemplazará los datos VLESS actuales y conservará las entradas VMess. Escribe RESTAURAR para continuar: ')
        if answer!='RESTAURAR': raise BackupError('restauración cancelada')
        if base.exists(): safe_dir(base)
        if secrets_dir.exists(): safe_dir(secrets_dir)
        had_connections=base.exists(); had_secrets=secrets_dir.exists()
        stamp=utc_now(); old_base=base_parent/f'.vless-connections-before-{stamp}'; old_secrets=secrets_parent/f'.vless-secrets-before-{stamp}'
        journal=root/'RESTORE_IN_PROGRESS.json'
        journal_data={'format':'xray-manager-restore-journal','backup_id':manifest['backup_id'],'stage_connections':str(stage_base),'stage_secrets':str(stage_secrets),'live_connections':str(base),'live_secrets':str(secrets_dir),'old_connections':str(old_base),'old_secrets':str(old_secrets),'had_connections':had_connections,'had_secrets':had_secrets,'phase':'prepared'}
        atomic_file(journal,(json.dumps(journal_data,sort_keys=True,indent=2)+'\n').encode())
        if had_connections:
            os.replace(base,old_base); fsync_dir(base_parent); swapped.append(('old_base',old_base,base))
        journal_data['phase']='connections_saved'; atomic_file(journal,(json.dumps(journal_data,sort_keys=True,indent=2)+'\n').encode())
        if had_secrets:
            os.replace(secrets_dir,old_secrets); fsync_dir(secrets_parent); swapped.append(('old_secrets',old_secrets,secrets_dir))
        journal_data['phase']='old_data_saved'; atomic_file(journal,(json.dumps(journal_data,sort_keys=True,indent=2)+'\n').encode())
        os.replace(stage_base,base); stage_base=None; fsync_dir(base_parent); swapped.append(('new_base',base,None))
        journal_data['phase']='connections_published'; atomic_file(journal,(json.dumps(journal_data,sort_keys=True,indent=2)+'\n').encode())
        os.replace(stage_secrets,secrets_dir); stage_secrets=None; fsync_dir(secrets_parent); swapped.append(('new_secrets',secrets_dir,None))
        journal_data['phase']='published'; atomic_file(journal,(json.dumps(journal_data,sort_keys=True,indent=2)+'\n').encode())
        # Validación final de referencias y autenticación sobre rutas publicadas.
        _,revs,certs=inspect_catalog(base)
        for e in json.loads((base/'connections.json').read_text()):
            if e.get('secret_ref'):
                sm=re.fullmatch(r'secrets/([A-Za-z0-9_.-]+)\.r([0-9]{6})\.bin',e['secret_ref'])
                if not sm: raise BackupError('referencia final inválida')
                crypto_path=secrets_dir/sm.group(1) if False else secrets_dir/f'{sm.group(1)}.r{int(sm.group(2)):06d}.bin'
                sys.path.insert(0,str(Path(__file__).resolve().parent)); import vless_crypto as crypto
                crypto.decrypt_secret(crypto_path.read_bytes(),key,e['id'],1)
        journal.unlink();
        return {'status':'restored','backup_id':manifest['backup_id'],'connections':merge_counts['total'],'vless_connections_restored':merge_counts['vless_restored'],'vmess_connections_preserved':merge_counts['vmess_preserved'],'previous_data_preserved':True,'previous_connections_path':str(old_base) if old_base.exists() else None,'previous_secrets_path':str(old_secrets) if old_secrets.exists() else None,'external_tls_dependencies':certs,'runtime_activated':False}
    except Exception:
        # Rollback best-effort en orden inverso. Si el proceso/host se interrumpe,
        # el journal persistente bloquea operaciones posteriores para evitar daño.
        try:
            if old_base and old_base.exists():
                if base.exists():
                    failed=base_parent/f'.vless-connections-failed-{utc_now()}'; os.replace(base,failed)
                os.replace(old_base,base)
            elif base.exists() and root.joinpath('RESTORE_IN_PROGRESS.json').exists():
                failed=base_parent/f'.vless-connections-failed-{utc_now()}'; os.replace(base,failed)
            if old_secrets and old_secrets.exists():
                if secrets_dir.exists():
                    failed=secrets_parent/f'.vless-secrets-failed-{utc_now()}'; os.replace(secrets_dir,failed)
                os.replace(old_secrets,secrets_dir)
            elif secrets_dir.exists() and root.joinpath('RESTORE_IN_PROGRESS.json').exists():
                failed=secrets_parent/f'.vless-secrets-failed-{utc_now()}'; os.replace(secrets_dir,failed)
            if root.joinpath('RESTORE_IN_PROGRESS.json').exists():
                fsync_dir(base_parent); fsync_dir(secrets_parent)
                root.joinpath('RESTORE_IN_PROGRESS.json').unlink(); fsync_dir(root)
        except Exception:
            pass
        raise
    finally:
        if stage_base and stage_base.exists():
            import shutil; shutil.rmtree(stage_base)
        if stage_secrets and stage_secrets.exists():
            import shutil; shutil.rmtree(stage_secrets)
        unlock_pair(fds)

def recover_interrupted_restore(args):
    """Revierte de forma conservadora un restore cuyo journal quedó pendiente."""
    require_root(); root=Path(args.backups).absolute(); base=Path(args.base).absolute(); secrets_dir=Path(args.secrets_dir).absolute()
    safe_dir(root)
    journal=root/'RESTORE_IN_PROGRESS.json'
    if not journal.exists(): raise BackupError('no hay una restauración interrumpida')
    fds=lock_pair()
    try:
        safe_regular(journal,64*1024)
        record=json.loads(journal.read_text(encoding='utf-8'))
        required={'format','backup_id','stage_connections','stage_secrets','live_connections','live_secrets','old_connections','old_secrets','had_connections','had_secrets','phase'}
        legacy_required=required-{'had_connections','had_secrets'}
        if not isinstance(record,dict) or set(record) not in (required,legacy_required) or record.get('format')!='xray-manager-restore-journal':
            raise BackupError('journal de restauración inválido; no se modificó ningún dato')
        legacy=set(record)==legacy_required
        if record['live_connections']!=str(base) or record['live_secrets']!=str(secrets_dir):
            raise BackupError('journal no corresponde a las rutas actuales; requiere intervención manual')
        if record['phase'] not in ('prepared','connections_saved','old_data_saved','connections_published','published'):
            raise BackupError('fase del journal desconocida; requiere intervención manual')
        if not legacy and (type(record['had_connections']) is not bool or type(record['had_secrets']) is not bool):
            raise BackupError('indicadores de estado previo inválidos; journal conservado')
        base_parent=base.parent; secrets_parent=secrets_dir.parent
        old_base=Path(record['old_connections']); old_secrets=Path(record['old_secrets'])
        stage_base=Path(record['stage_connections']); stage_secrets=Path(record['stage_secrets'])
        if old_base.parent!=base_parent or not old_base.name.startswith('.vless-connections-before-'):
            raise BackupError('ruta de respaldo previo en journal no permitida')
        if old_secrets.parent!=secrets_parent or not old_secrets.name.startswith('.vless-secrets-before-'):
            raise BackupError('ruta de secretos previos en journal no permitida')
        if stage_base.parent!=base_parent or not stage_base.name.startswith('.vless-restore-connections.'):
            raise BackupError('ruta staging de conexiones no permitida')
        if stage_secrets.parent!=secrets_parent or not stage_secrets.name.startswith('.vless-restore-secrets.'):
            raise BackupError('ruta staging de secretos no permitida')
        for path in (base,secrets_dir,old_base,old_secrets,stage_base,stage_secrets):
            if path.exists() or path.is_symlink(): safe_dir(path)
        # Journals antiguos no registraban had_*; se infiere conservadoramente
        # usando los nombres staging/old y el destino, cuyo estado refleja cada rename.
        if legacy:
            had_connections = old_base.exists() or (stage_base.exists() and base.exists())
            had_secrets = old_secrets.exists() or (stage_secrets.exists() and secrets_dir.exists())
        else:
            had_connections = record['had_connections']; had_secrets = record['had_secrets']
        for live,old,stage,label,had_original in (
                (base,old_base,stage_base,'connections',had_connections),
                (secrets_dir,old_secrets,stage_secrets,'secrets',had_secrets),
        ):
            if old.exists():
                if not had_original:
                    raise BackupError(f'existe respaldo previo inesperado para {label}; journal conservado')
                if live.exists():
                    failed=live.parent/f'.vless-{label}-interrupted-{utc_now()}'; os.replace(live,failed)
                os.replace(old,live)
            elif had_original:
                # Si el staging ya se publicó, el original debería seguir en
                # old. Si el staging sigue allí, el original debe seguir live.
                if not live.exists() or not stage.exists():
                    raise BackupError(f'falta el respaldo previo de {label}; journal conservado')
            else:
                if live.exists() and stage.exists():
                    raise BackupError(f'estado ambiguo para {label}; journal conservado')
                if not live.exists() and not stage.exists():
                    raise BackupError(f'falta el directorio nuevo y su staging de {label}; journal conservado')
                if live.exists():
                    failed=live.parent/f'.vless-{label}-interrupted-{utc_now()}'; os.replace(live,failed)
        fsync_dir(base_parent); fsync_dir(secrets_parent)
        # El staging no publicado se conserva en cuarentena para inspección.
        for stage,label in ((stage_base,'connections-stage'),(stage_secrets,'secrets-stage')):
            if stage.exists():
                quarantine=stage.parent/f'.vless-{label}-interrupted-{utc_now()}'
                os.replace(stage,quarantine)
        fsync_dir(base_parent); fsync_dir(secrets_parent)
        journal.unlink()
        fsync_dir(root)
        return {'status':'rolled_back','backup_id':record['backup_id'],'journal_removed':True,'quarantined_artifacts_preserved':True,'runtime_activated':False}
    finally: unlock_pair(fds)

def validate_payload_no_secrets(archive: bytes, manifest: dict):
    if manifest.get('encrypted_secret_blob_count',0): raise BackupError('se requiere clave maestra para autenticar secretos')
    extracted=_read_archive_members(archive,manifest,retain=True)
    raw=extracted.get('connections/connections.json')
    if raw is None or not isinstance(json.loads(raw),list): raise BackupError('catálogo restaurado inválido')
    return extracted

def _recover_key_locked(args):
    require_root()
    recovery=verify_recovery(Path(args.recovery_dir).absolute())
    backup_id=recovery['header']['backup_id']
    data_dir=Path(args.backups)/'data'/backup_id
    manifest=verify_data_dir(data_dir)
    if not manifest.get('encrypted_secret_blob_count'): raise BackupError('backup asociado no contiene secretos')
    if Path(args.master_key).exists() or Path(args.master_key).is_symlink(): raise BackupError('ya existe una clave maestra; no se sobrescribirá')
    password=getpass.getpass('Contraseña del archivo de recuperación: ')
    header=recovery['header']; salt=bytes.fromhex(header['salt']); nonce=bytes.fromhex(header['nonce'])
    derived=derive(password,salt); aad=json.dumps(header,sort_keys=True,separators=(',',':')).encode()
    try: key=AESGCM(derived).decrypt(nonce,bytes.fromhex(recovery['ciphertext']),aad)
    except Exception as exc: raise BackupError('contraseña incorrecta o archivo de recuperación alterado') from exc
    if len(key)!=32: raise BackupError('clave recuperada con longitud inválida')
    archive=(data_dir/'backup.tar.gz').read_bytes(); validate_payload(archive,manifest,key)
    key_path=Path(args.master_key); safe_dir(key_path.parent)
    fd=os.open(key_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
    try:
        os.fchown(fd,0,0); os.fchmod(fd,0o600)
        with os.fdopen(fd,'wb') as f: f.write(key); f.flush(); os.fsync(f.fileno())
        dfd=os.open(key_path.parent,os.O_RDONLY|getattr(os,'O_DIRECTORY',0)); os.fsync(dfd); os.close(dfd)
    except Exception:
        key_path.unlink(missing_ok=True); raise
    return {'status':'recovered','backup_id':backup_id,'master_key_installed':True,'overwrote_existing_key':False,'data_restore_required':True}

def recover_key(args):
    require_root()
    fds=lock_pair()
    try: return _recover_key_locked(args)
    finally: unlock_pair(fds)

def list_backups(args):
    root=Path(args.backups); result={'data':[],'recovery':[]}
    for kind in result:
        d=root/kind
        if not d.exists(): continue
        safe_dir(d)
        for p in sorted(d.iterdir()):
            if p.is_dir() and not p.is_symlink():
                result[kind].append({'backup_id':p.name,'path':str(p)})
    return {'status':'listed',**result,'automatic_deletion':False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('backup-data','restore-data','recover-restore','create-recovery','recover-key','list','verify-data','verify-recovery'))
    p.add_argument('--base',default=str(DEFAULT_BASE)); p.add_argument('--secrets-dir',default=str(DEFAULT_SECRETS)); p.add_argument('--master-key',default=str(DEFAULT_KEY)); p.add_argument('--backups',default=str(DEFAULT_BACKUPS)); p.add_argument('--backup-dir'); p.add_argument('--recovery-dir')
    a=p.parse_args()
    try:
        if a.action=='backup-data': result=create_data(a)
        elif a.action=='restore-data': result=restore_data(a)
        elif a.action=='recover-restore': result=recover_interrupted_restore(a)
        elif a.action=='create-recovery': result=create_recovery(a)
        elif a.action=='recover-key': result=recover_key(a)
        elif a.action=='list': result=list_backups(a)
        elif a.action=='verify-data': result={'status':'verified','manifest':verify_data_dir(Path(a.backup_dir))}
        else:
            recovery_dir=a.recovery_dir or a.backup_dir
            if not recovery_dir: raise BackupError('--recovery-dir requerido')
            result={'status':'verified','backup_id':verify_recovery(Path(recovery_dir))['header']['backup_id']}
        print(json.dumps(result,ensure_ascii=False,separators=(',',':'))); return 0
    except (BackupError,OSError,ValueError,KeyError,tarfile.TarError,json.JSONDecodeError) as exc:
        print(f'ERROR: {exc}',file=sys.stderr); return 1

if __name__=='__main__': raise SystemExit(main())
