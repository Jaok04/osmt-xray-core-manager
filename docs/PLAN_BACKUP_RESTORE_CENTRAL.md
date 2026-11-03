# Diseño de backup/restore compartido — conexiones y certificados centrales

**Versión:** 1.6
**Fecha:** 2026-11-03
**Estado:** ALCANCE INCREMENTAL V1 APROBADO / CONTENEDOR CIFRADO V1 IMPLEMENTADO Y VERIFICADO / CONTRATO DE MANIFIESTO EN DISEÑO / ORQUESTACIÓN BACKUP-RESTORE PENDIENTE
**Ámbito:** contenedor criptográfico neutral y primera versión incremental de snapshot para VLESS/VMess/metadatos de identidades/certificados TLS centrales. Las categorías normativas no cubiertas se declaran explícitamente como no soportadas; extensible a protocolos futuros mediante adaptadores.

## 1. Objetivo

La primera versión incremental coordinará el snapshot lógico de:

- catálogo de conexiones VLESS y VMess, con sus configuraciones de revisión actualmente referenciada;
- metadatos no secretos de usuarios, identidades y asociaciones vinculadas a esas conexiones;
- catálogo central TLS, certificados públicos `managed` y metadatos/dependencias de certificados `reference`;
- manifiesto interno que declare categorías solicitadas, incluidas, no soportadas, exclusiones, dependencias y completitud por elemento y global.

Las credenciales y claves privadas quedan excluidas por defecto: UUID VMess, UUID VLESS, secretos REALITY, claves privadas TLS administradas y cualquier otra credencial detectada por adaptadores. Un elemento que necesite uno de esos secretos se marcará incompleto/no restaurable íntegramente mientras no se aporte por un flujo autorizado. La inclusión de secretos requiere selección, autorización expresa y confirmación adicional; no forma parte del alcance por defecto de esta primera versión.

La primera versión no implementará adaptadores para perfiles, registro de perfil activo, preferencias del gestor, dominios independientes ni protocolos distintos de VLESS/VMess. Estas categorías se declararán `unsupported` en el manifiesto cuando sean solicitadas. Conforme a Etapa 5 de `Xray-Normativa`, si se solicita alguna categoría no soportada, el resultado global será `PARTIAL`, nunca `COMPLETE`.

Los backups de protocolo existentes deben seguir siendo compatibles y no deben incorporar silenciosamente el almacén central ni alterar su contrato. El backup compartido será un artefacto/versionado distinto o una capa orquestadora explícita. El snapshot contiene únicamente la revisión actualmente referenciada por cada conexión; no empaqueta historiales de revisiones/validaciones/logs.

## 2. Qué se incluye y qué no

| Elemento | Tratamiento |
|---|---|
| Catálogo VLESS y revisiones actualmente referenciadas | Incluir snapshot validado |
| Catálogo VMess y revisiones actualmente referenciadas | Incluir snapshot validado |
| Metadatos no secretos de usuarios/identidades/asociaciones | Incluir dentro del alcance VLESS/VMess; conservar relaciones e IDs globales |
| UUID VMess / UUID VLESS | Excluir por defecto como credenciales; marcar los elementos afectados incompletos |
| `email` y `level` VMess | Conservar como metadatos/configuración dentro del payload cifrado; nunca exponerlos en logs/manifiesto externo |
| Secretos REALITY por conexión | Excluir por defecto; marcar elementos incompletos |
| Catálogo central TLS | Incluir snapshot y referencias necesarias |
| Certificados públicos `managed` | Incluir |
| Claves privadas TLS centrales | Excluir por defecto; marcar certificados/conexiones afectados incompletos |
| Certificados `reference` | No copiar automáticamente; registrar fingerprint y dependencia; no exponer rutas privadas fuera del payload protegido |
| Perfiles y asociaciones (versión actual) | `unsupported` en v1 incremental |
| Registro de perfil activo | `unsupported` en v1 incremental |
| Preferencias del gestor | `unsupported` en v1 incremental |
| Dominios independientes | `unsupported` en v1 incremental |
| Protocolos distintos de VLESS/VMess | `unsupported` en v1 incremental; requieren adaptador propio |
| Clave maestra `/etc/xray-manager/keys/master.key` | No incluir en el mismo backup |
| `/run/xray-manager-certificates` y leases | Excluir: son temporales y regenerables |
| Configuración activa Xray, runtime, firewall, servicios | Excluir del backup de datos; tratar en flujo de despliegue separado |
| REALITY como recurso TLS | Prohibido; REALITY no forma parte del catálogo TLS |

