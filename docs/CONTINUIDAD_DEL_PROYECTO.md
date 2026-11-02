# Protocolo de continuidad — Xray Core Manager

## 1. Objetivo

Permitir que cualquier IA o desarrollador retome el proyecto desde su último estado válido aunque el chat original se haya perdido, borrado o sustituido. La fuente de continuidad es el repositorio y la evidencia de la VPS, no la memoria de una conversación.

## 2. Mensaje para iniciar un chat nuevo

Copia y pega el siguiente texto en el nuevo chat:

~~~text
CONTINUAR PROYECTO XRAY CORE MANAGER

Necesito recuperar y continuar el proyecto exactamente desde su último punto de control documentado.

Repositorio oficial:
https://github.com/Jaok04/xray-core-manager

Rama autorizada:
design/user-identity-association-v1

No modificar la rama main.

Rutas oficiales de la VPS:
- Documentación normativa aprobada: /root/Xray_Manager_Documentacion_Final_2026-10-31
- Proyecto en desarrollo: /opt/xray-manager

Primero lee, en este orden:
1. AGENTS.md
2. PROJECT_STATE.md
3. docs/CONTINUIDAD_DEL_PROYECTO.md
4. docs/PUNTO_CONTROL_ACTUAL.md
5. HISTORY.md

Después realiza una auditoría de recuperación sin modificar archivos:
- consulta el HEAD real de la rama autorizada;
- verifica el estado y contenido de /opt/xray-manager;
- comprueba si la VPS tiene .git; no presupongas que sí;
- consulta la documentación normativa;
- contrasta los archivos y hashes de GitHub y VPS;
- identifica diferencias, cambios sin publicar y estados inciertos;
- recupera el estado de cada etapa y el último punto de control.

Distingue IMPLEMENTADO, VERIFICADO, PUBLICADO, SINCRONIZADO y ACEPTADO. No presentes pruebas históricas como si se hubieran ejecutado ahora.

No implementes, publiques, sincronices ni modifiques nada durante la auditoría. Presenta el informe y espera mi autorización explícita para el siguiente paso.
~~~

## 3. Orden de lectura

1. AGENTS.md: reglas obligatorias para la IA.
2. PROJECT_STATE.md: fotografía consolidada del estado y las etapas.
3. Este documento: procedimiento de recuperación y reanudación.
4. docs/PUNTO_CONTROL_ACTUAL.md: tarea exacta en la que se detuvo el trabajo.
5. HISTORY.md: decisiones e hitos cronológicos.
6. Documentación normativa de la VPS y documentos técnicos específicos de la etapa que se vaya a trabajar.
7. `docs/REGLA_CONTRASTE_DOCUMENTACION_PRELIMINAR.md` y `docs/REGLA_AUDITORIA_INTEGRAL_CIERRE_ETAPAS.md`.

## 4. Auditoría de recuperación obligatoria

Antes de proponer implementación:

### GitHub
- Confirmar que existe el repositorio y la rama autorizada.
- Consultar el HEAD actual de design/user-identity-association-v1.
- Registrar SHA, mensaje y fecha del último commit.
- Revisar los archivos de continuidad y los archivos técnicos relevantes.
- Confirmar que main no se ha modificado.

### VPS
- Inspeccionar /opt/xray-manager.
- Comprobar explícitamente si existe .git.
- Si no existe .git, tratarla como copia de trabajo sin rama/commit verificables.
- Inventariar módulos, configuración, pruebas y documentación.
- Revisar cambios locales y fechas, sin sobrescribir nada.
- Leer la documentación normativa en /root/Xray_Manager_Documentacion_Final_2026-10-31.

### Contraste
- Comparar archivos por contenido y SHA-256 cuando sea posible.
- Separar coincidencias, divergencias, archivos solo locales y archivos solo remotos.
- No corregir diferencias automáticamente.
- No asumir que una diferencia de hash con texto aparentemente igual carece de importancia; revisar bytes, codificación, saltos de línea y final de archivo.
- Identificar cualquier cambio no publicado o no sincronizado.

## 4.1 Contraste normativo obligatorio antes de implementar

Antes de iniciar cualquier etapa o tarea de implementación, consulta directamente la documentación preliminar aprobada en `/root/Xray_Manager_Documentacion_Final_2026-10-31` y contrástala punto por punto con el estado real de GitHub, la VPS, el código, los catálogos, las pruebas y la documentación técnica. Presenta el informe de conformidad, omisiones y divergencias antes de editar.

