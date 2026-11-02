# P4 — Backup y recuperación segura de persistencia VLESS

**Estado del incremento:** IMPLEMENTADO, VERIFICADO Y ACEPTADO por el propietario el 2026-11-02. P4 se considera COMPLETADA dentro del alcance definido en este documento.
**Fecha:** 2026-11-02
**Rama autorizada:** `design/user-identity-association-v1`

## 1. Alcance

P4 incorpora un subsistema específico para el almacén VLESS. No reutiliza el backup temporal de desinstalación ni los respaldos de actualización de Xray Core.

Rutas:

- Datos: `/var/backups/xray-manager/vless/data/<backup_id>/`
- Recuperación de clave: `/var/backups/xray-manager/vless/recovery/<backup_id>/`
- Catálogo/configuración: `/var/lib/xray-manager/connections/`
- Blobs cifrados: `/var/lib/xray-manager/secrets/`
- Clave maestra local: `/etc/xray-manager/keys/master.key`

El directorio `vless` y sus subdirectorios se crean root-only (`0700`); archivos `0600`. No se cambió el modo del directorio histórico `/var/backups/xray-manager` ni se modificaron backups existentes.

## 2. Backup de datos

`python3 scripts/vless_backup.py backup-data`:

1. Adquiere `lifecycle.lock` y después `integrity.lock`.
2. Valida propietarios, permisos, tipos de archivo, enlaces simbólicos y límites.
3. Incluye `connections.json`, revisiones JSON y blobs secretos cifrados.
4. No incluye ni descifra la clave maestra.
5. Crea `backup.tar.gz`, `manifest.json` y `SHA256SUMS` en un directorio de publicación único.
6. Verifica el archivo, rutas, contenido, tamaños y hashes antes de devolver éxito.

El manifiesto registra IDs/revisiones, conteo de blobs, versiones de esquema/formato, SHA-256, fecha UTC y dependencias TLS externas. Las rutas de certificados TLS se documentan como dependencias externas; no se copian certificados ni claves externas.

No se aplica retención ni eliminación automática.

## 3. Backup de recuperación de clave

`create-recovery` requiere que exista la clave maestra y que se seleccione un backup de datos que contenga blobs cifrados. La contraseña se solicita dos veces mediante `getpass`; no se pasa por argumentos ni se almacena.

- KDF: scrypt (`N=32768`, `r=8`, `p=1`, salida de 32 bytes).
- Cifrado: AES-256-GCM, salt de 16 bytes y nonce de 12 bytes aleatorios.
- El encabezado autenticado vincula el paquete al `backup_id` de datos.
- El archivo contiene la clave cifrada, nunca la clave en claro.
- No se sobrescribe un paquete de recuperación existente.

El paquete debe copiarse fuera de la VPS. La contraseña debe ser independiente de root y de las cuentas del servidor. Perder la contraseña y la única copia del paquete impide recuperar la clave.

## 4. Verificación y restauración

`verify-data` comprueba SHA256SUMS, hash del archivo, manifiesto, rutas, tipos, tamaños, lista de miembros y hashes individuales.

`restore-data`:

- exige confirmación interactiva escribiendo `RESTAURAR`;
- exige la clave maestra local cuando el backup contiene secretos;
- adquiere `lifecycle.lock` y después `integrity.lock` antes de leer/revalidar el backup, leer la clave, extraer y validar los datos; no reutiliza contenido extraído antes del lock;
- valida autónomamente en el lector de payload los nombres/rutas relativas, tipos regulares, enlaces, duplicados, cantidad, tamaños individuales/agregados y hashes del manifiesto;
- autentica los blobs AES-GCM y sus AAD antes de publicar los datos;
- prepara directorios de staging y reemplaza los directorios de conexiones y secretos mediante renombrados dentro de sus respectivos padres;
- conserva los directorios previos con nombres `.vless-*-before-*` como respaldo preventivo;
- no aplica runtime ni modifica firewall/puertos.

Los dos directorios no pueden sustituirse con una única operación atómica global. Se escribe `RESTORE_IN_PROGRESS.json` antes de los renombrados. El journal nuevo registra `had_connections` y `had_secrets`, es decir, si cada directorio existía antes de iniciar. Cada renombrado de publicación/respaldo fuerza (`fsync`) el directorio padre antes de avanzar la fase del journal. Si el proceso recibe una excepción ordinaria, intenta rollback; si hay una interrupción abrupta del proceso/host, el journal permanece y las siguientes restauraciones fallan de forma cerrada. La opción `recover-restore` resuelve el journal con rollback conservador: devuelve los directorios previos a sus rutas y conserva los artefactos parciales/staging en cuarentena, sin borrarlos. También admite journals anteriores que no contenían `had_*`, infiriendo la existencia previa a partir de los nombres `old`, `stage` y `live`. Si las rutas no concuerdan, faltan respaldos requeridos o el estado es ambiguo, falla sin eliminar el journal y exige intervención manual.

