# Arquitectura de certificados TLS centralizados

**Versión:** 1.1 — contrato con primer almacén y resolutor parciales
**Fecha:** 2026-11-03
**Estado:** DISEÑO APROBADO; almacén y resolutor IMPLEMENTADOS PARCIALMENTE; integración VMess/VLESS pendiente
**Rama:** `design/user-identity-association-v1`
**Normativa funcional de referencia:** `Xray-Normativa/04_Certificados_Dominios/Etapa_4_Certificados_Dominios.md` v1.1 (inmutable)

## 1. Propósito y límites

Definir el contrato técnico para que VMess y VLESS utilicen una identidad central de certificado TLS y una única copia cifrada de su clave privada, en lugar de almacenar una copia cifrada por conexión.

Este documento desarrolla una decisión arquitectónica aprobada por el propietario. No sustituye ni modifica la especificación funcional normativa de Etapa 4. La implementación completa de la Etapa 4 (ACME, DNS, renovación, menús y diagnóstico) no queda declarada realizada por este diseño.

**Alcance de este bloque:** catálogo central, referencias, secreto privado central, resolución controlada para Xray, integración VMess/VLESS, migración histórica, backup/restore, pruebas y documentación.

**Fuera de alcance inmediato:** emisión ACME, automatización DNS, renovación automática, modificación de conexiones activas, cambios en runtime o despliegue en la VPS de pruebas. Cada uno requiere su diseño/validación y autorización aplicable.

## 2. Decisiones aprobadas por el propietario

1. Existirá un catálogo central de certificados, independiente del catálogo de conexiones.
2. Se admitirán recursos de tipo `managed` y `reference`.
3. Cada recurso de certificado tendrá una única identidad central para su clave privada cifrada.
4. Las conexiones VMess y VLESS referenciarán el recurso mediante `certificate_id`; no conservarán una copia cifrada propia de esa clave ni rutas libres a la clave.
5. Un resolutor controlado será responsable de preparar los archivos que Xray necesita.
6. Las conexiones no podrán leer arbitrariamente secretos de otros recursos: la resolución comprobará la asociación/autorización.
7. Las renovaciones o sustituciones se administrarán en el recurso central y no reescribirán automáticamente conexiones.
8. REALITY conservará su propio modelo de clave y permanecerá fuera del catálogo TLS.
9. La migración reconocerá datos históricos, verificará correspondencia criptográfica, conservará los secretos anteriores hasta validar la migración y permitirá auditoría/reversión.
10. No se borrarán automáticamente secretos históricos ni se modificarán configuraciones runtime existentes.

La aprobación del modelo no equivale a aceptación de la implementación ni autoriza cambios en la VPS de pruebas.

## 3. Relación con la normativa

La Etapa 4 normativa v1.1 requiere, entre otros puntos, gestionar certificados y dominios, instalar certificados existentes, validar certificado/clave/dominio, proteger claves privadas, conservar el certificado vigente hasta validar el nuevo y no modificar automáticamente conexiones Xray al gestionar certificados o dominios.

El catálogo central es una decisión de implementación compatible con esos principios. La especificación normativa no define el modelo de persistencia, el formato del catálogo, el identificador ni el mecanismo de resolución. Este documento no presenta esos detalles como requisitos normativos ya aprobados.

La carpeta `Xray-Normativa/` queda excluida de todos los cambios de este trabajo hasta consentimiento previo, explícito y específico.

## 4. Modelo conceptual

### 4.1 Recurso de certificado

Cada recurso tiene un identificador estable, por ejemplo `cert-001`, independiente de los IDs de conexión.

Campos conceptuales mínimos:

| Campo | Propósito |
|---|---|
| `schema_version` | Versión del formato persistido |
| `certificate_id` | Identificador estable e inmutable |
| `storage_type` | `managed` o `reference` |
| `certificate_source` | Ubicación controlada del certificado público |
| `secret_ref` | Referencia interna al secreto cifrado central; nunca el secreto |
| `fingerprint_sha256` | Identidad criptográfica del certificado |
| `subject` / `issuer` | Metadatos públicos |
| `sans` | Nombres DNS/IP cubiertos |
| `not_before` / `not_after` | Vigencia |
| `public_key_fingerprint` | Huella de la clave pública para cotejar el par |
| `status` | Estado administrativo/validación |
| `revision` | Revisión monotónica del recurso |
| `created_at` / `updated_at` | Auditoría temporal |

El catálogo nunca contendrá bytes PEM de la clave privada, contraseña, plaintext, clave maestra ni material secreto.

### 4.2 Semántica de almacenamiento

