# Diseño técnico — gestor de configuraciones independientes de Xray

**Fecha:** 2026-11-04
**Rama:** design/user-identity-association-v1
**Normativa:** Xray-Normativa/05_Configuraciones_Perfiles/Etapa_5_Configuraciones_Perfiles.md §§ 2–5 y 14; YAML aprobado correspondiente.
**Estado actualizado 2026-11-04:** C-01/C-02/C-03 aceptadas formalmente como componentes limitados; C-04A aceptada/publicada; C-04B implementada, verificada y aceptada formalmente como componente limitado; C-04C no autorizada ni iniciada.

## 1. Objetivo y límites

Diseñar el subsistema de configuraciones JSON independientes administrado desde Etapa 5 → Configuraciones → Gestionar configuraciones de Xray.

Una configuración independiente es un objeto administrado, con identidad propia, metadatos y versiones. No es una conexión, no es un perfil y no constituye una vía de activación. Crear un perfil desde una configuración independiente copiará los bytes de una versión concreta; después no habrá sincronización en ninguna dirección. Eliminar la fuente no elimina la copia que ya pertenece a un perfil.

Este componente no escribirá /etc/xray/config.json, no preparará ni iniciará Xray, no modificará systemd, firewall, puertos, certificados ni red, y no activará configuraciones.

## 2. Contraste normativo

| Requisito aprobado | Diseño propuesto |
|---|---|
| Ver configuración y distinguir guardada/aplicada | Vista de solo lectura; el subsistema independiente informa que no administra activación |
| Crear desde plantilla o archivo vacío | Crear una revisión Borrador; plantilla inicial explícitamente no validada |
| Editar guiado o JSON avanzado | Toda edición crea una revisión nueva; nunca muta una revisión anterior |
| Editar Validada crea Borrador | Nueva revisión sin alterar la última revisión validada |
| Importar sin modificar el original | Lectura de origen; vista previa y confirmación antes de crear |
| Importación incompleta/errónea puede quedar Borrador | Preservar texto UTF-8 importado dentro de límites aunque no pase validación; nunca marcarlo Validado |
| Exportar una o varias | Exportación explícita, verificación byte a byte y política de sobrescritura confirmada |
| Comparar por inbounds/outbounds/routing/DNS/otras | Diff estructural JSON por secciones; comparar solo lectura |
| Eliminar solo el objeto seleccionado | Eliminación transaccional del registro/almacenamiento propio; informes de validación conservados |
| Configuración independiente no activa | Prohibido publicar desde este módulo; activación solo mediante perfiles |

La especificación YAML confirma las mismas reglas, incluida la separación entre configuración independiente y copia de perfil.

## 3. Arquitectura propuesta

### 3.1 Módulo y responsabilidades

- Motor Python: scripts/xray_configurations.py.
- Interfaz Bash: modules/configurations.sh.
- Integración del menú aprobado: modules/main_menu.sh y el punto de entrada correspondiente.
- Pruebas aisladas: tests/xray_configurations.sh.
- Documentación de auditoría/diseño y actualización de continuidad.

El motor Python será la única capa autorizada para leer/escribir el catálogo y los objetos persistentes. Bash solo recopila entradas, muestra vistas previas y presenta resultados; no construye JSON persistente ni modifica archivos del almacén directamente.

No se reutilizará el catálogo de conexiones VLESS/VMess ni los directorios connections/configurations y vmess/configurations: esos artefactos pertenecen a conexiones concretas y tienen contratos diferentes. Tampoco se modificará el almacén de perfiles v1.1 ya aceptado.

### 3.2 Rutas propuestas

- Raíz: /var/lib/xray-manager/configurations.
- Catálogo: /var/lib/xray-manager/configurations/catalog.json.
- Lock exclusivo: /var/lib/xray-manager/configurations/.configurations.lock.
- Journal WAL: /var/lib/xray-manager/configurations/.configurations.transaction.json.
- Objetos: /var/lib/xray-manager/configurations/items/<config_id>/metadata.json.
- Revisiones: items/<config_id>/revisions/rNNNNNN/.
- Blob: config.enc.json.
- Manifiesto: manifest.json.

