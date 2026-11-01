# Etapa 2 - Protocolos y conexiones

## Alcance implementado

- Catálogo de 38 modalidades previstas en `config/protocols.tsv`.
- Consulta del catálogo desde el menú de protocolos y conexiones.
- Alta de conexiones en estado `draft`.
- Listado de conexiones registradas.
- Edición de nombre, modalidad, puerto y límite de slots, únicamente en estado `draft`.
- Eliminación de borradores mediante confirmación literal `ELIMINAR`.
- Validación de identificador, nombre (máximo 64 caracteres), puerto (1-65535), límite de slots (1-100000), modalidad válida y duplicidad de puerto.
- Comprobación de puertos TCP/UDP en escucha mediante `ss -H -lntu`; si `ss` no está disponible, la operación se detiene.
- Bloqueo exclusivo `flock` compartido con el módulo de usuarios en `/run/xray-manager/integrity.lock` antes de inicializar, validar, leer o modificar registros relacionados.
- Persistencia mediante `lib/json_store.sh`: temporal en el mismo directorio, validación, permisos privados (`0600`), `fsync` del archivo, reemplazo atómico y `fsync` del directorio.
- Si el JSON existente está corrupto o no es un arreglo, el administrador se detiene y no lo sobrescribe.

## Límites importantes

Un borrador no es una conexión activa. Esta implementación no genera configuración Xray, no valida una configuración con el binario, no abre puertos, no toca firewall, no reinicia servicios y no modifica el runtime.

La detección de colisión real consulta sockets TCP/UDP que el sistema muestra como escucha mediante `ss`. Es una comprobación puntual: no reserva el puerto ni elimina la posibilidad de que otro proceso lo ocupe después. La reserva lógica del administrador se comprueba por separado contra todos los registros.

La edición y eliminación se limitan a registros cuyo estado sea exactamente `draft`. Los estados futuros o distintos de `draft` quedan protegidos. La eliminación retira el registro del JSON; no elimina configuraciones externas ni recursos del sistema.

Las modalidades de plugins externos de Shadowsocks se catalogan como dependientes de plugins y requieren comprobación de compatibilidad e instalación antes de poder aplicarse.

## Compatibilidad que debe respetarse al implementar el generador Xray

- VLESS REALITY se limita a TCP/RAW, gRPC o XHTTP; no combinarlo con WS, HTTPUpgrade ni mKCP.
- VMess gRPC y XHTTP pueden contemplar sin TLS, TLS o REALITY según la modalidad; mKCP se limita a sin TLS o TLS.
- Trojan se ofrece aquí solo con TLS en las modalidades enumeradas.
- Hysteria 2 se representa mediante el protocolo Xray `hysteria`, versión 2, transporte `hysteria` versión 2 y TLS sobre QUIC/UDP.
- Shadowsocks con OBFS o V2Ray-Plugin depende de software externo y no debe declararse operativo por el mero registro.
- SOCKS, HTTP Proxy y WireGuard son modalidades auxiliares opcionales; su generador y validación requieren pruebas específicas.

## Pendiente antes de aplicar conexiones

1. Instalar y fijar una versión de Xray-core.
2. Definir el modelo de configuración por modalidad y validarlo con `xray run -test` en entorno aislado.
3. Diseñar transacciones de aplicar/verificar/rollback sin interferir con instancias activas.
4. Verificar compatibilidad real por versión de Xray y dependencias externas.
5. Ampliar las pruebas de integración para colisiones concurrentes de sockets/puertos y fallos de persistencia; la concurrencia entre alta de usuarios y eliminación de conexiones ya tiene pruebas específicas.


## Ampliación VLESS XHTTP

Se agregaron `vless_xhttp`, `vless_xhttp_tls` y `vless_xhttp_reality` sin retirar WebSocket ni gRPC. Las nueve modalidades VLESS están contempladas por el modelo neutral y el adaptador versionado Xray v26.10.31. La validación de configuración se realiza en `tests/xray_vless_integration.sh`; los detalles del contrato de opciones y sus límites están en `GENERADOR_VLESS_DISENO.md`.