- **managed:** el administrador conserva una copia controlada del certificado público en su espacio de gestión. La clave privada se cifra y se conserva una sola vez en el almacén central de secretos.
- **reference:** el certificado público permanece en su ubicación externa original y el administrador conserva una referencia validada. La clave privada se importa al almacén central cifrado para que el resolutor disponga de una identidad central uniforme. El archivo externo original no se mueve, modifica ni elimina.
- En ambos casos, el secreto central es la fuente de la clave privada utilizada por el resolutor. No se permite una segunda copia cifrada por conexión.
- La importación no autoriza borrar el archivo de clave externo. La eliminación de originales es una operación independiente, explícita y fuera de la migración automática.

Si una instalación futura requiere una semántica diferente para `reference`, deberá presentarse como cambio de diseño antes de implementarla.

### 4.3 Identidad y deduplicación

- `certificate_id` es estable y no se deriva de un nombre de dominio ni de un ID de conexión.
- La huella SHA-256 del certificado permite detectar el mismo certificado importado más de una vez.
- Antes de consolidar registros se verifica que la clave privada corresponda criptográficamente al certificado.
- La misma huella de certificado con material de clave incompatible es un conflicto bloqueante; no se fusiona.
- No se deduplican certificados distintos únicamente porque compartan clave pública o dominio.
- La rotación de certificado se registra como una nueva revisión/recurso conforme al procedimiento de reemplazo; el recurso anterior se conserva hasta validar el nuevo y sus dependencias.

## 5. Contrato de conexión VMess/VLESS

Una conexión TLS persistida contendrá una referencia:

```json
{
  "security": "tls",
  "security_options": {
    "certificate_id": "cert-001"
  }
}
```

Reglas:

- `certificate_id` es obligatorio para TLS gestionado por el administrador.
- La conexión no persistirá `certificate_file`, `key_file`, `secret_ref` ni una copia cifrada de la clave.
- No se permitirá resolver un ID inexistente, inactivo, corrupto o incompatible.
- El modelo neutral valida forma y referencia; el almacén central valida existencia, integridad y correspondencia.
- REALITY conserva sus campos y secreto independientes; nunca se convierte en recurso TLS.
- Cualquier formato histórico se tratará mediante migración versionada, no mediante aceptación silenciosa de campos antiguos en el nuevo contrato.

La forma exacta del objeto de configuración deberá mantenerse consistente entre los modelos VMess/VLESS, sus almacenes, asistentes, generadores, listados y backup/restore.

## 6. Almacén central y protección criptográfica

El almacén central será el único responsable de cifrar, recuperar, auditar y versionar las claves privadas de certificados.

Requisitos obligatorios:

1. Cifrado autenticado (AEAD); no almacenar claves privadas en claro en catálogos ni archivos de configuración.
2. Vincular criptográficamente el ciphertext a su identidad y contexto mediante AAD que incluya, como mínimo, el ID de certificado, versión de esquema y revisión.
3. Rechazar ciphertext alterado, referencias rotas, revisiones incoherentes, symlinks y archivos inseguros.
4. Aplicar permisos restrictivos a directorios, almacén y material temporal.
5. No imprimir secretos ni incluirlos en argumentos de proceso, logs, informes, errores, backups sin cifrar o commits.
6. No borrar automáticamente huérfanos o secretos históricos: la auditoría informa y la limpieza exige procedimiento explícito.
7. Registrar eventos sin incluir material secreto.
8. No reutilizar formatos VMess/VLESS por inferencia. Antes de elegir la clave maestra y el formato final se auditarán ambos módulos criptográficos y su compatibilidad; cualquier cambio de formato será versionado.

La implementación deberá identificar la clave maestra realmente utilizada por cada almacén, su ruta, permisos, inicialización, backup y compatibilidad. No se asumirá que los almacenes actuales comparten clave maestra sólo porque exista una ruta común en configuración.

## 7. Resolutor TLS

El resolutor es la única frontera entre el secreto central y los archivos que Xray necesita.

Flujo contractual:

1. Recibe el ID de conexión y el `certificate_id` solicitado.
2. Comprueba que la conexión existe, que el protocolo es VMess/VLESS y que su configuración referencia ese certificado.
3. Comprueba que el recurso está disponible, íntegro, habilitado y en revisión válida.
4. Valida certificado, vigencia, SAN y correspondencia criptográfica con la clave privada.
5. Recupera el secreto central autenticado.
6. Prepara los archivos de entrada para Xray en una ubicación protegida, con permisos compatibles con la identidad real del servicio.
7. Devuelve rutas controladas al generador/aplicador autorizado, sin devolver la clave privada en texto a la capa de interfaz.
8. Limpia los archivos temporales conforme a un ciclo de vida verificable y registra el resultado sin secretos.

