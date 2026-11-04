# Auditoría formal — almacén de perfiles v1.1

**Fecha:** 2026-11-03
**Rama:** `design/user-identity-association-v1`
**Base de código revisada:** commit `7d1782f9b4359b15d025ad771d92a582e39a2944` (regularización documental previa).
**Alcance:** revisión de solo lectura del almacén de perfiles, su menú, pruebas y diseño contra `Xray-Normativa/05_Configuraciones_Perfiles/Etapa_5_Configuraciones_Perfiles.md` y YAML.
**Resultado recomendado:** **NO ACEPTAR AÚN como subsistema completo**; conservar el componente publicado, resolver el bloqueo transaccional y volver a auditar.

## 1. Alcance y método

Se inspeccionaron:

- `scripts/xray_profiles.py` (persistencia, catálogo, revisiones, cifrado, locking y CLI).
- `modules/profiles.sh` y su integración en `bin/xray-manager` / `modules/main_menu.sh`.
- `tests/xray_profiles.sh`, `tests/stage1_menu.sh` y `tests/smoke.sh`.
- `docs/DISENO_IMPLEMENTACION_PERFILES.md`.
- Especificación funcional Etapa 5 en Markdown y YAML.

No se modificó código. No se creó almacén ni perfil live. `/var/lib/xray-manager/profiles` estaba ausente. Se confirmó que existe `master.key`, pero **no se leyó ni se utilizó**. Las pruebas/fault injection de esta auditoría utilizaron exclusivamente un directorio temporal y una clave sintética, eliminados al terminar.

La documentación normativa se comparó por SHA-256 con la copia maestra disponible: **14/14 archivos normativos coincidentes**; `README.md` es un auxiliar extra y no forma parte de esos 14.

## 2. Resultado de verificaciones ejecutadas

| Verificación en esta revisión | Resultado |
|---|---|
| `bash tests/xray_profiles.sh` | PASS |
| `bash tests/stage1_menu.sh` | PASS |
| `bash tests/smoke.sh` | PASS |
| Python AST de `scripts/xray_profiles.py` | PASS |
| `bash -n` de módulo/entrypoint/menú | PASS |
| ShellCheck `-S warning` en módulo y prueba de perfiles | PASS |
| `git diff --check` | PASS |
| Fault injection de fallo al guardar catálogo durante `update()` | **REPRODUCE INCONSISTENCIA** |

La cifra histórica 51/51 scripts PASS y AST 18/18 corresponde a la regresión documentada en la implementación anterior; no se volvió a ejecutar la suite completa de 51 scripts en esta auditoría. Las tres pruebas de regresión indicadas arriba sí se ejecutaron ahora.

## 3. Hallazgo bloqueante

### PF-01 — `update()` puede dejar catálogo y metadatos inconsistentes tras un fallo

**Severidad:** BLOQUEANTE para aceptación del almacén.
**Evidencia:** `scripts/xray_profiles.py:641-667`, especialmente `save_metadata()` antes de `save_catalog()` (líneas 658-665).

El método actualiza primero `metadata.json` y después `catalog.json`. Si la segunda escritura falla, no revierte el primer cambio ni restaura el catálogo. Cuando la actualización incluye un nuevo nombre, el catálogo conserva el nombre anterior y los metadatos el nuevo. La siguiente consulta `list_profiles()` detecta la discrepancia y falla cerrada.

**Reproducción ejecutada:** en un almacén temporal con clave sintética se creó un perfil; se sustituyó `save_catalog()` por una función que lanza `OSError`; `update(profile_id, name="Nombre nuevo")` falló después de guardar metadatos. Al restaurar el método y ejecutar `list_profiles()`, se obtuvo: `El catálogo y los metadatos no coinciden para <profile_id>`. El resultado confirma que una operación reportada como fallida puede dejar el almacén inconsistente.

**Impacto:** el perfil puede quedar inaccesible desde el listado normal, aunque su directorio y metadatos existan. Esto contradice el requisito de Etapa 5 §6 de conservar el estado anterior ante fallo.

