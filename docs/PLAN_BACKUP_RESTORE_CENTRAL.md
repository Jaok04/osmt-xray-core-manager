# Diseño de backup/restore compartido — conexiones y certificados centrales

**Versión:** 1.10
**Fecha:** 2026-11-03
**Estado:** ALCANCE INCREMENTAL V1 APROBADO / CONTRATO DE MANIFIESTO V1 APROBADO / CONTENEDOR CIFRADO V1 IMPLEMENTADO Y VERIFICADO / FORMATO LÓGICO DE PAQUETE V1 APROBADO / ORQUESTACIÓN BACKUP-RESTORE PENDIENTE
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

Los nombres y directorios anteriores son nombres lógicos internos, no rutas actuales confirmadas del host. El paquete lógico v1 se empaqueta como archivo ZIP usando exclusivamente `ZIP_STORED` (sin compresión). `manifest.json` e `index.json` son entradas de primer nivel y permanecen dentro del payload cifrado por el contenedor compartido; no se publica un índice de contenido en claro junto al contenedor. Los miembros de datos conservan paths POSIX relativos normalizados definidos por el manifiesto/índice.

El ZIP sólo puede contener entradas de archivos regulares. Se rechazan nombres duplicados, rutas absolutas, `..`, separadores alternativos, NUL, colisiones tras normalización, symlinks y tipos especiales; no se extrae siguiendo rutas ni enlaces del archivo. Cada miembro debe corresponder exactamente a una entrada del índice y validar tamaño y SHA-256 sobre sus bytes. Se rechazan métodos de compresión distintos de `ZIP_STORED`, miembros no indexados e índices que apunten a miembros ausentes.

El límite total del archivo ZIP lógico es 512 MiB, sin exceder el límite de payload del contenedor cifrado v1; el writer deberá contabilizar también cabeceras y directorio central antes de publicar. El ZIP admite como máximo 10.000 entradas en total, contando `manifest.json` e `index.json`; por tanto, hasta 9.998 miembros de datos. El límite es estricto: si se supera, la creación aborta sin publicar un paquete parcial. Las claves privadas TLS y secretos REALITY no aparecen por defecto; la sección opcional sólo se materializa tras selección y autorización adicionales.

`external-dependencies.json` enumera recursos `reference` con `certificate_id`, fingerprint, path esperado, conexiones dependientes y validación requerida. Las rutas son datos no confiables: nunca seguir symlinks durante restore.

### Canonicalización JSON v1

`manifest.json`, `index.json` y cualquier JSON estructural del paquete usan un único perfil canónico:

- UTF-8 estricto, sin BOM; no se admiten sustitutos Unicode aislados ni secuencias inválidas.
- Objetos con claves ordenadas lexicográficamente por sus cadenas Unicode; no se admiten claves duplicadas.
- Sin espacios insignificantes: separadores compactos `,` y `:`; sin espacios ni saltos de línea añadidos fuera de strings.
- No se admiten números de punto flotante, NaN, Infinity ni -Infinity. Los números permitidos son enteros JSON dentro del rango interoperable exacto `-(2^53-1)` a `2^53-1`; cantidades y tamaños no pueden ser negativos.
- Strings se codifican como JSON UTF-8; se escapan comillas, barra inversa y caracteres de control según JSON, sin escapar innecesariamente caracteres Unicode imprimibles.
- El parser debe rechazar claves duplicadas, tipos inesperados, valores no finitos, trailing data y cualquier representación no conforme. La validación de canonicalidad compara los bytes originales con la serialización canónica del objeto parseado; no basta con que el JSON sea parseable.

Esta política define el perfil de canonicalización propio del formato lógico Xray Manager v1; no se declara compatibilidad automática con RFC 8785/JCS.

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

