# Auditoría R-04 — publicación atómica y rollback aislados

**Fecha:** 2026-11-04
**Resultado:** PASS en entorno aislado; pendiente de aceptación formal del propietario.

## 1. Alcance auditado

Se revisó `scripts/xray_runtime_publisher.py`, la ampliación del esquema en `scripts/xray_runtime_journal.py`, y las pruebas `tests/test_xray_runtime_publisher.py` e integración `tests/test_xray_runtime_staging.py`.

La operación solo acepta el staging vinculado a profile_id + revision, validation_id, manifiesto, asociaciones, leases TLS y huella del binario. XRAY_SERVICE_ROOT, operation_store y lease_root requieren marcadores fixture; no hay fallback a almacenes ni destinos reales.

## 2. Matriz focal R-04

| Caso | Resultado |
|---|---|
| Publicación atómica, hash/propietario/permisos, rollback exacto e idempotencia de publicación/restauración | PASS |
| Sin config previa: no borrar al hacer rollback | PASS |
| Crash después del primer rename sin config previa: recovery_required | PASS |
| Crash antes del rename: conservar anterior y limpiar temporal en recovery | PASS |
| Crash después del rename antes del journal: detectar y revertir | PASS |
| Crash después del rename de rollback: recovery idempotente | PASS |
| Cambio externo del destino/TOCTOU | PASS — no sobrescribe |
| Symlink en destino | PASS — rechazado |
| Hardlink en destino | PASS — rechazado |
| Contención de lock | PASS — operación bloqueada |
| Snapshot corrupto | PASS — publicación bloqueada |
| Xray rechaza candidato | PASS — config anterior intacta |

Prueba focal `tests/test_xray_runtime_publisher.py`: **12/12 PASS**.

## 3. Integración y regresión

- R-02 staging + lease TLS sintético → R-03 snapshot/journal → R-04 publicación/rollback: PASS en fixture temporal.
- `tests/test_xray_runtime_staging.py`: **11/11 PASS**.
- `tests/test_xray_runtime_journal.py`: **22/22 PASS**.
- Regresión Python: **153/153 PASS**.
- Regresión shell: **58/58 PASS**.
- `py_compile`, `bash -n` global, `install.sh --check`, ShellCheck severidad error y `git diff --check`: PASS.

## 4. Límites

La publicación solo escribe el destino dentro de XRAY_SERVICE_ROOT fixture. El binario Xray valida el temporal y la configuración restaurada bajo identidad UID/GID simulada. No hay interacción con systemd, proceso Xray real, almacenes/llaves reales, certificados desplegados, red ni firewall.

R-04 no prueba que el servicio real esté ejecutando la nueva configuración. Ese punto pertenece a R-05/R-06 y requiere autorizaciones separadas. No confundir `xray run -test` con activación real.

## 5. Dictamen

R-04 queda implementada y supera la matriz focal y regresión descritas. No se declara Etapa 5 ni subfase runtime cerrada. Requiere revisión y aceptación formal del propietario antes de commit/push. R-05 pendiente; R-06/live NO AUTORIZADA.


## Reconciliación posterior de publicación — 2026-11-04

R-04 está AUDITADA, PUBLICADA y SINCRONIZADA en la rama autorizada, commit de corte `05aceabf11414040abbb32fff1428984370ff521`. La aceptación formal del propietario sigue PENDIENTE. El estado de aceptación del expediente permanece pendiente; su publicación posterior queda confirmada por el commit de corte. El dictamen y sus límites permanecen vigentes.
