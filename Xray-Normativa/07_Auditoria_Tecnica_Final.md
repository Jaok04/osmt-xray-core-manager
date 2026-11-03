# XRAY CORE MANAGER — AUDITORÍA TÉCNICA FINAL

**Versión del informe:** 1.0  
**Fecha:** 31/10/2026  
**Alcance:** coherencia global, viabilidad técnica y cierre documental de las seis etapas.  
**Naturaleza:** evaluación de diseño y documentación; no es una prueba de implementación.

## 1. Resultado ejecutivo

La documentación funcional de las seis etapas presenta una arquitectura global coherente y técnicamente viable, siempre que la implementación respete las limitaciones y condiciones indicadas en este informe.

**Resultado de cierre:** APROBADA CON CONDICIONES Y PENDIENTES EXPLÍCITOS.

Este resultado permite cerrar la fase de auditoría de diseño. No certifica que el administrador esté programado, que Xray esté configurado, ni que se hayan ejecutado pruebas en una VPS.

## 2. Trabajo 1 — Auditoría de coherencia entre las seis etapas

### 2.1 Comprobaciones realizadas

- Inventario de los documentos incluidos en el paquete: un índice general y dos documentos por cada una de las seis etapas (Markdown y YAML).
- Lectura de la estructura, menús, responsabilidades, delimitaciones y secciones de pendientes.
- Comprobación de que los seis archivos YAML se pueden analizar sintácticamente.
- Contraste de las versiones declaradas en Markdown y YAML.
- Revisión de los límites de responsabilidad y dependencias entre etapas, usando las decisiones funcionales aprobadas.

### 2.2 Coherencias confirmadas

1. **Navegación y responsabilidades:** Etapa 1 concentra el menú principal y la configuración general; Etapas 2 a 6 conservan sus módulos funcionales.
2. **Conexiones e identidades:** Etapa 2 administra conexiones técnicas; Etapa 3 administra identidades globales y asociaciones de acceso. Una identidad puede tener varias asociaciones y una conexión puede tener varias asociaciones.
3. **Certificados y dominios:** Etapa 4 administra certificados, dominios, DNS y renovaciones; el registro de un dominio no se confunde con la verificación de su DNS.
4. **Configuraciones y perfiles:** Etapa 5 distingue configuraciones independientes, copias de perfiles, estado guardado, estado aplicado y perfil activo. Seleccionar un perfil no equivale a activarlo.
5. **Servicio y mantenimiento:** Etapa 6 administra el servicio, diagnóstico, registros, red, firewall y mantenimiento; no sustituye la administración funcional de las etapas anteriores.
6. **Historiales y registros:** Etapas 4 y 5 conservan la propiedad de sus historiales. Etapa 6 centraliza consulta, exportación y limpieza sin duplicar el almacenamiento.
7. **Desinstalación:** existe un único punto de entrada acordado en Etapa 1, opción [8], evitando rutas de desinstalación duplicadas.
8. **Perfiles y servicio:** activar un perfil en Etapa 5 se mantiene separado de recargar el servicio en Etapa 6.
9. **Tareas programadas:** el planificador se concibe como infraestructura compartida, pero cada etapa conserva la responsabilidad sobre sus propias tareas.
10. **Seguridad y recuperación:** las reglas transversales de transacciones, registros, bloqueos, recuperación y permisos complementan los módulos sin cambiar su propiedad funcional.

### 2.3 Resultado de coherencia

No se identificó una contradicción estructural que obligue a rediseñar las seis etapas o sus menús. Las principales cuestiones detectadas son de integración técnica y de definición de la fuente de verdad de los datos; se detallan en las secciones siguientes y deben resolverse antes de implementar las funciones afectadas.

## 3. Trabajo 2 — Evaluación de viabilidad técnica

La evaluación se basa en las especificaciones aprobadas y en la documentación oficial de Project X (Xray). La compatibilidad real debe comprobarse con el binario y la versión instalados, no deducirse únicamente de la documentación de la versión más reciente.

