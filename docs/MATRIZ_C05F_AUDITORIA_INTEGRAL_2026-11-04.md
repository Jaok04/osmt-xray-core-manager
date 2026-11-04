# Matriz C-05F — Auditoría integral del subsistema de validación Xray

**Fecha:** 2026-11-04
**Estado:** MATRIZ PROPUESTA — pendiente de aprobación y ejecución.
**Alcance:** C-05A–C-05E. No representa auditoría completa de Etapa 5.

## Convenciones

- `PENDIENTE DE EJECUCIÓN`: estado de planificación; no afirma resultado.
- `PASS / FAIL / PARCIAL / PENDIENTE / NO APLICABLE / DIVERGENCIA NORMATIVA`: estados que se asignarán tras la ejecución.
- Las pruebas históricas se citan como antecedentes; no sustituyen su reejecución durante C-05F.
- Toda prueba de escritura usa exclusivamente directorios temporales y datos sintéticos.

## A. Línea base, custodia e inventario

| ID | Requisito/criterio | Fuente normativa o regla | Componentes/archivos | Evidencia o prueba prevista | Estado inicial |
|---|---|---|---|---|---|
| F01 | Rama, HEAD, upstream, árbol y SHA remoto identificados antes de auditar | AGENTS §3 | Git `/opt/xray-manager` | `git status`, `rev-parse`, `ls-remote`, divergencia | PENDIENTE DE EJECUCIÓN |
| F02 | Línea base normativa Markdown/YAML verificada por SHA-256 contra respaldo | AGENTS §2.1 | `Xray-Normativa/05_Configuraciones_Perfiles/*`, respaldo | Comparación SHA-256; conservar README sin homólogo como custodia | PENDIENTE DE EJECUCIÓN |
| F03 | Inventario C-05A–E completo, incluidos módulos, CLI, menú, pruebas y documentos | Regla auditoría integral §3 | `scripts/`, `modules/`, `bin/`, `config/`, `tests/`, `docs/` | Inventario de archivos, funciones y referencias | PENDIENTE DE EJECUCIÓN |
| F04 | `main`, normativa, secretos, almacenes live, runtime y VPS de pruebas permanecen fuera del alcance | AGENTS §§2.0, 4, 7 | Repositorio y VPS de desarrollo | Inspección read-only de estado; sin abrir secretos ni datos live | PENDIENTE DE EJECUCIÓN |
| F05 | Versiones y herramientas disponibles registradas sin instalación/actualización | AGENTS §§4, 7 | Python, Bash, jq, ShellCheck, Xray | `--version`/`command -v`, solo lectura | PENDIENTE DE EJECUCIÓN |

## B. Correspondencia con la normativa de validación

