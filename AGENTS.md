# Instrucciones para agentes de IA — Xray Core Manager

## 1. Propósito y alcance

Este archivo establece las reglas obligatorias para cualquier IA o colaborador que analice, mantenga o desarrolle Xray Core Manager. Su objetivo es permitir que el trabajo continúe de forma segura aunque se pierda el chat anterior.

Lee este archivo antes de analizar o modificar el proyecto. Después consulta PROJECT_STATE.md y docs/PUNTO_CONTROL_ACTUAL.md.

## 2. Fuentes oficiales y jerarquía

- Repositorio: https://github.com/Jaok04/xray-core-manager
- Rama de desarrollo autorizada: design/user-identity-association-v1
- Rama main: protegida por instrucción del propietario; no modificarla.
- VPS de desarrollo: /opt/xray-manager
- Documentación funcional normativa aprobada y versionada: `Xray-Normativa/`. Copia maestra original de respaldo en la VPS: `/root/Xray_Manager_Documentacion_Final_2026-10-31`.

La documentación normativa define QUÉ debe hacer el producto. El código, las pruebas y la documentación técnica describen CÓMO se ha implementado. No conviertas una decisión técnica en un requisito funcional aprobado sin autorización del usuario.

Orden para resolver discrepancias:
1. Instrucciones explícitas y recientes del propietario.
2. Documentación normativa aprobada en la ruta indicada.
3. Decisiones aprobadas registradas en los documentos de continuidad.
4. Documentación técnica y código existente.
5. Hipótesis: nunca tratarlas como decisiones.

Si una ampliación técnica contradice o amplía la especificación normativa, conserva la implementación existente sin extenderla y registra la discrepancia como pendiente de ratificación. No reescribas silenciosamente la especificación.

## 2.0 Custodia inmutable de la documentación normativa

`Xray-Normativa/` contiene la documentación maestra normativa aprobada. **Ningún agente o colaborador puede modificar, corregir, reformatear, renombrar, mover, eliminar o sustituir sus archivos sin consentimiento previo, explícito y específico del propietario.** La autorización para implementar código, corregir documentación técnica o publicar cambios no autoriza a modificar la normativa. Si se detecta un error, ambigüedad o mejora, conservar el original y presentar una propuesta separada; esperar consentimiento expreso. Toda modificación autorizada debe quedar justificada y registrada en `HISTORY.md`.

## 2.1 Regla obligatoria: contrastar con la documentación preliminar aprobada

Antes de implementar cualquier etapa, subetapa, módulo, protocolo, modalidad o funcionalidad, es obligatorio contrastar el alcance y el estado real del proyecto con la documentación preliminar aprobada ubicada en `Xray-Normativa/` dentro de la rama autorizada del repositorio; la copia original `/root/Xray_Manager_Documentacion_Final_2026-10-31` se conserva como respaldo en la VPS. Debe consultarse desde `Xray-Normativa/` y contrastarse por SHA-256 con el respaldo cuando esté disponible; no basta con recordar su contenido ni con revisar únicamente el código, el catálogo o los resúmenes de continuidad.

Procedimiento vinculante:
1. Identificar en la documentación preliminar la etapa, requisitos, alcance, decisiones, exclusiones, dependencias y criterios aplicables.
2. Contrastar punto por punto esos elementos con el código, pruebas, configuración y documentación técnica existentes en la rama autorizada y en la VPS.
3. Registrar qué está conforme, implementado, verificado, incompleto, ausente, divergente, no verificado o contradice la referencia. Una entrada de catálogo no equivale a una función implementada.
4. Presentar el resultado del contraste antes de proponer cambios.
5. Si se detectan mejoras, ampliaciones, correcciones de diseño o cambios respecto de lo aprobado, explicar motivo, impacto, alternativas y archivos/áreas afectados, y solicitar autorización expresa del propietario antes de incorporarlos.
6. No implementar una mejora ni cambiar silenciosamente el alcance normativo. El silencio, una aprobación de otra tarea o la existencia de código no constituyen autorización para un cambio nuevo.
7. Tras la autorización, actualizar primero el diseño/decisión correspondiente cuando proceda y luego implementar exclusivamente el alcance aprobado.

La documentación preliminar aprobada es la línea base funcional. Las mejoras están permitidas, pero solo después del contraste y de la autorización expresa. Si el archivo o la ruta no están disponibles, hay contradicciones sin resolver o no puede determinarse qué versión fue aprobada, detener la implementación y pedir aclaración.

Documento operativo: `docs/REGLA_CONTRASTE_DOCUMENTACION_PRELIMINAR.md`.

## 2.2 Regla obligatoria: auditoría integral y cierre de etapas

