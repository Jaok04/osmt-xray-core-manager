# H6-G2 — Puente seguro de control del servicio Xray

**Fecha:** 2026-11-06
**Rama:** `design/user-identity-association-v1`
**Alcance:** implementación local en desarrollo; sin commit, push ni operaciones live.

## 1. Objetivo

Contrato aprobado G1: `docs/DECISION_H6G1_CONTRATO_BACKEND_RUNTIME_LIVE_2026-11-06.md`.

Implementar la primera pieza del backend systemd live: delegar las mutaciones permitidas al controlador único `modules/xray_service.sh`, reutilizando el descriptor del lifecycle lock que ya posee el orquestador R-05.

Este bloque no habilita todavía el backend live en R-05 ni en el menú. El backend fixture continúa siendo el predeterminado.

## 2. Contraste normativo

La implementación respeta:

- **Etapa 5, sección 7:** aplicar un perfil requiere confirmación, validación y verificación real antes de actualizar el registro activo; ante fallo debe intentarse recuperar la configuración anterior y registrarse el estado parcial.
- **Etapa 6, módulo 1:** start/restart deben validar instalación/unidad y comprobar el resultado; stop requiere confirmación; el inicio automático es independiente.
- **Etapa 6, reglas transversales:** reutilizar módulos existentes, no duplicar controladores, releer antes de cambios, bloquear ante concurrencia, usar timeouts/reintentos limitados, registrar resultados parciales y no repetir a ciegas.
- **Auditoría técnica final, secciones 3.6 y 3.7:** las pruebas runtime deben aislarse y los mecanismos de concurrencia/recuperación deben validarse antes de habilitar cambios reales.

No se modifica la documentación normativa aprobada.

## 3. Archivos modificados

- `modules/xray_service.sh`
  - Se agrega `xray_service_action_inherited_lock()`.
  - Solo acepta `start`, `restart` y `stop`.
  - Comprueba descriptor numérico abierto, ruta exacta, identidad dispositivo/inode, propietario root:root, modo 0600 y bloqueo exclusivo.
  - Solo después delega en `xray_service_action_locked()`.
  - No sustituye ni duplica la función pública `xray_service_action()`.

- `scripts/xray_runtime_service_control.py`
  - Nuevo puente Python para R-05.
  - Valida root, descriptor, ruta sin symlinks, inode y permisos.
  - Conserva el lock durante la llamada y pasa el descriptor explícitamente con `pass_fds`.
  - Invoca Bash y carga `modules/xray_service.sh`; no ejecuta `systemctl` directamente.
  - Superficie de acciones limitada a start/restart/stop.
  - Un timeout o resultado no satisfactorio genera error controlado y no declara éxito.

- `tests/test_xray_runtime_service_control.py`
  - Pruebas de contrato del puente Python, validación del descriptor, bloqueo concurrente, timeout y rechazo del controlador.

- `tests/xray_service_control.sh`
  - Pruebas aisladas del puente Bash, descriptor correcto, descriptor ajeno y descriptor ausente.

## 4. Decisión de bloqueo — versión inicial, sustituida por F-03

La implementación inicial pasaba el descriptor de R-05 y comprobaba ruta/inode, pero utilizaba `flock -n` sobre el descriptor heredado como verificación. Esa comprobación no era suficiente: sobre el mismo open-file-description podía adquirir el lock si estaba libre.

La corrección autorizada F-03 sustituye íntegramente esa verificación por evidencia del descriptor en `/proc/.../fdinfo`, exige FLOCK exclusivo vinculado al descriptor y PID propietario igual al proceso R-05. La decisión y el cambio están documentados en `docs/DECISION_H6G2_F03_PROPIEDAD_LIFECYCLE_LOCK_2026-11-06.md` y `docs/IMPLEMENTACION_H6G2_F03_PROPIEDAD_LIFECYCLE_LOCK_2026-11-06.md`.

La función `xray_service_action_locked()` sigue siendo el controlador interno único. El puente no adquiere ni renueva locks.

## 5. Límites explícitos

Este bloque **no**:

- habilita el backend live en `_with_service_backend`;
- modifica `xray_runtime_orchestrator.py`, el journal ni el menú;
- adapta todavía la semántica fixture de generation/hash al modelo de evidencia systemd;
- implementa rollback live de archivo + proceso;
- ejecuta systemctl real, inicia/detiene/reinicia Xray o modifica `/etc/xray/config.json`;
- acredita qué bytes fueron cargados en memoria por Xray.

El adaptador read-only `xray_runtime_systemd_adapter.py` sigue siendo la fuente de observación systemd. La atestación H6-E continúa limitada a identidad de proceso e InvocationID, no a configuración cargada.

## 6. Pruebas ejecutadas

- `python3 -m unittest tests.test_xray_runtime_service_control -v`
- `bash tests/xray_service_control.sh`
- `python3 -m unittest tests.test_xray_runtime_systemd_adapter tests.test_xray_runtime_process_attestation tests.test_xray_runtime_process_identity -v`
- `bash -n modules/xray_service.sh tests/xray_service_control.sh`
- `python3 -m py_compile scripts/xray_runtime_service_control.py`

Resultados observados al momento de documentar:
- Puente Python: 9/9 PASS, incluyendo integración Python → descriptor heredado → Bash → systemctl mock.
- Control Bash: PASS, incluyendo descriptor correcto, descriptor ajeno y descriptor ausente.
- Systemd read-only + atestación de proceso/identidad: 58/58 PASS.
- Suite Python completa: 340/340 PASS.
- Suites Bash completas: 62/62 PASS (incluye pruebas aisladas de Xray 26.10.31 para configuraciones VLESS/VMess; no es prueba de servidor WAN).
- `bash -n`, `py_compile` y `git diff --check`: PASS.

## 7. Estado y siguientes pasos

**Estado: implementación parcial de H6-G2; no habilitada para producción.**

Antes de cerrar G2:
1. Realizar revisión independiente del código y del contrato de lock.
2. Auditar errores, timeouts y el ciclo de vida del descriptor.
3. Revisar el diff final y confirmar que no se habilitó el backend live.
4. Emitir la auditoría formal de G2.

G3 deberá diseñar e integrar la semántica de estado/rollback live y mantener la separación entre hash del archivo publicado y evidencia de proceso. Hasta entonces, el puente no debe exponerse al menú ni utilizarse contra una unidad real.