## 3. Protección criptográfica y recuperación de clave maestra

Los blobs del catálogo central están cifrados con la clave maestra del host. Copiar esos blobs sin una estrategia de recuperación de clave no permite restaurarlos en otro host.

**Hallazgo de auditoría:** el backup actual `scripts/vless_backup.py backup-data` crea un `tar.gz` de datos y manifiesto con hashes; no cifra el archivo completo. Los blobs de secretos ya están cifrados bajo la master key del host. `create-recovery` cifra una copia de la master key por separado con scrypt + AES-256-GCM, pero no cifra el backup de datos. Por tanto, no se debe describir el backup actual como un contenedor cifrado ni reutilizarlo como si ya ofreciera cifrado integral.

**Diseño que se implementará para el formato compartido:**

- Paquete independiente versionado con cifrado autenticado integral AES-256-GCM y clave derivada de una contraseña introducida interactivamente mediante scrypt. Parámetros KDF versionados y límites de recursos estrictos.
- Por defecto, no exportar credenciales ni claves privadas. Sólo si una credencial/clase de secreto se selecciona y autoriza expresamente con confirmación adicional, descifrarla en memoria usando el backend que corresponde, reenvolverla dentro del payload y cifrar el paquete antes de persistirlo. No escribir PEM/secretos descifrados en staging, archivos temporales, logs ni manifiestos.
- El backup no incluye `master.key` ni una copia recuperable de ésta. El paquete queda ligado a su contraseña; el destino no necesita reutilizar la clave maestra de origen.
- Durante restore, autenticar y descifrar el paquete en memoria, validar todos los recursos y volver a cifrar los secretos bajo la master key ya existente del destino, preservando el envelope/AAD específico de VLESS, VMess y certificados centrales.
- No guardar contraseña ni clave derivada en el manifiesto. Fallar cerrado ante contraseña incorrecta, tag/hash inválido, KDF no admitido, clave maestra destino ausente/inválida o formato incompatible.

Este mecanismo es nuevo para el backup compartido; no modifica retroactivamente el formato VLESS actual ni sus herramientas legacy.

## 3.1 Contenedor criptográfico compartido v1 — implementado

La especificación binaria y la implementación están documentadas en `docs/FORMATO_CIFRADO_COMPARTIDO_V1.md` y `scripts/shared_backup_format.py`. El módulo cifra bytes opacos y no conoce protocolos ni escribe archivos.

- Magic `XRMGSBKP`, longitud de cabecera de 4 bytes big-endian, JSON canónico y ciphertext AES-GCM.
- Scrypt fijo `N=2^15, r=8, p=1`, salida 32 bytes, límite de memoria 64 MiB; salt aleatorio de 16 bytes.
- AES-256-GCM, nonce aleatorio de 12 bytes, tag de 16 bytes. AAD cubre magic, longitud y bytes exactos de la cabecera.
- Cabecera declara formato/versión, algoritmo, KDF/perfil, salt, nonce y longitud cifrada. Perfil KDF fijo: no se aceptan parámetros arbitrarios del paquete.
- Contraseña UTF-8: mínimo 12 caracteres y 16 bytes, máximo 1024 bytes; no se normaliza ni se acepta NUL. Se solicitará interactivamente en la futura integración, nunca como argumento/variable/archivo.
- Payload máximo 512 MiB; cabecera máxima 4096 bytes. Validación estricta de magic, versión, estructura canónica, claves duplicadas, longitudes, truncamiento, bytes sobrantes y tag.
- La master key no forma parte del paquete. Este módulo no crea staging, no serializa catálogos, no descifra envelopes de protocolos, no verifica referencias ni restaura datos.

La neutralidad permite que VLESS, VMess, Trojan y futuros protocolos utilicen el mismo contenedor. Cada protocolo requiere su propio adaptador de snapshot/validación y su backend nativo de re-envoltura; no se reutilizan envelopes ni AAD entre protocolos.

**Límite de memoria:** el módulo trabaja con bytes en memoria. Python no garantiza zeroization de objetos `bytes` inmutables; la futura orquestación debe minimizar copias y evitar logs, temporales en claro, core dumps y exposición por swap.

## 4. Consistencia del snapshot

