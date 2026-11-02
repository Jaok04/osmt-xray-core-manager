# Auditoría técnica integral del módulo VMess

**Fecha:** 2026-11-02
**Proyecto:** Xray Core Manager
**Etapa:** 2 — Gestión de protocolos y conexiones
**Alcance de esta revisión:** módulo VMess y sus integraciones directas. Esta auditoría no certifica la Etapa 2 completa.
**Resultado actualizado:** **NO APTO PARA ACEPTACIÓN FORMAL** — F-01 a F-05 resueltos/verificados; VM-38/39/40 verificados; VM-47 verificado en loopback local. No se ha probado cliente externo/WAN. La aceptación formal de VMess permanece pendiente.

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
- HEAD de partida de la auditoría: df632aee5d8139c721b81a6d65f14d93f7676226. Commit correctivo: d2d33a32bdf5e21d1d35ad41d00bd0b116443cb7; referencias finales de continuidad sincronizadas en 0a39af5c2aa35bf853c05f3a864bcc362d86bf67.
- HEAD remoto de la rama autorizado al inicio: el mismo SHA que el HEAD de partida.
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
| Suite completa `tests/*.sh` | **39/39 PASS** |
| Matriz Xray VMess | **14/14 PASS** |
| Casos negativos Xray VMess | **16/16 PASS** |
| Navegación de 14 modalidades | PASS |
| Pruebas de asistente y persistencia VMess | PASS |
| Preservación de VMess durante restore VLESS | PASS |
| `bash -n` en scripts Bash | PASS |
| AST Python, 7 archivos | PASS |
| ShellCheck `-S warning` sobre archivos relevantes | PASS |
| `./install.sh --check` | PASS; no modificó el sistema |
| `git diff --check` | PASS |
| Política shfmt documentada en README | PASS en los cuatro archivos seleccionados por el proyecto |

La exploración adicional de `shfmt -d -i 4 -ci` sobre módulos VMess mostró diferencias de formato, pero esos módulos no forman parte de los cuatro archivos incluidos en la política concreta del README. No se considera un fallo del gate definido por el proyecto y no se reformateó ningún archivo. ShellCheck de los archivos modificados pasó; la invocación global señala el warning preexistente SC2174 en tests/vless_backup_restore.sh:7, archivo VLESS fuera del alcance y sin cambios.

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

## 5. Hallazgos y estado de corrección

### F-01 — La clave privada TLS puede ser legible por otros usuarios

**Estado:** RESUELTO — seguridad.
**Corrección:** el adaptador Xray y vmess_prepare_config.py exigen que la clave privada TLS sea archivo regular, propietario root:root, modo exacto 0600 y un solo enlace duro. Se mantiene rechazo de symlinks.
**Evidencia:** tests/xray_vmess_integration.sh rechaza modos 0644, 0640, 0400, grupo distinto de root y enlace duro adicional; ambos lectores aceptan 0600 root:root. Se volvió a ejecutar la matriz Xray.
**Resultado:** la clave 0644 que reproducía el hallazgo ya no es aceptada.

### F-02 — `read` y `audit` no verifican la coherencia de revisión/esquema del catálogo

**Estado:** RESUELTO — integridad/versionado.
**Corrección:** store, read y audit validan que vmess_configuration_revision coincida con la revisión de vmess_configuration_ref; que vmess_configuration_schema_version sea el esquema admitido y coincida con schema_version del documento; y que la referencia del secreto TLS/REALITY use la misma revisión. También se detectan metadatos parciales sin referencia de configuración.
**Evidencia:** tests/vmess_persistence_hardening.sh fuerza incoherencias de revisión de catálogo, schema de catálogo, schema de documento, revisión de secreto y metadatos parciales. read falla de forma cerrada; audit reporta la entrada como rota; store rechaza continuar desde metadatos incoherentes.

### F-03 — Cancelar el asistente deja persistido el registro base de conexión

**Estado:** RESUELTO — flujo de creación.
**Decisión autorizada:** cancelar o fallar antes de guardar debe dejar el catálogo como estaba antes de iniciar la creación, salvo cambios concurrentes ajenos al intento.
**Corrección:** el asistente devuelve estado no exitoso cuando se rechaza el consentimiento o se alcanza EOF. El flujo común retira el registro creado sólo si sigue siendo un borrador VMess no aplicado y no contiene referencias/metadatos VMess. La limpieza usa el bloqueo compartido y una actualización atómica; no elimina borradores que ya tengan configuración publicada.
**Evidencia:** tests/vmess_assistant.sh comprueba el estado de cancelación y catálogo intacto. El nuevo tests/vmess_creation_flow.sh comprueba cancelación, fallo previo al guardado, preservación de otras conexiones y protección de un borrador que ya tiene referencias VMess.

