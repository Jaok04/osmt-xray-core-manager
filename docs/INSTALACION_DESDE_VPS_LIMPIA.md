# Instalación desde una VPS limpia — descarga autenticada desde GitHub

## Requisitos

- Ubuntu o Debian con `apt-get`.
- Acceso de red HTTPS a `api.github.com` y `codeload.github.com`.
- Un Fine-grained Personal Access Token de GitHub:
  - Repository access: **Only select repositories**.
  - Repository: `Jaok04/xray-core-manager`.
  - Repository permissions: **Contents — Read-only**.
  - Expiración limitada y revocable.
- No se requiere Git, SSH, Deploy Key ni permiso de escritura.

### Crear el Fine-grained PAT

1. En GitHub, abre **Settings → Developer settings → Personal access tokens → Fine-grained tokens**.
2. Selecciona **Generate new token** y el propietario del repositorio.
3. En **Repository access**, selecciona **Only select repositories** y marca `xray-core-manager`.
4. En **Repository permissions**, deja **Contents: Read-only**. No concedas `Contents: Read and write`, administración, Actions ni permisos de otros repositorios.
5. Define una expiración razonable, genera el token y cópialo para introducirlo en la terminal de la VPS.

GitHub incluye Metadata read-only como permiso básico del token; no hace falta conceder permisos adicionales.

El PAT no debe pegarse como argumento ni guardarse en archivos. El bootstrap lo solicita sin eco y lo mantiene en memoria durante la instalación.

## Comando de instalación

Ejecutar el bloque completo en la terminal de la VPS. `sudo bash` solicita privilegios; el PAT se lee desde `/dev/tty` sin mostrarse.

```bash
sudo bash <<'BOOTSTRAP'
set -Eeuo pipefail

if ! command -v python3 >/dev/null 2>&1 || ! command -v dpkg-query >/dev/null 2>&1 || ! dpkg-query -s ca-certificates >/dev/null 2>&1; then
    apt-get update
    apt-get install -y --no-install-recommends python3 ca-certificates
fi

read -r -s -p 'Fine-grained GitHub PAT (Contents: Read-only): ' XRAY_MANAGER_GITHUB_TOKEN </dev/tty
printf '\n'
[[ -n "$XRAY_MANAGER_GITHUB_TOKEN" ]] || { echo 'Token vacío.' >&2; exit 1; }
export XRAY_MANAGER_GITHUB_TOKEN

BOOTSTRAP_DIR="$(mktemp -d /var/tmp/xray-manager-bootstrap-download.XXXXXX)"
chmod 700 "$BOOTSTRAP_DIR"
trap 'rm -rf -- "$BOOTSTRAP_DIR"; unset XRAY_MANAGER_GITHUB_TOKEN XRAY_MANAGER_GITHUB_COMMIT_SHA' EXIT

python3 - "$BOOTSTRAP_DIR/install.sh" "$BOOTSTRAP_DIR/commit" <<'PY'
import base64
import hashlib
import json
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

repo = 'Jaok04/xray-core-manager'
branch = 'design/user-identity-association-v1'
token = os.environ['XRAY_MANAGER_GITHUB_TOKEN']
headers = {
    'Authorization': 'Bearer ' + token,
    'Accept': 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
    'User-Agent': 'xray-core-manager-installer-bootstrap',
}
api = 'https://api.github.com'

def get_json(url):
    try:
        with urlopen(Request(url, headers=headers), timeout=45) as response:
            raw = response.read(32 * 1024 * 1024 + 1)
    except HTTPError as exc:
        raise SystemExit('GitHub rechazó la solicitud (HTTP %s). Verifique PAT y permiso Contents: Read-only.' % exc.code)
    except (URLError, TimeoutError, OSError):
        raise SystemExit('No se pudo conectar con GitHub por HTTPS.')
    if len(raw) > 32 * 1024 * 1024:
        raise SystemExit('Respuesta API demasiado grande.')
    try:
        value = json.loads(raw.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise SystemExit('GitHub devolvió JSON inválido.')
    if not isinstance(value, dict):
        raise SystemExit('Estructura API inesperada.')
    return value

commit_data = get_json(f'{api}/repos/{repo}/commits/{quote(branch, safe="")}')
commit_sha = commit_data.get('sha')
tree_sha = (commit_data.get('commit') or {}).get('tree', {}).get('sha')
if not isinstance(commit_sha, str) or not re.fullmatch(r'[0-9a-f]{40}', commit_sha):
    raise SystemExit('SHA de commit inválido.')
if not isinstance(tree_sha, str) or not re.fullmatch(r'[0-9a-f]{40}', tree_sha):
    raise SystemExit('SHA de árbol inválido.')
tree = get_json(f'{api}/repos/{repo}/git/trees/{tree_sha}?recursive=1')
if tree.get('sha') != tree_sha or tree.get('truncated') is not False:
    raise SystemExit('Árbol Git inconsistente o truncado.')
entry = next((item for item in tree.get('tree', []) if item.get('path') == 'install.sh'), None)
if not isinstance(entry, dict) or entry.get('type') != 'blob' or entry.get('mode') != '100755':
    raise SystemExit('No se encontró install.sh ejecutable en el commit.')
blob = get_json(f'{api}/repos/{repo}/git/blobs/{entry["sha"]}')
if blob.get('encoding') != 'base64' or not isinstance(blob.get('content'), str):
    raise SystemExit('GitHub no entregó install.sh como blob base64.')
try:
    data = base64.b64decode(''.join(blob['content'].split()), validate=True)
except (ValueError, TypeError):
    raise SystemExit('Contenido base64 de install.sh inválido.')
git_sha = hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()
if git_sha != entry.get('sha'):
    raise SystemExit('La integridad Git de install.sh no coincide con el commit.')
with open(sys.argv[1], 'xb') as output:
    output.write(data)
with open(sys.argv[2], 'x', encoding='ascii') as output:
    output.write(commit_sha + '\n')
print('[OK] install.sh verificado para commit ' + commit_sha)
PY

export XRAY_MANAGER_GITHUB_COMMIT_SHA="$(cat "$BOOTSTRAP_DIR/commit")"
bash "$BOOTSTRAP_DIR/install.sh" --install
BOOTSTRAP
```

