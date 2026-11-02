# Auditoría técnica integral del módulo VMess

**Fecha:** 2026-11-02
**Proyecto:** Xray Core Manager
**Etapa:** 2 — Gestión de protocolos y conexiones
**Alcance de esta revisión:** módulo VMess y sus integraciones directas. Esta auditoría no certifica la Etapa 2 completa.
**Resultado:** **NO APTO PARA ACEPTACIÓN FORMAL** — existen brechas de seguridad, integridad y flujo que requieren corrección o decisión expresa.

## 1. Línea base y autoridad

Se consultaron directamente en la VPS:

- `/root/Xray_Manager_Documentacion_Final_2026-10-31/00_Indice_General.md`
- `/root/Xray_Manager_Documentacion_Final_2026-10-31/02_Protocolos_Conexiones/Etapa_2_Protocolos.md` — revisión 1.3.
- `/root/Xray_Manager_Documentacion_Final_2026-10-31/02_Protocolos_Conexiones/Etapa_2_Protocolos.yaml`.
- `/root/Xray_Manager_Documentacion_Final_2026-10-31/07_Auditoria_Tecnica_Final.md`.
- `AGENTS.md`.
- `docs/REGLA_CONTRASTE_DOCUMENTACION_PRELIMINAR.md`.
- `docs/REGLA_AUDITORIA_INTEGRAL_CIERRE_ETAPAS.md`.
- `docs/DISEÑO_TECNICO_VMESS.md` y `docs/DECISIONES_ETAPA_2.md`.

La especificación normativa Etapa 2 revisión 1.3 clasifica VMess en cinco modalidades principales y tres adicionales. El diseño complementario aprobado concreta 14 combinaciones de transporte/seguridad. HTTPUpgrade-TLS se conserva como decisión complementaria aprobada; no se reescribe retroactivamente la especificación normativa.

La especificación YAML usa el identificador `vmess_tls`; el catálogo/implementación usa `vmess_tcp_tls` para RAW/TCP + TLS. La equivalencia se mantiene documentada y no se cambió ningún ID.

## 2. Entorno y sincronización

- VPS: `/opt/xray-manager`.
- Rama autorizada: `design/user-identity-association-v1`.
- HEAD local: `df632aee5d8139c721b81a6d65f14d93f7676226`.
- HEAD remoto de la rama autorizado, consultado con `git ls-remote`: el mismo SHA.
- HEAD remoto de `main`: `656ecedc506a94a6461aee296b20871d51a38bf3`; no se modificó.
- Árbol de trabajo: único elemento sin seguimiento `scripts/__pycache__/`, preexistente al inicio de esta auditoría. No se eliminó ni se incorporó.
- Los hashes Git de los archivos principales VMess y de continuidad contrastados coinciden con los blobs recuperados de la rama autorizada.

## 3. Inventario auditado

Componentes revisados:

- Menú, resolución de modalidades y listados: `modules/connections.sh`.
- Modelo neutral: `modules/vmess_model.sh`.
- Asistente y recuperación: `modules/vmess_assistant.sh`.
- Adaptador Xray: `modules/vmess_xray_26_10_31.sh`.
- Preparación segura: `scripts/vmess_prepare_config.py`.
- Persistencia cifrada/versionada: `scripts/vmess_config_store.py`.
- Carga de módulos: `bin/xray-manager`.
- Rutas: `config/paths.sh`.
- Desinstalación: `modules/uninstall.sh`.
- Pruebas: `tests/stage2_navigation.sh`, `tests/vmess_model.sh`, `tests/vmess_assistant.sh`, `tests/xray_vmess_integration.sh`, `tests/vmess_persistence_hardening.sh`, `tests/vmess_vless_backup_isolation.sh`, `tests/vless_restore_preserves_vmess.sh` y suite general.
- Documentación técnica, decisiones, continuidad, historial y punto de control.

La matriz exhaustiva requisito → diseño → implementación → prueba → evidencia se encuentra en `docs/MATRIZ_TRAZABILIDAD_VMESS_2026-11-02.md`.

## 4. Resultados de pruebas ejecutadas en esta auditoría

<small>Entorno: VPS de desarrollo Ubuntu 24.04.4 LTS; Xray-core v26.10.31, build `a4a3dff`; fixtures y directorios temporales para los casos aislados.</small>

