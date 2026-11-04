# Diseño C-05F — Auditoría integral del subsistema de validación Xray

**Fecha:** 2026-11-04
**Estado:** PROPUESTA DE DISEÑO — pendiente de revisión y autorización de ejecución por el propietario.
**Base de trabajo:** `design/user-identity-association-v1`, HEAD `a4f2c6356652e04206918c410ddf3f6aa3181808`.
**Alcance auditado:** conjunto C-05A, C-05B, C-05C, C-05D y C-05E.
**No es:** auditoría integral de toda la Etapa 5 ni cierre de Etapa 5.

## 1. Propósito

C-05F realizará una auditoría técnica transversal del subsistema de validación de configuraciones Xray incorporado mediante C-05A–C-05E. Su objetivo es verificar, con evidencia reproducible, que las cinco entregas funcionan conjuntamente, mantienen sus contratos, preservan la integridad de datos y respetan los requisitos aplicables de la especificación normativa aprobada de Etapa 5.

La auditoría debe identificar conformidad, defectos, cobertura insuficiente, divergencias normativas, limitaciones y decisiones pendientes. No debe convertir una opción deshabilitada o una prueba no ejecutada en un resultado PASS.

## 2. Línea base y jerarquía

1. `Xray-Normativa/05_Configuraciones_Perfiles/Etapa_5_Configuraciones_Perfiles.md` y su YAML aprobado son la línea base funcional.
2. `AGENTS.md`, `docs/REGLA_CONTRASTE_DOCUMENTACION_PRELIMINAR.md` y `docs/REGLA_AUDITORIA_INTEGRAL_CIERRE_ETAPAS.md` gobiernan el método y la custodia.
3. Las decisiones técnicas aprobadas y los expedientes C-05A–C-05E describen la implementación y sus límites; no reemplazan la normativa.
4. La base de revisión es el commit publicado `a4f2c6356652e04206918c410ddf3f6aa3181808`. Si el HEAD cambia antes de ejecutar C-05F, se debe detener la ejecución y revisar el diff/alcance con el propietario.

En la preparación de este diseño, los 13 archivos normativos presentes en `Xray-Normativa/` que tienen copia homóloga en `/root/Xray_Manager_Documentacion_Final_2026-10-31` coincidieron por SHA-256. `Xray-Normativa/README.md` no tiene homólogo en el respaldo y se trata como documento de custodia del repositorio, no como requisito funcional. No se modificó ningún archivo normativo.

## 3. Alcance incluido

### 3.1 Componentes

| Entrega | Responsabilidad | Archivos principales |
|---|---|---|
| C-05A | Motor de validación estática y nativa | `scripts/xray_config_validator.py`, `tests/test_xray_config_validator.py` |
| C-05B | Almacén append-only de informes, integridad, permisos, lock y WAL | `scripts/xray_validation_store.py`, `tests/test_xray_validation_store.py` |
| C-05C | Orquestación de validación, identidad exacta de configuración/revisión, promoción y transacción | `scripts/xray_config_promotion.py`, `scripts/xray_configurations.py`, `tests/test_xray_config_promotion.py` |
| C-05D | Historial, filtros, detalle y comparación read-only | `scripts/xray_validation_history.py`, `tests/test_xray_validation_history.py` |
| C-05E | Integración CLI/Bash y navegación de menú | `modules/xray_validation_menu.sh`, `modules/profiles.sh`, `bin/xray-manager`, `config/paths.sh`, `tests/xray_validation_menu.sh` |

Se inspeccionarán también los documentos de diseño, implementación, auditoría, continuidad y el conjunto de pruebas de regresión relacionado.

### 3.2 Requisitos normativos aplicables

La trazabilidad se limita a los requisitos de Etapa 5 relacionados directamente con validación:

- Menú principal, navegación y retorno: sección 2.
- Menú de validación y sus cinco operaciones: sección 4.
- Validación estática: sintaxis JSON, estructura Xray, parámetros requeridos, tipos/valores, compatibilidad con versión instalada, referencias y conflictos detectables: sección 4.1.
- Validación de configuración guardada y asociación del informe con la versión exacta: sección 4.1.
- Validación externa y activa, incluyendo sus restricciones de solo lectura y reporte de incertidumbre: sección 4.1.
- Distinción entre validación estática y prueba de funcionamiento: sección 4.1.
- Persistencia de informes tras editar/eliminar configuraciones; consulta por archivo, fecha y tipo; inspección y comparación: sección 4.1.
- Estados Borrador, Validada, Aplicada y Anterior, y reglas de edición de versiones: sección 5.
- Exclusión del historial de validación de los respaldos: sección 8 y YAML `backup_creation.exclude_all_history`.

