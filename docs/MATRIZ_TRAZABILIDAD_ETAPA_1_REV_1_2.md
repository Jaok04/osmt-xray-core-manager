# Matriz de trazabilidad — Etapa 1 revisión 1.2

**Fuente normativa:** documentación aprobada del 31/10/2026, Etapa 1 revisión 1.2 (Markdown y YAML).  
**Fotografía de implementación:** copia local /opt/xray-manager, 01/11/2026.  
**Estado global:** PARCIAL — no certificada.

## 1. Criterios de estado

- **IMPLEMENTADO:** existe comportamiento en código y hay prueba automatizada pertinente.
- **PARCIAL:** existe código, pero falta cobertura de escenarios o validación operativa aislada.
- **PENDIENTE:** no se encontró implementación suficiente.
- Las pruebas con mocks/fixtures no equivalen a una operación real en VPS.
- Los menús de Etapas 2–6 son puntos de entrada definidos por Etapa 1; no certifican la implementación de esas etapas.

## 2. Menú principal y encabezado

| ID | Requisito aprobado | Implementación | Evidencia | Estado |
|---|---|---|---|---|
| M01 | Opciones [1]–[9] y [0] con etiquetas aprobadas | modules/main_menu.sh: menu_main | tests/stage1_menu.sh | IMPLEMENTADO |
| M02 | Encabezado con IP pública si disponible | lib/system.sh: system_public_ip, system_show_header | tests/stage1_header.sh simula fallo de curl y verifica el fallback No disponible | IMPLEMENTADO |
| M03 | Encabezado con versión Xray y estado de servicio | lib/system.sh: system_xray_version, system_xray_service_state, system_show_header | tests/stage1_menu.sh y pruebas de información | IMPLEMENTADO |
| M04 | Encabezado con autostart y perfil activo | lib/system.sh: system_xray_autostart, system_active_profile, system_show_header | tests/stage1_header.sh cubre perfil ausente/presente y servicio no configurado/habilitado; falta el estado explícito deshabilitado | PARCIAL |
| M05 | Fecha/hora local | lib/system.sh: system_show_header; preferencias APP_TIMEZONE/APP_DATE_FORMAT/APP_TIME_FORMAT | tests/stage1_settings.sh | IMPLEMENTADO |
| M06 | Datos no disponibles no deben impedir mostrar el menú | Funciones system_* con fallback y menú desacoplado de los datos | Falta prueba de fallo independiente para cada proveedor de datos | PARCIAL |
| M07 | Al volver al menú principal, actualizar el encabezado | system_show_header se ejecuta dentro del bucle de menu_main | tests/stage1_menu.sh verifica el renderizado inicial y los retornos desde las nueve entradas principales | IMPLEMENTADO |
| M08 | Salir requiere confirmación | menu_main, opción 0 | tests/stage1_menu.sh | IMPLEMENTADO |

## 3. Opción [8] — Configuración del sistema y administrador

| ID | Requisito aprobado | Implementación | Evidencia | Estado |
|---|---|---|---|---|
| A01 | Submenú [8] con las cinco entradas y [0] Volver | modules/main_menu.sh: menu_system_admin | tests/stage1_menu.sh | IMPLEMENTADO |
| A02 | Administración Xray con opciones [1]–[6] | modules/main_menu.sh: menu_xray_admin; modules/xray_admin.sh | tests/stage1_menu.sh, tests/xray_admin.sh | IMPLEMENTADO con validación operativa pendiente |
| A03 | Consultar versión instalada | menu_xray_admin y system_xray_version | tests/stage1_menu.sh | IMPLEMENTADO |
| A04 | Consultar última versión disponible | menu_xray_latest_release y xray_admin_latest_release | tests/stage1_menu.sh, tests/xray_admin.sh | IMPLEMENTADO |
| A05 | Dependencias específicas del administrador | modules/system_admin.sh | tests/stage1_dependencies.sh | IMPLEMENTADO con mocks |
| A06 | No duplicar gestores de paquetes; separar Etapa 1 de mantenimiento general Etapa 6 | manager_dependencies_update actualiza solo paquetes requeridos instalados; excluye apt y dpkg | tests/stage1_dependencies.sh | IMPLEMENTADO |
| A07 | Configuración del administrador y preferencias | config/preferences.sh; modules/admin_settings.sh | tests/stage1_settings.sh | IMPLEMENTADO con almacenamiento temporal |
| A08 | Información de instalación | menu_installation_information, menu_installation_paths, menu_installation_files, menu_installation_systemd | tests/stage1_menu.sh | IMPLEMENTADO |
| A09 | Errores de submenús no deben cerrar el administrador | Enrutamiento de menu_system_admin con recuperación de errores | tests/stage1_menu.sh inyecta retorno de error en las cinco opciones del administrador y comprueba que el menú continúa | IMPLEMENTADO |
| A10 | Todos los submenús usan [0] Volver y regresan al nivel anterior | Menús funcionales de conexiones, usuarios legacy/v2, Xray, dependencias y preferencias | tests/stage1_menu.sh verifica 11 rutas de retorno [0] y cinco fallos de acciones inyectados | IMPLEMENTADO |
| A11 | Operaciones destructivas requieren confirmación | Instalación/actualización/reinstalación/reparación, cambios de dependencias y desinstalación | tests/xray_admin.sh verifica cancelación desde el menú Xray sin iniciar descarga; tests/stage1_dependencies.sh verifica cancelación de instalación/actualización sin ejecutar apt; tests/uninstall.sh verifica cancelación de certificados y de la confirmación final sin borrar rutas | IMPLEMENTADO |