**Corrección requerida (no implementada):** definir una transacción recuperable para metadatos/catálogo (journal/manifest de operación o mecanismo equivalente), con orden durable, rollback idempotente y recuperación tras terminación abrupta. Añadir pruebas de fallo antes/después de replace y fsync para cada archivo. No basta con capturar la excepción y reescribir el valor anterior sin resolver también fallos durante el rollback.

## 4. Hallazgos importantes adicionales

### PF-02 — Ventana de consistencia y durabilidad en create/duplicate/rename/restore

**Severidad:** ALTA.
**Evidencia:** `create()` líneas 470-527; `duplicate()` 578-639; `rename()` 556-576; `restore()` 682-700; `atomic_write()` 125-153.

- `create()` y `duplicate()` renombran el directorio temporal a su nombre final y luego actualizan el catálogo, pero no sincronizan explícitamente el directorio padre `profiles/` después del rename.
- `rename()`, `update()` y `restore()` modifican más de un archivo persistente sin una transacción recuperable.
- `atomic_write()` hace `os.replace()` y después `fsync()` del directorio. Si el replace ya ocurrió y el fsync falla, el llamador recibe error aunque el nuevo contenido pueda estar visible; las rutinas superiores no distinguen ese estado de commit ambiguo. En `create()`/`duplicate()` el cleanup puede retirar el directorio final aun cuando el catálogo ya haya sido reemplazado.

**Corrección requerida:** especificar y probar puntos de commit, fsync de todos los directorios padres implicados, estados de publicación ambigua, recuperación idempotente y preservación de la última versión consistente.

### PF-03 — Importación/modificación sin vista previa ni diff normativo

**Severidad:** MEDIA.
**Evidencia:** `modules/profiles.sh:24-86` y `116-148`; Etapa 5 §6.

La interfaz confirma que copiará el archivo, pero no presenta una vista previa de la configuración importada. Al modificar un JSON, informa que se creará una revisión nueva, pero no calcula ni muestra diferencias antes de guardar. La especificación exige vista previa y diff. El CLI tampoco implementa ese flujo interactivo.

### PF-04 — Validación Xray por revisión ausente

**Severidad:** PENDIENTE DE ALCANCE.
**Evidencia:** `scripts/xray_profiles.py:448-449`, `create()` y `duplicate()` generan `xray_static=not_run`, `status=pending`; `metadata.validation_status=not_validated`.

No existe operación que ejecute validación estática Xray por revisión ni informe asociado. El estado actual es honesto y no presenta una configuración como Validada. Sin embargo, Etapa 5 §6 requiere validar al crear/modificar un perfil con configuración y mantener el último estado Validado. Bloquea la aceptación funcional completa de Etapa 5, aunque puede mantenerse fuera de un alcance v1.1 limitado si el propietario lo acepta expresamente.

### PF-05 — Operaciones/requisitos de perfil aún incompletos

**Severidad:** PENDIENTE DE ALCANCE.

- Crear desde configuración independiente no está disponible; la interfaz ofrece desde cero, archivo JSON u otro perfil. El gestor de configuraciones independientes aún no está implementado.
- Comparar revisiones/configuraciones no está implementado.
- No existe historial separado de modificaciones.
- No existe retención configurable de revisiones.
- No hay registro de perfil activo ni composición de conexiones, usuarios/asociaciones y referencias de certificados.
- Eliminación permanece deliberadamente deshabilitada.
- No existe activación transaccional, verificación del runtime ni rollback.
- Backup/restore de perfiles no está integrado.

Estos pendientes están descritos en el diseño v1.1; no deben presentarse como funciones disponibles. La activación debe seguir exclusivamente el cambio de perfil activo aprobado para Etapa 5.

### PF-06 — Cobertura de pruebas de corrupción y fallos de filesystem incompleta

**Severidad:** MEDIA.

