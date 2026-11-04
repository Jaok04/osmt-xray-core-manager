# Diseño técnico C-05E — Integración del menú Bash de validación Xray

**Fecha:** 2026-11-04
**Rama de referencia:** `design/user-identity-association-v1`
**Base:** `ed700c1e770063f6e67c6ebaeae4652172bb2f02` (C-05D publicada)
**Estado:** DISEÑO APROBADO; implementación C-05E autorizada y ejecutada en la rama indicada. Sin commit ni push.

## 1. Objetivo

Integrar en el menú existente la validación estática/nativa de configuraciones independientes y la consulta de informes de C-05B/C-05D, respetando las opciones normativas de Etapa 5. La interfaz será una capa de presentación/orquestación; las reglas de validación, persistencia, integridad y comparación seguirán en los servicios Python ya aceptados.

## 2. Fuentes y contratos

- Normativa inmutable: `Xray-Normativa/05_Configuraciones_Perfiles/Etapa_5_Configuraciones_Perfiles.md`, sección 4, y su YAML asociado.
- Motor y promoción: `scripts/xray_config_validator.py` y `scripts/xray_config_promotion.py` (C-05A/C).
- Almacén append-only: `scripts/xray_validation_store.py` (C-05B).
- Servicio read-only de historial/comparación: `scripts/xray_validation_history.py` (C-05D).
- Patrón de integración de menú: `modules/xray_configurations_menu.sh`, `modules/profiles.sh`, `bin/xray-manager`.
- Precedente de integración: `docs/AUDITORIA_C04C_INTEGRACION_MENU_BASH_2026-11-04.md`.

La normativa define el submenú de validación con cinco entradas: validar configuración guardada, validar archivo externo, validar configuración activa, ver último informe y consultar historial. Define además informes conservados tras edición/eliminación, inspección de errores/advertencias y comparación read-only.

## 3. Punto de entrada y navegación propuestos

La entrada se conectará en `menu_config_profiles_backups()` de `modules/profiles.sh`, sustituyendo únicamente la opción `[2] Validar archivos de configuración (pendiente)` por el submenú C-05E. El submenú tendrá navegación de retorno y no alterará el menú principal.

### Submenú visible

```text
VALIDACIÓN DE CONFIGURACIONES XRAY
[1] Validar configuración guardada
[2] Validar archivo externo (no disponible en esta entrega)
[3] Validar configuración activa (no disponible en esta entrega)
[4] Ver último informe de validación
[5] Consultar historial de validaciones
[0] Volver
```

Las opciones 2 y 3 se muestran como pendientes/no disponibles, sin solicitar rutas, inspeccionar el runtime ni simular una validación. La razón es contractual: el flujo C-05C actual valida una revisión exacta del almacén independiente; no existe todavía adaptador aprobado para archivos externos ni para identificar de forma fiable la configuración realmente ejecutada. La normativa prohíbe modificar/reiniciar Xray y exige informar incertidumbre sobre el estado activo.

## 4. Funcionalidad de cada opción

### 4.1 Validar configuración guardada

1. Seleccionar una configuración mediante el catálogo del CLI existente; nunca construir rutas desde nombre/entrada del usuario.
2. Mostrar nombre, `config_id`, revisión actual y estado antes de validar.
3. Si no hay revisión/contenido, informar y volver sin invocar el motor.
4. Solicitar confirmación explícita indicando que se ejecutará validación estática y nativa de esa revisión y que se guardará un informe permanente.
5. Invocar `xray_config_promotion.py validate --config-id ... [--revision ...]` con argumentos separados y rutas configurables; no interpolar datos en `eval` ni shell dinámico.
6. Mostrar resultado resumido: PASS, PASS_WITH_WARNINGS, FAIL o INCOMPLETE; revisión exacta, identificador del informe, fecha, checks y conteos de errores/advertencias.
7. Aclarar que la validación no aplica ni reinicia Xray. La promoción de estado Validada solo sucede según las reglas transaccionales ya implementadas en C-05C.

No se añadirá un segundo camino de validación ni se replicarán las reglas de C-05A/C-05C en Bash.

### 4.2 Archivo externo

En esta entrega queda deshabilitada con mensaje explícito. No se importará automáticamente ni se copiará al almacén. La habilitación futura requiere diseño/contrato para validar bytes externos y persistir un informe sin asignar identidad/revisión ficticia.

### 4.3 Configuración activa

En esta entrega queda deshabilitada con mensaje explícito. No se leerá `/etc/xray/config.json` ni se inferirá que el archivo configurado equivale al proceso en ejecución. No se consultará ni modificará systemd/runtime desde C-05E. Requiere fase futura con identificación verificable de la configuración cargada y comparación guardado/aplicado.

### 4.4 Último informe

