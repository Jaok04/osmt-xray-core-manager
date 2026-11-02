# Informe de implementación — concurrencia y confirmaciones de Etapa 1

**Fecha:** 01/11/2026  
**Proyecto:** Xray Core Manager  
**Rama destino:** `design/user-identity-association-v1`  
**Estado:** implementado en la copia de trabajo; pendiente publicación tras validación final.

## 1. Hallazgos que motivaron el cambio

- `install.sh` no coordinaba su despliegue con otras operaciones del Manager ni con escrituras de usuarios/conexiones.
- Las operaciones de instalación/actualización de dependencias y el guardado de preferencias no compartían un lock de ciclo de vida.
- La desinstalación generaba el respaldo antes de adquirir sus locks. Por ello, el contenido respaldado podía diferir del estado protegido al momento de borrar.
- La cancelación desde el menú de instalación Xray y la cancelación de la confirmación irreversible final no tenían pruebas directas.

## 2. Cambios implementados

### 2.1 Bloqueo común

Nuevo `lib/operation_lock.sh` con adquisición no bloqueante, archivo de lock con modo 600, liberación explícita y rechazo de rutas con componentes simbólicos. El lock predeterminado es `/run/lock/xray-manager-lifecycle.lock`.

Operaciones coordinadas: instalador, administración de Xray-core, acciones mutantes del servicio systemd, instalación/actualización de dependencias y persistencia de preferencias. El instalador toma también el lock de integridad de usuarios/conexiones antes de inicializar o ajustar ese registro.

### 2.2 Desinstalación

El flujo adquiere lifecycle, uninstall, integridad y administración Xray en orden fijo y antes de crear el respaldo. Mantiene los locks durante el respaldo local, exportación opcional, resumen, confirmación irreversible y borrado. El trap de retorno libera los locks también al cancelar o fallar. El servicio, systemd, firewall y SSH siguen fuera del alcance de eliminación. Las acciones de control del servicio también comparten lifecycle para impedir carreras de inicio/reinicio durante el flujo de desinstalación.

### 2.3 Confirmaciones

- Cancelar instalación desde el menú Xray no inicia descarga ni instalación.
- Cancelar instalación/actualización de dependencias no ejecuta `apt-get`.
- Cancelar la confirmación irreversible de desinstalación conserva las rutas seleccionadas y elimina el respaldo temporal de esa tentativa.
- Se mantiene la advertencia y cancelación específica de certificados/claves privadas.

## 3. Pruebas añadidas o ampliadas

- `tests/operation_lock.sh`: exclusión mutua, liberación, modo 600 y rechazo de symlinks.
- `tests/install.sh`: contención de lock lifecycle y lock de integridad antes de desplegar.
- `tests/stage1_dependencies.sh`: contención lifecycle sin llamadas apt.
- `tests/stage1_settings.sh`: bloqueo de escritura de preferencias durante otra operación lifecycle.
- `tests/xray_admin.sh`: cancelación del menú y contención lifecycle en administración Xray.
- `tests/xray_service_control.sh`: una acción `start` con lifecycle ocupado se rechaza sin invocar systemctl ni cambiar el estado simulado.
- `tests/uninstall.sh`: contención lifecycle/data/Xray, respaldo bajo locks y cancelación final sin borrado.

## 4. Validación

- 20/20 scripts `tests/*.sh`: PASS.
- `bash -n` en bin, config, lib, modules, install y tests: PASS.
- ShellCheck `-S warning -x` en el proyecto: PASS.
- shfmt en archivos de producción modificados y pruebas con estilo homogéneo: PASS; `tests/uninstall.sh` conserva formato histórico mixto.
- `./install.sh --check`: PASS, sin modificaciones.

Las pruebas de instalación/desinstalación y contención utilizan prefijos y fixtures temporales. No se ejecutó `apt-get`, no se instaló ni desinstaló Xray real, no se modificaron unidades systemd, firewall, SSH ni datos operativos. Xray permaneció inactivo.

## 5. Estado de Etapa 1

A11 (confirmaciones), U14 (concurrencia de desinstalación) y N03 (confirmaciones destructivas) pasan a IMPLEMENTADO para las operaciones internas del Manager cubiertas por estos locks.

En la fotografía de esta ronda (01/11), Etapa 1 continuaba **PARCIAL — no certificada**. M04/M06 y las validaciones operativas se cerraron en las actualizaciones del 02/11; el estado vigente se encuentra en la matriz y en `ETAPA_1_VALIDACION_OPERATIVA_VPS_DESECHABLE_2026-11-02.md`.


## Actualización — encabezado M04/M06 (02/11/2026)

M04 pasa a IMPLEMENTADO: la función de autostart distingue expresamente unidad no configurada, habilitada, deshabilitada, enmascarada y estados no aplicables. Se cubren `enabled` y `disabled` con mocks de systemd.

M06 pasa a IMPLEMENTADO: el encabezado captura fallos/salidas vacías de cada proveedor y muestra `No disponible` en el campo afectado. `tests/stage1_header.sh` falla de forma independiente IP, versión, estado del servicio, autostart, perfil y fecha/hora, y después falla todos a la vez al entrar a `menu_main`; las opciones [1] y [0] siguen visibles.

En la fotografía de esta ronda (01/11), la Etapa 1 permanecía PARCIAL. Las validaciones operativas y el cotejo final se completaron el 02/11; el estado vigente está registrado en la matriz y en el informe de auditoría final.
