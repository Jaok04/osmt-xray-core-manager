## 2026-11-03 — Incorporación de Xray-Normativa al repositorio

Por instrucción expresa del propietario, se incorporó la documentación maestra normativa a `Xray-Normativa/` en la rama `design/user-identity-association-v1`. Se copiaron los 14 archivos originales conservando nombres, estructura y contenido; se añadió `README.md` como regla de custodia, sin alterar los documentos normativos. La carpeta queda protegida: ningún archivo podrá modificarse, corregirse, reformatearse, renombrarse, moverse, eliminarse o sustituirse sin consentimiento previo, explícito y específico del propietario. La autorización para desarrollar código no implica autorización para modificar la normativa.

Desde esta actualización, `Xray-Normativa/` es la ubicación canónica versionada en GitHub y en `/opt/xray-manager`. La copia original `/root/Xray_Manager_Documentacion_Final_2026-10-31` se conserva en la VPS como respaldo. Antes de cada etapa o módulo se debe contrastar el alcance punto por punto con `Xray-Normativa/`; las divergencias se presentan antes de editar o implementar.

Publicación confirmada en GitHub, rama `design/user-identity-association-v1`: commit de incorporación `1f303fdd1ab4776a2b33b821140cb3502c3801bb`, seguido de corrección de preservación byte a byte `0f6ee47fd38be85495769ab29cc73a970c81f9a7`. Se verificó que los 14 documentos normativos del directorio original y los 14 de `Xray-Normativa/` son idénticos por SHA-256 (mismos bytes, nombres y estructura). El checkout local quedó alineado con el HEAD remoto `0f6ee47fd38be85495769ab29cc73a970c81f9a7`; la única entrada no versionada preexistente `scripts/__pycache__/` se conservó sin cambios.

## 2026-11-02 — Aprobación y formalización del diseño VMess

- El propietario aprobó el diseño técnico VMess y confirmó expresamente que VMess-HTTPUpgrade-TLS también será implementado.
- La matriz aprobada contempla 14 identificadores del catálogo: WS sin TLS/TLS; RAW/TCP TLS/REALITY; gRPC sin TLS/TLS/REALITY; HTTPUpgrade sin TLS/TLS; XHTTP sin TLS/TLS/REALITY; mKCP sin TLS/TLS.
- Se contrastó la decisión con la especificación preliminar Etapa 2 revisión 1.3, el catálogo config/protocols.tsv, la navegación y las decisiones complementarias existentes. La especificación preliminar no se reescribió; la ampliación queda registrada como decisión complementaria.
- Se confirmó que el catálogo contiene vmess_httpupgrade_tls, pero el menú actual sólo permite seleccionar HTTPUpgrade sin TLS. No hay todavía modelo, adaptador, asistente ni persistencia VMess.
- Se creó docs/DISEÑO_TECNICO_VMESS.md y se actualizaron docs/DECISIONES_ETAPA_2.md, PROJECT_STATE.md y docs/PUNTO_CONTROL_ACTUAL.md.
- No se modificó código, catálogo, pruebas, runtime, firewall, puertos ni certificados. Esta actualización formaliza diseño; la implementación requiere un contraste previo específico y autorización expresa posterior.
- Publicación inicial del diseño y las decisiones en la rama autorizada: commit 90ff83510691e8daef934ff8bbafd08cb576e03a. El árbol local/remoto coincidió en 0687ee1225e14790cd69a4f486a3cff8cc200845.
- VMess permanece NO IMPLEMENTADO; HTTPUpgrade-TLS está APROBADO EN DISEÑO, NO IMPLEMENTADO y NO VERIFICADO. Etapa 2 permanece abierta.

### Precisión del estado de Etapa 3

Durante la revisión final se ajustaron PROJECT_STATE.md y docs/PUNTO_CONTROL_ACTUAL.md para no describir Etapa 3 como inexistente: el árbol contiene módulos, pruebas y documentación de usuarios/identidades/asociaciones (incluidos users_v2). Su estado formal y cobertura requieren una auditoría específica.
- PROJECT_STATE.md: commits 716d833c25041d4f82da16196baa8317e60522f1 y afeb9a9e84ce82685ad3cf0a08fadfd278245142.
- docs/PUNTO_CONTROL_ACTUAL.md: commit a482f1759695c1468dcac61dd102df9b50d81e82.

### Actualización de cierre del registro de continuidad

Se actualizó el estado final de los documentos PROJECT_STATE.md y docs/PUNTO_CONTROL_ACTUAL.md para indicar que el conjunto fue publicado y verificado:
- PROJECT_STATE.md: commit f2bb854e856e92f9294b2509935fad10f011a669.
- docs/PUNTO_CONTROL_ACTUAL.md: commit 53326dda7e4d32433cee4c519c668df1940e4d1e.

La verificación final de los cinco documentos se realizó después de estas actualizaciones y se registra en el resultado de cierre de la sesión.

## 2026-11-02 — Publicación y verificación del sistema de continuidad

Se crearon los cinco documentos en /opt/xray-manager y se publicaron en la rama design/user-identity-association-v1 de GitHub.

Commits de creación (en orden):
- AGENTS.md: 9eb906515a287658b9d5b2e93bfc7b20ff8ea63e
- PROJECT_STATE.md: 8faa3486ce78574504bd296127280408e277090e
- docs/CONTINUIDAD_DEL_PROYECTO.md: 689fbd55a1fa29ac45928a1dcc71b54e741ab187
- docs/PUNTO_CONTROL_ACTUAL.md: de5f9368ff5776827213e6f8f6b49c4132b6438f
- HISTORY.md: e1aa2c75716195871b5c7450ef80a7e73a4a3ea8

Verificación posterior: los cinco archivos se recuperaron desde GitHub y se compararon con la lectura SFTP de la VPS; los contenidos de texto coincidieron exactamente y sus longitudes fueron iguales. La VPS continúa sin .git; por tanto, se verificó igualdad de contenido de estos cinco archivos, no un checkout Git ni la sincronización del proyecto completo.

# Historial de hitos — Xray Core Manager

## 2026-11-03 — Cifrado AES-256-GCM del almacén de perfiles v1.1

- Durante el contraste de la primera implementación local se detectó que persistir `config.json` en texto plano contradecía Etapa 5 normativa (no guardar credenciales ni claves privadas en texto plano). Esa versión no se publicó.
- El propietario eligió explícitamente la opción 1: cifrado AES-256-GCM en reposo.
- `scripts/xray_profiles.py` ahora cifra el JSON completo de cada revisión en `config.enc.json`, con nonce aleatorio de 12 bytes y AAD que vincula versión, perfil y revisión. El manifiesto conserva tamaño del plaintext, tamaño almacenado y SHA-256 del ciphertext; el archivo persistido contiene sólo ciphertext.
- La clave se carga desde la clave maestra existente mediante `certificate_crypto.load_master_key`; no se crea, regenera, rota ni modifica. Clave ausente/incorrecta y ciphertext alterado fallan de forma cerrada. No hay fallback ni migración automática de plaintext.
- Las pruebas usan claves sintéticas temporales; no se lee ni modifica `master.key` real. Se confirmó que `/var/lib/xray-manager/profiles` no existe y no hay perfiles live que migrar.
- Se actualizó `docs/DISENO_IMPLEMENTACION_PERFILES.md` y se incorporó el estado de esta decisión en los documentos de continuidad.
- Verificación: `tests/*.sh` 51/51 PASS; Python AST 18/18; `bash -n` global PASS; ShellCheck focal PASS; shfmt de los dos archivos nuevos PASS; `git diff --check` PASS. Pruebas sintéticas únicamente.
- Commit inicial de implementación: `03b63ca109a2fabb262924daf5d2fe4a683b23d8`; commit final de sincronización byte a byte con el índice Git de la VPS: `4cec7496585390adbe72d8887cb6dacd94743c32`.
- No se modificaron `Xray-Normativa/`, `main`, runtime, systemd, firewall, puertos, certificados, red ni la conexión VLESS live.

## 2026-11-02 — Corrección de recuperación P4 y pruebas de interrupción

Se corrigió el journal de `scripts/vless_backup.py` para registrar si existían los directorios de conexiones y secretos antes de la restauración. Se añadieron `fsync` de directorios padres después de los renombrados y recuperación conservadora compatible con journals legacy sin esos campos.

Evidencia focal: 32 interrupciones abruptas simuladas cubriendo fases/renombrados y las cuatro combinaciones de existencia previa; pruebas de journal legacy/nuevo; restauración TLS/REALITY con certificado externo referenciado pero ausente. Todas PASS. Suite completa final tras la última edición: 31/31 PASS; `install.sh --check`, sintaxis Bash, `py_compile`, ShellCheck, shfmt y `git diff --check`: PASS.

Publicación confirmada en `design/user-identity-association-v1`: commit `90766d4cb8000ed1f94fb808b80f18483d5778cb`, árbol `cfdb26fd7716f622127ba5d7784884df58799b4c`. La VPS hizo fetch y quedó sincronizada con `origin`; la escritura remota se realizó mediante GitHub API porque la Deploy Key SSH es de solo lectura.

P4 continúa ABIERTA: resta auditar límites agregados de extracción/descompresión, memoria, rutas y permisos de staging/publicación, y recibir aceptación formal. No se creó backup operativo ni se accedió a la clave maestra real.


Este archivo registra hitos, decisiones y publicaciones relevantes. Es cronológico: añade entradas nuevas al principio y no borres el historial anterior. Para el estado actual consulta PROJECT_STATE.md y docs/PUNTO_CONTROL_ACTUAL.md.

## 2026-11-02 — Creación del sistema de continuidad

**Objetivo:** permitir que cualquier IA retome el proyecto desde el estado real de GitHub y de la VPS, aunque se pierda el chat.

Se estableció el conjunto de cinco documentos:
- AGENTS.md — reglas permanentes para agentes.
- PROJECT_STATE.md — fotografía consolidada del proyecto.
- docs/CONTINUIDAD_DEL_PROYECTO.md — procedimiento y prompt de recuperación.
- docs/PUNTO_CONTROL_ACTUAL.md — punto exacto de reanudación.
- HISTORY.md — historial cronológico.

La primera inspección confirmó que ninguno de esos cinco archivos existía en /opt/xray-manager ni en la rama consultada de GitHub antes de crearlos.

**Estado de destinos:** pendiente de registrar la escritura y verificación final en cada destino.

## 2026-11-02 — Auditoría y estado de Etapa 2

- Especificación normativa vigente: Etapa 2, revisión 1.3, aprobada el 30/10/2026.
- Se observó catálogo de 38 modalidades en config/protocols.tsv.
- Se observó navegación y administración inicial de conexiones en módulos de Etapa 2.
- VLESS dispone de modelo neutral de nueve modalidades y adaptador Xray-core 26.10.31.
- La prueba documentada de integración VLESS aceptó nueve fixtures con xray run -test.
- La implementación actual registra conexiones como borradores; todavía no aplica configuración al runtime ni abre puertos desde el administrador de conexiones.
- La Etapa 2 permanece abierta.

### Discrepancias identificadas

- Las tres modalidades VLESS-XHTTP están en el catálogo y en el diseño técnico, pero no aparecen explícitamente en la clasificación VLESS de la especificación normativa 1.3.
- VMess-HTTPUpgrade-TLS aparece en catálogo/código, pero no está definido expresamente como modalidad independiente en la especificación 1.3.
- Se recomendó conservar VLESS-XHTTP y dejar VMess-HTTPUpgrade-TLS pendiente de validación; queda pendiente la decisión del propietario.

## 2026-11-02 — Etapa 1 aceptada

El propietario declaró expresamente aceptada la Etapa 1 como completada.

Evidencia técnica registrada en la documentación:
- 47/47 comprobaciones normativas PASS.
- 20/20 scripts de prueba PASS.
- bash -n, ShellCheck, shfmt e ./install.sh --check PASS.
- Validación operativa en una VPS desechable Ubuntu 24.04.4 LTS.

Limitaciones documentadas que se conservan:
- La exportación remota SSH/SCP y SHA-256 se probó con mocks, no con un servidor remoto real.
- No se desinstalaron Xray ni Manager instalados en el host de pruebas.
- No se realizó un reinicio del host para validar persistencia tras reboot.

## 2026-11-02 — Último commit conocido de GitHub

- Repositorio: Jaok04/xray-core-manager.
- Rama de trabajo: design/user-identity-association-v1.
- SHA conocido: cd76e84a48974762f28b666e8d440de52062d6a8.
- Mensaje: docs: record stage two menu implementation.
- Fecha: 2026-11-02 09:55:08 UTC.

Este dato debe revalidarse contra el HEAD remoto en cada sesión.

## 2026-11-01 — Ampliación del catálogo VLESS con XHTTP

La documentación técnica registra la decisión de conservar WebSocket/gRPC e incorporar XHTTP como transporte adicional. El catálogo pasó de 35 a 38 registros; VLESS pasó de seis a nueve modalidades. No se migraron registros existentes ni se cambiaron sus identificadores.