No se auditarán como parte de C-05F los administradores de perfiles, aplicación de perfil, backup/restore completo, certificados ni otros módulos de Etapa 5, salvo las interfaces de integración necesarias para comprobar que C-05 no los altera.

## 4. Fuera de alcance y restricciones

- No implementar ni corregir código durante la auditoría.
- No cambiar requisitos ni editar `Xray-Normativa/`.
- No crear ni consultar el almacén live `/var/lib/xray-manager/validation` si existe; la auditoría no debe leer datos operativos existentes.
- No leer, derivar ni utilizar `/etc/xray-manager/keys/master.key`.
- No inspeccionar ni modificar configuraciones activas, secretos de usuario o archivos operativos de Xray.
- No iniciar, detener, reiniciar ni recargar Xray; no aplicar configuraciones.
- No modificar systemd, runtime, certificados, firewall, puertos, red, paquetes o dependencias.
- No ejecutar pruebas contra `Vps de Pruebas`.
- No hacer commit, push ni sincronización como parte de esta autorización de diseño. La ejecución y publicación se decidirán separadamente.

Las pruebas automatizadas utilizarán directorios temporales aislados, identidades y configuraciones sintéticas y claves generadas exclusivamente para las pruebas. Si una prueba requiere permisos elevados, el binario Xray real o condiciones no disponibles, se documentará como no ejecutada o limitada; no se relajarán guardas para hacerla pasar.

## 5. Método de auditoría

### Fase 0 — control de entrada

- Verificar rama, HEAD, árbol de trabajo, upstream y SHA remoto.
- Confirmar que la base sigue siendo `a4f2c6356652e04206918c410ddf3f6aa3181808` y que la rama no diverge.
- Confirmar custodia de `main`, `Xray-Normativa/` y VPS de pruebas.
- Registrar versiones de Python, Bash, jq, ShellCheck y Xray disponibles sin instalar ni actualizar nada.
- Si hay cambios inesperados, divergencia o archivos locales no explicados, detenerse.

### Fase 1 — inventario y revisión estática

- Mapear cada requisito aplicable a funciones, archivos, interfaces, datos y pruebas.
- Revisar los contratos de entrada/salida entre A→B→C→D→E.
- Revisar manejo de errores, estados, códigos de salida, saneamiento, secretos, rutas, permisos, symlinks/hardlinks, locks, atomicidad, WAL y recuperación.
- Comprobar que el menú Bash no duplique reglas de negocio ni construya comandos inseguros.
- Contrastar los informes previos y distinguir pruebas reales, fixtures, mocks y pruebas de UI.

### Fase 2 — pruebas focales

Reejecutar, en entorno aislado, las pruebas focales de C-05A, B, C, D y E. Repetir además los escenarios que las auditorías previas marcaron PARCIAL o PENDIENTE cuando sean pertinentes y seguros. La matriz `docs/MATRIZ_C05F_AUDITORIA_INTEGRAL_2026-11-04.md` define los casos concretos.

### Fase 3 — integración transversal

Ejecutar recorridos completos y verificables:

1. Seleccionar una configuración sintética guardada y su revisión exacta.
2. Validar bytes de esa revisión con el motor estático/nativo.
3. Persistir el informe con identidad y hash correctos.
4. Promover solo los resultados elegibles y comprobar el estado resultante.
5. Consultar el informe recién generado desde último informe, historial y detalle.
6. Comparar informes de revisiones distintas de la misma configuración.
7. Editar la configuración para generar un Borrador y confirmar que la revisión Validada previa y el informe histórico permanecen íntegros.
8. Eliminar la configuración sintética en el almacén temporal y comprobar que el informe histórico sigue consultable.
9. Confirmar que las consultas no alteran informes ni catálogo, salvo recuperación WAL preexistente demostrablemente pendiente; separar y documentar ese comportamiento.

No se utilizarán configuraciones reales ni se aplicará nada al daemon.

### Fase 4 — regresión y controles estáticos

- Ejecutar toda la suite Python pertinente de C-05A/B/C/D.
- Ejecutar los 57 scripts `tests/*.sh` de la base, registrando conteos reales, códigos de salida y skips.
- Ejecutar `py_compile`, `bash -n`, ShellCheck severidad error en los archivos afectados, `install.sh --check` como no-op y `git diff --check`.
- Si cambia la cantidad de pruebas o scripts desde el baseline, registrar el nuevo inventario y no reutilizar conteos históricos.
- No ejecutar instalación ni actualización de dependencias.

### Fase 5 — dictamen

