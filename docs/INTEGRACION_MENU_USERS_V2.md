# Integración inicial del menú de identidades v2

**Estado:** integrada en la rama de trabajo; interfaz v2 de consulta.

## Enrutamiento por esquema

La opción **Gestión de usuarios** del menú principal utiliza `users_menu_dispatch`:

- Si el archivo no existe, conserva el comportamiento histórico y delega en `users_menu`, que inicializa el arreglo legacy como lo hacía antes.
- Si el documento JSON es un arreglo, abre el menú legacy.
- Si es un objeto con `schema_version: 2` y arreglos `identities` y `associations`, abre `users_v2_menu`.
- Si el JSON está corrupto, no puede leerse o presenta un esquema desconocido/incompleto, bloquea la gestión y no escribe sobre el archivo.

El selector no migra, convierte ni inicializa automáticamente un documento v2.

## Alcance de esta primera interfaz

El menú v2 expone únicamente consultas:

1. Listado de identidades y asociaciones.
2. Resumen por estado funcional y protocolo.

El listado presenta IDs, alias, conexión, protocolo, estado funcional, estado de implementación y vencimiento. No presenta UUID VLESS ni claves públicas/privadas de WireGuard.

Las consultas adquieren el bloqueo compartido y validan el documento v2 y sus referencias contra el catálogo de conexiones antes de mostrar información.

## Operaciones aún no expuestas

Aunque el módulo de dominio ya contiene funciones para crear y eliminar identidades/asociaciones, gestionar alias, suspender, reactivar, renovar, modificar duración y calcular vencimientos, estas acciones todavía no están conectadas a la interfaz.

La integración de esas operaciones se hará de forma incremental, con validación de entradas, confirmaciones para eliminaciones y pruebas sobre fixtures aislados.

## Límites operativos

- El menú v2 no aplica ni revoca clientes/peers en Xray.
- No activa el servicio Xray ni modifica puertos, firewall o SSH.
- No ejecuta la migración legacy a v2.
- Mientras el registro real siga siendo un arreglo legacy, el menú principal continúa usando el gestor legacy.
- La activación del runtime y la sincronización del estado de provisioning son etapas posteriores.

## Pruebas

`tests/users_v2_menu.sh` cubre el enrutamiento legacy/v2, el listado sin credenciales, el resumen y el bloqueo sin escritura para JSON corrupto y esquemas desconocidos.

La suite se incorpora a `tests/smoke.sh`.