Las mejoras son posibles, pero toda mejora o cambio respecto del alcance aprobado debe justificarse, describir sus impactos y alternativas, y recibir autorización expresa del propietario antes de modificar diseño o código. No infieras autorización por silencio, continuidad de la conversación ni aprobaciones anteriores de otras tareas. Si la fuente no está disponible o existe una contradicción relevante, detente y solicita aclaración.

Procedimiento completo y vinculante: `docs/REGLA_CONTRASTE_DOCUMENTACION_PRELIMINAR.md`. Esta regla complementa AGENTS.md y es de cumplimiento obligatorio para cualquier IA o colaborador.


## 4.2 Auditoría integral obligatoria antes de cerrar cualquier etapa

Regla permanente del propietario: ninguna etapa puede declararse TERMINADA/COMPLETADA si no se han auditado y documentado técnicamente todos sus puntos, subpuntos, módulos, submódulos y componentes internos. No basta con cerrar un protocolo, completar una funcionalidad, pasar pruebas, publicar o sincronizar.

Antes de proponer un cierre:
- construir el inventario completo desde la documentación preliminar aprobada;
- trazar cada requisito hacia diseño, implementación, pruebas y evidencia;
- auditar cada elemento individualmente, incluyendo comportamiento, diseño, código, datos, seguridad, errores, integración, pruebas y documentación técnica aplicables;
- identificar explícitamente ausencias, incompletitudes, divergencias, elementos no verificados, riesgos y decisiones pendientes;
- completar la documentación técnica de cada punto/módulo y la regresión integral de la etapa;
- emitir un informe final de auditoría y obtener aceptación formal expresa del propietario.

Cualquier elemento sin auditoría, documentación o evidencia suficiente bloquea el cierre, salvo excepción específica autorizada y documentada por el propietario. Un módulo sí puede cerrarse individualmente, pero la etapa permanece ABIERTA hasta superar la puerta integral.

Documento operativo vinculante: `docs/REGLA_AUDITORIA_INTEGRAL_CIERRE_ETAPAS.md`. Debe leerse junto con la regla de contraste previo; ambas son obligatorias y no se sustituyen entre sí.

## 5. Cómo reanudar el desarrollo

Después de la auditoría:

1. Presentar el estado real y las incertidumbres.
2. Identificar el siguiente paso permitido por la documentación normativa.
3. Señalar qué archivos se modificarían y por qué.
4. Explicar las pruebas previstas y el riesgo.
5. Esperar autorización explícita del propietario.
6. Implementar únicamente el alcance aprobado.
7. Probar y documentar el resultado.
8. Actualizar los documentos de continuidad.
9. Publicar en la rama autorizada si se autorizó la publicación.
10. Verificar GitHub y la VPS por separado.

## 6. Reconciliación segura de GitHub y VPS

La VPS puede no ser un checkout Git. En ese caso, la sincronización debe hacerse como transferencia controlada de archivos:
- comparar antes de copiar;
- conservar una copia de seguridad de los archivos destino que vayan a reemplazarse;
- no sobrescribir archivos divergentes sin resolución;
- verificar el SHA-256 de origen y destino después de transferir;
- registrar la fecha, los archivos y el método utilizado.

Si la VPS tiene .git en una sesión futura, no asumir que está limpia. Inspeccionar branch, status, remotos y commits antes de cualquier operación.

## 7. Actualización obligatoria tras cada cambio aprobado

Todo cambio que se implemente y sea aprobado debe cerrar con la actualización de la continuidad y la sincronización del repositorio con GitHub. Es una regla permanente: no debe depender de que el propietario vuelva a solicitarla en cada tarea. La aprobación del alcance incluye completar el ciclo de documentación, commit y publicación en la rama autorizada, salvo que el propietario indique expresamente una restricción distinta.

Al cerrar cada cambio aprobado:
- **PROJECT_STATE.md:** actualizar la fotografía global cuando cambie el estado, alcance o avance del proyecto.
- **docs/PUNTO_CONTROL_ACTUAL.md:** actualizar el punto exacto de reanudación, lo completado, lo pendiente y la siguiente acción permitida.
- **HISTORY.md:** añadir una entrada cronológica con el cambio, la aprobación/decisión, pruebas y commit; nunca borrar entradas anteriores.
- **AGENTS.md:** actualizar únicamente cuando se apruebe o cambie una regla permanente para agentes.
- **Este documento:** actualizar únicamente cuando cambie el procedimiento de continuidad, recuperación o sincronización.
- **Documentación técnica afectada:** mantenerla alineada con el comportamiento real del código.
- **Documentación normativa:** no modificarla sin aprobación expresa del propietario.