| ID | Requisito/criterio | Fuente normativa | Componente/archivo | Evidencia o prueba prevista | Estado inicial |
|---|---|---|---|---|---|
| F06 | Opción de validación integrada en el menú principal aprobado, retorno al padre y errores no cierran gestor | Etapa 5 §2 | `modules/profiles.sh`, `modules/xray_validation_menu.sh`, `bin/xray-manager` | Recorrido interactivo desde entrypoint y retorno | PENDIENTE DE EJECUCIÓN |
| F07 | Menú de validación ofrece las operaciones y retorno especificados | Etapa 5 §4 | `modules/xray_validation_menu.sh` | Verificar opciones, textos, navegación y EOF | PENDIENTE DE EJECUCIÓN |
| F08 | Validación guardada identifica configuración y revisión exactas | Etapa 5 §4.1 | C-05C, C-05E | Configuración con varias revisiones; selección y confirmación de revisión | PENDIENTE DE EJECUCIÓN |
| F09 | Validación externa acepta ruta legible, sin importar, modificar ni aplicar | Etapa 5 §4.1 | Menú C-05E | Revisar opción actual y su comportamiento | DIVERGENCIA NORMATIVA PREVISTA: actualmente deshabilitada; confirmar en auditoría |
| F10 | Validación activa comprueba servicio/relación guardado-ejecutado cuando sea posible y declara incertidumbre sin modificar/reiniciar | Etapa 5 §4.1 | Menú C-05E y detección runtime | Revisar opción actual; no consultar runtime real | DIVERGENCIA NORMATIVA PREVISTA: actualmente deshabilitada; confirmar en auditoría |
| F11 | Prueba de funcionamiento es independiente de validación estática y no asume segunda instancia del daemon | Etapa 5 §4.1 | Contrato C-05A–E | Inspección de diseño/documentación y límites | PENDIENTE DE DECISIÓN: mecanismo normativo figura pendiente |
| F12 | Informe permanece disponible tras editar/eliminar configuración | Etapa 5 §4.1 | C-05B/C/D | Guardar informe, editar y borrar fixture; consultar informe | PENDIENTE DE EJECUCIÓN |
| F13 | Historial consultable por archivo/configuración, fecha y tipo | Etapa 5 §4.1 | C-05D/E | Probar filtros CLI y UX disponible; comparar contra campos normativos | PENDIENTE DE EJECUCIÓN |
| F14 | Informes permiten inspección de errores/advertencias y comparación de resultados | Etapa 5 §4.1 | C-05D/E | Detalle y comparación de informes sintéticos | PENDIENTE DE EJECUCIÓN |
| F15 | Estado Validada solo se asigna tras validación estática obligatoria satisfactoria | Etapa 5 §5 | C-05C | PASS, PASS_WITH_WARNINGS, FAIL, INCOMPLETE y checks obligatorios | PENDIENTE DE EJECUCIÓN |
| F16 | Editar Validada crea Borrador nuevo y conserva la Validada anterior | Etapa 5 §3, §5 | `scripts/xray_configurations.py`, C-05C | Validar, editar, verificar revisiones y puntero previo | PENDIENTE DE EJECUCIÓN |
| F17 | Estados Validada/Aplicada/Anterior no se confunden; C-05 no declara Aplicada sin verificación runtime | Etapa 5 §5 | C-05C/E | Inspección de metadatos y rutas de promoción | PENDIENTE DE EJECUCIÓN |
| F18 | Historial de validación queda excluido de respaldos | Etapa 5 §8 y YAML `exclude_all_history` | C-05B/C y backup format | Inspección de exclusiones/manifest; prueba temporal si existe cobertura segura | PENDIENTE DE EJECUCIÓN |

## C. C-05A — motor estático y nativo

| ID | Requisito/criterio | Componente | Evidencia o prueba prevista | Estado inicial |
|---|---|---|---|---|
| F19 | JSON estricto: bytes inválidos, claves duplicadas, constantes no válidas y raíz incorrecta rechazados | `xray_config_validator.py` | Casos positivos/negativos focales | PENDIENTE DE EJECUCIÓN |
| F20 | Estructura y parámetros requeridos se comprueban sin sustituir parser nativo | C-05A | Fixtures incompletos y válidos | PENDIENTE DE EJECUCIÓN |
| F21 | Tipos/valores, tags, namespaces y referencias detectables se validan correctamente | C-05A | Duplicados inbound/outbound, referencias desconocidas y casos límite | PENDIENTE DE EJECUCIÓN |
| F22 | Compatibilidad nativa se comprueba con el binario Xray configurado y salida controlada | C-05A | Xray real disponible; fixture sintético | PENDIENTE DE EJECUCIÓN |
| F23 | Binario inseguro, symlink, hardlink, ausente o timeout falla cerrado como INCOMPLETE | C-05A | Pruebas de filesystem y timeout en tmp | PENDIENTE DE EJECUCIÓN |
| F24 | Hash representa los bytes exactos evaluados; stdout/stderr/secretos no se persisten | C-05A/B | Comparar SHA-256 y revisar informe saneado | PENDIENTE DE EJECUCIÓN |
| F25 | Límites de tamaño, timeout y entradas inválidas se aplican | C-05A | Pruebas de límites y errores | PENDIENTE DE EJECUCIÓN |

## D. C-05B — almacenamiento e integridad

