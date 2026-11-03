# Xray Manager — Etapa 2: Gestión de protocolos y conexiones

**Versión:** 1.3  
**Estado:** APROBADA — especificación funcional  
**Fecha de aprobación:** 30/10/2026  
**Proyecto:** Xray Core Manager

## 1. Objetivo

Definir la organización visual y funcional del módulo **Gestión de protocolos y conexiones**, incluyendo las familias de protocolos aprobadas, sus modalidades, los flujos para crear y administrar configuraciones y las reglas de navegación.

Esta etapa define el alcance funcional. No contiene implementación Bash ni implica que todas las modalidades estén técnicamente implementadas. Antes de programar se deberá validar cada combinación con la versión concreta de Xray-core y con los componentes externos que correspondan.

## 2. Menú principal del módulo

Se accede desde la opción `[1] Gestión de protocolos y conexiones` del menú principal.

```text
╔══════════════════════════════════════════════╗
║       GESTIÓN DE PROTOCOLOS Y CONEXIONES     ║
╠══════════════════════════════════════════════╣
║  PROTOCOLOS PRINCIPALES                      ║
║  [1] VLESS                                   ║
║  [2] VMess                                   ║
║  [3] Trojan                                  ║
║  [4] Shadowsocks                             ║
║  [5] Hysteria2                               ║
║                                              ║
║  PROTOCOLOS OPCIONALES                       ║
║  [6] Protocolos opcionales                   ║
║                                              ║
║  [0] Volver al menú principal               ║
╚══════════════════════════════════════════════╝
```

## 3. Protocolos principales

### 3.1 VLESS

```text
╔══════════════════════════════════════════════╗
║              ADMINISTRAR VLESS              ║
╠══════════════════════════════════════════════╣
║  [1] VLESS-WS                               ║
║      (Sin TLS)                              ║
║  [2] VLESS-TLS                              ║
║      (RAW/TCP + TLS)                        ║
║  [3] VLESS-WS-TLS                           ║
║      (WebSocket + TLS)                      ║
║  [4] VLESS-REALITY                          ║
║      (RAW/TCP + REALITY)                    ║
║  [5] VLESS-GRPC                             ║
║      (TLS o REALITY)                        ║
║  [0] Volver                                 ║
╚══════════════════════════════════════════════╝
```

Decisiones aprobadas:
- Se conservan las cinco modalidades mostradas.
- VLESS-GRPC permitirá elegir el modo de seguridad previsto (TLS o REALITY) durante la creación.
- VLESS-WS sin TLS permanece disponible y debe identificarse claramente como una modalidad sin TLS.
- La combinación exacta de transporte y seguridad deberá validarse con la versión objetivo antes de implementarla.

### 3.2 VMess

```text
╔══════════════════════════════════════════════╗
║              ADMINISTRAR VMESS              ║
╠══════════════════════════════════════════════╣
║  PRINCIPALES                                 ║
║  [1] VMess-WS                               ║
║  [2] VMess-TLS                              ║
║  [3] VMess-WS-TLS                           ║
║  [4] VMess-REALITY                          ║
║  [5] VMess-GRPC                             ║
║                                              ║
║  ADICIONALES                                 ║
║  [6] VMess-HTTPUpgrade                      ║
║  [7] VMess-XHTTP                            ║
║  [8] VMess-mKCP                             ║
║  [0] Volver                                 ║
╚══════════════════════════════════════════════╝
```

Decisiones aprobadas:
- Se mantienen cinco modalidades principales y tres adicionales.
- VMess-GRPC: durante la creación se contempla seleccionar sin TLS, TLS o REALITY.
- VMess-XHTTP: durante la creación se contempla seleccionar sin TLS, TLS o REALITY.
- VMess-mKCP: durante la creación se contempla seleccionar sin TLS o TLS; no se ofrecerá REALITY.
- VMess-WS se identifica como WebSocket sin TLS adicional; VMess conserva su cifrado propio.
- VMess utiliza UUID y su mecanismo de cifrado propio.
- Las combinaciones de transporte y seguridad se verificarán contra la versión objetivo de Xray-core antes de implementar. La clasificación aprobada es el diseño del menú, no una garantía anticipada de compatibilidad de todas las combinaciones.

