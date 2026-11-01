# Xray Core Manager

Administrador modular de Xray-core para Linux, desarrollado en Bash.

## Estado del proyecto

**Versión:** 0.2.0-dev  
**Plataforma de referencia:** Ubuntu 24.04 LTS, amd64, Bash 5.2+  
**Rama de desarrollo:** `main`

La implementación actual incluye:

- Menú principal y módulos de administración.
- Catálogo de 38 modalidades de conexión.
- Registro local de conexiones como borradores (`draft`).
- Gestión de usuarios VLESS asociados a conexiones.
- Modelo neutral VLESS y adaptador de configuración para Xray 26.10.31.
- Administración controlada del binario Xray y sus datos geográficos.
- Rutas centralizadas, persistencia JSON atómica, bloqueo compartido y pruebas de concurrencia.
- Respaldo y flujo de desinstalación con salvaguardas.

## Límites operativos actuales

- Crear o editar un borrador no genera ni aplica automáticamente una configuración al runtime.
- La instalación/reparación de Xray está separada de la gestión de servicios: el módulo no crea ni modifica unidades systemd, no inicia ni reinicia Xray y no modifica firewall, SSH ni red.
- La reserva de puertos del Manager es lógica y global por número de puerto. La detección con `ss` es puntual; no reserva el socket frente a procesos externos.
- El adaptador VLESS está fijado a Xray 26.10.31 y se valida con el binario de prueba en caché.
- El flujo de desinstalación real aún requiere pruebas integrales de recuperación en un entorno aislado; no debe considerarse autorizado ni validado para borrar instalaciones reales.
- Las rutas futuras de perfiles, dominios, certificados e historiales están centralizadas, pero varios consumidores aún están pendientes de implementación.

Consulta `docs/` para las decisiones, contratos, estado de implementación y limitaciones de cada etapa.

## Estructura

- `bin/`: punto de entrada.
- `config/`: configuración general, rutas, catálogo y versión de Xray fijada.
- `lib/`: utilidades comunes y persistencia.
- `modules/`: conexiones, usuarios, administración Xray y desinstalación.
- `docs/`: arquitectura, decisiones técnicas y documentación por etapa.
- `tests/`: pruebas funcionales, concurrencia, persistencia e integración.

## Ejecución

La ruta de instalación prevista es:

```bash
/opt/xray-manager/bin/xray-manager
```

El administrador requiere los permisos adecuados para sus operaciones. Los datos, configuraciones, registros, cachés y respaldos se mantienen separados del código del proyecto.

## Validación

Desde la raíz del repositorio:

```bash
bash -n bin/xray-manager config/paths.sh lib/*.sh modules/*.sh tests/*.sh
shellcheck -x bin/xray-manager config/paths.sh lib/*.sh modules/*.sh tests/*.sh
shfmt -d bin/xray-manager config/paths.sh lib/*.sh modules/*.sh tests/*.sh

for test in tests/*.sh; do
  bash "$test"
done
```

La prueba `tests/xray_vless_integration.sh` requiere el binario Xray de validación indicado por `XRAY_BIN` o disponible en la ruta de caché configurada.

## Principios

1. Validar antes de aplicar.
2. Separar preparación, validación, aplicación, verificación y persistencia.
3. No presentar estadísticas ausentes como cero.
4. No asumir soporte dinámico de usuarios para todos los protocolos.
5. No exponer la API administrativa de Xray a Internet.
6. No modificar firewall, SSH ni red sin autorización explícita.
7. Mantener separados código, datos, registros, respaldos y archivos temporales.