| ID | Requisito/criterio | Componente | Evidencia o prueba prevista | Estado inicial |
|---|---|---|---|---|
| F26 | Esquema estricto, IDs, tipos y tamaños validados | `xray_validation_store.py` | Entradas válidas/ inválidas, claves desconocidas/duplicadas | PENDIENTE DE EJECUCIÓN |
| F27 | Informes append-only y catálogo con SHA-256 verificable | C-05B | Intentos de alteración, omisión y archivos extra | PENDIENTE DE EJECUCIÓN |
| F28 | Permisos y filesystem seguros: root ownership/modes, regular files, symlink/hardlink y O_NOFOLLOW | C-05B | Pruebas temporales de permisos y enlaces | PENDIENTE DE EJECUCIÓN |
| F29 | Escritura atómica, fsync, lock y exclusión de escritores concurrentes | C-05B | Inyección de fallos y concurrencia | PENDIENTE DE EJECUCIÓN |
| F30 | WAL preparado revierte; WAL committed completa; rutas/snapshots se validan | C-05B/C-05D | SIGKILL controlado en temporales y recuperación | PENDIENTE DE EJECUCIÓN |
| F31 | Saneamiento de diagnósticos y ausencia de configuración/secretos/stdout/stderr | C-05A/B | Patrones sintéticos sensibles y revisión de informes | PENDIENTE DE EJECUCIÓN |
| F32 | Consultas ordinarias no mutan informes ni catálogo; se identifica explícitamente recuperación WAL | C-05B/D | Hashes antes/después de operaciones read-only | PENDIENTE DE EJECUCIÓN |

## E. C-05C — orquestación y promoción

| ID | Requisito/criterio | Componente | Evidencia o prueba prevista | Estado inicial |
|---|---|---|---|---|
| F33 | La revisión exacta se resuelve y verifica antes de validar; hash de contenido coincide | `xray_config_promotion.py`, `xray_configurations.py` | Revisiones múltiples y hash deliberadamente discrepante | PENDIENTE DE EJECUCIÓN |
| F34 | Solo PASS/PASS_WITH_WARNINGS elegibles promueven; FAIL/INCOMPLETE no promueven | C-05C | Matriz de cuatro resultados y checks obligatorios | PENDIENTE DE EJECUCIÓN |
| F35 | Revisión histórica produce informe sin marcar como Validada la revisión actual | C-05C | Validación de revisión antigua | PENDIENTE DE EJECUCIÓN |
| F36 | Edición posterior crea Borrador y conserva puntero validado anterior | C-05C | Flujo de edición tras promoción | PENDIENTE DE EJECUCIÓN |
| F37 | Transacción informe+metadatos recupera estados prepared/committed y mantiene orden de locks | C-05C | SIGKILL en puntos documentados, recuperación y concurrencia | PENDIENTE DE EJECUCIÓN |
| F38 | Estado no se promueve con metadatos incoherentes, ID incorrecto o hash de informe no coincidente | C-05C | Mutaciones sintéticas controladas | PENDIENTE DE EJECUCIÓN |
| F39 | C-05 no aplica configuración ni inicia/reinicia Xray | C-05C/E | Revisión de llamadas y prueba de no-efecto en entorno temporal | PENDIENTE DE EJECUCIÓN |

## F. C-05D — historial y comparación

| ID | Requisito/criterio | Componente | Evidencia o prueba prevista | Estado inicial |
|---|---|---|---|---|
| F40 | Historial: orden, filtros, fechas con zona horaria, límites y paginación | `xray_validation_history.py` | Casos H01–H13 y límites adicionales | PENDIENTE DE EJECUCIÓN |
| F41 | Detalle/latest funcionan con informes presentes, ausentes y configuración eliminada | C-05D | Casos H14–H18 y flujo tras borrado temporal | PENDIENTE DE EJECUCIÓN |
| F42 | Comparación detecta igualdad, cambios, errores, warnings, checks, hash y Xray | C-05D | Casos H19–H28 | PENDIENTE DE EJECUCIÓN |
| F43 | Comparación rechaza configuraciones diferentes e IDs inválidos | C-05D | H28–H29 | PENDIENTE DE EJECUCIÓN |
| F44 | Integridad/symlink/archivos inesperados/WAL/concurrencia/saneamiento se mantienen en consultas | C-05D | H30–H38 | PENDIENTE DE EJECUCIÓN |
| F45 | CLI JSON tiene códigos de salida, validación de argumentos y límites consistentes | C-05D | `list/latest/show/compare`, entradas inválidas y stdout/stderr | PENDIENTE DE EJECUCIÓN |

## G. C-05E — integración Bash y experiencia de uso

