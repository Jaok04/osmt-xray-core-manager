# Informe de validación de pruebas — Etapa 1

**Fecha:** 01/11/2026  
**Proyecto:** Xray Core Manager  
**Entorno:** VPS de desarrollo, `/opt/xray-manager`  
**Alcance:** pruebas automatizadas y fixtures; sin operaciones destructivas sobre el sistema.

## Resultado

- **20/20 suites** `tests/*.sh`: aprobadas en la ejecución integral del 02/11/2026.
- Sintaxis Bash de `bin`, `config`, `lib`, `modules`, `scripts` y `tests`: aprobada.
- Compilación de `scripts/users_v2_cutover.py`: aprobada con `PYTHONPYCACHEPREFIX` temporal fuera del repositorio.

## Cobertura nueva

### Encabezado

`tests/stage1_header.sh` verifica el fallback de IP pública cuando falla y respuesta válida de `curl`, Xray ausente y presente, servicio systemd no configurado/activo, autostart no configurado/habilitado/deshabilitado, perfil ausente/presente y renderizado de fecha/hora. También inyecta fallos independientes en IP, versión, estado del servicio, autostart, perfil y fecha/hora; luego falla todos simultáneamente y verifica que `menu_main` sigue mostrando las opciones [1] y [0].

### Navegación

`tests/stage1_menu.sh` verifica que el encabezado se consulta nuevamente después de volver desde la opción [8]. También inyecta fallos en las cinco opciones de Administración del sistema y comprueba que el menú sigue disponible.

### Desinstalación

`tests/uninstall.sh` verifica:

- Contención de los bloqueos de ciclo de vida, integridad de usuarios/conexiones y administración Xray antes de crear el respaldo.
- Cancelación de la confirmación irreversible final sin eliminar rutas.
- El respaldo se genera mientras se mantienen los bloqueos de las operaciones internas que podrían modificar su contenido.
- Advertencia específica de certificados/claves privadas y cancelación sin borrar la clave fixture.
- Prueba individual de las nueve categorías: `xray-config`, `profiles`, `users`, `connections`, `domains`, `certificates`, `backups`, `preferences` y `logs` (incluye `history`).
- Políticas `keep`, `all` y `selected` en los tres alcances (`xray`, `manager`, `both`), con fixtures temporales.
- Política `all`: borrado de respaldos preexistentes y temporales en Xray-core, Manager y ambos.
- Política `selected` en alcance combinado: elimina la categoría elegida y conserva las demás categorías de datos.
- Exportación remota simulada con verificación SHA-256 correcta e incorrecta.

## Resultado de ejecución integral

Todas las suites finalizaron con código cero: concurrencia, carreras cruzadas, fallos de almacenamiento JSON, colisiones de puertos, smoke, dependencias, encabezado, menú, preferencias, desinstalación, usuarios legacy/v2, cutover, administración Xray e integración de configuraciones VLESS.

La prueba de integración VLESS produjo advertencias de Xray sobre la deprecación de WebSocket/gRPC y sobre REALITY en puertos distintos de 443. Las configuraciones se validaron correctamente; las advertencias no hicieron fallar las pruebas.

## Límites y pendientes

No se ejecutaron `apt-get`, instalación/reinstalación real de Xray, modificación de systemd, firewall o SSH, ni desinstalación de componentes reales. No se migraron datos operativos. M04/M06 ya cuentan con cobertura automatizada y pasan a IMPLEMENTADO. Sigue pendiente la validación operativa en VPS desechable y el cotejo final del resto de la matriz.

## Actualización de desinstalación — 01/11/2026

Se amplió `tests/uninstall.sh` con pruebas individuales de las nueve categorías, los tres alcances y las tres políticas. La limpieza de respaldos existentes y temporales se comprobó en los tres alcances. También se verificó que `selected` en alcance combinado conserva las categorías de datos no seleccionadas.

Las pruebas usan exclusivamente fixtures temporales. No se ejecutó la desinstalación real de Xray ni del Manager.

**Dictamen:** Etapa 1 continúa **PARCIAL — no certificada**.


## Actualización — bloqueos y confirmaciones (01/11/2026)

Se incorporó `lib/operation_lock.sh` con locks no bloqueantes, permisos privados y rechazo de rutas simbólicas. El bloqueo `/run/lock/xray-manager-lifecycle.lock` coordina instalador, administración Xray, dependencias y guardado de preferencias. El instalador coordina además el lock de integridad de datos.

Las acciones mutantes de `xray.service` toman lifecycle. La desinstalación toma lifecycle, uninstall, integridad y Xray antes de crear el respaldo y los conserva durante toda la operación; esto evita que un `start` se cuele entre la comprobación de servicio detenido y el borrado. Pruebas de fixtures verifican contención de cada lock y cancelación de la confirmación irreversible sin borrado.

La batería completa pasó 20/20. Bash syntax y ShellCheck pasaron en el proyecto; shfmt pasó en archivos de producción modificados y pruebas con estilo homogéneo. `tests/uninstall.sh` conserva formato histórico mixto. `./install.sh --check` pasó sin modificar el sistema. No se ejecutó instalación real ni desinstalación real.


## Actualización — M04/M06 del encabezado (02/11/2026)

- M04: `system_xray_autostart` distingue `Habilitado`, `Deshabilitado`, `Enmascarado`, `No aplica (...)`, `No configurado` y `No disponible`. La prueba cubre explícitamente el estado `disabled`, además de `enabled` y unidad ausente.
- M06: se añaden fallbacks para fallos y salidas vacías de cada proveedor de encabezado. La prueba inyecta fallos uno por uno en seis proveedores (IP, versión, servicio, autostart, perfil y fecha/hora) y luego simultáneamente; confirma que el menú principal conserva sus opciones.
- Resultado final del 02/11/2026: suite completa 20/20 PASS; `bash -n`, ShellCheck y shfmt PASS; `./install.sh --check` PASS sin modificaciones. `tests/port_collisions.sh` tuvo un fallo intermitente en una primera ejecución integral; pasó tres ejecuciones aisladas consecutivas y volvió a pasar en la suite completa. Xray permaneció inactive.