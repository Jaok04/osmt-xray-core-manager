# H6-G2 — F-03: contrato de propiedad y handoff del lifecycle lock

**Fecha:** 2026-11-06
**Estado:** decisión de implementación autorizada; sin habilitación live.

## Decisión

R-05 conserva la propiedad del `lifecycle_lock`. El puente Python/Bash no adquiere ni intenta adquirir ese lock: únicamente acepta un descriptor que demuestre que el proceso R-05 actual mantiene el bloqueo exclusivo sobre el archivo esperado.

La prueba se realiza sobre el descriptor exacto mediante `/proc/self/fdinfo/<fd>`. En Linux, la entrada `lock:` identifica el tipo `FLOCK`, el modo `WRITE`, el PID propietario y el dispositivo/inode. Se exige:

- descriptor abierto y regular;
- ruta absoluta sin componentes simbólicos;
- identidad dispositivo/inode coincidente entre descriptor y ruta;
- propietario/permisos `root:root 0600`, sin hardlinks;
- entrada FLOCK exclusiva vinculada al descriptor recibido;
- PID propietario igual al PID del proceso R-05 que hace la delegación.

El proceso Bash heredado vuelve a comprobar la entrada `fdinfo`, el PID propietario recibido y el inode del descriptor. No ejecuta `flock` para validar, porque `flock(LOCK_EX|LOCK_NB)` sobre el mismo open-file-description podría adquirir un lock que estuviera libre.

## Rechazo cerrado

Si procfs/fdinfo no está disponible, el descriptor no contiene la entrada FLOCK, el PID no coincide, la ruta/inode/permisos no coinciden o la información es ambigua, la acción se rechaza antes de invocar el controlador.

## Responsabilidades

- R-05 adquiere lifecycle y luego application lock, y conserva sus descriptores mientras dura cada tramo protegido.
- El puente solo transporta y verifica el descriptor lifecycle lock de R-05.
- `modules/xray_service.sh` sigue siendo el controlador único de start/stop/restart.
- Python no ejecuta `systemctl` ni cambia la propiedad del lock.
- El orden de liberación sigue siendo inverso: application y luego lifecycle.

## Límite de alcance

Esta decisión corrige la prueba de propiedad/handoff del puente, no integra todavía el backend live en R-05 ni cambia el alcance temporal de los locks del orquestador. G3 deberá establecer una sección crítica transaccional coherente para publicación, transición, observación, journal y recuperación, sin reacquisiciones anidadas. Fixture continúa como default y live sigue deshabilitado.

No se autorizan operaciones reales de systemd/Xray, escritura runtime, ACME, red, DNS, firewall, puertos, commit ni push.
