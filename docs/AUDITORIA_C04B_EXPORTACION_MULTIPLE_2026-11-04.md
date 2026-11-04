# Auditoría C-04B — exportación múltiple de configuraciones independientes

**Fecha:** 2026-11-04
**Rama:** `design/user-identity-association-v1`
**Host/ruta:** `Implementación-Xray:/opt/xray-manager`
**Autorización:** el propietario autorizó expresamente C-04B después de la aceptación/publicación de C-04A. La autorización no incluye C-04C, publicación, commit, push ni sincronización.

## 1. Alcance y contraste normativo

C-04B implementa exportación de varias configuraciones/revisiones independientes mediante manifiesto JSON explícito. Se contrastó con `Xray-Normativa/05_Configuraciones_Perfiles/Etapa_5_Configuraciones_Perfiles.md`, §§3 y 3.1, y con el contrato de exportación de `docs/DISENO_GESTOR_CONFIGURACIONES_INDEPENDIENTES.md`, §5.5.

Se mantienen las reglas: exportación explícita; destino por cada salida; no seguir symlinks; no sobrescribir sin autorización; escritura atómica; modo restrictivo; relectura y verificación byte a byte; advertencia de contenido en claro; un fallo individual no cancela las demás exportaciones.

## 2. CLI incorporada

- `preview-export-batch --manifest /ruta/absoluta/manifest.json`
- `export-batch --manifest /ruta/absoluta/manifest.json --expected-manifest-sha256 HASH --expected-preview-sha256 HASH --confirm`

El manifiesto tiene contrato cerrado:

- raíz exacta: `schema_version`, `exports`;
- `schema_version` entero exacto `1`;
- entre 1 y 100 entradas;
- cada entrada contiene exactamente `config_id`, `revision`, `destination`, `overwrite`;
- `revision` es `null` para la revisión actual o un identificador `rNNNNNN` explícito;
- destino absoluto individual;
- `overwrite` booleano exacto por entrada.

El archivo de manifiesto debe ser regular, root:root, modo 0600, sin symlink/hardlink y no superar 1 MiB. JSON con claves duplicadas, campos adicionales, tipos incorrectos o entradas fuera de límite se rechaza.

## 3. Vista previa y confirmación optimista

La vista previa valida cada elemento por separado: existencia/identidad de la configuración, revisión autenticada, ruta y directorio destino, estado del destino existente, política `overwrite`, destinos repetidos y rutas con `..`. Devuelve resultado por entrada sin revelar contenido, tamaño/hash plaintext, revisión resuelta, contadores y advertencia de que la salida queda en claro.

Devuelve dos hashes:

- `manifest_sha256`: liga la confirmación al manifiesto exacto.
- `preview_sha256`: liga la confirmación al resultado exacto de la vista previa, incluidas revisiones resueltas y errores/destinos observados.

La ejecución exige ambos hashes y `--confirm`, vuelve a leer el manifiesto y reconstruye la vista previa. Si el manifiesto o el resultado cambió desde la revisión del operador, aborta antes de exportar. Una revisión `null` queda resuelta a una revisión inmutable concreta durante preview; la ejecución usa esa revisión, no vuelve a seleccionar “la actual”.

Los destinos duplicados bloquean todas las entradas que los comparten. Destinos inseguros, symlinks, hardlinks y traversal se rechazan individualmente.

## 4. Ejecución y fallos parciales

Cada entrada lista para exportar reutiliza `export_file`, que conserva su contrato individual: temporal exclusivo, modo root:root 0600, escritura/fsync, publicación sin sobrescritura silenciosa, comprobación de identidad del destino y verificación byte a byte tras escribir.

Los errores por configuración/revisión/destino/escritura se capturan por entrada y el proceso continúa con las demás. La salida JSON distingue `exported` y `error`, con contadores globales. No hay rollback de una salida que ya terminó correctamente si falla otra entrada; este comportamiento parcial es explícito y reportado.

## 5. Pruebas C-04B

Nueva suite `tests/xray_configurations_c04b.sh` con almacén temporal y clave sintética:

- manifiesto válido y contrato estricto;
- preview con entrada válida, destino existente sin overwrite y configuración inexistente;
- confirmación obligatoria y hash de manifiesto incorrecto;
- exportación byte a byte y permisos 0600 root:root;
- resultados parciales: exporta la entrada válida e informa errores individuales;
- revisión actual que cambia después del preview: `preview_sha256` obsoleto rechazado y no se crea salida;
- destinos duplicados: todas las entradas afectadas bloqueadas;
- rechazo de ruta con `..`, destino symlink, manifiesto symlink y hardlink;
- inyección de fallo en la primera salida y comprobación de que la segunda se completa.

## 6. Resultados de verificación

- Prueba focal `tests/xray_configurations_c04b.sh`: PASS.
- Regresión integral final `tests/*.sh`: **55/55 PASS**, exit code 0, después de añadir el caso de revisión obsoleta.
- `python3 -m py_compile scripts/*.py`: PASS.
- `bash -n scripts/*.sh tests/*.sh modules/*.sh bin/xray-manager`: PASS.
- ShellCheck focal de `tests/xray_configurations_c04b.sh`: PASS tras corregir el diagnóstico SC2034.
- `git diff --check`: PASS.

## 7. Exclusiones y estado

Sólo se utilizaron almacenes temporales y claves sintéticas. No se leyó `/etc/xray-manager/keys/master.key`, no se accedió al almacén real, no se modificaron perfiles live, VLESS/VMess, runtime, servicios/systemd, certificados, firewall, puertos, red o dependencias. No se tocó `Vps de Pruebas`, `main` ni `Xray-Normativa/`.

C-04B está **IMPLEMENTADA Y VERIFICADA LOCALMENTE**, pendiente de revisión/aceptación formal del propietario. No se hizo commit, push, publicación ni sincronización. C-04C (integración del menú Bash) no está autorizada ni iniciada. C-04, Etapa 5 y Etapa 2 permanecen ABIERTAS.
