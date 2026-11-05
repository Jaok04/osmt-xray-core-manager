# Auditoría R-02 — staging integrado de perfil y leases TLS

**Fecha:** 2026-11-04
**Resultado:** PASS técnico en entorno aislado; pendiente de aceptación formal y publicación.
**Alcance auditado:** scripts/xray_runtime_staging.py y tests/test_xray_runtime_staging.py.

## 1. Dictamen

R-02 cumple el objetivo de ensamblar una revisión exacta de perfil con sus leases TLS temporales y validar los bytes finales bajo una identidad de servicio no privilegiada simulada. No publica configuración runtime ni ejecuta acciones de servicio.

El mapa inbound_tag → connection_id fue aprobado por el propietario en esta conversación y se aplica de forma fail-closed. El certificado se obtiene del almacén central; no se permite que el mapa o el perfil inyecten PEM/rutas privadas.

## 2. Controles auditados

| Control | Resultado | Evidencia |
|---|---|---|
| Identidad exacta profile_id + revision | PASS | Preflight R-01 antes y después del staging; hash exacto |
| Informe de validación | PASS | Se conserva validation_id del informe persistido |
| Fixture aislado y rutas | PASS | marcador obligatorio; todos los datos dentro del fixture, sin defaults live |
| Mapa estricto/permisos | PASS | JSON estricto, root:root 0600, tamaño limitado |
| Asociación inbound TLS exacta | PASS | Cobertura total, sin tags/conexiones duplicados ni extras |
| Fuente de certificado | PASS | security_options central y certificate_resolver |
| Lease TLS | PASS | Resolutor real con certificado/clave sintéticos |
| Permisos del staging | PASS | staging_root root:root 0711, directorio de operación 0750 y archivos 0640 para grupo simulado |
| Identidad de ejecución | PASS | Xray real 26.10.31 ejecutado como UID/GID 65534:65534 |
| TOCTOU de perfil/informe | PASS | Segundo preflight y segunda lectura antes de validar bytes finales |
| Validación final | PASS | Xray run -test aceptó configuración con lease |
| Cleanup por fallo | PASS | Se verifica cleanup tras rechazo simulado |
| Ausencia de publicación | PASS | El artefacto declara runtime_published=false |
| Ausencia de acción systemd | PASS | No hay llamadas systemctl ni cambios de unidad |
| Secretos en manifiesto/log | PASS | Solo IDs, hashes, rutas de lease y metadatos; sin PEM/clave |

## 3. Pruebas focales

tests/test_xray_runtime_staging.py: **11/11 PASS**.

- test_stages_profile_and_records_exact_binding_and_validation
- test_duplicate_or_unknown_inbound_binding_fails_before_lease
- test_duplicate_connection_and_duplicate_tag_are_rejected
- test_cleanup_is_attempted_if_native_validation_fails
- test_mapping_requires_root_private_regular_file
- test_fixture_root_marker_is_mandatory
- test_all_data_paths_must_remain_inside_fixture_root
- test_profile_or_validation_change_during_lease_resolution_aborts
- test_staging_root_symlink_ancestor_is_rejected
- test_service_identity_can_read_staged_config_and_tls_lease
- test_actual_central_resolver_lease_is_staged_and_readable_by_service

La última prueba integra el catálogo y almacén central de certificados, certificate_resolver.prepare, lease temporal real y cleanup; usa un certificado autofirmado y clave sintéticos. También entrega el artefacto staged a R-03, que valida sus marcadores/rutas y crea el snapshot/journal temporal. Cuando está disponible /usr/local/bin/xray, utiliza ese binario real; en esta VPS se utilizó Xray-core 26.10.31.

## 4. Regresión

- Python: 140/140 PASS.
- Shell: 58/58 PASS.
- py_compile: PASS.
- bash -n global: PASS.
- install.sh --check: PASS.
- ShellCheck severidad error sobre pruebas shell: PASS.
- git diff --check: PASS.

## 5. Hallazgos y limitaciones

No se identificó un defecto bloqueante en el alcance R-02 probado.

Limitaciones conocidas:
1. El mapa de asociaciones es un archivo explícito externo a la revisión del perfil; su hash y contenido se fijan en el manifiesto staged. La gestión persistente/UI no está implementada.
2. UID/GID 65534:65534 simula una identidad no privilegiada. No demuestra los permisos/identidad reales de xray.service.
3. La ejecución xray run -test valida la configuración staged, no inicia el servicio ni demuestra conectividad cliente/WAN.
4. Los leases exitosos permanecen activos para el ciclo R-03; el snapshot/journal R-03 ya está implementado y auditado localmente, pero R-02 por sí sola no define la política de publicación/cleanup posterior.
5. No se utilizó clave maestra ni almacenes reales y no se tocaron datos operativos.

## 6. Protecciones

No se modificaron main, Xray-Normativa/, /etc/xray/config.json, systemd real, runtime, certificados desplegados, firewall, puertos, red, dependencias, VPS de pruebas ni la clave maestra real. No se ejecutó R-06/live ni NetMod.

## 7. Estado

R-02: IMPLEMENTADA / VERIFICADA EN FIXTURES Y CON XRAY REAL SOBRE LEASE SINTÉTICO / AUDITADA LOCALMENTE. Pendiente de aceptación formal y publicación en la rama autorizada.

R-03 está implementada/auditada localmente; R-04 y R-05 pendientes. R-06/live NO AUTORIZADA. Etapas 2, 3 y 5 permanecen ABIERTAS.
