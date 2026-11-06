# H6-E1 — ampliación del contrato de observación systemd

**Fecha:** 2026-11-06
**Estado:** IMPLEMENTADO EN CÓDIGO — PRUEBAS AISLADAS PASS
**Alcance:** adaptador H6-A read-only; pruebas con mocks y archivos temporales.

## 1. Objetivo

Corregir y ampliar el contrato de observación antes de diseñar la inspección directa del proceso (H6-E2). El adaptador no realiza operaciones mutadoras y continúa separado del backend fixture R-05.

## 2. Cambios

Se amplió scripts/xray_runtime_systemd_adapter.py para consultar además:

- NeedDaemonReload: exige no.
- DropInPaths: exige ausencia de drop-ins.
- Type: exige simple, como la unidad administrada actual.
- ExecStartPre: valida ejecutable y argv exactos de la prueba nativa.
- ExecStart: valida ejecutable y argv exactos del proceso Xray.

La lectura de propiedades conserva la allowlist, argumentos separados, entorno mínimo, timeout y subprocess.run sin shell. El adaptador no acepta una definición pendiente de daemon-reload, overrides adicionales ni comandos efectivos divergentes.

Se corrigió la comprobación de configuración runtime: ahora exige propietario root, grupo xray y modo 0640, coherente con modules/xray_service.sh. El GID esperado se obtiene del grupo del sistema xray; no se expone un parámetro de producción para omitir esa comprobación. También se compara el inode abierto con el observado mediante lstat para detectar sustitución entre ambas operaciones.

El campo runtime_config_sha256 sigue describiendo únicamente el archivo observado. loaded_generation_id y loaded_config_sha256 permanecen nulos; generation_evidence sigue siendo not_attested.

## 3. Pruebas

La suite focal tests/test_xray_runtime_systemd_adapter.py pasó **20/20**. Incluye validación de propiedades efectivas, rechazo de daemon-reload pendiente, drop-ins, tipo de servicio distinto, ExecStart/ExecStartPre divergentes, argumentos adicionales y grupo incorrecto del archivo.

Todas las consultas systemd de las pruebas usan mocks. Los archivos de unidad y configuración son temporales. No se ejecutó systemctl real.

## 4. Límites

H6-E1 no inspecciona todavía /proc, identidad real del proceso, PID reuse ni hash del ejecutable; eso corresponde a H6-E2. No conecta H6-A al orquestador R-05 ni crea un backend mutador. No habilita selector live en menú/CLI. No demuestra qué bytes de configuración fueron cargados por Xray.

No se modificaron modules/xray_service.sh, la unidad systemd real, /etc/xray, runtime, certificados, DNS, firewall, puertos, red ni dependencias. No se modificó Xray-Normativa/ ni main. No hubo commit ni push.

## Estado posterior — auditoría integral H6-E (2026-11-06)

H6-E2 y H6-E3 se implementaron después de este corte; la auditoría integral H6-E4 quedó completada con dictamen PASS CON LIMITACIONES. Consultar docs/IMPLEMENTACION_H6E2_IDENTIDAD_PROCESO_2026-11-06.md, docs/IMPLEMENTACION_H6E3_CORRELACION_PROCESO_ATESTACION_2026-11-06.md y docs/AUDITORIA_H6E_INTEGRAL_2026-11-06.md. H6-E no habilita backend mutador ni operaciones live.
