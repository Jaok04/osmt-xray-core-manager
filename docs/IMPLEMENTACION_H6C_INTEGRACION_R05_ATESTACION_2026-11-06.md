# Implementación H6-C — integración controlada R-05/H6-B

**Fecha:** 2026-11-06
**Estado:** implementada, verificada y auditada en alcance exclusivo de mocks/fixtures.
**Rama:** `design/user-identity-association-v1`

## 1. Objetivo

Conectar el ciclo de vida R-05 con el contrato de atestación H6-B mediante una interfaz de backend inyectable, sin cambiar el backend predeterminado ni habilitar acciones sobre systemd/Xray real.

## 2. Backend inyectable

- R-05 mantiene `xray_runtime_service_adapter` como backend predeterminado.
- Se incorporó un contexto `ContextVar` para aislar la selección de backend por ejecución y evitar contaminación entre llamadas.
- Las entradas públicas `apply_operation`, `start_pending_operation` y `recover_operations` aceptan un backend interno opcional.
- El backend predeterminado sigue siendo el adaptador fixture R-05.
- Un backend distinto sólo se admite si declara explícitamente `RUNTIME_BACKEND_TEST_ONLY = True` y cumple la interfaz `status/start/restart/restore/ServiceAdapterError`.
- La selección se limita a dobles de prueba; no existe selector de backend real en CLI ni una implementación mutadora systemd.

La marca `RUNTIME_BACKEND_TEST_ONLY` es una salvaguarda de integración y no una frontera de seguridad frente a código Python arbitrario.

## 3. Integración H6-B

Cuando un backend de prueba proporciona snapshots sintéticos y un `AttestationStore` temporal:

1. R-05 captura el snapshot anterior dentro del lock de ciclo de vida.
2. Ejecuta la acción fixture start/restart.
3. Verifica el estado activo, generation_id y SHA-256 mediante el backend.
4. Captura dos observaciones posteriores (after/confirmed).
5. Persiste H6-B antes de marcar la operación `service_verified/completed`.

La persistencia conserva el lock de ciclo de vida R-05 y adquiere además el lock propio del almacén H6-B. La evidencia debe concordar con operation_id, generation_id y config_sha256 del journal.

Si la atestación falla o diverge, R-05 invalida la verificación y sigue su ruta de rollback existente. No se marca la operación como completada.

## 4. Recuperación

- Si la atestación ya se persistió antes de una interrupción, recovery valida operation_id/generation_id/config_sha256 y puede completar la reconciliación.
- Si se detecta una transición aplicada pero falta la atestación esperada, recovery queda en `RECOVERY_REQUIRED`; no declara éxito.
- Si no se inyectó un almacén H6-B (flujo fixture normal), R-05 conserva su comportamiento anterior.

## 5. Límites deliberados

- Los snapshots usados por H6-C son sintéticos y generados por un doble de prueba.
- H6-A no se invoca desde el backend fixture ni se mezcla con los snapshots simulados.
- H6-A sigue siendo observador read-only; no ejecuta start/restart.
- No se implementó backend mutador systemd.
- No hay selección de backend externo en CLI.
- No se cambió el esquema del journal R-05.
- No se cambió el almacén activo B4 ni se reutiliza como atestación.
- No se ejecutó systemctl real, no se consultó ni modificó el proceso Xray real.
- No se tocaron /etc/xray, /etc/systemd, certificados, DNS, firewall, puertos, red o dependencias.

## 6. Archivos

- Modificado `scripts/xray_runtime_orchestrator.py`.
- Nuevo `tests/test_xray_runtime_h6c.py`.
- Documentación H6-C de implementación y auditoría.

## 7. Verificación

- H6-C focal: 7/7 PASS.
- H6-B focal: 12/12 PASS.
- Regresión Python global: 276/276 PASS.
- compileall, bash -n global, ShellCheck -S error, install.sh --check, pruebas Bash de servicio y git diff --check: PASS.
- El módulo de orquestación y el módulo de atestación no contienen invocaciones a systemctl, subprocess, shell ni eval.

## 8. Dictamen

H6-C queda IMPLEMENTADA, VERIFICADA Y AUDITADA, PASS CON LIMITACIONES. La integración probada demuestra el flujo R-05/H6-B bajo dobles de prueba; no acredita una invocación systemd real ni una generación cargada por un proceso Xray real. H6 live permanece NO AUTORIZADA. No se realizó commit ni push.