## Integridad y concurrencia entre conexiones y usuarios

- El módulo de conexiones comparte `/run/xray-manager/integrity.lock` con el módulo de usuarios para serializar cambios que afectan asociaciones entre ambos registros.
- `connections_delete_draft()` consulta el registro de usuarios mientras conserva el lock compartido y rechaza eliminar una conexión que tenga usuarios asociados.
- `tests/cross_race.sh` ejecuta procesos independientes y fuerza ambos órdenes de la carrera entre `users_create()` y `connections_delete_draft()`. Si el alta obtiene primero el lock, el borrado detecta la asociación y falla; si el borrado obtiene primero el lock, el alta revalida y falla sin crear un usuario huérfano.
- La prueba pasó cinco ejecuciones consecutivas y otra dentro de la suite completa. No se modificaron registros reales ni el runtime.


## Pruebas de fallos de persistencia

`tests/json_store_faults.sh` ejercita el helper compartido `lib/json_store.sh` en un directorio temporal aislado:

- Inyecta error en `fsync` del archivo temporal y comprueba que el destino anterior permanece intacto.
- Inyecta error en `fsync` del directorio después de `os.replace`; el destino nuevo queda visible y `json_store_commit` devuelve el código especial `3`. `connections_atomic_update` reconoce que el cambio ya se aplicó, conserva el resultado y emite una advertencia de durabilidad no confirmada.
- Termina abruptamente el proceso antes del reemplazo y comprueba que permanece el archivo anterior.
- Termina abruptamente el proceso después del reemplazo y antes del `fsync` del directorio y comprueba que el archivo nuevo visible sigue siendo JSON completo.

La prueba pasó tres ejecuciones consecutivas y otra dentro de la suite completa. Es una prueba de fallos controlados del proceso; no simula pérdida eléctrica, caída del kernel ni corrupción del sistema de archivos.

El mismo contrato de código `3` es utilizado por `users_atomic_update`; un fallo anterior al reemplazo conserva el código de error normal y no se presenta como un cambio aplicado.

## Pruebas de colisión concurrente de puertos y sockets

Se incorporó `tests/port_collisions.sh`, con fixtures JSON y locks dentro de un directorio temporal aislado. No utiliza el registro real ni modifica el runtime de Xray.

- Dos procesos independientes intentan crear simultáneamente borradores con el mismo puerto. Exactamente uno debe guardar; el segundo debe detectar la reserva lógica después de adquirir el lock compartido.
- Dos procesos editan simultáneamente borradores distintos para asignarles el mismo puerto. Exactamente una edición debe guardarse y el JSON final debe conservar la unicidad.
- Se enlaza un socket TCP en loopback y se comprueba que el alta rechaza ese puerto mediante `ss -H -lntu`.
- Se enlaza un socket UDP en loopback y se comprueba el mismo rechazo.
- Se verifican el número de registros, la unicidad de puertos y los permisos `0600` tras las operaciones concurrentes.

La prueba completa pasó cinco ejecuciones consecutivas. También pasó en la suite de regresión junto con `concurrency.sh`, `cross_race.sh`, `smoke.sh`, `users.sh`, `xray_admin.sh`, `xray_vless_integration.sh`, `json_store_faults.sh` y `uninstall.sh`. `bash -n`, ShellCheck y `shfmt -d` no reportaron problemas.

**Alcance del contrato actual:** la reserva lógica compara el número de puerto globalmente entre conexiones, sin distinguir protocolo de transporte. La comprobación de sockets consulta cualquier escucha TCP o UDP que `ss` muestre en ese número, sin distinguir dirección local. Esto refleja el comportamiento implementado; no establece todavía una política de multiplexación ni permite compartir un número de puerto entre transportes.

**Limitación:** `ss` es una observación puntual, no una reserva del socket. Un proceso externo podría ocupar el puerto después de la comprobación y antes de que una futura configuración se aplique. La exclusión mutua del Manager solo serializa sus propios cambios; no coordina procesos externos. La prueba valida el comportamiento del registro y la detección de sockets, no un bind real de Xray ni una garantía frente a carreras con procesos ajenos.