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
- Bloqueo compartido de ciclo de vida para coordinar instalador, administración Xray, dependencias, preferencias, acciones de systemd y desinstalación; esta última protege respaldo y borrado con locks de integridad y Xray.
- Instalación/actualización de Xray-core desde releases oficiales fijados, con verificación SHA-256 y rollback.
- Preparación del usuario/grupo de sistema `xray`, rutas, permisos y unidad `xray.service` endurecida.
- Consulta del estado, diagnóstico y registros de systemd.
- Inicio, detención y reinicio explícitos del servicio.
- Habilitación y deshabilitación explícitas del inicio automático.

## Límites operativos y seguridad

- Crear o editar conexiones no genera ni aplica automáticamente una configuración al runtime de Xray.
- La instalación predeterminada despliega únicamente Xray Core Manager; Xray-core se instala después desde su menú.
- La opción explícita `--with-xray` conserva el flujo integral de instalación verificada de Xray-core y preparación de `xray.service`, sin habilitar ni iniciar el servicio.
- Iniciar, reiniciar o habilitar el servicio requiere que `/etc/xray/config.json` exista y supere la validación del binario como usuario de servicio `xray`.
- Habilitar el inicio automático no inicia Xray; deshabilitarlo no detiene un servicio que ya esté activo.
- Detener Xray no deshabilita el inicio automático.
- El Manager no modifica firewall, SSH ni configuración de red.
- La reserva de puertos del Manager es lógica; la detección de sockets con `ss` es puntual y no reserva el socket frente a procesos externos.
- El adaptador de configuración VLESS está fijado a Xray 26.10.31. WebSocket y gRPC emiten advertencias de deprecación en ese release; se conservan por compatibilidad del catálogo aprobado.
- La Etapa 1 mantiene pendientes de certificación integral documentados en `docs/MATRIZ_TRAZABILIDAD_ETAPA_1_REV_1_2.md`.

## Instalación

En una VPS Ubuntu/Debian limpia no es necesario clonar el repositorio. El repositorio es privado: crea un Fine-grained PAT limitado a `Jaok04/xray-core-manager` con permiso `Contents: Read-only` y sigue el comando completo de [`docs/INSTALACION_DESDE_VPS_LIMPIA.md`](docs/INSTALACION_DESDE_VPS_LIMPIA.md). El bootstrap solicita el PAT sin eco, descarga `install.sh` mediante GitHub API y verifica su blob contra el commit seleccionado. El instalador obtiene después el árbol completo de esa misma revisión, verifica el helper y cada archivo, y despliega el proyecto sin `.git` ni historial.

El instalador instala solo dependencias faltantes, sin ejecutar `apt upgrade`. Por defecto despliega únicamente el Manager en `/opt/xray-manager`; no instala Xray-core, no crea la cuenta `xray` ni modifica `/etc/xray` o systemd.

Después, desde **[1] Administración de Xray-core**, selecciona **[1] Instalar Xray-core** y luego **[7] Preparar servicio**. Como alternativa explícita para instalaciones integrales, `--install --with-xray` instala Xray con verificación SHA-256 y prepara la cuenta/unidad systemd. En ambos casos el servicio queda detenido y deshabilitado; su activación requiere una acción posterior y confirmación.

Desde el árbol ya desplegado, las comprobaciones son `sudo /opt/xray-manager/install.sh --check` y el menú se inicia con `sudo /opt/xray-manager/bin/xray-manager`.

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
