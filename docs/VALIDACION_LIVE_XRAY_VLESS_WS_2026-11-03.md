# Validación live inicial — instalación Xray-core y VLESS-WS

**Fecha:** 2026-11-03
**Entorno:** VPS de desarrollo Ubuntu 24.04.4 LTS, amd64
**Repositorio:** Jaok04/xray-core-manager
**Rama:** design/user-identity-association-v1
**HEAD de código:** d632908300441341d84db8573c417f14002c3f70

## 1. Instalación real de Xray-core

Se ejecutó el menú real del Manager: Sistema → Configuración del sistema y administrador → Administración de Xray-core → Instalar Xray-core.

- Versión: Xray-core 26.10.31, commit a4a3dff, Linux amd64.
- Release oficial y archivo .dgst comprobados; SHA-256 del ZIP coincidente con el valor fijado en config/xray-version.conf.
- Binario instalado en /usr/local/bin/xray; geodata en /usr/local/share/xray/.
- El binario declara la versión solicitada y la instalación terminó correctamente.
- No había binario/geodata previos que respaldar.
- No se creó unidad systemd ni se inició/habilitó servicio en esta operación.

SHA-256 de los archivos instalados:
- xray: cc4b84d3069569f297a61f04b914f2bb37e9d202fd7b84cb50def1fc30fd40e1
- geoip.dat: ce90dc02a81528109c99d769e1f8fe3071ded6b02a574f31e62d8f4eee312563
- geosite.dat: 9ee94acb06e2f795831fb1589c0dc7af9242b0fb8d9196afd981b915b1097ed3

## 2. Corrección de permisos previa al almacén VLESS

El preflight read-only de scripts/vless_config_store.py audit falló porque la raíz del catálogo /var/lib/xray-manager/connections estaba root:root 750, mientras el contrato del almacén y la política de install.sh exigen root:root 700.

Se verificó que la ruta era un directorio real, sin symlink, propiedad de root:root. Se ajustó únicamente ese directorio de modo 750 a 700, que es el modo declarado por el instalador. Tras el ajuste, el preflight/audit pasó. No se modificó el código del repositorio.

## 3. Conexión VLESS-WS

La conexión se creó desde el menú real del Manager y el asistente VLESS:

| Campo | Valor |
|---|---|
| Nombre | Prueba-VLESS-WS-Real |
| ID | conn-1793749234-670662 |
| Modalidad | vless_ws — VLESS-WS sin TLS |
| Dirección de escucha | 0.0.0.0 |
| Puerto previsto | 10001 |
| Transporte | WebSocket |
| Ruta | /ws |
| Seguridad de transporte | none |
| Capacidad | 1 usuario |
| Estado | draft |
| runtime_applied | false |
| Revisión persistida | 1 |

El almacén publicó la revisión configurations/conn-1793749234-670662.r000001.json; secret_ref es null, como corresponde a esta modalidad sin TLS/REALITY. La auditoría posterior devolvió cero referencias rotas, cero archivos huérfanos y cero secretos huérfanos.

Se creó un usuario VLESS de prueba con etiqueta Cliente-Prueba-VLESS-WS, estado draft y runtime_applied=false. El UUID se omite deliberadamente de esta documentación y se comunica al propietario por el canal de trabajo.

**Nota de esquema:** el archivo live de usuarios continúa en formato legacy (arreglo JSON), por lo que el menú utilizó el módulo legacy VLESS. No se ejecutó cutover ni migración a users v2; no se alteró el esquema de identidades/asociaciones.

## 4. Validación Xray

- La previsualización temporal del asistente terminó con Configuration OK.
- La recuperación desde el menú volvió a validar la revisión guardada.
- Se ejecutó una segunda recuperación del mismo borrador con XRAY_VALIDATION_BINARY=/usr/local/bin/xray, para validar expresamente con el binario instalado en esta VPS. Resultado: Configuration OK.
- La configuración persistida no contiene secretos privados; el modelo incorpora el usuario desde el registro de usuarios al reconstruir la configuración.
- Xray advirtió que WebSocket está obsoleto/no recomendado, puede retirarse y recomienda migrar a XHTTP H2/H3. La modalidad se mantuvo porque fue la seleccionada para esta prueba.

## 5. Límites de esta prueba

**Verificado:** instalación real, navegación del Manager, creación de borrador, persistencia de revisión VLESS, usuario de prueba, recuperación, validación con el binario instalado y auditoría del almacén.

**No probado / no ejecutado:**
- No se escribió /etc/xray/config.json.
- No se ejecutó xray_service_prepare; no existe xray.service ni cuenta/grupo de servicio creados por esta prueba.
- No se inició ni habilitó Xray.
- El puerto 10001 no está escuchando; no se modificó firewall ni reglas de red.
- No se realizó conexión desde un cliente externo ni prueba WAN.
- No se aplicó configuración al runtime.

La creación y validación de un borrador no equivale a una conexión operativa. La siguiente fase requiere diseñar/autorizar la aplicación segura de la configuración al runtime, preparar la unidad/cuenta systemd y acordar explícitamente el inicio del listener y las reglas de red. La inspección del menú actual no encontró una acción de aplicación runtime para esta conexión.

## 6. Estado Git y normativa

- Código: sin cambios; HEAD permanece en d632908300441341d84db8573c417f14002c3f70.
- Documentación de continuidad: actualizada localmente en esta revisión; pendiente de commit/publicación.
- Xray-Normativa/: sin cambios.
- main: sin cambios.
- No se modificaron certificados, firewall, puertos, servicio ni configuración runtime.

## 7. Publicación de la evidencia

La documentación de esta prueba y los registros de continuidad asociados se incluyen en la publicación autorizada a la rama `design/user-identity-association-v1`. La publicación no altera los resultados ni los límites operativos descritos: conexión draft, `runtime_applied=false`, Xray inactivo, sin listener, sin cambios de firewall y sin prueba WAN.
