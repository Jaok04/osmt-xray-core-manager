# H6-G3-E — auditoría integral de segunda pasada

**Fecha:** 2026-11-06
**Rama:** `design/user-identity-association-v1`
**HEAD observado:** `9bab1dbed7d4873aa30a3fd00a976a1d666d9355`
**Revisor:** misma sesión de trabajo; esta revisión es una segunda pasada, no una auditoría independiente.
**Dictamen:** **PASS CON LIMITACIONES — ALCANCE FIXTURE**
**Estado de G3:** A/B/C/D verificados en fixtures; segunda pasada completada. La aceptación independiente/formal permanece pendiente.

## 1. Alcance y exclusiones

Se revisaron el contrato `docs/DECISION_H6G3_COORDINACION_TRANSACCIONAL_2026-11-06.md`, las implementaciones G3-A/B/C/D, el publicador R-04, el orquestador R-05, el journal, los adaptadores de servicio, las pruebas y la separación del backend live.

El trabajo se limitó a lectura, pruebas automatizadas y validaciones estáticas en la VPS de desarrollo `Implementación-Xray`, ruta `/opt/xray-manager`.

No se ejecutó `systemctl` real, no se inició/detuvo/reinició Xray, no se publicó configuración en `/etc/xray`, no se modificó runtime persistente, certificados, DNS, firewall, puertos ni red. Algunas suites existentes invocaron Xray 26.10.31 únicamente con `run -test` sobre configuraciones temporales. No se instaló ni actualizó ninguna dependencia. No se utilizó la VPS de pruebas. No hubo commit ni push.

## 2. Matriz de auditoría

| Área | Resultado | Evidencia / observación |
|---|---|---|
| Orden y propiedad de locks | PASS | `transaction_locks()` adquiere lifecycle y luego application; libera en orden inverso. Los contextos anidados con las mismas rutas reutilizan el propietario. |
| Reacquisición anidada | PASS | `_acquire()` devuelve una lista vacía dentro del contexto propietario; los `finally` internos no liberan los descriptores exteriores. Un conjunto de rutas distinto falla cerrado. |
| Apply/publicación/transición | PASS | `_continue_apply_operation()` mantiene el ámbito desde la revalidación posterior al staging hasta publicación, transición, observación, registro o rollback. |
| Start pendiente | PASS | `start_pending_operation()` conserva el contexto mientras persiste la solicitud y llama a `_execute_start()`; la llamada anidada reutiliza el mismo propietario. |
| Restart y rollback | PASS | `_execute_restart()` y `_restore_after_failure()` permanecen dentro del ámbito exterior; no se libera el lock entre el fallo y el rollback. |
| Recovery | PASS | `_recover_one()` conserva el contexto en continuación, observación y rollback anidado. Las rutas recursivas reutilizan el contexto. |
| Timeout y respuesta perdida | PASS EN FIXTURE | La decisión se basa en observación correlacionada de estado, generación y hash. La transición confirmada se reconcilia sin repetir acción; failed/unknown o reobservación fallida termina en `RECOVERY_REQUIRED`. |
| Rollback e idempotencia | PASS EN FIXTURE | Drift externo y snapshot corrupto no se sobrescriben. Recovery repetido tras rollback confirmado es byte-a-byte idempotente. Los fallos de restore no se reintentan automáticamente. |
| Journal, snapshot y hashes | PASS EN FIXTURE | Se valida la cadena de estados y la integridad del snapshot. El camino controlado puede registrar `RECOVERY_REQUIRED` ante snapshot inválido sin utilizarlo para restaurar bytes. |
| Aislamiento live | PASS | R-05 conserva `xray_runtime_service_adapter` como backend por defecto. No hay importación/instanciación de `LiveRuntimeBackend` desde el orquestador o el puente del menú. El lector de evidencia actual devuelve `environment=fixture`, que el backend live rechaza. |
| Archivos protegidos | PASS | `git status --short -- main Xray-Normativa` vacío. |
| Copia normativa | PASS | Los 14 archivos de `/root/Xray_Manager_Documentacion_Final_2026-10-31` coinciden byte a byte con sus homólogos en `Xray-Normativa/`. La comparación global muestra únicamente un `README.md` auxiliar adicional en `Xray-Normativa/`; no existe discrepancia en los 14 archivos normativos. |

## 3. Validaciones ejecutadas

- Python: `python3 -B -m unittest discover -s tests -p 'test_*.py'` — **388/388 PASS**.
- Suites Bash: `tests/*.sh` — **62/62 PASS**, cero fallos.
- `bash -n` global — PASS.
- ShellCheck `-S error` global — PASS.
- `./install.sh --check` — PASS; informó que no modificó el sistema.
- `git diff --check` — PASS.
- Comparación de normativa maestra — **14 archivos, 0 discrepancias**.
- Rama/HEAD — rama autorizada; HEAD sin cambios.
- Limpieza de artefactos de prueba: `scripts/__pycache__/` y `tests/__pycache__/` retirados.

Las suites de integración de protocolos usaron Xray 26.10.31 para validar configuraciones temporales con `run -test`. Esto no constituye una prueba de servicio real ni de conectividad externa.

## 4. Hallazgos y limitaciones

No se identificó un defecto bloqueante nuevo en G3-A/B/C/D dentro del alcance fixture revisado.

La revisión no es independiente: la realizó la misma sesión que participó en la implementación. Por ello, el resultado no sustituye la revisión independiente prevista en el diseño ni la aceptación formal del propietario.

El resultado tampoco acredita comportamiento live. Permanecen fuera de alcance y sin resolver para producción:

1. Rollback live completo de archivo y proceso (F-05).
2. Reconciliación durable de timeout/ambigüedad en el backend live (F-04).
3. Evidencia live verificable de operación/generación/publicación; el journal y el lector actuales son fixture-only.
4. Integración controlada del backend live con R-05, CLI y menú, que sigue expresamente bloqueada.
5. Prueba de servidor real y conexión externa VLESS-WS-TLS.

## 5. Dictamen

**PASS CON LIMITACIONES — G3-A/B/C/D en fixtures.**

Los invariantes de coordinación, recuperación y rollback fixture revisados son consistentes con el contrato G3 y las pruebas globales pasan. La segunda pasada de G3-E queda documentada, pero no debe denominarse auditoría independiente ni usarse para declarar habilitado el backend live.

**H6-G2 permanece abierto y NO APTO PARA INTEGRACIÓN LIVE. El MVP continúa NO LISTO PARA DESPLIEGUE END-TO-END.** No se autoriza por este informe ninguna operación real sobre systemd, Xray, certificados, red o runtime.

## 6. Estado Git

- Rama: `design/user-identity-association-v1`.
- HEAD y upstream observados: `9bab1dbed7d4873aa30a3fd00a976a1d666d9355`.
- Cambios de G2/G3 y documentos: locales, sin commit ni push.
- `main` y `Xray-Normativa/`: sin modificaciones.