### F-04 — Validación de email duplicado inconsistente entre modelo y almacén

**Estado:** RESUELTO — validación.
**Corrección:** modelo, adaptador y almacén rechazan emails duplicados con la misma comparación exacta y sensible a mayúsculas/minúsculas.
**Evidencia:** tests/vmess_model.sh y tests/vmess_assistant.sh rechazan emails repetidos con UUID diferentes antes del resumen/consentimiento; tests/xray_vmess_integration.sh demuestra que el adaptador también rechaza un modelo suministrado directamente con emails duplicados.

### F-05 — No existe validación operativa VMess en el estado live de la VPS

**Estado inicial de auditoría:** NO VERIFICADO. **Estado vigente tras autorización y prueba del 2026-11-02:** RESUELTO — VERIFICADO LIVE.
**Evidencia vigente:** primer guardado real de `vmess_tcp_tls` con clave TLS temporal, inicialización de la clave maestra compartida y almacén VMess, permisos `root:root 0600/0700`, lectura/descifrado autenticado, recuperación con el asistente y validación Xray 26.10.31. La auditoría no encontró referencias rotas, huérfanos ni entradas inseguras. Alterar el ciphertext GCM hizo fallar la lectura sin producir plaintext.
**Limpieza:** el borrador y sus dos archivos versionados fueron retirados; el catálogo volvió a quedar vacío. Se conservaron la clave maestra compartida y los directorios VMess vacíos como estado inicial persistente intencional.
**Límites:** no se activó runtime ni se desplegaron certificados. VM-47 se verificó posteriormente en loopback local; no se ha probado cliente externo/WAN. Evidencias en `docs/VALIDACION_LIVE_VMESS_F05_2026-11-02.md` y `docs/VALIDACION_CLIENTE_SERVIDOR_VMESS_VM47_2026-11-02.md`.
**Siguiente validación:** revisión de evidencias y aceptación formal del propietario; cliente externo/WAN sólo si se decide ampliar el alcance.

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
- La conectividad cliente-servidor VMess-TLS se verificó en loopback local; cliente externo/WAN no probado.

## 2026-11-02 — Bloque correctivo autorizado F-01 a F-04

Se aplicaron exclusivamente las correcciones autorizadas por el propietario. Archivos de producción afectados: modules/vmess_xray_26_10_31.sh, modules/vmess_assistant.sh, modules/vmess_model.sh, modules/connections.sh, scripts/vmess_prepare_config.py y scripts/vmess_config_store.py. Pruebas ampliadas: tests/xray_vmess_integration.sh, tests/vmess_model.sh, tests/vmess_assistant.sh, tests/vmess_persistence_hardening.sh; nueva tests/vmess_creation_flow.sh.

- F-01: root:root 0600, un solo enlace duro, validado en adaptador y preparador.
- F-02: metadatos de revisión/schema y referencias verificadas en store/read/audit.
- F-03: cancelación/fallo retira sólo el borrador base VMess vacío y no aplicado; preserva conexiones ajenas y configuraciones ya publicadas.
- F-04: email único en modelo, adaptador y almacén.

Resultado posterior: suite 39/39 PASS; Xray 14/14 modalidades y 16/16 casos negativos PASS. bash -n, py_compile, ShellCheck de archivos modificados, install.sh --check, gate shfmt de README y git diff --check PASS. Una ejecución ShellCheck global detectó únicamente el warning preexistente SC2174 en tests/vless_backup_restore.sh:7, fuera del alcance y sin modificaciones.

No se creó almacén/clave maestra live; no se modificó runtime, firewall, puertos ni servicio. F-05 permanece NO VERIFICADO. VMess no está aceptado y Etapa 2 sigue ABIERTA.

## 7. Estado consolidado

| Dimensión | Estado al 2026-11-02 |
|---|---|
| Diseño | APROBADO |
| Código base | IMPLEMENTADO |
| Compatibilidad estática Xray | VERIFICADA 14/14 |
| Suite de regresión | VERIFICADA 40/40 (revalidación controlada 2026-11-02) |
| Auditoría integral del módulo | F-01 a F-05 RESUELTOS/VERIFICADOS; VM-47 VERIFICADO en loopback; cliente externo/WAN pendiente; otros límites en matriz |
| Documentación de auditoría | DOCUMENTADA en este expediente y matriz |
| Publicación | Bloque correctivo, prueba de navegación y validación live documentados en la rama autorizada; sincronización de este expediente en el commit que lo contiene |
| Sincronización | VPS/local/remoto en rama `design/user-identity-association-v1`; esta actualización se publica junto con el expediente |
| Aceptación formal del propietario | PENDIENTE |

