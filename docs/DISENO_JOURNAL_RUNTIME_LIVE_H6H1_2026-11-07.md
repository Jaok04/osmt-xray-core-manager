# Diseño técnico — journal runtime live (H6-H1)

**Fecha:** 2026-11-07
**Rama de referencia:** `design/user-identity-association-v1`
**Estado:** CONTRATO DE DISEÑO APROBADO POR EL PROPIETARIO (2026-11-07) — IMPLEMENTACIÓN PENDIENTE
**Alcance:** diseño del journal y persistencia para una futura aplicación runtime live. No habilita R-06 ni autoriza operaciones reales.

## 1. Objetivo

Definir un registro durable, recuperable y verificable para operaciones que en el futuro puedan publicar una generación de Xray y solicitar una transición de `xray.service`.

El journal debe permitir reconstruir qué se intentó, qué efectos quedaron demostrados, qué permanece ambiguo y qué recuperación es segura después de SIGKILL, caída del host, timeout o respuesta perdida.

El journal no ejecuta systemd, no publica archivos y no decide por sí solo que una configuración fue cargada. Es evidencia de coordinación, no una prueba autónoma del estado real.

## 2. Contraste normativo y compatibilidad

Se contrastó con:

- `Xray-Normativa/05_Configuraciones_Perfiles/Etapa_5_Configuraciones_Perfiles.md`: verificación real antes de declarar éxito; rollback e informe de estados afectados; no activar un perfil restaurado sin flujo normal de validación/aplicación.
- `Xray-Normativa/06_Servicio_Diagnostico/Etapa_6_Servicio_Diagnostico.md`: detectar operaciones interrumpidas sin repetirlas automáticamente; detectar cambios externos sin sobrescribirlos; releer y comparar antes de cambiar; timeouts y reintentos limitados; preparar, validar, respaldar, verificar y recuperar.
- `docs/DISENO_APLICACION_RUNTIME_XRAY_2026-11-04.md`: snapshot previo obligatorio, publicación atómica, reinicio controlado, rollback condicionado al estado previo y R-06 sujeto a autorización independiente.
- `docs/DECISION_H6G3_COORDINACION_TRANSACCIONAL_2026-11-06.md`: orden lifecycle → application, un único ámbito coordinador, observación antes de reintentar y `RECOVERY_REQUIRED` ante ambigüedad.

No se modifica `Xray-Normativa/`. Este diseño no cambia ni relaja los contratos fixture R-01–R-05.

## 3. Separación estricta fixture/live

No convertir el journal fixture actual en un journal dual mediante una bandera de entorno.

Se propone un módulo independiente, por ejemplo `scripts/xray_runtime_live_journal.py`, con:

- esquema live propio, inicial `schema_version=1` dentro de ese módulo;
- almacén live dedicado, propuesto: `/var/lib/xray-manager/runtime-operations`;
- raíz de operaciones y cada directorio de operación propiedad de `root:root`, modo `0700`;
- journal, snapshot metadata y copia de configuración previa propiedad de `root:root`, modo `0600`;
- lock files bajo la jerarquía de locks acordada, propiedad `root:root`, modo `0600`;
- validación de ruta absoluta, componentes sin symlink, directorios/archivos regulares, hardlinks no permitidos, propietario, grupo, permisos y límites de tamaño;
- rechazo explícito de rutas fixture, marcadores fixture, rutas arbitrarias y cualquier intento de reutilizar `XRAY_SERVICE_ROOT` para live.

El almacén no debe ser configurable desde el menú ni desde variables de entorno no confiables. Su ruta se fija en código/contrato y se valida en cada operación. La creación del almacén es una operación de preparación separada y requerirá autorización live específica.

El journal live no debe aceptar registros fixture; el journal fixture no debe aceptar registros live. No habrá fallback entre ambos.

## 4. Identidad y estructura de una operación

Cada operación tendrá un ID aleatorio no reutilizable: `runtime-op-<32 hex>`. Un directorio por operación contendrá:

- `journal.json`: estado actual y evidencia correlacionada.
- `snapshot/config.json`: bytes exactos de la configuración anterior, si existía.
- `snapshot/metadata.json`: hashes, tamaño, propietario, grupo, modo y presencia/ausencia del archivo anterior.
- `events/`: opcional, solo si se aprueba un registro append-only; no duplicar estado autoritativo sin definir reconciliación.
- No almacenar PEM, claves privadas, master keys, tokens, UUID completos ni contenido de configuración en el journal.

El snapshot de configuración puede contener identificadores/credenciales operativas. Por ello será root-only, no se incluirá en exportaciones ni backups ordinarios y se conservará hasta cierre auditado/retención aprobada. El hash no sustituye a la copia.

