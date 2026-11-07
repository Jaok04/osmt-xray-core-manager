# Xray Core Manager — Estado del proyecto

> Los registros cronológicos posteriores describen el estado que existía en su fecha; cualquier estado anterior que contradiga el bloque «Estado vigente — corte 2026-11-06» al inicio de este documento está SUPERADO y se conserva sólo por trazabilidad.

**Corte de estado vigente:** 2026-11-06 — H6-G3-A/B/C/D implementadas en fixtures; segunda pasada PASS CON LIMITACIONES (misma sesión, no independiente). H6-G2 F-01/F-02/F-03 corregidos/implementados; F-04/F-05 pendientes y backend live no conectado. Instalador autónomo con bootstrap GitHub aprobado, implementado y verificado en pruebas automatizadas; PAT/VPS limpia real pendiente. Rama design/user-identity-association-v1. HEAD base antes de esta implementación: `b00314c931b06829548d3096b9fce740e1bbb216`; cambios locales pendientes de publicación en esta fotografía.
**Estado global:** Etapa 1 aceptada; Etapas 2–6 abiertas/parciales. H6-G2 NO CERRADO; H6-G3 no tiene auditoría independiente. H6-F NO LISTO END-TO-END. Backend runtime live no integrado; no ejecutar acciones live sin autorización específica.
**Repositorio:** https://github.com/Jaok04/xray-core-manager
**Rama autorizada:** design/user-identity-association-v1
**VPS de desarrollo:** /opt/xray-manager

> Este documento es una fotografía de estado, no sustituye la documentación normativa. Antes de actuar, verifica el HEAD actual de GitHub y vuelve a inspeccionar la VPS.

> **Regla obligatoria permanente:** antes de implementar cualquier etapa o funcionalidad, contrastar el proyecto con la documentación preliminar aprobada en `Xray-Normativa/` del repositorio (respaldo original en `/root/Xray_Manager_Documentacion_Final_2026-10-31`). Las mejoras requieren informe previo y autorización expresa del propietario. Ver `docs/REGLA_CONTRASTE_DOCUMENTACION_PRELIMINAR.md` y `AGENTS.md`.

> **Segunda regla obligatoria permanente:** ninguna etapa se declara TERMINADA/COMPLETADA sin auditoría integral y documentación técnica de todos sus puntos, subpuntos, módulos, submódulos y componentes internos, matriz de trazabilidad, pruebas y aceptación formal expresa. Cerrar un módulo no cierra su etapa. Ver `docs/REGLA_AUDITORIA_INTEGRAL_CIERRE_ETAPAS.md` y `AGENTS.md`.



## Actualización vigente — instalador autónomo con GitHub privado (2026-11-06)

- El propietario aprobó implementar un instalador de un solo archivo, autenticación Fine-grained PAT read-only y descarga del árbol completo sin clonar Git.
- `install.sh` ahora detecta si sólo se dispone del archivo aislado. En ese caso autentica GitHub API, fija el commit de `design/user-identity-association-v1`, verifica el helper con SHA-256 fijado y descarga el tarball por SHA inmutable.
- `scripts/installer_bootstrap.py` verifica cada blob Git, tamaño y modo; rechaza árboles truncados, rutas traversal, symlinks, hardlinks, submódulos, duplicados, archivos extra/faltantes y modos no admitidos. No instala `.git` ni historial.
- PAT limitado a `Jaok04/xray-core-manager`, `Contents: Read-only`; entrada oculta o `XRAY_MANAGER_GITHUB_TOKEN`. No se guarda en disco, URLs, argumentos ni logs.
- Procedimiento de primer bootstrap: `docs/INSTALACION_DESDE_VPS_LIMPIA.md`. `--install` sigue Manager-only; `--install --with-xray` sigue siendo explícito.
- Pruebas actuales: bootstrap focal 18/18; Python global 406/406; Bash 62/62; ShellCheck `-S error`, `compileall`, `bash -n`, `install.sh --check` y `git diff --check` PASS. Extractor contra `git archive` local: 330/330 archivos verificados.
- **Límite:** no se ha ejecutado GitHub API con el PAT real ni el bootstrap de un solo archivo en la VPS nueva. Validación live pendiente del propietario. No se instaló Manager/Xray en esa VPS y no se tocó runtime, DNS, firewall, puertos, certificados o red.
- HEAD base antes de esta implementación: `b00314c931b06829548d3096b9fce740e1bbb216`; cambios locales aún no publicados en esta fotografía. `main` y `Xray-Normativa/` intactas.
- Documentos: `docs/DECISION_INSTALADOR_AUTODESCARGA_GITHUB_2026-11-06.md`, `docs/IMPLEMENTACION_INSTALADOR_AUTODESCARGA_GITHUB_2026-11-06.md` y `docs/AUDITORIA_INSTALADOR_AUTODESCARGA_GITHUB_2026-11-06.md`.

## Estado vigente — corte 2026-11-06

## Actualización de ejecución — H6-G2 F-01 (2026-11-06)

## Actualización de ejecución — H6-G2 F-02 (2026-11-06)

- Diseñado contrato de evidencia operation_id -> generation_id -> validation_id/profile/revision/content hash -> staging/lease -> publicación -> hash de bytes runtime.
- Nuevo `scripts/xray_runtime_operation_evidence.py`: valida journal schema 2, generación, estado publicado, rollback no iniciado, manifiesto/staging, informe persistido y checks obligatorios, hash de binario, destino y bytes runtime. Lectura del historial read-only.
- Backend live ya no admite hash libre; requiere operation_id/generation_id y lector verificado. Exige entorno `live`; rechaza evidencia `fixture`. El lector actual declara `environment=fixture` porque el journal R-03/R-05 sigue aislado.
- Pruebas: backend 20/20, lector 9/9, Python 370/370, Bash 62/62, validaciones estáticas PASS.
- F-02: contrato/implementación fixture PASS; evidencia live PENDIENTE de evolución G3. No conectar R-05 ni menú.
- Evidencia: `docs/DECISION_H6G2_F02_EVIDENCIA_OPERACION_GENERACION_2026-11-06.md` y `docs/IMPLEMENTACION_H6G2_F02_EVIDENCIA_OPERACION_2026-11-06.md`. Sin acciones live ni commit/push.


- Corregido `scripts/xray_runtime_live_backend.py`: `inactive` rechaza PID residual e InvocationID; `active` exige PID entero >1, InvocationID hexadecimal de 32 caracteres, `sub_state=running` y `result=success`.
- Pruebas adversariales añadidas: 17/17 focales PASS; Python global 358/358; Bash 62/62; py_compile, bash -n focal, ShellCheck -S error y git diff --check PASS.
- F-01: CORREGIDO Y VERIFICADO EN FIXTURES. H6-G2 NO CERRADO; F-02/F-03 siguen bloqueando integración y F-04/F-05 siguen pendientes para G3. Backend live continúa desconectado de R-05/menú.
- Solo desarrollo `/opt/xray-manager`; no systemctl/Xray real, runtime, certificados, DNS, firewall, puertos ni red. Sin commit/push; `main` y `Xray-Normativa/` intactas.
- Evidencia: `docs/IMPLEMENTACION_H6G2_F01_VALIDACION_ESTADOS_2026-11-06.md`.


- Rama autorizada: design/user-identity-association-v1. Base local/remota previa a esta actualización: 32496d749901d34cd1a60f720843901125b536b6.
- H6-E1: contrato systemd read-only; H6-E2: identidad de proceso; H6-E3: correlación H6-A/H6-E2 y persistencia R-05/H6-B schema v2. Auditoría integral H6-E (H6-A/B/C/D/E1/E2/E3) PASS CON LIMITACIONES. Evidencia: docs/AUDITORIA_H6E_INTEGRAL_2026-11-06.md.
- H6-E4 corresponde a la auditoría integral del bloque y queda cubierta por el expediente anterior; no hay operaciones live.
- Instalador: install.sh --install instala sólo Manager; install.sh --install --with-xray conserva la instalación integral explícita. Xray-core puede instalarse después desde el menú.
- Regresión: Python 332/332; Bash 62/62; ShellCheck -S error, compileall, bash -n, install.sh --check y git diff --check PASS.
- H6-F: NO LISTO END-TO-END. Bloqueos: decisión/instalación autorizada de Certbot, endpoint público/Host/SNI confirmados, VPS de aceptación y backend runtime mutador con autorización live específica.
- No se modificaron main ni Xray-Normativa/; no se ejecutaron systemctl/Xray/Certbot reales, cambios DNS/firewall/puertos ni pruebas WAN. Manager-only sólo se probó con prefijos temporales.

## Estado vigente — B3 VLESS-WS-TLS (2026-11-05)

- B3 autorizada por el propietario solo con fixtures/pruebas aisladas.
- Añadida acción contextual en la conexión VLESS-WS-TLS draft: asociar identidad existente o crear identidad global y asociarla, reutilizando Usuarios V2 y UUID único global.
- Exportador NetMod exige validación Xray satisfactoria en el manifiesto de la revisión exacta.
- Exportador valida SAN del certificado central activo contra SNI configurado o dominio del endpoint cuando SNI está ausente; wildcard limitado a un nivel. Endpoint IP sin SNI DNS verificable falla cerrado.
- Integración compone perfil, ejecuta validador real con Xray 26.10.31 y exporta URI fixture hellen.tvrc.me:443.
- Python 186/186; Bash 61/61; py_compile/compileall, bash -n, ShellCheck -S error, git diff --check e install.sh --check PASS.
- B3: IMPLEMENTADA, VERIFICADA, AUDITADA, ACEPTADA FORMALMENTE, PUBLICADA y SINCRONIZADA el 2026-11-05 con las limitaciones de la auditoría. Commits funcional/documental: `aae4c15bf9b8f2c7c46c1e28a8a3881910ab71f4` / `9f4cc18d856ec0ccb31951f343a1fd3e870a0684`; HEAD local/upstream/remoto coincide y el árbol está limpio.
- No se ejecutó ACME real, NetMod real, WAN, runtime, systemd ni cambios de certificados persistentes, claves, DNS, firewall, puertos, red o dependencias. main y Xray-Normativa/ intactas. R-06/live NO AUTORIZADA.
- Evidencia: docs/DECISION_B3_VLESS_WS_TLS.md, docs/IMPLEMENTACION_B3_VLESS_WS_TLS_2026-11-05.md y docs/AUDITORIA_B3_VLESS_WS_TLS_2026-11-05.md.

## Estado vigente — I-04 exportación VLESS-WS-TLS (2026-11-05)

- Autorización expresa del propietario: exportar clientes VLESS-WS-TLS para NetMod con endpoint inicial hellen.tvrc.me:443; puerto público igual al puerto del inbound.
- Nuevo scripts/vless_client_export.py y opción [10] del menú de perfiles. Genera un URI vless:// por cliente UUID desde perfil/revisión exactos, mapping privado y configuración fuente validada.
- Host WebSocket y SNI cliente se recuperan independientemente; no se infieren del endpoint ni se confunden con el certificado TLS del servidor.
- Exportación estricta/fail-closed: mapping exacto, puerto coincidente, UUID válidos/no duplicados, config fuente coherente; salida opcional TXT 0600, atómica y sin sobrescritura.
- El lector de perfiles usa lock compartido sin ejecutar recuperación/limpieza del almacén. No se modifica configuración persistida.
- Pruebas I-04: 7/7 PASS; integración menú/compositor PASS; regresión Python 171/171, Bash 59/59; py_compile, bash -n global, ShellCheck focal, install.sh --check y git diff --check PASS.
- No se probó NetMod real ni conectividad WAN. No se verificó DNS, listener público, firewall, certificados desplegados ni runtime.
- I-02/I-03/I-04: IMPLEMENTADOS, VERIFICADOS y AUDITADOS en alcance focal; ACEPTACIÓN FORMAL PENDIENTE; NO PUBLICADOS; NO SINCRONIZADOS. Los cambios locales I-02/I-03 se preservan junto con I-04.
- No se modificó Xray-Normativa/, main, runtime/systemd, certificados reales, DNS, firewall, puertos, red, dependencias ni VPS de pruebas. R-06/live continúa NO AUTORIZADA.
- Documentos I-04: docs/DECISION_I04_VLESS_CLIENT_EXPORT.md, docs/IMPLEMENTACION_I04_VLESS_CLIENT_EXPORT_2026-11-05.md, docs/AUDITORIA_I04_VLESS_CLIENT_EXPORT_2026-11-05.md.

## Estado vigente — I-02 / I-03 VLESS-WS-TLS (2026-11-05)

- Rama autorizada: design/user-identity-association-v1; base publicada I-01: 792f382ca1b4f753ff763dc50a442aa66a0cd42f.
- I-02 añade [9] al menú de perfiles: selecciona perfil/revisión actual y conexión VLESS-WS-TLS draft/runtime_applied=false; previsualiza path, Host, SNI y certificado mediante VLESS Config Store; pide confirmación; crea revisión nueva pendiente, sin activar perfil ni invocar R-01–R-04.
- I-03 persiste transport_options.host y client_options.tls_server_name con esquema 2; esquema 1 sigue válido. El adaptador/compositor emite streamSettings.wsSettings.host; SNI permanece como metadata cliente y no se inyecta en inbound ni sustituye certificado servidor.
- Xray 26.10.31 validó VLESS-WS-TLS con y sin Host. Se descartó wsSettings.headers.Host por advertencia de obsolescencia; se usa wsSettings.host.
- Certificate Resolver y backup/restore aceptan esquema 2. Backup/restore conserva Host/SNI y referencia certificate_id sin duplicar claves privadas.
- Regresión completa final: Python 164/164, Bash 59/59, py_compile, bash -n global, ShellCheck -S error en todos los Bash modificados, git diff --check e install.sh --check PASS. ShellCheck global completo también había pasado en la ejecución previa.
- Exportación de URI/perfil VLESS para NetMod pendiente: requiere endpoint público explícito para la conexión. No se genera URI incompleto ni se asume dominio.
- I-02/I-03: IMPLEMENTADOS en alcance descrito; VERIFICADOS; AUDITADOS focalmente; ACEPTACIÓN FORMAL PENDIENTE; NO PUBLICADOS; NO SINCRONIZADOS.
- No se leyó clave maestra real ni se tocaron runtime Xray/systemd, certificados desplegados, firewall, puertos, DNS, red, dependencias, VPS de pruebas, main o Xray-Normativa/.

## Estado vigente — I-01 compositor VLESS-WS-TLS (2026-11-04)

- Rama autorizada: `design/user-identity-association-v1`; HEAD base verificado antes de I-01: `bf73fd6a15aa169379c7cd71d1ea9cf5fb13f8b1`.
- I-01 implementado en `scripts/vless_ws_tls_composer.py`; pruebas focales en `tests/test_vless_ws_tls_composer.py`.
- El propietario aprobó que el mapping TLS se guarde fuera del JSON del perfil, en un archivo privado vinculado por ruta a `profile_id` y `revision`, conservando exactamente el esquema R-02.
- Composición VLESS-WS-TLS con Usuarios V2, certificado central activo, revisión inmutable, mapping TLS compatible con el parser R-02, protección de revisión obsoleta y preservación de inbounds existentes.
- Pruebas focales: 11/11 PASS. Regresión completa: Python 163/163 y Bash 58/58 PASS; ShellCheck -S error, bash -n, py_compile, diff y install.sh --check PASS. Auditoría focal documentada.
- I-01: IMPLEMENTADO; VERIFICADO; AUDITADO en alcance focal; ACEPTADO formalmente el 2026-11-05 con limitaciones; publicación/sincronización pendientes de verificación.
- No se modificaron R-01–R-04 ni la normativa. No se ejecutó Xray/systemd real, no se activó perfil ni se tocó runtime. Solo fixtures, claves/certificados sintéticos y temporales.
- Auditoría: `docs/AUDITORIA_I01_COMPOSITOR_VLESS_WS_TLS_2026-11-04.md`. Publicación autorizada por separado el 2026-11-05, exclusivamente en la rama autorizada.
- R-05 permanece en pausa; R-06/live NO AUTORIZADA. Etapas 2, 3 y 5 ABIERTAS.


## Estado actualizado — formato cifrado compartido v1 (2026-11-03)

- `scripts/shared_backup_format.py` implementa un contenedor binario neutral, sin dependencias de protocolo: scrypt perfil fijo + AES-256-GCM, salt/nonce aleatorios y AAD de cabecera.
- `tests/shared_backup_format.sh` pasa pruebas de round-trip, aleatoriedad, autenticación, alteración, truncamiento, trailing bytes, parámetros/contraseña inválidos.
- `docs/FORMATO_CIFRADO_COMPARTIDO_V1.md` define el contrato; `docs/PLAN_BACKUP_RESTORE_CENTRAL.md` está en v1.2.
- La misma envoltura puede transportar snapshots de VLESS, VMess, Trojan y futuros protocolos mediante adaptadores separados. No se comparte la lógica de envelopes/AAD internos de cada protocolo.
- La normativa exige que credenciales/claves privadas estén excluidas por defecto; su inclusión futura requiere selección, autorización y confirmación adicional. Los historiales y logs quedan excluidos.
- Regresión actual `tests/*.sh`: 47/47 PASS; `py_compile`, `bash -n`, ShellCheck/shfmt focal y `git diff --check`: PASS.
- No existe todavía snapshot/orquestador, backup generado, verify, restore, journal o rollback compartido. Sin secretos en disco ni cambios runtime.

## Estado actualizado — integración VMess TLS centralizado (2026-11-03)

- Bloque 1 (catálogo/almacén) y Bloque 2 (resolutor) están publicados; sus límites están documentados en `docs/IMPLEMENTACION_ALMACEN_CERTIFICADOS_CENTRALIZADOS.md` y `docs/IMPLEMENTACION_RESOLUTOR_CERTIFICADOS_TLS.md`.
- Bloque 3 está PARCIAL: el store VMess y el preparador admiten `certificate_id` para nuevas configuraciones TLS; REALITY conserva secretos por conexión; las configuraciones TLS históricas siguen siendo legibles sin migración automática.
- Adaptación inicial del asistente VMess iniciada; generador Xray y cobertura integral de los flujos TLS aún pendientes. No afirmar integración completa ni validación runtime.
- Pruebas focales de persistencia VMess, backup/restore VLESS, almacén y resolutor PASS; no se ha ejecutado todavía la regresión global posterior al cambio.
- La VPS de desarrollo carece de unidad/cuenta/grupo Xray, por lo que el resolutor CLI falla cerrado y no se ha probado lectura de leases por el proceso Xray real.
- No se modificaron runtime, servicios, firewall, puertos, certificados desplegados, VPS de pruebas ni `Xray-Normativa/`.

## Estado actualizado — integración VLESS TLS centralizado (2026-11-03)

- `scripts/vless_config_store.py` guarda nuevas revisiones TLS con `security_options: {certificate_id}`; verifica que el recurso central exista y esté activo. No crea blob TLS por conexión.
- `scripts/vless_prepare_config.py` emite el contrato central. REALITY conserva su secreto individual cifrado.
- `modules/vless_xray_26_10_31.sh` exige lease autorizado para TLS y rechaza rutas libres. Nuevo `scripts/vless_tls_lease_check.py` valida manifest, conexión/protocolo, revisión, fingerprint, UID/GID y permisos.
- `modules/vless_assistant.sh` solicita ID central, persiste el borrador bajo confirmación, solicita lease, valida Xray si existe el binario y limpia el lease en éxito/fallo. La recuperación TLS central usa el resolutor; TLS histórico falla cerrado hasta migración controlada.
- `scripts/vless_backup.py` documenta dependencias centrales y exige catálogo/recurso activo al restaurar. El backup VLESS no incorpora el almacén central ni sus secretos.
- `vless_tls_lease_assistant.sh` valida creación RAW/TCP y recuperación de RAW/TCP, WS, gRPC y XHTTP; simula `systemctl`/Xray y verifica permisos POSIX de `www-data` y cleanup. No prueba Xray real.
- Auditoría cruzada: validadores de lease VMess/VLESS equivalentes excepto protocolo; asistentes pasan explícitamente todos los paths configurables al resolutor.
- Suite completa `tests/*.sh`: 45/45 PASS. Xray 26.10.31 acepta 9/9 modalidades VLESS con fixtures.
- Propuestas sin implementación: `docs/PLAN_MIGRACION_TLS_HISTORICO.md` y `docs/PLAN_BACKUP_RESTORE_CENTRAL.md`.
- La VPS de desarrollo carece de unidad Xray con `User`/`Group` explícitos no privilegiados. El resolutor CLI falla cerrado; no se ha probado lectura de lease por Xray real. El asistente deja el borrador TLS guardado si el resolutor no puede preparar el lease.
- TLS histórico no se migra ni borra. No se activó runtime ni se tocaron servicio, firewall, puertos, certificados reales, VPS de pruebas ni `Xray-Normativa/`.
- Informe: `docs/IMPLEMENTACION_VLESS_TLS_CENTRALIZADO_PARCIAL.md`. Estado: IMPLEMENTADO PARCIALMENTE / VERIFICADO EN FIXTURES / NO PUBLICADO / NO SINCRONIZADO / NO ACEPTADO.

## 1. Referencias oficiales

- Documentación normativa canónica: `Xray-Normativa/` (14 archivos originales + README de custodia). Respaldo local VPS: `/root/Xray_Manager_Documentacion_Final_2026-10-31`.
- Especificación funcional Etapa 2: `Xray-Normativa/02_Protocolos_Conexiones/Etapa_2_Protocolos.md` y `Xray-Normativa/02_Protocolos_Conexiones/Etapa_2_Protocolos.yaml`.
- Código en VPS: /opt/xray-manager
- Rama autorizada: design/user-identity-association-v1
- main: no modificar.

## 2. Estado de repositorio y VPS

### GitHub

- Repositorio: Jaok04/xray-core-manager.
- Rama autorizada: design/user-identity-association-v1.
- HEAD de partida previo a esta actualización documental, verificado en VPS y remoto: df632aee5d8139c721b81a6d65f14d93f7676226. Informe: docs/AUDITORIA_INTEGRAL_VMESS_2026-11-02.md; matriz: docs/MATRIZ_TRAZABILIDAD_VMESS_2026-11-02.md.
- Corrección posterior Bloque 1 (restore VLESS preserva VMess): `c890b5b5362e17e439f198b9b8bbbdbe0af0c653` (`fix(vless): preserve current VMess entries on restore`), publicado y sincronizado en la rama autorizada.
- La rama main no se modificó.
- Verificar siempre el HEAD remoto antes de nuevas tareas.

### VPS

- Ruta: /opt/xray-manager.
- La ruta contiene un checkout Git válido.
- El remoto origin apunta al repositorio oficial mediante el alias SSH dedicado.
- La VPS tiene una Deploy Key SSH dedicada con `Allow write access`; el alias `github.com-xray-core-manager` se usa para fetch/push de este repositorio.
- Tras la publicación del cierre técnico y la actualización documental, HEAD local y `origin/design/user-identity-association-v1` se verificaron coincidentes y el árbol de trabajo quedó limpio.
- No se deben asumir estados históricos de sincronización: comprobar rama, HEAD, remoto, árbol y git status en cada sesión.

## 3. Etapas

| Etapa | Alcance | Estado |
|---|---|---|
| Etapa 1 | Menú principal y administración del sistema | ACEPTADA por el propietario |
| Etapa 2 | Protocolos y conexiones | EN DESARROLLO; abierta |
| Etapa 3 | Gestión de usuarios, identidades y asociaciones | Hay módulos y documentación existentes; el estado formal y la cobertura de la etapa requieren auditoría específica |
| Etapas posteriores | Según documentación normativa | Pendientes |

No confundir las etapas del proyecto con las fases A/B/C del instalador o de administración de Xray.

La carpeta de desarrollo ya contiene módulos y pruebas de usuarios/identidades/asociaciones (incluidos users_v2); no se debe tratar Etapa 3 como inexistente. Su alcance, cobertura y criterios de cierre deben auditarse por separado antes de declararla completada.

## 4. Etapa 1 — resultado aceptado

El propietario aceptó expresamente la Etapa 1 como completada.

Evidencia documentada:
- Cotejo normativo: 47/47 comprobaciones PASS.
- Suite posterior a los últimos cambios: 20/20 scripts PASS.
- bash -n: PASS.
- ShellCheck: PASS.
- shfmt: PASS en los archivos homogéneos; tests/uninstall.sh conserva formato histórico mixto.
- ./install.sh --check: PASS.
- Validación operativa en VPS desechable Ubuntu 24.04.4 LTS.
- Instalación aislada de Xray 26.10.31, comprobaciones de permisos/unidad y pruebas de guardas, sin activar la unidad real ni alterar firewall/SSH.

Limitaciones conocidas que deben conservarse:
- U08: SSH/SCP y SHA-256 de exportación externa probados con mocks; no hubo destino remoto real ni credenciales.
- No se desinstalaron Xray ni Manager instalados en el host de pruebas.
- No se reinició la VPS para probar persistencia tras reboot.
Estas limitaciones no anulan la aceptación del propietario; deben seguir identificándose como límites de validación, no ocultarse ni convertirse automáticamente en tareas de implementación.

Documentos técnicos de evidencia:
- docs/MATRIZ_TRAZABILIDAD_ETAPA_1_REV_1_2.md
- docs/ETAPA_1_VALIDACION_PRUEBAS_2026-11-01.md
- docs/ETAPA_1_AUDITORIA_FINAL_2026-11-02.md
- docs/ETAPA_1_VALIDACION_OPERATIVA_VPS_DESECHABLE_2026-11-02.md
- docs/ETAPA_1_CONCURRENCIA_CONFIRMACIONES_2026-11-01.md

## 5. Etapa 2 — estado actual

La especificación funcional aprobada es revisión 1.3, aprobada el 30/10/2026. Define cinco familias principales (VLESS, VMess, Trojan, Shadowsocks, Hysteria2), tres opcionales (SOCKS, HTTP Proxy, WireGuard), navegación jerárquica y flujos Crear/Administrar.

### Implementado en la base actual

- Menú de familias y protocolos opcionales.
- Navegación por modalidades y selección de seguridad prevista.
- Flujo Crear / Administrar / Volver.
- Registro y administración inicial de conexiones como borradores.
- Listado, consulta de detalles, edición y eliminación confirmada de borradores.
- Catálogo config/protocols.tsv con 38 registros.
- Modelo neutral VLESS de nueve modalidades y adaptador Xray-core 26.10.31.
- VMess: modelo neutral, adaptador Xray-core 26.10.31, asistente, preparación segura, persistencia versionada cifrada y almacén aislado.
- VMess: 14 modalidades integradas en el catálogo, asistente y navegación; validación positiva y negativa.
- Prueba de integración VLESS para nueve modalidades y VMess para 14 modalidades.

### Límites importantes