Identidad inmutable: config- + 32 caracteres hexadecimales aleatorios. Nombre visible único, normalizado y comparado sin distinción de mayúsculas/minúsculas. Revisión monotónica r000001, r000002, etc.

Límites iniciales propuestos: 16 MiB por configuración en texto UTF-8; límite cifrado derivado y validado; 10.000 objetos en catálogo. Los límites deben ser constantes documentadas y probadas, no valores dispersos.

### 3.3 Esquema de catálogo y metadatos

Catálogo raíz estricto:
- schema_version: entero exacto 1.
- configurations: lista de registros con exactamente config_id, name, created_at, modified_at.

Metadatos del objeto:
- schema_version, config_id, name;
- created_at, modified_at;
- current_revision (nulo solo si se permite objeto sin contenido);
- last_validated_revision (nulo si nunca se validó);
- validation_status (not_validated, valid, invalid);
- config_present booleano exacto.

Los esquemas serán cerrados: campos ausentes/adicionales, coerciones de tipo, fechas inválidas, duplicados y punteros incoherentes producirán error controlado sin reparar ni reescribir el archivo inválido.

### 3.4 Contenido, revisiones y cifrado

Cada revisión es inmutable y contiene:
- config.enc.json: sobre cifrado autenticado.
- manifest.json: identidad/revisión, origen, tamaños, huella del ciphertext, versión criptográfica y metadatos de creación.

Se propone AES-256-GCM, nonce aleatorio de 12 bytes y AAD vinculada a config_id y revisión. Se utilizará únicamente la clave maestra existente mediante el helper de lectura ya establecido; el módulo no generará ni regenerará una clave maestra. No se leerá la clave real durante pruebas. Cada revisión se cifra de nuevo, incluso si procede de otra configuración o de un perfil.

Justificación: los JSON pueden contener UUID, credenciales, claves REALITY u otros datos sensibles. El cifrado en reposo evita que el nuevo gestor introduzca una excepción de seguridad respecto al almacén de perfiles. Exportar produce JSON en claro solo en el destino elegido explícitamente; se advertirá al usuario y se creará con permisos restrictivos.

Se conservarán los bytes de texto UTF-8 originales de la revisión. La validación JSON se ejecuta aparte: un documento sintácticamente inválido pero legible podrá guardarse como Borrador conforme a la normativa. No se normalizará ni reescribirá automáticamente el JSON importado.

## 4. Modelo de estados

- Borrador: estado inicial de toda creación/importación/edición. Puede ser incompleto o inválido.
- Validada: solo cuando el validador estático obligatorio emita PASS para los bytes exactos de esa revisión y se conserve el informe asociado.
- Anterior: revisión que ya no es la actual, sin borrar su resultado histórico.
- Aplicada: no es un estado que este gestor pueda asignar. La activación pertenece al flujo de perfiles.

Editar una revisión Validada crea otra revisión Borrador. La revisión Validada anterior y su informe permanecen intactos. Un fallo de validación no destruye ni revierte el Borrador y nunca convierte una revisión en Validada.

## 5. Contrato de operaciones

### 5.1 Crear

- Elegir plantilla o documento vacío.
- El contenido inicial se presenta como Borrador.
- Mostrar vista previa y confirmar.
- Crear objeto, primera revisión, manifiesto y catálogo como una sola operación recuperable.
- No activar ni modificar el archivo usado por Xray.

### 5.2 Importar

- Aceptar ruta absoluta legible y archivo regular; rechazar symlink, hardlink, archivo no regular, tamaño excedido o lectura cambiante.
- No modificar el origen.
- Leer bytes UTF-8 y conservarlos exactamente; no ejecutar ni cargar el JSON como código.
- Intentar parseo estricto para construir la vista previa y el diagnóstico inicial. Si falla, ofrecer conservar el contenido como Borrador, nunca como Validado.
- Mostrar nombre propuesto, tamaño, secciones detectadas, problemas conocidos y destino interno.
- Exigir nombre único y confirmación. La colisión de nombre ofrece elegir otro o reemplazo explícito con historial preservado; nunca sobrescritura silenciosa.

