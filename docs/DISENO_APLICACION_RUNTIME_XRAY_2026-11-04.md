# Diseño técnico — aplicación segura de configuración runtime Xray

**Fecha:** 2026-11-04  
**Estado:** DISEÑO TÉCNICO AJUSTADO Y APROBADO PARA R-01–R-05 AISLADOS.
**Fecha de ajuste:** 2026-11-04.
**Precondición:** U-01 aceptada formalmente por el propietario y su auditoría aceptada.  
**Alcance autorizado:** desarrollo y pruebas de R-01–R-05 exclusivamente con perfiles/revisiones identificados, fixtures, datos sintéticos, almacenes temporales, mocks y `XRAY_SERVICE_ROOT` temporal en la VPS de desarrollo. R-06/live continúa expresamente NO AUTORIZADO.

## 1. Objetivo y límites

Permitir que el administrador aplique una revisión exacta, previamente validada, de forma controlada, verificable y recuperable. La operación debe distinguir claramente entre `validada`, `preparada`, `publicada`, `servicio activo` y `verificada`; ninguna de esas etiquetas debe inferirse de otra.

Fuera de alcance: instalar/actualizar Xray o dependencias; ACME/Cloudflare/DNS-01; importar o renovar certificados; cambios de firewall, puertos o red; migración legacy; activación en VPS de pruebas; y pruebas externas NetMod. Los secretos TLS deben resolverse mediante el almacén central y leases existentes, no copiarse al almacén de configuración ni imprimirse.

## 2. Arquitectura propuesta

1. **Selección inmutable de perfil:** el usuario elige `profile_id` y `revision` concretos. No se admite seleccionar una configuración independiente ni resolver silenciosamente `current_revision` después de la confirmación. El perfil contiene una copia JSON propia e independiente.
2. **Prueba de validación ligada al perfil:** la validación estática se ejecuta sobre los bytes descifrados que devuelve `ProfileStore.read_revision_config(profile_id, revision)`. El informe persistente debe identificar explícitamente ese `profile_id`, esa `revision`, el SHA-256 de los bytes exactos y los metadatos del validador/Xray. Se almacenará en un historial específico de validaciones de perfiles; no se reutilizarán informes C-05B/C-05C de configuraciones independientes.
3. **Preflight de estado read-only:** volver a leer el perfil/revisión exactos, comprobar integridad del manifiesto y blob cifrado, calcular el hash de los bytes descifrados, confirmar que el informe de perfil íntegro coincide con ambos identificadores y hash y que el resultado es PASS. Si falta el informe, está corrupto, no es PASS o no coincide el hash, abortar y exigir revalidación. No sustituir `profile_id` + `revision` por `config_id`.
4. **Materialización temporal:** descifrar sólo en un directorio temporal privado, con permisos mínimos, sin symlinks ni hardlinks, en filesystem adecuado; resolver certificados con leases de vida controlada. No dejar claves privadas en logs ni en directorios persistentes no protegidos.
5. **Composición:** producir una única configuración Xray completa a partir de la revisión exacta del perfil. Validar JSON estricto, estructura, referencias, rutas, listeners/puertos, ausencia de colisiones y política de certificados. La revisión aplicada debe conservar `profile_id`, `revision`, SHA-256 y el `validation_id` del informe de perfil.
6. **Validación final:** ejecutar el binario Xray exacto que usa systemd con `run -test -config` sobre los bytes ya materializados y con la identidad/permisos efectivos del servicio (`xray:xray`). No validar una copia distinta de la que se publicará.
7. **Snapshot de recuperación:** antes de tocar el destino, capturar de forma segura la configuración efectiva anterior, su hash, metadatos/permisos y estado previo del servicio. Si no hay configuración anterior, registrar explícitamente `no_previous_config`; no inventar una restauración.
8. **Publicación atómica:** escribir archivo temporal en el mismo filesystem/directorio del destino, establecer `root:xray` y modo `0640`, `fsync` del archivo, `rename` atómico a `/etc/xray/config.json` y `fsync` del directorio. Rechazar destinos/symlinks inesperados. Mantener journal durable con ID de operación y estados monotónicos.
9. **Aplicación del proceso:** Xray se administra mediante systemd. La estrategia aprobada es `systemctl restart xray.service` (no asumir hot reload). Capturar estado previo `active/inactive/failed`; no habilitar/deshabilitar el servicio como efecto lateral.
10. **Verificación posterior:** confirmar `systemd LoadState`, `ActiveState`, `SubState`, `Result`, `ExecMainStatus`; comprobar que el proceso corresponde a la unidad esperada; confirmar listeners esperados sin confundir puerto abierto con conectividad de cliente; consultar journal de la ventana de operación; y volver a verificar hash/permisos del archivo publicado. La prueba externa es una fase separada.
11. **Commit del estado:** marcar aplicación `verified` sólo si todos los controles pasan. Guardar referencia exacta a `profile_id`, `revision`, hash, `validation_id` del informe de perfil, binario Xray, operación, hora y resultado. No actualizar el estado de usuarios/asociaciones a runtime-applied hasta que la aplicación esté verificada.

