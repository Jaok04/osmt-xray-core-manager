# B4.3-B — implementación fixture del adaptador de evidencia persistente

**Fecha:** 2026-11-08
**Estado:** IMPLEMENTADO Y VALIDADO EN FIXTURES; no integrado en backend live.
**Rama:** `design/user-identity-association-v1`
**Base:** `f1f5218108756755c814ee80eb29252ff414c4b7` (diseño B4.3-B).

## 1. Alcance

Se implementó el paso siguiente al diseño B4.3-B: conectar, exclusivamente en fixtures, el PID del hijo bloqueado por el supervisor con el almacén persistente B4.3-A. El objetivo de este bloque es demostrar que el registro root-only se crea y verifica antes de liberar el pipe gate, usando una raíz anclada por descriptor y sin fallback al contrato plano B4.1.

No se modificaron `modules/xray_service.sh`, R-05, menú, unidad systemd, backend live, runtime del host, certificados, DNS, firewall, puertos, cuentas ni VPS Pruebas. No se ejecutó `systemctl` ni daemon Xray.

## 2. Implementación

### 2.1 Almacén B4.3-A

Archivo: `scripts/xray_runtime_evidence_store.py`.

Se conservaron las APIs por ruta existentes (`create_evidence()` y `verify_evidence()`) para no romper la regresión B4.3-A. Se añadieron:

- `create_evidence_from_root_fd()`
- `verify_evidence_from_root_fd()`
- `_open_evidence_dir_from_root_fd()`

La API nueva duplica el descriptor recibido, marca su copia no heredable y nunca cierra el descriptor propiedad del caller. Verifica con `fstat` que el ancla sea un directorio `root:root 0711`; abre el marcador fixture con `O_NOFOLLOW`, verifica inode/propiedad/modo y contenido exacto; recorre el layout componente a componente mediante `dir_fd`, `O_DIRECTORY|O_NOFOLLOW` y `fstat`.

El recorrido valida los directorios `var`, `var/lib`, `var/lib/xray`, `var/lib/xray-manager`, `var/lib/xray-manager/evidence`, `run` y `run/xray` contra UID/GID/modos del contrato B4.3. No reabre la raíz por ruta absoluta ni repara drift.

La creación conserva publicación exclusiva, escritura completa, `fsync`, `root:root 0600`, hard-link sin reemplazo y verificación posterior. La verificación exige `st_nlink=1`, JSON válido y el conjunto exacto de campos permitidos. El registro contiene únicamente schema, InvocationID, estado `prepared_before_exec`, PID, SHA-256 y tamaño. La referencia retornada es el nombre del registro, no una ruta re-resuelta.

### 2.2 Adaptador

Nuevo archivo: `scripts/xray_runtime_supervisor_evidence.py`.

`prepare_persistent_evidence()` valida que el plan sea fixture, el PID sea el hijo que el supervisor acaba de bloquear, el GID coincida con el plan y el hash/tamaño correspondan a los metadatos previamente verificados del memfd. Crea y verifica el registro mediante la API anclada y comprueba que el contenido devuelto corresponde al PID/hash/tamaño esperados.

No devuelve bytes de configuración ni secretos. Convierte fallos del almacén en un error controlado del adaptador.

### 2.3 Supervisor

Archivo: `scripts/xray_runtime_launcher_prototype.py`.

Se añadió el parámetro explícito `evidence_backend`:

- `legacy_b41` (predeterminado): conserva la ruta B4.1 previa.
- `persistent_b43`: abre el descriptor de raíz fixture con `O_DIRECTORY|O_NOFOLLOW`, lo marca no heredable y lo entrega al adaptador antes de escribir el token del gate.

El hijo cierra su copia del descriptor de raíz inmediatamente después de `fork` y antes de esperar el gate. El descriptor no llega al proceso ejecutado. El padre cierra su descriptor en el bloque `finally`. Si falla la creación/verificación de evidencia, la excepción impide escribir el token, el hijo es terminado y recolectado; no se invoca B4.1 como fallback.