El backup no debe mezclar revisiones de un instante con catálogos de otro.

- Adquirir locks en orden global ya auditado: `lifecycle → integrity → catalog`; liberar en orden inverso.
- Validar catálogos y referencias mientras se mantienen locks.
- Capturar únicamente archivos regulares, root-owned, modos esperados, sin symlinks/hardlinks ni traversal.
- Construir snapshot en staging privado; no cambiar datos activos.
- Registrar hashes, tamaños, schema versions, revisions y dependencias en manifiesto.
- Liberar locks sólo después de cerrar/verificar el snapshot.

El inventario estático y las pruebas de contención constan en §10.4. El orden está documentado, pero la auditoría estática no sustituye pruebas de estrés exhaustivas. El writer deberá usar adquisición no bloqueante con timeout finito configurable y abortar sin publicar si algún lock no se obtiene.

## 5. Formato de paquete propuesto

Paquete lógico versionado, por ejemplo `xray-manager-shared-backup-v1`:

```text
manifest.json                 # dentro del payload cifrado
index.json                    # índice lógico de miembros
connections/
  vless/catalog.json
  vless/configurations/<logical-id>.json
  vmess/catalog.json
  vmess/configurations/<logical-id>.json
identities/
  identities.json
  associations.json
certificates/
  catalog.json
  managed/public/<logical-id>.pem
optional-secrets/             # sólo con selección/autorización adicional
  <protocol-or-resource>/<logical-id>.bin
```

Los nombres y directorios son ilustrativos y no constituyen aún un contrato congelado ni rutas actuales confirmadas. El paquete debe tener límites de tamaño/entradas, nombres lógicos normalizados, hashes, identificación de backup y versión de esquema. El manifiesto y el índice viajan dentro del contenedor cifrado. Las claves privadas TLS y los secretos REALITY no aparecen en la estructura por defecto; la sección opcional sólo se materializa tras selección y autorización adicionales.

`external-dependencies.json` debe enumerar recursos `reference` con `certificate_id`, fingerprint, path esperado, conexión(es) dependientes y validación requerida. Las rutas son datos no confiables: nunca seguir symlinks durante restore.

## 6. Preflight de restauración

Antes de escribir en el host destino:

1. Verificar versión, integridad global, autenticidad, tamaño, límites y estructura del paquete.
2. Validar los dos catálogos de conexiones y todas las revisiones referenciadas.
3. Verificar en el manifiesto las exclusiones de UUID/REALITY y marcar como incompletos los elementos que dependan de esos secretos; sólo validar blobs REALITY si fueron incluidos mediante autorización adicional.
4. Validar catálogo central, certificados públicos `managed`, recursos `reference`, fingerprints y dependencias; si falta una clave privada excluida, no presentar la conexión TLS afectada como íntegramente restaurable.
5. Si el paquete contiene secretos seleccionados, confirmar master key destino presente, válida y de 32 bytes sin mostrarla y validar la re-envoltura. Si no contiene secretos, no exigirla sólo para inspeccionar/restaurar metadatos.
6. Para cada `reference`, verificar que el archivo externo existe, es regular, no es symlink/hardlink, fingerprint coincide y el par corresponde tras resolver el secreto en memoria.
7. Verificar que toda conexión TLS central apunta a un certificado activo incluido en el snapshot.
8. Detectar colisiones de connection_id, certificate_id, paths, revisiones y recursos existentes.
9. Mostrar resumen y solicitar consentimiento explícito antes de publicar.

La falta de una dependencia `reference` bloquea por defecto el restore completo; se podría diseñar un modo parcial explícito, pero nunca restaurar silenciosamente conexiones no funcionales.

## 7. Publicación y rollback

- Preparar todo en staging root-only y validar una segunda vez.
- Mantener snapshot/backup de los destinos existentes.
- Publicar mediante journal durable, renombres atómicos por árbol y un punto de commit explícito.
- El catálogo de conexiones no puede apuntar a certificados que aún no estén publicados.
- Orden propuesto: publicar almacén/catálogo de certificados, publicar stores de protocolo, publicar catálogos de conexiones al final.
- En fallo, restaurar referencias/catálogos previos y conservar staging/cuarentena para análisis; no borrar datos originales.
- Recuperar interrupciones de forma idempotente. No afirmar atomicidad global de filesystem: el journal y el rollback coordinado son obligatorios.
- No aplicar configuración Xray, iniciar servicios ni modificar firewall/puertos.