### 3.1 Protocolos y transportes

**Viable con validación por versión.** La documentación oficial de Xray presenta una matriz explícita de compatibilidad entre protocolos, transportes y seguridad. VLESS, VMess y Trojan disponen de combinaciones con RAW, XHTTP, gRPC, WebSocket, HTTPUpgrade y mKCP sujetas a la matriz; REALITY no es compatible con WebSocket, HTTPUpgrade ni mKCP. gRPC puede combinarse con TLS o REALITY. Hysteria utiliza transporte QUIC con TLS obligatorio.

**Condiciones que deben conservarse en el implementador:**

- No generar combinaciones fuera de la matriz de compatibilidad de la versión detectada.
- Mantener VLESS-WS sin TLS claramente identificado como transporte sin TLS. En la documentación actual de Xray, VLESS con `security: none` y sin VLESS Encryption está limitado a destinos de red privada; no debe presentarse como equivalente a VLESS-TLS o REALITY para un servidor público.
- La opción funcional Hysteria2 debe traducirse al esquema de Xray correspondiente: protocolo `hysteria` con versión 2, transporte `hysteria` con versión 2 y TLS. No debe inventarse un protocolo independiente llamado `hysteria2` en el JSON de Xray.
- Las opciones de VMess, VLESS y Trojan deben validarse por protocolo, transporte y seguridad como una combinación, no como tres selectores independientes sin restricciones.

### 3.2 API y gestión dinámica de usuarios

**Viable parcialmente; requiere dos rutas de implementación.** La API oficial de Xray utiliza gRPC y ofrece servicios seleccionables. `HandlerService` permite agregar o quitar usuarios dinámicamente en inbounds VMess, VLESS, Trojan y Shadowsocks. La lista oficial no incluye Hysteria, WireGuard, SOCKS ni HTTP Proxy para esas operaciones dinámicas de usuario.

Por tanto:

- Usar operaciones dinámicas de API únicamente en los protocolos y operaciones que la versión detectada soporte.
- Para protocolos sin operación dinámica de usuario, usar el flujo controlado de configuración: preparar cambios, validar, respaldar, aplicar y verificar.
- No simular soporte API ni llamar a métodos no documentados.
- Mantener la API deshabilitada cuando la función no se necesite.

La configuración simplificada de API está disponible desde Xray v1.8.12 según la documentación oficial; en modo tradicional se requiere el inbound y la regla de routing indicados por Xray. El administrador debe detectar qué modalidad utiliza y no duplicar tags, inbounds o reglas existentes.

### 3.3 Estadísticas y asociación de usuarios

**Viable con cobertura condicionada al protocolo y a la política.** Xray requiere habilitar el módulo `stats` y las opciones correspondientes de `policy` para recoger los contadores. La consulta de tráfico por usuario usa el campo `email` como identificador de la estadística.

Antes de implementar:

- Definir un identificador técnico estable y único por asociación que pueda mapearse al campo `email` cuando el protocolo lo admita.
- No usar el alias visible como clave primaria.
- Verificar por protocolo que los contadores se generan y pueden asociarse a la asociación administrativa correcta.
- Cuando Xray no proporcione una estadística individual verificable, mostrarla como no disponible/no verificable; nunca convertir ausencia de datos en cero.
- Probar por separado el comportamiento de WireGuard, Hysteria y los proxies auxiliares; no asumir que todos exponen estadísticas con la misma granularidad.

### 3.4 Persistencia y fuente de verdad

**Condición crítica de arquitectura antes de implementar usuarios dinámicos.** La API puede modificar el estado en ejecución, mientras que Xray también carga configuración persistente desde archivos. Si el administrador cambia solo el runtime, un reinicio de Xray puede restaurar el contenido del archivo y perder el cambio dinámico.

Debe quedar definido un único flujo autoritativo:

1. El administrador prepara el cambio en sus registros y en la representación persistente de la configuración activa.
2. Valida referencias, IDs, capacidad y compatibilidad.
3. Aplica el cambio por API solo cuando sea compatible; en los demás casos usa el procedimiento controlado de configuración.
4. Verifica el estado real de Xray.
5. Persiste el resultado administrativo y la configuración que se usará en el siguiente arranque, de forma transaccional.
6. Si falla una fase, registra el estado parcial y activa el procedimiento de recuperación; no declara éxito ni repite a ciegas.

También debe definirse cómo se propagan —o deliberadamente no se propagan— los cambios de usuarios a perfiles y copias de configuración independientes. La independencia de perfiles aprobada no debe producir una divergencia accidental entre registros administrativos, configuración activa y runtime.

### 3.5 Certificados y dominios

**Viable, con decisiones de proveedor pendientes.** HTTP-01, DNS-01 e instalación de certificados existentes son flujos técnicamente realizables. La etapa todavía deja pendiente el cliente ACME concreto, su instalación/actualización, el proveedor DNS/API cuando se use DNS-01 y el mecanismo de renovación. Estos elementos deben seleccionarse y probarse antes de programar la automatización de certificados.

La renovación fallida no debe reemplazar un certificado válido. La integración debe validar dominio, SAN, correspondencia certificado-clave, permisos, rutas y disponibilidad del método de desafío.

### 3.6 Configuración, perfiles, respaldos y restauración

**Viable con aislamiento obligatorio para pruebas.** La separación de configuraciones independientes y copias de perfiles es realizable. La validación estática y la prueba nativa de Xray deben mantenerse diferenciadas.

La prueba de carga/runtime no debe iniciar una segunda instancia sobre los mismos puertos, sockets, rutas de logs o archivos de estado de la instancia activa. Si no se puede crear un entorno aislado verificable, la prueba se marca como no disponible/no verificable y no se sustituye por una simple validación JSON.

El flujo de restauración con respaldo de seguridad obligatorio, vista previa, aplicación selectiva y verificación es viable, pero exige transacciones, journal y rollback probados antes de habilitar restauraciones reales.

### 3.7 Procesos, concurrencia, registros y tareas

**Viable en Linux/Ubuntu con detección de capacidades.** `flock`, systemd, permisos POSIX, procesos secundarios y directorios de runtime permiten implementar los mecanismos descritos. No se debe asumir que todas las distribuciones, sistemas de archivos o instalaciones tienen las mismas herramientas o capacidades; las funciones deben habilitarse según detección y pruebas.

Las tareas programadas deben tener identidad, estado, journal y política de recuperación. La finalización del menú no debe cancelar tareas independientes; el cierre de Xray no debe cancelar tareas administrativas no relacionadas.

### 3.8 Seguridad de la API

La escucha en loopback reduce la exposición de red, pero no autentica ni aísla por sí sola a otros procesos locales. La documentación oficial muestra el servicio gRPC y su configuración; la autorización local adicional debe resolverse mediante controles del sistema operativo y permisos compatibles. No se debe afirmar que Xray ofrece autenticación de API si no se ha implementado y verificado un mecanismo específico.

Si no se puede restringir el acceso a la API a procesos autorizados, no se habilita la API administrativa.

## 4. Trabajo 3 — Informe de cierre y registro de pendientes

### 4.1 Decisiones aprobadas y excepciones

- Puntos técnicos 1–113: aprobados a nivel de diseño, conforme al registro de auditoría de la conversación.
- Punto 55: autenticidad mediante firmas digitales, pospuesto; no se considera aprobado ni implementado.
- Punto 61: frecuencia de consulta de estadísticas/API, omitida por ahora; no se considera aprobada ni descartada.
- Punto 114: integridad y protección frente a manipulación, omitido por ahora; no se considera aprobado ni descartado.
- Puntos 110–113: cierre del subsistema de instancias, integración y revisiones transversales de seguridad, aprobados a nivel de diseño.

### 4.2 Pendientes que bloquean funciones concretas

