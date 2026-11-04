# Implementación R-01 — validación y preflight runtime por perfil/revisión

**Fecha:** 2026-11-04
**Estado:** IMPLEMENTADA, INTEGRADA EN CLI/MENÚ, VERIFICADA EN FIXTURES, PUBLICADA Y SINCRONIZADA (c605b3e).
**Rama:** design/user-identity-association-v1
**Alcance:** R-01 aislada; no aplica runtime real.

## 1. Objetivo

Vincular de forma verificable cada validación estática/nativa con un perfil y una revisión exactos. El informe debe corresponder a los bytes JSON descifrados de esa revisión, nunca a una configuración independiente.

## 2. Cambios

### scripts/xray_profile_validation_store.py

Almacén/historial independiente de informes de validación de perfiles:

- Identidad persistente profile_id + revision.
- SHA-256 y tamaño de los bytes descifrados validados.
- Resultado PASS, PASS_WITH_WARNINGS, FAIL o INCOMPLETE.
- Comprobaciones, diagnósticos saneados, versión del validador y metadatos del binario Xray.
- Catálogo y hash del informe.
- Directorios root-owned 0700, archivos 0600, rechazo de symlinks/hardlinks y JSON estricto.
- Journal prepared/committed con recuperación rollback/roll-forward.
- API latest_for_revision() estrictamente read-only: no crea almacenes, no corrige permisos, no limpia huérfanos ni recupera journals. Si detecta una transacción pendiente, falla cerrado.
- No modifica ni reinterpreta los esquemas C-05B/C-05C ligados a config_id.

### scripts/xray_profile_validation.py

Servicio y CLI para validar una revisión exacta:

- Requiere profile_id y revision explícitos; no elige current_revision automáticamente.
- Usa el motor existente xray_config_validator.validate_configuration sobre los bytes exactos descifrados de ProfileStore.
- Persiste el informe en el almacén separado.
- Relee y vuelve a calcular el hash antes de actualizar el estado.
- Actualiza el manifiesto de la revisión y, únicamente si se valida current_revision, metadata.json en una transacción recuperable de ProfileStore.
- Una validación histórica no altera el resumen de la revisión actual.
- No aplica ni publica configuración ni inicia servicios.

Se amplió el journal transaccional de perfiles para admitir el manifiesto de una revisión exacta como destino permitido junto a metadata.json. Las operaciones update/restore limpian last_validated_revision cuando crean una nueva revisión no validada.

### scripts/xray_runtime_preflight.py

Preflight de solo lectura:

1. Abre el lock de perfiles en modo compartido, sin ejecutar ProfileStore.locked() (que también realiza limpieza).
2. Verifica previamente tipos, propietarios y permisos del árbol del perfil para impedir que las rutinas de lectura corrijan permisos.
3. Lee profile_id + revision exactos; verifica manifiesto, blob AES-GCM y hash del contenido descifrado.
4. Exige que el manifiesto de esa revisión esté validado.
5. Si la revisión seleccionada es current_revision, exige además que metadata.json indique valid y apunte a esa revisión. Para revisiones históricas, metadata.json resume current_revision y no invalida una revisión histórica cuyo manifiesto e informe siguen siendo válidos.
6. Recupera el informe de perfil más reciente y exige identidad, revisión, hash, tamaño y resultado PASS/PASS_WITH_WARNINGS coincidentes, con todas las comprobaciones obligatorias en PASS.
7. Exige que el hash del binario Xray del informe coincida con el binario seleccionado.
8. Lee un fixture root-owned 0600 para verificar unidad, usuario/grupo, binario y estado simulado. No consulta systemd real.
9. Devuelve PREFLIGHT_PASS con runtime_published=false y service_action_performed=false.

La consulta de informes es read-only y no crea el almacén. Si detecta un journal pendiente, falla cerrado sin recuperarlo.

### modules/profiles.sh

Se añadió la opción 8, “Validar revisión del perfil”, con selección explícita de perfil y revisión. Invoca el CLI usando las rutas configuradas y presenta el resultado persistido. La validación no equivale a activar runtime.

### Rutas

XRAY_MANAGER_PROFILE_VALIDATIONS_DIR en config/paths.sh apunta a /var/lib/xray-manager/profile-validations. El almacén se inicializa bajo demanda por su API de escritura; el preflight no crea el directorio.

## 3. Pruebas focales

- tests/test_xray_runtime_preflight.py: **18/18 PASS**.
- tests/test_xray_profile_validation.py: **10/10 PASS**.
- Total focal R-01: **28/28 PASS**.

Incluye revisión histórica, PASS/PASS_WITH_WARNINGS/FAIL/INCOMPLETE, informe ausente o discordante, binario incorrecto, corrupción de ciphertext, estados y permisos inseguros, symlinks, read-only, cambio concurrente de current_revision, actualización/restauración de perfiles, transacción de manifiesto+metadata y recuperación WAL.

Los perfiles, claves, informes, binarios y fixtures son sintéticos y se crean en directorios temporales.

## 4. Limitaciones conocidas

- CLI y menú están integrados, pero no se han ejecutado contra el almacén de perfiles ni la clave maestra reales. Todas las pruebas usan perfiles y claves sintéticos en directorios temporales.
- El fixture de estado de servicio no equivale a consultar systemd real.
- La validación nativa C-05A se ejecuta con la identidad del llamador; no demuestra todavía que el usuario xray pueda leer los leases TLS ni validar la configuración final de staging. Ese control corresponde a R-02.
- R-01 no publica configuración, no reinicia/inicia Xray, no prepara leases TLS y no prueba conectividad.
- R-02–R-05 no se implementaron en este incremento; R-06/live continúa NO AUTORIZADA.

## 5. Archivos

- scripts/xray_profile_validation_store.py — nuevo.
- scripts/xray_profile_validation.py — nuevo.
- scripts/xray_runtime_preflight.py — nuevo.
- tests/test_xray_runtime_preflight.py — nuevo.
- tests/test_xray_profile_validation.py — nuevo.
- scripts/xray_profiles.py — transacción admite manifiesto de revisión; update/restore limpian el puntero de validación actual.
- modules/profiles.sh — CLI y opción de menú para validar revisión exacta.
- config/paths.sh — ruta persistente de informes de perfil.
- docs/DISENO_APLICACION_RUNTIME_XRAY_2026-11-04.md — diseño corregido.

## 6. Estado

R-01 queda IMPLEMENTADA, INTEGRADA EN CLI/MENÚ, VERIFICADA EN FIXTURES y AUDITADA LOCALMENTE. No se ejecutó sobre el almacén/clave reales ni se probó runtime. La aceptación formal del propietario sigue pendiente. Etapa 5 permanece ABIERTA.
