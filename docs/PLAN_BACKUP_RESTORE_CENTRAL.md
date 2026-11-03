# Diseño de backup/restore compartido — conexiones y certificados centrales

**Versión:** 1.1
**Fecha:** 2026-11-03
**Estado:** CRITERIOS APROBADOS / DISEÑO CRIPTOGRÁFICO EN REVISIÓN / IMPLEMENTACIÓN PENDIENTE
**Ámbito:** backup consistente de conexiones VLESS/VMess y catálogo central TLS.

## 1. Objetivo

Añadir un flujo coordinado que respalde/restaure en conjunto:

- catálogo de conexiones y revisiones VLESS;
- catálogo de conexiones y revisiones VMess;
- blobs cifrados REALITY históricos/actuales de ambos protocolos;
- catálogo central de certificados TLS;
- certificados públicos `managed`;
- blobs cifrados de claves privadas centrales;
- manifiesto de dependencias externas para certificados `reference`.

Los backups de protocolo existentes deben seguir siendo compatibles y no deben incorporar silenciosamente el almacén central ni alterar su contrato. El backup compartido será un artefacto/versionado distinto o una capa orquestadora explícita.

## 2. Qué se incluye y qué no

| Elemento | Tratamiento |
|---|---|
| Catálogo VLESS y revisiones referenciadas | Incluir snapshot validado |
| Catálogo VMess y revisiones referenciadas | Incluir snapshot validado |
| Blobs REALITY por conexión | Incluir cifrados, con metadatos y referencias verificadas |
| Catálogo central TLS | Incluir snapshot |
| Certificados públicos `managed` | Incluir |
| Blobs privados centrales cifrados | Incluir en forma cifrada y autenticada |
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

## 11. Estado y siguiente diseño

Los criterios funcionales anteriores están aprobados. Antes de escribir el backup compartido se debe cerrar y probar el contrato de cifrado integral descrito en §3, el formato del manifiesto externo/interno, el orden real de locks y la detección de conflictos del restore. La auditoría del código actual confirmó que el backup de datos VLESS no cifra el tar.gz completo; sólo los blobs de secretos usan cifrado bajo master key y el archivo de recuperación de master key se cifra aparte.

**Estado:** criterios aprobados; implementación compartida no iniciada. No se ha creado ni restaurado un backup compartido.
