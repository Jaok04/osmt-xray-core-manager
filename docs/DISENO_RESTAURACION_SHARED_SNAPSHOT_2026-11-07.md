# Diseño — restauración segura de shared snapshots v1 / TLS schema v2

**Fecha:** 2026-11-07
**Estado:** diseño técnico; NO implementado ni aprobado para mutación.
**Ámbito:** análisis del formato emitido por `shared_snapshot_writer.py`, `shared_backup_zip.py` y `shared_backup_format.py`. Solo desarrollo/fixtures cuando exista autorización específica.

## 1. Hallazgo y alcance

El repositorio dispone de un escritor de shared snapshots, un emisor ZIP streaming y un contenedor cifrado AES-256-GCM/scrypt. No se encontró un lector ZIP/restaurador general de esos paquetes. `vless_backup.py` implementa otro formato y otra transacción para datos VLESS/VMess; no es un restaurador de shared snapshots ni reconstruye el catálogo central TLS.

El paquete compartido contiene `manifest.json`, `index.json`, miembros de catálogos/configuración y `external-dependencies.json`. El manifiesto `xray-manager-shared-snapshot` versión 1 registra recursos, miembros, exclusiones, dependencias, catálogo origen y completitud. Los miembros se identifican por SHA-256 y usan rutas lógicas.

## 2. Restricción crítica de TLS

El snapshot writer excluye deliberadamente las claves privadas TLS:

- El catálogo serializado elimina `secret_ref`.
- Cada certificado agrega exclusión `tls_private_key / excluded_by_default`.
- Los certificados managed aportan el PEM público versionado y sus metadatos/fingerprint.
- Los certificados reference eliminan la ruta `certificate_source` del catálogo snapshot y se documentan en `external-dependencies.json` con path esperado, fingerprint y conexiones dependientes.
- Las dependencias TLS pueden quedar `pending_restore_preflight`; el recurso se marca `PARTIAL`.

Por tanto, el paquete no es autosuficiente para crear una identidad TLS nueva. **Nunca generar ni inventar `secret_ref`, nunca crear una entrada TLS activa sin blob AES-GCM disponible y verificado en el host destino.** La restauración TLS solo puede reconciliar/reconstruir metadatos y certificados públicos cuando el blob privado cifrado correspondiente ya existe en el destino y supera autenticación, AAD, correspondencia cert/key, huellas y vigencia con la clave maestra local.

Para `reference`, el path externo debe existir como archivo regular seguro, sin symlink/hardlink, y coincidir con fingerprint; además debe existir el blob cifrado local correspondiente. Si falta cualquiera, la dependencia queda no resuelta y las conexiones dependientes no pueden activarse ni incluirse en un cutover.

## 3. Contrato de lectura y autenticación

1. Solicitar passphrase de forma interactiva; no persistirla ni pasarla por argumentos/logs.
2. Leer paquete con límite total 512 MiB; validar magic, cabecera canónica, perfil scrypt fijo y AES-256-GCM. No aceptar parámetros KDF arbitrarios.
3. No inspeccionar ni extraer contenido ZIP antes de autenticar el payload completo.
4. Lector ZIP propio/estricto para el subconjunto emitido: `ZIP_STORED`, sin ZIP64, sin cifrado ZIP, sin comentarios ni campos extra no definidos, sin directorios, sin symlink/hardlink, máximo 10.000 entradas/512 MiB.
5. Exigir `manifest.json` e `index.json` como primeras entradas exactas; datos ordenados lexicográficamente; nombres únicos y sin colisiones casefold/NFC.
6. Comparar local headers, central directory y EOCD; rechazar entradas duplicadas, solapamientos, offsets/longitudes incoherentes, flags/métodos no admitidos, paths absolutos, traversal, backslash, NUL, componentes `.`/`..` y nombres no normalizados.
7. Verificar CRC32, tamaño y SHA-256 de cada miembro contra `index.json` y `manifest.json`; validar `member_id == sha256:<digest>` y todas las referencias de recursos/dependencias.
8. Validar manifiesto con el mismo contrato estricto del writer y rechazar campos sensibles, rutas absolutas o claves privadas.
9. Mantener payload/miembros en memoria o staging root:root 0700 con archivos 0600; nunca extraer directamente sobre rutas activas.

## 4. Preflight de destino sin mutaciones

- Leer y validar todos los catálogos destino requeridos, permisos, locks y revisiones.
- Validar schemas concretos por categoría; no confiar en `source_snapshot` como estado actual.
- Construir un plan de merge con altas, idénticos, conflictos, dependencias satisfechas/no satisfechas y recursos parciales.
- No crear carpetas/archivos, locks persistentes ni temporales antes de que el operador apruebe el plan; los locks temporales de preflight deben tener limpieza segura.
- Rechazar paquetes `PARTIAL` por defecto para operaciones que impliquen dependencias no satisfechas. Permitir restauración parcial solo cuando el operador elija explícitamente recursos independientes y el plan demuestre que no quedan conexiones huérfanas.
- `certificates.tls`: cotejar cada `(certificate_id, revision, fingerprint)` con el catálogo/secret blobs locales. Para managed, el PEM público del paquete puede reparar/recrear el archivo versionado solo si existe el blob cifrado local esperado y la pareja pasa verificación criptográfica. Para reconstruir catálogo ausente, usar exclusivamente metadatos snapshot más `secret_ref` esperado derivado del ID/revisión, comprobar el blob AES-GCM local y verificar pareja/huellas/vigencia; nunca importar una clave del snapshot porque no la contiene. Si no existe blob local, bloquear ese certificado y sus conexiones dependientes.
- `tls_reference`: comprobar ruta externa declarada en `external-dependencies.json`, identidad segura del archivo, fingerprint y blob cifrado local. No copiar rutas externas desde el snapshot a catálogo sin validación local.

