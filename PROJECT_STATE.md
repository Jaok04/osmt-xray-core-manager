# Xray Core Manager — Estado del proyecto

**Corte de estado:** 2026-11-03 — contenedor cifrado compartido v1 IMPLEMENTADO/VERIFICADO en aislamiento; orquestación backup/restore pendiente. VMess técnicamente preparado para aceptación (VM-48 pendiente). Certificados TLS centralizados: almacén/resolutor parciales; integraciones VMess y VLESS parciales, verificadas en fixtures y no aceptadas. Ver `docs/IMPLEMENTACION_VMESS_TLS_CENTRALIZADO_PARCIAL.md`.
**Estado global:** Etapa 1 aceptada por el propietario; Etapa 2 en desarrollo y abierta.
**Repositorio:** https://github.com/Jaok04/xray-core-manager
**Rama autorizada:** design/user-identity-association-v1
**VPS de desarrollo:** /opt/xray-manager

> Este documento es una fotografía de estado, no sustituye la documentación normativa. Antes de actuar, verifica el HEAD actual de GitHub y vuelve a inspeccionar la VPS.

> **Regla obligatoria permanente:** antes de implementar cualquier etapa o funcionalidad, contrastar el proyecto con la documentación preliminar aprobada en `Xray-Normativa/` del repositorio (respaldo original en `/root/Xray_Manager_Documentacion_Final_2026-10-31`). Las mejoras requieren informe previo y autorización expresa del propietario. Ver `docs/REGLA_CONTRASTE_DOCUMENTACION_PRELIMINAR.md` y `AGENTS.md`.

> **Segunda regla obligatoria permanente:** ninguna etapa se declara TERMINADA/COMPLETADA sin auditoría integral y documentación técnica de todos sus puntos, subpuntos, módulos, submódulos y componentes internos, matriz de trazabilidad, pruebas y aceptación formal expresa. Cerrar un módulo no cierra su etapa. Ver `docs/REGLA_AUDITORIA_INTEGRAL_CIERRE_ETAPAS.md` y `AGENTS.md`.


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

Pruebas: nuevo `tests/vless_restore_preserves_vmess.sh` cubre VMess anteriores/posteriores al backup, referencias de configuración/secreto, integridad byte a byte del almacén, colisiones, catálogo corrupto, refs rotas y fallo de escritura. `tests/vless_backup_journal_crash_matrix.sh` conserva cobertura de 32 interrupciones con catálogo VMess válido. Suite completa: 37/37 scripts PASS. `python3 -m py_compile scripts/*.py`, `bash -n` de todos los scripts Bash, `install.sh --check`, ShellCheck warning de pruebas modificadas y `git diff --check`: PASS.

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
