# P4 — Backup y recuperación segura de persistencia VLESS

**Estado del incremento:** corrección del journal implementada y verificada; P4 continúa abierta hasta completar la auditoría de límites/permisos y recibir aceptación formal.
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
- `tests/vless_backup_restore.sh`: restauración aislada de catálogo, confirmación y conservación de datos previos.
- `tests/vless_backup_recovery.sh`: paquete scrypt/AES-GCM, asociación por `backup_id`, contraseña incorrecta/correcta y recuperación autenticada en directorio temporal.
- `tests/vless_backup_journal.sh`: rollback de journal nuevo y legacy, destino originalmente ausente, preservación de originales y cuarentena.
- `tests/vless_backup_journal_crash_matrix.sh`: 32 interrupciones abruptas con `os._exit`, cubriendo las escrituras de fases del journal, renombrados de originales, publicación de ambos directorios y las cuatro combinaciones de existencia previa de `connections/` y `secrets/`.
- `tests/vless_backup_restore_secrets.sh`: restore end-to-end de blobs REALITY/TLS, autenticación AES-GCM y certificado TLS externo referenciado pero ausente; la restauración conserva la dependencia, no la incorpora al backup y no activa runtime.
- Suite completa final `tests/*.sh`: 31/31 PASS (2026-11-02, después de la corrección del journal).
- `install.sh --check`, `bash -n` de todos los `.sh`, `py_compile`, ShellCheck y `shfmt` de las pruebas modificadas, y `git diff --check`: PASS en la revisión final.

No se creó ni leyó la clave maestra real de esta VPS; tampoco se creó un backup operativo. Todas las pruebas de restauración se ejecutaron en directorios temporales.

## 7. Pendientes antes de aceptación

1. Auditar límites agregados de extracción/descompresión, memoria, número/tamaño total de archivos y rutas de staging/publicación; ajustar límites si la auditoría lo requiere.
2. Revisar el diff completo y repetir la suite completa después de la revisión final.
3. Obtener aceptación formal del propietario.

**No forma parte de P4:** activar conexiones, aplicar configuración Xray, iniciar/reiniciar Xray, abrir puertos, cambiar firewall, ni desplegar certificados externos.