### 7.1 Verificación y publicación

1. Ejecutar las pruebas pertinentes y registrar resultados reales. Anotar las pruebas no ejecutadas y el motivo; nunca presentar pruebas históricas como recién ejecutadas.
2. Revisar el diff completo y validar formato, sintaxis y consistencia de los documentos.
3. Crear un commit descriptivo con los cambios aprobados.
4. Publicar en `design/user-identity-association-v1`; nunca en `main`.
5. Verificar el SHA remoto y los archivos publicados.
6. Verificar que `/opt/xray-manager` coincide con el estado publicado y queda limpio. Si hay divergencias, detener la sincronización destructiva, preservar los cambios y documentar el bloqueo.
7. Informar por separado los estados IMPLEMENTADO, VERIFICADO, ACEPTADO, PUBLICADO y SINCRONIZADO.

No se cierra la tarea mientras falte la actualización documental o la sincronización, excepto cuando exista una restricción explícita o un bloqueo técnico; en ese caso, el pendiente debe quedar claramente registrado.

## 8. Regla de recuperación

Si los archivos de continuidad contradicen el código o la documentación normativa, no elijas una versión por intuición. Informa la contradicción, conserva ambas evidencias y pide una decisión cuando afecte requisitos o comportamiento.


## Diseño de persistencia segura VLESS — 2026-11-02

El diseño arquitectónico está en docs/DISEÑO_PERSISTENCIA_SEGURA_VLESS.md y fue aprobado por el usuario el 2026-11-02. P1 está publicado; P2 está en implementación. La clave maestra real aún no se ha generado.

Hallazgo de seguridad: el asistente actual entrega la clave privada REALITY a jq mediante --arg; corregir esa exposición a argumentos de proceso será requisito de la fase de implementación.

## P1 — Infraestructura criptográfica VLESS (2026-11-02)

P1 está implementada en scripts/vless_crypto.py y probada mediante tests/vless_crypto.sh. La dependencia python3-cryptography quedó formalizada en install.sh y modules/system_admin.sh. La clave maestra real no se ha generado en la VPS; P3 ya permite generarla de forma idempotente durante el primer guardado real de una modalidad con secreto. Las funciones ensure_master_key, load_master_key, encrypt_secret, decrypt_secret, write_encrypted_blob y read_encrypted_blob forman la API inicial. El paso siguiente es P2: almacén versionado de configuración no secreta, referencias de secretos y consistencia transaccional con el catálogo.


### Actualización 2026-11-02 — P2 en curso

Se implementó inicialmente `scripts/vless_config_store.py` con esquema neutral VLESS versión 1, revisiones inmutables, publicación atómica de referencias bajo el bloqueo compartido y auditoría sin borrado automático. `tests/vless_config_store.sh` PASS. P2 no está completado: quedan pruebas de interrupciones/concurrencia, suite completa y auditoría final. No se activó runtime ni se creó la clave maestra real.

P2: `tests/*.sh` 25/25 PASS; pruebas específicas incluyen interrupción antes de publicar catálogo (huérfano detectable) y dos escritores concurrentes. `install.sh --check`, sintaxis, py_compile, ShellCheck, shfmt y diff PASS. El campo `secret_ref` queda reservado como null hasta P3.

### P3 — integración de persistencia segura VLESS (implementada y verificada)

Se integró guardado bajo confirmación desde el asistente, cifrado AES-256-GCM de claves privadas TLS/REALITY, referencias versionadas en catálogo/configuración y recuperación temporal para validación. Nuevo `scripts/vless_prepare_config.py`; `vless_config_store.py` ahora admite secretos cifrados y auditoría de blobs. El asistente deja de pasar la clave REALITY como `jq --arg` y usa `--rawfile`. Pruebas focales REALITY/TLS/recuperación PASS. Borradores no se activan. Suite completa `tests/*.sh` 25/25 PASS; `install.sh --check`, `bash -n`, `py_compile`, ShellCheck, shfmt y `git diff --check` PASS. Clave maestra real de VPS no generada. P3 aún no publicada en GitHub.