| ID | Requisito/criterio | Componente | Evidencia o prueba prevista | Estado inicial |
|---|---|---|---|---|
| F46 | Entry point carga el módulo y opción [2] llega al submenú correcto | `bin/xray-manager`, `profiles.sh` | Recorrido completo desde entrypoint | PENDIENTE DE EJECUCIÓN |
| F47 | Retorno, EOF, opción inválida y errores no rompen el menú padre | `xray_validation_menu.sh` | Casos E02/E03 y errores de CLI | PENDIENTE DE EJECUCIÓN |
| F48 | Dependencias ausentes y ejecución sin root se gestionan con mensaje seguro | C-05E | Casos E04–E06 | PENDIENTE DE EJECUCIÓN |
| F49 | Catálogo vacío, índice inválido y revisión ausente se manejan correctamente | C-05E | Casos E07–E09 | PENDIENTE DE EJECUCIÓN |
| F50 | Cancelación no escribe; validación positiva presenta identidad, resultado y promoción exactos | C-05E | E10/E11 con almacenes temporales y Xray disponible | PENDIENTE DE EJECUCIÓN |
| F51 | Último informe e historial vacíos/poblados se presentan correctamente | C-05E | E16–E20, incluida paginación y filtros UI | PENDIENTE DE EJECUCIÓN |
| F52 | Detalle, ID inválido, compare same-report y compare different revisions se comportan correctamente | C-05E/D | E21–E25, incluyendo huecos previos E22/E25 | PENDIENTE DE EJECUCIÓN |
| F53 | Opciones externa/activa son transparentes, no ejecutan operaciones no implementadas ni aparentan éxito | C-05E | E29/E30 y F09/F10 | PENDIENTE DE EJECUCIÓN |
| F54 | Consultas y validación mantienen append-only; hashes antes/después y WAL se interpretan correctamente | C-05B/D/E | E31/E32 y F32 | PENDIENTE DE EJECUCIÓN |
| F55 | `XRAY_MANAGER_VALIDATION_DIR` y paths configurables se aplican de forma consistente | `config/paths.sh`, módulos y CLIs | Rutas temporales alternativas, relativas/inseguras y ausentes | PENDIENTE DE EJECUCIÓN |
| F56 | No hay `eval`, inyección de argumentos, quoting defectuoso ni fuga de datos en la UI | Bash/CLI | Revisión estática y entradas adversariales | PENDIENTE DE EJECUCIÓN |

## H. Integración transversal A→E

| ID | Requisito/criterio | Componentes | Evidencia o prueba prevista | Estado inicial |
|---|---|---|---|---|
| F57 | Flujo completo: selección guardada → revisión exacta → validación → informe → promoción → consulta UI/CLI | A/B/C/D/E | Escenario sintético end-to-end | PENDIENTE DE EJECUCIÓN |
| F58 | Informe histórico sobrevive a edición y eliminación de la configuración origen | B/C/D | Crear informe, editar/borrar fixture y consultar historial | PENDIENTE DE EJECUCIÓN |
| F59 | Comparación entre revisiones de una misma config funciona; comparación entre configs distintas falla cerrada | D/E | Dos revisiones + segunda config sintética | PENDIENTE DE EJECUCIÓN |
| F60 | Informes, catálogo, metadatos y revisiones mantienen integridad cruzada | B/C/D | Correlación IDs, revision, hash, validation_id y timestamps | PENDIENTE DE EJECUCIÓN |
| F61 | Dos operaciones concurrentes no mezclan identidad, revisión, informe ni estado | B/C/D | Validaciones/consultas concurrentes en almacenes temporales | PENDIENTE DE EJECUCIÓN |
| F62 | Reinicio de proceso conserva informes e historial y no requiere catálogo de configuraciones para consultarlos | B/D | Guardar, terminar proceso, consultar desde proceso nuevo | PENDIENTE DE EJECUCIÓN |
| F63 | Estado Aplicada no se infiere de Validada y ninguna operación C-05 modifica runtime | C/D/E | Inspección y verificación no-efecto | PENDIENTE DE EJECUCIÓN |
| F64 | Historial de validación no se incorpora a respaldos | B y subsistema backup | Inspección de formato/selección de backup temporal | PENDIENTE DE EJECUCIÓN |

