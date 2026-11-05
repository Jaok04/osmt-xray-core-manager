# Decisión técnica R-05 — generation_id y orquestación fixture-only

**Fecha:** 2026-11-05
**Estado:** ALCANCE AUTORIZADO POR EL PROPIETARIO PARA IMPLEMENTACIÓN AISLADA
**Autorización:** respuesta afirmativa del propietario a la solicitud de implementar R-05 con fixtures, mocks, almacenes temporales y extensión compatible del journal.
**Base:** `docs/DISENO_R05_ORQUESTACION_SYSTEMD_SIMULADA_2026-11-04.md`, Etapa 5 §7 y Etapa 6 §2.
**Límites:** no autoriza R-06/live ni operaciones sobre systemd/Xray reales.

## 1. Compatibilidad del journal

1. Los journals históricos `schema_version: 1` conservan exactamente su estructura y semántica. El lector seguirá aceptándolos sin migración ni reescritura.
2. Las operaciones orquestadas R-05 usarán `schema_version: 2` y un objeto obligatorio `orchestration`. El resto del contrato R-03/R-04 permanece intacto.
3. `generation_id` será `generation-[0-9a-f]{32}`, generado con aleatoriedad criptográfica. Se crea una vez por operación, es inmutable y no se reutiliza. Antes de crear la operación se comprueba que no figure en ningún journal del almacén.
4. El identificador se conserva en el journal, cada petición del adaptador simulado y la evidencia de verificación. Una respuesta de otra generación nunca satisface la verificación actual.
5. No se migran automáticamente journals v1. R-03/R-04 continúan leyéndolos y procesándolos como hasta ahora; los estados R-05 quedan reservados a journals v2.

## 2. Semántica de estado del servicio

El adaptador fixture representa exclusivamente `xray.service` y admite `active`, `inactive`, `failed` y `unknown`.

- **active + confirmación aceptada:** publicar y solicitar un único restart simulado. Solo se considera aplicado si un status posterior informa `active`, el mismo `generation_id` y el SHA-256 exacto de la configuración publicada.
- **active + confirmación rechazada:** publicar sin restart y terminar en `published_pending_apply`. La configuración cargada por el servicio permanece en la generación/hash anterior.
- **inactive:** publicar sin start ni restart y terminar en `published_pending_start`. No se marca como aplicada.
- **failed / unknown:** fail-closed. No publicar ni iniciar/reiniciar. Conservar el journal de la operación en `recovery_required`, indicando que el estado inicial impide una aplicación segura. No inferir equivalencia ni recuperar automáticamente a `active`.

La confirmación se representa como un booleano explícito de entrada al orquestador; no se añade UI en R-05.

## 3. Fallos, rollback y recuperación

- Rechazo, excepción, timeout, pérdida de respuesta o verificación no coincidente después de un restart activo impiden declarar éxito.
- Tras una respuesta ambigua, consultar status antes de decidir. Solo generación + hash + estado coincidentes acreditan aplicación.
- Si la nueva generación no queda verificada, R-04 restaura atómicamente la configuración previa.
- Si el estado previo era `active`, el adaptador simula la restauración del estado cargado anterior y se verifica contra el hash/generación previos.
- Si el estado previo era `inactive`, no se emite start durante rollback; se conserva `inactive`.
- Si el estado previo era `failed` o `unknown`, nunca se intenta arrancar; se deja `recovery_required`.
- La restauración de configuración y la reconciliación del servicio se registran por separado. Si una falla o no puede verificarse, `recovery_required`.
- La recuperación repetida es idempotente. Una operación ya verificada/completada o con publicación pendiente no repite restart. Una solicitud ambigua se reconcilia por status y generación antes de cualquier acción.
- Si el servicio informa una generación ajena a la operación, no se sobrescribe ese estado externo. Se restaura el archivo si R-04 puede hacerlo y se deja `recovery_required` para intervención.

## 4. Estados R-05

Se conservan los estados base de R-03/R-04 y se añaden, solo para schema 2: `service_restart_requested`, `service_verified`, `published_pending_apply`, `published_pending_start` y `completed`. `rolled_back` y `recovery_required` reutilizan el significado existente, con evidencia R-05 adicional. Los cambios de fase se guardan en `orchestration.phase`; la publicación R-04 sigue siendo la autoridad sobre el hash y el destino publicado.

## 5. Adaptador y aislamiento

El adaptador ofrece únicamente `status`, `restart` y restauración simulada del estado previo. Su almacenamiento y bitácora están bajo un fixture R-05 marcado, root-only, sin symlinks. Los fallos se inyectan mediante perfiles deterministas de prueba. El adaptador no usa subprocess, shell, PATH, systemctl, service, journalctl, D-Bus ni APIs del sistema.

Las operaciones públicas `status`, `restart`, `restore` y `audit_events` adquieren un lock exclusivo interproceso (`fcntl.flock`) sobre `adapter.lock`, dentro del directorio root-only del fixture. El lock cubre la transacción completa: lectura, comparación, modificación, escritura atómica y append de auditoría. Así, el compare-and-swap de `restart` y `restore` no depende solo de `os.replace`: la lectura y la comprobación de precondiciones quedan serializadas frente a otros procesos del adaptador. El archivo de lock se valida con `O_NOFOLLOW`, tipo regular, propietario root:root, modo 0600, un único hardlink e identidad de inode estable tras adquirir el lock. La restauración exige que la generación cargada siga siendo la de la operación.

R-05 reutiliza R-01–R-04; no duplica validación, staging TLS, snapshot ni publicación. Las llamadas al binario Xray para `run -test` siguen confinadas al binario de fixture ya previsto por R-02/R-04.

## 6. Criterios de aceptación técnica

Implementar y probar éxito active; confirmación rechazada; inactive; failed/unknown; rechazo de restart; estado posterior incorrecto; timeout antes/después de transición; pérdida de respuesta; caída entre publicación/restart/verificación/rollback; fallos de rollback de configuración/servicio; locks; TOCTOU; identidad/hash/generación stale; aislamiento; ausencia de invocaciones reales; compare-and-swap interproceso de restart/restore; serialización de auditoría; rechazo de symlink en lock; compatibilidad v1/v2 y recuperación idempotente.

Este incremento no cierra Etapa 5, no integra un adaptador real, no demuestra systemd real ni conectividad externa y no autoriza la prueba live del primer servidor.