## 8. Interoperabilidad con backups actuales

- `vless_backup.py` seguirá respaldando VLESS y preservando VMess según su contrato actual, pero no incluirá el catálogo central.
- Los backups de protocolo seguirán declarando `certificate_id` como dependencia externa y requerirán el catálogo central en restore.
- El nuevo backup compartido orquestará ambos protocolos y el catálogo TLS de forma consistente.
- Debe probarse que restore compartido no pisa conexiones creadas después del snapshot sin política explícita de merge/conflicto.
- Versiones antiguas deben seguir restaurándose por sus herramientas actuales; el nuevo formato no reinterpreta archivos legacy sin migración explícita.

## 9. Pruebas obligatorias

- Backup/verify/restore de metadatos VLESS + VMess + identidades/asociaciones + catálogo TLS.
- Verificar que UUID/REALITY/claves privadas se excluyen por defecto y que los recursos afectados quedan `PARTIAL`.
- Recursos managed y reference presentes/ausentes/modificados.
- Si se habilita inclusión de secretos: master key destino correcta, ausente e inválida; re-envoltura y passphrase errónea.
- Alteración de cada archivo, manifiesto, tag, hash, fingerprint y blob.
- Límites de tamaño/archivos, traversal, symlink/hardlink, permisos y ownership.
- Colisiones de IDs/revisiones y cambios concurrentes durante snapshot.
- Fallo inyectado después de cada fase de publicación y recuperación de journal.
- Rollback preserva datos activos previos; no borra archivos huérfanos automáticamente.
- Confirmar que leases `/run`, runtime Xray, firewall, servicios y master key no se incluyen.

## 10. Decisiones aprobadas (2026-11-03)

1. **Secretos:** reenvolverlos con cifrado propio del backup y restaurarlos bajo la master key existente del destino; no incluir `master.key` en el paquete.
2. **Dependencias `reference`:** si falta una referencia o no coincide su fingerprint/par, bloquear el restore completo por defecto. No omitir silenciosamente conexiones.
3. **Datos posteriores al snapshot:** no sobrescribir. Si el destino contiene datos no idénticos o posteriores que entren en conflicto con el snapshot, bloquear la publicación completa y conservar el destino intacto; no realizar merge automático.
4. **Retención/custodia:** contraseña no persistida en VPS ni manifiesto; el operador debe custodiarla y almacenar el paquete fuera de la VPS. Política de retención se fijará antes de habilitar producción.
5. **Formato:** paquete compartido versionado y separado de backups legacy; compatibilidad legacy preservada.

## 10.1. Decisión de metadatos VMess — 2026-11-03

**Decisión del propietario:** adoptar la recomendación de conservar el campo email como metadato administrativo en el payload cifrado del backup compartido, mientras se excluye el UUID por defecto.

| Campo | Tratamiento | Motivo |
|---|---|---|
| id (UUID VMess) | Excluir por defecto como secreto/credencial | Participa en la autenticación VMess; su inclusión requiere selección, autorización expresa y confirmación adicional conforme a la política general de secretos. |
| email | Conservar como metadato administrativo dentro del payload cifrado | Identifica administrativamente al cliente/asociación y puede apoyar logs/estadísticas; no sustituye al UUID ni es necesario para que un cliente externo se conecte. |
| level | Conservar como metadato de configuración | No es la credencial de autenticación y forma parte de la configuración del cliente VMess en Xray. |

La conservación de email no significa que deba exponerse en el manifiesto externo ni en logs. Se mantiene dentro del contenido protegido por el contenedor AES-256-GCM. El manifiesto podrá indicar que la credencial UUID fue excluida, sin copiar su valor ni exponer innecesariamente el email.

Un registro VMess cuyo UUID se excluya debe marcarse como incompleto/no restaurable íntegramente hasta que la credencial se aporte por un flujo explícito y autorizado. La presencia de email y level no permite reconstruir ni autenticar al usuario. Esta decisión no cambia el esquema operativo ni elimina campos del catálogo actual.

## 11. Estado y siguiente diseño

