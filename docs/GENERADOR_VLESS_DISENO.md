# Diseño del generador VLESS

**Estado:** diseño técnico previo a la implementación del serializador.  
**Proyecto:** Xray Core Manager 0.2.0-dev.

## 1. Objetivo y límites

Definir un modelo interno neutral para las nueve modalidades VLESS presentes en `config/protocols.tsv`. El modelo no debe depender de los nombres de campos JSON de una versión concreta de Xray.

Esta etapa no genera todavía una configuración Xray ejecutable. Tampoco instala Xray, crea usuarios, genera credenciales, abre puertos, modifica firewall ni reinicia servicios.

## 2. Modalidades contempladas

| ID del catálogo | Transporte interno | Seguridad |
|---|---|---|
| `vless_ws` | `websocket` | `none` |
| `vless_tcp_tls` | `raw` | `tls` |
| `vless_ws_tls` | `websocket` | `tls` |
| `vless_reality` | `raw` | `reality` |
| `vless_grpc_tls` | `grpc` | `tls` |
| `vless_grpc_reality` | `grpc` | `reality` |
| `vless_xhttp` | `xhttp` | `none` |
| `vless_xhttp_tls` | `xhttp` | `tls` |
| `vless_xhttp_reality` | `xhttp` | `reality` |

La modalidad del catálogo es la fuente de verdad para transporte y seguridad. No se permitirá que una entrada de usuario cambie libremente esos dos atributos y produzca combinaciones no representadas por el catálogo.

## 3. Modelo interno neutral

El objeto de trabajo propuesto contiene:

- `schema_version`: versión del esquema interno del administrador.
- `connection_id`: identificador de la conexión registrada.
- `protocol`: valor fijo `vless`.
- `mode_id`: ID exacto del catálogo.
- `transport`: `raw`, `websocket`, `grpc` o `xhttp`.
- `security`: `none`, `tls` o `reality`.
- `listen_address`: dirección de escucha explícita; nunca inferida silenciosamente.
- `listen_port`: puerto validado de la conexión.
- `transport_options`: opciones específicas del transporte.
- `security_options`: opciones específicas de TLS o REALITY.
- `users`: referencias a identidades/credenciales VLESS; su gestión queda pendiente de la etapa 3.
- `flow`: valor opcional, sujeto a compatibilidad comprobada con la versión y el transporte.

El modelo debe distinguir entre un campo ausente, un campo vacío y un valor explícito. No se deben inventar rutas WS, service names gRPC, dominios, certificados, UUID, claves REALITY ni valores de flow.

## 4. Reglas de compatibilidad

1. WebSocket sin TLS se representa honestamente como `security=none`; no debe etiquetarse como conexión cifrada mediante TLS.
2. TLS exige que posteriormente se definan y validen los parámetros del certificado y del nombre de servidor.
3. REALITY requiere sus parámetros propios; no es un alias de TLS y no debe heredar opciones de certificados. Se admite con RAW, gRPC y XHTTP; no con WebSocket.
4. No combinar REALITY con WebSocket, HTTPUpgrade ni mKCP.
5. gRPC con TLS y gRPC con REALITY son modalidades separadas y requieren validación específica. WebSocket y gRPC se conservan aunque Xray emita avisos de obsolescencia.
6. No habilitar Vision/flow por defecto. Su compatibilidad depende de la versión, el transporte y las opciones elegidas.
7. Las opciones de transporte que no correspondan a la modalidad deben rechazarse, no ignorarse silenciosamente.

## 5. Adaptadores por versión de Xray

El modelo neutral no serializa JSON. Un adaptador versionado será responsable de traducirlo al esquema exacto soportado por la versión de Xray seleccionada.

Antes de implementar ese adaptador se debe:

- seleccionar una versión/release concreta;
- obtener la documentación o esquema correspondiente a esa misma versión;
- verificar los nombres y la estructura de los campos de inbound, stream settings, TLS y REALITY;
- verificar la sintaxis con el binario de esa versión en un entorno aislado;
- registrar la versión del adaptador y del binario usado para validar.

No se mezclarán nombres de campos de esquemas de versiones distintas. No se utilizará documentación de la rama más reciente como prueba de compatibilidad con una versión anterior.

## 6. Dependencias con otras etapas

- **Etapa 2:** aporta el registro de conexión, ID de modalidad, puerto y capacidad.
- **Etapa 3:** debe aportar identidades, UUID/credenciales, estado y asociaciones. El generador no inventará usuarios.
- **Etapa 4:** debe aportar certificados y dominios cuando TLS lo requiera.
- **Etapa 5:** debe integrar el resultado en perfiles y respaldos con escritura transaccional.
- **Etapa 6:** debe validar y aplicar cambios al servicio, con verificación y recuperación.

El generador no debe marcar una conexión como activa ni runtime-applied por el solo hecho de construir un objeto o archivo.

## 7. Secuencia de implementación propuesta

