# Evidencia correlativa de arranque live — etapa aislada (2026-11-08)

**Estado:** implementado y probado en fixtures; no integrado al backend, journal, R-05 ni menú. No autoriza operaciones live.

## Objetivo

Definir qué puede demostrarse después de que el controlador oficial solicite `start`: que la unidad `xray.service` quedó activa, que la invocación posterior corresponde al PID/InvocationID observado, que el proceso ejecuta el binario/argv administrados y que el archivo runtime conserva el hash publicado antes y después de la observación.

## Implementación

Se añadió `scripts/xray_runtime_live_start_attestation.py` con `attest_start(...)` y siete pruebas en `tests/test_xray_runtime_live_start_attestation.py`.

La función exige:

- Publicación confirmada y timestamp con zona horaria.
- Hash runtime igual al hash publicado en dos lecturas independientes.
- `xray.service` cargado, `active/running`, resultado `success`, `ExecMainStatus=0` e identidad `xray:xray`.
- `ExecMainStartTimestamp` y `ActiveEnterTimestamp` posteriores a la publicación.
- Correlación exacta entre MainPID/InvocationID y el proceso atestado read-only.
- Binario `/usr/local/bin/xray` y hash SHA-256 del ejecutable.

La salida utiliza `evidence_level=launch_correlated_file_unchanged` y `configuration_evidence=launch_correlated_only`; mantiene expresamente `configuration_loaded=false`.

## Límite probatorio fundamental

La correlación temporal, el argv `-config /etc/xray/config.json`, el `xray run -test` previo y el hash estable del archivo son evidencia fuerte de que la invocación arrancó apuntando al archivo publicado. **No demuestran criptográficamente qué bytes quedaron cargados en memoria.** El proceso Xray no proporciona actualmente una atestación nativa del hash de configuración cargado. Una lectura del archivo después del arranque tampoco prueba por sí sola el contenido ya parseado por el proceso, especialmente frente a un administrador root externo que no comparte los locks del Manager.

Por tanto, este módulo no puede promover el journal a `configuration_attested` ni marcar `configuration_loaded=true`. No se debe renombrar esta evidencia como “configuración cargada”. Para obtener una prueba más fuerte se necesita una fuente de evidencia adicional diseñada y revisada (por ejemplo, instrumentación/contrato del proceso que exponga un identificador de generación derivado de los bytes efectivamente parseados); no se improvisará a partir de logs genéricos.

## Exclusiones

- No llama a `systemctl` ni al controlador `modules/xray_service.sh`.
- No publica, restaura ni modifica configuración.
- No se conecta a `LiveRuntimeBackend`, `LiveOperationStore`, R-05 ni menú.
- No se ejecutó en VPS Pruebas ni contra servicios reales.
- No modifica `modules/xray_service.sh`, `main` ni `Xray-Normativa/`.

## Validación

Pruebas focales: **7/7 PASS**. `compileall` y `git diff --check`: PASS.

## Próximo paso

Integrar de forma aislada el estado de solicitud/aceptación/observación al journal, manteniendo el estado terminal bloqueado mientras la evidencia sea sólo correlativa. Antes de habilitar el arranque desde el Manager, obtener revisión independiente H6-G3, resolver la fuente de evidencia de configuración cargada y contar con autorización live específica.