El alcance incremental del snapshot v1 está aprobado en §10.5. El contenedor cifrado v1 está implementado y probado en aislamiento; el contrato lógico/JSON del manifiesto está aprobado en §10.6–§10.8 y el formato ZIP/canonicalización JSON está aprobado en §5 y §10.9. El inventario estático de locks y el orden `lifecycle → integrity → catalog` constan en §10.4; falta stress testing de concurrencia y la futura implementación deberá usar timeout finito. La detección de conflictos del restore, el schema formal ejecutable, las pruebas sintéticas del snapshot siguen pendientes; el máximo de entradas ZIP quedó aprobado en §10.10. La política de campos VMess queda definida en §10.1: excluir UUID por defecto y conservar email y level como metadatos dentro del payload cifrado. La auditoría del código actual confirmó que el backup de datos VLESS no cifra el tar.gz completo; sólo los blobs de secretos usan cifrado bajo master key y el archivo de recuperación de master key se cifra aparte.

**Estado:** contenedor criptográfico neutral v1 IMPLEMENTADO y VERIFICADO con prueba aislada; alcance incremental, contrato de manifiesto y formato lógico ZIP/JSON APROBADOS; snapshot, adaptadores VLESS/VMess/identidades/certificados, backup, verify, restore, journal y rollback aún NO IMPLEMENTADOS. El schema formal ejecutable sigue pendiente; el máximo de entradas ZIP quedó aprobado en §10.10. No se ha creado ni restaurado un backup compartido.

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

## 10.6. Contrato lógico de manifiesto — aprobado (2026-11-03)

El manifiesto residirá dentro del payload cifrado por el contenedor compartido v1. No habrá manifiesto de contenido en claro junto al paquete. La estructura y semántica de este contrato quedan aprobadas; la estructura JSON concreta y sus reglas están desarrolladas en §10.7.

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
| `completeness` | Estado del paquete `COMPLETE`/`PARTIAL` y detalle por recurso/categoría; `BLOCKED` es resultado de preflight y no genera paquete |
| `source_snapshot` | Revisiones/schema versions y hashes de los catálogos/entradas que fijan la vista consistente |

Los miembros se identificarán por hashes SHA-256 y nombres lógicos normalizados, no por rutas absolutas del host. El contenedor lógico rechazará symlinks, hardlinks, devices, traversal, nombres duplicados, tamaños/entradas fuera de límite y discrepancias entre hash/tamaño declarado y bytes. El manifiesto y el índice de miembros se validarán antes de cualquier restore.

**Reglas de estado propuestas:** `COMPLETE` significa que todo lo solicitado está incluido y restaurable; `PARTIAL` significa que el paquete íntegro contiene omisiones declaradas (categorías no soportadas, secretos excluidos o dependencias no satisfechas); `BLOCKED` es un resultado del preflight y significa que no se publica paquete porque falló una validación de seguridad/consistencia. La integridad criptográfica del contenedor es independiente de la completitud funcional.

**Aprobado:** nombres y relaciones lógicas de los campos, enums de estado, cardinalidades conceptuales, referencias recurso-miembro, timestamp UTC, paths lógicos relativos, exclusión de credenciales y validaciones cruzadas descritas en §10.7. En la fecha de esta aprobación inicial, codificación canónica y empaquetado físico permanecían pendientes; se cerraron posteriormente en §10.9. El writer continúa pendiente.


## 10.7. Estructura JSON del manifiesto — aprobada (2026-11-03)

La siguiente estructura concreta desarrolla §10.6 y queda aprobada como contrato lógico v1. El ejemplo no es un manifiesto real ni sustituye un JSON Schema formal; los identificadores y hashes son marcadores ilustrativos y no deben copiarse como valores reales.

