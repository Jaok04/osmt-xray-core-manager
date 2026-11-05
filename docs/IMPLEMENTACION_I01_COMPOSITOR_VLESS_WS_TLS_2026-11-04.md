# Implementación I-01 — Compositor VLESS-WS-TLS para perfiles

**Fecha:** 2026-11-04
**Rama:** `design/user-identity-association-v1`
**VPS:** `Implementación-Xray:/opt/xray-manager`
**Estado al 2026-11-05:** IMPLEMENTADO / VERIFICADO EN FIXTURES / AUDITADO EN ALCANCE FOCAL / ACEPTADO FORMALMENTE CON LIMITACIONES / PUBLICACIÓN Y SINCRONIZACIÓN EN CURSO.

## 1. Objetivo y alcance

I-01 conecta las piezas ya existentes de Usuarios V2, configuración VLESS persistida, certificados centrales y almacén versionado de perfiles. El alcance inicial se limita deliberadamente a `protocol_id=vless_ws_tls`.

No crea una conexión, no activa un perfil, no valida Xray, no prepara leases, no publica runtime, no llama systemd y no inicia/reinicia servicios.

## 2. Componentes

- Nuevo `scripts/vless_ws_tls_composer.py`.
- Nueva suite focal `tests/test_vless_ws_tls_composer.py`.
- Reutiliza `scripts/vless_config_store.py` y sus validadores de configuración/certificado.
- Reutiliza el exportador oficial `users_v2_export_vless_candidate_clients` de `modules/users_v2.sh`.
- Reutiliza `xray_profiles.ProfileStore`, cifrado AES-256-GCM, revisiones inmutables y transacciones existentes.
- Emite el mapping que consume `scripts/xray_runtime_staging.py` / R-02.

No modifica el esquema de perfiles ni los módulos existentes de R-01–R-04.

## 3. Contrato de entrada

El CLI exige rutas explícitas para evitar defaults implícitos a datos live:

- `--profile-store`, `--master-key`, `--profile-id`, `--expected-revision`.
- `--connection-id`, `--connections-catalog`, `--connections-base`, `--connection-lock`.
- `--users-file`, `--users-lock`.
- `--certificate-catalog`.
- `--mapping-root`; opcionalmente `--existing-bindings` si el perfil ya tiene inbounds TLS.

Condiciones obligatorias:

1. El perfil y la revisión existen y la revisión esperada sigue siendo la actual.
2. La conexión existe exactamente una vez, es `vless_ws_tls`, está en `draft` y `runtime_applied=false`.
3. La configuración VLESS persistida coincide con el catálogo, tiene esquema/modalidad correctos y referencia un certificado central activo.
4. Usuarios V2 valida el almacén y exporta únicamente asociaciones VLESS activas, no vencidas y de esa conexión. Si no hay clientes válidos, no se genera un inbound vacío.
5. Los catálogos de conexiones y usuarios quedan bloqueados en lectura durante la composición para evitar carreras con escritores que respetan esos locks.
6. Si el perfil ya contiene TLS, se exige el mapping previo completo y exacto. No se inventan asociaciones para inbounds preexistentes.

## 4. Inbound producido

El inbound generado tiene esta forma lógica:

- `protocol: vless`.
- `settings.decryption: none`.
- `settings.clients`: UUID y `email=assoc:<association_id>` entregados por Usuarios V2.
- `streamSettings.network: ws`.
- `streamSettings.security: tls`.
- `wsSettings.path`: path de la configuración persistida.
- `tlsSettings.certificates: []`: R-02 inyecta los archivos temporales autorizados desde el almacén central.

El tag es `vless-<connection_id>`. Se rechazan tags/puertos en conflicto y UUID repetidos con otros inbounds. Se preservan los demás inbounds y outbounds del perfil.

## 5. Revisión y mapping auxiliar

- Se crea una revisión nueva mediante `ProfileStore.add_revision`; las revisiones anteriores no se sobrescriben.
- La metadata del perfil avanza a la nueva revisión y vuelve a `not_validated`; el manifiesto queda `pending`.
- Las asociaciones TLS se escriben en un archivo independiente:
  `<mapping-root>/<profile_id>/<revision>.json`.
- El documento conserva exactamente el esquema R-02: `{"schema_version":1,"bindings":[{"inbound_tag":"...","connection_id":"..."}]}`.
- Directorios root:root 0700; mapping root:root 0600; escritura atómica y fsync.
- El path enlaza de forma inequívoca el mapping al `profile_id` y a la revisión, sin alterar el JSON del perfil.
- Si la revisión se publica pero el mapping no puede escribirse, el comando informa `REVISIÓN INCOMPLETA`; no se oculta ni se borra la revisión. Está prohibido continuar a R-02 hasta recuperación explícita.

## 6. Concurrencia y límites

- Compara `expected_revision` dentro del lock exclusivo del almacén de perfiles.
- Mantiene locks compartidos de conexiones/usuarios durante lectura y composición.
- La validación de certificado central se repite en el momento de componer; R-02 volverá a resolver el certificado y comprobará sus dependencias.
- El mapping es un artefacto privado versionado por perfil/revisión. La UI de perfiles todavía no lo administra.
- I-01 aún no está integrado al menú de perfiles ni a una operación de usuario final.
- No incorpora Host WebSocket ni parámetros SNI/serverName del cliente; son parte de una brecha separada del recorrido de cliente.
- No prueba que la configuración completa pase `xray run -test`; eso pertenece al flujo posterior de validación/preflight.
- No se declara compatibilidad general con otras modalidades VLESS/VMess.

## 7. Ejecución controlada

La prueba se invoca con rutas explícitas de fixtures y claves sintéticas. No ejecutar el CLI apuntando a `/etc/xray-manager/keys/master.key`, almacenes operativos o catálogos live en esta fase.

## 8. Pruebas focales

`python3 -m unittest -v tests.test_vless_ws_tls_composer`

Casos cubiertos:

1. composición válida, selección de usuario activo y exclusión del suspendido;
2. inbound WS-TLS, certificado vacío para R-02, mapping privado y permisos;
3. lectura del mapping por el parser real de R-02;
4. preservación de inbounds anteriores y combinación exacta de mappings TLS;
5. revisión obsoleta / protección TOCTOU;
6. colisión de puerto;
7. mapping previo TLS ausente;
8. certificado central corrupto / fallo cerrado;
9. ausencia de usuarios candidatos activos;
10. UUID duplicado entre inbounds;
11. configuración VLESS persistida incoherente.

Resultado final: **10/10 pruebas focales PASS**. Regresión completa: **163/163 Python** y **58/58 scripts Bash** PASS; `py_compile`, `bash -n`, ShellCheck `-S error`, `git diff --check` e `install.sh --check` PASS.

## 9. Estado y siguiente paso

I-01 está implementado, verificado y auditado en el alcance focal descrito. El propietario otorgó aceptación formal el 2026-11-05 con las limitaciones documentadas. La autorización de commit/push se recibió por separado el 2026-11-05. La publicación y sincronización se registrarán tras su verificación. R-01–R-04 no se repiten; R-05 continúa en pausa; R-06/live sigue NO AUTORIZADA.

No modificar `main` ni `Xray-Normativa/`. No tocar Xray/systemd real, DNS, certificados desplegados, firewall, puertos, red, claves o almacenes live, dependencias ni VPS de pruebas.
