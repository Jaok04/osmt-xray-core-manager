# Diseño — renovación automática Certbot y aplicación controlada en Xray

**Fecha:** 2026-11-07
**Estado:** análisis de arquitectura; implementación live NO autorizada ni disponible.
**Ámbito:** diseño y futura implementación fixture-only. No modifica la normativa funcional.

## 1. Objetivo

Permitir que `certbot.timer` renueve certificados sin depender de que el Administrador esté abierto y que Xray adopte el certificado renovado únicamente después de validar y sincronizar de forma segura el almacén central y el runtime.

La cadena lógica requerida es:

1. `certbot.timer` ejecuta `certbot renew`.
2. Certbot invoca el deploy hook únicamente después de desplegar una renovación exitosa.
3. El hook identifica de forma segura el lineage renovado mediante `RENEWED_LINEAGE` y valida su asociación registrada; no confía en nombres arbitrarios ni en argumentos del shell.
4. El Manager valida certificado, clave, vigencia y SAN, y actualiza una revisión del mismo `certificate_id` conservando su identidad estable.
5. Se determina qué conexiones TLS activas referencian ese `certificate_id`.
6. Se valida la configuración candidata y se publica mediante el flujo transaccional autorizado.
7. Si Xray estaba activo, el backend live solicita la acción a `modules/xray_service.sh` bajo el lifecycle lock y verifica la postcondición. Si estaba inactivo, no lo inicia.
8. Se registra resultado, huellas, revisión, conexiones afectadas y evidencia de la operación. Una repetición del hook no debe duplicar revisiones ni recargas.

## 2. Hallazgos bloqueantes en el código actual

### 2.1 El almacén central no admite rotación

`scripts/certificate_store.py` declara `SCHEMA_VERSION = 1`. `load_catalog()` exige que cada registro tenga `revision == 1` y `secret_ref == secrets/<certificate_id>.r000001.bin`. `import_certificate()` siempre crea `revision = 1`, rechaza el `certificate_id` ya existente y escribe el certificado administrado como `managed/<certificate_id>.pem`.

Por tanto, la importación ACME actual solo crea certificados nuevos; no puede actualizar de forma segura el mismo `certificate_id` que ya referencian las conexiones.

### 2.2 El resolutor tampoco admite revisiones

`scripts/certificate_resolver.py` exige `item["revision"] == 1`, `secret_ref` de revisión `r000001` y para `storage_type=managed` lee `managed/<certificate_id>.pem`. No existe selección de revisión ni estrategia de publicación/rollback de material TLS.

### 2.3 Importar no aplica el certificado al servicio

`certificate_acme.py stage_and_import()` valida lineage, SAN y pareja certificado/clave, y crea un nuevo `certificate_id`. El flujo actual no correlaciona el lineage con un certificado central preexistente, no actualiza conexiones y no solicita una aplicación runtime.

### 2.4 El backend live no está habilitado

`LiveRuntimeBackend` sigue desconectado de R-05/CLI/menú. El lector de evidencia actual solo acredita fixtures y el backend live rechaza evidencia `environment=fixture`. `restore()` live falla cerrado. No se puede declarar que el hook puede recargar Xray de forma transaccional.

### 2.5 La unidad de servicio no está desplegada en VPS Pruebas

En el último estado observado, la VPS Pruebas no tenía `/etc/xray/config.json` ni `xray.service`. No hay todavía un servicio real que recargar.

## 3. Diseño de datos requerido

Se requiere una evolución compatible del almacén de certificados:

- Mantener `certificate_id` estable para que las conexiones no cambien sus referencias.
- Incorporar revisiones inmutables del certificado público y de la clave cifrada: `r000001`, `r000002`, etc.
- Cada revisión debe almacenar fingerprint SHA-256, public-key fingerprint, SAN, vigencia y referencias a blobs versionados.
- Un puntero `active_revision` selecciona la revisión vigente; no sobrescribir el blob anterior.
- La importación/rotación valida SAN contra los dominios autorizados del registro original y verifica que la clave corresponde al certificado.
- Rechazar revisión duplicada por fingerprint, rollback de revisión y cambio de identidad de clave no autorizado según política explícita.
- El resolver debe leer de forma atómica una revisión activa concreta, mantenerla fija durante la creación del lease y dejar evidencia de `certificate_id` + `revision` + fingerprint.
- La retención de revisiones previas permite rollback de archivos; no implica rollback automático del proceso Xray.

La migración debe aceptar el catálogo schema v1 sin reescribirlo durante lectura, ofrecer migración explícita y verificable a schema v2, preservar byte-a-byte los artefactos anteriores y fallar cerrado ante estados mixtos o referencias rotas.

## 4. Contrato del deploy hook

