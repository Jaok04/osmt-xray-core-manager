# H6-G3-A/B — coordinación transaccional de locks en R-05

**Fecha:** 2026-11-06
**Alcance:** rama de desarrollo, fixtures/mocks únicamente.
**Estado:** implementación focal completada; auditoría independiente pendiente.

## Cambios

### 1. Propietario único de locks

En `scripts/xray_runtime_publisher.py` se añadió `transaction_locks()`, un contexto propietario de lifecycle lock y application lock. Conserva el orden lifecycle → application y libera en orden inverso. Un contexto anidado con las mismas rutas reutiliza al propietario; un conjunto de rutas diferente se rechaza. `_acquire()` valida las rutas y devuelve una lista vacía cuando ya existe el contexto propietario, por lo que los `finally` heredados no liberan locks que no poseen.

### 2. Apply, publicación, transición y rollback

`apply_operation()` mantiene preflight/staging/preparación fuera de la sección crítica, pero revalida el servicio bajo lock antes de modificar el runtime. La continuación posterior a la preparación se trasladó a `_continue_apply_operation()`, que conserva ambos locks durante:

- revalidación de estado inicial;
- confirmación persistida;
- publicación atómica y commit del journal;
- solicitud de start/restart y observación;
- registro del perfil activo;
- rollback de configuración y reconciliación del servicio;
- persistencia de estado terminal o `RECOVERY_REQUIRED`.

Los caminos `_execute_restart()`, `_execute_start()` y `_restore_after_failure()` reutilizan el mismo contexto. Ya no existe una liberación entre el fallo de transición y la entrada al rollback.

### 3. Start pendiente y recuperación

`start_pending_operation()` conserva el lock desde la lectura/verificación de la operación pending hasta la transición, observación y posible rollback. `_recover_one()` mantiene un único contexto durante la lectura del journal, observación, continuación conservadora o rollback. Las llamadas recursivas y a helpers anidados reutilizan el mismo propietario; las antiguas llamadas `release_locks([])` no liberan el lock exterior.

### 4. Pruebas nuevas

- `test_nested_transaction_context_reuses_one_lock_owner`: contexto anidado reutiliza los locks; rutas distintas se rechazan; los locks quedan disponibles al salir.
- `test_lifecycle_lock_remains_owned_across_publish_restart_and_rollback`: un segundo descriptor no puede adquirir lifecycle lock durante restart ni rollback.
- `test_pending_start_holds_lifecycle_lock_through_start_and_rollback`: el mismo invariante para start explícito.
- `test_recovery_keeps_lifecycle_lock_through_nested_rollback`: recovery conserva el lock durante el rollback anidado.

## Validación

- Python global: **377/377 PASS**.
- Suites Bash: **62/62 PASS**.
- `py_compile` y `compileall`: PASS.
- `bash -n` sobre módulos/scripts/instalador: PASS.
- ShellCheck `-S error`: PASS.
- `git diff --check`: PASS.

## Límites y pendientes

- Todo el flujo ejercitado usa fixture y mocks; no se ejecutó `systemctl`, Xray real ni backend live.
- No se modificó el journal para aceptar `environment=live`; el lector F-02 continúa produciendo evidencia fixture y el backend live la rechaza.
- No se conectó backend live a R-05, CLI ni menú.
- G3-C sigue pendiente: reconciliación explícita de timeout/resultado ambiguo y `RECOVERY_REQUIRED` sin retry ciego.
- G3-D sigue pendiente: auditoría adversarial integral del rollback fixture y su idempotencia bajo failpoints adicionales.
- G3-E auditoría independiente integral pendiente.
- H6-G2 permanece abierto; no se declara G3 cerrado ni listo para live.

No hubo instalación/actualización de dependencias, operaciones live, cambios de runtime persistente, systemd, certificados, DNS, firewall, puertos o red. No se hicieron commits ni push; `main` y `Xray-Normativa/` permanecen intactas.
