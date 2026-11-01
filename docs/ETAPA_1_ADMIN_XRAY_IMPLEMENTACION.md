# Etapa 1 — Administración de Xray-core: implementación inicial

Estado: módulo de instalación controlada implementado; operaciones reales aún pendientes de validación operativa en VPS.

## Alcance actual

- Catálogo de versiones compatibles derivado de adaptadores locales existentes. Actualmente solo `26.10.31` está habilitada.
- Selección de versión durante instalación/actualización/reinstalación/reparación.
- Descarga desde el release oficial `XTLS/Xray-core`.
- Verificación de tag, release no borrador, presencia del paquete y archivo `.dgst`.
- Verificación SHA2-256 contra `.dgst`; para `26.10.31` amd64, también contra el hash fijado en `config/xray-version.conf`.
- Extracción acotada de `xray`, `geoip.dat` y `geosite.dat`; rechazo de nombres/rutas inesperados.
- Comprobación de la versión declarada por el binario antes y después de instalar.
- Copia de respaldo del binario/geodata preexistentes y restauración ante error.
- Exclusión mutua mediante `flock`.
- No se modifica la configuración Xray, certificados, unidad systemd, firewall, SSH ni se inicia/reinicia el servicio.

## Límites pendientes

- El catálogo no debe ampliarse hasta que exista adaptador de versión y pasen pruebas nativas de todas las configuraciones habilitadas.
- El modo repair actualmente reinstala el binario/geodata verificados; no repara unidad systemd ni configuración.
- La administración de la unidad systemd y la validación/recuperación de configuraciones se implementarán en las etapas correspondientes, con sus propias pruebas.
- La implementación se ha probado estáticamente y mediante pruebas del catálogo; no se ha ejecutado una instalación real en este VPS.

## Validación del paquete 26.10.31

- Release tag: `v26.10.31`.
- Arquitectura del VPS: `x86_64` → `Xray-linux-64.zip`.
- SHA2-256 oficial y configurado: `e4bd9119f50ae7c41658b1abd0679ae06f98bd864a2907ff33f2f2cf7081b214`.
- Binario de validación local: `Xray 26.10.31`, commit `a4a3dff`, `linux/amd64`.
- Contenido requerido del paquete: `xray`, `geoip.dat`, `geosite.dat`.

## Pendientes de Etapa 1

- Especificación de Dependencias del sistema y Configuración del administrador.
- Política y flujo completo de desinstalación, conforme a Etapa 1 rev. 1.2.
- Más pruebas de fallo/interrupción/rollback para la operación de instalación.


## Incremento: desinstalación segura (2026-11-01)

Se incorpora `modules/uninstall.sh` como único punto de entrada para la opción `[8] > [5] Desinstalar componentes`. El flujo ofrece alcance (Xray-core, Xray Manager o ambos), política de datos (conservar, eliminar todos o seleccionar categorías), respaldo previo, exportación opcional a un directorio externo y confirmación final irreversible.

### Límites deliberados

- La implementación solo elimina rutas inventariadas explícitamente: `/usr/local/bin/xray`, `/usr/local/share/xray`, `/usr/local/etc/xray`, `/opt/xray-manager`, archivos de usuarios/conexiones bajo `/var/lib/xray-manager`, y rutas propias identificadas de caché, logs y respaldos.
- Categorías de perfiles, dominios, certificados/llaves y preferencias sin ruta administrada verificada se informan y no se borran por aproximación.
- Si se detecta una unidad systemd de Xray, el flujo se bloquea; no modifica ni elimina unidades, no detiene procesos y no toca firewall ni SSH.
- El respaldo local se crea fuera de `/var/backups/xray-manager` para evitar incluirse a sí mismo en el archivo. Se comprueba con `tar -tzf` y `gzip -t`; la exportación se vuelve a verificar mediante SHA-256 en el destino.
- Con política «eliminar todos», se eliminan respaldos locales existentes y el respaldo temporal local; una exportación externa verificada será la única copia superviviente.
- No se ejecutó ninguna desinstalación real en el VPS.

### Pruebas

`tests/uninstall.sh` valida la creación/verificación del archivo y el rechazo de rutas inexistentes. La batería general se ejecuta después de integrar el módulo. La eliminación real permanece pendiente de pruebas controladas en un entorno desechable, especialmente interrupción durante borrado, exportación fallida y restauración del archivo.


## Incremento: centralización inicial de rutas (2026-11-01)

