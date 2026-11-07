# Auditoría técnica independiente H6-G2 — backend runtime live

**Fecha:** 2026-11-06
**Rama:** `design/user-identity-association-v1`
**HEAD:** `9bab1dbed7d4873aa30a3fd00a976a1d666d9355`
**Alcance:** revisión estática, revisión de contrato, pruebas automatizadas y probes adversariales en VPS de desarrollo.
**Resultado:** **PASS CON LIMITACIONES — NO APTO PARA INTEGRACIÓN LIVE / NO CERRAR G2**.

## 1. Alcance revisado

- `docs/DECISION_H6G1_CONTRATO_BACKEND_RUNTIME_LIVE_2026-11-06.md`
- `scripts/xray_runtime_service_control.py`
- `modules/xray_service.sh` (controlador y puente de lock heredado)
- `scripts/xray_runtime_systemd_adapter.py`
- `scripts/xray_runtime_process_attestation.py`
- `scripts/xray_runtime_live_backend.py`
- `tests/test_xray_runtime_service_control.py`
- `tests/test_xray_runtime_live_backend.py`
- `tests/xray_service_control.sh`
- documentos de implementación y continuidad H6-G2.

La revisión se realizó sobre la VPS de desarrollo `Implementación-Xray`, ruta `/opt/xray-manager`. No se inspeccionó ni modificó la VPS de pruebas.

## 2. Verificaciones satisfactorias

1. El puente Python no ejecuta `systemctl`; delega únicamente en `modules/xray_service.sh`.
2. La superficie de acciones está limitada a `start`, `restart` y `stop`.
3. El puente valida root, descriptor, ruta absoluta, inode, propietario/permisos y ruta protegida del controlador; hereda el descriptor con `pass_fds`.
4. El controlador Bash verifica la unidad administrada, valida configuración con Xray antes de start/restart y comprueba estado activo/inactivo tras la operación.
5. El observador systemd es read-only y diferencia hash de archivo runtime de evidencia de configuración cargada.
6. La atestación correlaciona MainPID e InvocationID y comprueba identidad del proceso.
7. El backend live no se encuentra conectado a `_with_service_backend`, R-05 ni al menú. Fixture sigue siendo el backend por defecto.
8. `restore()` falla cerrado; no simula ni declara rollback live.

## 3. Hallazgos y acciones requeridas

### F-01 — Invariantes incompletos para estado inactive

**Severidad: media.**

`LiveRuntimeBackend._validate_snapshot()` acepta un snapshot `inactive` aunque incluya `main_pid=4321` y un `invocation_id` válido. Se reprodujo mediante un probe adversarial: el validador aceptó ese estado contradictorio.

El adaptador systemd real normalmente devuelve MainPID cero y sin InvocationID cuando está inactivo, pero el backend debe defender su propio contrato y no depender de que la fuente nunca regrese datos contradictorios.

**Corrección exigida antes de G3:** para `inactive`, exigir MainPID nulo/cero y ausencia de InvocationID/proceso; para `active`, exigir PID > 1, InvocationID válido, subestado `running`, resultado satisfactorio y atestación completa. Añadir pruebas negativas.

### F-02 — start no acredita publicación ni validación de la generación

**Severidad: alta como requisito de integración.**

`start()` compara el hash del archivo runtime con `expected_runtime_config_sha256`, pero el backend devuelve `published_config_sha256=None` y no recibe prueba de que ese hash proviene de una generación publicada y validada por R-05.

Por tanto, el hash coincidente demuestra el contenido actual del archivo, no que el Manager haya publicado la generación correcta ni que se haya ejecutado la validación transaccional requerida.

**Corrección exigida antes de G3:** el orquestador debe pasar una referencia de operación/generación y la evidencia de validación/publicación; el backend debe comprobar que el hash runtime coincide con el hash publicado de esa operación. No aceptar un hash libre como única autorización de `start`.

### F-03 — El puente no demuestra que R-05 ya era propietario del lock

**Severidad: media; desviación del contrato G1.**

`_validate_lock_descriptor()` ejecuta `flock(LOCK_EX|LOCK_NB)` sobre el descriptor. Si el descriptor es válido pero todavía no estaba bloqueado, esa llamada adquiere el lock. La función Bash vuelve a comprobarlo de la misma manera.

