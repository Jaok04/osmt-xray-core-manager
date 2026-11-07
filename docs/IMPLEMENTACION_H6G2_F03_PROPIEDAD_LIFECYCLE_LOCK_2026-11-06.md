# H6-G2 — implementación F-03: propiedad verificable del lifecycle lock

**Fecha:** 2026-11-06
**Alcance:** VPS de desarrollo `/opt/xray-manager`; rama `design/user-identity-association-v1`.
**Estado:** implementado en el puente aislado; pendiente auditoría independiente e integración G3.

## Cambios

- `scripts/xray_runtime_service_control.py`
  - Se eliminó la llamada `flock(LOCK_EX|LOCK_NB)` que podía adquirir un lock libre.
  - Se inspecciona `/proc/self/fdinfo/<fd>` y se exige una entrada FLOCK ADVISORY WRITE asociada al descriptor exacto, con PID propietario igual a `os.getpid()` y dispositivo/inode coincidente.
  - Se pasa `XRAY_MANAGER_LIFECYCLE_LOCK_OWNER_PID` al proceso Bash solo después de verificar la propiedad en Python.
  - Ausencia de procfs/fdinfo o evidencia no coincidente produce rechazo cerrado.

- `modules/xray_service.sh`
  - `xray_service_action_inherited_lock()` ya no ejecuta `flock -n`.
  - Comprueba la entrada FLOCK en `/proc/$$/fdinfo/<fd>`, el PID propietario heredado y el inode del descriptor, además de las comprobaciones previas de ruta, identidad, propietario y permisos.
  - Continúa delegando exclusivamente en `xray_service_action_locked()`.

- Pruebas
  - `tests/test_xray_runtime_service_control.py`: descriptor bloqueado correcto, descriptor abierto sin lock, lock en otro descriptor del mismo proceso, PID propietario divergente, archivo distinto, symlink, acciones no permitidas, timeout, error del controlador e integración con systemctl mock.
  - `tests/xray_service_control.sh`: handoff correcto, descriptor sin lock, descriptor ajeno y descriptor ausente; no se muta systemd real.

## Evidencia inicial

- Pruebas focales puente Python: 12/12 PASS.
- Prueba Bash de control de servicio: PASS.
- La prueba experimental read-only confirmó que `fdinfo` muestra el FLOCK vinculado al descriptor y el PID del proceso que lo adquirió; una apertura independiente no obtiene el lock mientras está retenido.

## Límites

- No se modificó `xray_runtime_orchestrator.py`, el journal ni el menú.
- R-05 no está conectado al backend live; fixture continúa como default.
- Esta corrección verifica el handoff del descriptor, pero no extiende por sí sola el lifecycle lock sobre todo el ciclo apply/publication/recovery. G3 deberá diseñar e implementar el alcance transaccional y evitar reacquisiciones anidadas.
- No se ejecutó systemctl real ni se tocó Xray runtime, `/etc/xray`, certificados, DNS, firewall, puertos, red o VPS de pruebas.
- No se actualizaron dependencias ni se hizo commit/push.

## Resultado

F-03 queda corregido en el puente aislado y listo para auditoría independiente. H6-G2 no se cierra y el backend live permanece deshabilitado hasta completar G3/G4/G5.
