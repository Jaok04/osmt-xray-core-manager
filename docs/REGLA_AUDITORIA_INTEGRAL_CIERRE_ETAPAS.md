# Regla obligatoria de auditoría integral y cierre de etapas

**Proyecto:** Xray Core Manager
**Vigencia:** permanente desde su aprobación e incorporación al repositorio.
**Autoridad:** instrucción expresa del propietario.
**Aplicación:** todas las etapas, subetapas, módulos, submódulos, componentes y entregables del proyecto.

## 1. Principio no negociable

**Ninguna etapa puede declararse TERMINADA o COMPLETADA mientras no se haya realizado y documentado una auditoría integral de todos y cada uno de sus puntos, subpuntos, módulos, submódulos y componentes internos.**

La finalización de una funcionalidad individual, la presencia de código, la aprobación de un módulo, una suite de pruebas satisfactoria, la publicación en GitHub o la sincronización de la VPS no equivalen al cierre de la etapa completa.

El cierre de un módulo no cierra automáticamente la etapa a la que pertenece. Del mismo modo, no se puede inferir que los componentes no mencionados están completos.

## 2. Contraste obligatorio con la línea base aprobada

La auditoría integral debe partir de la documentación preliminar aprobada que se conserva en:

`/root/Xray_Manager_Documentacion_Final_2026-10-31`

Se debe cumplir también, sin excepción, la regla descrita en `docs/REGLA_CONTRASTE_DOCUMENTACION_PRELIMINAR.md`:

1. Consultar directamente la documentación preliminar aplicable.
2. Identificar todos los requisitos, puntos, subpuntos, flujos, opciones, módulos, exclusiones, dependencias y criterios de aceptación de la etapa.
3. Contrastar cada elemento con la implementación real, las pruebas, los documentos técnicos y la evidencia disponible en la rama autorizada y en la VPS.
4. No sustituir la fuente normativa por resúmenes, memoria de conversaciones, catálogos, código o decisiones técnicas no aprobadas.
5. Toda diferencia, mejora o ampliación debe documentarse y someterse a autorización expresa antes de cambiar el alcance.

Si la fuente normativa no está disponible, es ambigua o presenta contradicciones relevantes, el cierre queda bloqueado hasta resolverlas con el propietario.

## 3. Inventario y trazabilidad exhaustiva

Antes de auditar, construir un inventario completo de la etapa a partir de la especificación aprobada. Cada requisito y componente debe tener un identificador trazable, aunque la documentación original no lo proporcione; los identificadores añadidos deben ser referencias de auditoría y no alterar el requisito.

La matriz de trazabilidad debe cubrir, según corresponda:

- etapa, subetapa, punto y subpunto normativo;
- módulo, submódulo, componente, función, menú, flujo y modalidad relacionada;
- comportamiento esperado y criterios de aceptación;
- archivo(s), interfaz(es), datos y dependencias que materializan el requisito;
- documento(s) de diseño y documentación técnica;
- pruebas unitarias, de integración, regresión, seguridad y validación operativa aplicables;
- evidencia verificable, fecha, entorno y resultado;
- limitaciones, riesgos, dependencias y decisiones aprobadas;
- estado individual y acción pendiente.

No se admite una auditoría basada únicamente en una lista general de funciones o en una muestra de componentes. Todos los elementos del inventario deben aparecer en la matriz y recibir una conclusión explícita.

## 4. Auditoría técnica de cada punto y módulo interno

Para cada punto, subpunto, módulo, submódulo o componente se debe verificar y documentar, en la medida en que aplique:

1. **Requisitos y comportamiento:** correspondencia exacta con el alcance aprobado, entradas, salidas, reglas y casos límite.
2. **Diseño:** responsabilidades, separación de capas, interfaces, dependencias, decisiones y compatibilidad.
3. **Implementación:** archivos y funciones reales; ausencia de opciones meramente decorativas, rutas incompletas o funciones simuladas presentadas como reales.
4. **Datos y persistencia:** esquemas, validación, integridad, transacciones, concurrencia, migraciones, recuperación y aislamiento.
5. **Seguridad:** secretos, permisos, validación de entradas, exposición de argumentos/logs, manejo de errores y límites de confianza.
6. **Errores y recuperación:** fallos previsibles, estados parciales, interrupciones, rollback y mensajes al usuario.
7. **Integración:** interacción con los demás módulos, menú, catálogo, servicios, runtime y componentes externos que correspondan.
8. **Pruebas:** casos positivos, negativos, límites, regresión y pruebas operativas que sean necesarias. Diferenciar pruebas reales, mocks, fixtures, simulaciones y pruebas no ejecutadas.
9. **Documentación técnica:** diseño, configuración, interfaces, procedimientos, restricciones, dependencias, operación y mantenimiento suficientes para que otro desarrollador pueda comprender y mantener el componente.
10. **Evidencia:** comandos, resultados, logs saneados, referencias de commit y entorno que permitan reproducir o revisar las conclusiones.

No se debe marcar un componente como auditado si faltan la inspección de su implementación o la evidencia correspondiente. Si una prueba no es aplicable, debe justificarse; si no pudo ejecutarse, debe registrarse como pendiente/no verificada, nunca como PASS.

## 5. Estados individuales obligatorios

Cada requisito y componente debe clasificarse, como mínimo, con uno de estos estados:

