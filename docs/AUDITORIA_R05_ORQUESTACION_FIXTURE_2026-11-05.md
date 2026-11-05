# Auditoría técnica R-05 — orquestación fixture-only

**Fecha:** 2026-11-05
**Resultado:** PASS CON LIMITACIONES — 43/43 pruebas focales R-05; 230/230 pruebas Python globales; 61/61 pruebas Bash globales.
**Estado de aceptación:** ACEPTADA FORMALMENTE por el propietario el 2026-11-05, limitada al alcance fixture-only y a las limitaciones documentadas.
**Rama:** `design/user-identity-association-v1`.
**HEAD base previo:** `53d60d26becf6cca943f4317068b66e232d936d9`.

## 1. Alcance auditado

Se auditó la implementación de R-05 en almacenes temporales, fixtures y mocks. R-05 reutiliza R-01 preflight, R-02 staging/TLS leases, R-03 snapshot/journal y R-04 publicación/rollback. El adaptador de servicio solo simula el estado de `xray.service`.

Archivos de código:
- `scripts/xray_runtime_service_adapter.py`
- `scripts/xray_runtime_orchestrator.py`
- `scripts/xray_runtime_journal.py`
- `scripts/xray_runtime_preflight.py`
- `scripts/xray_runtime_publisher.py`

Pruebas:
- `tests/test_xray_runtime_orchestrator.py`
- `tests/test_xray_runtime_preflight.py`
- suites globales existentes.

Contrato de decisiones: `docs/DECISION_R05_JOURNAL_GENERATION_2026-11-05.md`.

## 2. Resultado de pruebas focales

**43/43 PASS tras corrección de concurrencia.** La suite cubre:
1. restart activo confirmado, con verificación de generación y hash;
2. confirmación rechazada: publicación pendiente sin restart;
3. estado inicial inactive: publicación pendiente sin start/restart;
4. estado inicial failed y unknown: fail-closed antes de publicar;
5. discrepancia entre hash cargado y snapshot;
6. ausencia de configuración previa recuperable;
7. cambio de estado durante staging;
8. cambio externo después de publicar;
9. carrera entre status y restart: compare-and-swap rechaza la acción;
10. restart rechazado, excepción y timeout previo;
11. timeout posterior y pérdida de respuesta reconciliados por status;
12. generación ajena y hash incorrecto no se aceptan como éxito;
13. estados posteriores inactive/unknown;
14. fallo de rollback de configuración;
15. fallo de restauración del servicio;
16. caída después de publicar, antes/después de rename, tras restart, tras verificación y durante rollback;
17. recuperación idempotente después de rollback de archivo y servicio;
18. lock contention y recuperación posterior;
19. compatibilidad schema 1 sin reescritura;
20. validación estricta de schema 2 y unicidad de generation_id;
21. rechazo de symlink en fixture root y de datos JSON/estados no tipados;
22. bitácora de adaptador limitada a operaciones simuladas.

## 3. Regresión global y análisis estático

