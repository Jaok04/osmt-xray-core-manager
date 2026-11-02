# Protocolo de continuidad — Xray Core Manager

## 1. Objetivo

Permitir que cualquier IA o desarrollador retome el proyecto desde su último estado válido aunque el chat original se haya perdido, borrado o sustituido. La fuente de continuidad es el repositorio y la evidencia de la VPS, no la memoria de una conversación.

## 2. Mensaje para iniciar un chat nuevo

Copia y pega el siguiente texto en el nuevo chat:

~~~text
CONTINUAR PROYECTO XRAY CORE MANAGER

Necesito recuperar y continuar el proyecto exactamente desde su último punto de control documentado.

Repositorio oficial:
https://github.com/Jaok04/xray-core-manager

Rama autorizada:
design/user-identity-association-v1

No modificar la rama main.

Rutas oficiales de la VPS:
- Documentación normativa aprobada: /root/Xray_Manager_Documentacion_Final_2026-10-31
- Proyecto en desarrollo: /opt/xray-manager

Primero lee, en este orden:
1. AGENTS.md
2. PROJECT_STATE.md
3. docs/CONTINUIDAD_DEL_PROYECTO.md
4. docs/PUNTO_CONTROL_ACTUAL.md
5. HISTORY.md

Después realiza una auditoría de recuperación sin modificar archivos:
- consulta el HEAD real de la rama autorizada;
- verifica el estado y contenido de /opt/xray-manager;
- comprueba si la VPS tiene .git; no presupongas que sí;
- consulta la documentación normativa;
- contrasta los archivos y hashes de GitHub y VPS;
- identifica diferencias, cambios sin publicar y estados inciertos;
- recupera el estado de cada etapa y el último punto de control.

Distingue IMPLEMENTADO, VERIFICADO, PUBLICADO, SINCRONIZADO y ACEPTADO. No presentes pruebas históricas como si se hubieran ejecutado ahora.

No implementes, publiques, sincronices ni modifiques nada durante la auditoría. Presenta el informe y espera mi autorización explícita para el siguiente paso.
~~~

## 3. Orden de lectura

1. AGENTS.md: reglas obligatorias para la IA.
2. PROJECT_STATE.md: fotografía consolidada del estado y las etapas.
3. Este documento: procedimiento de recuperación y reanudación.
4. docs/PUNTO_CONTROL_ACTUAL.md: tarea exacta en la que se detuvo el trabajo.
5. HISTORY.md: decisiones e hitos cronológicos.
6. Documentación normativa de la VPS y documentos técnicos específicos de la etapa que se vaya a trabajar.

## 4. Auditoría de recuperación obligatoria

Antes de proponer implementación:

### GitHub
- Confirmar que existe el repositorio y la rama autorizada.
- Consultar el HEAD actual de design/user-identity-association-v1.
- Registrar SHA, mensaje y fecha del último commit.
- Revisar los archivos de continuidad y los archivos técnicos relevantes.
- Confirmar que main no se ha modificado.

### VPS
- Inspeccionar /opt/xray-manager.
- Comprobar explícitamente si existe .git.
- Si no existe .git, tratarla como copia de trabajo sin rama/commit verificables.
- Inventariar módulos, configuración, pruebas y documentación.
- Revisar cambios locales y fechas, sin sobrescribir nada.
- Leer la documentación normativa en /root/Xray_Manager_Documentacion_Final_2026-10-31.

### Contraste
- Comparar archivos por contenido y SHA-256 cuando sea posible.
- Separar coincidencias, divergencias, archivos solo locales y archivos solo remotos.
- No corregir diferencias automáticamente.
- No asumir que una diferencia de hash con texto aparentemente igual carece de importancia; revisar bytes, codificación, saltos de línea y final de archivo.
- Identificar cualquier cambio no publicado o no sincronizado.

## 5. Cómo reanudar el desarrollo

Después de la auditoría:

1. Presentar el estado real y las incertidumbres.
2. Identificar el siguiente paso permitido por la documentación normativa.
3. Señalar qué archivos se modificarían y por qué.
4. Explicar las pruebas previstas y el riesgo.
5. Esperar autorización explícita del propietario.
6. Implementar únicamente el alcance aprobado.
7. Probar y documentar el resultado.
8. Actualizar los documentos de continuidad.
9. Publicar en la rama autorizada si se autorizó la publicación.
10. Verificar GitHub y la VPS por separado.

## 6. Reconciliación segura de GitHub y VPS

La VPS puede no ser un checkout Git. En ese caso, la sincronización debe hacerse como transferencia controlada de archivos:
- comparar antes de copiar;
- conservar una copia de seguridad de los archivos destino que vayan a reemplazarse;
- no sobrescribir archivos divergentes sin resolución;
- verificar el SHA-256 de origen y destino después de transferir;
- registrar la fecha, los archivos y el método utilizado.

Si la VPS tiene .git en una sesión futura, no asumir que está limpia. Inspeccionar branch, status, remotos y commits antes de cualquier operación.

## 7. Actualización de continuidad

Al cerrar una implementación, auditoría o decisión:
- PROJECT_STATE.md: actualizar la fotografía global.
- docs/PUNTO_CONTROL_ACTUAL.md: actualizar la ubicación exacta del trabajo, estado y siguiente acción autorizada.
- HISTORY.md: añadir un registro cronológico, sin borrar entradas anteriores.
- AGENTS.md: cambiar solo cuando se apruebe una regla permanente nueva.
- Este documento: cambiar solo si cambia el procedimiento de continuidad.

La documentación normativa solo se modifica mediante decisión/aprobación del propietario. La documentación técnica debe reflejar lo que realmente hace el código.

## 8. Regla de recuperación

Si los archivos de continuidad contradicen el código o la documentación normativa, no elijas una versión por intuición. Informa la contradicción, conserva ambas evidencias y pide una decisión cuando afecte requisitos o comportamiento.