# Implementación H6-E3 — correlación de proceso y atestación R-05

**Fecha:** 2026-11-06
**Estado:** IMPLEMENTADA Y VERIFICADA CON DOBLES/ FIXTURES — PASS CON LIMITACIONES
**Rama:** design/user-identity-association-v1

## 1. Objetivo

Conectar la observación read-only H6-A, la identidad de proceso H6-E2 y la atestación H6-B con el punto de persistencia R-05. Se conserva el límite H6-C: backend mutador real y selector live no habilitados.

## 2. Correlación H6-A + H6-E2

Nuevo módulo scripts/xray_runtime_process_attestation.py:

- Toma un snapshot H6-A de xray.service y exige active/running, result success, ExecMainStatus 0, usuario/grupo xray, MainPID válido, InvocationID y ActiveEnterTimestamp.
- Resuelve UID/GID reales de la cuenta xray del sistema.
- Inspecciona exactamente el MainPID mediante H6-E2, exigiendo ejecutable /usr/local/bin/xray, argv administrado, UID/GID efectivos y SHA-256 del binario.
- Repite la observación H6-A después de inspeccionar el proceso.
- Exige que MainPID, InvocationID, ActiveEnterTimestamp y FragmentPath permanezcan estables.
- Devuelve evidencia correlacionada, pero mantiene configuration_loaded=false y configuration_evidence=not_attested.

Los observadores alternativos son puntos de inyección para pruebas. El módulo no realiza acciones mutadoras.

## 3. Integración R-05 y persistencia

Se modificó scripts/xray_runtime_orchestrator.py:

- El punto H6-C de persistencia exige process_identity en los snapshots after y confirmed.
- Valida que el PID del proceso sea el MainPID del snapshot systemd, que InvocationID y ActiveEnterTimestamp correspondan, que el ejecutable/argv sean los administrados y que UID/GID/hash/starttime sean válidos.
- Exige estabilidad de PID, starttime, hash de ejecutable, InvocationID y ActiveEnterTimestamp entre after y confirmed.
- Si falta evidencia o diverge, la operación no se completa y sigue el rollback/fail-closed R-05 existente.
- El proveedor de snapshots continúa restringido a dobles de prueba explícitos. No se añadió backend real ni selector en CLI/menú.

Se amplió scripts/xray_runtime_attestation.py a schema_version 2. La atestación persistida ahora incluye PID, starttime, ruta/hash del ejecutable, UID/GID efectivos y argv validado. El lector estricto valida también esos campos. La evidencia de configuración cargada sigue fuera del alcance y no se infiere.

No existían atestaciones persistentes de producción: el almacén H6-B estaba reservado pero no creado ni utilizado. Por ello no se requiere migración de datos reales; los registros schema v1 no son aceptados por el validador schema v2.

## 4. Pruebas

- Correlación H6-A/E2: tests/test_xray_runtime_process_attestation.py, 16/16 PASS.
- Persistencia H6-B schema v2: tests/test_xray_runtime_attestation.py, 15/15 PASS.
- Integración R-05/H6-C: tests/test_xray_runtime_h6c.py, 9/9 PASS.
- Regresión Python global: 332/332 PASS.
- py_compile, compileall, bash -n global, pruebas Bash de servicio/control/preparación, install.sh --check, ShellCheck -S error y git diff --check: PASS.

Las pruebas usan mocks, dobles y fixtures. No consultan systemd ni un proceso Xray real.

## 5. Límites

- H6-E3 no activa un backend mutador systemd; el backend predeterminado continúa siendo fixture.
- La función correlacionada usa H6-A y /proc reales por defecto si se invoca en producción, pero en esta etapa sólo se ejercitó con observadores sustituidos y fixtures.
- La persistencia H6-B schema v2 se ejercitó en almacenes temporales, no en /var/lib/xray-manager.
- No prueba qué configuración cargó Xray; sólo ata la identidad del proceso a la invocación systemd observada. loaded_generation_id/loaded_config_sha256 siguen sin inferirse.
- No se ejecutó systemctl real ni Xray real; no se modificaron unidades, runtime, /etc/xray, certificados, DNS, firewall, puertos, red o dependencias.
- No se modificaron main ni Xray-Normativa/. No hubo commit ni push.

H6-E3 queda IMPLEMENTADA Y VERIFICADA CON DOBLES/FIXTURES, PASS CON LIMITACIONES. La auditoría integral posterior del bloque H6-E (H6-E4) está documentada en docs/AUDITORIA_H6E_INTEGRAL_2026-11-06.md, con dictamen PASS CON LIMITACIONES. No autoriza operaciones live.