### 4.1 Campos mínimos del journal

- Identidad: `schema_version`, `operation_id`, `created_at`, `updated_at`, `environment=live`.
- Origen: `profile_id`, `revision`, `validation_id`, hash de contenido del perfil y hash de configuración staged.
- Artefactos: ID de generación, hash/tamaño del manifiesto staging, hash/tamaño de configuración final y hash del binario Xray.
- Destino: unidad fija `xray.service`, ruta fija `/etc/xray/config.json`; no aceptar destino del usuario.
- Observación inicial: LoadState, ActiveState, SubState, MainPID, InvocationID, ActiveEnterTimestamp, hash del archivo runtime, identidad/hash del ejecutable y hora UTC.
- Snapshot: si había configuración, hash/tamaño/metadatos y referencia interna; si no había, `no_previous_config=true`.
- Publicación: intent registrada, resultado observado, hash actual del destino y hora.
- Solicitud de servicio: acción, hora, resultado del proceso controlador (`accepted`, `rejected`, `timeout`, `response_lost`, `exception`).
- Observación posterior: estado systemd y correlación de proceso antes/después.
- Evidencia de carga: estado explícito `not_attested`, `pending`, `attested` o `contradicted`; hashes/generación observados solo si una fuente definida los demuestra.
- Rollback: estado de configuración y estado de servicio en campos separados.
- Recuperación: contador, última acción, último error sanitizado y decisión de intervención.

No almacenar mensajes crudos de subprocess, salida de journalctl ni valores sensibles. Errores persistidos deben ser códigos estables y mensajes sanitizados, con longitud limitada.

## 5. Estados monotónicos propuestos

Estados de alto nivel:

1. `prepared`: identidad de operación y journal inicial durable.
2. `validated`: staging, perfil, validación, binario y precondiciones comprobados.
3. `snapshot_saved`: snapshot anterior y metadata verificados y sincronizados a disco.
4. `publication_requested`: intención durable antes de tocar el destino.
5. `config_published`: destino observado con hash exacto de la generación nueva.
6. `service_action_requested`: acción y correlación de operación persistidas antes de delegar.
7. `service_action_accepted`: el controlador confirmó aceptación; no equivale a servicio activo.
8. `service_observed_active`: systemd y proceso se observaron coherentes después de la acción.
9. `configuration_attested`: solo cuando un mecanismo separado demuestra qué bytes/generación cargó el proceso.
10. `completed`: únicamente después de todas las evidencias requeridas, incluida la atestación de configuración.
11. `rollback_started`, `rollback_config_restored`, `rollback_service_restored`, `rolled_back`.
12. `recovery_required`: estado terminal de seguridad para ambigüedad, drift, corrupción o falta de evidencia.

`service_action_accepted` y `service_observed_active` nunca se promocionan automáticamente a `configuration_attested`. Si no existe evidencia fiable de carga, la operación no puede finalizar como `completed`.

Los estados no se pueden retroceder ni editar manualmente. Cada transición valida la combinación de estado, campos y hashes permitidos. Una transición no válida deja el journal intacto y exige intervención.

## 6. Persistencia durable y atomicidad

Cada actualización del journal seguirá este protocolo:

1. Validar directorio y journal existentes mediante descriptores seguros.
2. Crear temporal exclusivo en el mismo directorio, con `O_NOFOLLOW`, `O_EXCL`, modo `0600`.
3. Escribir JSON canónico estricto, comprobar longitud/hash y hacer `fsync(fd)`.
4. Reemplazar atómicamente con `rename/replace` en el mismo filesystem.
5. Hacer `fsync(directory_fd)`.
6. Reabrir y validar el journal final; no declarar durable una actualización si falla el paso anterior.

Para cada directorio nuevo: `mkdir`, fijar propietario/permisos, `fsync` del directorio creado y de su padre. No usar escritura directa truncando el journal existente.

El snapshot de configuración se copia a temporal, se verifica byte a byte/hash, se hace `fsync`, rename y `fsync` del directorio antes de persistir `snapshot_saved`.

La publicación de `/etc/xray/config.json` es responsabilidad de un publicador live separado, no del journal. Debe escribir temporal en el mismo directorio de destino, establecer `root:xray`/0640, sincronizar archivo, renombrar y sincronizar `/etc/xray`. El journal persiste intención antes y resultado después. El journal y el archivo runtime no comparten una transacción filesystem única; la recuperación debe reconciliar ambos hashes.

## 7. Locks y concurrencia

