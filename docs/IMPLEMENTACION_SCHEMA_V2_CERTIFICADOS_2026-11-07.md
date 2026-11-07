# Implementación inicial del almacén TLS schema v2 — 2026-11-07

## Alcance ejecutado

Trabajo realizado exclusivamente en la VPS de desarrollo, rama `design/user-identity-association-v1`, con fixtures temporales. No se modificó VPS Pruebas, no se leyó la clave maestra real y no se ejecutaron APT, Certbot, ACME, systemd ni cambios de runtime.

### Cambios de código

- `scripts/certificate_store.py`
  - Lectura compatible de catálogos schema v1 y v2.
  - Validación estructural de revisiones v2 y proyección de la revisión activa.
  - Importación inicial en v2 con nombres managed versionados `<id>.rNNNNNN.pem`.
  - Rotación de un ID existente mediante nueva revisión managed; no sobrescribe archivos anteriores.
  - Migración explícita `migrate-v1`: copia managed, verifica el contenido y conmuta el catálogo de forma atómica; conserva el archivo legacy original y los secretos existentes.
  - Acción `rollback`: verifica blob AES-GCM, correspondencia certificado/clave, huellas y vigencia antes de cambiar la revisión activa.
  - Auditoría de integridad sobre todas las revisiones históricas; no borra huérfanos.
- `scripts/certificate_resolver.py`: resuelve la revisión activa y genera leases con su número exacto.
- `scripts/certificate_acme.py`: `import-certbot` admite `--certificate-id` explícito para rotar un ID existente. No se añadió selección automática de ID ni se cambió el menú.
- `scripts/shared_snapshot_writer.py`: exporta certificados managed versionados de todas las revisiones y elimina referencias a secretos del catálogo de snapshot; no incluye claves privadas.

## Contrato de datos v2

El registro conserva los campos legacy como proyección de la revisión activa y añade `active_revision` y `revisions[]`. Cada revisión guarda metadatos, almacenamiento, referencia de certificado, referencia cifrada y timestamp de creación. Los secretos mantienen AES-256-GCM y AAD `certificate_id + revision`.

Las rotaciones de un ID existente se restringen a `managed`, porque una referencia externa puede cambiar de bytes sin control del almacén y no ofrece inmutabilidad histórica. Las referencias externas iniciales siguen admitidas; su restauración/rollback depende de que el archivo externo siga disponible y conserve su huella.

La migración v1→v2 es explícita; no se ejecuta automáticamente al leer el catálogo. Los catálogos v1 siguen siendo legibles. Antes de importar/rotar en un catálogo v1, el operador debe ejecutar la migración explícita desde el Administrador (integración de menú pendiente).

## Pruebas ejecutadas

- `tests/certificate_store.sh`: PASS; incluye import managed/reference, rotación r1→r2, auditoría de ambas revisiones, rollback r2→r1→r2, migración v1→v2 y conservación del archivo legacy.
- `tests/certificate_resolver.sh`: PASS; lease con revisión activa 2, VLESS/VMess, referencia externa, permisos, limpieza y fallos cerrados.
- `tests/shared_snapshot_writer.sh`: PASS; snapshot sintético, clasificación, dependencias y protección de secretos.
- `tests/test_certificate_acme.py`: 11/11 PASS.
- Suite Python completa: 406/406 PASS.
- Suites Bash: 62/62 PASS.
- `py_compile`, `git diff --check`: PASS en los archivos focales.

## Pendiente antes de considerar el bloque terminado

1. Adaptar el flujo de restauración de snapshots para reconstruir de forma coherente el catálogo v2 y sus ficheros versionados; la prueba ejecutada cubre el escritor, no una restauración v2 end-to-end.
2. Integrar migración, rotación y rollback en el menú del Administrador con confirmaciones explícitas y auditoría previa/posterior.
3. Revisar todos los consumidores del catálogo, especialmente exportaciones, restauración, perfiles y snapshots, y probar compatibilidad v1/v2 completa.
4. Añadir pruebas de corrupción de revisiones históricas, interrupción de migración y reintentos.
5. Completar documentación de continuidad y ejecutar auditoría adversarial separada.

**Estado:** implementación inicial parcial, no apta para despliegue ni para activar `certbot.timer`. No se ha integrado todavía la aplicación/recarga de Xray tras renovación. Sin commit, push o despliegue.

## Segunda pasada — menú, consumidores y controles adversariales

### Integración del menú

`modules/certificates.sh` ahora expone:

- Auditoría del almacén, mostrando roturas, entradas inseguras y huérfanos.
- Migración explícita v1→v2 con auditoría previa/posterior y confirmación del operador.
- Rollback por `certificate_id` + revisión exacta, con auditoría previa/posterior y confirmación.
- Importación de lineage con `certificate_id` opcional: vacío crea un ID nuevo; informado solicita auditoría limpia y rota ese ID mediante una revisión `managed` inmutable. El menú informa que las conexiones conservan su ID y que la revisión no se aplica al runtime automáticamente.

