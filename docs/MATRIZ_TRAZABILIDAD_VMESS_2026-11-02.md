# Matriz de trazabilidad VMess — 2026-11-02

**Línea base:** Etapa 2 revisión 1.3 (Markdown + YAML), más decisiones complementarias y diseño VMess aprobado.
**Alcance:** módulo VMess dentro de Etapa 2; no equivale a auditoría completa de la Etapa 2.
**Evidencia detallada:** `docs/AUDITORIA_INTEGRAL_VMESS_2026-11-02.md`.

| ID | Requisito / componente | Diseño / referencia | Implementación | Prueba / evidencia | Estado |
|---|---|---|---|---|---|
| VM-01 | Acceso desde menú Gestión de protocolos | Etapa 2 §2 | connections_menu | suite 40/40; navegación | VERIFICADO |
| VM-02 | Cinco principales y tres modalidades adicionales del menú VMess | Etapa 2 §3.2 | `connections_family_menu` | `stage2_navigation.sh` | VERIFICADO |
| VM-03 | 14 combinaciones transporte/seguridad aprobadas | Diseño VMess §3; decisión HTTPUpgrade-TLS | `vmess_model.sh`, adaptador, catálogo | Xray 14/14; navegación 14/14 | VERIFICADO |
| VM-04 | VMess-WS claramente sin TLS adicional | Etapa 2 §3.2; decisión de etiquetas | menú y `connections_mode_label` | aserciones de menú/listado | VERIFICADO |
| VM-05 | VMess-TLS identificado RAW/TCP + TLS | YAML `vmess_tls`; equivalencia documentada con `vmess_tcp_tls` | menú y `connections_mode_label` | aserciones de menú/listado | VERIFICADO |
| VM-06 | UUID y estructura Xray `settings.users` | Diseño VMess §4-5 | modelo/adaptador | `vmess_model.sh`, `xray_vmess_integration.sh` | VERIFICADO |
| VM-07 | UUID válido y no duplicado | Diseño VMess §8 | modelo/asistente/almacén | negativos UUID inválido/duplicado | VERIFICADO |
| VM-08 | Email/etiqueta único por usuario | Diseño y almacén | modelo, adaptador y almacén aplican unicidad exacta case-sensitive | pruebas de modelo, asistente, adaptador y persistencia | VERIFICADO EN FIXTURES |
| VM-09 | Nivel VMess dentro de rango | Diseño VMess §4 | modelo/asistente/almacén | casos del asistente/modelo | VERIFICADO |
| VM-10 | Límite de usuarios por slots y máximo interno | diseño de asistente | asistente/almacén | slots inválidos y límite | VERIFICADO |
| VM-11 | Dirección y puerto válidos | diseño de asistente/modelo | modelo/asistente | puerto inválido; integración Xray | VERIFICADO |
| VM-12 | Parámetros WebSocket/HTTPUpgrade | Etapa 2 §3.2; diseño §3 | asistente/adaptador | 14/14 y casos negativos | VERIFICADO |
| VM-13 | Parámetros gRPC | Etapa 2 §3.2; diseño §3 | asistente/adaptador | 14/14 | VERIFICADO |
| VM-14 | Parámetros XHTTP | Etapa 2 §3.2; diseño §3 | asistente/adaptador | 14/14 | VERIFICADO |
| VM-15 | Parámetros mKCP | Etapa 2 §3.2; diseño §3 | asistente/adaptador | 14/14 | VERIFICADO |
| VM-16 | Advertencia de reloj, máximo 120 segundos | Diseño VMess §5 y §7 | asistente | `vmess_assistant.sh` | VERIFICADO |
| VM-17 | Advertencia WebSocket | Diseño VMess §7 | asistente | `vmess_assistant.sh` | VERIFICADO |
| VM-18 | Advertencia HTTPUpgrade | Diseño VMess §7 | asistente | `vmess_assistant.sh` | VERIFICADO |
| VM-19 | Resumen completo previo al consentimiento | Etapa 2 §5.1; diseño §7-8 | asistente | orden resumen→consentimiento | VERIFICADO |
| VM-20 | No exponer claves privadas en resumen | Diseño VMess §7-8 | asistente | pruebas de ausencia de material TLS/REALITY | VERIFICADO |
| VM-21 | Validar certificado PEM, clave PEM y correspondencia | Diseño VMess §5 y §8 | adaptador | PEM inválido y mismatch negativos | VERIFICADO |
| VM-22 | Restringir permisos de clave TLS de origen | Diseño VMess §7 y decisión correctiva autorizada | adaptador/preparador exigen root:root, modo 0600 y un solo enlace duro | negativos 0644/0640/0400, grupo no root y hardlink; positivo 0600 | VERIFICADO EN FIXTURES |
| VM-23 | Validar REALITY y combinaciones compatibles | diseño VMess §3, §5, §8 | adaptador | clave ausente/inválida, short ID inválido | VERIFICADO |
| VM-24 | Generar JSON Xray válido por modalidad | Etapa 2 §7; diseño §5 | adaptador 26.10.31 | `xray run -test` 14/14 | VERIFICADO |
| VM-25 | Crear sólo borrador; no activar runtime | diseño VMess §1, §5 | asistente/almacén | catálogo `draft`, `runtime_applied=false` en fixtures | VERIFICADO EN FIXTURES |
| VM-26 | Cancelar/EOF no guardar configuración | diseño §8 y decisión correctiva autorizada | asistente devuelve estado no exitoso ante cancelación/EOF | prueba de estado 3 y catálogo intacto | VERIFICADO EN FIXTURES |
| VM-27 | Cancelar creación común no deja registro base | Etapa 2 §5.1; decisión correctiva autorizada | limpieza condicional bajo bloqueo; sólo retira draft VMess sin refs y no aplicado | vmess_creation_flow.sh: cancelación/fallo sin cambios; preserva draft con refs | VERIFICADO EN FIXTURES |
| VM-28 | Persistencia versionada y referencias VMess separadas | diseño VMess §6.1 | `vmess_config_store.py` | suite persistencia | VERIFICADO PARCIAL |
| VM-29 | AES-256-GCM y AAD VMess | diseño VMess §6.1-7 | almacén | store/read, tag alterado, AAD | VERIFICADO |
| VM-30 | Clave maestra fail-closed | diseño de persistencia | almacén | clave ausente/inválida | VERIFICADO EN FIXTURES |
| VM-31 | Archivos privados, regulares, no symlink | diseño VMess §7-8 | almacén | permisos/symlink tests | VERIFICADO PARA ALMACÉN |
| VM-32 | Escritura atómica y concurrencia | diseño VMess §8 | almacén | publicación fallida y escritores concurrentes | VERIFICADO CON LIMITACIÓN |
| VM-33 | Rollback transaccional del almacén VMess | diseño VMess §8 | no implementado; huérfanos detectables | fallo inyectado deja huérfanos; catálogo intacto | NO APLICABLE / LIMITACIÓN DOCUMENTADA |
| VM-34 | Lectura/recuperación y revalidación Xray | diseño VMess §8 | asistente restore/store read | recuperación TLS/REALITY y Xray test | VERIFICADO EN FIXTURES |
| VM-35 | Coherencia revisión de catálogo ↔ referencia ↔ schema | diseño de persistencia versionada y decisión correctiva autorizada | store/read/audit validan revisión, schema y referencia de secreto | pruebas de revision/schema catálogo/documento/secreto y metadatos parciales | VERIFICADO EN FIXTURES |
| VM-36 | Audit de refs rotas, huérfanos, symlinks y metadatos versionados | diseño VMess §8 | acción audit | refs rotas, huérfanos, symlinks, revisiones/schema incoherentes; sin borrado automático | VERIFICADO EN FIXTURES |
| VM-37 | Lista numerada, selección y detalle | Etapa 2 §5.2 | `connections_manage_existing` | `stage2_existing.sh` / suite | VERIFICADO |
| VM-38 | Lista vacía informativa y [0] volver | Etapa 2 §5.3-6 | `connections_manage_existing` | `vmess_navigation_edge_cases.sh`: mensaje, [0] y catálogo intacto | VERIFICADO EN FIXTURES |
| VM-39 | Navegación [0], entradas inválidas y errores recuperables | Etapa 2 §6 | menú/administrador | `vmess_navigation_edge_cases.sh`: entradas inválidas en lista/administrador, recuperación y retorno sin cambios | VERIFICADO EN FIXTURES |
| VM-40 | Confirmación de acción destructiva | Etapa 2 §6 | eliminación de borrador | `vmess_navigation_edge_cases.sh`: frase incorrecta cancela; `ELIMINAR` exacto elimina | VERIFICADO EN FIXTURES |
| VM-41 | Preservar VMess en restauración VLESS | autorización específica y P4 §9 | `vless_backup.py` | `vless_restore_preserves_vmess.sh` | VERIFICADO |
| VM-42 | Backup/restore VMess independiente | fuera del alcance aprobado | no implementado | no aplica | NO APLICABLE — requiere diseño/autorización |
| VM-43 | Identidades globales y asociaciones | Etapa 3 | usuarios VMess manuales | no corresponde a Etapa 2 | NO APLICABLE — Etapa 3 |
| VM-44 | Carga de módulos y rutas | integración del manager | `bin/xray-manager`, `config/paths.sh` | revisión de integración, suite | VERIFICADO |
| VM-45 | Desinstalación del almacén VMess | ciclo de vida del manager | `modules/uninstall.sh` | `tests/uninstall.sh` | VERIFICADO |
| VM-46 | Estado live, clave maestra y almacenamiento real | validación operativa | VPS de desarrollo | primer store TLS, clave compartida, permisos, read/restore, auditoría, alteración GCM y limpieza | VERIFICADO LIVE (F-05) |
| VM-47 | Conectividad cliente-servidor | diseño VMess §8 | modelo/adaptador real + Xray cliente/servidor | VMess-TLS loopback; solicitud HTTP a destino y respuesta exacta | VERIFICADO — loopback local; WAN/cliente externo no verificado |
| VM-48 | Aceptación formal del propietario | regla de cierre | pendiente | no existe aceptación formal | PENDIENTE DE DECISIÓN |