La prueba de modificación de ciphertext en `tests/xray_profiles.sh` cambia el blob sin actualizar el hash del manifiesto; por tanto, el camino normal detecta primero el SHA-256 incorrecto y no alcanza el rechazo por `InvalidTag` de AES-GCM. Las pruebas de clave incorrecta y AAD modificada sí ejercitan fallo de autenticación. No se encontraron pruebas de inyección de fallos para las secuencias multiarchivo de `update()`/`restore()`/`rename()` ni de crash en las ventanas de publicación.

**Corrección requerida (atendida parcialmente y verificada el 2026-11-04):** modificar ciphertext y actualizar el hash del manifiesto para forzar la comprobación GCM; añadir fault injection de write/replace/fsync/unlink y crash recovery. El alcance exacto y sus límites se documentan en `docs/AUDITORIA_PF06_COBERTURA_CRIPTO_FILESYSTEM_2026-11-04.md`.

### PF-07 — Validación de esquema del catálogo incompleta

**Severidad:** BAJA.
**Evidencia:** `scripts/xray_profiles.py:332-347`.

`load_catalog()` no comprueba explícitamente que `name` sea string antes de invocar `casefold()`, ni valida todos los tipos/fechas/campos del registro. Un catálogo malformado puede terminar en excepción no controlada en lugar de un error de esquema uniforme. Reforzar validación de tipos y rechazar versiones booleanas (`True == 1`) en campos de versión.

## 5. Controles que sí están implementados y verificados

- AES-256-GCM para el JSON completo de cada revisión, nonce aleatorio de 12 bytes y AAD ligado a `profile_id`/revisión (`scripts/xray_profiles.py:237-278`).
- La clave maestra se carga mediante el helper existente; el helper exige root, directorio padre `root:root 0700`, archivo regular `root:root 0600`, 32 bytes y apertura con `O_NOFOLLOW` (`scripts/certificate_crypto.py:45-91`). La clave real no se leyó durante esta auditoría.
- Envoltorio cifrado con campos exactos, versión/algoritmo esperados, Base64 estricto, longitud de nonce y autenticación GCM.
- JSON UTF-8 estricto, sin BOM, claves duplicadas ni valores no finitos; el objeto de configuración debe ser un objeto JSON.
- Directorios root-owned 0700, archivos root-owned 0600, rechazo de symlink/hardlink en las rutas/archivos de almacén, lock `flock`, escrituras atómicas y fsync del archivo/directorio de destino.
- Revisiones inmutables con `rNNNNNN`, cifrado nuevo al duplicar y restauración como nueva revisión.
- Estados conservadores: `xray_static=not_run`, `not_validated` y `active_status=not_integrated`; no se confunde guardar con validar o activar.
- Eliminación y activación permanecen deshabilitadas; el menú deja claro que son pendientes.

## 6. Corrección documental detectada

`docs/DISENO_IMPLEMENTACION_PERFILES.md` afirmaba que el manifiesto guardaba SHA-256 del JSON descifrado. El código realmente guarda `ciphertext_sha256` y `plaintext_size_bytes`; al leer, valida hash/tamaño del blob antes de descifrar y después verifica tamaño del plaintext. Se corrigió esa descripción documental para que coincida con el comportamiento implementado. No se cambió el código ni el formato de datos.

## 7. Matriz resumida frente a Etapa 5

| Requisito | Estado observado |
|---|---|
| Menú de perfiles integrado | IMPLEMENTADO |
| Crear desde cero | IMPLEMENTADO |
| Crear/importar desde archivo JSON | IMPLEMENTADO parcialmente; falta preview/validación funcional |
| Crear desde configuración independiente | NO IMPLEMENTADO |
| Crear desde otro perfil | IMPLEMENTADO mediante duplicación independiente |
| Consultar perfiles/versiones | IMPLEMENTADO parcialmente; estado activo no integrado |
| Modificar metadatos/configuración | IMPLEMENTADO con bloqueo PF-01/PF-02 |
| Duplicar / renombrar | IMPLEMENTADO con revisión transaccional pendiente |
| Eliminar perfil | DESHABILITADO deliberadamente |
| Validar Xray y conservar informe | NO IMPLEMENTADO |
| Comparar versiones / diff | NO IMPLEMENTADO |
| Restaurar versión como nueva | IMPLEMENTADO; rollback/atomicidad pendiente |
| Retención configurable / historial de cambios | NO IMPLEMENTADO |
| Registro activo / activación / verificación / rollback | NO IMPLEMENTADO |
| Composición integral de datos | NO IMPLEMENTADO |
| Backup/restore | NO IMPLEMENTADO en este subsistema |

