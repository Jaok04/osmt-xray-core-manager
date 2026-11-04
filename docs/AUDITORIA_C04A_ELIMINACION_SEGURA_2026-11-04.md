# Auditoría C-04A — eliminación segura de configuraciones independientes

**Fecha:** 2026-11-04
**Rama:** `design/user-identity-association-v1`
**Host/ruta:** `Implementación-Xray:/opt/xray-manager`
**Base de trabajo:** `c30a474195406617a20fd517b7588420e48293d2` (sin commit/push)

## 1. Alcance y autorización

El propietario aprobó el diseño y la matriz de C-04, autorizando únicamente C-04A (motor de eliminación segura), con pruebas y documentación locales. C-04B (exportación múltiple) y C-04C (integración Bash) no se iniciaron.

Se contrastó el comportamiento con:

- `Xray-Normativa/05_Configuraciones_Perfiles/Etapa_5_Configuraciones_Perfiles.md`, §3, opción 7 y §3.1.
- Contrato de persistencia definido en `docs/DISENO_GESTOR_CONFIGURACIONES_INDEPENDIENTES.md`, §§5.7 y 6.

La normativa exige mostrar identidad/nombre/ruta/estado, confirmar, no eliminar elementos aplicados en uso, eliminar sólo el objeto seleccionado y conservar perfiles, copias, respaldos e informes históricos.

## 2. Implementación

Archivo modificado: `scripts/xray_configurations.py`.

Operaciones nuevas:

- `preview-delete --config-id ID`
- `delete --config-id ID --expected-name NAME --confirm --assert-not-active`

### 2.1 Vista previa

La vista previa:

- Adquiere el lock exclusivo y recupera WAL pendiente.
- Comprueba registro único en catálogo y coherencia catálogo/metadatos.
- Verifica estructura completa del objeto, metadatos, todas las revisiones y autenticidad AES-256-GCM.
- Rechaza archivos/directorios inesperados, symlinks, hardlinks, permisos/propietarios inseguros y revisiones no verificables.
- Devuelve ID, nombre, ruta, revisión actual, número de revisiones, estado de activación del almacén, resultado de integridad y advertencia de que la actividad runtime no ha sido verificada.

### 2.2 Confirmaciones y control de estado activo

La eliminación exige simultáneamente:

- `--confirm`, posterior a la vista previa.
- `--expected-name`, que debe coincidir exactamente con el nombre revisado.
- `--assert-not-active`, afirmación explícita del operador de que el objeto no está aplicado ni en uso.

**Limitación deliberada:** el almacén de configuraciones independientes no dispone de integración con el registro runtime/perfil activo. El motor no puede certificar automáticamente si alguien aplicó manualmente una copia externa. Por eso la vista previa devuelve `runtime_activity_verified=false` y la eliminación requiere la afirmación explícita del operador. No se presenta el estado `not_managed_by_independent_configurations` como prueba de que Xray no está ejecutando esos mismos bytes por una vía externa.

### 2.3 Integridad previa

Antes de modificar el catálogo:

- Verifica todos los archivos y directorios esperados.
- Verifica todas las revisiones, no sólo la actual.
- Comprueba hash de ciphertext y autenticación AES-256-GCM.
- Comprueba que la revisión actual existe.
- Si encuentra corrupción o estructura inesperada, aborta y conserva íntegros los registros y archivos existentes.

### 2.4 Transacción de eliminación

Se añadió un formato WAL específico `schema_version=2`, con contrato exacto y rutas cerradas:

1. Escribe journal `prepared` con ID, rutas permitidas y snapshot exacto del catálogo anterior.
2. Renombra el directorio original a un tombstone aleatorio dentro de `items/`.
3. Actualiza atómicamente el catálogo para retirar sólo el ID seleccionado.
4. Publica journal `committed`.
5. Elimina el tombstone y sincroniza el directorio.
6. Retira WAL y sincroniza el almacén.