La auditoría bloquea migración, rotación y rollback si detecta referencias rotas o entradas inseguras. Los archivos huérfanos se muestran como advertencia y nunca se eliminan automáticamente.

### Endurecimiento del historial

`load_catalog()` ahora exige unicidad global de `fingerprint_sha256` a través de todas las revisiones históricas, no solo entre las revisiones activas. La importación también busca duplicados en el historial completo, evitando reintroducir una revisión anterior como si fuera una rotación nueva.

### Revisión de consumidores

- `vless_config_store.py`, `vmess_config_store.py`, `vless_client_export.py` y `certificate_migration.py` consultan el catálogo mediante `load_catalog()` y usan el `certificate_id`/proyección legacy de la revisión activa; no se encontró dependencia directa del nombre legacy `managed/<id>.pem`.
- `certificate_resolver.py` consume la revisión activa y fija `certificate_revision` en el lease.
- `certificate_acme.py` pasa el ID explícito al importador y conserva el flujo de solicitud ACME registrado.
- `vless_backup.py` valida referencias TLS centrales contra el ID activo del catálogo; no restaura ni sobrescribe el almacén central de certificados.
- `shared_snapshot_writer.py` serializa el catálogo de certificados v2, todas las revisiones managed y sus dependencias, sin claves privadas ni `secret_ref` utilizables.

### Alcance real de restauración

La búsqueda del árbol confirmó que no existe un restaurador general de paquetes `shared_snapshot_writer.py`/shared snapshots. `vless_backup.py` implementa un flujo separado de backup/restore de datos VLESS/VMess y conserva/verifica referencias a certificados centrales ya existentes; no reconstruye el almacén central de certificados ni consume el snapshot general `certificates.tls`.

Por tanto, no se inventó un restaurador general fuera del contrato aprobado. La restauración general de snapshots TLS v2 sigue siendo una limitación explícita y bloquea declarar completo el ciclo backup/restore del snapshot compartido. Se requiere diseñar y aprobar el contrato de restore (conflictos, dependencias externas, preservación de certificados presentes, journal, recuperación e importación de secretos) antes de implementarlo.

### Pruebas adversariales añadidas

- Rechazo de huella repetida entre revisiones históricas.
- Rechazo de destino versionado preexistente con contenido distinto durante migración; el catálogo v1 permanece intacto.
- Menú fixture: auditoría previa/posterior, migración confirmada, rollback con ID/revisión, y rotación ACME con `certificate_id` explícito.

Pruebas focales actualizadas: `tests/certificate_store.sh` y `tests/certificates_menu.sh` PASS. La batería global completa se volverá a ejecutar tras esta segunda pasada.

**Estado:** integración del menú y controles de historial implementados en desarrollo; restaurador general shared snapshot sigue ausente por decisión de alcance. No activar `certbot.timer`, deploy hook ni aplicación/recarga Xray. No operaciones live, no clave maestra real, no VPS Pruebas, no commit/push.

## Validación global de la segunda pasada

Ejecución completa en VPS desarrollo, sin mutaciones live:

- Suites Bash: **62/62 PASS**.
- Tests Python: **406/406 PASS**.
- `bash -n` sobre todos los scripts Bash: PASS.
- `python3 -m compileall -q scripts tests`: PASS.
- `shellcheck -S error modules/*.sh scripts/*.sh tests/*.sh`: PASS.
- `./install.sh --check`: PASS; comprobación no modificó el sistema.
- `git diff --check`: PASS.

Las pruebas de protocolos ejecutaron Xray 26.10.31 con `run -test` sobre configuraciones temporales; no se inició un servidor ni se tocó el runtime persistente.

### Protección de identidad SAN en rotación ACME

Una revisión adicional detectó que el importador validaba SAN contra la solicitud nueva, pero no comparaba esos SAN con el certificado activo del mismo `certificate_id`. Se corrigió `certificate_acme.py`: cuando el ID ya existe, exige catálogo v2, almacenamiento `managed` y que la nueva revisión conserve todos los SAN históricos. La UI comprueba además que el ID exista (`show`) antes de tratarlo como rotación. Si se omite el ID, se crea un certificado nuevo.

Prueba añadida: `test_rotation_rejects_certificate_that_drops_historical_sans` demuestra que una renovación que omite un SAN anterior se rechaza y el catálogo permanece en revisión 1. `tests/test_certificate_acme.py`: **12/12 PASS**. La validación global posterior a este ajuste está en ejecución.

## Validación tras protección SAN de rotación

- Suites Bash: **62/62 PASS**.
- Tests Python: **407/407 PASS**.
- `bash -n` global y `compileall`: PASS.
- ShellCheck `-S error` sobre los archivos Bash modificados: PASS.
- `./install.sh --check`: PASS, sin modificar el sistema.
- `git diff --check`: PASS.

La validación global ShellCheck de todos los scripts se había completado PASS antes del último ajuste; para el ajuste final se repitió ShellCheck en los cuatro archivos Bash afectados. La revisión Python global y las 62 suites Bash sí se repitieron después de los cambios finales.