### P4 — backup y recuperación segura VLESS (COMPLETADA Y ACEPTADA el 2026-11-02)

El subsistema incluye backup de datos/manifiesto/SHA256SUMS, paquete de recuperación scrypt + AES-256-GCM, verificación, restauración confirmada y menú. La corrección registra `had_connections`/`had_secrets`, fuerza `fsync` de los directorios padres tras renombrados y recupera journals nuevos y legacy de forma conservadora.

`tests/vless_backup_journal_crash_matrix.sh` cubre 32 interrupciones abruptas en fases y renombrados, con las cuatro combinaciones de existencia previa de ambos directorios. `tests/vless_backup_journal.sh` cubre journal legacy y destino originalmente ausente. `tests/vless_backup_restore_secrets.sh` comprueba restore de blobs REALITY/TLS con el certificado TLS externo ausente, dependencia declarada y runtime inactivo. La suite completa final tras esta revisión registró 31/31 PASS; `install.sh --check`, sintaxis Bash, `py_compile`, ShellCheck, shfmt y `git diff --check` PASS. No se creó backup operativo ni se accedió a la clave maestra real.
Publicación GitHub: `90766d4cb8000ed1f94fb808b80f18483d5778cb`; árbol `cfdb26fd7716f622127ba5d7784884df58799b4c`; VPS sincronizada con `origin`.

**P4 COMPLETADA:** journal robusto, límites agregados, validación autónoma del payload y cierre TOCTOU implementados; suite 32/32 PASS y aceptación formal del propietario el 2026-11-02. Ver `docs/P4_BACKUP_RECUPERACION_VLESS.md`.


## Incidente de pruebas — EOF en menús y crecimiento de /tmp (2026-11-02)

Se investigó una alerta real de disco al 95–99.9%. La auditoría de la VPS encontró un archivo de salida de 20,465,770,496 bytes dentro de `/tmp/tmp.oaFf5wTZwt/connections-action-error.out` y un proceso huérfano que mantenía abierto otro archivo ya eliminado de aproximadamente 925 MB. El proceso se detuvo de forma ordenada y se eliminó únicamente ese directorio temporal, después de verificar que no había handles abiertos. El disco quedó en 3.7 GB usados, 71 GB libres (5%). No se modificaron datos persistentes, configuraciones ni runtime.

Causa técnica confirmada: `ui_read_option()` convertía EOF en una cadena vacía y devolvía éxito. Los menús dentro de `while true` interpretaban esa cadena como opción inválida y volvían a imprimir el menú indefinidamente. Se corrigió el contrato para devolver estado 1 en EOF, limpiar la variable destino y hacer que los consumidores abandonen el menú/flujo actual de forma ordenada. También se protegieron los prompts de identificador del menú de backup VLESS.

La regresión quedó cubierta en `tests/stage1_menu.sh`: EOF directo en menús principales y secundarios, EOF anidado al navegar conexiones, y límite de salida de 1 MiB para que una regresión no vuelva a llenar el disco. La prueba `tests/vless_backup_restore_secrets.sh`, que ya estaba en la VPS sin seguimiento Git, se revisó y ejecutó PASS; se incorpora al repositorio en este cierre.

Resultados ejecutados: suite completa `tests/*.sh` 30/30 PASS; `install.sh --check`, `bash -n` de todos los `.sh`, ShellCheck de módulos y pruebas modificados, `shfmt -d -i 4 tests/stage1_menu.sh` y `git diff --check`: PASS. Los directorios `/tmp/tmp.u7Vq57eHNx` (282 MB) y `/tmp/tmp.EsxO527Ihe` (47 MB) se inspeccionaron; contienen salidas históricas de pruebas de menú V2 con repetición por EOF, pero se conservaron y no se borraron.

El cambio quedó IMPLEMENTADO y VERIFICADO. Publicación confirmada en GitHub, rama `design/user-identity-association-v1`, commit `fa7242a61248a71b64552511d1db932ebbc8d7d0`. El árbol Git remoto `b03db9b450288eccbf61e761655f286763df3a70` coincide exactamente con el árbol del commit local `b520c53bd5a32007b30519e0756fce13fe8916b5`: los 17 archivos y sus modos son idénticos. La VPS no pudo hacer `git push`/`git fetch` por falta de autenticación SSH y HTTPS; por ello los identificadores de commit local/remoto difieren y la referencia local `origin/design/user-identity-association-v1` permanece desactualizada en el commit base anterior. No se debe volver a aplicar el cambio; en una sesión con autenticación Git disponible, reconciliar la referencia local con el HEAD remoto sin duplicar commits.