No se fija todavía el propietario/grupo/modo final de los archivos preparados. Se determinará tras inspeccionar la unidad systemd y el usuario/grupo efectivo de Xray en el entorno de desarrollo. Se debe fallar de forma cerrada si no se puede garantizar lectura por Xray sin exponer la clave a otros usuarios.

El resolutor no modifica por sí mismo conexiones, certificados externos, configuración activa, firewall ni servicio.

Implementación parcial documentada en docs/IMPLEMENTACION_RESOLUTOR_CERTIFICADOS_TLS.md: scripts/certificate_resolver.py valida la asociación exacta connection_id/certificate_id, consulta catálogos/configuraciones versionados, verifica el recurso central, prepara un lease temporal con archivos root:<grupo-servicio> y permite limpieza controlada.

El contrato TLS central (security_options exactamente {certificate_id}) aún no está admitido por los almacenes actuales VMess/VLESS. Las pruebas usan fixtures de ese contrato; no prueban integración de asistentes/generadores ni lectura por un Xray real. La CLI obtiene User/Group de systemd y falla cerrada si no hay unidad/identidad explícita. En la VPS de desarrollo no existe xray.service ni cuenta/grupo xray.

Los temporales se preparan bajo /run/xray-manager-certificates, raíz/lease root:<grupo-servicio> 0750, archivos 0640. La clave se mantiene temporalmente en memoria y en el archivo que el servicio debe leer. El runtime path es volátil; la futura integración deberá recrearlo antes de validar/iniciar Xray.

## 8. Integración con generadores y runtime

- Los generadores VMess/VLESS dejan de aceptar rutas libres a claves para el flujo TLS centralizado.
- El generador consume únicamente rutas preparadas por el resolutor autorizado.
- La generación de JSON/draft y la aplicación al runtime son operaciones distintas.
- Esta integración no autoriza activar conexiones ni sobrescribir `/etc/xray/config.json`.
- El despliegue runtime requerirá un diseño separado con backup, validación, publicación atómica, reinicio controlado, health-check y rollback; además, consentimiento específico.
- No se tocará la VPS `Vps de Pruebas` durante este trabajo.

## 9. Migración de datos históricos

La migración debe ser versionada, idempotente, auditable y reversible.

Secuencia mínima:

1. Inventariar todas las entradas TLS VMess/VLESS, referencias de configuración y secreto, revisiones, rutas de certificado y archivos asociados.
2. Crear un backup recuperable del estado anterior y verificar su integridad antes de modificar datos.
3. Agrupar candidatos por huella del certificado; verificar SAN, vigencia y correspondencia criptográfica de cada clave.
4. Detectar conflictos, duplicados ambiguos, rutas ausentes, claves no coincidentes, symlinks y permisos inseguros. Los casos ambiguos bloquean la migración; no se elige una clave por heurística.
5. Crear un recurso central y cifrar una única vez la clave verificada.
6. Migrar referencias de conexiones a `certificate_id` mediante staging y publicación controlada.
7. Leer el secreto central y reconstruir entradas temporales; validar ambos protocolos y las configuraciones resultantes.
8. Ejecutar auditoría de referencias, secretos, huérfanos, integridad y aislamiento.
9. Conservar los secretos históricos sin borrarlos y registrar cómo revertir referencias/catálogos.
10. Retirar datos históricos sólo mediante una fase posterior expresamente aprobada, con evidencia de recuperación.

La migración nunca cambia runtime ni borra archivos externos.

## 10. Backup y restauración

El backup central debe conservar la relación entre catálogo de certificados, ciphertexts, revisiones y dependencias externas.

- Los secretos centrales se incluyen únicamente dentro de un backup cifrado y autenticado.
- Los backups no incluyen plaintext de claves privadas.
- Para recursos `reference`, se registra la dependencia externa; no se empaquetan ni copian silenciosamente archivos de terceros.
- Para recursos `managed`, se incluyen los archivos públicos administrados necesarios para reconstrucción.
- La restauración valida integridad, IDs, revisiones, referencias, AAD y disponibilidad de dependencias antes de publicar.
- Restaurar certificados no modifica automáticamente conexiones ni runtime.
- El backup VLESS actual no debe incorporar secretos VMess ni viceversa por accidente; el nuevo recurso central será un dominio de backup compartido con reglas explícitas de aislamiento.
- Una restauración parcial que deje conexiones con `certificate_id` inexistentes debe fallar o dejar el conjunto inactivo y claramente diagnosticado; nunca declarar éxito íntegro.