```json
{
  "manifest_format": "xray-manager-shared-snapshot",
  "manifest_version": 1,
  "backup_id": "<uuid-v4>",
  "created_at": "<UTC-RFC3339-timestamp>",
  "source": {
    "manager_version": null,
    "xray_version": null
  },
  "request": {
    "selection_mode": "selective",
    "requested_categories": [
      "connections.vless",
      "connections.vmess",
      "identities",
      "certificates.tls"
    ]
  },
  "categories": {
    "included": [
      "connections.vless",
      "connections.vmess",
      "identities",
      "certificates.tls"
    ],
    "unsupported": []
  },
  "resources": [
    {
      "resource_id": "vless:connection:<logical-id>",
      "resource_type": "connection",
      "protocol": "vless",
      "completeness": "PARTIAL",
      "member_ids": ["sha256:<64-hex>"] ,
      "dependency_ids": ["tls:<certificate-id>"],
      "exclusion_ids": ["exclude:<logical-id>:vless_uuid"]
    }
  ],
  "members": [
    {
      "member_id": "sha256:<64-hex>",
      "logical_path": "connections/vless/catalog.json",
      "category": "connections.vless",
      "media_type": "application/json",
      "size_bytes": 1234,
      "sha256": "<64-hex>"
    }
  ],
  "exclusions": [
    {
      "exclusion_id": "exclude:<logical-id>:vless_uuid",
      "resource_id": "vless:connection:<logical-id>",
      "secret_class": "vless_uuid",
      "reason": "excluded_by_default"
    }
  ],
  "dependencies": [
    {
      "dependency_id": "tls:<certificate-id>",
      "dependency_type": "tls_reference",
      "resource_id": "certificate:<certificate-id>",
      "fingerprint_sha256": "<64-hex>",
      "required": true,
      "validation": "pending_restore_preflight"
    }
  ],
  "source_snapshot": {
    "catalogs": [
      {
        "catalog_id": "connections.vless",
        "schema_version": 1,
        "revision": 7,
        "sha256": "<64-hex>"
      }
    ]
  },
  "completeness": {
    "status": "PARTIAL",
    "reasons": ["secret_excluded", "external_dependency_requires_validation"],
    "complete_resources": 0,
    "partial_resources": 1
  }
}
```

### Reglas de validación aprobadas

1. `manifest_version` es entero positivo; `backup_id` es UUID aleatorio; `created_at` es timestamp UTC RFC 3339 terminado en `Z`.
2. `selection_mode` sólo admite `selective` o `all_available`. `requested_categories` no puede estar vacío y no puede contener duplicados.
3. `categories.included` y `categories.unsupported` deben ser disjuntos. Toda categoría solicitada debe estar en una de esas dos listas o provocar `BLOCKED`; no se permite omisión silenciosa.
4. `resources`, `members`, `exclusions` y `dependencies` tienen IDs únicos. Toda referencia `member_id`, `exclusion_id` y `dependency_id` debe resolver exactamente una entrada.
5. Cada miembro declara tamaño y SHA-256 calculados sobre sus bytes exactos. `member_id` se deriva del contenido (`sha256:<digest>`); mismo contenido puede compartirse sin duplicar bytes.
6. `logical_path` es relativo, POSIX, normalizado y único; se rechazan rutas absolutas, `..`, separadores alternativos, NUL, symlinks, hardlinks, devices, FIFOs y colisiones tras normalización.
7. `resources[].completeness` sólo admite `COMPLETE` o `PARTIAL`. Si un recurso tiene una exclusión necesaria o una dependencia obligatoria no verificada, no puede declararse `COMPLETE`.
8. El estado global `COMPLETE` exige que todas las categorías solicitadas estén incluidas, todos los recursos solicitados sean completos y no haya exclusiones/dependencias pendientes que afecten la restauración. Cualquier omisión declarada fuerza `PARTIAL`.
9. `BLOCKED` es un resultado de preflight, no un paquete publicable: fallo de seguridad, consistencia, permisos, integridad o referencias aborta la creación sin publicar artefacto.
10. El manifiesto no contiene UUID, contraseñas, claves privadas, secretos REALITY, email VMess, rutas absolutas, contenido de credenciales ni valores de la master key. `email` y `level` VMess permanecen en los miembros de configuración protegidos, no en el manifiesto.
11. El manifiesto, índice y JSON estructural se serializan conforme al perfil canónico de §5: UTF-8 estricto sin BOM, claves ordenadas, separadores compactos, sin claves duplicadas, floats ni valores no finitos; el parser compara los bytes con la serialización canónica. Manifiesto e índice permanecen dentro del payload AES-GCM.
12. El ZIP lógico completo, incluyendo metadatos ZIP, nunca supera 512 MiB ni el límite del payload del contenedor compartido v1. El máximo es 10.000 entradas ZIP totales, incluyendo `manifest.json` e `index.json` (hasta 9.998 miembros de datos); superar el límite aborta la creación sin publicar paquete.

### Decisiones aprobadas por el propietario

