# Matriz de trazabilidad — Etapa 1 revisión 1.2

**Fuente normativa:** documentación aprobada del 31/10/2026, Etapa 1 revisión 1.2 (Markdown y YAML).  
**Fotografía de implementación:** copia local /opt/xray-manager, 02/11/2026.  
**Estado global:** IMPLEMENTADA — lista para aceptación final; no certificada formalmente.

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
| M04 | Encabezado con autostart y perfil activo | lib/system.sh: system_xray_autostart, system_active_profile, system_show_header | tests/stage1_header.sh verifica unidad no configurada, autostart habilitado/deshabilitado y perfil ausente/presente; clasifica masked y estados static/indirect/generated/transient | IMPLEMENTADO |
| M05 | Fecha/hora local | lib/system.sh: system_show_header; preferencias APP_TIMEZONE/APP_DATE_FORMAT/APP_TIME_FORMAT | tests/stage1_settings.sh | IMPLEMENTADO |
| M06 | Datos no disponibles no deben impedir mostrar el menú | system_show_header aísla fallos y salidas vacías de IP, versión, estado, autostart, perfil y fecha/hora con fallback No disponible | tests/stage1_header.sh inyecta fallo independiente en cada proveedor y falla todos simultáneamente al entrar a menu_main; verifica que [1] y [0] siguen visibles | IMPLEMENTADO |
| M07 | Al volver al menú principal, actualizar el encabezado | system_show_header se ejecuta dentro del bucle de menu_main | tests/stage1_menu.sh verifica el renderizado inicial y los retornos desde las nueve entradas principales | IMPLEMENTADO |
| M08 | Salir requiere confirmación | menu_main, opción 0 | tests/stage1_menu.sh | IMPLEMENTADO |

## 3. Opción [8] — Configuración del sistema y administrador

