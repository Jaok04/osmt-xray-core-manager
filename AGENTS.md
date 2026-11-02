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
- Actualiza documentación técnica y continuidad cuando cambie el estado.
- Publica únicamente en la rama autorizada y verifica el SHA/archivos remotos resultantes.
- No declares sincronizada la VPS si no se ha comparado el contenido real.
- No realices cambios de firewall, SSH, red, systemd o runtime sin autorización explícita y validación del alcance.

## 5. Estados que nunca deben confundirse

- IMPLEMENTADO: existe código o funcionalidad.
- VERIFICADO: las comprobaciones pertinentes se ejecutaron y pasaron; indica cuáles y dónde.
- PUBLICADO: el cambio está confirmado en la rama autorizada de GitHub.
- SINCRONIZADO: el contenido de la VPS se comparó y coincide con el destino previsto.
- ACEPTADO: el propietario aprobó formalmente el resultado.

Una prueba histórica documentada no equivale a una prueba ejecutada en la sesión actual. Indica fecha y evidencia. No llames completada o aceptada una etapa por inferencia.

## 6. Particularidad de la VPS

La ruta /opt/xray-manager puede ser una copia de trabajo sin metadatos Git. En el estado registrado el 02/11/2026 no tenía directorio .git. Si continúa así:
- trata la VPS como árbol de archivos, no como checkout;
- no ejecutes comandos Git dentro de ella;
- no atribuyas branch/commit a sus archivos;
- compara archivos mediante hashes y contenido con GitHub;
- preserva cualquier archivo que difiera;
- documenta exactamente cómo se transfirieron y verificaron los cambios.

## 7. Reglas técnicas

- El proyecto es un administrador modular de Xray-core para Linux, desarrollado en Bash.
- Respeta separación entre modelos neutrales, adaptadores versionados, persistencia, validación y aplicación.
- Una configuración en estado draft no es una conexión activa ni está aplicada al runtime.
- Validar JSON con Xray no demuestra conectividad extremo a extremo.
- Distingue funciones nativas de Xray-core de componentes externos/plugins.
- No inventes compatibilidad entre versión, protocolo, transporte y seguridad.
- Conserva los límites y advertencias de las pruebas, incluidos mocks, fixtures y entornos desechables.
- No expongas secretos en logs, informes o commits.

## 8. Protocolo de cierre de cada trabajo

Al terminar una tarea autorizada:
1. Actualiza PROJECT_STATE.md con el estado real.
2. Actualiza docs/PUNTO_CONTROL_ACTUAL.md con el punto exacto de reanudación.
3. Registra hitos, decisiones y publicaciones en HISTORY.md.
4. Actualiza docs/CONTINUIDAD_DEL_PROYECTO.md si cambia el procedimiento.
5. Actualiza la documentación técnica afectada.
6. Ejecuta y registra las pruebas aplicables.
7. Publica en la rama autorizada, si el usuario autorizó la publicación.
8. Verifica el commit y los archivos de GitHub.
9. Compara la VPS y deja constancia de su sincronización o divergencia.
10. Indica qué se implementó, verificó, publicó, sincronizó y qué queda pendiente.

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