## 3. Máquina de estados y journal

Estados propuestos: `prepared` → `validated` → `snapshot_saved` → `config_published` → `restart_requested` → `service_active` → `verified`.

Cualquier error posterior a `config_published` debe iniciar recuperación y quedar registrado como `rollback_started` → `rollback_config_restored` → `rollback_service_restored` → `rolled_back`. Si la restauración o el reinicio de recuperación fallan: `rollback_failed`, conservar journal y snapshot, bloquear nuevas aplicaciones y mostrar instrucciones de intervención; nunca borrar evidencia ni afirmar éxito.

El journal debe ser root-owned, modo `0600`, JSON estricto, versionado, limitado en tamaño y protegido contra symlinks/hardlinks. Debe registrar hashes y rutas controladas, no secretos. La recuperación tras SIGKILL/reinicio debe ser idempotente y distinguir entre publicación incompleta, servicio reiniciado y rollback parcial.

## 4. Política de rollback

- Si falla antes de publicar: borrar sólo temporales propios y liberar leases.
- Si falla después de publicar: restaurar bytes anteriores mediante el mismo mecanismo atómico y validar de nuevo la configuración restaurada antes de reiniciar.
- Si el servicio estaba activo antes: reiniciar la versión restaurada y exigir confirmación `active`.
- Si estaba inactivo antes: restaurar archivo sin arrancar el servicio; conservar el estado inactivo.
- Si no existía configuración previa: no borrar automáticamente el destino nuevo ni improvisar una configuración; dejar el sistema en estado de recuperación explícito y detener la operación para intervención controlada.
- No hacer rollback automático de datos de usuarios, certificados o almacenes centrales: la operación sólo revierte el archivo runtime y el estado de servicio asociado.

## 5. Concurrencia y seguridad

- Un único lock de ciclo de vida debe serializar start/stop/restart/enable/disable y aplicación/rollback.
- Lock de aplicación exclusivo para impedir dos publicaciones simultáneas.
- Revalidar revisión/hash inmediatamente antes de publicar (protección TOCTOU).
- Rechazar symlinks en cada componente sensible, archivos no regulares, hardlinks, permisos laxos, rutas fuera de allowlist y binarios no confiables.
- Nunca interpolar valores de usuario en comandos shell; usar `subprocess` con argumentos separados y entorno mínimo.
- No registrar UUID completos, claves, tokens Cloudflare, PEM ni contenido de configuración.
- Lease TLS debe mantenerse válido mientras Xray lo necesite; cleanup sólo después de confirmar proceso detenido/reemplazado y no mientras el proceso aún referencia esos archivos.
- Aplicar límites de tamaño, timeout, validación estricta y control de propietario/grupo.

## 6. Integración con componentes existentes

- `scripts/xray_config_promotion.py` valida y promueve informes/metadatos C-05C, pero su propio contrato indica que no modifica runtime. No reutilizar su término `promote` como sinónimo de aplicación.
- `scripts/xray_runtime_candidates.py` realiza staging y validación nativa de candidatos; su contrato también prohíbe publicar `/etc/xray/config.json` o iniciar Xray. Puede aportar patrones de staging, hashes, permisos y locks, no se debe convertir sin ampliar explícitamente su contrato.
- `modules/xray_service.sh` valida configuración runtime como usuario de servicio y serializa acciones de systemd mediante lock de ciclo de vida. La futura operación debe compartir el mismo lock, no competir con `xray_service_action`.
- `scripts/certificate_resolver.py` prepara leases TLS. Debe revisarse la duración y limpieza del lease frente al ciclo de vida del proceso Xray antes de diseñar la implementación final.
- La unidad systemd declara `ExecStartPre=/usr/local/bin/xray run -test -config /etc/xray/config.json` y `ExecStart=...`; reinicio implica volver a validar antes de ejecutar.