1. Congelar este modelo neutral y sus reglas.
2. Implementar validadores puros para modalidad, transporte, seguridad y opciones permitidas.
3. Añadir pruebas positivas y negativas para las nueve modalidades.
4. Seleccionar y fijar la versión de Xray.
5. Implementar el adaptador/serializador para esa versión.
6. Validar el JSON con el binario exacto en un entorno aislado.
7. Integrar la generación con el flujo transaccional de perfiles, sin aplicar automáticamente.

## 8. Pendientes explícitos

- Versión/release exacta de Xray.
- Dirección de escucha predeterminada: debe decidirse explícitamente según el escenario.
- Modelo de opciones WebSocket y gRPC.
- Política de certificados TLS.
- Política y parámetros REALITY.
- Compatibilidad exacta de flow/Vision.
- Integración con identidades de la etapa 3.

**Criterio de aceptación de esta etapa:** ningún dato de configuración de producción se genera a partir de supuestos; las incompatibilidades se rechazan con un mensaje claro y las opciones ausentes permanecen pendientes.

## 9. Estado de implementación del modelo neutral

**Implementado:** `modules/vless_model.sh` resuelve las nueve modalidades anteriores y valida ID de conexión, modalidad, dirección de escucha explícita y puerto. `vless_model_build` emite un objeto JSON neutral con `schema_version=1`, transporte y seguridad derivados exclusivamente de `mode_id`, opciones vacías y lista de usuarios vacía. No incorpora `flow` si no se ha definido.

**Pruebas:** `tests/smoke.sh` comprueba las nueve correspondencias, los campos del modelo y rechazos de modalidades, puertos, direcciones e ID inválidos. La entrada principal carga el módulo.

**Límite:** esto todavía no es un generador de configuración Xray. No valida sintaxis IP/DNS de la dirección, no verifica la existencia de la conexión en el registro, no añade usuarios y no crea parámetros WS, gRPC, TLS o REALITY. El JSON emitido no debe instalarse ni aplicarse a Xray.

## 10. Versión objetivo fijada y validación oficial

**Versión seleccionada:** Xray-core `v26.10.31`, release estable marcado como Latest en el repositorio oficial al 1 de noviembre de 2026. Release: <https://github.com/XTLS/Xray-core/releases/tag/v26.10.31>.

- Commit de release: `a4a3dff`.
- Publicación: `2026-10-31`.
- Activo de validación del VPS: `Xray-linux-64.zip`.
- SHA-256 oficial del activo: `e4bd9119f50ae7c41658b1abd0679ae06f98bd864a2907ff33f2f2cf7081b214`.
- Versión comprobada del binario: `Xray 26.10.31 (go1.27.3 linux/amd64)`.

El archivo `config/xray-version.conf` centraliza esta fijación. El binario se descargó únicamente al caché de validación `/var/cache/xray-manager/validation/v26.10.31/`; no se instaló en `/usr/local/bin`, no se creó ni modificó un servicio y no se abrió ningún puerto.

**Validación real realizada:** `xray run -test` aceptó un fixture temporal de inbound VLESS RAW sin TLS, con `decryption: none`, escuchando en loopback. Resultado: `Configuration OK.` El fixture está aislado en el caché de validación y no se aplicó al servicio.

**Aviso de seguridad del release:** el anuncio oficial identifica esta versión como actualización urgente que desactiva MPTCP por defecto debido a un riesgo de escalada remota asociado a MPTCP en Linux con Go 1.24+. También recomienda actualizar el kernel Linux. La actualización del kernel del VPS no se ha realizado y queda fuera de este cambio.

**Pendiente:** validar fixtures independientes para WebSocket, gRPC, XHTTP, TLS y REALITY; ampliar posteriormente las opciones avanzadas XHTTP solo después de definir los parámetros requeridos de certificados, transporte y REALITY. No se inferirán ni generarán credenciales o secretos de producción.

## 11. Adaptador versionado VLESS -> Xray-core v26.10.31

**Implementado:** `modules/vless_xray_26_10_31.sh` contiene `vless_xray_26_10_31_build <modelo.json> <opciones.json>`. Recibe el modelo neutral y un objeto de opciones explícitas; emite por stdout una configuración completa de Xray. No escribe la configuración, no crea usuarios ni aplica cambios.

### Contrato de opciones

| Modalidad | Opciones obligatorias |
|---|---|
| `vless_ws` | `path` (debe comenzar por `/`) |
| `vless_tcp_tls`, `vless_ws_tls` | `certificate_file`, `key_file` (archivos legibles) |
| `vless_reality` | `target`, `server_names`, `private_key`, `short_ids` |
| `vless_grpc_tls` | `service_name`, `certificate_file`, `key_file` |
| `vless_grpc_reality` | `service_name`, `target`, `server_names`, `private_key`, `short_ids` |
| `vless_xhttp` | `path`, `mode` |
| `vless_xhttp_tls` | `path`, `mode`, `certificate_file`, `key_file` |
| `vless_xhttp_reality` | `path`, `mode`, `target`, `server_names`, `private_key`, `short_ids` |

