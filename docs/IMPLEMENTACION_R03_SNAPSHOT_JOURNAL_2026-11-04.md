# Implementación R-03 — snapshot y journal de operación runtime

**Fecha:** 2026-11-04
**Estado:** IMPLEMENTADA Y VERIFICADA EN FIXTURES AISLADOS; AUDITORÍA LOCAL COMPLETADA; PENDIENTE DE ACEPTACIÓN FORMAL Y PUBLICACIÓN.
**Alcance:** snapshot, journal y recuperación simulada; sin publicación runtime ni acciones de servicio.

## 1. Contraste con el diseño y la normativa

Se implementó R-03 conforme a las secciones 3, 4, 5 y 7 del diseño aprobado. Se conserva la identidad profile_id + revision y se enlazan validation_id, hashes, asociaciones inbound tag → connection_id y leases del staging R-02.

Etapa 5 de Xray-Normativa/ sigue intacta. R-03 no habilita una vía de activación desde configuraciones independientes, no cambia el perfil, no publica runtime y no actualiza estados de usuarios/asociaciones.

## 2. Archivo y comandos

- scripts/xray_runtime_journal.py
- tests/test_xray_runtime_journal.py

Subcomandos:
- prepare: valida el staging/leases R-02, captura el estado previo del fixture y crea snapshot + journal.
- recover: recupera journals incompletos de manera idempotente.
- inspect: consulta un journal sin modificarlo.

No hay valores por defecto que apunten a /etc/xray, /var/lib/xray-manager o locks del sistema. Todos los directorios y locks se proporcionan explícitamente y requieren marcadores de fixture.

## 3. Barreras de aislamiento

R-03 exige simultáneamente:

1. XRAY_SERVICE_ROOT explícito, root:root 0711, con marcador .xray-manager-fixture cuyo propósito es xray-runtime-isolated-fixture.
2. operation_store explícito, root:root 0700, con marcador .xray-manager-r03-operations-fixture.
3. lifecycle_lock y application_lock distintos y contenidos dentro de operation_store/locks; el directorio de locks debe ser root:root 0700.
4. lease_root del staging R-02 con marcador .xray-manager-r02-leases-fixture y permisos root:grupo-servicio 0750. El manifiesto R-02 fija fixture_root, staging_dir y lease_root; R-03 comprueba que ambas rutas estén dentro del fixture y coincidan con el artefacto.
5. service-state fixture root:root 0600, binario/hash idénticos a los del staging y UID/GID simulados coincidentes.
6. Configuración staged, manifiesto y leases íntegros, regulares, sin symlinks/hardlinks y con permisos esperados.

El fixture de servicio representa /etc/xray/config.json como XRAY_SERVICE_ROOT/etc/xray/config.json. El script rechaza rutas simbólicas, archivos no regulares, hardlinks y permisos inesperados. No consulta systemd ni toca rutas reales.

## 4. Snapshot

Si existe configuración anterior:
- la lee sin modificarla;
- exige archivo root:grupo-servicio 0640, regular y sin hardlinks;
- copia los bytes exactos a operation_dir/snapshot/config.json;
- guarda SHA-256, tamaño, UID, GID y modo;
- persiste metadatos de snapshot root:root 0600.

Si no existe:
- registra present=false y no_previous_config=true;
- no crea config.json vacío ni placeholder;
- no borra ni crea archivos en XRAY_SERVICE_ROOT.

El snapshot incluye además el estado previo del servicio tomado exclusivamente del fixture (loaded, active/inactive/failed, subestado, usuario/grupo y binario), identidad profile_id/revision/validation_id, hash del staging y referencias de leases. No contiene PEM ni claves privadas.

## 5. Journal y recuperación

El journal es JSON estricto root:root 0600, dentro de una operación root:root 0700. Estados R-03:
- prepared
- validated
- snapshot_saved
- aborted
- recovery_required

Cada escritura se realiza con archivo temporal exclusivo, fsync del archivo, rename atómico y fsync del directorio. El snapshot de configuración y los metadatos se sincronizan antes de avanzar a snapshot_saved.

La recuperación:
- limpia sólo temporales atómicos reconocibles y seguros;
- elimina únicamente directorios huérfanos vacíos creados antes del primer journal;
- aborta operaciones interrumpidas antes de completar el snapshot, sin modificar runtime;
- completa el commit del snapshot si snapshot.json está íntegro y el journal quedó en prepared/validated por una interrupción;
- verifica de nuevo operaciones snapshot_saved;
- si hay corrupción o evidencia inesperada, conserva archivos y marca recovery_required;
- es idempotente.

Los leases no se liberan por R-03: siguen perteneciendo al staging y deberán conservarse hasta que R-04/R-05 determinen el ciclo de vida posterior a publicación/reemplazo del proceso.

## 6. Pruebas

Prueba focal tests/test_xray_runtime_journal.py: **22/22 PASS**.

Cobertura:
- snapshot de configuración previa y metadatos;
- no_previous_config sin placeholder;
- captura de estado active e inactive/failed como fixture;
- inspección read-only;
- matriz de seis puntos de interrupción y recuperación repetida;
- snapshot corrupto preservado como recovery_required;
- staging/hash/lease/binario discordantes;
- symlink/hardlink;
- ausencia de marcadores fixture;
- locks fuera del almacén o contendidos;
- operación huérfana sin journal y artefacto inesperado;
- ninguna escritura sobre el config runtime del fixture.

Regresión global al corte R-03:
- Python: 140/140 PASS.
- Shell: 58/58 PASS.
- py_compile: PASS.
- bash -n global: PASS.
- install.sh --check: PASS, sin modificar el sistema.
- shellcheck -S error tests/*.sh: PASS.
- git diff --check: PASS.

R-02 focal actualizado: 11/11 PASS. Su integración real usa Xray-core 26.10.31 y certificado/clave sintéticos bajo UID/GID simulado 65534:65534.

## 7. Límites y pendientes

- Sólo se utilizaron directorios, perfiles, claves, certificados, conexiones, fixtures y leases sintéticos.
- No se utilizó la clave maestra real ni almacenes live.
- No se escribió XRAY_SERVICE_ROOT/etc/xray/config.json; se leyó y snapshotteó únicamente la copia del fixture.
- No se publicó en /etc/xray/config.json.
- No se llamó systemctl, systemd, journalctl ni se inició/reinició Xray.
- No se tocaron runtime, certificados desplegados, firewall, puertos, red, dependencias ni VPS de pruebas.
- R-04 (publicación atómica aislada) y R-05 (orquestación systemd simulada) siguen pendientes.
- R-06/live y prueba NetMod siguen NO AUTORIZADAS.

R-03 no cierra Etapa 5, Etapa 2 ni Etapa 3.