## 8. Decisión técnica recomendada

**No emitir aceptación formal todavía**, ni siquiera como componente de persistencia limitado, hasta resolver PF-01 y PF-02 y añadir pruebas de fallos transaccionales. La criptografía y el aislamiento del almacén muestran una base sólida, pero la consistencia entre catálogo y metadatos es parte esencial de la integridad del almacén.

Una vez corregidos los bloqueos, el propietario podrá decidir si acepta el almacén v1.1 como módulo limitado con los pendientes funcionales explícitamente excluidos, sin confundir esa aceptación con la finalización de Etapa 5 o Etapa 2.

## 9. Restricciones respetadas durante la auditoría

- Código fuente sin modificaciones.
- No se leyó ni utilizó `/etc/xray-manager/keys/master.key`.
- No se creó `/var/lib/xray-manager/profiles` ni perfiles reales.
- No se tocó Xray runtime, systemd, firewall, puertos, certificados reales o red.
- `Xray-Normativa/` y `main` no se modificaron.
- La prueba de fallo se realizó únicamente con almacén temporal y clave sintética.

**Conclusión:** perfiles v1.1 tiene un núcleo criptográfico y de persistencia útil, con pruebas focales satisfactorias, pero la auditoría detectó un fallo reproducible de consistencia tras un error de escritura y ventanas de commit multiarchivo sin recuperación suficiente. Se conserva publicado, no se modifica el código y la aceptación formal queda pendiente de corregir esos hallazgos y recibir la decisión expresa del propietario.


## 10. Remediación PF-01/PF-02 — implementación inicial en rama de trabajo

Tras la autorización expresa del propietario, se implementó en el árbol de trabajo un journal de recuperación `.profiles.transaction.json` con snapshots de catálogo/metadatos anteriores, rutas restringidas y rollback idempotente al adquirir el lock. Se integró en create/duplicate/rename/update/restore; los cambios de catálogo y metadatos se confirman como unidad y las revisiones/directorios no confirmados se retiran durante rollback. La documentación del protocolo está en §12 de `docs/DISENO_IMPLEMENTACION_PERFILES.md`.

La prueba focal `tests/xray_profiles.sh` ahora inyecta fallos al crear el journal, al escribir el catálogo y al sincronizar directorios después de replace; simula terminación entre escrituras, después de ambos replaces pero antes de retirar journal e interrupción durante rollback. También cubre catálogo inicialmente ausente, recuperación al reabrir y limpieza de operaciones create/duplicate/update/restore. Todas las pruebas usan almacén temporal y clave sintética.

La regresión completa posterior a la última modificación ejecutó **51/51 scripts PASS**, además de Python AST, sintaxis Bash, ShellCheck focal y `git diff --check` PASS. La revisión final del diff y publicación GitHub aún están pendientes; por tanto, PF-01/PF-02 no se declaran cerrados/publicados hasta completar esos pasos. Los temporales ocultos no referenciados creados antes de escribir el journal pueden permanecer tras una caída; la limpieza automática de temporales huérfanos queda fuera de esta corrección.
## 11. Actualización de remediación y temporales huérfanos — 2026-11-04