- **CONFORME:** coincide con el requisito aprobado.
- **IMPLEMENTADO:** existe la implementación, sin que ello implique que esté verificada.
- **VERIFICADO:** las pruebas pertinentes se ejecutaron y existe evidencia.
- **DOCUMENTADO:** su documentación técnica está completa y corresponde al comportamiento real.
- **INCOMPLETO:** existe parcialmente, pero no cubre todo el requisito.
- **AUSENTE:** no está implementado.
- **DIVERGENTE:** su comportamiento o diseño no coincide con la línea base.
- **NO VERIFICADO:** no existe evidencia suficiente o la prueba no pudo ejecutarse.
- **NO APLICABLE:** solo cuando exista justificación técnica y trazabilidad explícita.
- **PENDIENTE DE DECISIÓN:** requiere resolución o autorización del propietario.

Los estados no son intercambiables. IMPLEMENTADO no significa VERIFICADO; VERIFICADO no significa DOCUMENTADO; y ninguno de ellos significa ACEPTADO.

## 6. Criterios de bloqueo del cierre

La etapa no puede pasar a TERMINADA/COMPLETADA cuando ocurra cualquiera de estas condiciones:

- existen requisitos, puntos, subpuntos o componentes internos sin inventariar;
- hay componentes que no fueron auditados individualmente;
- falta documentación técnica de uno o más componentes;
- existen requisitos ausentes, incompletos o divergentes;
- hay pruebas aplicables sin ejecutar o evidencia insuficiente;
- hay defectos, riesgos o dependencias que impiden cumplir el alcance;
- hay decisiones pendientes que afectan comportamiento, arquitectura, seguridad o aceptación;
- no existe una matriz de trazabilidad completa y un informe final de auditoría;
- la documentación de continuidad no refleja el resultado real.

Una excepción, exclusión o limitación solo podrá dejar de bloquear el cierre si la documentación normativa la permite o el propietario la autoriza expresamente, con alcance, impacto y riesgo registrados. La autorización debe ser específica; no se presume por silencio ni por aceptación de otro módulo.

## 7. Documentación técnica exigida para el cierre

Cada punto y módulo interno debe tener documentación técnica suficiente y actualizada. La profundidad depende de su complejidad, pero debe permitir comprender qué hace, cómo lo hace, cómo se integra, cómo se configura, cómo se valida, cómo falla y cómo se mantiene.

Como mínimo, el expediente de cierre de la etapa debe incluir:

- inventario completo de requisitos y componentes;
- matriz de trazabilidad requisito → diseño → implementación → pruebas → evidencia;
- documento técnico por módulo o componente, o una sección inequívoca que lo documente;
- matriz de pruebas con resultados, entorno y limitaciones;
- registro de defectos, divergencias, riesgos y decisiones;
- informe de auditoría integral con conclusión por elemento;
- evidencia de revisión de integración y regresión de la etapa completa;
- registro de aceptación formal del propietario.

Los documentos deben estar versionados en el repositorio y formar parte del paquete de continuidad. No basta con que el conocimiento exista únicamente en el chat o en la memoria de una IA.

## 8. Puerta formal de cierre de etapa

El cierre debe seguir este orden:

1. Congelar el alcance de auditoría tomando la versión aprobada de la documentación preliminar.
2. Construir y revisar el inventario exhaustivo.
3. Auditar cada requisito y cada componente interno.
4. Corregir únicamente los defectos autorizados y volver a probar los elementos afectados.
5. Completar la documentación técnica de todos los puntos y módulos.
6. Ejecutar la regresión e integración de la etapa completa.
7. Elaborar el informe de auditoría y la matriz final de trazabilidad.
8. Presentar al propietario los resultados, limitaciones y cualquier excepción solicitada.
9. Obtener aceptación formal expresa del propietario para cerrar la etapa.
10. Actualizar PROJECT_STATE.md, docs/PUNTO_CONTROL_ACTUAL.md, docs/CONTINUIDAD_DEL_PROYECTO.md y HISTORY.md; actualizar AGENTS.md si cambia una regla permanente.
11. Publicar la documentación y los cambios aprobados en la rama autorizada, verificar GitHub y sincronizar la VPS.

No se puede omitir un paso por razones de rapidez o porque una parte del producto ya esté funcionando.

## 9. Distinción entre cierre de módulo y cierre de etapa

Se permite declarar un módulo como IMPLEMENTADO, VERIFICADO, DOCUMENTADO o ACEPTADO de forma individual si su alcance y evidencia lo justifican. Sin embargo, el estado de la etapa seguirá siendo EN DESARROLLO/ABIERTA hasta superar la puerta formal de cierre descrita aquí.

Por tanto, el cierre técnico individual de VMess no significa que la Etapa 2 esté terminada: la auditoría integral de todos los protocolos, opciones, flujos y componentes internos de Etapa 2 debe realizarse antes de cerrar esa etapa.

## 10. Aplicación a estados históricos

Esta regla no altera retroactivamente el contenido de decisiones o aceptaciones históricas. Sin embargo, cualquier declaración de etapa completada que se utilice como referencia vigente debe contar con evidencia documental de auditoría integral conforme a esta regla. Si el expediente histórico no cubre todos los puntos internos, se debe realizar y documentar una auditoría complementaria antes de usar esa etapa como ejemplo de cierre integral o dar por cumplida una dependencia que requiera ese nivel de evidencia.

## 11. Carácter obligatorio y continuidad

Esta regla es permanente y vinculante para el propietario, cualquier IA, desarrollador o colaborador que trabaje en el proyecto. Debe leerse junto con:

- `AGENTS.md`;
- `docs/REGLA_CONTRASTE_DOCUMENTACION_PRELIMINAR.md`;
- `docs/CONTINUIDAD_DEL_PROYECTO.md`;
- `PROJECT_STATE.md`;
- `docs/PUNTO_CONTROL_ACTUAL.md`.

Si una instrucción, un resumen o un plan de trabajo contradice esta regla, se debe detener el cierre, exponer la contradicción y pedir aclaración. No se puede rebajar ni ignorar esta condición por conveniencia.
