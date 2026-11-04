# Protocolo de continuidad — Xray Core Manager

> **Punto de reanudación vigente — 2026-11-03:** almacén de perfiles v1.1 implementado localmente con AES-256-GCM para cifrar el JSON completo de cada revisión. La decisión de texto plano de la primera iteración fue sustituida por elección expresa del propietario (opción 1); la versión plaintext no se publicó. Consultar `docs/DISENO_IMPLEMENTACION_PERFILES.md`, `PROJECT_STATE.md` y el último bloque de este documento. No leer ni modificar `master.key` real, no crear perfiles live, no activar runtime. La regresión integral y la publicación siguen pendientes.

> Los apartados cronológicos antiguos se conservan como historial. Para el estado actual y el punto de reanudación prevalece el bloque «Punto de reanudación posterior a la aceptación del Snapshot Writer v1» al final del documento.

> Frente activo 2026-11-03: aceptación formal del Snapshot Writer v1 con limitaciones documentadas. La corrección A-16 y B-01/B-02/B-03 están publicadas; se añadieron diez negativos A-16 y una matriz de trazabilidad A-01–A-19 en §10.20. Última regresión: 49/49 scripts PASS; AST 16/16; bash -n 74 archivos; ShellCheck, shfmt y diff-check PASS. Writer ACEPTADO FORMALMENTE CON LIMITACIONES DOCUMENTADAS el 2026-11-03. No crear backups reales ni leer secretos/master.key; no restore/verify independiente ni runtime apply. Xray-Normativa inmutable; no tocar VPS de pruebas.
> La aceptación formal y su actualización documental están registradas en la parte final de este archivo. La rama autorizada sigue siendo design/user-identity-association-v1; main y Xray-Normativa permanecen protegidas.


> Registro histórico: la auditoría inicial de almacenes/certificados y el cierre del contrato se documentaron antes del primer bloque. Consultar los dos informes de implementación para el estado vigente.


> **Estado vigente 2026-11-03:** VMess técnicamente preparado para aceptación formal. F-01–F-05 resueltos/verificados; VM-28 verificado; VM-32 verificado con límite transaccional documentado; VM-33 no aplica al alcance aprobado; VM-38/39/40 verificados; suite 40/40 PASS; Xray 14/14 y 16 negativos PASS; VM-46 live PASS; VM-47 cliente-servidor VMess-TLS loopback PASS. Cliente externo/WAN no probado y no requerido por el diseño. VM-48 requiere decisión expresa del propietario; VMess NO está aún aceptado y Etapa 2 permanece ABIERTA. Leer primero docs/PUNTO_CONTROL_ACTUAL.md, docs/AUDITORIA_INTEGRAL_VMESS_2026-11-02.md, docs/MATRIZ_TRAZABILIDAD_VMESS_2026-11-02.md y docs/VALIDACION_CLIENTE_SERVIDOR_VMESS_VM47_2026-11-02.md. No iniciar Trojan.


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
- Documentación normativa canónica versionada: `/opt/xray-manager/Xray-Normativa` (en GitHub: `Xray-Normativa/`).
- Copia maestra de respaldo en la VPS: `/root/Xray_Manager_Documentacion_Final_2026-10-31`.
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
6. `Xray-Normativa/` y los documentos técnicos específicos de la etapa que se vaya a trabajar.
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
- Leer la documentación normativa en `Xray-Normativa/`; comparar sus SHA-256 con la copia de respaldo `/root/Xray_Manager_Documentacion_Final_2026-10-31`.

### Contraste
- Comparar archivos por contenido y SHA-256 cuando sea posible.
- Separar coincidencias, divergencias, archivos solo locales y archivos solo remotos.
- No corregir diferencias automáticamente.
- No asumir que una diferencia de hash con texto aparentemente igual carece de importancia; revisar bytes, codificación, saltos de línea y final de archivo.
- Identificar cualquier cambio no publicado o no sincronizado.

## 4.1 Contraste normativo obligatorio antes de implementar

Antes de iniciar cualquier etapa o tarea de implementación, consulta directamente la documentación preliminar aprobada en `Xray-Normativa/` del repositorio y contrástala punto por punto con el estado real de GitHub, la VPS, el código, los catálogos, las pruebas y la documentación técnica. Presenta el informe de conformidad, omisiones y divergencias antes de editar.

Las mejoras son posibles, pero toda mejora o cambio respecto del alcance aprobado debe justificarse, describir sus impactos y alternativas, y recibir autorización expresa del propietario antes de modificar diseño o código. No infieras autorización por silencio, continuidad de la conversación ni aprobaciones anteriores de otras tareas. Si la fuente no está disponible o existe una contradicción relevante, detente y solicita aclaración.

Procedimiento completo y vinculante: `docs/REGLA_CONTRASTE_DOCUMENTACION_PRELIMINAR.md`. Esta regla complementa AGENTS.md y es de cumplimiento obligatorio para cualquier IA o colaborador.


## 4.2 Custodia inmutable de Xray-Normativa

La carpeta `Xray-Normativa/` contiene la documentación maestra normativa aprobada. **Está prohibido modificar, corregir, reformatear, renombrar, mover, eliminar o sustituir cualquiera de sus archivos sin consentimiento previo, explícito y específico del propietario.** La autorización para implementar o publicar código no incluye autorización para alterar la normativa. Ante errores, ambigüedades o mejoras, conservar los originales y presentar una propuesta separada; esperar consentimiento expreso. Toda modificación autorizada debe quedar justificada y registrada en `HISTORY.md`.

Antes de iniciar cada etapa, subetapa o módulo, se debe contrastar su alcance punto por punto con `Xray-Normativa/`, identificar conformidades, ausencias, divergencias y decisiones pendientes, y presentar el resultado antes de editar o implementar. La copia `/root/Xray_Manager_Documentacion_Final_2026-10-31` se conserva en la VPS como respaldo; comprobar sus hashes frente a la carpeta versionada cuando esté disponible. Si hay diferencias, no resolverlas automáticamente: informar y solicitar decisión.

## 4.3 Auditoría integral obligatoria antes de cerrar cualquier etapa

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

El diseño VMess y su implementación fueron autorizados por el propietario, incluyendo HTTPUpgrade-TLS. El trabajo local en `/opt/xray-manager` contiene modelo, adaptador Xray-core 26.10.31, asistente, preparación de configuración, almacén cifrado y pruebas. La matriz de 14 modalidades pasó `xray run -test`; suite completa histórica: 36/36 PASS (la reejecución actual del 2026-11-02 fue 38/38; ver informe vigente). También pasaron `bash -n`, `py_compile`, ShellCheck a nivel warning, shfmt de archivos VMess nuevos, `install.sh --check` y `git diff --check`. Los cambios están publicados y sincronizados en la rama autorizada, pero no aceptados como módulo completo; consultar `docs/PUNTO_CONTROL_ACTUAL.md`.

### Separación del almacenamiento VMess

La persistencia VMess se ubica en `/var/lib/xray-manager/vmess/`, con `configurations/` y `secrets/` privados. El catálogo común continúa en `/var/lib/xray-manager/connections/connections.json`, pero VMess solo usa `vmess_configuration_ref`, `vmess_secret_ref`, `vmess_configuration_revision` y `vmess_configuration_schema_version`. No cambiar los campos VLESS ni `scripts/vless_backup.py` como parte de esta tarea. El bloqueo de integridad continúa compartido para serializar escrituras del catálogo.

P4 VLESS no incluye el almacén VMess separado. La restauración VLESS ahora combina las entradas VLESS del backup con las entradas VMess vigentes y valida sus referencias; los archivos del almacén VMess permanecen intactos. Esta corrección posterior se documenta en la sección 9 de `docs/P4_BACKUP_RECUPERACION_VLESS.md`. Backup/restore VMess independiente debe diseñarse y aprobarse por separado.

Los usuarios VMess todavía se introducen manualmente; la asociación con identidades globales pertenece a Etapa 3 y no debe implementarse dentro de esta tarea sin su definición/autorización.

### Estado de publicación

La implementación VMess y el aislamiento fueron publicados tras autorización expresa: commit `c20277c04b9417f2e22b285891fb3f348ea8e8f4` en `design/user-identity-association-v1`. La Deploy Key SSH de la VPS es de solo lectura; la publicación se efectuó mediante GitHub API y luego la VPS hizo fetch/reset para igualar HEAD local/remoto. No se modificó la rama `main`. No tocar runtime, firewall, puertos ni servicio. La Etapa 2 continúa abierta.

## Cierre técnico VMess — 2026-11-02

La auditoría de cierre contrastó el módulo con la especificación funcional Etapa 2 revisión 1.3 y con el diseño aprobado en `docs/DISEÑO_TECNICO_VMESS.md`. El módulo VMess quedó IMPLEMENTADO y VERIFICADO según la auditoría histórica de esa fecha. Este estado histórico fue revisado por la auditoría integral del 2026-11-02, que detectó F-01–F-04 y F-05 live no verificado; consultar la actualización vigente al final de este documento y los informes de auditoría.

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