**Ninguna etapa puede declararse TERMINADA/COMPLETADA sin una auditoría integral y documentación técnica de todos sus puntos, subpuntos, módulos, submódulos y componentes internos.** Cerrar un módulo, pasar pruebas, publicar código o sincronizar la VPS no cierra la etapa.

Antes de proponer el cierre de una etapa, es obligatorio:
1. Consultar la documentación preliminar aprobada en `Xray-Normativa/` y aplicar la regla 2.1.
2. Construir un inventario exhaustivo de todos los requisitos y componentes internos de la etapa.
3. Mantener una matriz de trazabilidad requisito → diseño → implementación → pruebas → evidencia.
4. Auditar individualmente cada punto y módulo: comportamiento, diseño, implementación, datos/persistencia, seguridad, errores/recuperación, integración, pruebas, documentación técnica y evidencia aplicables.
5. Documentar explícitamente los estados de cada elemento; nunca inferir que algo está completo porque no se haya mencionado.
6. Resolver todos los bloqueos o solicitar al propietario una excepción expresa, específica y documentada. Los elementos no verificados, incompletos, divergentes o sin documentación bloquean el cierre, salvo excepción aprobada.
7. Ejecutar integración y regresión de la etapa completa, emitir el informe final y obtener aceptación formal expresa del propietario.
8. Actualizar la continuidad y publicar el expediente aprobado en la rama autorizada, verificando GitHub y VPS.

Un módulo puede recibir un estado individual (IMPLEMENTADO, VERIFICADO, DOCUMENTADO o ACEPTADO), pero la etapa permanece ABIERTA hasta superar esta puerta formal. La auditoría integral y los documentos técnicos no pueden existir únicamente en el chat: deben estar versionados en el repositorio.

Documento operativo vinculante: `docs/REGLA_AUDITORIA_INTEGRAL_CIERRE_ETAPAS.md`. Esta regla se aplica a todas las etapas y prevalece frente a cualquier resumen o plan que sugiera cerrar una etapa con auditoría parcial.

## 3. Procedimiento obligatorio al iniciar una sesión

Antes de implementar:

1. Lee AGENTS.md, PROJECT_STATE.md, docs/CONTINUIDAD_DEL_PROYECTO.md, docs/PUNTO_CONTROL_ACTUAL.md y HISTORY.md.
2. Consulta el HEAD real de la rama autorizada en GitHub; no confíes únicamente en el SHA guardado en estos documentos.
3. Comprueba si /opt/xray-manager contiene .git. Si no existe, no afirmes una rama, commit ni estado Git local.
4. Inspecciona los archivos y modificaciones actuales de la VPS sin sobrescribirlos.
5. Lee la documentación normativa pertinente en `Xray-Normativa/` y verifica su coincidencia con la copia de respaldo `/root/Xray_Manager_Documentacion_Final_2026-10-31` cuando esté disponible.
6. Contrasta GitHub, VPS, documentación normativa y documentos técnicos.
7. Identifica divergencias, archivos no publicados, archivos remotos no presentes localmente y cualquier estado incierto.
8. Presenta un informe de recuperación y espera autorización del usuario antes de implementar.

No uses pull, checkout, reset, clean, rebase, push ni sincronizaciones destructivas como método de diagnóstico. No reemplaces archivos locales por los remotos sin comparar y preservar las diferencias.

## 4. Reglas de modificación y publicación

- Trabaja solo en design/user-identity-association-v1, salvo autorización explícita distinta.
- Nunca hagas commits, cambios de referencia ni PR destinados a main.
- Antes de editar, explica el alcance y los archivos que se modificarán.
- No cambies requisitos normativos aprobados por iniciativa propia.
- No inventes parámetros, credenciales, rutas, certificados, claves, valores predeterminados ni compatibilidades.
- Conserva los cambios locales y remotos no reconciliados. Ante una divergencia, detente y presenta opciones.
- Ejecuta las pruebas pertinentes después de cada cambio.
- Todo cambio implementado y aprobado debe cerrar con la actualización de los documentos de continuidad afectados y la sincronización del repositorio con GitHub. Esta es una regla permanente, no una tarea opcional ni dependiente de que el usuario vuelva a recordarla.
- La aprobación del alcance autoriza a completar ese ciclo de documentación, commit y publicación en la rama autorizada; si el usuario limita expresamente la publicación, respeta esa limitación y deja constancia de lo pendiente.
- Publica únicamente en la rama autorizada y verifica el SHA y los archivos remotos resultantes.
- No declares sincronizada la VPS si no se ha comparado el contenido real.
- No realices cambios de firewall, SSH, red, systemd o runtime sin autorización explícita y validación del alcance.

## 5. Estados que nunca deben confundirse

