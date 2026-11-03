# Plan de migración histórica TLS — VMess y VLESS

**Versión:** 1.1
**Fecha:** 2026-11-03
**Estado:** DISEÑO APROBADO / FASE DE PREFLIGHT IMPLEMENTADA / MIGRACIÓN ESCRITORA PENDIENTE
**Ámbito:** migrar revisiones TLS históricas al catálogo central de certificados.
**No forma parte:** migrar REALITY, modificar runtime o eliminar datos históricos.

## 1. Objetivo

Sustituir, para nuevas revisiones de conexiones TLS históricas seleccionadas, el contrato por conexión:

- `security_options.certificate_file`
- `security_options.secret_ref`
- `secret_ref` en el catálogo de conexión (`secret_ref` VLESS o `vmess_secret_ref` VMess)
- blob cifrado de clave privada por revisión

por el contrato central:

- `security_options: {"certificate_id": "cert-..."}`
- referencia de secreto por conexión igual a `null`
- certificado y clave privada almacenados una sola vez en el almacén central.

Las modalidades REALITY y las conexiones sin TLS quedan fuera de la migración.

## 2. Reglas no negociables

1. Nunca modificar ni eliminar la revisión histórica original ni su blob durante la migración.
2. No inferir que dos certificados son iguales por nombre, ruta o CN: comparar fingerprint del certificado y validar que la clave privada corresponda al certificado.
3. Deduplicar por identidad criptográfica validada (fingerprint del certificado y huella de clave pública derivada), no por ruta.
4. Un certificado central `managed` debe ser la opción predeterminada para migración: copia pública controlada y clave privada cifrada centralmente. `reference` sólo si el operador selecciona expresamente conservar una ruta externa estable y el archivo puede verificarse.
5. No registrar claves privadas, PEM, passphrases ni contenido descifrado en CLI, JSON, logs, journal o documentación.
6. Rechazar certificado vencido, aún no válido, corrupto, clave que no corresponde, secreto ausente, autenticación AES-GCM fallida, metadatos incoherentes, symlinks/hardlinks y permisos inseguros.
7. REALITY conserva su contrato y su secreto individual. No convertirlo en TLS ni procesarlo como certificado TLS.
8. No ejecutar migración automáticamente durante `read`, `audit`, backup, restore, arranque ni actualización.
9. Requerir backup verificable antes de cualquier escritura y consentimiento explícito para cada lote.
10. Migración no implica runtime apply, reinicio ni despliegue.

## 3. Inventario y preflight de solo lectura

Una herramienta futura `scripts/certificate_migration.py` debe empezar con `plan`/`audit` sin escribir:

- Enumerar entradas VMess/VLESS y sus referencias de configuración vigentes.
- Seleccionar exclusivamente modalidades cuya seguridad en el mapa `MODES` sea `tls`.
- Clasificar contrato central (`certificate_id`) frente a legado (`certificate_file` + `secret_ref`).
- Comprobar referencias, revisiones, schema, puertos, protocolo, modalidad, paths, permisos y existencia de blobs.
- Descifrar cada secreto legado en memoria usando el backend criptográfico correspondiente al protocolo y la revisión; no asumir que los envelopes VMess y VLESS son intercambiables.
- Leer el certificado de la ruta histórica, validar vigencia y comprobar par certificado/clave.
- Calcular fingerprints y agrupar conexiones que usan exactamente el mismo par.
- Marcar rutas externas inaccesibles, material ambiguo, certificado vencido, secretos no autenticables y conflictos como `BLOCKED`; nunca intentar reparación automática.
- Emitir un informe sin secretos: connection_id, protocolo, modalidad, revisión, fingerprint, estado, motivo, certificado propuesto y grupo de deduplicación.

El preflight no importa certificados, no crea revisiones, no cambia catálogos y no elimina nada.

## 4. Flujo de migración propuesto

### Fase A — aprobación y backup

1. Generar informe `plan` con hash del catálogo de conexiones, referencias/configs/blobs involucrados y catálogo central.
2. Crear backup compartido consistente (ver `PLAN_BACKUP_RESTORE_CENTRAL.md`).
3. Verificar el backup y guardar su identificador en un journal de migración.
4. Solicitar aprobación explícita del lote y de cada grupo de certificados/fingerprints.

### Fase B — importación central idempotente

1. Adquirir bloqueo de migración y bloqueos de catálogos en un orden único y documentado.
2. Volver a validar los hashes/versions capturados por el preflight; abortar si hubo cambios concurrentes.
3. Recuperar clave privada heredada sólo en memoria y validar de nuevo el par.
4. Importar una sola vez cada par único al catálogo central. Por defecto `managed`.
5. Registrar `certificate_id`, fingerprint, protocolo/origen, conexiones asociadas y journal; no registrar material secreto.
6. Si ya existe recurso central activo con el mismo fingerprint y clave pública, reutilizarlo sólo después de verificar el par completo.

### Fase C — nuevas revisiones

Para cada conexión aprobada:

1. Mantener intacta la revisión anterior y su blob.
2. Crear una nueva revisión inmutable con el mismo protocolo, modalidad, transporte, dirección, puerto y opciones de transporte, sustituyendo únicamente el contrato TLS por `certificate_id`.
3. Publicar la nueva referencia de configuración y poner `secret_ref`/`vmess_secret_ref` en `null` mediante escritura atómica del catálogo correspondiente.
4. Verificar que `read` y `audit` aceptan la nueva revisión y que el resolutor puede preparar un lease autorizado en el entorno de prueba.
5. No ejecutar Xray real ni aplicar runtime como parte de la migración.