## 11. Seguridad y aislamiento

- Una conexión sólo puede resolver el certificado que figura en su propia configuración y que está autorizado en el catálogo.
- No se acepta un `certificate_id` arbitrario suministrado por una capa no confiable sin comprobar la asociación.
- Las interfaces no muestran PEM, ciphertext ni rutas privadas sensibles.
- Los errores distinguen ausencia, corrupción, falta de permisos y asociación no autorizada sin filtrar secretos.
- Los archivos temporales no deben quedar legibles por usuarios ajenos al servicio.
- La limpieza debe ejecutarse también ante fallos/cancelación y tener una estrategia de recuperación ante terminación abrupta.
- REALITY mantiene separación de secretos y pruebas específicas.

## 12. Pruebas y criterios de aceptación técnica

Se requieren pruebas focales y cruzadas, al menos:

| Área | Casos mínimos |
|---|---|
| Catálogo | alta/listado/lectura, IDs duplicados, schema/revisión inválidos, colisión de huella |
| Importación | managed/reference, certificado ausente, clave no coincidente, SAN, vigencia |
| Criptografía | round-trip, ciphertext/tag alterado, AAD incorrecto, clave maestra ausente/inválida |
| Seguridad filesystem | symlink, hardlink, permisos, propietario, archivos no regulares, temporal residual |
| Resolutor | conexión autorizada, ID ajeno, recurso inactivo, secreto corrupto, limpieza |
| VMess | creación TLS, persistencia, recuperación, generación y validación Xray |
| VLESS | creación TLS, persistencia, recuperación, generación y validación Xray |
| Aislamiento | VMess no altera VLESS y viceversa; REALITY permanece intacto |
| Migración | duplicados idénticos, conflictos, interrupción, reanudación, auditoría, rollback |
| Backup/restore | recursos centrales, referencias externas ausentes, corrupción, restauración parcial y aislamiento |
| Regresión | suite completa del proyecto y pruebas previas VMess/VLESS |

Un test de JSON válido o `xray run -test` no demuestra conectividad extremo a extremo. Las pruebas live requieren un entorno controlado y autorización específica.

## 13. Etapas de implementación

| Etapa | Entregable | Estado |
|---|---|---|
| 1 | Contrato arquitectónico, esquema y decisiones de seguridad | DOCUMENTADO; revisión evolutiva pendiente |
| 2 | Catálogo central y almacén cifrado | IMPLEMENTADO PARCIALMENTE; import/list/show/audit |
| 3 | Resolutor TLS y posterior integración VMess | RESOLUTOR PARCIAL IMPLEMENTADO; integración pendiente |
| 4 | Integración VLESS | PENDIENTE |
| 5 | Migración versionada y reversible | PENDIENTE |
| 6 | Backup/restore central compartido | PENDIENTE |
| 7 | Pruebas cruzadas, aislamiento y regresión | PARCIAL; pruebas focales y regresión base |
| 8 | Auditoría integral, documentación final y continuidad | PENDIENTE |

Cada etapa tendrá inventario, trazabilidad, pruebas y evidencia. Ninguna etapa se cerrará sin auditoría integral y aceptación formal del propietario.

## 14. Decisiones técnicas pendientes después de los primeros bloques

Los primeros bloques cerraron las decisiones siguientes:

- Clave maestra: se reutiliza en lectura la ruta común existente /etc/xray-manager/keys/master.key; no se crea, regenera ni modifica.
- Envelope: AES-256-GCM, nonce aleatorio de 12 bytes, AAD xray-manager:certificate-secret:v1:<certificate_id>:<revision>, JSON versionado.
- Catálogo: /var/lib/xray-manager/certificates/catalog.json, con directorios separados managed/, references/ (reservado) y secrets/.
- Resolución temporal: lease volátil bajo /run/xray-manager-certificates; raíz/lease root:<grupo-servicio> 0750, archivos 0640.
- Identidad del servicio: se consulta la identidad efectiva de systemd; no se asume usuario/grupo ni se permite resolver cuando no se puede verificar.
- La conexión debe autorizar exactamente el certificate_id guardado en su configuración; se bloquean rutas TLS libres y referencias ajenas.

Continúan pendientes antes de integrar y usar el resolutor en producción:

