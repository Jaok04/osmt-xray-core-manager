# Diseño de integración — adaptador real systemd para Xray Runtime

**Fecha:** 2026-11-05
**Estado:** DISEÑO TÉCNICO PRELIMINAR — NO HABILITA OPERACIONES LIVE
**Rama prevista:** `design/user-identity-association-v1`
**Base:** R-05 fixture B4 + `modules/xray_service.sh` + plan H6
**Límite:** diseño y pruebas con mocks/fixtures. No ejecutar systemctl ni modificar runtime real.

## 1. Hallazgos de la inspección

1. `modules/xray_service.sh` ya implementa el control del servicio y usa `XRAY_MANAGER_LIFECYCLE_LOCK`. Incluye comprobación de unidad administrada, validación de configuración, estado, logs y acciones start/stop/restart/enable/disable.
2. `modules/main_menu.sh` ya conecta el menú de gestión de servicio con `xray_service_status` y `xray_service_action`. No se debe crear un segundo menú de control ni duplicar estas acciones.
3. `scripts/xray_runtime_service_adapter.py` es exclusivamente fixture. Su contrato de estado contiene `loaded_generation_id` y `loaded_config_sha256` porque los fixtures pueden controlar esos valores.
4. El estado `systemd active` y el hash actual de `/etc/xray/config.json` no prueban por sí solos qué generación cargó el proceso. El adaptador real no puede inventar esos campos ni copiar los valores de B4.

## 2. Arquitectura objetivo

- Mantener `xray_runtime_service_adapter.py` como adaptador fixture por defecto y conservar intacta su semántica de pruebas.
- Añadir un adaptador systemd separado, con contrato explícito y limitado a `xray.service`.
- No ejecutar comandos mediante shell, `eval` ni interpolación. Usar argumentos separados, entorno mínimo, timeout y lista cerrada de subcomandos/propiedades.
- Reutilizar el lock de ciclo de vida compartido de `modules/xray_service.sh`; la orquestación R debe adquirirlo antes de cualquier transición.
- Mantener el menú actual de servicios como interfaz de gestión general. La aplicación de un perfil debe entrar desde la gestión de perfiles y delegar en R-01–R-05; no debe duplicar lógica en Bash.
- Inyectar el adaptador en la orquestación para que los tests continúen usando fixture y la ruta real no pueda seleccionarse accidentalmente.
- El adaptador real no se seleccionará desde el CLI/menú en esta entrega. La conexión live se habilitará en un bloque posterior, después de auditoría y autorización específica.

## 3. Contrato del adaptador systemd

### Lecturas permitidas

Consultar únicamente `xray.service` y propiedades explícitas:
`LoadState`, `ActiveState`, `SubState`, `Result`, `ExecMainStatus`,
`MainPID`, `ExecMainStartTimestamp`, `ActiveEnterTimestamp`,
`InvocationID`, `FragmentPath`, `User`, `Group`, `ExecStart`,
`ExecStartPre` y `UnitFileState`.

Validar la unidad administrada comparando ruta, tipo de archivo, propietario,
permisos y contenido esperado. Si la unidad no coincide, el resultado es
`unmanaged`/no verificable y no se ejecutan acciones.

### Acciones futuras (no invocadas en este bloque)

- `restart`: sólo si el estado previo es `active`, hay confirmación explícita,
  la unidad coincide y las precondiciones de generación/hash/InvocationID siguen
  vigentes.
- `start`: sólo desde `inactive`, con confirmación explícita y operación
  `published_pending_start`.
- No incluir `stop`, `enable` ni `disable` en la interfaz de aplicación de
  perfiles. Esas acciones permanecen en el menú de servicio normativo.
- No iniciar automáticamente un servicio inactivo al publicar.
- No habilitar inicio automático como efecto lateral.

## 4. Evidencia de generación aplicada

La evidencia real debe separar tres hechos:

1. **Estado del servicio:** observado directamente desde systemd.
2. **Identidad de la configuración publicada:** hash calculado sobre el archivo
   runtime y enlazado al journal de la operación.
3. **Identidad de la invocación del proceso:** `InvocationID` y marcas de
   tiempo de systemd obtenidos después de la transición.

La atestación persistente propuesta debe incluir, como mínimo:
`operation_id`, `generation_id`, `config_sha256`, `InvocationID`,
`ActiveEnterTimestamp`, `unit_fragment_sha256` y fecha UTC. Debe ser
root:root, modo 0600, JSON estricto, tamaño acotado, sin secretos, escritura
atómica y protegida contra symlinks/hardlinks.

La atestación sólo se acepta si:
- la transición fue solicitada por una operación R identificada;
- systemd confirma la nueva invocación y `ActiveState=active`;
- el hash del archivo antes y después de la transición coincide con el hash
  publicado;
- la unidad corresponde a la unidad administrada esperada;
- la lectura posterior de systemd conserva el mismo `InvocationID`;
- no hay divergencia detectada en una nueva consulta.