La sección 10 describe el estado de la remediación transaccional antes de la fase de limpieza y queda superada en cuanto a los temporales ocultos pendientes. El código de la rama de trabajo incorpora ahora:
- recuperación WAL primero y limpieza automática después, bajo el mismo lock exclusivo;
- reconocimiento limitado de .new-<16 hex>, .revision-<16 hex> y temporales atómicos .<destino>.<16 hex>.tmp en rutas controladas;
- validación lstat, tipo, root:root, modos 0700/0600, hardlinks y estructura permitida antes de borrar;
- preservación y advertencia de candidatos sospechosos;
- limpieza del temporal propio de atomic_write() ante fallos de replace/fsync, sin borrar el destino publicado.

La prueba focal tests/xray_profiles.sh pasó, incluidos SIGKILL real en procesos hijos antes del replace y durante publicación de directorios, idempotencia, preservación de artefactos sospechosos (symlink, modo, owner y hardlink), revisión válida intacta y destino publicado preservado ante fallo de fsync posterior a replace. La regresión completa ejecutó 51/51 scripts PASS. Python AST 18/18, bash -n, ShellCheck focal (excluyendo SC2251/SC2034 históricos del archivo), shfmt focal y git diff --check también pasaron.

Toda la prueba de limpieza se ejecutó con almacenes temporales y claves sintéticas. No se leyó /etc/xray-manager/keys/master.key, no se creó ni limpió el almacén live /var/lib/xray-manager/profiles y no se modificó Xray runtime, systemd, firewall, puertos, certificados o red.

Estado: fase implementada y verificada en la VPS de trabajo; revisión final del diff y sincronización GitHub pendientes. Esto no constituye aceptación formal del almacén de perfiles ni cierre de Etapa 5/Etapa 2.
## 12. Revisión correctiva WAL y estado consolidado — 2026-11-04

La remediación PF-01/PF-02 quedó implementada, probada y publicada en `design/user-identity-association-v1`. Los apartados históricos que describen esos hallazgos como abiertos reflejan el estado de la auditoría original y quedan superados por esta sección y por las secciones 10–11 de remediación.

### 12.1 Endurecimiento adicional de recuperación

Se separó la validación integral del journal de su aplicación:
- `_validate_transaction_journal()` valida esquema/versión estricta, cantidad de entradas, rutas permitidas, duplicados, Base64 y límites de snapshots.
- Verifica previamente componentes sin symlinks, directorios padre root-owned con modo 0700 y destinos existentes como archivos regulares root-owned, modo 0600 y `nlink == 1`.
- Valida todas las rutas de directorios a retirar, su tipo/propietario/modo, duplicados y ausencia de solapamiento con destinos de archivos.
- Sólo después de validar todas las entradas se inicia el rollback. Un journal inválido permanece intacto y no produce escrituras parciales de snapshots anteriores.

### 12.2 Pruebas añadidas

`tests/xray_profiles.sh` incluye dos casos de regresión: entrada inválida tardía después de una entrada válida, y lista de directorios de rollback inválida después de un snapshot válido. En ambos casos se comprueba que el catálogo permanece byte a byte igual y que el journal se conserva para diagnóstico. La prueba focal de perfiles pasó con estos casos y las pruebas existentes de recuperación/temporales.

### 12.3 Estado de hallazgos

| Hallazgo | Estado actualizado | Evidencia |
|---|---|---|
| PF-01 — consistencia catálogo/metadatos en update | CORREGIDO | WAL, rollback y fault injection |
| PF-02 — transacciones multiarchivo | CORREGIDO en las operaciones enumeradas | WAL, recuperación idempotente y pruebas de interrupción |
| Temporales huérfanos pre-WAL | CORREGIDO dentro de patrones/rutas documentados | limpieza limitada y pruebas SIGKILL |
| Validación integral previa del WAL | CORREGIDO | preflight completo y pruebas de journal malformado |
| PF-06 — cobertura criptográfica/fallos filesystem | CERRADO DENTRO DEL ALCANCE DE PRUEBAS | ciphertext alterado con SHA-256 recalculado alcanza y falla en AES-GCM; fallos inyectados de escritura parcial, fsync de archivo, replace, fsync de directorio y unlink WAL; crash recovery probado. No se afirma cobertura combinatoria exhaustiva ni fallos físicos del dispositivo |
| PF-07 — esquema integral del catálogo | CORREGIDO DENTRO DEL ALCANCE PROBADO | validación estricta y 18 casos negativos con preservación del archivo |

