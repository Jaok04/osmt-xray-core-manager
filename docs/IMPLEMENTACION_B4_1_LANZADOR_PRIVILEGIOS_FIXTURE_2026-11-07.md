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

---

## Auditoría focal B4.1 — correcciones en fixtures (2026-11-07)

**Estado:** CORREGIDO Y VERIFICADO EN DESARROLLO; no integrado ni publicado. HEAD base: 899f29f4253f56f80d0d803207feceb743879a0a.

- **A01 — identidad modificable (alta): RESUELTO.** Antes del fork se revalida usuario/grupo mediante NSS; UID/GID deben ser enteros no-root, coincidir con los nombres y con el grupo primario.
- **A02 — descriptor/metadatos (alta): RESUELTO.** Se verifican heredabilidad, seals, tamaño real con fstat, lectura íntegra con pread y SHA-256 de los bytes; se contrastan metadatos. Un memfd sustituto con bytes diferentes se rechaza.
- **A03 — espera indefinida (media): RESUELTO.** Timeout 0.1–300 s, waitpid no bloqueante, terminación del grupo de procesos y recolección del hijo. Retorno 124 identifica timeout.
- **A04 — ejecutables (media): MITIGADO.** Xray y setpriv deben ser rutas absolutas a archivos regulares no simbólicos, propiedad de root, ejecutables y sin escritura de grupo/otros. Persiste una ventana TOCTOU entre validación y exec; no es una primitiva de producción frente a un actor que pueda modificar directorios raíz.

### Pruebas y verificación
La suite B4.1 creció de 9 a 16 pruebas: manipulación UID/GID, metadatos, sustitución de memfd, binario symlink, binario modificable y timeout con terminación/recolección. Se conserva Xray 26.10.31 run -test tras setpriv y la evidencia privada. B4.1 focal 16/16; Python global 433/433; Bash 62/62; compileall, bash -n, ShellCheck -S error, install.sh --check y git diff --check PASS.

No se ejecutó systemd ni se crearon cuentas/grupos; no se tocó /etc/xray, unidad, servicio, runtime, R-05, modules/xray_service.sh ni VPS Pruebas. Xray-Normativa intacta.

**Límites y siguiente paso:** identidad nobody:nogroup, InvocationID sintético y run -test; no daemon ni sandbox systemd real. Diseñar fixture xray:xray y requisitos del sandbox. No integrar a R-05/controlador ni preparar infraestructura live sin autorización específica. Sin commit ni push.