## 2026-11-02 — Bloque 3: cobertura de pruebas VMess

Se amplió `tests/vmess_assistant.sh` para probar cancelación y EOF en dirección/UUID/path/confirmación, slots inválidos, UUID inválido/duplicado, puerto inválido y modalidad incompatible. Se verifica que las entradas fallidas y la cancelación después del resumen no alteran el catálogo.

Se creó `tests/vmess_persistence_hardening.sh`: store/read TLS AES-256-GCM y AAD; permisos; clave maestra ausente sin regeneración en read; clave inválida en read/store; ciphertext/tag alterado sin plaintext; referencias de configuración y secreto rotas; huérfanos; symlinks; fallos antes de publicar el catálogo; y concurrencia de escritores con IDs distintos y misma conexión/revisiones r1-r2.

La prueba de fallo inyectado confirma que una interrupción después de escribir archivos y antes de publicar el catálogo deja huérfanos detectables, mientras el catálogo permanece intacto. No hay rollback transaccional VMess en el diseño aprobado; `audit` detecta los huérfanos y no los borra automáticamente. No se modificó código de producción en este bloque. La rama autorizada y la VPS quedaron sincronizadas en `08b2044dd820eb465afecbb6ec66fccefe6397a5`; la rama `main` no fue modificada.

Suite completa `tests/*.sh`: 38/38 PASS. También PASS: `python3 -m py_compile scripts/*.py`, `bash -n` de todos los scripts Bash, `install.sh --check`, ShellCheck warning de los archivos modificados y `git diff --check`. Estado Bloque 3: IMPLEMENTADO, VERIFICADO, PUBLICADO y SINCRONIZADO en `08b2044dd820eb465afecbb6ec66fccefe6397a5`.


## 2026-11-02 — Bloque 4: etiquetas explícitas de modalidades VMess

Se actualizó `modules/connections.sh`: VMess-WS se muestra como `VMess-WS (sin TLS adicional)` y VMess-TLS como `VMess-TLS (RAW/TCP + TLS)`, tanto en el menú como en `connections_mode_label` usado por listados. No se cambiaron IDs, modalidades ni el orden. `tests/stage2_navigation.sh` comprueba las etiquetas y conserva las verificaciones de las 14 combinaciones.

Se confirmó que `README.md` define `shfmt -d -i 4 -ci` para archivos Bash seleccionados. No se reformateó el árbol: la aplicación general generaría diffs ajenos al alcance y el proyecto no declara una política para reformateo global. La regla permanece limitada a los archivos explicitados en README.

Cambios implementados y verificados: pruebas focales y suite completa 38/38 PASS; controles estáticos y shfmt baseline PASS. Auditoría integral de VMess pendiente. Cambios publicados y sincronizados en `9528f4b00f6b9654f7236050bbadfd8f9415bf69`.

Publicación Bloque 4: commit `9528f4b00f6b9654f7236050bbadfd8f9415bf69`; HEAD local/remoto y árboles verificados idénticos. `main` no fue modificada.


## Auditoría integral VMess — 2026-11-02 (hallazgos iniciales; superados por el bloque correctivo posterior)

El informe vigente y la matriz requisito→diseño→implementación→prueba→evidencia son docs/AUDITORIA_INTEGRAL_VMESS_2026-11-02.md y docs/MATRIZ_TRAZABILIDAD_VMESS_2026-11-02.md. La suite actual pasó 38/38; Xray validó 14/14 y rechazó 10 casos negativos. Sintaxis Bash, AST Python, ShellCheck, install check, diff check y el gate shfmt definido en README pasaron.

Hallazgos pendientes: F-01 la clave TLS root-owned 0644 se acepta; F-02 read/audit no detectan incoherencia de revisión/schema; F-03 cancelar el asistente deja el registro base draft creado previamente; F-04 el modelo acepta email duplicado que el almacén rechaza; F-05 el estado live no se ha inicializado (catálogo vacío, almacén VMess y master key ausentes). No se corrigió código. Solicitar autorización antes de modificar.

Auditoría y matriz publicadas/sincronizadas en commit 88f82f2f9d7d19833b814d9a810dedb4bc3edc8c de la rama autorizada; main no modificada. scripts/__pycache__/ permanece sin seguimiento y no se eliminó.


## Bloque correctivo VMess F-01 a F-04 — 2026-11-02

F-01 exige clave TLS root:root 0600 y un solo enlace duro en adaptador/preparador; negativos 0644/0640/0400, grupo no root y hardlink, positivo 0600. F-02 valida revisión de catálogo/referencia, schema catálogo/documento y revisión de referencia secreta en store/read/audit, y detecta metadatos parciales. F-03 cancela con estado no exitoso y el flujo común retira sólo el draft VMess vacío/no aplicado bajo bloqueo; preserva otras entradas y configuraciones ya publicadas. F-04 modelo/adaptador/almacén rechazan emails duplicados con comparación exacta consistente.

Suite 39/39 PASS; Xray 14/14 modalidades y 16/16 negativos PASS. bash -n, py_compile, ShellCheck de archivos modificados, install.sh --check, gate shfmt README y git diff --check PASS. ShellCheck global informa warning preexistente SC2174 en tests/vless_backup_restore.sh:7, archivo VLESS sin cambios.

Corrección de código publicada en d2d33a32bdf5e21d1d35ad41d00bd0b116443cb7; actualización final de continuidad sincronizada en 0a39af5c2aa35bf853c05f3a864bcc362d86bf67. F-05 live permanece NO VERIFICADO: catálogo vacío, almacén VMess y clave maestra no inicializados. No se tocó runtime, firewall, puertos ni servicio. VMess no está aceptado; Etapa 2 abierta. Requiere autorización separada validar live y completar VM-38/39/40.


## Revalidación controlada — 2026-11-02

La VPS de desarrollo `/opt/xray-manager` fue confirmada accesible como root, en la rama autorizada y HEAD `4c87557e0aff4166c540c633effe5cb6dac40096`. Se añadió `tests/vmess_navigation_edge_cases.sh`; VM-38 lista vacía/[0], VM-39 entradas inválidas recuperables y VM-40 confirmación destructiva exacta pasan. Suite completa `tests/*.sh`: 40/40 PASS. La primera ejecución parcial de `port_collisions.sh` falló en la comprobación UDP; la repetición aislada y la suite completa posterior pasaron.

F-05 live queda pendiente de autorización específica para crear clave maestra y almacén VMess persistentes en esta VPS de desarrollo. No se crearon, ni se añadió conexión live. Xray no está instalado localmente; las pruebas de integración utilizaron el binario de validación 26.10.31 en caché. Servicio inactivo; no se tocaron runtime, firewall, puertos ni servicios.


## Validación live F-05 — 2026-11-02

El propietario autorizó la inicialización persistente controlada en la VPS de desarrollo. F-05/VM-46 quedó VERIFICADO LIVE: clave maestra compartida generada con 32 bytes `root:root 0600`; almacén VMess creado con directorios `root:root 0700`; borrador VMess-TLS guardado, leído/descifrado, recuperado por el asistente y validado con Xray 26.10.31. Auditoría limpia y alteración GCM rechazada sin plaintext. La conexión temporal y sus dos archivos versionados fueron retirados; catálogo vacío. Se conservan clave maestra y directorios VMess vacíos como estado inicial. Sin activación de runtime, cambios de firewall/puertos/servicios ni certificado desplegado. VM-47 conectividad cliente-servidor sigue NO VERIFICADA. Detalle: `docs/VALIDACION_LIVE_VMESS_F05_2026-11-02.md`.


## Validación cliente-servidor VM-47 — 2026-11-02

VM-47 quedó verificado en loopback local. El modelo y adaptador reales generaron la configuración VMess-TLS del servidor; un cliente Xray SOCKS estableció el túnel TLS/VMess y una solicitud HTTP llegó al destino, que respondió HTTP 200 con el marcador esperado. Configuraciones cliente y servidor `xray run -test`: PASS. Los procesos y listeners temporales se detuvieron. No se tocaron runtime, firewall, puertos públicos, catálogo ni servicio. No se probó cliente externo/WAN. Informe: `docs/VALIDACION_CLIENTE_SERVIDOR_VMESS_VM47_2026-11-02.md`.


## 2026-11-03 — Revalidación y punto de reanudación VMess

La revalidación se ejecutó en `/opt/xray-manager` sobre `design/user-identity-association-v1`. Suite completa `tests/*.sh`: 40/40 PASS; Xray 26.10.31: 14/14 modalidades y 16/16 casos negativos PASS. También pasaron `bash -n` para los archivos Bash VMess, `py_compile` para `vmess_config_store.py` y `vmess_prepare_config.py`, ShellCheck de módulos/pruebas VMess y `git diff --check`.

Se documentaron con supresión local SC2034 tres variables globales intencionales en `tests/vmess_creation_flow.sh` y `tests/vmess_navigation_edge_cases.sh`, consumidas dinámicamente por funciones de `modules/connections.sh` cargado con `source`; se conservaron las asignaciones. La matriz y auditoría aclaran VM-28 como VERIFICADO, VM-32 como atomicidad individual/concurrencia con límite multiarchivo y VM-33 como no aplicable porque el diseño no promete rollback transaccional.

