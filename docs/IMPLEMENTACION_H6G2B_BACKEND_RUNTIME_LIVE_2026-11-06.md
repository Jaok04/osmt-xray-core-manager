# H6-G2-B — Contrato aislado del backend runtime live

**Fecha:** 2026-11-06
**Rama:** `design/user-identity-association-v1`
**Estado:** implementado en desarrollo y validado con mocks; no integrado ni habilitado.

## 1. Objetivo y límites

Completar la primera capa del backend live separada del adaptador fixture: observación systemd + correlación de proceso, precondiciones para acciones limitadas y contrato de resultado no verificado. No se conecta a R-05, CLI ni menú. No se ejecuta ninguna acción real de systemd.

## 2. Archivos nuevos

- `scripts/xray_runtime_live_backend.py`
- `tests/test_xray_runtime_live_backend.py`

## 3. Modelo de observación

El backend compone:
1. `xray_runtime_systemd_adapter.status()` (read-only): unidad, estado, PID, InvocationID, hash del archivo runtime y contrato efectivo de la unidad.
2. `xray_runtime_process_attestation.observe_process_identity()`: doble observación systemd y verificación de MainPID, starttime, ejecutable, argv, UID/GID y SHA-256 del binario.

El snapshot expone por separado:
- `published_config_sha256`: no lo inventa el observador; permanece null hasta que el orquestador aporte el dato de publicación.
- `runtime_config_sha256`: hash del archivo presente en disco.
- `process_identity`: evidencia de identidad del proceso correlacionada con PID e InvocationID.
- `loaded_generation_id` y `loaded_config_sha256`: siempre null.
- `configuration_loaded=false`, `configuration_evidence=not_attested`.

El estado `failed` o `unknown` se puede observar y reportar, pero bloquea cualquier mutación. Estados transitorios también bloquean.

## 4. Precondiciones de acciones

- `start`: confirmación explícita, estado inicial `inactive`, hash runtime igual al SHA-256 esperado.
- `restart`: confirmación explícita, estado `active`, proceso correlacionado, hash runtime igual al esperado.
- `stop`: confirmación explícita, servicio `active`, identidad de proceso verificada, hash runtime esperado y justificación de recuperación no vacía.
- Antes de delegar se toma un segundo snapshot y se comparan estado, PID, InvocationID y hash runtime (CAS conservador).
- Mutaciones delegadas únicamente a `xray_runtime_service_control.run_action()`, que pasa descriptor lifecycle lock a `modules/xray_service.sh`.
- El resultado `accepted_not_verified` solo significa que el controlador aceptó la solicitud. La postcondición queda `pending_observation`; no se declara servicio activo ni configuración cargada.

El lifecycle lock serializa operaciones del Manager, pero no impide cambios externos directos a systemd. La reobservación reduce la ventana de carrera, no constituye un CAS atómico del propio systemd. G3 debe conservar la observación posterior y el estado ambiguo como recuperación requerida.

## 5. Restore / rollback

`restore()` falla cerrado deliberadamente. No es correcto reiniciar Xray ni restaurar servicio desde este adaptador aislado: primero debe publicarse atómicamente la configuración previa, verificarse su hash, demostrar que el InvocationID/proceso observado pertenece a la operación fallida y luego solicitar la recuperación por el controlador único. Esa secuencia pertenece a G3, con journal y estado `RECOVERY_REQUIRED` si no se demuestra.

## 6. Pruebas

- Backend nuevo: 14/14 PASS.
- Puente control servicio + systemd read-only + atestación proceso: 45/45 PASS.
- Suite Python completa: 355/355 PASS.
- Suites Bash completas: 62/62 PASS.
- `bash -n`, `py_compile`, `git diff --check`: PASS.

Las pruebas usan mocks/fixtures. No ejecutan systemctl real ni modifican configuración, certificados, firewall, DNS, puertos o red.

## 7. Estado de cierre

H6-G2-B queda implementado y probado como componente aislado. H6-G2 global permanece **PARCIAL / NO CERRADO** hasta revisión independiente y auditoría formal del bloque. No se integró backend live en `_with_service_backend`, R-05 ni menú. Fixture sigue como default. Sin commit ni push.
