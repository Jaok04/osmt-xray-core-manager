# Implementación del puente menú → runtime live: primer start

**Fecha:** 2026-11-08
**Rama:** `design/user-identity-association-v1`
**Alcance:** integración de código y pruebas en VPS de desarrollo; no es un despliegue live.

## Resultado

Se implementó `scripts/xray_runtime_live_operation_evidence.py` para verificar la cadena live antes de delegar una acción: journal live en `service_action_requested`, vínculo `operation_id`/`generation_id`/confirmación, publicación cuyo hash coincide con el staged, informe persistido de validación de perfil/revisión/binario con todos los checks obligatorios en PASS y bytes actuales de `/etc/xray/config.json` con propietario/permisos esperados y hash exacto.

El puente también valida el objetivo concreto antes de publicar: exactamente un mapping TLS y un inbound VLESS en `0.0.0.0:443`, WebSocket + TLS, clientes presentes, paths de certificado/clave limitados al lease de esa operación, conexión central coincidente y SAN del certificado cubriendo `pruebas.tvrc.me` y el SNI configurado. El Host WebSocket se conserva independiente del SNI. Se reforzó `certificate_resolver` para comparar SAN, sujeto, emisor y vigencia del PEM real contra los metadatos del catálogo; no confía sólo en el SAN declarado por el catálogo.

Se implementó `scripts/xray_runtime_live_apply_bridge.py`, que conecta en orden:

1. Observación read-only de `xray.service`.
2. Gate estricto de primer despliegue: unidad cargada e inactive, sin MainPID/InvocationID y sin configuración runtime previa.
3. `stage_live(profile_id, revision)`.
4. `publish_live(staging_dir)`.
5. Adquisición del lifecycle lock compartido.
6. `LiveRuntimeBackend` con el nuevo lector de evidencia.
7. `start_published_operation(...)`, con generación explícita, confirmación, delegación única a `modules/xray_service.sh` y observación correlativa posterior.

La opción `[12]` de Gestión de perfiles invoca el puente tras seleccionar una revisión validada y responder afirmativamente a dos confirmaciones. La CLI exige además `--confirm-live`. La opción fixture `[11]` se conserva separada.

## Restricciones deliberadas del primer puente

- Sólo primer despliegue, desde `xray.service` cargado e inactive.
- Rechaza cualquier `/etc/xray/config.json` preexistente porque `LiveRuntimeBackend.restore()` sigue fallando cerrado; no sobrescribe una configuración existente.
- No ejecuta restart ni stop.
- Ante resultado ambiguo de start, conserva el `operation_id` para inspección y exige reconciliación; no reintenta automáticamente.
- Mantiene `configuration_loaded=false` y `completed=false`. La evidencia demuestra publicación y correlación de arranque/proceso, no los bytes parseados internamente por Xray.
- No cambia la unidad directa `User=xray`, `Group=xray`, ni integra el prototipo memfd fixture en systemd.

## Pruebas ejecutadas en desarrollo

- Nuevas pruebas de evidencia live: **11/11 PASS**.
- Nuevas pruebas del puente: **7/7 PASS**.
- Nuevas pruebas de objetivo/limpieza staging: **10/10 PASS**.
- Suite Python completa: **570/570 PASS**.
- Suites Bash: **62/62 PASS**.
- `bash -n` global: PASS.
- ShellCheck global `-S error`: PASS.
- `bash install.sh --check`: PASS, sin modificar el sistema.
- `git diff --check`: PASS tras corregir un espacio final detectado.
- Prueba de menú: ruta live explícita, cancelación sin invocar el puente y doble confirmación antes de invocarlo.
- Suite `certificate_resolver.sh`: PASS incluyendo rechazo de SAN falsificado en catálogo frente al PEM real.

## Límites y estado live

Esta implementación no se ejecutó contra una unidad/servicio productivo. Las pruebas del nuevo puente usan dependencias simuladas para verificar el orden y los gates; las piezas live preexistentes mantienen sus propias suites fixture. No se ejecutó `stage_live`, `publish_live`, `systemctl start`, ACME ni Xray real a través de este nuevo puente.

No se tocó VPS Pruebas, `/etc/xray`, `/var/lib/xray-manager`, `xray.service`, cuentas/grupos, certificados, DNS, firewall o puertos. No se modificó `main` ni `Xray-Normativa/`.

Antes de una prueba real, VPS Pruebas debe tener instalado el Manager, Xray, la identidad `xray:xray` y la unidad administrada detenida/deshabilitada según el instalador; deben existir perfil y asociaciones centrales válidas, certificado TLS central vigente y conectividad de DNS/443. El puente rechazará el host si falta la unidad, si el servicio no está inactive o si ya existe configuración.

La revisión independiente H6-G3 no se declara realizada. La verificación de esta implementación se hizo en esta misma sesión, conforme a la instrucción del propietario de validar aquí; los resultados internos no se etiquetan como auditoría independiente.