**Conclusión vigente:** F-01 a F-05 están resueltos/verificados; VM-38/39/40 pasaron pruebas focales y la suite completa pasó 40/40; VM-47 demostró tráfico cliente-servidor VMess-TLS real en loopback usando el modelo y adaptador del proyecto. No se probó un cliente en otra máquina ni conectividad WAN. VMess todavía NO está ACEPTADO formalmente: falta la aceptación expresa del propietario. La Etapa 2 continúa ABIERTA por VMess y por los demás protocolos y opciones aún no implementados/auditados.

## 8. Siguiente paso permitido

F-05/VM-46 y VM-47 (loopback local) están verificados. Revisar `docs/VALIDACION_CLIENTE_SERVIDOR_VMESS_VM47_2026-11-02.md` y decidir si el alcance local es suficiente para la aceptación formal o si se requiere una prueba adicional desde un cliente externo. Esa prueba externa requeriría autorización y preparación de red separadas. No activar runtime, tocar puertos/firewall/servicio ni iniciar Trojan sin autorización específica y aceptación formal de VMess.


## 2026-11-02 — Revalidación controlada en VPS de desarrollo

El propietario autorizó usar la VPS de desarrollo para pruebas controladas. Se verificó el acceso root y que el repositorio estaba en `design/user-identity-association-v1`, HEAD `4c87557e0aff4166c540c633effe5cb6dac40096`, sin cambios versionados pendientes. Xray no está instalado en esa VPS y el servicio permanece inactivo; las pruebas de integración utilizaron el binario de validación Xray 26.10.31 disponible en caché.

Se añadió `tests/vmess_navigation_edge_cases.sh`: VM-38 lista vacía y `[0]`; VM-39 entradas inválidas recuperables en lista y administrador; VM-40 cancelación y confirmación destructiva exacta. Los tres casos pasaron. La suite completa `tests/*.sh` pasó 40/40, incluidas colisiones TCP/UDP; la primera ejecución de `port_collisions.sh` falló transitoriamente en la comprobación UDP, pero su repetición aislada y la suite completa posterior pasaron.

No se inicializó `/etc/xray-manager/keys/master.key`, no se creó `/var/lib/xray-manager/vmess`, no se añadió conexión live y no se modificó runtime, firewall, puertos ni servicio. F-05 sigue NO VERIFICADO; VM-47 conectividad cliente-servidor sigue NO VERIFICADO. VMess no está aceptado y Etapa 2 permanece ABIERTA.


## Revalidación live F-05 — 2026-11-02

La prueba live autorizada quedó completada. Se creó y conservó la clave maestra compartida y el almacén VMess; se guardó un borrador TLS real de prueba, se recuperó y descifró, el asistente lo reconstruyó y Xray 26.10.31 lo validó. Auditoría limpia; ciphertext GCM alterado rechazado sin plaintext. El borrador y sus archivos versionados se retiraron, el catálogo volvió a quedar vacío y se conservaron únicamente clave maestra y directorios VMess vacíos. Servicio Xray inactivo, puerto de prueba sin escucha, sin cambios de runtime/firewall/puertos/servicios. F-05/VM-46: VERIFICADO LIVE. VM-47 conectividad cliente-servidor: NO VERIFICADO. Ver `docs/VALIDACION_LIVE_VMESS_F05_2026-11-02.md`.


## Validación cliente-servidor VM-47 — 2026-11-02

VM-47 quedó VERIFICADO en loopback local. El modelo y adaptador reales generaron el servidor VMess-TLS (`settings.users`); dos procesos Xray 26.10.31 establecieron el túnel TLS/VMess y transportaron una solicitud HTTP desde el SOCKS cliente hasta el servicio destino. El destino respondió HTTP 200 con el marcador exacto esperado. Ambos `xray run -test` pasaron. La prueba usó listeners sólo en `127.0.0.1`, un certificado efímero fijado por SHA-256 y una excepción `freedom.finalRules` temporal restringida a TCP/127.0.0.1/18080. Los procesos se detuvieron y los listeners se cerraron. No se modificaron runtime, firewall, puertos públicos, catálogo ni servicio del sistema. No se probó cliente externo/WAN. Informe reproducible: `docs/VALIDACION_CLIENTE_SERVIDOR_VMESS_VM47_2026-11-02.md`.