## Notas de interpretación

- VERIFICADO EN FIXTURES no significa que se haya creado o usado el almacén real de la VPS.
- La validación `xray run -test` no equivale a interoperabilidad ni conectividad extremo a extremo.
- La limitación de rollback transaccional está documentada y no debe describirse como función implementada.
- VM-42 y VM-43 permanecen fuera del alcance actual.
- La Etapa 2 sigue ABIERTA; esta matriz sólo cubre VMess y sus integraciones directas. F-01 a F-05 están corregidos/verificados; VM-38/39/40 se verificaron con pruebas focales. VM-46 quedó VERIFICADO LIVE; VM-47 quedó VERIFICADO en loopback local (sin cliente externo/WAN); VM-48 requiere aceptación formal.


## Revalidación controlada en VPS de desarrollo — 2026-11-02

Se agregó `tests/vmess_navigation_edge_cases.sh`: VM-38 lista vacía y `[0]`; VM-39 entradas inválidas recuperables en lista y administrador; VM-40 cancelación con confirmación incorrecta y eliminación sólo con `ELIMINAR`. Los tres casos pasaron. La suite completa `tests/*.sh` pasó 40/40. F-05 live continúa NO VERIFICADO porque no se inicializaron `/etc/xray-manager/keys/master.key` ni el almacén real VMess.


