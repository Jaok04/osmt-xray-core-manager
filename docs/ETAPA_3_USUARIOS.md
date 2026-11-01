# Etapa 3 - Gestión de usuarios VLESS

## Alcance implementado

El módulo `modules/users.sh` gestiona identidades VLESS como registros locales en borrador. La opción 2 del menú principal ya abre este módulo.

Funciones disponibles:

1. Crear usuario: genera un UUID aleatorio con `uuidgen`, lo asocia a una conexión VLESS existente en estado `draft` y solicita una etiqueta descriptiva.
2. Consultar usuarios: muestra UUID, conexión, etiqueta, estado y si fue aplicado al runtime.
3. Editar etiqueta: conserva el UUID y la asociación.
4. Eliminar usuario: requiere el UUID exacto y la confirmación literal `ELIMINAR`.

## Persistencia y controles

- Archivo: `/var/lib/xray-manager/users/users.json`.
- Permisos: `0600`; persistencia mediante `lib/json_store.sh`, con temporal en el mismo directorio, validación, `fsync` y reemplazo atómico.
- Bloqueo: `/run/xray-manager/integrity.lock` con `flock`, compartido con el módulo de conexiones.
- UUID: formato estándar generado localmente; no se deriva de datos del usuario.
- La creación respeta `max_users` de la conexión.
- Solo admite conexiones del catálogo cuyo ID comienza por `vless_` y que estén en estado `draft`.
- Los registros solo pueden editarse/eliminarse en estado `draft`.
- Se impide eliminar una conexión que tenga usuarios asociados. La comprobación se realiza bajo el mismo lock compartido que protege el alta de usuarios.
- Si el archivo de usuarios tiene un formato incompatible, la operación se detiene sin sobrescribirlo.

## Integración con el modelo VLESS

`users_export_clients <connection_id>` exporta un arreglo JSON con la estructura `[{ "id": "<UUID>", "email": "<etiqueta>" }]`, que corresponde a la forma de clientes VLESS usada por el adaptador.

`users_build_vless_model <connection_id> <listen_address>` obtiene la modalidad y puerto de la conexión registrada, construye el modelo neutral VLESS y adjunta los usuarios asociados. Ese modelo se puede pasar al adaptador `vless_xray_26_10_31_build` con las opciones explícitas de transporte/seguridad.

No se crea ningún `flow` por defecto. El UUID y la etiqueta son los únicos campos gestionados por esta etapa.

## Límites de seguridad y alcance

- Los registros no se aplican al servicio Xray.
- `runtime_applied` permanece en `false`.
- No se generan enlaces VLESS ni archivos de configuración activos.
- No se reinicia ni inicia ningún servicio.
- Los registros se asocian a conexiones en borrador; el flujo de activación, revocación en runtime, expiración, cuotas de tráfico y auditoría quedan pendientes.
- El límite `max_users` es un límite administrativo local, no una cuota de tráfico ni un mecanismo de autenticación activo mientras no se aplique el runtime.

## Pruebas

`tests/users.sh` usa directorios temporales y verifica:
- alta y formato UUID;
- permisos `0600`;
- límite de usuarios por conexión;
- exportación de clientes VLESS;
- construcción del modelo neutral con usuarios;
- edición de etiqueta sin cambiar UUID;
- bloqueo de eliminación de conexiones con usuarios asociados;
- eliminación confirmada.

Ejecutar:
```bash
bash tests/users.sh
bash tests/smoke.sh
```


### Pruebas de concurrencia cruzada

`tests/cross_race.sh` ejecuta `users_create()` y `connections_delete_draft()` en procesos independientes y fuerza ambos órdenes posibles de adquisición del lock:

- Si el alta obtiene primero el lock, el usuario se guarda y el borrado posterior detecta la asociación y rechaza eliminar la conexión.
- Si el borrado obtiene primero el lock, elimina la conexión todavía vacía; cuando el alta obtiene el lock, la revalidación falla y no crea el usuario.

La prueba pasó cinco ejecuciones consecutivas y una ejecución adicional dentro de la suite completa. `tests/concurrency.sh` complementa esta cobertura con 16 altas, 16 ediciones y 16 eliminaciones concurrentes de usuarios.

Ejecutar:
```bash
bash tests/cross_race.sh
bash tests/concurrency.sh
```


### Fallos de persistencia

El almacenamiento de usuarios usa `lib/json_store.sh`, compartido con conexiones. `tests/json_store_faults.sh` inyecta fallos en `fsync` del archivo y del directorio y termina el proceso de commit antes/después del reemplazo atómico. Comprueba que el destino visible sea siempre JSON completo. Si falla el `fsync` del directorio, el reemplazo ya ocurrió: `json_store_commit` devuelve el código especial `3`, y `users_atomic_update` conserva el cambio aplicado y emite una advertencia de durabilidad no confirmada. Esto no confirma durabilidad ante pérdida de alimentación.