## 4. Desinstalación única — opción [8] > [5]

| ID | Requisito aprobado | Implementación | Evidencia | Estado |
|---|---|---|---|---|
| U01 | Único punto de entrada; no dentro de Administración Xray | menu_system_admin → uninstall_menu_action; menu_xray_admin no ofrece desinstalación | tests/stage1_menu.sh | IMPLEMENTADO |
| U02 | Alcances Xray-core, Manager o ambos | modules/uninstall.sh: uninstall_menu_action | tests/uninstall.sh; pruebas keep/all en los tres alcances y selected en Xray, Manager y ambos | IMPLEMENTADO en fixtures |
| U03 | Políticas conservar, eliminar todos o seleccionar categorías | uninstall_menu_action | tests/uninstall.sh; keep/all/selected probadas en los tres alcances | IMPLEMENTADO en fixtures |
| U04 | Categorías Xray config, perfiles/versiones, usuarios/asociaciones, conexiones, dominios, certificados/claves, respaldos, preferencias, logs/historiales | Mapeo explícito a rutas administradas y allowlist | tests/uninstall.sh; prueba individual de las nueve categorías; logs incluye history | IMPLEMENTADO en fixtures |
| U05 | Advertencia específica antes de eliminar certificados/claves privadas | uninstall_menu_action, certificate_deletion | tests/uninstall.sh verifica el aviso, cancelación y preservación de la clave fixture; también confirma el aviso en eliminación total | IMPLEMENTADO |
| U06 | Respaldo opcional antes de borrar; verificar archivo | uninstall_make_backup | tests/uninstall.sh | IMPLEMENTADO |
| U07 | Si falla creación/verificación del respaldo, cancelar borrado | uninstall_menu_action | tests/uninstall.sh | IMPLEMENTADO |
| U08 | Ofrecer exportación fuera del servidor y verificarla | uninstall_export_remote mediante SSH/SCP y SHA-256 remoto | tests/uninstall.sh con mocks SSH/SCP, hash correcto e incorrecto | IMPLEMENTADO con prueba simulada |
| U09 | Si se elige eliminar todo, eliminar respaldos existentes y respaldo temporal local | Política all en uninstall_menu_action | tests/uninstall.sh crea respaldo previo temporal y respaldo preexistente; verifica ambos respaldos desaparecen en Xray-core, Manager y ambos | IMPLEMENTADO en fixtures |
| U10 | Advertir exclusiones de respaldos Etapa 5: historial de perfiles, validaciones, informes de restauración y logs técnicos | Advertencia enumerada en el resumen previo | tests/uninstall.sh | IMPLEMENTADO |
| U11 | Vista previa de alcance, categorías, rutas, respaldo/exportación y advertencias | Resumen previo a la confirmación final | tests/uninstall.sh cubre parte del texto; falta verificar todos los campos | PARCIAL |
| U12 | Confirmación final explícita e irreversible | locks adquiridos antes del respaldo; ui_confirm final antes de borrar | tests/uninstall.sh | IMPLEMENTADO |
| U13 | Rechazar rutas fuera de allowlist y componentes simbólicos | uninstall_paths_are_allowed y uninstall_path_has_symlink_component | tests/uninstall.sh | IMPLEMENTADO |
| U14 | Evitar carreras con operaciones de usuarios/conexiones y administración Xray | Bloqueo compartido de ciclo de vida más locks de desinstalación, integridad y administración Xray; todos se adquieren antes del respaldo y se mantienen hasta finalizar/cancelar | tests/uninstall.sh prueba contención de lifecycle, integridad y Xray; tests/install.sh prueba contención lifecycle/integridad; tests/xray_admin.sh, tests/stage1_dependencies.sh y tests/stage1_settings.sh verifican coordinación con las operaciones correspondientes | IMPLEMENTADO para operaciones internas del Manager |
| U15 | No modificar unidades systemd, firewall o SSH; bloquear si Xray está activo | uninstall_service_guard y flujo de eliminación | Prueba con guard simulado; falta entorno desechable con servicio real controlado | PARCIAL |

## 5. Navegación y seguridad general

