# Arquitectura de almacenamiento y rutas

Estado: arquitectura aprobada; implementación parcial en curso.
Fecha: 2026-11-01

## Decisiones aprobadas

1. Configuración de Xray-core: `/etc/xray/`.
2. Certificados: modelo híbrido. Xray Manager administra únicamente certificados propios bajo su árbol de datos y mantiene referencias a certificados gestionados por terceros. No mueve ni elimina los originales externos.
3. Historiales: separados por dominio funcional.

## Fuente única de verdad

`config/paths.sh` define las rutas canónicas. El lanzador `bin/xray-manager` carga este archivo después de `config/manager.conf` y antes de los módulos.

| Dominio | Ruta |
|---|---|
| Código | `/opt/xray-manager` |
| Configuración Xray | `/etc/xray` |
| Preferencias del administrador | `/etc/xray-manager` |
| Datos raíz | `/var/lib/xray-manager` |
| Usuarios | `/var/lib/xray-manager/users/users.json` |
| Conexiones | `/var/lib/xray-manager/connections/connections.json` |
| Perfiles | `/var/lib/xray-manager/profiles` |
| Dominios | `/var/lib/xray-manager/domains` |
| Certificados administrados | `/var/lib/xray-manager/certificates/managed` |
| Referencias externas de certificados | `/var/lib/xray-manager/certificates/references` |
| Historiales | `/var/lib/xray-manager/history` |
| Estado | `/var/lib/xray-manager/state` |
| Logs | `/var/log/xray-manager` |
| Caché | `/var/cache/xray-manager` |
| Respaldos | `/var/backups/xray-manager` |
| Runtime/locks | `/run/xray-manager` |

## Migración de conexiones realizada

La ruta anterior era `/var/lib/xray-manager/connections.json`. Se creó la nueva ruta canónica `/var/lib/xray-manager/connections/connections.json` mediante copia validada:

- El origen se validó como arreglo JSON.
- La copia se instaló con permisos `600`.
- Se compararon los archivos con `cmp`.
- SHA-256 de ambos archivos: `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570`.
- El archivo antiguo se conserva intacto como copia heredada temporal. No se elimina hasta cerrar la validación de migración.
- La aplicación ya usa la nueva ruta canónica.

Respaldo previo de esta intervención:
`/var/backups/xray-manager/pre-rutas-20261101T142257Z/`.

## Permisos

Política objetivo, pendiente de endurecimiento y validación integral por cada consumidor:

- Datos administrativos sensibles y archivos JSON: `600`.
- Directorios de datos y certificados: `700` o `750` según necesidad de lectura.
- Claves privadas: `600`; directorios que las contienen: `700`.
- Respaldos: directorio `700`, archivos `600`.
- Propietario inicial: `root:root`. Un futuro usuario de servicio Xray recibirá solo los permisos mínimos requeridos para leer configuración y claves.

## Estado de implementación

Completado en este incremento:
- módulo central `config/paths.sh`;
- carga del módulo desde el lanzador;
- rutas de usuarios y conexiones adaptadas;
- lectura de asociación usuario-conexión adaptada;
- ruta de bloqueo centralizada;
- rutas de caché y respaldos del instalador referenciadas al módulo central;
- ruta de perfil activo ajustada al árbol de perfiles;
- rutas principales del desinstalador alineadas con `/etc/xray` y las nuevas categorías.

Pendiente:
- adaptar y probar el consumidor real de configuración Xray para `/etc/xray`;
- implementar almacenamiento de preferencias, perfiles, dominios, certificados e historiales;
- terminar inventario exhaustivo de desinstalación y reglas para referencias externas;
- retirar la copia heredada de conexiones solo después de un período de verificación;
- definir migración y rollback automatizados;
- verificar permisos y acceso del futuro usuario de servicio;
- sincronizar las rutas en los documentos YAML/MD de etapas 2–6.

## Restricciones

- No se ha instalado Xray ni creado una unidad systemd.
- No se han movido certificados ni configuraciones Xray existentes.
- No se ha ejecutado una desinstalación real.
- No se eliminó el archivo heredado de conexiones.
- La ruta `/usr/local/etc/xray` deja de ser destino de diseño; las referencias operativas al binario Xray en `/usr/local/bin/xray` y geodata en `/usr/local/share/xray` permanecen vigentes.

## Incremento: persistencia JSON y bloqueo de integridad (2026-11-01)

