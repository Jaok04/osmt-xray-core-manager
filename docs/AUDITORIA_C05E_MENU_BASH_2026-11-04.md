# Auditoría técnica C-05E — Integración del menú Bash

**Fecha:** 2026-11-04
**Rama:** `design/user-identity-association-v1`
**HEAD base:** `ed700c1e770063f6e67c6ebaeae4652172bb2f02`
**Objeto:** auditoría de la implementación local C-05E. No incluye aceptación formal ni publicación.

## 1. Dictamen ejecutivo

La integración conecta el submenú de validación con el motor transaccional C-05C y el servicio de historial C-05D, manteniendo separadas las responsabilidades. Las opciones que carecen de contrato seguro (archivo externo y configuración activa) siguen deshabilitadas. No se detectaron defectos bloqueantes en el alcance auditado.

**Resultado:** C-05E IMPLEMENTADA, VERIFICADA Y AUDITADA LOCALMENTE; PENDIENTE DE ACEPTACIÓN FORMAL; NO PUBLICADA NI SINCRONIZADA.

## 2. Revisión de arquitectura y seguridad

- El punto de entrada es la opción `[2]` de `menu_config_profiles_backups()`; no se altera el menú principal ni la navegación de otros módulos.
- El nuevo módulo se carga desde `bin/xray-manager` y usa las funciones de UI existentes.
- La validación de una revisión guardada llama exclusivamente al CLI C-05C. No hay una segunda implementación del motor en Bash.
- `config_id` se obtiene del catálogo; la revisión se vuelve a obtener desde los metadatos y se pasa explícitamente. C-05C verifica la revisión exacta bajo sus locks.
- La confirmación ocurre antes de la validación persistente. La prueba de cancelación comprueba que el catálogo de informes permanece vacío.
- El argumento de clave maestra es solo una ruta transferida al CLI C-05C; el módulo Bash no abre ni lee el archivo.
- Historial, detalle, último informe y comparación pasan por `ValidationHistoryService` y el almacén C-05B. Se conservan validación de IDs, filtros (configuración, revisión, fechas, tipo y resultado), límites, integridad, lock y reglas de comparación.
- La CLI no crea almacenes ausentes ni corrige permisos. Para directorios incompletos, symlinks y locks ausentes falla cerrada.
- Consultas de servicio conservan la semántica de recuperación WAL preexistente: pueden completar una transacción interrumpida, pero no alteran informes ya confirmados.
- No se introdujo `eval`, shell dinámico, dependencia nueva, ruta de informe controlada por el usuario ni operación de mutación de historial.
- Las opciones externa/activa no leen rutas, no inspeccionan procesos y no consultan/modifican runtime.

## 3. Matriz de verificación ejecutada

| Verificación | Resultado |
|---|---:|
| Prueba focal C-05E (`tests/xray_validation_menu.sh`) | PASS |
| Regresión Python C-05A/B/C/D | 76/76 PASS |
| Regresión de scripts shell | 57/57 PASS |
| `tests/xray_configurations_menu.sh` | PASS |
| `tests/smoke.sh` | PASS |
| `bash -n` en entrypoint, rutas, módulos y pruebas focales | PASS |
| ShellCheck `-S error` en archivos Bash modificados | PASS |
| `install.sh --check` | PASS; no-op |
| `git diff --check` | PASS |

La regresión shell se ejecutó sobre los 57 scripts `tests/*.sh`, todos con código de salida 0; no hubo skips. La regresión Python ejecutó 76 pruebas en 2.6 segundos aproximadamente.

## 4. Cobertura focal observada

- Acceso desde el menú Configuraciones/Perfiles/Respaldos y retorno.
- Menú de validación con navegación de retorno.
- Opciones de archivo externo y configuración activa claramente no disponibles y sin efectos laterales.
- Almacén vacío: último informe `null` e historial con cero registros.
- CLI `list`, `latest`, `show` y `compare`: salida JSON comprobada con dos informes sintéticos, incluyendo comparación de revisiones distintas de una misma configuración.
- Almacén ausente: `list` devuelve cero registros sin crear el directorio.
- Cancelación explícita de validación guardada: no se escribe informe.
- Validación de sintaxis de módulos Bash y CLI Python.

La prueba positiva C-05E ejecutó el flujo completo desde el menú con una configuración sintética guardada, clave temporal y Xray real 26.10.31; verificó PASS, `promoted=true`, informe persistido y estado `valid`. No utilizó almacenes live ni clave real. La suite C-05C cubre además PASS_WITH_WARNINGS, FAIL, INCOMPLETE, revisión histórica, concurrencia y WAL.

## 5. Trazabilidad de la matriz E01–E38

La matriz del diseño es una matriz de cobertura propuesta, no una afirmación de que cada escenario se haya ejecutado individualmente. Se distinguen los escenarios probados en la integración C-05E, los que cuentan con cobertura en las regresiones C-05A/B/C/D y los que permanecen pendientes de prueba específica de interfaz.

