# Auditoría U-01 — Integración Usuarios V2 con VLESS

**Fecha:** 2026-11-04
**Base Git:** `ca6d76895821310a3072d9de47268f925ecea7ba`
**Rama:** `design/user-identity-association-v1`
**Entorno:** VPS de desarrollo `Implementación-Xray`, `/opt/xray-manager`; pruebas aisladas y datos sintéticos.
**Dictamen:** PASS para el alcance U-01; IMPLEMENTADA, VERIFICADA, PUBLICADA y SINCRONIZADA. Aceptación formal del propietario pendiente; no cierra una etapa.
**Commit:** `1c2cd12f15be75d9f3a080ce028951724618c492` (`feat(vless): integrate V2 users into candidate generation`), push fast-forward desde `ca6d76895821310a3072d9de47268f925ecea7ba`.

## 1. Alcance auditado

Se auditó el diseño U-01 aprobado: fuente única Usuarios V2, exportación de candidatos independiente del estado runtime, integración de creación/recuperación VLESS, UUID automático/manual y validación con pruebas aisladas. No se auditó migración legacy, ACME/Cloudflare, publicación runtime ni conectividad externa porque están fuera del alcance autorizado.

## 2. Matriz de criterios

| ID | Criterio | Evidencia | Resultado |
|---|---|---|---|
| U01-01 | Usuarios V2 es la única fuente del asistente | `connections_vless_assistant_build_model`; prueba con `modules/users.sh` legacy también cargado | PASS |
| U01-02 | Active/draft/not_applied se incluye en candidato | `tests/users_v2_vless_candidate.sh`; `tests/xray_vless_integration.sh` | PASS |
| U01-03 | Suspended y expired se excluyen | `tests/users_v2_vless_candidate.sh` | PASS |
| U01-04 | Active con vencimiento pasado se excluye antes del barrido | `tests/users_v2_vless_candidate.sh` | PASS |
| U01-05 | Otras conexiones y protocolos no se exportan | `tests/users_v2_vless_candidate.sh` | PASS |
| U01-06 | Alias repetidos no colisionan; `email` deriva de asociación | exportación `{id,email}` y prueba candidata | PASS |
| U01-07 | Unicidad global de UUID VLESS | `users_association_create`, `tests/users_v2.sh`, `tests/users_v2_menu.sh` | PASS |
| U01-08 | UUID automático predeterminado y entrada manual oculta | `tests/users_v2_menu.sh` | PASS |
| U01-09 | UUID se normaliza y compara sin distinguir mayúsculas | fixture UUID uppercase en `tests/users_v2_vless_candidate.sh` | PASS |
| U01-10 | Vista runtime conserva el filtro applied/applied | `tests/users_v2_vless_candidate.sh` | PASS |
| U01-11 | Fallo previo de provisioning/runtime permite regenerar candidato | `tests/users_v2_vless_candidate.sh` | PASS |
| U01-12 | Almacén ausente no se inicializa accidentalmente | `tests/users_v2_vless_candidate.sh`, `tests/vless_assistant.sh` | PASS |
| U01-13 | JSON, referencias o vencimiento inválidos fallan cerrado | `tests/users_v2_vless_candidate.sh` | PASS |
| U01-14 | Snapshot está protegido por lock compartido compatible con escritores exclusivos | inspección de `flock -s` en exportador y `flock -x` en operaciones V2 | PASS (revisión de código) |
| U01-15 | Creación y recuperación del asistente usan V2 | `tests/vless_assistant.sh`, `tests/vless_tls_lease_assistant.sh` | PASS |
| U01-16 | El adaptador Xray recibe UUID y email de asociación válidos | `tests/xray_vless_integration.sh`, Xray real 26.10.31 | PASS |
| U01-17 | No se activa runtime ni se modifican servicios | pruebas de borrador, inspección de alcance y código | PASS |
| U01-18 | Migración legacy permanece separada | no se invocó `users_v2_migrate_legacy` ni `users_v2_cutover.py` | PASS |

## 3. Evidencia de ejecución

### Pruebas focales