- Se añadió `lib/json_store.sh` para sustituir archivos JSON mediante temporal en el mismo directorio, validación de archivo regular, rechazo de destino simbólico, `fsync` del archivo, `os.replace` y `fsync` del directorio.
- `connections_atomic_update` y `users_atomic_update` validan la estructura del JSON generado antes de confirmar la sustitución y aplican modo `600`.
- Se detectó que los locks independientes de usuarios y conexiones no protegían las asociaciones entre ambos registros frente a operaciones concurrentes.
- Se unificaron ambos en `/run/xray-manager/integrity.lock`. Las constantes antiguas permanecen como alias de compatibilidad.
- `users_create()` vuelve a validar la conexión VLESS en estado `draft` inmediatamente después de adquirir el bloqueo compartido; si desapareció o cambió de estado durante la captura de la etiqueta, libera el lock y no crea el usuario.
- Se añadió una regresión determinista a `tests/users.sh`: simula que la conexión deja de estar disponible entre la consulta inicial y la revalidación protegida por lock; verifica que la operación falla y el registro permanece vacío.
- Prueba aislada: se comprobó que el lock de usuarios espera mientras el de conexiones está adquirido y continúa al liberarse. Se probó además el commit durable, modo `600` y rechazo de destino symlink en un directorio temporal.
- La batería de sintaxis, ShellCheck, shfmt y pruebas `users`, `smoke`, `uninstall`, `xray_admin` y `xray_vless_integration` pasó.

### Prueba de estrés de operaciones concurrentes (`tests/concurrency.sh`)

- Se creó un entorno temporal aislado con archivos `connections.json` y `users.json` propios y un lock compartido temporal. No se utilizaron ni modificaron los datos reales de la aplicación.
- Se lanzaron 16 procesos independientes para crear usuarios simultáneamente sobre una conexión `draft`; se verificaron 16 registros, UUID únicos, asociación correcta, estado `draft`, `runtime_applied=false` y permisos `600`.
- Se lanzaron 16 procesos independientes para editar esos usuarios; se verificó que las 16 etiquetas quedaran actualizadas y que no hubiera UUID duplicados.
- Se lanzaron 16 procesos independientes para eliminar los usuarios; se verificó que el archivo quedara vacío. Solo después se eliminó la conexión de prueba y se comprobó que tampoco quedaran conexiones residuales.
- Resultado observado: `OK: 16 altas, 16 ediciones y 16 eliminaciones concurrentes; sin pérdidas de registros ni asociaciones residuales.` La prueba pasó cuatro ejecuciones consecutivas.
- La batería completa posterior también pasó: `tests/concurrency.sh`, `tests/smoke.sh`, `tests/uninstall.sh`, `tests/users.sh`, `tests/xray_admin.sh` y `tests/xray_vless_integration.sh`; además `bash -n`, ShellCheck y shfmt sobre lanzador, configuración, librerías, módulos y pruebas.
- Se añadió `tests/cross_race.sh`, que coordina procesos independientes para forzar los dos órdenes de la carrera entre `users_create()` y `connections_delete_draft()`: (1) el alta obtiene primero el lock y el borrado posterior detecta el usuario asociado; (2) el borrado obtiene primero el lock, elimina la conexión vacía y el alta posterior falla al revalidarla.
- `tests/cross_race.sh` pasó cinco ejecuciones consecutivas y volvió a pasar dentro de la suite completa. Se comprobó que no se crean usuarios huérfanos ni se elimina una conexión que ya tiene un usuario.
- Suite completa posterior: `tests/cross_race.sh`, `tests/concurrency.sh`, `tests/smoke.sh`, `tests/uninstall.sh`, `tests/users.sh`, `tests/xray_admin.sh` y `tests/xray_vless_integration.sh`; además `bash -n`, ShellCheck y shfmt globales. Todas pasaron.
- Se añadió `tests/json_store_faults.sh` para inyectar fallos en las dos llamadas a `fsync` y terminar abruptamente el proceso de commit en dos puntos controlados: antes de `os.replace` y después del reemplazo, antes del `fsync` del directorio.
- `json_store_commit` reserva el código de salida `3` para el caso en que `os.replace` ya se ejecutó, pero falla el `fsync` del directorio. Los módulos de usuarios y conexiones reconocen ese resultado como reemplazo aplicado con durabilidad no confirmada: conservan el registro nuevo y emiten una advertencia, en lugar de reportar falsamente que la operación no se guardó.
- Resultado: si falla el `fsync` del temporal, el destino anterior permanece intacto y el temporal sigue disponible; si falla el `fsync` del directorio, el reemplazo ya ocurrió y el destino nuevo queda visible aunque la función devuelve error. Una terminación antes del reemplazo conserva el destino anterior; una terminación después del reemplazo deja visible el archivo nuevo. En todos los casos el destino observado fue JSON completo, nunca parcial.
- `tests/json_store_faults.sh` pasó tres ejecuciones consecutivas y una ejecución adicional dentro de la suite completa. La batería completa y las validaciones globales volvieron a pasar.

Límites: estas pruebas no cubren todavía colisiones concurrentes de puertos/sockets ni pérdida real de alimentación/kernel, corrupción física del sistema de archivos o recuperación tras reinicio. Los fallos de `fsync` se inyectan en el proceso Python y las terminaciones abruptas se provocan en barreras controladas; no equivalen a una prueba de corte eléctrico. Si falla el `fsync` del directorio, el `os.replace` ya se ha ejecutado: la función informa error, pero el nuevo destino puede estar visible y la durabilidad tras pérdida de energía no queda confirmada. Los registros de datos reales no se modificaron en estas pruebas.