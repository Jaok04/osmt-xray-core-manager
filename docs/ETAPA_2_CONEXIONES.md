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
- Bloqueo exclusivo `flock` antes de inicializar, validar, leer o modificar el JSON.
- Escritura atómica mediante archivo temporal, permisos privados (0600) y reemplazo con `mv`.
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
5. Añadir pruebas de integración para colisiones de sockets y concurrencia de procesos.


## Ampliación VLESS XHTTP

Se agregaron `vless_xhttp`, `vless_xhttp_tls` y `vless_xhttp_reality` sin retirar WebSocket ni gRPC. Las nueve modalidades VLESS están contempladas por el modelo neutral y el adaptador versionado Xray v26.10.31. La validación de configuración se realiza en `tests/xray_vless_integration.sh`; los detalles del contrato de opciones y sus límites están en `GENERADOR_VLESS_DISENO.md`.