## 2026-11-02 — autenticación SSH y reconciliación de referencias

Se creó una clave SSH Ed25519 dedicada a este repositorio y se registró en GitHub como Deploy Key de solo lectura (sin permiso de escritura). La VPS autentica correctamente mediante el alias `github.com-xray-core-manager`; la URL `origin` de este checkout usa ese alias y los demás repositorios/configuraciones SSH no se modificaron. `git fetch` se completó correctamente. Se verificó que el árbol local anterior y el árbol remoto eran idénticos (`b6ed32ae1ff32dc4c8c6953a2d1eec48159b1d08`), por lo que se movió únicamente la referencia local de la rama con comprobación del SHA anterior, sin resetear ni sobrescribir archivos. Estado final: `design/user-identity-association-v1` y `origin/design/user-identity-association-v1` apuntan a `5ade7feda328ff4a4f6796fd7ab263237b40dbfa`; working tree limpio y sin divergencia. Las notas anteriores sobre falta de autenticación y refs obsoletas quedan superadas por esta verificación. La clave SSH anterior se conservó intacta. La Deploy Key nueva es de solo lectura; las publicaciones futuras deberán seguir usando el mecanismo autorizado de GitHub API u otro acceso de escritura expresamente configurado.


### Actualización P4 — auditoría de límites y TOCTOU (2026-11-02)

Se implementó límite agregado de 512 MiB sin comprimir en recolección, creación, verificación y extracción. El lector de payload valida independientemente rutas, traversal, tipos regulares, enlaces, duplicados, cantidad, tamaños y hashes. La restauración verifica y lee el backup y la clave, y extrae el payload únicamente después de adquirir `lifecycle.lock` e `integrity.lock`; el hash se vuelve a comprobar sobre los bytes usados. Nueva prueba `tests/vless_backup_limits.sh` PASS; suite completa posterior 32/32 PASS. P4 quedó COMPLETADA tras la aceptación formal del propietario el 2026-11-02. No se creó backup operativo ni se accedió a la clave maestra real.


### Cierre formal P4 — 2026-11-02

El propietario aceptó las correcciones adicionales de seguridad. La etapa P4 de backup y recuperación segura VLESS queda **COMPLETADA Y ACEPTADA**. Verificación final: suite `tests/*.sh` 32/32 PASS; `install.sh --check`, `bash -n`, `py_compile`, ShellCheck, shfmt y `git diff --check` PASS. El commit de implementación está publicado y sincronizado en la rama del proyecto. El alcance no incluye activar runtime, reiniciar Xray, abrir puertos, cambiar firewall ni desplegar certificados externos.


## VMess — continuidad de implementación (2026-11-02)

El diseño VMess y su implementación fueron autorizados por el propietario, incluyendo HTTPUpgrade-TLS. El trabajo local en `/opt/xray-manager` contiene modelo, adaptador Xray-core 26.10.31, asistente, preparación de configuración, almacén cifrado y pruebas. La matriz de 14 modalidades pasó `xray run -test`; suite completa `tests/*.sh`: 36/36 PASS. También pasaron `bash -n`, `py_compile`, ShellCheck a nivel warning, shfmt de archivos VMess nuevos, `install.sh --check` y `git diff --check`. Los cambios están publicados y sincronizados en la rama autorizada, pero no aceptados como módulo completo; consultar `docs/PUNTO_CONTROL_ACTUAL.md`.

### Separación del almacenamiento VMess

La persistencia VMess se ubica en `/var/lib/xray-manager/vmess/`, con `configurations/` y `secrets/` privados. El catálogo común continúa en `/var/lib/xray-manager/connections/connections.json`, pero VMess solo usa `vmess_configuration_ref`, `vmess_secret_ref`, `vmess_configuration_revision` y `vmess_configuration_schema_version`. No cambiar los campos VLESS ni `scripts/vless_backup.py` como parte de esta tarea. El bloqueo de integridad continúa compartido para serializar escrituras del catálogo.

