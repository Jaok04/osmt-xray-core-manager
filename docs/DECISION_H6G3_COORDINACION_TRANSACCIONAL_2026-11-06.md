# H6-G3 — diseño de coordinación transaccional y recuperación

**Fecha:** 2026-11-06
**Rama:** `design/user-identity-association-v1`
**Estado:** diseño técnico inicial; no implementado ni auditado.
**Alcance:** desarrollo/fixtures únicamente. No habilita backend live.

## 1. Objetivo

Cerrar las ventanas de concurrencia entre publicación, transición del servicio, observación, journal y rollback. Mantener una sola autoridad de locks y evitar reacquisiciones anidadas.

## 2. Hallazgos confirmados en la inspección

1. `publisher.publish_operation()` adquiere y libera lifecycle + application locks alrededor de la publicación.
2. `_execute_restart()` y `_execute_start()` vuelven a adquirir ambos locks para la transición y observación.
3. Si la transición falla, esas funciones liberan los locks antes de llamar a `_restore_after_failure()`, que vuelve a adquirirlos. Existe una ventana de intercalado entre el fallo y el rollback.
4. `apply_operation()` deja una ventana entre publicación y transición: el publicador libera locks antes de que el orquestador solicite restart.
5. `start_pending_operation()` persiste la solicitud y libera locks antes de ejecutar start.
6. `_recover_one()` libera y vuelve a adquirir locks en rutas de rollback y continuación de transición.
7. El publicador y journal actuales son fixture-only. El lector F-02 devuelve deliberadamente `environment=fixture`; el backend live rechaza correctamente esta evidencia.

## 3. Contrato de G3

### 3.1 Propiedad de locks

- Orden invariable: lifecycle lock y luego application lock.
- Un solo ámbito coordinador conserva ambos locks desde la entrada a la sección crítica de apply/start/recovery hasta que termina la verificación, rollback o persistencia de `RECOVERY_REQUIRED`.
- Los helpers internos aceptan un contexto de locks ya adquirido; no deben adquirirlos de nuevo.
- Los helpers que adquieren locks por sí mismos mantienen compatibilidad para invocaciones independientes, y liberan únicamente los locks de los que son propietarios.
- La liberación siempre es inversa: application y luego lifecycle.
- Una excepción o crash simulado libera descriptores en el proceso; el journal deja estado recuperable y la recuperación posterior vuelve a adquirir los locks desde cero.

### 3.2 Transacción de apply

1. Preparar staging y journal bajo las protecciones existentes.
2. Adquirir ambos locks en orden.
3. Revalidar estado del servicio y snapshot.
4. Publicar configuración mediante una ruta interna que reutilice los locks ya adquiridos.
5. Persistir solicitud de transición antes de invocarla.
6. Ejecutar la transición solo a través del adaptador permitido.
7. Observar y correlacionar el resultado.
8. Si falla o queda ambiguo, realizar rollback de configuración y reconciliación del servicio bajo los mismos locks.
9. Persistir estado terminal o `RECOVERY_REQUIRED`.
10. Liberar locks.

### 3.3 Start pendiente y recovery

- `start_pending_operation` debe conservar el mismo ámbito desde la validación/confirmación hasta observación o recuperación.
- `_recover_one` no debe liberar locks para llamar helpers que vuelven a adquirirlos. Debe transferir/reutilizar el contexto de locks.
- No se reintenta una acción de servicio solo por timeout o respuesta perdida. Primero se observa el estado y se correlaciona con journal, generación y evidencia disponible.
- Estado failed/unknown o correlación insuficiente termina en `RECOVERY_REQUIRED`.

### 3.4 Rollback

- Restaurar bytes de configuración no equivale a restaurar el servicio.
- La secuencia debe registrar separadamente `config_status` y `service_status`.
- Si el estado previo era inactive, no se emite start durante rollback.
- Si el estado previo era active, solo se permite recuperar el servicio si la transición observada pertenece inequívocamente a la operación.
- Si no puede demostrarse la pertenencia de la invocación o el estado es ambiguo, no se ejecuta una mutación adicional y se registra `RECOVERY_REQUIRED`.
- El rollback live de archivo + proceso no está implementado en G2; no se debe simular ni conectar con el rollback fixture.

## 4. Límites de habilitación

- Fixture permanece como backend predeterminado.
- No conectar `LiveRuntimeBackend` a R-05, CLI o menú en G3.
- No cambiar el journal fixture-only para aceptar `environment=live`.
- No habilitar systemd real, publicación en `/etc/xray`, ni start/restart/stop reales.
- La evidencia `loaded_config_sha256` seguirá ausente salvo mecanismo específico que la acredite.
- F-04 (reconciliación tras timeout) y F-05 (rollback live completo) requieren contratos, pruebas y auditorías específicas; no se declaran resueltos por el refactor de locks.

## 5. Secuencia de implementación

- **G3-A:** reutilización explícita de locks en publicador/orquestador; transacción fixture de apply y rollback sin ventanas de reacquisición.
- **G3-B:** start pendiente y rutas de recovery con el mismo contexto; eliminar liberaciones/reacquisiciones intermedias.
- **G3-C:** endurecer timeout/resultado ambiguo: observación obligatoria, no retry ciego, journal `RECOVERY_REQUIRED` cuando no se demuestra el resultado.
- **G3-D:** rollback fixture idempotente y adversarialmente probado; mantener claramente separado del rollback live.
- **G3-E:** auditoría integral independiente, revisión de invariantes y actualización de continuidad.

## 6. Criterios de aceptación

1. No hay reacquisición de lifecycle/application lock dentro de una sección crítica.
2. No existe ventana entre publicación y transición, ni entre fallo y rollback, ni entre confirmación de start y observación.
3. Todas las salidas y excepciones liberan exactamente los locks que posee el ámbito.
4. Pruebas concurrentes demuestran que una segunda operación no puede intercalarse en una transacción activa.
5. Failpoints antes/después de publicación, petición, transición, observación y rollback recuperan sin duplicar acciones.
6. Suite Python/Bash, análisis estático y diff-check completos.
7. Dictamen separado para fixture y live; live permanece deshabilitado.

## 7. Estado

Esta entrega registra el diseño derivado de la inspección de código. No modifica código funcional, journal, dependencias, ramas, commits ni configuración del sistema. G3 continúa abierto y pendiente de implementación y auditoría.