- Instalarlo en un directorio administrado root:root, no escribible por grupo/otros.
- Consumir `RENEWED_LINEAGE` y `RENEWED_DOMAINS` desde el entorno Certbot; no interpolarlos en shell ni construir comandos con `eval`.
- Comprobar ruta absoluta, componentes sin symlinks, lineage dentro del `config-dir` esperado y archivos regulares `fullchain.pem`/`privkey.pem` cuyos enlaces resuelvan dentro del archive autorizado.
- No imprimir ni registrar clave privada, token ACME ni contenido PEM.
- Usar lock dedicado de renovación y el lifecycle lock en el orden definido por el contrato transaccional; evitar deadlocks con locks de certificado/conexiones.
- Mantener un journal idempotente con identidad de lineage, fingerprint renovado, revisión candidata y estado (`received`, `validated`, `staged`, `published`, `reload_requested`, `verified`, `recovery_required`).
- El hook no ejecuta `systemctl`, `service`, `kill` ni comandos shell para reiniciar Xray. Solo invoca una interfaz del Manager validada.
- Si el Manager no puede aplicar la renovación, registrar el pendiente y devolver error a Certbot; no iniciar Xray ni reemplazar material activo parcialmente.

## 5. Contrato de aplicación runtime

- Resolver y validar la configuración completa con la nueva revisión antes de publicar.
- Capturar estado previo de servicio, MainPID, InvocationID y hash runtime.
- Solo se permite solicitar `restart` cuando el servicio estaba `active` y la identidad de proceso se verificó; si estaba `inactive`, mantenerlo inactivo.
- Delegar exclusivamente en `modules/xray_service.sh`, con lifecycle lock adquirido por R-05 y descriptor heredado verificado.
- Reobservar estado después de la acción. No equiparar aceptación de `systemctl restart` con configuración cargada verificada.
- Ante timeout/respuesta perdida, reconciliar por observación y journal; nunca repetir restart a ciegas.
- Para un fallo después de publicar, el rollback debe coordinar la revisión activa del certificado, la configuración runtime y la identidad del proceso. No se admite restaurar solo una de esas piezas.
- Si no existe evidencia suficiente o el rollback no es seguro, registrar `RECOVERY_REQUIRED`, conservar ambas revisiones y no realizar más mutaciones automáticas.

## 6. Política recomendada para certbot.timer

- Permitir la renovación periódica automática de Certbot.
- No modificar el calendario predeterminado del paquete sin necesidad demostrada.
- Inspeccionar `systemctl cat/status/list-timers` después de la instalación, no asumir nombre, calendario ni estado por versión.
- El deploy hook se ejecuta solo para una renovación exitosa; una ejecución sin certificado renovado no debe tocar el almacén ni Xray.
- La instalación del paquete y la activación/estado de `certbot.timer` se muestran al operador y requieren la confirmación correspondiente desde el Administrador.
- No usar `certbot renew --dry-run` como prueba de deploy hook de producción: definir una prueba aislada con directorios Certbot temporales y hooks mockeados.

## 7. Secuencia de implementación propuesta

1. Diseñar y aprobar schema v2 de certificados y migración v1→v2.
2. Implementar revisión inmutable, rotación y rollback del almacén con fixtures.
3. Actualizar `certificate_resolver.py` para resolver la revisión activa y fijar la revisión en cada lease.
4. Implementar registro lineage Certbot ↔ `certificate_id` central, con unicidad y validación de SAN.
5. Implementar hook y journal idempotente; probar variables ausentes, rutas maliciosas, symlinks, hardlinks, duplicados y reejecución.
6. Completar la integración transaccional live H6/R-05, incluidos rollback y reconciliación durable; el backend fixture permanece default.
7. Integrar la consulta/gestión de `certbot.timer` desde el Administrador, sin habilitar operaciones live por defecto.
8. Auditoría independiente, aceptación y autorización específica de publicación/despliegue.
9. Solo después, instalar Certbot, revisar el timer y emitir certificado en VPS Pruebas con autorización explícita. La recarga real espera a que exista `xray.service` y configuración validada.

## 8. Pruebas fixture obligatorias

- Renovación exitosa con SAN idénticos y clave igual/diferente según política aprobada.
- SAN incompletos, expirado, aún no válido, clave que no corresponde, PEM malformado.
- Lineage fuera de `/etc/letsencrypt`, symlink/hardlink, path traversal, archivo sustituido durante lectura.
- Renovación sin hook, hook duplicado y dos lineages renovados en una misma ejecución.
- Certificado no asociado, asociado a varias conexiones, conexión draft y conexión runtime activa.
- Xray active, inactive, failed, estado transitorio, InvocationID/PID divergentes.
- Configuración inválida, publicación fallida, restart fallido, timeout antes/después y respuesta perdida.
- Rollback completo, recovery repetido byte-a-byte idempotente y lock concurrente.
- Confirmar que nunca se inicia un servicio previamente inactivo y que el hook no invoca `systemctl`.

## 9. Límites de este diseño

Este documento no instala ni habilita `certbot.timer`, no crea hooks reales, no modifica el catálogo, no lee la clave maestra, no actualiza conexiones, no invoca systemd/Xray, no solicita certificados ni modifica VPS, DNS, firewall, puertos o red. No autoriza commit/push ni despliegue.