La documentación normativa `Xray-Normativa/` se comparó con el respaldo `/root/Xray_Manager_Documentacion_Final_2026-10-31`: 14 archivos originales coincidentes; no se modificó ninguno. No se tocó runtime, firewall, puertos, certificados desplegados ni servicio.

**Punto exacto de reanudación:** expediente técnico VMess listo para que el propietario emita o deniegue la aceptación formal VM-48. Cliente externo/WAN no probado y no requerido por el diseño aprobado. Etapa 2 permanece ABIERTA; no iniciar Trojan antes de la aceptación formal de VMess y del contraste normativo específico de Trojan.


## 2026-11-03 — Punto de reanudación: integración VMess TLS centralizado parcial

La integración del Bloque 3 comenzó y se publicó como avance intermedio; no se debe confundir con su cierre. Consultar primero `docs/IMPLEMENTACION_VMESS_TLS_CENTRALIZADO_PARCIAL.md`.

- `scripts/vmess_config_store.py`: nuevas revisiones TLS guardan sólo `certificate_id`, exigen certificado central existente/activo y no crean secretos TLS por conexión. REALITY conserva su secreto individual.
- TLS histórico `{certificate_file, secret_ref}` sigue siendo legible para compatibilidad, sin migración ni borrado automático. Nuevas revisiones TLS deben usar el formato central.
- `scripts/vmess_prepare_config.py` emite el contrato TLS central; `scripts/vless_backup.py` conserva la lectura/validación de VMess TLS histórico al restaurar VLESS.
- `modules/vmess_assistant.sh` tiene adaptación preliminar para seleccionar ID central y pedir lease. El flujo interactivo TLS no tiene todavía cobertura integral y no debe considerarse terminado.
- `modules/vmess_xray_26_10_31.sh` aún requiere adaptación/endurecimiento para impedir rutas TLS arbitrarias y consumir sólo leases del resolutor.
- Pruebas focales: persistencia VMess, restauración VLESS preservando VMess, almacén central, resolutor, modelo, creación y aislamiento backup PASS. Sintaxis/compilación y `git diff --check` PASS. La suite global no se ha reejecutado tras este cambio.
- En VPS desarrollo no existe unidad/cuenta/grupo Xray; CLI real del resolutor falla cerrada. No se ha probado lectura de lease por Xray real.
- No se migraron históricos, no se importaron certificados reales, no se modificó runtime/servicios/firewall/puertos, no se tocó VPS de pruebas ni `Xray-Normativa/`.

**Siguiente paso exacto:** adaptar el generador VMess Xray al lease autorizado, después completar y probar asistente/recuperación/cleanup y backup/restore, ejecutar regresión integral y actualizar trazabilidad. No declarar Bloque 3 completado hasta cubrir todo lo anterior.


## 2026-11-03 — Continuidad: VMess TLS centralizado, avance posterior al commit 8d3b848

**Rama de trabajo:** `design/user-identity-association-v1`. El último commit remoto sigue siendo `8d3b848` hasta que el propietario autorice publicar esta actualización. No repetir el análisis de persistencia TLS central ya documentado; continuar desde el endurecimiento del adaptador y el asistente descrito aquí.

- `modules/vmess_xray_26_10_31.sh` ahora requiere `lease-id` como tercer argumento. En TLS sólo acepta `certificate.pem` y `private-key.pem` dentro del lease exacto, con manifiesto válido para `connection_id`, `protocol=vmess`, `certificate_id`, revisión, fingerprint y UID/GID. Rechaza rutas externas y leases reutilizados para otra conexión. Los archivos deben ser root:<grupo-servicio> 0640, el directorio del lease 0750.
- Nuevo `scripts/vmess_tls_lease_check.py` implementa la comprobación estructural del lease antes de construir JSON Xray.
- `modules/vmess_assistant.sh` pasa `--runtime-root` explícito tanto en creación como en recuperación; el `read` de VMess usa el catálogo central correcto. El ciclo limpia lease en éxito y fallo mediante trap. La recuperación de TLS histórico `{certificate_file, secret_ref}` falla cerrada y requiere migración controlada; la lectura histórica del store se mantiene.
- `scripts/vless_backup.py` verifica que un VMess TLS central preservado durante restore VLESS apunte a un recurso `managed`/`reference` activo en `certificates/catalog.json`. No copia ni modifica el almacén VMess ni el catálogo central.
- Tests nuevos/ampliados: `tests/vmess_tls_lease_assistant.sh`, `tests/xray_vmess_integration.sh`, `tests/vless_restore_preserves_vmess.sh`.
- Verificación: `tests/*.sh` 43/43 PASS; Xray 26.10.31 valida 14/14 modalidades usando fixtures de lease; el ciclo de recuperación/cleanup usa resolutor y Xray simulados; ShellCheck warning, Bash syntax, py_compile y `git diff --check` PASS.

**Límites importantes:** el CLI real del resolutor continúa fallando cerrado porque la VPS de desarrollo no tiene `xray.service` ni usuario/grupo Xray. No se demostró lectura de lease por Xray real. No hubo runtime apply ni despliegue. El backup VLESS sigue excluyendo VMess y el catálogo central; backup/restore compartido e independiente VMess continúan pendientes del bloque específico. Integración VLESS del resolutor sigue pendiente. No se migraron TLS históricos, no se importaron certificados reales y no se tocó la VPS de pruebas, firewall, puertos, servicios ni `Xray-Normativa/`.

**Estado:** IMPLEMENTADO PARCIALMENTE, VERIFICADO EN FIXTURES, NO PUBLICADO, NO SINCRONIZADO, NO ACEPTADO. `main` y `Xray-Normativa/` permanecen intactas.

**Siguiente paso:** completar la revisión de todos los caminos de persistencia/backup afectados y decidir el siguiente bloque de integración VLESS; antes de afirmar operatividad TLS real, disponer de una unidad Xray de desarrollo con identidad no privilegiada verificable y probar prepare → lectura real por Xray → cleanup. No tocar runtime de producción ni la VPS de pruebas sin autorización específica.


## 2026-11-03 — Integración VLESS TLS centralizado parcial

Se retomó el acceso a `/opt/xray-manager`; la VPS responde y permanece en `design/user-identity-association-v1`, HEAD `8d3b8482da369e902b32795dc3a36e5023d25e62`. Los cambios locales VMess anteriores se conservaron. La integración VLESS se realizó sobre los archivos vigentes, tras auditoría y contraste con `Xray-Normativa/02_Protocolos_Conexiones/Etapa_2_Protocolos.md` y YAML; `Xray-Normativa/` no se modificó.

- Nuevas revisiones TLS VLESS guardan sólo `certificate_id` y validan recurso central activo `managed`/`reference`; no generan secreto TLS por conexión. Lectura/auditoría admiten revisiones TLS históricas sin migrarlas ni borrarlas. REALITY mantiene secreto individual.
- `vless_prepare_config.py` emite el contrato central. El adaptador `vless_xray_26_10_31.sh` exige lease autorizado para TLS y rechaza rutas libres; `vless_tls_lease_check.py` valida manifest, conexión/protocolo, certificado/revisión/fingerprint, UID/GID y permisos.
- El asistente solicita ID central, persiste el borrador bajo confirmación, solicita lease y limpia en éxito/fallo. Restore central también usa lease; TLS histórico falla cerrado hasta migración.
- Backup/restore VLESS documenta dependencia central y rechaza restaurar si falta el catálogo o el recurso activo. No incorpora el almacén central ni sus secretos al backup VLESS.
- Se añadieron `tests/vless_tls_central_backup.sh` y `tests/vless_tls_lease_assistant.sh`, y se ampliaron pruebas de store, asistente y Xray. Suite global `tests/*.sh`: 45/45 PASS. Xray 26.10.31 aceptó 9/9 modalidades VLESS con fixtures. La prueba del asistente simula `systemctl`/Xray y verifica lectura POSIX por `www-data` más cleanup en éxito/fallo; no prueba un Xray real. Bash syntax global, py_compile, install check, ShellCheck warning de modificados y diff check PASS.

**Límite bloqueante:** la VPS de desarrollo no tiene una unidad Xray con `User`/`Group` explícitos y no privilegiados. El CLI del resolutor falla cerrado; el asistente guarda el borrador y no aplica runtime. No se probó lectura del lease por Xray real. No se tocaron runtime, servicio, firewall, puertos, certificados desplegados, VPS de pruebas ni normativa.

**Estado:** VLESS TLS central IMPLEMENTADO PARCIALMENTE y VERIFICADO EN FIXTURES; NO PUBLICADO, NO SINCRONIZADO, NO ACEPTADO. `main` intacta. No se ha autorizado commit/push. Informe: `docs/IMPLEMENTACION_VLESS_TLS_CENTRALIZADO_PARCIAL.md`.

**Siguiente paso exacto:** ampliar la matriz integrada de recuperación/cleanup para WS, gRPC y XHTTP TLS; después diseñar migración histórica versionada y backup/restore central compartido. Mantener REALITY separado y no tocar runtime sin autorización específica.


