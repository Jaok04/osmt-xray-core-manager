# B4.3-B — segunda revisión técnica adversarial

**Fecha:** 2026-11-08
**Dictamen:** PASS CON LIMITACIONES para el prototipo fixture, después de una corrección menor.
**Naturaleza:** revisión adicional realizada en la misma sesión/agente; no constituye certificación ni auditoría externa independiente.
**Rama:** `design/user-identity-association-v1`.

## 1. Alcance revisado

Se releyó desde cero el estado Git, el contrato B4.3, el almacén B4.3-A, el adaptador B4.3-B, el supervisor y las pruebas. Se inspeccionaron:

- `scripts/xray_runtime_evidence_store.py`
- `scripts/xray_runtime_supervisor_evidence.py`
- `scripts/xray_runtime_launcher_prototype.py`
- `scripts/xray_runtime_directory_contract.py`
- `tests/test_xray_runtime_evidence_store.py`
- `tests/test_xray_runtime_launcher_prototype.py`
- `docs/IMPLEMENTACION_B4_3B_SUPERVISOR_EVIDENCIA_FIXTURE_2026-11-08.md`
- `docs/AUDITORIA_B4_3B_ADAPTADOR_EVIDENCIA_FIXTURE_2026-11-08.md`

No se accedió ni modificó VPS Pruebas. No se ejecutó systemd real ni se inició un daemon Xray.

## 2. Controles confirmados por inspección

| Área | Evaluación |
|---|---|
| Raíz anclada | FD duplicado; `fstat` root:root 0711; no se vuelve a resolver la raíz por ruta dentro del almacén FD |
| Marcador | `O_NOFOLLOW`, tipo regular, owner/group/modo/contenido exactos |
| Layout | recorrido por `dir_fd`; `O_DIRECTORY|O_NOFOLLOW`; `fstat` de todos los componentes del contrato, incluidos state y runtime |
| Ownership | caller conserva su FD; helper cierra sólo la copia duplicada |
| Herencia | FD no heredable; hijo lo cierra antes de esperar el gate |
| Registro | `root:root 0600`, regular, `st_nlink=1`, tamaño acotado y conjunto exacto de claves en verificación FD |
| Publicación | temporal exclusivo, escritura completa, `fsync`, link sin reemplazo, unlink temporal y `fsync` del directorio |
| Replay | InvocationID única; colisión existente rechazada sin sobrescritura |
| Gate | creación y verificación preceden al token; excepción provoca terminación y recolección del hijo |
| Backend | `persistent_b43` explícito; `legacy_b41` sigue predeterminado; no hay fallback implícito |
| Evidencia | estado `prepared_before_exec`; no se promueve a proceso activo ni estado systemd |

## 3. Hallazgo detectado y corrección

**H-01 — claves de metadatos no textuales producían `AttributeError` no controlado.**

La validación de metadatos llamaba `key.lower()` antes de comprobar que todas las claves fueran cadenas. Una entrada con clave entera causaba `AttributeError`, en lugar del error de dominio `EvidenceStoreError`.

Corrección aplicada:

- `scripts/xray_runtime_evidence_store.py`: rechazo explícito de claves que no sean `str` antes de comparar campos prohibidos.
- `scripts/xray_runtime_supervisor_evidence.py`: normalización de errores `OSError` al inspeccionar el descriptor raíz como `SupervisorEvidenceError`, preservando el comportamiento fail-closed del supervisor.
- `tests/test_xray_runtime_evidence_store.py`: prueba negativa para claves no textuales y cierre correcto del FD del test.

**Estado H-01: CORREGIDO Y PROBADO.** No se encontraron otros defectos bloqueantes dentro del alcance fixture revisado.

## 4. Resultados de regresión después de la corrección

| Validación | Resultado |
|---|---:|
| Focal B4.3-A/B | 44/44 PASS |
| Python global (`unittest discover`) | 470/470 PASS |
| Suites Bash (`tests/*.sh`) | 62/62 PASS |
| `compileall` | PASS |
| `py_compile` de módulos y pruebas B4.3-B | PASS |
| `bash -n` global | PASS |
| ShellCheck global `-S error` | PASS |
| `install.sh --check` | PASS; no modificó el sistema |
| `git diff --check` | PASS |

Las suites Bash 61 y 62 ejecutaron validaciones Xray 26.10.31 de configuraciones VLESS/VMess en archivos temporales. Esto no representa una prueba del selector `persistent_b43` con Xray real ni un daemon activo.

## 5. Límites y riesgos que siguen abiertos

1. **Autoridad del ancla:** el almacén puede validar el inode y el layout recibido, pero no autentica por sí solo al proceso que abrió el FD. El Manager deberá entregar un descriptor cuya autoridad ya esté establecida.
2. **Actor root hostil:** el modelo asume root confiable. Los controles de dirfd/O_NOFOLLOW no pretenden defenderse de un root hostil con capacidad de mutar concurrentemente todo el árbol.
3. **Fallo posterior a publicación:** si el registro se publica y falla la verificación posterior, puede quedar evidencia persistente huérfana semánticamente. El gate sigue cerrado. Retención y reconciliación deben diseñarse antes de producción.
4. **Durabilidad:** se hace `fsync` del archivo y del directorio de evidencia. La creación previa del árbol de directorios fixture no constituye una transacción durable de creación del layout; el layout live deberá administrarse y persistirse mediante el Manager/systemd.
5. **Cobertura de proceso:** el selector `persistent_b43` se prueba con un ejecutable fixture controlado. No se ha validado aún la combinación de este selector con `xray run -test` real.
6. **Producción:** no hay integración con `modules/xray_service.sh`, R-05, menú, systemd real, backend live, `/etc/xray`, certificados ni VPS Pruebas.

## 6. Dictamen

**PASS CON LIMITACIONES — FIXTURE ONLY.** El hallazgo menor encontrado se corrigió y la regresión completa quedó verde. B4.3-B puede pasar a revisión externa/independiente y al diseño de la integración mínima siguiente. No debe integrarse directamente en producción ni interpretarse como evidencia de que Xray está ejecutándose.

La siguiente tarea recomendada es diseñar el puente mínimo de integración del Manager que permita probar el flujo de extremo a extremo sin habilitar todavía acciones live. Cualquier creación de cuentas, unidad, escritura en `/etc/xray`, apertura de puertos, solicitud ACME o arranque de daemon requiere autorización específica.