## I. Calidad, regresión y expediente

| ID | Requisito/criterio | Evidencia o prueba prevista | Estado inicial |
|---|---|---|---|
| F65 | Pruebas focales A, B, C, D y E ejecutadas y resultados reproducibles | Conteo por suite, salida y códigos de retorno | PENDIENTE DE EJECUCIÓN |
| F66 | Regresión Python C-05A/B/C/D completa ejecutada | `unittest` discovery; registrar total real | PENDIENTE DE EJECUCIÓN |
| F67 | Regresión `tests/*.sh` completa ejecutada sin skips no explicados | Registrar cada script, RC y skips | PENDIENTE DE EJECUCIÓN |
| F68 | Sintaxis, compilación, ShellCheck severidad error e instalador check no-op | `py_compile`, `bash -n`, ShellCheck, `install.sh --check` | PENDIENTE DE EJECUCIÓN |
| F69 | Documentación de interfaces, rutas, datos, seguridad, fallos, recuperación y límites coincide con el código | Revisión cruzada de docs C-05A–E | PENDIENTE DE EJECUCIÓN |
| F70 | Hallazgos, riesgos, decisiones pendientes y estados no verificados quedan explícitos | Informe C-05F y matriz final | PENDIENTE DE EJECUCIÓN |
| F71 | No se declara cierre de Etapa 5 por aceptar C-05F | `PROJECT_STATE.md` y punto de control | PENDIENTE DE EJECUCIÓN |

## J. Huecos conocidos que la auditoría debe resolver con evidencia

| ID | Hueco heredado | Fuente | Acción de auditoría | Estado inicial |
|---|---|---|---|---|
| G01 | E02 solo probó opción 0; EOF no probado | Auditoría C-05E | Probar EOF y retorno seguro | PENDIENTE |
| G02 | E03 opción inválida no probada | Auditoría C-05E | Probar entrada inválida y permanencia en menú | PENDIENTE |
| G03 | E04–E06 dependencias ausentes/no-root no probados | Auditoría C-05E | Simular entorno controlado sin alterar host | PENDIENTE |
| G04 | E07–E09 catálogo vacío/índice/revisión UI no probados | Auditoría C-05E | Fixtures temporales y entradas límite | PENDIENTE |
| G05 | E19 paginación UI no probada | Auditoría C-05E | Poblar historial sintético y recorrer páginas | PENDIENTE |
| G06 | E21 detalle visual UI parcial | Auditoría C-05E | Recorrer detalle desde UI | PENDIENTE |
| G07 | E22 ID inválido desde UI no probado | Auditoría C-05E | Probar ID inválido sin efectos laterales | PENDIENTE |
| G08 | E25 comparación del informe consigo mismo no probada | Auditoría C-05E | Verificar semántica y salida same-report | PENDIENTE |
| G09 | E27 symlink/directorio inseguro no repetidos desde CLI en C-05E | Auditoría C-05E | Verificar rechazo sin reparación automática | PENDIENTE |
| G10 | E32 hashes antes/después de cada consulta no comparados explícitamente | Auditoría C-05E | Capturar hashes de catálogo/informes en todas las consultas | PENDIENTE |
| G11 | E33 entrypoint principal completo no recorrido | Auditoría C-05E | Recorrer desde `bin/xray-manager` con entrada controlada | PENDIENTE |
| G12 | E04–E09, E19, E22, E25 y E32 fueron reconocidos como pendientes; no se deben convertir en PASS por regresiones de API | Auditoría C-05E | Mantener separación UI/API y asociar evidencia exacta | PENDIENTE |
| G13 | Validación externa y activa deshabilitadas, aunque aparecen en la normativa | Etapa 5 §4 / C-05E | Confirmar divergencia y documentar impacto; no implementar | PENDIENTE DE DECISIÓN |
| G14 | Mecanismo seguro de prueba runtime figura pendiente en normativa | Etapa 5 §4.1 YAML `runtime_test.mechanism` | Confirmar que no se simula como disponible | PENDIENTE DE DECISIÓN |
| G15 | La UI no expone necesariamente todos los filtros de historial que ofrece la CLI | Etapa 5 §4.1 / auditoría C-05E | Contrastar por campo y documentar brecha | PENDIENTE |

## Resultado de la matriz

