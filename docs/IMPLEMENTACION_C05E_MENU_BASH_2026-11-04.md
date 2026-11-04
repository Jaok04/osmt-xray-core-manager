# Implementación C-05E — Integración del menú Bash de validación Xray

**Fecha:** 2026-11-04
**Rama:** `design/user-identity-association-v1`
**Base:** `ed700c1e770063f6e67c6ebaeae4652172bb2f02`
**Autorización:** aprobación del diseño y autorización expresa de implementación completa; sin commit ni push.

## 1. Alcance ejecutado

Se integró la validación de configuraciones guardadas y la consulta de informes en el menú `CONFIGURACIONES, PERFILES Y RESPALDOS`, respetando el diseño C-05E. La interfaz Bash orquesta servicios existentes y no duplica reglas de negocio.

Archivos modificados:

- `bin/xray-manager`: carga el nuevo módulo de validación.
- `config/paths.sh`: define `XRAY_MANAGER_VALIDATION_DIR`, configurable por entorno y con valor predeterminado `/var/lib/xray-manager/validation`.
- `modules/profiles.sh`: conecta la opción `[2]` con el submenú C-05E.
- `scripts/xray_validation_history.py`: añade CLI JSON a `ValidationHistoryService`, conservando su API.
- `tests/smoke.sh`: incorpora sintaxis y ejecución de la prueba focal.
- `tests/xray_configurations_menu.sh`: actualiza la expectativa del menú conectado.

Archivos nuevos:

- `modules/xray_validation_menu.sh`: interfaz, selección de configuración, confirmación de validación, último informe, historial, detalle y comparación.
- `tests/xray_validation_menu.sh`: pruebas de integración focales.
- Este documento y `docs/AUDITORIA_C05E_MENU_BASH_2026-11-04.md`.

## 2. Menú y operaciones

El submenú presenta:

```text
VALIDACIÓN DE CONFIGURACIONES XRAY
[1] Validar configuración guardada
[2] Validar archivo externo (no disponible en esta entrega)
[3] Validar configuración activa (no disponible en esta entrega)
[4] Ver último informe de validación
[5] Consultar historial de validaciones
[0] Volver
```

### Validar configuración guardada

- Obtiene el catálogo a través de `xray_configurations_cli`.
- Selecciona por índice y conserva el `config_id` validado por el servicio; no construye rutas desde la entrada del usuario.
- Muestra nombre, identidad, revisión actual y estado.
- Rechaza configuraciones sin contenido/revisión.
- Solicita confirmación explícita antes de ejecutar el motor.
- Reutiliza `scripts/xray_config_promotion.py validate --config-id ... --revision ...`, pasando por separado las rutas de almacén, configuración y clave maestra. Bash no abre ni lee la clave.
- Presenta el ID del informe, revisión exacta, resultado, promoción y estado resultante. Aclara que no aplica configuración ni inicia/reinicia Xray.
- Cancelar no genera informe ni promueve el estado.

### Historial y CLI C-05D

`xray_validation_history.py` incorpora subcomandos `list`, `latest`, `show` y `compare`, salida JSON UTF-8 por stdout y errores controlados por stderr. Los límites de paginación y los identificadores se validan antes de consultar. `--store` debe ser absoluto.

- `list`: filtros por configuración, revisión, intervalo de fechas, tipo y resultado; paginación acotada.
- `latest`: último informe global o por configuración.
- `show`: detalle de un ID validado.
- `compare`: compara dos IDs; el servicio rechaza `config_id` distintos y admite revisiones distintas.

La CLI no crea ni repara almacenes durante consultas. Si el almacén aún no existe, `list` devuelve una página vacía y `latest` devuelve `null`; para un almacén existente exige directorios y lock presentes, y el servicio C-05D verifica integridad. No se aceptan rutas arbitrarias de informes.

Las consultas utilizan el lock y la recuperación WAL existentes de C-05B/C-05D. Por tanto, una transacción interrumpida puede completarse mediante la recuperación ya definida; no se mutan informes/catálogo como parte de una consulta ordinaria.

### Opciones no disponibles

Validación de archivo externo y validación de configuración activa permanecen deshabilitadas con explicación explícita. No se lee un archivo externo, no se consulta el runtime, no se infiere qué configuración ejecuta Xray y no se modifica ningún servicio.

## 3. Seguridad y límites

- No se añadió dependencia.
- Se comprueban Python 3, `jq` y root antes de usar los servicios Bash.
- No se utiliza `eval` ni se concatenan argumentos de CLI en una cadena de shell.
- Bash no descifra configuración ni lee `master.key`.
- Los informes se presentan a través del servicio C-05B/C-05D y su saneamiento existente.
- Consultas sin almacén no lo crean; almacenes inseguros/incompletos se rechazan sin reparación automática.
- No hay operaciones de edición, borrado o retención de informes.
- No se habilitó archivo externo ni configuración activa.
- No se tocó runtime, servicios, certificados, firewall, puertos, red, dependencias ni VPS de pruebas.

## 4. Pruebas

La prueba focal `tests/xray_validation_menu.sh` utiliza una clave sintética y almacenes temporales. Verifica navegación, opciones no disponibles, historial vacío, último informe vacío, rechazo/ausencia de creación de almacén, cancelación sin persistencia y, cuando `/usr/local/bin/xray` está disponible, una validación positiva de extremo a extremo desde el menú con el binario Xray real.

Resultados registrados en la auditoría C-05E:

- C-05E focal: PASS.
- Regresión Python C-05A/B/C/D: 76/76 PASS.
- Regresión shell: 57/57 PASS.
- `bash -n` focal: PASS.
- ShellCheck severidad error focal: PASS.
- `install.sh --check`: PASS; no-op, sin cambios del sistema.
- `git diff --check`: PASS.

## 5. Estado

C-05E está implementada, probada y auditada localmente. Este registro no constituye aceptación formal ni publicación. No se creó commit ni se hizo push. C-05F no fue iniciada ni autorizada. Etapa 5 y Etapa 2 permanecen ABIERTAS.

## Addendum de aceptación formal — 2026-11-04

El propietario aceptó formalmente C-05E. La aceptación comprende la implementación y la evidencia de pruebas/auditoría aquí descritas, con las limitaciones y escenarios pendientes detallados en el expediente de auditoría. C-05E queda ACEPTADA. Esta decisión no autoriza commit, push ni sincronización; la publicación requiere autorización separada. C-05F no está autorizada ni iniciada.
