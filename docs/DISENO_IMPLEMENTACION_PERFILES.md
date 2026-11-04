# Diseño e implementación inicial — almacén de perfiles v1.1

**Fecha:** 2026-11-03
**Rama de trabajo:** `design/user-identity-association-v1`
**Estado:** implementación v1.1 publicada y sincronizada byte a byte; integración de validación nativa, activación y eliminación segura pendientes; aceptación formal del subsistema pendiente.

## 1. Base funcional y decisiones

La referencia funcional es `Xray-Normativa/05_Configuraciones_Perfiles/Etapa_5_Configuraciones_Perfiles.md` y su YAML asociado. Se contrastaron las operaciones de gestión de perfiles, independencia, historial y el requisito de no almacenar credenciales ni claves privadas en texto plano.

Decisiones vigentes:

- La activación sólo podrá ocurrir mediante el flujo de cambio de perfil activo de Etapa 5. No existe activación de conexiones independientes.
- **Todo el JSON de cada revisión se cifra en reposo con AES-256-GCM**, no sólo campos seleccionados. Así se cubren credenciales, UUID, claves privadas y otros valores sensibles presentes en la configuración.
- Se utiliza la clave maestra existente del gestor, por defecto `/etc/xray-manager/keys/master.key`. El módulo sólo la lee mediante `certificate_crypto.load_master_key`; no la crea, regenera, reemplaza ni rota.
- Si la clave falta, tiene permisos/propietario incorrectos o no autentica el contenido, la operación falla de forma cerrada. No se guarda una revisión sin cifrar como alternativa.
- Guardar, consultar, duplicar o restaurar una revisión no activa ni publica configuración runtime.
- No se modifica `Xray-Normativa/`.

## 2. Archivos del componente

- `scripts/xray_profiles.py`: CLI, persistencia y cifrado autenticado del catálogo, perfiles y revisiones.
- `modules/profiles.sh`: navegación y operaciones disponibles desde el menú.
- `tests/xray_profiles.sh`: pruebas sintéticas aisladas, incluida criptografía.
- `bin/xray-manager`: carga el módulo de perfiles.
- `modules/main_menu.sh`: enruta la opción de configuraciones/perfiles/respaldo al submenú normativo.
- `tests/stage1_menu.sh` y `tests/smoke.sh`: regresión de navegación y carga del módulo.

El directorio base ya estaba declarado en `config/paths.sh` y preparado por `install.sh`; no fue necesario modificar esas rutas.

## 3. Estructura de almacenamiento

Ubicación prevista: `/var/lib/xray-manager/profiles/`.

```text
profiles/
├── catalog.json
├── .profiles.lock
└── profiles/
    └── profile-<uuid>/
        ├── metadata.json
        └── revisions/
            ├── r000001/
            │   ├── config.enc.json
            │   └── manifest.json
            └── r000002/
                ├── config.enc.json
                └── manifest.json
```

- `catalog.json`: versión de esquema y lista de IDs/nombres/fechas; no contiene el JSON de configuración.
- `metadata.json`: ID inmutable, nombre, descripción, notas, fechas, revisión actual, presencia de JSON y estado de validación.
- `config.enc.json`: envelope JSON con versión, algoritmo, perfil/revisión, nonce aleatorio y ciphertext Base64. No contiene el JSON original en claro.
- `manifest.json`: perfil/revisión, fecha, tamaño original, tamaño almacenado, SHA-256 del ciphertext, formato criptográfico, origen y estado de validación. No contiene credenciales ni claves.
- `.profiles.lock`: bloqueo exclusivo `flock` para serializar operaciones del almacén.

El ID interno no depende del nombre. Renombrar no mueve ni reescribe los blobs. Duplicar genera un ID y directorio nuevos y vuelve a cifrar el contenido con un nonce nuevo y AAD de la nueva identidad.

## 4. Contrato criptográfico