P4 VLESS no incluye el almacén VMess separado. La restauración VLESS ahora combina las entradas VLESS del backup con las entradas VMess vigentes y valida sus referencias; los archivos del almacén VMess permanecen intactos. Esta corrección posterior se documenta en la sección 9 de `docs/P4_BACKUP_RECUPERACION_VLESS.md`. Backup/restore VMess independiente debe diseñarse y aprobarse por separado.

Los usuarios VMess todavía se introducen manualmente; la asociación con identidades globales pertenece a Etapa 3 y no debe implementarse dentro de esta tarea sin su definición/autorización.

### Estado de publicación

La implementación VMess y el aislamiento fueron publicados tras autorización expresa: commit `c20277c04b9417f2e22b285891fb3f348ea8e8f4` en `design/user-identity-association-v1`. La Deploy Key SSH de la VPS es de solo lectura; la publicación se efectuó mediante GitHub API y luego la VPS hizo fetch/reset para igualar HEAD local/remoto. No se modificó la rama `main`. No tocar runtime, firewall, puertos ni servicio. La Etapa 2 continúa abierta.

## Cierre técnico VMess — 2026-11-02

La auditoría de cierre contrastó el módulo con la especificación funcional Etapa 2 revisión 1.3 y con el diseño aprobado en `docs/DISEÑO_TECNICO_VMESS.md`. El módulo VMess queda IMPLEMENTADO y VERIFICADO; la aceptación formal del propietario permanece pendiente.

Evidencia de esta revisión:
- Xray-core 26.10.31 (build `a4a3dff`): 14/14 modalidades aceptadas con `xray run -test`.
- Navegación del menú: las 14 combinaciones recorridas individualmente.
- Pruebas negativas: certificado/clave TLS ausentes, symlink, PEM inválido, par certificado-clave no coincidente, REALITY incompleto/short ID inválido/clave inválida, campos incompatibles y combinación modelo-seguridad inválida.
- Se endureció el adaptador VMess para validar PEM y correspondencia criptográfica de certificado y clave privada con la biblioteca `cryptography`. La prueba detectó que `xray run -test` no rechaza por sí solo un certificado PEM malformado; por eso la validación se realiza antes de generar el JSON.
- Suite completa `tests/*.sh`: 36/36 scripts PASS.
- `bash -n`, `python3 -m py_compile scripts/*.py`, `./install.sh --check`, ShellCheck warning, shfmt y `git diff --check`: PASS.

Cambios de esta revisión:
- `modules/vmess_xray_26_10_31.sh`
- `tests/xray_vmess_integration.sh`
- `tests/stage2_navigation.sh`
- `docs/DISEÑO_TECNICO_VMESS.md`
- `PROJECT_STATE.md`
- `docs/PUNTO_CONTROL_ACTUAL.md`

Límites conservados:
- No se probó conectividad extremo a extremo ni se activaron borradores.
- No se tocó runtime, servicio, firewall, puertos, certificados desplegados ni P4 VLESS.
- Backup/restore VMess requiere diseño independiente.
- Integración con identidades globales pertenece a Etapa 3.
- Etapa 2 sigue abierta; completar VMess no implica completar Trojan, Shadowsocks, Hysteria2 ni protocolos opcionales.

**Estado de acceso Git vigente:** la Deploy Key SSH de este repositorio tiene actualmente permiso de escritura y el alias `github.com-xray-core-manager` está configurado en la VPS. Las notas históricas anteriores que la describen como solo lectura quedan superadas por esta configuración posterior.

Publicación del cierre técnico confirmada en `design/user-identity-association-v1`: commit `ab76a57032faa9793a62348f865fba2c9a7d8f77`. La VPS hizo push y fetch del commit funcional y de la actualización documental; HEAD local/remoto se verificaron coincidentes y el árbol quedó limpio. Obtener el SHA vigente con `git rev-parse HEAD`. La Deploy Key SSH actual tiene permiso de escritura; la nota anterior de solo lectura es histórica y está superada.

El punto de reanudación exacto está en `docs/PUNTO_CONTROL_ACTUAL.md`. No iniciar Trojan hasta recibir la aceptación formal de VMess y efectuar el contraste específico de Trojan.


## 2026-11-02 — Bloque 1: preservar VMess durante restauración VLESS