El alcance incremental del snapshot v1 está aprobado en §10.5. El contrato del contenedor cifrado v1 está implementado y probado en aislamiento. El borrador lógico de manifiesto está en §10.6 y requiere aprobación de sus tipos/campos y reglas exactas antes de congelarlo. El inventario estático de locks y el orden `lifecycle → integrity → catalog` constan en §10.4; falta stress testing de concurrencia y la futura implementación deberá usar timeout finito. La detección de conflictos del restore, el schema definitivo y las pruebas sintéticas del snapshot siguen pendientes. La política de campos VMess queda definida en §10.1: excluir UUID por defecto y conservar email y level como metadatos dentro del payload cifrado. La auditoría del código actual confirmó que el backup de datos VLESS no cifra el tar.gz completo; sólo los blobs de secretos usan cifrado bajo master key y el archivo de recuperación de master key se cifra aparte.

**Estado:** contenedor criptográfico neutral v1 IMPLEMENTADO y VERIFICADO con prueba aislada; alcance incremental APROBADO; manifiesto en BORRADOR; snapshot, adaptadores VLESS/VMess/identidades/certificados, backup, verify, restore, journal y rollback aún NO IMPLEMENTADOS. No se ha creado ni restaurado un backup compartido.

## 10.2. Coordinación de desinstalación y catálogo TLS — 2026-11-03

Se corrigió modules/uninstall.sh para que, cuando la selección incluya la categoría certificates (incluidas las políticas all para Manager o ambos componentes), adquiera el bloqueo central catalog.lock antes de respaldar/eliminar las rutas. La adquisición se hace después de integrity.lock y antes del bloqueo de administración Xray. Orden en este flujo: lifecycle.lock → uninstall.lock → integrity.lock → catalog.lock (si se eliminan certificados) → bloqueo Xray.

Los bloqueos se adquieren de forma no bloqueante mediante manager_lock_acquire. Si catalog.lock está ocupado, la desinstalación se cancela antes de crear el respaldo o eliminar rutas. Cuando se obtiene, se mantiene durante la confirmación, el respaldo previo y la eliminación; el trap de retorno libera los bloqueos en orden inverso. Si no se seleccionan certificados, no se solicita catalog.lock.

Pruebas añadidas a tests/uninstall.sh: una operación concurrente que mantiene catalog.lock impide la desinstalación y conserva los datos; el caso de eliminación de la categoría certificates verifica que el lock sigue ocupado durante la confirmación. La suite completa de scripts shell pasó tras el cambio, junto con Bash syntax, ShellCheck del módulo modificado y git diff --check.

**Límite de auditoría:** esto corrige el camino de desinstalación y prueba la coordinación con el lock del catálogo; no certifica todavía que se hayan inspeccionado todos los mutadores ni que el orden global esté completamente cerrado. La auditoría estática y pruebas más amplias de concurrencia siguen pendientes antes del writer compartido.

## 10.3. Ruta estable del lock TLS — 2026-11-03

Se establece como ruta única por defecto de catalog.lock: /run/xray-manager-certificate-locks/catalog.lock. La ruta anterior /var/lib/xray-manager/certificates/catalog.lock estaba dentro del directorio que la desinstalación elimina. Eliminar el archivo de lock mientras un proceso conserva abierto su inode rompe la coordinación: otro proceso puede crear un archivo nuevo en la misma ruta y bloquear un inode distinto.

La nueva ubicación queda fuera de /var/lib/xray-manager y del árbol de certificados; por tanto, la política de desinstalación de certificados o de todos los datos del Manager no desvincula el archivo mientras se mantiene el lock. certificate_store.py crea/valida el directorio padre con safe_dir en modo root-only; certificate_resolver.py utiliza el mismo acquire_lock del almacén. Los defaults CLI, config/paths.sh, los asistentes VLESS/VMess y uninstall.sh deben permanecer alineados con esta ruta. El flujo de desinstalación crea y valida el directorio padre como root:root 0700 antes de adquirir el lock; certificate_store también valida ese modo mediante safe_dir. Las pruebas de parser comprueban que ambos CLI usan el default estable y tests/uninstall.sh comprueba que el lock sobrevive al borrado del árbol de certificados.

La ruta es temporal bajo /run y se recrea tras reinicio cuando el almacén la necesite. No contiene datos del catálogo ni secretos. Este cambio modifica defaults de código/documentación, no mueve ni elimina archivos reales en la VPS y no ejecuta runtime apply.

## 10.4. Inventario estático de locks y orden para snapshot — 2026-11-03

La revisión de los puntos de adquisición del repositorio identifica este grafo:

| Operación | Orden de adquisición |
|---|---|
| Instalación/actualización del Manager | lifecycle → integrity |
| Backup VLESS existente | lifecycle → integrity |
| Administración de Xray-core | lifecycle → xray-admin |
| Desinstalación | lifecycle → uninstall → integrity → catalog (si elimina certificados) → xray-admin |
| Resolutor TLS | integrity → catalog |
| Almacén central de certificados | catalog |
| Conexiones, usuarios legacy y users v2 | integrity |
| Stores de configuración VLESS/VMess | integrity |
| Cutover users v2 | integrity |
| Preflight migración TLS (solo lectura) | integrity compartido |
| Preferencias, dependencias del sistema y acciones de servicio | lifecycle |

No se encontró una adquisición inversa entre integrity y catalog ni un ciclo en los caminos de adquisición inspeccionados. El resolutor y el desinstalador respetan integrity → catalog; el almacén de certificados toma catalog sin solicitar después integrity. Las operaciones de Xray toman lifecycle antes del lock Xray. Las operaciones de ciclo de vida que también toman integrity lo hacen después de lifecycle.

**Orden requerido para el snapshot compartido:** lifecycle → integrity → catalog. No necesita tomar uninstall ni xray-admin, porque el snapshot no desinstala ni modifica el runtime. Debe adquirir todos los locks antes de leer los catálogos/archivos y liberarlos en orden inverso.

**Tiempo de espera:** los stores/resolutor Python actuales usan flock bloqueante; no se debe copiar ese comportamiento al snapshot. El writer futuro debe usar adquisición no bloqueante con un timeout finito y configurable; si cualquier lock no se obtiene, aborta sin publicar paquete ni staging parcial.

**Pruebas de concurrencia disponibles:** tests/uninstall.sh cubre contención de lifecycle, integrity, catalog y Xray; confirma que catalog se mantiene durante la confirmación de eliminación de certificados, que el lock se libera si la adquisición posterior de Xray falla y que el lock externo sobrevive al borrado del árbol de certificados. tests/certificate_store.sh valida los defaults de ruta en ambos CLI. Suite completa: 47/47 PASS; Bash syntax, ShellCheck de uninstall.sh, shfmt focal, py_compile y git diff --check PASS.

**Límite:** inventario estático completo de los puntos de adquisición localizados en scripts, modules, lib, config e install.sh; no equivale a una prueba de estrés exhaustiva ni a una garantía frente a procesos de una versión antigua durante despliegue. El cambio de ruta del catálogo requiere desplegar con los procesos de la versión anterior detenidos. No se movió el lock antiguo ni se ejecutó migración/runtime en la VPS.


## 10.5. Alcance incremental del snapshot v1 — aprobado por el propietario (2026-11-03)

**Decisión:** aprobado el alcance incremental recomendado para la primera versión del snapshot compartido.

**Incluido en v1:**

1. Catálogo de conexiones VLESS y VMess, incluyendo únicamente la revisión/configuración actualmente referenciada por cada conexión.
2. Metadatos no secretos de usuarios, identidades globales y asociaciones, conservando IDs y relaciones sin reconstruir credenciales excluidas.
3. Catálogo central TLS, certificados públicos `managed` y metadatos de dependencias `reference` (fingerprint y asociación con recursos dependientes).
4. Manifiesto interno cifrado con categorías solicitadas/incluidas/no soportadas, recursos, miembros, exclusiones, dependencias y estado de completitud por elemento y global.

**Excluido por defecto:** UUID VMess, UUID VLESS, secretos REALITY, claves privadas TLS administradas y cualquier otra credencial/clave privada detectada por los adaptadores. El manifiesto podrá declarar tipo de secreto excluido y recurso afectado, pero nunca su valor. Los elementos que dependan de esos secretos quedan incompletos/no restaurables íntegramente hasta recibirlos mediante un flujo autorizado. Su inclusión requiere selección, autorización expresa y confirmación adicional.

Se conserva la decisión VMess de §10.1: `email` y `level` son metadatos dentro del payload cifrado; UUID es credencial excluida por defecto. Los metadatos de identidad/asociación se conservan sin asumir que contienen credenciales exportables.

**No soportado por la primera versión:** configuraciones JSON independientes fuera de las conexiones cubiertas, perfiles y asociaciones de perfil, registro del perfil activo, preferencias del gestor, dominios independientes y protocolos distintos de VLESS/VMess. Cada categoría solicitada y no soportada debe aparecer en `unsupported`; no se omite silenciosamente.