- El almacén scripts/xray_profile_validation_store.py mantiene informes separados ligados a profile_id + revision; no reutiliza C-05B/C-05C.
- scripts/xray_profile_validation.py conecta el motor C-05A con el almacén de informes de perfiles y actualiza manifiesto/metadata mediante transacción.
- scripts/xray_runtime_preflight.py implementa el contrato R-01 read-only. El estado systemd se suministra como fixture y no consulta la unidad real.

## 7. Plan de implementación por incrementos

- **R-01 — contrato y preflight read-only:** resolver `profile_id` + `revision`, integridad del perfil, hash de bytes descifrados, informe de validación de perfil, binario/identidad y estado de servicio; sin publicar ni reiniciar.
  Estado: implementada, integrada en CLI/menú y verificada en fixtures; no ejecutada sobre el almacén/clave real.
- **R-02 — staging integrado:** IMPLEMENTADA Y VERIFICADA LOCALMENTE. El CLI scripts/xray_runtime_staging.py ensambla la revisión exacta del perfil, resuelve leases TLS centrales mediante un mapa inbound_tag → connection_id, valida bajo UID/GID no privilegiados simulados y no publica runtime. Expedientes: docs/IMPLEMENTACION_R02_STAGING_PERFIL_TLS_2026-11-04.md y docs/AUDITORIA_R02_STAGING_PERFIL_TLS_2026-11-04.md. Pendiente de aceptación formal y publicación.
- **R-03 — journal y snapshot:** IMPLEMENTADA Y AUDITADA LOCALMENTE. scripts/xray_runtime_journal.py captura snapshot y journal en XRAY_SERVICE_ROOT/operation_store fixtures marcados, y recupera interrupciones de forma idempotente; no publica runtime ni llama systemd. Expedientes: docs/IMPLEMENTACION_R03_SNAPSHOT_JOURNAL_2026-11-04.md y docs/AUDITORIA_R03_SNAPSHOT_JOURNAL_2026-11-04.md. Pendiente de aceptación formal/publicación.
- **R-04 — publicación atómica aislada:** IMPLEMENTADA/VERIFICADA. Ver §15 y expedientes R-04; 12/12 focal PASS.
- **R-05 — orquestación systemd simulada:** usar adaptador/mocks para start/restart/status y fallos; demostrar preservación de estado previo y rollback idempotente.
- **R-06 — ensayo live controlado:** requiere autorización nueva y específica, backup verificable, preflight de VPS, ventana de cambio y criterios de abortar. No queda autorizado por aprobar este diseño.

## 8. Matriz mínima de aceptación

| ID | Caso | Resultado requerido |
|---|---|---|
| R01 | revisión exacta con informe PASS o PASS_WITH_WARNINGS y checks requeridos PASS | permite preflight |
| R02 | revisión seleccionada distinta de la validada | aborta sin publicar |
| R03 | informe de perfil ausente, corrupto, no PASS o con identidad/hash discordantes | aborta sin publicar |
| R04 | Xray rechaza bytes finales | aborta sin publicar |
| R05 | certificado/lease ausente, vencido o inconsistente | aborta sin publicar |
| R06 | symlink/hardlink/permisos inseguros | falla cerrado |
| R07 | dos aplicaciones concurrentes | serialización, una sola publicación |
| R08 | error antes de rename | destino anterior intacto |
| R09 | SIGKILL antes/después de rename | recuperación determinista con journal |
| R10 | restart falla | restaura config y estado de servicio previo |
| R11 | servicio estaba inactivo | rollback no lo arranca |
| R12 | rollback falla | conserva evidencia y bloquea nueva aplicación |
| R13 | listeners inesperados/ausentes | no marca `verified` |
| R14 | logs/errores | no revelan UUID, claves ni PEM |
| R15 | reintento tras operación verificada | idempotente; no duplica publicación |

