# B4-MIN — diseño mínimo de aplicación runtime y evidencia de configuración

**Fecha:** 2026-11-07
**Rama:** `design/user-identity-association-v1`
**Estado:** DISEÑO PRELIMINAR — requiere aprobación antes de implementar
**Alcance:** fixtures/mocks/temporales en VPS desarrollo. No autoriza R-06/live ni cambios en VPS Pruebas.

## 1. Alcance mínimo

Reutilizar R-01 (preflight perfil/revisión), R-02 (staging y leases TLS), R-03 (journal/snapshot), R-04 (publicación atómica fixture), R-05 (orquestación fixture) y `modules/xray_service.sh` como controlador único de systemd. No duplicar esos componentes ni convertir el journal fixture en dual live mediante una bandera. El backend live permanece aislado.

## 2. Brecha demostrada

1. R-04 publica atómicamente en el destino fixture y verifica hash, tamaño, propietario y modo; no publica en `/etc/xray` real.
2. R-05 coordina publicación y transiciones simuladas; sus resultados fixture no son evidencia live.
3. `xray_runtime_live_backend.py` exige evidencia de publicación live y CAS del hash runtime, pero devuelve `accepted_not_verified`; no verifica postcondición y `restore` no está implementado.
4. `xray_runtime_systemd_adapter.py` observa hash del archivo runtime y deja `loaded_generation_id` y `loaded_config_sha256` en null.
5. `xray_runtime_process_attestation.py` correlaciona MainPID, InvocationID, ejecutable, argv y UID/GID, pero fija `configuration_loaded=false` y `configuration_evidence=not_attested`.
6. La unidad actual usa `ExecStartPre=/usr/local/bin/xray run -test -config /etc/xray/config.json` y `ExecStart=/usr/local/bin/xray run -config /etc/xray/config.json`.

Conclusión: hash actual del archivo + systemd active + identidad del proceso prueban el destino y la existencia de un proceso Xray esperado, pero no prueban qué bytes fueron leídos por ese proceso. No se debe cambiar `configuration_loaded` a true ni declarar `completed` con esas observaciones.

## 3. Contrato funcional

- `validated`: perfil/revisión exactos, informe íntegro PASS/PASS_WITH_WARNINGS y validación nativa de los bytes finales.
- `snapshot_saved`: copia exacta anterior y metadatos verificables persistidos.
- `config_published`: destino coincide con SHA-256 de la generación publicada.
- `service_action_accepted`: controlador confirmó aceptación; no implica éxito.
- `service_active`: systemd y proceso Xray esperado están activos y correlacionados.
- `configuration_attested`: evidencia independiente liga los bytes exactos de configuración a la invocación/MainPID.
- `completed`: sólo después de todos los controles, incluida `configuration_attested`.

Si no puede probarse la carga, no se declara `completed` ni se actualiza el perfil activo. Se conserva un estado no terminal o `recovery_required`.

## 4. Mecanismo recomendado para cerrar la brecha

Evaluar un lanzador root-owned que sustituya el `ExecStart` directo sólo después de aprobación:

1. Abrir `/etc/xray/config.json` con no-follow y verificar tipo, propietario, grupo, modo, tamaño y SHA-256.
2. Copiar los bytes a un Linux `memfd` creado con `MFD_ALLOW_SEALING`.
3. Aplicar y verificar `F_SEAL_WRITE | F_SEAL_GROW | F_SEAL_SHRINK | F_SEAL_SEAL`; reposicionar el descriptor al inicio.
4. Mantener el descriptor abierto a través de `execve` y ejecutar Xray con `run -config /proc/self/fd/N`. El descriptor debe ser heredable y accesible bajo UID/GID xray:xray.
5. Antes del exec, escribir evidencia root-only atómica con schema, SHA-256 de los bytes sellados, tamaño, PID que será preservado por exec, `INVOCATION_ID`, timestamp y versión/hash del lanzador. Nunca guardar contenido, secretos, UUID ni PEM.
6. Tras el exec, el Manager correlaciona la evidencia con el mismo InvocationID, MainPID, starttime, ejecutable y estado active/running/result=success. Verifica que el hash del memfd coincide con el hash publicado por la operación.
7. Sólo entonces registra que los bytes inmutables fueron entregados al proceso que systemd mantiene activo. No describirlo como introspección arbitraria de memoria.

La evidencia previa no basta por sí sola: sin proceso activo correlacionado, con PID/InvocationID discordante o hash distinto, se rechaza.

### Condiciones que deben probarse

- La versión Xray fijada acepta `/proc/self/fd/N` en `-config` y lee correctamente el descriptor heredado.
- El descriptor sobrevive a `execve`; comprobar Go/Xray, permisos y acceso bajo xray:xray.
- memfd sellado funciona con `ProtectSystem=strict` y `NoNewPrivileges` sin relajar controles.
- El lanzador no acepta rutas, comandos ni opciones del usuario.
- Evidencia resistente a symlinks, hardlinks, sustitución, permisos laxos, escrituras parciales y replay de InvocationID.
- Fallo de escritura/fsync de evidencia aborta antes de exec.
- La correlación incluye InvocationID, no sólo PID reutilizable.
- Los leases TLS permanecen accesibles mientras Xray los use; no se limpian prematuramente.
- No alterar la unidad real hasta aprobación específica y pruebas aisladas satisfactorias.

