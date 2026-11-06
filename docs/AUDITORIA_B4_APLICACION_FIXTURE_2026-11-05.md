# Auditoría técnica B4 — aplicación fixture y registro activo

**Fecha:** 2026-11-05
**Dictamen:** PASS CON LIMITACIONES — 59/59 pruebas focales; 246/246 pruebas Python globales; 61/61 suites Bash.
**Rama:** `design/user-identity-association-v1`
**HEAD base:** `2902b2ef602dfe97acf62428d6b7c35ce7c81d5d`

## 1. Alcance

Auditoría del registro activo de perfil y su integración con la orquestación R-05 exclusivamente en almacenes temporales, fixtures y adaptadores simulados. No se auditó ni ejecutó integración live.

## 2. Pruebas focales

**59/59 PASS** en `tests.test_xray_runtime_orchestrator`, incluidas las 43 pruebas R-05 previas y 16 pruebas B4 nuevas. Se cubre:
1. Registro activo tras restart fixture confirmado y verificado por generación/hash.
2. Conservación del registro anterior en `published_pending_apply`, `published_pending_start` y rollback.
3. Rechazo de estados inactive/failed/unknown como evidencia de perfil activo.
4. Inicio explícito desde `published_pending_start`, con confirmación independiente.
5. Cancelación de start sin transición ni evento de start.
6. CAS de estado/generación/hash previo para start.
7. Rollback de configuración ante start rechazado.
8. Fallo posterior a transición que queda `recovery_required`, sin registrar perfil activo.
9. Recuperación tras caída posterior a start sin repetir la acción.
10. Recuperación tras caída después de verificación y antes de completar journal.
11. Reconciliación de journal completed cuando falta el registro.
12. Idempotencia de reconciliación; no cambia `applied_at` si la identidad ya está registrada.
13. Rechazo de marcador inválido, registro simbólico y afirmación de servicio inactive.
14. Conservación del registro anterior en fallo de restart/rollback.
15. Preflight del almacén activo inválido antes de publicar o solicitar una acción de servicio.

## 3. Regresión global

| Control | Resultado |
|---|---:|
| Python `unittest discover` | 246/246 PASS |
| Suites Bash `tests/*.sh` | 61/61 PASS |
| `compileall` (scripts/tests) | PASS |
| `bash -n` global | PASS |
| ShellCheck `-S error` global | PASS |
| `./install.sh --check` | PASS; sin cambios del sistema |
| `git diff --check` | PASS |

Las suites Bash completaron sin código de error. Las pruebas de integración que invocan el binario Xray lo hacen contra configuraciones de fixture/temporales; no levantan el servicio ni abren listeners.

## 4. Controles de seguridad

- El registro activo requiere un fixture root-only marcado y no puede confundirse con un almacén de producción.
- Escritura atómica, fsync, lock interproceso, validación estricta y rechazo de symlinks/hardlinks.
- No se registran credenciales, UUID, URI ni claves privadas.
- El registro se escribe solo tras observar estado active y generación/hash exactos.
- En estados pendientes o rollback no se sustituye el registro previo.
- La acción start desde inactive exige confirmación explícita y compare-and-swap.
- Recovery reconcilia por generación/hash y no repite una acción de start/restart ya observada.
- No se añadieron dependencias.
- El adaptador de servicio B4/R-05 no invoca systemd, D-Bus ni procesos externos.

## 5. Limitaciones abiertas

1. El registro activo B4 y la acción start son fixture-only.
2. No se conectó B4 al menú de perfiles ni al menú de servicio de producción.
3. No hay adaptador systemd real integrado en la transacción R-01–R-05.
4. No se ha demostrado el registro activo a partir de una observación real de Xray/systemd.
5. No se probó VPS limpia, ACME real, DNS público, firewall, listener WAN ni cliente NetMod externo.
6. Etapa 5, Etapa 6 y B4 no se cierran con esta auditoría.

## 6. Exclusiones y estado Git

No se ejecutó systemd real ni se consultó/modificó `xray.service`, `/etc/xray/config.json`, runtime persistente, certificados, claves, DNS, firewall, puertos, red o VPS de pruebas. No se instalaron/actualizaron dependencias. `Xray-Normativa/` permanece intacta; `main` no se modificó. No hubo commit ni push.

**Dictamen final:** PASS CON LIMITACIONES para B4 fixture-only. La siguiente brecha es el adaptador real, su integración de menú y la autorización específica para pruebas live. El primer servicio VLESS-WS-TLS todavía no está habilitado para producción desde el administrador.