| Comprobación | Resultado |
|---|---|
| Suite completa `tests/*.sh` | **38/38 PASS** |
| Matriz Xray VMess | **14/14 PASS** |
| Casos negativos Xray VMess | **10/10 PASS** |
| Navegación de 14 modalidades | PASS |
| Pruebas de asistente y persistencia VMess | PASS |
| Preservación de VMess durante restore VLESS | PASS |
| `bash -n` en scripts Bash | PASS |
| AST Python, 7 archivos | PASS |
| ShellCheck `-S warning` sobre archivos relevantes | PASS |
| `./install.sh --check` | PASS; no modificó el sistema |
| `git diff --check` | PASS |
| Política shfmt documentada en README | PASS en los cuatro archivos seleccionados por el proyecto |

La exploración adicional de `shfmt -d -i 4 -ci` sobre módulos VMess mostró diferencias de formato, pero esos módulos no forman parte de los cuatro archivos incluidos en la política concreta del README. No se considera un fallo del gate definido por el proyecto y no se reformateó ningún archivo.

### 4.1 Cobertura positiva Xray

Xray-core 26.10.31 aceptó:

1. `vmess_ws`
2. `vmess_tcp_tls`
3. `vmess_ws_tls`
4. `vmess_reality`
5. `vmess_grpc`
6. `vmess_grpc_tls`
7. `vmess_grpc_reality`
8. `vmess_httpupgrade`
9. `vmess_httpupgrade_tls`
10. `vmess_xhttp`
11. `vmess_xhttp_tls`
12. `vmess_xhttp_reality`
13. `vmess_mkcp`
14. `vmess_mkcp_tls`

### 4.2 Cobertura negativa Xray

Se rechazaron TLS sin clave, symlink de clave TLS, certificado PEM inválido, certificado/clave no coincidentes, REALITY sin clave, short ID inválido, clave REALITY inválida, campos TLS en modalidad sin TLS, campo de transporte desconocido y combinación modelo/seguridad inconsistente.

Estas pruebas demuestran validación de configuración, no conectividad extremo a extremo.

## 5. Hallazgos que bloquean aceptación

### F-01 — La clave privada TLS puede ser legible por otros usuarios

**Estado:** INCOMPLETO — seguridad.
**Evidencia:** se creó una clave TLS de prueba root:root con modo `0644`. `vmess_xray_26_10_31_build` la aceptó. El adaptador comprueba archivo regular, lectura y ausencia de symlink, pero no restringe lectura por grupo/otros. `vmess_prepare_config.py` rechaza escritura por grupo/otros, pero también permite lectura por grupo/otros.
**Impacto:** una clave privada TLS root-owned con permisos `0644` sigue expuesta a otros usuarios locales.
**Corrección propuesta:** exigir permisos privados explícitos, preferiblemente root:root `0600`, en todos los puntos que leen la clave; añadir pruebas negativas para `0644`, `0640` y otros modos no autorizados.
**Autorización:** no se modificó código.

### F-02 — `read` y `audit` no verifican la coherencia de revisión/esquema del catálogo

**Estado:** INCOMPLETO — integridad/versionado.
**Evidencia:** en un almacén temporal válido se cambió `vmess_configuration_revision` y `vmess_configuration_schema_version` a `99`, manteniendo la referencia a `r000001` y el archivo con `schema_version: 1`. Tanto `audit` como `read` terminaron correctamente y no señalaron la inconsistencia.
**Impacto:** metadatos de revisión/esquema del catálogo pueden contradecir el archivo realmente recuperado sin que el almacén lo detecte.
**Corrección propuesta:** comparar revisión de la referencia, `vmess_configuration_revision`, `vmess_configuration_schema_version` y `schema_version` del documento durante `read` y `audit`; añadir casos negativos.
**Autorización:** no se modificó código.

### F-03 — Cancelar el asistente deja persistido el registro base de conexión

**Estado:** INCOMPLETO / PENDIENTE DE DECISIÓN sobre la semántica exacta de cancelación.
**Evidencia:** `connections_create_draft` publica primero el registro `draft` en el catálogo y después invoca `connections_vmess_assistant`. Se reprodujo el flujo en un catálogo temporal con el asistente cancelado: queda el registro `draft`, sin `vmess_configuration_ref`. Las pruebas actuales de `vmess_assistant.sh` llaman directamente al asistente y comprueban que éste no modifica el catálogo, pero no cubren el flujo común completo.
**Impacto:** la afirmación «cancelar no persiste» es cierta para la configuración VMess, pero no para el registro base creado por el flujo común.
**Decisión requerida:** confirmar si cancelar debe eliminar también el registro base y dejar el catálogo exactamente igual, o si se acepta conservar un borrador vacío identificable. La especificación común pide validar parámetros antes de guardar; el plan correctivo aprobado mencionó cancelación sin persistencia.
**Autorización:** no se modificó código.