- IMPLEMENTADO: existe código o funcionalidad.
- VERIFICADO: las comprobaciones pertinentes se ejecutaron y pasaron; indica cuáles y dónde.
- PUBLICADO: el cambio está confirmado en la rama autorizada de GitHub.
- SINCRONIZADO: el contenido de la VPS se comparó y coincide con el destino previsto.
- ACEPTADO: el propietario aprobó formalmente el resultado.

Una prueba histórica documentada no equivale a una prueba ejecutada en la sesión actual. Indica fecha y evidencia. No llames completada o aceptada una etapa por inferencia.

## 6. Estado y tratamiento de Git en la VPS

Al 02/11/2026, /opt/xray-manager ya contiene metadatos Git y está configurado como checkout del repositorio oficial:
- remoto: git@github.com:Jaok04/xray-core-manager.git;
- rama autorizada: design/user-identity-association-v1;
- último HEAD verificado: 0c58f4adb95513fdd5e9a7d849bc2f34e896160b.

Este SHA es una referencia histórica, no una verdad permanente. En cada sesión consulta el estado real. Si .git existe, inspecciona branch, status, remotos, HEAD y divergencia antes de operar. Si no existe, trata la ruta como árbol de archivos sin identidad Git verificable y aplica el procedimiento de comparación por contenido y SHA-256. Nunca presupongas que el checkout está limpio ni reemplaces cambios divergentes sin resolverlos.

## 7. Reglas técnicas

- El proyecto es un administrador modular de Xray-core para Linux, desarrollado en Bash.
- Respeta separación entre modelos neutrales, adaptadores versionados, persistencia, validación y aplicación.
- Una configuración en estado draft no es una conexión activa ni está aplicada al runtime.
- Validar JSON con Xray no demuestra conectividad extremo a extremo.
- Distingue funciones nativas de Xray-core de componentes externos/plugins.
- No inventes compatibilidad entre versión, protocolo, transporte y seguridad.
- Conserva los límites y advertencias de las pruebas, incluidos mocks, fixtures y entornos desechables.
- No expongas secretos en logs, informes o commits.

## 8. Protocolo obligatorio de cierre de cada cambio aprobado

Todo cambio implementado y aprobado debe completar este ciclo antes de considerarse cerrado:
1. Ejecuta y registra las pruebas pertinentes; identifica expresamente las no ejecutadas y sus motivos.
2. Actualiza PROJECT_STATE.md con el estado real cuando el cambio afecte el estado, alcance o avance del proyecto.
3. Actualiza docs/PUNTO_CONTROL_ACTUAL.md para que indique el punto exacto de reanudación y la siguiente acción permitida.
4. Añade a HISTORY.md una entrada cronológica con el cambio, la decisión/aprobación pertinente, las verificaciones y el commit resultante. Nunca borres el historial anterior.
5. Actualiza docs/CONTINUIDAD_DEL_PROYECTO.md si cambia el procedimiento de recuperación, trabajo o publicación.
6. Actualiza AGENTS.md solo cuando cambie una regla permanente aprobada.
7. Actualiza la documentación técnica afectada para que describa el comportamiento real. No modifiques la documentación normativa salvo aprobación expresa.
8. Revisa el diff completo y ejecuta controles de formato/sintaxis pertinentes.
9. Crea un commit descriptivo y publica los cambios aprobados en design/user-identity-association-v1. No publiques en main. Si el usuario ha impuesto una restricción explícita de publicación, no la ignores: documenta el pendiente.
10. Verifica el SHA remoto, los archivos publicados y que la rama no tenga divergencias inesperadas.
11. Comprueba que el checkout de /opt/xray-manager corresponde al estado publicado y queda limpio; si no coincide, resuelve o documenta la divergencia sin sobrescribirla.
12. Informa por separado qué quedó IMPLEMENTADO, VERIFICADO, ACEPTADO, PUBLICADO y SINCRONIZADO.

No marques una tarea como cerrada si falta un criterio de aceptación.

## 9. Documentos de continuidad y responsabilidades

- PROJECT_STATE.md: fotografía consolidada del estado actual.
- docs/CONTINUIDAD_DEL_PROYECTO.md: procedimiento para que otra IA recupere y continúe el trabajo.
- docs/PUNTO_CONTROL_ACTUAL.md: ubicación precisa del trabajo y siguiente acción autorizada.
- HISTORY.md: registro cronológico de hitos y decisiones.
- AGENTS.md: reglas permanentes para agentes.

Evita copiar todo el contenido de un documento en los demás. Enlaza los documentos y mantén cada uno en su responsabilidad.

## 10. Regla final

Si falta evidencia, hay contradicciones o no está claro qué acción autorizó el propietario, detente, explica la incertidumbre y pregunta. La prioridad es preservar el proyecto y sus decisiones, no avanzar a costa de perder trazabilidad.