| Control | Resultado |
|---|---:|
| Python unittest global | 230/230 PASS |
| Bash tests/*.sh | 61/61 PASS |
| Python compileall (scripts y tests) | PASS |
| bash -n global | PASS |
| ShellCheck `-S error` global | PASS |
| `./install.sh --check` | PASS, sin cambios de sistema |
| `git diff --check` | PASS |
| Escaneo de módulos R-05 para llamadas systemd/proceso | Sin coincidencias |

El escaneo no encontró referencias a `systemctl`, `journalctl`, `subprocess`, `os.system`, `Popen`, D-Bus o equivalentes en los dos módulos R-05. La ejecución de `install.sh --check` confirmó que las dependencias ya estaban disponibles y no modificó el sistema.

## 4. Controles de seguridad y consistencia

- No se añadió ni actualizó ninguna dependencia.
- No se instaló ni ejecutó Certbot.
- El adaptador no invoca servicios reales, shell ni procesos externos.
- El adaptador exige fixture dedicado y almacenamiento root-only, rechaza symlinks y valida JSON estricto.
- El journal schema 1 mantiene compatibilidad; schema 2 es estricto y contiene generación ligada a la petición y evidencia.
- La operación compara el estado del servicio antes de staging, después de staging y justo antes de acción.
- Restart y restore del adaptador son compare-and-swap con generación/hash esperados; no pisan cambios externos.
- Un estado inicial failed/unknown no se inicia ni se reinicia automáticamente.
- Una confirmación rechazada conserva la configuración cargada anterior y registra `published_pending_apply`.
- Un servicio inicialmente inactive no se inicia y queda `published_pending_start`.
- La recuperación no repite acciones ambiguas sin reconciliar estado, generación y hash.
- Si se observa una generación ajena, se evita sobrescribir el estado externo y se solicita intervención mediante `recovery_required`.

## 5. Limitaciones y discrepancias pendientes

1. R-05 es simulación fixture-only. No acredita comportamiento de systemd real ni conectividad.
2. No se añadió UI/menú. La confirmación es un argumento booleano explícito de la API interna.
3. No se integró todavía el registro persistente del perfil activo exigido por Etapa 5 §7. La aplicación de perfil no se debe declarar funcionalmente completa hasta integrar y auditar ese registro.
4. No existe adaptador systemd real. No se ha conectado R-01–R-04 a un servicio real.
5. La recuperación de journals schema 2 queda delegada a R-05; los journals schema 1 mantienen su ruta previa.
6. El contrato no implementa start manual posterior de `published_pending_start`; la futura integración de UI debe realizar preflight, confirmación y verificación sin inferir autorización.
7. No se cierra Etapa 5 ni Etapa 6. R-05 es solo un bloque técnico de orquestación simulada.

## 6. Exclusiones confirmadas

No se consultó ni modificó systemd real, `xray.service`, runtime Xray, `/etc/xray/config.json`, certificados persistentes, claves, DNS, firewall, puertos, red, dependencias ni la VPS de pruebas. No se ejecutó ACME real ni se realizó una conexión WAN. No se modificó `main` ni `Xray-Normativa/`.

**R-06/live permanece NO AUTORIZADA.**

## 7. Dictamen

La implementación satisface los criterios técnicos fixture-only definidos para R-05 y supera las pruebas focales y de regresión registradas. Se recomienda aceptación formal limitada a este alcance, con las limitaciones de la sección 5. La aceptación no autoriza publicación, adaptador real, activación de perfiles, systemd real ni operaciones live. Se requiere autorización de publicación separada después de la aceptación.

## 8. Reauditoría de concurrencia R-05 — 2026-11-05

Tras la revisión técnica se detectó que `os.replace()` garantizaba sustitución atómica del archivo, pero no serializaba el ciclo completo lectura → comparación CAS → escritura entre procesos. El adaptador podía aceptar dos decisiones basadas en el mismo estado previo y la bitácora podía perder actualizaciones concurrentes.

### Corrección

- Se añadió `adapter.lock` al fixture R-05, protegido root:root 0600.
- Se añadió exclusión mutua interproceso con `fcntl.flock(LOCK_EX)` alrededor de las operaciones públicas `status`, `restart`, `restore` y `audit_events`.
- El lock cubre lectura, comparación, modificación, escritura atómica y append de auditoría; restart y restore ahora realizan CAS serializado.
- La apertura usa `O_NOFOLLOW`; se valida tipo regular, UID/GID root, modo 0600, `st_nlink == 1`, tamaño acotado, marcador esperado e identidad de inode después de adquirirlo.
- No se modificó el contrato de journal schema 1/2 ni el flujo del orquestador. No se añadieron dependencias.

### Pruebas nuevas

1. Dos procesos solicitan restart con la misma generación/hash previa mientras otros cuatro consultan status: exactamente un restart aceptado, uno rechazado por precondición y seis eventos persistidos sin pérdidas.
2. Dos procesos intentan restaurar simultáneamente desde la misma generación publicada: exactamente una restauración aceptada y una rechazada por precondición.
3. Un archivo `adapter.lock` simbólico se rechaza antes de operar.

### Regresión final

| Control | Resultado |
|---|---:|
| Pruebas focales R-05 | 43/43 PASS |
| Python global | 230/230 PASS |
| Suites Bash | 61/61 PASS |
| `compileall` Python | PASS |
| `bash -n` global | PASS |
| ShellCheck `-S error` global | PASS |
| `./install.sh --check` | PASS, sin cambios del sistema |
| `git diff --check` | PASS |
| Escaneo del adaptador para invocaciones de servicios/procesos reales | Sin coincidencias |

Las suites Bash se ejecutaron con sus fixtures temporales; las pruebas de integración Xray validan configuraciones temporales. No se consultó ni modificó systemd real, `xray.service`, `/etc/xray/config.json`, runtime persistente ni infraestructura. No se ejecutaron ACME real, DNS, firewall, puertos, red o conexiones WAN.

**Dictamen actualizado:** PASS CON LIMITACIONES en el alcance fixture-only, con la corrección de concurrencia implementada y auditada localmente. El propietario aceptó formalmente R-05 el 2026-11-05 dentro del alcance fixture-only. La publicación queda autorizada por separado en esta misma decisión; adaptador real y operaciones live siguen fuera de alcance y requieren autorizaciones independientes.
