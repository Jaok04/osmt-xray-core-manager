# Validación cliente-servidor VMess — VM-47 — 2026-11-02

## 1. Objetivo y alcance

Comprobar conectividad de datos real entre un cliente Xray y un servidor Xray mediante VMess-TLS (RAW/TCP + TLS), y demostrar que una solicitud de aplicación atraviesa el túnel y llega al destino. La prueba se ejecutó de forma aislada en la VPS de desarrollo, utilizando exclusivamente loopback.

Esta prueba valida el plano de datos cliente-servidor en una topología local. No equivale a probar un cliente de terceros, otra máquina, una ruta WAN/Internet o conectividad desde fuera de la VPS; esos escenarios permanecen fuera de esta evidencia.

## 2. Línea base

- Proyecto: `/opt/xray-manager`.
- Rama: `design/user-identity-association-v1`.
- HEAD de partida: `46c13148b4d3f8324eb5b7c20ca39dc701ed04f6`.
- Xray-core: `26.10.31`, build `a4a3dff`, binario de validación en caché `/var/cache/xray-manager/validation/v26.10.31/xray`.
- Catálogo compartido antes/después: vacío.
- Servicio Xray del sistema: `inactive` antes/después.

Se contrastó `docs/DISEÑO_TECNICO_VMESS.md`, sección 8: `xray run -test` no demuestra conectividad extremo a extremo; la interoperabilidad cliente-servidor debe registrarse como prueba separada.

## 3. Topología temporal

Todos los listeners se limitaron a `127.0.0.1`:

| Componente | Dirección | Función |
|---|---|---|
| Servidor Xray VMess-TLS | `127.0.0.1:43892` | Inbound VMess con TLS |
| Cliente Xray SOCKS | `127.0.0.1:10808` | Recibe la solicitud local y la envía por VMess-TLS |
| Servicio HTTP de prueba | `127.0.0.1:18080` | Destino de la solicitud; responde con un marcador único |

El UUID de prueba fue generado aleatoriamente y sólo se utilizó durante esta ejecución. El certificado autofirmado y su clave privada fueron temporales. El cliente verificó el certificado mediante su huella SHA-256 (`pinnedPeerCertSha256`); no se usó `allowInsecure`.

## 4. Integración con el proyecto

La configuración del servidor se generó con las funciones reales:

- `vmess_model_build` (`modules/vmess_model.sh`), modalidad `vmess_tcp_tls`.
- `vmess_xray_26_10_31_build` (`modules/vmess_xray_26_10_31.sh`).

El adaptador generó el inbound VMess usando `settings.users`, UUID, `alterId: 0`, `security: "auto"`, `level` y `email`, de acuerdo con el modelo del proyecto. Para el ensayo se añadió sólo a la configuración temporal del servidor una regla `freedom.finalRules` que permite TCP a `127.0.0.1/32`, puerto `18080`. No se modificó el adaptador, el catálogo ni ninguna configuración persistente.

El cliente temporal utilizó el mismo UUID, transporte RAW/TCP, TLS y un inbound SOCKS local. La huella SHA-256 del certificado de prueba se fijó explícitamente.

## 5. Resultados

| Comprobación | Resultado |
|---|---|
| Modelo VMess generado por el proyecto | PASS |
| Configuración del servidor generada por el adaptador | PASS |
| `xray run -test` del servidor | PASS — `Configuration OK` |
| `xray run -test` del cliente | PASS — `Configuration OK` |
| Listener servidor en loopback | PASS |
| Listener SOCKS cliente en loopback | PASS |
| Solicitud SOCKS → VMess-TLS → inbound VMess → outbound del servidor | PASS |
| Servicio HTTP destino recibió `GET /probe.txt` | PASS — HTTP 200 |
| Contenido recibido por el cliente | `VMESS-VM47-END-TO-END-OK` |

Evidencia de logs:

- Cliente: `TCP Connect request` y `tunneling request ... via 127.0.0.1:43892`.
- Servidor: `proxy/vmess/inbound: received request for tcp:127.0.0.1:18080`.
- Servidor: conexión aceptada asociada al usuario sintético `vm47-adapter@invalid`.
- Outbound servidor: `connection opened to tcp:127.0.0.1:18080`.
- HTTP destino: `GET /probe.txt HTTP/1.1` con respuesta `200`.

La respuesta recibida por `curl` coincidió exactamente con el marcador esperado.

## 6. Hallazgos técnicos de la ejecución

1. **TLS en Xray 26.10.31:** el cliente rechazó inicialmente `allowInsecure`, opción retirada por esta versión. La prueba final utilizó `pinnedPeerCertSha256` con la huella del certificado efímero.
2. **Protección del outbound `freedom`:** Xray bloquea por defecto destinos privados/reservados para tráfico procedente de inbounds VMess si ninguna regla explícita coincide. Para alcanzar el servicio HTTP loopback se utilizó una excepción temporal, limitada conjuntamente a TCP, `127.0.0.1/32` y puerto `18080`. Esa regla no se incorporó al proyecto ni a configuraciones persistentes.
3. **Aviso de VMess:** Xray 26.10.31 muestra una advertencia de que VMess carece de Forward Secrecy, está deprecado/no recomendado y podría retirarse en el futuro; recomienda migrar a VLESS Encryption. El aviso no impidió validar ni completar el tráfico. Se registra como advertencia de compatibilidad del core, no como fallo de la prueba.

## 7. Limpieza y seguridad

Se detuvieron los dos procesos Xray temporales y el servidor HTTP. Se comprobó que los listeners `43892`, `10808` y `18080` dejaron de escuchar y que los procesos de prueba terminaron.

No se modificaron:

- Servicio Xray del sistema ni unidades systemd.
- Firewall, reglas iptables/nftables o puertos públicos.
- Configuración de runtime del proyecto.
- Catálogo de conexiones o almacén persistente VMess/VLESS.
- Certificados desplegados o claves permanentes.

Todos los archivos de prueba se generaron bajo `/run/xray-manager/vmess-vm47/` y se retiraron tras registrar esta evidencia. Se comprobó que el directorio temporal ya no existe. No se guardó UUID, clave privada, certificado ni configuración temporal en Git.

## 8. Conclusión

**VM-47: VERIFICADO — conectividad cliente-servidor VMess-TLS en loopback local.** El modelo y el adaptador reales del proyecto generaron el lado servidor; el cliente Xray estableció el túnel TLS/VMess y transportó una solicitud HTTP hasta el destino, que respondió correctamente.

**Límite pendiente:** no se ha probado una máquina cliente externa, cliente de terceros ni conectividad por WAN/Internet. La aceptación formal del módulo VMess continúa pendiente del propietario; la Etapa 2 permanece ABIERTA.
