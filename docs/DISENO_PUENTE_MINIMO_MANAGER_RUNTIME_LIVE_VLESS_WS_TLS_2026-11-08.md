# Diseño del puente mínimo Manager → runtime live para el primer VLESS-WS-TLS

**Fecha:** 2026-11-08
**Estado:** DISEÑO TÉCNICO; no implementado; no autoriza operaciones live.
**Rama:** `design/user-identity-association-v1`
**Objetivo del producto:** primer servicio VLESS + WebSocket + TLS en `pruebas.tvrc.me:443`, gestionado desde Xray-Core Manager y comprobado mediante conexión externa bidireccional.

## 1. Decisión ejecutiva

El camino más corto y coherente con el código existente es **conservar el modelo actual de `xray.service`: Xray ejecutado directamente como `xray:xray`**. El Manager (root) prepara staging, snapshots, journal y evidencia root-only; delega start/restart exclusivamente en `modules/xray_service.sh` mediante el puente de lock verificado; observa systemd y correlaciona el proceso después de la transición.

No se recomienda convertir ahora `xray.service` en un supervisor root que haga `setpriv` para lanzar Xray. Esa alternativa del prototipo B4.2/B4.3 implicaría cambiar la unidad, el contrato del observador systemd, argv esperado, capacidades, ownership de `StateDirectory`/`RuntimeDirectory`, permisos y sandbox. No es necesaria para el primer servicio y contradice el contrato de unidad que ya existe en `modules/xray_service.sh` y `scripts/xray_runtime_systemd_adapter.py`.

B4.3-A/B se conserva como experimento fixture de evidencia persistente y como referencia de controles de filesystem. **No se conectará directamente `run_fixture_xray_validation()` al daemon real**: hoy ejecuta `xray run -test`, no el proceso servidor de systemd. Su `prepared_before_exec` tampoco demuestra que el daemon cargó una generación.

## 2. Línea base comprobada en el código

| Necesidad | Componente existente | Estado y límite |
|---|---|---|
| Crear inbound VLESS-WS-TLS | `modules/vless_assistant.sh`, `scripts/vless_config_store.py`, `scripts/vless_prepare_config.py` | Funcionalidad de conexión; no aplica runtime |
| Componer perfil/revisión | `scripts/vless_ws_tls_composer.py`, I-01/I-02 | Crea revisión inmutable y mapping privado por perfil/revisión |
| Host WebSocket y SNI cliente | I-03 | Persistidos separadamente; no confundirlos con TLS del inbound |
| Exportar cliente | `scripts/vless_client_export.py`, I-04 | Implementado con validación de certificado; el endpoint debe ser el aprobado para esta instalación |
| Certificado central y lease | `certificate_store.py`, `certificate_resolver.py`, `certificate_acme.py` | Almacén/resolutor y ACME existen; emisión/consumo live para este dominio aún debe verificarse |
| Preflight y staging | `xray_runtime_preflight.py`, `xray_runtime_staging.py` | R-01/R-02 fixture-only; `stage()` exige marcadores y rutas dentro del fixture |
| Snapshot, journal y publicación | `xray_runtime_journal.py`, `xray_runtime_publisher.py` | R-03/R-04 fixture-only; validan marcadores y confinan filesystem al fixture |
| Orquestación | `xray_runtime_orchestrator.py` | R-05 fixture-only; `_with_service_backend` rechaza un backend live y el default es fixture |
| Menú de aplicación | `modules/profiles.sh`, `xray_runtime_menu_bridge.py` | La acción disponible es explícitamente fixture; el puente exige rutas dentro del fixture |
| Unidad y control del servicio | `modules/xray_service.sh` | Unidad definida con `User=xray`, `Group=xray`, `ExecStartPre` y `ExecStart` directos de Xray; acciones delegadas al controlador único |
| Observación systemd | `xray_runtime_systemd_adapter.py` | Read-only; valida unidad, configuración y estado; no muta systemd |
| Identidad del proceso | `xray_runtime_process_attestation.py` | Correlaciona PID, InvocationID, starttime, ejecutable, argv y UID/GID; no afirma qué bytes están cargados |
| Puente de acción | `xray_runtime_service_control.py` | Start/restart/stop delegados a `xray_service.sh`; exige descriptor lifecycle lock FLOCK del propietario esperado |
| Backend live | `xray_runtime_live_backend.py` | Aislado; exige evidencia live de operación/generación; `restore()` falla cerrado |
| Evidencia de operación | `xray_runtime_operation_evidence.py` | Verifica cadena journal→validación→staging→publicación, pero fuerza `environment=fixture`; backend live la rechaza |
| Evidencia B4.3 | almacén y supervisor B4.3-A/B | Fixture-only; `prepared_before_exec` es evidencia de preparación del proceso de prueba, no del daemon systemd |

