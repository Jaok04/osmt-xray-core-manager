# Diseño técnico — Identidades globales y asociaciones (Etapas 2 y 3)

**Estado:** decisiones técnicas aprobadas el 01/11/2026; implementación v2 inicial aislada en pruebas. No modifica la especificación funcional aprobada.  
**Versión:** 1.2  
**Fecha:** 2026-11-01  
**Base funcional:** Etapa 2 v1.2 y Etapa 3 v1.2, aprobadas el 31/10/2026.  
**Alcance:** modelo de datos, propiedad de entidades, persistencia, migración y contratos para el siguiente incremento.

## 1. Resultado de la auditoría del código actual

La implementación actual usa:
- `connections.json`: conexiones con `id`, `protocol_id`, `port`, `max_users`, `state`, `runtime_applied`.
- `users.json`: arreglo plano de filas con `uuid`, `connection_id`, `label`, `state=draft`, `runtime_applied=false`, `created_at`.
- El generador VLESS recibe los registros de usuario por conexión y crea `clients: [{id,email}]`.

Limitaciones confirmadas:
1. Una fila de usuario representa simultáneamente identidad y asociación; no permite una identidad con varias asociaciones independientes.
2. No existe ID global inmutable distinto de la credencial UUID.
3. No existe ID estable de asociación.
4. La etiqueta visible se exporta como `email` de Xray. Esto contradice la decisión de auditoría: el campo técnico `email` debe derivarse de un ID estable de asociación, no del alias visible.
5. El modelo actual solo acepta usuarios y conexiones en estado `draft`; no implementa los estados funcionales `active`, `suspended`, `expired`.
6. Los registros no contienen duración, vencimiento, límites, estado deseado ni vínculo explícito identidad-asociación.
7. La API del módulo actual limita el alta a VLESS. Es una implementación parcial y no debe presentarse como Etapa 3 terminada.

La implementación actual es una base de borradores y no debe migrarse como si ya representara usuarios activos.

## 2. Reglas de propiedad

| Entidad/dato | Propietario | Regla |
|---|---|---|
| Conexión técnica | Etapa 2 | ID, protocolo, modalidad, puerto, capacidad y parámetros técnicos |
| Identidad global | Etapa 3 | ID global inmutable y fecha de creación |
| Asociación | Etapa 3 | Vínculo identidad-conexión, alias, credenciales, duración, límites y estado |
| Peer WireGuard | Etapa 3, dentro de la asociación | Claves, IP y parámetros propios del peer; nunca compartidos entre peers |
| Configuración nativa Xray | Etapa 5 / adaptador de protocolo | Proyección persistente generada desde datos administrativos |
| Estado runtime | Etapa 6 / servicio | Resultado observado de aplicación; no sustituye la fuente administrativa |

Una conexión no es una identidad. Una identidad no es una credencial. Una asociación es el derecho de acceso de una identidad a una conexión concreta.

## 3. Modelo canónico propuesto

### 3.1 Archivo y atomicidad

Propuesta: conservar un único documento administrativo para identidades y asociaciones:

`/var/lib/xray-manager/users/users.json`

Forma de nivel superior:

```json
{
  "schema_version": 2,
  "identities": [],
  "associations": []
}
```

Razón: identidad y asociaciones se crean/eliminan/modifican con invariantes cruzados. Un único reemplazo atómico del archivo evita transacciones parciales entre `identities.json` y `associations.json`. El catálogo de conexiones permanece en su archivo propiedad de Etapa 2. Las operaciones que deban cambiar simultáneamente el catálogo de conexiones y usuarios requerirán journal transaccional explícito; no se resolverán con dos escrituras atómicas independientes.

### 3.2 Identidad

```json
{
  "id": "UUID-global-inmutable",
  "created_at": "2026-11-01T12:00:00Z"
}
```

- `id`: UUID v4 generado por el sistema; único, inmutable y no es credencial.
- La identidad no contiene credenciales de acceso.
- El alias visible pertenece a cada asociación según la especificación funcional; por tanto, no se usa para identificar ni fusionar identidades.
- Se permiten alias repetidos entre asociaciones e identidades.
- Una importación sin `identity_id` nunca fusiona por alias.

