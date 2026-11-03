# Diseño de backup/restore compartido — conexiones y certificados centrales

**Versión:** 1.0
**Fecha:** 2026-11-03
**Estado:** PROPUESTA TÉCNICA / NO APROBADA PARA IMPLEMENTACIÓN
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

**Propuesta preferida:** el backup compartido debe envolver los blobs centrales con la protección de backup ya utilizada por el sistema (KDF robusta, cifrado autenticado y verificación de integridad), sin exportar `master.key`. En restore, los blobs se desenvuelven en memoria y se vuelven a cifrar bajo la clave maestra existente del destino, ligando la autenticación a `certificate_id` y revisión. No escribir claves privadas en claro en el staging ni en archivos temporales.

Alternativa de recuperación: usar la misma master key mediante un procedimiento de escrow externo, cifrado y fuera del paquete. No guardar la master key junto a los datos que protege. La decisión final debe comprobar compatibilidad con el mecanismo actual de backup y con `certificate_crypto.py` antes de implementar.

La contraseña/clave de backup no se almacena en el manifiesto. El proceso debe fallar cerrado ante contraseña incorrecta, tag inválido, clave maestra ausente/inválida o envelope incompatible.

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

## 10. Decisiones requeridas

1. Aprobar la re-envoltura de secretos centrales para restaurar bajo una master key destino (recomendado) o exigir escrow externo de la misma master key.
2. Definir si la falta de un certificado `reference` bloquea todo el restore o permite un restore parcial con conexiones bloqueadas (recomendado: bloquear todo por defecto).
3. Definir política de merge cuando existen conexiones nuevas en destino posteriores al backup.
4. Definir retención, cifrado externo, custodia de contraseña y almacenamiento fuera del VPS.
5. Aprobar formato/CLI compartido y plan de compatibilidad antes de implementar.

**Estado:** diseño propuesto. No se ha implementado un backup compartido ni se ha exportado/importado el catálogo central.
