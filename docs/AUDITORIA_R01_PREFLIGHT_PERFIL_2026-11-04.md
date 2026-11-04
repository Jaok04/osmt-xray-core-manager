# Auditoría R-01 — validación y preflight runtime por perfil/revisión

**Fecha:** 2026-11-04
**Dictamen:** PASS técnico del alcance implementado en entorno aislado.
**Estado:** AUDITADA LOCALMENTE; aceptación formal pendiente.

## 1. Contraste normativo

Se contrastó con Xray-Normativa/05_Configuraciones_Perfiles/Etapa_5_Configuraciones_Perfiles.md:

| Referencia | Requisito | Resultado |
|---|---|---|
| §3.1 | Las configuraciones independientes no son vía alternativa de activación; se activa mediante perfiles | PASS: CLI y preflight solo aceptan profile_id + revision; no reutilizan informes config_id |
| §4.1 | La validación estática es obligatoria y el informe debe asociarse a la versión exacta | PASS: CLI/menú ejecutan motor estático/nativo y persisten informe ligado a perfil/revisión |
| §5 | Borrador no es Validada; los estados deben distinguirse | PASS: manifiesto por revisión, informe y resumen de current_revision se actualizan con semántica separada |
| §7 | El perfil destino y su versión deben estar validados antes de aplicar; guardar/seleccionar no activa | PASS: preflight exige manifiesto e informe válidos; validar no publica ni activa |
| §8 | Los historiales de validación se excluyen de respaldos | PASS de diseño: el almacén es historial separado y no se incorpora al formato de backup |

No se modificó Xray-Normativa/. Los 14 archivos normativos Markdown/YAML del repositorio coinciden byte a byte con la copia maestra; README.md es auxiliar y no forma parte del conjunto normativo.

## 2. Controles de implementación

- La identidad se valida por profile_id + revision; no se consulta current_revision para sustituir la revisión solicitada.
- El motor estático/nativo recibe los bytes exactos descifrados de la revisión.
- El informe contiene identidad, hash/tamaño, resultado, checks, versión del validador y hash del binario Xray.
- La validación vuelve a leer la revisión y verifica su hash antes de persistir el estado.
- Manifiesto y metadata se actualizan mediante transacción recuperable. Un fallo entre escrituras restaura ambos.
- metadata.json resume current_revision. Validar una revisión histórica actualiza solo su manifiesto e informe; no cambia el resumen de la revisión actual.
- Al crear/restaurar una nueva revisión, se limpia last_validated_revision y el resumen vuelve a not_validated; los informes y manifiestos válidos históricos permanecen asociados a sus revisiones.
- El preflight comprueba integridad AES-GCM, hash del contenido, informe íntegro, resultado PASS/PASS_WITH_WARNINGS, checks obligatorios y hash del binario.
- El preflight usa lock compartido de perfil y lectura read-only del almacén de informes; no crea rutas, corrige permisos, limpia huérfanos ni recupera journals.
- El estado de servicio se verifica mediante fixture sintético root-owned 0600, no consultando systemd real.
- Se comprobaron explícitamente runtime_published=false y service_action_performed=false.

## 3. Resultados de pruebas

- Preflight R-01: **18/18 PASS**.
- Integración de validación de perfiles R-01: **10/10 PASS**.
- Total focal R-01: **28/28 PASS**.
- Regresión Python completa final: **108/108 PASS**.
- Regresión shell completa: **58/58 PASS**.
- install.sh --check: PASS; no modificó el sistema.
- py_compile de scripts/tests: PASS.
- bash -n global: PASS.
- ShellCheck focal de config/paths.sh y modules/profiles.sh: PASS.
- git diff --check: PASS.
- Los tests usan claves, perfiles, informes, binarios y fixtures sintéticos; no leen el master.key real.
- No se ejecutó Xray real desde R-01 ni se realizó prueba de conectividad.

## 4. Limitaciones y riesgos residuales

1. La CLI y el menú están integrados, pero no se ejecutaron contra el almacén/clave reales; todos los casos usan perfiles y claves sintéticos.
2. El estado de servicio se valida con un fixture; no se consulta systemd real.
3. La validación nativa C-05A se ejecuta con la identidad del llamador; todavía no demuestra que xray pueda leer leases TLS ni validar la configuración final de staging.
4. No se ha probado una identidad de servicio real ni lectura de leases TLS por el proceso Xray.
5. No se ejecutaron R-02, R-03, R-04 ni R-05.
6. No se ejecutó R-06/live ni se tocó la VPS de pruebas.

## 5. Dictamen

**PASS técnico de R-01 en entorno aislado.** El administrador ya dispone de un flujo CLI/menú para validar una revisión exacta y persistir su informe vinculado a profile_id + revision. El preflight puede comprobar esa prueba sin confundirla con una validación C-05B/C-05C de configuración independiente.

R-01: IMPLEMENTADA / INTEGRADA EN CLI-MENÚ / VERIFICADA EN FIXTURES / AUDITADA LOCALMENTE / ACEPTACIÓN FORMAL PENDIENTE.
R-02–R-05: NO INICIADAS.
R-06/live: NO AUTORIZADA.
Etapa 5: ABIERTA.
