# B4.3-B — revisión adversarial de segunda pasada

**Fecha:** 2026-11-08
**Dictamen:** PASS CON LIMITACIONES para el prototipo fixture.
**Independencia:** segunda pasada del mismo ciclo de implementación; NO equivale a auditoría independiente.

## 1. Superficie revisada

- `scripts/xray_runtime_evidence_store.py`
- `scripts/xray_runtime_supervisor_evidence.py`
- `scripts/xray_runtime_launcher_prototype.py`
- `tests/test_xray_runtime_evidence_store.py`
- `tests/test_xray_runtime_launcher_prototype.py`
- diseño B4.3-B y contrato de directorios B4.3.

## 2. Controles adversariales comprobados

| Riesgo | Control observado | Resultado |
|---|---|---|
| Cierre accidental del FD del caller | API duplica el descriptor y cierra sólo su copia | PASS |
| Herencia del ancla | copia CLOEXEC/no heredable; hijo cierra FD antes del gate | PASS |
| Reemplazo de la ruta nominal | operaciones internas relativas al descriptor abierto | PASS |
| Symlink en componentes | `O_NOFOLLOW|O_DIRECTORY` por componente | PASS |
| Drift de owner/group/mode | `fstat` por inode, rechazo sin reparación | PASS |
| Marcador fixture falso o simbólico | apertura `O_NOFOLLOW`, tipo/owner/modo/contenido exactos | PASS |
| Replay/sobrescritura | publicación exclusiva sin reemplazo y `st_nlink=1` | PASS |
| Registro con campos adicionales | esquema y conjunto de claves estrictos en verificación FD | PASS |
| Exposición a identidad de servicio | padre `root:root 0700`, registro `0600` | PASS |
| Fallo de creación/verificación | gate no recibe token; hijo terminado y recolectado | PASS |
| Fallback silencioso a B4.1 | selector explícito y error terminal | PASS |
| Descriptor de raíz filtrado al ejecutable | auditoría `/proc/self/fd` del proceso fixture | PASS |

## 3. Observaciones y límites residuales

1. **Ancla inicial:** la API FD no puede probar quién abrió originalmente el descriptor. El llamador es responsable de entregar un FD confiable. El prototipo abre la raíz fixture después de validarla; una integración de Manager debe establecer y conservar esa autoridad en el límite de confianza apropiado.
2. **Carreras con actor root:** `O_NOFOLLOW` y `dir_fd` eliminan la resolución por rutas mutables y las redirecciones por symlink durante cada apertura. No pretenden proteger frente a un actor root hostil capaz de mutar simultáneamente todos los directorios; el modelo de confianza del host/supervisor sigue siendo root confiable.
3. **Evidencia huérfana ante fallo posterior:** si la publicación completa pero falla la verificación posterior, el registro puede permanecer para diagnóstico. El gate no se libera. La política de retención/limpieza de registros incompletos semánticamente debe definirse antes de integración live.
4. **Semántica:** `prepared_before_exec` no acredita exec, configuración cargada, proceso activo ni systemd. No se debe promover a `running` ni `active` con esta evidencia.
5. **Cobertura de Xray:** el nuevo selector se prueba con un ejecutable fixture; la validación Xray 26.10.31 existente pertenece al camino B4.1. La prueba combinada `persistent_b43` + Xray real queda pendiente y no debe ejecutarse como daemon.
6. **Integración:** no hay conexión con `modules/xray_service.sh`, unidad systemd, R-05, menú, backend live, `/etc/xray` ni VPS Pruebas.

## 4. Verificación ejecutada

- B4.3-A/B focal: 43/43 PASS.
- Python global: 469/469 PASS.
- Bash: 62/62 PASS.
- `compileall`, `py_compile`, `bash -n`, ShellCheck global `-S error`, `install.sh --check` y `git diff --check`: PASS.

## 5. Dictamen

El contrato fixture B4.3-B cumple los controles de anclaje FD, rechazo de symlink/drift, persistencia, segregación, gate fail-closed y ausencia de fallback en los escenarios probados. La implementación se considera **apta para revisión independiente**, no para integración live. La revisión independiente y la autorización de despliegue siguen pendientes.