| ID | Requisito aprobado | Implementación | Evidencia | Estado |
|---|---|---|---|---|
| A01 | Submenú [8] con las cinco entradas y [0] Volver | modules/main_menu.sh: menu_system_admin | tests/stage1_menu.sh | IMPLEMENTADO |
| A02 | Administración Xray con opciones [1]–[6] | modules/main_menu.sh: menu_xray_admin; modules/xray_admin.sh | tests/stage1_menu.sh, tests/xray_admin.sh y descarga/verificación/instalación real de Xray 26.10.31 en prefijo aislado con SHA-256 oficial | IMPLEMENTADO |
| A03 | Consultar versión instalada | menu_xray_admin y system_xray_version | tests/stage1_menu.sh | IMPLEMENTADO |
| A04 | Consultar última versión disponible | menu_xray_latest_release y xray_admin_latest_release | tests/stage1_menu.sh, tests/xray_admin.sh | IMPLEMENTADO |
| A05 | Dependencias específicas del administrador | modules/system_admin.sh | tests/stage1_dependencies.sh; VPS desechable reportó todas disponibles y `apt-get -s install` sin cambios | IMPLEMENTADO |
| A06 | No duplicar gestores de paquetes; separar Etapa 1 de mantenimiento general Etapa 6 | manager_dependencies_update actualiza solo paquetes requeridos instalados; excluye apt y dpkg | tests/stage1_dependencies.sh | IMPLEMENTADO |
| A07 | Configuración del administrador y preferencias | config/preferences.sh; modules/admin_settings.sh | tests/stage1_settings.sh; VPS desechable: guardado, recarga desde disco, permisos root:root 600 y restauración byte por byte | IMPLEMENTADO |
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
| U08 | Ofrecer exportación fuera del servidor y verificarla | uninstall_export_remote mediante SSH/SCP y SHA-256 remoto | tests/uninstall.sh con mocks SSH/SCP, hash correcto e incorrecto; no se probó un destino remoto real por no disponer de host/credenciales de respaldo | IMPLEMENTADO con integración externa simulada |
| U09 | Si se elige eliminar todo, eliminar respaldos existentes y respaldo temporal local | Política all en uninstall_menu_action | tests/uninstall.sh crea respaldo previo temporal y respaldo preexistente; verifica ambos respaldos desaparecen en Xray-core, Manager y ambos | IMPLEMENTADO en fixtures |
| U10 | Advertir exclusiones de respaldos Etapa 5: historial de perfiles, validaciones, informes de restauración y logs técnicos | Advertencia enumerada en el resumen previo | tests/uninstall.sh | IMPLEMENTADO |
| U11 | Vista previa de alcance, categorías, rutas, respaldo/exportación y advertencias | Resumen previo a la confirmación final | tests/uninstall.sh verifica alcance, política, categorías seleccionadas, todas las rutas, respaldo temporal, exportación, exclusiones Etapa 5, advertencia systemd y las tres confirmaciones previas | IMPLEMENTADO |
| U12 | Confirmación final explícita e irreversible | locks adquiridos antes del respaldo; ui_confirm final antes de borrar | tests/uninstall.sh | IMPLEMENTADO |
| U13 | Rechazar rutas fuera de allowlist y componentes simbólicos | uninstall_paths_are_allowed y uninstall_path_has_symlink_component | tests/uninstall.sh | IMPLEMENTADO |
| U14 | Evitar carreras con operaciones de usuarios/conexiones y administración Xray | Bloqueo compartido de ciclo de vida para instalador, acciones de servicio, administración Xray, dependencias y preferencias, más locks de desinstalación e integridad; la desinstalación adquiere lifecycle/uninstall/integridad/Xray antes del respaldo y los mantiene hasta finalizar/cancelar | tests/uninstall.sh prueba contención de lifecycle, integridad y Xray; tests/install.sh prueba lifecycle/integridad; tests/xray_service_control.sh prueba que start no actúa con lifecycle ocupado; tests/xray_admin.sh, tests/stage1_dependencies.sh y tests/stage1_settings.sh verifican las operaciones correspondientes | IMPLEMENTADO para operaciones internas del Manager |
| U15 (control adicional) | No modificar unidades systemd, firewall o SSH; bloquear si Xray está activo | `uninstall_service_guard`: bloquea cualquier alcance si Xray está activo; permite Manager-only si está detenido; bloquea Xray/both si la unidad existe para no dejar una unidad huérfana. Nunca modifica systemd/firewall/SSH | `tests/uninstall.sh` cubre unidad presente/inactiva, servicio activo y alcances; VPS desechable con unidad real inactive/disabled: Manager-only eliminó solo fixture y preservó unidad/core; Xray-only fue bloqueado | IMPLEMENTADO |

## 5. Navegación y seguridad general

| ID | Requisito aprobado | Implementación | Evidencia | Estado |
|---|---|---|---|---|
| N01 | [0] Volver en todos los submenús | Menús principales y submenús funcionales de Etapa 1 con retorno explícito | tests/stage1_menu.sh cubre 11 rutas internas de [0] Volver, además de las nueve entradas principales | IMPLEMENTADO |
| N02 | Error no debe cerrar Manager | Llamadas recuperables desde menú principal | tests/stage1_menu.sh inyecta fallos en las nueve entradas principales y comprueba que el bucle continúa hasta la salida confirmada | IMPLEMENTADO para dispatch principal |
| N03 | Operaciones destructivas con confirmación | Xray, dependencias y desinstalación | tests/xray_admin.sh, tests/stage1_dependencies.sh y tests/uninstall.sh verifican cancelación sin ejecutar la acción destructiva | IMPLEMENTADO |
| N04 | Salir con confirmación | menu_main | tests/stage1_menu.sh | IMPLEMENTADO |
| N05 | Actualizar encabezado al volver al menú principal | Bucle de menu_main vuelve a invocar system_show_header | tests/stage1_menu.sh verifica 10 renderizados del encabezado: entrada inicial, retorno de las nueve opciones y ciclo de salida | IMPLEMENTADO para opciones principales |

## 6. Estado de cierre