- Algoritmo: AES-256-GCM mediante `cryptography`.
- Clave: 32 bytes, leída desde la clave maestra existente; el cargador exige directorio padre `root:root 0700` y archivo `root:root 0600`, regular, sin symlink ni hardlinks.
- Nonce: 96 bits (12 bytes) aleatorios por cifrado, generado con `secrets.token_bytes`.
- AAD: `xray-manager:profile-config:v1:<profile_id>:<revision>`. Vincula el ciphertext a su perfil y revisión; copiar un blob a otra identidad/revisión no permite descifrarlo.
- El envelope incluye `format_version`, `algorithm`, `profile_id`, `revision`, `nonce` y `ciphertext`. Se rechazan campos ausentes/extra, JSON duplicado, codificación Base64 inválida, versión/algoritmo no admitidos y longitudes incorrectas.
- El manifiesto conserva el tamaño del JSON en claro y el tamaño/SHA-256 del blob cifrado. Al leer, primero se comprueban tamaño y SHA-256 del blob; después se autentica AES-GCM y se verifica el tamaño del plaintext y el JSON estricto. No se almacena un hash del plaintext en el manifiesto.
- Sólo el blob cifrado se escribe a disco, con `root:root 0600`, dentro de directorios `root:root 0700`; la escritura es atómica y sincronizada. El plaintext existe transitoriamente en memoria para validar/cifrar y para operaciones que requieren recuperarlo.
- El cargador no crea automáticamente la clave maestra. La pérdida de la clave impide recuperar las revisiones; no existe todavía rotación ni recuperación de clave en este subsistema.

## 5. Operaciones implementadas

- Crear perfil desde cero sin configuración.
- Crear perfil desde un archivo JSON externo sin modificar el origen; normaliza y cifra el JSON.
- Consultar catálogo, metadatos y revisiones; la consulta del catálogo verifica autenticidad/integridad de la revisión actual.
- Modificar nombre, descripción, notas y/o configuración.
- Crear revisión nueva al cambiar el JSON; conservar las anteriores.
- Duplicar perfil con copia independiente y cifrado nuevo asociado a la identidad destino.
- Renombrar perfil sin modificar blobs.
- Consultar historial de revisiones y verificar autenticidad/integridad.
- Restaurar una revisión antigua creando una nueva revisión cifrada; nunca sobrescribe la revisión anterior.
- Menú principal y submenú de perfiles integrados.

Los nombres son únicos sin distinguir mayúsculas/minúsculas. Las configuraciones se limitan a 16 MiB y deben ser JSON UTF-8 estricto, sin BOM, claves duplicadas ni valores no finitos, y el nivel superior debe ser un objeto.

## 6. Estados y límites deliberados

Una revisión importada o modificada registra `json_syntax=pass`, `xray_static=not_run` y `status=pending`. El perfil conserva `validation_status=not_validated`. **La sintaxis JSON correcta y el descifrado autenticado no equivalen a validación Xray.** No se marca ninguna revisión como Validada.

Pendiente:

- Integrar validación estática completa y `xray run -test` sin iniciar el servicio, conservando informe por revisión.
- Modelo de última revisión Validada y comparación visual de revisiones.
- Historial de modificaciones separado del historial de versiones.
- Retención configurable y limpieza coordinada.
- Registro activo JSON y detección de discrepancias con runtime.
- Activación transaccional, verificación real y rollback.
- Eliminación segura: sólo después de validar el registro activo y dependencias. La opción del menú permanece deshabilitada.
- Integración con composición de configuraciones de conexiones, usuarios/asociaciones y referencias de certificados.
- Validación de fallos de filesystem y recuperación automática de temporales huérfanos (implementada y probada el 2026-11-04).
- Política de rotación y recuperación de la clave maestra, y migración explícita si se encontraran almacenes de perfiles anteriores en texto plano.

El lector rechaza fail-closed cualquier revisión cuyo manifiesto no declare `aes-256-gcm`; no hay downgrade ni migración automática desde el formato plaintext inicial. La inspección de esta VPS no ha creado `/var/lib/xray-manager/profiles`, por lo que no hay datos live de perfiles que migrar.

El campo de estado activo se muestra como no integrado; no se presume que todo perfil esté inactivo. El registro activo legacy de `lib/system.sh` no se modifica en esta fase.

## 7. Controles de seguridad