## 5. Política de conflictos propuesta (requiere aprobación)

Política por defecto: **merge no destructivo**.

- IDs ausentes: candidatos a alta si pasan validación y todas sus dependencias.
- Registro idéntico por ID/revisión/hash: no-op idempotente.
- Mismo ID con contenido diferente: conflicto; no sobrescribir ni cambiar la revisión activa automáticamente.
- UUID, `certificate_id`, revision o asociación duplicados con contenido distinto: bloquear el recurso y sus dependientes.
- Datos actuales no presentes en el snapshot: conservarlos; no borrar ni reemplazar catálogos completos por defecto.
- Una opción futura `replace-selected` requerirá confirmación separada, backup local verificable y autorización específica; no forma parte de la primera versión.

## 6. Transacción y recuperación

La restauración no puede publicar categoría por categoría sin coordinación. Diseño requerido:

1. Crear plan inmutable con hashes de origen/destino y selección aprobada.
2. Adquirir locks en orden global documentado (lifecycle → conexiones/identidades → certificados → almacenes de configuración) mediante un único propietario; no reacquirir locks anidados.
3. Crear backup local recuperable de todos los catálogos/archivos que se tocarán; verificar hashes antes de continuar.
4. Preparar staging aislado; validar todos los bytes y relaciones nuevamente.
5. Escribir journal durable con `operation_id`, `backup_id`, categorías, hashes, snapshots previos, destinos, dependencias y fase (`prepared`, `staged`, `published`, `committed`, `rollback_required`, `recovery_required`).
6. Publicar archivos versionados antes de catálogos; publicar catálogos atómicamente y en orden definido; no cambiar runtime ni iniciar Xray.
7. Verificar catálogos/archivos publicados, referencias y auditoría completa antes de `committed`.
8. Ante crash/fallo, recovery idempotente solo puede restaurar snapshots exactos si no existe drift externo; ante ambigüedad registrar `RECOVERY_REQUIRED` y no sobrescribir cambios posteriores.
9. Mantener rollback separado de aplicación runtime. Restaurar datos/configuración no equivale a aplicar o cargar configuración en Xray.

## 7. Interacción con R-05 y runtime

La primera versión del restaurador debe ser **data-only**. No ejecutar `systemctl`, no invocar `xray_service.sh`, no iniciar/reiniciar/recargar Xray y no marcar `runtime_applied=true`. Las conexiones restauradas permanecen draft/suspended según contrato de cada categoría hasta un flujo posterior de validación y cutover aprobado por R-05. No reactivar usuarios ni asociaciones de forma implícita.

## 8. Matriz mínima de pruebas fixture

- Passphrase incorrecta, tag AES-GCM alterado, cabecera no canónica, KDF manipulado, payload truncado y límites máximos.
- ZIP con symlink/hardlink, traversal, duplicados, casefold/NFC, ZIP64, compresión no soportada, flags/campos extra, local/central mismatch, offsets solapados, CRC/SHA/size incorrectos.
- Manifest/index incompatibles, member_id falso, referencias inexistentes, recursos COMPLETE con exclusiones o dependencias pendientes.
- Snapshot COMPLETE/PARTIAL; categorías omitidas y restauración parcial con dependencias.
- Catálogos destino v1/v2, ausentes/corruptos, IDs idénticos/conflictivos, revisiones TLS históricas y huellas duplicadas.
- TLS managed: blob local correcto/ausente/corrupto, certificado público ausente/alterado, key mismatch, expirado y SAN incoherentes.
- TLS reference: archivo externo ausente, symlink/hardlink, fingerprint divergente, blob ausente y ruta sustituida TOCTOU.
- Crash antes/después de cada rename, catálogo, journal y commit; recovery repetido byte-a-byte; drift externo y conflicto entre operaciones.
- Garantía de que ningún fallo cambia runtime, inicia servicio, borra datos actuales o publica conexiones con dependencias TLS no satisfechas.

## 9. Decisiones pendientes de aprobación

1. Política de merge por ID y conflictos (propuesta no destructiva arriba).
2. Si el primer release restaura solo conexiones/identidades sin TLS o también repara certificados públicos cuando ya existe blob local.
3. Política de snapshots `PARTIAL` y restauración selectiva por recursos.
4. Ubicación/retención del journal y backup local de rollback.
5. Orden definitivo de locks y límites de integración con los stores actuales.
6. Si la restauración de identidades/asociaciones se mantiene en primer release o se pospone.

**Estado:** diseño solamente. No hay lector ZIP, restaurador ni migración de datos implementados. No se tocaron catálogos reales, master.key, Certbot, ACME, systemd, runtime, VPS Pruebas, DNS, firewall, puertos, dependencias, commit o push.