### 3.3 Asociación

Estructura conceptual:

```json
{
  "id": "UUID-asociacion-inmutable",
  "identity_id": "UUID-global-inmutable",
  "connection_id": "ID-de-conexion-Etapa-2",
  "alias": "Etiqueta visible",
  "protocol": "vless",
  "credential": {
    "type": "uuid",
    "value": "UUID-credencial"
  },
  "created_at": "2026-11-01T12:00:00Z",
  "duration": {
    "kind": "custom",
    "value": 30,
    "unit": "days"
  },
  "expires_at": "2026-12-01T12:00:00Z",
  "suspended_at": null,
  "remaining_seconds": null,
  "traffic_limit_bytes": null,
  "simultaneous_connection_limit": null,
  "state": "active",
  "runtime": {
    "status": "not_applied",
    "last_applied_at": null
  }
}
```

Reglas:
- `id` identifica la asociación y no cambia al editar alias o credenciales.
- `identity_id` referencia exactamente una identidad existente.
- `connection_id` referencia exactamente una conexión existente.
- `credential` es específica de la asociación; no se comparte automáticamente entre conexiones.
- `alias` es presentación y nunca identificador técnico.
- `duration.kind`: `custom` o `unlimited`. Para custom, unidad: `days`, `hours`, `minutes`.
- `expires_at=null` para duración ilimitada o mientras una asociación limitada está suspendida.
- `suspended_at` registra cuándo comenzó la suspensión; `remaining_seconds` conserva el tiempo pausado de una duración limitada. Ambos vuelven a `null` al reactivar.
- Reactivar una asociación limitada exige elegir una duración nueva; el tiempo restante pausado no se acumula ni se transfiere al nuevo periodo, según Etapa 3 v1.2.
- Los límites ausentes se representan como `null`, nunca como cero.
- `state` funcional admite exclusivamente `active`, `suspended`, `expired`.
- `runtime.status` es independiente del estado funcional: `not_applied`, `applied`, `unknown`, `pending`, `failed`. No se declarará aplicado sin verificación.
- Credenciales y secretos deberán almacenarse con permisos restrictivos; el diseño de cifrado en reposo queda pendiente de evaluación de amenazas y gestión de claves, no se improvisará una clave local junto al archivo.

Nota: la estructura es una propuesta de contrato v2. Los nombres y campos definitivos se congelarán después de validar todos los protocolos, incluidos los que no usan UUID.

## 4. Identificadores y mapeo Xray

Para VLESS:
- `credential.value` es el UUID que Xray utiliza en `clients[].id`.
- `association.id` es la identidad técnica estable de la asociación.
- `clients[].email` se genera desde `association.id` (por ejemplo, `assoc:<uuid>`), no desde el alias ni desde el ID global.
- `identity.id` permanece estable al agregar asociaciones a distintas conexiones.
- La credencial UUID es única según el ámbito exigido por el protocolo/adaptador; el validador debe impedir colisiones.

Este mapeo mantiene estadísticas por asociación y permite cambiar el alias sin romper la correlación técnica. El formato exacto de `email` debe validarse contra Xray 26.10.31 en pruebas de integración antes de habilitar estadísticas.

Para otros protocolos, el adaptador define el tipo y validación de credencial. No se asumirá que todos usan UUID ni que todos soportan `email`/estadísticas de Xray.

## 5. Invariantes de integridad