- Se añadió `config/paths.sh` como fuente única de rutas canónicas y se carga desde el lanzador antes de los módulos.
- Se adaptaron usuarios y conexiones a sus directorios dedicados bajo `/var/lib/xray-manager/`.
- Se adaptaron las rutas de caché/respaldo del instalador y la lectura de perfil activo.
- El desinstalador reconoce `/etc/xray`, `/etc/xray-manager` y las nuevas ubicaciones de datos por categoría.
- El archivo de conexiones existente se copió y verificó en la ruta canónica nueva. El archivo heredado se conserva; no se ha eliminado.
- Se documentaron las decisiones en `docs/ARQUITECTURA_RUTAS_Y_ALMACENAMIENTO.md`.
- Validación: `tests/uninstall.sh`, `tests/xray_admin.sh`, `tests/smoke.sh`, `tests/users.sh` y `tests/xray_vless_integration.sh`; además `bash -n`, ShellCheck y shfmt. Todas superaron esta ejecución.

### Límites pendientes

- El consumidor de configuración Xray aún debe implementarse/adaptarse a `/etc/xray`; no se ha creado ese directorio.
- Preferencias, perfiles, dominios, certificados e historiales aún no tienen todos sus módulos de persistencia.
- El inventario del desinstalador necesita pruebas aisladas adicionales para las nuevas categorías, referencias externas y restauración.
- La copia heredada de conexiones no se elimina hasta completar el periodo de validación y un procedimiento de rollback.
- No se instaló Xray, no se creó ni modificó systemd y no se ejecutó ninguna eliminación real.


## Incremento: persistencia JSON y bloqueo de integridad (2026-11-01)

- Se incorporó `lib/json_store.sh` para el commit durable de archivos JSON mediante temporal en el mismo directorio, `fsync`, reemplazo atómico y sincronización del directorio; rechaza destinos simbólicos.
- Los módulos de conexiones y usuarios validan el JSON resultante antes de persistirlo y establecen permisos `600`.
- Se reemplazaron los locks independientes por `/run/xray-manager/integrity.lock`, compartido por ambos módulos, para proteger operaciones que cruzan las asociaciones usuarios-conexiones. Las variables antiguas se conservan como alias.
- `users_create()` revalida la conexión VLESS `draft` dentro del lock, antes de contar usuarios y persistir. Si la conexión dejó de estar disponible durante la entrada de datos, aborta sin crear una asociación huérfana.
- `tests/users.sh` incorpora una regresión determinista que simula la desaparición de la conexión entre la consulta inicial y la revalidación bajo lock; comprueba rechazo y registro vacío.
- La prueba aislada confirmó contención entre `connections_lock` y `users_lock`; pruebas temporales verificaron commit, modo `600` y rechazo de destino symlink.
- `tests/concurrency.sh` ejecuta 16 altas, 16 ediciones y 16 eliminaciones de usuarios en procesos independientes, usando exclusivamente almacenamiento y lock temporales. Comprueba la integridad de los registros, UUID únicos, asociaciones, estados y permisos; elimina la conexión de prueba únicamente después de vaciar los usuarios.
- `tests/concurrency.sh` pasó cuatro ejecuciones consecutivas. Después pasó la batería completa: `tests/concurrency.sh`, `tests/users.sh`, `tests/smoke.sh`, `tests/uninstall.sh`, `tests/xray_admin.sh` y `tests/xray_vless_integration.sh`; también pasaron `bash -n`, ShellCheck y shfmt.
- Estas pruebas no modificaron los datos reales ni el servicio Xray.
- `tests/cross_race.sh` fuerza ambos órdenes de la carrera entre `users_create()` y `connections_delete_draft()` con procesos independientes y barreras de sincronización: si el alta gana, el borrado detecta la asociación; si el borrado gana, el alta revalida y aborta. Pasó cinco ejecuciones consecutivas y una ejecución adicional en la suite completa.
- `tests/json_store_faults.sh` inyecta fallos en `fsync` del archivo y del directorio y mata el proceso de commit antes y después de `os.replace`. Pasó tres ejecuciones consecutivas y otra dentro de la suite completa; verifica que el destino visible sea siempre JSON completo y documenta que un fallo del `fsync` del directorio ocurre después de que el nuevo destino ya puede estar visible.
- Contrato de error posterior al reemplazo: `json_store_commit` devuelve `3` si `os.replace` se completó pero falla el `fsync` del directorio. `users_atomic_update` y `connections_atomic_update` reconocen ese código, conservan el cambio aplicado y emiten una advertencia sobre durabilidad no confirmada; otros errores previos al reemplazo siguen fallando normalmente.

### Límites pendientes

- Falta probar colisiones concurrentes de puertos/sockets, pérdida real de alimentación/kernel, corrupción física del sistema de archivos y recuperación tras reinicio. Los fallos de `fsync` e interrupciones controladas a nivel de proceso están cubiertos por `tests/json_store_faults.sh`, pero no sustituyen esas pruebas de sistema.
- El archivo heredado `/var/lib/xray-manager/connections.json` permanece intacto.
- No se modificó la configuración runtime, el servicio Xray, systemd, firewall ni SSH.