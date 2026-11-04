# Auditoría técnica C-05F — Auditoría integral del subsistema de validación Xray

**Fecha:** 2026-11-04
**Estado técnico:** **PASS CON HALLAZGO MENOR Y DIVERGENCIAS NORMATIVAS DOCUMENTADAS**.
**Estado administrativo:** **ACEPTADA FORMALMENTE POR EL PROPIETARIO (2026-11-04); publicación pendiente de autorización independiente.**
**Rama:** design/user-identity-association-v1
**HEAD local y remoto:** a4f2c6356652e04206918c410ddf3f6aa3181808
**Alcance:** C-05A, C-05B, C-05C, C-05D y C-05E.
**No equivale a:** auditoría integral ni cierre de toda la Etapa 5.

## 1. Dictamen ejecutivo

Se ejecutó la auditoría transversal del subsistema C-05A–C-05E frente a los requisitos de validación aplicables de la normativa aprobada de Etapa 5.

Resultados principales:

- Regresión Python: **76/76 PASS**.
- Regresión shell: **57/57 PASS**, cero fallos y cero marcadores de skip.
- Pruebas focales C-05E, menú de configuraciones y smoke: PASS.
- Sintaxis Bash en los archivos shell inventariados: PASS.
- ShellCheck severidad error sobre todos los archivos shell inventariados: PASS.
- ShellCheck severidad warning sobre los siete archivos Bash de integración focales: 0 advertencias.
- Compilación Python: PASS.
- install.sh --check: PASS, no modificó el sistema.
- git diff --check: PASS.
- Recorrido integral A→E con Xray real y almacenes temporales: PASS.
- Cuatro validaciones nativas concurrentes sobre una misma configuración/revisión: PASS.
- Custodia normativa: 13/13 documentos normativos con homólogo coinciden por SHA-256.
- Se detectó un defecto menor en la detección de un enlace simbólico roto en un componente padre de la ruta CLI del almacén. No se corrigió, por la condición aprobada de separar auditoría y correcciones.

El subsistema cumple técnicamente los flujos implementados y probados. Sin embargo, la auditoría confirma dos divergencias respecto de la normativa: la validación de archivo externo y la validación de configuración activa aparecen deshabilitadas en el menú. La prueba de funcionamiento runtime también sigue pendiente en la propia especificación. Estas brechas no se han ocultado ni se han clasificado como PASS.

**Recomendación:** aceptar el resultado técnico con el hallazgo menor registrado, y autorizar por separado su corrección y la planificación de las brechas normativas. No cerrar Etapa 5.

## 2. Línea base, custodia y entorno

### 2.1 Git

- Rama: design/user-identity-association-v1.
- HEAD local: a4f2c6356652e04206918c410ddf3f6aa3181808.
- HEAD remoto: mismo SHA.
- Upstream: origin/design/user-identity-association-v1.
- Los únicos cambios locales son documentos de diseño, matriz, auditoría y continuidad C-05F.
- No se modificó código fuente ni pruebas.
- No se creó commit ni se hizo push.
- main permanece intacta.

### 2.2 Normativa

Se comparó cada archivo de Xray-Normativa/ con su homólogo bajo /root/Xray_Manager_Documentacion_Final_2026-10-31:

- **13/13 coincidencias SHA-256**.
- Xray-Normativa/README.md no tiene homólogo en el respaldo; se mantiene como documento de custodia del repositorio.
- No se modificó ningún archivo de Xray-Normativa/.

### 2.3 Entorno

Versiones observadas sin instalar ni actualizar nada:

- Python 3.12.3.
- Bash 5.2.21.
- jq 1.7.
- ShellCheck 0.9.0.
- Xray 26.10.31, binario /usr/local/bin/xray.

En la entrada y al cierre:

- /var/lib/xray-manager/configurations: ausente.
- /var/lib/xray-manager/validation: ausente.
- /etc/xray-manager/keys/master.key: existe, pero **no se abrió, leyó ni utilizó**.
- Las pruebas de escritura usaron directorios temporales, claves sintéticas y configuraciones sintéticas.
- No se modificaron runtime, servicio, certificados, firewall, puertos, red, paquetes ni dependencias.
- No se tocó Vps de Pruebas.