## 3. Compatibilidad de la arquitectura de servicio

### 3.1 Plantilla de unidad administrada que debe conservarse para el MVP

`modules/xray_service.sh` genera la siguiente plantilla administrada (no implica que esté instalada en la VPS Pruebas):

- `User=xray`, `Group=xray`.
- `ExecStartPre=/usr/local/bin/xray run -test -config /etc/xray/config.json`.
- `ExecStart=/usr/local/bin/xray run -config /etc/xray/config.json`.
- `StateDirectory=xray`, `StateDirectoryMode=0750`.
- `RuntimeDirectory=xray`, `RuntimeDirectoryMode=0750`.
- `NoNewPrivileges=true`, `ProtectSystem=strict`, `PrivateTmp=true`, `PrivateDevices=true` y otras restricciones.
- `CapabilityBoundingSet=CAP_NET_BIND_SERVICE` y `AmbientCapabilities=CAP_NET_BIND_SERVICE`.

El observador systemd está diseñado para validar expresamente `User=xray`, `Group=xray`, el `ExecStart` y `ExecStartPre` directos, `Type=simple`, la unidad exacta y ausencia de drop-ins.

### 3.2 Por qué no se cambia a supervisor root

El diseño B4.2/B4.3 propone un supervisor `User=root`, `Group=xray` que conserva capacidades `CHOWN/SETUID/SETGID/NET_BIND_SERVICE` y desciende a `xray:xray`. Su layout fixture usa `root:xray 0770` para estado/runtime y evidencia root-only con `ReadWritePaths` específico.

Eso no coincide con la unidad actual: cambiar `User=`/`ExecStart` obliga a actualizar el observador, la atestación de proceso, el controlador de servicio, los permisos y el sandbox; también requiere probar el descriptor memfd y el gate dentro de systemd real. No se hará ese cambio en el MVP sin una decisión arquitectónica separada.

La evidencia live puede ser escrita por el Manager root fuera del proceso Xray. Xray no necesita acceso a la carpeta root-only de evidencia. Por tanto, no se añadirá `ReadWritePaths` para evidencia a la unidad actual.

## 4. Flujo end-to-end mínimo propuesto

