# Auditoría C-05A — Motor de validación estática y nativa

**Fecha:** 2026-11-04
**Resultado:** PASS con limitaciones de alcance documentadas.
**Estado de fase:** Aceptada formalmente por el propietario el 2026-11-04; C-05A cerrada.
**Rama:** `design/user-identity-association-v1`
**HEAD:** `2676b36403e414e9ece5e85250ce89e0b01185d3` (sin commit de C-05A).

## 1. Alcance auditado

- `scripts/xray_config_validator.py`
- `tests/test_xray_config_validator.py`
- `docs/IMPLEMENTACION_C05A_MOTOR_VALIDACION_2026-11-04.md`

Se comprobó que el motor no importe ni invoque `ConfigurationStore`, no lea la clave maestra, no acceda al almacén persistente, no escriba estados ni informes y no contenga rutas de activación, systemd o runtime.

## 2. Revisión de seguridad

| Control | Resultado |
|---|---|
| Entrada como bytes y límite de 16 MiB | PASS |
| UTF-8 estricto, JSON estricto y claves duplicadas | PASS |
| SHA-256 sobre bytes exactos recibidos | PASS |
| Binario Xray absoluto, sin symlink, regular y root-owned | PASS |
| Rechazo de hardlinks y permisos de escritura grupo/otros | PASS |
| Hash del binario leído desde descriptor abierto con O_NOFOLLOW | PASS |
| Directorio temporal 0700 y archivo 0600 | PASS |
| Ejecución nativa con argumentos separados, stdin cerrado y entorno mínimo | PASS |
| Timeout acotado | PASS |
| No persistencia de stdout/stderr ni configuración | PASS |
| No activación ni inicio de servicios | PASS |
| Sin cambios en clave maestra, runtime o infraestructura | PASS |

## 3. Revisión funcional

- Los errores estáticos bloqueantes detienen la validación nativa y producen `FAIL`.
- Ausencia/inseguridad del binario o timeout produce `INCOMPLETE`.
- Código de salida nativo distinto de cero produce `FAIL`.
- Aceptación nativa después de las comprobaciones estáticas produce `PASS`.
- El hash del contenido corresponde a los bytes recibidos, no a una serialización JSON reconstruida.
- Los espacios de nombres de etiquetas inbound/outbound se mantienen separados para evitar falsos positivos.
- Las referencias detectables a inbound, outbound y balancer se verifican sin sustituir al parser nativo.

## 4. Evidencia de pruebas

- Pruebas focales: **17/17 PASS**.
- Xray real 26.10.31: configuración sintética válida aceptada.
- Xray real 26.10.31: protocolo inexistente rechazado.
- Regresión de C-01/C-02, C-03, C-04A, C-04B, C-04C y smoke general: ejecutada satisfactoriamente.
- Python compile: PASS.
- `git diff --check`: PASS.

Los mensajes de terminación SIGKILL de las pruebas de recuperación WAL existentes corresponden a inyecciones intencionales de fallo; los scripts de prueba terminaron satisfactoriamente.

## 5. Limitaciones conocidas (no bloqueantes para C-05A)

1. No existe aún integración con el almacén independiente ni asociación persistente a ID/revisión. Se reserva para fases posteriores.
2. No se persisten informes ni se promueve el estado Validada. Se reserva para C-05B/C.
3. La compatibilidad se delega a `xray run -test`; no hay matriz local de opciones por versión.
4. `PASS_WITH_WARNINGS` está contemplado por el contrato, pero no se inventan heurísticas de advertencia. No se generan advertencias automáticamente en esta fase.
5. La validación nativa no comprueba conectividad ni comportamiento runtime.
6. El motor no ofrece aún CLI ni menú; se expone como función Python para que la integración posterior controle la procedencia y revisión exactas.

## 6. Dictamen

No se identificaron defectos bloqueantes dentro del alcance autorizado de C-05A. El motor y sus pruebas focales cumplen el límite de componente aislado. Las limitaciones descritas deben mantenerse visibles al diseñar la integración posterior; no se consideran autorización para ampliar el alcance.

**El propietario aceptó formalmente C-05A el 2026-11-04. La fase queda cerrada. C-05B requiere autorización independiente.**

## 7. Estado del repositorio y alcance

- Existen cuatro archivos nuevos de C-05A (motor, pruebas, registro de implementación y auditoría); no hay modificaciones de archivos preexistentes.
- `main` y `Xray-Normativa/` permanecen intactas.
- HEAD no cambió.
- No se realizó commit, push ni publicación.
- No se modificaron paquetes, servicios, certificados, puertos, firewall, configuración activa ni runtime.


## Addendum — publicación posterior de C-05A (2026-11-04)

El HEAD `2676b36403e414e9ece5e85250ce89e0b01185d3` citado arriba es la base histórica de la auditoría, anterior a la publicación; no es el HEAD actual. Tras la aceptación formal, C-05A se publicó junto con C-05B en `0b0e36e53dbc58c2102805834c2ffc1a5edd6b25` (commit de implementación: `0b0e36e53dbc58c2102805834c2ffc1a5edd6b25`). La actualización de continuidad se registró en `1815663438770a2271d769345adbc271714a6817`.

La publicación se verificó en `design/user-identity-association-v1` y en `/opt/xray-manager`, con árbol limpio. `main` y `Xray-Normativa/` no se modificaron. La aceptación de C-05A se mantiene limitada a su alcance auditado; C-05B fue aceptada y publicada conjuntamente en el mismo commit de implementación. C-05C requiere autorización independiente.