### 5.3 Consultar

- Listar ID, nombre, creación/modificación, revisión actual, estado de validación y estado de activación: “no administrada por configuraciones independientes”.
- Mostrar inbounds, outbounds, routing, DNS y otras secciones cuando el JSON se pueda parsear.
- Si no se puede parsear, mostrar diagnóstico y contenido textual de forma acotada/segura, evitando volcar secretos por defecto.
- Diferenciar siempre guardado, validado y runtime aplicado; este subsistema no puede afirmar lo último.

### 5.4 Editar

- Seleccionar objeto y revisión actual.
- Abrir flujo guiado o JSON avanzado sobre copia temporal privada.
- Cancelar no escribe nada.
- Calcular diff contra la revisión actual y mostrarlo antes de confirmar.
- Guardar como nueva revisión Borrador; no alterar versiones anteriores.
- Si la versión previa estaba Validada, conservar el puntero a la última Validada.

### 5.5 Exportar

- Seleccionar uno o varios objetos/revisiones.
- Solicitar destino y nombre por cada salida o patrón seguro.
- No seguir symlinks ni sobrescribir sin confirmación.
- Escribir de forma atómica con modo restrictivo, releer y comparar bytes con el contenido descifrado.
- Un fallo individual se informa sin cancelar las otras exportaciones.
- Advertir que el archivo exportado está en claro y puede contener credenciales.

### 5.6 Comparar

- Seleccionar dos configuraciones/revisiones.
- Parsear estrictamente ambos JSON.
- Comparar por inbounds, outbounds, routing, DNS y otras secciones.
- Clasificar iguales, diferentes, solo en primera y solo en segunda.
- Ignorar orden de claves de objetos JSON; conservar orden de arrays, que puede ser semánticamente relevante.
- Si uno no es JSON válido, informar que no hay diff estructural; opcionalmente ofrecer diff textual, sin fingir equivalencia semántica.

### 5.7 Eliminar

- Mostrar identidad, nombre, ruta lógica, revisión y estado.
- Confirmación explícita.
- La eliminación afecta solo al objeto independiente seleccionado; nunca perfiles, copias de perfil, archivos exportados o respaldos.
- Una copia ya creada en un perfil es autónoma y permanece aunque se elimine su fuente.
- Los informes de validación son históricos y se conservan aunque el objeto se elimine, conforme a la normativa.
- Ejecutar borrado con journal/rollback y limpieza segura; no permitir borrado parcial silencioso.

## 6. Transacciones y controles de filesystem

- Lock exclusivo con flock para todas las mutaciones y lecturas que necesiten consistencia.
- Directorios root:root 0700; archivos root:root 0600; rechazo de symlink/hardlink.
- Validación completa de rutas/objetos con lstat antes de leer, modificar o limpiar. No reparar automáticamente permisos de candidatos sospechosos.
- Escrituras atómicas con temporal privado, fsync de archivo, replace y fsync del directorio.
- Journal WAL con snapshots anteriores de catálogo/metadatos y lista cerrada de rutas permitidas. Validar el journal completo antes de ejecutar rollback.
- Recuperación idempotente al adquirir lock; limpieza posterior y conservadora de temporales/revisiones/objetos huérfanos.
- Las operaciones create/import/update/rename/delete deben definir punto de commit, rollback y tratamiento de fallo ambiguo después de replace/fsync.
- Nunca reutilizar ni modificar el journal del almacén de perfiles; el nuevo almacén tendrá su propio protocolo y pruebas.

## 7. Relación con el validador estático

El almacén y el validador serán componentes separados:

