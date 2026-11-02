# Validación operativa de Etapa 1 — VPS desechable

**Fecha:** 02/11/2026  
**Entorno:** Ubuntu 24.04.4 LTS, VPS de pruebas desechable  
**Proyecto:** Xray Core Manager  
**Estado:** validaciones parciales aprobadas; Etapa 1 no certificada.

## 1. Instalador — prefijo aislado

Se ejecutó `install.sh --install` con un prefijo temporal, omitiendo explícitamente apt y la descarga de Xray-core. Se preparó un binario ficticio y geodata fixture para satisfacer el preflight del módulo de servicio.

Verificado: despliegue completo del código, directorios del Manager, `connections.json`, preferencias y state file; modo 600 de JSON/preferencias, modo 644 de unidad systemd; contenido de unidad con usuario/grupo `xray`; estado `manager_installed=true`, `xray_installed=true`, `service_configured=true`; segunda ejecución desde el prefijo instalado sin sobrescritura y con resultado idempotente.

**Límite:** no se descargó ni instaló el binario real ni se ejecutó `systemctl daemon-reload`; la preparación fue en `XRAY_SERVICE_TEST_MODE`.

## 2. Xray-core real preexistente

El host ya tenía Xray 26.10.31 instalado. Se comprobó el binario, geodata y propiedad/permisos de directorios. Se creó una configuración SOCKS temporal, `root:xray` modo 640, y se validó con `runuser -u xray -- /usr/local/bin/xray run -test`. Resultado: `Configuration OK`. El archivo temporal se eliminó.

La unidad real quedó `inactive` y `disabled`. No se ejecutó actualización/reinstalación del core porque la versión ya estaba presente.

## 3. Dependencias

El módulo de dependencias reportó todas las dependencias requeridas disponibles. La simulación `apt-get -s install --no-install-recommends` devolvió 0 paquetes actualizados, 0 nuevos y 0 eliminados. No se ejecutó `apt-get update` ni se alteró el estado de paquetes.

## 4. Preferencias

Se guardaron temporalmente `APP_THEME=green` y `APP_DATE_FORMAT=ymd` en `/etc/xray-manager/preferences.conf`; se verificaron el modo `root:root 600` y la recarga desde disco. Después se restauró el original y se comprobó igualdad byte por byte.

## 5. Desinstalación

Se ejecutó `uninstall_menu_action` del módulo actual contra un `APP_ROOT` fixture bajo `/tmp`. Se confirmó la eliminación de ese árbol temporal. El guard de systemd fue aislado mediante un stub local para no tocar la unidad real del host. Se verificó que Xray, unidad, preferencias y datos persistentes reales permanecían intactos.

**Límite:** no se desinstaló el Manager real, Xray real ni se retiró la unidad systemd.

## 6. Limpieza y estado final

Los archivos temporales creados en esta ronda se eliminaron. Se dejaron intactos artefactos `/tmp/xray-manager-phase-b.*` preexistentes de una fase anterior. Estado final: Xray instalado, servicio `inactive/disabled`, preferencias `root:root 600`, datos de Manager presentes y sin archivo de configuración temporal de la prueba.

## 7. Pendientes

1. Ejecutar instalación/actualización real de Xray-core mediante el flujo de descarga y verificación SHA-256 en un entorno limpio o tras snapshot restaurable.
2. Probar la desinstalación frente a una unidad systemd real bajo una ventana controlada, comprobando bloqueo y preservación de unidad/servicio.
3. Terminar el cotejo del resto de la matriz y cerrar los parciales restantes, incluidos U11 y U15.

La Etapa 1 permanece **PARCIAL — no certificada**.