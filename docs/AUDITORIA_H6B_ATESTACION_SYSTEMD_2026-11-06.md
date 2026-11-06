# Auditoría H6-B — atestación persistente systemd

Fecha: 2026-11-06
Estado: PASS CON LIMITACIONES — alcance aislado.
Alcance: revisión estática y pruebas con snapshots sintéticos.

## Resultados
- [x] Contrato R-05: operación schema 2, acción start/restart, confirmación aceptada y publicación validada.
- [x] Hash runtime: comparación antes, después y segunda observación posterior.
- [x] InvocationID: formato válido, nueva invocación y estabilidad posterior.
- [x] ActiveEnterTimestamp: estabilidad entre observaciones posteriores.
- [x] Unidad: ruta coincidente, archivo regular root:root 0644 y SHA-256.
- [x] JSON estricto, esquema exacto y límite de 16 KiB.
- [x] Almacén root:root 0700, archivos/lock 0600, lock interproceso y fsync.
- [x] Rechazo de symlink en rutas/archivos, hardlinks por nlink y sobrescritura divergente.
- [x] Pruebas focales H6-B: 12/12 PASS.
- [x] Regresión Python: 269/269 PASS.
- [x] Pruebas Bash tests/xray_service.sh, tests/xray_service_control.sh y tests/xray_admin_prepare_service.sh: PASS.
- [x] compileall, bash -n global, ShellCheck -S error, install.sh --check y git diff --check: PASS.
- [x] Escaneo estático: el módulo H6-B no invoca systemctl, subprocess, shell ni eval.

## Limitaciones
- No se probó con systemctl real ni con un proceso Xray real.
- No se integró el lock de ciclo de vida con el almacén: el futuro caller debe mantenerlo durante toda la transición y persistencia.
- No se conectó H6-B a R-05, H6-A, B4, el menú ni el CLI.
- Las observaciones usadas en las pruebas son sintéticas; no acreditan ejecución real.
- El directorio /var/lib/xray-manager/attestations no fue creado ni utilizado.
- El resultado no habilita H6 live ni el primer servicio VLESS-WS-TLS.

## Dictamen
H6-B queda IMPLEMENTADA, VERIFICADA Y AUDITADA en alcance aislado, PASS CON LIMITACIONES. El siguiente bloque será la integración controlada del almacén y las observaciones H6-A bajo el lock de ciclo de vida, manteniendo fixture como default. Requiere revisión antes de modificar R-05. No se realizó commit ni push. main y Xray-Normativa permanecen fuera del alcance.