| Casos | Estado de evidencia | Alcance de la evidencia |
|---|---|---|
| E01 | PASS | Entrada desde el menú Configuraciones/Perfiles/Respaldos y retorno.
| E02 | PARCIAL | Se probó opción 0; EOF no se probó específicamente.
| E03 | PENDIENTE | Opción inválida en el submenú.
| E04–E06 | PENDIENTE | Ausencia de Python/jq y ejecución sin root.
| E07–E09 | PENDIENTE | Catálogo vacío para selección, índice inválido y selección sin revisión desde la UI.
| E10 | PASS | Cancelación comprobada; cero informes nuevos.
| E11 | PASS | Validación positiva por menú con Xray real 26.10.31, PASS, promoción e informe persistido en almacenes temporales.
| E12–E15 | REGRESIÓN C-05C | PASS/PASS_WITH_WARNINGS/FAIL/INCOMPLETE, revisión histórica y garantías de concurrencia/revisión exacta probadas a nivel de servicio; no se repitió cada resultado por UI C-05E.
| E16 | PARCIAL | Último informe vacío comprobado; ruta con informe existente se cubre por API/CLI, no por UI.
| E17 | PASS | `latest --config-id` verificado con dos informes sintéticos.
| E18 | PASS | Historial vacío en UI.
| E19 | PENDIENTE | Navegación de paginación de UI.
| E20 | PARCIAL | Filtro por configuración verificado; filtros por revisión/resultado/fechas/tipo están disponibles en CLI, pero no todos se ejercitaron en C-05E.
| E21 | PARCIAL | CLI `show` consultado con informe sintético; presentación visual del detalle desde la UI no se recorrió.
| E22 | PENDIENTE | ID inválido/inexistente desde UI.
| E23 | PASS | Comparación de dos revisiones distintas de una configuración en CLI.
| E24 | REGRESIÓN C-05D | Rechazo de comparación entre configuraciones distintas probado en la suite de historial.
| E25 | PENDIENTE | Comparación del mismo informe consigo mismo.
| E26 | REGRESIÓN C-05B/C-05D | Integridad y rechazo de informes/catálogos manipulados probados por las suites de almacén/historial.
| E27 | PARCIAL | Almacén ausente no creado; symlink y directorio inseguro desde la CLI no repetidos en la prueba focal C-05E.
| E28 | REGRESIÓN C-05B/C-05D | Saneamiento/integridad de informes cubiertos por las suites existentes; no se creó una prueba de secretos específica del menú.
| E29–E30 | PASS | Opciones externa/activa indican no disponibles y no realizan acciones.
| E31 | PASS | Cancelación sin escritura y validación positiva append-only verificadas.
| E32 | PENDIENTE | Hashes de catálogo/informes antes y después de cada consulta no comparados explícitamente en C-05E.
| E33 | PARCIAL | Navegación desde el submenú de perfiles; no se recorrió el entrypoint principal completo.
| E34 | PASS | `bash -n` y smoke incorporan módulo/prueba.
| E35 | PASS | Regresión Python 76/76.
| E36 | PASS | Regresión shell 57/57, sin skips.
| E37 | PASS | ShellCheck severidad error y `git diff --check`.
| E38 | PASS | `install.sh --check` no-op.

**Conclusión de trazabilidad:** los criterios funcionales centrales de C-05E están demostrados y las bases C-05B/C/D tienen regresiones previas sólidas. No se declara que E03–E09, E19, E22, E25 y E32 estén ejecutados. Estos escenarios pueden incorporarse a una ampliación de pruebas antes de aceptar formalmente si el propietario lo requiere.

## 6. Hallazgo corregido durante la auditoría

La primera regresión completa detectó una expectativa obsoleta en `tests/xray_configurations_menu.sh`, que buscaba el texto antiguo «(pendiente)» en la opción que ahora está conectada. Se actualizó la aserción al nuevo texto del menú y se repitió la suite completa: 57/57 PASS. No era un defecto funcional del menú.

## 7. Limitaciones y puntos no cubiertos

- No se implementa validación de archivo externo.
- No se implementa identificación/validación de configuración realmente activa.
- Se ejecutó validación positiva de una configuración guardada desde el menú interactivo en esta VPS, usando Xray real 26.10.31, clave sintética y almacenes temporales; se obtuvo PASS, promoción y persistencia de un informe. No se aplicó la configuración ni se inició/reinició servicio.
- El menú ofrece filtros de configuración, revisión y resultado en la CLI; la UX interactiva expone filtro por configuración y paginación, mientras que la CLI mantiene filtros de revisión/resultado.
- Las consultas usan el mecanismo WAL recuperable preexistente, por lo que una consulta después de una interrupción puede terminar una recuperación pendiente.
- La ejecución de `install.sh --check` fue de solo comprobación; no se ejecutó instalación.

## 8. Límites de alcance y custodia

No se modificaron `Xray-Normativa/`, `main`, la clave maestra real, almacenes live, runtime, servicios, certificados, firewall, puertos, red ni dependencias. No se accedió a `Vps de Pruebas`. No se hizo commit, push ni sincronización. C-05F no fue iniciada.

## 9. Recomendación

La implementación satisface los criterios técnicos de C-05E dentro de los límites declarados. Se recomienda presentar el expediente al propietario para revisión y aceptación formal. No publicar ni iniciar C-05F sin autorización expresa independiente.

## Addendum de decisión del propietario — 2026-11-04

El propietario aceptó formalmente C-05E después de revisar este expediente, incluidos los estados individuales de la matriz E01–E38 y las limitaciones descritas. La auditoría queda aceptada como evidencia del alcance probado; los casos marcados PARCIAL o PENDIENTE no se reinterpretan como PASS. C-05E queda ACEPTADA. La aceptación no autoriza publicación: no se ha creado commit ni ejecutado push. C-05F permanece no autorizada y no iniciada.
