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
