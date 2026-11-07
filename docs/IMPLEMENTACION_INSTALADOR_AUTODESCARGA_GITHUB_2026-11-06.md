# Implementación — instalador autónomo con descarga autenticada de GitHub

**Fecha:** 2026-11-06
**Rama:** `design/user-identity-association-v1`
**Estado:** IMPLEMENTADO Y VERIFICADO EN PRUEBAS AUTOMATIZADAS; validación real con PAT en VPS limpia pendiente.
**Decisión aprobada:** `docs/DECISION_INSTALADOR_AUTODESCARGA_GITHUB_2026-11-06.md`.

## 1. Resultado

`install.sh` ya no requiere que el usuario clone el repositorio para una instalación nueva. Cuando detecta que sólo se dispone del archivo `install.sh`, obtiene el árbol completo del repositorio privado, verifica la revisión y los archivos y luego continúa con el flujo de instalación existente.

## 2. Archivos

- `install.sh`: detecta árbol local completo o activa bootstrap remoto; fija repositorio/rama; solicita/recibe PAT; verifica el helper; ejecuta la descarga autenticada y conserva el flujo Manager-only / `--with-xray`.
- `scripts/installer_bootstrap.py`: descarga el tarball por SHA de commit y valida el árbol completo antes de escribirlo en el directorio temporal.
- `tests/test_installer_bootstrap.py`: pruebas de autenticación, fijación de commit, verificación de helper/blob, tarball, modos y ataques de rutas.
- `tests/install.sh`: verifica la huella SHA-256 fijada en `install.sh`, la rama y la regresión de instalación aislada.
- `docs/INSTALACION_DESDE_VPS_LIMPIA.md`: procedimiento completo para obtener el primer `install.sh` autenticado desde una VPS limpia.
- `README.md`, `docs/INSTALADOR_FASE_A_MANAGER.md` y `docs/INSTALADOR_FASE_B_XRAY_SERVICE.md`: uso y alcance actualizados.

## 3. Flujo implementado

1. El bootstrap documentado solicita el Fine-grained PAT sin eco y consulta GitHub API.
2. Resuelve el SHA del commit de `design/user-identity-association-v1` una sola vez.
3. Obtiene el blob `install.sh` de ese commit, comprueba su Git blob SHA y lo guarda temporalmente.
4. El `install.sh` descargado conserva ese SHA mediante `XRAY_MANAGER_GITHUB_COMMIT_SHA`.
5. `install.sh` obtiene el árbol Git recursivo, el blob del helper y valida el helper con SHA-256 fijado en el propio instalador.
6. El helper descarga el tarball de ese SHA inmutable.
7. Cada archivo se contrasta con su blob SHA-1 Git, tamaño y modo del árbol. Se rechazan árboles truncados, tipos especiales, symlinks, hardlinks, submódulos, rutas inseguras, duplicados, archivos faltantes/adicionales y destinos temporales no vacíos.
8. Sólo después de verificar todos los archivos se continúa con las comprobaciones y el despliegue en `/opt/xray-manager`.
9. El temporal se elimina al terminar. No se conserva `.git`, historial ni credencial.

## 4. Autenticación y manejo de secretos

- Fine-grained PAT limitado al repositorio `Jaok04/xray-core-manager`.
- Permiso requerido: `Contents: Read-only`.
- Se acepta `XRAY_MANAGER_GITHUB_TOKEN` o se solicita con entrada oculta.
- El token viaja en la cabecera HTTPS `Authorization: Bearer`; no se pasa como argumento, no se incluye en URLs y no se escribe en disco.
- No se configura SSH, Deploy Key, Git ni credencial persistente en la VPS destino.
- En caso de 401/403/404, falta de permiso o fallo de red/API, el bootstrap aborta antes de desplegar.

## 5. Comportamiento preservado

- `--install` continúa siendo Manager-only por defecto.
- `--install --with-xray` conserva la instalación verificada de Xray-core y preparación de unidad, detenida y deshabilitada.
- No se ejecuta `apt upgrade`; se instalan sólo dependencias faltantes.
- No se sobrescribe un destino `/opt/xray-manager` preexistente y distinto.
- No se realizan operaciones de DNS, firewall, puertos, Certbot, certificados persistentes ni runtime.
- `--check` requiere el árbol completo; desde una VPS limpia se utiliza el procedimiento `--install`.

## 6. Pruebas ejecutadas

- `tests/test_installer_bootstrap.py`: 18/18 PASS.
- Regresión Python global: 406/406 PASS.
- Suites Bash: 62/62 PASS.
- `tests/install.sh`: PASS.
- `python3 -m compileall -q scripts tests`: PASS.
- `bash -n` global: PASS.
- ShellCheck `-S error` global: PASS.
- `./install.sh --check`: PASS; no modificó el sistema.
- `git diff --check`: PASS.
- El extractor verificó un archivo `git archive` local de HEAD: 330/330 archivos, conservando los modos ejecutables.

## 7. Límites de validación

- No se ejecutó una descarga autenticada real desde GitHub con un PAT del propietario.
- No se ejecutó el bootstrap de un solo archivo en la VPS nueva del propietario.
- No se instaló el Manager en esa VPS ni se ejecutó `--with-xray`.
- No se ejecutó Xray/systemd real ni se modificaron DNS, firewall, puertos, certificados o red.
- No se guardó ni solicitó al propietario su PAT durante esta implementación.
- No se afirma que los commits estén firmados criptográficamente; la integridad se ancla al commit/tree de GitHub obtenido por HTTPS autenticado.

## 8. Estado

La implementación y las pruebas aisladas están listas para revisión. El criterio final de aceptación operativa requiere que el propietario ejecute el comando de `docs/INSTALACION_DESDE_VPS_LIMPIA.md` en su VPS nueva y comparta la salida, ocultando cualquier dato sensible. No se debe pegar el PAT en el chat.
