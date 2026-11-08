# Paquete para revisión independiente — H6-G3

## Objetivo

Solicitar a un revisor humano o a otra IA, que no haya participado en la implementación, una revisión técnica adversarial e independiente de H6-G3-A/B/C/D y del informe de segunda pasada G3-E. La revisión debe ejecutarse contra el HEAD actualizado indicado abajo; los hashes antiguos dentro de los informes históricos son contexto, no el árbol a revisar.

## Estado exacto del árbol a revisar

- Repositorio: `Jaok04/xray-core-manager` (privado).
- Rama local autorizada: `design/user-identity-association-v1`.
- HEAD objetivo: tip vigente de `origin/design/user-identity-association-v1` al iniciar la revisión. Ejecutar `git fetch origin` y comprobar que `git rev-parse HEAD` coincide con `git rev-parse origin/design/user-identity-association-v1`; anotar el SHA exacto en el informe. No usar los hashes históricos de los informes como árbol objetivo.
- Ruta de desarrollo: `/opt/xray-manager` en la VPS `Implementación-Xray`.
- Árbol de trabajo limpio al preparar este paquete. G2/G3 están publicados; inspeccionar el HEAD actual y no asumir los cortes históricos de 2026-11-06.
- No cambiar de rama, no resetear, no limpiar el árbol y no sobrescribir archivos.
- No modificar `main/` ni `Xray-Normativa/`.

## Lectura obligatoria

1. `docs/DECISION_H6G3_COORDINACION_TRANSACCIONAL_2026-11-06.md`
2. `docs/IMPLEMENTACION_H6G3_A_B_COORDINACION_LOCKS_2026-11-06.md`
3. `docs/IMPLEMENTACION_H6G3_C_TIMEOUT_RECONCILIACION_2026-11-06.md`
4. `docs/IMPLEMENTACION_H6G3_D_ROLLBACK_FIXTURE_2026-11-06.md`
5. `docs/AUDITORIA_H6G3_E_SEGUNDA_PASADA_2026-11-06.md`
6. `scripts/xray_runtime_publisher.py`
7. `scripts/xray_runtime_orchestrator.py`
8. `scripts/xray_runtime_journal.py`
9. `scripts/xray_runtime_service_adapter.py`
10. `scripts/xray_runtime_live_backend.py`
11. `scripts/xray_runtime_operation_evidence.py`
12. `modules/xray_service.sh`
13. `scripts/xray_runtime_service_control.py`
14. `tests/test_xray_runtime_publisher.py`
15. `tests/test_xray_runtime_orchestrator.py`
16. `tests/test_xray_runtime_live_backend.py`
17. `tests/test_xray_runtime_operation_evidence.py`
18. `tests/test_xray_runtime_service_control.py`
19. `tests/xray_service_control.sh`

Contrastar las obligaciones funcionales pertinentes con la normativa aprobada en `Xray-Normativa/`, sin modificarla.

## Contrato que debe comprobarse

- Orden estricto lifecycle lock -> application lock; liberación inversa.
- Un único ámbito coordinador mantiene ambos locks durante apply/start/restart/recovery hasta observación, rollback o `RECOVERY_REQUIRED`.
- Helpers anidados reutilizan el propietario; no reacquieren ni liberan locks externos.
- Timeout/response-lost: observar y correlacionar antes de cualquier retry; no repetir ciegamente.
- Drift externo, snapshot corrupto o estado ambiguo no deben sobrescribirse ni repararse destructivamente.
- Rollback de configuración y recuperación del proceso/servicio son dimensiones distintas.
- `RECOVERY_REQUIRED` no debe entrar en ciclos automáticos de retry.
- Journal, snapshot, generación, validación y hashes deben mantener correlación e integridad.
- R-05 continúa fixture-only; ninguna ruta puede habilitar live accidentalmente.
- El backend live debe rechazar evidencia fixture o evidencia no correlacionada.

## Instrucciones de seguridad para el revisor

- Revisión read-only. No ejecutar `systemctl`, no iniciar/detener/reiniciar Xray, no publicar en `/etc/xray`, no tocar runtime persistente, certificados, DNS, firewall, puertos ni red.
- No ejecutar operaciones live ni instalar/actualizar dependencias.
- No acceder a `/etc/xray-manager/keys/master.key` ni imprimir secretos.
- No ejecutar comandos destructivos de Git (`reset`, `clean`, checkout forzado, rebase, commit, push).
- Las pruebas automatizadas existentes usan fixtures; las suites de integración pueden llamar a Xray con `run -test` sobre archivos temporales. Si se ejecutan, confirmar que no haya side effects persistentes.
- No asumir que el estado `HEAD` contiene los cambios: inspeccionar el árbol de trabajo completo y `git diff`/archivos no rastreados.

## Pruebas adversariales que debe intentar reproducir

