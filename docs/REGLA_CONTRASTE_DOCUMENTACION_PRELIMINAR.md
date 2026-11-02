# Regla obligatoria de contraste con la documentación preliminar aprobada

**Proyecto:** Xray Core Manager  
**Vigencia:** permanente, desde su incorporación al proyecto.  
**Autoridad:** instrucción expresa del propietario.

## 1. Fuente normativa obligatoria

La línea base funcional de cada etapa es la documentación preliminar aprobada que se conserva en la VPS en:

`/root/Xray_Manager_Documentacion_Final_2026-10-31`

Esta documentación debe consultarse directamente antes de implementar cualquier etapa, subetapa, módulo, protocolo, modalidad o funcionalidad. Los documentos del repositorio, el código y las pruebas describen el estado del desarrollo; no sustituyen ni modifican por sí solos la línea base aprobada.

## 2. Contraste previo obligatorio

Antes de comenzar una implementación se debe:

1. Localizar y leer la especificación preliminar aplicable, incluidas sus decisiones, alcance, exclusiones, dependencias y criterios de aceptación.
2. Inspeccionar el estado real de la rama autorizada, la VPS, el código, los catálogos, las pruebas y la documentación técnica pertinente.
3. Comparar los requisitos aprobados uno por uno con lo existente.
4. Clasificar los hallazgos, al menos, como: conforme, implementado, verificado, incompleto, ausente, divergente, pendiente de validación o no verificable.
5. Identificar expresamente cualquier diferencia entre la especificación y el proyecto en desarrollo.
6. Entregar al propietario un informe de contraste antes de editar o implementar.

No se debe confundir una opción listada en un menú o catálogo con una funcionalidad implementada, probada o aceptada. Tampoco se deben declarar etapas completas por la finalización de una parte de su alcance.

## 3. Mejoras y cambios de alcance: autorización previa

Se permiten mejoras a la propuesta original, pero no se incorporan automáticamente. Si el contraste revela una mejora, actualización técnica, ampliación, sustitución, eliminación o cambio de comportamiento, se debe:

- describir el problema o la oportunidad;
- explicar la diferencia respecto de la documentación aprobada;
- justificar el beneficio y exponer riesgos, dependencias e impacto;
- identificar los documentos, módulos, pruebas y etapas afectados;
- presentar la propuesta al propietario y solicitar autorización expresa.

**No se modifica ni amplía el alcance aprobado hasta recibir autorización expresa.** No constituyen autorización el silencio, la continuidad de una conversación, una aprobación dada para otra tarea ni la mera presencia de una implementación previa.

## 4. Secuencia obligatoria de trabajo

1. Recuperar el estado real del proyecto y de GitHub/VPS.
2. Consultar la documentación preliminar aprobada en la ruta indicada.
3. Ejecutar y documentar el contraste completo de la etapa o tarea.
4. Presentar discrepancias y mejoras propuestas.
5. Esperar la autorización expresa del propietario para el alcance concreto.
6. Actualizar la decisión o el diseño técnico aprobado cuando corresponda.
7. Implementar solo lo autorizado y ejecutar las pruebas pertinentes.
8. Actualizar los documentos de continuidad y el historial.
9. Publicar los cambios aprobados en la rama autorizada de GitHub y sincronizar la VPS, verificando ambos destinos.

Si la documentación normativa no está disponible, su versión no puede identificarse o existe una contradicción que afecte requisitos, se debe detener el trabajo y solicitar aclaración. No se permite completar vacíos mediante suposiciones.

## 5. Jerarquía y control documental

Esta regla complementa `AGENTS.md` y se aplica a todas las etapas del proyecto. La documentación preliminar aprobada determina el alcance funcional; las decisiones complementarias solo pueden modificarlo cuando el propietario las autorice expresamente y queden registradas. La especificación original no se reescribe retroactivamente para ocultar diferencias: se conserva y se registra la decisión complementaria con su fecha y alcance.

Cualquier IA o colaborador que retome el proyecto debe leer esta regla y cumplirla antes de proponer o ejecutar una implementación.
