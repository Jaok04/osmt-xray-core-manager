# Auditoría R-03 — snapshot, journal y recuperación simulada

**Fecha:** 2026-11-04
**Resultado:** PASS técnico en fixtures aislados; pendiente de aceptación formal y publicación.
**Alcance:** scripts/xray_runtime_journal.py y tests/test_xray_runtime_journal.py.

## 1. Dictamen

R-03 captura una copia íntegra de la configuración runtime anterior dentro de XRAY_SERVICE_ROOT temporal, registra explícitamente su ausencia cuando no existe, persiste un journal durable y recupera interrupciones simuladas sin publicar configuración ni ejecutar acciones de servicio.

El alcance está limitado mediante marcadores obligatorios de fixture para XRAY_SERVICE_ROOT, operation_store y lease_root. Los locks de lifecycle/application deben ser distintos y residir dentro del operation_store aislado. No existen defaults hacia rutas live.

## 2. Controles

| Control | Resultado | Evidencia |
|---|---|---|
| Marcador XRAY_SERVICE_ROOT | PASS | root:root 0700 + marker JSON 0600 |
| Marcador operation_store | PASS | root:root 0700 + marker JSON 0600 |
| Locks separados y aislados | PASS | rutas dentro de operation_store/locks |
| Lease root R-02 | PASS | marcador fixture, rutas vinculadas al manifiesto y permisos root:grupo 0750 |
| Identidad profile/revision/validation | PASS | journal y snapshot contienen los tres IDs |
| Integridad de staging | PASS | hash/tamaño de config y manifiesto |
| Integridad de leases | PASS | manifiestos, IDs, certificado y UID/GID |
| Binario Xray | PASS | hash y tamaño coinciden con staging |
| Snapshot previo | PASS | bytes, SHA-256, tamaño, owner/group/mode |
| No previous config | PASS | estado explícito; no placeholder |
| Journal durable | PASS | atomic write, fsync y rename |
| Crash recovery | PASS | seis puntos de interrupción |
| Recuperación idempotente | PASS | segunda recuperación no altera estado |
| Corrupción | PASS | conserva evidencia y marca recovery_required |
| Symlink/hardlink | PASS | rechazo fail-closed |
| Lock contention | PASS | aborta sin crear operación |
| Runtime publication | PASS | no se modifica config del fixture |
| systemd | PASS | ninguna llamada/acción |

## 3. Pruebas focales

tests/test_xray_runtime_journal.py: **22/22 PASS**.

La matriz de interrupciones cubre after_prepared, after_snapshot_dir, after_validated, after_snapshot_config, after_snapshot_metadata y after_snapshot_saved. La prueba de integración R-02/R-03 verifica que el staging real, el manifiesto con rutas fixture y el lease central sintético son aceptados por el journal R-03. Se verifica la recuperación repetida. Un snapshot incompleto se aborta; un snapshot completo con journal atrasado se finaliza; una integridad rota se conserva en recovery_required.

## 4. Regresión

- Python: 140/140 PASS.
- Shell: 58/58 PASS.
- py_compile: PASS.
- bash -n global: PASS.
- install.sh --check: PASS.
- ShellCheck -S error sobre tests/*.sh: PASS.
- git diff --check: PASS.

## 5. Hallazgos y límites

No se identificó un defecto bloqueante dentro del alcance R-03 probado.

R-03 no implementa publicación, rollback de archivo runtime ni reinicio/verificación de servicio. Los leases exitosos se conservan y su cleanup queda pendiente de R-04/R-05. La prueba utiliza el estado de servicio fixture y no consulta systemd real. El snapshot guarda una copia sintética del config previo y no modifica el destino.

## 6. Protecciones

No se accedió a la clave maestra real ni a almacenes live. No se modificaron /etc/xray/config.json, systemd, runtime, certificados desplegados, firewall, puertos, red, dependencias, main, Xray-Normativa/ ni VPS de pruebas. R-06/live y NetMod permanecen NO AUTORIZADAS.

## 7. Estado

R-03: IMPLEMENTADA / VERIFICADA EN FIXTURES / AUDITADA LOCALMENTE. Pendiente de aceptación formal y publicación en la rama autorizada. R-04 y R-05 pendientes.


## Reconciliación posterior de publicación — 2026-11-04

R-03 está AUDITADA, PUBLICADA y SINCRONIZADA en la rama autorizada, commit de corte `05aceabf11414040abbb32fff1428984370ff521`. La aceptación formal del propietario sigue PENDIENTE. La frase anterior «pendiente de aceptación formal y publicación» corresponde al estado previo al commit y queda superada únicamente respecto de la publicación. El dictamen y sus limitaciones permanecen vigentes.