Antes de cada commit, validar el documento completo:
1. `schema_version` es una versión soportada.
2. Todos los IDs globales y de asociación son strings no vacíos y únicos en sus respectivos conjuntos.
3. Toda asociación referencia una identidad existente y una conexión existente.
4. Ninguna asociación duplica la pareja `identity_id + connection_id` para protocolos distintos de WireGuard. Para WireGuard se permiten varios peers de una misma identidad en la misma conexión; cada asociación/peer debe tener su propia clave pública y esta debe ser única.
5. Toda credencial obligatoria existe y cumple el tipo esperado por protocolo.
6. Las credenciales duplicadas se rechazan en el ámbito definido por el adaptador.
7. Estados funcionales válidos: active, suspended, expired. Los borradores históricos se migran con un estado de preparación separado y no se convierten automáticamente en active.
8. La capacidad de una conexión cuenta asociaciones active, suspended y expired, conforme a Etapa 3. Las asociaciones borrador históricas también deben ocupar capacidad hasta su eliminación o resolución, para no exceder slots durante migración.
9. Alias no es único y nunca se usa para deduplicar.
10. Los límites opcionales son null o valores positivos válidos; cero no significa ilimitado.
11. Fechas UTC ISO-8601; vencimiento posterior a creación/modificación según operación.
12. El documento se valida antes de sustituir el archivo existente; ante corrupción, no se sobrescribe.

### WireGuard

Un peer se modela como una asociación individual con su propio conjunto de claves/IP/parámetros. **Decisión aprobada:** una identidad puede tener varios peers incluso en la misma conexión WireGuard. Cada peer es una asociación independiente, con claves y parámetros propios. La unicidad de `identity_id + connection_id` no se aplica a WireGuard; la clave pública del peer identifica de forma única la credencial.

## 6. Estados: separación aprobada

La especificación funcional define los estados de asociación active/suspended/expired. El código actual usa `draft` como estado de registro porque aún no aplica configuraciones.

No se debe mezclar el ciclo de vida administrativo con el estado de acceso. **Decisión aprobada:**
- `state`: estado funcional de acceso (active/suspended/expired).
- `provisioning_status`: estado de configuración/aplicación (draft/pending/applied/failed).
- `runtime.status`: último estado observado (not_applied/applied/unknown/failed).

Así, un usuario recién creado puede tener estado deseado `active`, `provisioning_status=draft` y `runtime.status=not_applied`; la interfaz debe decir claramente que aún no tiene acceso efectivo. La expiración y suspensión cambian el estado funcional; la aplicación real se controla transaccionalmente.

Esta separación conserva los estados funcionales aprobados y evita ampliar esa enumeración con `draft`. Una asociación puede tener `state=active`, `provisioning_status=draft` y `runtime.status=not_applied`; eso expresa el estado funcional deseado, pero no significa que el acceso esté habilitado.

## 7. Capacidad y concurrencia

- Mantener el bloqueo de integridad compartido existente para las operaciones que toquen conexiones y asociaciones.
- Al crear una asociación: adquirir lock, volver a leer conexión y usuarios, validar capacidad, guardar documento, liberar lock.
- Contar active, suspended y expired; nunca solo active.
- No mover asociaciones automáticamente entre conexiones.
- La edición de una conexión que cambie capacidad debe comprobar asociaciones existentes y rechazar límites inferiores al número ocupado.
- La comprobación de puerto y la reserva de capacidad son validaciones distintas.
- Cualquier operación multiarchivo (p. ej. eliminar conexión y sus asociaciones) exige journal/recovery; preferiblemente bloquear eliminación si quedan asociaciones, como ya hace Etapa 2.

## 8. Migración desde el esquema plano actual

Migración no destructiva y explícita. El helper implementado trabaja sobre rutas de entrada/salida explícitas, exige un estado funcional confirmado (`active`, `suspended` o `expired`), nunca modifica el origen y rechaza un destino ya existente. La ejecución sobre los datos reales sigue pendiente:
1. Crear respaldo verificable de `users.json` y registrar hash, tamaño, fecha y permisos.
2. Validar el esquema antiguo completo; abortar si hay campos inesperados o registros inválidos.
3. Cada fila antigua se convierte inicialmente en una identidad nueva y una asociación nueva. No agrupar filas por `label`, porque alias duplicados están permitidos y no prueban identidad común.
4. Conservar el UUID antiguo como credencial VLESS de la asociación.
5. Conservar `connection_id`, `label` como `alias` y `created_at`.
6. Generar nuevos `identity.id` y `association.id`.
7. Traducir `state=draft` a `provisioning_status=draft`; no declararla activa ni aplicada.
8. El administrador debe seleccionar explícitamente el estado funcional para el lote; la herramienta no lo infiere ni convierte automáticamente un borrador en acceso activo.
9. Validar capacidad por conexión y unicidad de UUID.
10. Escribir v2 en temporal del mismo directorio, validar, fsync, reemplazo atómico y fsync del directorio.
11. Verificar lectura posterior, conteos, referencias, UUIDs y hash del respaldo.
12. Conservar el respaldo hasta completar pruebas de regresión y aprobación del administrador. No borrar automáticamente el original.