**Implementación de Etapa 1 completada; lista para aceptación final.** Todas las filas normativas M01–M08, A01–A11, U01–U14 y N01–N05 están en estado IMPLEMENTADO. U15 se mantiene como control adicional de seguridad registrado en la matriz.

### Cotejo final contra la especificación aprobada

Se parseó el YAML normativo y se cotejaron sus etiquetas y opciones con el código, además de los alcances, políticas, categorías, advertencias, orden del respaldo/confirmación/borrado, SHA-256 de exportación, fallbacks del encabezado, límite de paquetes y confirmación de salida. Resultado: **47/47 comprobaciones PASS**.

La suite de comportamiento posterior a los últimos cambios pasó **20/20 scripts**; `bash -n`, ShellCheck, shfmt de archivos con formato homogéneo e `./install.sh --check` también pasaron.

### Límites de validación conocidos

- U08: exportación SSH/SCP y verificación SHA-256 están cubiertas con mocks; no se usó un servidor remoto real porque no se dispone de destino/credenciales de respaldo.
- Desinstalación: se probó el borrado real de árboles fixture y el guard contra la unidad systemd real. No se desinstalaron Xray ni el Manager instalados en el host de pruebas.
- La unidad del host de pruebas quedó `inactive/disabled`; no se hizo un reinicio de la VPS para probar persistencia tras reboot.

No hay requisitos normativos de implementación marcados PARCIAL o PENDIENTE en la matriz. La Etapa 1 queda **lista para aceptación formal**, pero no se declara certificada hasta la revisión/aprobación del usuario.


## 7. Actualización de evidencia — 01/11/2026

Se incorporaron pruebas automatizadas adicionales:

- `tests/stage1_header.sh`: fallo de consulta IP, binario Xray ausente/presente, unidad systemd no configurada, autostart habilitado/deshabilitado, perfil ausente/presente, fallo independiente de seis proveedores y fallo simultáneo de todos al entrar al menú principal.
- `tests/stage1_menu.sh`: refresco del encabezado al regresar desde las nueve entradas principales; matriz de 11 rutas internas `[0] Volver` y cinco fallos de acciones inyectados en conexiones, usuarios legacy/v2, preferencias, dependencias, administración Xray y gestión del servicio.
- `tests/uninstall.sh`: contención de locks, aviso/cancelación de certificados y cancelación de la confirmación final; prueba individual de nueve categorías y políticas keep/all/selected en los tres alcances, incluida la limpieza de respaldos.
- `lib/operation_lock.sh`: bloqueo exclusivo no bloqueante, permisos 600, liberación y rechazo de componentes simbólicos.
- `install.sh`: bloqueo de ciclo de vida e integridad antes de apt/despliegue; pruebas de contención sin modificar el prefijo.
- Dependencias, preferencias y administración Xray comparten el bloqueo de ciclo de vida. La desinstalación adquiere lifecycle, uninstall, integridad y Xray antes de crear el respaldo y los conserva hasta terminar o cancelar.

**Ejecución integral:** 20/20 scripts `tests/*.sh` aprobados; sintaxis Bash aprobada para bin, config, lib, modules, install y tests; ShellCheck `-S warning -x` aprobado; shfmt aprobado en los archivos de producción modificados y en las pruebas con estilo de indentación homogéneo; `tests/uninstall.sh` conserva su formato histórico mixto; `./install.sh --check` aprobado sin modificaciones.

La integración Xray validó las configuraciones generadas. Xray emitió avisos de deprecación para transportes WebSocket/gRPC y advertencias de REALITY al usar puertos distintos de 443; no fueron fallos de validación.

Fotografía histórica al 01/11/2026: estas evidencias todavía no incluían validación operativa en VPS desechable. Las actualizaciones del 02/11 incorporaron esa validación y el cotejo final 47/47; el estado vigente figura en la sección 6.

## Actualización — coordinación de concurrencia y confirmaciones (01/11/2026)

