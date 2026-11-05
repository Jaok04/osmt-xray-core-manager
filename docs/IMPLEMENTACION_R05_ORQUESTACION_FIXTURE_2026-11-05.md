# Implementación R-05 — orquestación de runtime simulada

**Fecha:** 2026-11-05
**Estado:** IMPLEMENTADA, VERIFICADA, AUDITADA Y ACEPTADA FORMALMENTE el 2026-11-05 en alcance fixture-only. Publicación autorizada por separado.
**Autorización:** el propietario autorizó expresamente R-05 solo con fixtures, mocks, almacenes temporales y extensión compatible del journal.
**Base Git:** `design/user-identity-association-v1`, HEAD previo `53d60d26becf6cca943f4317068b66e232d936d9`.

## 1. Archivos

Nuevos:
- `scripts/xray_runtime_service_adapter.py`: adaptador fixture-only para status, restart y restauración simulada; CAS interproceso serializado con `fcntl.flock`; estado, lock y bitácora root-only.
- `scripts/xray_runtime_orchestrator.py`: composición R-01 → R-04 y coordinación de estado, confirmación, generación, verificación, rollback y recovery R-05.
- `tests/test_xray_runtime_orchestrator.py`: pruebas focales del orquestador y adaptador.
- `docs/DECISION_R05_JOURNAL_GENERATION_2026-11-05.md`: contrato de esquema, estados, generación, CAS y límites.

Modificados:
- `scripts/xray_runtime_journal.py`: lectura compatible de schema 1 y schema 2; `generation_id`; unicidad; validación estricta; estados R-05.
- `scripts/xray_runtime_preflight.py`: acepta `active_state=unknown` con `sub_state=unknown` como evidencia válida para que R-05 pueda fallar cerrado y registrar el estado desconocido.
- `scripts/xray_runtime_publisher.py`: persiste la fase `published` en schema 2 y deriva todos los journals schema 2 a recovery R-05, sin que R-04 intente rollback unilateral.

## 2. Contrato de journal

- Schema 1 conserva exactamente su estructura histórica y sigue siendo legible; no hay migración automática.
- Las operaciones R-05 usan schema 2 y el objeto `orchestration`.
- `generation_id` tiene formato `generation-[0-9a-f]{32}`, se genera criptográficamente, se valida contra todo el almacén y no se reutiliza.
- La misma generación queda ligada al journal, a la petición de restart, al status posterior y a la evidencia de SHA-256.
- Los valores/estados del objeto de orquestación se validan estrictamente; los campos inesperados, estados no tipados y discrepancias entre estado/fase fallan cerrados.
- Los estados R-05 se reservan a schema 2. R-03/R-04 siguen leyendo schema 1. Los recovery R-03/R-04 derivan schema 2 a R-05.

## 3. Flujo implementado

1. Consultar el estado del adaptador fixture y ejecutar R-01 preflight.
2. Ejecutar R-02 staging.
3. Crear snapshot/journal R-03 con schema 2 y `generation_id`.
4. Reconsultar estado y generación/hash después de staging; si hay divergencia, no publicar.
5. Rechazar publicación desde estado inicial `failed` o `unknown`.
6. Comprobar que, si el servicio está active, el hash cargado coincide con el snapshot previo.
7. Reutilizar R-04 para publicar atómicamente.
8. Resolver según el estado inicial:
   - active + confirmación aceptada: CAS contra estado/generación/hash previos, restart simulado y status posterior; éxito solo con active + generación exacta + SHA-256 publicado.
   - active + confirmación rechazada: `published_pending_apply`; no restart; la generación cargada anterior permanece.
   - inactive: `published_pending_start`; no start ni restart.
   - failed/unknown: `recovery_required`; no publicar ni iniciar.
9. Ante resultado no verificable, restaurar archivo con R-04 y reconciliar el estado simulado. Si la generación cargada pertenece a un actor/operación externa, no sobrescribirla: `recovery_required`.

## 4. Fallos y recuperación

Se prueban rechazo, excepción, timeout antes/después de transición, respuesta perdida, generación/hash incorrectos, servicio failed/inactive/unknown posterior al restart, divergencia externa y fallos de restauración.

La recuperación R-05:
- Detecta rename R-04 ocurrido antes de confirmar el journal (`snapshot_saved` + hash staged) y continúa desde `config_published`.
- Si el rename no ocurrió y el destino sigue en el hash previo, marca `aborted` y limpia temporales seguros.
- Si el destino no coincide con snapshot ni staging, deja `recovery_required`.
- Reconciliación de `service_restart_requested`: consulta status; generación/hash exactos permiten completar sin repetir restart. Si no coinciden, rollback.
- Completa `service_verified` tras caída mediante status y generación/hash.
- Reanuda rollback después de rename de restauración y después de restauración de servicio.
- Los estados pending_apply/pending_start no repiten restart/start en recovery.
- Journals schema 1 se omiten sin reescritura. R-03 resuelve sus fases preparatorias; R-04 deriva schema 2 a R-05.

El adaptador aplica compare-and-swap interproceso en restart usando el estado/generación/hash previamente observados y en restore exige que siga cargada la generación de esta operación. Las funciones públicas `status`, `restart`, `restore` y `audit_events` comparten un lock exclusivo `fcntl.flock` (`adapter.lock`) que protege lectura, comparación, escritura de estado y append de bitácora como una sola transacción. El lock se valida como archivo regular root:root 0600, sin symlink ni hardlinks, y se verifica su identidad de inode después de adquirirlo. No pisa cambios externos entre status y acción ni pierde eventos de auditoría por escrituras concurrentes.

## 5. Pruebas y controles

La evidencia detallada está en `docs/AUDITORIA_R05_ORQUESTACION_FIXTURE_2026-11-05.md`.

R-05 no añade dependencias. Las pruebas usan temporales, mocks y el binario Xray fixture ya utilizado por R-03/R-04. El adaptador no importa ni ejecuta subprocess, shell, systemctl, service, journalctl, D-Bus ni APIs de systemd. La reauditoría de concurrencia añade pruebas multiproceso para restart y restore con precondiciones idénticas, consultas status concurrentes, conservación de todos los eventos y rechazo de un lock simbólico.

## 6. Límites y trabajo posterior

- No hay integración de menú/UI en este bloque; la confirmación se representa mediante argumento booleano explícito del orquestador.
- No se implementa todavía el registro de perfil activo exigido por el flujo normativo de Etapa 5 §7. Esa integración queda pendiente antes de afirmar cierre del flujo de activación.
- No existe adaptador systemd real en R-05.
- No se ha instalado Xray en vivo, creado/activado `xray.service`, emitido un certificado real, publicado una configuración real ni conectado NetMod.
- No se modificaron `Xray-Normativa/`, `main`, runtime real, certificados persistentes, claves, DNS, firewall, puertos, red, dependencias ni VPS de pruebas.
- R-06/live sigue NO AUTORIZADA. Etapas 2, 3, 4, 5 y 6 siguen abiertas/parciales.
- La implementación no está aceptada formalmente ni publicada; se requiere revisión del propietario y autorización de publicación separada.
