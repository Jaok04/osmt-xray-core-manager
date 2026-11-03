# Xray Manager — Etapa 3: Gestión de usuarios

**Versión:** 1.2  
**Estado:** APROBADA — especificación funcional  
**Fecha:** 31/10/2026  
**Proyecto:** Xray Core Manager

## 1. Objetivo y alcance

Definir la identidad global de los usuarios, sus asociaciones independientes con conexiones, las operaciones de administración, los límites, el consumo de tráfico y los procesos de importación y exportación. Esta etapa especifica el comportamiento funcional; no constituye implementación técnica.

La administración debe respetar el protocolo, modalidad y capacidad de la conexión definidos en la Etapa 2. Las credenciales y los campos disponibles dependerán de las capacidades reales del protocolo y de la versión de Xray-core o del componente externo utilizado.

## 2. Menú principal

```text
╔══════════════════════════════════════════════╗
║              GESTIÓN DE USUARIOS            ║
╠══════════════════════════════════════════════╣
║  [1] Gestión global de usuarios             ║
║  [2] Usuarios por protocolo y conexión      ║
║  [0] Volver                                 ║
╚══════════════════════════════════════════════╝
```

- **Gestión global:** consulta y administra identidades y sus asociaciones en todos los protocolos y conexiones.
- **Por protocolo y conexión:** limita la consulta y las operaciones a las asociaciones de la conexión seleccionada.

## 3. Modelo de identidad y asociaciones

La Etapa 2 es propietaria de la configuración técnica de cada conexión (protocolo, modalidad/transporte, puerto y parámetros técnicos). Esta etapa es propietaria de las identidades globales y de las asociaciones que conceden acceso a esas conexiones. Una conexión no equivale a un usuario ni a una asociación: una conexión puede tener varias asociaciones, y una identidad puede estar asociada a varias conexiones.

### 3.1 Identidad global

Cada identidad tendrá un identificador global único, generado automáticamente al crearla. El identificador no depende del alias, no cambia al modificarlo, se comparte entre todas las asociaciones de esa identidad y se incluye en las exportaciones para conservar la identidad en futuras importaciones. No es una credencial de acceso ni sustituye UUID, contraseña o claves.

Los alias pueden repetirse entre identidades distintas. No se fusionarán identidades basándose únicamente en un alias. Si un archivo externo carece de identificador global, el proceso de importación deberá solicitar una correspondencia inequívoca o tratar el registro como identidad nueva, sin fusionarlo automáticamente por nombre.

### 3.2 Asociación por conexión

Una identidad puede tener varias asociaciones, incluso en conexiones diferentes del mismo protocolo. Cada asociación es independiente y tiene sus propios datos: credenciales, duración, vencimiento, límite de tráfico, límite de conexiones simultáneas y estado. Modificar, renovar, suspender, reactivar o eliminar una asociación no modifica las demás.

#### Asociación WireGuard y peers

En una conexión WireGuard, cada peer debe estar vinculado a una identidad global. Una identidad puede tener varios peers para distintos dispositivos o accesos. Cada peer conserva sus propias claves, dirección IP y parámetros técnicos; estos datos pertenecen al peer y a su asociación, no a la identidad global como un único conjunto compartido. La eliminación de una asociación WireGuard elimina únicamente el peer correspondiente y conserva las demás asociaciones y peers de la identidad. La eliminación de una identidad global elimina todas sus asociaciones y todos sus peers WireGuard. Las claves privadas se tratarán como información sensible y se protegerán conforme a las reglas de credenciales y respaldos.

Desde Gestión global se podrá seleccionar una identidad existente y asociarla a una o varias conexiones adicionales. Para cada asociación nueva se podrá generar credenciales automáticamente o introducirlas manualmente. Se validarán compatibilidad y unicidad según protocolo, modalidad y tipo de credencial. La conexión de destino debe existir y disponer de capacidad.

### 3.3 Capacidad de conexión

El máximo de usuarios se configura en Etapa 2. Las asociaciones activas, suspendidas y vencidas ocupan espacio. Si se alcanza el máximo, se rechazan nuevas asociaciones. No se realiza traslado automático. Una asociación eliminada libera una plaza en su conexión; la eliminación global libera las plazas de todas las asociaciones.

## 4. Menú de operaciones comunes