**Conclusión actualizada al 2026-11-04:** PF-01/PF-02, PF-06 y PF-07 quedan corregidos dentro de los escenarios/contratos documentados y probados. No se declara el almacén formalmente aceptado. Persisten los requisitos funcionales pendientes de Etapa 5; la aceptación del componente limitado requiere decisión expresa del propietario.

### 12.4 Alcance y seguridad

Pruebas con almacenes temporales y clave sintética. No se leyó `master.key`, no se creó ni modificó almacén/perfil live, no se modificó `Xray-Normativa/`, `main`, runtime, systemd, firewall, puertos, certificados o red. La Etapa 5 y la Etapa 2 permanecen ABIERTAS.

## 13. Remediación PF-07 — validación integral del catálogo (2026-11-04)

Se endureció `ProfileStore.load_catalog()` para validar el documento completo antes de devolverlo. El contrato aceptado es `schema_version` entero estricto (no `bool`) igual a 1 y `profiles` como lista con máximo 10000 registros. Cada registro debe contener exactamente `profile_id`, `name`, `created_at` y `modified_at`; los IDs siguen `profile-` más 32 caracteres hexadecimales minúsculos; los nombres deben ser cadenas normalizadas de 1–80 caracteres sin controles; las fechas deben ser timestamps UTC reales `YYYY-MM-DDTHH:MM:SSZ`, y `modified_at` no puede preceder a `created_at`. Se rechazan IDs y nombres duplicados sin coerciones de tipos.

Se añadieron 18 casos de catálogo malformado (versión booleana/string, claves extra, estructura incorrecta, campos ausentes/adicionales, IDs/nombres/fechas con tipos o valores inválidos y duplicados). Cada caso debe producir `ProfileError`, nunca una excepción incidental, y conservar byte a byte el archivo. Un catálogo válido se vuelve a cargar al final de la prueba.

Estado PF-07: **CORREGIDO dentro del contrato de esquema documentado y los casos probados**. No implica aceptación formal del almacén ni cierre de Etapa 5/Etapa 2. La prueba usa exclusivamente almacén temporal y clave sintética.


### 13. Remediación PF-06 — cobertura criptográfica y fallos de filesystem (2026-11-04)

Se amplió `tests/xray_profiles.sh` sin modificar el comportamiento de producción:

- **Autenticidad GCM:** se altera un byte del ciphertext y se recalculan `stored_size_bytes` y `ciphertext_sha256` en el manifiesto. Así se supera deliberadamente la comprobación SHA-256 y se verifica que AES-256-GCM rechaza el blob por autenticación (`ProfileError` controlado). Después se restauran manifiesto y blob originales y se confirma lectura correcta.
- **Escritura parcial:** `os.write` escribe una fracción y después lanza `OSError`; el destino anterior permanece byte a byte igual y el temporal privado se elimina.
- **fsync del archivo:** se inyecta fallo antes de `os.replace`; no se publica contenido parcial, se conserva el destino y se elimina el temporal.
- **replace:** ya existía una prueba de fallo de `os.replace`; el destino se conserva y sólo se retira el temporal no publicado.
- **fsync del directorio:** ya existía una prueba que falla después de `replace`; el destino publicado permanece y no se intenta borrar. La transacción WAL exterior cubre la reversión cuando corresponde.
- **unlink del WAL:** se hace fallar una vez la retirada del journal después de publicar los destinos; el camino de recuperación revierte la transacción, consume el journal y deja catálogo/metadatos coherentes.
- **Crash recovery:** se mantienen las pruebas de terminación abrupta entre reemplazos, después de publicar ambos destinos y durante el rollback; la recuperación posterior es idempotente.

**Resultado:** prueba focal `tests/xray_profiles.sh` PASS; regresión completa `tests/*.sh` **51/51 PASS**, exit code 0. No se modificó `scripts/xray_profiles.py` ni otro código de producción.

