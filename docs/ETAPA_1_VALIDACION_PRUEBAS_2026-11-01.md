# Informe de validación de pruebas — Etapa 1

**Fecha:** 01/11/2026  
**Proyecto:** Xray Core Manager  
**Entorno:** VPS de desarrollo, `/opt/xray-manager`  
**Alcance:** pruebas automatizadas y fixtures; sin operaciones destructivas sobre el sistema.

## Resultado

- **16/16 suites** `tests/*.sh`: aprobadas.
- Sintaxis Bash de `bin`, `config`, `lib`, `modules`, `scripts` y `tests`: aprobada.
- Compilación de `scripts/users_v2_cutover.py`: aprobada con `PYTHONPYCACHEPREFIX` temporal fuera del repositorio.

## Cobertura nueva

### Encabezado

`tests/stage1_header.sh` verifica el fallback de IP pública cuando falla y respuesta válida de `curl`, Xray ausente y presente, servicio systemd no configurado/activo, autostart no configurado/habilitado, perfil ausente/presente y renderizado de fecha/hora sin impedir la pantalla.

### Navegación

`tests/stage1_menu.sh` verifica que el encabezado se consulta nuevamente después de volver desde la opción [8]. También inyecta fallos en las cinco opciones de Administración del sistema y comprueba que el menú sigue disponible.

### Desinstalación

`tests/uninstall.sh` verifica:

- Contención del bloqueo de integridad de usuarios/conexiones.
- Contención del bloqueo de administración Xray.
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

No se ejecutaron `apt-get`, instalación/reinstalación real de Xray, modificación de systemd, firewall o SSH, ni desinstalación de componentes reales. No se migraron datos operativos. Siguen pendientes la matriz exhaustiva de navegación y confirmaciones, concurrencia con otros procesos Manager y validación en VPS desechable.

## Actualización de desinstalación — 01/11/2026

Se amplió `tests/uninstall.sh` con pruebas individuales de las nueve categorías, los tres alcances y las tres políticas. La limpieza de respaldos existentes y temporales se comprobó en los tres alcances. También se verificó que `selected` en alcance combinado conserva las categorías de datos no seleccionadas.

Las pruebas usan exclusivamente fixtures temporales. No se ejecutó la desinstalación real de Xray ni del Manager.

**Dictamen:** Etapa 1 continúa **PARCIAL — no certificada**.