Importante: el esquema antiguo no contiene información suficiente para reconstruir identidades compartidas entre conexiones. La migración conservadora crea una identidad independiente por fila. La vinculación de varias asociaciones a una misma identidad requiere una correspondencia manual inequívoca; nunca se deduce por alias.

## 9. Contratos internos v2 — primera implementación

Implementado en `modules/users_v2.sh`:
- `users_v2_validate_document <json>`: valida el documento, referencias a conexiones, estados, credenciales y unicidad.
- `users_v2_validate_file <path>`: valida el archivo persistido.
- `users_v2_commit_document <json>`: valida y realiza reemplazo atómico con permisos 0600.
- `users_identity_create`
- `users_association_create`
- `users_association_set_alias`
- `users_association_suspend`
- `users_association_reactivate`
- `users_association_renew`
- `users_association_set_duration`
- `users_v2_expire_due`
- `users_association_delete`
- `users_identity_delete`
- `users_v2_export_vless_clients <connection_id>`
- `users_v2_migrate_legacy <legacy_json> <connections_json> <output_json> <confirmed_state>`

Reglas del módulo:
- Usa el bloqueo de integridad compartido.
- Cuenta todas las asociaciones de una conexión para la capacidad, independientemente del estado.
- Rechaza UUID VLESS repetidos globalmente.
- Permite varias asociaciones WireGuard por identidad/conexión, pero rechaza claves públicas duplicadas.
- No fusiona por alias.
- La exportación VLESS solo incluye asociaciones activas con provisioning y runtime marcados como aplicados; el alias no se usa como `email`.
- La migración es de VLESS legacy, exige estado funcional explícito, verifica capacidad, escribe a un destino nuevo y nunca modifica el origen.

Implementado en este incremento:
- Suspensión de una asociación activa: conserva los segundos restantes de duración limitada, borra el vencimiento activo y registra `suspended_at`. Las asociaciones ilimitadas también registran la suspensión.
- Modificación de duración: recalcula desde el momento de modificación; si está suspendida, conserva la duración nueva en pausa.
- Reactivación: exige una duración explícita (`custom` o `unlimited`), inicia el periodo desde la reactivación y descarta el tiempo restante previo.
- Renovación: disponible para asociaciones activas o vencidas; inicia el periodo desde la renovación, reemplaza el vencimiento anterior y deja la asociación en `active`. No permite renovar una asociación suspendida; debe reactivarse siguiendo su flujo.
- `users_v2_expire_due`: marca como `expired` cada asociación activa cuyo vencimiento haya llegado; admite un epoch opcional para pruebas deterministas. Puede invocarse como hook periódico y al iniciar el administrador/servicio.

Pendiente:
- bloquear/revocar el acceso en runtime al suspender o vencer; el módulo actual solo actualiza el estado administrativo y no aplica cambios Xray;
- programar el hook periódico y llamarlo desde los flujos reales de inicio;
- búsqueda/consulta pública de entidades, edición de credenciales y límites;
- modelo completo de datos WireGuard;
- integración con menú, generador y flujo de activación runtime.

El módulo v2 todavía no está conectado al menú ni al adaptador de runtime. No reemplaza `modules/users.sh` ni convierte automáticamente el almacenamiento existente.

## 10. Matriz de pruebas mínima para este incremento

