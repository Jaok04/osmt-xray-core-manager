# Xray Core Manager

Administrador modular de Xray-core para Linux, desarrollado en Bash.

## Estado del proyecto

**Versión:** 0.2.0-dev  
**Plataforma de referencia:** Ubuntu 24.04 LTS, amd64, Bash 5.2+  
**Idioma de la interfaz:** español

La implementación incluye menú principal, catálogo de modalidades, gestión local de conexiones y usuarios, administración del binario Xray-core, preparación segura de su unidad systemd y control explícito del ciclo de vida del servicio.

## Funcionalidades implementadas

- Catálogo de modalidades de conexión y registro local de conexiones en estado `draft`.
- Gestión de identidades y asociaciones de usuarios.
- Persistencia JSON atómica, bloqueo compartido, protección de asociaciones y pruebas de concurrencia.
- Bloqueo compartido de ciclo de vida para coordinar instalador, administración Xray, dependencias, preferencias y desinstalación; esta última protege respaldo y borrado con locks de integridad y Xray.
- Instalación/actualización de Xray-core desde releases oficiales fijados, con verificación SHA-256 y rollback.
- Preparación del usuario/grupo de sistema `xray`, rutas, permisos y unidad `xray.service` endurecida.
- Consulta del estado, diagnóstico y registros de systemd.
- Inicio, detención y reinicio explícitos del servicio.
- Habilitación y deshabilitación explícitas del inicio automático.

## Límites operativos y seguridad

- Crear o editar conexiones no genera ni aplica automáticamente una configuración al runtime de Xray.
- La instalación prepara Xray-core y `xray.service`, pero no habilita ni inicia el servicio.
- Iniciar, reiniciar o habilitar el servicio requiere que `/etc/xray/config.json` exista y supere la validación del binario como usuario de servicio `xray`.
- Habilitar el inicio automático no inicia Xray; deshabilitarlo no detiene un servicio que ya esté activo.
- Detener Xray no deshabilita el inicio automático.
- El Manager no modifica firewall, SSH ni configuración de red.
- La reserva de puertos del Manager es lógica; la detección de sockets con `ss` es puntual y no reserva el socket frente a procesos externos.
- El adaptador de configuración VLESS está fijado a Xray 26.10.31. WebSocket y gRPC emiten advertencias de deprecación en ese release; se conservan por compatibilidad del catálogo aprobado.
- La Etapa 1 mantiene pendientes de certificación integral documentados en `docs/MATRIZ_TRAZABILIDAD_ETAPA_1_REV_1_2.md`.

## Instalación

En Ubuntu/Debian, desde el directorio del proyecto:

```bash
sudo ./install.sh --check
sudo ./install.sh --install
sudo /opt/xray-manager/bin/xray-manager
```

El instalador instala solo dependencias faltantes, sin ejecutar `apt upgrade`. Despliega el Manager en `/opt/xray-manager`, instala la versión Xray aprobada, verifica su SHA-256 y prepara la cuenta y unidad systemd. No sobrescribe unidades ajenas ni activa el servicio.

## Menú de servicio

En el menú principal, selecciona **[5] Gestión del servicio Xray-core**. Cada operación que cambia el estado solicita confirmación. Las operaciones de inicio, reinicio y habilitación validan la configuración antes de invocar systemd.

La configuración debe prepararse por el flujo de configuración correspondiente antes de activar el servicio. No se crea una configuración ficticia ni se inicia Xray automáticamente.

## Rutas principales

- Código: `/opt/xray-manager`
- Configuración Xray: `/etc/xray/config.json`
- Binario: `/usr/local/bin/xray`
- Geodata: `/usr/local/share/xray`
- Datos del Manager: `/var/lib/xray-manager`
- Registros: `/var/log/xray-manager`
- Respaldos: `/var/backups/xray-manager`

Las rutas canónicas se centralizan en `config/paths.sh`.

## Validación

Desde la raíz del repositorio:

```bash
bash -n bin/xray-manager config/*.sh lib/*.sh modules/*.sh install.sh tests/*.sh
shellcheck -S warning -x bin/xray-manager config/*.sh lib/*.sh modules/*.sh install.sh tests/*.sh
shfmt -d -i 4 -ci modules/xray_service.sh modules/main_menu.sh tests/xray_service_control.sh tests/stage1_menu.sh

for test in tests/*.sh; do
  bash "$test" || exit 1
done
```

La prueba `tests/xray_vless_integration.sh` requiere el binario Xray de validación en la ruta de caché configurada o mediante `XRAY_BIN`.

## Principios

1. Validar antes de aplicar.
2. Separar preparación, validación, aplicación, verificación y persistencia.
3. No presentar estadísticas ausentes como cero.
4. No asumir soporte dinámico de usuarios para todos los protocolos.
5. No exponer la API administrativa de Xray a Internet.
6. No ejecutar cambios de red, firewall o SSH sin autorización explícita.
7. Mantener separados código, datos, registros, respaldos y archivos temporales.

Consulta `docs/` para las decisiones, contratos, estado de implementación y limitaciones de cada etapa.