| Área | Decisión o prueba pendiente | Efecto si no se resuelve |
|---|---|---|
| API/usuarios | Matriz de operaciones dinámicas por versión y protocolo | Deshabilitar solo las operaciones no soportadas; usar flujo de configuración cuando corresponda |
| Persistencia | Fuente de verdad y sincronización entre registros, archivo activo y runtime | No habilitar cambios dinámicos de usuarios hasta asegurar persistencia tras reinicio |
| Estadísticas | Mapeo de ID de asociación a `email` y cobertura real por protocolo | Mostrar datos no disponibles donde no exista asociación verificable |
| Protocolos | Matriz exacta de versión/transporte/seguridad y pruebas de configuración | Bloquear solo combinaciones incompatibles |
| Hysteria2 | Mapeo exacto a protocolo/transporte Hysteria versión 2 y TLS | No generar JSON hasta validar el esquema con la versión objetivo |
| Certificados | Cliente ACME, proveedor DNS y política de renovación | No activar automatización de obtención/renovación hasta elegir y probar el cliente |
| Runtime | Método de prueba aislada sin interferir con Xray activo | Mantener la prueba runtime como no disponible; no confundirla con validación estática |
| API local | Aislamiento efectivo de procesos locales autorizados | No habilitar API administrativa si no se puede verificar el control de acceso |
| Firmas | Punto 55 pospuesto | No afirmar autenticidad criptográfica del administrador basada en firmas |
| Integridad antimanipulación | Punto 114 omitido | No afirmar que se completó esa auditoría específica |

### 4.3 Pruebas obligatorias antes de declarar estable una implementación

1. Pruebas de sintaxis, lint y validación de todos los módulos Bash.
2. Pruebas unitarias de validadores, almacenamiento, IDs, locks, journal y transacciones.
3. Pruebas de configuración nativa con cada versión de Xray soportada.
4. Pruebas de creación, edición, suspensión, expiración, renovación y eliminación por asociación.
5. Pruebas de estadísticas por protocolo y de casos sin datos.
6. Pruebas de persistencia después de reinicio y de reconciliación con cambios externos.
7. Pruebas de certificados HTTP-01/DNS-01 y renovación fallida sin reemplazo del certificado válido.
8. Pruebas de respaldo, restauración, rollback, corrupción e interrupción.
9. Pruebas de concurrencia, procesos secundarios, cierre abrupto y recuperación.
10. Pruebas de permisos, secretos, API local, firewall y protección SSH en un entorno aislado.
11. Pruebas en las arquitecturas y versiones de sistema operativo que se declaren soportadas.

### 4.4 Criterio para iniciar implementación

Se puede iniciar la implementación modular después de congelar la versión objetivo de Xray y definir los contratos internos y la fuente de verdad de los datos. No es necesario resolver todas las funciones opcionales antes de empezar: cada función puede permanecer deshabilitada hasta superar su propia matriz de compatibilidad y pruebas.

No se debe habilitar una función si su validación, persistencia, recuperación o protección de acceso no puede demostrarse.

## 5. Fuentes técnicas oficiales consultadas

- Project X — Transport Configuration: https://xtls.github.io/en/config/transport.html
- Project X — API Interface: https://xtls.github.io/en/config/api.html
- Project X — Statistics: https://xtls.github.io/en/config/stats.html
- Project X — Hysteria inbound: https://xtls.github.io/en/config/inbounds/hysteria.html
- Project X — Hysteria transport: https://xtls.github.io/en/config/transports/hysteria.html
- Project X — Inbound Proxy: https://xtls.github.io/en/config/inbound.html

Estas páginas documentan la configuración actual de Project X y pueden evolucionar. La implementación debe fijar y probar una versión concreta; las páginas de documentación por sí solas no sustituyen esas pruebas.

---

**Conclusión:** la auditoría de coherencia y viabilidad del diseño queda cerrada con condiciones explícitas. Las seis etapas funcionales conservan sus decisiones aprobadas. Los pendientes se trasladan a la matriz de implementación y pruebas, sin convertirlos en aprobaciones implícitas ni afirmar que el software ya funciona.