### Alternativas insuficientes

- Hash de archivo antes/después de restart: prueba el archivo, no los bytes consumidos.
- `systemctl is-active`, PID y argv: prueban unidad/proceso, no contenido cargado.
- `ExecStartPre -test`: valida parseo, no demuestra que el proceso principal leyó la misma generación.
- Listener 443 o handshake TLS: no identifica por sí solo la generación exacta.
- Wrapper que calcula hash y luego ejecuta Xray con ruta mutable: mantiene una ventana TOCTOU.

## 5. Transacción mínima B4

1. Mantener locks lifecycle → application durante toda la operación; no reacquirir internamente.
2. Observar systemd, proceso, hash runtime y unidad; fallar ante estado failed/unknown/transitorio, drift o unidad no administrada.
3. Ejecutar preflight R-01 y staging R-02 de perfil/revisión exactos; revalidar hash, manifiesto, leases y binario.
4. Guardar snapshot exacto y journal durable R-03. Si no existía configuración previa, no crear placeholder.
5. Publicar atómicamente con R-04 adaptado sólo tras diseñar/auditar una implementación live separada; comparar destino inmediatamente antes del rename.
6. Si estaba active, pedir confirmación explícita y restart. Si estaba inactive, dejar `published_pending_start` y solicitar start por acción separada confirmada; no arrancar implícitamente durante publicación. failed/unknown bloquean.
7. Delegar start/restart exclusivamente a `modules/xray_service.sh` con descriptor lifecycle heredado; Python no llama systemctl.
8. Verificar systemd, proceso, InvocationID, hash publicado y evidencia del lanzador.
9. Commit del perfil activo sólo tras atestación completa.
10. En fallo, rollback condicionado por CAS. Restaurar sólo si el destino sigue siendo el hash de la operación. Si antes active, recuperar servicio y verificar nueva InvocationID con hash anterior; si antes inactive, restaurar sin iniciar. Sin snapshot previo, drift o rollback ambiguo: `recovery_required`, preservar evidencia y bloquear nueva aplicación.

## 6. Fuera del MVP

Renovación automática Certbot/timer/deploy hook; restaurador general shared snapshot; nuevos protocolos; cambios automáticos firewall/puertos/DNS; automatización multi-host; aplicación desde configuraciones independientes; hot reload; enable/disable como efecto lateral.

## 7. Matriz mínima de pruebas

| ID | Caso | Resultado |
|---|---|---|
| B4-01 | memfd contiene bytes exactos y hash coincide | PASS |
| B4-02 | write/truncate/grow del memfd sellado | kernel lo rechaza |
| B4-03 | Xray fixture lee `/proc/self/fd/N` tras exec | PASS |
| B4-04 | evidencia con PID/InvocationID stale o discordante | fail-closed |
| B4-05 | proceso activo correlacionado con hash publicado | attested |
| B4-06 | exec falla después de escribir evidencia | no completed |
| B4-07 | evidencia no puede escribirse/fsync | no ejecuta Xray |
| B4-08 | hash esperado no coincide con archivo | aborta |
| B4-09 | drift externo posterior a publicación | no sobrescribe; recovery_required |
| B4-10 | systemd active pero evidencia ausente | no completed |
| B4-11 | PID coincide pero InvocationID cambia | no completed |
| B4-12 | rollback con servicio previo active | hash anterior + nueva invocación activa |
| B4-13 | rollback con servicio previo inactive | restaura archivo sin iniciar |
| B4-14 | no había config previa y falla aplicación | recovery_required sin placeholder |
| B4-15 | snapshot corrupto/ausente | bloquea rollback |
| B4-16 | timeout/respuesta perdida | reobserva; nunca repite a ciegas |
| B4-17 | aplicación concurrente | bloqueo por locks |
| B4-18 | lease TLS inválido/cleanup prematuro | aborta o recovery_required |
| B4-19 | unidad alterada/drop-in/NeedDaemonReload | fail-closed |
| B4-20 | errores/logs | sin UUID completos, PEM, claves ni config |

## 8. Decisiones aprobadas por el propietario — 2026-11-07

1. **Aprobado:** lanzador con memfd sellado y descriptor heredado como mecanismo de evidencia de bytes entregados al proceso, sujeto a pruebas B4.
2. **Aprobado:** si el servicio está inactive, publicar `published_pending_start`; el inicio requiere segunda confirmación explícita.
3. **Aprobado como diseño:** conservar `xray.service` y evaluar un lanzador root-owned con evidencia root-only en ruta fija; cualquier cambio real de unidad requiere autorización de despliegue separada.

Estas aprobaciones son sólo de diseño. No habilitan R-06/live ni autorizan cambios reales en unidad, systemd, `/etc/xray` o VPS Pruebas. La primera implementación fixture se registra en `docs/IMPLEMENTACION_FIXTURE_B4_MEMFD_2026-11-07.md`; cubre el descriptor sellado, herencia a través de exec y verificación fixture, no el binario Xray real.

## 9. Criterios de salida

Contrato aprobado y trazado a Etapas 5/6; implementación separada fixture/live; matriz B4 automatizada; auditoría focal documentada; ninguna operación live hasta autorización específica; MVP end-to-end sólo cuando servicio real, atestación de configuración y prueba externa bidireccional VLESS-WS-TLS estén demostrados.