1. **Seleccionar revisión:** desde Gestión de perfiles, elegir `profile_id` + `revision` exactos. No inferir `current_revision` si el usuario seleccionó otra revisión.
2. **Validar:** reutilizar informe persistido de perfil y `xray run -test` de R-01 con la versión/binario fijados.
3. **Resolver asociaciones:** reutilizar el mapping I-01/I-02 guardado en `<profile-bindings>/<profile_id>/<revision>.json`; no pedir un archivo manual si ya existe mapping generado por el compositor.
4. **Resolver TLS:** por cada inbound TLS, resolver `connection_id` y `certificate_id` central; preparar un lease temporal con `certificate_resolver`. No aceptar PEM/rutas libres desde el perfil.
5. **Staging live:** producir configuración final en un directorio temporal administrado por root, con acceso de lectura limitado a `xray:xray`; validar bytes exactos con `xray run -test` como `xray:xray`. No invocar el `stage()` fixture actual con rutas live ni relajar sus marcadores.
6. **Preparar operación:** generar `operation_id` y `generation_id`; adquirir lifecycle lock y application lock en orden fijo; reobservar estado; guardar snapshot exacto de la configuración anterior (si existe), metadatos, hash, estado systemd/proceso, identidad de perfil/revisión/validación, hash de staging y leases.
7. **Publicar:** crear temporal root-owned en el mismo filesystem de `/etc/xray`, propietario final `root:xray`, modo `0640`; validar antes de rename; fsync del archivo y directorio; reemplazo atómico; volver a verificar inode/hash/permisos.
8. **Decidir transición:** si el servicio estaba `active`, exigir confirmación explícita para `restart`; si estaba `inactive`, persistir `published_pending_start` y no iniciar automáticamente; si está `failed`, `unknown`, `activating` o no es verificable, no publicar/continuar y dejar recuperación controlada.
9. **Delegar acción:** usar `LiveRuntimeBackend` y `xray_runtime_service_control.run_action()`, heredando el descriptor lifecycle lock que el Manager ya posee. El único ejecutor de systemctl sigue siendo `modules/xray_service.sh`.
10. **Observar:** después de start/restart, consultar systemd y atestar MainPID/InvocationID/starttime/ejecutable/argv/UID/GID. Registrar por separado `runtime_config_sha256` y la identidad del proceso. No declarar `loaded_config_sha256` ni `configuration_loaded=true` sin una fuente específica que lo demuestre.
11. **Finalizar o recuperar:** persistir estado terminal; ante timeout/respuesta perdida, reobservar antes de cualquier reintento; ante drift/ambigüedad, `RECOVERY_REQUIRED`. Rollback de archivo y recuperación del servicio son estados distintos.
12. **Prueba externa:** solo tras servicio local verificado, comprobar DNS, TLS/SNI, WebSocket, autenticación VLESS y tráfico bidireccional desde cliente externo, con autorización de red/puertos correspondiente.

## 5. Componentes mínimos que faltan para el puente live

### L1 — almacén live de operación/evidencia

Crear un almacén root-only separado del journal fixture, con schema estricto y estado transaccional. Ubicación propuesta, pendiente de validar con el contrato de directorios del Manager: `/var/lib/xray-manager/runtime-operations/` (directorios `root:root 0700`, archivos `root:root 0600`). No reutilizar el marcador fixture ni cambiar `xray_runtime_journal` para aceptar live.

Debe enlazar `operation_id`, `generation_id`, `profile_id`, `revision`, `validation_id`, hashes de perfil/mapping/staging/publicación, snapshot previo, leases, estado inicial systemd, confirmación, acción solicitada, observaciones posteriores, InvocationID/MainPID y estado de recuperación. No guardar UUID, PEM, clave privada ni bytes de configuración dentro del journal; el snapshot cifrado o los bytes de configuración se conservan en artefacto privado con hash y permisos propios.

El lector que consume `LiveRuntimeBackend` debe devolver `environment=live` sólo después de verificar esa cadena completa. El lector actual de R-05 devuelve fixture y debe seguir siendo rechazado por el backend live.

### L2 — staging live sin debilitar R-02 fixture

Extraer la lógica pura de lectura/validación/composición de R-02 para compartirla entre dos envolturas explícitas:

- `stage_fixture`: conserva exactamente los marcadores y confinamiento actuales.
- `stage_live`: exige almacenes centrales administrados, locks reales, rutas exactas, lease TLS central, permisos y política de temporales live.

No permitir que una variable de entorno cambie de fixture a live. La selección live debe ser una llamada interna explícita y no estar disponible en el CLI general hasta superar auditoría.

### L3 — publicador y rollback live

Crear el adaptador de filesystem live mínimo o extraer primitivas seguras del publicador fixture sin permitir que rutas fixture se resuelvan contra `/`. Debe cubrir snapshot, publicación atómica, validación de Xray, verificación post-rename, rollback de bytes y recuperación tras crash. Si no hay configuración previa, no inventar placeholder ni borrar la primera configuración tras un fallo; persistir `RECOVERY_REQUIRED` y detenerse.

### L4 — orquestador live separado

No habilitar el backend live mediante un simple cambio del default de R-05. El decorador `_with_service_backend` hoy lo bloquea deliberadamente. Crear un entrypoint interno live con inyección explícita de `LiveRuntimeBackend`, almacén live y publicador live; el flujo fixture existente debe permanecer intacto y predeterminado.

