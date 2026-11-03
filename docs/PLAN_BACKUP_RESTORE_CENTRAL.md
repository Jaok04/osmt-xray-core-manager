# Diseño de backup/restore compartido — conexiones y certificados centrales

**Versión:** 1.4
**Fecha:** 2026-11-03
**Estado:** CRITERIOS APROBADOS / CONTENEDOR CIFRADO V1 IMPLEMENTADO Y VERIFICADO / ORQUESTACIÓN BACKUP-RESTORE PENDIENTE
**Ámbito:** contenedor criptográfico neutral y futuro backup consistente de VLESS/VMess/certificados; extensible a protocolos futuros mediante adaptadores.

## 1. Objetivo

Añadir un flujo coordinado que respalde/restaure en conjunto:

- catálogo de conexiones y revisiones VLESS;
- catálogo de conexiones y revisiones VMess;
- blobs REALITY actualmente referenciados por ambos protocolos, sujetos a selección/autorización expresa para incluir secretos;
- catálogo central de certificados TLS;
- certificados públicos `managed`;
- claves privadas centrales, sólo si el operador las selecciona y autoriza expresamente con confirmación adicional;
- manifiesto de dependencias externas para certificados `reference`.

Los backups de protocolo existentes deben seguir siendo compatibles y no deben incorporar silenciosamente el almacén central ni alterar su contrato. El backup compartido será un artefacto/versionado distinto o una capa orquestadora explícita. El snapshot contiene únicamente la revisión actualmente referenciada por cada conexión; no empaqueta el historial de revisiones/validaciones/logs.

## 2. Qué se incluye y qué no

| Elemento | Tratamiento |
|---|---|
| Catálogo VLESS y revisiones referenciadas | Incluir snapshot validado |
| Catálogo VMess y revisiones referenciadas | Incluir snapshot validado |
| Blobs REALITY por conexión | Excluir por defecto; incluir sólo con selección, autorización y confirmación adicional; reenvolver dentro del contenedor |
| Catálogo central TLS | Incluir snapshot |
| Certificados públicos `managed` | Incluir |
| Claves privadas TLS centrales | Excluir por defecto; inclusión sólo con selección, autorización y confirmación adicional; cifrado integral del paquete |
| Certificados `reference` | No copiar automáticamente; registrar ruta, fingerprint y dependencia |
| Clave maestra `/etc/xray-manager/keys/master.key` | No incluir en el mismo backup |
| `/run/xray-manager-certificates` y leases | Excluir: son temporales y regenerables |
| Configuración activa Xray, runtime, firewall, servicios | Excluir del backup de datos; tratar en flujo de despliegue separado |
| REALITY como recurso TLS | Prohibido; REALITY no forma parte del catálogo TLS |

## 3. Protección criptográfica y recuperación de clave maestra

Los blobs del catálogo central están cifrados con la clave maestra del host. Copiar esos blobs sin una estrategia de recuperación de clave no permite restaurarlos en otro host.

**Hallazgo de auditoría:** el backup actual `scripts/vless_backup.py backup-data` crea un `tar.gz` de datos y manifiesto con hashes; no cifra el archivo completo. Los blobs de secretos ya están cifrados bajo la master key del host. `create-recovery` cifra una copia de la master key por separado con scrypt + AES-256-GCM, pero no cifra el backup de datos. Por tanto, no se debe describir el backup actual como un contenedor cifrado ni reutilizarlo como si ya ofreciera cifrado integral.

**Diseño que se implementará para el formato compartido:**

- Paquete independiente versionado con cifrado autenticado integral AES-256-GCM y clave derivada de una contraseña introducida interactivamente mediante scrypt. Parámetros KDF versionados y límites de recursos estrictos.
- Durante el backup, descifrar cada secreto legado/REALITY/TLS central en memoria usando el backend que corresponde, construir el contenido lógico del snapshot y cifrar el paquete antes de persistirlo. No escribir PEM/secretos descifrados en staging, archivos temporales, logs ni manifiestos.
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

- Adquirir locks de catálogos de conexiones VLESS, VMess y certificados en orden global fijo y compatible con resolutor/migrador.
- Validar catálogos y referencias mientras se mantienen locks.
- Capturar únicamente archivos regulares, root-owned, modos esperados, sin symlinks/hardlinks ni traversal.
- Construir snapshot en staging privado; no cambiar datos activos.
- Registrar hashes, tamaños, schema versions, revisions y dependencias en manifiesto.
- Liberar locks sólo después de cerrar/verificar el snapshot.

El orden exacto de locks debe reconciliarse con el código existente para evitar deadlocks; no asumir que el orden propuesto aquí ya está implementado.