## 9. Decisiones confirmadas por el propietario

1. Estrategia inicial `systemctl restart xray.service`: APROBADA; no se presupone hot reload.
2. Primera aplicación sin configuración anterior: detenerse en recuperación explícita; no crear placeholder ni autoarrancar Xray.
3. Rollback: restaurar la configuración previa; si el servicio estaba activo, exigir que vuelva a activo; si estaba inactivo, no arrancarlo.
4. Verificación de aplicación: incluir estado systemd, listeners locales y journal. La conectividad WAN/NetMod permanece como prueba separada.
5. R-01–R-05: desarrollo y pruebas exclusivamente con fixtures, datos sintéticos, almacenes temporales, mocks y `XRAY_SERVICE_ROOT` temporal en la VPS de desarrollo.
6. R-06/live: NO AUTORIZADA; requiere autorización nueva, explícita y específica.

## 10. Límites de ejecución y autorización

R-01–R-05 están autorizadas únicamente en entornos aislados y desechables. Esto no autoriza escribir `/etc/xray/config.json`, instalar Xray o dependencias, crear/modificar la unidad o usuario real de servicio, iniciar/reiniciar Xray real, abrir puertos, tocar firewall/red, importar/renovar certificados reales, ejecutar ACME/Cloudflare, acceder a la clave maestra real, utilizar la VPS de pruebas ni probar NetMod. R-06/live requiere autorización nueva, explícita y específica. Ningún incremento cierra una etapa por sí solo.

## 11. Decisiones aprobadas por el propietario — 2026-11-04

El propietario aprobó expresamente las siguientes decisiones de diseño:

- **Reinicio controlado:** usar `systemctl restart xray.service` como estrategia inicial de aplicación; no asumir hot reload. El reinicio sólo se solicitará después de staging, validación final, snapshot durable y publicación atómica, bajo el lock de ciclo de vida compartido.
- **Rollback:** si la aplicación falla después de publicar, restaurar atómicamente la configuración anterior y recuperar el estado previo del servicio. Si estaba activo, exigir que vuelva a quedar activo; si estaba inactivo, no arrancarlo. Si no había configuración previa, detenerse en estado de recuperación explícito y no inventar una configuración anterior.

Estas aprobaciones son decisiones de diseño. La aprobación posterior del propietario autoriza R-01–R-05 exclusivamente en entornos aislados; no autoriza R-06/live.


## 12. Corrección normativa aprobada — identidad de perfil y revisión (2026-11-04)

El propietario aprobó corregir el diseño para que el flujo runtime trabaje exclusivamente con `profile_id` + `revision`, de acuerdo con el apartado 3.1 de Etapa 5: las configuraciones independientes no son una vía alternativa de activación; la activación se realiza mediante perfiles. También se respetan los apartados 4.1, 5 y 7: la validación estática es obligatoria, guardar/seleccionar no activa y el perfil destino debe estar validado antes de aplicar.

### 12.1 Informe persistente específico de perfil

Se implementará un almacén/historial independiente para informes de validación de perfiles, sin alterar el esquema ni reinterpretar C-05B/C-05C. Cada informe contendrá, como mínimo:

- `validation_id` único y `schema_version`.
- `profile_id` y `revision` exactos.
- `content_sha256` y `content_size_bytes` de los bytes JSON descifrados y validados.
- Resultado global: PASS, PASS_WITH_WARNINGS, FAIL o INCOMPLETE; comprobaciones, diagnósticos saneados y fecha UTC.
- Versión/hash del binario Xray utilizado cuando aplique, además de versión del validador.
- Hash íntegro del informe, verificado contra su catálogo.

El informe se generará a partir de los bytes devueltos por `ProfileStore.read_revision_config(profile_id, revision)`, que verifica manifiesto, identidad, blob cifrado y hash. El preflight repetirá esa lectura y comprobará que el hash de contenido coincide con el informe. El vínculo no dependerá de que la revisión siga siendo `current_revision`: las revisiones históricas inmutables podrán validarse y consultarse por su ID exacto.

### 12.2 Estados y autoridad

