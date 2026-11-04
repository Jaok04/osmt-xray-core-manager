# Auditoría correctiva PF-08, PF-09 y PF-10 — 2026-11-04

## Alcance y autorización

Correcciones autorizadas por el propietario para la rama design/user-identity-association-v1, en /opt/xray-manager, host de desarrollo Implementación-Xray.

Alcance limitado al almacén de perfiles y sus pruebas. Se utilizaron exclusivamente almacenes temporales y claves sintéticas. No se leyó ni utilizó master.key; no se crearon perfiles live ni se modificó el runtime, Xray/systemd, certificados, firewall, puertos o red. No se modificaron main ni Xray-Normativa/. La publicación GitHub se realiza tras la autorización expresa recibida el 2026-11-04.

## PF-08 — revisión huérfana tras actualización rechazada

Hallazgo previo: update() publicaba una revisión antes de que commit_transaction() validara el tamaño de los datos del journal. Una descripción superior al límite transaccional podía hacer fallar la operación y dejar una revisión no referenciada.

Corrección: create() y update() validan previamente el tipo, longitud y contenido imprimible de descripción/notas (máximo 4096 caracteres); también validan que la configuración sea bytes entre 1 byte y MAX_CONFIG. En update(), estos controles ocurren antes de add_revision().

Prueba: cuatro casos inválidos (descripción excesiva, notas excesivas, configuración vacía y configuración superior a MAX_CONFIG) fueron rechazados. En todos, el conjunto de revisiones y el puntero actual permanecieron sin cambios.

## PF-09 — interrupción entre publicación de revisión y WAL

Hallazgo previo: add_revision() podía renombrar el directorio temporal a rNNNNNN y sufrir una interrupción antes de crear el WAL de la transacción que actualiza metadatos/catálogo. El limpiador previo sólo reconocía directorios temporales .revision-*.

Corrección: durante cada operación bajo el lock exclusivo, después de recuperar el WAL y limpiar temporales, el almacén reconcilia revisiones definitivas posteriores al puntero current_revision confirmado. Sólo elimina un candidato si el directorio y sus archivos cumplen propietario/permisos/tipo esperados, contiene exactamente config.enc.json y manifest.json, y el manifiesto coincide con el ID de perfil y revisión. Metadatos o artefactos no verificables se conservan y se reportan como anomalía. Las revisiones iguales o anteriores al puntero confirmado se conservan.

Prueba: inyección de SIGKILL después del rename de r000002 y al entrar al fsync del directorio de revisiones. Se verificó que r000002 quedó publicada tras la caída; la siguiente operación exclusiva conservó r000001 y eliminó únicamente r000002.

## PF-10 — contrato estricto de metadatos

Hallazgo previo: load_metadata() aceptaba coerciones y no verificaba el conjunto completo de campos, fechas, tipos y coherencia entre referencias de revisión y estados.

Corrección: validación exacta de campos; schema_version debe ser entero real (no booleano); identidad; nombre normalizado; descripción/notas imprimibles de hasta 4096 caracteres; fechas UTC reales y orden cronológico; tipos/formatos estrictos para current_revision y last_validated_revision; booleano real para config_present; coherencia de los punteros, existencia/permisos de las revisiones referenciadas y estados de validación reconocidos (un estado final exige una revisión validada).

Prueba: 18 metadatos malformados rechazados con ProfileError controlado, sin aceptar el objeto ni alterar la fixture válida.

## Archivos modificados

- scripts/xray_profiles.py
- tests/xray_profiles.sh

No se modificaron documentos normativos ni archivos de infraestructura.

## Verificación

- python3 -m py_compile scripts/xray_profiles.py: PASS.
- bash -n tests/xray_profiles.sh: PASS.
- shellcheck -S warning modules/profiles.sh tests/xray_profiles.sh: PASS.
- git diff --check: PASS.
- bash tests/xray_profiles.sh: PASS; incluye pruebas WAL/rollback, SIGKILL/limpieza, PF-07 (18 casos), PF-08 (4 casos), PF-09 (SIGKILL) y PF-10 (18 casos).
- Regresión completa tests/*.sh: 51/51 scripts PASS (ejecución finalizada con exit code 0).

shfmt -d -i 4 tests/xray_profiles.sh detecta diferencias de indentación preexistentes en bloques if del archivo (97 líneas de diff); no se aplicó reformateo global para evitar churn fuera del alcance.

## Estado y límites

PF-08, PF-09 y PF-10 quedan IMPLEMENTADOS Y VERIFICADOS EN PRUEBAS AISLADAS. Esto no equivale a aceptación formal del almacén v1.1 ni al cierre de Etapa 5 o Etapa 2. No se ejecutó validación live de perfiles, activación, backup/restore integral ni prueba externa.

GitHub: publicación autorizada el 2026-11-04 en design/user-identity-association-v1. Commit publicado: 46444bcf11b41750d45f2187d77eeb5f7fce654c. origin/design/user-identity-association-v1 y /opt/xray-manager en Implementación-Xray coinciden; árbol local limpio. main y Xray-Normativa/ permanecen intactas.