- Las conexiones se guardan como draft; no equivalen a conexiones activas.
- La creación/edición no aplica una configuración al runtime.
- No se abren puertos ni se modifica firewall por el flujo de conexiones.
- El asistente VLESS ya está integrado con el modelo/adaptador para construir una previsualización temporal; cuando está disponible, incorpora usuarios VLESS en estado borrador.
- El asistente solicita opciones por modalidad y ejecuta xray run -test con el binario fijado si está disponible. Los archivos temporales se eliminan al terminar.
- La persistencia segura VLESS P1–P4 está implementada, verificada y aceptada; incluye almacenamiento versionado, cifrado de secretos y backup/recuperación. Consultar docs/DISEÑO_PERSISTENCIA_SEGURA_VLESS.md y docs/P4_BACKUP_RECUPERACION_VLESS.md.
- El asistente VLESS conserva el flujo de borrador/previsualización y no aplica runtime ni activa el servicio.
- La clave REALITY dejó de pasarse a jq mediante --arg; la integración usa lectura de archivo privado para evitar exposición en argumentos de proceso.
- La finalización de P4 no implica despliegue de certificados externos, activación runtime, puertos ni firewall.
- La validación xray run -test no prueba conectividad extremo a extremo.
- La prueba documentada de nueve modalidades corresponde al entorno y binario Xray 26.10.31; no asumir que se reejecutó en cada sesión.

### Pruebas registradas

Se documentan resultados PASS para navegación, administración de borradores, VLESS, colisiones de puertos, carreras de concurrencia, persistencia JSON, sintaxis Bash, ShellCheck y shfmt. La auditoría del 02/11 no reejecutó todas esas pruebas; consulta los informes y repítelas cuando el cambio lo requiera.

## 6. Decisiones complementarias aprobadas el 2026-11-02

- Se conservan las nueve modalidades VLESS del catálogo, incluidas XHTTP sin TLS, TLS y REALITY.
- El propietario aprobó el diseño técnico VMess y confirmó que VMess-HTTPUpgrade-TLS se implementará.
- La matriz VMess aprobada incluye 14 combinaciones, entre ellas HTTPUpgrade sin TLS y HTTPUpgrade-TLS. Las 14 pasan `xray run -test` con Xray-core 26.10.31.
- El adaptador VMess valida certificados y claves TLS PEM, verifica que correspondan criptográficamente y rechaza symlinks/archivos inválidos. Esta comprobación se añade porque `xray run -test` por sí solo no detecta un certificado PEM malformado.
- Las pruebas de navegación recorren las 14 combinaciones y las opciones de seguridad correspondientes.
- La especificación normativa 1.3 no se reescribió retroactivamente. Las decisiones y el diseño se registran en docs/DECISIONES_ETAPA_2.md y docs/DISEÑO_TECNICO_VMESS.md.
- El propietario autorizó expresamente la implementación VMess y, después, el aislamiento del almacén para mantener intacto P4 VLESS.

## 7. Pendientes principales de Etapa 2

- Resolver y formalizar las discrepancias normativas indicadas.
- VMess: base implementada/publicada; estado vigente en `docs/PUNTO_CONTROL_ACTUAL.md`, `docs/AUDITORIA_INTEGRAL_VMESS_2026-11-02.md`, `docs/MATRIZ_TRAZABILIDAD_VMESS_2026-11-02.md`, `docs/VALIDACION_LIVE_VMESS_F05_2026-11-02.md` y `docs/VALIDACION_CLIENTE_SERVIDOR_VMESS_VM47_2026-11-02.md`. Suite 40/40; VM-38/39/40 PASS; F-05/VM-46 PASS; VM-47 VMess-TLS loopback PASS. Cliente externo/WAN no probado. VMess pendiente de aceptación formal.
- La restauración VLESS conserva las entradas VMess vigentes y su almacén aislado; el backup/restore VMess independiente requiere diseño y aprobación separados.
- Integrar usuarios VMess con asociaciones globales de Etapa 3 solo cuando se aborde esa integración conforme a su especificación.
- Definir e implementar modelos, generadores y validadores para Trojan, Shadowsocks e Hysteria2.
- Implementar administradores específicos SOCKS, HTTP Proxy y WireGuard.
- Integrar peers WireGuard con las identidades/asociaciones de Etapa 3.
- Diseñar aplicación transaccional de configuración, validación, verificación y rollback.
- Realizar pruebas de runtime e integración por modalidad y dependencias externas.
- Verificar compatibilidad real de plugins externos.

## 8. Reglas de estado

Usa siempre IMPLEMENTADO, VERIFICADO, PUBLICADO, SINCRONIZADO y ACEPTADO como estados separados, según AGENTS.md. Registra fecha, evidencia y entorno. No extrapoles un resultado de un entorno a otro.

## 9. Siguiente punto de control

Consultar docs/PUNTO_CONTROL_ACTUAL.md y docs/AUDITORIA_INTEGRAL_VMESS_2026-11-02.md. Resolver F-01 a F-04 con autorización expresa y decidir la semántica de cancelación; no aceptar VMess ni iniciar Trojan todavía.
## Hito P1 — Persistencia segura VLESS (2026-11-02)