### 3.3 Trojan

```text
╔══════════════════════════════════════════════╗
║              ADMINISTRAR TROJAN             ║
╠══════════════════════════════════════════════╣
║  PRINCIPALES                                 ║
║  [1] Trojan-TLS                             ║
║  [2] Trojan-WS-TLS                          ║
║  [3] Trojan-GRPC-TLS                        ║
║                                              ║
║  ADICIONALES                                 ║
║  [4] Trojan-XHTTP-TLS                       ║
║  [5] Trojan-HTTPUpgrade-TLS                 ║
║  [0] Volver                                 ║
╚══════════════════════════════════════════════╝
```

Decisiones aprobadas:
- Las modalidades incluidas se presentan con TLS.
- No se incluyen Trojan sin TLS ni Trojan-REALITY en esta clasificación.
- La compatibilidad de cada transporte se verificará antes de implementar.

### 3.4 Shadowsocks

```text
╔══════════════════════════════════════════════╗
║           ADMINISTRAR SHADOWSOCKS           ║
╠══════════════════════════════════════════════╣
║  [1] Shadowsocks-TCP                        ║
║  [2] Shadowsocks-UDP                        ║
║  [3] Shadowsocks-TCP-UDP                    ║
║                                              ║
║  OFUSCACIÓN / PLUGINS                        ║
║  [4] Shadowsocks + OBFS                     ║
║      [1] OBFS-HTTP                          ║
║      [2] OBFS-TLS                           ║
║  [5] Shadowsocks + V2Ray-Plugin             ║
║  [0] Volver                                 ║
╚══════════════════════════════════════════════╝
```

Parámetros funcionales contemplados:
- Método de cifrado.
- Contraseña.
- Puerto.
- Red: TCP, UDP o TCP-UDP, según la modalidad.
- Plugin y sus parámetros, cuando se seleccione una opción de plugin.

Métodos de cifrado considerados en el diseño:
- AEAD clásicos: `aes-128-gcm`, `aes-256-gcm`, `chacha20-poly1305`.
- AEAD 2022: `2022-blake3-aes-128-gcm`, `2022-blake3-aes-256-gcm`, `2022-blake3-chacha20-poly1305`.

Condiciones técnicas:
- Shadowsocks dispone de cifrado propio; TLS no es obligatorio para las modalidades TCP/UDP básicas.
- OBFS-HTTP, OBFS-TLS y V2Ray-Plugin se conservan en el diseño funcional, pero dependen de componentes externos compatibles.
- Los plugins no se presentarán como funciones nativas de Xray-core. Antes de habilitarlos se verificará el binario, la compatibilidad, los parámetros y la disponibilidad del componente tanto donde corresponda en cliente como en servidor.
- No se agregan modalidades independientes Shadowsocks-WS ni Shadowsocks-WS-TLS en esta aprobación.

### 3.5 Hysteria2

```text
╔══════════════════════════════════════════════╗
║             ADMINISTRAR HYSTERIA             ║
╠══════════════════════════════════════════════╣
║  HYSTERIA 2                                  ║
║  [1] Hysteria2-QUIC                          ║
║      (UDP + TLS)                             ║
║                                              ║
║  [0] Volver                                  ║
╚══════════════════════════════════════════════╝
```

Parámetros contemplados para el asistente de creación:
1. Conexión: dominio o IP y puerto UDP.
2. TLS: certificado, clave privada, SNI y validación correspondiente.
3. Usuarios: contraseña de autenticación e identificador.
4. Velocidad: límites o valores de subida y descarga, según soporte.
5. UDP: opciones de retransmisión UDP disponibles.
6. Masquerade: opciones de respuesta o destino, únicamente si están soportadas por la versión objetivo.
7. Resumen: mostrar los parámetros antes de guardar y aplicar.

Condiciones técnicas:
- La clasificación aprobada es Hysteria2 sobre QUIC/UDP con TLS.
- No se crean variantes artificiales WS, gRPC, REALITY o TCP.
- No se ofrecen Salamander ni Gecko como opciones del administrador hasta verificar soporte real en la versión objetivo y en la configuración de Xray seleccionada.
- La implementación deberá distinguir Hysteria2 integrado en Xray-core de servidores o clientes Hysteria independientes.