- Ejecución root obligatoria.
- Rechazo de componentes simbólicos en rutas del almacén.
- Directorios y archivos de datos deben ser reales, root-owned y sin hardlinks.
- Bloqueo exclusivo y escritura atómica con `fsync`.
- No se sobrescriben revisiones existentes.
- JSON de origen abierto con `O_NOFOLLOW`, comprobación de inode, tipo y número de enlaces.
- No se registran ni imprimen contenidos de configuración ni plaintext criptográfico.
- La clave maestra se lee sólo al operar sobre una revisión con JSON; no se genera ni se modifica.
- La pérdida o sustitución de `master.key` hace irrecuperables los datos cifrados; proteger la clave y sus respaldos es requisito operativo.

## 8. Pruebas focales

`tests/xray_profiles.sh` cubre:

- alta desde cero y desde JSON;
- uso de una clave maestra sintética temporal, no la clave real;
- ausencia del marcador secreto en `config.enc.json` y recuperación byte/JSON equivalente mediante descifrado;
- metadatos de algoritmo/formato, permisos y tamaño;
- rechazo de clave ausente sin crearla ni dejar perfiles parciales;
- rechazo de clave incorrecta y de ciphertext alterado (fallo de autenticación GCM);
- copia independiente, con nuevo cifrado ligado al ID destino;
- unicidad de nombres, modificación con nueva revisión, renombrado sin alterar el blob y restauración no destructiva;
- JSON con claves duplicadas/estructura incorrecta, symlink/hardlink, almacén simbólico y concurrencia;
- navegación/alta/consulta desde el menú con almacén y clave temporales.
- limpieza de temporales exactos en raíz/perfil/revisión, árboles .new-*/.revision-*, validación de owner/group/mode/nlink, preservación de anomalías, revisión válida intacta, idempotencia, SIGKILL y fallo de os.replace().

Verificación ejecutada en esta iteración: `tests/*.sh` 51/51 PASS; Python AST 18/18; `bash -n` de todos los shell scripts PASS; ShellCheck focal PASS; shfmt de los dos archivos nuevos PASS; `git diff --check` PASS después de normalizar el formato Markdown. Ninguna prueba utiliza `/etc/xray-manager/keys/master.key` ni `/var/lib/xray-manager/profiles` reales.

## 9. Límites operativos

- No se creó ni inicializó `/var/lib/xray-manager/profiles` en la VPS; las pruebas usan almacenes temporales.
- No se creó ningún perfil real.
- No se leyó, creó, modificó ni rotó `/etc/xray-manager/keys/master.key`.
- No se modificó la conexión live `Prueba-VLESS-WS-Real`.
- No se escribió `/etc/xray/config.json`, no se ejecutó staging runtime desde un perfil, no se ejecutó `xray_service_prepare`, no se creó/inició/habilitó `xray.service`.
- No se modificaron firewall, puertos, certificados ni reglas de red.
- Xray sigue fuera del runtime; la Etapa 2 permanece ABIERTA.


## 10. Publicación y sincronización

- Commit funcional inicial: `03b63ca109a2fabb262924daf5d2fe4a683b23d8`.
- Reconciliación de contenido byte a byte con el índice Git de la VPS: `4cec7496585390adbe72d8887cb6dacd94743c32`.
- La publicación conserva exactamente los blobs Git del índice local; el árbol remoto se comparó con `git write-tree` de la VPS y ambos dieron el mismo SHA de árbol.
- Rama `design/user-identity-association-v1`; `main` no se modificó. `Xray-Normativa/` no se modificó. `scripts/__pycache__/` se preservó y excluyó.
- Estado de aceptación: pendiente de decisión formal del propietario. La publicación no declara completada Etapa 5 ni habilita runtime.


## 11. Auditoría formal v1.1 — 2026-11-03

La revisión formal de solo lectura contra Etapa 5 está registrada en `docs/AUDITORIA_FORMAL_PERFILES_V1_1_2026-11-03.md`. Se confirma el alcance de almacenamiento cifrado y versionado implementado, pero se identificó un bloqueo de consistencia transaccional en `update()` ante fallo de escritura del catálogo, reproducido mediante inyección de fallo en un almacén temporal. También permanecen pendientes los requisitos de validación Xray, vista previa/diff, comparación/retención/historial, composición y activación.

