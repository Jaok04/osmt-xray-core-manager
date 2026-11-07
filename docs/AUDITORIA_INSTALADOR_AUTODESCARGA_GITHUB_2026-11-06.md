# Auditoría — instalador autónomo y descarga privada de GitHub

**Fecha:** 2026-11-06
**Dictamen:** PASS EN PRUEBAS AUTOMATIZADAS — VALIDACIÓN GITHUB/VPS REAL PENDIENTE
**Alcance:** bootstrap de un único `install.sh`, autenticación PAT read-only, fijación de commit, integridad del helper y del árbol de distribución.
**Tipo de revisión:** auditoría interna de implementación; no independiente.

## 1. Controles revisados

- Repositorio y rama están fijados a `Jaok04/xray-core-manager` y `design/user-identity-association-v1`.
- El bootstrap obtiene `install.sh` de un commit resuelto por API y verifica el Git blob SHA.
- El instalador verifica el helper con SHA-256 fijado en `install.sh`.
- El helper descarga el tarball por SHA inmutable, no por rama mutable.
- El árbol recursivo debe declarar `truncated=false` y coincidir con el tree SHA del commit.
- Cada archivo debe coincidir con blob SHA-1 Git, tamaño y modo esperado.
- Se rechazan symlinks, hardlinks, submódulos, archivos especiales, rutas absolutas/traversal, duplicados, archivos extra/faltantes y árboles no completos.
- La extracción se realiza en un temporal privado; el instalador sólo recibe el árbol después de validar el conjunto completo.
- El PAT se envía en cabecera HTTPS, no en argumentos/URLs/logs ni en archivos persistentes.
- La credencial se solicita sin eco o se recibe por variable de entorno; no se configura almacenamiento persistente.
- La instalación predeterminada sigue siendo Manager-only; `--with-xray` sigue siendo explícito.
- `main` y `Xray-Normativa/` no forman parte del alcance ni se modificaron.

## 2. Pruebas adversariales

`tests/test_installer_bootstrap.py`: 18/18 PASS, incluyendo:

- Git blob hash y modo ejecutable.
- Hash de archivo alterado.
- Archivo faltante o adicional.
- Path traversal y ruta de directorio insegura.
- Symlink/hardlink en tarball.
- Symlink mode en árbol Git.
- Miembros duplicados.
- Árbol truncado o sin archivos esenciales.
- Destino de extracción no vacío.
- SHA tree incoherente.
- Autenticación HTTP 401 sin filtrar el token.
- URL de descarga fijada al commit y token únicamente en cabecera.
- Descarga del helper del commit y rechazo de SHA-256 incorrecto.

## 3. Regresión

- Python global: 406/406 PASS.
- Bash: 62/62 suites PASS.
- `tests/install.sh`: PASS.
- `compileall`: PASS.
- `bash -n` global: PASS.
- ShellCheck `-S error` global: PASS.
- `install.sh --check`: PASS, no modificó el sistema.
- `git diff --check`: PASS.
- Extractor contra archivo Git local: 330/330 archivos verificados.

## 4. Límites y riesgos residuales

- No se probó GitHub API en vivo con un PAT real del propietario. El transporte, permisos efectivos del token, redirect al host codeload y descarga privada real deben validarse desde la VPS nueva.
- No se ejecutó una instalación real desde el archivo único.
- El repositorio no aplica actualmente firma criptográfica obligatoria de commits. El control de integridad liga todos los archivos al commit/tree recibido de GitHub por HTTPS autenticado; no debe describirse como firma digital del autor.
- Si GitHub cambia el formato del tarball, el endpoint, el esquema API o el comportamiento del redirect, el bootstrap debe fallar cerrado y requerirá adaptación.
- El helper y el instalador son código privilegiado: su confianza depende de la revisión protegida del repositorio, TLS y custodia del PAT.

## 5. Dictamen

PASS en pruebas automatizadas y revisión de código. El flujo remoto no se declara validado end-to-end hasta que el propietario ejecute la instalación de un solo archivo en una VPS limpia con un PAT Fine-grained limitado a Contents: Read-only. No se autoriza por esta auditoría iniciar Xray, instalar Certbot ni modificar DNS/firewall/puertos.