Se documentaron pruebas de XHTTP sin TLS, TLS y REALITY con Xray-core 26.10.31. Esta ampliación técnica no actualizó por sí misma la especificación funcional normativa 1.3.

## 2026-10-30 — Aprobación de especificación funcional Etapa 2

La especificación Etapa 2 revisión 1.3 quedó registrada como APROBADA. Define la clasificación funcional de protocolos, modalidades, flujos de creación/administración y reglas de navegación. La aprobación funcional no garantiza compatibilidad técnica anticipada; cada combinación debe validarse contra la versión objetivo y los componentes externos.
## 2026-11-02 — Decisión complementaria e integración del asistente VLESS

- El propietario aprobó conservar las nueve modalidades VLESS existentes, incluidas XHTTP sin TLS/TLS/REALITY.
- VMess-HTTPUpgrade-TLS queda pendiente de validación; no se considera modalidad funcionalmente aprobada por su sola presencia en el catálogo.
- Se añadió docs/DECISIONES_ETAPA_2.md sin reescribir la especificación normativa 1.3.
- Se integró modules/vless_assistant.sh al alta de borradores VLESS y se añadió el acceso a las tres variantes XHTTP en el menú.
- El asistente construye una previsualización temporal con el modelo neutral y el adaptador v26.10.31; solicita la clave REALITY con entrada oculta y ejecuta xray run -test cuando está disponible.
- No persiste secretos/configuración ni activa runtime. Los registros permanecen draft y runtime_applied=false.
- Se añadieron docs y tests/vless_assistant.sh.
- Verificación actual: todos los tests/*.sh PASS; bash -n, ShellCheck de módulos modificados y git diff --check PASS; shfmt aplicado al nuevo módulo.
- Commit publicado: 29459ce3abd6961238182631a28738633b7cc8d0 (feat: integrate VLESS draft configuration assistant).
- Push confirmado en design/user-identity-association-v1; SHA local/remoto idénticos y árbol de trabajo limpio.


## 2026-11-02 — Diseño de persistencia segura VLESS

- Se auditó el almacenamiento actual: directorios root-only 0700, JSON 0600, bloqueo compartido y json_store_commit atómico.
- Se detectó que el asistente VLESS actual pasa la clave privada REALITY a jq mediante --arg, con posible exposición temporal en argumentos del proceso.
- Se creó docs/DISEÑO_PERSISTENCIA_SEGURA_VLESS.md con propuesta AES-256-GCM, separación de datos, clave maestra local, flujos atómicos, recuperación fail-closed, pruebas y fases P1–P4.
- Diseño pendiente de aprobación; no se modificó el código ni se generó clave maestra/secretos persistentes.

## 2026-11-02 — P1 infraestructura criptográfica VLESS

- El propietario aprobó las cinco decisiones del diseño de persistencia segura.
- Se implementó scripts/vless_crypto.py con AES-256-GCM, clave maestra local root-only, AAD por conexión/esquema, blobs versionados, escritura atómica y validación estricta de permisos.
- Se añadió tests/vless_crypto.sh y se formalizó python3-cryptography en instalador y catálogo de dependencias.
- Se añadieron rutas reservadas y directorios privados para claves/secretos; no se creó la clave maestra real ni se ejecutó apt-get.
- Verificación: 21/21 scripts de pruebas PASS; bash -n, ShellCheck, py_compile, install --check y git diff --check PASS.
- Sin cambios en conexiones reales, usuarios, firewall, servicio ni runtime. P2 pendiente.

## 2026-11-02 — P2 almacén VLESS (implementación en curso)

Se añadió `scripts/vless_config_store.py` y `tests/vless_config_store.sh`: almacenamiento versionado de configuraciones neutrales no secretas, referencias en catálogo, auditoría de referencias rotas/huérfanos y conservación de borradores. Prueba focal inicial PASS. P2 sigue en curso: faltan pruebas de fallos/interrupciones y concurrencia, suite completa y revisión final.

P2: `tests/*.sh` 25/25 PASS; pruebas específicas incluyen interrupción antes de publicar catálogo (huérfano detectable) y dos escritores concurrentes. `install.sh --check`, sintaxis, py_compile, ShellCheck, shfmt y diff PASS. El campo `secret_ref` queda reservado como null hasta P3.

### P3 — integración de persistencia segura VLESS (implementada y verificada)

Se integró guardado bajo confirmación desde el asistente, cifrado AES-256-GCM de claves privadas TLS/REALITY, referencias versionadas en catálogo/configuración y recuperación temporal para validación. Nuevo `scripts/vless_prepare_config.py`; `vless_config_store.py` ahora admite secretos cifrados y auditoría de blobs. El asistente deja de pasar la clave REALITY como `jq --arg` y usa `--rawfile`. Pruebas focales REALITY/TLS/recuperación PASS. Borradores no se activan. Suite completa `tests/*.sh` 25/25 PASS; `install.sh --check`, `bash -n`, `py_compile`, ShellCheck, shfmt y `git diff --check` PASS. Clave maestra real de VPS no generada. P3 aún no publicada en GitHub.

## 2026-11-02 — Inicio P4 backup/recuperación VLESS

- Aprobado contrato técnico P4.
- Añadido `scripts/vless_backup.py` con backup de datos separado de clave maestra, manifiesto y hashes, paquete de recuperación scrypt/AES-256-GCM, verificación y restauración con confirmación, staging y journal.
- Añadidos `modules/vless_backup.sh` e integración del menú de conexiones.
- Pruebas focales de backup/manipulación, restauración aislada y recuperación scrypt/AES-GCM con rechazo de contraseña incorrecta PASS; suite completa 29/29 PASS.
- P4 permanece abierta por resolución del journal tras interrupción abrupta y pruebas end-to-end de recuperación/restore de secretos TLS/REALITY.
- No se creó backup operativo ni se accedió a la clave maestra real.


## 2026-11-02 — Corrección de EOF en menús y recuperación de espacio en disco

- Se investigó alerta Termalin de disco al 95–99.9%; se localizó `/tmp/tmp.oaFf5wTZwt/connections-action-error.out` con 20,465,770,496 bytes y un proceso huérfano que retenía otro archivo borrado de ~925 MB.
- Se detuvo el proceso huérfano PID 36728 de forma ordenada y se eliminó únicamente el directorio temporal afectado tras verificar ausencia de handles abiertos. Resultado: 3.7 GB usados, 71 GB libres, 5% de uso. No se tocaron datos persistentes, configuraciones, claves, firewall ni runtime.
- Causa raíz: `ui_read_option()` convertía EOF en cadena vacía y éxito; los menús repetían el mensaje de opción inválida dentro de bucles infinitos.
- Se cambió el contrato del lector y se actualizaron sus consumidores para salir al recibir EOF; se protegieron también los prompts de identificador del menú de backup VLESS.
- Se añadieron pruebas de EOF directo/anidado con límite de salida de 1 MiB en `tests/stage1_menu.sh`.
- Se revisó y ejecutó PASS `tests/vless_backup_restore_secrets.sh`, que existía localmente sin seguimiento Git; se incluye en el cierre de sincronización.
- PASS: pruebas `stage1_menu`, `users_v2_menu`, `stage1_settings`, restore end-to-end de secretos TLS/REALITY, `bash -n` de scripts shell, ShellCheck de archivos modificados y `git diff --check`. Suite completa `tests/*.sh`: 30/30 PASS; `install.sh --check`, `bash -n` de todos los scripts shell, ShellCheck, shfmt del test nuevo y `git diff --check`: PASS.
- Se conservaron sin borrar los directorios `/tmp/tmp.u7Vq57eHNx` (282 MB) y `/tmp/tmp.EsxO527Ihe` (47 MB), con salidas históricas repetitivas de pruebas V2.


### Publicación GitHub — corrección EOF

- Publicación verificada en `design/user-identity-association-v1`: `fa7242a61248a71b64552511d1db932ebbc8d7d0` (`fix: handle EOF safely in interactive menus`).
- El árbol remoto `b03db9b450288eccbf61e761655f286763df3a70` coincide exactamente con el árbol del commit local `b520c53bd5a32007b30519e0756fce13fe8916b5`; 17 archivos.
- La VPS no pudo hacer push/fetch nativo por falta de autenticación SSH/HTTPS. El contenido está sincronizado; la referencia Git local `origin/...` quedó obsoleta y debe reconciliarse en una sesión con autenticación disponible, sin duplicar los cambios.

## 2026-11-02 — autenticación SSH y reconciliación de referencias

Se creó una clave SSH Ed25519 dedicada a este repositorio y se registró en GitHub como Deploy Key de solo lectura (sin permiso de escritura). La VPS autentica correctamente mediante el alias `github.com-xray-core-manager`; la URL `origin` de este checkout usa ese alias y los demás repositorios/configuraciones SSH no se modificaron. `git fetch` se completó correctamente. Se verificó que el árbol local anterior y el árbol remoto eran idénticos (`b6ed32ae1ff32dc4c8c6953a2d1eec48159b1d08`), por lo que se movió únicamente la referencia local de la rama con comprobación del SHA anterior, sin resetear ni sobrescribir archivos. Estado final: `design/user-identity-association-v1` y `origin/design/user-identity-association-v1` apuntan a `5ade7feda328ff4a4f6796fd7ab263237b40dbfa`; working tree limpio y sin divergencia. Las notas anteriores sobre falta de autenticación y refs obsoletas quedan superadas por esta verificación. La clave SSH anterior se conservó intacta. La Deploy Key nueva es de solo lectura; las publicaciones futuras deberán seguir usando el mecanismo autorizado de GitHub API u otro acceso de escritura expresamente configurado.


## 2026-11-02 — Límites agregados y cierre de TOCTOU en P4

Se añadió límite total de 512 MiB descomprimidos, aplicado durante recolección, creación, verificación y extracción. El lector común valida autónomamente rutas, tipos, enlaces, duplicados, cantidad, límites por miembro/agregados y hashes del manifiesto. La restauración realiza la verificación, lectura de clave y extracción bajo `lifecycle.lock` + `integrity.lock`; elimina el uso de contenido extraído antes de adquirir locks y vuelve a comprobar el hash de los bytes usados.

Nueva prueba `tests/vless_backup_limits.sh`: PASS. Suite completa posterior: 32/32 PASS. P4 sigue abierta hasta revisión final y aceptación formal. No se generó backup operativo ni se leyó la clave maestra real.


## 2026-11-02 — Aceptación formal y cierre de P4

El propietario aceptó formalmente las correcciones adicionales de seguridad (límite agregado de 512 MiB descomprimidos, validación autónoma de miembros y rutas, y lectura/verificación/extracción bajo locks para cerrar TOCTOU). Con la suite completa 32/32 PASS y las verificaciones estáticas satisfactorias, **P4 BACKUP/RECUPERACIÓN VLESS queda COMPLETADA Y ACEPTADA**. No se creó backup operativo ni se accedió a la clave maestra real. La activación de conexiones/runtime, reinicio de Xray, puertos, firewall y despliegue de certificados externos permanecen fuera del alcance de P4.


## 2026-11-02 — Regla permanente de contraste con documentación preliminar aprobada

Por instrucción expresa del propietario, se estableció como regla obligatoria que antes de implementar cualquier etapa, subetapa, módulo, protocolo, modalidad o funcionalidad se consulte y contraste el estado real del proyecto con la documentación preliminar aprobada conservada en `/root/Xray_Manager_Documentacion_Final_2026-10-31`. El contraste debe identificar conformidades, ausencias, divergencias y elementos no verificados, y presentarse antes de editar o implementar.

Las mejoras siguen permitidas, pero deben justificarse y presentarse al propietario; requieren autorización expresa previa antes de modificar diseño, alcance o código. Se prohíben las modificaciones silenciosas y completar vacíos mediante suposiciones. Si la referencia no está disponible o hay contradicciones relevantes, se detiene el trabajo y se solicita aclaración.

La regla quedó desarrollada en `docs/REGLA_CONTRASTE_DOCUMENTACION_PRELIMINAR.md` y referenciada en `AGENTS.md`, `PROJECT_STATE.md`, `docs/CONTINUIDAD_DEL_PROYECTO.md` y `docs/PUNTO_CONTROL_ACTUAL.md`. Aplicable a todas las etapas y a cualquier IA o colaborador que retome el proyecto.


## 2026-11-02 — Implementación VMess y aislamiento de persistencia (en curso)

- El propietario autorizó implementar el diseño VMess aprobado, incluida la modalidad HTTPUpgrade-TLS, y posteriormente autorizó separar el almacenamiento VMess para preservar P4 VLESS.
- Se añadieron modelo neutral, adaptador Xray-core 26.10.31, asistente, preparación segura, almacén versionado cifrado y pruebas VMess. La matriz de 14 combinaciones pasó `xray run -test` en esta sesión.
- Se aisló el almacenamiento en `/var/lib/xray-manager/vmess/configurations/` y `/var/lib/xray-manager/vmess/secrets/`. El catálogo utiliza `vmess_configuration_ref`, `vmess_secret_ref`, `vmess_configuration_revision` y `vmess_configuration_schema_version`; no se escriben campos de persistencia VLESS.
- Se adaptaron menú, recuperación, detalle, rutas centrales y categoría de desinstalación para el almacén VMess. Se añadió prueba `tests/vmess_vless_backup_isolation.sh`.
- PASS focales tras aislamiento: `tests/vmess_assistant.sh`, `tests/vmess_vless_backup_isolation.sh`, `tests/uninstall.sh`. La suite completa `tests/*.sh` cerró 36/36 PASS. También PASS: `bash -n`, `py_compile scripts/*.py`, ShellCheck a nivel warning de archivos afectados, shfmt de archivos VMess nuevos, `install.sh --check` y `git diff --check`.
- P4 VLESS y `scripts/vless_backup.py` permanecen sin cambios. El backup VLESS no incluye los archivos VMess; como el catálogo es compartido, restaurar una instantánea VLESS antigua puede revertir registros VMess, dejando sus archivos aislados huérfanos. Se documenta como limitación; backup/restore VMess queda pendiente de diseño.
- Usuarios VMess aún se introducen manualmente; integración con identidades globales queda para Etapa 3. No se tocó runtime, firewall, puertos ni servicio.
- Los cambios fueron publicados y sincronizados tras autorización expresa: commit `c20277c04b9417f2e22b285891fb3f348ea8e8f4` en `design/user-identity-association-v1`. La escritura remota se realizó mediante GitHub API porque la Deploy Key SSH de la VPS es de solo lectura. La VPS hizo fetch/reset y quedó con HEAD idéntico al remoto.

## 2026-11-02 — Auditoría final y endurecimiento VMess antes de Trojan

- Por instrucción del propietario se completó el trabajo necesario para cerrar técnicamente VMess antes de avanzar a Trojan.
- La auditoría contrastó la especificación normativa Etapa 2 revisión 1.3 y el diseño VMess aprobado. No se modificó la documentación normativa ni la matriz aprobada.
- Se detectó una brecha en pruebas negativas TLS: Xray-core 26.10.31 acepta el archivo de configuración con `xray run -test` aunque el certificado PEM esté malformado. El adaptador VMess ahora valida el certificado PEM y la clave privada PEM, compara sus claves públicas con `cryptography`, rechaza archivos no regulares y symlinks, y falla de forma cerrada sin imprimir material sensible. No se añadió dependencia nueva: `python3-cryptography` ya es requisito del proyecto.
- `tests/xray_vmess_integration.sh` ahora cubre 14/14 combinaciones positivas y rechazos de TLS ausente, symlink, PEM inválido, par certificado/clave no coincidente, REALITY incompleto, short ID y clave inválidos, campos incompatibles y combinación modelo/seguridad incorrecta.
- `tests/stage2_navigation.sh` recorre individualmente las 14 combinaciones VMess y las selecciones de seguridad de gRPC, HTTPUpgrade, XHTTP y mKCP.
- PASS: suite completa `tests/*.sh` 36/36 scripts; `bash -n`; `python3 -m py_compile scripts/*.py`; `./install.sh --check`; ShellCheck (`-S warning`); shfmt; `git diff --check`.
- Xray-core verificado: v26.10.31, build `a4a3dff`. Las 14 combinaciones pasan `xray run -test`; esto no equivale a conectividad extremo a extremo.
- No se modificaron P4 VLESS ni `scripts/vless_backup.py`; tampoco runtime, servicio, firewall, puertos ni certificados desplegados. Las pruebas usan temporales.
- VMess queda IMPLEMENTADO y VERIFICADO. La aceptación formal del propietario sigue pendiente. Backup/restore VMess continúa como diseño separado; identidad global continúa en Etapa 3.
- Se actualizaron `docs/DISEÑO_TECNICO_VMESS.md`, `PROJECT_STATE.md`, `docs/PUNTO_CONTROL_ACTUAL.md` y este documento de continuidad.
- Publicación confirmada únicamente en `design/user-identity-association-v1`: commit funcional `ab76a57032faa9793a62348f865fba2c9a7d8f77`; se publicó después la actualización documental. La VPS hizo push/fetch y HEAD local/remoto se verificaron coincidentes. `main` permanece intacta.

## 2026-11-02 — Regla permanente de auditoría integral y cierre de etapas

Por instrucción expresa del propietario se establece una segunda regla obligatoria de gobernanza, acumulativa a la regla de contraste previo con la documentación preliminar aprobada:

- Ninguna etapa puede declararse TERMINADA/COMPLETADA sin auditoría integral de todos sus puntos, subpuntos, módulos, submódulos y componentes internos.
- Se exige inventario exhaustivo, matriz de trazabilidad requisito → diseño → implementación → pruebas → evidencia, auditoría individual de cada elemento y documentación técnica suficiente de cada módulo/componente.
- La auditoría debe cubrir, según aplique, comportamiento, diseño, implementación, datos/persistencia, seguridad, errores/recuperación, integración, pruebas, documentación y evidencia.
- Elementos ausentes, incompletos, divergentes, no verificados o sin documentación bloquean el cierre, salvo excepción específica autorizada y documentada por el propietario.
- Cerrar un módulo individual, pasar una suite, publicar o sincronizar no equivale a cerrar la etapa.
- Se requiere informe final, regresión integral y aceptación formal expresa del propietario.
- La regla aplica a todas las etapas y a cualquier IA/desarrollador que retome el proyecto. Los documentos normativos preliminares siguen siendo la línea base y la regla de contraste previo continúa siendo obligatoria.
- Se creó `docs/REGLA_AUDITORIA_INTEGRAL_CIERRE_ETAPAS.md` y se integró la obligación en `AGENTS.md`, `docs/CONTINUIDAD_DEL_PROYECTO.md`, `PROJECT_STATE.md`, `docs/PUNTO_CONTROL_ACTUAL.md` y `docs/REGLA_CONTRASTE_DOCUMENTACION_PRELIMINAR.md`.
- La Etapa 2 permanece ABIERTA; el cierre técnico individual de VMess no constituye cierre de la etapa.


## 2026-11-02 — Bloque 1: protección de VMess durante restauración VLESS

- El propietario aprobó el plan completo de correcciones de cierre VMess y autorizó iniciar el Bloque 1. Se contrastaron las reglas de gobernanza, el diseño normativo Etapa 2 y `docs/P4_BACKUP_RECUPERACION_VLESS.md` antes de modificar código.
- Se corrigió `scripts/vless_backup.py`: restore VLESS combina las conexiones VLESS del backup con las entradas VMess actuales del catálogo compartido. Las entradas VMess antiguas de la instantánea no reemplazan las vigentes. Se validan IDs, modalidades, referencias y archivos VMess; las colisiones, datos corruptos, referencias rotas y fallos staging se rechazan antes de publicar.
- El almacén VMess separado no se copia ni modifica; el backup VLESS continúa sin contener configuraciones ni secretos VMess.
- Nuevo `tests/vless_restore_preserves_vmess.sh`: VMess pre/post backup, refs de configuración/secreto, integridad del almacén, colisión IDs, catálogo corrupto, refs rotas y fallo de escritura sin cambio activo. Se actualizó el fixture de `tests/vless_backup_journal_crash_matrix.sh` para usar catálogo VMess válido; 32 interrupciones siguen PASS.
- Verificación: suite `tests/*.sh` 37/37 PASS; `python3 -m py_compile scripts/*.py`; `bash -n` de todos los scripts Bash; `install.sh --check`; ShellCheck warning de pruebas modificadas; `git diff --check`: PASS.
- Estado: IMPLEMENTADO, VERIFICADO, PUBLICADO y SINCRONIZADO; commit `c890b5b5362e17e439f198b9b8bbbdbe0af0c653`. La aceptación formal específica permanece pendiente. P4 mantiene la aceptación histórica de su alcance original. No se generó backup operativo ni se accedió a la clave maestra real. Sin cambios de runtime, servicio, firewall, puertos, certificados desplegados ni documentación normativa preliminar.
- Próximo paso del plan aprobado: Bloque 2 del asistente VMess.

- Verificación de publicación: HEAD local y `origin/design/user-identity-association-v1` coinciden en `c890b5b5362e17e439f198b9b8bbbdbe0af0c653`; árboles idénticos. `main` remoto (`656ecedc506a94a6461aee296b20871d51a38bf3`) no fue modificado.


## 2026-11-02 — Bloque 2: advertencias y resumen del asistente VMess

- Se añadió el aviso operativo de sincronización horaria VMess (máximo 120 segundos) y las advertencias específicas de WebSocket y HTTPUpgrade, conservando las modalidades aprobadas.
- Se incorporó un resumen completo posterior a `xray run -test` y anterior al consentimiento: identidad, dirección/puerto, modalidad, transporte/seguridad, usuarios y parámetros aplicables. El contenido de claves privadas TLS/REALITY no se muestra.
- Se corrigió una colisión de variable local en funciones de lectura que impedía asignar el target REALITY al llamador.
- `tests/vmess_assistant.sh` valida avisos, resumen, orden resumen→consentimiento y ocultamiento de secretos. Pruebas focales VMess assistant/model/integration/navigation: PASS; Xray-core 26.10.31 validó 14/14 modalidades y negativos previstos. `bash -n` y ShellCheck warning: PASS.
- Estado: IMPLEMENTADO, VERIFICADO, PUBLICADO y SINCRONIZADO en `9d03d4b4e77e1a160b94ee2c2f3c74487977e362`. La suite completa posterior se ejecutará en Bloque 3; VMess sigue pendiente de aceptación formal.

- Publicación verificada: HEAD local/remoto y árboles idénticos en `9d03d4b4e77e1a160b94ee2c2f3c74487977e362`; sólo rama `design/user-identity-association-v1`.


## 2026-11-02 — Bloque 3: cobertura de pruebas VMess

- `tests/vmess_assistant.sh` ahora prueba EOF/cancelación en varios puntos, slots inválidos, UUID inválido/duplicado, puerto inválido, modalidad incompatible y EOF al confirmar; comprueba que el catálogo no cambia en flujos fallidos/cancelados.
- Nuevo `tests/vmess_persistence_hardening.sh`: clave maestra ausente/inválida, AES-256-GCM/ciphertext alterado, refs rotas, huérfanos, symlinks, permisos, fallo de publicación del catálogo y concurrencia sobre IDs distintos y misma conexión/revisiones.
- El fallo inyectado entre escritura de configuración/secreto y publicación del catálogo deja huérfanos detectables, sin cambiar referencias; `audit` no borra automáticamente. Esto respeta la decisión de no ofrecer rollback transaccional VMess.
- Suite completa: 38/38 scripts PASS. `py_compile`, `bash -n` de todos los scripts, `install.sh --check`, ShellCheck warning de archivos modificados y `git diff --check`: PASS.
- No se modificó código de producción en este bloque. Estado: IMPLEMENTADO, VERIFICADO, PUBLICADO y SINCRONIZADO en `08b2044dd820eb465afecbb6ec66fccefe6397a5`. VMess sigue pendiente de aceptación formal.

- Publicación confirmada: HEAD local/remoto y árboles idénticos en `08b2044dd820eb465afecbb6ec66fccefe6397a5`; rama `main` no modificada.


## 2026-11-02 — Bloque 4: etiquetas VMess

- Menú y etiquetas de listado ahora muestran `VMess-WS (sin TLS adicional)` y `VMess-TLS (RAW/TCP + TLS)`.
- IDs `vmess_ws` y `vmess_tcp_tls`, las 14 modalidades y la navegación se conservan.
- `tests/stage2_navigation.sh` incorpora aserciones de las dos etiquetas.
- Criterio shfmt contrastado con README: `-i 4 -ci` en archivos seleccionados; no se aplicó reformateo global.
- Pruebas focales y suite completa 38/38 PASS; controles estáticos y shfmt baseline PASS. Auditoría integral pendiente; cambios publicados y sincronizados en `9528f4b00f6b9654f7236050bbadfd8f9415bf69`.

- Publicación Bloque 4 confirmada: `9528f4b00f6b9654f7236050bbadfd8f9415bf69`; HEAD local/remoto y árboles idénticos. Rama `main` intacta.


## 2026-11-02 — Auditoría integral VMess: hallazgos y trazabilidad

- Se consultó directamente la línea base normativa Etapa 2 revisión 1.3 (Markdown/YAML), el informe de auditoría técnica, AGENTS y las reglas permanentes de contraste/cierre. Se limitó el alcance a VMess y sus integraciones directas; Etapa 2 completa sigue abierta.
- Se reejecutó la suite completa: 38/38 PASS; Xray 26.10.31 aceptó 14/14 combinaciones y rechazó 10 casos negativos. Sintaxis Bash, AST Python (7 archivos), ShellCheck, install.sh --check, git diff --check y gate shfmt del README PASS.
- Hallazgos: F-01 clave TLS root-owned 0644 aceptada; F-02 read/audit aceptan metadatos de revisión/schema incoherentes; F-03 el flujo común deja un registro draft vacío al cancelar el asistente; F-04 modelo acepta email duplicado mientras store lo rechaza; F-05 estado live no verificado porque catálogo está vacío y almacén/clave maestra VMess no existen.
- Nuevos documentos: docs/AUDITORIA_INTEGRAL_VMESS_2026-11-02.md y docs/MATRIZ_TRAZABILIDAD_VMESS_2026-11-02.md. No se modificó código de producción ni la documentación normativa. No se creó almacén/clave real ni se tocó runtime, firewall, puertos o servicio.
- Estado: VMess IMPLEMENTADO en su base funcional, VERIFICADO PARCIALMENTE, DOCUMENTADO; aceptación pendiente y bloqueada por hallazgos. Etapa 2 ABIERTA. Se requiere autorización para corregir F-01/F-02/F-04 y decisión expresa sobre F-03.

- Publicación documental de auditoría y matriz: commit 88f82f2f9d7d19833b814d9a810dedb4bc3edc8c en design/user-identity-association-v1; push confirmado. main sin cambios.

- Actualización de referencias del punto de control/estado para registrar la publicación del expediente: commit 81f485ffb77d84afb0a46ccb3ed46fe29814a83d; rama autorizada sincronizada, main intacta.


## 2026-11-02 — Bloque correctivo autorizado VMess F-01 a F-04

- Contraste previo repetido con reglas de gobernanza, Etapa 2 revisión 1.3 Markdown/YAML y diseño VMess; se implementó únicamente el alcance aprobado por el propietario.
- F-01: adaptador y preparador exigen TLS key root:root, modo 0600, un solo hardlink; negativos de permisos/grupo/hardlink.
- F-02: store/read/audit comprueban revisión de catálogo y referencia, schema catálogo/documento y revisión de secreto; detectan metadatos parciales y bloquean store sobre metadatos incoherentes.
- F-03: cancelación devuelve estado no exitoso; flujo común retira bajo bloqueo sólo el draft VMess vacío/no aplicado. Tests prueban cancelación, error, preservación de otras entradas y de drafts ya configurados.
- F-04: modelo, adaptador y almacén validan unicidad exacta de email; pruebas negativas antes de consentimiento y en adaptador.
- Nueva prueba tests/vmess_creation_flow.sh; pruebas ampliadas de modelo, asistente, persistencia e integración Xray. Suite completa 39/39 PASS; Xray 14/14 y 16 negativos PASS; sintaxis, py_compile, ShellCheck de modificados, install check, shfmt README y diff check PASS. ShellCheck global mantiene warning preexistente SC2174 en prueba VLESS sin modificar.
- F-01–F-04 RESUELTOS/VERIFICADOS EN FIXTURES. F-05 live no verificado; VM-38 test específico pendiente y VM-39/40 cobertura parcial. No se creó almacén/clave real, no se tocó runtime/firewall/puertos/servicio, main intacta. VMess no aceptado; Etapa 2 abierta.

- Publicación y sincronización del bloque correctivo y su expediente: commit d2d33a32bdf5e21d1d35ad41d00bd0b116443cb7 en design/user-identity-association-v1; HEAD local/remoto coincidente, main intacta.

- Referencias finales del HEAD y la sincronización documental actualizadas en commit 0a39af5c2aa35bf853c05f3a864bcc362d86bf67; rama autorizada y VPS coincidentes, main intacta.


## 2026-11-02 — Revalidación controlada en VPS de desarrollo

- Se confirmó acceso root a la VPS de desarrollo `/opt/xray-manager`, rama `design/user-identity-association-v1`, HEAD `4c87557e0aff4166c540c633effe5cb6dac40096`; árbol versionado limpio.
- Se creó `tests/vmess_navigation_edge_cases.sh`: VM-38 lista vacía y `[0]`; VM-39 entradas inválidas recuperables en lista/administrador; VM-40 cancelación y confirmación destructiva exacta. Todos PASS.
- Suite completa `tests/*.sh`: 40/40 PASS. Xray 26.10.31 validó 14/14 modalidades y 16 casos negativos PASS. Sintaxis Bash, py_compile, install check y diff check PASS.
- `tests/port_collisions.sh` falló en una primera ejecución parcial en el caso UDP; la repetición aislada y la suite completa posterior pasaron. Se registra el evento sin ocultarlo.
- No se creó clave maestra ni almacén VMess live; no se añadió conexión live. Xray no está instalado en la VPS de desarrollo, el test de integración utilizó el binario de validación en caché. Servicio inactivo; no se tocó runtime, firewall, puertos ni servicios. F-05 y conectividad cliente-servidor siguen NO VERIFICADOS; VMess no aceptado; Etapa 2 abierta.
- Nuevo test pendiente de publicar y sincronizar: `tests/vmess_navigation_edge_cases.sh`. `scripts/__pycache__/` permanece sin seguimiento y no se elimina.


## 2026-11-02 — F-05 validación live VMess

- El propietario autorizó inicializar clave maestra y almacén VMess reales en la VPS de desarrollo para una prueba temporal controlada.
- Preflight: catálogo compartido vacío, sin entradas/datos VLESS persistidos, sin clave maestra ni almacén VMess previos; servicio Xray inactivo. La clave maestra es compartida por VLESS/VMess.
- Se creó por el flujo real un borrador VMess-TLS, se validó con Xray 26.10.31, se almacenó con secreto AES-256-GCM, se recuperó byte a byte y se reconstruyó/validó mediante el asistente. Permisos: clave `root:root 0600`, directorios VMess `root:root 0700`.
- Auditoría live: cero referencias rotas, huérfanos o entradas inseguras. Ciphertext alterado rechazado sin producir plaintext.
- Se retiró la conexión temporal y sus dos archivos versionados; catálogo vacío y auditoría posterior limpia. Se conservaron clave maestra compartida y directorios VMess vacíos como inicialización persistente intencional. Se eliminaron certificados/clave TLS y outputs temporales.
- Xray permaneció inactivo; puerto de prueba sin escucha; sin cambios de runtime, firewall, puertos, servicios o certificados desplegados. F-05/VM-46 VERIFICADO LIVE. VM-47 conectividad cliente-servidor sigue NO VERIFICADA. VMess no aceptado formalmente; Etapa 2 abierta.
- Informe: `docs/VALIDACION_LIVE_VMESS_F05_2026-11-02.md`.


## 2026-11-02 — VM-47 conectividad cliente-servidor VMess

- Se contrastó el requisito de `docs/DISEÑO_TECNICO_VMESS.md` §8: `xray run -test` no demuestra conectividad extremo a extremo y la prueba cliente-servidor debe registrarse por separado.
- En VPS de desarrollo se generó la configuración del servidor mediante `vmess_model_build` y `vmess_xray_26_10_31_build`, modalidad `vmess_tcp_tls`, con `settings.users` del adaptador. Dos procesos Xray 26.10.31 establecieron túnel TLS/VMess sobre loopback.
- El cliente SOCKS envió una solicitud HTTP al servidor; el servidor la recibió por VMess, abrió conexión al servicio local y éste respondió HTTP 200 con `VMESS-VM47-END-TO-END-OK`. Cliente y servidor pasaron `xray run -test`.
- Se fijó la huella SHA-256 del certificado TLS efímero; no se usó `allowInsecure`. Se añadió sólo al JSON temporal una regla `freedom.finalRules` TCP/127.0.0.1/18080 para permitir el destino local.
- Procesos y listeners temporales detenidos. Sin cambios en runtime, firewall, puertos públicos, catálogo o servicio Xray. Cliente externo/WAN no probado. Xray 26.10.31 emitió advertencia de deprecación de VMess; se documenta como advertencia del core, no como fallo de la prueba.
- VM-47: VERIFICADO — loopback local. VMess sigue pendiente de aceptación formal; Etapa 2 permanece ABIERTA. Informe: `docs/VALIDACION_CLIENTE_SERVIDOR_VMESS_VM47_2026-11-02.md`.


## 2026-11-03 — Revalidación final y preparación de aceptación VMess

- El propietario autorizó completar la limpieza de advertencias, reconciliación de trazabilidad y actualización de continuidad para preparar la aprobación formal de VMess, sin modificar código de producción ni `Xray-Normativa/`.
- Se documentaron con supresión local SC2034 tres variables globales intencionales de `tests/vmess_creation_flow.sh` y `tests/vmess_navigation_edge_cases.sh`, consumidas dinámicamente por funciones de `modules/connections.sh`; se conservaron las asignaciones y el comportamiento de las pruebas.
- Revalidación ejecutada en `/opt/xray-manager`: suite completa 40/40 PASS; Xray-core 26.10.31 14/14 combinaciones VMess y 16/16 negativos PASS; sintaxis Bash VMess, compilación Python VMess, ShellCheck de módulos/pruebas VMess y `git diff --check`: PASS.
- Se actualizó la clasificación de VM-28 a VERIFICADO con evidencia de versionado, referencias separadas, coherencia y concurrencia r1/r2. VM-32 se precisa como atomicidad individual/concurrencia con límite multiarchivo documentado. VM-33 no aplica como requisito porque el diseño VMess §8 no promete rollback transaccional.
- Se actualizaron matriz, auditoría integral, punto de control, continuidad e `PROJECT_STATE.md`. VM-46 live y VM-47 loopback permanecen verificados; no se afirma prueba WAN. VM-42 está fuera del alcance y VM-43 pertenece a Etapa 3.
- `Xray-Normativa/` se comparó con el respaldo original: 14/14 archivos originales coincidentes; sin cambios normativos. No se modificó código de producción ni runtime, firewall, puertos, certificados desplegados o servicio.
- Estado: VMess IMPLEMENTADO, VERIFICADO y DOCUMENTADO; técnicamente preparado para aceptación formal, pero VM-48 PENDIENTE DE DECISIÓN. Etapa 2 ABIERTA. No iniciar Trojan antes de la aceptación formal y del contraste normativo específico.
- Publicación del bloque técnico/documental confirmada en `ef0fbad9de276b4fe15d79831b7b0dc8bbc0f4be` (`docs(vmess): prepare module for formal acceptance`); GitHub y VPS quedaron en el mismo SHA de la rama autorizada. Este registro cronológico se incorpora en un commit documental posterior. `main` no se modificó.


## 2026-11-03 — Inicio del diseño de certificados TLS centralizados

- El propietario aprobó iniciar los cambios de código y documentación no normativa para implementar el modelo centralizado de certificados TLS. La aprobación arquitectónica previa define catálogo independiente, recursos `managed`/`reference`, una única clave privada cifrada central por certificado, referencias `certificate_id` desde VMess/VLESS y resolución controlada. REALITY permanece separado.
- Se creó `docs/ARQUITECTURA_CERTIFICADOS_CENTRALIZADOS.md` v1.0 como contrato técnico inicial. Documenta semántica de recursos, contrato de conexión, seguridad, resolutor, migración, backup/restore, pruebas, etapas y decisiones técnicas pendientes.
- Se actualizaron `PROJECT_STATE.md`, `docs/PUNTO_CONTROL_ACTUAL.md` y `docs/CONTINUIDAD_DEL_PROYECTO.md` para identificar el nuevo frente activo y el punto exacto de reanudación.
- Esta entrega sólo modifica documentación técnica/no normativa. No se modificó código de producción, `Xray-Normativa/`, catálogo/secretos live, configuración runtime, servicio, firewall, puertos ni certificados desplegados. La VPS `Vps de Pruebas` no fue utilizada.
- La decisión arquitectónica está APROBADA y el contrato inicial DOCUMENTADO. El contrato requiere revisión técnica; §14 enumera decisiones pendientes antes de implementar el almacén central. No se declaran funcionalidades IMPLEMENTADAS ni VERIFICADAS por esta entrega.
- Rama de trabajo: `design/user-identity-association-v1`; HEAD de partida local/remoto verificado: `ee694da113ebd0ab3f33285a2e0480c5efc10b52`. Contrato publicado en `e88f0c3`; actualización de continuidad publicada en `f97de26`. La verificación remota final se registra tras el push.


## 2026-11-03 — Bloque inicial del almacén central de certificados TLS

- Se implementó scripts/certificate_crypto.py: AES-256-GCM, nonce aleatorio de 12 bytes, envelope versionado y AAD ligado a certificate_id y revisión. Lee la clave maestra existente /etc/xray-manager/keys/master.key; no la crea, regenera ni modifica.
- Se implementó scripts/certificate_store.py: importación managed/reference, catálogo separado, deduplicación por huella, validación PEM y correspondencia certificado/clave, verificación de vigencia, list, show y audit. No existe aún operación de resolución ni entrega de plaintext al servicio.
- Se añadieron rutas de catálogo, managed, references (reservado), secretos y bloqueo a config/paths.sh; nueva prueba tests/certificate_store.sh.
- Importación exige clave privada fuente root:root 0600 y rechaza symlinks/hardlinks; los secretos se cifran centralmente. managed copia el certificado público; reference conserva su ruta externa. La auditoría detecta referencias corruptas, blobs alterados, huérfanos y entradas inseguras; no borra automáticamente.
- Pruebas ejecutadas en fixtures temporales: managed/reference, duplicados, mismatch de clave, symlink, alteración ciphertext/tag y ausencia de clave maestra. Focal PASS. Suite completa posterior: 41/41 PASS. bash -n, py_compile, ShellCheck de la prueba nueva y git diff --check: PASS.
- No se importaron certificados al almacén real ni se tocaron asistentes/generadores/stores VMess/VLESS históricos, migración, backup/restore, runtime, servicio, firewall, puertos o certificados desplegados. La VPS Vps de Pruebas no fue utilizada. Xray-Normativa no fue modificada.
- La VPS de desarrollo no tiene Xray instalado ni unidad/cuenta/grupo xray; permisos de resolución y runtime siguen pendientes. La etapa de catálogo/almacén queda IMPLEMENTADA PARCIALMENTE y VERIFICADA en pruebas; aceptación global pendiente.
- Documentación: docs/IMPLEMENTACION_ALMACEN_CERTIFICADOS_CENTRALIZADOS.md; contrato y continuidad actualizados.
- Commit de implementación: c720fbf4d65f61e5b7d3dc8a9cb5c69639eb628f; commit de registro: 6d35b0dde502db66d9826bc4fb67e8500b6b4561. Push completado; HEAD local, origin y GitHub coinciden en 6d35b0dde502db66d9826bc4fb67e8500b6b4561.

- Verificación posterior: main remoto se mantiene en 656ecedc506a94a6461aee296b20871d51a38bf3; diff de Xray-Normativa vacío. Los SHA-256 de Etapa 4 Markdown/YAML coinciden con la línea base registrada antes de editar. El checkout versionado coincide con origin; scripts/__pycache__/ permanece untracked y no se borró.


## 2026-11-03 — Segundo bloque: resolutor TLS centralizado parcial

- Se añadió scripts/certificate_resolver.py. Comprueba conexión y protocolo VMess/VLESS, referencia/revisión de configuración, modalidad TLS y asociación exacta certificate_id. Rechaza protocolos no admitidos, IDs ajenos, campos de seguridad adicionales y configuraciones inconsistentes.
- Comprueba certificado central activo, referencia managed/reference, blob autenticado AES-256-GCM, par certificado/clave, huellas y período de validez.
- Prepara leases aleatorios en /run/xray-manager-certificates con directorios root:<grupo-servicio> 0750 y archivos 0640; manifest contiene metadatos no secretos. Cleanup valida ID, manifest, tipo, propietario, grupo, modos y hardlinks; sólo borra el lease indicado.
- La CLI consulta identidad efectiva con systemctl show, requiere User/Group explícitos y no admite grupos suplementarios ni identidad privilegiada. En VPS desarrollo no existe xray.service/cuenta/grupo xray; CLI fail-closed sin crear lease. Prueba de API con UID/GID sintético 1 sólo valida permisos POSIX, no acceso por Xray real.
- Se añadió tests/certificate_resolver.sh con managed/reference y ambos protocolos, asociación autorizada/no autorizada, permisos, cleanup y negativos.
- Regresión completa: 42/42 scripts PASS. bash -n, py_compile, ShellCheck de ambas pruebas y git diff --check PASS.
- Los stores VMess/VLESS y sus asistentes/generadores aún no admiten el contrato certificate_id; la integración está pendiente. No se cambió runtime, servicio, VPS Vps de Pruebas, firewall, puertos, certificados desplegados, secretos históricos, REALITY ni Xray-Normativa.
- Documentación: docs/IMPLEMENTACION_RESOLUTOR_CERTIFICADOS_TLS.md; arquitectura, estado y continuidad actualizados.


## 2026-11-03 — Bloque 3 VMess TLS centralizado: persistencia parcial

- Se actualizó `scripts/vmess_config_store.py`: nuevas revisiones TLS VMess requieren `certificate_id` válido y activo en el catálogo central; se rechazan rutas TLS libres y secretos TLS por conexión. Lectura/auditoría validan la referencia central. REALITY mantiene su secreto individual cifrado.
- Compatibilidad histórica: el store puede leer/validar TLS legacy `{certificate_file, secret_ref}` como revisión previa, sin migrar ni borrar archivos. Nuevas revisiones deben usar `certificate_id`.
- `scripts/vmess_prepare_config.py` emite el contrato TLS central sin extraer clave privada por conexión. `scripts/vless_backup.py` conserva validación de configuraciones VMess TLS históricas durante restauración VLESS.
- Adaptación preliminar de `modules/vmess_assistant.sh` para solicitar `certificate_id` y pedir un lease al resolutor; el flujo interactivo no tiene cobertura integral y permanece incompleto.
- Pruebas focales PASS: `vmess_persistence_hardening.sh`, `vless_restore_preserves_vmess.sh`, `certificate_store.sh`, `certificate_resolver.sh`, `vmess_model.sh`, `vmess_creation_flow.sh`, `vmess_vless_backup_isolation.sh` y prueba existente `vmess_assistant.sh`. Sintaxis Bash, py_compile y `git diff --check`: PASS. La suite completa no se reejecutó después de estos cambios.
- Pendiente: adaptación segura de `modules/vmess_xray_26_10_31.sh`, cobertura integral del asistente/lease/cleanup/restore, revisión completa de backup/restore y regresión global. La VPS de desarrollo carece de Xray service/user/group; no hay prueba de lectura real de lease por Xray.
- No se modificó runtime, servicio, firewall, puertos, certificados desplegados, VPS de pruebas ni `Xray-Normativa/`. No se migraron secretos históricos ni se importaron certificados reales.
- Informe: `docs/IMPLEMENTACION_VMESS_TLS_CENTRALIZADO_PARCIAL.md`. Estado: IMPLEMENTADO PARCIALMENTE / PRUEBAS FOCALES PASS / ACEPTACIÓN PENDIENTE.


## 2026-11-03 — VMess TLS centralizado: adaptación por lease y recuperación

Se endureció `modules/vmess_xray_26_10_31.sh`: el adaptador ahora exige un lease `resolve-*` para TLS y comprueba que el manifiesto, conexión, protocolo, certificado, revisión, huella, UID/GID y permisos correspondan al material temporal del resolutor. Se añadió `scripts/vmess_tls_lease_check.py`; el adaptador rechaza rutas externas, leases de otra conexión y manifests alterados. La clave privada temporal conserva `root:<grupo-servicio> 0640`, que permite lectura al servicio Xray sin relajar el almacén central.

Se completó la recuperación TLS central del asistente con `--runtime-root` explícito, lectura del catálogo central, uso del lease y limpieza en éxito/fallo. El restore de revisiones TLS históricas falla cerrado hasta migración controlada; no se modifica ni elimina el histórico. Se amplió el restore VLESS para validar que los `certificate_id` TLS centrales VMess preservados existan y estén activos en el catálogo central, sin incluir ni modificar el almacén VMess.

Pruebas: suite completa 43/43 PASS; Xray-core 26.10.31 14/14 modalidades con fixtures de lease; test de recuperación/cleanup del asistente con resolutor y Xray simulados; restauración VLESS con certificado central activo/ausente; ShellCheck warning, `bash -n`, `py_compile` y `git diff --check` PASS.

No se probó lectura de lease por un servicio Xray real: la VPS de desarrollo carece de `xray.service` y usuario/grupo Xray. No se tocó runtime, servicio, firewall, puertos, VPS de pruebas, certificados reales ni `Xray-Normativa/`. Esta actualización permanece local, sin commit/push; `main` intacta. Bloque 3 continúa parcial y Etapa 2 abierta.


## 2026-11-03 — Integración VLESS TLS centralizado parcial

- Nuevas revisiones TLS VLESS guardan sólo `certificate_id`; el store valida certificado central activo `managed`/`reference` y rechaza secreto/ruta TLS por conexión. Lectura/auditoría conservan compatibilidad histórica sin migración automática. REALITY permanece separado.
- `vless_prepare_config.py`, `vless_xray_26_10_31.sh` y `vless_assistant.sh` integrados parcialmente con el resolutor y leases. El adaptador rechaza rutas libres y valida manifest, conexión, protocolo, certificado, revisión, fingerprint, UID/GID y permisos. Cleanup en éxito/fallo.
- `vless_backup.py` registra `certificate_id` como dependencia externa y valida catálogo/recurso activo antes de restaurar; no empaqueta el almacén central.
- Nuevas pruebas `tests/vless_tls_central_backup.sh` y `tests/vless_tls_lease_assistant.sh`; pruebas de store/asistente/Xray ampliadas. Suite global: 45/45 PASS; Xray 26.10.31 9/9 modalidades VLESS. La prueba de lease usa `systemctl`/Xray simulados y verifica permisos de lectura con UID/GID `www-data` y cleanup en éxito/fallo; no es una prueba con Xray real. Bash syntax, py_compile, install check, ShellCheck warning de modificados y diff check PASS.
- Limitación: VPS desarrollo sin unidad Xray con identidad explícita no privilegiada; resolutor CLI falla cerrado y no se probó lectura por Xray real. No runtime apply ni despliegue.
- Estado: IMPLEMENTADO PARCIALMENTE / VERIFICADO EN FIXTURES / NO PUBLICADO / NO SINCRONIZADO / NO ACEPTADO. Sin cambios a `Xray-Normativa/`, `main`, servicios, firewall, puertos, certificados desplegados o VPS de pruebas. Ver `docs/IMPLEMENTACION_VLESS_TLS_CENTRALIZADO_PARCIAL.md`.


## 2026-11-03 — Matriz de recuperación VLESS y diseños de continuidad

- Corregido adaptador VLESS-WS-TLS para aceptar `path` más certificado/clave del lease; el contrato RAW/TCP sigue sin opciones de transporte adicionales.
- Prueba integrada del asistente amplía recuperación a RAW/TCP, WS, gRPC y XHTTP y verifica cleanup en éxito/fallo mediante `systemctl`/Xray simulados y usuario `www-data`. No es prueba con Xray real. Suite completa: 45/45 PASS.
- Auditoría cruzada: validadores de lease VMess/VLESS equivalentes salvo el protocolo; asistentes VMess ahora pasan explícitamente todos los paths del almacén central al resolutor.
- Nuevos documentos de propuesta: `docs/PLAN_MIGRACION_TLS_HISTORICO.md` y `docs/PLAN_BACKUP_RESTORE_CENTRAL.md`. No se implementaron migración ni backup compartido.
- Sin cambios a datos históricos, runtime, servicios, firewall, puertos, certificados desplegados, VPS de pruebas o `Xray-Normativa/`; sin commit/push.


## 2026-11-03 — Aprobación de migración histórica y backup compartido; preflight

- El propietario aprobó criterios para migración TLS histórica VMess+VLESS y backup/restore compartido: `managed` por defecto, bloquear certificados vencidos/no vigentes, conservar históricos, reenvolver secretos bajo cifrado del backup y master key destino, excluir master key, bloquear restore completo si faltan references y no sobrescribir datos posteriores/conflictos.
- Nuevo `scripts/certificate_migration.py` con `plan --protocol all|vless|vmess`, read-only. Verifica contrato/revisiones, permisos, descifra con backends específicos, valida par PEM/vigencia/fingerprints y deduplica entre protocolos. No importa ni escribe.
- Nuevo `tests/certificate_migration_plan.sh`: VLESS+VMess, envelopes distintos, deduplicación, no escritura y ciphertext alterado bloqueado.
- Regresión completa: 46/46 pruebas PASS; Bash syntax, py_compile, ShellCheck y diff-check PASS.
- Inventario real VPS implementación: 0 registros en catálogo, 0 candidatos TLS; no se migró nada.
- Auditoría de `vless_backup.py`: backup tar actual no cifra el archivo completo; secretos cifrados bajo master key y recuperación de master key cifrada por separado. Plan compartido v1.1 define contenedor cifrado integral nuevo.
- Documentos: `docs/PLAN_MIGRACION_TLS_HISTORICO.md` v1.1, `docs/PLAN_BACKUP_RESTORE_CENTRAL.md` v1.1, `docs/IMPLEMENTACION_PREFLIGHT_MIGRACION_TLS.md`.
- Sin runtime, servicio, firewall, puertos, certificados desplegados, VPS pruebas ni cambios a `Xray-Normativa/`. Pendiente backup compartido y migración escritora. Cambios aún locales, no commit/push.

**Publicación:** commit `631d7eda11615b692557a2e0958a8f318b81c223` sincronizado con GitHub en `design/user-identity-association-v1`. `main` permanece en `656ecedc506a94a6461aee296b20871d51a38bf3`; `Xray-Normativa/` sin cambios.


## 2026-11-03 — Contenedor cifrado compartido v1

- Contraste normativo de Etapa 5: secretos/credenciales y claves privadas excluidos por defecto; inclusión requiere selección expresa, autorización y confirmación adicional. Historiales de versiones/modificaciones, validaciones, informes y logs excluidos. La futura orquestación debe aplicar estas reglas.
- Nuevo `scripts/shared_backup_format.py`: contenedor binario neutral para bytes opacos, magic `XRMGSBKP`, cabecera JSON canónica, scrypt fijo `N=2^15/r=8/p=1` (64 MiB maxmem), AES-256-GCM, salt 16 bytes, nonce 12 bytes, tag 16 bytes y AAD que autentica cabecera completa. Límites de payload/cabecera/paquete y rechazo fail-closed de parámetros KDF no admitidos, truncamiento, bytes sobrantes, contraseña errónea y manipulación.
- Passphrase UTF-8: mínimo 12 caracteres/16 bytes, máximo 1024 bytes. No se persiste, no se acepta por argumento ni variable de entorno. El módulo no crea archivos ni staging.
- Nuevo `tests/shared_backup_format.sh`; nuevo `docs/FORMATO_CIFRADO_COMPARTIDO_V1.md`; `docs/PLAN_BACKUP_RESTORE_CENTRAL.md` actualizado a v1.2.
- La envoltura es independiente del protocolo y reutilizable por VLESS, VMess, Trojan y futuros adaptadores; cada protocolo conserva su backend/AAD nativo para re-envoltura.
- Pruebas actuales: `tests/*.sh` 47/47 PASS; `python3 -m py_compile scripts/*.py`, `bash -n` de shell modules/scripts, ShellCheck warning y shfmt focal, `git diff --check` PASS.
- No se creó snapshot ni backup real; no se implementó writer, verify, restore, journal o rollback compartido. No se leyó/modificó master key ni datos persistentes; runtime, servicios, firewall, puertos, certificados desplegados, VPS de pruebas y `Xray-Normativa/` intactos.
- Estado del bloque: IMPLEMENTADO / VERIFICADO en aislamiento / PUBLICADO / SINCRONIZADO; aceptación formal pendiente. Commit `164f91f9c9be8ab275da0b28a53b2314a636f1e2` en `design/user-identity-association-v1`; HEAD local/remoto verificado idéntico. `main` y `Xray-Normativa/` sin cambios.

## 2026-11-03 — Política de campos VMess en backup compartido

- El propietario adoptó la recomendación de excluir el UUID VMess por defecto como credencial y conservar email y level como metadatos/configuración dentro del payload cifrado.
- Se documentó que email no autentica ni es necesario para la conexión del cliente externo; tampoco se debe exponer en el manifiesto externo ni en logs.
- Los registros cuyo UUID se excluya se marcarán incompletos/no restaurables íntegramente hasta aportar la credencial mediante flujo autorizado. Incluir UUID requiere selección, autorización y confirmación adicional.
- Actualizado docs/PLAN_BACKUP_RESTORE_CENTRAL.md a v1.3 y registrados los límites en PROJECT_STATE.md, docs/CONTINUIDAD_DEL_PROYECTO.md y docs/PUNTO_CONTROL_ACTUAL.md.
- No se modificó el esquema operativo VMess, el código, la normativa, los datos persistentes ni runtime. No se generó backup ni snapshot real.

## 2026-11-03 — Desinstalación coordinada con catálogo TLS

- Se corrigió modules/uninstall.sh: si la política elimina certificados, adquiere catalog.lock después de integrity.lock y antes del bloqueo Xray. Orden del flujo: lifecycle → uninstall → integrity → catalog → Xray.
- Si el catálogo está ocupado, la desinstalación se cancela antes de respaldar o eliminar; si se adquiere, el lock se mantiene durante confirmación, respaldo y eliminación.
- Se amplió tests/uninstall.sh para probar contención de catalog.lock y que el bloqueo se mantiene durante la confirmación de eliminación de certificados.
- Verificación local: suite tests/*.sh completa PASS; bash -n, ShellCheck del módulo modificado, py_compile scripts/*.py y git diff --check PASS.
- La auditoría global de locks continúa ABIERTA; este cambio corrige únicamente el camino de desinstalación y no autoriza iniciar el writer compartido.
- Sin runtime, datos persistentes, certificados reales, master key, servicios, firewall ni cambios en Xray-Normativa/.

## 2026-11-03 — Ruta estable externa para catalog.lock

- Se detectó que borrar /var/lib/xray-manager/certificates también borraba catalog.lock aunque estuviera bloqueado, abriendo una carrera por cambio de inode.
- Se trasladó el default de catalog.lock a /run/xray-manager-certificate-locks/catalog.lock, fuera del árbol de certificados y de los datos persistentes del Manager.
- Alineados defaults CLI de certificate_store.py y certificate_resolver.py, config/paths.sh, fallbacks VLESS/VMess, desinstalación y documentación de implementación.
- tests/certificate_store.sh valida defaults de ambos CLI; tests/uninstall.sh valida que el lock vive fuera y sobrevive al borrado de los datos de certificados.
- Sin operaciones sobre archivos/locks reales, runtime, servicios, master key, datos persistentes ni Xray-Normativa/.

## 2026-11-03 — Auditoría estática del orden de locks

- Inventariados los puntos de adquisición en scripts, modules, lib, config e install.sh. No se encontró ciclo entre lifecycle, integrity, catalog y Xray-admin en los caminos inspeccionados.
- Orden recomendado para snapshot: lifecycle → integrity → catalog; liberar en orden inverso. El writer futuro debe usar timeout finito y no bloquear indefinidamente.
- tests/uninstall.sh cubre contención lifecycle/integrity/catalog/Xray, lock catalog retenido durante confirmación, liberación cuando Xray está ocupado y supervivencia del lock externo. tests/certificate_store.sh valida defaults de los dos CLI.
- Suite 47/47 PASS; Bash syntax, ShellCheck de uninstall.sh, shfmt focal, py_compile y git diff --check PASS.
- Auditoría estática no equivale a stress test exhaustivo. El cambio de ruta del lock TLS requiere despliegue con procesos de versión anterior detenidos; no se hizo runtime apply ni migración de locks reales.


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


## 2026-11-03 — Aprobación del formato lógico ZIP y canonicalización JSON v1

El propietario aprobó empaquetado ZIP con `ZIP_STORED`, estructura interna `manifest.json`/`index.json`, entradas deterministas, validaciones estrictas de rutas y tipos, hashes/tamaños/CRC, límite total de 512 MiB y perfil JSON canónico propio (UTF-8 sin BOM, claves ordenadas, compactación, sin duplicados ni floats/valores no finitos, enteros interoperables y comparación de bytes canónicos). No se afirma compatibilidad RFC 8785/JCS. El máximo de cantidad de miembros queda pendiente.

`docs/PLAN_BACKUP_RESTORE_CENTRAL.md` pasa a v1.9. Es una aprobación de diseño; no autoriza writer, verify, restore, paquetes reales, inclusión de secretos ni runtime apply. `Xray-Normativa/` no se modificó.


## 2026-11-03 — Aprobación del máximo de entradas ZIP v1

El propietario aprobó un máximo estricto de 10.000 entradas ZIP totales, contando `manifest.json` e `index.json` (hasta 9.998 miembros de datos). La creación debe abortar sin publicar paquete parcial si se supera; el lector/verify debe rechazar paquetes que excedan el límite. `docs/PLAN_BACKUP_RESTORE_CENTRAL.md` pasa a v1.10. No se autorizó implementación de writer/verify/restore ni creación de paquetes reales.


## 2026-11-03 — Aprobación del contrato técnico del snapshot writer v1

El propietario aprobó el contrato técnico del snapshot writer compartido v1 y la ampliación de cifrado incremental compatible con el contenedor criptográfico v1. Se congelan: secuencia fail-closed; locks `lifecycle → integrity → catalog`, adquisición no bloqueante con timeout total configurable (30 s inicial recomendado) y liberación inversa; captura coherente de catálogos/revisiones referenciadas; adaptadores VLESS/VMess/identidades/TLS; exclusiones predeterminadas; validación segura de archivos; manifiesto/índice/ZIP `ZIP_STORED`; máximo 10.000 entradas y 512 MiB; cifrado GCM por bloques sin cambiar el formato binario v1; verificación y publicación atómica exclusiva sin sobrescritura; estados de resultado y matriz de pruebas.

La interfaz incremental deberá conservar magic, cabecera/AAD, perfil scrypt, salt/nonce, AES-256-GCM y tag del formato v1, con compatibilidad cruzada respecto a la interfaz actual. El ZIP se emitirá en streaming al cifrador sin crear ZIP en claro en disco; el tamaño exacto del ZIP se calculará antes de fijar `ciphertext_length` y se contrastará con el flujo emitido.

`docs/PLAN_BACKUP_RESTORE_CENTRAL.md` pasa a v1.11. La aprobación autoriza implementar writer y cifrado incremental en la rama autorizada, pero no crear backups reales, incluir secretos, implementar restore/verify independiente, leer/modificar master key ni tocar runtime/servicios/firewall/puertos/certificados desplegados/VPS de pruebas. `Xray-Normativa/` permanece inmutable.


## 2026-11-03 — API incremental compatible con contenedor cifrado v1

Se añadieron `encrypt_payload_stream()` y `verify_package_stream()` a `scripts/shared_backup_format.py`. El cifrado/verificador trabajan por bloques y conservan el formato binario v1, incluida cabecera/AAD, perfil scrypt, AES-256-GCM, salt/nonce y tag. Se mantienen las APIs de bytes existentes. El verificador incremental requiere un flujo seekable, descarta plaintext no autenticado y sólo confirma autenticidad después de validar el tag GCM.

`tests/shared_backup_format.sh` amplía cobertura de compatibilidad cruzada, longitudes exactas, truncamiento, bytes sobrantes, alteración/tag y contraseña incorrecta. Prueba focal PASS; suite completa `tests/*.sh`: 47/47 PASS; pruebas adicionales de tamaños aleatorios, sintaxis Python y `git diff --check` PASS. ZIP streaming y snapshot writer siguen pendientes. No se creó backup real ni se tocaron secretos, master key o runtime.


## 2026-11-03 — Generador ZIP determinista en streaming v1

Se añadió `scripts/shared_backup_zip.py` con `ZipMember`, `ZipStream` y `write_zip_stream()`. La fuente `ZipStream.read(n)` conecta el ZIP directamente con `encrypt_payload_stream()` sin archivo ZIP temporal en claro. El ZIP es `ZIP_STORED`, determinista, UTF-8/NFC, timestamps fijos, `manifest.json` e `index.json` primero, datos ordenados, sin ZIP64; límite estricto 10.000 entradas y 512 MiB incluyendo overhead.

La lectura de archivos requiere `allowed_root` explícito, recorre directorios sin seguir symlinks, valida root:root 0600, nlink 1, inode/metadatos, tamaño, CRC-32 y SHA-256 en preflight y emisión. `tests/shared_backup_zip.sh` PASS: ZIP estándar, CRC, determinismo, integración ZIP→AES-GCM streaming→verificación→ZIP válido, rutas inseguras, symlink/hardlink, permisos, TOCTOU y límites. Suite completa `tests/*.sh`: 48/48 PASS; sintaxis Python, ShellCheck focal, shfmt focal y `git diff --check` PASS. No se creó backup real ni se tocaron secretos, master key o runtime.


## 2026-11-03 — Primera implementación local del snapshot writer compartido v1

Se implementó localmente scripts/shared_snapshot_writer.py conforme al contrato aprobado §10.11. Se corrigió el modo selective para exigir categorías explícitas; se reordenó el flujo para validar destino y preparar staging privado antes del prompt de passphrase, y pedir la passphrase antes de adquirir locks; se prohibió crear directorios operativos ausentes para locks y se endureció la validación del timeout.

Se añadió tests/shared_snapshot_writer.sh con pruebas sintéticas de selección, staging/cleanup, locks ausentes/inseguros, orden de adquisición/liberación, timeout, referencias de identidad y exclusión de credenciales. Pruebas focales writer, contenedor cifrado y ZIP streaming PASS; AST Python PASS; regresión global tests/*.sh: 49/49 PASS; git diff --check PASS.

No se creó backup real ni se ejecutó el writer contra datos reales. No se accedió a master key ni secretos reales, no se ejecutó restore/verify independiente y no se tocó runtime ni Xray-Normativa/. Estado: IMPLEMENTADO LOCALMENTE / VERIFICADO PARCIALMENTE / NO PUBLICADO / NO SINCRONIZADO / NO ACEPTADO. Pendiente suite de aceptación integral. Sin commit/push; rama design/user-identity-association-v1, HEAD ec9b306b38f0bce17f28c301c47df3b3d092785a.

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

## 2026-11-03 — Recuperación segura de staging en snapshot writer

- Aprobada por el propietario la enmienda técnica de §10.11: solicitar/confirmar y validar passphrase antes de crear staging.
- Añadido `.xrm-coordination.lock` para serializar recuperación, creación y limpieza de temporales; añadido `owner.lock` por staging, root:root 0600 y `nlink == 1`, bloqueado durante toda la operación.
- Recuperación fail-closed: retirar únicamente temporales abandonados con lock libre y estructura/permisos estrictos; conservar procesos activos y estructuras inesperadas. Coordinación liberada antes de los locks de datos, cuyo orden permanece intacto.
- Actualizada la suite SW-02 y matriz de interrupciones; suite focal PASS. Regresión `bash tests/*.sh` PASS; AST 16/16; ShellCheck, shfmt y `git diff --check` PASS. RSS aislado 74.120 KiB.
- Writer permanece local, no publicado y pendiente de aceptación formal. No backup real, secretos/master.key, restore ni cambios runtime.

## 2026-11-03 — Corrección fail-closed de coordinación y validación completa del manifiesto

Por autorización expresa del propietario, se corrigió `_acquire_coordination_lock()`: los archivos preexistentes se inspeccionan antes de abrirlos y nunca se les aplica `fchown`/`fchmod`; se rechazan hardlinks, symlinks, FIFO, tipos/permisos/propietarios inseguros y cambios de inode entre inspección y apertura. Los locks ausentes se crean exclusivamente con `O_EXCL` y `O_NOFOLLOW`, y sólo el inode recién creado recibe propietario/modo.

Se endureció `_validate_manifest_contract()` con comprobaciones de estructura, UUID v4 canónico, timestamp UTC RFC 3339, versión entera, source, selección/categorías, listas, contadores, SHA-256/tamaño/media type y coherencia `COMPLETE` frente a exclusiones/dependencias pendientes.

Pruebas nuevas de preservación de metadatos ante hardlink, symlink, FIFO, modo inseguro, timeout/contención y manifiestos inválidos. Suite focal PASS; regresión completa 49 scripts PASS; AST 16/16; `bash -n`, ShellCheck, shfmt y `git diff --check` PASS. RSS aislado focal 75.120 KiB.

Estado: cambios locales IMPLEMENTADOS/VERIFICADOS, writer NO PUBLICADO y NO ACEPTADO FORMALMENTE. Sin commit/push/sync. No se creó backup real ni se accedió a datos secretos; no restore/verify independiente ni runtime apply. `Xray-Normativa/` intacta.


## 2026-11-03 — Publicación del snapshot writer v1

Se publicó en design/user-identity-association-v1 el snapshot writer compartido v1, su suite de pruebas, los cambios de soporte del ZIP streaming/API y la documentación técnica asociada. Commit: ae8a7a089809e2e1913c14a714f45d956f8a5a1d.

Verificación previa a publicación: regresión completa 49/49 scripts PASS; AST Python 16/16; bash -n, ShellCheck, shfmt y git diff --check PASS; 14/14 archivos normativos comparados por SHA-256 con la copia maestra. scripts/__pycache__/ fue excluido. Xray-Normativa/ no se modificó.

Estado separado: IMPLEMENTADO / VERIFICADO EN AISLAMIENTO / PUBLICADO; NO ACEPTADO FORMALMENTE. No se creó backup real ni se accedió a secretos/master.key; no restore/verify independiente ni runtime apply.


## 2026-11-03 — Correcciones de segunda revisión del snapshot writer v1

Por autorización expresa del propietario se implementaron las correcciones de aceptación B-01, B-02 y B-03, manteniendo el writer NO ACEPTADO FORMALMENTE.

- B-01: se aplicó allowlist estricta a identidades/asociaciones. Sólo se conservan metadatos saneados de asociaciones VLESS/VMess; WireGuard y protocolos fuera del alcance v1 se excluyen íntegramente y se registran como unsupported_protocol/PARTIAL. Campos desconocidos o sensibles (private key, preshared key, PSK y variantes) bloquean fail-closed.
- B-02: se eliminó el silenciamiento de errores de cleanup. El descriptor de owner.lock se cierra incluso ante fallos; errores de coordinación, unlink, rmdir o fsync producen FAILED. Cuando el hard-link final ya se publicó, se conserva el paquete y el mensaje distingue publicación de limpieza fallida.
- B-03: el manifiesto sólo admite versión 1; categorías incluidas/no soportadas deben ser disjuntas y resolver exactamente la solicitud. Se valida la estructura de todos los objetos internos antes de acceder a campos.
- Se amplió la matriz de terminaciones abruptas con el prompt (sin staging), cifrado, antes de publicación y después del enlace exclusivo pero antes del fsync del directorio.

Verificación ejecutada en VPS: suite completa tests/*.sh 49/49 PASS; AST Python 16/16; bash -n 74 archivos; ShellCheck focal PASS; shfmt focal PASS; git diff --check PASS. Normativa 14/14 SHA-256 idénticos a la copia maestra.

La base del writer permanece publicada en ae8a7a089809e2e1913c14a714f45d956f8a5a1d. Las correcciones y actualizaciones documentales de esta revisión están sólo en /opt/xray-manager: sin commit, push ni sincronización. No se creó backup real ni se leyó master.key/secretos reales; no restore/verify independiente ni runtime apply. Xray-Normativa intacta.


## 2026-11-03 — Auditoría de aceptación A-16 y autorización de publicación B-01/B-02/B-03

La auditoría de aceptación identificó A-16 como bloqueo: `_recover_orphan_staging()` exige `st_nlink == 1`, pero el intervalo legítimo posterior a `os.link(package.tmp, final_path)` y anterior al unlink de `package.tmp` deja ambos nombres sobre el mismo inode (`st_nlink == 2`). La recuperación rechaza ese staging residual y lo conserva, aunque el paquete final permanezca intacto. La prueba sintética en VPS reprodujo `SnapshotBlocked`, staging y destino presentes, mismo inode y `nlink == 2`. Los tests de crash/cleanup actuales no invocan el recuperador sobre ese estado.

El propietario autorizó publicar B-01/B-02/B-03 manteniendo el writer NO ACEPTADO y documentando A-16 como pendiente bloqueante. Esta publicación no corrige A-16 ni constituye aceptación. La corrección propuesta deberá reconocer exclusivamente el hardlink legítimo demostrable hacia el artefacto final, sin relajar globalmente el rechazo de hardlinks arbitrarios, y añadir pruebas reales de recuperación.

## Publicación — B-01/B-02/B-03 (2026-11-03)

Commit `b6582da` (`fix(backup): harden snapshot identity and manifest validation`) publicado en `origin/design/user-identity-association-v1`. Incluye las correcciones B-01/B-02/B-03, sus pruebas y la documentación de continuidad/estado que mantiene A-16 como bloqueo. Snapshot Writer v1 continúa NO ACEPTADO.

## 2026-11-03 — Corrección A-16 implementada localmente (pendiente de auditoría)

Se añadió publication.json privado y durable antes de publicar el hardlink. El marcador ata el destino exacto al device/inode/tamaño/SHA-256 del paquete. _recover_orphan_staging() admite package.tmp con nlink == 2 sólo cuando el marcador y el destino prueban que ambos nombres son el mismo artefacto; elimina únicamente el nombre temporal, valida el destino restante con nlink == 1 y conserva el paquete final. La recuperación también es idempotente si se interrumpe después de retirar package.tmp. Hardlinks arbitrarios, enlaces adicionales, destinos distintos y estructuras inseguras continúan bloqueados.

Verificación posterior: tests/*.sh 49/49 PASS; AST 16/16; bash -n 74 archivos; ShellCheck PASS; shfmt focal PASS; git diff --check PASS; normativa 14/14 hashes coincidentes. A-16 pasa las pruebas de recuperación post-link y de interrupción idempotente. El writer continúa NO ACEPTADO formalmente. No backup real, secretos/master.key, restore/verify independiente, runtime ni normativa.

## Publicación — corrección A-16 (2026-11-03)

Por autorización expresa del propietario, se publicó la corrección A-16 y la documentación/pruebas asociadas en `design/user-identity-association-v1`. Commit: `40c907e2a9da639f3458547e09fec6f26fdac5e1` (`fix(backup): recover verified post-publication staging`). GitHub confirmó el mismo SHA mediante `git ls-remote`; la VPS permanece en ese HEAD y el checkout está limpio. Snapshot Writer v1 sigue NO ACEPTADO FORMALMENTE; la publicación no equivale a aceptación. No se modificó `main` ni `Xray-Normativa/`.


## 2026-11-03 — Matriz A-01–A-19 trazable y negativos adicionales A-16

Se recuperaron los nombres originales de los criterios A-01–A-19 desde el registro de auditoría previo y se documentó su trazabilidad en `docs/PLAN_BACKUP_RESTORE_CENTRAL.md` §10.20, con archivos/pruebas principales, resultado y límites de la evidencia. No se inventaron nuevos criterios ni se convirtió la prueba sintética en prueba operativa.

Se añadieron diez negativos A-16 que ejercitan el recuperador real con marcadores JSON malformados/no canónicos, hash/device/inode/tamaño incorrectos, campo extra, symlink, hardlink adicional y permisos abiertos. Todos exigen bloqueo fail-closed y preservación de staging, temporal y destino. La implementación del writer no necesitó cambios.

Regresión actual: 49/49 scripts PASS; AST Python 16/16; `bash -n` 74 archivos; ShellCheck, shfmt y `git diff --check` PASS; RSS focal 76.336 KiB. SHA-256 normativa 14/14 coincidente con la copia maestra; `README.md` es archivo adicional no normativo. Se rotularon como históricos/superados los apartados de continuidad que todavía describían A-16 como pendiente.

Estado: matriz A-01–A-19 documentada y verificada en aislamiento; Snapshot Writer v1 continúa NO ACEPTADO FORMALMENTE. No backup real, no acceso a master.key/secretos, no restore/verify independiente, no runtime apply y no modificación de `Xray-Normativa/`.


## 2026-11-03 — Publicación de la matriz A-01–A-19 y negativos A-16

Se publicó la matriz de trazabilidad A-01–A-19, diez casos negativos adicionales A-16, las actualizaciones de `PROJECT_STATE.md`, continuidad, punto de control y plan técnico. Commit `101853e6ef0990686128f45561b22e1cd4248aea` (`test(backup): expand snapshot writer acceptance evidence`) en `design/user-identity-association-v1`. `git ls-remote` confirmó el mismo SHA; la VPS quedó sincronizada y el worktree limpio. `main` no se modificó y `Xray-Normativa/` permanece intacta. La publicación no implica aceptación formal del Snapshot Writer v1.


## 2026-11-03 — Registro final de sincronización de la matriz A-01–A-19

Se actualizó el estado operativo del plan y punto de control para reflejar la publicación final. Commit `7f03efcf080465d8bced447549e29f8abb95248b` (`docs(backup): publish snapshot acceptance matrix`) en `design/user-identity-association-v1`; la VPS y GitHub coinciden en ese HEAD. El commit anterior `101853e6ef0990686128f45561b22e1cd4248aea` contiene la matriz y los diez nuevos negativos A-16. Snapshot Writer v1 permanece NO ACEPTADO FORMALMENTE.


## Aceptación formal del Snapshot Writer v1 — 2026-11-03

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


La decisión se registró en los documentos de estado, continuidad, punto de control y plan técnico. La publicación se registra en el commit de esta entrada una vez sincronizado con GitHub.


## 2026-11-03 — Primera prueba live del administrador: Xray-core y VLESS-WS

Se ejecutó el administrador en la VPS de desarrollo. Xray-core 26.10.31 (a4a3dff) quedó instalado desde el menú de administración, con verificación del release oficial, SHA-256, versión y geodata.

El preflight del almacén VLESS detectó que /var/lib/xray-manager/connections estaba en modo 750, mientras install.sh y el almacén requieren 700. Tras verificar directorio real y propietario root:root, se ajustó únicamente a modo 700; el audit posterior pasó. No se modificó código.

Desde el menú real se creó Prueba-VLESS-WS-Real (conn-1793749234-670662), modalidad vless_ws, escucha prevista 0.0.0.0:10001, path /ws, seguridad sin TLS y un slot. Se creó un usuario de prueba en el registro legacy de usuarios, que sigue siendo un arreglo JSON. La revisión neutral 1 quedó persistida; el UUID se omite del historial.

La previsualización, recuperación del borrador y validación con /usr/local/bin/xray devolvieron Configuration OK. El audit del almacén reportó cero referencias rotas y cero huérfanos.

No hubo runtime apply: Xray sigue inactivo, no existe /etc/xray/config.json ni xray.service, el puerto 10001 no escucha y no se tocó firewall. No se probó cliente externo/WAN. Xray advirtió que WebSocket está obsoleto/no recomendado y recomienda XHTTP H2/H3.

Informe: docs/VALIDACION_LIVE_XRAY_VLESS_WS_2026-11-03.md. Código sin cambios; documentos actualizados localmente, sin commit/push/sync. Xray-Normativa/ y main intactas.

## 2026-11-03 — Infraestructura inicial de candidatos runtime mediante perfiles

El propietario aprobó la opción A para respetar la normativa de Etapa 5: la activación se realizará únicamente mediante el flujo de cambio de perfil activo. No se habilitará una ruta de activación de conexiones independientes.

La inspección del repositorio confirmó que no existe todavía un gestor funcional de perfiles. Los adaptadores VLESS/VMess construyen configuraciones por conexión, no una configuración integral versionada de perfil. Por eso se implementó una primitiva aislada de staging y se dejó pendiente la integración con perfiles.

Archivos nuevos:
- scripts/xray_runtime_candidates.py
- tests/xray_runtime_candidates.sh
- docs/DISENO_IMPLEMENTACION_RUNTIME_PERFILES.md

La primitiva lee un candidato regular sin symlink/hardlink, limita el tamaño a 16 MiB, comprueba JSON, valida con el binario Xray sobre los mismos bytes almacenados, aplica timeout, almacena config y manifiesto privados (0600) bajo directorios 0700, registra SHA-256 y procedencia profile_id/profile_revision, bloquea concurrencia y no sobrescribe revisiones existentes. El resultado es STAGED, con runtime_published=false y service_started=false.

Prueba focal sintética PASS. Esta prueba no es validación de perfil real ni prueba de conectividad. La publicación runtime, el servicio y el arranque permanecen fuera del componente. No se escribió /etc/xray/config.json, no se ejecutó xray_service_prepare, no se creó unidad ni cuenta/grupo, no se inició Xray, no se habilitó autostart, no se abrió puerto ni se modificó firewall/certificados.

La conexión Prueba-VLESS-WS-Real permanece draft y runtime_applied=false. No se modificó Xray-Normativa/ ni main. No commit/push/sync.

### Corrección del aislamiento de tests/users.sh

La regresión inicial detectó que tests/users.sh recargaba modules/users.sh con rutas por defecto y podía consultar el registro live de la VPS. La prueba se detuvo por límite de capacidad sin modificar el archivo real. Se fijaron las variables de rutas/lock temporales antes de cargar los módulos; las ejecuciones posteriores de tests/users.sh y tests/smoke.sh pasan. También se reforzaron los requisitos root-owned del almacén, bloqueo y binario del staging runtime.

### Verificación final del staging runtime

Regresión completa 50/50 PASS; AST Python 17/17 PASS; bash -n en todos los archivos shell PASS; ShellCheck/shfmt focal PASS; git diff --check PASS. Xray-core 26.10.31 real validó candidato sintético temporal y lo dejó en STAGED sin publicar runtime ni iniciar servicio. Los 14 archivos normativos comparados coinciden con la copia maestra; README.md es auxiliar no normativo. Sin commit/push/sync.

## 2026-11-03 — Publicación autorizada de staging runtime y continuidad

Por autorización expresa del propietario se publica en `design/user-identity-association-v1` el componente de staging de candidatos runtime por perfil, su prueba focal, la corrección de aislamiento de `tests/users.sh`, y los documentos de diseño, validación live, estado, continuidad y punto de control. Se excluye `scripts/__pycache__/` por ser un artefacto local.

La publicación no crea ni activa el subsistema de perfiles, no publica configuración runtime, no prepara/inicia Xray, no abre puertos ni modifica firewall/certificados. `Xray-Normativa/` y `main` permanecen intactas. Etapa 2 continúa ABIERTA.


## 2026-11-03 — Implementación inicial del almacén de perfiles v1

[DECISIÓN HISTÓRICA SUPERADA EL 2026-11-03] La primera implementación local contempló texto plano, con permisos root-only. El propietario eligió posteriormente AES-256-GCM antes de la publicación de cualquier versión del almacén de perfiles; consultar la entrada cronológica más reciente al inicio de este historial.

Se añadieron `scripts/xray_profiles.py`, `modules/profiles.sh`, `tests/xray_profiles.sh` y `docs/DISENO_IMPLEMENTACION_PERFILES.md`. Se integró la carga del módulo en `bin/xray-manager`, el submenú en `modules/main_menu.sh` y la regresión de navegación en `tests/stage1_menu.sh`/`tests/smoke.sh`.

El almacén soporta creación desde cero o JSON, consulta, modificación de metadatos/configuración, duplicación independiente, renombrado, historial de revisiones y restauración no destructiva mediante nueva revisión. IDs inmutables, nombres únicos, JSON estricto hasta 16 MiB, manifiesto SHA-256, bloqueo exclusivo, archivos temporales/atómicos y controles de filesystem. Eliminación permanece deshabilitada hasta integrar y verificar perfil activo/dependencias.

Verificación ejecutada: 51/51 scripts PASS; Python AST 18/18; `bash -n` global PASS; ShellCheck y shfmt focal PASS; `git diff --check` PASS. Pruebas de perfiles aisladas en almacenes temporales.

Limitaciones: validación Xray nativa aún `not_run`; perfiles `not_validated`; estado activo `not_integrated`; no composición integral ni activación/rollback. No se creó `/var/lib/xray-manager/profiles` ni perfil real. No se modificó la conexión live, runtime, servicio, systemd, firewall, puertos, certificados o red. No se leyó/uso `master.key`. `Xray-Normativa/` y `main` intactas. Etapa 2 permanece ABIERTA.


## 2026-11-03 — Regularización de continuidad y evidencia live VMess TLS

Se incorporó el informe `docs/VALIDACION_LIVE_VMESS_TLS_LEASE_2026-11-03.md` a partir de capturas compartidas por el propietario. La segunda ejecución de Xray-core 26.10.31 bajo UID 999/GID 988 leyó el certificado y la clave sintéticos del lease y completó un handshake TLS 1.3 verificado. La primera ejecución no se contabiliza como exitosa. No se inventaron comandos, rutas, puertos, SNI, cipher suite ni causa del primer intento, porque no se dispone de la transcripción íntegra.

Se actualizaron `docs/CONTINUIDAD_DEL_PROYECTO.md`, `docs/IMPLEMENTACION_VMESS_TLS_CENTRALIZADO_PARCIAL.md`, `PROJECT_STATE.md` y `docs/PUNTO_CONTROL_ACTUAL.md` para reflejar la evidencia acotada, corregir el encabezado de perfiles v1.1 (ya publicado/sincronizado) y fijar la siguiente actividad: revisión formal de solo lectura del almacén de perfiles contra Etapa 5. No se modificó código ni documentación normativa. No se usó `master.key` real ni se creó perfil live; no runtime apply, servicio, firewall, puertos, certificados reales o WAN. VMess y Etapa 2 siguen sin aceptación integral.


## 2026-11-03 — Auditoría formal de perfiles v1.1; aceptación pendiente

Se completó la revisión de solo lectura del almacén de perfiles contra Etapa 5 Markdown/YAML. Pasaron `tests/xray_profiles.sh`, `tests/stage1_menu.sh`, `tests/smoke.sh`, AST Python, `bash -n`, ShellCheck focal y `git diff --check`; no se repitió la regresión completa histórica 51/51.

PF-01 BLOQUEANTE reproducido mediante fault injection en un almacén temporal: `update()` puede guardar metadatos y fallar al guardar catálogo, dejando discrepancia que hace fallar `list_profiles()`. PF-02 ALTO: las operaciones multiarchivo requieren transacción recuperable y pruebas de write/replace/fsync/crash. Se documentaron además pendientes funcionales de Etapa 5. No se modificó código ni normativa. No se leyó `master.key`, no se creó almacén/perfil live ni se tocó runtime.

Se corrigió `docs/DISENO_IMPLEMENTACION_PERFILES.md` para describir el hash real del manifiesto (SHA-256 del ciphertext y tamaño del plaintext). Informe: `docs/AUDITORIA_FORMAL_PERFILES_V1_1_2026-11-03.md`. Recomendación: no aceptar aún v1.1 hasta resolver PF-01/PF-02. Siguiente paso sujeto a autorización expresa del propietario.


## 2026-11-03 — Inicio de remediación transaccional PF-01/PF-02

Tras autorización expresa del propietario, se implementó localmente un journal WAL con snapshots de catálogo/metadatos, whitelist de rutas, rollback idempotente y recuperación al adquirir el lock. Integración en create/duplicate/rename/update/restore. Se añadieron pruebas de fallo de escritura, fsync posterior a replace, crash en varias fases e interrupción durante rollback. Prueba focal `tests/xray_profiles.sh` PASS. Regresión completa final: 51/51 scripts PASS; Python AST, Bash syntax, ShellCheck focal y `git diff --check` PASS. La revisión final del diff y publicación aún están pendientes. Sin secretos reales, perfiles live ni cambios runtime.
## 2026-11-04 — Limpieza segura de temporales huérfanos de perfiles

Se implementó en /opt/xray-manager sobre design/user-identity-association-v1 la fase correctiva previamente autorizada.

- ProfileStore.locked() ejecuta recover_transaction() y, sólo después de una recuperación exitosa y aún bajo lock exclusivo, cleanup_orphan_temps().
- Se reconocen sólo .new- + 16 hex dentro de profiles/, .revision- + 16 hex dentro de profiles/<profile_id>/revisions/ y temporales atómicos .<destino>.<16 hex>.tmp en ubicaciones controladas.
- Validación lstat, tipo, root:root, permisos 0700/0600, nlink=1 y estructura acotada antes de eliminar. Symlinks, metadatos anómalos y entradas desconocidas se preservan y reportan.
- atomic_write() retira su temporal si os.replace() falla; si el replace ya publicó el destino y falla el fsync del directorio, no elimina el destino.
- Pruebas añadidas: SIGKILL real antes del replace, durante publicación .new-* y .revision-*, recuperación en siguiente operación, idempotencia, anomalías symlink/modo/owner/hardlink preservadas, revisión publicada conservada y destino publicado intacto ante fallo de fsync.

Verificación: tests/*.sh 51/51 PASS; Python AST 18/18; bash -n; ShellCheck focal (SC2251/SC2034 preexistentes excluidos); shfmt focal; git diff --check. Las pruebas usan únicamente almacenes temporales y claves sintéticas. No se leyó master.key, no se creó/limpió almacén live y no se tocó runtime, systemd, firewall, puertos, certificados o red.

Estado: cambios locales en VPS; revisión final y sincronización GitHub pendientes. No implica aceptación formal del almacén ni cierre de Etapa 5/Etapa 2.
## 2026-11-04 — Endurecimiento de recuperación WAL de perfiles

- Separada la validación integral del journal de la aplicación del rollback.
- Validación previa de esquema, rutas permitidas, duplicados, snapshots Base64/límites, directorios padre, destinos existentes y directorios a retirar.
- Rechazo de solapamientos entre destinos y directorios de rollback; journal inválido se conserva y falla cerrado sin rollback parcial.
- Añadidas pruebas de entrada inválida tardía y lista de eliminación inválida, verificando catálogo byte a byte intacto.
- PF-01/PF-02 corregidos dentro del alcance probado; PF-06 parcialmente cubierto; PF-07 pendiente. Sin aceptación formal ni cierre de Etapa 5/Etapa 2.

## 2026-11-04 — Remediación PF-07: esquema estricto del catálogo

Se endureció `ProfileStore.load_catalog()` para validar íntegramente el catálogo antes de usarlo: versión entera exacta (sin aceptar booleanos), raíz y campos exactos, máximo 10000 perfiles, IDs con formato fijo, nombres normalizados sin controles, timestamps UTC reales y orden temporal, además de unicidad de IDs/nombres. Los datos inválidos generan `ProfileError` sin modificar el archivo.

Se añadieron 18 pruebas negativas y una comprobación de preservación byte a byte. La prueba focal `tests/xray_profiles.sh` pasó con almacén temporal y clave sintética. Verificación final: 51/51 scripts, AST 18/18, bash -n, ShellCheck focal, shfmt y `git diff --check` PASS. Revisión del diff completada; publicado/sincronizado en `design/user-identity-association-v1`, commit `85c637c93778780c98589dc2f791b190daeedfd6`. PF-07 se considera corregido dentro del alcance probado; no hay aceptación formal ni cierre de Etapa 5/Etapa 2.

## Correcciones PF-08/PF-09/PF-10 del almacén de perfiles — 2026-11-04

Autorización del propietario aplicada en la rama design/user-identity-association-v1, host Implementación-Xray, ruta /opt/xray-manager.

- PF-08: validación previa de tipos, límites y texto imprimible de descripción/notas; configuración validada antes de publicar una nueva revisión. Cuatro casos negativos verifican que no se crea revisión huérfana.
- PF-09: reconciliación bajo lock de revisiones definitivas posteriores al current_revision confirmado. Sólo se elimina una revisión con directorio/archivos seguros, contenido exacto y manifiesto coherente; artefactos no verificables se preservan y reportan.
- PF-10: contrato estricto de metadatos: conjunto exacto de campos, tipos no coercitivos, fechas UTC reales, límites y caracteres de texto, IDs de revisión y coherencia de estado/punteros.

Pruebas focales: tests/xray_profiles.sh PASS; PF-08 cuatro casos, PF-09 SIGKILL después del rename y recuperación en la siguiente operación, PF-10 dieciocho metadatos malformados rechazados. Python AST 18/18, py_compile del módulo modificado, bash -n global, ShellCheck focal y git diff --check PASS. shfmt -d -i 4 tests/xray_profiles.sh muestra diferencias de estilo preexistentes (indentación de bloques if en el archivo); no se reformateó el archivo completo para evitar cambios ajenos al alcance.

Informe: docs/AUDITORIA_CORRECCIONES_PF08_PF09_PF10_2026-11-04.md. Regresión general tests/*.sh finalizada: 51/51 scripts PASS (exit code 0).

Límites: sólo almacenes temporales y claves sintéticas. No se leyó master.key, no se crearon perfiles live, no se tocó runtime/servicios/certificados/firewall/puertos/red. Xray-Normativa/ y main intactas. No publicado en GitHub; publicación requiere autorización expresa posterior. Almacén v1.1 no aceptado formalmente; Etapa 5 y Etapa 2 siguen ABIERTAS.
