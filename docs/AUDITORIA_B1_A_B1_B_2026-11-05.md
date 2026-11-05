# Auditoría B1-A / B1-B — 2026-11-05

**Alcance:** B1-A preparación de servicio desde el administrador y B1-B manifiesto de integridad.
**Entorno:** VPS de desarrollo `Implementación-Xray`, checkout `/opt/xray-manager`, rama `design/user-identity-association-v1`.
**Base Git:** `fb5010c7f6bd19aed279eb42d1ae29e4a8050530`.
**Resultado:** pruebas aisladas PASS; B1 aceptado formalmente y publicado; sin validación live.

## 1. Matriz de aceptación

| Requisito | Implementación | Evidencia | Resultado |
|---|---|---|---|
| Registrar versión y arquitectura | Manifiesto v1 | `tests/xray_admin.sh` | PASS |
| Registrar hashes binario/geodata/paquete | SHA-256 | `tests/xray_admin.sh` | PASS |
| Verificar instalación antes de no-op update | verify previo | `tests/xray_admin.sh` | PASS |
| Bloquear geodata alterado | hash mismatch fail-closed | `tests/xray_admin.sh` | PASS |
| Bloquear binario alterado | hash mismatch fail-closed | `tests/xray_admin.sh` | PASS |
| Bloquear instalación heredada sin manifiesto | estado no verificado | `tests/xray_admin.sh` | PASS |
| Bloquear artefactos huérfanos en install | no descarga ni sobrescribe | tests/xray_admin.sh | PASS |
| Bloquear manifiesto con permisos incorrectos | verify fail-closed; repair lo sustituye de forma segura | tests/xray_admin.sh | PASS |
| Reparación explícita | repair registra manifiesto nuevo | `tests/xray_admin.sh` | PASS |
| Rollback restaura manifiesto anterior | respaldo/restauración | `tests/xray_admin.sh` | PASS |
| Preparación desde menú | opción [7] y enrutamiento | `tests/stage1_menu.sh` | PASS |
| Preparación exige integridad y confirmación | fixture válido, cancelación, hash alterado y manifiesto ausente | `tests/xray_admin_prepare_service.sh` | PASS |
| Servicio activo bloquea preparación | guard al inicio | `tests/xray_service.sh` | PASS |
| Preparación de menú respeta bloqueo de ciclo de vida | contención con lock ocupado, sin invocar preparación | tests/xray_admin_prepare_service.sh | PASS |
| Preparación idempotente/colisiones/permisos | fixture de servicio | `tests/xray_service.sh` | PASS |
| Instalador aislado conserva comportamiento | fixture con prefijo | `tests/install.sh` | PASS |

## 2. Pruebas ejecutadas

- Suite Bash completa: **60/60 scripts PASS**.
- Suite Python: **171/171 tests PASS** mediante `python3 -m unittest discover -s tests -p 'test_*.py'`.
- `python3 -m py_compile scripts/*.py tests/*.py`: PASS.
- `bash -n` en módulos, lib, config, tests, `install.sh` y `bin/xray-manager`: PASS.
- ShellCheck `-S error` en todos los Bash del proyecto: PASS.
- `./install.sh --check`: PASS; no modificó el sistema.
- `git diff --check`: PASS.
- `python3 -m pytest -q tests` no pudo ejecutarse porque pytest no está instalado; no se instaló ninguna dependencia. La suite Python se ejecutó con unittest y pasó completa.

## 3. Límites y exclusiones

- No se ejecutó instalación, actualización ni reparación live.
- No se ejecutó la nueva opción [7] contra el sistema real.
- No se creó usuario/grupo Xray real ni unidad `xray.service`.
- No se invocó el binario real systemctl; la comprobación de servicio activo se simuló con un stub. No se inició/habilitó/reinició Xray.
- No se modificaron configuración runtime, certificados reales, DNS, firewall, puertos, red o dependencias.
- No se usó `Vps de Pruebas`.
- No se leyó `/etc/xray-manager/keys/master.key`.
- `main` y `Xray-Normativa/` permanecen intactas.

## 4. Estado Git y publicación

- Commit funcional B1: c8cd20c2a576fb1926fdcf11945cd75cf1c4211c (feat(xray): verify installation and prepare service).
- Push fast-forward confirmado a design/user-identity-association-v1.
- Verificación posterior: HEAD local = HEAD remoto; árbol limpio.
- main permanece en 656ecedc506a94a6461aee296b20871d51a38bf3.
- Los 14 documentos normativos sustantivos continúan idénticos al respaldo.
- Etapas 2, 3 y 5 siguen ABIERTAS; R-06/live continúa NO AUTORIZADA.


Prueba adicional de B1-A: tests/xray_service.sh ocupa el bloqueo de ciclo de vida en un descriptor independiente, comprueba que la preparación concurrente falla sin modificar el fixture, libera el lock y vuelve a ejecutar la preparación correctamente. PASS.

## Addendum de aceptación y publicación — 2026-11-05

El propietario aceptó formalmente B1-A/B1-B y autorizó commit/push exclusivamente en design/user-identity-association-v1. Commit funcional c8cd20c2a576fb1926fdcf11945cd75cf1c4211c; GitHub confirmó push fast-forward. Verificación posterior confirmó HEAD local/remoto coincidentes, árbol limpio, main intacta y 14/14 documentos normativos idénticos al respaldo. La publicación no cambia las limitaciones live descritas en esta auditoría.