**Estado de aceptación:** no se recomienda aceptar todavía el subsistema v1.1 como componente terminado hasta resolver y probar la consistencia entre catálogo y metadatos en los caminos de actualización/restauración/renombrado y la recuperación ante fallos/crash. No se modificó código durante la auditoría. La decisión final corresponde al propietario.


## 12. Fase correctiva PF-01/PF-02 — journal transaccional (2026-11-03)

Se incorporó un journal de recuperación en `.profiles.transaction.json`, protegido por el lock exclusivo existente. La presencia del journal significa que la transacción no alcanzó su punto de confirmación y debe revertirse.

### 12.1 Secuencia de commit

1. Bajo `flock`, leer los bytes previos de los destinos persistentes y preparar los nuevos bytes en memoria.
2. Escribir el journal mediante `atomic_write` (archivo temporal exclusivo, `fsync` del archivo, `os.replace` y `fsync` del directorio raíz). El journal conserva snapshots Base64 del catálogo/metadatos anteriores y las rutas de directorios que deben retirarse si hay rollback. No almacena configuraciones ni secretos.
3. Escribir cada destino mediante `atomic_write`, que sincroniza el archivo y su directorio.
4. Retirar el journal y sincronizar el directorio raíz. La ausencia durable del journal es el punto de confirmación.

Si hay error de escritura, se reproduce la recuperación antes de propagar el error. Si el proceso termina abruptamente, la siguiente operación que obtiene el lock ejecuta recuperación antes de leer o mutar el almacén.

### 12.2 Recuperación

- Validar tipo, propietario, permisos, estructura, Base64 y rutas permitidas del journal; cualquier journal inválido provoca fallo cerrado.
- Restaurar snapshots anteriores de catálogo y metadatos con escritura atómica; eliminar revisiones/directorios nuevos indicados por el journal.
- Sincronizar los directorios afectados, retirar el journal y sincronizar la raíz.
- El procedimiento es idempotente: si la recuperación también se interrumpe, el journal permanece y la siguiente operación repite el rollback.
- Las rutas se limitan a `catalog.json`, `profiles/<id>/metadata.json`, `profiles/<id>` y `profiles/<id>/revisions/rNNNNNN`; no se aceptan rutas absolutas, traversal ni destinos arbitrarios.

### 12.3 Operaciones cubiertas

- `rename()` y `update()` confirman catálogo y metadatos como una sola unidad recuperable.
- `restore()` confirma la nueva revisión actual junto con metadatos/catálogo; si se revierte, elimina la revisión no confirmada.
- `create()` y `duplicate()` publican el directorio completo, sincronizan `profiles/` y registran el catálogo en una transacción que elimina el nuevo directorio durante rollback.
- `update()` elimina la nueva revisión si la transacción de metadatos/catálogo no confirma.

### 12.4 Límites y tratamiento de fallos

El journal protege las operaciones persistentes coordinadas enumeradas, pero no pretende hacer atómica la creación de cada archivo interno de una revisión: las revisiones se construyen en directorios temporales y se publican por rename; una caída anterior al registro transaccional puede dejar un temporal oculto no referenciado, que no se interpreta como revisión válida. La limpieza de temporales huérfanos se implementó como fase correctiva independiente y se ejecuta automáticamente después de recover_transaction(), todavía bajo el lock exclusivo. Su contrato y límites están descritos en §13.

Un fallo de almacenamiento que impida escribir el journal o completar el rollback puede dejar el journal pendiente; el gestor falla cerrado y no permite nuevas operaciones hasta recuperar el estado. No se debe borrar manualmente el journal ni los snapshots. La ausencia del journal después del `fsync` de la raíz indica commit; si la sincronización de la retirada falla, el código intenta recrear el journal y revertir. Una pérdida física de almacenamiento que viole las garantías de `fsync` del filesystem/dispositivo no puede ser resuelta por software.

### 12.5 Pruebas añadidas

`tests/xray_profiles.sh` incluye fallo al crear el journal, fallo de escritura del catálogo, fallo de `fsync` del directorio después de reemplazar metadatos, terminación abrupta entre escrituras, terminación después de reemplazar ambos destinos pero antes de retirar el journal, interrupción durante el propio rollback, catálogo inicialmente ausente y recuperación idempotente al reabrir el almacén. También verifica rollback y limpieza en create/duplicate/update/restore. Todas las pruebas usan almacén temporal y clave sintética.
## 13. Fase correctiva — limpieza segura de temporales huérfanos (2026-11-04)