- Clasificar cada fila de la matriz con evidencia y estado individual.
- Abrir hallazgos con severidad, impacto, reproducción, archivo/función afectada y recomendación.
- Distinguir defecto de implementación, limitación deliberada, requisito pendiente, riesgo residual y decisión del propietario.
- No corregir hallazgos en esta fase. Proponer una subfase de corrección separada y solicitar autorización.
- Emitir un dictamen de C-05F; no declarar cerrada toda la Etapa 5.

## 6. Criterios de evaluación y estados

Cada caso tendrá uno de estos estados:

- **PASS:** prueba ejecutada y evidencia suficiente que satisface el criterio dentro del alcance.
- **FAIL:** prueba ejecutada y el comportamiento no satisface el criterio.
- **PARCIAL:** cobertura o resultado incompleto.
- **PENDIENTE:** no ejecutado o evidencia ausente.
- **NO APLICABLE:** justificación técnica explícita y aprobada cuando afecte el requisito.
- **DIVERGENCIA NORMATIVA:** la implementación no cubre o difiere del requisito aprobado; no se reclasifica como PASS por ser una limitación conocida.

La aceptación individual previa de C-05A–C-05E se conserva. C-05F evalúa su integración y conformidad transversal, sin revocar decisiones históricas por inferencia. Cualquier divergencia normativa se presenta al propietario para decisión.

## 7. Entregables previstos

1. `docs/MATRIZ_C05F_AUDITORIA_INTEGRAL_2026-11-04.md` — matriz requisito → componente → prueba → evidencia → estado.
2. `docs/AUDITORIA_C05F_AUDITORIA_INTEGRAL_2026-11-04.md` — informe ejecutado, hallazgos, límites, dictamen y referencias de evidencia.
3. Addenda de continuidad en `PROJECT_STATE.md`, `docs/PUNTO_CONTROL_ACTUAL.md`, `docs/CONTINUIDAD_DEL_PROYECTO.md` y `HISTORY.md` después de completar la auditoría.

Este diseño no afirma que la auditoría haya sido ejecutada. El informe final y los estados de la matriz solo se completarán después de ejecutar las comprobaciones.

## 8. Criterios de aceptación de C-05F

- Todos los componentes C-05A–C-05E y requisitos normativos aplicables están inventariados.
- Cada requisito tiene conclusión explícita y trazabilidad a código, prueba y evidencia.
- Se ejecutaron las pruebas aprobadas y se declaran las no ejecutadas.
- Se verificó el recorrido transversal A→B→C→D→E con datos sintéticos y almacenes temporales.
- Se evaluaron seguridad, persistencia, integridad, transacciones, recuperación, solo lectura, UX/CLI y regresión.
- Todos los hallazgos y divergencias están documentados, sin ocultar requisitos incompletos.
- No se alteró normativa, secretos, almacenes live, runtime ni infraestructura.
- El propietario revisa el informe y acepta formalmente C-05F.

C-05F no cierra Etapa 5. El cierre de Etapa 5 requiere inventario y auditoría de todos sus demás puntos (configuraciones independientes, perfiles, activación, backup, gestión de respaldos, restauración, informes de restauración y logs), conforme a la regla integral del proyecto.

## 9. Decisiones que requieren confirmación antes de ejecutar

1. Confirmar que el alcance de C-05F es la auditoría transversal del subsistema C-05A–C-05E, y no una auditoría integral de toda la Etapa 5.
2. Confirmar que las opciones normativas de validación externa y activa, actualmente deshabilitadas, se registren como divergencias/requisitos incompletos, sin intentar implementarlas en C-05F.
3. Confirmar que cualquier defecto detectado quede documentado y se someta a autorización de corrección separada.

**Estado actual:** diseño preparado para revisión. No se ha ejecutado C-05F ni se ha modificado código, pruebas, runtime o infraestructura.

## Addendum — ejecución autorizada y realizada (2026-11-04)

El propietario aprobó las tres condiciones de ejecución. La auditoría se ejecutó conforme al alcance de C-05A–C-05E, sin implementar correcciones. El resultado, evidencias, H-01 y divergencias D-01–D-05 se encuentran en:

- docs/AUDITORIA_C05F_AUDITORIA_INTEGRAL_2026-11-04.md
- docs/MATRIZ_C05F_AUDITORIA_INTEGRAL_2026-11-04.md

Resultado técnico: PASS con un hallazgo menor y divergencias normativas documentadas. La auditoría queda pendiente de aceptación formal del propietario. No se modificó código, no se hizo commit ni push y Etapa 5/Etapa 2 siguen abiertas.