## 4. Protocolos opcionales

El menú opcional contiene exclusivamente SOCKS, HTTP Proxy y WireGuard. Se excluyen Tunnel (Dokodemo-door), TUN y MASQUE.

```text
╔══════════════════════════════════════════════╗
║             PROTOCOLOS OPCIONALES           ║
╠══════════════════════════════════════════════╣
║  PROXIES AUXILIARES                         ║
║  [1] SOCKS                                  ║
║  [2] HTTP Proxy                             ║
║                                              ║
║  TÚNELES Y REDES                            ║
║  [3] WireGuard                              ║
║                                              ║
║  [0] Volver                                 ║
╚══════════════════════════════════════════════╝
```

Alcance de administración aprobado:

| Opción | Elementos administrados |
|---|---|
| SOCKS | Conexiones y credenciales |
| HTTP Proxy | Conexiones y credenciales |
| WireGuard | Peers y claves |

Notas:
- SOCKS y HTTP Proxy se administran como configuraciones de conexión y, cuando se configure autenticación, sus credenciales.
- WireGuard se administra mediante peers y claves. Cada peer debe estar asociado a una identidad global de la Etapa 3; una identidad puede tener varios peers para distintos dispositivos o accesos. Cada peer conserva sus propias claves, dirección IP y parámetros técnicos. La asociación de acceso es el vínculo administrativo entre la identidad y la conexión WireGuard; los detalles técnicos del peer pertenecen a esa asociación. Los campos concretos se definirán en el diseño técnico correspondiente.
- No se debe asumir que SOCKS o HTTP Proxy cifran por sí mismos el tráfico. La seguridad dependerá de la configuración y del entorno de uso.

## 5. Flujo común de creación y administración

Después de seleccionar una modalidad principal, o directamente después de seleccionar SOCKS, HTTP Proxy o WireGuard, se mostrará el siguiente menú:

```text
╔══════════════════════════════════════════════╗
║          ADMINISTRAR [PROTOCOLO]            ║
╠══════════════════════════════════════════════╣
║  [1] Crear una configuración nueva         ║
║  [2] Administrar configuraciones existentes║
║  [0] Volver                                 ║
╚══════════════════════════════════════════════╝
```

El título se adaptará al protocolo y, cuando corresponda, a la modalidad seleccionada.

### 5.1 Crear una configuración nueva

- Iniciar el asistente específico del protocolo/modalidad.
- Solicitar únicamente los parámetros aplicables.
- Validar entradas antes de guardar.
- Mostrar un resumen para revisión antes de aplicar cambios.
- Informar el resultado de la operación.
- Regresar al menú inmediatamente anterior después de mostrar el resultado, o permitir que el usuario vuelva según el flujo definido para el asistente.

Los campos exactos y las operaciones internas de creación se detallarán en el diseño técnico de cada protocolo y en las etapas posteriores relacionadas con usuarios, certificados y perfiles.

### 5.2 Administrar configuraciones existentes

En esta etapa, **conexión** significa una configuración técnica del servidor asociada a un protocolo, modalidad/transporte, puerto y sus parámetros técnicos. Una conexión puede admitir varias asociaciones de usuarios, según su capacidad configurada.

La distinción funcional es:
- **Conexión:** configuración técnica del servidor; se crea y administra en esta etapa.
- **Usuario:** identidad global única administrada en Etapa 3.
- **Asociación:** vínculo de acceso entre una identidad y una conexión; se administra en Etapa 3 y tiene sus propios parámetros de acceso.

Por tanto, el listado siguiente muestra conexiones, no usuarios ni asociaciones.

- Consultar las configuraciones guardadas para el protocolo y modalidad seleccionados.
- Mostrar una lista numerada y legible.
- Permitir seleccionar una configuración.
- Presentar las operaciones aplicables a esa configuración.
- Mostrar el resultado de cada operación antes de regresar.

Ejemplo ilustrativo:

```text
╔══════════════════════════════════════════════╗
║          CONEXIONES VLESS-WS                ║
╠══════════════════════════════════════════════╣
║  [1] VLESS-WS - puerto 8080                 ║
║  [2] VLESS-WS - puerto 8081                 ║
║  [3] VLESS-WS - puerto 8082                 ║
║                                              ║
║  [0] Volver                                 ║
╚══════════════════════════════════════════════╝
```

Los nombres y puertos del ejemplo son ilustrativos. Cada elemento representa una conexión técnica independiente; los usuarios que acceden a ella se consultan y administran desde Etapa 3.

### 5.3 Lista vacía

Si no existen configuraciones para el protocolo/modalidad elegidos, mostrar un mensaje informativo y la opción `[0] Volver`. No mostrar una lista vacía ni provocar un error.

## 6. Reglas de navegación

1. Todos los menús y submenús tendrán `[0] Volver`.
2. `[0]` regresará al nivel inmediatamente anterior, sin saltarse niveles.
3. En el menú principal del módulo, `[0]` regresará al menú principal de Xray Manager.
4. En los menús de modalidad, `[0]` regresará al menú de la familia de protocolo.
5. En el menú Crear/Administrar, `[0]` regresará al menú de modalidad o al menú del protocolo opcional, según corresponda.
6. En una lista de configuraciones, `[0]` regresará al menú Crear/Administrar.
7. Una entrada inválida mostrará un mensaje y permitirá reintentar.
8. Los errores de una operación no cerrarán inesperadamente el administrador.
9. Las operaciones terminadas mostrarán su resultado antes de regresar.
10. Las acciones destructivas solicitarán confirmación.
11. Al regresar al menú principal se actualizará la información de estado que corresponda.

## 7. Criterios de compatibilidad antes de implementar

La aprobación de los menús no sustituye la validación técnica. Antes de programar cada modalidad se deberá:

- Fijar la versión objetivo de Xray-core.
- Contrastar el protocolo, transporte y seguridad con la documentación y el esquema de configuración de esa versión.
- Validar qué funciones son nativas de Xray-core y cuáles dependen de binarios o servicios externos.
- No ofrecer en pantalla parámetros que el motor seleccionado no pueda aplicar.
- Registrar como pendiente cualquier combinación cuya compatibilidad no se haya comprobado.
- Probar la configuración generada antes de reiniciar o recargar el servicio.

## 8. Decisiones aprobadas y exclusiones

### Aprobado
- Cinco familias principales: VLESS, VMess, Trojan, Shadowsocks y Hysteria2.
- Tres protocolos opcionales: SOCKS, HTTP Proxy y WireGuard.
- Clasificaciones y modalidades descritas en esta etapa.
- Flujo Crear una configuración nueva / Administrar configuraciones existentes.
- Listado de configuraciones y tratamiento de lista vacía.
- Navegación jerárquica con `[0] Volver`.

### Excluido del menú opcional
- Tunnel (Dokodemo-door).
- TUN.
- MASQUE.

### Condicionado a validación técnica
- Combinaciones de transporte y seguridad de VLESS, VMess y Trojan.
- Plugins OBFS y V2Ray-Plugin de Shadowsocks.
- Parámetros opcionales de Hysteria2, incluidos Masquerade y cualquier mecanismo de ofuscación.
- Dependencias externas y capacidades no nativas del motor.

## 9. Límites de esta etapa

Esta etapa define la navegación, clasificación y alcance funcional de los protocolos y conexiones técnicas. Una conexión puede contener varias asociaciones de usuarios. La identidad global y las asociaciones de acceso se administran en Etapa 3; certificados y dominios, perfiles, respaldos, servicio, registros y mantenimiento se desarrollan en sus etapas respectivas.

## 10. Próxima etapa

**Etapa 3 — Gestión de usuarios.** Se definirá la creación, edición, suspensión, eliminación y demás operaciones de usuarios, así como su relación con las conexiones y protocolos.

---

**Control del documento:** Etapa 2 aprobada como especificación funcional, revisión 1.3. La revisión 1.2 formalizó la distinción entre conexión técnica, identidad global y asociación de acceso, y corrigió el ejemplo de listado. La revisión 1.3 define la relación de los peers WireGuard con las identidades globales y las asociaciones. Cualquier cambio posterior deberá registrarse como una nueva revisión.