## 5. Formato de paquete propuesto

Paquete lógico versionado, por ejemplo `xray-manager-shared-backup-v1`:

```text
manifest.json
connections/
  connections.json
  configurations/*.json
  secrets/*.bin
vmess/
  connections.json
  configurations/*.json
  secrets/*.bin
certificates/
  catalog.json
  managed/*.pem
  secrets/*.backup-envelope
external-dependencies.json
integrity.json
```

Los nombres y directorios son un contrato propuesto, no rutas actuales confirmadas. El paquete debe tener límites de tamaño/entradas, paths normalizados, hashes, identificación de backup y versión de esquema. El contenido sensible debe ir cifrado por el contenedor de backup; el manifiesto externo no debe exponer rutas privadas o datos innecesarios.

`external-dependencies.json` debe enumerar recursos `reference` con `certificate_id`, fingerprint, path esperado, conexión(es) dependientes y validación requerida. Las rutas son datos no confiables: nunca seguir symlinks durante restore.

## 6. Preflight de restauración

Antes de escribir en el host destino:

1. Verificar versión, integridad global, autenticidad, tamaño, límites y estructura del paquete.
2. Validar los dos catálogos de conexiones y todas las revisiones referenciadas.
3. Validar blobs REALITY sin exponer plaintext y validar que su `secret_ref` coincide.
4. Validar catálogo central, recursos `managed`/`reference`, fingerprints y blobs cifrados/envelopes.
5. Confirmar master key destino presente, válida y de 32 bytes sin mostrarla; o validar el mecanismo de re-envoltura acordado.
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

- Backup/verify/restore VLESS + VMess + TLS central + REALITY.
- Recursos managed y reference presentes/ausentes/modificados.
- Master key destino correcta, ausente e inválida; re-envoltura y passphrase errónea.
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

Los criterios funcionales anteriores están aprobados. El contrato del contenedor cifrado v1 ya está implementado y probado en aislamiento. Antes de escribir el orquestador de backup compartido se deben cerrar el manifiesto interno, el orden real de locks y la detección de conflictos del restore. La política de campos VMess queda definida en §10.1: excluir UUID por defecto y conservar email y level como metadatos dentro del payload cifrado. La desinstalación que incluya certificados ahora adquiere catalog.lock después de integrity.lock y lo mantiene durante el respaldo/confirmación/eliminación; la auditoría global de locks sigue abierta. La auditoría del código actual confirmó que el backup de datos VLESS no cifra el tar.gz completo; sólo los blobs de secretos usan cifrado bajo master key y el archivo de recuperación de master key se cifra aparte.

**Estado:** contenedor criptográfico neutral v1 IMPLEMENTADO y VERIFICADO con prueba aislada; snapshot, manifiesto, adaptadores VLESS/VMess/certificados, backup, verify, restore, journal y rollback aún NO IMPLEMENTADOS. No se ha creado ni restaurado un backup compartido.

## 10.2. Coordinación de desinstalación y catálogo TLS — 2026-11-03

Se corrigió modules/uninstall.sh para que, cuando la selección incluya la categoría certificates (incluidas las políticas all para Manager o ambos componentes), adquiera el bloqueo central catalog.lock antes de respaldar/eliminar las rutas. La adquisición se hace después de integrity.lock y antes del bloqueo de administración Xray. Orden en este flujo: lifecycle.lock → uninstall.lock → integrity.lock → catalog.lock (si se eliminan certificados) → bloqueo Xray.

Los bloqueos se adquieren de forma no bloqueante mediante manager_lock_acquire. Si catalog.lock está ocupado, la desinstalación se cancela antes de crear el respaldo o eliminar rutas. Cuando se obtiene, se mantiene durante la confirmación, el respaldo previo y la eliminación; el trap de retorno libera los bloqueos en orden inverso. Si no se seleccionan certificados, no se solicita catalog.lock.

Pruebas añadidas a tests/uninstall.sh: una operación concurrente que mantiene catalog.lock impide la desinstalación y conserva los datos; el caso de eliminación de la categoría certificates verifica que el lock sigue ocupado durante la confirmación. La suite completa de scripts shell pasó tras el cambio, junto con Bash syntax, ShellCheck del módulo modificado y git diff --check.

**Límite de auditoría:** esto corrige el camino de desinstalación y prueba la coordinación con el lock del catálogo; no certifica todavía que se hayan inspeccionado todos los mutadores ni que el orden global esté completamente cerrado. La auditoría estática y pruebas más amplias de concurrencia siguen pendientes antes del writer compartido.