La matriz incorpora un bloqueo de ciclo de vida no bloqueante en `/run/lock/xray-manager-lifecycle.lock`, compartido por el instalador, administración Xray, acciones mutantes de `xray.service`, instalación/actualización de dependencias y persistencia de preferencias. El instalador toma además el bloqueo de integridad de usuarios/conexiones.

La desinstalación adquiere, antes de crear el respaldo, los bloqueos de ciclo de vida, desinstalación, integridad y administración Xray. Los conserva durante el respaldo, exportación, confirmación final y borrado. Así se evita que operaciones internas cubiertas por esos locks alteren el contenido entre el respaldo y la eliminación.

Se añadieron pruebas de contención para instalador, dependencias, preferencias, administración Xray y desinstalación, además de cancelaciones explícitas en el menú Xray y en la confirmación irreversible final. `A11`, `U14` y `N03` pasan a IMPLEMENTADO dentro del alcance de operaciones internas del Manager.

Estado en la actualización inicial del 02/11: M04, M06, A02, A05, U11 y U15 pasan a IMPLEMENTADO. El cotejo final posterior se registra en las secciones 6 y 14.


## Actualización — encabezado M04/M06 (02/11/2026)

- M04: `system_xray_autostart` distingue expresamente `enabled`/`enabled-runtime`, `disabled`, `masked`/`masked-runtime` y estados no aplicables (`static`, `indirect`, `generated`, `transient`). La prueba cubre los estados no configurado, habilitado y deshabilitado.
- M06: `system_show_header` aísla el fallo o salida vacía de cada proveedor: IP pública, versión Xray, estado del servicio, autostart, perfil y fecha/hora. Cada campo adopta `No disponible` sin cancelar el resto del encabezado.
- La prueba provoca cada fallo por separado y después todos simultáneamente; confirma que `menu_main` sigue mostrando sus opciones y permite salir normalmente.
- M04, M06, A02, A05, U11 y U15 pasan a IMPLEMENTADO. En ese corte aún faltaba el cotejo final, completado posteriormente con 47/47 PASS.


## Actualización — validación operativa en VPS desechable (02/11/2026)

Entorno: Ubuntu 24.04.4 LTS, host de pruebas desechable. No se modificó la VPS de desarrollo.

- Instalador: se descargó, verificó por SHA-256 oficial e instaló Xray 26.10.31 con `xray_admin_install_version` en un prefijo temporal. Después se ejecutó `install.sh --install` sobre el mismo prefijo con `XRAY_MANAGER_SKIP_DEPENDENCIES=1` y `XRAY_MANAGER_SKIP_XRAY_INSTALL=1` porque el core real ya estaba presente. Se verificaron despliegue del Manager, estado, preferencias modo 600, unidad systemd modo 644, identidad `xray` en la unidad y segunda ejecución idempotente. La unidad temporal no se registró en systemd real.
- Xray real del host: se verificó Xray 26.10.31, permisos y directorios. Se creó una configuración SOCKS temporal en `/etc/xray`, se validó con `runuser -u xray -- xray run -test`, y se eliminó. `systemd-analyze verify /etc/systemd/system/xray.service` pasó; la unidad permaneció inactive/disabled.
- Dependencias: el gestor informó todas las dependencias requeridas disponibles. `apt-get -s install` resolvió 0 upgrades, 0 instalaciones y 0 eliminaciones; no se ejecutó `apt-get update` ni se modificaron paquetes.
- Preferencias: se cambió temporalmente `APP_THEME` y `APP_DATE_FORMAT` en `/etc/xray-manager/preferences.conf`, se guardaron y recargaron correctamente, se verificó root:root 600 y se restauró el archivo original byte por byte.
- Desinstalación: se ejecutó el flujo real del módulo contra un `APP_ROOT` fixture dentro de `/tmp`; el árbol temporal se eliminó tras la confirmación. Por separado, el `uninstall_service_guard` real detectó la unidad systemd del host y bloqueó la operación sin alterarla. Xray, unidad, datos persistentes y Manager instalados quedaron intactos.