Usar `ValidationHistoryService.get_latest_report()` y mostrar metadatos y resumen de checks, errores y advertencias. Permitir seleccionar una configuración para filtrar o mostrar el último informe global, según decisión de UX en implementación. Si no hay informes, informar sin error. No mostrar JSON de configuración ni secretos.

### 4.5 Historial y comparación

- Listar informes ordenados del más reciente al más antiguo, con paginación acotada.
- Mostrar fecha, configuración, revisión, resultado e ID corto/identificador completo seleccionable.
- Permitir filtro por configuración y resultado; filtros avanzados de revisión/fecha/tipo pueden añadirse si la UX es clara y no excede el contrato C-05D.
- Ver detalle de un informe seleccionado: metadatos Xray, checks, errores, advertencias y detalles sanitizados.
- Comparar dos informes seleccionados. La interfaz debe informar que ambos deben pertenecer al mismo `config_id`; las revisiones pueden ser distintas. Rechazar comparación entre configuraciones distintas mediante el servicio C-05D y presentar cambios agregados/eliminados/modificados.
- No permitir edición, borrado, purga ni retención de informes.

## 5. Adaptación CLI / límites de arquitectura

C-05D expone una API Python (`ValidationHistoryService`) pero no una CLI de historial. La implementación C-05E deberá proporcionar un adaptador CLI estrecho para listar/detallar/comparar informes o una invocación Python equivalente con contrato JSON estable. Preferencia: un `scripts/xray_validation_history.py` CLI con subcomandos `list`, `show`, `latest` y `compare`, manteniendo `ValidationHistoryService` como única lógica de negocio.

La CLI debe:
- validar argumentos y devolver errores no cero sin trazas internas al usuario;
- emitir JSON UTF-8 estructurado por stdout y diagnósticos por stderr;
- admitir ruta de almacén configurable, con valor por defecto `/var/lib/xray-manager/validation`;
- no aceptar rutas de informes arbitrarias ni crear el almacén durante una consulta;
- no exponer secretos ni contenido JSON original;
- mantener root/propiedad/permisos y verificación de integridad exigidos por C-05B;
- no introducir dependencias.

La integración Bash debe seguir el patrón `xray_configurations_cli`: verificar Python 3, jq y root, sin instalar dependencias. La ruta del almacén de informes debe configurarse en `config/paths.sh` como variable propia (propuesta `XRAY_MANAGER_VALIDATION_DIR`) y pasarse explícitamente a la CLI. La ruta de configuración y la clave maestra se reutilizarán únicamente a través del CLI C-05C existente; Bash no leerá la clave.

Archivos candidatos de implementación (no modificados por este diseño):
- `modules/xray_validation_menu.sh` (nuevo módulo Bash).
- `scripts/xray_validation_history.py` (extensión CLI del servicio existente, conservando API).
- `config/paths.sh` (ruta de almacén de informes).
- `bin/xray-manager` (carga del módulo).
- `modules/profiles.sh` (navegación desde opción 2).
- `tests/xray_validation_menu.sh` y `tests/smoke.sh` (integración/sintaxis).

## 6. Seguridad y comportamiento

- Solo lectura para historial, detalle y comparación.
- La opción de validar es la única que ejecuta el flujo C-05C y escribe un informe append-only; requiere confirmación.
- No se descifra configuración desde Bash ni se muestra contenido de configuración.
- No usar `eval`; pasar cada argumento por separado.
- No construir rutas con nombres, IDs ni filtros introducidos por usuario.
- No leer `master.key` directamente desde Bash; C-05C gestiona su uso.
- No modificar ni reiniciar servicio Xray, runtime, firewall, red, certificados o puertos.
- No instalar dependencias; si faltan, explicar el requisito y cancelar de forma segura.
- No crear, editar, eliminar, retener ni alterar informes.
- Todas las pruebas deben usar almacenes temporales y claves sintéticas; no usar almacenes live ni la clave maestra real.

## 7. Matriz de pruebas propuesta

