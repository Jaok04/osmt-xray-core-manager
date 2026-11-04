# Auditoría C-05B — Almacén permanente de informes

**Fecha:** 2026-11-04
**Resultado:** PASS dentro del alcance C-05B.
**Estado:** Aceptada formalmente por el propietario el 2026-11-04; C-05B cerrada.
**Rama:** `design/user-identity-association-v1`
**HEAD de referencia:** `2676b36403e414e9ece5e85250ce89e0b01185d3` (antes de publicar C-05A/C-05B).

## 1. Alcance auditado

- `scripts/xray_validation_store.py`
- `tests/test_xray_validation_store.py`
- `docs/IMPLEMENTACION_C05B_ALMACEN_INFORMES_2026-11-04.md`

Se verificó que el almacén no importa ni ejecuta el motor Xray, no lee el almacén de configuraciones, no descifra documentos, no carga la clave maestra, no promueve estados, no toca runtime ni ofrece borrado/edición de informes.

## 2. Controles revisados

| Control | Resultado |
|---|---|
| IDs estrictos para informe, configuración y revisión | PASS |
| Esquema JSON cerrado y rechazo de claves duplicadas | PASS |
| Diagnósticos acotados y saneamiento de patrones sensibles | PASS |
| No persistencia de configuración ni stdout/stderr | PASS |
| Directorios root:root 0700 y archivos root:root 0600 | PASS |
| Archivos regulares, hardlinks rechazados y aperturas O_NOFOLLOW | PASS |
| Directorios/archivos simbólicos rechazados | PASS |
| Escritura atómica, fsync y publicación exclusiva de informes | PASS |
| Lock exclusivo para operaciones consistentes | PASS |
| Catálogo append-only y SHA-256 de cada informe | PASS |
| Verificación de integridad en lectura/listado | PASS |
| Rechazo de archivos extra, ausentes o alterados | PASS |
| WAL con rutas acotadas y snapshots validados | PASS |
| Recuperación de WAL preparado (rollback) tras SIGKILL | PASS |
| Recuperación de WAL committed tras SIGKILL | PASS |
| No hay API de modificación o eliminación de informes | PASS |
| Sin promoción Validada ni integración de menú | PASS — límite de alcance |

## 3. Pruebas ejecutadas

- Pruebas específicas del almacén: **8/8 PASS**.
- Regresión Python combinada de C-05A y C-05B: **25/25 PASS**.
- Regresión shell de C-01/C-02, C-03, C-04A, C-04B, C-04C y smoke general: PASS.
- Compilación Python de C-05A/C-05B: PASS.
- `bash -n modules/*.sh`: PASS.
- `git diff --check`: PASS.
- Las salidas SIGKILL observadas en pruebas preexistentes C-01/C-03/C-04 y en C-05B son inyecciones deliberadas de fallo para comprobar recuperación; los scripts envolventes terminaron correctamente.

## 4. Limitaciones y responsabilidades posteriores

1. C-05B es almacenamiento, no autoridad de validación. La futura integración deberá vincular la ejecución al config_id, revisión y hash exactos.
2. No se verifica que la configuración siga existiendo al guardar el informe. La política aprobada exige que el informe sobreviva a la edición/eliminación; la comprobación de identidad/revisión antes de ejecutar y persistir se implementará en la fase de integración correspondiente.
3. No se cambia el estado de configuración ni se actualiza `last_validated_revision`.
4. No hay historial/comparación ni menú.
5. El saneamiento cubre patrones comunes; no puede garantizar la eliminación de cualquier secreto arbitrario incrustado en un diagnóstico futuro. El motor C-05A evita conservar stdout/stderr y usa mensajes acotados; futuras fuentes de diagnósticos deberán mantener esa disciplina.
6. El almacén se prueba con directorios temporales y datos sintéticos. No se creó `/var/lib/xray-manager/validation` en el sistema real.

## 5. Dictamen y aceptación

No se identificaron defectos bloqueantes dentro del alcance de persistencia C-05B. Los informes se almacenan como objetos append-only, con catálogo verificable, controles de filesystem y recuperación transaccional. El almacén permanece desacoplado del motor y del estado funcional de configuraciones.

**El propietario aceptó formalmente C-05B el 2026-11-04. La fase queda cerrada. C-05C requiere autorización independiente.**

## 6. Estado del repositorio y límites

- Publicación autorizada en la rama `design/user-identity-association-v1`.
- `main` y `Xray-Normativa/` permanecen intactas.
- Se publicarán conjuntamente los archivos aceptados de C-05A y C-05B.
- No se modificaron paquetes, servicios, certificados, puertos, firewall, configuración activa ni runtime.
- No se leyó ni utilizó la clave maestra real.


## Addendum — publicación posterior de C-05B (2026-11-04)

La referencia a `2676b36403e414e9ece5e85250ce89e0b01185d3` corresponde al HEAD base previo a la publicación y se conserva como evidencia histórica. Tras la aceptación formal, C-05B se publicó junto con C-05A en `0b0e36e53dbc58c2102805834c2ffc1a5edd6b25`; el registro de aceptación y continuidad quedó en `1815663438770a2271d769345adbc271714a6817`.

Se verificó el mismo HEAD en GitHub y `/opt/xray-manager`, con árbol limpio. La publicación fue fast-forward; `main` y `Xray-Normativa/` permanecieron intactas. C-05B queda IMPLEMENTADA, VERIFICADA, AUDITADA, ACEPTADA, PUBLICADA y SINCRONIZADA. La promoción a Validada no forma parte de C-05B y C-05C requiere autorización independiente.
