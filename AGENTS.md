# Instrucciones para agentes de IA — Xray Core Manager

## 1. Propósito y alcance

Este archivo establece las reglas obligatorias para cualquier IA o colaborador que analice, mantenga o desarrolle Xray Core Manager. Su objetivo es permitir que el trabajo continúe de forma segura aunque se pierda el chat anterior.

Lee este archivo antes de analizar o modificar el proyecto. Después consulta PROJECT_STATE.md y docs/PUNTO_CONTROL_ACTUAL.md.

## 2. Fuentes oficiales y jerarquía

- Repositorio: https://github.com/Jaok04/xray-core-manager
- Rama de desarrollo autorizada: design/user-identity-association-v1
- Rama main: protegida por instrucción del propietario; no modificarla.
- VPS de desarrollo: /opt/xray-manager
- Documentación funcional normativa aprobada: /root/Xray_Manager_Documentacion_Final_2026-10-31

La documentación normativa define QUÉ debe hacer el producto. El código, las pruebas y la documentación técnica describen CÓMO se ha implementado. No conviertas una decisión técnica en un requisito funcional aprobado sin autorización del usuario.

Orden para resolver discrepancias:
1. Instrucciones explícitas y recientes del propietario.
2. Documentación normativa aprobada en la ruta indicada.
3. Decisiones aprobadas registradas en los documentos de continuidad.
4. Documentación técnica y código existente.
5. Hipótesis: nunca tratarlas como decisiones.

Si una ampliación técnica contradice o amplía la especificación normativa, conserva la implementación existente sin extenderla y registra la discrepancia como pendiente de ratificación. No reescribas silenciosamente la especificación.

## 3. Procedimiento obligatorio al iniciar una sesión

Antes de implementar:

1. Lee AGENTS.md, PROJECT_STATE.md, docs/CONTINUIDAD_DEL_PROYECTO.md, docs/PUNTO_CONTROL_ACTUAL.md y HISTORY.md.
2. Consulta el HEAD real de la rama autorizada en GitHub; no confíes únicamente en el SHA guardado en estos documentos.
3. Comprueba si /opt/xray-manager contiene .git. Si no existe, no afirmes una rama, commit ni estado Git local.
4. Inspecciona los archivos y modificaciones actuales de la VPS sin sobrescribirlos.
5. Lee la documentación normativa pertinente en /root/Xray_Manager_Documentacion_Final_2026-10-31.
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