Si falta la atestación, cambia el InvocationID, cambia el hash o el estado no
es verificable, el adaptador devuelve generación/hash no demostrados. Nunca
se deducen del registro de perfil activo ni del mero estado `active`.

## 5. Orquestación y almacenamiento

- Separar el almacén B4 fixture de cualquier almacén real. No reutilizar
  `XRAY_SERVICE_ROOT` temporal ni el marcador fixture en producción.
- La futura ruta de registro activo debe respetar el diseño aprobado de
  `/var/lib/xray-manager/profiles`; la atestación de invocación debe tener
  contrato y ubicación propios antes de implementación.
- La orquestación debe recibir un adaptador explícito; el default seguirá
  siendo fixture. La selección real requerirá una interfaz interna no
  disponible desde menús generales y un control de autorización live.
- El lock debe cubrir: relectura de estado, validación de precondiciones,
  acción systemd, observación posterior y escritura de atestación. No liberar
  el lock entre esos pasos.
- Si systemd devuelve timeout o se pierde la respuesta, consultar el estado
  y `InvocationID`; no repetir start/restart automáticamente.
- Si la recuperación no puede demostrar el estado previo, marcar
  `RECOVERY_REQUIRED`; no afirmar rollback exitoso.
- El menú de perfiles mostrará estados distintos: validada, publicada
  pendiente, aplicación solicitada, servicio verificado y recuperación
  requerida.

## 6. Pruebas requeridas antes de conectar el menú

1. Propiedades systemd completas, incompletas y malformadas.
2. Unidad ausente, no administrada, symlink, permisos/propietario incorrectos.
3. `active`, `inactive`, `failed`, `unknown` y `LoadState` no loaded.
4. Timeout antes de la transición, timeout después y respuesta perdida.
5. InvocationID que cambia, no cambia o desaparece.
6. Hash runtime divergente antes, durante o después de la transición.
7. Cambio externo concurrente y lock de ciclo de vida ocupado.
8. Rechazo de confirmación sin llamadas mutadoras.
9. Estado inicial inactive: publicación no inicia; sólo start manual confirmado.
10. Rollback con servicio previamente active/inactive y escenarios ambiguos.
11. Regresión completa de R-01–R-05 fixture, B4 y menú de servicio.
12. Inspección estática que demuestre que las pruebas no invocan systemctl
    real, no escriben `/etc/xray` y no modifican red/firewall/certificados.

## 7. Decisión de implementación por fases

**Fase A — contrato y adaptador de observación:** implementar consultas read-only
y pruebas con un ejecutable systemctl simulado. No conectar a menús ni invocar
systemd del host.

**Fase B — acciones aisladas con mocks:** implementar start/restart detrás de
un contrato inyectable y probar CAS, timeout, InvocationID, hash y lock. No
habilitar el adaptador real desde el CLI.

**Fase C — puente de orquestación:** adaptar R-05 para inyección del backend,
manteniendo fixture como default. La ruta systemd permanece bloqueada por
defecto; pruebas completas sólo con mocks.

**Fase D — conexión de perfiles/servicio:** añadir el flujo de confirmación
desde perfiles y reutilizar el menú actual de servicio. Requiere auditoría
integral del contrato y autorización específica antes de habilitar ejecución
live.

## 8. Límites

Este documento no autoriza:
- ejecutar `systemctl`, `journalctl` o comandos de servicio sobre el host;
- crear, modificar, recargar o habilitar unidades systemd reales;
- escribir `/etc/xray/config.json`;
- iniciar, reiniciar o detener Xray real;
- cambiar certificados, DNS, firewall, puertos o red;
- instalar/actualizar dependencias;
- usar almacenes o claves reales;
- modificar `main` o `Xray-Normativa/`;
- commit o push.

El primer ensayo live continúa sujeto a autorización nueva, explícita y
específica que identifique servidor, operaciones, rutas, versiones, ventana
y mecanismo de reversión.

## Addendum H6-A — implementación de observación (2026-11-05)

H6-A quedó implementada y auditada en alcance read-only:
- `scripts/xray_runtime_systemd_adapter.py` observa propiedades de `xray.service` y hash del archivo runtime.
- `tests/test_xray_runtime_systemd_adapter.py` aporta 11 pruebas focales con mocks.
- La generación/hash cargados permanecen nulos hasta disponer de atestación ligada al InvocationID.
- No hay acciones mutadoras ni integración en menús/orquestación.

Evidencia: `docs/IMPLEMENTACION_H6A_ADAPTADOR_SYSTEMD_OBSERVACION_2026-11-05.md` y `docs/AUDITORIA_H6A_ADAPTADOR_SYSTEMD_OBSERVACION_2026-11-05.md`. Resultado: 11/11 focales, 59/59 R-05+B4 y 257/257 Python globales PASS; smoke Bash, ShellCheck, AST y diff-check PASS.

H6-A no equivale a H6/live. No se invocó systemctl real ni se modificó runtime.