Las claves adicionales se rechazan. No se generan rutas, nombres de servicio, certificados ni claves. Los usuarios se toman del arreglo `users` del modelo; mientras la etapa 3 no los gestione, el modelo puede seguir produciendo una lista vacía para pruebas, pero esa configuración no ofrece acceso autenticado a clientes.

### Estructura de Xray verificada en la etiqueta exacta

- `streamSettings.method`: `raw`, `websocket`, `grpc` o `xhttp`.
- `streamSettings.security`: `none`, `tls` o `reality`.
- WebSocket: `wsSettings.path`.
- gRPC: `grpcSettings.serviceName`.
- XHTTP: `xhttpSettings.path` y `xhttpSettings.mode`.
- TLS: `tlsSettings.certificates[].certificateFile` y `keyFile`.
- REALITY: `realitySettings.target`, `type`, `serverNames`, `privateKey`, `shortIds`.

La modalidad y la pareja transporte/seguridad deben coincidir exactamente con el catálogo. El serializador no permite combinaciones arbitrarias.

### Prueba de integración

Se añadió `tests/xray_vless_integration.sh`. Utiliza el binario de validación en caché, crea un certificado autofirmado y una clave REALITY efímeros, genera nueve configuraciones temporales y ejecuta `xray run -test` en cada una. El directorio temporal y las claves se eliminan al salir.

**Resultado en VPS (2026-11-01):** las nueve modalidades devolvieron `Configuration OK.`; las pruebas negativas de opciones incompletas y modo XHTTP desconocido también pasaron. No se inició Xray como servicio ni se abrió ningún socket.

### Advertencias del propio binario

Xray v26.10.31 emite avisos de que WebSocket y gRPC están obsoletos/no recomendados y sugiere migrar a XHTTP. También advierte que REALITY escuchando en puertos distintos de 443 puede aumentar la probabilidad de bloqueo. Son advertencias del binario, no errores de validación. El catálogo incorpora tres modalidades XHTTP adicionales y conserva los IDs anteriores.

**Límite actual:** el adaptador es específico de v26.10.31. Todavía no se integra con un flujo de usuarios reales, certificados de producción, persistencia de perfiles, escritura transaccional ni activación del servicio. La prueba de configuración no equivale a una prueba de conectividad extremo a extremo.


## 12. Ampliación XHTTP sin retirar WebSocket/gRPC

**Decisión:** mantener todas las modalidades WebSocket y gRPC existentes e incorporar XHTTP como transporte adicional. El catálogo pasa de 35 a 38 modalidades totales y VLESS pasa de seis a nueve. No se migran registros existentes ni se cambian sus identificadores.

### Nuevas modalidades

| ID | Transporte | Seguridad | Opciones explícitas |
|---|---|---|---|
| `vless_xhttp` | XHTTP | Sin TLS | `path`, `mode` |
| `vless_xhttp_tls` | XHTTP | TLS | `path`, `mode`, `certificate_file`, `key_file` |
| `vless_xhttp_reality` | XHTTP | REALITY | `path`, `mode`, `target`, `server_names`, `private_key`, `short_ids` |

El adaptador genera `streamSettings.method: "xhttp"` y `xhttpSettings` con `path` y `mode`. Los modos aceptados por el validador son `auto`, `packet-up`, `stream-up` y `stream-one`; se exige seleccionar uno explícitamente. Para TLS se comprueba que certificado y clave sean legibles. Para REALITY se validan las listas, el formato hexadecimal de `short_ids` y el puerto de `target`.

### Verificación con Xray v26.10.31

La prueba de integración construye fixtures efímeros de XHTTP sin TLS, TLS y REALITY, con certificados autofirmados y clave REALITY temporal. Los tres fueron aceptados por `xray run -test` con `Configuration OK.`. Las seis modalidades anteriores también siguen pasando. Los fixtures y secretos de prueba se eliminan al terminar. No se inició el servicio ni se abrió ningún puerto.

**Advertencia:** la documentación oficial de Project X indica que XHTTP admite TLS y REALITY; REALITY se limita a RAW, XHTTP y gRPC. El binario v26.10.31 continúa advirtiendo que WebSocket y gRPC están obsoletos/no recomendados. Se conservan por decisión explícita de diseño, sin presentarlos como recomendación del proyecto Xray.

**Límite actual de XHTTP:** se implementó el conjunto inicial de parámetros de servidor `path` y `mode`. No se han incorporado aún `host`, `headers`, `extra`, parámetros avanzados de multiplexación ni `downloadSettings`; no se generan ni se presuponen. La validación `xray run -test` confirma la sintaxis del inbound, no la conectividad extremo a extremo ni la interoperabilidad con clientes externos.
