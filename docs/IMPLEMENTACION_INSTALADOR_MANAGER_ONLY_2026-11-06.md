# Implementación — instalación Manager-only por defecto

**Fecha:** 2026-11-06
**Estado:** IMPLEMENTADA Y VERIFICADA EN PREFIJOS AISLADOS
**Rama:** design/user-identity-association-v1

## Objetivo

Alinear el primer paso de instalación con el flujo operativo aprobado: desplegar Xray Core Manager primero y permitir instalar Xray-core después desde el propio menú.

## Cambios

### install.sh

- --install despliega únicamente Xray Core Manager.
- --with-xray requiere --install explícito y conserva la instalación integral anterior.
- El modo predeterminado no importa ni ejecuta modules/xray_admin.sh o modules/xray_service.sh.
- No descarga ni instala Xray-core, no crea usuario/grupo xray, no crea /etc/xray, no escribe geodata/binario y no crea/modifica xray.service.
- El preflight de rutas Xray (/var/lib/xray, /etc/xray, binario/geodata y unidad systemd) sólo se ejecuta con --with-xray.
- Se conservan los locks de ciclo de vida/integridad, validación de rutas y symlinks del Manager, permisos, registros JSON, preferencias e idempotencia.
- El estado inicial queda manager_installed=true, xray_installed=false, service_configured=false.
- El flujo explícito --install --with-xray conserva verificación SHA-256, respaldo/rollback, preparación de usuario/grupo/unidad y deja el servicio detenido/deshabilitado.

### Flujo posterior desde el menú

1. Ejecutar /opt/xray-manager/bin/xray-manager.
2. Entrar en Administración de Xray-core → Instalar Xray-core.
3. Después seleccionar Preparar servicio.
4. La instalación/preparación no inicia ni habilita el servicio; esas acciones siguen requiriendo sus operaciones y confirmaciones independientes.

### Documentación

Se actualizó README.md y docs/INSTALADOR_FASE_B_XRAY_SERVICE.md para describir la modalidad predeterminada y la opción integral explícita.

## Pruebas

- tests/install.sh: PASS; Manager-only, conservación de fixtures Xray preexistentes, no creación de unidad ni /etc/xray, estado false/false, idempotencia y modalidad integral explícita.
- Prueba adicional: una ruta /etc/xray simbólica no bloquea ni es seguida por Manager-only; la modalidad integral sí la rechaza antes de desplegar.
- Suite Python: 332/332 PASS.
- Suites Bash: 62/62 PASS.
- bash -n: PASS.
- ShellCheck -S error: PASS.
- python3 -m compileall -q scripts tests: PASS.
- install.sh --check: PASS, sin modificar el sistema.
- git diff --check: PASS.

## Límites

Todas las pruebas del cambio se ejecutaron con prefijos temporales. No se ejecutó instalación real en el host, no se instaló Xray-core, no se creó cuenta de servicio, no se modificó systemd, no se tocaron DNS/firewall/puertos/certificados ni se habilitó backend runtime live.

## Dictamen

El instalador predeterminado ahora deja el Manager listo para que Xray-core se instale desde su menú. La instalación integral anterior sigue disponible mediante autorización explícita de línea de comandos. Implementación verificada en fixtures; no implica prueba live ni despliegue end-to-end.