## Qué hace el instalador

1. El bootstrap obtiene `install.sh` desde GitHub Contents API y verifica su Git blob SHA contra el árbol del commit.
2. El instalador autentica nuevamente las solicitudes necesarias usando el PAT en memoria.
3. Resuelve/respeta el mismo SHA inmutable del commit y verifica el helper de bootstrap contra un SHA-256 fijado en `install.sh`.
4. Descarga el tarball de ese commit, sin historial Git ni `.git`.
5. Contrasta todos los archivos con los SHA Git blob, tamaños y modos del árbol; rechaza archivos faltantes/adicionales, rutas traversal, symlinks, hardlinks, submódulos y árboles truncados.
6. Sólo después de verificar el árbol completo despliega el proyecto en `/opt/xray-manager`.
7. Instala dependencias faltantes, sin ejecutar `apt upgrade`.

## Modalidades

- `--install`: Manager-only; Xray-core no se instala ni se prepara automáticamente.
- `--install --with-xray`: instala Xray-core con la verificación SHA-256 existente y prepara `xray.service`, que queda detenido y deshabilitado.
- `--check`: se utiliza desde el árbol completo ya desplegado, por ejemplo `sudo /opt/xray-manager/install.sh --check`. Un `install.sh` aislado no puede hacer `--check` porque aún no tiene el árbol de código.

El instalador no sobrescribe una instalación existente distinta ni actúa como actualizador. Tampoco configura DNS, firewall, puertos, certificados ACME ni inicia el servicio.

## Credenciales y privacidad

El PAT requiere exclusivamente `Contents: Read-only` para este repositorio. No se guarda en `/etc`, `/root`, `/opt/xray-manager`, preferencias, logs ni historial. Se elimina de las variables del proceso después de la descarga. No se configura Git ni SSH en la VPS.

La integridad se verifica respecto del commit obtenido de GitHub por HTTPS autenticado. Este mecanismo no afirma que los commits estén firmados criptográficamente; el repositorio no tiene actualmente una política de firma de commits establecida.