```text
╔══════════════════════════════════════════════╗
║             ADMINISTRAR USUARIO             ║
╠══════════════════════════════════════════════╣
║  [1] Crear usuario                          ║
║  [2] Consultar información                  ║
║  [3] Modificar usuario                      ║
║  [4] Renovar usuario                        ║
║  [5] Suspender usuario                      ║
║  [6] Reactivar usuario                      ║
║  [7] Consultar consumo de tráfico           ║
║  [8] Eliminar usuario                       ║
║  [0] Volver                                 ║
╚══════════════════════════════════════════════╝
```

Estas son operaciones comunes. Si un protocolo no permite una operación, se indicará como no disponible; no se ofrecerá una función no soportada.

## 5. Datos y credenciales

Cada asociación incluye alias/nombre obligatorio, credencial compatible con el protocolo, fecha de creación automática, duración, vencimiento calculado, límite de tráfico opcional y límite de conexiones simultáneas opcional cuando el protocolo lo soporte.

Las credenciales pueden generarse automáticamente o introducirse manualmente durante la creación, modificación o creación de una asociación adicional. Las credenciales duplicadas se rechazan; se informa al administrador y se permite introducir otra o generar una nueva. La unicidad se valida según los requisitos del protocolo y tipo de credencial.

## 6. Creación de usuarios

### 6.1 Desde gestión global

1. Seleccionar protocolo.
2. Seleccionar modalidad, si corresponde.
3. Seleccionar una conexión existente.
4. Completar los datos de la asociación.
5. Validar credenciales, parámetros y capacidad.
6. Mostrar resumen y confirmar antes de guardar.

### 6.2 Desde una conexión

Si ya se está administrando una conexión, se podrá crear el usuario directamente sin volver a seleccionar protocolo ni conexión.

### 6.3 Asociación adicional de identidad existente

Desde la ficha global se podrá agregar una o varias conexiones. Para cada nueva asociación se configura independientemente credencial (automática o manual), duración, vencimiento, límites y estado. No se alteran las asociaciones existentes.

## 7. Duración, vencimiento, renovación y estados

### 7.1 Selección de duración

```text
╔══════════════════════════════════════════════╗
║             DURACIÓN DEL USUARIO            ║
╠══════════════════════════════════════════════╣
║  [1] Duración personalizada                 ║
║  [2] Sin vencimiento                        ║
║  [0] Volver                                 ║
╚══════════════════════════════════════════════╝
```

La duración personalizada solicita cantidad y unidad: días, horas o minutos. El vencimiento se calcula desde la fecha y hora de creación. No existen otros periodos fijos predefinidos en esta especificación.

Al modificar la duración, se solicita una nueva duración y el vencimiento se calcula desde el momento de modificación, reemplazando el anterior. Al renovar, el nuevo periodo comienza desde el momento de renovación; no se suma al vencimiento anterior.

### 7.2 Vencimiento automático

Los usuarios vencidos se bloquean y su estado cambia a `expired`/`Vencido`. Se utilizarán ambos mecanismos de comprobación:
- Revisión periódica de vencimientos.
- Revisión al iniciar el administrador o el servicio correspondiente para detectar vencimientos ocurridos durante una parada.

La comprobación y el bloqueo se aplican por asociación. El vencimiento de una asociación no bloquea las demás asociaciones de la identidad global.

### 7.3 Suspensión y reactivación

Suspender bloquea inmediatamente el acceso de esa asociación y no solicita motivo. Durante la suspensión se pausa el conteo de su tiempo restante.

Al reactivar una asociación que tenía duración limitada, se solicita una duración nueva:

```text
[1] Duración personalizada
[2] Sin vencimiento
[0] Volver
```

La nueva fecha se calcula desde el momento de reactivación y reemplaza el vencimiento anterior; no se acumula el tiempo restante previo. Si se elige `[0]`, se cancela sin reactivar. Una vez elegida una duración, la reactivación es inmediata y no requiere segunda confirmación.

Si la asociación era sin vencimiento, se pregunta:

```text
[1] Sin vencimiento
[2] Establecer una caducidad
[0] Volver
```

La segunda opción solicita cantidad y unidad (días, horas o minutos). La reactivación se ejecuta inmediatamente después de seleccionar una opción válida.

Estados permitidos: `active` (Activo), `suspended` (Suspendido) y `expired` (Vencido).

