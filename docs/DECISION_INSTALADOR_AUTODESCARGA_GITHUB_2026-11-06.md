# Decisión — bootstrap autenticado y descarga del proyecto desde GitHub

**Fecha:** 2026-11-06
**Rama:** `design/user-identity-association-v1`
**Estado:** APROBADA POR EL PROPIETARIO PARA IMPLEMENTACIÓN
**Autorización:** respuesta afirmativa del propietario al diseño de descarga autónoma y autenticación mediante Fine-grained PAT de solo lectura.

## 1. Objetivo

Permitir instalar Xray Core Manager en una VPS Ubuntu/Debian limpia descargando un único `install.sh`, sin clonar el repositorio ni conservar `.git`. El propio instalador obtendrá de GitHub el árbol completo de la revisión autorizada, verificará su integridad y desplegará los archivos en `/opt/xray-manager` y sus rutas de datos existentes.

## 2. Repositorio y revisión

- Repositorio privado: `Jaok04/xray-core-manager`.
- Rama autorizada fijada por el instalador: `design/user-identity-association-v1`.
- El instalador resuelve una sola vez el commit de la rama y descarga el archivo de distribución por ese SHA inmutable.
- No se permite cambiar silenciosamente a `main`, a otra rama o a una revisión distinta durante una misma instalación.
- El despliegue contiene los archivos versionados del proyecto, no el directorio `.git` ni su historial.

## 3. Autenticación

- Fine-grained Personal Access Token (PAT) de GitHub.
- Acceso limitado al repositorio `Jaok04/xray-core-manager`.
- Permiso `Contents: Read-only`; no requiere escritura, administración, Actions ni acceso a otros repositorios.
- El instalador acepta `XRAY_MANAGER_GITHUB_TOKEN` o solicita el token mediante entrada oculta.
- El token se utiliza en memoria para solicitudes HTTPS autenticadas; no se escribe en el árbol instalado, archivos de configuración, argumentos de procesos, logs ni historial de shell.
- No se almacena una credencial persistente ni se configura Git/SSH en la VPS de destino.
- Una descarga no autenticada, un token inválido, falta de permiso o error de API aborta antes de desplegar el código.

## 4. Bootstrap de un solo archivo

Como el repositorio es privado, la primera descarga de `install.sh` también requiere autenticación. La documentación proporcionará un comando de bootstrap que:

1. solicita el PAT de forma oculta;
2. obtiene `install.sh` mediante GitHub Contents API autenticada;
3. conserva el token únicamente en el entorno del proceso que invoca el instalador (o solicita el token de nuevo si no se preserva);
4. ejecuta `install.sh --install`.

El propio `install.sh`, cuando no detecta un árbol fuente completo a su lado, obtiene el helper de bootstrap desde el mismo commit resuelto, valida su hash SHA-256 fijado en el instalador y lo ejecuta.

## 5. Integridad de la distribución

- El helper se descarga desde GitHub Contents API y su SHA-256 se compara con una constante fijada en `install.sh`.
- El helper resuelve el SHA del commit y el SHA del árbol Git mediante la API autenticada.
- La descarga del archivo tarball se solicita por SHA de commit, no por nombre mutable de rama.
- Cada archivo extraído se contrasta con el objeto blob del árbol Git (SHA-1 Git `blob <size>\0<bytes>`), tamaño y modo.
- Se rechazan árboles truncados, archivos faltantes o adicionales, rutas absolutas/traversal, duplicados, symlinks, hardlinks, dispositivos, submódulos y modos no admitidos.
- La extracción ocurre en un directorio temporal privado; sólo después de verificar el árbol completo se entrega el origen al instalador existente.
- Si no puede verificarse cada archivo, se aborta sin desplegar código parcial.

La verificación autentica el contenido respecto del commit servido por GitHub mediante HTTPS y autenticación del repositorio. No se afirma que el commit esté firmado criptográficamente: el repositorio actualmente no tiene una política de firma de commits establecida.

## 6. Comportamiento de instalación preservado

- `--install` sigue siendo Manager-only por defecto.
- `--install --with-xray` sigue siendo la opción explícita para instalar Xray-core verificado y preparar la unidad.
- El servicio permanece detenido y deshabilitado.
- Se conservan locks, validación de rutas/symlinks, permisos, idempotencia, protección de datos y rechazo de destinos preexistentes ajenos.
- No se instala Certbot ni se realizan cambios de DNS, firewall, puertos, red o runtime.
- No se sobrescribe una instalación existente distinta. Las actualizaciones requieren un flujo separado y explícito.

## 7. No objetivos

- Hacer público el repositorio.
- Solicitar credenciales de escritura.
- Guardar PAT en la VPS.
- Instalar automáticamente Xray-core por defecto.
- Modificar `main` o `Xray-Normativa/`.
- Habilitar/iniciar `xray.service`.
- Convertir el instalador en un actualizador automático de instalaciones existentes.

## 8. Criterios de aceptación

1. Un `install.sh` descargado sin clonar el repositorio puede obtener el árbol privado con PAT read-only.
2. El commit se resuelve una sola vez y todas las operaciones usan ese SHA.
3. El helper y cada archivo del tarball se verifican antes del despliegue.
4. Token ausente/inválido, API fallida, árbol truncado, hash incorrecto, tarball malicioso o destino conflictivo abortan de forma segura.
5. No se conserva `.git` ni el token.
6. Manager-only y `--with-xray` mantienen sus comportamientos existentes.
7. Pruebas automatizadas cubren integridad, rutas maliciosas, archivos ausentes/adicionales, autenticación y fallos de red/API.
8. La regresión existente pasa y la documentación técnica/continuidad queda actualizada.