`recover-key` valida el paquete, exige la contraseña, comprueba que el backup de datos emparejado existe y autentica todos sus blobs con la clave recuperada. Solo instala la clave si no existe una clave local; nunca sobrescribe una clave existente. Después se debe ejecutar la restauración de datos asociada.

## 5. Integración

El menú de conexiones incorpora `Backup y recuperación VLESS`, con opciones para crear backup, restaurar datos, crear/recuperar paquete de clave, listar y verificar.

## 6. Pruebas ejecutadas

- `tests/vless_backup.sh`: backup aislado, manifiesto, hash y rechazo de manipulación.
- `tests/vless_backup_limits.sh`: límite agregado, rechazo autónomo de traversal/symlink y validación positiva.
- `tests/vless_backup_restore.sh`: restauración aislada de catálogo, confirmación y conservación de datos previos.
- `tests/vless_backup_recovery.sh`: paquete scrypt/AES-GCM, asociación por `backup_id`, contraseña incorrecta/correcta y recuperación autenticada en directorio temporal.
- `tests/vless_backup_journal.sh`: rollback de journal nuevo y legacy, destino originalmente ausente, preservación de originales y cuarentena.
- `tests/vless_backup_journal_crash_matrix.sh`: 32 interrupciones abruptas con `os._exit`, cubriendo las escrituras de fases del journal, renombrados de originales, publicación de ambos directorios y las cuatro combinaciones de existencia previa de `connections/` y `secrets/`.
- `tests/vless_backup_restore_secrets.sh`: restore end-to-end de blobs REALITY/TLS, autenticación AES-GCM y certificado TLS externo referenciado pero ausente; la restauración conserva la dependencia, no la incorpora al backup y no activa runtime.
- Suite completa tras corrección de journal: 31/31 PASS. Suite posterior a los límites y TOCTOU: 32/32 PASS (2026-11-02).
- `install.sh --check`, `bash -n` de todos los `.sh`, `py_compile`, ShellCheck y `shfmt` de las pruebas modificadas, y `git diff --check`: PASS en la revisión final.

Publicación en GitHub: commit `90766d4cb8000ed1f94fb808b80f18483d5778cb` en `design/user-identity-association-v1`; árbol `cfdb26fd7716f622127ba5d7784884df58799b4c`. La VPS quedó sincronizada con `origin` y el working tree limpio.

No se creó ni leyó la clave maestra real de esta VPS; tampoco se creó un backup operativo. Todas las pruebas de restauración se ejecutaron en directorios temporales.

## 7. Cierre y aceptación formal

El propietario aceptó formalmente las correcciones de seguridad adicionales el 2026-11-02. Con la suite completa en 32/32 PASS, las verificaciones estáticas satisfactorias y la publicación sincronizada, **P4 queda COMPLETADA** para el alcance de backup, verificación, recuperación de clave y restauración segura de datos VLESS descrito aquí.

Quedan fuera del alcance de P4 la activación de conexiones, aplicación de configuración Xray, inicio/reinicio de Xray, apertura de puertos, cambios de firewall y despliegue de certificados externos. Cualquier ampliación futura deberá tratarse como una nueva etapa/cambio, no como una condición pendiente de esta aceptación.

**No forma parte de P4:** activar conexiones, aplicar configuración Xray, iniciar/reiniciar Xray, abrir puertos, cambiar firewall, ni desplegar certificados externos.


## 8. Auditoría adicional: límites y consistencia de restauración — 2026-11-02

Se añadió `MAX_TOTAL_UNCOMPRESSED = 512 MiB`. El límite se aplica al recolectar archivos para backup, al construir el tar y al leer/verificar/extractar miembros. La validación de miembros mantiene un máximo de 64 MiB por archivo y 20.000 entradas, verifica hashes mientras lee en bloques y evita retener datos durante la verificación. Durante la restauración se retienen como máximo 512 MiB de contenido extraído, además del archivo comprimido acotado a 512 MiB.