## 8. Límites

### 8.1 Tráfico

```text
╔══════════════════════════════════════════════╗
║              LÍMITE DE TRÁFICO              ║
╠══════════════════════════════════════════════╣
║  [1] Límite personalizado (GB)              ║
║  [2] Sin límites                            ║
║  [0] Volver                                 ║
╚══════════════════════════════════════════════╝
```

El administrador introduce el límite en GB o selecciona sin límites. Al modificarlo puede establecer un nuevo límite o quitarlo. Cambiar el límite no reinicia el consumo acumulado.

### 8.2 Conexiones simultáneas

```text
╔══════════════════════════════════════════════╗
║       CONEXIONES SIMULTÁNEAS                ║
╠══════════════════════════════════════════════╣
║  [1] Límite personalizado                   ║
║  [2] Sin límites                            ║
║  [0] Volver                                 ║
╚══════════════════════════════════════════════╝
```

Se configura un máximo personalizado o sin límites. Solo se aplicará cuando el protocolo y el mecanismo de control lo permitan. Si no se soporta, se informará y no se simulará el control.

## 9. Listado, búsqueda y filtros

La lista numerada mostrará número, alias, protocolo y conexión, estado y vencimiento. Se podrá:
1. Buscar por nombre/alias.
2. Filtrar por protocolo.
3. Filtrar por estado (activo, suspendido o vencido).
4. Mostrar todos.

En modo global se incluyen todas las asociaciones, conservando protocolo y conexión. En modo por conexión solo se muestran las asociaciones de la conexión seleccionada. Al seleccionar una identidad global se abrirá su ficha con todas sus asociaciones y su administración independiente.

## 10. Modificación de usuarios

Se podrán modificar independientemente:
1. Nombre o alias.
2. Credenciales.
3. Duración y vencimiento.
4. Límite de tráfico.
5. Límite de conexiones simultáneas.

Cada modificación preserva los demás campos. Las credenciales pueden generarse automáticamente o introducirse manualmente. Cambiar el límite de tráfico no reinicia el consumo. Los parámetros técnicos de conexión (Path, SNI, Host, puerto, TLS/REALITY y transporte) se administran en Etapa 2, no aquí.

## 11. Consulta y reinicio de consumo

La consulta mostrará, cuando estén disponibles: tráfico descargado, subido, total, límite asignado, porcentaje consumido y tráfico restante. Si una métrica no puede obtenerse de forma fiable, se mostrará **«No disponible para este protocolo»**. No se inventarán valores ni se presentarán estimaciones como mediciones reales.

El consumo y sus contadores son independientes por asociación. No se conservará historial de consumos ni de reinicios en esta etapa.

Se permiten reinicios manuales y automáticos. El reinicio manual requiere consultar el consumo y confirmar. La programación automática admite:
1. Diario.
2. Semanal.
3. Mensual.
4. Cada N días.

Si el servidor está apagado cuando corresponde el reinicio, al iniciar se detectará el reinicio pendiente y se ejecutará una sola vez; no se acumularán múltiples reinicios por el tiempo apagado. Después continuará la programación normal. Reiniciar contadores no modifica credenciales, duración ni vencimiento.

## 12. Eliminación

Se ofrecen dos alcances:

- **Eliminar asociación:** elimina el acceso únicamente a la conexión seleccionada, conserva las demás asociaciones y libera una plaza en esa conexión. Si corresponde a WireGuard, elimina también únicamente el peer vinculado a esa asociación.
- **Eliminar usuario globalmente:** elimina la identidad, todas sus asociaciones y registros asociados, revoca todos los accesos y libera todas las plazas correspondientes. También elimina todos los peers WireGuard vinculados a esa identidad.

Ambas operaciones requieren confirmación. La eliminación es permanente; no se contempla recuperación desde el administrador.

## 13. Exportación

Se podrá exportar una asociación/usuario individual, todos los usuarios o un conjunto filtrado por protocolo, conexión o estado. Formatos: JSON, CSV y TXT.

Antes de exportar, el administrador preguntará si se incluirán credenciales. Si se incluyen, solicitará una confirmación adicional. Sin autorización explícita, las credenciales no se exportarán. Se incluirá el identificador global para conservar la identidad al reimportar.

## 14. Importación

