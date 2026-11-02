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

### P4 — backup y recuperación segura VLESS (corrección del journal implementada; aceptación pendiente)

El subsistema incluye backup de datos/manifiesto/SHA256SUMS, paquete de recuperación scrypt + AES-256-GCM, verificación, restauración confirmada y menú. La corrección registra `had_connections`/`had_secrets`, fuerza `fsync` de los directorios padres tras renombrados y recupera journals nuevos y legacy de forma conservadora.

`tests/vless_backup_journal_crash_matrix.sh` cubre 32 interrupciones abruptas en fases y renombrados, con las cuatro combinaciones de existencia previa de ambos directorios. `tests/vless_backup_journal.sh` cubre journal legacy y destino originalmente ausente. `tests/vless_backup_restore_secrets.sh` comprueba restore de blobs REALITY/TLS con el certificado TLS externo ausente, dependencia declarada y runtime inactivo. La suite completa final tras esta revisión registró 31/31 PASS; `install.sh --check`, sintaxis Bash, `py_compile`, ShellCheck, shfmt y `git diff --check` PASS. No se creó backup operativo ni se accedió a la clave maestra real.

**P4 sigue ABIERTA:** queda auditar límites agregados de extracción/descompresión, memoria, rutas y permisos de staging/publicación, además de la aceptación formal. Ver `docs/P4_BACKUP_RECUPERACION_VLESS.md`.


## Incidente de pruebas — EOF en menús y crecimiento de /tmp (2026-11-02)

Se investigó una alerta real de disco al 95–99.9%. La auditoría de la VPS encontró un archivo de salida de 20,465,770,496 bytes dentro de `/tmp/tmp.oaFf5wTZwt/connections-action-error.out` y un proceso huérfano que mantenía abierto otro archivo ya eliminado de aproximadamente 925 MB. El proceso se detuvo de forma ordenada y se eliminó únicamente ese directorio temporal, después de verificar que no había handles abiertos. El disco quedó en 3.7 GB usados, 71 GB libres (5%). No se modificaron datos persistentes, configuraciones ni runtime.

Causa técnica confirmada: `ui_read_option()` convertía EOF en una cadena vacía y devolvía éxito. Los menús dentro de `while true` interpretaban esa cadena como opción inválida y volvían a imprimir el menú indefinidamente. Se corrigió el contrato para devolver estado 1 en EOF, limpiar la variable destino y hacer que los consumidores abandonen el menú/flujo actual de forma ordenada. También se protegieron los prompts de identificador del menú de backup VLESS.

La regresión quedó cubierta en `tests/stage1_menu.sh`: EOF directo en menús principales y secundarios, EOF anidado al navegar conexiones, y límite de salida de 1 MiB para que una regresión no vuelva a llenar el disco. La prueba `tests/vless_backup_restore_secrets.sh`, que ya estaba en la VPS sin seguimiento Git, se revisó y ejecutó PASS; se incorpora al repositorio en este cierre.

Resultados ejecutados: suite completa `tests/*.sh` 30/30 PASS; `install.sh --check`, `bash -n` de todos los `.sh`, ShellCheck de módulos y pruebas modificados, `shfmt -d -i 4 tests/stage1_menu.sh` y `git diff --check`: PASS. Los directorios `/tmp/tmp.u7Vq57eHNx` (282 MB) y `/tmp/tmp.EsxO527Ihe` (47 MB) se inspeccionaron; contienen salidas históricas de pruebas de menú V2 con repetición por EOF, pero se conservaron y no se borraron.

El cambio quedó IMPLEMENTADO y VERIFICADO. Publicación confirmada en GitHub, rama `design/user-identity-association-v1`, commit `fa7242a61248a71b64552511d1db932ebbc8d7d0`. El árbol Git remoto `b03db9b450288eccbf61e761655f286763df3a70` coincide exactamente con el árbol del commit local `b520c53bd5a32007b30519e0756fce13fe8916b5`: los 17 archivos y sus modos son idénticos. La VPS no pudo hacer `git push`/`git fetch` por falta de autenticación SSH y HTTPS; por ello los identificadores de commit local/remoto difieren y la referencia local `origin/design/user-identity-association-v1` permanece desactualizada en el commit base anterior. No se debe volver a aplicar el cambio; en una sesión con autenticación Git disponible, reconciliar la referencia local con el HEAD remoto sin duplicar commits.

## 2026-11-02 — autenticación SSH y reconciliación de referencias

Se creó una clave SSH Ed25519 dedicada a este repositorio y se registró en GitHub como Deploy Key de solo lectura (sin permiso de escritura). La VPS autentica correctamente mediante el alias `github.com-xray-core-manager`; la URL `origin` de este checkout usa ese alias y los demás repositorios/configuraciones SSH no se modificaron. `git fetch` se completó correctamente. Se verificó que el árbol local anterior y el árbol remoto eran idénticos (`b6ed32ae1ff32dc4c8c6953a2d1eec48159b1d08`), por lo que se movió únicamente la referencia local de la rama con comprobación del SHA anterior, sin resetear ni sobrescribir archivos. Estado final: `design/user-identity-association-v1` y `origin/design/user-identity-association-v1` apuntan a `5ade7feda328ff4a4f6796fd7ab263237b40dbfa`; working tree limpio y sin divergencia. Las notas anteriores sobre falta de autenticación y refs obsoletas quedan superadas por esta verificación. La clave SSH anterior se conservó intacta. La Deploy Key nueva es de solo lectura; las publicaciones futuras deberán seguir usando el mecanismo autorizado de GitHub API u otro acceso de escritura expresamente configurado.