| Caso | Resultado esperado |
|---|---|
| Una identidad con dos conexiones | Un ID global, dos asociaciones distintas |
| Dos identidades con mismo alias | Permitido; IDs distintos |
| Cambiar alias | No cambia IDs ni credenciales |
| Cambiar credencial | No cambia IDs ni otras asociaciones |
| Eliminar asociación | Conserva identidad y asociaciones restantes |
| Eliminar identidad | Elimina todas sus asociaciones y peers |
| Límite de conexión alcanzado | Rechaza nueva asociación |
| Estado suspended/expired | Consume slot |
| Suspender duración limitada | Guarda segundos restantes y pausa el vencimiento |
| Modificar duración suspendida | Actualiza duración pausada sin activar |
| Reactivar limitada | Exige nueva duración; no acumula el resto anterior |
| Reactivar ilimitada | Permite seguir ilimitada o elegir duración nueva |
| Renovar activa/vencida | Periodo nuevo desde la renovación |
| Barrido de vencimientos | Marca vencidas solo asociaciones activas; es idempotente |
| Asociación con conexión inexistente | Rechazo sin escritura |
| UUID duplicado | Rechazo sin escritura |
| Email Xray | ID de asociación estable, no alias |
| Corrupción del JSON | No sobrescribe el original |
| Interrupción antes de replace | Original intacto |
| Error de fsync de directorio | Resultado parcial explícito y recuperable |
| Migración de draft | Conserva credencial y datos; no marca acceso activo |
| Alias coincidente en dos filas legacy | No fusiona identidades automáticamente |
| WireGuard múltiples peers | Cada peer conserva claves y parámetros propios |\n| UUID VLESS duplicado entre conexiones | Rechazo global |\n| Clave pública WireGuard duplicada | Rechazo |\n| Migración por encima de max_users | Abortada antes de crear salida |

## 11. Decisiones cerradas y pendientes

**Decisiones aprobadas por el administrador el 01/11/2026:**
1. WireGuard permite múltiples peers por identidad, incluso en la misma conexión.
2. Los UUID VLESS tienen unicidad global entre todas las conexiones.
3. El estado funcional se separa del estado de provisioning y del estado runtime.

**Pendientes antes de habilitar importación/producción:**
1. **Importación de identidades existentes:** sin `identity_id` no se fusiona por alias; se requiere mapeo manual inequívoco.
2. **Protección de credenciales:** definir cifrado en reposo, gestión de claves y exportación protegida antes de soportar claves privadas y contraseñas.
3. **WireGuard completo:** definir y validar campos específicos del peer (clave privada, clave pública, IP/AllowedIPs, endpoint y parámetros del túnel) en su adaptador.
4. **Duración en producción:** conectar suspensión/reactivación/renovación al menú y a la revocación real en runtime; programar el barrido de vencimientos al inicio y periódicamente. La lógica administrativa y sus pruebas aisladas ya existen.

## 12. Alcance de este documento

**Revisión 1.2:** incorpora el ciclo administrativo de duración, pausa, reactivación, renovación y detección de vencimientos. No altera la especificación funcional aprobada.

El código inicial está en `modules/users_v2.sh` y `tests/users_v2.sh`. La suite v2 valida identidad global, asociaciones múltiples, alias duplicados, unicidad global de UUID VLESS, peers WireGuard, CRUD básico, pausa y reactivación de duración, modificación, renovación, vencimiento idempotente, corrupción y migración aislada. La suite completa existente (concurrency, cross-race, fallos de JSON, colisiones de puertos, smoke, uninstall, users, users_v2, xray_admin y Xray VLESS integration) ha pasado en la VPS con Xray 26.10.31.

**Límites de esta entrega:** el módulo no está integrado al menú ni a la activación de runtime; no se ha migrado el archivo real, no se ha reemplazado `modules/users.sh`, y no se ha tocado el servicio Xray, firewall o SSH. La Etapa 3 no se declara terminada. Antes de producción faltan la revocación real en runtime y la programación de los barridos al iniciar y periódicamente, los campos específicos de WireGuard, la protección de secretos y la importación/exportación con resolución manual de identidades.