**Completitud:** `COMPLETE` sólo podrá declararse cuando todas las categorías/elementos solicitados estén incluidos y sean íntegros/restaurables conforme al alcance y no existan exclusiones o dependencias pendientes que afecten esos elementos. Si se solicita una categoría `unsupported`, o si un elemento solicitado requiere un secreto excluido o una dependencia `reference` no verificada, el resultado correspondiente será `PARTIAL` (o `BLOCKED` si no es seguro producir el paquete). Nunca declarar `COMPLETE` por el solo hecho de que el contenedor AES-GCM se haya creado correctamente.

**Contraste normativo:** la Etapa 5 de `Xray-Normativa/05_Configuraciones_Perfiles/Etapa_5_Configuraciones_Perfiles.md` §8 permite selección de configuraciones, perfiles actuales, perfil activo, usuarios/identidades/asociaciones, preferencias, dominios y certificados; exige credenciales/claves privadas excluidas por defecto y prohíbe declarar completo un respaldo que omitió elementos solicitados. El alcance incremental no modifica ni sustituye esa normativa: las categorías diferidas quedan explícitamente `unsupported` y fuerzan `PARTIAL` cuando sean solicitadas. `Xray-Normativa/` permanece inmutable.

**Límite de esta aprobación:** aprueba el alcance funcional incremental, no el schema definitivo, el código writer, la creación de paquetes reales, la inclusión de secretos, el restore ni cambios de runtime.

## 10.6. Borrador del contrato lógico de manifiesto — pendiente de aprobación

El manifiesto residirá dentro del payload cifrado por el contenedor compartido v1. No habrá manifiesto de contenido en claro junto al paquete. Este borrador define semántica y campos requeridos; no es aún un schema JSON congelado.

| Campo lógico | Contenido/contrato |
|---|---|
| `manifest_format` / `manifest_version` | Identificador del manifiesto y versión independiente del contenedor criptográfico |
| `backup_id` / `created_at` | UUID aleatorio y timestamp UTC ISO-8601 |
| `manager_version` / `xray_version` | Versiones conocidas; usar `null`/`unknown` si no pueden determinarse, nunca inventarlas |
| `request` | Categorías/recursos solicitados y modalidad (selectiva o conjunto completo disponible) |
| `categories.included` | Categorías realmente representadas en el payload |
| `categories.unsupported` | Categorías solicitadas no soportadas por adaptadores v1, con razón estable |
| `resources[]` | Tipo, ID lógico, protocolo/propietario, estado de completitud y referencias a miembros; sin credenciales ni rutas host-specific |
| `members[]` | ID lógico/content-addressed, categoría, tamaño, SHA-256 y tipo de contenido; nunca ruta absoluta |
| `exclusions[]` | Recurso afectado, clase de secreto excluida y razón; nunca valor secreto |
| `dependencies[]` | Tipo/ID de dependencia, fingerprint esperado, recursos dependientes y resultado de validación; para `reference` no incluir ruta privada en claro fuera del payload cifrado |
| `completeness` | Estado global `COMPLETE`/`PARTIAL`/`BLOCKED` y detalle por recurso/categoría |
| `source_snapshot` | Revisiones/schema versions y hashes de los catálogos/entradas que fijan la vista consistente |

Los miembros se identificarán por hashes SHA-256 y nombres lógicos normalizados, no por rutas absolutas del host. El contenedor lógico rechazará symlinks, hardlinks, devices, traversal, nombres duplicados, tamaños/entradas fuera de límite y discrepancias entre hash/tamaño declarado y bytes. El manifiesto y el índice de miembros se validarán antes de cualquier restore.

**Reglas de estado propuestas:** `COMPLETE` significa que todo lo solicitado está incluido y restaurable; `PARTIAL` significa que el paquete íntegro contiene omisiones declaradas (categorías no soportadas, secretos excluidos o dependencias no satisfechas); `BLOCKED` significa que no debe publicarse un paquete porque falló una validación de seguridad/consistencia. La integridad criptográfica del contenedor es independiente de la completitud funcional.

**Pendiente de aprobación:** nombres/tipos exactos, enums, cardinalidades, relación recurso-miembro, codificación canónica, formato de timestamps, reglas de paths lógicos, límite de entradas/expansión y validaciones cruzadas. No implementar writer hasta congelar este contrato y sus pruebas sintéticas.
