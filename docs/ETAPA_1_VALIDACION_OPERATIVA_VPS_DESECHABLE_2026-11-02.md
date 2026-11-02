# Validación operativa de Etapa 1 — VPS desechable

**Fecha:** 02/11/2026  
**Entorno:** Ubuntu 24.04.4 LTS, VPS de pruebas desechable  
**Proyecto:** Xray Core Manager  
**Estado:** validaciones operativas parciales aprobadas; Etapa 1 no certificada hasta cotejo final.

## 1. Instalación real de Xray-core en prefijo temporal

Se ejecutó `xray_admin_install_version 26.10.31 install` usando el release oficial de Xray-core. El flujo consultó el release, comprobó el digest publicado, comparó SHA-256 con el valor fijado en `config/xray-version.conf`, extrajo el ZIP con validación de entradas y CRC, e instaló binario y geodata en un prefijo temporal. Resultado: Xray 26.10.31, commit `a4a3dff`; binario modo 755 y geodata modo 644.

Sobre el mismo prefijo se ejecutó `install.sh --install` con `XRAY_MANAGER_SKIP_DEPENDENCIES=1` y `XRAY_MANAGER_SKIP_XRAY_INSTALL=1`, porque Xray real ya estaba instalado en ese prefijo. Se verificaron despliegue del Manager, estado persistente, preferencias modo 600, unidad modo 644, referencias `User=xray`/`Group=xray` y segunda ejecución idempotente. La unidad temporal se preparó en `XRAY_SERVICE_TEST_MODE`; no se registró en systemd real.

## 2. Xray-core real del host

El host ya tenía Xray 26.10.31. Se comprobaron binario, geodata y permisos. Se creó una configuración SOCKS temporal `root:xray` modo 640, se validó como usuario del servicio con `runuser -u xray -- /usr/local/bin/xray run -test`, y se eliminó. Resultado: `Configuration OK`.

`systemd-analyze verify /etc/systemd/system/xray.service` pasó. La unidad real permaneció `inactive` y `disabled`; no se inició ni habilitó.

## 3. Dependencias

El módulo reportó todas las dependencias requeridas disponibles. `apt-get -s install --no-install-recommends` resolvió 0 paquetes actualizados, 0 nuevos y 0 eliminados. No se ejecutó `apt-get update` ni se modificó ningún paquete.

## 4. Preferencias

Se cambiaron temporalmente `APP_THEME=green` y `APP_DATE_FORMAT=ymd` en `/etc/xray-manager/preferences.conf`; se guardaron y recargaron desde disco, verificando `root:root 600`. Luego se restauró el archivo original y se comprobó igualdad byte por byte.

## 5. Desinstalación

Se ejecutó `uninstall_menu_action` contra un `APP_ROOT` fixture bajo `/tmp`; el árbol temporal se eliminó tras la confirmación. Con la unidad real `xray.service` inactive/disabled, el alcance Manager-only se permitió y eliminó únicamente el fixture, conservando binario y unidad. El alcance Xray-only fue bloqueado por la unidad real. No se modificó systemd, firewall ni SSH. Xray, unidad, preferencias y datos persistentes reales quedaron intactos.

## 6. Vista previa U11

`tests/uninstall.sh` cubre `both + selected(users)` con respaldo y exportación simulada. Verifica alcance, política, categoría, todas las rutas, respaldo temporal, exportación verificada, advertencia systemd, exclusiones Etapa 5 y los tres prompts: respaldo, exportación y confirmación irreversible. Comprueba modo 600 del respaldo y que solo se eliminen las rutas seleccionadas. Los saltos de línea de las advertencias se corrigieron para producir líneas reales.

## 7. Limpieza y estado final

Se eliminaron los staging y artefactos temporales creados en esta ronda. Se dejaron intactos archivos `/tmp/xray-manager-phase-b.*` preexistentes de una fase anterior. Estado final: Xray instalado, servicio `inactive/disabled`, preferencias `root:root 600`, datos de Manager presentes y sin configuración temporal de prueba. La VPS de desarrollo no se modificó.

## 8. Resultado de pruebas

- Suite completa: 20/20 PASS.
- `bash -n`: PASS en bin, config, lib, modules, install y tests.
- ShellCheck `-S warning -x`: PASS en el proyecto.
- shfmt: PASS en los archivos modificados con estilo homogéneo; `tests/uninstall.sh` conserva su formato histórico mixto.
- `./install.sh --check`: PASS sin modificaciones.
- `tests/port_collisions.sh` tuvo un fallo intermitente en una primera ejecución integral; pasó tres ejecuciones aisladas consecutivas y en la suite completa repetida.

## 9. Pendiente

La validación operativa de instalación, dependencias, preferencias, Xray, guard systemd y flujo de borrado fixture está cubierta. U11 y U15 también están IMPLEMENTADOS. El cotejo final contra la especificación aprobada dio 47/47 PASS.

El cotejo final posterior dio 47/47 comprobaciones PASS y no dejó filas normativas PARCIAL/PENDIENTE. La Etapa 1 queda IMPLEMENTADA y lista para aceptación formal; no se declara certificada hasta aprobación del usuario.


## 10. Guard U15 por alcance — prueba operativa real (02/11/2026)

Con la unidad real `xray.service` instalada e inactive/disabled, se ejecutó el flujo Manager-only con un `APP_ROOT` temporal: la desinstalación terminó y eliminó solo el fixture, preservando `/usr/local/bin/xray` y `/etc/systemd/system/xray.service`. Después se intentó Xray-only; el guard lo bloqueó al detectar la unidad, sin tocar binario ni unidad. El estado final siguió inactive/disabled.

La política queda así: Xray activo bloquea cualquier alcance; Manager-only se permite si está detenido; Xray-only/both se bloquean si la unidad está instalada para no dejarla huérfana.


## 11. Aceptación y límite de integración externa

La Etapa 1 queda implementada y lista para aceptación formal. U08 (exportación SSH/SCP con SHA-256) está implementado y cubierto con mocks de transporte/hash correcto e incorrecto; no se realizó una transferencia real porque no se proporcionó un host remoto ni credenciales de respaldo. No se declara certificación formal hasta la aceptación del usuario.