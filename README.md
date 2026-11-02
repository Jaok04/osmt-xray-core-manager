# Xray Core Manager

Administrador modular de Xray-core para Linux.

## Estado

**Fase:** etapa 2 en desarrollo: catálogo y administración local de conexiones en borrador.  
**Versión:** 0.2.0-dev  
**Plataforma de referencia:** Ubuntu 24.04 LTS, amd64, Bash 5.2+.

La aplicación incorpora el menú principal, el encabezado del sistema, un catálogo de modalidades de protocolo y el registro local de conexiones en estado `draft`. Permite consultar, editar y eliminar borradores. Las conexiones aún no se generan ni aplican al runtime de Xray.

La edición y eliminación solo aceptan registros `draft`; eliminar exige escribir `ELIMINAR`. El almacenamiento JSON usa bloqueo exclusivo, escritura atómica y permisos 0600. Los puertos se comprueban contra los registros y contra sockets TCP/UDP visibles mediante `ss`.

No instala ni inicia Xray-core. Tampoco abre puertos ni modifica firewall, SSH o configuración de red.

## Estructura

- `bin/`: puntos de entrada.
- `lib/`: funciones comunes.
- `modules/`: módulos funcionales.
- `config/`: configuración general y catálogo de protocolos.
- `docs/`: documentación de arquitectura y decisiones.
- `tests/`: pruebas automatizadas.

## Instalación inicial del Manager

En Ubuntu/Debian, desde el directorio del proyecto:

```bash
sudo ./install.sh --check
sudo ./install.sh --install
/opt/xray-manager/bin/xray-manager
```

El instalador instala únicamente dependencias faltantes (sin ejecutar apt upgrade), despliega el código en /opt/xray-manager, prepara las rutas persistentes y aplica permisos restrictivos. Instala Xray-core desde el release oficial fijado, verifica SHA-256 y prepara el usuario/grupo de sistema xray y la unidad xray.service. Conserva datos/preferencias existentes y se niega a sobrescribir destinos de código o unidades ajenas.

La unidad incluye validación de configuración previa al arranque y endurecimiento de systemd. La instalación no habilita ni inicia el servicio: queda detenido y deshabilitado hasta que se genere y valide una configuración. El registro de usuarios tampoco se inicializa ni migra automáticamente.

## Uso

Como root:

```bash
/opt/xray-manager/bin/xray-manager
```

Los registros se guardan en `/var/lib/xray-manager/connections.json` con permisos privados. Cada alta inicial queda marcada como borrador y `runtime_applied=false`.

## Validación

Desde el directorio del proyecto:

```bash
bash tests/smoke.sh
shellcheck bin/xray-manager lib/ui.sh lib/system.sh modules/connections.sh modules/main_menu.sh tests/smoke.sh
shfmt -d -i 4 -ci bin/xray-manager lib/ui.sh lib/system.sh modules/connections.sh modules/main_menu.sh tests/smoke.sh
```

## Principios

1. Validar antes de aplicar.
2. Preparar → validar → aplicar → verificar → persistir.
3. No presentar estadísticas ausentes como cero.
4. No asumir soporte dinámico de usuarios para todos los protocolos.
5. No exponer la API administrativa de Xray a Internet.
6. No ejecutar cambios de red, firewall o SSH sin autorización explícita.
7. Mantener separados código, datos, registros, respaldos y archivos temporales.