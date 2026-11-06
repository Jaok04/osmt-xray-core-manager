# Auditoría H6-E1 — contrato de observación systemd

**Fecha:** 2026-11-06
**Dictamen:** PASS CON LIMITACIONES
**Rama:** design/user-identity-association-v1
**Base de trabajo:** commit H6-D publicado; cambios H6-E1 locales sin commit.

## 1. Evidencia

- Adaptador H6-A focal: **20/20 PASS**.
- Suite Python global: **289/289 PASS**.
- python3 -m compileall -q scripts tests: PASS.
- bash -n sobre scripts Bash, módulos, librerías, binario de menú y pruebas: PASS.
- ShellCheck -S error: PASS.
- tests/xray_service.sh: PASS.
- tests/xray_service_control.sh: PASS.
- tests/xray_admin_prepare_service.sh: PASS.
- install.sh --check: PASS; confirmó dependencias presentes y no modificó el sistema.
- git diff --check: PASS.

## 2. Alcance de seguridad

- _systemctl_show fue sustituido por mocks en las pruebas; no se invocó systemctl real.
- No se llamó start, stop, restart, reload, enable ni disable.
- No se consultó ni modificó el servicio Xray real.
- No se inspeccionó /proc ni se afirmó identidad de proceso; corresponde a H6-E2.
- No se modificaron archivos de /etc/systemd ni /etc/xray.
- No se instalaron ni actualizaron dependencias.
- No se modificaron certificados, claves, DNS, firewall, puertos, red, main ni Xray-Normativa/.
- No hubo commit ni push.

## 3. Limitaciones y riesgos pendientes

1. El formato de propiedades estructuradas ExecStart/ExecStartPre debe contrastarse con la versión de systemd del entorno objetivo durante una futura prueba autorizada; H6-E1 sólo valida el contrato simulado.
2. El observador aún no inspecciona ejecutable, argumentos ni credenciales del PID en /proc.
3. La correlación entre archivo actual y contenido realmente cargado no queda demostrada por este bloque.
4. No existe backend systemd mutador ni conexión live con R-05.

## 4. Resultado

H6-E1 queda IMPLEMENTADA, VERIFICADA Y AUDITADA en alcance read-only/mocks, PASS CON LIMITACIONES. H6-E2 puede continuar con el diseño e implementación aislada de identidad del proceso. Cualquier conexión mutadora o prueba live requiere autorización independiente.

## Estado posterior — auditoría integral H6-E (2026-11-06)

H6-E2 y H6-E3 se implementaron después de este corte; la auditoría integral H6-E4 quedó completada con dictamen PASS CON LIMITACIONES. Consultar docs/AUDITORIA_H6E_INTEGRAL_2026-11-06.md. Las limitaciones originales de H6-E1 siguen vigentes: systemctl real y formato efectivo de ExecStart/ExecStartPre aún no contrastados en el entorno objetivo; no se habilitan operaciones live.