- P1 IMPLEMENTADO: primitivas AES-256-GCM, clave maestra idempotente y fail-closed, AAD, blobs versionados, escritura atómica y controles de permisos.
- Dependencia python3-cryptography formalizada en instalador y gestor de dependencias.
- P1 VERIFICADO: 21/21 pruebas tests/*.sh PASS; controles de sintaxis, ShellCheck, compilación Python, install.sh --check y diff PASS.
- La clave maestra real no fue generada; no se modificaron datos operativos ni runtime.
- Siguiente: P2, almacén versionado de configuraciones y referencias.


### Actualización 2026-11-02 — P2 en curso

Se implementó inicialmente `scripts/vless_config_store.py` con esquema neutral VLESS versión 1, revisiones inmutables, publicación atómica de referencias bajo el bloqueo compartido y auditoría sin borrado automático. `tests/vless_config_store.sh` PASS. P2 no está completado: quedan pruebas de interrupciones/concurrencia, suite completa y auditoría final. No se activó runtime ni se creó la clave maestra real.

P2: `tests/*.sh` 25/25 PASS; pruebas específicas incluyen interrupción antes de publicar catálogo (huérfano detectable) y dos escritores concurrentes. `install.sh --check`, sintaxis, py_compile, ShellCheck, shfmt y diff PASS. El campo `secret_ref` queda reservado como null hasta P3.

### P3 — integración de persistencia segura VLESS (implementada y verificada)

Se integró guardado bajo confirmación desde el asistente, cifrado AES-256-GCM de claves privadas TLS/REALITY, referencias versionadas en catálogo/configuración y recuperación temporal para validación. Nuevo `scripts/vless_prepare_config.py`; `vless_config_store.py` ahora admite secretos cifrados y auditoría de blobs. El asistente deja de pasar la clave REALITY como `jq --arg` y usa `--rawfile`. Pruebas focales REALITY/TLS/recuperación PASS. Borradores no se activan. Suite completa `tests/*.sh` 25/25 PASS; `install.sh --check`, `bash -n`, `py_compile`, ShellCheck, shfmt y `git diff --check` PASS. Clave maestra real de VPS no generada. P3 aún no publicada en GitHub.

## 2026-11-02 — P4 backup/recuperación VLESS (COMPLETADA Y ACEPTADA)

Se corrigió la recuperación del journal para registrar si `connections/` y `secrets/` existían antes de restaurar, forzar `fsync` de directorios padres tras los renombrados y admitir journals legacy sin esos indicadores mediante inferencia conservadora. `tests/vless_backup_journal_crash_matrix.sh` valida 32 interrupciones abruptas, incluidas todas las fases y renombrados y las cuatro combinaciones de existencia previa. `tests/vless_backup_journal.sh` valida también journals legacy y destinos originalmente ausentes. `tests/vless_backup_restore_secrets.sh` confirma que la restauración funciona con el certificado TLS externo referenciado ausente, deja documentada la dependencia y no activa runtime. La suite completa final tras esta revisión registró 31/31 PASS; `install.sh --check`, sintaxis Bash, `py_compile`, ShellCheck, shfmt y `git diff --check` PASS. En la revisión inicial P4 seguía ABIERTA; esos puntos se corrigieron en la actualización posterior documentada abajo y recibieron aceptación formal del propietario el 2026-11-02. No se creó backup operativo ni se accedió a la clave maestra real. Publicado en GitHub: `90766d4cb8000ed1f94fb808b80f18483d5778cb` (árbol `cfdb26fd7716f622127ba5d7784884df58799b4c`); VPS sincronizada con `origin`. Consultar `docs/P4_BACKUP_RECUPERACION_VLESS.md`.


## Incidente de pruebas por EOF — 2026-11-02

- Se confirmó que la alerta de disco correspondió a un episodio real: `/tmp/tmp.oaFf5wTZwt/connections-action-error.out` alcanzó 20,465,770,496 bytes. Un proceso huérfano conservaba además un archivo borrado de aproximadamente 925 MB abierto.
- Se detuvo el proceso huérfano y se eliminó solo `/tmp/tmp.oaFf5wTZwt`; el filesystem quedó en 3.7 GB usados, 71 GB libres y 5% de uso. No se tocaron datos persistentes ni runtime.
- Causa: `ui_read_option()` ocultaba EOF como respuesta vacía; los menús con bucles repetían indefinidamente el mensaje de opción inválida. Se corrigió la propagación de EOF en los consumidores de menús y prompts.
- `tests/stage1_menu.sh` ahora verifica EOF en menús anidados y limita la salida de regresión a 1 MiB. Pruebas de menú Etapa 1, usuarios V2, preferencias, restore end-to-end TLS/REALITY, sintaxis Bash, ShellCheck y diff check: PASS.
- Se conservan sin borrar `/tmp/tmp.u7Vq57eHNx` (282 MB) y `/tmp/tmp.EsxO527Ihe` (47 MB), artefactos históricos de pruebas V2 con salida repetitiva por EOF.
- `tests/vless_backup_restore_secrets.sh` era un archivo local sin seguimiento Git; se revisó, ejecutó PASS y se incorpora al control de versiones.
- Publicado en GitHub: commit `fa7242a61248a71b64552511d1db932ebbc8d7d0` en `design/user-identity-association-v1`; árbol remoto `b03db9b450288eccbf61e761655f286763df3a70` idéntico al árbol del commit local `b520c53bd5a32007b30519e0756fce13fe8916b5`. La VPS no pudo actualizar refs mediante Git SSH/HTTPS; la referencia remota local quedó obsoleta y requiere reconciliación Git autenticada, sin repetir los cambios.

## 2026-11-02 — autenticación SSH y reconciliación de referencias

Se creó una clave SSH Ed25519 dedicada a este repositorio y se registró en GitHub como Deploy Key de solo lectura (sin permiso de escritura). La VPS autentica correctamente mediante el alias `github.com-xray-core-manager`; la URL `origin` de este checkout usa ese alias y los demás repositorios/configuraciones SSH no se modificaron. `git fetch` se completó correctamente. Se verificó que el árbol local anterior y el árbol remoto eran idénticos (`b6ed32ae1ff32dc4c8c6953a2d1eec48159b1d08`), por lo que se movió únicamente la referencia local de la rama con comprobación del SHA anterior, sin resetear ni sobrescribir archivos. Estado final: `design/user-identity-association-v1` y `origin/design/user-identity-association-v1` apuntan a `5ade7feda328ff4a4f6796fd7ab263237b40dbfa`; working tree limpio y sin divergencia. Las notas anteriores sobre falta de autenticación y refs obsoletas quedan superadas por esta verificación. La clave SSH anterior se conservó intacta. La Deploy Key nueva es de solo lectura; las publicaciones futuras deberán seguir usando el mecanismo autorizado de GitHub API u otro acceso de escritura expresamente configurado.


### Actualización P4 — límites agregados y validación bajo locks (2026-11-02)

Se corrigieron los dos hallazgos adicionales de auditoría. `scripts/vless_backup.py` limita a 512 MiB el contenido total sin comprimir en recolección, creación, verificación y extracción. La validación de payload verifica rutas relativas y traversal, archivos regulares, enlaces, duplicados, conteo, tamaño individual/agregado y hashes del manifiesto. `restore_data()` realiza verificación, lectura de clave, lectura final del archivo y extracción después de adquirir los locks; el hash se contrasta sobre los mismos bytes entregados al validador. Prueba focal `tests/vless_backup_limits.sh` PASS; suite completa posterior 32/32 PASS. El propietario aceptó formalmente estas correcciones el 2026-11-02; P4 queda COMPLETADA. No se creó backup operativo ni se accedió a la clave maestra real.


### Aceptación formal P4 — 2026-11-02

El propietario respondió afirmativamente a la solicitud de aceptación de las correcciones adicionales de límites agregados y TOCTOU. **P4 BACKUP/RECUPERACIÓN VLESS: COMPLETADA Y ACEPTADA.** Cierre respaldado por suite completa 32/32 PASS, `install.sh --check`, sintaxis Bash, `py_compile`, ShellCheck, shfmt y `git diff --check` satisfactorios; commit publicado y VPS sincronizada. El alcance excluye activar conexiones/runtime, reiniciar Xray, abrir puertos, cambiar firewall o desplegar certificados externos. No se creó backup operativo ni se leyó la clave maestra real durante estas pruebas.


## 10. VMess — cierre técnico y aceptación pendiente (2026-11-02)

> Registro histórico de la auditoría inicial. El estado vigente y sus hallazgos se actualizan en la sección 14 de este documento.

La base de código VMess está IMPLEMENTADA, PUBLICADA y SINCRONIZADA. La verificación previa 14/14 y 38/38 se confirmó nuevamente; la auditoría actual detectó F-01 a F-04, por lo que la verificación integral queda INCOMPLETA y no procede aceptación formal.

- Matriz aprobada: 14/14 combinaciones.
- Xray-core 26.10.31: 14/14 configuraciones aceptadas mediante `xray run -test`.
- Navegación: prueba individual de las 14 combinaciones, incluidos los selectores de seguridad de gRPC, HTTPUpgrade, XHTTP y mKCP.
- Pruebas negativas: TLS ausente, symlink, PEM inválido, certificado/clave no coincidentes, campos de seguridad incompatibles, REALITY incompleto, short ID inválido y clave REALITY inválida.
- TLS: el adaptador valida PEM de certificado y clave privada, y compara sus claves públicas con la biblioteca `cryptography`. Xray `run -test` no basta para detectar por sí solo PEM inválido.
- Suite completa: 36/36 scripts PASS en la auditoría final.
- Estáticos: `bash -n`, `python3 -m py_compile scripts/*.py`, `install.sh --check`, ShellCheck warning, shfmt y `git diff --check`: PASS.
- Persistencia aislada: `/var/lib/xray-manager/vmess/configurations/` y `/var/lib/xray-manager/vmess/secrets/`; referencias `vmess_*`, sin reutilizar campos VLESS.
- P4 VLESS y sus archivos de implementación permanecen sin cambios.
- Backup/restore VMess queda como diseño independiente posterior; no bloquea el cierre técnico de este módulo salvo que la especificación normativa disponga lo contrario.
- Los usuarios VMess siguen siendo introducidos manualmente; la integración con identidades globales pertenece a Etapa 3.
- No se tocó runtime, firewall, puertos, certificados desplegados ni servicio. No se probó conectividad cliente-servidor.

Consultar `docs/DISEÑO_TECNICO_VMESS.md` y `docs/PUNTO_CONTROL_ACTUAL.md` para el detalle y el siguiente paso. Etapa 2 permanece abierta porque faltan Trojan, Shadowsocks, Hysteria2 y protocolos opcionales.


## 10. Corrección de restauración VLESS para preservar VMess — 2026-11-02

El propietario autorizó la protección de las entradas VMess actuales durante una restauración VLESS. `scripts/vless_backup.py` prepara el catálogo combinando las entradas VLESS del backup con las entradas VMess vigentes, bajo los bloqueos lifecycle/integrity. Valida catálogo, IDs, modalidad y referencias VMess; ante corrupción, referencias rotas, IDs duplicados o fallo de escritura staging, aborta antes de publicar. El almacén `/var/lib/xray-manager/vmess/` no se modifica y el backup VLESS no incorpora sus archivos.

Pruebas: nuevo `tests/vless_restore_preserves_vmess.sh` cubre VMess anteriores/posteriores al backup, referencias de configuración/secreto, integridad byte a byte del almacén, colisiones, catálogo corrupto, refs rotas y fallo de escritura. `tests/vless_backup_journal_crash_matrix.sh` conserva cobertura de 32 interrupciones con catálogo VMess válido. Suite completa: 38/38 scripts PASS. `python3 -m py_compile scripts/*.py`, `bash -n` de todos los scripts Bash, `install.sh --check`, ShellCheck warning de pruebas modificadas y `git diff --check`: PASS.

Estado del incremento: IMPLEMENTADO, VERIFICADO, PUBLICADO y SINCRONIZADO; aceptación formal específica pendiente. Commit: `c890b5b5362e17e439f198b9b8bbbdbe0af0c653`. P4 conserva su aceptación histórica para el alcance original; esta corrección posterior se registra por separado. No se creó backup operativo ni se accedió a la clave maestra real. No se modificaron runtime, servicio, firewall, puertos, certificados desplegados ni documentación normativa preliminar.


## 11. Bloque 2 — advertencias y resumen del asistente VMess — 2026-11-02

`modules/vmess_assistant.sh` muestra antes de solicitar parámetros el requisito de sincronización horaria VMess (desfase máximo 120 segundos). Añade advertencias específicas para WebSocket y HTTPUpgrade, sin retirar modalidades aprobadas. Tras `xray run -test` y antes del consentimiento de guardado, presenta un resumen de nombre/ID, dirección, puerto, modalidad, transporte/seguridad, usuarios y parámetros aplicables de transporte/TLS/REALITY. El contenido de claves privadas no se muestra; para TLS se muestra la ruta elegida, y para REALITY sólo la presencia del secreto y sus parámetros públicos.

Se corrigió además una colisión de nombre local en las funciones de lectura de parámetros que impedía asignar correctamente el target REALITY. La prueba `tests/vmess_assistant.sh` ahora verifica advertencias, resumen, orden resumen-antes-de-guardar y ausencia de material secreto TLS/REALITY en la salida.

Verificación focal: `tests/vmess_assistant.sh`, `tests/vmess_model.sh`, `tests/xray_vmess_integration.sh` (14/14 combinaciones y negativos) y `tests/stage2_navigation.sh` (14/14): PASS. `bash -n` y ShellCheck warning de archivos modificados: PASS. Suite completa posterior al Bloque 2 queda pendiente del Bloque 3. Estado: IMPLEMENTADO, VERIFICADO, PUBLICADO y SINCRONIZADO; commit `9d03d4b4e77e1a160b94ee2c2f3c74487977e362`. VMess sigue sin aceptación formal.


## 12. Bloque 3 — cobertura de pruebas VMess — 2026-11-02

Se amplió `tests/vmess_assistant.sh` para comprobar cancelación/EOF en dirección, UUID y path; slots inválidos; UUID inválido y duplicado; puerto fuera de rango; modalidad incompatible; y EOF en el consentimiento después del resumen. Los intentos inválidos o cancelados no deben modificar el catálogo. Se conservan las comprobaciones de resumen previo al consentimiento y ocultamiento de material TLS/REALITY.

Se creó `tests/vmess_persistence_hardening.sh`, que cubre store/read TLS AES-256-GCM, AAD, permisos, clave maestra ausente (read no la regenera), clave inválida (read/store fallan antes de publicar), ciphertext/tag alterado (sin plaintext), referencias de configuración/secreto rotas, archivos huérfanos, symlinks, fallo después de escribir archivos y antes de publicar catálogo, auditoría sin borrado automático, dos escritores concurrentes sobre IDs distintos y dos escrituras concurrentes sobre el mismo ID con revisiones r1/r2.

El fallo inyectado en la publicación del catálogo deja los archivos de configuración/secreto como huérfanos detectables; el catálogo permanece intacto. Esto es coherente con el diseño aprobado, que no ofrece rollback transaccional para VMess y exige detección sin borrado automático. No se cambió producción en este bloque; sólo cobertura de pruebas.

Verificación integral posterior: `tests/*.sh` 38/38 PASS; `python3 -m py_compile scripts/*.py`; `bash -n` de todos los scripts Bash; `install.sh --check`; ShellCheck (`-S warning`) sobre archivos modificados; `git diff --check`: PASS. Estado: IMPLEMENTADO, VERIFICADO, PUBLICADO y SINCRONIZADO; commit `08b2044dd820eb465afecbb6ec66fccefe6397a5`. VMess sigue pendiente de aceptación formal.


## 13. Bloque 4 — etiquetas de modalidades y criterio shfmt — 2026-11-02

Se corrigieron las etiquetas visibles del menú VMess y de los listados que usan `connections_mode_label`: `VMess-WS (sin TLS adicional)` y `VMess-TLS (RAW/TCP + TLS)`. Los identificadores `vmess_ws` y `vmess_tcp_tls`, el orden del menú y las 14 modalidades permanecen intactos. `tests/stage2_navigation.sh` comprueba ambos textos en el menú y en la función de etiquetas, además de mantener la navegación de las 14 combinaciones.

Criterio de formato: `README.md` documenta `shfmt -d -i 4 -ci` para archivos Bash seleccionados. Se inspeccionó el formato existente y se compararon las diferencias que `shfmt` produciría en módulos VMess. No existe una regla que autorice reformatear todo el árbol y el cambio produciría diffs de estilo fuera del alcance; por tanto, no se reformateó ningún archivo. El criterio del proyecto se mantiene: aplicar shfmt con `-i 4 -ci` sólo a los archivos incluidos explícitamente en las verificaciones de README, sin ampliar automáticamente el conjunto.

Estado Bloque 4: etiquetas IMPLEMENTADAS, VERIFICADAS, PUBLICADAS y SINCRONIZADAS en `9528f4b00f6b9654f7236050bbadfd8f9415bf69`. Auditoría integral de VMess pendiente. No se cierra VMess ni Etapa 2.


## 14. Auditoría integral VMess — 2026-11-02 (estado previo a correcciones; histórico)

Se ejecutó auditoría con contraste directo de la línea base normativa Etapa 2 revisión 1.3 y del diseño complementario VMess. Suite completa 38/38 PASS; Xray 14/14 y 10 casos negativos PASS; sintaxis Bash, AST Python (7 archivos), ShellCheck, install.sh --check, git diff --check y el gate shfmt exacto del README PASS.

Hallazgos bloqueantes: F-01 clave TLS root-owned 0644 aceptada; F-02 read/audit aceptan incoherencia entre revisión/schema del catálogo y referencia/archivo; F-03 cancelación del asistente deja registro base draft creado antes de invocarlo; F-04 modelo acepta emails duplicados mientras el almacén los rechaza. F-05 live no verificado: catálogo vacío, almacén VMess y clave maestra ausentes. Detalle y trazabilidad en los dos documentos de auditoría.

Estado: VMess IMPLEMENTADO en su base funcional, VERIFICADO PARCIALMENTE, DOCUMENTADO, PUBLICADO y SINCRONIZADO; NO ACEPTADO. Etapa 2 ABIERTA. No se modificó código, no se creó almacén/clave real, no se tocó runtime/firewall/puertos/servicio y no se modificó main.


## 15. Bloque correctivo VMess F-01 a F-04 — 2026-11-02

Se implementó el alcance autorizado: clave TLS root:root 0600 y un solo hardlink en adaptador/preparador; validación de revisión/schema y referencias de secreto en store/read/audit; cancelación/fallo del asistente retira el draft base VMess vacío y no aplicado bajo bloqueo, preservando configuraciones publicadas; emails únicos en modelo/adaptador/almacén.

Pruebas: suite completa 39/39 PASS; Xray 14/14 modalidades y 16 casos negativos PASS; pruebas focales VMess PASS. bash -n, py_compile, ShellCheck de todos los archivos modificados, install.sh --check, shfmt de los cuatro archivos definidos en README y git diff --check PASS. ShellCheck global conserva warning preexistente SC2174 en tests/vless_backup_restore.sh:7, fuera del alcance y sin cambios.

F-01 a F-04 RESUELTOS y VERIFICADOS EN FIXTURES. VM-38/39/40 verificados con prueba focal. F-05 NO VERIFICADO; no hubo prueba cliente-servidor real. VMess NO ACEPTADO; Etapa 2 ABIERTA. No se creó almacén/clave real ni se tocó runtime/firewall/puertos/servicio; main intacta.


## Revalidación controlada VMess — 2026-11-02

En la VPS de desarrollo, sobre HEAD `4c87557e0aff4166c540c633effe5cb6dac40096`, se agregó `tests/vmess_navigation_edge_cases.sh`. VM-38/39/40 pasan. Suite completa `tests/*.sh`: 40/40 PASS; Xray 26.10.31 valida 14/14 modalidades y 16 casos negativos. La primera ejecución parcial de la prueba de colisiones tuvo un fallo UDP transitorio; repetición aislada y suite completa posterior PASS.

F-05 live no se ejecutó: no se creó `/etc/xray-manager/keys/master.key`, almacén VMess real ni conexión persistente. Xray no está instalado en esta VPS; se utilizó el binario de validación en caché. Servicio inactivo y sin cambios en runtime/firewall/puertos/servicio. VM-47 conectividad cliente-servidor sigue NO VERIFICADO. VMess no aceptado; Etapa 2 abierta.


## Validación live F-05 — 2026-11-02

F-05/VM-46 VERIFICADO LIVE en VPS de desarrollo: clave maestra compartida creada (32 bytes, root:root 0600), almacén VMess inicializado (directorios root:root 0700), primer store VMess-TLS, lectura/descifrado byte a byte, recuperación por asistente y validación Xray 26.10.31. Audit limpio; GCM alterado rechazado sin plaintext. Conexión temporal y archivos versionados retirados; catálogo vacío. Clave y directorios vacíos conservados. Sin runtime/firewall/puertos/servicios; Xray inactivo. VM-47 conectividad cliente-servidor NO VERIFICADA. VMess no aceptado; Etapa 2 abierta. Evidencia: `docs/VALIDACION_LIVE_VMESS_F05_2026-11-02.md`.


## Validación cliente-servidor VM-47 — 2026-11-02

VM-47 VERIFICADO en loopback local: modelo y adaptador reales generaron el servidor VMess-TLS; cliente Xray SOCKS conectó mediante TLS/VMess y transportó una solicitud HTTP hasta un servicio destino, que respondió 200 con el marcador esperado. Ambos `xray run -test` pasaron. Procesos/listeners temporales detenidos; sin cambios de runtime, firewall, puertos públicos, catálogo o servicio. Cliente externo/WAN no probado. VMess no aceptado formalmente; Etapa 2 abierta. Informe: `docs/VALIDACION_CLIENTE_SERVIDOR_VMESS_VM47_2026-11-02.md`.


## Actualización de estado — revalidación VMess 2026-11-03

**Estado del módulo:** VMess IMPLEMENTADO, VERIFICADO y DOCUMENTADO; técnicamente preparado para aceptación formal del propietario. VM-48 sigue pendiente, por lo que VMess no está aún ACEPTADO. Etapa 2 permanece ABIERTA.

**Evidencia ejecutada en `/opt/xray-manager`:** suite completa `tests/*.sh` 40/40 PASS; Xray-core 26.10.31 14/14 modalidades VMess PASS y 16/16 casos negativos PASS; `bash -n` de módulos/pruebas Bash VMess; `py_compile` de `vmess_config_store.py` y `vmess_prepare_config.py`; ShellCheck de módulos/pruebas VMess; `git diff --check`: PASS.

**Reconciliación de trazabilidad:** VM-28 VERIFICADO por persistencia versionada, referencias separadas, coherencia de revisiones/schema/secreto y concurrencia r1/r2. VM-32 VERIFICADO para atomicidad individual y serialización de catálogo, con límite multiarchivo explícito. VM-33 NO APLICA como requisito: el diseño técnico VMess §8 no promete rollback transaccional. VM-42 backup/restore VMess independiente está fuera del alcance aprobado; VM-43 corresponde a Etapa 3. VM-47 cliente-servidor VMess-TLS está verificado en loopback; cliente externo/WAN no probado ni requerido por el diseño.

**Cambios de esta revalidación:** únicamente se documentaron tres variables globales intencionales consumidas por el módulo cargado con `source`, con supresión local SC2034; no se eliminaron asignaciones necesarias. No se modificó código de producción, documentación normativa `Xray-Normativa/`, runtime, firewall, puertos, certificados desplegados ni servicio. La carpeta normativa se comparó con el respaldo original: 14/14 archivos originales coincidentes.

**Siguiente paso:** decisión formal del propietario sobre VM-48. No iniciar Trojan hasta obtener aceptación VMess y contrastar específicamente su alcance normativo.


## Trabajo aprobado — certificados TLS centralizados (2026-11-03)

- El propietario aprobó el modelo arquitectónico: catálogo de certificados independiente de conexiones; recursos `managed` y `reference`; una única clave privada cifrada central por recurso; conexiones VMess/VLESS referencian mediante `certificate_id`; resolución controlada; REALITY permanece separado.
- Contrato inicial documentado en `docs/ARQUITECTURA_CERTIFICADOS_CENTRALIZADOS.md`.
- La decisión arquitectónica está APROBADA. El contrato está DOCUMENTADO en revisión inicial; las decisiones técnicas de implementación listadas en §14 siguen pendientes de auditoría/cierre.
- Código de producción todavía NO MODIFICADO por este trabajo. Catálogo central, almacén, resolutor, integración VMess/VLESS, migración y backup/restore compartido siguen pendientes.
- No se modificó `Xray-Normativa/`, ni la VPS `Vps de Pruebas`, ni runtime, certificados desplegados, firewall, puertos o servicio.
- Etapa 4 funcional sigue sin implementación completa; este trabajo sólo establece el diseño técnico para el recurso de certificados compartidos.
- Próximo paso: auditar los módulos criptográficos, catálogos y permisos/identidad efectiva del servicio Xray en la VPS de desarrollo; cerrar las decisiones de §14 antes de implementar el almacén central.


## Implementación progresiva — certificados TLS centralizados (2026-11-03)

- Contrato: docs/ARQUITECTURA_CERTIFICADOS_CENTRALIZADOS.md.
- Informe del primer bloque: docs/IMPLEMENTACION_ALMACEN_CERTIFICADOS_CENTRALIZADOS.md.
- Implementados: scripts/certificate_crypto.py, scripts/certificate_store.py, rutas dedicadas en config/paths.sh y tests/certificate_store.sh.
- Funciones disponibles: importar certificado como managed o reference, listar, mostrar y auditar. La clave privada se cifra una sola vez por recurso con AES-256-GCM y AAD ligado a certificate_id + revisión.
- La clave maestra existente /etc/xray-manager/keys/master.key se reutiliza sólo en lectura; no se creó, rotó ni modificó. Sólo se inspeccionaron sus metadatos.
- Verificación ejecutada: suite completa 41/41 PASS; bash -n, py_compile, ShellCheck de prueba nueva y git diff --check: PASS.
- No se importaron certificados reales al catálogo persistente. Las pruebas utilizaron certificados efímeros en directorios temporales.
- Pendiente: resolutor, autorización por conexión, integración VMess/VLESS, migración histórica, backup/restore compartido, rotación y permisos de lectura por el servicio Xray.
- En VPS de desarrollo no hay Xray instalado ni unidad/cuenta/grupo xray; la integración runtime no se puede validar allí actualmente.
- No se tocó VPS Vps de Pruebas, runtime, servicio, firewall, puertos o certificados desplegados. Xray-Normativa sigue intacta.

- Publicación del bloque inicial TLS verificada: HEAD local/remoto 6d35b0dde502db66d9826bc4fb67e8500b6b4561 en design/user-identity-association-v1. main permanece en 656ecedc506a94a6461aee296b20871d51a38bf3. Xray-Normativa sin diferencias en el bloque publicado.


## Segundo bloque — resolutor TLS centralizado (2026-11-03)

- Informe: docs/IMPLEMENTACION_RESOLUTOR_CERTIFICADOS_TLS.md.
- Nuevo scripts/certificate_resolver.py: autorización exacta connection_id + certificate_id, lectura versionada VMess/VLESS, validación de catálogo TLS central, huellas, vigencia y correspondencia de clave.
- Prepara leases aleatorios temporales en XRAY_MANAGER_CERTIFICATES_RUNTIME_DIR (/run/xray-manager-certificates), con root:<grupo-servicio> 0750 y archivos 0640; ofrece cleanup validado.
- Identidad de systemd se consulta con systemctl show y requiere User/Group explícitos, sin grupos suplementarios. En VPS desarrollo no hay xray.service ni cuenta/grupo xray; CLI fail-closed, sin crear lease.
- Pruebas aisladas managed/reference y VMess/VLESS con UID/GID sintético 1; no son prueba de acceso por Xray real.
- Nueva tests/certificate_resolver.sh. Suite completa 42/42 PASS; bash -n, py_compile, ShellCheck de pruebas y git diff --check PASS.
- Los stores y asistentes/generadores VMess/VLESS todavía no guardan/aceptan certificate_id; la integración permanece pendiente.
- No se tocó runtime, servicio, VPS Vps de Pruebas, firewall, puertos, certificados desplegados, secretos históricos, REALITY ni Xray-Normativa.


## 20. Bloque 3 — VMess TLS centralizado, endurecimiento del lease (2026-11-03)

- `modules/vmess_xray_26_10_31.sh` exige `lease-id` para TLS; ya no acepta rutas TLS arbitrarias. `scripts/vmess_tls_lease_check.py` valida manifiesto, conexión, protocolo VMess, certificado/revisión/huella, identidad de servicio y permisos root:<grupo-servicio> 0750/0640. El par PEM se valida bajo los mismos permisos que emite el resolutor.
- `modules/vmess_assistant.sh`: creación y recuperación pasan `--runtime-root` explícito, leen con el catálogo central correcto y limpian leases en éxito y fallo mediante trap. TLS histórico sigue siendo legible por el store, pero su recuperación falla cerrada hasta migración controlada.
- `scripts/vless_backup.py`: restauración VLESS preserva VMess vigente y ahora valida que cada `certificate_id` TLS central VMess esté activo en el catálogo central. No incluye el almacén VMess ni el catálogo central en el backup VLESS.
- Pruebas nuevas/ampliadas: `tests/vmess_tls_lease_assistant.sh`, `tests/xray_vmess_integration.sh`, `tests/vless_restore_preserves_vmess.sh`.
- Verificación: suite completa 43/43 PASS; Xray-core 26.10.31 valida 14/14 modalidades con fixture de lease; ciclo asistente con resolutor/Xray simulados PASS; ShellCheck warning, Bash syntax, py_compile y git diff --check PASS.
- Límites: la VPS de desarrollo carece de `xray.service` y usuario/grupo Xray. No se ha demostrado lectura del lease por Xray real. No hubo runtime apply, despliegue, certificados persistentes ni migración histórica. Backup compartido/independiente VMess pendiente; integración VLESS pendiente.
- Cambios locales aún no publicados ni sincronizados. `Xray-Normativa/` y `main` intactas. VMess/Etapa 2 no se consideran aceptados ni cerrados.


## 2026-11-03 — Migración TLS histórica / backup compartido: preflight y decisiones aprobadas

- Aprobados los criterios de migración histórica VMess+VLESS, `managed` por defecto, referencias sólo con consentimiento, bloqueo de certificados fuera de vigencia y conservación de históricos.
- Aprobados criterios de backup compartido: cifrado propio del paquete, re-cifrado bajo master key destino, master key fuera del backup, bloquear restore completo si falta `reference`, y no sobrescribir datos posteriores/conflictos.
- Nuevo `scripts/certificate_migration.py` ofrece `plan --protocol all|vless|vmess`, sólo lectura. Descifra en memoria con el backend de cada protocolo, valida contrato/revisiones, archivos/permisos, par PEM, vigencia, fingerprints y deduplicación. No escribe ni migra.
- `tests/certificate_migration_plan.sh` añadido. Suite `tests/*.sh`: 46/46 PASS; Bash syntax, py_compile, ShellCheck de prueba nueva y git diff check PASS.
- Inventario real: catálogo de conexiones de VPS implementación vacío; 0 candidatos TLS. Sin migración real.
- Se corrigió el plan de backup tras auditoría: backup-data VLESS actual no cifra el tar integral; sólo los blobs de secretos y el paquete de recuperación de master key tienen cifrado. El nuevo backup compartido tendrá contenedor integral independiente.
- Informe: `docs/IMPLEMENTACION_PREFLIGHT_MIGRACION_TLS.md`; planes v1.1 en `docs/PLAN_MIGRACION_TLS_HISTORICO.md` y `docs/PLAN_BACKUP_RESTORE_CENTRAL.md`.
- Estado: PREFLIGHT IMPLEMENTADO/VERIFICADO EN FIXTURES; BACKUP COMPARTIDO Y FASE ESCRITORA DE MIGRACIÓN PENDIENTES. No runtime apply, servicios, firewall, puertos, certificados desplegados, VPS pruebas ni cambios normativos. No commit/push aún; `Xray-Normativa/` intacta.

**Publicación:** commit `631d7eda11615b692557a2e0958a8f318b81c223` publicado en `design/user-identity-association-v1`; HEAD local/remoto coincide. `main` sin cambios (`656ecedc506a94a6461aee296b20871d51a38bf3`); `Xray-Normativa/` intacta.

## Decisión de backup compartido — metadatos VMess (2026-11-03)

- Decisión del propietario: excluir el UUID VMess por defecto como credencial; conservar email y level como metadatos/configuración dentro del payload cifrado.
- email no es requisito de autenticación ni de conexión para el cliente externo. No debe exponerse en el manifiesto externo ni en logs.
- Los registros sin UUID quedan incompletos/no restaurables íntegramente hasta recibir la credencial por un flujo autorizado. La inclusión de UUID exige selección, autorización y confirmación adicional.
- Detalle contractual: docs/PLAN_BACKUP_RESTORE_CENTRAL.md §10.1 (v1.3).
- No se modificó el esquema operativo VMess ni se creó backup/snapshot real. El contenedor v1 sigue siendo la única pieza implementada del backup compartido; snapshot, manifiesto y orquestación siguen pendientes.

## Desinstalación coordinada con catálogo TLS — 2026-11-03

- IMPLEMENTADO localmente: modules/uninstall.sh adquiere catalog.lock cuando la política/selección elimina certificados; orden en ese flujo: lifecycle → uninstall → integrity → catalog → Xray.
- Si catalog.lock está ocupado, aborta antes del respaldo/eliminación. Si lo obtiene, lo mantiene durante confirmación, respaldo y borrado; libera en retorno.
- Tests tests/uninstall.sh: lock ocupado bloquea la operación y conserva datos; caso de categoría certificates verifica que el lock permanece ocupado durante confirmación.
- Verificación: todos los tests/*.sh PASS; bash -n PASS; ShellCheck del módulo modificado PASS; git diff --check PASS; py_compile scripts/*.py PASS.
- La auditoría global de locks sigue ABIERTA: aún falta inventariar y contrastar exhaustivamente todos los mutadores/órdenes y ampliar pruebas de concurrencia. No comenzar writer compartido todavía.
- Sin cambios en Xray-Normativa, datos persistentes, certificados reales, master key, runtime, servicios ni firewall. Cambios de código/docs locales hasta su publicación.

## Ruta estable del bloqueo TLS — 2026-11-03

- Hallazgo: el lock anterior dentro de /var/lib/xray-manager/certificates se eliminaba junto con el árbol; mantener flock sobre un inode desvinculado no protege frente a procesos que creen un archivo nuevo.
- Nuevo default único: /run/xray-manager-certificate-locks/catalog.lock. Fuera del árbol de datos persistentes que desinstalación elimina; certificate_store crea/valida su padre root-only y resolver reutiliza el acquire_lock central. uninstall.sh prepara el padre como root:root 0700.
- Alineados config/paths.sh, defaults de certificate_store.py y certificate_resolver.py, fallbacks en asistentes VLESS/VMess, uninstall.sh y documentación. Pruebas parser y supervivencia del lock añadidas.
- No se movió/eliminó ningún lock real en la VPS ni se ejecutó runtime apply. Auditoría global de mutadores sigue abierta.

## Auditoría estática de locks para snapshot — 2026-11-03

- Inventario estático de todos los puntos de adquisición encontrados en scripts, modules, lib, config e install.sh.
- Orden observado: lifecycle → integrity → catalog (resolver); lifecycle → integrity (install/VLESS backup); lifecycle → Xray-admin; uninstall añade uninstall entre lifecycle e integrity y catalog condicional antes de Xray.
- Conexiones, usuarios legacy/v2, stores VLESS/VMess, cutover y preflight migración TLS usan integrity; almacén de certificados usa catalog; settings/dependencias/servicio usan lifecycle.
- No se encontró ciclo/inversión en los caminos inspeccionados. Orden recomendado snapshot: lifecycle → integrity → catalog; liberación inversa.
- Los locks Python existentes son bloqueantes; el writer futuro deberá usar adquisición no bloqueante con timeout finito configurable y abortar sin publicar si falla.
- Pruebas de contención lifecycle/integrity/catalog/Xray, retención/liberación del catalog y ruta estable; suite 47/47 PASS, Bash syntax, ShellCheck uninstall, shfmt focal, py_compile y diff-check PASS.
- Limitación: auditoría estática no equivale a stress test exhaustivo. Cambio de ruta catalog requiere despliegue con procesos de versión anterior detenidos; no se movió lock antiguo ni se hizo runtime apply.


## 2026-11-03 — Aprobación del alcance incremental del snapshot compartido v1

El propietario aprobó el alcance incremental: snapshot de conexiones/configuraciones actuales VLESS y VMess; metadatos no secretos de usuarios, identidades y asociaciones; catálogo central TLS, certificados públicos `managed` y dependencias `reference`. Se excluyen por defecto UUID VLESS/VMess, secretos REALITY, claves privadas TLS y cualquier otra credencial; los elementos afectados se marcan incompletos. Se mantienen `email` y `level` VMess como metadatos protegidos.

Perfiles, perfil activo, preferencias, dominios independientes y protocolos distintos de VLESS/VMess quedan `unsupported` en v1. Si una categoría no soportada es solicitada, el resultado global será `PARTIAL`, nunca `COMPLETE`. Esto se contrasta con Etapa 5 normativa, que sigue siendo la referencia íntegra y no se modifica.

`docs/PLAN_BACKUP_RESTORE_CENTRAL.md` actualizado a v1.6 con la decisión y un borrador del contrato lógico de manifiesto. El borrador sigue pendiente de aprobación: no es schema congelado. La aprobación actual no autoriza writer, paquetes reales, restore, inclusión de secretos ni runtime apply.


**Publicación del alcance incremental v1:** commit `bccaba94be4160e6c01f281c7f4829f02c07db41` (`docs(backup): approve incremental snapshot v1 scope`) publicado en `origin/design/user-identity-association-v1`; HEAD local/remoto verificado idéntico en ese commit. Sólo documentación; `Xray-Normativa/` intacta. No se implementó writer ni se crearon paquetes/backups reales.


## 2026-11-03 — Borrador detallado de schema del manifiesto compartido

Se amplió `docs/PLAN_BACKUP_RESTORE_CENTRAL.md` a v1.7 con una propuesta concreta de estructura JSON y reglas de validación para el manifiesto interno: solicitud/categorías, recursos, miembros content-addressed, exclusiones, dependencias, snapshot de origen y completitud. `COMPLETE`/`PARTIAL` son estados de paquete; `BLOCKED` es preflight fallido y no produce paquete. El manifiesto permanece dentro del payload cifrado y no contiene credenciales ni email VMess.

El schema sigue PENDIENTE DE APROBACIÓN. No se implementó writer, verify, restore ni formato de empaquetado; no se creó backup real. `Xray-Normativa/` permanece intacta.


**Publicación del borrador de manifiesto:** commit `2bffbb6eee3c84b8008d2445ae0c0377bca40536` (`docs(backup): draft shared manifest schema v1`) publicado en `origin/design/user-identity-association-v1`; HEAD local/remoto verificado idéntico en ese commit. Sólo documentación; `Xray-Normativa/` intacta. El schema continúa pendiente de aprobación y no hay writer ni backup real.


## 2026-11-03 — Aprobación del contrato JSON del manifiesto compartido v1

El propietario aprobó expresamente el contrato lógico y la estructura JSON de las secciones 10.6 y 10.7 de `docs/PLAN_BACKUP_RESTORE_CENTRAL.md`. Se aprueban campos/relaciones, categorías, recursos, miembros content-addressed, exclusiones, dependencias, source snapshot, hashes/tamaños, paths relativos, reglas de validación y estados `COMPLETE`/`PARTIAL`; `BLOCKED` queda como resultado de preflight que aborta sin publicar paquete. El manifiesto no contiene credenciales ni email VMess.

El plan pasa a v1.8 y el contrato de manifiesto v1 queda APROBADO. Empaquetado físico, máximo de miembros y canonicalización JSON exacta siguen pendientes de cierre técnico. No se implementó writer/verify/restore ni se creó backup real. `Xray-Normativa/` permanece inmutable.


**Publicación de aprobación del manifiesto:** commit `000eb537fbb11c9870b6bef917769b1ca8448c66` (`docs(backup): approve shared manifest contract v1`) publicado en `origin/design/user-identity-association-v1`; HEAD local/remoto verificado idéntico en ese commit. Sólo documentación; `Xray-Normativa/` intacta. El writer sigue sin implementarse.


## Estado actualizado — formato lógico de paquete compartido v1 (2026-11-03)

- Aprobado ZIP interno con `ZIP_STORED`, `manifest.json` e `index.json`; sólo archivos regulares y validación de rutas, duplicados, miembros indexados, tamaño y SHA-256.
- Aprobado perfil JSON canónico propio: UTF-8 estricto sin BOM, claves ordenadas, separadores compactos, sin claves duplicadas ni floats/valores no finitos, enteros interoperables y comparación byte-a-byte con serialización canónica. No se declara RFC 8785/JCS.
- Límite del ZIP completo: 512 MiB. Máximo aprobado: 10.000 entradas ZIP totales, incluidas `manifest.json` e `index.json` (hasta 9.998 miembros de datos); superar el límite aborta sin publicar paquete. Plan `docs/PLAN_BACKUP_RESTORE_CENTRAL.md` actualizado a v1.9.
- Decisión de diseño/documentación solamente. No hay writer, verify, restore ni paquete real; no se incluyeron secretos ni se ejecutó runtime apply. `Xray-Normativa/` permanece intacta.


## Decisión aprobada — límite de entradas ZIP (2026-11-03)

Máximo estricto de 10.000 entradas ZIP totales, incluyendo `manifest.json` e `index.json`; hasta 9.998 miembros de datos. Writer/preflight abortará sin publicar si se excede; verify/lector rechazará paquetes sobre el límite. Plan actualizado a v1.10. Esto cierra el máximo de miembros, pero no autoriza writer, verify, restore, paquetes reales, inclusión de secretos ni runtime apply.


## 2026-11-03 — Aprobación del contrato técnico del snapshot writer v1

El propietario aprobó el contrato técnico del snapshot writer compartido v1 y la ampliación de cifrado incremental compatible con el contenedor criptográfico v1. Se congelan: secuencia fail-closed; locks `lifecycle → integrity → catalog`, adquisición no bloqueante con timeout total configurable (30 s inicial recomendado) y liberación inversa; captura coherente de catálogos/revisiones referenciadas; adaptadores VLESS/VMess/identidades/TLS; exclusiones predeterminadas; validación segura de archivos; manifiesto/índice/ZIP `ZIP_STORED`; máximo 10.000 entradas y 512 MiB; cifrado GCM por bloques sin cambiar el formato binario v1; verificación y publicación atómica exclusiva sin sobrescritura; estados de resultado y matriz de pruebas.

La interfaz incremental deberá conservar magic, cabecera/AAD, perfil scrypt, salt/nonce, AES-256-GCM y tag del formato v1, con compatibilidad cruzada respecto a la interfaz actual. El ZIP se emitirá en streaming al cifrador sin crear ZIP en claro en disco; el tamaño exacto del ZIP se calculará antes de fijar `ciphertext_length` y se contrastará con el flujo emitido.

`docs/PLAN_BACKUP_RESTORE_CENTRAL.md` pasa a v1.11. La aprobación autoriza implementar writer y cifrado incremental en la rama autorizada, pero no crear backups reales, incluir secretos, implementar restore/verify independiente, leer/modificar master key ni tocar runtime/servicios/firewall/puertos/certificados desplegados/VPS de pruebas. `Xray-Normativa/` permanece inmutable.


## 2026-11-03 — API incremental del contenedor compartido v1

Se añadieron `encrypt_payload_stream()` y `verify_package_stream()` a `scripts/shared_backup_format.py`. La interfaz cifra y verifica por bloques, exige longitud conocida para la cabecera autenticada y conserva el formato binario v1; las APIs de bytes anteriores permanecen compatibles. El verificador descarta plaintext no autenticado y valida el tag antes de declarar éxito.

Pruebas: `tests/shared_backup_format.sh` PASS con compatibilidad cruzada, truncamiento, bytes sobrantes, alteración/tag, contraseña incorrecta y longitudes incorrectas; pruebas adicionales de tamaños aleatorios PASS; suite completa `tests/*.sh` 47/47 PASS; sintaxis Python y `git diff --check` PASS.

Estado: cifrado incremental IMPLEMENTADO/VERIFICADO en aislamiento. snapshot writer/orquestador y adaptadores pendientes. No se creó backup real ni se tocaron secretos, master key, runtime o `Xray-Normativa/`.


## 2026-11-03 — Generador ZIP determinista en streaming v1

Se añadió `scripts/shared_backup_zip.py` con `ZipMember`, `ZipStream` y `write_zip_stream()`. Permite preflight de bytes/archivos autorizados y emisión ZIP_STORED determinista; las rutas de origen requieren `allowed_root`, se recorren sin symlinks, se valida root:root 0600/nlink 1 y se comparan inode/metadatos, SHA-256 y CRC-32 durante emisión. `ZipStream` alimenta directamente `encrypt_payload_stream()` sin ZIP temporal en claro.

Se aplican UTF-8/NFC, nombres seguros y orden estable, `manifest.json`/`index.json` primero, sin ZIP64, límite 10.000 entradas y 512 MiB contando overhead. Prueba focal `tests/shared_backup_zip.sh` PASS con ZIP estándar, CRC, determinismo, integración cifrada, TOCTOU, paths, symlink/hardlink/permisos y límites. Suite completa `tests/*.sh`: 48/48 PASS; sintaxis Python, ShellCheck focal, shfmt focal y `git diff --check` PASS.

Snapshot writer/orquestador y adaptadores siguen pendientes. No se creó backup real ni se tocaron secretos, master key, runtime o `Xray-Normativa/`.


## 2026-11-03 — Snapshot writer compartido v1: primera implementación local

- Se implementó localmente scripts/shared_snapshot_writer.py conforme al contrato aprobado §10.11. No se ha publicado ni sincronizado.
- Correcciones incorporadas: selective requiere categorías explícitas; destino y staging privado se preparan antes de solicitar passphrase; la passphrase se solicita antes de adquirir locks; directorios padres de locks deben existir y ser root-owned y no permitir escritura grupal/otros salvo sticky; timeout debe ser numérico, finito y no negativo.
- Se añadió tests/shared_snapshot_writer.sh con pruebas sintéticas de selección explícita, secuencia staging/passphrase, limpieza, locks ausentes/inseguros, orden de locks y liberación inversa, timeout, referencias de identidad y exclusión de UUID/secret refs. Se prueba que VMess conserva email/level dentro del miembro protegido y elimina UUID.
- Verificación focal en VPS: tests/shared_snapshot_writer.sh PASS; tests/shared_backup_format.sh PASS; tests/shared_backup_zip.sh PASS; análisis AST Python de los tres módulos PASS; regresión global tests/*.sh: 49/49 PASS; git diff --check PASS.
- No se ejecutó el writer real, no se creó backup/snapshot, no se leyeron master key ni secretos reales, no se ejecutó restore/verify independiente y no se tocó runtime, servicios, firewall, puertos, certificados desplegados, VPS de pruebas ni Xray-Normativa/.
- Estado: writer IMPLEMENTADO LOCALMENTE / VERIFICADO PARCIALMENTE / NO PUBLICADO / NO SINCRONIZADO / NO ACEPTADO. Requiere auditoría y suite de aceptación integral antes de publicación. Rama design/user-identity-association-v1; HEAD sin commit nuevo: ec9b306b38f0bce17f28c301c47df3b3d092785a.
- SHA-256 writer: d502db8c82a0ef044cb413eb6b5cd4e2775392500e70a31c97c0fccdf814c7ca. SHA-256 pruebas writer: 9e230d0d74c9a76e94297d02aa1e41f9b52a453d8ec67d91dd76cb15ce6de827.

## 2026-11-03 — Endurecimiento y ampliación de pruebas del snapshot writer v1

Implementados localmente los cuatro bloques autorizados de corrección:

1. **Destino y TOCTOU:** la validación inspecciona toda la cadena de directorios; exige root:root, rechaza symlinks y ancestros group/world-writable sin sticky bit; conserva la excepción segura para directorios sticky como /tmp y exige 0700 en el directorio final.
2. **Dependencias TLS:** se incorpora `external-dependencies.json` como miembro del ZIP cifrado. Para certificados `reference` registra certificate_id, fingerprint, ruta esperada, conexiones dependientes y validación requerida. La ruta absoluta no se incorpora al manifiesto y sólo queda dentro del payload cifrado. Las dependencias TLS reference se identifican como `tls_reference`.
3. **Errores y estados:** passphrase inválida, origen/miembro ZIP alterado, límites/formato cifrado inválido y verificación fallida se clasifican como `BLOCKED`; fallos operativos de I/O se mantienen como `FAILED`.
4. **Snapshot y exclusiones:** `source_snapshot` registra catalog_id, schema_version, revision, SHA-256 y presencia. Los almacenes sin schema/revision propia declaran null, no valores inventados. El catálogo de identidades ausente bloquea en vez de interpretarse silenciosamente como vacío. Las exclusiones de asociaciones ahora identifican asociación, identidad y conexión y se representan como recursos individuales.

La suite focal `tests/shared_snapshot_writer.sh` se amplió con:
- Rechazo de ancestros inseguros y symlinks en el destino.
- Rechazo de passphrase débil como BLOCKED.
- Revisiones VLESS/VMess incorrectas, destino preexistente y cleanup.
- Dependencias TLS reference con agregación de conexiones y path confinado al miembro cifrado.
- E2E sintético VLESS + VMess + identidades: UUID ausentes del paquete, email/level VMess conservados.
- E2E sintético TLS reference y TLS managed: certificado público managed incluido; clave privada excluida; ruta reference sólo en external-dependencies.json.
- Cambio de configuración después del preflight rechazado por hash/size del miembro.
- Fallos de verificación, fsync, interrupción controlada y carrera de publicación sin sobrescritura.
- Medición tracemalloc de emisión ZIP→AES-GCM para un miembro de 16 MiB con umbral de memoria Python inferior a 8 MiB.

Pruebas focales writer, formato cifrado y ZIP PASS; AST Python, ShellCheck, shfmt y git diff --check PASS. Regresión global `tests/*.sh`: 49/49 PASS.

**Limitaciones aún abiertas antes de aceptación:** no se ha ejecutado una matriz de terminaciones abruptas SIGKILL en cada fase; la medición de memoria es tracemalloc (no RSS máximo del proceso); los límites de 10.000 entradas/512 MiB se verifican en el generador ZIP, pero falta una prueba de orquestación que los fuerce desde el writer; falta ampliar escenarios integrales de catálogos y revisiones VLESS/VMess y pruebas de publicación/durabilidad posteriores al punto de commit. Por tanto, el writer sigue NO ACEPTADO.

No se creó backup real ni se accedió a master.key o secretos reales. No se ejecutó restore/verify independiente ni se modificó runtime, servicios, firewall, puertos, certificados desplegados o VPS de pruebas. `Xray-Normativa/` permanece intacta. Sin commit/push ni sincronización GitHub; rama `design/user-identity-association-v1`, HEAD sin cambio `ec9b306b38f0bce17f28c301c47df3b3d092785a`.

## 2026-11-03 — Cierre de la matriz ampliada de pruebas del snapshot writer

Se completó una segunda ampliación de la suite de aceptación local:

- E2E sintético VLESS + VMess + identidades, TLS `reference` y TLS `managed`; se verificó ausencia de UUID/credenciales excluidas, conservación de `email`/`level` VMess y ruta de referencia sólo dentro del miembro cifrado.
- TOCTOU de configuración después del preflight: el cambio de bytes se detecta y bloquea antes de publicar.
- Límites ejercidos a través de `create_snapshot`: 10.001 entradas y ZIP lógico superior a 512 MiB producen BLOCKED sin paquete final.
- Locks con contención real: timeout al segundo lock y liberación del primero comprobada.
- Publicación: destino concurrente no sobrescrito; fallos pre-commit limpian staging; fallo de fsync post-commit informa FAILED y conserva el artefacto ya publicado, que se vuelve a autenticar.
- Terminación abrupta mediante `os._exit` en tres puntos (antes del prompt, durante emisión cifrada y antes del enlace final): no aparece destino final; los residuos observados permanecen dentro de staging root:root 0700 y archivo 0600. La prueba los elimina al terminar.
- Memoria: tracemalloc bajo el umbral de 8 MiB adicionales; proceso aislado con miembro de 16 MiB midió RSS máximo de 73.436 KiB (incluye Python y scrypt).
- CLI/API: `all_available` delega selección por defecto correctamente; `selective` exige categorías explícitas.

Validación final: `tests/*.sh` 49/49 PASS; AST Python 16/16; ShellCheck PASS; shfmt PASS; `git diff --check` PASS.

**Consideración operativa pendiente:** tras una terminación no capturable (`os._exit`/SIGKILL), el proceso no puede ejecutar `finally`; puede quedar un staging privado sin destino publicado. La matriz demuestra que el residuo es privado y no contiene un ZIP en claro, pero no se implementó un recolector automático de staging huérfano. No se borrarán esos directorios de forma heurística mientras pueda existir otro proceso activo.

El writer continúa **IMPLEMENTADO LOCALMENTE / VERIFICADO EN AISLAMIENTO / NO PUBLICADO / NO ACEPTADO FORMALMENTE**. No se ejecutó backup real ni se accedió a master.key/secretos reales; no restore, verify independiente ni runtime apply. `Xray-Normativa/` intacta. Rama `design/user-identity-association-v1`, HEAD `ec9b306b38f0bce17f28c301c47df3b3d092785a`; sin commit/push ni sincronización GitHub.

## Estado actualizado — 2026-11-03

El snapshot writer cuenta con recuperación segura de staging implementada localmente: passphrase validada antes de staging, coordinación persistente y lock individual de propietario. La recuperación sólo retira staging abandonados seguros; preserva staging activos y estructuras no reconocidas. Se mantiene el orden de locks de datos. Validación: suite focal PASS; `bash tests/*.sh` PASS; AST 16/16; ShellCheck, shfmt y diff-check PASS; RSS aislado 74.120 KiB. No aceptado formalmente, no publicado. No se creó backup real ni se accedió a secretos/master.key; no restore ni runtime apply. Rama de desarrollo y HEAD sin cambios; `Xray-Normativa/` intacta.

## Actualización — auditoría de coordinación/manifiesto (2026-11-03)

Se corrigió localmente el lock de coordinación para rechazar archivos inseguros sin alterar metadatos compartidos; se añadió creación exclusiva y validación de identidad del descriptor. Se completaron validaciones de UUID v4, timestamp UTC, estructura, categorías, miembros y completitud del manifiesto. Nuevas pruebas cubren hardlink/symlink/FIFO/modo, timeout y entradas inválidas. Regresión: 49/49 scripts PASS; AST 16/16; `bash -n`, ShellCheck, shfmt y diff-check PASS. Writer continúa NO PUBLICADO y NO ACEPTADO FORMALMENTE. No se creó backup real ni se accedió a datos secretos; no restore, verify independiente ni runtime apply.


## Publicación del snapshot writer v1 — 2026-11-03

El snapshot writer, su suite de pruebas, las ampliaciones requeridas del ZIP streaming/API y los documentos técnicos de continuidad se publicaron en design/user-identity-association-v1, commit ae8a7a089809e2e1913c14a714f45d956f8a5a1d, verificado como HEAD remoto el 2026-11-03.

La publicación no equivale a aceptación formal. El writer permanece NO ACEPTADO hasta completar la revisión de aceptación y obtener aprobación expresa. Regresión local: 49/49 scripts PASS; AST 16/16; bash -n, ShellCheck, shfmt y git diff --check PASS. Xray-Normativa/ permanece intacta; scripts/__pycache__/ se excluyó del commit.


## Actualización — segunda revisión de aceptación del snapshot writer (2026-11-03)

Por autorización expresa del propietario se corrigieron los hallazgos B-01, B-02 y B-03:

- **B-01:** allowlist estricta para los campos de identidades/asociaciones. Snapshot v1 sólo conserva asociaciones VLESS/VMess saneadas; WireGuard y otros protocolos fuera del alcance se excluyen íntegramente y quedan identificadas como causa de PARTIAL; campos inesperados o sensibles (incluidas variantes de claves privadas y pre-shared keys) bloquean la operación.
- **B-02:** la limpieza no silencia fallos. Se cierra el descriptor del propietario incluso cuando falla la limpieza y se informa FAILED, distinguiendo si el paquete ya alcanzó el punto de publicación.
- **B-03:** el manifiesto sólo admite versión 1; included y unsupported deben resolver exactamente las categorías solicitadas. Se valida la estructura de resources, members, exclusions, dependencies y source_snapshot antes de acceder a sus campos.
- **Interrupciones:** la matriz ejecuta el crash del prompt (sin staging), cifrado, antes del enlace final y después del enlace exclusivo pero antes del fsync del directorio.
- **Pruebas de cleanup:** fallos inyectados de lock de coordinación, unlink, rmdir y fsync. Se comprueba cierre de owner_fd, preservación del paquete publicado y retorno FAILED.

**Verificación ejecutada en VPS:** 49/49 tests/*.sh PASS; AST Python 16/16; bash -n en 74 archivos; ShellCheck focal PASS; shfmt focal PASS; git diff --check PASS. La comparación normativa sigue 14/14 hashes SHA-256 idénticos a la copia maestra.

**Estado separado:** base del writer PUBLICADA en commit ae8a7a089809e2e1913c14a714f45d956f8a5a1d; correcciones B-01/B-02/B-03 y pruebas actuales IMPLEMENTADAS/VERIFICADAS localmente en /opt/xray-manager, pero SIN COMMIT, SIN PUSH y SIN SINCRONIZACIÓN. El writer sigue **NO ACEPTADO FORMALMENTE** hasta revisión y aprobación expresa del propietario. No se creó backup real, no se leyó master.key ni secretos reales, no se ejecutó restore/verify independiente y no se tocó runtime. Xray-Normativa permanece intacta.


## Registro histórico SUPERADO — publicación B-01/B-02/B-03 y bloqueo A-16 — 2026-11-03

- Autorización expresa recibida para publicar B-01/B-02/B-03 en `design/user-identity-association-v1`, manteniendo Snapshot Writer v1 como **NO ACEPTADO**.
- A-16 bloquea la aceptación: tras `os.link(package.tmp, final_path)`, el inode legítimo tiene `st_nlink == 2`; `_recover_orphan_staging()` exige 1 y rechaza la recuperación del staging post-publicación. La prueba sintética reprodujo el rechazo conservando staging y paquete final.
- Los tests actuales no ejercitan el recuperador sobre el estado post-link ni demuestran recuperación tras fallos de cleanup equivalentes.
- La corrección A-16 no está autorizada/implementada en este punto; requiere preservar el rechazo de hardlinks arbitrarios y validar de forma segura la correspondencia exacta entre staging y artefacto final.
- No crear backup real, no leer `master.key`/secretos, no restore/verify independiente, no runtime apply. `Xray-Normativa/` permanece inmutable.

- Publicación B-01/B-02/B-03: commit `b6582da` en `origin/design/user-identity-association-v1` (2026-11-03). La publicación no implica aceptación; A-16 sigue bloqueante.

## A-16 — corrección implementada localmente, auditoría pendiente (2026-11-03)

- Se agregó marcador de publicación publication.json root:root 0600, nlink == 1, durable antes de os.link, con destino exacto, device/inode, tamaño y SHA-256.
- Recuperación post-link sólo acepta package.tmp nlink == 2 cuando el marcador coincide y el destino es el mismo archivo regular root:root 0600, con exactamente dos enlaces y hash coincidente. Retira sólo el enlace de staging y valida el destino final con nlink == 1.
- Recuperación idempotente tras crash posterior al unlink de package.tmp. Hardlinks arbitrarios sin marcador, nlink > 2, destino diferente y estructura insegura bloquean.
- Verificación posterior: tests/*.sh 49/49 PASS; AST 16/16; bash -n 74 archivos; ShellCheck PASS; shfmt focal PASS; git diff --check PASS; normativa 14/14 hashes coincidentes. A-16 pasa. Snapshot Writer v1 continúa NO ACEPTADO formalmente.

## Publicación A-16 — 2026-11-03

- Commit: `40c907e2a9da639f3458547e09fec6f26fdac5e1` en `origin/design/user-identity-association-v1`.
- Publicación verificada por SHA remoto; `/opt/xray-manager` corresponde al mismo HEAD y está limpio.
- Writer: IMPLEMENTADO / VERIFICADO EN AISLAMIENTO / PUBLICADO / SINCRONIZADO / NO ACEPTADO FORMALMENTE.
- No se modificó `main` ni `Xray-Normativa/`. No backup real, secretos/master.key, restore/verify independiente ni runtime apply.


## Estado vigente — cierre técnico de aceptación A-01–A-19 (2026-11-03)

- Matriz de trazabilidad completa documentada en `docs/PLAN_BACKUP_RESTORE_CENTRAL.md` §10.20. Se recuperaron los nombres originales de los 19 criterios y se enlazaron con sus pruebas versionadas; A-01–A-15 y A-17–A-19 conservan su resultado PASS de la auditoría previa y la regresión actual volvió a ejecutarse.
- A-16: diez negativos nuevos para marcador malformado/no canónico, hash/device/inode/tamaño alterados, campo extra, symlink, hardlink y modo inseguro. Cada caso confirma bloqueo fail-closed y preservación de la evidencia. No requirió modificar el código del writer.
- Verificación actual: 49/49 scripts PASS; AST 16/16; `bash -n` 74 archivos; ShellCheck PASS; shfmt PASS; `git diff --check` PASS; RSS focal 76.336 KiB. Normativa 14/14 hashes coincidentes con la copia maestra; `README.md` es archivo adicional no normativo.
- Rama `design/user-identity-association-v1`; base verificada `b1e2ef4537eafeacefd5584a7fde5c9fd02626a9`. La matriz y los diez negativos A-16 se publicaron en `101853e6ef0990686128f45561b22e1cd4248aea`; el registro final de publicación quedó en `7f03efcf080465d8bced447549e29f8abb95248b`. VPS y GitHub comparten el HEAD final.
- `Xray-Normativa/` no se modificó. No backup real, no acceso a `master.key`/secretos, no restore/verify independiente, no runtime apply.
- Estado: A-01–A-19 PASS en pruebas aisladas/sintéticas; Snapshot Writer v1 **NO ACEPTADO FORMALMENTE**. La aceptación formal requiere decisión expresa del propietario y no se infiere de pruebas o publicación.


## Estado vigente — aceptación formal del Snapshot Writer v1 — 2026-11-03

El propietario aceptó formalmente el **Snapshot Writer v1**, con las limitaciones expresamente documentadas en la matriz A-01–A-19 y en este plan. Esta aceptación cierra el componente Snapshot Writer v1; no equivale a certificar el flujo integral de backup/restore ni autoriza operaciones reales.

**Alcance de la aceptación:** implementación v1 para las categorías soportadas y sus contratos de captura, manifiesto, ZIP streaming, cifrado, publicación, limpieza y recuperación; resultados A-01–A-19 PASS en pruebas aisladas/sintéticas; correcciones B-01/B-02/B-03 y A-16 incluidas.

**Limitaciones que permanecen vigentes:**
- No se ha ejecutado un backup real sobre datos del usuario.
- No se ha ejecutado restore ni verify independiente de un backup real.
- No se ha leído `master.key` ni secretos reales.
- No se ha aplicado el Writer al runtime ni modificado servicios, firewall, puertos o certificados desplegados.
- Los PASS acreditan pruebas aisladas/sintéticas; no constituyen evidencia de operación real ni conectividad extremo a extremo.
- Categorías/protocolos fuera del alcance v1 se excluyen y pueden producir `PARTIAL`; `BLOCKED` y `FAILED` conservan sus semánticas documentadas.
- Se mantienen los límites de 10.000 entradas ZIP y 512 MiB.

**Decisión:** Snapshot Writer v1 = **ACEPTADO FORMALMENTE CON LIMITACIONES DOCUMENTADAS**. Backup/restore integral y sus verificaciones reales permanecen pendientes y no se declaran aceptados por esta decisión. La Etapa 2 del proyecto permanece ABIERTA conforme a la regla de auditoría integral de cierre de etapas.


## Estado vigente — primera validación live de Xray-core y VLESS-WS (2026-11-03)

- Xray-core 26.10.31 instalado en la VPS de desarrollo desde el menú real del administrador. Release oficial, SHA-256, versión del binario y geodata verificados.
- Se corrigió únicamente el modo de /var/lib/xray-manager/connections de 750 a 700, conforme a la política de install.sh y al contrato del almacén VLESS.
- Conexión Prueba-VLESS-WS-Real (conn-1793749234-670662), modalidad vless_ws, escucha prevista 0.0.0.0:10001, path /ws, seguridad none, capacidad 1. Revisión neutral 1 persistida, estado draft y runtime_applied=false.
- Usuario de prueba creado mediante el gestor legacy VLESS porque el registro live continúa en formato arreglo JSON. UUID omitido de la documentación.
- Previsualización, recuperación y validación con el binario instalado: Configuration OK. Audit del almacén sin referencias rotas ni archivos huérfanos.
- Xray permanece inactivo; no existe /etc/xray/config.json ni xray.service; no hay listener en 10001. Sin runtime apply, firewall, apertura de puertos ni prueba cliente externa/WAN.
- Xray advierte que WebSocket está obsoleto/no recomendado y recomienda XHTTP H2/H3.
- Evidencia: docs/VALIDACION_LIVE_XRAY_VLESS_WS_2026-11-03.md.
- Código sin cambios. Documentación de continuidad actualizada localmente, todavía sin commit/push/sync. Xray-Normativa y main intactas.

**Siguiente punto:** diseñar y autorizar el flujo de aplicación de configuración al runtime. La inspección del menú no encontró una acción de aplicación para esta conexión. Etapa 2 permanece ABIERTA; la aceptación del Snapshot Writer v1 y la prueba de instalación no implican aceptación ni activación del runtime.

## Estado vigente — staging de candidatos runtime por perfil (2026-11-03)

- Decisión del propietario: opción A; respetar Etapa 5. La activación sólo podrá ocurrir mediante el flujo de cambio de perfil activo. No crear una ruta de activación para conexiones independientes.
- Auditoría: no se encontró implementación funcional del gestor de perfiles en modules/scripts/config. Existe directorio preparado por install.sh, pero no módulo, menú ni esquema operativo. Los adaptadores VLESS/VMess construyen configuraciones por conexión, no una configuración integral de perfil.
- Se implementó localmente scripts/xray_runtime_candidates.py y tests/xray_runtime_candidates.sh. La primitiva valida JSON y Xray nativo sobre los mismos bytes que almacena, limita tamaño, rechaza symlinks/hardlinks/traversal, usa bloqueo, almacén privado 0700, archivos 0600, SHA-256 y manifiesto perfil/revisión. No sobrescribe revisiones existentes.
- Esta primitiva sólo realiza STAGING. No publica /etc/xray/config.json, no prepara systemd/cuenta de servicio, no inicia Xray, no habilita autostart y no cambia red.
- Prueba focal sintética PASS. Aún pendiente repetir con binario real sobre un candidato sintético y ejecutar regresión integral.
- Diseño y límites: docs/DISENO_IMPLEMENTACION_RUNTIME_PERFILES.md.
- La conexión Prueba-VLESS-WS-Real sigue draft y runtime_applied=false. No se ha aplicado al runtime ni probado desde cliente externo.
- Sin commit/push/sync; conservar cambios locales preexistentes. Xray-Normativa/ y main intactas.
- Siguiente dependencia: diseñar/implementar el subsistema de perfiles y su flujo de activación antes de integrar publicación runtime. Etapa 2 sigue ABIERTA.

### Nota de seguridad de regresión

Se corrigió el fixture de tests/users.sh para que las recargas de módulos sigan usando rutas temporales y nunca consulten los datos live. La ejecución previa se detuvo por límite de capacidad y no modificó el archivo real de usuarios. El staging runtime se endureció para exigir root, directorios/lock root-owned y binario Xray root-owned no modificable por grupo/otros.

### Verificación final de la infraestructura de candidatos runtime

- Pruebas automatizadas: 50/50 scripts PASS.
- Python AST: 18/18 PASS.
- bash -n: todos los archivos shell del proyecto PASS.
- ShellCheck y shfmt: prueba nueva focal PASS.
- git diff --check PASS.
- Xray-core 26.10.31 real validó una configuración sintética temporal; resultado STAGED, sin publicación runtime ni arranque.
- Comparación normativa: 14/14 archivos normativos coinciden con la copia maestra; README.md se excluye por ser auxiliar.
- No commit/push/sync. La rama y HEAD no cambiaron.
## Actualización de publicación — infraestructura de candidatos runtime (2026-11-03)

Por autorización expresa del propietario, se publica en GitHub la implementación y documentación de staging de candidatos runtime por perfil, junto con la corrección de aislamiento de `tests/users.sh` y los informes de validación live y diseño. Esta publicación no cambia la decisión de opción A ni habilita runtime.

Archivos incluidos: `scripts/xray_runtime_candidates.py`, `tests/xray_runtime_candidates.sh`, `tests/users.sh`, `docs/DISENO_IMPLEMENTACION_RUNTIME_PERFILES.md`, `docs/VALIDACION_LIVE_XRAY_VLESS_WS_2026-11-03.md`, `PROJECT_STATE.md`, `docs/CONTINUIDAD_DEL_PROYECTO.md`, `docs/PUNTO_CONTROL_ACTUAL.md` y `HISTORY.md`.

Se excluye deliberadamente `scripts/__pycache__/` por ser un artefacto local de Python. No se modifica `Xray-Normativa/`, `main`, el servicio Xray, la configuración runtime, firewall, puertos ni certificados. Etapa 2 continúa ABIERTA; el subsistema de perfiles aún no está implementado y el staging no es activación.

## Estado vigente — almacén de perfiles v1.1 cifrado (2026-11-03)

- El propietario eligió explícitamente AES-256-GCM para el almacenamiento de las configuraciones de perfil, en lugar del texto plano de la primera implementación local. La primera implementación plaintext no fue publicada y se corrigió antes de sincronizar.
- `scripts/xray_profiles.py` cifra el JSON completo de cada revisión en `config.enc.json` con AES-256-GCM. Nonce aleatorio de 12 bytes; AAD vincula versión, `profile_id` y revisión; envelope versionado; manifiesto conserva tamaño del plaintext, tamaño almacenado y SHA-256 del ciphertext. Sólo el ciphertext se escribe en el almacén.
- La clave se carga desde la clave maestra existente (`/etc/xray-manager/keys/master.key` por defecto) mediante `certificate_crypto.load_master_key`. No se crea, lee ni modifica la clave real durante las pruebas; no hay fallback plaintext. Clave ausente/inválida, ciphertext alterado o AAD/identidad incorrectos provocan fallo cerrado.
- Las pruebas focales usan claves sintéticas temporales y cubren ausencia de clave sin creación automática, no exposición del marcador secreto, descifrado, copia independiente con AAD nuevo, clave incorrecta, alteración GCM, versionado, restauración no destructiva, concurrencia y controles de filesystem.
- Operaciones funcionales disponibles: crear desde cero/JSON, consultar, modificar, duplicar, renombrar, historial y restauración como nueva revisión. Eliminar sigue deshabilitado; no hay validación Xray nativa, composición integral, registro activo ni activación.
- Los manifests con formato plaintext/no reconocido se rechazan fail-closed. No hay migración automática. La inspección confirmó que `/var/lib/xray-manager/profiles` no existe, por lo que no hay perfiles live que migrar.
- Protección filesystem: directorios root:root 0700 y archivos root:root 0600; escritura atómica/fsync y lock. La pérdida de la clave maestra impediría recuperar perfiles; rotación/recuperación de clave sigue pendiente.
- Diseño: `docs/DISENO_IMPLEMENTACION_PERFILES.md`. Normativa contrastada: `Xray-Normativa/05_Configuraciones_Perfiles/Etapa_5_Configuraciones_Perfiles.md` y YAML; no se modificó `Xray-Normativa/`.
- No se creó `/var/lib/xray-manager/profiles`, no se leyó/usó `master.key` real, no se alteró la conexión VLESS live ni se tocó runtime, systemd, firewall, puertos, certificados o red.
- Verificación ejecutada: `tests/*.sh` 51/51 PASS; Python AST 18/18; `bash -n` global PASS; ShellCheck focal PASS; shfmt de los dos archivos nuevos PASS; `git diff --check` PASS.
- Estado de esta entrega: IMPLEMENTADA, VERIFICADA EN PRUEBAS SINTÉTICAS, PUBLICADA y SINCRONIZADA byte a byte en `design/user-identity-association-v1`; aceptación formal del subsistema pendiente. Commit funcional inicial `03b63ca109a2fabb262924daf5d2fe4a683b23d8`; commit de reconciliación byte a byte `4cec7496585390adbe72d8887cb6dacd94743c32`. La actualización documental final también quedó publicada.
- Verificación de publicación: árbol Git de la VPS y árbol remoto idénticos; `main` sin cambios; `Xray-Normativa/` sin cambios (el README auxiliar sigue siendo el único archivo extra frente al respaldo). `scripts/__pycache__/` permanece local y excluido.

**Siguiente paso:** revisión del propietario y aceptación formal del subsistema o indicación de ajustes. No activar perfiles ni ejecutar pruebas con secretos reales. Etapa 2 continúa ABIERTA.


## Estado vigente — validación live de lectura del lease VMess TLS por Xray real (2026-11-03)

- Evidencia compartida por el propietario: Xray-core 26.10.31 se ejecutó realmente bajo UID 999/GID 988 y accedió al certificado y a la clave sintéticos del lease.
- La segunda ejecución completó un handshake TLS 1.3 verificado. La primera ejecución no se contabiliza como exitosa; la causa no se infiere porque no se dispone de la salida íntegra.
- Esta prueba demuestra lectura de los materiales sintéticos por un proceso Xray real bajo la identidad indicada. No demuestra despliegue de `xray.service`, aplicación del runtime desde el administrador, activación por perfil, conectividad externa/WAN ni uso de certificados reales.
- Informe: `docs/VALIDACION_LIVE_VMESS_TLS_LEASE_2026-11-03.md`. La implementación VMess TLS sigue parcial y su aceptación formal permanece pendiente; Etapa 2 continúa ABIERTA.

## Punto de reanudación vigente — revisión formal de perfiles v1.1 (2026-11-03)

- El almacén de perfiles v1.1 con AES-256-GCM está IMPLEMENTADO, VERIFICADO EN PRUEBAS SINTÉTICAS, PUBLICADO y SINCRONIZADO byte a byte en `design/user-identity-association-v1`. La aceptación formal del subsistema sigue pendiente.
- Siguiente actividad autorizada por el propietario: revisión documental y técnica de solo lectura contra `Xray-Normativa/05_Configuraciones_Perfiles/Etapa_5_Configuraciones_Perfiles.md` y su YAML, inspeccionando implementación, pruebas, límites y trazabilidad. No modificar código durante la revisión.
- No usar `master.key` real, no crear perfiles live, no activar runtime, no habilitar eliminación ni modificar servicios, firewall, puertos, certificados o red.
- Tras presentar hallazgos, solicitar decisión formal del propietario: aceptar el subsistema con límites o autorizar correcciones concretas. Etapa 2 permanece ABIERTA.


## Estado vigente — auditoría formal de perfiles v1.1 (2026-11-03)

- Revisión de solo lectura contra Etapa 5 Markdown/YAML completada. Se inspeccionaron `scripts/xray_profiles.py`, `modules/profiles.sh`, integración de menú, `tests/xray_profiles.sh` y diseño.
- Verificaciones actuales: `tests/xray_profiles.sh`, `tests/stage1_menu.sh`, `tests/smoke.sh`, AST Python, Bash syntax, ShellCheck focal y `git diff --check`: PASS. La regresión histórica 51/51 no se repitió completa en esta auditoría.
- **PF-01 BLOQUEANTE:** fallo reproducido con fault injection: si `update()` guarda metadatos y falla al guardar catálogo, queda discrepancia y `list_profiles()` falla.
- **PF-02 ALTO:** operaciones multiarchivo (`create`, `duplicate`, `rename`, `update`, `restore`) carecen de transacción recuperable completa; hay ventanas de rename/replace/fsync y rollback que requieren diseño y pruebas de crash/fallo.
- Pendientes funcionales frente a Etapa 5: vista previa/diff, validación Xray por revisión e informes, creación desde configuración independiente, comparación de revisiones, historial de modificaciones, retención, registro activo, composición integral, activación/verificación/rollback y backup/restore. La eliminación permanece deshabilitada deliberadamente.
- Se corrigió la documentación del manifiesto: el código guarda `ciphertext_sha256` y `plaintext_size_bytes`, no SHA-256 del plaintext.
- Informe: `docs/AUDITORIA_FORMAL_PERFILES_V1_1_2026-11-03.md`.

**Estado:** IMPLEMENTADO y PUBLICADO/SINCRONIZADO; pruebas focales PASS; **NO ACEPTADO FORMALMENTE** por PF-01/PF-02. No se modificó código ni normativa; no se leyó la clave maestra real ni se creó almacén/perfil live.

**Siguiente paso:** esperar autorización expresa para corregir PF-01/PF-02 y añadir fault injection/crash recovery en almacén temporal. No ejecutar cambios sobre runtime ni secretos reales. Etapa 2 permanece ABIERTA.


## Fase correctiva PF-01/PF-02 — implementación local bajo prueba (2026-11-03)

- Autorización del propietario recibida para corregir consistencia transaccional y probar fault/crash recovery.
- Implementado localmente `.profiles.transaction.json` (WAL) con snapshots de catálogo/metadatos, whitelist de rutas, rollback idempotente y recuperación automática al adquirir el lock.
- Integrado en create/duplicate/rename/update/restore; sincronización explícita de `profiles/` tras publicar directorios nuevos; limpieza de directorios/revisiones no confirmados.
- Pruebas nuevas cubren fallo de escritura de catálogo, fallo de fsync después de replace, crash entre escrituras, crash después de ambos replaces antes de retirar WAL, interrupción durante rollback y recuperación al reabrir.
- `tests/xray_profiles.sh` PASS; regresión completa posterior a la última modificación: 51/51 scripts PASS; Python AST, Bash syntax, ShellCheck focal y `git diff --check` PASS.
- Estado: cambios locales NO PUBLICADOS; PF-01/PF-02 no se cierran hasta completar revisión final del diff y sincronización GitHub.
- Límites: no se usa clave maestra real ni almacén live; no se crean perfiles reales ni se toca runtime/servicios/firewall/puertos/red. Temporales ocultos huérfanos anteriores al journal no se limpian automáticamente en esta fase.
## Estado vigente — limpieza segura de temporales huérfanos (2026-11-04)

- Checkout de trabajo: /opt/xray-manager, rama design/user-identity-association-v1, HEAD base 3f8f88d8146409acfdf457529ce53075242a5bcd; cambios de esta fase aún locales.
- scripts/xray_profiles.py: locked() recupera WAL y después limpia temporales huérfanos bajo lock exclusivo. atomic_write() elimina su temporal propio ante fallo de replace/fsync sin borrar el destino publicado.
- Limpieza limitada a .new-<16 hex>, .revision-<16 hex> y .<destino>.<16 hex>.tmp en rutas y destinos explícitos. Validación con lstat, root:root, modos 0700/0600, nlink=1 y estructura acotada. Candidatos sospechosos se preservan y notifican.
- tests/xray_profiles.sh: pruebas de SIGKILL en procesos hijos, recuperación en siguiente operación, idempotencia, symlink/modo/owner/hardlink sospechosos preservados, revisión publicada intacta y destino conservado ante fallo de fsync posterior a replace.
- Verificación: regresión tests/*.sh 51/51 PASS; Python AST 18/18; Bash syntax; ShellCheck focal (exclusiones SC2251/SC2034 preexistentes); shfmt focal; git diff --check.
- Sin almacén live ni claves reales: no se accedió a master.key, no se creó/limpió /var/lib/xray-manager/profiles y no se modificó runtime, systemd, firewall, puertos, certificados o red.
- Estado de publicación: cambios locales, revisión final y sincronización GitHub pendientes. No declarar aceptación formal de perfiles ni cierre de Etapa 5/Etapa 2.
## Actualización de perfiles v1.1 — consolidación WAL (2026-11-04)

- La remediación transaccional PF-01/PF-02 y la limpieza de temporales huérfanos están implementadas y publicadas en `design/user-identity-association-v1` (base publicada `4dc4570dd81d49a8201af62a66ca58b07c89dd99`).
- Endurecimiento adicional local en curso: recuperación WAL con validación integral de todas las entradas, snapshots, destinos y directorios de rollback antes de cualquier mutación. Journals inválidos se conservan y fallan cerrados.
- Pruebas añadidas: entrada inválida tardía y directorio de rollback inválido no deben causar rollback parcial; se comprueba conservación byte a byte del catálogo y del journal.
- PF-01/PF-02: CORREGIDOS dentro del alcance probado. PF-06: cobertura ampliada pero no exhaustiva. PF-07: pendiente de revisión.
- La auditoría formal se actualizó en `docs/AUDITORIA_FORMAL_PERFILES_V1_1_2026-11-03.md`; el diseño en `docs/DISENO_IMPLEMENTACION_PERFILES.md`.
- La aceptación formal del almacén de perfiles sigue pendiente de decisión expresa. No se cierra Etapa 5 ni Etapa 2.
- Restricciones: no usar `master.key` real; no crear/alterar perfiles live; no tocar runtime, servicios, firewall, puertos, certificados, red, `main` o `Xray-Normativa/`.

## PF-07 — validación estricta de catálogo (2026-11-04)

- `load_catalog()` valida esquema raíz, versión entera estricta (rechaza `bool`), lista acotada a 10000, campos exactos por registro, ID, nombre normalizado, timestamps UTC reales, orden temporal y unicidad de ID/nombre.
- Se eliminaron coerciones de tipo que podían ocultar datos malformados y producir excepciones incidentales. Los errores de esquema se reportan como `ProfileError`; la lectura inválida no modifica el archivo.
- Prueba focal ampliada con 18 casos malformados y control de preservación byte a byte.
- PF-07: CORREGIDO dentro del contrato y pruebas documentados. Verificación: 51/51 scripts, AST 18/18, bash -n, ShellCheck focal, shfmt y git diff --check PASS. Publicado y sincronizado en `85c637c93778780c98589dc2f791b190daeedfd6` sobre `design/user-identity-association-v1`; árbol limpio. No se declara aceptación formal ni cierre de Etapa 5/Etapa 2.

## Correcciones PF-08/PF-09/PF-10 del almacén de perfiles — 2026-11-04

Autorización del propietario aplicada en la rama design/user-identity-association-v1, host Implementación-Xray, ruta /opt/xray-manager.

- PF-08: validación previa de tipos, límites y texto imprimible de descripción/notas; configuración validada antes de publicar una nueva revisión. Cuatro casos negativos verifican que no se crea revisión huérfana.
- PF-09: reconciliación bajo lock de revisiones definitivas posteriores al current_revision confirmado. Sólo se elimina una revisión con directorio/archivos seguros, contenido exacto y manifiesto coherente; artefactos no verificables se preservan y reportan.
- PF-10: contrato estricto de metadatos: conjunto exacto de campos, tipos no coercitivos, fechas UTC reales, límites y caracteres de texto, IDs de revisión y coherencia de estado/punteros.

Pruebas focales: tests/xray_profiles.sh PASS; PF-08 cuatro casos, PF-09 SIGKILL después del rename y recuperación en la siguiente operación, PF-10 dieciocho metadatos malformados rechazados. Python AST 18/18, py_compile del módulo modificado, bash -n global, ShellCheck focal y git diff --check PASS. shfmt -d -i 4 tests/xray_profiles.sh muestra diferencias de estilo preexistentes (indentación de bloques if en el archivo); no se reformateó el archivo completo para evitar cambios ajenos al alcance.

Informe: docs/AUDITORIA_CORRECCIONES_PF08_PF09_PF10_2026-11-04.md. Regresión general tests/*.sh finalizada: 51/51 scripts PASS (exit code 0).

Límites: sólo almacenes temporales y claves sintéticas. No se leyó master.key, no se crearon perfiles live, no se tocó runtime/servicios/certificados/firewall/puertos/red. Xray-Normativa/ y main intactas. No publicado en GitHub; publicación requiere autorización expresa posterior. Almacén v1.1 no aceptado formalmente; Etapa 5 y Etapa 2 siguen ABIERTAS.

Sincronización GitHub/VPS de desarrollo completada el 2026-11-04: commit 46444bcf11b41750d45f2187d77eeb5f7fce654c publicado en origin/design/user-identity-association-v1. El checkout /opt/xray-manager del host Implementación-Xray quedó en ese mismo commit, con árbol limpio. main y Xray-Normativa/ sin cambios.

## Estado vigente — remediación PF-11/PF-12 del almacén de perfiles (2026-11-04)

- Autorización expresa del propietario recibida para corregir PF-11/PF-12 en `design/user-identity-association-v1`, con pruebas aisladas y actualización documental. No incluye VPS de pruebas ni runtime.
- PF-11 implementado: contrato estricto del manifiesto (campos exactos, versión entera exacta, identidad, fecha UTC, config/crypto metadata, tamaños, SHA-256, origen y estados de validación coherentes). La lectura de revisión valida el manifiesto antes de comprobar ciphertext y descifrar.
- PF-12 implementado: después de WAL, temporales y revisiones huérfanas, el lock exclusivo reconcilia directorios de perfil definitivos no presentes en un catálogo existente/seguro. Sólo retira candidatos cuya estructura, permisos, identidad, metadatos y revisión cifrada se verifican íntegramente.
- Regla conservadora: si el catálogo falta (p. ej. caída en el primer alta), está inseguro o no se puede verificar, no se eliminan perfiles por inferencia. Candidatos ambiguos/inseguros se preservan y notifican; la inspección previa `lstat` evita reparación automática de sus permisos.
- `tests/xray_profiles.sh`: PASS; 13 casos de manifiesto malformado, SIGKILL real en create/duplicate, alta inicial sin catálogo preservada y candidato inseguro preservado sin reparación de permisos.
- Diseño y auditoría: `docs/DISENO_IMPLEMENTACION_PERFILES.md` §16 y `docs/AUDITORIA_CORRECCIONES_PF11_PF12_2026-11-04.md`.
- Regresión integral posterior a la última modificación: `tests/*.sh` **51/51 PASS**, exit code 0. AST Python, Bash syntax, ShellCheck focal y `git diff --check` PASS.
- Sin aceptación formal del almacén. PF-11/PF-12 no cierran Etapa 5; siguen pendientes las funciones normativas de validación Xray por revisión, preview/diff, comparación, historial/retención, composición integral, registro activo, activación/rollback y backup/restore. Etapa 5 y Etapa 2 permanecen ABIERTAS.
- Restricciones: pruebas sólo con almacenes temporales y claves sintéticas. No se leyó `master.key`, no se creó/alteró perfil live, runtime, systemd, certificados, firewall, puertos o red. No se tocó `Vps de Pruebas`. `Xray-Normativa/` y `main` sin cambios.
- Publicación GitHub: pendiente de revisión final del diff y confirmación del estado de regresión; no se ha creado commit/push.


## PF-06 — cobertura criptográfica/filesystem ampliada (2026-11-04)

- Se añadieron pruebas que alteran ciphertext y recalculan el SHA-256 del manifiesto para alcanzar el control de autenticidad AES-256-GCM; el blob adulterado es rechazado y los artefactos originales vuelven a leerse tras restaurarlos.
- Fault injection añadido: escritura parcial (`os.write`), `fsync` de archivo antes de replace y `unlink` del WAL después de publicar destinos. Se comprueba destino intacto, limpieza de temporales o rollback/recuperación, según el caso.
- Se mantienen casos de fallo de replace, fsync de directorio y SIGKILL/crash recovery.
- `tests/xray_profiles.sh` PASS; regresión `tests/*.sh` **51/51 PASS**. Sólo se modificaron pruebas y documentación; código de producción intacto.
- PF-06: CERRADO DENTRO DEL ALCANCE DE ESCENARIOS DOCUMENTADOS; no se afirma cobertura combinatoria exhaustiva ni fallos físicos del almacenamiento.
- Informe: `docs/AUDITORIA_PF06_COBERTURA_CRIPTO_FILESYSTEM_2026-11-04.md`. Diseño §17.
- Almacén v1.1 aún no aceptado formalmente; Etapa 5 y Etapa 2 ABIERTAS. Sin commit/push/sync. Sin secretos ni runtime live.

## Decisión vigente — aceptación limitada del almacén de perfiles v1.1 (2026-11-04)

El propietario aceptó formalmente el almacén de persistencia de perfiles v1.1 **como componente limitado**, circunscrito a los contratos, controles y escenarios implementados/auditados/probados. Se aceptan los controles de cifrado y autenticidad, contratos estrictos de catálogo/metadatos/manifiestos, revisiones inmutables, transacciones WAL y recuperación, limpieza/reconciliación conservadora de artefactos huérfanos, locking/permisos y pruebas documentadas PF-01/PF-02 y PF-06 a PF-12. La aceptación no amplía los límites de cobertura de cada informe.

**No equivale a completar Etapa 5 ni Etapa 2. Ambas permanecen ABIERTAS.** Siguen pendientes, entre otros: preview/diff de importación y modificación, creación desde configuración independiente, validación estática Xray por revisión e informe, comparación de revisiones, historial separado y retención, registro/composición de perfil activo, eliminación segura integrada, activación/verificación/rollback y backup/restore integral.

Los estados not_validated y not_integrated siguen vigentes; no se afirma validación Xray, activación ni conectividad extremo a extremo. Pruebas sintéticas no equivalen a cobertura combinatoria exhaustiva ni a pruebas de fallos físicos.

No se leyó master.key, no se tocó almacén/perfil live, runtime, servicios, systemd, certificados, firewall, puertos o red. Vps de Pruebas, main y Xray-Normativa/ permanecen fuera del alcance. Documentación actualizada localmente, sin commit/push/sync.

## Diseño siguiente — gestor de configuraciones independientes (2026-11-04)

Se contrastó la normativa aprobada de Etapa 5 §§2–5 y 14 (Markdown/YAML) con el código actual. No existe un gestor de configuraciones JSON independientes: los almacenes VLESS/VMess existentes guardan configuraciones asociadas a conexiones, y el almacén v1.1 guarda copias pertenecientes a perfiles; no deben confundirse ni reutilizarse como catálogo independiente.

Se preparó docs/DISENO_GESTOR_CONFIGURACIONES_INDEPENDIENTES.md. Propone un almacén separado, versionado, AES-256-GCM, WAL, importación/exportación segura, preview, diff y comparación, con estados Borrador/Validada/Anterior y sin operación de activación. La validación estática y los informes se mantienen como componente separado; la integración de creación de perfil desde configuración independiente copiará bytes y no sincronizará ambos objetos.

Estado: diseño propuesto, no implementado. La implementación C-01/C-02 requiere autorización expresa. No se modificó código funcional, dependencias, normativa, almacén live, runtime, servicios, red, certificados, firewall o puertos. Sin commit/push/sync.

## C-01 — gestor de configuraciones independientes implementado localmente (2026-11-04)

Autorización de continuidad recibida para iniciar C-01 conforme al diseño aprobado para esta fase. En `scripts/xray_configurations.py` se implementó un almacén separado con `create` (vacío/plantilla mínima), `list` y `show`; catálogo, metadatos y manifiesto estrictos; IDs propios; revisiones inmutables; AES-256-GCM con nonce de 12 bytes y AAD por ID/revisión; hash de ciphertext; permisos root-only; lock y WAL con recuperación conservadora. La publicación del directorio definitivo ocurre después de persistir WAL, de modo que SIGKILL antes/durante/después de la publicación puede revertirse en el siguiente lock.

Pruebas nuevas en `tests/xray_configurations.sh`: plantillas, permisos, catálogo malformado, clave errónea/ausente, ciphertext manipulado con hash recalculado y SIGKILL en tres puntos de la transacción. Prueba focal PASS; regresión completa `tests/*.sh` **52/52 PASS**; AST Python, Bash syntax, ShellCheck focal y `git diff --check` PASS.

Auditoría: `docs/AUDITORIA_C01_GESTOR_CONFIGURACIONES_2026-11-04.md`. Diseño actualizado: `docs/DISENO_GESTOR_CONFIGURACIONES_INDEPENDIENTES.md`.

C-01 está implementado y auditado localmente, pero **pendiente de aceptación expresa**. C-02 importación/exportación no iniciada. No hay menú Bash, validador, `apply`/`activate`, edición/diff ni integración con perfiles. Etapa 5 y Etapa 2 permanecen ABIERTAS.

Sólo temporales y clave sintética. No se leyó `master.key`, no se creó almacén live ni se modificaron perfiles, conexiones VLESS/VMess, runtime, servicios, certificados, firewall, puertos o red. No se tocaron dependencias, `main`, `Xray-Normativa/` ni `Vps de Pruebas`. Sin commit/push/sync.

## Aceptación C-01 e implementación C-02 (2026-11-04)

El propietario aceptó formalmente C-01 como componente limitado, conforme a `docs/AUDITORIA_C01_GESTOR_CONFIGURACIONES_2026-11-04.md`, y autorizó iniciar C-02.

C-02 implementa en `scripts/xray_configurations.py`:
- `preview-import --source`: ruta absoluta, archivo regular, symlink/hardlink y tamaño controlados; UTF-8/BOM; diagnóstico JSON y secciones detectadas; SHA-256 de los bytes originales.
- `import --source --name --expected-sha256 --confirm [--accept-invalid]`: vuelve a leer el archivo una vez, verifica el hash previsualizado y cifra exactamente esos mismos bytes; no modifica el origen. JSON inválido/vacío requiere aceptación expresa y queda Borrador. UTF-8 inválido se rechaza.
- `export --config-id [--revision] --destination [--overwrite]`: escritura temporal/atómica, modo root:root 0600, no sobrescribe sin flag, relectura y comparación byte a byte; advierte que el destino está en claro.

Pruebas C-02 añadidas a `tests/xray_configurations.sh`: JSON válido, UTF-8 BOM, bytes exactos, origen inalterado, SHA-256/TOCTOU, JSON inválido, archivo vacío, UTF-8 inválido, symlink/hardlink, >16 MiB, exportación exacta, permisos, overwrite explícito, symlink destino y fallo parcial de escritura con conservación del destino. Prueba focal PASS; regresión completa prevista al cierre de fase. Auditoría: `docs/AUDITORIA_C02_IMPORTACION_EXPORTACION_2026-11-04.md`.

C-02 está implementado localmente y pendiente de aceptación. C-03–C-06 no iniciadas. La preview sólo verifica UTF-8/JSON y secciones; no es validador estático Xray. No hay menú, reemplazo de nombre duplicado, exportación por lotes, `apply` ni `activate`. Etapa 5 y Etapa 2 ABIERTAS.

No se leyó clave real, no se creó almacén live ni se tocó perfiles, VLESS/VMess, runtime, servicios, certificados, firewall, puertos, red o VPS de pruebas. Sin dependencias nuevas, commit, push o sync. `main` y `Xray-Normativa/` intactas.


## Estado vigente — gestor de configuraciones independientes C-01/C-02 (2026-11-04)

- C-01: **ACEPTADO FORMALMENTE COMO COMPONENTE LIMITADO** conforme a `docs/AUDITORIA_C01_GESTOR_CONFIGURACIONES_2026-11-04.md`.
- C-02: importación/exportación implementadas y auditadas; **pendiente de aceptación expresa** conforme a `docs/AUDITORIA_C02_IMPORTACION_EXPORTACION_2026-11-04.md`.
- Regresión integral: `tests/*.sh` **52/52 PASS**. Sintaxis Bash, Python AST y `git diff --check` PASS. ShellCheck no disponible; no se instalaron dependencias.
- C-03–C-06 no iniciadas. No hay menú integrado, validador estático Xray, edición/diff/comparación, activación ni creación de perfil desde configuración independiente.
- Etapa 5 y Etapa 2 permanecen ABIERTAS. La prueba integral VLESS WS TLS sigue condicionada a superar los puntos de control funcionales pendientes.
- Sólo almacenes temporales y claves sintéticas. No se leyó `master.key`, no se creó almacén live, no se modificó runtime/servicios/systemd/certificados/firewall/puertos/red, no se tocaron dependencias ni VPS de pruebas. `main` y `Xray-Normativa/` sin cambios.
- La sincronización GitHub/VPS se solicitó expresamente y su commit/HEAD se registrará aquí y en `HISTORY.md` al verificarse.


**Sincronización verificada (2026-11-04):** commit `3523368729a4e872d65dc7a37c8a2276a04f640e` publicado en `origin/design/user-identity-association-v1`; checkout `Implementación-Xray:/opt/xray-manager` en el mismo SHA. Publicación fast-forward. `git status --short` vacío. `main`, `Xray-Normativa/` y `Vps de Pruebas` fuera del alcance.

## Estado vigente — gestor de configuraciones independientes C-01/C-02/C-03 (2026-11-04)

- C-01: **ACEPTADO FORMALMENTE COMO COMPONENTE LIMITADO** conforme a su auditoría.
- C-02: **ACEPTADO FORMALMENTE COMO COMPONENTE LIMITADO** conforme a `docs/AUDITORIA_C02_IMPORTACION_EXPORTACION_2026-11-04.md`.
- C-03: edición, diff estructural, comparación y listado de revisiones **ACEPTADOS FORMALMENTE COMO COMPONENTE LIMITADO** conforme a `docs/AUDITORIA_C03_EDICION_DIFF_COMPARACION_2026-11-04.md` (aceptación del propietario: 2026-11-04). Auditoría: `docs/AUDITORIA_C03_EDICION_DIFF_COMPARACION_2026-11-04.md`.
- CLI C-03: `preview-edit`, `edit`, `compare`, `revisions`. Edición exige hash de preview, revisión base y confirmación; crea nueva revisión AES-256-GCM inmutable y conserva la anterior. Diff no expone valores, ignora orden de claves JSON y conserva orden de arrays. JSON inválido sólo se guarda con aceptación expresa como Borrador.
- Prueba focal C-03 PASS. Regresión completa `tests/*.sh` 53/53 PASS. `python3 -m py_compile scripts/*.py`, `bash -n` en scripts/tests, ShellCheck focal y `git diff --check` PASS. ShellCheck global conserva diagnósticos preexistentes en otros archivos y no se declara limpio globalmente.
- C-04–C-06 no iniciadas. No hay menú integrado, validador estático Xray, promoción a Validada, eliminación, activación ni creación de perfil desde configuración independiente. Etapa 5 y Etapa 2 siguen ABIERTAS.
- Sólo almacenes temporales y claves sintéticas. No se leyó `master.key`, no se creó almacén live, no se modificó runtime/servicios/systemd/certificados/firewall/puertos/red, no se tocaron dependencias, VPS de pruebas, `main` o `Xray-Normativa/`. Sin commit, push ni sincronización.
- El código y la auditoría C-03 se publican en la rama autorizada y se sincronizan con `Implementación-Xray:/opt/xray-manager` mediante el commit de sincronización documentado más abajo. No se inició C-04.

**Aceptación y sincronización C-03 (2026-11-04):** el propietario aceptó C-03 como componente limitado conforme a su auditoría. Se publica el código, la prueba focal y la documentación en `design/user-identity-association-v1`; la VPS de desarrollo debe quedar en el mismo SHA. Sin force push. `main`, `Xray-Normativa/` y `Vps de Pruebas` permanecen fuera del alcance. Etapa 5 y Etapa 2 continúan ABIERTAS; C-04 no autorizada ni iniciada.

## C-04A — eliminación segura de configuraciones independientes (2026-11-04)

El propietario aprobó el diseño C-04 y autorizó sólo C-04A. En scripts/xray_configurations.py se añadieron preview-delete y delete. La vista previa valida catálogo/metadatos, estructura y todas las revisiones, hash y autenticación AES-256-GCM. La eliminación requiere confirmación, nombre esperado coincidente con la vista previa y --assert-not-active.

El almacén independiente no administra ni puede verificar aplicaciones runtime manuales externas; por ello el preview informa runtime_activity_verified=false y exige afirmación explícita del operador de que el objeto no está aplicado ni en uso. No se presenta el estado interno not_managed_by_independent_configurations como verificación runtime.

La transacción usa WAL v2 con tombstone y estados prepared/committed; rollback restaura objeto y snapshot exacto del catálogo; recuperación committed finaliza limpieza. Rutas WAL cerradas y protocolo WAL v1 existente preservado. Sólo se elimina el objeto independiente elegido; perfiles/copias y respaldos no se modifican.

Prueba focal tests/xray_configurations_c04a.sh PASS. Regresión completa tests/*.sh 54/54 PASS. Python compile, bash -n global, ShellCheck focal y git diff --check PASS. Auditoría: docs/AUDITORIA_C04A_ELIMINACION_SEGURA_2026-11-04.md.

Estado: C-04A implementada y auditada localmente, pendiente de aceptación formal. C-04B (exportación múltiple) y C-04C (integración menú Bash) no iniciadas. No se cerró C-04, Etapa 5 ni Etapa 2.

Sólo almacenes temporales y claves sintéticas. No se leyó master.key, no se accedió al almacén real ni se tocó runtime/servicios/systemd/certificados/firewall/puertos/red/dependencias. VPS de pruebas, main y Xray-Normativa/ intactas. No commit/push/sync.


## Aceptación formal y publicación de C-04A — 2026-11-04

El propietario aceptó formalmente C-04A como componente limitado conforme a `docs/AUDITORIA_C04A_ELIMINACION_SEGURA_2026-11-04.md`. La aceptación cubre exclusivamente la eliminación segura de configuraciones independientes, los controles, las pruebas y las limitaciones documentadas. No cierra C-04 completa, Etapa 5 ni Etapa 2.

C-04A está IMPLEMENTADA, VERIFICADA, AUDITADA, PUBLICADA y SINCRONIZADA en `design/user-identity-association-v1`. Commit de implementación: `afb2f7bf8cc040ca2731787b9e113b5a4660a00f`.

C-04B (exportación múltiple) y C-04C (integración del menú Bash) no están autorizadas ni iniciadas. La aceptación no autoriza runtime, servicios, dependencias, certificados, firewall, puertos, red, VPS de pruebas ni cambios en `main` o `Xray-Normativa/`.

## Estado vigente — C-04B exportación múltiple (2026-11-04)

- Autorización expresa recibida para implementar exclusivamente C-04B, después de la aceptación formal y publicación de C-04A.
- `scripts/xray_configurations.py` incorpora `preview-export-batch` y `export-batch`. El contrato usa manifiesto JSON estricto (1–100 entradas), ruta por salida, revisión específica o revisión actual resuelta durante preview y política `overwrite` individual.
- Preview valida configuración/revisión/destinos, rechaza rutas inseguras y destinos duplicados, y devuelve `manifest_sha256` y `preview_sha256`. La ejecución exige ambos hashes más `--confirm`, reconstruye el preview y rechaza cambios en manifiesto, revisión actual resuelta o estado revisado antes de exportar.
- Cada archivo reutiliza la exportación individual atómica, root:root 0600 y verificación byte a byte. Un fallo individual se informa sin cancelar las demás salidas. Los archivos quedan en claro y la salida lo advierte.
- Nueva prueba focal: `tests/xray_configurations_c04b.sh` PASS; incluye revisión obsoleta, manifiesto/destinos inseguros, duplicados, fallos parciales y confirmación/hash.
- Regresión global final `tests/*.sh`: **55/55 PASS** después de incluir el caso de revisión obsoleta. `py_compile`, `bash -n` global, ShellCheck focal y `git diff --check` PASS.
- Auditoría: `docs/AUDITORIA_C04B_EXPORTACION_MULTIPLE_2026-11-04.md`. Diseño actualizado en `docs/DISENO_GESTOR_CONFIGURACIONES_INDEPENDIENTES.md`.
- Estado: C-04B IMPLEMENTADA y VERIFICADA localmente; pendiente de aceptación formal. C-04C (menú Bash) no autorizada ni iniciada. C-04, Etapa 5 y Etapa 2 siguen ABIERTAS.
- Sólo almacenes temporales y claves sintéticas. No se leyó `master.key`, no se accedió al almacén real ni se tocó runtime, servicios, systemd, certificados, firewall, puertos, red, dependencias, VPS de pruebas, `main` o `Xray-Normativa/`. Sin commit/push/sync.

## Aceptación formal C-04B — 2026-11-04

El propietario aceptó formalmente C-04B como componente limitado conforme a `docs/AUDITORIA_C04B_EXPORTACION_MULTIPLE_2026-11-04.md`. La aceptación cubre exclusivamente la exportación múltiple, el contrato de manifiesto, las comprobaciones previas, la confirmación por hashes, la ejecución parcial y las pruebas documentadas. No cierra C-04 completa, Etapa 5 ni Etapa 2.

C-04B permanece implementada, verificada y aceptada localmente. La publicación/sincronización no se entiende autorizada por esta aceptación. C-04C (integración del menú Bash) no se inicia sin autorización específica. `main`, `Xray-Normativa/`, runtime, servicios y VPS de pruebas permanecen fuera del alcance.


## C-04C — integración del menú Bash (2026-11-04)

El propietario autorizó expresamente C-04C, limitada a conectar el gestor independiente con el menú Bash, después de publicar y verificar primero C-04B.

Se incorporó modules/xray_configurations_menu.sh, se cargó desde bin/xray-manager y se conectó la opción [1] Gestionar configuraciones de Xray de menu_config_profiles_backups. config/paths.sh define la ruta del almacén independiente y la ruta configurable de la clave maestra existente.

El submenú integra consulta/metadatos y visualización opcional del JSON con confirmación, creación, edición con preview/hash/revisión base, importación con preview/hash, exportación individual y múltiple, comparación sin valores secretos, historial de revisiones y eliminación con preview y doble confirmación. No existe acción apply/activate.

Nueva prueba tests/xray_configurations_menu.sh: PASS con almacén temporal y clave sintética. tests/smoke.sh y tests/stage1_menu.sh: PASS. Regresión completa tests/*.sh: 56/56 PASS. Bash syntax global, ShellCheck focal, Python compile y git diff --check: PASS. Auditoría: docs/AUDITORIA_C04C_INTEGRACION_MENU_BASH_2026-11-04.md.

Estado: C-04C IMPLEMENTADA, VERIFICADA y AUDITADA LOCALMENTE; pendiente de aceptación formal. No se hizo commit/push/sync de C-04C. C-04, Etapa 5 y Etapa 2 siguen ABIERTAS. No se accedió al almacén real ni se leyó la clave maestra; no se tocaron runtime, servicios, dependencias, certificados, firewall, puertos, red, VPS de pruebas, main ni Xray-Normativa/.


## Aceptación formal C-04C — 2026-11-04

El propietario aceptó formalmente C-04C conforme a la auditoría `docs/AUDITORIA_C04C_INTEGRACION_MENU_BASH_2026-11-04.md`. La aceptación cubre exclusivamente la integración de las operaciones del gestor independiente en el menú Bash y las pruebas documentadas. No cierra C-04 completa, Etapa 5 ni Etapa 2, y no autoriza C-05.

Se autoriza expresamente publicar los cambios C-04C aceptados. La implementación, pruebas, auditoría y registro de aceptación se publicarán en `design/user-identity-association-v1`; `main` y `Xray-Normativa/` permanecen protegidas.


## Estado vigente — cierre integral C-04 aceptado (2026-11-04)

El propietario acepta formalmente el cierre integral de C-04, con base en la auditoría integral documentada y sus resultados. C-04A (eliminación segura), C-04B (exportación múltiple) y C-04C (integración del menú Bash) quedan reconocidas como fases completadas dentro del alcance aprobado. La auditoría integral ejecutó la regresión completa con **56/56 PASS**, además de las verificaciones estáticas documentadas, y no identificó defectos funcionales bloqueantes.

La publicación de las correcciones documentales quedó verificada en el commit `7f215b1dbfaa0b2dc7a2a3726a76dfa25b1cbb10`, rama `design/user-identity-association-v1`. Este registro de aceptación integral es un cambio documental posterior y queda local, sin commit ni push. C-05 no está autorizada ni iniciada. Etapa 5 y Etapa 2 permanecen ABIERTAS. `main`, `Xray-Normativa/`, runtime, servicios e infraestructura siguen fuera del alcance.

## Estado vigente — C-05A y C-05B aceptadas, publicadas y sincronizadas (2026-11-04)

- C-05A — motor de validación estática y nativa: IMPLEMENTADA, AUDITADA y ACEPTADA FORMALMENTE como componente limitado. Evidencia: `docs/AUDITORIA_C05A_MOTOR_VALIDACION_2026-11-04.md`.
- C-05B — almacén permanente e inmutable de informes: IMPLEMENTADA, AUDITADA y ACEPTADA FORMALMENTE. Evidencia: `docs/AUDITORIA_C05B_ALMACEN_INFORMES_2026-11-04.md`.
- Motor: `scripts/xray_config_validator.py`; almacén desacoplado: `scripts/xray_validation_store.py`. Pruebas focales combinadas: 25/25 PASS (17 C-05A + 8 C-05B).
- Regresión shell C-01/C-02, C-03, C-04A, C-04B, C-04C y smoke general: PASS. Python compile, `bash -n modules/*.sh` y `git diff --check`: PASS.
- Publicación: commit inicial `0b0e36e53dbc58c2102805834c2ffc1a5edd6b25` contiene los ocho archivos C-05A/C-05B. Rama autorizada `design/user-identity-association-v1`.
- Sincronización GitHub/VPS: verificada posteriormente en el commit de continuidad que acompaña este estado; comprobar siempre `git rev-parse HEAD`, `git ls-remote` y árbol limpio.
- C-05C (promoción al estado Validada), C-05D (historial/comparación), C-05E (menú) y C-05F (auditoría integral) requieren autorizaciones independientes. Ninguna queda autorizada por la aceptación/publicación de C-05A/B.
- El almacén de informes no se ha creado en `/var/lib/xray-manager/validation`; no hay integración funcional con el motor ni promoción de estados. No se modificaron runtime, servicios, certificados, firewall, puertos, dependencias ni configuración activa. No se leyó la clave maestra real.
- `main` y `Xray-Normativa/` permanecen intactas. Etapa 5 y Etapa 2 siguen ABIERTAS.


## Verificación de continuidad documental y sincronización — 2026-11-04

Se revisaron los documentos de continuidad, diseño y expediente C-05A/C-05B. Se corrigieron los estados iniciales desactualizados mediante encabezados vigentes y addenda, preservando el contenido histórico y las evidencias originales. C-05A/B continúan aceptadas, publicadas y sincronizadas; C-05C sigue pendiente de autorización específica. El HEAD verificado antes de esta actualización documental fue 1815663438770a2271d769345adbc271714a6817; main y Xray-Normativa/ permanecieron intactas.


## Estado vigente — C-05C implementada y auditada localmente (2026-11-04)

C-05A (motor estático/nativo) y C-05B (almacén permanente de informes) permanecen aceptadas, publicadas y sincronizadas. El propietario autorizó exclusivamente C-05C para implementación, pruebas, auditoría técnica y documentación, limitando expresamente la publicación/sincronización.

C-05C añade `scripts/xray_config_promotion.py`, amplía la validación de metadatos en `scripts/xray_configurations.py` y agrega `tests/test_xray_config_promotion.py`. Integra validación de bytes/revisión exactos, criterios estrictos PASS/PASS_WITH_WARNINGS, informe permanente y promoción transaccional recuperable. Las ediciones posteriores crean Borrador y conservan el puntero a la revisión validada anterior. La validación histórica no marca la revisión actual como Validada.

Evidencia: auditoría `docs/AUDITORIA_C05C_PROMOCION_VALIDADA_2026-11-04.md`; implementación `docs/IMPLEMENTACION_C05C_PROMOCION_VALIDADA_2026-11-04.md`. C-05C focal 13/13 PASS; regresión Python C-05A/B/C 38/38 PASS; suites shell C-01/C-02, C-03, C-04A/B/C y perfiles PASS; Xray 26.10.31 real PASS en almacenes temporales.

Estado administrativo C-05C: IMPLEMENTADA, VERIFICADA y AUDITADA LOCALMENTE; pendiente de aceptación formal; NO PUBLICADA ni SINCRONIZADA. C-05D, C-05E y C-05F no autorizadas. Etapa 5 y Etapa 2 siguen ABIERTAS.

La base Git sigue siendo `6ab158f436d2d88755d70e954114efb4fa2f6129` en `design/user-identity-association-v1`; los cambios están locales y sin commit. No se creó almacén live, no se leyó la clave maestra real, no se instalaron/actualizaron dependencias ni se tocaron runtime, servicios, certificados, firewall, puertos, red, `main`, `Xray-Normativa/` o `Vps de Pruebas`.


## Registro de aceptación/publicación C-05C — 2026-11-04

El propietario aceptó formalmente C-05C y autorizó publicar cambios y actualizar documentación. C-05C queda ACEPTADA, PUBLICADA y SINCRONIZADA en `design/user-identity-association-v1`. Evidencias en los documentos de implementación y auditoría C-05C. Pruebas: 13/13 focal y 38/38 regresión Python C-05A/B/C; regresiones shell C-01/C-02, C-03, C-04A/B/C y perfiles PASS.

C-05D/E/F siguen sin autorización. Etapa 5 y Etapa 2 permanecen ABIERTAS. La publicación no alteró `main`, `Xray-Normativa/`, runtime, almacenes live, dependencias, servicios, certificados, firewall, puertos, red ni VPS de pruebas; no se leyó la clave maestra real.

**Publicación C-05C:** commit `58c273a18ea32c1feddc02012d0318952c7a0689` (`58c273a`) en `design/user-identity-association-v1`; push fast-forward verificado. La sincronización del checkout de desarrollo en `/opt/xray-manager` corresponde al mismo commit.

## Recuperación y verificación del punto C-05C — 2026-11-04

- Estado vigente: C-05A/B/C aceptadas, auditadas, publicadas y sincronizadas. C-05D/E/F requieren autorizaciones independientes. Etapa 5 y Etapa 2 siguen ABIERTAS.
- VPS /opt/xray-manager: rama design/user-identity-association-v1, HEAD 670e6ab371e620a8cb8b51f9431746f0a2270cda, árbol limpio.
- GitHub confirma el mismo HEAD de la rama autorizada; main continúa en 656ecedc506a94a6461aee296b20871d51a38bf3.
- SSH: primer git ls-remote origin falló, autenticación directa de las claves RW y RO aceptada y reintento posterior de git ls-remote origin satisfactorio. No se modificaron claves, configuración SSH, remoto ni credenciales. No existe ref local origin/main; la rama remota main sí fue consultada directamente.
- Normativa Etapa 5: hashes SHA-256 del Markdown y YAML en Xray-Normativa/ coinciden con la copia aprobada bajo /root/Xray_Manager_Documentacion_Final_2026-10-31.
- Se aclaró documentalmente que los estados antiguos de C-05C pendiente son históricos y están superados por el registro final de aceptación/publicación.
- No se implementó C-05D, no se ejecutaron pruebas de escritura, no hubo commit/push, no se tocaron main, Xray-Normativa/, secretos, almacenes live, runtime, servicios, dependencias, certificados, firewall, puertos, red ni VPS de pruebas.
- Próximo paso: preparar diseño y matriz de pruebas C-05D sin implementación. Requiere autorización expresa antes de codificar.

## Registro de implementación C-05D — 2026-11-04

El propietario autorizó C-05D: historial y comparación de informes de validación. Se implementó exclusivamente el servicio read-only `scripts/xray_validation_history.py` y su suite `tests/test_xray_validation_history.py`; se añadieron los documentos de implementación y auditoría. La modalidad aprobada es comparación de informes de una misma configuración, permitiendo revisiones distintas y rechazando configuraciones diferentes.

Verificación local: C-05D focal H01–H38 38/38 PASS; regresión Python C-05A/B/C/D 76/76 PASS; suites shell existentes 56/56 PASS; `py_compile`, `bash -n`, `install.sh --check`, ShellCheck severidad error y `git diff --check` PASS. ShellCheck en severidad warning informa cuatro advertencias preexistentes en tests/stage1_header.sh (SC2034, dos), tests/uninstall.sh (SC2154) y tests/vless_backup_restore.sh (SC2174); no se modificaron por estar fuera del alcance.

El servicio consulta el almacén C-05B bajo su lock, valida fechas ISO-8601 con zona horaria, ofrece filtros/paginación, detalle y comparación estructurada. No modifica informes/catálogo ni el esquema C-05B. Prueba WAL con SIGKILL, integridad, concurrencia, saneamiento y solo lectura PASS.

Estado: C-05D IMPLEMENTADA, VERIFICADA Y AUDITADA LOCALMENTE; PENDIENTE DE ACEPTACIÓN FORMAL; NO PUBLICADA NI SINCRONIZADA. No se creó commit ni push. C-05E y C-05F siguen sin autorización; Etapa 5 y Etapa 2 permanecen ABIERTAS. No se modificaron main, Xray-Normativa/, almacenes live, clave maestra real, runtime, servicios, dependencias, certificados, firewall, puertos, red ni VPS de pruebas.


## Aceptación formal y publicación C-05D — 2026-11-04

El propietario aceptó formalmente C-05D y autorizó crear el commit y publicar exclusivamente en `design/user-identity-association-v1`. La aceptación cubre el servicio de historial/comparación, sus pruebas focales y la auditoría documentada. C-05D queda ACEPTADA; C-05E y C-05F continúan sin autorización independiente. Etapa 5 y Etapa 2 permanecen ABIERTAS.


## Estado vigente — C-05E implementada y auditada localmente (2026-11-04)

- C-05A/B/C/D continúan aceptadas, publicadas y sincronizadas en `design/user-identity-association-v1`.
- C-05E integra el submenú Bash con C-05C para validar configuraciones guardadas y C-05D para último informe, historial, detalle y comparación.
- Opciones de validación de archivo externo y configuración activa siguen deshabilitadas.
- Evidencias: `docs/IMPLEMENTACION_C05E_MENU_BASH_2026-11-04.md` y `docs/AUDITORIA_C05E_MENU_BASH_2026-11-04.md`. Regresión C-05A/B/C/D: 76/76 Python PASS; shell: 57/57 PASS; focal C-05E PASS; `bash -n`, ShellCheck severidad error, `install.sh --check` y `git diff --check` PASS.
- C-05E está IMPLEMENTADA, VERIFICADA y AUDITADA LOCALMENTE; pendiente de aceptación formal. Sin commit ni push. C-05F no iniciada ni autorizada.
- No se creó almacén live ni se leyó la clave maestra real. No se instalaron dependencias ni se modificaron runtime, servicios, certificados, firewall, puertos, red, `main`, `Xray-Normativa/` o VPS de pruebas.
- Etapa 5 y Etapa 2 permanecen ABIERTAS.

## Aceptación formal C-05E — 2026-11-04

- **Estado:** C-05E ACEPTADA FORMALMENTE por el propietario.
- **Alcance aceptado:** integración del menú Bash, CLI read-only de historial, pruebas y auditoría C-05E, con las limitaciones E01–E38 expresamente documentadas.
- **Git:** cambios C-05E continúan sin commit ni push en `design/user-identity-association-v1`; base HEAD `ed700c1e770063f6e67c6ebaeae4652172bb2f02`.
- **Publicación:** no autorizada. No ejecutar commit, push ni sincronización hasta autorización expresa independiente.
- **Siguiente decisión:** solicitar autorización separada para publicar C-05E o recibir instrucciones para ampliar pruebas; no asumir ninguna de ellas.
- **C-05F:** no autorizada ni iniciada.
- **Límites:** `main`, `Xray-Normativa/`, VPS de pruebas, secretos, almacenes live, runtime e infraestructura permanecen fuera del alcance.
- **Etapas:** Etapa 5 y Etapa 2 siguen ABIERTAS.

## Publicación confirmada C-05E — 2026-11-04

- **Estado:** C-05E ACEPTADA, AUDITADA, PUBLICADA y SINCRONIZADA.
- **Rama:** `design/user-identity-association-v1`.
- **Commit:** `8378ca47a751678f4eeeab20a5e2d06effd47fff` — `feat(validation): integrate C-05E validation menu`.
- **Push:** fast-forward desde `ed700c1e770063f6e67c6ebaeae4652172bb2f02`; `git ls-remote` confirmó que GitHub publica el mismo SHA.
- **main:** sin cambios; SHA remoto verificado `656ecedc506a94a6461aee296b20871d51a38bf3`.
- **Árbol local:** limpio después del push y del registro de publicación (este addendum se versiona a continuación).
- **Próxima decisión:** C-05F requiere autorización expresa independiente. No iniciar por inferencia.
- **Protecciones:** `Xray-Normativa/`, VPS de pruebas, secretos, almacenes live, runtime e infraestructura no fueron modificados.
- **Etapas:** Etapa 5 y Etapa 2 permanecen ABIERTAS.

## C-05F — diseño y matriz preparados, ejecución pendiente (2026-11-04)

- El propietario autorizó preparar el diseño técnico y la matriz de C-05F, no ejecutar aún la auditoría ni implementar correcciones.
- Documentos locales: `docs/DISENO_C05F_AUDITORIA_INTEGRAL_2026-11-04.md` y `docs/MATRIZ_C05F_AUDITORIA_INTEGRAL_2026-11-04.md`.
- Alcance propuesto: auditoría transversal del subsistema C-05A–C-05E frente a los requisitos de validación aplicables de Etapa 5. No es auditoría integral ni cierre de toda Etapa 5.
- La matriz contiene 71 criterios F01–F71 y 15 huecos G01–G15. Todos están pendientes de ejecución/decisión; no se afirma ningún resultado PASS.
- Pendiente de confirmación: alcance de C-05F; registro como divergencia de las opciones de validación externa/activa actualmente deshabilitadas; y corrección de hallazgos mediante autorización separada.
- No se modificó código, pruebas, runtime, infraestructura ni `Xray-Normativa/`. Los dos documentos y este registro están locales, sin commit/push.
- C-05A–C-05E siguen aceptadas y publicadas. C-05F aún no ejecutada ni aceptada. Etapa 5 y Etapa 2 permanecen ABIERTAS.

## C-05F — auditoría transversal ejecutada, aceptación pendiente (2026-11-04)

- El propietario aprobó las condiciones de ejecución: alcance C-05A–E; registrar validación externa/activa como divergencias sin implementarlas; separar auditoría de correcciones.
- Auditoría ejecutada y documentada en docs/AUDITORIA_C05F_AUDITORIA_INTEGRAL_2026-11-04.md; matriz final en docs/MATRIZ_C05F_AUDITORIA_INTEGRAL_2026-11-04.md.
- Resultado técnico: PASS con un hallazgo menor H-01 y divergencias D-01–D-05. No se modificó código ni pruebas.
- Regresión Python: 76/76 PASS. Regresión shell: 57/57 PASS, cero fallos y cero skips. Entry point/menú, CLI, recorrido A→E con Xray real y concurrencia: PASS.
- H-01 (baja): CLI no detecta symlink roto en un componente padre de la ruta del almacén y responde como si el almacén estuviera ausente. Abierto; requiere autorización de corrección.
- D-01/D-02: validación externa/activa deshabilitadas frente a normativa. D-03: mecanismo de prueba runtime sigue pendiente en la propia normativa. D-04: exclusión del historial en backup queda fuera de C-05F y pendiente para auditoría backup/restore de Etapa 5. D-05: filtros CLI completos, controles UI parciales.
- No se implementaron correcciones ni funcionalidades nuevas. No se hizo commit ni push. Rama y HEAD publicados siguen en a4f2c6356652e04206918c410ddf3f6aa3181808.
- main, Xray-Normativa/, clave maestra real, almacenes live, runtime, infraestructura y VPS de pruebas permanecieron intactos.
- C-05F: ejecutada y documentada localmente; pendiente de aceptación formal. Etapa 5 y Etapa 2 permanecen ABIERTAS.


## Estado vigente — C-05F aceptada formalmente (2026-11-04)

- C-05F — auditoría integral del subsistema C-05A–C-05E: **ACEPTADA FORMALMENTE** por el propietario.
- Dictamen aceptado: PASS técnico con hallazgo menor H-01 y divergencias/asuntos D-01–D-05 documentados.
- Expediente: docs/AUDITORIA_C05F_AUDITORIA_INTEGRAL_2026-11-04.md; matriz: docs/MATRIZ_C05F_AUDITORIA_INTEGRAL_2026-11-04.md.
- H-01 sigue abierto y sin corregir; requiere autorización independiente. D-01/D-02/D-03/D-04/D-05 no quedan resueltos por la aceptación.
- No se autorizaron commit, push ni sincronización. Los cambios documentales siguen locales sobre HEAD a4f2c6356652e04206918c410ddf3f6aa3181808.
- Etapa 5 y Etapa 2 siguen ABIERTAS. La aceptación C-05F no equivale al cierre de ninguna de ellas.

## Estado vigente — H-01 corregido y verificado (2026-11-04)

- C-05F fue aceptada formalmente por el propietario.
- H-01 fue corregido bajo autorización posterior: CLI ahora usa lstat() para rechazar symlinks directos, ancestros válidos y rotos.
- Pruebas nuevas H39–H42; suite de historial 42/42 PASS; regresión Python 80/80 PASS; shell 57/57 PASS.
- py_compile, bash -n, ShellCheck -S error, warning focal, install.sh --check y git diff --check: PASS.
- Evidencia: docs/CORRECCION_H01_RUTAS_SYMLINK_C05F_2026-11-04.md.
- D-01–D-05 no se modificaron ni resolvieron. Etapa 5 y Etapa 2 siguen ABIERTAS.


## U-01 — integración Usuarios V2 con VLESS (2026-11-04)

- El propietario aprobó el diseño U-01 y autorizó su implementación con el alcance descrito.
- Usuarios V2 es ahora la única fuente del asistente VLESS; se eliminó el fallback legacy en creación y recuperación.
- `users_v2_export_vless_candidate_clients` proyecta asociaciones VLESS de la conexión solicitada con estado funcional active y vencimiento futuro/nulo, sin exigir provisioning/runtime applied. Excluye suspended/expired/vencidas y valida snapshot bajo lock compartido. Si el almacén no existe, falla sin inicializarlo.
- `users_v2_export_vless_clients` mantiene su contrato runtime de asociaciones activas y aplicadas.
- UUID VLESS: menú con generación automática predeterminada o entrada manual oculta; unicidad global y normalización a minúsculas.
- `tests/users_v2_vless_candidate.sh` cubre filtros, vencimientos, estados, aislamiento por conexión/protocolo, separación runtime, JSON inválido y almacén ausente. `tests/xray_vless_integration.sh` proyecta una asociación V2 sintética y la valida con Xray 26.10.31 real.
- Regresión `tests/*.sh`: 58/58 PASS. `bash -n`, `py_compile`, `install.sh --check`, ShellCheck severidad error, shfmt y `git diff --check`: PASS.
- Expedientes: `docs/IMPLEMENTACION_U01_INTEGRACION_USUARIOS_V2_VLESS_2026-11-04.md`, `docs/AUDITORIA_U01_INTEGRACION_USUARIOS_V2_VLESS_2026-11-04.md`; diseño actualizado en `docs/DISENO_IDENTIDADES_ASOCIACIONES_V1.md`.
- Estado U-01: IMPLEMENTADA, VERIFICADA, AUDITADA, PUBLICADA y SINCRONIZADA; aceptación formal del propietario pendiente. Commit `1c2cd12f15be75d9f3a080ce028951724618c492`.
- No se ejecutó migración legacy/cutover, ACME DNS-01/Cloudflare, publicación runtime, inicio de servicio ni prueba externa NetMod. No se modificaron almacenes live, clave maestra real, runtime, servicios, certificados desplegados, firewall, puertos, red, dependencias, `main`, `Xray-Normativa/` ni VPS de pruebas.
- Etapa 2, Etapa 3 y Etapa 5 permanecen ABIERTAS.


### Publicación U-01 — 2026-11-04

U-01 se publicó mediante commit `1c2cd12f15be75d9f3a080ce028951724618c492` (`feat(vless): integrate V2 users into candidate generation`) en `design/user-identity-association-v1`. Push fast-forward desde `ca6d76895821310a3072d9de47268f925ecea7ba`; SHA remoto confirmado. Aceptación formal pendiente. `main`, `Xray-Normativa/`, VPS de pruebas, almacenes live, runtime e infraestructura permanecen intactos.

## Aceptación formal U-01 — 2026-11-04

U-01 y su auditoría fueron aceptadas formalmente por el propietario. Se autoriza avanzar al diseño del mecanismo de aplicación runtime, no a implementarlo ni ejecutarlo. Diseño propuesto: `docs/DISENO_APLICACION_RUNTIME_XRAY_2026-11-04.md`. R-01–R-05 requieren aprobación de alcance/decisiones antes de implementación; R-06 requiere autorización live independiente. Etapas 2, 3 y 5 permanecen abiertas.


## Estado vigente — R-01 runtime por perfil/revisión (2026-11-04)

- U-01: ACEPTADA FORMALMENTE.
- Diseño runtime: ajustado y aprobado para que R-01–R-05 trabajen exclusivamente con profile_id + revision, conforme a Etapa 5 §3.1.
- Alcance autorizado: R-01–R-05 exclusivamente en entornos aislados (fixtures, datos sintéticos, almacenes temporales y mocks). R-06/live NO AUTORIZADA.
- R-01: IMPLEMENTADA, INTEGRADA EN CLI/MENÚ, VERIFICADA EN FIXTURES, AUDITADA LOCALMENTE, PUBLICADA Y SINCRONIZADA. Aceptación formal de R-01 pendiente.
- Funcionalidad: selección explícita de revisión; validación estática/nativa; informe persistente ligado a profile_id + revision y SHA-256; actualización transaccional de manifiesto/metadata; preflight read-only.
- Archivos principales: scripts/xray_profile_validation_store.py, scripts/xray_profile_validation.py, scripts/xray_runtime_preflight.py, modules/profiles.sh (opción 8), scripts/xray_profiles.py y config/paths.sh.
- Evidencia R-01: pruebas focales 28/28 PASS (preflight 18/18 + validación 11/11); regresión Python 108/108 PASS; regresión shell 58/58 PASS. py_compile, bash -n global, ShellCheck focal, install.sh --check y git diff --check PASS.
- Publicación de código R-01: c605b3efc904d75a142e9e8c539210eb65070acd. Actualización documental inicial: 856662b0981ad4457f4e4bba72c41735e998f958; reconciliación de continuidad publicada: 94556849316852625fbcf98d8ea0796600097088. Consultar HEAD remoto vigente en GitHub; no asumir que un SHA histórico sigue siendo HEAD.
- Estado Git verificado al inicio de esta actualización: VPS /opt/xray-manager y origin/design/user-identity-association-v1 coincidían en 856662b0981ad4457f4e4bba72c41735e998f958; árbol limpio. main: 656ecedc506a94a6461aee296b20871d51a38bf3.
- Limitaciones: R-01 no se ejecutó contra el almacén de perfiles ni la clave maestra reales; el estado de servicio usa fixture, no systemd real; validación bajo identidad efectiva xray y leases TLS queda para R-02.
- Siguiente paso permitido: iniciar R-02 — staging integrado de la revisión exacta y leases TLS en directorio temporal, validación bajo identidad de servicio simulada. No publicar runtime.
- No se leyó la clave maestra real ni se modificaron almacenes live, /etc/xray/config.json, systemd real, runtime, certificados desplegados, firewall, puertos, red, dependencias, main, Xray-Normativa/ ni VPS de pruebas.
- Etapas 2, 3 y 5 permanecen ABIERTAS.

## Estado vigente — R-02 staging integrado (2026-11-04)

- R-01: IMPLEMENTADA, INTEGRADA EN CLI/MENÚ, VERIFICADA, AUDITADA, PUBLICADA y SINCRONIZADA; aceptación formal específica pendiente.
- R-02: IMPLEMENTADA, VERIFICADA EN FIXTURES Y CON XRAY REAL SOBRE CERTIFICADO/CLAVE SINTÉTICOS, AUDITADA LOCALMENTE; pendiente de aceptación formal y publicación.
- Diseño aprobado: asociación explícita inbound tag → connection_id. El mapa JSON privado se fija al staging mediante SHA-256; el certificate_id se obtiene únicamente de la conexión central y el lease se prepara mediante certificate_resolver.
- Archivos R-02: scripts/xray_runtime_staging.py; tests/test_xray_runtime_staging.py; docs/IMPLEMENTACION_R02_STAGING_PERFIL_TLS_2026-11-04.md; docs/AUDITORIA_R02_STAGING_PERFIL_TLS_2026-11-04.md.
- Pruebas: R-02 focal 9/9 PASS; regresión Python 117/117 PASS; shell 58/58 PASS; py_compile, bash -n global, install.sh --check, ShellCheck -S error en tests/*.sh y git diff --check PASS.
- Prueba nativa: Xray-core 26.10.31 real aceptó el archivo staged y leyó el certificado/clave sintéticos bajo UID/GID 65534:65534. No se ejecutó systemd ni se inició/reinició Xray.
- Limitación: el mapa de asociaciones es una entrada explícita externa a la revisión, fijada en el manifiesto staged; no existe todavía UI/almacén persistente de ese mapa. Los leases exitosos permanecen para R-03.
- Git: R-02 aún no tiene commit ni push. No asumir publicación hasta recibir aceptación formal y autorización expresa.
- Siguiente paso: revisión del expediente R-02 por el propietario; después continuar R-03 (snapshot/journal) tras aceptación.
- No autorizado: R-06/live, escritura runtime, systemd real, certificados reales, firewall, puertos, red, dependencias, VPS de pruebas, main o Xray-Normativa/.
- Etapas 2, 3 y 5 siguen ABIERTAS.

## Estado vigente — R-03 snapshot/journal implementada (2026-11-04)

- R-01: implementada, integrada, auditada, publicada y sincronizada; aceptación formal específica pendiente.
- R-02: implementada, probada con Xray-core 26.10.31 real sobre certificados/clave sintéticos, endurecida con fixture_root obligatorio y auditada localmente; pendiente de aceptación formal/publicación.
- R-03: IMPLEMENTADA, VERIFICADA Y AUDITADA LOCALMENTE; pendiente de aceptación formal/publicación.
- R-03: snapshot exacto de configuración previa en XRAY_SERVICE_ROOT fixture, journal durable, estados prepared/validated/snapshot_saved/aborted/recovery_required y recuperación idempotente. Marcadores obligatorios de XRAY_SERVICE_ROOT, operation_store y lease_root; locks dentro de operation_store.
- Archivos R-03: scripts/xray_runtime_journal.py; tests/test_xray_runtime_journal.py; docs/IMPLEMENTACION_R03_SNAPSHOT_JOURNAL_2026-11-04.md; docs/AUDITORIA_R03_SNAPSHOT_JOURNAL_2026-11-04.md.
- Pruebas al corte: R-02 11/11 PASS; R-03 21/21 PASS; Python 140/140 PASS; shell 58/58 PASS; py_compile, bash -n global, install.sh --check, ShellCheck -S error en tests/*.sh y git diff --check PASS.
- No se modificó el config del fixture; no se publicó runtime ni se llamó systemd. No se usó clave maestra ni almacenes reales.
- R-02/R-03 aún no tienen commit ni push. Aceptación formal y autorización de publicación pendientes.
- Siguiente paso: revisión de R-02/R-03; luego R-04 publicación atómica aislada.
- R-06/live, runtime real, systemd real, certificados reales, firewall, puertos, red, dependencias, VPS de pruebas, main y Xray-Normativa/ siguen fuera de alcance.
- Etapas 2, 3 y 5 siguen ABIERTAS.


## Estado vigente — R-04 publicación atómica aislada (2026-11-04)

- R-01: publicada/sincronizada; aceptación formal específica pendiente.
- R-02: implementada y auditada localmente; focal 11/11.
- R-03: implementada y auditada localmente; journal focal 22/22.
- R-04: IMPLEMENTADA Y VERIFICADA LOCALMENTE; focal 12/12; pendiente de auditoría/aceptación formal y publicación.
- R-04: publicación atómica en XRAY_SERVICE_ROOT fixture, validación del temporal con Xray bajo UID/GID simulado, journal publication/rollback, rollback exacto y recuperación idempotente. Sin systemd.
- Expedientes: docs/IMPLEMENTACION_R04_PUBLICACION_ATOMICA_2026-11-04.md; docs/AUDITORIA_R04_PUBLICACION_ATOMICA_2026-11-04.md.
- Pruebas al corte: R-02 11/11; R-03 journal 22/22; R-04 12/12; Python 153/153; shell 58/58 PASS; verificaciones estáticas PASS.
- Integración R-02→R-03→R-04 comprobada en fixture temporal.
- No se publicó runtime real ni se llamó systemd; no se usaron almacenes/llaves/certificados reales.
- R-02/R-03/R-04 no tienen commit/push. Aceptación formal y autorización de publicación pendientes.
- Siguiente paso: revisión/aceptación de R-02–R-04; luego R-05 systemd simulado.
- R-06/live, NetMod, runtime real, systemd real, certificados reales, firewall, puertos, red, dependencias, VPS de pruebas, main y Xray-Normativa/ siguen fuera de alcance.
- Etapas 2, 3 y 5 siguen ABIERTAS.


## Estado vigente — reconciliación R-01–R-04 y diseño R-05 (2026-11-04)

Este addendum prevalece como fotografía de estado sobre los registros históricos anteriores, que se conservan íntegros.

- Rama autorizada: `design/user-identity-association-v1`.
- Commit publicado y verificado al corte: `05aceabf11414040abbb32fff1428984370ff521`.
- R-01: IMPLEMENTADA, INTEGRADA, VERIFICADA, AUDITADA, PUBLICADA y SINCRONIZADA. ACEPTACIÓN FORMAL PENDIENTE.
- R-02: IMPLEMENTADA, VERIFICADA, AUDITADA, PUBLICADA y SINCRONIZADA. ACEPTACIÓN FORMAL PENDIENTE.
- R-03: IMPLEMENTADA, VERIFICADA, AUDITADA, PUBLICADA y SINCRONIZADA. ACEPTACIÓN FORMAL PENDIENTE.
- R-04: IMPLEMENTADA, VERIFICADA, AUDITADA, PUBLICADA y SINCRONIZADA. ACEPTACIÓN FORMAL PENDIENTE.
- Pruebas focales registradas: R-01 28/28; R-02 11/11; R-03 22/22; R-04 12/12. Regresión global documentada tras R-04: Python 153/153 y Bash 58/58 PASS. No se reejecutaron en esta actualización documental.
- R-02→R-03→R-04 se verificó integrada en fixtures temporales.
- R-05: NO INICIADA. Diseño propuesto en `docs/DISENO_R05_ORQUESTACION_SYSTEMD_SIMULADA_2026-11-04.md`; requiere revisión y aprobación antes de implementar.
- R-06/live: NO AUTORIZADA. Etapas 2, 3 y 5 ABIERTAS.
- Los estados anteriores que describen R-02–R-04 como no publicados son fotografías históricas previas al commit indicado; no describen el estado vigente.
- No se modificaron normativa, main, runtime/systemd reales, claves, almacenes live, certificados desplegados, firewall, puertos, red, dependencias ni VPS de pruebas.

**Siguiente paso permitido:** revisar el diseño R-05 con el propietario. No iniciar implementación hasta aprobación expresa.


## Estado vigente — prioridad primer servicio real VLESS-WS-TLS (2026-11-04)

Este addendum prevalece sobre las fotografías anteriores para la prioridad y el siguiente punto de trabajo. Los registros históricos se conservan íntegros.

- **Objetivo prioritario:** demostrar la viabilidad de Xray-Core Manager ejecutando y administrando un servicio real VLESS + WebSocket + TLS, con operaciones del servidor realizadas desde el administrador.
- **Hoja de ruta:** `docs/PLAN_HITO_PRIMER_SERVICIO_REAL_VLESS_WS_TLS_2026-11-04.md`. Define H0 auditoría de brechas, H1 instalación/ciclo de vida, H2 DNS/TLS, H3 VLESS-WS-TLS, H4 perfil/configuración, H5 orquestación/confirmaciones, H6 adaptador systemd real y primera aplicación, H7 diagnóstico/backup/recuperación y H8 prueba externa.
- **R-01–R-04:** implementadas, verificadas/auditadas, publicadas y sincronizadas al commit `4433cd324756eb32f2d9b6b5d48ed8dba7681e34`; aceptación formal individual sigue pendiente. No repetirlas.
- **R-05:** el diseño previo de systemd simulado debe evolucionar como banco de pruebas de la orquestación, no como objetivo final. La primera aplicación real requiere adaptador real y autorización específica.
- **Decisiones nuevas aprobadas:** reinicio de servicio `active` requiere confirmación; rechazar deja la revisión publicada pendiente de aplicación y conserva el proceso actual; publicar con servicio `inactive` no lo inicia y permite inicio manual posterior desde el administrador con confirmación; usar `generation_id` único para cada operación y su evidencia.
- **Decisiones técnicas aún abiertas:** tratamiento final de estado previo `failed` cuando no pueda probarse equivalencia tras rollback; extensión versionada del journal R-03/R-04 o registro separado. La recomendación de diseño es fail-closed y extender el journal de forma compatible, respectivamente; no tratarlas como aprobaciones.
- **Aceptación formal:** no se declara aceptado ningún incremento nuevo ni cerrado ningún hito por este cambio documental.
- **Autorización live:** R-06/live continúa NO AUTORIZADA. La nueva prioridad no autoriza instalar Xray, modificar systemd/runtime, DNS, certificados, firewall, puertos, red ni ejecutar NetMod.
- **Normativa:** los documentos de `Xray-Normativa/` permanecen inmutables; `main` no se modifica; no utilizar la VPS de pruebas.
- **Pruebas:** esta actualización es exclusivamente documental; no reejecuta regresiones ni pruebas runtime.

**Siguiente acción:** H0 — auditoría de brechas, sin cambios live ni código de producto, para identificar exactamente qué capacidades ya existen y cuáles faltan antes de implementar.


## Addendum vigente — auditoría H0 del primer servicio VLESS-WS-TLS (2026-11-04)

Se inspeccionó en solo lectura el código, los menús, las pruebas/documentación existentes y las Etapas normativas 2, 4, 5 y 6. Informe: `docs/AUDITORIA_H0_BRECHAS_PRIMER_SERVICIO_VLESS_WS_TLS_2026-11-04.md`.

- Dictamen: el proyecto todavía NO está listo para un servicio real VLESS-WS-TLS administrado de extremo a extremo.
- Base reutilizable: instalador Xray 26.10.31 con SHA-256, módulo de preparación/control systemd, asistente/adaptador VLESS, almacén/resolutor TLS central y R-01–R-04.
- Brechas críticas: Etapa 4 (UI, dominios, DNS y ACME) ausente; VLESS-WS-TLS limitado a borrador/validación; falta exportación de perfil cliente y campos Host/SNI del flujo VLESS; activación de perfil ausente; R-01 preflight read-only dependiente de fixture de estado; R-02–R-04 fixture-only; R-05 no implementada; diagnóstico/backup genéricos parciales.
- Entorno verificado solo por metadata: Ubuntu 24.04.4 amd64; dependencias requeridas presentes; Xray 26.10.31 y geodata presentes; `xray.service`, `/etc/xray/config.json` y cuenta/grupo `xray` ausentes. No se ejecutó systemctl ni se consultó estado de servicio.
- Normativa: 14/14 archivos con homólogo en respaldo idénticos byte a byte.
- `install.sh --check`: PASS sin modificar el sistema. No se ejecutaron suites de pruebas.
- No se leyó la clave maestra, no se accedió a almacenes live, no se modificó runtime, systemd, DNS, certificados, firewall, puertos, red, dependencias ni VPS de pruebas.
- H0 queda PREPARADA, pendiente de aceptación formal. No autoriza código de producto ni cambios live. R-01–R-04 no deben repetirse; R-05 permanece no implementada.


## Estado vigente — prioridad MVP mínimo VLESS-WS-TLS (2026-11-04)

Este addendum prevalece sobre el orden de trabajo H1–H8 anterior. La aceptación formal de H0 queda registrada; el propietario aprobó reducir el alcance a un MVP vertical que demuestre primero la capacidad real del Manager.

- Plan técnico vigente: `docs/PLAN_MVP_DESPLIEGUE_VLESS_WS_TLS_2026-11-04.md`.
- Objetivo: desde Xray-Core Manager instalar/preparar Xray y `xray.service`, emitir/validar/registrar un certificado, crear usuario y conexión VLESS-WS-TLS, generar/validar configuración, publicarla, iniciar/aplicar el servicio y verificar conexión externa.
- Orden: B0 inspección focal → B1 instalación/servicio → B2 certificado → B3 usuario/conexión → B4 aplicación/inicio → B5 prueba end-to-end.
- Reutilizar instalador, módulo de servicio, Usuarios V2, asistente/modelo/adaptador VLESS, almacén/resolutor TLS y persistencia existentes. No repetir R-01–R-04.
- ACME propuesto para el primer MVP: Let's Encrypt/Certbot HTTP-01 standalone, condicionado a DNS correcto y disponibilidad/accesibilidad del puerto 80. La elección y la instalación de dependencias se revisarán antes de ejecutar; no se instalará nada sin autorización.
- Se aplazan R-05 avanzado, ampliaciones de journal/generation, reconciliación avanzada, DNS-01/proveedores DNS múltiples, renovación/rotación avanzada, múltiples protocolos/instancias y diagnóstico/backup general.
- Se conservan guardas esenciales: validación Xray antes de publicar, copia recuperable, reemplazo atómico, permisos mínimos, confirmación antes de reiniciar un servicio activo y fail-closed ante estado failed/desconocido. Un servicio inactive no se inicia por efecto lateral de publicar.
- H0 está ACEPTADA FORMALMENTE. La aprobación del MVP autoriza el plan y el trabajo aislado/documental, no operaciones live.
- No se ha iniciado implementación del MVP. No se modificaron código, runtime, systemd, certificados, DNS, firewall, puertos, red, dependencias, normativa, main ni VPS de pruebas en esta actualización.
- R-01–R-04 conservan su estado técnico/publicado; su aceptación formal individual sigue pendiente. R-05 avanzado queda en pausa. R-06/live no autorizada. Etapas 2, 3 y 5 abiertas.

**Siguiente acción permitida:** B0 — inspección focal del código y de la normativa pertinente, producir una matriz breve de reutilización/brechas y proponer el primer cambio mínimo de B1. No ejecutar acciones live.


## Estado vigente — aceptación y publicación I-02/I-03/I-04 (2026-11-05)

- I-02 — integración de compositor en menú de perfiles: IMPLEMENTADA, VERIFICADA, AUDITADA y ACEPTADA FORMALMENTE con limitaciones documentadas.
- I-03 — Host WebSocket y SNI cliente separados: IMPLEMENTADA, VERIFICADA, AUDITADA y ACEPTADA FORMALMENTE con limitaciones documentadas.
- I-04 — exportación de clientes VLESS-WS-TLS para NetMod: IMPLEMENTADA, VERIFICADA, AUDITADA y ACEPTADA FORMALMENTE con limitaciones documentadas.
- Autorización expresa recibida para commit/push/sincronización solo en `design/user-identity-association-v1`.
- Regresión ejecutada antes de publicar: Python 171/171; Bash 59/59; py_compile, bash -n, ShellCheck `-S error`, `install.sh --check`, `git diff --check`: PASS.
- Los 13 documentos normativos sustantivos comparados coinciden byte a byte con el respaldo. `Xray-Normativa/` no se modifica.
- Publicación y verificación remota se registran en el addendum de HISTORY y en el punto de control cuando se obtenga el SHA definitivo.
- No se probó NetMod real ni conectividad WAN. No se realizaron operaciones live ni cambios en runtime/systemd, certificados reales, DNS, firewall, puertos o red.
- Etapas 2, 3 y 5 permanecen ABIERTAS; R-06/live NO AUTORIZADA.


## Cierre de publicación — I-02/I-03/I-04 (2026-11-05)

- Commit funcional publicado: `ac119d923ba0eae35579e944d59f5262c5d105a7` en `design/user-identity-association-v1`.
- GitHub confirmó el mismo SHA; push fast-forward desde `792f382ca1b4f753ff763dc50a442aa66a0cd42f`.
- HEAD local = HEAD remoto después de `git fetch`; checkout limpio.
- `main` permanece en `656ecedc506a94a6461aee296b20871d51a38bf3`; `Xray-Normativa/` sin cambios; 13/13 documentos sustantivos comparados byte a byte con el respaldo.
- I-02/I-03/I-04: IMPLEMENTADAS, VERIFICADAS, AUDITADAS, ACEPTADAS, PUBLICADAS y SINCRONIZADAS.
- Sin NetMod real/WAN ni operaciones live. Etapas 2, 3 y 5 abiertas; R-06/live no autorizada.


## Estado vigente — B1-A / B1-B (2026-11-05)

- El propietario autorizó implementar B1-A y B1-B exclusivamente con fixtures y sin operaciones live.
- B1-A añade [7] Preparar servicio (verifica integridad) al submenú Administración de Xray-core. La acción verifica el manifiesto, muestra el alcance y exige confirmación; adquiere el bloqueo de ciclo de vida, revalida integridad bajo el lock y reutiliza xray_service_prepare; no inicia ni habilita el servicio y bloquea el cambio si Xray está activo.
- B1-B incorpora scripts/xray_install_integrity.py y el manifiesto /var/lib/xray-manager/state/xray-install.json: versión, arquitectura, rutas, SHA-256 del binario, geodata y paquete de origen; permisos root:root 0600, directorio 0700, escritura atómica y fsync.
- update y reinstall fallan cerrados si falta el manifiesto o no coinciden hashes/rutas/versión. repair es la recuperación explícita; respaldo y rollback incluyen el manifiesto. Instalaciones heredadas sin manifiesto quedan NO VERIFICADAS.
- Documentos: docs/DECISION_B1_SERVICE_PREPARATION_AND_INSTALL_INTEGRITY.md, docs/IMPLEMENTACION_B1_A_B1_B_2026-11-05.md, docs/AUDITORIA_B1_A_B1_B_2026-11-05.md.
- Pruebas: Bash 60/60 scripts PASS; Python unittest 171/171 PASS; py_compile global, bash -n global, ShellCheck -S error global, install.sh --check y git diff --check PASS.
- No se ejecutó preparación/instalación live ni el binario real systemctl; el estado activo se simuló con un stub. No se modificaron unidad/cuenta reales, runtime, certificados, DNS, firewall, puertos, red o dependencias.
- Rama: design/user-identity-association-v1. B1-A/B1-B aceptados formalmente y publicados mediante commit c8cd20c2a576fb1926fdcf11945cd75cf1c4211c. Push fast-forward confirmado; HEAD local y remoto coinciden. main permanece en 656ecedc506a94a6461aee296b20871d51a38bf3.
- Los 14 documentos normativos sustantivos se mantienen idénticos al respaldo; Xray-Normativa/ no se modificó.
- Etapas 2, 3 y 5 siguen ABIERTAS; R-06/live NO AUTORIZADA.

Siguiente acción: revisión del expediente B1 por el propietario; después, aceptación formal y autorización independiente de commit/push únicamente en la rama autorizada. No ejecutar B1 live ni avanzar a B2 sin autorización correspondiente.


## Estado vigente — B2 ACME Certbot (2026-11-05)

- El propietario aprobó Certbot como cliente ACME inicial: HTTP-01 standalone y DNS-01 manual TXT; API DNS se aplaza. Autorizó B2-A a B2-G exclusivamente en fixtures, sin instalación, ACME real, cambios DNS, operaciones live ni publicación.
- Se implementó scripts/certificate_acme.py: validación de dominios, wildcard solo DNS-01, construcción de comandos Certbot, preflight HTTP, hooks DNS, journal privado de solicitudes e importación de lineages Certbot al Certificate Store.
- Se incorporó modules/certificates.sh y se conectó la opción principal [3]. La UI permite solicitar ACME tras confirmación explícita, listar el almacén e importar un lineage emitido.
- La importación valida SAN, vigencia y correspondencia criptográfica; resuelve symlinks live solo dentro de archive, crea staging root-only y reutiliza el Certificate Store. Una prueba importa certificado sintético y obtiene/limpia un lease mediante Certificate Resolver con fixture VLESS-WS-TLS.
- Pruebas B2: 11/11 focales PASS; regresión global Python 182/182 y Bash 61/61 PASS; py_compile, bash -n, ShellCheck -S error, install.sh --check y git diff --check PASS. Evidencia en docs/AUDITORIA_B2_ACME_CERTIFICADOS_2026-11-05.md.
- Certbot y dig no se instalaron; no se ejecutó certbot --version, ninguna solicitud ACME real ni comunicación con CA. No se probó DNS público, propagación real, acceso WAN/puerto 80 ni identidad systemd real.
- B2 fue aceptada formalmente por el propietario el 2026-11-05, con las limitaciones y exclusiones de `docs/AUDITORIA_B2_ACME_CERTIFICADOS_2026-11-05.md`.
- Publicación funcional: `2669c45` (`feat(certificates): add Certbot ACME workflows`). Publicación documental: `21a103a7a15e003ddc3e2031aaf591efefe064ce` (`docs(certificates): record B2 ACME implementation and audit`). HEAD local/GitHub verificado en el segundo commit; checkout limpio.
- B2: IMPLEMENTADA, VERIFICADA, AUDITADA, ACEPTADA, PUBLICADA y SINCRONIZADA dentro del alcance fixture-only.
- No se instaló Certbot; no hubo ACME real, comunicación con CA, DNS/TXT real, acceso WAN/TCP 80 ni prueba con identidad systemd real. No se modificaron runtime, certificados persistentes, DNS, firewall, puertos, red, dependencias, normativa, main ni VPS de pruebas.
- Etapa 4 sigue ABIERTA. R-06/live NO AUTORIZADA.

**Siguiente paso permitido:** realizar B3 — usuario y conexión VLESS-WS-TLS — comenzando por el contraste documental específico y la inspección read-only de los componentes existentes. No ejecutar operaciones live ni ampliar el alcance sin autorización específica.

## Addendum 2026-11-05 — R-05 fixture-only implementada y auditada

- El propietario autorizó R-05 exclusivamente con fixtures, mocks, almacenes temporales y extensión compatible del journal. No se autorizó systemd/Xray real ni R-06/live.
- Nuevos: `scripts/xray_runtime_service_adapter.py`, `scripts/xray_runtime_orchestrator.py`, `tests/test_xray_runtime_orchestrator.py`, `docs/DECISION_R05_JOURNAL_GENERATION_2026-11-05.md`, `docs/IMPLEMENTACION_R05_ORQUESTACION_FIXTURE_2026-11-05.md`, `docs/AUDITORIA_R05_ORQUESTACION_FIXTURE_2026-11-05.md`.
- Modificados: `scripts/xray_runtime_journal.py` (schema 1 compatible + schema 2 estricto y generation_id), `scripts/xray_runtime_preflight.py` (estado unknown documentable para fail-closed R-05), `scripts/xray_runtime_publisher.py` (fase schema 2 y delegación de recovery a R-05), `tests/test_xray_runtime_preflight.py`.
- R-05 coordina R-01→R-04 con adaptador simulado, CAS, generación única, verificación por estado+generation_id+SHA-256, publicación pendiente para active sin confirmación e inactive sin start, fail-closed para failed/unknown, rollback y recovery idempotente.
- Auditoría: 40/40 pruebas focales R-05 PASS; Python global 227/227 PASS; Bash 61/61 PASS; compileall, bash -n, ShellCheck -S error, install.sh --check y git diff --check PASS. No se añadieron dependencias.
- R-05 no tiene UI ni adaptador systemd real. Falta integrar el registro persistente de perfil activo exigido por Etapa 5 §7. No se cierra Etapa 5/6.
- No se tocaron systemd/Xray real, runtime, certificados persistentes, claves, DNS, firewall, puertos, red, `main`, `Xray-Normativa/` ni VPS de pruebas. R-06/live sigue NO AUTORIZADA.
- Estado: IMPLEMENTADA, VERIFICADA Y AUDITADA; aceptación formal del propietario y publicación todavía pendientes.
- Próximo paso: revisión del informe de auditoría R-05 por el propietario. No publicar hasta aceptación y autorización de publicación separada.


## Addendum vigente — corrección y reauditoría de concurrencia R-05 (2026-11-05)

El propietario autorizó corregir el hallazgo de concurrencia y repetir la auditoría exclusivamente con fixtures. Se incorporó `fcntl.flock` interproceso mediante `adapter.lock` root-only. El bloqueo cubre la transacción completa de `status`, `restart`, `restore` y `audit_events`, incluyendo CAS y escritura de bitácora. Se valida `O_NOFOLLOW`, tipo/propietario/permisos, hardlinks, marcador e identidad de inode.

Se añadieron pruebas multiproceso: dos restart concurrentes con el mismo estado previo (un ganador y un rechazo), cuatro status concurrentes sin pérdida de eventos, dos restore concurrentes (una restauración y un rechazo) y rechazo de lock symlink.

**Resultado actualizado:** 43/43 pruebas focales R-05; 230/230 Python global; 61/61 Bash; `compileall`, `bash -n`, ShellCheck `-S error`, `install.sh --check` y `git diff --check` PASS. Escaneo del adaptador sin invocaciones a servicios/procesos reales. Sin dependencias nuevas.

R-05 queda CORREGIDA, VERIFICADA Y AUDITADA LOCALMENTE; aceptación formal pendiente. No se publicó ni se autorizó publicación. No se ejecutaron operaciones live ni se modificaron systemd/Xray real, runtime persistente, certificados, claves, DNS, firewall, puertos, red, `main`, `Xray-Normativa/` o VPS de pruebas. R-06/live continúa NO AUTORIZADA.

**Siguiente acción:** revisión del propietario y aceptación formal de la auditoría corregida. La publicación requiere autorización separada.

## Aceptación formal y autorización de publicación R-05 — 2026-11-05

El propietario acepta formalmente R-05 en el alcance fixture-only auditado en `docs/AUDITORIA_R05_ORQUESTACION_FIXTURE_2026-11-05.md` y autoriza publicar los cambios exclusivamente en `design/user-identity-association-v1`. La aceptación no cierra Etapa 5/6 ni Etapa 2; no acepta UI, registro persistente de perfil activo, adaptador systemd real ni operaciones live. R-06/live continúa NO AUTORIZADA. `main` y `Xray-Normativa/` quedan fuera de la publicación.

## B4 fixture-only — aplicación y registro activo (2026-11-05)

Autorizado por el propietario para implementación y auditoría aislada; sin operaciones live, commit ni push.

- Nuevo \`scripts/xray_runtime_active_profile.py\`: almacén fixture-only, marcador dedicado, root:root 0700/0600, JSON estricto, lock interproceso, escritura atómica/fsync e idempotencia.
- \`scripts/xray_runtime_orchestrator.py\`: registro del perfil solo después de observar estado \`active\` con \`generation_id\` y SHA-256 exactos; recovery puede reconciliar el registro tras una interrupción.
- \`scripts/xray_runtime_service_adapter.py\`: start simulado por CAS desde inactive.
- \`scripts/xray_runtime_journal.py\`: schema 2 reconoce \`start_requested\`/\`service_start_requested\`.
- Desde inactive, la publicación permanece \`published_pending_start\`; el start fixture posterior exige confirmación explícita.
- Estados pendientes, rechazo y rollback conservan el registro anterior. Fallos ambiguos quedan fail-closed.
- Auditoría B4: \`docs/IMPLEMENTACION_B4_APLICACION_FIXTURE_2026-11-05.md\` y \`docs/AUDITORIA_B4_APLICACION_FIXTURE_2026-11-05.md\`.
- Resultado: 59/59 focales R-05+B4, 246/246 Python globales, 61/61 suites Bash; compileall, bash -n, ShellCheck -S error, install.sh --check y git diff --check PASS.
- B4 continúa incompleta para producción: sin integración de menú, sin adaptador systemd real y sin prueba externa. No se ejecutó systemd real, no se modificó \`/etc/xray\`, certificados, DNS, firewall o red.
- \`Xray-Normativa/\` y \`main\` intactas. Sin commit/push. HEAD base permanece \`2902b2ef602dfe97acf62428d6b7c35ce7c81d5d\`.

## H6-A — adaptador systemd de observación (2026-11-05)

Implementado `scripts/xray_runtime_systemd_adapter.py` como adaptador separado read-only. Consulta propiedades allowlist de `xray.service`, valida la unidad administrada y calcula únicamente el hash actual del archivo runtime. No afirma que ese hash sea el cargado por el proceso; `loaded_generation_id` y `loaded_config_sha256` permanecen nulos hasta contar con atestación ligada a InvocationID.

Pruebas: 11/11 focales, 59/59 R-05+B4, 257/257 Python globales; smoke Bash, ShellCheck, AST y diff-check PASS. Las llamadas systemd fueron simuladas en pruebas. No se conectó a R-05 ni al menú, no hay acciones mutadoras ni operaciones live. Auditoría: `docs/AUDITORIA_H6A_ADAPTADOR_SYSTEMD_OBSERVACION_2026-11-05.md`.

Siguiente: diseñar atestación generation_id/config_sha256/InvocationID e inyección segura del backend, manteniendo fixture como default. H6/live sigue NO AUTORIZADA. Sin commit/push; `main` y `Xray-Normativa/` intactas.


## H6-B — atestación persistente de generación systemd (2026-11-06)

Se implementó H6-B en alcance aislado: `scripts/xray_runtime_attestation.py` y `tests/test_xray_runtime_attestation.py`. La atestación enlaza operation_id, generation_id, SHA-256 publicado, InvocationID nuevo/estable, ActiveEnterTimestamp, SHA-256 de la unidad y fecha UTC. El almacén reservado es `/var/lib/xray-manager/attestations`, pero no se creó ni se utilizó en el sistema real.

Contraste normativo: Etapa 5 §§4, 5 y 7 exige distinguir configuración guardada/aplicada, verificar la configuración realmente ejecutada y actualizar el registro activo solo después de verificar. Etapa 6 §2 exige observación del estado/proceso y verificación de funcionamiento. H6-B aporta evidencia técnica para ese objetivo, pero aún no completa la activación funcional ni la verificación end-to-end.

Auditoría: 12/12 pruebas focales H6-B; 269/269 Python global; pruebas Bash de servicio, control de servicio y preparación PASS; compileall, bash -n global, ShellCheck -S error, install.sh --check y git diff --check PASS. El módulo no invoca systemctl, subprocess, shell ni eval.

Limitaciones: observaciones sintéticas; sin systemctl/Xray real; no conectado a H6-A, R-05, B4, menú ni CLI. La futura integración debe mantener el lock de ciclo de vida durante transición, observaciones y persistencia, y usar snapshots directos de H6-A. H6-B queda IMPLEMENTADA, VERIFICADA Y AUDITADA, PASS CON LIMITACIONES. No se hizo commit ni push. HEAD continúa `be524eef65037f74bb36ee9e7fd9b385c3ffb613`; rama `design/user-identity-association-v1`. `main` y `Xray-Normativa/` permanecen intactas. No hubo operaciones live ni cambios de runtime, systemd, certificados, DNS, firewall, puertos, red o dependencias.

Siguiente paso propuesto: H6-C, integración del almacén/atestación con R-05 mediante backend inyectable, manteniendo fixture como default y sin habilitar ejecución real desde CLI. Requiere revisión y autorización del alcance de integración; no habilita operaciones live.


## H6-C — integración R-05/H6-B (2026-11-06)

El propietario autorizó H6-C exclusivamente con mocks y fixtures. Se modificó scripts/xray_runtime_orchestrator.py para inyección de backend por contexto, manteniendo el adaptador fixture R-05 como default. Los backends alternativos sólo se aceptan como dobles de prueba explícitos; no hay selector real en CLI. Se conectó la persistencia H6-B a las rutas fixture de start/restart, con snapshots sintéticos before/after/confirmed dentro del lock de ciclo de vida. Divergencias provocan rollback fixture. Recovery valida la atestación persistida y falla cerrado si falta.

Evidencia: docs/IMPLEMENTACION_H6C_INTEGRACION_R05_ATESTACION_2026-11-06.md y docs/AUDITORIA_H6C_INTEGRACION_R05_ATESTACION_2026-11-06.md. H6-C 7/7 focales, H6-B 12/12 focales y Python global 276/276 PASS. compileall, bash -n, ShellCheck -S error, install.sh --check, tres pruebas Bash de servicio y git diff --check PASS.

Limitaciones: las observaciones son sintéticas; H6-A no se invocó; no existe backend mutador systemd ni selección live en CLI. La marca de doble de prueba es una salvaguarda de diseño, no una frontera contra código Python arbitrario. Sin systemctl/Xray real, WAN, certificados/DNS/firewall/red o dependencias. No commit/push. main y Xray-Normativa/ intactas. H6-C queda IMPLEMENTADA, VERIFICADA Y AUDITADA, PASS CON LIMITACIONES. Siguiente bloque requiere diseñar el adaptador de servicio real por separado y solicitar autorización live específica.
## H6-D — integración de menú de perfiles con R-05 fixture (2026-11-06)

Estado: IMPLEMENTADA Y AUDITADA, PASS CON LIMITACIONES. El menú Etapa 5 y Gestión de perfiles enrutan a un puente fixture-only que exige marcador R-02, rutas confinadas, revisión validada y confirmación. En modo normal permanece bloqueado. Backend explícito `xray_runtime_service_adapter`; no H6-A/systemd real, no Xray real, no aplicación live. Pruebas: puente 4/4, menú Bash PASS, Python global 280/280 PASS. Documentos: `docs/IMPLEMENTACION_H6D_MENU_PERFILES_R05_FIXTURE_2026-11-06.md`, `docs/AUDITORIA_H6D_MENU_PERFILES_R05_FIXTURE_2026-11-06.md`.

## Addendum 2026-11-06 — H6-E1

H6-E1 amplió el observador H6-A para comprobar la definición efectiva de xray.service: NeedDaemonReload=no, ausencia de DropInPaths, Type=simple, ExecStartPre y ExecStart con argv exactos. La validación de config.json exige root:xray y modo 0640, coherente con modules/xray_service.sh, y compara identidad inode entre lstat y descriptor abierto.

Auditoría: 20/20 pruebas focales H6-A, 289/289 Python global, compileall, bash -n, ShellCheck -S error, pruebas Bash de servicio, install.sh --check y git diff --check PASS. Las pruebas sustituyen systemctl por mocks; no se inspeccionó /proc ni se realizaron operaciones live.

H6-E1 PASS CON LIMITACIONES. H6-E2 queda como siguiente subbloque: identidad de proceso con mocks. No hay backend systemd mutador ni selector live. Sin commit/push; main y Xray-Normativa/ intactas.

## H6-E2 — identidad del proceso (2026-11-06)

Implementado scripts/xray_runtime_process_identity.py como inspector read-only separado. Verifica PID/starttime antes/después, UID/GID efectivos, destino de /proc/PID/exe, argv exacto y SHA-256 del ejecutable. Procfs alternativo exige marcador fixture. No atribuye configuración cargada al proceso (configuration_loaded=false, configuration_evidence=not_attested).

Pruebas focales 22/22; Python global 332/332; py_compile, compileall, bash -n, pruebas Bash de servicio, install.sh --check, ShellCheck -S error y git diff --check PASS. Sólo fixtures. No se conectó a H6-A/R-05 ni se inspeccionó proceso real. H6-E2 PASS CON LIMITACIONES; H6-E3 y H6-E4 pendientes. Sin commit/push; main y Xray-Normativa/ intactas.

## H6-E3 — correlación de proceso y atestación (2026-11-06)

Nuevo scripts/xray_runtime_process_attestation.py correlaciona H6-A antes/después con H6-E2 para el MainPID, exigiendo estabilidad de PID, InvocationID, ActiveEnterTimestamp y unidad. R-05 exige process_identity en snapshots after/confirmed y falla cerrado ante ausencia/divergencia. H6-B schema v2 persiste PID/starttime, ruta/hash de ejecutable, UID/GID y argv. No existían atestaciones reales schema v1; almacén reservado no creado.

Pruebas focales: correlación 16/16, H6-B 15/15, H6-C 9/9; Python global 332/332. py_compile, compileall, bash -n, pruebas Bash de servicio, install.sh --check, ShellCheck -S error y git diff --check PASS. Todo con mocks/dobles/fixtures. No systemctl/Xray/procfs real, no backend mutador ni selector live. H6-E3 PASS CON LIMITACIONES; H6-E4 pendiente. Sin commit/push; main y Xray-Normativa/ intactas.

## Auditoría integral H6-E — 2026-11-06

H6-E1/E2/E3 y la integración H6-A/B/C/D revisadas conjuntamente. Dictamen PASS CON LIMITACIONES. Evidencia: H6-E2 22/22, correlación 16/16, H6-B schema v2 15/15, H6-C 9/9 y Python global 332/332 PASS; py_compile, compileall, bash -n, pruebas Bash de servicio, install.sh --check, ShellCheck -S error y git diff --check PASS.

Sin systemctl ni proceso Xray real, sin procfs de producción, sin backend mutador, sin WAN ni prueba de instalación limpia. No se ha probado configuración realmente cargada ni conexión cliente. H6-F queda como evaluación previa a prueba live y requiere autorización específica. Sin commit/push; main y Xray-Normativa/ intactas.

## H6-F — evaluación de preparación para prueba real (2026-11-06)

Evaluación read-only completada; dictamen NO LISTO END-TO-END. install.sh instala Xray y prepara xray.service por defecto; Certbot no está en dependencias y certificate_acme.py no lo instala; normativa Etapa 4 deja pendiente selección ACME formal; exportador VLESS-WS-TLS usa hellen.tvrc.me como endpoint por defecto; aplicación R-05 sigue fixture-only y no existe backend mutador live.

Plan, contraste normativo, bloqueos y autorizaciones requeridas: docs/EVALUACION_H6F_PREPARACION_PRUEBA_REAL_2026-11-06.md. No se ejecutó systemctl/Xray/Certbot real, no se cambiaron DNS/firewall/puertos, no hubo WAN ni cambios de código/dependencias. H6-F requiere decisiones y autorización específica antes de cualquier acción live.

## Instalador Manager-only por defecto (2026-11-06)

Implementado y auditado en prefijos aislados. install.sh --install despliega sólo el Manager; no instala Xray-core, no crea cuenta/grupo xray, no prepara /etc/xray ni modifica systemd. --install --with-xray conserva explícitamente la instalación integral. El preflight de rutas Xray sólo se realiza en el modo integral. Estado inicial: manager_installed=true, xray_installed=false, service_configured=false.

Evidencia: tests/install.sh PASS; Python 332/332, Bash 62/62, bash -n, ShellCheck -S error, compileall, install.sh --check y git diff --check PASS. Implementación y auditoría: docs/IMPLEMENTACION_INSTALADOR_MANAGER_ONLY_2026-11-06.md y docs/AUDITORIA_INSTALADOR_MANAGER_ONLY_2026-11-06.md. Sólo fixtures/prefijos temporales; no instalación real, systemctl ni Xray. H6-F continúa NO LISTO END-TO-END por backend runtime live, ACME y endpoint. Sin commit/push.

## Reconciliación documental y sincronización (2026-11-06)

Los estados cronológicos anteriores a este corte se conservan por trazabilidad. Para el estado operativo prevalece el bloque Estado vigente — corte 2026-11-06. H6-E4 es la auditoría integral del bloque H6-E y está documentada; no habilita live. El cambio Manager-only está implementado. H6-F mantiene bloqueos ACME/Certbot, endpoint/Host/SNI, VPS de aceptación y backend mutador. Publicación confirmada: implementación en 4984ce207ff446bb097cc53c6445ad1e9b53c585 y cierre documental en 537fb5475ce6bfcbba8401a1fced1642ca203cba, ambos en design/user-identity-association-v1. HEAD local/remoto: 537fb5475ce6bfcbba8401a1fced1642ca203cba; árbol limpio. main permanece en 656ecedc506a94a6461aee296b20871d51a38bf3.


## H6-G2 — puente seguro hacia el controlador de servicio (2026-11-06)

Contrato G1 aprobado y documentado en `docs/DECISION_H6G1_CONTRATO_BACKEND_RUNTIME_LIVE_2026-11-06.md`. El propietario aprobó el contrato H6-G1 y autorizó la implementación G2 en desarrollo, exclusivamente con mocks/fixtures. Se agregó `scripts/xray_runtime_service_control.py` y el punto de entrada `xray_service_action_inherited_lock()` en `modules/xray_service.sh`. Python hereda explícitamente el descriptor lifecycle lock hacia Bash; ambos lados verifican ruta/inode y condiciones de seguridad. Las acciones permitidas en este puente son start/restart/stop y se delegan al controlador único `xray_service.sh`; Python no ejecuta systemctl directamente.

Pruebas: puente Python 9/9; observación systemd y atestación de proceso/identidad 58/58; Python global 341/341; las 62 suites Bash ejecutadas finalizaron correctamente; `bash -n`, `py_compile` y `git diff --check` PASS. La integración Python→Bash utilizó systemctl mock. Las pruebas VLESS/VMess con Xray 26.10.31 validan configuraciones en entorno temporal, no una instancia real expuesta a WAN.

**Límites:** G2 está IMPLEMENTADA PARCIALMENTE; falta auditoría formal independiente. El puente no está conectado a R-05, no se habilitó backend live en `_with_service_backend` ni en el menú. No se modificó journal/orquestador, runtime persistente, unidad systemd real, `/etc/xray`, certificados, DNS, firewall, puertos ni red. No se ejecutaron acciones reales start/restart/stop, ACME ni conexión externa. El hash del archivo runtime sigue sin equivaler a evidencia de configuración cargada en memoria.

Archivos de esta entrega: `modules/xray_service.sh`, `scripts/xray_runtime_service_control.py`, `tests/test_xray_runtime_service_control.py`, `tests/xray_service_control.sh` y `docs/IMPLEMENTACION_H6G2_PUENTE_CONTROL_SERVICIO_2026-11-06.md`.

Estado Git: rama `design/user-identity-association-v1`, HEAD base `9bab1dbed7d4873aa30a3fd00a976a1d666d9355`; árbol con cambios locales sin commit. Sin push. `main` y `Xray-Normativa/` intactas. Las VPS de prueba no fueron utilizadas.

**Siguiente:** auditoría formal del puente G2 y luego G3: diseñar la semántica live de observación, transición, correlación de InvocationID y rollback sin inferir configuración cargada. No habilitar live hasta superar G3/G4/G5 y recibir autorización específica para el host real.


## H6-G2-B — backend live aislado (2026-11-06)

Implementado en desarrollo: `scripts/xray_runtime_live_backend.py` y `tests/test_xray_runtime_live_backend.py`. Compone observación systemd read-only + atestación de proceso, separa hash runtime de evidencia de proceso y no afirma configuración cargada. Define precondiciones start/restart/stop con confirmación, doble observación CAS conservadora y resultado `accepted_not_verified`. `restore()` falla cerrado hasta G3. Pruebas: Python 355/355, Bash 62/62, estáticas PASS. No integrado a R-05/menú, no systemd real, no live, no commit/push. G2 sigue parcial. Ver `docs/IMPLEMENTACION_H6G2B_BACKEND_RUNTIME_LIVE_2026-11-06.md`.


## Auditoría independiente H6-G2 (2026-11-06)

Resultado: PASS CON LIMITACIONES; NO APTO PARA INTEGRACIÓN LIVE y G2 NO CERRADO. Hallazgos F-01: snapshot inactive acepta PID/InvocationID contradictorios; F-02: start no acredita generación publicada/validada, solo hash runtime esperado; F-03: flock puede adquirir lock libre, no demuestra handoff previo desde R-05; F-04/F-05: timeout y rollback necesitan reconciliación transaccional G3. Python 355/355, Bash 62/62, ShellCheck Bash PASS, estáticas PASS. Auditoría: `docs/AUDITORIA_H6G2_BACKEND_RUNTIME_LIVE_2026-11-06.md`. Live sigue deshabilitado; fixture default.


## H6-G2 — F-03: propiedad verificable del lifecycle lock (2026-11-06)

Se corrigió el handoff del lock en el puente Python/Bash. La validación ya no llama `flock(LOCK_EX|LOCK_NB)` sobre el descriptor recibido, porque eso podía adquirir un lock libre. Python y Bash verifican la entrada FLOCK exclusiva de `/proc/.../fdinfo`, el PID propietario R-05 y la identidad inode; cualquier ausencia o divergencia bloquea la acción. Pruebas focales: Python 12/12 y `tests/xray_service_control.sh` PASS.

F-03 queda implementado en el puente aislado, pendiente auditoría independiente. No se conectó a R-05/menú ni se amplió todavía la duración del lock sobre todo el ciclo transaccional; G3 debe resolver ese alcance y evitar reacquisiciones anidadas. Fixture sigue default, live deshabilitado. Sin systemctl/Xray real, cambios runtime, dependencias, commit ni push. Documentos: `docs/DECISION_H6G2_F03_PROPIEDAD_LIFECYCLE_LOCK_2026-11-06.md` y `docs/IMPLEMENTACION_H6G2_F03_PROPIEDAD_LIFECYCLE_LOCK_2026-11-06.md`.

## H6-G3-A/B — coordinación transaccional R-05 (2026-11-06)

Implementado en desarrollo: `publisher.transaction_locks()` es el propietario único de lifecycle→application locks y permite reutilización anidada sin reacquisición ni liberación accidental. `apply_operation()` conserva los locks desde la revalidación posterior al staging hasta publicación, transición, observación y rollback. `start_pending_operation()` y `_recover_one()` mantienen el mismo ámbito en start y recuperación. Los locks se liberan en orden inverso.

Pruebas nuevas: contexto anidado, lock sostenido durante publish/restart/rollback, start pendiente y recovery con rollback anidado. Python global 377/377, Bash 62/62, py_compile/compileall, bash -n, ShellCheck -S error y git diff --check PASS. Evidencia: `docs/IMPLEMENTACION_H6G3_A_B_COORDINACION_LOCKS_2026-11-06.md`.

Estado: G3-A/B implementados y verificados con fixtures; auditoría independiente pendiente. G3-C (timeout/resultado ambiguo), G3-D (rollback adversarial) y G3-E (auditoría integral) siguen abiertos. H6-G2 no se cierra; backend live sigue deshabilitado y no conectado a R-05/CLI/menú. Sin systemctl/Xray real, dependencias, commit o push. `main` y `Xray-Normativa/` intactas.


## H6-G3-C — reconciliación de timeout/ambigüedad (2026-11-06)

Implementado en R-05 fixture. Los resultados timeout/response_lost se conservan en el journal y la transición se decide por observación exacta de estado, generación y hash. Timeout antes de la acción con estado previo intacto permite rollback de configuración sin mutar servicio; timeout o respuesta perdida después de transición exacta se reconcilia como completado sin repetir acción. Si la observación es failed/unknown, no correlacionada o no disponible, se restaura la configuración cuando es seguro y se registra `RECOVERY_REQUIRED`, sin otra mutación de servicio. Ese estado queda como `NO_OP` en recuperaciones automáticas.

Se añadió failpoint de prueba tras persistir start request y pruebas para start timeout_before/timeout_after/response_lost_after, crash antes de start, estados failed/unknown y reobservación fallida. Suite focal R-05: 67/67 PASS. Evidencia: `docs/IMPLEMENTACION_H6G3_C_TIMEOUT_RECONCILIACION_2026-11-06.md`.

**Límites:** sólo fixtures/mocks. El backend live continúa aislado, sin reconciliación durable propia, sin conexión a R-05/CLI/menú. No se modifica journal para aceptar live ni se realiza rollback live. G3-C implementado focalmente; auditoría pendiente. G3-D y G3-E pendientes; H6-G2 permanece abierto. Sin systemctl/Xray real, dependencias, cambios persistentes, commit ni push.


## H6-G3-D — rollback fixture adversarial e idempotencia (2026-11-06)

La auditoría adversarial encontró un defecto: si el snapshot se corrompía después de publicar, `_load_operation()` lanzaba antes de que rollback/recovery pudiera persistir `RECOVERY_REQUIRED`. Se ajustó el camino controlado del publicador para leer el journal estructuralmente, validar snapshot y registrar `recovery_required` ante corrupción, sin usar el snapshot ni sobrescribir el runtime.

Pruebas adversariales añadidas: drift externo antes de rollback; snapshot corrupto durante rollback y recovery; drift externo después de crash tras rename; recovery repetido byte-a-byte idempotente; generación de servicio ajena después de restaurar configuración; crash después de restaurar servicio sin repetir restore; fallo de restore seguido de recovery `NO_OP`. Se conservan pruebas de symlink/hardlink, TOCTOU, ausencia de snapshot previo y crashes de rename.

Resultados: publicador + orquestador 86/86 PASS; Python global 388/388 PASS. Documento: `docs/IMPLEMENTACION_H6G3_D_ROLLBACK_FIXTURE_2026-11-06.md`.

**Estado:** G3-A/B/C/D implementados y verificados con fixtures. G3-E auditoría independiente integral pendiente. H6-G2 permanece abierto; backend live no conectado y no habilitado. Sin systemctl/Xray real, dependencias, operaciones persistentes, commit ni push. `main` y `Xray-Normativa/` intactas.


## H6-G3-E — auditoría integral de segunda pasada (2026-11-06)

Se completó una segunda pasada sobre G3-A/B/C/D, contrastando el contrato transaccional, publicador R-04, orquestador R-05, journal, rollback, recuperación y aislamiento live. **Dictamen: PASS CON LIMITACIONES en alcance fixture.** No se identificó un defecto bloqueante nuevo dentro de ese alcance.

Validación global: Python **388/388**, Bash **62/62**, `bash -n` global, ShellCheck `-S error`, `install.sh --check` y `git diff --check` PASS. Los 14 archivos normativos maestros coinciden byte a byte con `Xray-Normativa/`; el único archivo adicional es el README auxiliar. `main` y `Xray-Normativa/` permanecen sin modificaciones.

Esta revisión fue realizada por la misma sesión que participó en la implementación: es una **auditoría de segunda pasada, no independiente**. No habilita live. El backend live sigue desconectado y bloqueado; H6-G2 permanece abierto y el MVP NO está listo para despliegue end-to-end. Las suites de protocolos invocaron Xray 26.10.31 únicamente con `run -test` sobre configuraciones temporales; no se inició un servidor ni se modificó runtime persistente.

Informe: `docs/AUDITORIA_H6G3_E_SEGUNDA_PASADA_2026-11-06.md`. Sin systemctl real, cambios de runtime, certificados, DNS, firewall, puertos, red, dependencias, VPS de pruebas, commit o push.

## H6-G3 — paquete de revisión independiente preparado

Se creó `docs/PAQUETE_REVISION_INDEPENDIENTE_H6G3_2026-11-06.md` con inventario de archivos, contrato, restricciones de seguridad, escenarios adversariales y prompt para otro revisor. La revisión independiente aún no se ha ejecutado ni se declara completada. G3-E sigue siendo auditoría de segunda pasada de la misma sesión. Backend live no habilitado; sin commit/push.
