# Coordinador durable de start live — etapa fixture (2026-11-08)

**Estado:** implementado y probado con dobles; sin conexión a backend live real, CLI, menú, R-05 o servicio systemd. No autoriza operaciones live.

## Alcance

Se añadió `scripts/xray_runtime_live_start_coordinator.py`, API interna `start_published_operation(...)`, y siete pruebas aisladas. Recibe explícitamente el almacén de journal, backend, observadores read-only de systemd/proceso y lector del hash runtime. No tiene CLI ni crea por sí misma locks o servicios: el caller futuro deberá conservar el lifecycle lock y entregar el backend correctamente configurado.

## Secuencia durable

1. Comprueba confirmación explícita, IDs, estado `config_published`/`published_pending_start`, publicación y hash runtime actual.
2. Persiste `service_action_requested` **antes** de invocar el backend.
3. Llama una sola vez a `backend.start(...)`; no invoca `systemctl` ni reintenta.
4. Si el controlador devuelve aceptación pendiente, persiste `service_action_accepted`.
5. Observa systemd y proceso de forma independiente y read-only; vuelve a leer el hash runtime.
6. Exige `MainPID`, `InvocationID`, timestamps posteriores a publicación, argv, ejecutable, UID/GID y hash runtime estables mediante `attest_start()`.
7. Persiste `service_observed_active` con evidencia `launch_correlated_file_unchanged`.

Si la llamada al controlador expira/falla de forma ambigua, si no se puede persistir la aceptación o si la observación post-start falla, registra `recovery_required`. No reintenta start automáticamente. Un estado `service_observed_active` **no** equivale a `configuration_attested` ni `completed`.

## Límite de evidencia

Xray no expone actualmente una prueba nativa del hash de configuración efectivamente parseado y conservado en memoria. El coordinador demuestra correlación temporal entre publicación, arranque, proceso e invariancia del archivo; conserva `configuration_loaded=false`. No se usa el hash del archivo, el resultado de `run -test` ni logs genéricos para afirmar bytes cargados.

Una alternativa técnica a estudiar por separado es una generación de configuración inmutable entregada al proceso mediante un descriptor sellado (p. ej. memfd) y un launcher de servicio explícito. Eso cambiaría el contrato de `ExecStart`, argv, unidad y observador actual; **no se implementó ni se recomienda activar sin diseño, pruebas de seguridad y revisión independiente**. Mantener `xray:xray` directo hasta que esa decisión sea aprobada.

## Exclusiones

- No se llamó al controlador `modules/xray_service.sh` real ni a systemd.
- No se ejecutó `start`, `restart` o `stop` en ningún host.
- No se conectó al `LiveRuntimeBackend` productivo, R-05, menú o CLI.
- No se modificaron `/etc/xray`, certificados, DNS, firewall, puertos ni VPS Pruebas.
- No se modificaron `main` ni `Xray-Normativa/`.

## Validación

Coordinador focal: **7/7 PASS**. La suite global se registra en continuidad tras ejecutar regresión completa.
