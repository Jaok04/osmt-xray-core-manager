# Auditoría H6-E3 — correlación de proceso y atestación R-05

**Fecha:** 2026-11-06
**Dictamen:** PASS CON LIMITACIONES
**Alcance:** integración aislada H6-A/H6-E2/H6-B/R-05 con mocks, dobles y fixtures.

## Pruebas

- H6-A/E2 process attestation: 16/16 PASS.
- H6-B schema v2: 15/15 PASS.
- H6-C/R-05: 9/9 PASS.
- Python global: 332/332 PASS.
- py_compile: PASS.
- compileall -q scripts tests: PASS.
- bash -n sobre módulos, librerías, binarios de menú, instalador y pruebas: PASS.
- tests/xray_service.sh: PASS.
- tests/xray_service_control.sh: PASS.
- tests/xray_admin_prepare_service.sh: PASS.
- install.sh --check: PASS; sin cambios del sistema.
- ShellCheck -S error: PASS.
- git diff --check: PASS.

## Controles verificados

- Rechazo de servicio inactivo, MainPID inválido y campos systemd inválidos.
- Rechazo de cambios de MainPID, InvocationID o ActiveEnterTimestamp durante inspección.
- Rechazo de ejecutable, argv o UID/GID divergentes.
- Rechazo de evidencia de proceso ausente o que pretenda afirmar configuración cargada.
- Persistencia exige process_identity y estabilidad after/confirmed.
- Divergencia o ausencia de evidencia provoca rollback/fail-closed.
- Schema v2 valida PID/starttime, SHA-256 de ejecutable, ruta, argv y UID/GID.
- Recovery lee la atestación persistida y conserva el fail-closed si falta.

## Límites

No se ejecutó systemctl real, no se inspeccionó /proc de producción ni un proceso Xray real. No se inició/detuvo/reinició servicio ni se escribió en /etc/xray o /var/lib/xray-manager. No se probó WAN, DNS, certificados, firewall o puertos. Backend live y selector CLI/menú continúan deshabilitados. No hubo cambios de dependencias, commit ni push.

## Dictamen

H6-E3: IMPLEMENTADA Y VERIFICADA CON DOBLES/FIXTURES, PASS CON LIMITACIONES. La auditoría integral H6-E4 se completó posteriormente; consultar docs/AUDITORIA_H6E_INTEGRAL_2026-11-06.md. No se autoriza inferir configuración cargada ni funcionamiento externo.