### Fase D — verificación y cierre

- Confirmar que todas las conexiones migradas apuntan a la revisión nueva.
- Confirmar que cada `certificate_id` está activo y corresponde al fingerprint esperado.
- Confirmar que las revisiones y blobs anteriores siguen presentes y legibles.
- Confirmar que REALITY y modalidades no TLS no cambiaron.
- Ejecutar backup, restore de prueba y auditoría cruzada.
- Cerrar el journal como `COMPLETED` sólo si todos los controles pasan; de lo contrario `PARTIAL` con cada conexión identificada.

## 5. Atomicidad, reanudación y rollback

No existe una transacción filesystem única que abarque catálogo central, catálogo VMess, catálogo VLESS y archivos de revisiones. Por tanto, no prometer atomicidad global mediante una sola operación `rename`.

Se requiere journal durable con estados monotónicos:

`PLANNED → BACKED_UP → CERTIFICATES_IMPORTED → REVISIONS_STAGED → CATALOGS_PUBLISHED → VERIFIED → COMPLETED`.

Cada paso debe ser idempotente y registrar hashes de entrada/salida. Un fallo después de importar certificados puede dejar recursos centrales sin referencias; deben quedar marcados como `unreferenced_by_migration`, no borrarse automáticamente. Un fallo tras publicar una nueva revisión requiere rollback explícito que restaure la referencia previa del catálogo, conservando la nueva revisión y todos los blobs. No reescribir ni truncar revisiones históricas.

El orden de locks debe evitar deadlocks con el resolutor: primero lock de migración, luego catálogo de conexiones del protocolo (orden estable VLESS/VMess), finalmente catálogo central de certificados. Esta propuesta debe contrastarse con los locks reales antes de implementar.

## 6. CLI futura (propuesta)

- `certificate_migration.py plan --protocol all|vless|vmess`
- `certificate_migration.py show --plan-id ...`
- `certificate_migration.py execute --plan-id ... --approval-token ...`
- `certificate_migration.py verify --migration-id ...`
- `certificate_migration.py rollback --migration-id ... --approval-token ...`

La herramienta debe ser root-only, no interactiva en modo automatizado, requerir confirmación explícita de lote, rechazar cambios de hash posteriores al plan y producir salida redactada.

## 7. Pruebas obligatorias antes de habilitar ejecución

- VLESS y VMess, múltiples conexiones que comparten el mismo par y conexiones con pares distintos.
- Certificado/key mismatch, expirado, no vigente, corrupto, secreto ausente o AES-GCM alterado.
- Misma ruta con contenido cambiado y rutas distintas con mismo fingerprint.
- Catálogo central existente/inactivo, colisión de IDs, importación repetida e interrupción en cada estado del journal.
- Fallo antes/después de publicar cada catálogo, concurrencia y rollback.
- Confirmar que no se modifica ninguna revisión histórica, blob histórico, REALITY ni modalidad no TLS.
- Restore completo desde backup antes y después de una migración parcial.
- Probar leases en fixtures y, en entorno autorizado, lectura por Xray real como prueba separada.

## 8. Decisiones aprobadas (2026-11-03)

1. **Alcance:** VMess y VLESS.
2. **Almacenamiento:** `managed` por defecto. `reference` sólo con selección/confirmación explícita para cada grupo de certificado.
3. **Vigencia:** certificados vencidos o aún no vigentes bloquean la migración; no se asocian a conexiones.
4. **Retención:** conservar revisiones y blobs históricos; no eliminarlos como parte de la migración.
5. **Ejecución real:** requiere backup compartido verificable, revisión del plan/fingerprints y autorización específica del lote y ventana. La aprobación del diseño no autoriza una migración de datos reales ni runtime apply.

## 9. Implementación del preflight — 2026-11-03

Implementado `scripts/certificate_migration.py plan --protocol all|vless|vmess`.

- Sólo lectura: no crea directorios/locks, no importa certificados, no genera revisiones/journals y no modifica catálogos, configuraciones ni blobs.
- Reconoce las modalidades TLS a partir de los mapas `MODES` de ambos almacenes.
- Valida referencias, revisión/schema, contrato histórico, permisos root, archivos regulares y rechazo de symlinks/hardlinks.
- Descifra en memoria con el backend específico: `vless_crypto.decrypt_secret` o `vmess_config_store.decrypt`; los formatos/AAD no se consideran intercambiables.
- Comprueba PEM, correspondencia certificado/clave, vigencia y fingerprints SHA-256; agrupa pares idénticos entre protocolos.
- Emite `READY`, `BLOCKED` o `ALREADY_CENTRAL`, hashes de entrada y `plan_id`; no emite PEM ni claves privadas.
- Usa lock compartido de integridad si ya existe y vuelve a comprobar hashes de catálogo/configuración/blob/certificado. Si una entrada cambia, aborta el plan.
- Prueba sintética `tests/certificate_migration_plan.sh`: VLESS+VMess, deduplicación, backend criptográfico distinto, sólo lectura y blob alterado bloqueado.

**Inventario real de la VPS de implementación (2026-11-03):** el catálogo `/var/lib/xray-manager/connections/connections.json` contiene 0 registros; el preflight devuelve 0 candidatos TLS, 0 bloqueados y 0 listos. Los directorios de configuración VLESS y el catálogo central TLS no existen actualmente en esa VPS. No se migró ningún dato.

**Estado:** PREFLIGHT IMPLEMENTADO Y VERIFICADO CON FIXTURES; inventario real ejecutado sin candidatos. Fases de backup obligatorio, importación `managed`, publicación de revisiones, journal, verify y rollback siguen pendientes.