La matriz contiene 71 criterios F01–F71 y 15 huecos G01–G15. Todos están pendientes de ejecución o decisión. Esta matriz es un plan de auditoría, no evidencia de conformidad ni dictamen. La matriz final conservará los identificadores y añadirá resultado, referencia de evidencia, entorno, fecha y hallazgo/acción para cada caso.

---

## Registro final de ejecución C-05F — 2026-11-04

La columna «Estado inicial» de las tablas anteriores conserva la condición previa a ejecutar la auditoría. La siguiente tabla es el resultado final y prevalece para el dictamen.

| Criterio | Resultado final | Evidencia |
|---|---|---|
| F01 | PASS | Rama, HEAD, upstream y SHA remoto coinciden; cambios locales limitados a documentos C-05F |
| F02 | PASS | 13/13 hashes normativos coinciden; README sin homólogo identificado |
| F03 | PASS | Inventario de componentes, fuentes, módulos, CLI, menú y pruebas |
| F04 | PASS | main/normativa intactas; live stores ausentes; clave real no leída; VPS pruebas no tocada |
| F05 | PASS | Versiones registradas; sin instalación/actualización |
| F06 | PASS | Entry point completo probado: principal → configuraciones → validación → retorno → salida |
| F07 | PASS | Opciones y navegación recorridas; EOF y opción inválida comprobados |
| F08 | PASS | Revisión exacta comprobada en prueba transversal |
| F09 | DIVERGENCIA NORMATIVA | Opción externa explícitamente deshabilitada |
| F10 | DIVERGENCIA NORMATIVA | Opción activa explícitamente deshabilitada |
| F11 | PENDIENTE NORMATIVO | El mecanismo runtime sigue pending en YAML; no equivale a xray run -test |
| F12 | PASS | Informes permanecen después de editar y eliminar configuración sintética |
| F13 | PASS (API) / PARCIAL (UI) | CLI filtra configuración/revisión/fecha/tipo/resultado; UI filtra configuración |
| F14 | PASS | Detalle, errores/warnings y comparación probados |
| F15 | PASS | PASS/PASS_WITH_WARNINGS promueven; FAIL/INCOMPLETE no promueven |
| F16 | PASS | Edición crea revisión Borrador y preserva puntero validado anterior |
| F17 | PASS | Validada no se confunde con Aplicada; respuesta declara no aplicado |
| F18 | PENDIENTE FUERA DE ALCANCE | Exclusión de historial en backup se reserva a auditoría backup/restore Etapa 5 |
| F19–F25 | PASS | 76 pruebas Python y Xray real en entorno temporal |
| F26–F32 | PASS | Almacén, integridad, permisos, WAL, saneamiento y hash read-only; symlink roto queda como H-01 |
| F33–F39 | PASS | Identidad exacta, elegibilidad, revisión histórica, WAL y no aplicación |
| F40–F45 | PASS | H01–H38, filtros, paginación, detalle, comparación y CLI |
| F46 | PASS | Entry point y submenús completos |
| F47 | PASS | EOF, opción inválida y retorno |
| F48 | PASS | Python/jq ausentes y no-root |
| F49 | PASS | Catálogo vacío, índice inválido y configuración sin revisión |
| F50 | PASS | Cancelación sin persistencia y validación positiva con Xray |
| F51 | PARCIAL | Historial vacío/poblado y paginación UI; último informe poblado comprobado por CLI, no repetido en UI |
| F52 | PASS | Detalle UI válido/inválido; comparación UI same-report y entre revisiones |
| F53 | PASS | Opciones externa/activa no ejecutan operación ni consultan runtime |
| F54 | PASS | Append-only y hashes CLI antes/después sin cambios |
| F55 | FAIL — H-01 | Symlink existente rechazado; symlink roto en componente padre no se detecta |
| F56 | PASS | Sin eval, os.system ni shell=True; shellcheck error PASS |
| F57 | PASS | Recorrido transversal A→E completo |
| F58 | PASS | Informe histórico permanece tras edición/eliminación |
| F59 | PASS | Revisiones distintas misma config comparadas; configs distintas rechazadas por regresión |
| F60 | PASS | Correlación ID/revisión/hash/informe verificada |
| F61 | PASS | Cuatro validaciones concurrentes, cuatro IDs únicos e integridad del catálogo |
| F62 | PASS | Reinicio de proceso cubierto por H38 |
| F63 | PASS | Sin aplicación ni inicio de servicio |
| F64 | PENDIENTE FUERA DE ALCANCE | Exclusión de historial en backup se reserva a auditoría backup/restore Etapa 5 |
| F65 | PASS | Pruebas focales A–E ejecutadas |
| F66 | PASS | 76/76 pruebas Python |
| F67 | PASS | 57/57 scripts shell; cero fallos y cero skips |
| F68 | PASS CON NOTA | py_compile, bash -n, shellcheck error e install check; warning global expiró, focal C-05E cero warnings |
| F69 | PASS | Expedientes C-05A–E y requisitos de validación contrastados |
| F70 | PASS | H-01 y D-01–D-05 documentados con límites y recomendación |
| F71 | PASS | Etapa 5 permanece abierta |