**Límites:** las pruebas cubren los puntos de fallo indicados, no todas las permutaciones posibles ni errores del kernel, filesystem/dispositivo o pérdida física de datos que incumplan garantías de durabilidad. PF-06 queda cerrado sólo dentro del alcance de escenarios documentados. Almacén v1.1 aún requiere aceptación expresa; Etapa 5 y Etapa 2 siguen abiertas.

## 14. Decisión del propietario — aceptación formal limitada (2026-11-04)

El propietario emitió aceptación expresa de la versión 1.1 del almacén de persistencia de perfiles, limitada a los contratos, controles y escenarios efectivamente implementados, auditados y probados en este documento y en los informes complementarios PF-06 a PF-12.

**Decisión:** almacén de persistencia de perfiles v1.1 = **ACEPTADO FORMALMENTE COMO COMPONENTE LIMITADO**, con las restricciones y exclusiones siguientes.

### 14.1 Alcance aceptado

La aceptación comprende el componente de persistencia y sus controles probados: cifrado AES-256-GCM y lectura autenticada; contratos estrictos de catálogo, metadatos y manifiestos; revisiones inmutables; validación previa de entradas; transacciones WAL y recuperación; limpieza/reconciliación conservadora de temporales, revisiones y perfiles huérfanos; locking, permisos y controles de filesystem; y los escenarios de fault injection/crash recovery documentados.

PF-01/PF-02 se consideran corregidos en las operaciones y escenarios probados; PF-06 queda cerrado dentro de su cobertura expresamente enumerada; PF-07 queda corregido dentro del contrato probado; PF-08 a PF-12 quedan corregidos dentro de los alcances y pruebas de sus informes. Esta decisión no amplía la evidencia más allá de esos límites.

### 14.2 Exclusiones y pendientes normativos

Esta aceptación **no** declara completa la Etapa 5 ni habilita como disponibles las funciones aún pendientes. Entre ellas:

- vista previa de importación y diff antes de guardar;
- creación desde configuración independiente;
- validación estática Xray por revisión e informe persistido;
- comparación de revisiones/configuraciones;
- historial separado de modificaciones y retención configurable;
- registro de perfil activo y composición integral de conexiones, usuarios/asociaciones y certificados;
- eliminación de perfiles integrada con dependencias y perfil activo;
- activación transaccional, verificación del runtime y rollback;
- backup/restore integral integrado y validado.

Los estados not_validated y not_integrated continúan siendo conservadores y no deben interpretarse como validación o activación.

### 14.3 Límites de la evidencia y seguridad

Los resultados de pruebas acreditan exclusivamente los escenarios sintéticos documentados. No representan cobertura combinatoria exhaustiva, simulación de fallos físicos del almacenamiento ni una prueba integral de operación real. No se ha probado la activación de perfiles ni la conectividad extremo a extremo como consecuencia de esta aceptación.

No se leyó ni utilizó la clave maestra real; no se creó ni modificó almacén/perfil live; no se tocó runtime, servicios, systemd, certificados reales, firewall, puertos o red; no se modificó Xray-Normativa/ ni main; y no se intervino la VPS de pruebas.

### 14.4 Efecto sobre las etapas del proyecto

La aceptación cierra únicamente el punto de control del **componente de persistencia de perfiles v1.1**. La **Etapa 5 permanece ABIERTA** hasta implementar, probar y auditar sus requisitos pendientes. La **Etapa 2 permanece ABIERTA** y no se autoriza su cierre por esta decisión. La prueba integral VLESS WS TLS sigue condicionada a los puntos de control y a la implementación funcional que aún falta.

La decisión fue registrada en PROJECT_STATE.md, docs/PUNTO_CONTROL_ACTUAL.md, docs/CONTINUIDAD_DEL_PROYECTO.md y HISTORY.md. Esta actualización documental queda local; no implica commit, push ni sincronización con GitHub.
