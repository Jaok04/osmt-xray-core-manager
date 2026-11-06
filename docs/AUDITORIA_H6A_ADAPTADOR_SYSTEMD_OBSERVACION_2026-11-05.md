# Auditoría H6-A — adaptador systemd de observación

**Fecha:** 2026-11-05
**Dictamen:** PASS CON LIMITACIONES
**Rama:** design/user-identity-association-v1
**Base HEAD:** 2902b2ef602dfe97acf62428d6b7c35ce7c81d5d

## 1. Evidencia ejecutada

- 11/11 pruebas focales de `test_xray_runtime_systemd_adapter.py`: PASS.
- 59/59 pruebas focales R-05+B4: PASS.
- 257/257 pruebas Python globales mediante unittest discovery: PASS.
- `tests/smoke.sh`: PASS.
- `tests/xray_service.sh`: PASS.
- `bash -n` de los módulos de servicio y menú: PASS.
- Parseo AST de todos los scripts Python: PASS.
- ShellCheck `-S error` sobre módulos/tests Bash: PASS.
- `git diff --check`: PASS.

No se instaló pytest ni ninguna dependencia. El entorno no dispone de pytest; se utilizó unittest, que es el framework de estas suites.

## 2. Seguridad y límites

- Las pruebas del adaptador reemplazan `_systemctl_show` por mocks; no ejecutan systemctl real.
- No se invocó journalctl ni se inspeccionó el estado operativo de Xray.
- No se modificaron `/etc/systemd`, `/etc/xray`, usuarios/grupos, certificados, DNS, firewall, puertos o red.
- No se ejecutaron acciones start/restart/stop/enable/disable.
- No se accedió a claves maestras ni almacenes reales.
- No se instalaron/actualizaron dependencias.
- No se modificó `main` ni `Xray-Normativa/`.
- No se hizo commit ni push.

## 3. Limitaciones pendientes

1. El adaptador sólo observa; no implementa acciones mutadoras.
2. No se ha creado la atestación persistente que vincula generation_id/hash con InvocationID.
3. No se ha inyectado el backend en R-05.
4. No se ha conectado la aplicación de perfiles al menú.
5. No se ha ejecutado una prueba live ni una conexión externa.

## 4. Resultado

H6-A queda implementada y auditada en alcance read-only/mocks. No se declara H6 completa ni se acredita que el Manager pueda aplicar un perfil en systemd real. El siguiente bloque debe diseñar e implementar la atestación de generación e inyección del backend, manteniendo el adaptador fixture como default. La conexión live requiere autorización separada.
