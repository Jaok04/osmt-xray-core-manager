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