### 13.1 Orden y coordinación

ProfileStore.locked() adquiere el lock exclusivo, ejecuta primero recover_transaction() y sólo si la recuperación termina correctamente invoca cleanup_orphan_temps(). La limpieza nunca se ejecuta fuera del lock ni antes del WAL. Un journal inválido o una recuperación fallida bloquea la operación y evita que la limpieza se ejecute.

### 13.2 Patrones y ubicaciones admitidos

Se reconocen únicamente nombres generados por el código:
- .new- seguido de exactamente 16 caracteres hexadecimales, sólo dentro de profiles/.
- .revision- seguido de exactamente 16 caracteres hexadecimales, sólo dentro de profiles/<profile_id>/revisions/.
- Temporales atómicos .<filename>.<16 hex>.tmp sólo en ubicaciones controladas y para destinos conocidos: raíz (catalog.json y .profiles.transaction.json), perfil (metadata.json), revisión (config.enc.json y manifest.json).

No se usa rglob(), no se recorren rutas arbitrarias ni se siguen enlaces simbólicos. Los IDs de perfil recorridos deben corresponder al formato emitido por el generador (profile- más 32 hexadecimales); las revisiones publicadas se preservan.

### 13.3 Validación antes de eliminar

Cada candidato se inspecciona mediante lstat() sin seguir symlinks. Se exige tipo esperado, propietario y grupo root, permisos exactos (directorios 0700, archivos 0600) y nlink == 1 para archivos. Los árboles .new-* y .revision-* se validan con una estructura explícita y profundidad acotada antes de retirarlos.

Si hay un tipo, propietario, grupo, modo, hardlink o contenido de directorio inesperado, el candidato se conserva íntegro y se emite una advertencia. No se corrigen permisos de candidatos sospechosos ni se intenta limpiar parcialmente un árbol no validado.

### 13.4 Escritura atómica

atomic_write() limpia su propio nombre temporal si la escritura, os.replace() o el fsync posterior fallan. La limpieza sólo intenta retirar el nombre temporal de esa operación; nunca elimina el destino. Si replace() ya publicó el destino y falla el fsync del directorio, el destino publicado permanece y el nombre temporal ya no existe.

### 13.5 Pruebas añadidas y límites

tests/xray_profiles.sh cubre temporales exactos en ubicaciones permitidas, staging .new-*/.revision-*, SIGKILL real antes de replace() y durante la publicación de perfiles/revisiones, idempotencia, preservación de revisiones válidas, symlinks, owner/group incorrectos, modos inseguros, hardlinks, nombres no canónicos, fallo inyectado de replace() y fallo de fsync del directorio después de publicar el destino. Todas las pruebas usan almacenes temporales y claves sintéticas.

La regresión completa del repositorio ejecutó 51/51 scripts PASS. AST Python 18/18, bash -n, ShellCheck focal con exclusiones históricas SC2251/SC2034, shfmt focal y git diff --check PASS. La limpieza no se ejecutó sobre /var/lib/xray-manager/profiles, no se leyó master.key y no se modificó runtime, servicio, firewall, puertos, certificados o red. Esta fase no equivale a aceptación formal del subsistema de perfiles ni cierra Etapa 5 o Etapa 2.
## 14. Validación integral previa a recuperación WAL (2026-11-04)

La recuperación transaccional se divide ahora en dos fases. `_validate_transaction_journal()` valida el documento completo, todos los snapshots, destinos, directorios padre y rutas de eliminación antes de permitir mutaciones. Comprueba rutas permitidas y no duplicadas, Base64 estricto, límites de tamaño, ausencia de symlinks, tipo/propietario/modo esperado y ausencia de solapamientos entre destinos y directorios de rollback. Sólo después `recover_transaction()` aplica los snapshots y retira directorios.

Un journal inválido se conserva y provoca fallo cerrado. Las pruebas comprueban que una entrada inválida tardía o una ruta de eliminación inválida no permite aplicar parcialmente una entrada válida anterior. Esta defensa evita que la validación incremental produzca un rollback parcial ante un journal corrupto o manipulado.