| ID | Escenario | Resultado esperado |
|---|---|---|
| E01 | Entrada desde Configuraciones, perfiles y respaldos | Abre submenú de validación; retorno correcto |
| E02 | Opción 0 / EOF | Regresa sin efectos secundarios |
| E03 | Opción inválida | Mensaje controlado; menú sigue operativo |
| E04 | Sin Python 3 | Operación cancelada; no instala nada |
| E05 | Sin jq | Operación cancelada; no instala nada |
| E06 | Ejecución sin root | Rechazo controlado antes de invocar CLI |
| E07 | Catálogo vacío | Mensaje claro y retorno |
| E08 | Selección inválida/fuera de rango | No invoca validación |
| E09 | Configuración sin revisión/contenido | No invoca C-05C |
| E10 | Cancelación de confirmación | No ejecuta motor ni crea informe |
| E11 | Validación PASS | Muestra resultado, revisión e ID de informe |
| E12 | PASS_WITH_WARNINGS | Muestra advertencias y estado correcto |
| E13 | FAIL | Muestra errores; no presenta como Validada |
| E14 | INCOMPLETE / timeout / Xray ausente | Informa incompleto sin alterar runtime |
| E15 | Cambio concurrente de revisión | C-05C valida la revisión exacta; no sustituye por current distinta |
| E16 | Informe más reciente global | Muestra el más reciente o estado vacío |
| E17 | Último informe por configuración | Filtra correctamente por `config_id` |
| E18 | Historial vacío | Mensaje claro, sin traceback |
| E19 | Historial paginado | Orden descendente, sin duplicados ni saltos |
| E20 | Filtro por resultado/configuración | Solo devuelve coincidencias |
| E21 | Detalle de informe | Muestra metadatos/checks/diagnósticos sanitizados |
| E22 | ID de informe inválido/inexistente | Error controlado, sin traceback |
| E23 | Comparación misma config y revisiones distintas | Resumen de cambios correcto |
| E24 | Comparación entre config_id distintos | Rechazo explícito, sin comparación parcial |
| E25 | Selección de mismo informe dos veces | Resultado idéntico o aviso de comparación redundante, según UX final |
| E26 | Informe/catálogo manipulado | Integridad C-05B rechaza; no se repara ni modifica |
| E27 | Almacén ausente/inseguro/symlink | Error seguro; no crear ni corregir en consultas |
| E28 | Secretos en errores/detalles | No se muestran valores sensibles; respetar sanitización C-05B |
| E29 | Opción archivo externo | Mensaje pendiente; no lee/importa/modifica el archivo |
| E30 | Opción configuración activa | Mensaje pendiente; no consulta ni modifica runtime |
| E31 | Confirmación de validación | Informe append-only; cancelación no produce escritura |
| E32 | Bytes del almacén tras consultas | List/detail/compare no mutan catálogo ni informes |
| E33 | Navegación completa desde menú principal | Llega al submenú y vuelve correctamente |
| E34 | `bash -n` y smoke | Incluye módulo nuevo y pasa |
| E35 | Regresión Python C-05A/B/C/D | 76/76 o total actualizado PASS |
| E36 | Regresión shell completa | Todas las suites preexistentes PASS |
| E37 | ShellCheck focal / `git diff --check` | PASS |
| E38 | `install.sh --check` | PASS sin cambios de sistema |

## 8. Criterios de aceptación C-05E

1. La opción de validación está conectada desde el menú aprobado y navega/retorna correctamente.
2. Validar configuración guardada reutiliza exclusivamente C-05C y muestra el resultado persistido.
3. Último informe, historial, detalle y comparación reutilizan C-05D/C-05B sin duplicar lógica.
4. Opciones externa y activa no simulan funcionalidad no implementada; su indisponibilidad queda explícita.
5. Las consultas históricas son read-only y preservan integridad/inmutabilidad.
6. No se exponen secretos ni se accede a la clave maestra desde Bash.
7. No hay cambios de runtime/infraestructura ni dependencias.
8. Los casos E01–E38 constituyen la matriz de cobertura; su ejecución efectiva y los casos cubiertos por regresiones previas se identifican individualmente en la auditoría, sin asumir que los escenarios no ejecutados han pasado.
9. C-05E no cierra C-05 ni Etapa 5/Etapa 2 y no autoriza C-05F.

## 9. Fuera de alcance y decisiones pendientes

- C-05F auditoría integral.
- Habilitar validación de archivos externos.
- Identificar/validar configuración activa o ejecutar pruebas runtime.
- Activar/aplicar/reiniciar Xray.
- Cambios en esquema o retención de informes.
- Modificar normativa protegida.

Decisiones de UX aplicadas: historial global por defecto; página inicial de 20 registros; IDs completos en el listado para permitir selección/copiar sin ambigüedad.

## 10. Autorización

El usuario aprobó el diseño y autorizó expresamente la implementación completa de C-05E en `design/user-identity-association-v1`, sin commit ni push. La implementación y sus resultados se registran en `docs/IMPLEMENTACION_C05E_MENU_BASH_2026-11-04.md` y la auditoría en `docs/AUDITORIA_C05E_MENU_BASH_2026-11-04.md`.

## Addendum de aceptación y publicación — 2026-11-04

El diseño C-05E fue implementado, auditado, aceptado formalmente y publicado. Commit `8378ca47a751678f4eeeab20a5e2d06effd47fff` en `design/user-identity-association-v1`; push fast-forward y SHA remoto verificado. Las limitaciones de pruebas permanecen descritas en el informe de auditoría. C-05F requiere autorización independiente.
