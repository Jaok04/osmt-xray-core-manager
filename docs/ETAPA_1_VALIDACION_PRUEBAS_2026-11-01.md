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

En esa ronda inicial (01/11) no se ejecutaron `apt-get`, instalación/reinstalación real de Xray, modificación de systemd, firewall o SSH, ni desinstalación de componentes reales. Las pruebas operativas posteriores del 02/11 se documentan en `ETAPA_1_VALIDACION_OPERATIVA_VPS_DESECHABLE_2026-11-02.md`. M04/M06 cuentan con cobertura automatizada y pasan a IMPLEMENTADO.

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


## Validación operativa en VPS desechable — 02/11/2026

Se utilizó Ubuntu 24.04.4 LTS en el host de pruebas. La VPS de desarrollo no se modificó.

1. **Instalador:** instalación con prefijo aislado y Xray ficticio; validó despliegue, archivos de estado, preferencias, permisos, unidad systemd y segunda ejecución idempotente. Se omitieron deliberadamente dependencias y descarga del core (`XRAY_MANAGER_SKIP_DEPENDENCIES=1`, `XRAY_MANAGER_SKIP_XRAY_INSTALL=1`).
2. **Xray real ya instalado:** versión 26.10.31; se validó una configuración SOCKS temporal como usuario `xray` con `runuser`. Archivo temporal eliminado. Unidad real permaneció inactive/disabled. No se reinstaló el core.
3. **Dependencias:** todas disponibles. `apt-get -s install` reportó 0 upgraded, 0 newly installed y 0 to remove. No se ejecutó una operación apt real.
4. **Preferencias:** guardado atómico y recarga real de tema/fecha en `/etc/xray-manager/preferences.conf`; propiedad y modo root:root 600 verificados; contenido original restaurado exactamente.
5. **Desinstalación:** el módulo eliminó realmente un `APP_ROOT` fixture en `/tmp`, con confirmación final. El guard systemd fue aislado; no se eliminó la unidad ni el Manager real.

Los artefactos temporales de esta ronda se eliminaron. Se conservaron archivos temporales preexistentes de pruebas anteriores que no pertenecían a esta ronda. Estado final del host: Xray instalado, `xray.service` inactive/disabled, preferencias y datos persistentes presentes.

**Límites:** aún falta una instalación/actualización real del core mediante descarga verificada y una prueba real de desinstalación con la unidad systemd en ventana controlada. Etapa 1 sigue **PARCIAL — no certificada**.


## Actualización operativa adicional — 02/11/2026

Se probó `xray_admin_install_version` con el release oficial 26.10.31 en un prefijo temporal: descarga, digest oficial, SHA-256 fijado, extracción segura, instalación y versión resultante correctos. Sobre el mismo prefijo, `install.sh --install` desplegó el Manager y preparó la unidad en modo de prueba; la segunda ejecución fue idempotente.

En el host real, `systemd-analyze verify` pasó. Con la unidad `xray.service` instalada e inactive/disabled, el alcance Manager-only eliminó solo un `APP_ROOT` fixture y preservó la unidad y el binario; el alcance Xray-only fue bloqueado. El guard también bloquea cualquier alcance si Xray está activo. U15 pasa a IMPLEMENTADO. U11 también pasa a IMPLEMENTADO tras verificar todos los campos del resumen previo y las tres confirmaciones.


## Actualización — U11 vista previa completa (02/11/2026)

`tests/uninstall.sh` ahora verifica el resumen `both + selected(users)` con respaldo y exportación simulada: alcance, política, categorías, rutas, respaldo temporal, exportación verificada, advertencia systemd, exclusiones Etapa 5 y prompts de respaldo/exportación/confirmación irreversible. Se valida además el modo 600 del archivo de respaldo y la eliminación exclusiva de rutas seleccionadas.

Se corrigieron los saltos de línea de las advertencias del resumen. Suite integral posterior: 20/20 PASS; `bash -n`, ShellCheck y shfmt de archivos con estilo homogéneo PASS; `./install.sh --check` PASS. `tests/uninstall.sh` conserva su formato histórico mixto.


## Actualización — guard de desinstalación dependiente del alcance (02/11/2026)

Se corrigió `uninstall_service_guard`: el estado activo de Xray bloquea todos los alcances; si está detenido, Manager-only puede retirarse sin tocar la unidad ni Xray; Xray-only/both se bloquean si la unidad está instalada para evitar una unidad huérfana. `tests/uninstall.sh` cubre estos tres escenarios.

En VPS desechable con unidad real inactive/disabled se ejecutó Manager-only contra un `APP_ROOT` fixture: el árbol fue eliminado y Xray/unidad permanecieron intactos. Xray-only fue bloqueado por la unidad real.