- El almacén conserva bytes, revisiones, metadatos y punteros.
- El validador recibe una copia inmutable de una revisión y devuelve un informe.
- El informe se vincula a config_id, revisión, SHA-256 de los bytes exactos, versión del gestor, versión/binario de Xray, fecha, tipo de prueba, errores y advertencias.
- Solo un informe estático PASS correspondiente al hash exacto podrá promover la revisión a Validada.
- El validador nunca modifica la configuración ni aplica cambios.

La validación estática normativa incluye sintaxis JSON estricta, estructura Xray, parámetros requeridos, tipos/valores, compatibilidad detectable con versión instalada y referencias/conflictos detectables. Se estudiará el uso del comando de prueba del binario Xray sobre un archivo temporal privado. No se iniciará una segunda instancia daemon ni se sustituirá la instancia activa. La prueba de funcionamiento, si se diseña, será separada de la validación estática y queda fuera de este primer componente.

## 8. Integración futura con perfiles

Al crear un perfil desde una configuración independiente:
1. seleccionar objeto y revisión fuente;
2. leer y autenticar la revisión;
3. mostrar preview y resultado de validación disponible;
4. copiar los bytes exactos a una nueva revisión del perfil, cifrándolos de nuevo con AAD propia del perfil;
5. registrar origen independent_config con ID/revisión de procedencia;
6. confirmar que los dos almacenes quedan desacoplados.

La eliminación o modificación posterior de la configuración independiente no afecta el perfil. La integración requerirá una operación pública segura del almacén de perfiles o una interfaz interna estable; no se accederá directamente a sus rutas desde Bash.

## 9. CLI propuesta

Subcomandos de solo gestión:
- list
- create --name ... --template ...
- import --name ... --source ...
- show --config-id ...
- export --config-id ... --revision ... --destination ...
- update --config-id ... --input ...
- rename --config-id ... --name ...
- compare --first ... --second ...
- delete --config-id ...
- revisions --config-id ...

Los comandos devuelven JSON estructurado para la interfaz Bash. No habrá comando apply ni activate.

## 10. Secuencia de implementación propuesta

**Fase C-01 — contrato y persistencia**
- [x] CLI de catálogo, identidad, metadatos, cifrado, manifiesto, revisiones y WAL.
- [x] create vacío/plantilla, list/show y pruebas de corrupción/fallos.
- [x] Sin integración del menú; persistencia aislada.
- Auditoría: `docs/AUDITORIA_C01_GESTOR_CONFIGURACIONES_2026-11-04.md`.
- Estado: implementado y probado localmente; pendiente de aceptación expresa.

**Fase C-02 — importación y exportación**
- [x] Importación de archivo sin modificar fuente, preview, borrador inválido y exportación verificada.
- [x] Pruebas de symlink/hardlink, UTF-8/BOM, tamaño, sobrescritura y fallos de escritura.
- Auditoría: `docs/AUDITORIA_C02_IMPORTACION_EXPORTACION_2026-11-04.md`.
- Estado: implementado, auditado y aceptado formalmente como componente limitado conforme a `docs/AUDITORIA_C02_IMPORTACION_EXPORTACION_2026-11-04.md`.

**Fase C-03 — edición, diff y comparación**
- [x] `preview-edit` y `edit` con copia de origen, hash confirmado, revisión base y confirmación explícita.
- [x] Nueva revisión inmutable cifrada; revisión anterior preservada y metadata publicada con WAL.
- [x] Diff estructural JSON Pointer por secciones, sin valores; objetos ignoran orden de claves y arrays conservan orden.
- [x] Comparación de solo lectura entre objetos/revisiones; JSON inválido informa que el diff estructural no está disponible.
- [x] Historial de revisiones y pruebas de concurrencia optimista/hash, BOM, secretos y recuperación SIGKILL.
- Auditoría: `docs/AUDITORIA_C03_EDICION_DIFF_COMPARACION_2026-11-04.md`.
- Estado: implementado, verificado y aceptado formalmente como componente limitado (2026-11-04). No cierra la Etapa 5.