El propietario aprobó el plan completo de correcciones para el cierre de VMess y autorizó iniciar por el Bloque 1. Se contrastó de nuevo la gobernanza, la documentación preliminar de Etapa 2 y el contrato P4 documentado. Se confirmó que `restore_data()` reemplazaba `connections/` con el catálogo histórico del backup; como el catálogo es compartido, esto podía perder entradas VMess actuales.

Se implementó en `scripts/vless_backup.py` una combinación en staging bajo `lifecycle.lock` e `integrity.lock`: las conexiones VLESS proceden del backup y las VMess proceden del catálogo vigente. Las VMess históricas del snapshot no prevalecen. Se validan catálogo actual, IDs únicos, modalidades VMess, referencias de configuración/secreto y archivos regulares con permisos seguros. Colisiones VLESS/VMess, catálogo corrupto, referencias rotas, protocolo desconocido o fallo de escritura staging detienen la operación antes de publicar. El almacén VMess separado no se modifica ni se incluye en el backup VLESS.

Se creó `tests/vless_restore_preserves_vmess.sh` con casos de VMess anteriores y posteriores al backup, referencias `vmess_*`, comprobación byte a byte del almacén, colisión de IDs, catálogo corrupto, refs rotas y fallo de escritura. Se ajustó `tests/vless_backup_journal_crash_matrix.sh` para que su estado previo sea un catálogo VMess JSON válido y se conservaron las 32 pruebas de interrupción/rollback. Suite completa: 37/37 scripts PASS. `python3 -m py_compile scripts/*.py`, `bash -n` de todos los scripts Bash, `install.sh --check`, ShellCheck warning de las pruebas modificadas y `git diff --check`: PASS.

Estado del Bloque 1: IMPLEMENTADO, VERIFICADO, PUBLICADO y SINCRONIZADO; commit `c890b5b5362e17e439f198b9b8bbbdbe0af0c653`. La aceptación formal específica permanece pendiente. P4 conserva su aceptación histórica para el alcance original; la corrección se registra como incremento posterior. No se creó backup operativo ni se accedió a la clave maestra real. No se tocó runtime, servicio, firewall, puertos ni certificados desplegados. La documentación normativa preliminar se mantuvo intacta.

Próximo paso del plan aprobado: Bloque 2, correcciones del asistente VMess. Etapa 2 sigue ABIERTA y VMess no se considera ACEPTADO hasta completar el proceso de cierre.


## 2026-11-02 — Bloque 2: advertencias y resumen del asistente VMess

El asistente VMess ahora informa, antes de solicitar parámetros, que el desfase horario cliente/servidor no debe superar 120 segundos. Muestra una advertencia WebSocket (Xray 26.10.31 lo marca obsoleto/no recomendado y recomienda migrar a XHTTP H2/H3) y una advertencia HTTPUpgrade: Xray 26.10.31 lo marca obsoleto/no recomendado, podría retirarlo y recomienda XHTTP H2/H3; ambos transportes pueden presentar patrones identificables. Ambas modalidades se conservan conforme al alcance aprobado.

Después de `xray run -test` y antes del consentimiento de guardado, se presenta el resumen de conexión: nombre/ID, dirección/puerto, modalidad, transporte/seguridad, usuarios y parámetros aplicables de transporte, TLS o REALITY. No se imprime el contenido de claves privadas. La ruta TLS se muestra como parámetro; para REALITY se indica sólo que la clave está presente y se almacenará cifrada.

Durante la prueba REALITY se detectó una colisión de nombre en las funciones `connections_vmess_read*`: el parámetro local `target` ocultaba el destino del llamador al intentar capturar el target REALITY. Se renombró el parámetro local a `target_name` en las funciones de lectura; la captura REALITY y el resumen quedaron verificados.

`tests/vmess_assistant.sh` cubre avisos, campos del resumen, orden previo al guardado y ausencia de material secreto TLS/REALITY. Pruebas focales `tests/vmess_assistant.sh`, `tests/vmess_model.sh`, `tests/xray_vmess_integration.sh` (14/14 y negativos) y `tests/stage2_navigation.sh` (14/14): PASS. `bash -n` y ShellCheck warning de archivos modificados: PASS. Estado Bloque 2: IMPLEMENTADO, VERIFICADO, PUBLICADO y SINCRONIZADO en `9d03d4b4e77e1a160b94ee2c2f3c74487977e362`. Suite completa se repetirá en Bloque 3.
