# Diseño del generador VLESS

**Estado:** diseño técnico previo a la implementación del serializador.  
**Proyecto:** Xray Core Manager 0.2.0-dev.

## 1. Objetivo y límites

Definir un modelo interno neutral para las seis modalidades VLESS presentes en `config/protocols.tsv`. El modelo no debe depender de los nombres de campos JSON de una versión concreta de Xray.

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

La modalidad del catálogo es la fuente de verdad para transporte y seguridad. No se permitirá que una entrada de usuario cambie libremente esos dos atributos y produzca combinaciones no representadas por el catálogo.

## 3. Modelo interno neutral

El objeto de trabajo propuesto contiene:

- `schema_version`: versión del esquema interno del administrador.
- `connection_id`: identificador de la conexión registrada.
- `protocol`: valor fijo `vless`.
- `mode_id`: ID exacto del catálogo.
- `transport`: `raw`, `websocket` o `grpc`.
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
3. REALITY requiere sus parámetros propios; no es un alias de TLS y no debe heredar opciones de certificados.
4. No combinar REALITY con WebSocket, HTTPUpgrade ni mKCP.
5. gRPC con TLS y gRPC con REALITY son modalidades separadas y requieren validación específica.
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
3. Añadir pruebas positivas y negativas para las seis modalidades.
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

**Implementado:** `modules/vless_model.sh` resuelve las seis modalidades anteriores y valida ID de conexión, modalidad, dirección de escucha explícita y puerto. `vless_model_build` emite un objeto JSON neutral con `schema_version=1`, transporte y seguridad derivados exclusivamente de `mode_id`, opciones vacías y lista de usuarios vacía. No incorpora `flow` si no se ha definido.

**Pruebas:** `tests/smoke.sh` comprueba las seis correspondencias, los campos del modelo y rechazos de modalidades, puertos, direcciones e ID inválidos. La entrada principal carga el módulo.

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

**Pendiente:** validar fixtures independientes para WebSocket, gRPC, TLS y REALITY; implementar el serializador final solo después de definir los parámetros requeridos de certificados, transporte y REALITY. No se inferirán ni generarán credenciales o secretos de producción.