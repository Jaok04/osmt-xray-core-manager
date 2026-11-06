# Auditoría H6-E4 — revisión integral H6-A, H6-B, H6-C, H6-D y H6-E1/E2/E3

**Fecha:** 2026-11-06
**Dictamen:** PASS CON LIMITACIONES — NO AUTORIZA OPERACIONES LIVE
**Rama de trabajo:** design/user-identity-association-v1

## 1. Alcance revisado

- H6-A: observación read-only de xray.service, validación de unidad/propiedades efectivas y hash del archivo runtime.
- H6-B: atestación persistente schema v2 que incorpora InvocationID/ActiveEnterTimestamp y evidencia del PID/starttime/ejecutable/UID/GID/argv.
- H6-C: integración R-05 con backend fixture predeterminado y dobles de prueba explícitos.
- H6-D: puente de menú confinado a fixtures.
- H6-E1: contrato efectivo systemd.
- H6-E2: identidad del proceso y detección de cambios durante inspección.
- H6-E3: correlación H6-A/H6-E2 y gate de persistencia R-05.

## 2. Resultados de pruebas

- H6-E2 identidad de proceso: 22/22 PASS.
- Correlación H6-A/E2: 16/16 PASS.
- H6-B schema v2: 15/15 PASS.
- H6-C/R-05: 9/9 PASS.
- Regresión Python global: 332/332 PASS.
- py_compile de módulos y pruebas H6: PASS.
- compileall -q scripts tests: PASS.
- bash -n sobre módulos, librerías, binarios de menú, instalador y pruebas: PASS.
- tests/xray_service.sh: PASS.
- tests/xray_service_control.sh: PASS.
- tests/xray_admin_prepare_service.sh: PASS.
- install.sh --check: PASS; no modificó el sistema.
- ShellCheck -S error: PASS.
- git diff --check: PASS.

## 3. Revisión de límites y seguridad

- Los módulos de identidad/correlación no contienen subprocess, shell, os.system, eval ni ejecución de comandos.
- H6-A usa systemctl show de forma read-only y con propiedades allowlist; no ejecuta start/stop/restart/enable/disable.
- R-05 mantiene service_adapter fixture como backend por defecto. Los backends externos siguen rechazados salvo dobles explícitamente marcados para pruebas.
- H6-C sólo persiste atestación mediante backend test-only. La integración valida evidencia de proceso after/confirmed y estabilidad de PID/starttime/hash/InvocationID/ActiveEnterTimestamp.
- Los locks R-05 de ciclo de vida/aplicación se mantienen durante la transición, observación, atestación y persistencia; el almacén de atestaciones tiene su lock independiente.
- Recovery exige atestación persistida válida y conserva fail-closed cuando falta o no coincide.
- Schema v2 no lee schema v1. No había almacén de atestaciones real creado/operado, por lo que no se detectó dato de producción que migrar.

## 4. Limitaciones no resueltas

- No se ejecutó systemctl real ni se contrastó el formato efectivo de ExecStart/ExecStartPre en un systemd del entorno objetivo.
- No se inspeccionó un proceso Xray real ni se consultó /proc de producción.
- El observador combinado usa H6-A y /proc reales por defecto, pero sólo se ejercitó con observadores sustituidos/fixtures.
- La integración R-05 de persistencia sigue restringida a dobles de prueba; no existe backend mutador live ni selector CLI/menú.
- La atestación demuestra identidad de proceso e invocación, pero no demuestra por sí sola qué configuración interna cargó Xray ni tráfico WAN.
- No se ha probado instalación limpia end-to-end, emisión TLS, DNS, firewall, puertos, conectividad ni cliente externo.
- No se modificaron unidad systemd real, Xray, /etc/xray, runtime, certificados, DNS, firewall, puertos, red o dependencias.
- No se modificaron main ni Xray-Normativa/.

## 5. Dictamen y siguiente control

H6-E1, H6-E2 y H6-E3 quedan implementadas y auditadas en alcance aislado; H6-E4 (auditoría integral) queda completada. El conjunto H6-E obtiene **PASS CON LIMITACIONES**. Este dictamen no habilita despliegue ni operaciones live.

Siguiente fase: H6-F, evaluación formal de preparación y definición del plan de prueba live. Antes de cualquier operación real se requiere autorización específica para la VPS de pruebas, acciones mutadoras concretas, instalación de Xray/systemd y cambios de red/certificados. La prueba de aceptación debe ejecutarse en una VPS limpia separada del entorno de desarrollo.