- Cambiar contratos de configuración, catálogos, asistentes y generadores VMess/VLESS para guardar/consumir certificate_id.
- Confirmar la unidad systemd instalada y su usuario/grupo efectivos en un entorno donde Xray exista; probar lectura real dentro de sus restricciones (ProtectSystem, PrivateTmp).
- Resolver el ciclo de vida de leases al aplicar/reiniciar Xray y recrear temporales después de reinicio.
- Diseñar publicación atómica de configuración y rollback de runtime en un bloque independiente, con autorización expresa.
- Política de rotación y revisiones posteriores a r1.
- Migración versionada, idempotente y reversible de secretos históricos.
- Backup/restore compartido y reglas de aislamiento.
- Estrategia de limpieza de leases abandonados, sin eliminar archivos fuera del directorio controlado.
- Validar la semántica de reference y dependencias externas durante backup/restore.

No se habilitará runtime ni se borrarán secretos históricos para avanzar más rápido.

## 15. Evidencia y estado

Este documento registra el diseño aprobado y dos bloques de implementación parcial; no declara terminado el sistema central de certificados.

- Decisión arquitectónica: APROBADA por el propietario.
- Catálogo/almacén central: IMPLEMENTADO PARCIALMENTE; import/list/show/audit, pruebas focales y regresión.
- Resolutor TLS: IMPLEMENTADO PARCIALMENTE; autorización, verificación, temporales y limpieza probados con fixtures.
- Contrato TLS central en stores/asistentes/generadores VMess/VLESS: PENDIENTE.
- Xray real, identidad efectiva y sandbox: NO PROBADO; la VPS de desarrollo carece de servicio/cuenta Xray.
- Migración y backup/restore central: PENDIENTES.
- Runtime y VPS de pruebas: SIN MODIFICACIONES.
- Normativa: SIN MODIFICACIONES.
- Aceptación de implementación: PENDIENTE.

## 16. Primer bloque implementado — catálogo y secreto central

El primer bloque está implementado y documentado en docs/IMPLEMENTACION_ALMACEN_CERTIFICADOS_CENTRALIZADOS.md.

- scripts/certificate_crypto.py: envelope AES-256-GCM con AAD por certificado/revisión; lectura estricta de la clave maestra existente, sin crearla ni regenerarla.
- scripts/certificate_store.py: importación managed/reference, catálogo independiente, consulta/listado y auditoría de blobs, referencias y archivos huérfanos. No expone plaintext de clave privada.
- config/paths.sh: rutas dedicadas para catálogo, managed, references (reservado), secretos y bloqueo.
- tests/certificate_store.sh: casos positivos y negativos del almacén.
- Suite completa ejecutada después de este bloque: 41/41 scripts PASS. bash -n, py_compile, ShellCheck de la prueba nueva y git diff --check: PASS.
- Las pruebas usan fixtures y directorios temporales. No se importó ningún certificado al almacén persistente real.
- No hay operación resolve, integración VMess/VLESS, migración ni backup/restore central.
- No se modificaron runtime, servicio, firewall, puertos, certificados desplegados ni Xray-Normativa.

Estado: catálogo/almacén IMPLEMENTADO PARCIALMENTE y VERIFICADO en pruebas aisladas y regresión del proyecto. Aceptación formal pendiente.


## 17. Segundo bloque implementado — resolutor TLS parcial

Informe: docs/IMPLEMENTACION_RESOLUTOR_CERTIFICADOS_TLS.md.

- scripts/certificate_resolver.py comprueba la conexión, protocolo, referencia/revisión de configuración y asociación exacta security_options.certificate_id.
- Comprueba estado y revisión del certificado, referencia central, autenticación AES-GCM, par criptográfico, huellas y vigencia.
- Admite recursos managed y reference.
- Prepara leases aleatorios bajo /run/xray-manager-certificates, con archivos root:<grupo-servicio> 0640 y directorios 0750; no imprime secretos.
- La identidad de servicio se obtiene de systemctl show; exige User y Group explícitos, sin grupos suplementarios. En la VPS de desarrollo no hay unidad/cuenta Xray y la CLI rechaza la operación sin crear temporales.
- La limpieza verifica lease, manifest, propietario/grupo/permisos y sólo elimina el directorio de ese lease.
- tests/certificate_resolver.sh: casos VLESS/VMess, managed/reference, autorización, permisos, cleanup y fallos cerrados.
- Regresión completa tras el bloque: 42/42 scripts PASS. bash -n, py_compile, ShellCheck de ambas pruebas y git diff --check: PASS.
- Los stores VMess/VLESS actuales aún no aceptan el contrato central certificate_id; las pruebas usan fixtures. No hay integración de asistentes/generadores ni lectura por Xray real.
- No se tocó runtime, servicio, firewall, puertos, VPS Vps de Pruebas, secretos históricos, REALITY ni Xray-Normativa.

Estado: resolutor IMPLEMENTADO PARCIALMENTE y VERIFICADO con fixtures; no aceptado para producción.