- Estructura de campos y sus relaciones: APROBADA.
- Estados globales `COMPLETE`/`PARTIAL`; `BLOCKED` sólo como resultado de preflight sin paquete: APROBADOS.
- `logical_path` como nombre relativo interno sin rutas host-specific: APROBADO.
- Manifiesto sin `email` VMess ni credenciales, aunque esos metadatos puedan existir en miembros cifrados: APROBADO.
- Formato ZIP con `ZIP_STORED`, estructura `manifest.json` + `index.json`, validaciones de entradas (paths seguros, sin duplicados, symlinks ni tipos especiales; miembros identificados por SHA-256) y perfil canónico JSON de §5: APROBADOS en §10.9.
- Máximo de entradas ZIP: 10.000 en total, incluyendo `manifest.json` e `index.json` (máximo 9.998 miembros de datos); superar el límite aborta sin publicar paquete: APROBADO en §10.10.

**La aprobación del manifiesto no autoriza writer, verify, restore, creación de paquetes reales ni runtime apply.**


## 10.8. Aprobación del contrato de manifiesto — 2026-11-03

El propietario aprobó expresamente §10.6 y §10.7: estructura lógica y JSON, relaciones y referencias, campos, estados, reglas de completitud, nombres lógicos relativos, validación de miembros/hashes y ausencia de credenciales/email VMess en el manifiesto. `COMPLETE` y `PARTIAL` son estados de paquete; `BLOCKED` es sólo un resultado de preflight que aborta sin publicar paquete.

El contrato de manifiesto v1 quedó **APROBADO** en esa decisión. No se cambia el alcance funcional aprobado en §10.5. En ese momento no se incluían formato físico, límite final de miembros ni canonicalización exacta; el empaquetado ZIP y la canonicalización se aprobaron posteriormente en §10.9. La aprobación del manifiesto no autorizó writer, verify, restore, inclusión de secretos ni runtime apply.


## 10.9. Aprobación del empaquetado ZIP y canonicalización JSON — 2026-11-03

El propietario aprobó el formato lógico ZIP con `ZIP_STORED` (sin compresión) y la política de canonicalización JSON definida en §5. Quedan aprobados el contenedor ZIP interno al payload cifrado, `manifest.json` e `index.json`, admisión exclusiva de archivos regulares, rechazo de rutas inseguras, duplicados, symlinks/tipos especiales, métodos distintos de `ZIP_STORED`, entradas ausentes/no indexadas y verificación de tamaño/SHA-256.

La canonicalización aprobada requiere UTF-8 estricto sin BOM, claves lexicográficamente ordenadas, separadores compactos, sin claves duplicadas, sin floats/valores no finitos, enteros dentro del rango interoperable exacto y comparación de bytes originales contra la serialización canónica. Es un perfil propio del formato Xray Manager v1; no se afirma compatibilidad RFC 8785/JCS. El límite del ZIP completo es 512 MiB. El máximo de entradas ZIP quedó fijado en 10.000 en total (hasta 9.998 miembros de datos) por aprobación posterior en §10.10.

Esta aprobación sólo congela las decisiones descritas. No autoriza implementar writer, verify, restore, crear paquetes/backups reales, incluir secretos ni ejecutar runtime apply. El alcance incremental sigue siendo el aprobado en §10.5 y la normativa `Xray-Normativa/` permanece inmutable.


## 10.10. Aprobación del máximo de entradas ZIP — 2026-11-03

El propietario aprobó un máximo estricto de **10.000 entradas ZIP en total**, contando las dos entradas estructurales `manifest.json` e `index.json`. En consecuencia, se permiten hasta **9.998 miembros de datos**.

El writer/preflight deberá contar todas las entradas antes de publicar. Si el conjunto supera el máximo, la operación abortará sin publicar un paquete parcial ni sustituir un artefacto previo. El lector/verify deberá rechazar paquetes que excedan el límite, incluso si su tamaño total está dentro de 512 MiB.

Con esta decisión queda cerrado el límite de cantidad de miembros del paquete lógico v1. La aprobación no autoriza implementar writer, verify, restore, crear paquetes/backups reales, incluir secretos ni ejecutar runtime apply.
