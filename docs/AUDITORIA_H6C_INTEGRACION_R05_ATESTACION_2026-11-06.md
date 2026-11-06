# Auditoría H6-C — integración R-05/H6-B con backend inyectable

**Fecha:** 2026-11-06
**Dictamen:** PASS CON LIMITACIONES — sólo mocks/fixtures.
**Rama:** `design/user-identity-association-v1`

## Resultados

- [x] Backend fixture R-05 se mantiene como default.
- [x] ContextVar limita el backend inyectado a la llamada y se restablece en finally.
- [x] Backend externo sin marca de doble de prueba es rechazado antes de ejecución.
- [x] Contrato del backend: status/start/restart/restore/ServiceAdapterError.
- [x] Captura sintética before/after/confirmed dentro del ciclo R-05.
- [x] H6-B persiste atestación con operation_id, generation_id y SHA-256 del journal.
- [x] Divergencia de InvocationID provoca fallo de verificación y rollback fixture.
- [x] Start sólo produce atestación después de confirmación explícita.
- [x] Recovery reconcilia una atestación persistida tras interrupción.
- [x] Recovery sin atestación esperada queda RECOVERY_REQUIRED.
- [x] El almacén H6-B permanece separado del registro activo B4.
- [x] No se añadió selector de backend real a CLI ni se implementó mutación systemd.

## Evidencia de pruebas

- H6-C: 7/7 PASS.
- H6-B: 12/12 PASS.
- Python global: 276/276 PASS.
- compileall: PASS.
- bash -n global: PASS.
- ShellCheck -S error: PASS.
- install.sh --check: PASS.
- tests/xray_service.sh: PASS.
- tests/xray_service_control.sh: PASS.
- tests/xray_admin_prepare_service.sh: PASS.
- git diff --check: PASS.
- Escaneo estático H6-C/H6-B: sin llamadas systemctl, subprocess, os.system, Popen o eval.

## Límites y riesgos residuales

1. Todos los snapshots H6-C son sintéticos; no se utilizó H6-A contra systemd real.
2. La marca RUNTIME_BACKEND_TEST_ONLY es una barrera de diseño para impedir selección accidental; no es un límite de seguridad contra código Python arbitrario.
3. No existe todavía backend mutador systemd ni un flujo live habilitado.
4. No se probó conexión WAN ni cliente externo.
5. No se instalaron ni actualizaron dependencias.
6. No se modificaron /etc/xray, /etc/systemd, certificados, DNS, firewall, puertos, red, main ni Xray-Normativa/.

## Dictamen

H6-C se considera IMPLEMENTADA, VERIFICADA Y AUDITADA en el alcance de pruebas. La integración R-05/H6-B opera con backend fixture y dobles de prueba; la falta de evidencia durante recovery es fail-closed. No habilita operación real, no cierra Etapa 5/6 y no permite afirmar que Xray esté ejecutando la generación publicada. No se hizo commit ni push.
