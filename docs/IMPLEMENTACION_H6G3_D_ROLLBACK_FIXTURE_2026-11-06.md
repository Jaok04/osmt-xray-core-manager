# H6-G3-D — rollback fixture adversarial e idempotencia

**Fecha:** 2026-11-06
**Rama:** `design/user-identity-association-v1`
**Alcance:** R-04/R-05 fixture, mocks y pruebas aisladas.
**Estado:** implementación y pruebas adversariales focales completadas; auditoría independiente G3-E pendiente.

## Objetivo

Verificar que rollback y recovery:
- nunca sobrescriban cambios externos;
- no restauren desde snapshots corruptos;
- sobrevivan a crashes entre rename y journal;
- no repitan acciones de servicio tras recuperación ya realizada;
- mantengan estados de configuración y servicio diferenciados;
- persistan `RECOVERY_REQUIRED` cuando no se puede demostrar una recuperación segura.

## Hallazgo corregido

La inspección adversarial encontró que `publisher._load_operation()` validaba el snapshot antes de que `rollback_operation()` pudiera registrar un fallo durable. Un snapshot corrupto bloqueaba la escritura, pero dejaba el journal en `config_published` en vez de registrar `recovery_required`.

Corrección:
1. `_load_operation()` admite omitir exclusivamente la verificación del snapshot para el camino controlado de rollback.
2. `rollback_operation()` valida el snapshot después de leer un journal estructuralmente válido; si falla, escribe `recovery_required` y no modifica el runtime.
3. `recover_publications()` aplica el mismo comportamiento en estados activos y al verificar estados restaurados.
4. No se debilita la validación de integridad: un snapshot inválido nunca se usa para restaurar bytes.

## Pruebas adversariales añadidas

### Publicador R-04
- Drift externo del destino antes del rollback: conserva los bytes externos y persiste `recovery_required`.
- Snapshot alterado después de publicar: conserva configuración staged y persiste `recovery_required`.
- Snapshot alterado durante recovery: no publica snapshot corrupto; conserva runtime y registra `recovery_required`.
- Drift externo después de crash tras rollback rename: recovery no sobrescribe el actor externo.
- Recovery repetido después de rollback: journal y runtime permanecen byte por byte idénticos en la segunda pasada.
- Se conservan las pruebas existentes de crash antes/después de rename, ausencia de configuración previa, symlink, hardlink y TOCTOU.

### Orquestador R-05
- Después de crash con configuración restaurada, una generación de servicio ajena se conserva y produce `recovery_required`; no se invoca restore sobre el estado externo.
- Crash después de restaurar servicio: recovery finaliza sin repetir restore; segunda recovery es `NO_OP`.
- Fallo de restore: persiste `recovery_required`; recovery posterior es `NO_OP` y no vuelve a invocar restore.
- Se mantienen las pruebas de timeout, pérdida de respuesta, failed/unknown y crashes de G3-C.

## Resultados

- Suite combinada publicador/orquestador: **86/86 PASS**.
- Suite Python global: **388/388 PASS**.
- Las pruebas son aisladas y usan fixtures/mocks; no invocan systemd ni Xray real.

## Límites

- Este resultado valida exclusivamente rollback de configuración R-04 y reconciliación de servicio R-05 fixture.
- No demuestra rollback live de archivo + proceso; F-05 del backend live sigue pendiente.
- No conecta `LiveRuntimeBackend` a R-05, CLI o menú.
- No cambia el journal fixture-only a live.
- G3-A/B/C/D quedan implementados y verificados en pruebas; auditoría independiente G3-E pendiente.
- H6-G2 permanece abierto y el proyecto continúa NO APTO PARA DESPLIEGUE END-TO-END.

No se modificaron dependencias, systemd, Xray, runtime persistente, certificados, DNS, firewall, puertos ni red. No se hicieron commits ni push. `main` y `Xray-Normativa/` permanecen intactas.