## 2026-11-03 — Matriz VLESS TLS, auditoría cruzada y diseños pendientes

Se amplió `tests/vless_tls_lease_assistant.sh`: además de creación RAW/TCP y cleanup tras éxito/fallo del Xray simulado, se ejecuta recuperación de las cuatro modalidades TLS (RAW/TCP, WS, gRPC y XHTTP), comprobando limpieza del lease tras cada recuperación. Durante esa prueba se encontró y corrigió un rechazo incorrecto de `path` en el adaptador `vless_ws_tls`; el adaptador ahora valida opciones exactas por modalidad. `tests/xray_vless_integration.sh` vuelve a validar WS-TLS con su path.

Auditoría cruzada VMess/VLESS: validadores de lease equivalentes salvo el protocolo declarado en manifest. Se alinearon las dos llamadas de preparación del asistente VMess para proporcionar rutas explícitas configurables de almacén central, catálogo, managed dir, secretos, lock y master key, en vez de depender parcialmente de defaults. Suite global final `tests/*.sh`: 45/45 PASS.

Se redactaron dos propuestas sin ejecutar: `docs/PLAN_MIGRACION_TLS_HISTORICO.md` (inventario de solo lectura, validación de pares/fingerprints, deduplicación, importación central, nuevas revisiones inmutables, journal y rollback) y `docs/PLAN_BACKUP_RESTORE_CENTRAL.md` (snapshot coordinado VLESS/VMess/certificados, dependencias reference, envoltura de secretos centrales y restore/rollback). Ambas están marcadas como propuestas no aprobadas.

No se migraron revisiones históricas, no se eliminó ningún blob, no se creó el backup compartido, no se modificó runtime, servicios, firewall, puertos, certificados desplegados, VPS de pruebas ni `Xray-Normativa/`. Sin commit ni push.


## 2026-11-03 — Continuidad: aprobación de migración histórica y backup compartido; preflight inicial

**Rama autorizada:** `design/user-identity-association-v1`. **HEAD de partida sincronizado:** `cd5095514f4a08bc2feca26d29f1fbdc3302db39`. GitHub y VPS estaban alineados antes de este trabajo. `Xray-Normativa/` permanece intacta.

El propietario aprobó los criterios de ambos bloques:

- Migración TLS histórica: VMess y VLESS; `managed` por defecto; `reference` sólo con confirmación expresa; certificados vencidos/no vigentes bloqueados; conservar revisiones y blobs históricos; backup verificable y autorización específica antes de cualquier lote real.
- Backup/restore compartido: reenvolver secretos con cifrado propio del backup y re-cifrarlos bajo la master key existente del destino; no incluir `master.key`; bloquear restore completo si faltan referencias externas; no sobrescribir datos posteriores al snapshot ni realizar merge automático ante conflictos.

**Implementación de migración:** nuevo `scripts/certificate_migration.py`, comando `plan --protocol all|vless|vmess`. Es estrictamente read-only: no crea locks/directorios, no importa certificados, no crea revisiones ni journals y no modifica stores. Valida las referencias/revisiones, permisos y archivos; usa el backend criptográfico específico VLESS o VMess; comprueba PEM, par, vigencia y fingerprints; agrupa pares duplicados y emite `READY`, `BLOCKED` o `ALREADY_CENTRAL`. Si existe el lock de integridad lo toma compartido y revalida hashes de entradas, incluyendo master key, antes de cerrar el plan. No muestra ni persiste claves descifradas.

Prueba nueva `tests/certificate_migration_plan.sh`: fixtures VLESS/VMess, sobres criptográficos diferentes, deduplicación cruzada, no escritura y ciphertext alterado bloqueado. Regresión completa: 46/46 archivos de prueba PASS; Bash syntax, `py_compile`, ShellCheck de prueba nueva y `git diff --check` PASS.

**Inventario real VPS implementación:** `/var/lib/xray-manager/connections/connections.json` contiene 0 registros; preflight `--protocol all` devuelve 0 candidatos TLS, 0 READY, 0 BLOCKED y 0 ALREADY_CENTRAL. La carpeta de configuración VLESS y el catálogo central TLS no existen actualmente; el preflight no los creó. No hay migración real.

**Hallazgo backup crítico:** `scripts/vless_backup.py backup-data` genera `tar.gz` y manifiesto con hashes; el tar no está cifrado integralmente. Los blobs de secretos sí están cifrados bajo la master key del host. `create-recovery` cifra la master key separadamente mediante scrypt + AES-256-GCM. Por tanto, el backup compartido necesita un contenedor cifrado integral nuevo; no debe describirse el backup VLESS actual como ya cifrado. El diseño v1.1 de `docs/PLAN_BACKUP_RESTORE_CENTRAL.md` define paquete compartido independiente, scrypt + AES-256-GCM y re-cifrado de secretos bajo la master key destino, sin escribir plaintext en staging.

Documentos actualizados: `docs/PLAN_MIGRACION_TLS_HISTORICO.md` v1.1, `docs/PLAN_BACKUP_RESTORE_CENTRAL.md` v1.1 y nuevo `docs/IMPLEMENTACION_PREFLIGHT_MIGRACION_TLS.md`.

**Pendiente:** implementar y probar backup/restore compartido; completar fase escritora de migración (importación idempotente, nuevas revisiones, publicación, journal, verify y rollback). Ningún certificado histórico fue migrado ni se creó backup compartido.

**Límites:** no se tocó runtime, servicio, firewall, puertos, certificados desplegados, VPS de pruebas ni `Xray-Normativa/`. No commit/push aún para este avance; `main` no se modificó. `scripts/__pycache__/` continúa no rastreado y excluido.

**Siguiente punto exacto:** terminar el contrato de backup compartido, especialmente el cifrado integral, reconstrucción de envelopes VLESS/VMess/certificados y preflight de conflictos, antes de habilitar la migración escritora.


## Publicación del preflight de migración TLS — 2026-11-03

El bloque anterior quedó publicado y sincronizado en GitHub y VPS de implementación: commit `631d7eda11615b692557a2e0958a8f318b81c223` (`feat(tls): add read-only historical migration preflight`), rama `design/user-identity-association-v1`. `origin/main` permanece en `656ecedc506a94a6461aee296b20871d51a38bf3`. El commit no contiene cambios en `Xray-Normativa/`; `git diff HEAD^ HEAD -- Xray-Normativa/` está vacío. `scripts/__pycache__/` permanece no rastreado y excluido.


## Continuidad — formato cifrado compartido v1 (2026-11-03)

El contenedor neutral se implementó en `scripts/shared_backup_format.py`; contrato detallado en `docs/FORMATO_CIFRADO_COMPARTIDO_V1.md` y plan actualizado en `docs/PLAN_BACKUP_RESTORE_CENTRAL.md` v1.2.

El módulo sólo cifra/descifra bytes opacos y no conoce protocolos ni escribe archivos. Usa scrypt fijo `N=2^15/r=8/p=1`, AES-256-GCM, salt 16 bytes, nonce 12 bytes, tag 16 bytes y AAD que autentica cabecera completa. El payload máximo es 512 MiB. La contraseña no se persiste ni se pasa por CLI.

**Compatibilidad futura:** VLESS, VMess, Trojan y otros protocolos pueden transportar su snapshot por el mismo contenedor. Cada protocolo debe tener un adaptador de snapshot/validación y usar su backend/AAD nativo para re-envolver secretos bajo la master key destino. No reutilizar sobres entre protocolos.

**Restricción normativa:** credenciales y claves privadas excluidas por defecto; incluir requiere selección, autorización y confirmación adicional. Historiales, validaciones, informes y logs excluidos. La futura UI/orquestación deberá hacer cumplir estas reglas.

**Verificación actual:** 47/47 `tests/*.sh` PASS; `py_compile scripts/*.py`, `bash -n` de shell modules/scripts, ShellCheck warning y shfmt focal, `git diff --check` PASS. No se ha generado un backup real ni se ha implementado snapshot/restore. No hubo cambios en runtime, servicios, firewall, puertos, master key, datos persistentes ni `Xray-Normativa/`.

**Siguiente punto:** definir el manifiesto interno y el snapshot lógico de datos actuales, resolver orden global de locks y diseñar adaptadores por protocolo antes de implementar el writer.


**Publicación del contenedor v1:** commit `164f91f9c9be8ab275da0b28a53b2314a636f1e2` en `design/user-identity-association-v1`; HEAD local/remoto coincide. Sin cambios a `Xray-Normativa/` ni `main`.

## Continuidad — política de metadatos VMess para backup compartido (2026-11-03)

La decisión del propietario queda registrada en docs/PLAN_BACKUP_RESTORE_CENTRAL.md §10.1 (v1.3):

- Excluir el UUID VMess por defecto porque es una credencial de autenticación.
- Conservar email y level como metadatos/configuración dentro del payload cifrado. email no autentica ni es necesario para el cliente externo.
- No exponer email en el manifiesto externo ni en logs.
- Marcar los registros sin UUID como incompletos/no restaurables íntegramente hasta que la credencial se aporte mediante flujo autorizado. Incluir UUID exige selección, autorización y confirmación adicional.