**Pendiente:** revisión final independiente de esta matriz y aprobación de cierre. En el host real no se retiró el Manager ni Xray; el flujo Manager-only se probó contra un árbol fixture y el flujo Xray-only quedó bloqueado por la unidad real instalada.


## Actualización — instalación real aislada y guard systemd (02/11/2026)

- `xray_admin_install_version 26.10.31 install` descargó el release oficial, validó el digest publicado y el SHA-256 fijado en `config/xray-version.conf`, extrajo de forma segura e instaló binario y geodata en un prefijo temporal. La versión resultante fue Xray 26.10.31/a4a3dff.
- Sobre el mismo prefijo se ejecutó `install.sh --install` con dependencias/core omitidos porque ya estaban presentes; verificó el estado persistente, permisos, unidad y segunda ejecución idempotente.
- `systemd-analyze verify` validó la unidad real del host. El guard de desinstalación detectó `xray.service` instalado y bloqueó el flujo, incluso estando inactive/disabled. La unidad no fue modificada.
- U15 pasa a IMPLEMENTADO con guard dependiente del alcance: Manager-only se permite si Xray está detenido; Xray/both se bloquean si la unidad sigue instalada; cualquier alcance se bloquea si Xray está activo. U11 se cierra con una prueba integral de todos los campos y confirmaciones del resumen previo.


## Actualización — U11, resumen previo completo (02/11/2026)

Se amplió `tests/uninstall.sh` con un escenario combinado `both + selected(users)` que genera un respaldo local y simula exportación externa verificada. La prueba comprueba alcance, política, categorías, todas las rutas, respaldo temporal, estado de exportación, advertencia sobre systemd, las cuatro exclusiones de respaldos Etapa 5 y el registro de las tres confirmaciones (respaldo, exportación y confirmación final irreversible). También verifica que el respaldo quede con modo 600 y que solo se eliminen las rutas seleccionadas.

Se corrigieron los saltos de línea del bloque de advertencias para que el resumen se muestre como líneas reales, no como secuencias `\n` literales. U11 pasa a IMPLEMENTADO.

Validación posterior: 20/20 scripts, `bash -n`, ShellCheck y shfmt de los archivos con formato homogéneo; `tests/uninstall.sh` conserva su formato histórico mixto. `./install.sh --check` PASS.


## Actualización — U15 y alcance de desinstalación (02/11/2026)

Se corrigió el guard para respetar los tres alcances aprobados. Si Xray está activo (systemd o proceso), se bloquea cualquier desinstalación. Si está detenido, `manager` puede retirarse aunque `xray.service` siga instalada, porque se conservan binario y unidad. Los alcances `xray` y `both` se bloquean mientras exista la unidad, evitando dejarla huérfana; el flujo no modifica systemd, firewall ni SSH.

Pruebas automatizadas: unidad instalada/inactiva permite Manager-only y bloquea Xray/both; servicio activo bloquea Manager-only. Validación operativa en VPS desechable con unidad real inactive/disabled: se eliminó solo un `APP_ROOT` fixture, se preservaron Xray y la unidad, y el alcance Xray-only fue rechazado. U15 IMPLEMENTADO.


## Actualización — cotejo final de Etapa 1 (02/11/2026)

La especificación aprobada Markdown/YAML se cotejó contra el código. Se verificaron las diez entradas del menú principal, las cinco entradas de la opción [8], las seis operaciones de administración Xray, los tres alcances de desinstalación, las tres políticas, las nueve categorías, advertencias, orden de respaldo/confirmación/borrado, exportación SHA-256, fallbacks, límite de paquetes y confirmación de salida. Resultado: 47/47 comprobaciones PASS.

No quedan filas normativas en estado PARCIAL o PENDIENTE. U15 es un control adicional de seguridad. U08 está implementado y probado con mocks; queda como limitación conocida que no se realizó exportación a un servidor remoto real. Etapa 1 queda lista para aceptación formal, sin declararla certificada por cuenta propia.