La restauración ahora adquiere ambos locks antes de verificar y leer el backup, comprobar la clave y extraer el contenido. El lector común valida por sí mismo nombres de ruta, traversal, tipos, symlinks/hardlinks, duplicados, cantidad, tamaños y hashes del manifiesto, incluso si se invoca sin una validación estructural previa. El hash del archivo se vuelve a comprobar sobre los mismos bytes que se entregan al lector.

Prueba focal nueva: `tests/vless_backup_limits.sh` (límite agregado, traversal, symlink y caso positivo). Suite completa posterior: 32/32 PASS. El propietario aceptó formalmente estas correcciones el 2026-11-02; P4 queda COMPLETADA.


## 9. Corrección posterior: preservar VMess durante restauraciones VLESS — 2026-11-02

**Estado del incremento:** IMPLEMENTADO, VERIFICADO, PUBLICADO y SINCRONIZADO; aceptación formal específica pendiente del propietario. Commit `c890b5b5362e17e439f198b9b8bbbdbe0af0c653`. Esta corrección posterior no amplía el contenido del backup VLESS ni modifica la aceptación histórica del alcance P4 original.

### 9.1 Comportamiento

El catálogo `connections.json` es compartido por VLESS y VMess, aunque sus almacenes de configuración y secretos son independientes. Antes de esta corrección, `restore-data` sustituía el directorio `connections/` completo con la instantánea del backup. Eso podía revertir o eliminar entradas VMess creadas después del backup y dejar referencias VMess sin registro.

La restauración ahora prepara el catálogo de publicación combinando:
- Las entradas VLESS contenidas en el backup seleccionado.
- Las entradas VMess que existen en el catálogo vigente inmediatamente antes de la restauración.

Las entradas VMess históricas presentes en la instantánea del backup no prevalecen sobre las entradas actuales. Las entradas VMess vigentes se conservan completas, incluidos `vmess_configuration_ref`, `vmess_secret_ref`, `vmess_configuration_revision` y `vmess_configuration_schema_version`. Los archivos de `/var/lib/xray-manager/vmess/` no se copian, reemplazan, modifican ni incorporan al backup VLESS.

### 9.2 Validaciones y fallo seguro

La combinación se realiza mientras se mantienen `lifecycle.lock` e `integrity.lock`, antes de crear el journal o publicar directorios. Se valida el catálogo actual, la unicidad de IDs, las modalidades VMess, la coherencia de las referencias y la existencia/seguridad de los archivos VMess referenciados. También se verifica el catálogo combinado después de su escritura atómica en staging.

La restauración se detiene antes de publicar si el catálogo actual falta o es ilegible, contiene registros/IDs inválidos, referencias VMess rotas, una modalidad desconocida, un protocolo no cubierto por esta operación o una colisión entre el ID VLESS restaurado y un ID VMess vigente. Los errores de escritura del catálogo combinado tampoco modifican el catálogo activo.

El resultado informa por separado las conexiones VLESS restauradas, las VMess preservadas y el total combinado. Se mantiene la confirmación interactiva `RESTAURAR`, el journal, el rollback, la conservación preventiva de directorios anteriores y la ausencia de activación runtime.

### 9.3 Pruebas y evidencia

- `tests/vless_restore_preserves_vmess.sh`: backup con VMess histórico; VMess creado antes y después del backup; restauración VLESS; preservación de referencias de configuración y secreto; almacén VMess byte a byte sin cambios; rechazo de IDs duplicados; catálogo corrupto; referencias rotas; y fallo de escritura staging sin modificación del catálogo activo.
- `tests/vless_backup_journal_crash_matrix.sh`: sus fixtures ahora usan un catálogo JSON válido que incluye una entrada VMess sin configuración, de modo que las 32 interrupciones siguen probando fases/renombrados y rollback bajo el nuevo contrato de validación.
- Suite completa `tests/*.sh`: 37/37 scripts PASS.
- `python3 -m py_compile scripts/*.py`, `bash -n` de todos los scripts Bash, `install.sh --check`, ShellCheck (`-S warning`) sobre las pruebas modificadas y `git diff --check`: PASS.
- Las pruebas se ejecutaron con directorios temporales; no se creó un backup operativo ni se leyó/creó la clave maestra real de la VPS.

**Límites:** el backup continúa siendo exclusivamente VLESS; backup/restore VMess no se implementa aquí. No se modificaron runtime, servicio, firewall, puertos, certificados desplegados ni la documentación normativa preliminar.