No se ha cambiado el esquema VMess ni se ha creado snapshot/backup real. Esta nota describe el estado previo a la aprobación posterior del manifiesto, formato ZIP/JSON y contrato técnico del writer; consultar las actualizaciones de continuidad posteriores para el estado vigente.

## Continuidad — lock TLS en desinstalación (2026-11-03)

Se implementó localmente la coordinación de modules/uninstall.sh con catalog.lock cuando la desinstalación incluye certificados. Orden del flujo: lifecycle.lock → uninstall.lock → integrity.lock → catalog.lock (sólo si aplica) → bloqueo Xray. La adquisición es no bloqueante; si falla, se aborta sin crear backup ni eliminar rutas. Si se adquiere, se mantiene durante confirmación, respaldo y eliminación, y se libera en retorno.

tests/uninstall.sh prueba que el lock ocupado impide la operación y que, durante la confirmación de eliminación de certificados, otro adquirente no puede tomar catalog.lock. La suite completa tests/*.sh, Bash syntax, ShellCheck del módulo modificado, py_compile y git diff check pasaron.

La auditoría estática de locks descrita en esta nota fue completada posteriormente para los puntos localizados; no equivale a stress test exhaustivo. El contrato de manifiesto, snapshot y writer se aprobó después. Consultar la actualización de aprobación del contrato técnico al final de este documento.

## Continuidad — ubicación estable de catalog.lock (2026-11-03)

Se corrigió una segunda condición necesaria para que el lock de desinstalación sea efectivo: el archivo no puede vivir dentro del directorio que se elimina. Default único actualizado a /run/xray-manager-certificate-locks/catalog.lock, fuera de /var/lib/xray-manager. certificate_store.py crea/valida el directorio padre root-only; certificate_resolver.py utiliza el mismo acquire_lock. uninstall.sh prepara el padre como root:root 0700 y comprueba ese modo antes de tomar el lock.

Defaults CLI, paths centrales, asistentes VLESS/VMess, desinstalación y docs quedaron alineados. tests/certificate_store.sh valida defaults de ambos CLI; tests/uninstall.sh valida contención del lock y supervivencia fuera del árbol borrado. La suite completa debe volver a ejecutarse tras estos cambios.

No se movió ni eliminó ningún lock real, no se aplicó runtime ni se tocaron datos persistentes. La auditoría global de todos los mutadores sigue abierta.

## Continuidad — auditoría estática de locks (2026-11-03)

Se completó el inventario estático de puntos de adquisición localizados en scripts, modules, lib, config e install.sh. No se encontró ciclo/inversión en los caminos inspeccionados. El orden recomendado para el snapshot compartido es lifecycle → integrity → catalog, liberando en orden inverso. El writer deberá usar locks no bloqueantes con timeout finito; los stores Python actuales son bloqueantes y no deben copiarse sin límite.

La desinstalación ahora coordina catalog.lock cuando elimina certificados. El lock vive fuera del árbol de datos, en /run/xray-manager-certificate-locks/catalog.lock, con padre root:root 0700. Pruebas cubren contención lifecycle/integrity/catalog/Xray, retención durante confirmación, liberación si Xray está ocupado y supervivencia al borrado del árbol. Suite 47/47 PASS y verificaciones estáticas PASS.

La auditoría estática no sustituye pruebas de estrés exhaustivas. El cambio de ruta requiere despliegue con procesos de versión anterior detenidos; no se movió el lock antiguo ni se ejecutó runtime apply.


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


## 2026-11-03 — Aprobación de formato lógico ZIP/JSON v1

El propietario aprobó ZIP con `ZIP_STORED`, `manifest.json` e `index.json`, validación estricta de paths/tipos/duplicados/miembros indexados/tamaño/SHA-256. Límite total ZIP: 512 MiB. Canonicalización JSON propia: UTF-8 estricto sin BOM, claves ordenadas lexicográficamente, separadores compactos, sin duplicados, floats ni valores no finitos, enteros interoperables y comparación byte-a-byte con serialización canónica. No se declara RFC 8785/JCS. Máximo de entradas ZIP aprobado: 10.000 en total (incluye `manifest.json` e `index.json`; hasta 9.998 miembros de datos).

El plan es v1.9. No existe writer, verify, restore ni paquete real; esta aprobación no autoriza su implementación ni runtime apply. `Xray-Normativa/` permanece intacta.


## 2026-11-03 — Máximo de entradas ZIP aprobado

Se aprobó el límite estricto de 10.000 entradas ZIP totales (incluye `manifest.json` e `index.json`), por lo que caben hasta 9.998 miembros de datos. Si se supera, writer/preflight aborta sin publicar paquete parcial y verify/lector rechaza el paquete. El plan pasa a v1.10. Esta decisión cierra el límite de miembros, pero no autoriza writer, verify, restore ni paquetes reales.


## 2026-11-03 — Aprobación del contrato técnico del snapshot writer v1

El propietario aprobó el contrato técnico del snapshot writer compartido v1 y la ampliación de cifrado incremental compatible con el contenedor criptográfico v1. Se congelan: secuencia fail-closed; locks `lifecycle → integrity → catalog`, adquisición no bloqueante con timeout total configurable (30 s inicial recomendado) y liberación inversa; captura coherente de catálogos/revisiones referenciadas; adaptadores VLESS/VMess/identidades/TLS; exclusiones predeterminadas; validación segura de archivos; manifiesto/índice/ZIP `ZIP_STORED`; máximo 10.000 entradas y 512 MiB; cifrado GCM por bloques sin cambiar el formato binario v1; verificación y publicación atómica exclusiva sin sobrescritura; estados de resultado y matriz de pruebas.

La interfaz incremental deberá conservar magic, cabecera/AAD, perfil scrypt, salt/nonce, AES-256-GCM y tag del formato v1, con compatibilidad cruzada respecto a la interfaz actual. El ZIP se emitirá en streaming al cifrador sin crear ZIP en claro en disco; el tamaño exacto del ZIP se calculará antes de fijar `ciphertext_length` y se contrastará con el flujo emitido.

`docs/PLAN_BACKUP_RESTORE_CENTRAL.md` pasa a v1.11. La aprobación autoriza implementar writer y cifrado incremental en la rama autorizada, pero no crear backups reales, incluir secretos, implementar restore/verify independiente, leer/modificar master key ni tocar runtime/servicios/firewall/puertos/certificados desplegados/VPS de pruebas. `Xray-Normativa/` permanece inmutable.


## Continuidad — cifrado incremental compatible con contenedor compartido v1 (2026-11-03)

Se amplió `scripts/shared_backup_format.py` con `encrypt_payload_stream()` y `verify_package_stream()`. El cifrado incremental usa AES-GCM por bloques y longitud de plaintext conocida; conserva magic, cabecera canónica, AAD, scrypt v1, salt/nonce, AES-256-GCM y tag. El verificador incremental requiere flujo seekable, descarta plaintext no autenticado y sólo informa éxito después de validar el tag. Las APIs de bytes existentes se mantienen.

`tests/shared_backup_format.sh` cubre compatibilidad cruzada: paquetes de la API incremental se descifran con la API v1 de bytes y el verificador incremental autentica paquetes de ambas interfaces; también comprueba truncamiento, bytes sobrantes, alteración/tag, contraseña incorrecta y longitudes de entrada. Prueba focal PASS; suite completa `tests/*.sh`: 47/47 PASS; sintaxis Python y `git diff --check` PASS. Pruebas adicionales con tamaños aleatorios y límites de bloque PASS.

Estado: API incremental IMPLEMENTADA/VERIFICADA en aislamiento. El ZIP streaming/determinista y snapshot writer aún no están implementados. No se creó backup real, no se leyeron secretos/master key ni se tocó runtime.


## Continuidad — generador ZIP determinista en streaming v1 (2026-11-03)

Se añadió `scripts/shared_backup_zip.py`: `ZipMember` prepara miembros bytes o archivos dentro de un `allowed_root` explícito; valida root:root 0600, archivo regular, `st_nlink == 1`, recorrido de directorios sin symlinks, identidad de inode/metadatos y hashes/CRC en preflight y emisión. `ZipStream.read(n)` genera ZIP `ZIP_STORED` determinista directamente como fuente para `encrypt_payload_stream()`, sin ZIP temporal en claro. `write_zip_stream()` permite probar/emisión a un sink.

El ZIP fija timestamps, UTF-8/NFC, nombres y orden; `manifest.json`/`index.json` son las dos primeras entradas. Se rechazan traversal, paths absolutos, separadores alternativos, NUL/control, colisiones normalizadas/casefold, symlinks/hardlinks, permisos inseguros, cambios TOCTOU, ZIP64, más de 10.000 entradas y tamaño total >512 MiB.

Prueba focal `tests/shared_backup_zip.sh` PASS: lectura ZIP estándar, ZIP_STORED, CRC, determinismo, integración directa ZIP→AES-GCM streaming→verificación→ZIP válido, límites, paths y archivos inseguros. Suite completa `tests/*.sh`: 48/48 PASS; sintaxis Python, ShellCheck focal, shfmt focal y `git diff --check` PASS. Snapshot writer y adaptadores aún no implementados; no se creó backup real ni se tocaron secretos/master key/runtime.


## Continuidad — primera implementación local del snapshot writer compartido v1 (2026-11-03)

Se creó localmente scripts/shared_snapshot_writer.py conforme al contrato técnico aprobado §10.11. Se corrigieron tres puntos de la revisión: selective requiere categorías explícitas; la secuencia valida destino/prepara staging privado antes de pedir passphrase y solicita passphrase antes de adquirir locks; los directorios padres de locks deben existir y superar controles de propiedad/permisos, sin crearlos automáticamente. El timeout ahora rechaza valores no numéricos, booleanos, negativos o no finitos.

Se añadió tests/shared_snapshot_writer.sh. Cubre selección, staging antes del prompt, limpieza por contraseña no coincidente, locks ausentes/inseguros, orden de adquisición/liberación, timeout, referencias de identidad y exclusión de credenciales. Pruebas sintéticas confirman que los UUID de asociaciones/VMess no aparecen en el catálogo saneado, mientras email y level VMess se conservan como metadatos protegidos.

Verificación focal VPS: tests/shared_snapshot_writer.sh, tests/shared_backup_format.sh, tests/shared_backup_zip.sh y AST Python: PASS. Regresión global tests/*.sh: 49/49 PASS; git diff --check: PASS. No se ejecutó create_snapshot contra datos reales; no se generó backup; no se accedió a master key ni secretos reales. No se ejecutó restore ni verify independiente.

Estado: IMPLEMENTADO LOCALMENTE / VERIFICADO PARCIALMENTE / NO PUBLICADO / NO SINCRONIZADO / NO ACEPTADO. Pendiente completar la suite de aceptación integral y auditoría de trazabilidad §10.11. Rama autorizada design/user-identity-association-v1, HEAD ec9b306b38f0bce17f28c301c47df3b3d092785a; no se creó commit ni se hizo push. Xray-Normativa/ y main permanecen intactas.

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

## Actualización de continuidad — recuperación de staging autorizada (2026-11-03)

La enmienda autorizada a §10.11 fue implementada localmente. La passphrase se solicita y valida antes de crear staging. `.xrm-coordination.lock` serializa recuperación/preparación/limpieza; `owner.lock` root:root 0600 y `nlink == 1` permanece bloqueado durante cada operación. Se recuperan sólo directorios `.xrm-snapshot-*` cuyo lock esté libre y cuya estructura sea estrictamente válida. Staging activos se conservan; temporales vacíos sólo se retiran bajo coordinación; nombres/tipos/permisos inesperados bloquean fail-closed y no se borran. La coordinación se libera antes de adquirir los locks de datos, cuyo orden sigue siendo `lifecycle → integrity → catalog`.

La suite focal pasó tras corregir una colisión inicial del nombre del lock de coordinación con el patrón de staging. Se retiró el caso de terminación abrupta durante el prompt del crash matrix porque ahora no debe existir staging en esa fase; SW-02 verifica esa propiedad. Permanecen los casos de terminación durante cifrado y antes de publicación. `bash tests/*.sh` PASS; AST 16/16; ShellCheck, shfmt y `git diff --check` PASS. RSS aislado medido: 74.120 KiB. El writer sigue implementado localmente, no publicado y pendiente de aceptación formal. No se creó backup real ni se accedió a secretos o `master.key`; normativa intacta; sin commit/push/sync.

## 2026-11-03 — Corrección del lock de coordinación y contrato de manifiesto

Por autorización expresa del propietario se corrigió `_acquire_coordination_lock()`: los locks preexistentes se inspeccionan sin mutación; se rechazan hardlinks, symlinks, tipos especiales y permisos/propietarios incorrectos antes de modificar nada. Se comprueba que el descriptor abierto conserve el inode inspeccionado. El archivo nuevo se crea de forma exclusiva (`O_EXCL`/`O_NOFOLLOW`) y sólo entonces se fijan propietario y modo.

Se completaron validaciones del manifiesto: estructura raíz, UUID v4 canónico, timestamp UTC RFC 3339 `Z`, versión entera, source, selección y categorías únicas/no vacías, listas estructurales, contadores, miembros SHA-256/tamaño/media type y coherencia de recursos/global `COMPLETE` con exclusiones/dependencias.

Pruebas nuevas: hardlink (incluida preservación de modo, inode, nlink y contenido del otro nombre), symlink, FIFO, modo inseguro, contención/timeout de coordinación y manifiestos con UUID/timestamps/categorías/versión inválidos. Suite focal PASS; regresión completa PASS (49 scripts); AST 16/16; `bash -n`, ShellCheck, shfmt y `git diff --check` PASS. RSS aislado focal 75.120 KiB.

Estado: IMPLEMENTADO LOCALMENTE / VERIFICADO EN AISLAMIENTO / NO PUBLICADO / NO ACEPTADO FORMALMENTE. No commit/push ni sincronización GitHub. No se creó backup real ni se accedió a datos secretos; no restore/verify independiente ni runtime apply. Normativa inmutable. Siguiente paso: revisión de aceptación actualizada; no publicar sin autorización expresa.


## Continuidad — publicación del snapshot writer v1 (2026-11-03)

Se publicó el código local del snapshot writer v1, las pruebas, dependencias de ZIP streaming/API y documentos técnicos en la rama autorizada design/user-identity-association-v1. Commit publicado: ae8a7a089809e2e1913c14a714f45d956f8a5a1d, verificado como HEAD remoto el 2026-11-03.

La regresión local previa a publicar pasó: 49/49 scripts; AST 16/16; bash -n, ShellCheck, shfmt y git diff --check. La normativa mantiene 14/14 hashes coincidentes con la copia maestra. scripts/__pycache__/ quedó fuera del commit. El writer sigue NO ACEPTADO FORMALMENTE; publicar no equivale a aceptar. Próximo paso: revisión de aceptación contra §10.11.8 y plan v1.14. No ejecutar backup real, restore/verify independiente, ni tocar secretos/master.key/runtime.


## Continuidad — correcciones de la segunda revisión del snapshot writer (2026-11-03)

El propietario autorizó corregir B-01/B-02/B-03 manteniendo el writer NO ACEPTADO. Se implementó allowlist de identidades/asociaciones y exclusión íntegra de WireGuard/protocolos no soportados; limpieza fail-closed con cierre garantizado de owner_fd y reporte FAILED cuando falla cleanup; validación estricta de versión v1, conjuntos de categorías y estructura de objetos del manifiesto.

La suite focal añade pruebas sintéticas para claves privadas/PSK, campos desconocidos, versión 2, categorías extra/omitidas/duplicadas, objetos internos incompletos, fallos de coordinación/unlink/rmdir/fsync y crash tras el enlace final antes del fsync del directorio.

Verificación ejecutada en esta sesión: 49/49 scripts PASS; AST 16/16; bash -n 74 archivos; ShellCheck focal, shfmt focal y git diff --check PASS. SHA-256 de la documentación normativa: 14/14 coincidentes con /root/Xray_Manager_Documentacion_Final_2026-10-31.

**Punto exacto de reanudación:** revisar diff y documentación técnica actualizados; ejecutar auditoría de aceptación final. No aceptar el writer ni publicar estas correcciones hasta decisión expresa del propietario. Base publicada: ae8a7a089809e2e1913c14a714f45d956f8a5a1d; cambios actuales locales no committeados. No backup real, master.key, secretos, restore/verify independiente ni runtime.


## Registro histórico SUPERADO — publicación B-01/B-02/B-03 con bloqueo A-16 (2026-11-03)

El propietario autorizó publicar las correcciones B-01/B-02/B-03 en la rama autorizada, sin aceptar Snapshot Writer v1. La publicación debe incluir este estado de auditoría: **A-16 BLOQUEANTE / WRITER NO ACEPTADO**.

A-16: `_recover_orphan_staging()` rechaza un staging post-publicación legítimo porque `os.link(package.tmp, final_path)` deja temporal y destino apuntando al mismo inode (`st_nlink == 2`), mientras el recuperador exige `st_nlink == 1`. La reproducción sintética produjo `SnapshotBlocked` y conservó ambos nombres. Los tests de crash/cleanup no ejecutan recuperación sobre ese estado.

Siguiente paso tras publicar/sincronizar: diseñar y solicitar autorización para una corrección fail-closed que reconozca sólo el hardlink post-link demostrablemente correspondiente al paquete final; mantener rechazo de hardlinks arbitrarios, staging activo, symlinks, tipos especiales y metadatos inseguros. Añadir tests de recuperación tras crash post-link, unlink fallido y fallo de coordinación, comprobando integridad/preservación del paquete final y conservación de staging ambiguos. Repetir auditoría antes de proponer aceptación.

No ejecutar backup real, no leer `master.key`/secretos, no restore/verify independiente, no runtime apply ni modificar `Xray-Normativa/`.

## Continuidad — A-16 corregido localmente, pendiente de auditoría (2026-11-03)

El propietario autorizó corregir A-16. La implementación local incorpora publication.json en el staging privado, escrito y sincronizado antes del hardlink final. El marcador vincula el basename exacto de destino, device/inode, tamaño y SHA-256 del paquete. El recuperador admite el estado legítimo package.tmp nlink == 2 sólo con marcador válido y destino coincidente; retira exclusivamente package.tmp, comprueba que el destino conserva nlink == 1 y elimina después marcador/owner/staging. El flujo soporta reintento si el recuperador se interrumpe tras retirar el nombre temporal.

Se mantienen bloqueados hardlinks sin marcador, nlink > 2, destino con nombre/inode/tamaño/hash distinto, symlinks, tipos especiales, metadatos inseguros y staging activos. Los tests focales ejercitan crash post-link, fallos de coordinación/unlink y crash del propio recuperador. Verificación ejecutada: tests/*.sh 49/49 PASS; AST 16/16; bash -n 74 archivos; ShellCheck PASS; shfmt focal PASS; git diff --check PASS; normativa 14/14 hashes coincidentes. A-16 pasa. El Snapshot Writer sigue NO ACEPTADO formalmente hasta revisión/decisión expresa del propietario.

No crear backup real, no leer master.key/secretos, no restore/verify independiente, no runtime apply y no modificar Xray-Normativa/.

## Publicación y sincronización A-16 — 2026-11-03

Por autorización expresa del propietario, la corrección A-16, sus pruebas y la documentación afectada quedaron publicadas en `design/user-identity-association-v1`, commit `40c907e2a9da639f3458547e09fec6f26fdac5e1`. `git ls-remote` confirmó el mismo SHA en GitHub; el checkout de `/opt/xray-manager` coincide con el commit y quedó limpio. La rama `main` y `Xray-Normativa/` no se modificaron. Snapshot Writer v1 continúa NO ACEPTADO FORMALMENTE: publicar/sincronizar no equivale a aceptación.


## Estado vigente — cierre técnico de aceptación A-01–A-19 (2026-11-03)

- Matriz de trazabilidad completa documentada en `docs/PLAN_BACKUP_RESTORE_CENTRAL.md` §10.20. Se recuperaron los nombres originales de los 19 criterios y se enlazaron con sus pruebas versionadas; A-01–A-15 y A-17–A-19 conservan su resultado PASS de la auditoría previa y la regresión actual volvió a ejecutarse.
- A-16: diez negativos nuevos para marcador malformado/no canónico, hash/device/inode/tamaño alterados, campo extra, symlink, hardlink y modo inseguro. Cada caso confirma bloqueo fail-closed y preservación de la evidencia. No requirió modificar el código del writer.
- Verificación actual: 49/49 scripts PASS; AST 16/16; `bash -n` 74 archivos; ShellCheck PASS; shfmt PASS; `git diff --check` PASS; RSS focal 76.336 KiB. Normativa 14/14 hashes coincidentes con la copia maestra; `README.md` es archivo adicional no normativo.
- Rama `design/user-identity-association-v1`; base verificada `b1e2ef4537eafeacefd5584a7fde5c9fd02626a9`. La matriz y los diez negativos A-16 se publicaron en `101853e6ef0990686128f45561b22e1cd4248aea`; el registro final de publicación quedó en `7f03efcf080465d8bced447549e29f8abb95248b`. VPS y GitHub comparten el HEAD final.
- `Xray-Normativa/` no se modificó. No backup real, no acceso a `master.key`/secretos, no restore/verify independiente, no runtime apply.
- Estado: A-01–A-19 PASS en pruebas aisladas/sintéticas; Snapshot Writer v1 **NO ACEPTADO FORMALMENTE**. La aceptación formal requiere decisión expresa del propietario y no se infiere de pruebas o publicación.


## Punto de reanudación posterior a la aceptación del Snapshot Writer v1

La continuidad más reciente se amplía con la validación live inicial de Xray-core y VLESS-WS registrada al final de este documento.

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


Siguiente trabajo permitido: continuar con el plan de backup/restore integral y sus componentes pendientes, siempre contrastando la normativa y solicitando autorización para cada nuevo alcance. La aceptación del Writer no autoriza backup real, restore/verify independiente ni cambios de runtime. Etapa 2 sigue ABIERTA.


## Validación live inicial de Xray-core y VLESS-WS — 2026-11-03

Se realizó la primera prueba operativa real del administrador en la VPS de desarrollo.

**Instalación Xray-core**
- El menú real de administración instaló Xray-core 26.10.31 (a4a3dff) para Linux amd64.
- El release oficial, su archivo .dgst, el SHA-256 fijado para el ZIP, la versión del binario y los archivos geodata se verificaron correctamente.
- El administrador informó instalación exitosa y no creó ni inició un servicio systemd.

**Ajuste de permisos del almacén**
- El preflight de vless_config_store.py detectó /var/lib/xray-manager/connections en modo 750, incompatible con su contrato root:root 0700.
- Se confirmó que install.sh establece esa ruta en modo 700. Se ajustó sólo ese directorio de 750 a 700; el audit posterior pasó. No se modificó código del repositorio.

**Conexión de prueba**
- Creada desde el menú: Prueba-VLESS-WS-Real, ID conn-1793749234-670662.
- Modalidad vless_ws; escucha prevista 0.0.0.0:10001; WebSocket /ws; seguridad none; capacidad 1.
- Se creó un usuario de prueba Cliente-Prueba-VLESS-WS con estado draft. El registro live de usuarios sigue en esquema legacy (arreglo JSON), por lo que se utilizó el gestor VLESS legacy. No se migró a users v2. El UUID se omite de la documentación.
- La revisión neutral 1 se persistió en connections/configurations/conn-1793749234-670662.r000001.json; secret_ref=null; conexión draft; runtime_applied=false.
- La previsualización y recuperación desde el Manager terminaron con Configuration OK. Se repitió la recuperación fijando XRAY_VALIDATION_BINARY=/usr/local/bin/xray, validando expresamente con el binario instalado.
- Audit del almacén: cero referencias rotas, cero archivos huérfanos y cero secretos huérfanos.

**Límites y advertencias**
- Xray emitió la advertencia oficial de que WebSocket está obsoleto/no recomendado, puede retirarse y recomienda XHTTP H2/H3.
- No se creó /etc/xray/config.json; no se ejecutó xray_service_prepare; no existe xray.service ni se creó cuenta/grupo Xray durante esta prueba.
- Servicio inactivo, sin proceso Xray y puerto 10001 sin listener. No firewall, no apertura de puertos, no runtime apply y no conexión cliente externa/WAN.
- La inspección del menú actual no encontró una acción de aplicación runtime de la conexión. El siguiente frente requiere diseño/implementación y autorización específica antes de preparar servicio, publicar configuración o iniciar listener.

Evidencia detallada: docs/VALIDACION_LIVE_XRAY_VLESS_WS_2026-11-03.md.

**Estado:** Xray instalado y verificado en entorno real; VLESS-WS creado, persistido y validado en entorno real; conectividad externa y runtime apply pendientes. Etapa 2 sigue ABIERTA. Código sin cambios; documentación actualizada localmente, sin commit/push/sync. Xray-Normativa/ y main intactas.

## Continuidad — infraestructura inicial de candidatos runtime mediante perfiles (2026-11-03)

El propietario aprobó la opción A: respetar estrictamente la normativa de Etapa 5. La activación debe ocurrir a través del cambio de perfil activo; una conexión independiente no es una vía alternativa.

La inspección del árbol confirmó que todavía no existe un gestor funcional de perfiles (módulo, menú y esquema/registro). Los adaptadores VLESS/VMess existentes construyen configuraciones por conexión, pero no componen una versión integral de perfil. No conectar el runtime directamente a Prueba-VLESS-WS-Real ni inventar un esquema de perfil.

Se implementó localmente:
- `scripts/xray_runtime_candidates.py`: primitiva de staging privado de candidatos asociados a profile_id/profile_revision.
- `tests/xray_runtime_candidates.sh`: prueba sintética focal.
- `docs/DISENO_IMPLEMENTACION_RUNTIME_PERFILES.md`: decisiones, flujo objetivo, controles, pruebas y pendientes.

El staging exige JSON objeto con inbounds/outbounds, archivo fuente regular nlink 1 sin symlinks, máximo 16 MiB, tokens de perfil/revisión sin traversal, validación nativa con Xray, bloqueo, no sobrescritura de revisión, hash SHA-256 y manifiesto. Los bytes se copian a un archivo temporal privado y Xray valida exactamente esa copia; luego se publica el directorio candidato mediante rename. Configuración/manifiesto 0600 y directorios 0700.

Límite fundamental: el componente sólo almacena un candidato validado. No escribe /etc/xray/config.json ni prepara/inicia/habilita Xray. No existe aún flujo de publicación runtime integrado; deberá implementarse dentro del cambio de perfil activo de Etapa 5.

La conexión Prueba-VLESS-WS-Real sigue draft y runtime_applied=false. No se ejecutó xray_service_prepare, no se creó usuario/grupo de servicio ni unidad, no se abrió 10001, no se cambió firewall ni certificados y no se probó conectividad WAN.

**Próximo paso:** ejecutar la prueba focal y regresión; probar validación con el binario real sólo sobre configuración sintética temporal. Después, diseñar/implementar el subsistema de perfiles y su composición/validación. No publicar ni activar runtime hasta que el flujo de perfil esté integrado y autorizado. No commit/push/sync sin autorización expresa. Xray-Normativa/ y main permanecen inmutables.

### Nota de regresión segura

La primera ejecución de tests/smoke.sh reveló que tests/users.sh perdía las rutas temporales al volver a cargar modules/users.sh y llegaba a consultar el registro live. La prueba se detuvo al detectar el límite de capacidad del usuario de prueba; no modificó el registro real. Se corrigió el fixture para fijar XRAY_MANAGER_USERS_DIR, XRAY_MANAGER_USERS_FILE, XRAY_MANAGER_CONNECTIONS_DIR, XRAY_MANAGER_CONNECTIONS_FILE y XRAY_MANAGER_INTEGRITY_LOCK antes de cargar los módulos. Después de la corrección, tests/users.sh y tests/smoke.sh pasan.

### Verificación final de este punto de continuidad

Regresión completa: 50/50 scripts PASS; Python AST 17/17; bash -n de todos los archivos shell PASS; ShellCheck y shfmt de la nueva prueba focal PASS; git diff --check PASS. El binario Xray-core 26.10.31 real validó un candidato sintético temporal y el staging devolvió STAGED sin publicar runtime ni iniciar servicio. Los 14 archivos normativos comparados coinciden con la copia maestra (README.md es auxiliar y no normativo). No commit/push/sync.

## Publicación de la infraestructura de candidatos runtime — 2026-11-03

Por autorización expresa del propietario, se sincronizan con GitHub en `design/user-identity-association-v1` los cambios locales de la infraestructura de staging por perfiles, el aislamiento de `tests/users.sh` y los documentos de continuidad/diseño/validación live. Se incluyen los nueve archivos de proyecto identificados en el punto de control de esta publicación. Se excluye `scripts/__pycache__/`, que permanece como artefacto local y no forma parte del repositorio.

La publicación no activa Xray ni altera el estado operativo: `Prueba-VLESS-WS-Real` permanece draft y `runtime_applied=false`; no existe configuración runtime aplicada ni listener 10001. No se ejecutó preparación/arranque del servicio ni se modificó firewall, red o certificados. `Xray-Normativa/` y `main` permanecen intactas. Etapa 2 continúa ABIERTA; el siguiente bloque de desarrollo es el subsistema de perfiles, conforme a la opción A aprobada.


## Continuidad — almacén de perfiles v1 (2026-11-03)

[SUPERADO EL 2026-11-03] La decisión provisional de la primera iteración fue mantener las configuraciones de perfiles en texto plano. El propietario eligió después AES-256-GCM; consultar el punto de reanudación vigente y el último bloque de este documento. Los datos se protegen mediante directorios `root:root 0700` y archivos `root:root 0600`; esta protección no equivale a cifrado y root puede leer el contenido.

### Implementación disponible

- `scripts/xray_profiles.py`: CLI y persistencia del catálogo, perfiles y revisiones.
- `modules/profiles.sh`: submenú funcional inicial.
- `tests/xray_profiles.sh`: pruebas sintéticas focales.
- `bin/xray-manager`: carga el módulo.
- `modules/main_menu.sh`: opción principal de configuraciones/perfiles/respaldo conectada al submenú normativo.
- `docs/DISENO_IMPLEMENTACION_PERFILES.md`: diseño, estructura, controles, operaciones y límites.

El almacén usa `/var/lib/xray-manager/profiles/` cuando se invoque desde el Manager; las pruebas usan exclusivamente `--store`/`XRAY_MANAGER_PROFILES_DIR` en rutas temporales. El catálogo tiene IDs inmutables y nombres únicos; cada perfil mantiene metadatos y directorios de revisiones. [DESCRIPCIÓN HISTÓRICA SUPERADA] La primera implementación guardaba `config.json` en texto plano. La versión vigente usa `config.enc.json` cifrado con AES-256-GCM; consultar el último bloque de este documento y `docs/DISENO_IMPLEMENTACION_PERFILES.md`. Renombrar no cambia JSON ni ID.

### Operaciones que ya se pueden usar

Crear desde cero sin JSON; crear copiando un archivo JSON externo; consultar perfiles y revisiones; modificar nombre/descripción/notas y/o importar una nueva configuración; duplicar; renombrar; consultar hashes de revisiones; restaurar una revisión como nueva. La eliminación aparece deshabilitada hasta integrar/verificar el registro activo y dependencias.

### Límites y pendientes vinculantes

- Una importación sólo acredita sintaxis JSON estricta. `xray_static=not_run`; `validation_status=not_validated`. No afirmar Validada ni Aplicada.
- El estado activo se informa como no integrado. No se ha creado el registro `active-profile.json` ni conectado el antiguo indicador de perfil activo.
- No existe validación Xray nativa asociada a cada revisión, informes de validación, comparación de revisiones, historial de modificaciones ni retención configurable.
- No hay composición integral de conexiones/usuarios/asociaciones/certificados en un perfil.
- No hay activación, publicación runtime, verificación del servicio ni rollback de activación. La regla opción A permanece: sólo el cambio de perfil activo podrá ser la vía de activación.
- No hay eliminación real de perfiles; no habilitarla antes de proteger perfil activo, dependencias y conservación de JSON.

### Verificación ejecutada

En la VPS: `tests/xray_profiles.sh`, `tests/stage1_menu.sh`, `tests/smoke.sh` y regresión `tests/*.sh`: 51/51 PASS; Python AST 18/18; `bash -n` todos los shell scripts; ShellCheck/shfmt focal; `git diff --check`. La suite nueva cubre permisos, ciphertext sin marcador plaintext, descifrado, clave ausente/incorrecta, autenticación GCM/AAD, copias independientes, nombres únicos, modificación/versionado, rename sin cambio de blob, restore no destructivo, JSON malformado/duplicado, symlink/hardlink, almacén simbólico y concurrencia por nombre.

Las pruebas usan almacenes temporales. No se creó `/var/lib/xray-manager/profiles`, no hay perfiles reales y no se alteró la conexión live. No se escribió `/etc/xray/config.json`, no se inició Xray ni se tocaron systemd, firewall, puertos, certificados o red. No se leyó ni usó `master.key`. `Xray-Normativa/` y `main` siguen intactas. Etapa 2 continúa ABIERTA.

**Punto exacto de reanudación:** revisar el diff completo y el diseño; después implementar validación estática Xray por revisión con pruebas sintéticas/aisladas, sin iniciar el servicio ni publicar runtime. Mantener deshabilitada la eliminación y no crear flujo de activación todavía.


## Punto de reanudación posterior a la implementación de cifrado de perfiles — 2026-11-03

La primera versión local del gestor de perfiles almacenaba `config.json` en texto plano. Al contrastarla con Etapa 5 normativa se detectó que esto contradecía la regla de no guardar credenciales ni claves privadas en texto plano. No se publicó aquella versión. El propietario eligió explícitamente AES-256-GCM (opción 1).

La implementación local actual cifra todo el JSON por revisión en `config.enc.json` con nonce aleatorio y AAD ligado a `profile_id`/revisión. Lee únicamente la clave maestra existente por el cargador seguro; no la crea ni la regenera. Las pruebas utilizan claves sintéticas temporales. Clave ausente o incorrecta y ciphertext manipulado se rechazan fail-closed. Los manifests plaintext/no reconocidos también se rechazan; no existe migración automática.

La inspección confirmó que `/var/lib/xray-manager/profiles` no existe; no hay perfiles reales que migrar. No se ha leído ni modificado `/etc/xray-manager/keys/master.key`. No se modificó runtime, servicio, firewall, puertos, certificados, conexión live ni `Xray-Normativa/`.

**Verificación:** `tests/*.sh` 51/51 PASS; Python AST 18/18; `bash -n` global PASS; ShellCheck focal PASS; shfmt de los archivos nuevos PASS; `git diff --check` PASS.

**Estado:** IMPLEMENTADO, VERIFICADO EN PRUEBAS SINTÉTICAS, PUBLICADO y SINCRONIZADO byte a byte en `design/user-identity-association-v1`. Commit funcional inicial `03b63ca109a2fabb262924daf5d2fe4a683b23d8`; commit de reconciliación byte a byte `4cec7496585390adbe72d8887cb6dacd94743c32`. El árbol Git local y remoto coincide. `scripts/__pycache__/` es un artefacto local preexistente y se preserva/excluye. `main` permanece protegida.

**Próxima acción:** revisión del propietario y aceptación formal del subsistema o solicitud de ajustes. No usar la clave maestra real en pruebas ni ejecutar activación runtime.