El estado validation del manifiesto es específico de cada revisión; los metadatos del perfil resumen el estado de current_revision. Ninguno de esos resúmenes sustituye el informe persistido. El preflight exigirá:
1. manifiesto y contenido íntegros para el profile_id + revision seleccionado;
2. manifiesto de esa revisión en estado valid;
3. informe persistido de perfil, íntegro, PASS o PASS_WITH_WARNINGS, con todas las comprobaciones obligatorias en PASS, la misma identidad y el mismo content_sha256;
4. si la revisión seleccionada es current_revision, metadatos del perfil en estado valid y last_validated_revision igual a esa revisión. Si es histórica, no se comparará contra el resumen de la revisión actual: mandan el manifiesto y el informe de la revisión histórica.

Al crear una revisión nueva mediante update/restore, el resumen del perfil actual vuelve a not_validated y su puntero last_validated_revision se limpia; los manifiestos e informes de revisiones históricas se conservan. Validar una revisión histórica actualiza su manifiesto e informe, pero no cambia el resumen de la revisión actual.

La ausencia o inconsistencia de cualquiera de estos elementos produce rechazo seguro. Un informe C-05B/C-05C asociado a `config_id` nunca satisface este requisito. Los informes de perfil son historial técnico interno y no se incluirán en respaldos, conforme al apartado 8 de Etapa 5 (exclusión de historiales).

### 12.3 Reglas para R-01–R-05

Todas las estructuras de operación, staging, snapshot, journal, publicación simulada y rollback conservarán `profile_id`, `revision`, `validation_id` y `content_sha256`. No se añadirá una ruta de aplicación directa desde configuraciones independientes. Las pruebas deben incluir perfiles sintéticos, revisiones múltiples, perfiles duplicados, informe ausente/corrupto/no PASS, discordancia de identidad/hash, revisión histórica y cambio de `current_revision` posterior a seleccionar la revisión.

Esta corrección fue aprobada por el propietario antes de implementar R-01. La autorización se limita a R-01–R-05 aisladas; no amplía el alcance a R-06/live.


## 13. R-02 implementada — asociación explícita inbound/connection (2026-11-04)

El propietario aprobó el mecanismo explícito inbound tag → connection_id. El contrato R-02 recibe un archivo JSON de asociaciones root:root 0600; el mapa se normaliza, se valida y su hash/contenido quedan fijados en el manifiesto del staging. Cada inbound TLS debe tener exactamente una asociación y no se permiten tags/conexiones duplicados ni inbounds TLS omitidos.

El mapa no aporta certificate_id, PEM ni rutas privadas. R-02 resuelve la conexión central VLESS/VMess, obtiene certificate_id desde security_options y llama al resolutor central, que vuelve a verificar la conexión y genera el lease. El perfil debe dejar tlsSettings.certificates ausente o vacío; el staging inyecta las rutas temporales. La revisión cifrada del perfil no se modifica.

Se implementó scripts/xray_runtime_staging.py y tests/test_xray_runtime_staging.py. Se valida la revisión y el informe R-01 antes y después de resolver leases, se comprueba el hash exacto, se escribe la configuración staged root:grupo-servicio 0640 dentro de directorio 0750 y se ejecuta Xray run -test con UID/GID no privilegiados simulados. El manifiesto conserva fixture_root, staging_dir y lease_root, además de profile_id, revision, validation_id, hash del perfil/mapa/config final, asociaciones, IDs de leases e identidad/binario; no contiene PEM ni claves.

R-02 focal 9/9 PASS; regresión Python 117/117 PASS; shell 58/58 PASS; py_compile, bash -n, install.sh --check, ShellCheck severidad error y git diff --check PASS. En la VPS de desarrollo Xray-core 26.10.31 real aceptó la configuración staged y leyó el certificado/clave sintéticos como UID/GID 65534:65534. No se consultó ni reinició systemd real.

Limitación deliberada: el mapa de asociaciones es una entrada explícita externa a la revisión, fijada criptográficamente en el artefacto staged; su gestión persistente/UI no forma parte de R-02. Los leases exitosos permanecen para R-03. R-03–R-05 siguen pendientes; R-06/live no autorizada. R-02 está pendiente de aceptación formal y publicación.


## 14. R-03 implementada — snapshot y journal aislados (2026-11-04)

