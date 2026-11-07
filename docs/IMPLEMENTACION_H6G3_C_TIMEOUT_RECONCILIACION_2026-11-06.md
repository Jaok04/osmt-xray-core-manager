# H6-G3-C — reconciliación de timeout y resultado ambiguo

**Fecha:** 2026-11-06
**Rama:** `design/user-identity-association-v1`
**Alcance:** R-05 fixture, mocks y pruebas aisladas.
**Estado:** implementación focal completada; auditoría independiente pendiente.

## Objetivo

Evitar reintentos ciegos cuando una petición start/restart termina en timeout, excepción o pérdida de respuesta. La decisión se toma mediante observación del adaptador fixture y correlación exacta de estado, generación y hash.

## Cambios

1. `_restore_after_failure()` restaura primero los bytes de configuración según el contrato R-05 y observa el servicio antes de cualquier recuperación de proceso.
2. Si la observación del servicio devuelve `failed` o `unknown`, registra `RECOVERY_REQUIRED`, conserva `config_status=restored` y `service_status=failed`; no emite una segunda mutación de servicio.
3. Si el servicio permanece exactamente en la identidad previa, el rollback de configuración puede finalizar sin mutación del servicio.
4. Si el servicio está activo con la generación de la operación, la recuperación fixture puede restaurar la identidad previa mediante CAS y verificación; si la generación no corresponde, falla cerrado.
5. `service_start_requested` ya persiste la petición antes de invocar start. Se añadió un failpoint de prueba `after_start_request` para demostrar recuperación sin repetir start.
6. `RECOVERY_REQUIRED` es terminal para la recuperación automática: `_recover_one()` responde `NO_OP` y no repite start/restart/restore.
7. Los resultados originales `timeout` y `response_lost` permanecen en el journal aunque la observación posterior permita reconciliar el resultado.

## Matriz de comportamiento verificada

| Escenario | Resultado |
|---|---|
| Timeout antes de transición; observación exacta del estado previo | rollback de configuración; servicio sin mutación |
| Timeout después de transición; active + generation/hash exactos | reconciliado como completado; sin segunda acción |
| Respuesta perdida después de transición exacta | completado; sin segunda acción |
| Estado failed/unknown después de la petición | configuración restaurada; `RECOVERY_REQUIRED`; no mutar servicio |
| Generación/hash no correlacionados | `RECOVERY_REQUIRED`; no sobrescribir estado externo |
| Fallo de reobservación | `RECOVERY_REQUIRED`; no mutación adicional |
| Crash después de persistir start request, antes de start | rollback seguro; cero llamadas start |
| Journal ya `recovery_required` | recuperación automática `NO_OP` |

## Pruebas

- Suite focal `tests.test_xray_runtime_orchestrator`: **67/67 PASS**.
- Incluye timeout y respuesta perdida para restart y start, crash tras solicitud start, estados failed/unknown, reobservación fallida, ausencia de reintento y recuperación idempotente.
- Los tests de rollback de proceso usan el escenario `wrong_hash` (servicio activo y generación correlacionada) para distinguirlo de estados systemd `failed/unknown`, que ahora bloquean mutaciones.

## Límites

- Todo lo anterior usa el adaptador R-05 fixture; no se ejecutó systemd ni Xray real.
- No se conectó `LiveRuntimeBackend` a R-05, CLI o menú.
- El backend live aislado sigue sin reconciliación durable propia tras timeout y no está habilitado; esta entrega no convierte el journal fixture en evidencia live.
- No implementa rollback live de archivo + proceso (F-05).
- G3-D (rollback fixture adversarial/idempotencia integral) y G3-E (auditoría independiente) siguen pendientes.
- H6-G2 permanece abierto y no apto para integración live.

No se modificaron dependencias, configuración persistente, certificados, DNS, firewall, puertos ni red. No se hicieron commits ni push. `main` y `Xray-Normativa/` permanecen intactas.
