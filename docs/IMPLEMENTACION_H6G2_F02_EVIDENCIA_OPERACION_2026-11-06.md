# H6-G2 — implementación F-02: evidencia operation/generation/publication

Fecha: 2026-11-06
Entorno: VPS de desarrollo `Implementación-Xray`, `/opt/xray-manager`
Rama: `design/user-identity-association-v1`
Base Git: `9bab1dbed7d4873aa30a3fd00a976a1d666d9355`

## Cambios

- Nuevo `scripts/xray_runtime_operation_evidence.py`.
- El lector verifica journal schema 2, operation_id/generation_id, estado publicado, ausencia de rollback, staging/manifest/lease, validación persistida exacta, checks obligatorios, hash del binario, hash de staging/publicación y bytes runtime actuales en la ruta asociada a la operación.
- La consulta al historial de validación usa `read_only_locked()`; no recupera ni modifica el almacén.
- El lector marca obligatoriamente `environment=fixture`, ya que el journal R-03/R-05 actual requiere marcadores fixture. No puede emitir evidencia live.
- `LiveRuntimeBackend.start/restart/stop` ya no aceptan `expected_runtime_config_sha256`. Exigen `operation_id` + `generation_id` y un lector de evidencia. La evidencia debe estar verificada, coincidir con ambas identidades, indicar `environment=live`, publicación y validación satisfactoria. Compara runtime hash únicamente contra el hash de publicación devuelto por el lector.
- Falta de lector, evidencia fixture, operación/generación ajena, publicación no confirmada o hash runtime divergente bloquean antes de llamar al controlador.
- No se conecta el lector a R-05, CLI ni menú. No se cambia el backend fixture predeterminado.

## Pruebas

- Backend live: 20/20 PASS.
- Lector de evidencia: 9/9 PASS.
- Suite Python completa: 370/370 PASS.
- Suites Bash: 62/62 PASS.
- `py_compile`, `bash -n` focal, `git diff --check` y ShellCheck `-S error` focal: PASS.

Las pruebas son unitarias/mocks/fixtures. No se ejecutó systemctl real ni se modificó runtime, certificados, DNS, firewall, puertos o red.

## Dictamen

F-02: **implementación del contrato y verificación de cadena fixture completadas; evidencia live aún NO DISPONIBLE**. No se puede declarar resuelto para integración live porque el almacén/journal actual está deliberadamente restringido a fixtures. El backend exige evidencia live y rechaza la salida del lector actual (`environment=fixture`). Se requiere diseño de journal/evidence store live en G3 y auditoría posterior.

No commit/push. `main` y `Xray-Normativa/` intactas.