**Fase C-04 — interfaz y eliminación (desglosada por autorización)**
- [x] C-04A: eliminación segura transaccional; auditoría `docs/AUDITORIA_C04A_ELIMINACION_SEGURA_2026-11-04.md`; aceptada y publicada.
- [x] C-04B: exportación múltiple mediante manifiesto explícito, preview/hash de confirmación y resultados parciales; auditoría `docs/AUDITORIA_C04B_EXPORTACION_MULTIPLE_2026-11-04.md`; implementada, verificada y aceptada formalmente como componente limitado.
- [ ] C-04C: integración del menú Bash; no autorizada ni iniciada.
- C-04 no se considera completa hasta completar las fases autorizadas, su auditoría y aceptación.

**Fase C-05 — integración con validador**
- Contrato de informes y promoción a Validada. Esta fase depende del diseño/implementación del validador estático, que se auditará por separado.

**Fase C-06 — integración perfil desde configuración independiente**
- Copia independiente hacia perfil con procedencia verificable; sin sincronización.

Cada fase requiere auditoría, documentación técnica, regresión completa y aceptación antes de avanzar. No se cierra Etapa 5 por terminar este subsistema.

## 11. Matriz mínima de aceptación

| Área | Casos mínimos |
|---|---|
| Esquemas | campos ausentes/adicionales, tipos incorrectos, bool en enteros, fechas inválidas, duplicados, punteros incoherentes |
| Seguridad | symlink/hardlink, propietario/modo incorrectos, path traversal, archivo cambiante, permisos de exportación |
| Criptografía | ciphertext alterado con hash recalculado, clave equivocada sintética, AAD/ID/revisión intercambiados |
| Transacciones | fallo write/replace/fsync/unlink WAL, SIGKILL antes/después de publicación y durante rollback |
| Versionado | revisión nueva, revisión anterior intacta, Validada anterior preservada al editar |
| Importación | JSON válido, incompleto, sintácticamente inválido, UTF-8 inválido, BOM, archivo vacío, exceso de tamaño |
| Exportación | bytes exactos, destino existente, symlink, fallo parcial en lote, relectura posterior |
| Diff | iguales, cambios de claves/arrays, elementos solo en un lado, secciones desconocidas, JSON inválido |
| Independencia | eliminar fuente conserva copia de perfil; editar fuente no altera perfil y viceversa |
| No activación | ninguna operación escribe config runtime, llama systemctl, abre puertos o cambia firewall |

Todas las pruebas utilizarán directorios temporales y claves sintéticas. No se leerá master.key real.

## 12. Decisiones técnicas que requieren aprobación antes de implementar

1. Cifrado en reposo: se recomienda AES-256-GCM con la clave maestra existente y AAD por ID/revisión, alineado con perfiles.
2. Límite de tamaño: se propone 16 MiB por documento, igual al límite de perfiles.
3. Borradores con JSON inválido: se recomienda preservar bytes UTF-8 importados como Borrador y no normalizarlos.
4. Plantilla inicial: se recomienda plantilla mínima marcada Borrador; no prometer que es válida para cualquier versión de Xray.
5. Alcance inicial: implementar primero C-01 y C-02; mantener C-03 a C-06 como fases separadas y sujetas a aceptación.

**Estado actualizado (2026-11-04):** C-01 aceptado como componente limitado. C-02 implementado localmente y auditado; pendiente de aceptación. C-03–C-06 siguen sin implementar. No se modificó runtime ni se usó clave real.

## Addendum C-03 — implementación local (2026-11-04)

C-03 añade `preview-edit`, `edit`, `compare` y `revisions` al motor. La edición recibe un archivo fuente UTF-8 (máximo 16 MiB), preserva bytes/BOM, exige SHA-256 de preview, revisión base esperada y confirmación; JSON inválido requiere aceptación expresa. Cada edición crea una revisión AES-256-GCM inmutable con `source=edit` y estado de validación pendiente. El WAL admite sólo las rutas exactas de staging/revisión para recuperación.

