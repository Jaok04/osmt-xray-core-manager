# Implementación inicial — almacén central de certificados TLS

**Fecha:** 2026-11-03
**Versión:** 1.0
**Estado:** IMPLEMENTADO Y VERIFICADO EN PRUEBAS AISLADAS; integración operativa pendiente
**Rama:** `design/user-identity-association-v1`

## 1. Alcance de la entrega

Se implementó la primera parte del modelo aprobado: primitives criptográficas versionadas, catálogo independiente de certificados, importación de recursos `managed` y `reference`, consulta/listado y auditoría de integridad.

No se integraron todavía VMess/VLESS, asistentes, generadores, runtime, backup/restore ni migración. Esta entrega no activa certificados en Xray.

## 2. Archivos incorporados/modificados

| Archivo | Cambio |
|---|---|
| `scripts/certificate_crypto.py` | Nuevo cifrado autenticado AES-256-GCM del secreto central |
| `scripts/certificate_store.py` | Nuevo catálogo, importación, consulta, listado y auditoría |
| `config/paths.sh` | Rutas dedicadas para catálogo, managed, references, secretos y bloqueo |
| `tests/certificate_store.sh` | Prueba aislada de importación, integridad y casos negativos |
| `docs/ARQUITECTURA_CERTIFICADOS_CENTRALIZADOS.md` | Contrato arquitectónico y decisiones técnicas actualizadas |
| `docs/IMPLEMENTACION_ALMACEN_CERTIFICADOS_CENTRALIZADOS.md` | Este informe |
| `PROJECT_STATE.md`, `docs/PUNTO_CONTROL_ACTUAL.md`, `docs/CONTINUIDAD_DEL_PROYECTO.md`, `HISTORY.md` | Continuidad y trazabilidad |

## 3. Persistencia

Rutas definidas en `config/paths.sh`:

- Base: `/var/lib/xray-manager/certificates`
- Catálogo: `/var/lib/xray-manager/certificates/catalog.json`
- Certificados administrados: `/var/lib/xray-manager/certificates/managed`
- Directorio reservado para referencias: `/var/lib/xray-manager/certificates/references`
- Secretos cifrados: `/var/lib/xray-manager/certificates/secrets`
- Bloqueo: `/var/lib/xray-manager/certificates/catalog.lock`

El catálogo tiene `schema_version=1`, una revisión global y una colección de recursos. Cada registro contiene ID, tipo de almacenamiento, referencia al certificado público, referencia al secreto cifrado, huellas, sujeto/emisor, SAN DNS, vigencia, estado y revisión. No contiene PEM de clave privada ni plaintext.

La referencia `managed` apunta a `managed/<certificate_id>.pem`; el certificado público se copia a ese directorio. La referencia `reference` conserva la ruta absoluta del certificado externo y no copia ni mueve ese archivo. En ambos casos la clave privada se cifra una sola vez en `secrets/<certificate_id>.r000001.bin`.

## 4. Contrato criptográfico implementado

- Algoritmo: AES-256-GCM.
- Clave: 32 bytes.
- Nonce: 12 bytes aleatorios por cifrado.
- AAD: `xray-manager:certificate-secret:v1:<certificate_id>:<revision>`.
- Envelope JSON: `format_version`, `algorithm`, `certificate_id`, `revision`, `nonce`, `ciphertext`.
- La clave maestra se lee desde `/etc/xray-manager/keys/master.key`, que es la ruta común ya utilizada por los almacenes actuales. El almacén nuevo no crea, regenera ni modifica esa clave.
- En la VPS de desarrollo se verificaron sólo metadatos de la clave existente: archivo regular, propietario `root:root`, modo `0600`, un hardlink y 32 bytes. Su contenido no fue leído.
- El nuevo AAD separa criptográficamente este formato de los formatos históricos VMess/VLESS vinculados a IDs de conexión.

## 5. Validaciones y controles

La importación:

1. Requiere ejecución como root.
2. Rechaza certificado/clave que no sean archivos regulares, symlinks o hardlinks.
3. Exige clave privada de origen `root:root`, modo `0600`.
4. Valida PEM de certificado y clave privada sin passphrase.
5. Compara las claves públicas SubjectPublicKeyInfo en DER.
6. Rechaza certificados fuera de su período de validez.
7. Registra huella SHA-256, huella de clave pública, sujeto, emisor, SAN DNS y vigencia.
8. Rechaza IDs duplicados y certificados duplicados por huella.
9. Usa bloqueo exclusivo para operaciones del catálogo.
10. Escribe blobs y catálogo con staging/escritura atómica, permisos root-only y sincronización de directorio.
11. Ante una interrupción entre la escritura del blob y la publicación del catálogo, conserva el archivo huérfano para auditoría; no lo borra automáticamente.

La auditoría comprueba referencias, descifra/authentica el secreto, vuelve a validar el par certificado/clave, verifica huellas, detecta secretos/archivos administrados huérfanos y entradas inseguras. No elimina datos.

## 6. Interfaz CLI disponible

Los argumentos globales permiten seleccionar rutas de base, catálogo, managed, secretos, clave maestra y bloqueo.

Subcomandos implementados:

- `import --storage-type managed|reference --certificate-file ... --private-key-file ... [--certificate-id ...]`
- `list`
- `show --certificate-id ...`
- `audit`

Las respuestas son JSON. No existe todavía una operación que entregue plaintext a un resolutor; tampoco existe un comando de rotación o eliminación.

## 7. Pruebas ejecutadas

Prueba focal `tests/certificate_store.sh`:

- importación managed y catálogo sin clave privada;
- blob cifrado y permisos;
- list/show/audit sin referencias rotas;
- deduplicación por huella;
- importación reference conservando el certificado externo;
- rechazo de clave no coincidente;
- rechazo de symlink de clave privada;
- detección de ciphertext/tag alterado;
- clave maestra ausente rechazada sin regeneración.

Resultado focal: PASS.

Verificaciones ejecutadas después de los cambios:

- `bash -n tests/certificate_store.sh`: PASS.
- `python3 -m py_compile scripts/certificate_crypto.py scripts/certificate_store.py`: PASS.
- `shellcheck -S warning tests/certificate_store.sh`: PASS.
- `git diff --check`: PASS.
- Suite completa del proyecto, ejecutada después del ajuste final de locking: 41/41 scripts PASS.

## 8. Límites y pendientes

- No hay resolutor TLS; el almacén no entrega todavía la clave privada a Xray.
- No se implementó autorización por conexión ni se cambió el contrato TLS VMess/VLESS.
- No se migraron registros históricos ni se borró ningún secreto existente.
- No se adaptó backup/restore VLESS/VMess al catálogo compartido.
- No hay rotación de certificado ni revisiones posteriores a r1.
- La ruta `references/` está reservada; el path externo se conserva actualmente en el catálogo.
- No hay Xray instalado ni unidad/usuario/grupo `xray` en la VPS de desarrollo. No se fijaron permisos de resolución para un servicio no presente.
- No se probó resolución contra un runtime real.
- No se creó ningún recurso persistente en el catálogo real de la VPS; las importaciones se probaron en directorios temporales.
- No se tocó la VPS `Vps de Pruebas`, certificados desplegados, runtime, firewall, puertos ni servicio.
- `Xray-Normativa/` permanece intacta.

## 9. Estado por categoría

| Categoría | Estado |
|---|---|
| Diseño centralizado | APROBADO |
| Contrato técnico | DOCUMENTADO |
| Criptografía central | IMPLEMENTADA; pruebas focales PASS |
| Catálogo/importación | IMPLEMENTADO; pruebas focales PASS |
| Auditoría | IMPLEMENTADA; pruebas focales PASS |
| Integración VMess | PENDIENTE |
| Integración VLESS | PENDIENTE |
| Resolutor TLS | PENDIENTE |
| Migración histórica | PENDIENTE |
| Backup/restore central | PENDIENTE |
| Runtime real | NO PROBADO |
| Aceptación del propietario | PENDIENTE |

**No declarar terminada la Etapa 4 ni aceptada la implementación global de certificados.**
