# B4.1 — prototipo fixture del contrato de privilegios del lanzador

**Fecha:** 2026-11-07
**Estado:** PROTOTIPO AISLADO IMPLEMENTADO; pruebas focales PASS. No es launcher de producción.
**Entorno:** VPS desarrollo `/opt/xray-manager`, fixtures temporales.
**Alcance autorizado:** desarrollo/fixtures; sin integración R-05/menú, sin cambios systemd y sin operaciones en VPS Pruebas.

## 1. Objetivo y resultado

Se implementó `scripts/xray_runtime_launcher_prototype.py` y su suite `tests/test_xray_runtime_launcher_prototype.py` para comprobar el contrato de privilegios propuesto para B4.1:

1. La fase privilegiada crea un `memfd` con los bytes exactos, valida SHA-256 y aplica todos los seals requeridos.
2. Se crea un enlace temporal `config.json` hacia `/proc/self/fd/N`; no se copia la configuración a un archivo mutable.
3. El proceso padre conserva la autoridad para escribir evidencia privada; la identidad de servicio no tiene permiso de escritura en esa evidencia.
4. Un hijo queda bloqueado antes de `exec`. El padre conoce su PID, escribe evidencia atómica 0600 con ese PID e InvocationID y sólo entonces libera al hijo.
5. El hijo ejecuta `setpriv`, desciende a una identidad no privilegiada, activa `NoNewPrivs`, conserva únicamente `CAP_NET_BIND_SERVICE` y ejecuta `xray run -test` mediante `exec` encadenado. El PID se conserva a través de `exec`.
6. La prueba confirma que Xray 26.10.31 lee el descriptor sellado y valida el JSON después del descenso de privilegios.

## 2. Archivos

- `scripts/xray_runtime_launcher_prototype.py`: preparación de fixture, plan de ejecución, fork/gate para escribir evidencia antes del exec y validación Xray aislada.
- `tests/test_xray_runtime_launcher_prototype.py`: pruebas de aislamiento fixture, memfd, rechazo de entradas inválidas, identidad no root, evidencia privada y ejecución Xray real tras `setpriv`.
- Se reutiliza `scripts/xray_runtime_config_attestation.py`; no se convierte su API fixture en API live.

## 3. Evidencia y límites

La evidencia de prueba se escribe para el PID hijo antes del exec; la cadena `setpriv` → Xray usa exec y conserva ese PID. El test vuelve a leer y verificar la evidencia por PID, InvocationID, SHA-256 y tamaño. El directorio de evidencia permanece 0700 y el archivo 0600, bajo propietario privilegiado; la identidad de servicio no puede escribirlo.

La prueba inspeccionó `/proc/self/status` tras `setpriv`: `CapInh`, `CapPrm`, `CapEff`, `CapBnd` y `CapAmb` quedaron limitadas a `CAP_NET_BIND_SERVICE` (`0x400`), y `NoNewPrivs=1`.

La prueba ejecutó `xray run -test`, no `xray run` como daemon. No abrió listener, no inició systemd ni probó `xray.service`. El InvocationID usado es sintético; no procede de systemd. El UID/GID usado es `nobody:nogroup`, no una cuenta `xray` administrada por el producto.

## 4. Restricciones de seguridad

- Cada entrada exige raíz absoluta con `.xray-manager-fixture` válido y de propiedad del ejecutor.
- El prototipo no contiene rutas live ni API para seleccionar una ruta de configuración del host.
- No acepta identidad root como identidad de servicio.
- El memfd es heredable y sellado; el enlace temporal sólo apunta a `/proc/self/fd/N`.
- La evidencia se escribe antes de liberar el hijo para exec; fallo al escribir evidencia impide que el hijo continúe.
- El hijo no escribe ni modifica evidencia.
- No se guarda contenido JSON, UUID, claves, PEM ni credenciales en el registro de evidencia.
- No se integra con R-05, backend live, menú ni `modules/xray_service.sh`.

## 5. Verificaciones

- Pruebas B4.1: 9/9 PASS.
- Pruebas B4 memfd existentes: 10/10 PASS.
- Prueba de compatibilidad Xray 26.10.31 tras descenso de privilegios: `Configuration OK`, exit 0.
- Prueba de escritura de evidencia como identidad de servicio: acceso de escritura rechazado.

La verificación global de regresión y controles estáticos se registra en el cierre de esta implementación.

## 6. Pendientes antes de integración

1. Probar identidad `xray:xray` y permisos definitivos; la prueba actual usa `nobody:nogroup`.
2. Verificar el descriptor heredado, enlace temporal y capacidades dentro del sandbox real de systemd administrado por Manager.
3. Diseñar el launcher ejecutable root-owned final y el contenido de unidad correspondiente; cualquier cambio real de unidad requiere autorización live específica.
4. Integrar correlación con systemd MainPID/InvocationID/starttime y el verificador de proceso, sin declarar `completed` hasta verificar postcondiciones.
5. Conectar al flujo transaccional R-05 y al controlador único `modules/xray_service.sh` sólo después de completar pruebas/auditoría y obtener autorización para ese alcance.

**Conclusión:** el contrato de privilegios es viable en una prueba aislada con Xray real y memfd sellado. Esto no habilita operaciones live ni demuestra todavía compatibilidad con el sandbox systemd final.