R-03 incorpora scripts/xray_runtime_journal.py y tests/test_xray_runtime_journal.py. La operación valida el staging R-02 y sus leases, comprueba que el binario conserva hash/tamaño, verifica el fixture de estado del servicio y captura la configuración previa desde XRAY_SERVICE_ROOT/etc/xray/config.json.

El alcance está protegido con marcadores obligatorios:
- XRAY_SERVICE_ROOT: .xray-manager-fixture.
- operation_store: .xray-manager-r03-operations-fixture.
- lease_root: .xray-manager-r02-leases-fixture.

Los locks lifecycle/application deben ser distintos y residir dentro de operation_store/locks. El manifiesto R-02 fija fixture_root, staging_dir y lease_root, y R-03 verifica que staging y leases permanecen dentro del mismo fixture marcado. R-02 fue endurecida para exigir fixture_root con marcador, mantener todos los almacenes/claves/catálogos/locks/mapa/staging/leases dentro del fixture y eliminar defaults hacia rutas live; el binario Xray es el único recurso externo permitido y se verifica por hash.

El snapshot guarda bytes anteriores root:root 0600, metadatos de propietario/grupo/modo/hash/tamaño, estado de servicio fixture, profile_id, revision, validation_id, hashes de staging/mapa/config final y leases. Si no existe configuración anterior, registra no_previous_config y no crea placeholder. El journal root:root 0600 avanza prepared → validated → snapshot_saved; la recuperación también contempla aborted y recovery_required. Los writes usan temporal exclusivo, fsync, rename y fsync de directorio.

La recuperación maneja seis failpoints de prueba, huérfanos previos al primer journal, temporales atómicos, snapshot completo con journal atrasado, corrupción y reintentos idempotentes. No modifica XRAY_SERVICE_ROOT/etc/xray/config.json, no publica runtime y no ejecuta systemd.

R-03 focal 22/22 PASS; R-02 focal 11/11 PASS; regresión Python 153/153 PASS; shell 58/58 PASS; py_compile, bash -n, install.sh --check, ShellCheck severidad error y git diff --check PASS. Expedientes: docs/IMPLEMENTACION_R03_SNAPSHOT_JOURNAL_2026-11-04.md y docs/AUDITORIA_R03_SNAPSHOT_JOURNAL_2026-11-04.md.

R-03 está pendiente de aceptación formal/publicación. R-04 (publicación atómica aislada) y R-05 (systemd simulado) siguen pendientes. R-06/live NO AUTORIZADA.


## 15. R-04 implementada — publicación atómica y rollback aislados (2026-11-04)

R-04 incorpora `scripts/xray_runtime_publisher.py` con `publish`, `rollback`, `recover` e `inspect`. Solo opera sobre el XRAY_SERVICE_ROOT fixture marcado y el operation_store R-03. Valida journal/snapshot, staging exacto profile_id + revision + validation_id, mapa, leases TLS y binario Xray.

La publicación crea temporal exclusivo root:grupo-servicio 0640 en el mismo directorio del destino, fsync, valida con `xray run -test -config` bajo UID/GID simulado, repite la comprobación TOCTOU y hace rename atómico. Luego fsync del directorio, verifica hash/propietario/permisos y actualiza journal. No toca systemd ni el Xray real.

El rollback repone bytes exactos del snapshot mediante rename atómico y valida la configuración restaurada. Si no existía configuración previa, no elimina la primera configuración publicada: deja `recovery_required`. Recuperación detecta renames interrumpidos, limpia temporales seguros y es idempotente en los failpoints cubiertos.

El journal ahora persiste publication/rollback con validación estricta de estado y metadatos. Pruebas: R-04 12/12; R-03 journal 22/22; R-02 staging 11/11; Python 153/153; shell 58/58 PASS. Integración R-02→R-03→R-04 verificada en fixture. Expedientes: `docs/IMPLEMENTACION_R04_PUBLICACION_ATOMICA_2026-11-04.md` y `docs/AUDITORIA_R04_PUBLICACION_ATOMICA_2026-11-04.md`.

R-04 queda pendiente de aceptación formal/publicación. R-05 (systemd simulado) pendiente. R-06/live, runtime real y prueba NetMod no autorizadas.
