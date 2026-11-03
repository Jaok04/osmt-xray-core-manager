# Integración VMess con certificados TLS centralizados — avance parcial

**Fecha:** 2026-11-03  
**Bloque:** Etapa 2 — Bloque 3, integración VMess  
**Estado:** IMPLEMENTACIÓN PARCIAL; no aceptada ni desplegada.

## Alcance realizado

1. `scripts/vmess_config_store.py` acepta para nuevas revisiones TLS únicamente `security_options: {certificate_id}` y exige que el certificado exista, esté activo y tenga tipo `managed` o `reference` en el catálogo central. Rechaza secretos TLS por conexión, rutas TLS libres y certificados inexistentes/inactivos.
2. La persistencia TLS central no crea `vmess_secret_ref`, no crea un blob TLS por conexión y no necesita descifrar una clave privada al leer la configuración.
3. REALITY conserva el secreto cifrado individual y su flujo anterior.
4. La validación de la revisión previa permite leer TLS histórico `{certificate_file, secret_ref}` para conservar compatibilidad. No se migran ni eliminan revisiones históricas. Las nuevas revisiones TLS deben usar `certificate_id`.
5. `scripts/vmess_prepare_config.py` prepara el nuevo contrato TLS sin leer ni escribir una clave privada por conexión; REALITY sigue requiriendo su salida secreta.
6. `scripts/vless_backup.py` permite validar durante la restauración los registros VMess históricos TLS preservados.
7. `modules/vmess_assistant.sh` recibió una adaptación inicial para pedir `certificate_id`, guardar con el catálogo central y solicitar un lease al resolutor para la validación Xray. La adaptación del asistente es preliminar: no hay aún prueba integral del flujo interactivo TLS y no debe considerarse finalizada.
8. `tests/vmess_persistence_hardening.sh` incorpora casos centrales TLS, rechazo de IDs inexistentes/inactivos y rutas/secretos libres, además de lectura de TLS histórico.

## Pruebas ejecutadas

- `tests/vmess_persistence_hardening.sh`: PASS; central TLS sin secreto por conexión, negativos de certificado y compatibilidad histórica; conserva pruebas de integridad, concurrencia, atomicidad, REALITY y auditoría.
- `tests/vless_restore_preserves_vmess.sh`: PASS.
- `tests/certificate_store.sh`: PASS.
- `tests/certificate_resolver.sh`: PASS.
- `tests/vmess_model.sh`: PASS.
- `tests/vmess_creation_flow.sh`: PASS.
- `tests/vmess_vless_backup_isolation.sh`: PASS.
- `tests/vmess_assistant.sh`: PASS; prueba selección/persistencia del ID central y el fallo cerrado del resolutor cuando no puede verificar la identidad de Xray. No constituye prueba de lease real con Xray.
- `bash -n` en módulos VMess modificados y `py_compile` de `vmess_config_store.py`, `vmess_prepare_config.py` y `vless_backup.py`: PASS.
- ShellCheck con severidad warning en los módulos/pruebas modificados: PASS. `git diff --check`: PASS.

Regresión completa `tests/*.sh`: 42/42 PASS después de estos cambios, incluida la prueba del preparador TLS centralizado.

## Pendiente antes de completar Bloque 3

- Adaptar y endurecer `modules/vmess_xray_26_10_31.sh` para que el generador TLS sólo reciba rutas temporales emitidas por el resolutor y no permita rutas arbitrarias como entrada del flujo normal.
- Completar la adaptación del asistente y cubrir mediante pruebas automatizadas los caminos de creación, lectura, edición/recuperación, lease, validación Xray y limpieza ante éxito y fallo.
- Revisar todos los caminos de backup/restore VMess/VLESS afectados y la compatibilidad de configuraciones históricas.
- Ejecutar regresión integral, ShellCheck/shfmt aplicables y revisión de seguridad del diff.
- Actualizar la documentación final del Bloque 3 y la matriz de trazabilidad al completar las pruebas.

## Límites y seguridad

- El resolutor necesita la identidad real de la unidad systemd Xray. La VPS de desarrollo no tiene `xray.service` ni usuario/grupo de servicio; la CLI real falla cerrada. No se simula acceso real de Xray mediante UID/GID sintético.
- Por tanto, no se ha demostrado que el proceso Xray real pueda leer los leases ni que el flujo interactivo TLS completo funcione en runtime.
- No se aplicaron borradores al runtime, no se instalaron servicios, no se tocaron firewall/puertos y no se modificó la VPS `Vps de Pruebas`.
- No se importaron certificados reales ni se migraron secretos históricos.
- REALITY permanece separado.
- `Xray-Normativa/` no se modificó.

## Clasificación

| Estado | Resultado |
|---|---|
| IMPLEMENTADO | Parcial: contrato de persistencia y preparación TLS central; asistente en adaptación inicial |
| VERIFICADO | Pruebas focales indicadas arriba |
| PUBLICADO | Se registra en la publicación intermedia de la rama autorizada |
| SINCRONIZADO | Pendiente de confirmación posterior al push |
| ACEPTADO | No; Bloque 3 y Etapa 2 continúan abiertos |
