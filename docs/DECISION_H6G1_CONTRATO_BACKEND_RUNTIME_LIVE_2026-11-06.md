# H6-G1 — Contrato técnico del backend runtime live

**Fecha:** 2026-11-06
**Rama:** `design/user-identity-association-v1`
**Estado:** contrato aprobado por el propietario; diseño, sin habilitación live.

## 1. Propósito

Definir la integración futura entre R-05 y systemd sin duplicar el controlador del servicio, sin romper el lifecycle lock y sin convertir observaciones parciales en afirmaciones de configuración cargada.

## 2. Fuentes revisadas

- `scripts/xray_runtime_orchestrator.py`
- `scripts/xray_runtime_publisher.py`
- `scripts/xray_runtime_journal.py`
- `scripts/xray_runtime_service_adapter.py`
- `scripts/xray_runtime_systemd_adapter.py`
- `scripts/xray_runtime_process_attestation.py`
- `modules/xray_service.sh`
- `lib/operation_lock.sh`
- `docs/PLAN_MVP_DESPLIEGUE_VLESS_WS_TLS_2026-11-04.md`
- `docs/EVALUACION_H6F_PREPARACION_PRUEBA_REAL_2026-11-06.md`
- Normativa aprobada: Etapa 5 §§4–7; Etapa 6, módulo 1 y reglas transversales; Auditoría Técnica Final §§3.6–3.7.

## 3. Hallazgos de arquitectura

1. R-05 sigue fixture-only. `_with_service_backend` rechaza backends no marcados como dobles de prueba; `apply_operation` declara orquestación fixture.
2. R-05 adquiere lifecycle lock y application lock. `xray_service_action()` adquiere lifecycle lock por su cuenta; llamarlo desde R-05 produciría colisión con `flock -n`.
3. Existe `xray_service_action_locked()`, pero debe invocarse únicamente mediante una interfaz que demuestre propiedad del lock; una variable de entorno declarativa no es prueba suficiente.
4. El observador systemd proporciona PID, InvocationID y hash del archivo runtime, pero no generation_id ni hash de configuración cargada.
5. La atestación H6-E acredita identidad del proceso y correlación con systemd, no bytes de configuración cargados en memoria.
6. El rollback fixture cambia estado simulado; el rollback live necesita coordinar restauración atómica de archivo y transición real del servicio, con recuperación conservadora ante ambigüedad.

## 4. Contrato aprobado

### 4.1 Autoridad y responsabilidades

- R-05 conserva la coordinación transaccional: preflight, journal, locks, publicación, solicitud, verificación y recuperación.
- `modules/xray_service.sh` permanece como controlador único de start/stop/restart.
- `scripts/xray_runtime_systemd_adapter.py` permanece read-only.
- El puente Python no ejecutará `systemctl` directamente.
- Fixture continúa como backend predeterminado. Live no se expone a menú/CLI hasta superar implementación y auditoría separadas.

### 4.2 Lifecycle lock

- Un único propietario mantiene lifecycle lock durante toda la transición coordinada.
- El descriptor adquirido por R-05 se pasa explícitamente al proceso Bash mediante herencia de descriptor.
- El receptor verifica descriptor abierto, ruta esperada, dispositivo/inode, propietario/permisos y bloqueo exclusivo.
- No se permite depender exclusivamente de `XRAY_MANAGER_LIFECYCLE_LOCK_HELD=1`.
- Orden de adquisición: lifecycle lock y luego application lock; liberar en orden inverso.
- Ninguna ruta debe adquirir los mismos locks en orden contrario.

### 4.3 Observación

El backend observa estado systemd, PID, InvocationID, timestamps, unidad efectiva, identidad del proceso y hash actual del archivo runtime. Debe mantener separados:

- `published_config_sha256`: bytes publicados por el Manager.
- `runtime_config_sha256`: bytes observados actualmente en el archivo.
- `process_identity`: evidencia del proceso asociado a MainPID/InvocationID.
- `loaded_config_sha256`: no disponible salvo evidencia específica que lo demuestre.

No inferir configuración cargada desde ActiveState, PID, InvocationID, hash de archivo ni registro activo.

### 4.4 Acciones y precondiciones

- `start`: solo desde inactive, después de publicar y validar, con confirmación explícita.
- `restart`: solo desde active, con confirmación explícita.
- `stop`: solo para recuperación justificada, con identidad y propiedad del proceso verificadas.
- `enable/disable`: fuera del alcance inicial de R-05; son operaciones de preferencia independientes.

El controlador valida la unidad administrada y ejecuta `xray run -test` antes de start/restart.

### 4.5 Verificación y rollback

La transición exige resultado del controlador y nueva observación systemd correlacionada con PID/InvocationID y evidencia de proceso. Hash del archivo y evidencia del proceso se registran por separado.

- Estado inicial inactive: publicar no inicia; rollback no inicia.
- Estado inicial active: reinicio solo tras confirmación; si falla la aplicación, restaurar archivo previo y recuperar el servicio solo si se demuestra que la invocación observada pertenece a la operación.
- Estado failed/unknown: bloquear automatización.
- Timeout, respuesta perdida o estado ambiguo: observar antes de reintentar.
- Si no se demuestra recuperación: `RECOVERY_REQUIRED`; no declarar éxito ni repetir a ciegas.

## 5. Secuencia de bloques

- **G1:** contrato y auditoría de diseño. Aprobado.
- **G2:** puente de control Bash/Python con descriptor heredado, pruebas aisladas y mocks. Implementación parcial en curso; sin integración R-05.
- **G3:** modelo live de observación, transiciones, correlación, journal y rollback.
- **G4:** conexión controlada al menú, manteniendo fixture como default y live bloqueado hasta aprobación.
- **G5:** auditoría integral y preparación de una prueba live específica. Requiere autorización separada por host/operaciones.

## 6. Restricciones de seguridad

Este contrato no autoriza instalación real, Certbot, publicación en `/etc/xray`, start/restart/stop en una VPS, cambios DNS/firewall/puertos/red, ni commit/push. `main` y `Xray-Normativa/` permanecen fuera del alcance.