Se podrá importar a un protocolo y conexión concretos o globalmente a varias conexiones/protocolos. Se aceptarán archivos exportados previamente o preparados con la estructura definida por el administrador.

### 14.1 Validación y vista previa

Antes de incorporar registros se validarán estructura, versión, compatibilidad, campos requeridos, credenciales duplicadas, conexión de destino y capacidad disponible. La vista previa mostrará:
1. Total detectado.
2. Válidos.
3. Credenciales duplicadas.
4. Incompletos o inválidos.
5. Registros que se importarán.

### 14.2 Identidad ya existente y asociación adicional

Si el identificador global del archivo corresponde a una identidad existente y el registro apunta a otra conexión, se creará una nueva asociación dentro de esa identidad, conservando intactas las asociaciones anteriores. La nueva asociación tendrá sus propios parámetros. Se validarán compatibilidad y capacidad.

Si el archivo no contiene identificador global, no se fusionarán identidades únicamente por alias: se solicitará correspondencia inequívoca o se tratará como identidad nueva.

### 14.3 Conflicto en la misma asociación

Si el usuario ya tiene una asociación en la misma conexión y el archivo contiene datos diferentes, se permitirá actualización selectiva. Los campos elegibles son alias, credenciales, duración/vencimiento, límite de tráfico, límite de conexiones simultáneas y estado. Se mostrarán valores actuales y nuevos; el administrador seleccionará los campos, revisará los cambios y confirmará. Los campos no seleccionados y las demás asociaciones permanecerán intactos.

### 14.4 Conexiones inexistentes y reasignación

No se crearán conexiones automáticamente. Si el destino no existe, se podrá rechazar el registro o reasignarlo a otra conexión existente y compatible. La reasignación se mostrará en la vista previa. Se podrán seleccionar varios usuarios y asignarlos a una misma conexión compatible. Si no existe destino compatible o no hay capacidad, se rechazará la asociación.

### 14.5 Estados, errores y resumen

Si el archivo contiene usuarios suspendidos o vencidos, se preguntará qué estado aplicar. Un error inesperado en un registro no detendrá el procesamiento de los demás. El resumen final indicará importados correctamente, rechazados, motivo de cada rechazo y ruta del archivo. Una importación parcial se identificará como parcial, nunca como éxito total.

### 14.6 Versiones y campos desconocidos

Se identificará la versión y estructura del archivo. Se conservarán los datos compatibles y se advertirá sobre campos desconocidos o incompatibles; no se descartará información silenciosamente. Se mostrará una vista previa y se solicitará autorización. Los registros incompletos o incompatibles se rechazarán individualmente sin detener los registros válidos.

## 15. Reglas generales de navegación y seguridad

- Todos los menús y submenús incluyen `[0] Volver` al nivel inmediatamente anterior.
- Las entradas inválidas permiten reintentar.
- Los errores no cierran inesperadamente el administrador.
- Las operaciones muestran el resultado antes de regresar.
- Las operaciones destructivas requieren confirmación, excepto la reactivación que se ejecuta inmediatamente después de elegir la duración, según lo aprobado.
- Las credenciales se protegen en exportaciones y vistas; nunca se incluyen sin autorización explícita.
- La gestión de una asociación no debe afectar otras asociaciones de la misma identidad.
- Las operaciones de creación e importación respetan la capacidad definida en Etapa 2.

## 16. Límites y validación técnica previa

Esta etapa define el comportamiento funcional aprobado, no garantiza que todos los protocolos ofrezcan medición de tráfico, límite simultáneo u operaciones idénticas. Antes de implementar se verificará la capacidad real de cada protocolo, versión y componente. Las funciones no soportadas se marcarán como no disponibles, sin simular resultados.

Los detalles adicionales que no quedaron definidos podrán incorporarse posteriormente mediante una revisión documentada, sin alterar silenciosamente estas decisiones.

## 17. Control de versión

- **Versión 1.0:** primera especificación funcional aprobada de Gestión de usuarios.
- **Versión 1.2:** define la relación entre identidad global, asociación de acceso y peer WireGuard; una identidad puede tener varios peers, la eliminación de una asociación elimina solo su peer y la eliminación global elimina todos sus peers.
- Las ampliaciones posteriores deberán actualizar Markdown y YAML conjuntamente y registrarse en el historial de cambios.

---

**Fin de Etapa 3 — Gestión de usuarios.**