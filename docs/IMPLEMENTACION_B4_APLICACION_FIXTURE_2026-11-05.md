# Implementación B4 — aplicación fixture y registro activo de perfil

**Fecha:** 2026-11-05
**Rama:** `design/user-identity-association-v1`
**Estado:** IMPLEMENTACIÓN AISLADA; auditoría fixture-only. No autoriza despliegue live.

## 1. Objetivo

Conectar la publicación R-01–R-04 y la orquestación fixture R-05 con el registro persistente de perfil activo exigido por Etapa 5 §7. El registro representa únicamente una configuración cuya generación y hash han sido observados en estado `active` por el adaptador simulado. No es evidencia de que systemd o Xray reales estén funcionando.

## 2. Archivos

- `scripts/xray_runtime_active_profile.py` — almacén fixture-only del registro activo.
- `scripts/xray_runtime_service_adapter.py` — añade la acción simulada `start` para el estado inicial `inactive`, con compare-and-swap y auditoría.
- `scripts/xray_runtime_orchestrator.py` — integra el registro con la verificación posterior a restart, la recuperación y el inicio explícito de operaciones `published_pending_start`.
- `scripts/xray_runtime_journal.py` — extiende el contrato schema 2 para la petición explícita `start` y el estado durable `service_start_requested`.
- `tests/test_xray_runtime_orchestrator.py` — cobertura B4 adicional.

## 3. Registro persistente

El almacén requiere un directorio fixture dedicado con marcador `.xray-manager-b4-active-fixture`. Aplica:
- directorio root:root 0700;
- archivos root:root 0600 y enlaces simbólicos rechazados;
- JSON estricto, esquema exacto y límites de tamaño;
- lock interproceso `flock`, apertura `O_NOFOLLOW` y comprobación de identidad del inode;
- escritura temporal, fsync, reemplazo atómico y fsync del directorio;
- operación idempotente para la misma identidad de perfil/revisión/generación/hash.

El registro contiene schema_version, profile_id, revision, validation_id, generation_id, config_sha256, operation_id, applied_at, service_unit, service_state y config_target. No almacena UUID, claves privadas, credenciales ni URI de cliente.

## 4. Contrato de aplicación

### Servicio inicialmente active

1. R-01 preflight comprueba perfil/revisión exacta, informe validado y binario.
2. R-02 staging prepara configuración y leases temporales.
3. R-03 guarda snapshot/journal y R-04 publica atómicamente.
4. R-05 exige confirmación explícita antes de restart.
5. El adaptador fixture compara estado/generación/hash previos (CAS), simula restart y se consulta de nuevo.
6. Solo con `active`, generation_id esperado y SHA-256 esperado se marca completed y se actualiza el registro activo.

### Servicio inicialmente inactive

1. La publicación termina en `published_pending_start`; no inicia automáticamente.
2. `start_pending_operation(..., confirm_start=True)` exige una segunda decisión explícita.
3. El journal registra `service_start_requested` y acción `start`.
4. El adaptador fixture exige que el estado siga inactive y que generación/hash previos no hayan cambiado.
5. Solo tras observar `active` con la generación y hash nuevos se marca completed y se actualiza el registro.

Si la confirmación no se entrega, no hay acción de servicio. Si start/restart falla antes de transición, se intenta rollback de configuración. Si el estado posterior es ambiguo o no coincide, se falla cerrado y se solicita recuperación; no se detiene ni se inicia a ciegas un servicio.

## 5. Registro y recuperación

- `published_pending_apply` y `published_pending_start` no modifican el registro anterior.
- Rollback correcto conserva el registro previo.
- Estados iniciales `failed` o `unknown` bloquean la publicación.
- Si el proceso cae tras una transición, recovery consulta el adaptador fixture; si la generación/hash nueva están activos, finaliza el journal y registra el perfil sin repetir start/restart.
- Si el journal ya está completed pero el registro falta, recovery puede reconciliarlo tras verificar nuevamente generación/hash.
- Escrituras repetidas para la misma operación son idempotentes.

## 6. Alcance y exclusiones

Todo lo anterior es una implementación fixture-only. No existe todavía un adaptador systemd real conectado a este flujo ni integración de menú que invoque este puente en producción. El almacén B4 de pruebas requiere marcador fixture y no debe apuntarse a `/var/lib/xray-manager/profiles` en producción.

No se ejecutaron `systemctl`, `journalctl`, ACME/Certbot, instalación/actualización de paquetes, lectura de claves maestras reales, ni operaciones en `/etc/xray`, certificados persistentes, DNS, firewall, puertos o red. No se modificaron `Xray-Normativa/` ni `main`. No hubo commit ni push.

## 7. Trazabilidad normativa

- Etapa 5 §7: el registro activo se actualiza después de verificar ejecución real; esta entrega implementa y prueba el contrato únicamente con evidencia fixture.
- Etapa 6 §§2, 5 y 6: distingue publicación, aplicación, estado y recuperación; la ejecución real sigue pendiente.
- Plan MVP B4: preserva confirmación para restart, no inicia automáticamente desde inactive, bloquea failed/unknown y conserva recuperación.

**Resultado:** base B4 fixture-only implementada; no equivale a B4 live aceptada ni al primer servidor funcional.