Esto sí garantiza exclusión mutua durante la acción, pero no demuestra literalmente que el descriptor fue adquirido previamente por R-05, como exige el contrato G1. El puente puede actuar como adquirente efectivo cuando recibe un descriptor válido no bloqueado.

**Corrección exigida antes de G3:** resolver la propiedad del lock de forma explícita: o R-05 sigue siendo el propietario y la interfaz demuestra el handoff de forma verificable, o se revisa/aprueba un diseño donde el puente sea el propietario único. No describir el comportamiento actual como prueba de que R-05 ya poseía el lock.

### F-04 — Timeout requiere reconciliación externa

**Severidad: media; pendiente de G3.**

El puente devuelve error al expirar el timeout y no declara éxito. No obstante, la llamada no incluye reconciliación posterior ni registra por sí misma `RECOVERY_REQUIRED`. El orquestador deberá observar systemd/proceso antes de cualquier reintento; matar el proceso cliente no debe interpretarse como cancelación garantizada de un trabajo ya aceptado por systemd.

**Acción:** G3 debe convertir timeout, pérdida de respuesta o estado ambiguo en una transición journal explícita; nunca reintentar a ciegas.

### F-05 — Restore/rollback live aún no existe

**Severidad: alta para despliegue end-to-end; limitación declarada.**

`restore()` rechaza toda solicitud. Es la conducta segura mientras no exista restauración atómica del archivo anterior, verificación de hash, correlación de InvocationID/proceso y reconciliación del servicio.

**Acción:** implementar en G3 junto con journal, snapshots y `RECOVERY_REQUIRED`. No habilitar operaciones de publicación/inicio live antes de ello.

## 4. Pruebas ejecutadas durante la auditoría

- Backend live aislado: 14/14 PASS.
- Puente Python + observador systemd + atestación de proceso: 45/45 PASS.
- Suite Python completa: 355/355 PASS.
- Suites Bash completas: 62/62 PASS.
- `bash -n`: PASS.
- `py_compile`: PASS.
- `git diff --check`: PASS.
- ShellCheck `-S error` sobre `modules/xray_service.sh` y `tests/xray_service_control.sh`: PASS.
- Probe adversarial F-01: reprodujo aceptación de snapshot inactive contradictorio.

Las pruebas se ejecutaron con mocks/fixtures. No se ejecutó systemctl real ni se cambió configuración runtime, certificados, DNS, firewall, puertos o red.

## 5. Dictamen

El puente Python/Bash y la observación read-only tienen una base técnica razonable y pasan las pruebas disponibles. Sin embargo, la auditoría no puede aprobar la integración live por F-01, F-02 y F-03; F-04 y F-05 deben resolverse en la capa transaccional G3.

**Estado oficial:**
- H6-G2: **PARCIAL — NO CERRADO**.
- Backend live: **NO HABILITADO**.
- Backend fixture: continúa como predeterminado.
- Despliegue real VLESS + WS + TLS: **NO AUTORIZADO POR ESTA AUDITORÍA**.

## 6. Siguiente secuencia recomendada

1. Corregir F-01 y ampliar pruebas de estados contradictorios.
2. Diseñar el contrato de evidencia de generación/publicación/validación para F-02.
3. Resolver formalmente la propiedad del lifecycle lock para F-03 y actualizar G1 si se aprueba un cambio contractual.
4. Implementar G3 con journal, post-observación, timeout ambiguo, rollback atómico y recuperación conservadora.
5. Auditar G3 antes de conectar el backend live al menú.

No se hicieron commits ni push. No se modificó `main` ni `Xray-Normativa/`.


## Seguimiento de F-03 — implementación posterior (2026-11-06)

El hallazgo F-03 de esta auditoría se corrigió posteriormente en el puente aislado. La validación ya no ejecuta `flock` sobre el descriptor recibido; ahora exige una entrada FLOCK exclusiva vinculada al descriptor exacto en `/proc/.../fdinfo`, PID propietario igual al proceso R-05 e inode esperado. Bash verifica nuevamente el registro heredado y falla cerrado si fdinfo no está disponible.

Pruebas focales posteriores: puente Python 12/12 y Bash de control PASS; suite Python global 373/373, suites Bash 62/62 y verificaciones estáticas PASS. Este seguimiento no altera el dictamen original ni equivale a auditoría independiente del cambio. G2 sigue sin cerrar; la integración R-05 y el alcance continuo del lock quedan para G3.