### F-04 — Validación de email duplicado inconsistente entre modelo y almacén

**Estado:** INCOMPLETO — validación.
**Evidencia:** `vmess_model_validate_users` acepta dos usuarios con UUID diferentes y el mismo email. `vmess_config_store.validate_users` rechaza ese mismo conjunto con «email VMess duplicado». Se reprodujo con datos temporales.
**Impacto:** la validación preliminar/modelo puede aceptar y presentar un conjunto que el almacén rechaza sólo después del consentimiento.
**Corrección propuesta:** unificar la regla de unicidad en modelo/asistente y almacén; añadir prueba negativa de email duplicado antes del resumen/consentimiento.
**Autorización:** no se modificó código.

### F-05 — No existe validación operativa VMess en el estado live de la VPS

**Estado:** NO VERIFICADO — operación real.
**Evidencia:** el catálogo live de conexiones está vacío; `/var/lib/xray-manager/vmess/` no existe y la clave maestra `/etc/xray-manager/keys/master.key` tampoco existe. Las pruebas se ejecutaron con fixtures temporales.
**Impacto:** no hay evidencia de primer guardado real, inicialización del almacén VMess, permisos reales, recuperación de una configuración guardada en live ni uso real de la clave maestra.
**Límite:** no se creó el almacén ni la clave maestra porque eso sería una operación persistente no necesaria para esta auditoría.
**Siguiente validación:** requiere autorización y una conexión de prueba en un entorno controlado.

## 6. Elementos conformes y límites explícitos

- Las 14 combinaciones se resuelven en el menú/modelo/adaptador y pasan `xray run -test`.
- Se conservan VMess-WS sin TLS adicional y VMess-TLS RAW/TCP + TLS con etiquetas visibles inequívocas.
- Se usa `settings.users`, UUID, `level`, `email`, `alterId: 0` y `security: auto`.
- El asistente muestra el requisito de sincronización horaria (máximo 120 segundos), las advertencias de WebSocket/HTTPUpgrade y el resumen previo al consentimiento.
- El contenido de claves privadas TLS/REALITY no se imprime en el resumen.
- El almacén separa configuraciones y secretos; usa AES-256-GCM y AAD VMess específico; aplica permisos privados a los archivos persistidos; serializa escritores; detecta referencias rotas, huérfanos y symlinks; no elimina huérfanos automáticamente.
- El fallo de publicación del catálogo puede dejar archivos huérfanos detectables. No existe rollback transaccional VMess y esa limitación está documentada; no se presenta como funcionalidad disponible.
- La restauración VLESS conserva entradas VMess actuales y no incorpora el almacén VMess al backup VLESS.
- Carga, rutas y desinstalación contemplan los componentes/rutas VMess.
- No se activa runtime, no se abren puertos ni se modifica firewall/servicio.
- Usuarios VMess manuales e integración con identidades globales pertenecen a Etapa 3.
- Backup/restore VMess independiente está fuera del alcance aprobado y requiere diseño/autorización separados.
- No hubo conectividad cliente-servidor real.

## 7. Estado consolidado

| Dimensión | Estado al 2026-11-02 |
|---|---|
| Diseño | APROBADO |
| Código base | IMPLEMENTADO |
| Compatibilidad estática Xray | VERIFICADA 14/14 |
| Suite de regresión | VERIFICADA 38/38 |
| Auditoría integral del módulo | INCOMPLETA — F-01 a F-05 |
| Documentación de auditoría | DOCUMENTADA en este expediente y matriz |
| Publicación | La base previa y este expediente forman parte del paquete documental que se publica en la rama autorizada |
| Sincronización | HEAD VPS/remoto coincidente antes de este expediente |
| Aceptación formal del propietario | PENDIENTE |

**Conclusión:** no declarar VMess ACEPTADO ni cerrar la Etapa 2. Los cuatro primeros hallazgos requieren corrección/decisión y repetición de pruebas. La validación operativa live permanece no verificada. La Etapa 2 continúa ABIERTA por VMess y por los demás protocolos y opciones aún no implementados/auditados.

## 8. Siguiente paso permitido

Presentar al propietario F-01 a F-04 para autorización de corrección y decisión de cancelación. No cambiar código, no crear almacén/clave real, no activar runtime, no tocar puertos/firewall/servicio y no iniciar Trojan sin la autorización y aceptación formal correspondientes.