## 3. Pruebas añadidas

`tests/test_xray_runtime_evidence_store.py` amplía el contrato FD con:

- creación/verificación desde descriptor;
- persistencia al cerrar/reabrir;
- anclaje al inode original tras renombrar/reemplazar la ruta nominal;
- rechazo de descriptor cerrado;
- rechazo de symlink y drift de modo;
- rechazo de replay/InvocationID duplicada.

`tests/test_xray_runtime_launcher_prototype.py` amplía el flujo con:

- backend persistente exitoso y correlación del PID bloqueado;
- modo/owner del registro y denegación de lectura a la identidad de servicio;
- fallo inyectado de creación: el ejecutable fixture no se alcanza y el hijo se recolecta;
- fallo inyectado de verificación: el ejecutable fixture no se alcanza y el hijo se recolecta;
- comprobación de que el descriptor de raíz no aparece en los descriptores del proceso ejecutado;
- ausencia de fallback al backend B4.1.

El éxito del nuevo backend se probó con un ejecutable fixture controlado. La prueba preexistente con Xray 26.10.31 `run -test` sigue validando el camino B4.1/memfd heredado; no se afirma que Xray real se haya ejecutado a través del selector `persistent_b43`.

## 4. Resultados ejecutados

| Validación | Resultado |
|---|---:|
| Evidencia B4.3-A + supervisor B4.3-B focal | 43/43 PASS |
| Python global (`unittest discover`) | 469/469 PASS |
| Suites Bash (`tests/*.sh`) | 62/62 PASS |
| `python3 -m compileall -q scripts tests` | PASS |
| `py_compile` de los cinco archivos afectados | PASS |
| `bash -n` global | PASS |
| ShellCheck global `-S error` | PASS |
| `./install.sh --check` | PASS, sin modificar el sistema |
| `git diff --check` | PASS |

La regresión Bash completa ejecutó Xray-core 26.10.31 `run -test` para sus matrices existentes de protocolos y casos negativos, en configuraciones temporales. No inició un daemon ni un listener.

## 5. Semántica probatoria y límites

`prepared_before_exec` demuestra solamente que el supervisor preparó y verificó un registro para un PID/InvocationID sintético antes de liberar el gate. No demuestra que `exec` tuvo éxito, que Xray leyó la configuración, que el proceso está activo, que systemd lo supervisa ni que exista `MainPID`/`InvocationID` real.

Si la publicación tuvo éxito pero la verificación posterior falla, puede quedar un registro completo para diagnóstico; el gate permanece cerrado y el hijo no ejecuta Xray. No se borra evidencia automáticamente en ese escenario.

La prueba de anclaje demuestra que el backend FD no sigue el reemplazo de la ruta nominal. La confianza inicial del descriptor sigue siendo responsabilidad del caller: este prototipo lo abre desde una raíz fixture previamente validada. La futura integración deberá recibir el descriptor de una raíz confiable del Manager, no reconstruir confianza desde una ruta mutable.

## 6. Estado y siguiente puerta

B4.3-B está implementado y probado sólo en fixtures. El resultado no cierra H6-G2/H6-G3, no integra B4.1/B4.2 con systemd real, no habilita R-05 ni satisface el objetivo del primer servidor. Antes de cualquier integración se requiere revisión independiente, evaluación integral de contrato/ownership/sandbox y autorización específica. No modificar `main`, `Xray-Normativa/`, VPS Pruebas, unidad, controlador ni runtime en esta fase.


## Addendum de revisión técnica posterior (2026-11-08)

Una segunda pasada detectó y corrigió la validación de claves no textuales en metadatos (H-01), y normalizó errores OSError del descriptor raíz en el adaptador. La prueba focal quedó en 44/44 y la regresión Python global en 470/470; Bash 62/62 y controles estáticos/instalador continuaron PASS. Ver `docs/AUDITORIA_TECNICA_B4_3B_SEGUNDA_PASADA_2026-11-08.md`.