- Orden único: lifecycle lock → application lock.
- Un único coordinador conserva ambos locks durante snapshot, publicación, solicitud, observación, rollback y escritura de `RECOVERY_REQUIRED`.
- Los helpers reciben contexto/descriptor ya adquirido; no reacquieren locks ni liberan recursos ajenos.
- El descriptor lifecycle se hereda por el controlador único `modules/xray_service.sh`, validando inode, permisos y propiedad del lock.
- La recuperación vuelve a adquirir ambos locks en orden desde cero.
- No se permite que el journal adquiera locks fuera del coordinador ni que un proceso de recuperación compita con una operación viva.
- La propiedad del lock protege frente a otros procesos del Manager, no frente a modificaciones externas de root/systemd. Por eso se requiere reobservación/CAS conservador antes de cada efecto.

## 8. Reconciliación tras crash, timeout o respuesta perdida

La recuperación nunca repite una acción de servicio como primer paso.

Con ambos locks adquiridos:

1. Leer journal estricto y validar su esquema, ID, estado, rutas y hashes.
2. Observar systemd y proceso mediante adaptadores read-only.
3. Calcular hash actual de `/etc/xray/config.json` y verificar metadatos/permisos.
4. Comparar con hash anterior del snapshot y hash de generación nueva.
5. Correlacionar InvocationID, PID, starttime, ActiveEnterTimestamp y ventana temporal con la operación.
6. Clasificar el caso sin modificar nada:
   - destino sigue en hash anterior y no hay acción: operación no publicada; puede abortarse de forma segura;
   - destino coincide con hash nuevo y la solicitud no consta: publicación posiblemente completada; continuar solo si el journal y evidencia de staging son íntegros;
   - destino coincide con hash nuevo y systemd refleja nueva invocación: acción pudo surtir efecto; no repetir, evaluar evidencia;
   - destino coincide con hash anterior tras rollback: verificar estado de servicio según snapshot inicial;
   - destino tiene hash desconocido, unidad/ejecutable cambió, snapshot falta/corrompido, estado failed/unknown o correlación no concluyente: `recovery_required`.
7. Persistir decisión y evidencia. Si no se puede demostrar una transición segura, conservar todos los artefactos y solicitar intervención.

No limpiar temporales, snapshots ni journals de operaciones ambiguas. No hacer repair, overwrite ni restart automático ante drift externo.

## 9. Rollback: dos dimensiones independientes

### 9.1 Configuración

- Requiere snapshot anterior verificado.
- Releer destino y comprobar que sigue en hash de la generación de esta operación; si no coincide, no sobrescribir.
- Restaurar bytes anteriores mediante temporal en `/etc/xray`, permisos exactos y rename atómico.
- Recalcular hash después de publicación y persistir `rollback_config_restored`.
- Si no existía configuración anterior, no borrar la nueva ni crear placeholder: `recovery_required`.

### 9.2 Servicio

- Si inicialmente estaba `inactive`, rollback no puede iniciar Xray.
- Si inicialmente estaba `active`, solo se puede solicitar recuperación después de demostrar que la invocación actual pertenece a la operación y que el destino contiene exactamente el hash restaurado.
- Si el estado inicial era `failed`, `unknown`, transitorio o no correlacionable, no mutar; `recovery_required`.
- La restauración de bytes no demuestra restauración del proceso. Mantener `config_status` y `service_status` separados.
- Cualquier timeout/response-lost exige observación antes de considerar otra acción.

## 10. Límites de evidencia: configuración realmente cargada

El estado actual del observador informa `configuration_loaded=false` y `configuration_evidence=not_attested`. El nuevo journal debe preservar esa verdad.

Un hash de `/etc/xray/config.json`, un proceso activo, InvocationID nuevo, ExecStartPre exitoso o una respuesta `accepted` no demuestran por sí solos qué bytes exactos leyó Xray. No marcar `configuration_attested` hasta diseñar y auditar un mecanismo que cierre la carrera entre validación, publicación y lectura por el proceso.

Por tanto, H6-H1 no resuelve la atestación. Si al integrar journal no existe evidencia de carga, el máximo resultado será `service_observed_active` o `recovery_required`; nunca `completed`.

## 11. Retención y protección

- Mantener operaciones activas, no terminales y `recovery_required` sin límite automático de limpieza.
- Retención de operaciones `completed`/`rolled_back` será una decisión separada; limpieza solo después de verificación de integridad, edad, estado terminal y política aprobada.
- No borrar snapshots de recuperación por falta de espacio automáticamente.
- No incluir snapshots ni journals live en backups compartidos/exportables.
- No imprimir configuración, UUID, PEM, tokens, claves ni salida completa de Xray/systemd.
- Auditoría de acceso y errores sin contenido sensible.

## 12. Matriz mínima de pruebas H6-H1

Todas las pruebas de desarrollo deben usar directorios temporales, datos sintéticos y mocks. No se llama systemctl real ni se toca `/etc/xray`.

