# Fase C — Administración controlada del servicio Xray-core

Estado: implementación integrada; pruebas automatizadas y validación operativa real parcial aprobadas.  
Fecha de actualización: 2026-11-01

## Alcance

La Fase C incorpora el ciclo de vida de `xray.service` desde el menú principal del administrador:

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
2. La unidad debe ser un archivo regular, no simbólico; en el sistema real debe pertenecer a `root:root` y tener modo `644`.
3. Las operaciones requieren root y systemd.
4. `start`, `restart` y `enable` validan `config.json` antes de invocar la operación correspondiente.
5. La validación se ejecuta como usuario `xray` en el sistema real, no como root.
6. Las rutas del binario y de `config.json` deben coincidir con las fijadas actualmente en la unidad (`/usr/local/bin/xray` y `/etc/xray/config.json`). Si las preferencias del Manager apuntan a rutas personalizadas, el control se bloquea en lugar de validar un archivo distinto del que systemd ejecutaría.
7. Se comprueban el binario, la configuración, los componentes de ruta y los permisos esperados:
   - `/etc/xray`: `root:xray`, modo `750`;
   - `/etc/xray/config.json`: `root:xray`, modo `640`.
8. `start` y `restart` comprueban después que systemd confirme el estado `active`.
9. `enable` no inicia el servicio. `disable` no lo detiene.
10. `stop` y `disable` se pueden ejecutar aunque la configuración sea inválida, para permitir detener el servicio o evitar arranques futuros.
11. El módulo no crea ni modifica `config.json`, no cambia firewall, SSH ni red.
12. Las consultas de journal limitan el volumen entre 1 y 200 líneas.
13. El modo de prefijo alternativo solo admite operaciones de control cuando se activa explícitamente el doble indicador de pruebas; nunca alcanza el systemd del host.

## Archivos

- `modules/xray_service.sh`: funciones de control, validación, estado y journal.
- `modules/main_menu.sh`: submenú y confirmaciones.
- `bin/xray-manager`: carga del módulo.
- `tests/xray_service_control.sh`: pruebas aisladas con `systemctl`, `journalctl` y binario Xray simulados.
- `tests/stage1_menu.sh`: stub de la nueva entrada de menú.

## Validación automatizada

La suite de control del servicio comprueba, entre otros escenarios:

- bloqueo de inicio, reinicio y habilitación cuando Xray rechaza la configuración;
- inicio y confirmación posterior de estado activo;
- fallo de reinicio;
- detención sin cambiar el inicio automático;
- fallo cuando systemd devuelve éxito pero el servicio no queda activo;
- habilitación sin inicio y deshabilitación sin detener;
- diagnóstico de estado y validación de configuración;
- consulta del journal y límites de líneas;
- rechazo de unidad modificada;
- rechazo de configuración ausente;
- navegación desde el menú principal.

Las pruebas usan prefijos temporales y dobles de prueba. No ejecutan operaciones de control sobre el systemd real del host.

En la validación de integración del proyecto, la suite completa registró **20/20 pruebas aprobadas y 0 fallos**, incluyendo `xray_service_control`. También pasaron `bash -n`, ShellCheck con nivel `warning`, formato `shfmt` en los archivos modificados y `./install.sh --check`.

## Validación operativa real en VPS desechable

Se realizó una prueba controlada en la VPS desechable del proyecto, sin modificar la VPS de desarrollo.

### Entorno de prueba

- Xray-core: `26.10.31`.
- Unidad: `xray.service`, inicialmente cargada, inactiva y deshabilitada.
- Cuenta de servicio: `xray:xray`.
- Configuración temporal: inbound SOCKS sin autenticación, enlazado exclusivamente a `127.0.0.1:39091`, y outbound `freedom`.
- La configuración no contenía credenciales ni servidores externos y no abrió un puerto público.
- Propiedad y permisos de la configuración: `root:xray`, modo `640`.
- La validación ejecutada como usuario `xray` devolvió `Configuration OK.`.

El módulo `modules/xray_service.sh` se transfirió temporalmente a `/tmp` en la VPS desechable y se cargó para ejecutar sus funciones reales. No se instaló ni se modificó el Manager de esa VPS.

### Resultados

| Operación | Resultado | Verificación |
|---|---|---|
| `start` | PASS | Servicio `active/running`, proceso ejecutándose como `xray:xray` y listener en `127.0.0.1:39091`. |
| `restart` | PASS | Servicio volvió a `active/running`, cambió el PID y el listener siguió disponible en loopback. |
| `stop` | PASS | Servicio `inactive/dead` y listener eliminado. |

El journal registró los eventos esperados de inicio, reinicio y detención, sin errores. El inicio automático permaneció `disabled` durante toda la prueba.

### Límites de esta validación

- **No se probaron operativamente `enable` ni `disable`** en systemd real; se mantuvo el inicio automático deshabilitado deliberadamente.
- No se probó tráfico de clientes a través del inbound SOCKS. La comprobación de red se limitó a verificar la presencia y retirada del listener local.
- La prueba acredita el funcionamiento operativo de `start`, `restart` y `stop` con una configuración temporal válida; no equivale a una prueba funcional de una conexión VLESS real.
- Una primera comprobación inmediata del listener tuvo una condición de carrera de disponibilidad. La repetición incorporó espera de disponibilidad y el ciclo completo pasó. El resultado PASS corresponde a esa repetición robusta.

### Limpieza y estado final

Después de la prueba se eliminaron la configuración temporal `/etc/xray/config.json` y el módulo transferido `/tmp/xray_service_phase_c.sh`.

Estado final comprobado en la VPS desechable:

- `xray.service`: `loaded`, `inactive/dead`, `disabled`, resultado `success`;
- configuración temporal: ausente;
- módulo temporal: ausente;
- listener `127.0.0.1:39091`: ausente;
- proceso Xray: ausente;
- `/etc/xray`: propietario `root:xray`, modo `750`.

La VPS de desarrollo no fue modificada durante la prueba operativa.

## Estado y próximos pasos

La Fase C cuenta con pruebas automatizadas y validación operativa real de `start`, `restart` y `stop`. Las operaciones `enable` y `disable` están cubiertas por pruebas automatizadas aisladas, pero siguen pendientes de validación operativa real.

La instalación inicial sigue sin habilitar ni iniciar el servicio automáticamente. La Fase C no certifica por sí sola la Fase 1 del proyecto. La coordinación interna de concurrencia y la cobertura de confirmaciones destructivas se han implementado y probado; siguen pendientes M04/M06 del encabezado y la validación operativa real de instalación, dependencias, preferencias y desinstalación en VPS desechable.