## 3. Evidencia de regresión

| Verificación | Resultado |
|---|---:|
| Python C-05A/B/C/D | **76/76 PASS** |
| Scripts tests/*.sh | **57/57 PASS** |
| Marcadores de skip en regresión shell | 0 |
| Prueba focal tests/xray_validation_menu.sh | PASS |
| tests/xray_configurations_menu.sh | PASS |
| tests/smoke.sh | PASS |
| py_compile scripts/*.py tests/test_*.py | PASS |
| bash -n sobre archivos shell inventariados y install.sh | PASS |
| ShellCheck -S error sobre todos los archivos shell inventariados | PASS |
| ShellCheck -S warning sobre siete archivos Bash C-05E focales | 0 advertencias |
| install.sh --check | PASS, no-op |
| git diff --check | PASS |
| Escaneo de eval, os.system y shell=True en componentes C-05 | Sin coincidencias |

La exploración ShellCheck de severidad warning sobre todos los archivos shell se intentó con un límite de 180 segundos y expiró antes de finalizar. No se declara resultado global para ese nivel. La verificación de severidad error sí finalizó correctamente para todos los archivos; los siete archivos focales de C-05E no presentan advertencias. La auditoría C-05D había documentado cuatro advertencias preexistentes en tres pruebas ajenas a C-05; no se modificaron.

## 4. Pruebas adicionales de interfaz y CLI

Se añadieron comprobaciones temporales, sin cambiar archivos del proyecto:

| Escenario | Resultado |
|---|---:|
| E02 — EOF retorna sin bucle | PASS |
| E03 — opción inválida en menú | PASS |
| E04 — Python ausente | PASS |
| E05 — jq ausente | PASS |
| E06 — ejecución sin root | PASS |
| E07 — catálogo de configuraciones vacío | PASS |
| E08 — índice de configuración inválido | PASS |
| E09 — configuración sin revisión/contenido | PASS |
| E19 — navegación de paginación | PASS |
| E20 — filtro UI por configuración | PASS |
| E21 — detalle válido e inválido en UI | PASS |
| E22 — ID de informe inválido | PASS |
| E23 — comparación UI entre revisiones | PASS |
| E25 — comparación de un informe consigo mismo | PASS |
| E27 — almacén bajo ruta simbólica existente | PASS, rechazado |
| E32 — hashes antes/después de consultas CLI | PASS, sin cambios |
| E33 — entrypoint → menú de configuraciones → validación → retorno → salida | PASS |

Las opciones de archivo externo y configuración activa se recorrieron y confirmaron que no leen archivos ni consultan/modifican runtime.

## 5. Integración transversal A→E

### 5.1 Recorrido de extremo a extremo

Se ejecutó un escenario aislado con configuración y clave sintéticas:

1. Crear configuración independiente vacía.
2. Escribir una configuración SOCKS/Freedom sintética como revisión r000001.
3. Ejecutar C-05C sobre esa revisión exacta con Xray 26.10.31.
4. Confirmar resultado PASS, informe persistido y promoción a Validada.
5. Consultar informe por detalle e historial C-05D.
6. Editar el contenido y crear r000002.
7. Confirmar que la nueva revisión queda Borrador/no validada y que last_validated_revision conserva r000001.
8. Validar r000002 y comparar los dos informes.
9. Eliminar la configuración sintética.
10. Consultar ambos informes después de eliminar la configuración.

Resultado: **PASS**. Dos informes permanecen consultables después de eliminar el registro de configuración. Ambas respuestas de validación declararon configuration_applied=false y service_started=false. No se inició daemon ni se abrió listener de servicio.

### 5.2 Concurrencia

Se ejecutaron cuatro validaciones nativas simultáneas de la misma configuración y revisión en almacenes temporales.

Resultado: **PASS**. Se generaron cuatro IDs únicos, el catálogo verificó integridad, todos los informes conservaron la misma identidad/revisión y el estado final quedó Validada.

### 5.3 Integridad y solo lectura

- Se verificó que los comandos CLI list/latest/show/compare no alteran los bytes del catálogo ni de los informes.
- Se verificó rechazo de ID inválido y ruta de almacén simbólica cuyo destino existe.
- Las pruebas focales y de regresión cubrieron integridad SHA-256, archivos inesperados, symlinks, hardlinks, permisos, locks, WAL preparado/committed y recuperación.
- Las consultas ordinarias no escriben informes. El acceso al almacén utiliza el lock y el mecanismo de recuperación WAL del componente C-05B; una recuperación real de un WAL pendiente es una operación de recuperación, no una consulta puramente pasiva.

## 6. Hallazgos

### H-01 — Detección incompleta de symlink roto en componente padre

<badge color="warning">Severidad baja</badge> <badge color="danger">FAIL reproducido</badge>

**Ubicación:** scripts/xray_validation_history.py:193–196, con retorno de almacén vacío en líneas 215–225.

**Reproducción:**

1. Crear un directorio temporal.
2. Crear un enlace simbólico roto <tmp>/dangling que apunte a un destino inexistente.
3. Ejecutar xray_validation_history.py --store <tmp>/dangling/validation list.

**Resultado observado:** el CLI devuelve código 0 y un historial vacío (total: 0), en vez de rechazar el componente simbólico.

**Causa:** la comprobación usa component.exists() and component.is_symlink(). exists() devuelve falso para el enlace roto, por lo que el enlace padre no se detecta. La ruta final tampoco es el propio enlace simbólico.

**Impacto:** una ruta configurada que atraviese un symlink roto puede interpretarse como un almacén legítimamente ausente. No se observó escritura, reparación ni lectura de datos fuera del directorio temporal; el impacto principal es una validación incompleta de la ruta y una respuesta vacía potencialmente engañosa.

**Corrección recomendada (no aplicada):** inspeccionar cada componente con lstat() y rechazar stat.S_ISLNK, incluyendo enlaces rotos, antes de la rama que interpreta el almacén como ausente. Añadir pruebas para symlink directo, ancestro symlink válido y ancestro symlink roto.

**Estado:** abierto; requiere autorización separada para corrección.

## 7. Divergencias normativas y asuntos pendientes

### D-01 — Validación de archivo externo

La normativa Etapa 5 §4.1 contempla validar un archivo externo legible, sin importarlo, modificarlo ni aplicarlo. C-05E muestra explícitamente la opción como no disponible y no lee el archivo.

**Clasificación:** DIVERGENCIA NORMATIVA confirmada. No se intentó implementar durante C-05F.

### D-02 — Validación de configuración activa

La normativa Etapa 5 §4.1 contempla comprobar el servicio y comparar configuración guardada/ejecutada cuando sea posible, declarar incertidumbre y no reiniciar/modificar. C-05E muestra la opción como no disponible y no consulta runtime.

**Clasificación:** DIVERGENCIA NORMATIVA confirmada. No se intentó consultar ni modificar runtime durante C-05F.

### D-03 — Prueba runtime independiente

La normativa YAML declara que la prueba runtime debe ser independiente de la validación estática y mantiene mechanism: pending. C-05A/C-05E prueban validación estática/nativa mediante Xray run -test; eso no demuestra que el servicio pueda cargar y operar la configuración.

**Clasificación:** PENDIENTE NORMATIVO/DISEÑO. No se simuló como funcionalidad implementada.

### D-04 — Exclusión de historial en respaldos

La normativa exige excluir el historial de validación de los respaldos. La auditoría C-05F no incluye la implementación integral de backup/restore de Etapa 5; el inventario de módulos de respaldo disponible no ofrece una ruta de integración C-05 para verificar el comportamiento completo.

**Clasificación:** pendiente fuera del alcance C-05F; debe auditarse en la fase de backup/restore de Etapa 5. No se afirma conformidad.

### D-05 — Filtros de historial

La CLI admite filtros por configuración, revisión, fechas, tipo y resultado. La interfaz Bash expone filtro por configuración, detalle, comparación y paginación, pero no presenta controles UI para todos los filtros CLI.

**Clasificación:** cobertura API PASS; cobertura UI PARCIAL. No bloquea el contrato de consulta CLI, pero la diferencia de experiencia queda documentada.

## 8. Limitaciones de la auditoría

- No se probaron validación externa ni activa, porque están deshabilitadas y su implementación no fue autorizada.
- No se ejecutó prueba runtime real del servicio.
- No se auditó el flujo completo de backup/restore de Etapa 5.
- El análisis global de ShellCheck warning expiró por tiempo; el nivel error sí se completó y los archivos Bash C-05E focales reportaron cero warnings.
- La prueba Xray real utiliza configuración SOCKS/Freedom sintética y almacenes temporales; no equivale a prueba sobre una configuración productiva.
- No se modificó ningún hallazgo.

## 9. Estado administrativo y recomendación

**C-05F: IMPLEMENTADA COMO AUDITORÍA, EJECUTADA, DOCUMENTADA Y ACEPTADA FORMALMENTE POR EL PROPIETARIO (2026-11-04).**

No se creó commit ni push. El expediente, matriz final y addendas de continuidad permanecen locales en la rama autorizada.

Se recomienda:

1. La aceptación formal C-05F fue otorgada por el propietario el 2026-11-04, considerando expresamente H-01 y D-01–D-05.
2. La corrección H-01 fue autorizada y ejecutada posteriormente; su evidencia se registra en docs/CORRECCION_H01_RUTAS_SYMLINK_C05F_2026-11-04.md.
3. Las divergencias D-01/D-02 y el mecanismo D-03 requieren trabajos independientes con diseño y autorización propios.
4. Mantener backup/restore como parte de la auditoría posterior de Etapa 5.

La aceptación de C-05F no cerrará Etapa 5. La Etapa 5 y la Etapa 2 permanecen ABIERTAS.

## 10. Custodia final

- Código y pruebas: sin cambios durante C-05F.
- main: intacta.
- Xray-Normativa/: intacta; 13/13 hashes canónicos coincidentes.
- Clave maestra real: no leída ni utilizada.
- Almacenes live de configuraciones y validaciones: ausentes antes y después.
- Runtime/servicios/infraestructura: sin cambios.
- VPS de pruebas: no tocada.
- Dependencias: sin instalación ni actualización.
- Commit/push: no realizados.


## 11. Aceptación formal del propietario — 2026-11-04

El propietario respondió afirmativamente a la solicitud de aceptación formal de C-05F. Se registra **C-05F ACEPTADA FORMALMENTE**, incluyendo el dictamen técnico PASS, el hallazgo menor H-01 y las divergencias/asuntos D-01–D-05 documentados en este expediente y en la matriz.

Esta aceptación no constituye autorización para corregir H-01, implementar validación externa/activa, resolver D-03/D-04/D-05, cerrar Etapa 5/Etapa 2, crear commit, hacer push ni sincronizar GitHub. Cada una de esas acciones conserva su autorización independiente.

## 12. Addendum posterior — remediación H-01 (2026-11-04)

Tras la aceptación formal de C-05F, el propietario autorizó expresamente corregir H-01, añadir pruebas y ejecutar la regresión correspondiente. La corrección se implementó en scripts/xray_validation_history.py mediante inspección lstat() de todos los componentes de la ruta absoluta. Se añadieron H39–H42 para symlink directo, ancestro válido, ancestro roto y ruta ordinaria inexistente. Resultado: suite focal 42/42 PASS; regresión Python 80/80 PASS; shell 57/57 PASS; compilación Python, sintaxis Bash, ShellCheck severidad error, ShellCheck warning focal, install.sh --check y git diff --check PASS. El hallazgo histórico se conserva para trazabilidad, pero queda CORREGIDO Y VERIFICADO. Evidencia: docs/CORRECCION_H01_RUTAS_SYMLINK_C05F_2026-11-04.md. D-01–D-05 no cambian; Etapa 5 y Etapa 2 siguen abiertas.
