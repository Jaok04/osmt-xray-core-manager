# Integración inicial del menú de identidades v2

**Estado:** integrada en la rama de trabajo; interfaz v2 de consulta y primeras operaciones de creación.

## Enrutamiento por esquema

La opción **Gestión de usuarios** del menú principal utiliza `users_menu_dispatch`:

- Si el archivo no existe, conserva el comportamiento histórico y delega en `users_menu`, que inicializa el arreglo legacy como lo hacía antes.
- Si el documento JSON es un arreglo, abre el menú legacy.
- Si es un objeto con `schema_version: 2` y arreglos `identities` y `associations`, abre `users_v2_menu`.
- Si el JSON está corrupto, no puede leerse o presenta un esquema desconocido/incompleto, bloquea la gestión y no escribe sobre el archivo.

El selector no migra, convierte ni inicializa automáticamente un documento v2.

## Alcance de esta primera interfaz

El menú v2 expone:

1. Listado de identidades y asociaciones.
2. Resumen por estado funcional y protocolo.
3. Creación de identidad global.
4. Creación de asociación VLESS o WireGuard compatible con el modelo actual.
5. Consulta de detalle de asociación.
6. Edición del alias y límites administrativos de una asociación.

El listado presenta IDs, alias, conexión, protocolo, estado funcional, estado de implementación y vencimiento. No presenta UUID VLESS ni claves públicas/privadas de WireGuard.

Las consultas adquieren el bloqueo compartido y validan el documento v2 y sus referencias contra el catálogo de conexiones antes de mostrar información. La vista de detalle presenta identidad, alias, protocolo, conexión, duración, vencimiento, estado funcional, provisioning, runtime y límites; las credenciales se sustituyen por el texto «[oculta]».

La edición de asociación se realiza por ID exacto y actualiza alias, límite de tráfico y límite de conexiones simultáneas en un único commit atómico. El valor `0` se almacena como `null` (sin límite). No modifica credenciales, duración, estado funcional, provisioning ni runtime.

## Operaciones aún no expuestas

El módulo de dominio contiene funciones para editar alias, suspender, reactivar, renovar, modificar duración, eliminar asociaciones/identidades y calcular vencimientos. Esas operaciones administrativas aún no están conectadas a la interfaz.

La integración de las operaciones restantes se hará de forma incremental, con validación de entradas, confirmaciones para eliminaciones y pruebas sobre fixtures aislados.

## Límites operativos

- El menú v2 no aplica ni revoca clientes/peers en Xray.
- No activa el servicio Xray ni modifica puertos, firewall o SSH.
- No ejecuta la migración legacy a v2.
- Mientras el registro real siga siendo un arreglo legacy, el menú principal continúa usando el gestor legacy.
- La activación del runtime y la sincronización del estado de provisioning son etapas posteriores.

## Pruebas

`tests/users_v2_menu.sh` cubre el enrutamiento legacy/v2, el listado y detalle sin credenciales, el resumen, la creación de identidades/asociaciones VLESS y WireGuard, la edición de alias/límites, la cancelación sin escritura, las validaciones de identidad/conexión/capacidad/credenciales duplicadas y el bloqueo sin escritura para JSON corrupto y esquemas desconocidos.

La suite se incorpora a `tests/smoke.sh`.