1. Contextos anidados con las mismas rutas: demostrar un solo propietario y que un tercero no puede adquirir lifecycle lock antes de finalizar rollback.
2. Contextos anidados con rutas distintas: comprobar rechazo fail-closed.
3. Fallo/crash en cada frontera: antes y después de publicación, persistencia de solicitud start, transición, observación, rollback de bytes, restore del servicio y escritura final del journal.
4. Timeout antes de transición, timeout después de transición, response-lost y fallo de reobservación.
5. Estado `failed`/`unknown`, PID/InvocationID inconsistentes, generación ajena y hash runtime distinto.
6. Snapshot corrupto o ausente, drift externo antes/durante rollback y recovery repetido.
7. Repetición de recovery: comprobar idempotencia byte-a-byte y ausencia de acciones duplicadas.
8. Import graph/entrypoints: demostrar que R-05 y menú no importan/instancian el backend live.
9. Evidencia fixture presentada al backend live: debe ser rechazada.
10. Comprobar preservación de `main` y `Xray-Normativa/`.
11. Revisar `docs/DISENO_PUENTE_MINIMO_MANAGER_RUNTIME_LIVE_VLESS_WS_TLS_2026-11-08.md` sólo como contexto del siguiente objetivo; no confundir diseño con implementación ni ampliar el alcance G3.

## Entregable solicitado

Emitir un informe separado con:

- Dictamen `PASS`, `PASS CON LIMITACIONES` o `FAIL`.
- Hallazgos ordenados por severidad (BLOCKER/CRITICAL/HIGH/MEDIUM/LOW).
- Cada hallazgo con archivo, función y líneas; escenario reproducible; impacto; prueba que falla o evidencia que lo demuestra; corrección propuesta.
- Pruebas ejecutadas, comandos exactos y resultados.
- Limitaciones y cualquier punto no verificable.
- Confirmación expresa de que la revisión fue independiente y que no se modificó el árbol.

No aceptar un PASS basado únicamente en que las pruebas existentes pasan. Buscar defectos de concurrencia, TOCTOU, pérdida de locks, errores de recuperación, journal no durable y bypass de backend.

## Prompt listo para el revisor

Actúa como auditor sénior independiente de Bash/Python, Linux, concurrencia, persistencia transaccional y systemd. No participaste en la implementación. Revisa el árbol de trabajo actual en `/opt/xray-manager` siguiendo este paquete y el contrato G3. Tu tarea no es continuar desarrollando ni confiar en el informe previo: intenta refutarlo. Inspecciona el código real, reconstruye los flujos y reproduce adversarialmente los escenarios indicados, exclusivamente con fixtures y en modo read-only respecto al sistema real. No ejecutes operaciones live ni modifiques archivos. Entrega un informe técnico con severidad, archivo/línea, evidencia reproducible, pruebas y dictamen. Si no puedes acceder al árbol local no inventes hallazgos ni resultados: solicita el diff/archivos exactos que falten.

## Anexo de preparación — estado posterior al avance B4-MIN (2026-11-08)

Este anexo actualiza el contexto de entrega; no modifica el contrato ni amplía el alcance de H6-G3.

- HEAD comprobado en desarrollo y upstream: `8a5e5a1de5a3c96ec6922dad949a18376b4c4789`.
- Rama: `design/user-identity-association-v1`.
- Árbol limpio al iniciar esta comprobación; no se cambiaron fuentes durante la pre-revisión.
- Informe nuevo de contexto técnico: `docs/VALIDACION_SANDBOX_SYSTEMD_MEMFD_FIXTURE_2026-11-08.md`. Registra que el launcher memfd funciona bajo un servicio systemd transitorio con sandbox fixture. No es parte de G3-A/B/C/D y no debe interpretarse como habilitación live.
- Los avances posteriores B4-MIN (journal, staging, publicador, start coordinator y launcher memfd) siguen desconectados de R-05/menú según el diseño y estado documentados. El revisor debe comprobar el árbol real y no aceptar esa afirmación sin verificar imports, entrypoints y rutas de ejecución.
- La unidad transitoria usada en la prueba B4-MIN fue retirada y el fixture eliminado. No se debe repetir esa prueba para esta auditoría: la revisión H6-G3 es read-only respecto al sistema real.

### Prevalidación técnica interna (no independiente)

En una comprobación preliminar posterior al HEAD indicado se ejecutaron:

- Python global: `python3 -B -m unittest discover -s tests -p 'test_*.py'` — **542/542 PASS**.
- Pruebas focales G3/backend/evidencia/control: publicador 18, orquestador 68, backend live 20, lector de evidencia 9 y service control 12 — **127/127 PASS**.
- Suites Bash: `tests/*.sh` — **62/62 PASS**.
- `bash -n` global sobre scripts/módulos/instalador — PASS.
- `python3 -B -m compileall -q scripts tests` — PASS.
- ShellCheck focal `-S error` sobre `modules/xray_service.sh` y `tests/xray_service_control.sh` — PASS; no equivale a ShellCheck global.
- `bash install.sh --check` — PASS, sin modificar el sistema.
- `git diff --check` — PASS.

Esta prevalidación fue ejecutada por la misma sesión que participó en el desarrollo. **No es auditoría independiente, no emite dictamen H6-G3 y no sustituye la revisión solicitada.** El revisor externo debe reproducir lo necesario, reconstruir los flujos y buscar fallos nuevos, no limitarse a aceptar estos resultados.

## Condición de cierre

H6-G3 permanece pendiente hasta que una persona u otra IA independiente, que no haya participado en implementación ni prevalidación, entregue un informe firmado/identificable con el dictamen y evidencias solicitadas. No integrar backend live ni habilitar operaciones reales basándose en esta prevalidación.