Resolver antes los límites abiertos de H6-G2/G3: evidencia live F-02, ownership del lock, timeout/response-lost, rollback archivo+proceso y reconciliación durable. `restore()` del backend live no puede permanecer como stub si se va a ofrecer apply/start.

### L5 — menú live separado y confirmaciones

La opción actual `profiles_apply_fixture_menu` debe seguir diciendo fixture-only. Añadir un flujo live sólo después de L1–L4 y revisión independiente; debe seleccionar revisión exacta, mostrar dominio/puerto/certificado/estado previo, solicitar confirmación adecuada y distinguir `published_pending_start`, `published_pending_apply`, `verified` y `RECOVERY_REQUIRED`.

No permitir que `XRAY_RUNTIME_MENU_FIXTURE_MODE` o una variable similar active live accidentalmente.

## 6. Parámetros concretos del primer servidor

- Dominio objetivo: `pruebas.tvrc.me`.
- Transporte: VLESS + WebSocket + TLS.
- Puerto público: `443/TCP`.
- Certificado: catálogo central y lease; emisión ACME real aún no demostrada en el host objetivo.
- Host WebSocket y SNI del cliente: propiedades distintas; reutilizar I-03, no inferirlas una de otra.
- El menú de exportación tiene un default histórico `hellen.tvrc.me`; antes de exportar el primer cliente debe seleccionar explícitamente `pruebas.tvrc.me` o cambiar el default mediante una modificación aprobada y probada. No usar el endpoint antiguo por accidente.
- El mapping inbound tag → connection_id ya se genera por I-01/I-02 y se guarda por perfil/revisión; R-02 lo consume. No crear un segundo sistema de mapping.

## 7. Bloqueos y puertas previas

1. H6-G2 permanece abierto: el backend live no está integrado; evidencia live F-02 y restore/rollback F-05 no están disponibles como flujo end-to-end.
2. H6-G3 A-D se implementó en fixtures; G3-E fue segunda pasada de la misma sesión. El paquete `docs/PAQUETE_REVISION_INDEPENDIENTE_H6G3_2026-11-06.md` exige revisión por otro revisor humano/IA antes de integración live.
3. B4.3-A/B es fixture-only; su revisión técnica posterior tampoco es auditoría externa independiente.
4. VPS Pruebas no tiene aún unidad/configuración runtime activa; la inspección anterior encontró Xray instalado, `/etc/xray` y `xray.service` ausentes, sin listener 80/443 y certificado pendiente. No se ha revalidado en este diseño.
5. Certificado ACME, DNS, disponibilidad de puerto 80 para HTTP-01 o TXT para DNS-01, firewall y conectividad WAN requieren comprobación y autorización específica.
6. La unidad y el layout propuestos por B4.3 no se deben aplicar a la unidad actual sin resolver la diferencia de identidad/permisos descrita en §3.

## 8. Orden recomendado

1. Obtener revisión externa independiente de H6-G3 con el paquete existente, sin modificar el árbol ni realizar acciones live.
2. Implementar L1 en fixtures con pruebas de esquema, integridad, locking, durabilidad y recuperación; después diseñar su ubicación live final.
3. Separar la lógica pura de staging y diseñar L2 sin alterar el confinamiento de R-02 fixture.
4. Diseñar/implementar L3 con crash matrix y rollback de primera configuración.
5. Integrar L4 con el backend live existente, corregir los hallazgos de G2 y auditar toda la cadena.
6. Implementar L5 manteniendo el flujo fixture separado.
7. Solicitar autorización live específica por host/operación; preparar servicio/certificado/configuración desde Manager; comprobar estado local y luego cliente externo.

## 9. Exclusiones expresas

Este documento no autoriza crear `xray:xray`, instalar Certbot, solicitar certificados, modificar `/etc/xray`, escribir unidades, ejecutar `systemctl`, abrir puertos, modificar firewall/DNS/red, iniciar/reiniciar Xray ni utilizar VPS Pruebas. No se modifica `modules/xray_service.sh`, R-05, backend live, journal, runtime, `main` ni `Xray-Normativa/` durante esta fase de diseño.
