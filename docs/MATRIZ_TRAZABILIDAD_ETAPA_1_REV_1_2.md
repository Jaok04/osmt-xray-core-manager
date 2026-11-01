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
| M02 | Encabezado con IP pública si disponible | lib/system.sh: system_public_ip, system_show_header | Prueba indirecta de menú; falta mock específico de IP ausente | PARCIAL |
| M03 | Encabezado con versión Xray y estado de servicio | lib/system.sh: system_xray_version, system_xray_service_state, system_show_header | tests/stage1_menu.sh y pruebas de información | IMPLEMENTADO |
| M04 | Encabezado con autostart y perfil activo | lib/system.sh: system_xray_autostart, system_active_profile, system_show_header | Prueba parcial; falta cubrir todas las condiciones ausentes | PARCIAL |
| M05 | Fecha/hora local | lib/system.sh: system_show_header; preferencias APP_TIMEZONE/APP_DATE_FORMAT/APP_TIME_FORMAT | tests/stage1_settings.sh | IMPLEMENTADO |
| M06 | Datos no disponibles no deben impedir mostrar el menú | Funciones system_* con fallback y menú desacoplado de los datos | Falta prueba de fallo independiente para cada proveedor de datos | PARCIAL |
| M07 | Al volver al menú principal, actualizar el encabezado | system_show_header se ejecuta dentro del bucle de menu_main | Código revisado; falta prueba que compruebe una segunda lectura tras volver de cada submenú | PARCIAL |
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
| A09 | Errores de submenús no deben cerrar el administrador | Enrutamiento de menu_system_admin y menu_main con recuperación de errores | tests/stage1_menu.sh | PARCIAL: faltan fallos inyectados en todos los submenús |
| A10 | Todos los submenús usan [0] Volver y regresan al nivel anterior | Menús de Xray, dependencias, preferencias e información | tests/stage1_menu.sh | PARCIAL: falta matriz automatizada de todos los caminos |
| A11 | Operaciones destructivas requieren confirmación | Instalación/reinstalación/reparación, cambios de dependencias y desinstalación | tests/stage1_menu.sh, tests/stage1_dependencies.sh, tests/xray_admin.sh, tests/uninstall.sh | PARCIAL: cobertura de confirmaciones por operación aún no exhaustiva |

## 4. Desinstalación única — opción [8] > [5]

| ID | Requisito aprobado | Implementación | Evidencia | Estado |
|---|---|---|---|---|
| U01 | Único punto de entrada; no dentro de Administración Xray | menu_system_admin → uninstall_menu_action; menu_xray_admin no ofrece desinstalación | tests/stage1_menu.sh | IMPLEMENTADO |
| U02 | Alcances Xray-core, Manager o ambos | modules/uninstall.sh: uninstall_menu_action | tests/uninstall.sh; falta cubrir los tres alcances en toda combinación de políticas | PARCIAL |
| U03 | Políticas conservar, eliminar todos o seleccionar categorías | uninstall_menu_action | tests/uninstall.sh; faltan pruebas exhaustivas por política/alcance | PARCIAL |
| U04 | Categorías Xray config, perfiles/versiones, usuarios/asociaciones, conexiones, dominios, certificados/claves, respaldos, preferencias, logs/historiales | Mapeo explícito a rutas administradas y allowlist | tests/uninstall.sh; falta una prueba por cada categoría | PARCIAL |
| U05 | Advertencia específica antes de eliminar certificados/claves privadas | uninstall_menu_action, certificate_deletion | Falta prueba automatizada que compruebe el aviso y la cancelación | PARCIAL |
| U06 | Respaldo opcional antes de borrar; verificar archivo | uninstall_make_backup | tests/uninstall.sh | IMPLEMENTADO |
| U07 | Si falla creación/verificación del respaldo, cancelar borrado | uninstall_menu_action | tests/uninstall.sh | IMPLEMENTADO |
| U08 | Ofrecer exportación fuera del servidor y verificarla | uninstall_export_remote mediante SSH/SCP y SHA-256 remoto | tests/uninstall.sh con mocks SSH/SCP, hash correcto e incorrecto | IMPLEMENTADO con prueba simulada |
| U09 | Si se elige eliminar todo, eliminar respaldos existentes y respaldo temporal local | Política all en uninstall_menu_action | Código revisado; falta prueba explícita de limpieza total en cada alcance | PARCIAL |
| U10 | Advertir exclusiones de respaldos Etapa 5: historial de perfiles, validaciones, informes de restauración y logs técnicos | Advertencia enumerada en el resumen previo | tests/uninstall.sh | IMPLEMENTADO |
| U11 | Vista previa de alcance, categorías, rutas, respaldo/exportación y advertencias | Resumen previo a la confirmación final | tests/uninstall.sh cubre parte del texto; falta verificar todos los campos | PARCIAL |
| U12 | Confirmación final explícita e irreversible | ui_confirm antes de adquirir locks y borrar | tests/uninstall.sh | IMPLEMENTADO |
| U13 | Rechazar rutas fuera de allowlist y componentes simbólicos | uninstall_paths_are_allowed y uninstall_path_has_symlink_component | tests/uninstall.sh | IMPLEMENTADO |
| U14 | Evitar carreras con operaciones de usuarios/conexiones y administración Xray | Locks no bloqueantes de uninstall, integridad y Xray; runtime lock no se elimina | tests/uninstall.sh prueba contención de lock de integridad | PARCIAL: falta prueba de contención del lock Xray y revisión de procesos Manager concurrentes |
| U15 | No modificar unidades systemd, firewall o SSH; bloquear si Xray está activo | uninstall_service_guard y flujo de eliminación | Prueba con guard simulado; falta entorno desechable con servicio real controlado | PARCIAL |

## 5. Navegación y seguridad general

| ID | Requisito aprobado | Implementación | Evidencia | Estado |
|---|---|---|---|---|
| N01 | [0] Volver en todos los submenús | Menús con retorno explícito | tests/stage1_menu.sh | PARCIAL: falta cobertura exhaustiva |
| N02 | Error no debe cerrar Manager | Llamadas recuperables desde menú principal | tests/stage1_menu.sh | PARCIAL |
| N03 | Operaciones destructivas con confirmación | Xray, dependencias y desinstalación | Pruebas por módulo | PARCIAL |
| N04 | Salir con confirmación | menu_main | tests/stage1_menu.sh | IMPLEMENTADO |
| N05 | Actualizar encabezado al volver al menú principal | Bucle de menu_main vuelve a invocar system_show_header | Revisión de código; falta prueba de regresión específica | PARCIAL |

## 6. Estado de cierre

**No declarar Etapa 1 completa todavía.**

Bloqueos para certificación:

1. Completar las pruebas de encabezado con fuentes de datos ausentes y verificar actualización tras regresar de submenús.
2. Automatizar el recorrido [0] Volver y recuperación de error para cada submenú.
3. Añadir pruebas de advertencia/cancelación de certificados y de cada categoría de desinstalación.
4. Probar explícitamente las combinaciones de alcance/política, borrado total de respaldos y lock de administración Xray.
5. Validar instalación Xray, dependencias, preferencias y desinstalación en un VPS desechable.
6. Revisar cualquier discrepancia encontrada en la matriz contra la especificación aprobada y actualizar la documentación de implementación.

Las pruebas actuales son fixtures/mocks. No se ejecutaron apt-get, instalación real de Xray, desinstalación real, cambios de systemd, firewall, SSH ni migraciones de datos reales.