Recuperación:

- `prepared`: restaura el tombstone a su ruta original si el rename ocurrió, restaura el snapshot exacto del catálogo y elimina WAL.
- `committed`: comprueba que el catálogo ya no contiene el ID, termina la limpieza del tombstone si existe y elimina WAL.
- Si encuentra rutas, estados, snapshots o combinaciones ambiguas, falla de forma conservadora y preserva el journal para inspección.

Los journals C-01/C-02/C-03 (`schema_version=1`) mantienen su protocolo anterior. El WAL v2 sólo acepta la operación `delete` y los patrones exactos `items/config-ID` y `items/.delete-ID-random`.

La eliminación no llama a `apply`, `activate`, systemd ni modifica runtime.

## 3. Preservación de elementos relacionados

La operación elimina únicamente el directorio de la configuración independiente elegida y su entrada de catálogo.

No accede ni modifica:

- Perfiles.
- Copias JSON independientes pertenecientes a perfiles.
- Archivos previamente exportados.
- Respaldos.
- Historiales o informes externos.

La independencia de las copias de perfil se mantiene conforme a la normativa §3.1.

## 4. Pruebas C-04A

Nueva suite: `tests/xray_configurations_c04a.sh`.

Casos incluidos:

- Confirmación y afirmación de no-aplicación obligatorias.
- Rechazo de ID inválido y nombre esperado incorrecto.
- Vista previa con identidad, revisión e integridad.
- Eliminación de configuración con varias revisiones.
- Eliminación de objeto vacío sin inventar revisiones.
- Preservación de otra configuración del catálogo.
- Rechazo de ciphertext manipulado y conservación del objeto/catálogo.
- Rechazo de archivos inesperados y conservación del objeto/catálogo.
- SIGKILL después del rename: rollback y recuperación.
- SIGKILL después de actualizar catálogo pero antes de publicar commit: rollback.
- SIGKILL durante limpieza de tombstone tras commit: finalización de eliminación en la siguiente operación.
- Verificación de ausencia de WAL/tombstones residuales tras recuperación.

Las pruebas crean almacenes temporales y claves sintéticas. No utilizan `/var/lib/xray-manager/configurations` ni `/etc/xray-manager/keys/master.key`.

## 5. Resultados de validación

- Prueba focal C-04A: **PASS**.
- Regresión completa `tests/*.sh`: **54/54 PASS** (se añadieron los casos C-04A).
- `python3 -m py_compile scripts/*.py`: PASS.
- `bash -n` en scripts/tests/modules y `bin/xray-manager`: PASS.
- ShellCheck de `tests/xray_configurations_c04a.sh`: PASS.
- `git diff --check`: PASS.

Los procesos SIGKILL de los escenarios de recuperación generan los mensajes esperados de terminación por señal; la suite comprueba el código 137 y verifica la recuperación posterior.

## 6. Archivos y estado Git

Modificados:

- `scripts/xray_configurations.py`
- `tests/xray_configurations_c04a.sh` (nuevo)
- `docs/AUDITORIA_C04A_ELIMINACION_SEGURA_2026-11-04.md` (nuevo)
- Documentos de diseño/continuidad/estado que registran este corte.

No se hizo commit, push ni sincronización. No se modificó `main` ni `Xray-Normativa/`.

## 7. Límites y estado

C-04A queda **implementada y auditada localmente, pendiente de aceptación formal**.

No equivale a completar C-04, la Etapa 5 ni la Etapa 2. C-04B y C-04C no se iniciaron. No hay exportación múltiple ni menú Bash integrado.

No se intervino el almacén real, la clave maestra, runtime, servicios, systemd, certificados, firewall, puertos, red, dependencias ni la VPS de pruebas.

**Siguiente puerta:** aceptación formal de C-04A. C-04B/C-04C requieren autorización específica posterior. La publicación GitHub y sincronización VPS también requieren autorización independiente.
