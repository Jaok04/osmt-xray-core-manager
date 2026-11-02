# Fase C — Administración controlada del servicio Xray-core

Estado: implementación inicial integrada y validada con pruebas aisladas.  
Fecha: 2026-11-02

## Alcance

La Fase C incorpora el ciclo de vida de xray.service desde el menú principal del administrador:

- consulta de estado y diagnóstico;
- inicio;
- detención;
- reinicio;
- habilitación del inicio automático;
- deshabilitación del inicio automático;
- consulta de hasta 200 líneas recientes del journal (la interfaz solicita 50).

El menú principal, opción [5] Gestión del servicio Xray-core, abre el submenú dedicado. Cada operación mutante requiere confirmación explícita.

## Salvaguardas

1. Solo se controlan unidades que coincidan exactamente con la unidad administrada por el proyecto.
2. La unidad debe ser un archivo regular, no simbólico; en el sistema real debe pertenecer a root:root y tener modo 644.
3. Las operaciones requieren root y systemd.
4. start, restart y enable validan config.json antes de invocar la operación correspondiente.
5. La validación se ejecuta como usuario xray en el sistema real, no como root.
6. Las rutas del binario y de config.json deben coincidir con las fijadas actualmente en la unidad (/usr/local/bin/xray y /etc/xray/config.json). Si las preferencias del Manager apuntan a rutas personalizadas, el control se bloquea en lugar de validar un archivo distinto del que systemd ejecutaría.
7. Se comprueban el binario, la configuración, los componentes de ruta y los permisos esperados:
   - /etc/xray: root:xray, modo 750;
   - /etc/xray/config.json: root:xray, modo 640.
8. start y restart comprueban después que systemd confirme el estado active.
9. enable no inicia el servicio. disable no lo detiene.
10. stop y disable se pueden ejecutar aunque la configuración sea inválida, para permitir detener el servicio o evitar arranques futuros.
11. El módulo no crea ni modifica config.json, no cambia firewall, SSH ni red.
12. Las consultas de journal limitan el volumen entre 1 y 200 líneas.
13. El modo de prefijo alternativo solo admite operaciones de control cuando se activa explícitamente el doble indicador de pruebas; nunca alcanza el systemd del host.

## Archivos

- modules/xray_service.sh: funciones de control, validación, estado y journal.
- modules/main_menu.sh: submenú y confirmaciones.
- bin/xray-manager: carga del módulo.
- tests/xray_service_control.sh: pruebas aisladas con systemctl, journalctl y binario Xray simulados.
- tests/stage1_menu.sh: stub de la nueva entrada de menú.

## Validación

Las pruebas cubren:

- bloqueo de inicio, reinicio y habilitación cuando Xray rechaza la configuración;
- inicio y confirmación posterior de estado activo;
- fallo de restart;
- detención sin cambiar autostart;
- fallo cuando systemd devuelve éxito pero el servicio no queda activo;
- habilitación sin inicio y deshabilitación sin detener;
- diagnóstico de estado y validación de configuración;
- consulta de journal y límites de líneas;
- rechazo de unidad modificada;
- rechazo de configuración ausente;
- navegación del menú principal.

Las pruebas se ejecutan con prefijos temporales y dobles de prueba. No requieren ni ejecutan systemctl start, restart o enable sobre el servicio real.

## Pendiente de prueba en VPS desechable

La validación real de las operaciones de ciclo de vida queda pendiente hasta que exista una configuración Xray válida de prueba y se autorice expresamente activar el servicio. La implementación no debe probarse iniciando Xray sin configuración.

La instalación inicial sigue sin habilitar ni iniciar el servicio automáticamente.