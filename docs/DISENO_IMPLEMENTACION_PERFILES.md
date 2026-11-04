# Diseño e implementación inicial — almacén de perfiles v1.1

**Fecha:** 2026-11-03
**Rama de trabajo:** `design/user-identity-association-v1`
**Estado:** implementación local con cifrado autenticado de revisiones; integración de validación nativa, activación y eliminación segura pendientes; aceptación formal del subsistema pendiente.

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
- El manifiesto conserva SHA-256 y tamaño del JSON descifrado; después de autenticar GCM, se verifican ambos y se vuelve a validar el JSON estricto.
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
- Validación de fallos de filesystem y recuperación de temporales huérfanos.
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

Verificación ejecutada en esta iteración: `tests/*.sh` 51/51 PASS; Python AST 18/18; `bash -n` de todos los shell scripts PASS; ShellCheck focal PASS; shfmt de los dos archivos nuevos PASS; `git diff --check` PASS después de normalizar el formato Markdown. Ninguna prueba utiliza `/etc/xray-manager/keys/master.key` ni `/var/lib/xray-manager/profiles` reales.

## 9. Límites operativos

- No se creó ni inicializó `/var/lib/xray-manager/profiles` en la VPS; las pruebas usan almacenes temporales.
- No se creó ningún perfil real.
- No se leyó, creó, modificó ni rotó `/etc/xray-manager/keys/master.key`.
- No se modificó la conexión live `Prueba-VLESS-WS-Real`.
- No se escribió `/etc/xray/config.json`, no se ejecutó staging runtime desde un perfil, no se ejecutó `xray_service_prepare`, no se creó/inició/habilitó `xray.service`.
- No se modificaron firewall, puertos, certificados ni reglas de red.
- Xray sigue fuera del runtime; la Etapa 2 permanece ABIERTA.