- `tests/users_v2.sh`: PASS.
- `tests/users_v2_menu.sh`: PASS.
- `tests/users_v2_vless_candidate.sh`: PASS.
- `tests/vless_assistant.sh`: PASS.
- `tests/vless_tls_lease_assistant.sh`: PASS.
- `tests/xray_vless_integration.sh`: PASS.

`tests/xray_vless_integration.sh` ejecutó Xray-core 26.10.31, build `a4a3dff` (`go1.27.3 linux/amd64`). Primero construyó una configuración VLESS-WS mediante el exportador V2 y el modelo neutral; la configuración con asociación sintética `active/draft/not_applied` fue aceptada por `xray run -test`. Luego se validaron las nueve modalidades VLESS ya cubiertas por esa prueba: WS, RAW/TCP TLS, WS-TLS, REALITY, gRPC TLS/REALITY, XHTTP sin TLS/TLS/REALITY.

Las advertencias de obsolescencia de WebSocket/gRPC y de REALITY en puerto de prueba son mensajes nativos de Xray; no alteran el resultado ni amplían el alcance. Se conservaron las decisiones de compatibilidad aprobadas.

### Regresión completa

- Scripts shell: **58/58 PASS**, sin fallos.
- `bash -n` sobre `bin/`, `config/`, `lib/`, `modules/`, `scripts/` y `tests/`: PASS.
- `python3 -m py_compile scripts/*.py`: PASS.
- `./install.sh --check`: PASS; no modificó el sistema.
- ShellCheck `-S error` sobre los archivos Bash modificados: PASS.
- `shfmt -d` sobre los archivos Bash modificados: PASS.
- `git diff --check`: PASS.

## 4. Seguridad y límites verificados

- La exportación candidata usa lock compartido y no modifica el archivo V2.
- El exportador exige almacén existente, regular, legible y no symlink; no inicializa el documento.
- La validación V2 mantiene referencias, unicidad global de UUID, estados y esquema.
- Las credenciales no se imprimen en el menú ni se incorporan a logs/documentación.
- No se usó la clave maestra real ni se inspeccionó su contenido.
- No se realizaron operaciones de migración/cutover, ni escrituras en almacenes live.
- No se activaron configuraciones, no se inició Xray ni se modificaron servicios, certificados desplegados, firewall, puertos o red.
- No se accedió a la VPS de pruebas.

## 5. Hallazgos y pendientes

No se encontraron defectos bloqueantes dentro del alcance U-01.

Pendientes deliberadamente fuera de U-01:

1. Flujo seguro de publicación/aplicación runtime y verificación del estado aplicado.
2. Revocación efectiva de una asociación suspendida/vencida en runtime.
3. Gestión ACME DNS-01 con Cloudflare y ciclo de vida de certificados.
4. URI/QR de cliente y prueba externa NetMod de handshake TLS, WebSocket, autenticación y tráfico.
5. Migración legacy controlada, dry-run, backup, confirmación y rollback.

La aceptación de U-01 no cierra Etapa 2, Etapa 3 ni Etapa 5. La prueba Xray `run -test` no demuestra conectividad de extremo a extremo.

## 6. Conclusión

U-01 está IMPLEMENTADA, VERIFICADA y AUDITADA para el alcance aprobado. Se recomienda pasar a revisión/aceptación formal del propietario. Tras aceptación, la siguiente prioridad para la primera prueba real será diseñar y autorizar el flujo de aplicación runtime seguro; después se abordará ACME DNS-01/Cloudflare y la prueba externa NetMod. No se debe presentar la integración U-01 como una conexión ya operativa.


## 7. Publicación y sincronización

- Commit local: `1c2cd12f15be75d9f3a080ce028951724618c492`.
- Rama GitHub: `design/user-identity-association-v1`.
- Push: fast-forward desde `ca6d76895821310a3072d9de47268f925ecea7ba`, sin force push.
- La verificación posterior confirmó la misma referencia remota.
- La VPS `/opt/xray-manager` es el checkout que originó el commit; la sincronización final se vuelve a verificar después del registro documental.
- `main` y `Xray-Normativa/` no se modificaron.
- Aceptación formal de U-01: pendiente de decisión expresa del propietario.