| ID | Requisito aprobado | Implementación | Evidencia | Estado |
|---|---|---|---|---|
| N01 | [0] Volver en todos los submenús | Menús principales y submenús funcionales de Etapa 1 con retorno explícito | tests/stage1_menu.sh cubre 11 rutas internas de [0] Volver, además de las nueve entradas principales | IMPLEMENTADO |
| N02 | Error no debe cerrar Manager | Llamadas recuperables desde menú principal | tests/stage1_menu.sh inyecta fallos en las nueve entradas principales y comprueba que el bucle continúa hasta la salida confirmada | IMPLEMENTADO para dispatch principal |
| N03 | Operaciones destructivas con confirmación | Xray, dependencias y desinstalación | tests/xray_admin.sh, tests/stage1_dependencies.sh y tests/uninstall.sh verifican cancelación sin ejecutar la acción destructiva | IMPLEMENTADO |
| N04 | Salir con confirmación | menu_main | tests/stage1_menu.sh | IMPLEMENTADO |
| N05 | Actualizar encabezado al volver al menú principal | Bucle de menu_main vuelve a invocar system_show_header | tests/stage1_menu.sh verifica 10 renderizados del encabezado: entrada inicial, retorno de las nueve opciones y ciclo de salida | IMPLEMENTADO para opciones principales |

## 6. Estado de cierre

**No declarar Etapa 1 completa todavía.**

Bloqueos para certificación:

1. Validar instalación Xray, dependencias, preferencias y desinstalación en un VPS desechable.
2. Resolver las discrepancias pendientes de encabezado (M04/M06) y cotejar el resto de la matriz contra la especificación aprobada.

Las pruebas actuales son fixtures/mocks. No se ejecutaron apt-get, instalación real de Xray, desinstalación real, cambios de systemd, firewall, SSH ni migraciones de datos reales.


## 7. Actualización de evidencia — 01/11/2026

Se incorporaron pruebas automatizadas adicionales:

- `tests/stage1_header.sh`: fallo de consulta IP, binario Xray ausente/presente, unidad systemd no configurada, perfil ausente y renderizado completo del encabezado.
- `tests/stage1_menu.sh`: refresco del encabezado al regresar desde las nueve entradas principales; matriz de 11 rutas internas `[0] Volver` y cinco fallos de acciones inyectados en conexiones, usuarios legacy/v2, preferencias, dependencias, administración Xray y gestión del servicio.
- `tests/uninstall.sh`: contención de locks, aviso/cancelación de certificados y cancelación de la confirmación final; prueba individual de nueve categorías y políticas keep/all/selected en los tres alcances, incluida la limpieza de respaldos.
- `lib/operation_lock.sh`: bloqueo exclusivo no bloqueante, permisos 600, liberación y rechazo de componentes simbólicos.
- `install.sh`: bloqueo de ciclo de vida e integridad antes de apt/despliegue; pruebas de contención sin modificar el prefijo.
- Dependencias, preferencias y administración Xray comparten el bloqueo de ciclo de vida. La desinstalación adquiere lifecycle, uninstall, integridad y Xray antes de crear el respaldo y los conserva hasta terminar o cancelar.

**Ejecución integral:** 20/20 scripts `tests/*.sh` aprobados; sintaxis Bash aprobada para bin, config, lib, modules, install y tests; ShellCheck `-S warning -x` aprobado; shfmt aprobado en los archivos de producción modificados y en las pruebas con estilo de indentación homogéneo; `tests/uninstall.sh` conserva su formato histórico mixto; `./install.sh --check` aprobado sin modificaciones.

La integración Xray validó las configuraciones generadas. Xray emitió avisos de deprecación para transportes WebSocket/gRPC y advertencias de REALITY al usar puertos distintos de 443; no fueron fallos de validación.

Estas evidencias no sustituyen la validación operativa en una VPS desechable. La Etapa 1 permanece **PARCIAL — no certificada**.

## Actualización — coordinación de concurrencia y confirmaciones (01/11/2026)

La matriz incorpora un bloqueo de ciclo de vida no bloqueante en `/run/lock/xray-manager-lifecycle.lock`, compartido por el instalador, administración Xray, instalación/actualización de dependencias y persistencia de preferencias. El instalador toma además el bloqueo de integridad de usuarios/conexiones.

La desinstalación adquiere, antes de crear el respaldo, los bloqueos de ciclo de vida, desinstalación, integridad y administración Xray. Los conserva durante el respaldo, exportación, confirmación final y borrado. Así se evita que operaciones internas cubiertas por esos locks alteren el contenido entre el respaldo y la eliminación.

Se añadieron pruebas de contención para instalador, dependencias, preferencias, administración Xray y desinstalación, además de cancelaciones explícitas en el menú Xray y en la confirmación irreversible final. `A11`, `U14` y `N03` pasan a IMPLEMENTADO dentro del alcance de operaciones internas del Manager.

La Etapa 1 permanece PARCIAL: continúan pendientes M04/M06 y las validaciones operativas reales de instalación, dependencias, preferencias y desinstalación en VPS desechable.