## Validación live F-05 — 2026-11-02

Primer guardado TLS real, clave maestra compartida, permisos, lectura/descifrado, recuperador asistido, validación Xray, detección de alteración GCM y auditoría antes/después de limpieza: PASS. El catálogo quedó vacío y sólo permanecen la clave maestra `root:root 0600` y los directorios VMess vacíos `root:root 0700`. VM-47 conectividad cliente-servidor sigue NO VERIFICADA. Evidencia detallada: `docs/VALIDACION_LIVE_VMESS_F05_2026-11-02.md`.


## Validación cliente-servidor VM-47 — 2026-11-02

VM-47 se verificó con dos procesos Xray 26.10.31 en loopback. El modelo y adaptador reales generaron el servidor `vmess_tcp_tls` (`settings.users`); el cliente SOCKS estableció VMess-TLS y una solicitud HTTP llegó al servicio destino, que respondió HTTP 200 con el marcador exacto `VMESS-VM47-END-TO-END-OK`. Configuraciones cliente/servidor pasaron `xray run -test`. Los procesos y listeners temporales fueron detenidos. No se tocó servicio, firewall, runtime, puertos públicos ni catálogo. Alcance limitado a loopback: cliente externo/WAN no probado. Informe: `docs/VALIDACION_CLIENTE_SERVIDOR_VMESS_VM47_2026-11-02.md`.