El diff ignora orden de claves JSON, conserva orden de arrays, agrupa por secciones y no devuelve valores. Está limitado a 10.000 diferencias, 100.000 nodos y profundidad 128; los casos no JSON válido no producen diff estructural. La comparación es de solo lectura entre objetos/revisiones.

Prueba focal PASS; regresión `tests/*.sh` 53/53 PASS; AST/compilación Python, `bash -n` global y `git diff --check` PASS; ShellCheck de la nueva prueba focal PASS. C-03 está implementada y auditada localmente, pendiente de aceptación. C-04–C-06 no iniciadas. Etapa 5/Etapa 2 abiertas.


**Decisión vigente (2026-11-04):** C-03 queda aceptada formalmente como componente limitado conforme a `docs/AUDITORIA_C03_EDICION_DIFF_COMPARACION_2026-11-04.md`. C-04 sigue pendiente de diseño, aprobación y autorización independientes. Etapa 5 y Etapa 2 permanecen abiertas.

## Addendum C-04A — eliminación segura implementada (2026-11-04)

El propietario aprobó el diseño C-04 y autorizó iniciar exclusivamente C-04A. Se implementaron preview-delete y delete en scripts/xray_configurations.py.

La vista previa verifica catálogo/metadatos, estructura del objeto, todas las revisiones, hash del ciphertext y autenticación AES-256-GCM; informa ID, nombre, ruta, revisión, cantidad de revisiones, estado del almacén e integridad. La eliminación exige --confirm, --expected-name coincidente con la vista previa y --assert-not-active.

El almacén independiente no gestiona runtime ni puede detectar aplicaciones manuales externas. Por ello runtime_activity_verified=false y la eliminación requiere una afirmación explícita del operador de que el elemento no está aplicado ni en uso. No se interpreta not_managed_by_independent_configurations como prueba de inactividad runtime.

Se incorporó WAL v2 exclusivo para delete: estado prepared revierte rename/catálogo; estado committed finaliza la limpieza del tombstone. El journal valida esquema, snapshot y patrones exactos de rutas. Se conserva el protocolo WAL v1 de C-01/C-02/C-03. La operación elimina sólo el objeto independiente y su registro; no modifica perfiles/copias, exportaciones ni respaldos.

Auditoría: docs/AUDITORIA_C04A_ELIMINACION_SEGURA_2026-11-04.md. Prueba focal PASS; regresión completa 54/54 PASS; Python compile, Bash syntax, ShellCheck focal y git diff --check PASS.

Estado: C-04A implementada y auditada localmente, pendiente de aceptación formal. C-04B (exportación múltiple) y C-04C (interfaz Bash) no iniciadas. Etapa 5 y Etapa 2 continúan ABIERTAS. Sin commit/push/sync.


## 12. C-04B — contrato de exportación múltiple (2026-11-04)

La exportación múltiple usa un manifiesto JSON estricto de hasta 100 entradas. Cada entrada identifica `config_id`, revisión concreta o `null` para resolver la actual durante preview, destino absoluto y booleano `overwrite` individual. El manifiesto debe ser regular, root:root 0600, sin symlink/hardlink y hasta 1 MiB.

CLI: `preview-export-batch --manifest` y `export-batch --manifest --expected-manifest-sha256 --expected-preview-sha256 --confirm`. El primer hash liga el archivo de manifiesto; el segundo liga el resultado de preview, incluyendo la revisión resuelta y el estado de cada destino. La ejecución reconstruye el preview y aborta si cualquiera cambió; no vuelve a elegir una revisión actual diferente.

Cada salida reutiliza la escritura individual atómica/0600 y verificación byte a byte. Los errores son por entrada y no cancelan las restantes; el resultado reporta éxitos/errores y advierte que los archivos están en claro. Destinos duplicados bloquean todas las entradas afectadas. No se añadió patrón de nombres ni generación automática de rutas: cada destino se declara explícitamente.

Estado C-04B: implementada, verificada y aceptada formalmente como componente limitado. C-04C (menú Bash) no autorizada/iniciada. Sin commit/push/sync.