| ID | Escenario | Resultado requerido |
|---|---|---|
| J01 | JSON duplicado, esquema desconocido o campo extra | Rechazo fail-closed |
| J02 | Symlink, hardlink, owner/mode incorrectos | Rechazo sin mutación |
| J03 | Crash durante escritura temporal | Journal anterior intacto; temporal propio recuperable |
| J04 | Crash después rename antes fsync del padre | Relectura/reconciliación, sin afirmar durabilidad |
| J05 | Crash entre mkdir operación y journal inicial | Huérfano conservado o limpieza solo si se demuestra vacío |
| J06 | Snapshot truncado/hash discordante | `recovery_required`, no publicar |
| J07 | Crash después snapshot antes de publicar | Verificar snapshot; no invocar servicio |
| J08 | Crash después de rename config antes de actualizar journal | Comparar hash anterior/nuevo/desconocido |
| J09 | Timeout antes/después de transición | Observar y correlacionar; no repetir a ciegas |
| J10 | InvocationID/PID/starttime no correlacionan | `recovery_required` |
| J11 | Drift externo en config o unidad | No sobrescribir ni reparar |
| J12 | Servicio inicialmente inactive | Rollback nunca emite start |
| J13 | Sin configuración anterior | No borrar/placeholder; intervención |
| J14 | Snapshot ausente/corrupto durante rollback | No restaurar servicio; preservar evidencia |
| J15 | Recuperación repetida | Idempotencia byte a byte, cero acciones duplicadas |
| J16 | Journal fixture entregado al lector live o viceversa | Rechazo |
| J17 | Dos operaciones concurrentes | Exclusión lifecycle→application |
| J18 | Falla fsync/rename/chown/chmod | No marcar transición como completada |
| J19 | Error incluye secreto/UUID/PEM | Sanitización antes de persistir |
| J20 | Proceso activo sin prueba de bytes cargados | Nunca `configuration_attested`/`completed` |

## 13. Secuencia propuesta de implementación

1. **H6-H1-A:** contrato aprobado por el propietario el 2026-11-07; las seis decisiones de la sección 14 son vinculantes.
2. **H6-H1-B:** implementar lector/escritor live independiente, atomicidad, permisos, schema estricto y failpoints; solo fixtures de prueba del propio journal.
3. **H6-H1-C:** implementar reconciliación read-only de journals live usando snapshots simulados; sin systemctl real.
4. **H6-H1-D:** auditoría adversarial de crash consistency, concurrencia, TOCTOU, integridad y separación fixture/live.
5. Solo después de cierre auditado, diseñar H6-H2 para adaptar el orquestador. H6-H1 no habilita menú, publicación ni acciones live.

## 14. Decisiones del contrato — aprobadas por el propietario (2026-11-07)

Las seis decisiones siguientes quedan aprobadas y forman parte del contrato de implementación:

1. **Ruta fija — APROBADA:** `/var/lib/xray-manager/runtime-operations` como almacén root-only.
2. **Snapshots — APROBADO:** copia exacta root-only 0600, no cifrada, con exposición restringida y fuera de backups. Si se exige cifrado, debe definirse una clave de recuperación independiente y su ciclo de vida; no reutilizar ni leer `master.key`.
3. **Retención — APROBADA:** indefinidamente `recovery_required` y operaciones no terminales; proponer 30 días para terminales, sujeto a auditoría y limpieza explícita.
4. **Eventos — APROBADO:** un journal JSON autoritativo actualizado atómicamente, sin log append-only adicional en la primera versión; cada transición preserva timestamps y evidencia estructurada.
5. **Ausencia de configuración previa — APROBADA:** en `recovery_required`, sin eliminar la nueva configuración ni arrancar servicio.
6. **Atestación — APROBADA:** que H6-H1 no puede marcar `completed` hasta que un bloque posterior demuestre los bytes realmente cargados.

## 15. Dictamen

H6-H1 deja de ser una propuesta pendiente: el propietario aprobó las seis decisiones del contrato el 2026-11-07. La implementación sigue pendiente y debe limitarse a fixtures, directorios temporales y mocks en VPS desarrollo. No se modificó código funcional, el journal fixture, dependencias, configuración del sistema, runtime, DNS, firewall ni puertos. No se ejecutó systemctl ni Xray. No se instaló Certbot ni se solicitó certificado. No se modificó `Xray-Normativa/`, no se hizo commit ni push y no se sincronizó la VPS de pruebas.

**Estado:** CONTRATO APROBADO; IMPLEMENTACIÓN H6-H1-B/C Y AUDITORÍA H6-H1-D PENDIENTES. No autoriza R-06/live ni integración del backend live a R-05/menú.