### Resultado de huecos heredados

| Hueco | Resultado final | Evidencia |
|---|---|---|
| G01 | PASS | EOF probado |
| G02 | PASS | Opción inválida probada |
| G03 | PASS | Python/jq ausentes y no-root |
| G04 | PASS | Catálogo vacío, índice inválido y configuración sin revisión |
| G05 | PASS | Paginación UI |
| G06 | PASS | Detalle UI válido e inválido |
| G07 | PASS | ID inválido UI/CLI |
| G08 | PASS | Comparación de informe consigo mismo |
| G09 | PARCIAL + H-01 | Symlink a destino existente rechazado; symlink roto padre aceptado erróneamente |
| G10 | PASS | Hashes antes/después de list/latest/show/compare iguales |
| G11 | PASS | Entry point completo recorrido |
| G12 | PASS | Evidencia UI separada de CLI/API |
| G13 | DIVERGENCIA CONFIRMADA | Validación externa deshabilitada frente a normativa |
| G14 | PENDIENTE NORMATIVO | Mecanismo runtime marcado pending en YAML |
| G15 | PARCIAL | CLI dispone de filtros fecha/tipo; UI solo filtro de configuración |
| G16 | HALLAZGO H-01 | Reproducción de symlink roto en componente padre de la ruta CLI |

### Totales

- Criterios F: 71 evaluados.
- Huecos G: 16 registrados (G01–G16).
- Regresión Python: 76/76 PASS.
- Regresión shell: 57/57 PASS.
- Hallazgos técnicos: 1 menor (H-01).
- Divergencias normativas confirmadas: 2 (D-01, D-02).
- Asuntos pendientes de diseño normativo: 1 (D-03).
- Requisitos fuera del alcance de C-05F: 2 (F18/F64).
- Sin correcciones de código durante la auditoría.
- Aceptación formal del propietario: pendiente.


## Registro administrativo final — aceptación formal (2026-11-04)

**C-05F: ACEPTADA FORMALMENTE POR EL PROPIETARIO.** El propietario confirmó afirmativamente la aceptación del dictamen técnico, H-01 y D-01–D-05. Los resultados F01–F71 y G01–G16 permanecen tal como fueron evaluados; esta decisión administrativa no convierte los hallazgos, divergencias o pendientes en PASS.

La corrección H-01, implementación de validación externa/activa, mecanismo runtime, auditoría backup/restore, ampliaciones UI, commit, push y sincronización requieren decisiones/autorizaciones separadas. Etapa 5 y Etapa 2 permanecen ABIERTAS.

## Addendum de remediación H-01 — 2026-11-04

H-01, registrado originalmente en F55/G09/G16 como fallo/parcial, fue corregido bajo autorización posterior del propietario. La inspección de la ruta ahora utiliza lstat() y rechaza enlaces simbólicos rotos y válidos en cualquier componente. Pruebas nuevas H39–H42: PASS. Suite historial 42/42; regresión Python 80/80; shell 57/57; verificaciones estáticas y install.sh --check: PASS. El estado histórico de la auditoría no se reescribe; el seguimiento de remediación queda CERRADO — CORREGIDO Y VERIFICADO. Ver docs/CORRECCION_H01_RUTAS_SYMLINK_C05F_2026-11-04.md. D-01–D-05 permanecen sin cambios.
