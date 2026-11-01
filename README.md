# Xray Core Manager

Administrador modular de Xray-core para Linux, desarrollado en Bash.

## Estado del proyecto

- **Versión:** 0.2.0-dev
- **Etapa:** 2 — catálogo y gestión local de conexiones en borrador.
- **Plataforma de referencia:** Ubuntu 24.04 LTS, amd64, Bash 5.2+.
- **Idioma de la interfaz:** español.

La aplicación incluye un menú principal, información del sistema, un catálogo de 35 modalidades de protocolo y un registro local de conexiones en estado `draft`. Permite consultar, crear, editar y eliminar borradores.

**Un borrador no es una conexión activa.** Todavía no se genera ni aplica configuración al runtime de Xray.

## Estructura

- `bin/`: punto de entrada.
- `lib/`: funciones comunes de interfaz y sistema.
- `modules/`: módulos funcionales.
- `config/`: configuración general y catálogo de protocolos.
- `docs/`: decisiones técnicas y documentación de etapas.
- `tests/`: pruebas automatizadas.

## Seguridad y alcance actual

- Los borradores se almacenan en `/var/lib/xray-manager/connections.json`.
- El registro utiliza bloqueo exclusivo con `flock`, escritura atómica y permisos `0600`.
- La edición y eliminación solo aceptan registros en estado `draft`.
- La eliminación exige confirmación literal `ELIMINAR`.
- Se validan modalidades, nombres, puertos, límites y duplicados.
- La comprobación de sockets con `ss` es puntual y no reserva el puerto.
- No instala ni inicia Xray-core.
- No genera ni aplica configuraciones Xray.
- No abre puertos ni modifica firewall, SSH o red.

## Uso

Como root en la VPS:

```bash
/opt/xray-manager/bin/xray-manager
```

## Validación

Desde el directorio del proyecto:

```bash
bash tests/smoke.sh
shellcheck bin/xray-manager lib/ui.sh lib/system.sh modules/connections.sh modules/main_menu.sh tests/smoke.sh
shfmt -d -i 4 -ci bin/xray-manager lib/ui.sh lib/system.sh modules/connections.sh modules/main_menu.sh tests/smoke.sh
```

## Principios de diseño

1. Validar antes de aplicar.
2. Preparar → validar → aplicar → verificar → persistir.
3. Un dato ausente no equivale a cero.
4. No asumir soporte dinámico de usuarios para todos los protocolos.
5. No exponer la API administrativa de Xray a Internet.
6. No ejecutar cambios de red, firewall o SSH sin autorización explícita.
7. Mantener separados código, datos, registros, respaldos y archivos temporales.

Consulta los documentos de `docs/` para conocer las decisiones y limitaciones pendientes.
