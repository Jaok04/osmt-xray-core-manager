# Diseño técnico — VMess

**Proyecto:** Xray Core Manager
**Etapa:** 2 — Gestión de protocolos y conexiones
**Estado:** DISEÑO APROBADO por el propietario el 2026-11-02
**Motor objetivo:** Xray-core v26.10.31
**Base funcional:** `/root/Xray_Manager_Documentacion_Final_2026-10-31/02_Protocolos_Conexiones/Etapa_2_Protocolos.md`, revisión 1.3
**Decisión complementaria:** `docs/DECISIONES_ETAPA_2.md`

## 1. Objetivo y límites

Definir el modelo, las combinaciones de transporte/seguridad, la generación y validación de configuración Xray, el asistente de creación, la persistencia y las pruebas de VMess.

El alcance incluye expresamente **VMess-HTTPUpgrade-TLS**, aprobado por el propietario junto con el diseño. La aprobación del diseño no significa que todas las combinaciones estén implementadas o verificadas.

La primera integración crea y valida borradores/previsualizaciones. No activa conexiones, no modifica el runtime de Xray, no abre puertos ni cambia firewall, certificados desplegados o servicio. La activación transaccional pertenece a trabajo posterior y requiere su propio diseño y autorización.

## 2. Contraste con la especificación preliminar

La revisión 1.3 enumera VMess-WS, VMess-TLS, VMess-WS-TLS, VMess-REALITY, VMess-GRPC, VMess-HTTPUpgrade, VMess-XHTTP y VMess-mKCP. También exige validar cada combinación contra la versión concreta de Xray-core.

La decisión complementaria del propietario amplía el detalle funcional para incluir **HTTPUpgrade con TLS**, sin reescribir retroactivamente la especificación preliminar. Se conserva la distinción entre diseño aprobado, compatibilidad comprobada, implementación y aceptación.

## 3. Matriz de modalidades aprobadas

| Familia | Transporte | Seguridad permitida | Identificador de catálogo |
|---|---|---|---|
| VMess-WS | WebSocket | Sin TLS adicional | `vmess_ws` |
| VMess-TLS | RAW/TCP | TLS | `vmess_tcp_tls` |
| VMess-WS-TLS | WebSocket | TLS | `vmess_ws_tls` |
| VMess-REALITY | RAW/TCP | REALITY | `vmess_reality` |
| VMess-GRPC | gRPC | Sin TLS, TLS o REALITY | `vmess_grpc`, `vmess_grpc_tls`, `vmess_grpc_reality` |
| VMess-HTTPUpgrade | HTTPUpgrade | Sin TLS o TLS | `vmess_httpupgrade`, `vmess_httpupgrade_tls` |
| VMess-XHTTP | XHTTP | Sin TLS, TLS o REALITY | `vmess_xhttp`, `vmess_xhttp_tls`, `vmess_xhttp_reality` |
| VMess-mKCP | mKCP | Sin TLS o TLS | `vmess_mkcp`, `vmess_mkcp_tls` |

No se ofrecerá REALITY para WebSocket, HTTPUpgrade ni mKCP. No se crearán combinaciones adicionales por inferencia.

### 3.1 HTTPUpgrade-TLS

VMess-HTTPUpgrade-TLS forma parte del alcance aprobado. El asistente deberá permitir seleccionar explícitamente entre HTTPUpgrade sin TLS y HTTPUpgrade con TLS. La variante TLS usará los parámetros y referencias de certificado/clave privada admitidos por el adaptador Xray objetivo; los secretos no se expondrán en argumentos de proceso, logs ni mensajes de error.

El catálogo ya contiene `vmess_httpupgrade_tls`, pero la navegación actual sólo selecciona `vmess_httpupgrade`. La integración deberá añadir el selector de seguridad y pruebas de navegación para ambas variantes.

## 4. Modelo neutral VMess

El modelo será independiente de la estructura JSON de Xray y validará, como mínimo:

- Identificador de conexión y modalidad del catálogo.
- Transporte y modo de seguridad, como combinación cerrada.
- Dirección de escucha, puerto y parámetros específicos del transporte.
- UUID de usuario(s), nivel y correo/etiqueta cuando aplique.
- Host, path y demás parámetros de transporte sólo cuando correspondan.
- SNI, ALPN, certificados y parámetros TLS cuando correspondan.
- Parámetros REALITY sólo en RAW/TCP, gRPC y XHTTP.
- Estado del registro como borrador y ausencia de aplicación al runtime.

VMess utilizará UUID como identificador de usuario. La estructura de usuarios de Xray es `settings.users` con `id`, `level` y `email`; no se reutilizará el formato `clients` propio del inbound VLESS. La asociación de identidades globales y accesos se integrará respetando la frontera de Etapa 3, sin redefinirla dentro de este módulo.

## 5. Adaptador Xray-core

El adaptador fijado a Xray-core v26.10.31 traducirá el modelo neutral a la configuración nativa. Debe:

1. Construir el inbound VMess y sus `settings.users`.
2. Mapear exactamente transporte, parámetros y seguridad permitidos.
3. Rechazar combinaciones no soportadas o campos incompatibles.
4. Resolver certificados y secretos mediante mecanismos privados/temporales.
5. Producir JSON temporal para revisión y `xray run -test`.
6. No escribir en la configuración activa ni reiniciar servicios.

La configuración VMess requiere sincronización horaria: el desfase de reloj cliente/servidor debe mantenerse dentro del margen documentado por Xray (120 segundos). El asistente deberá mostrar esta condición como requisito operativo.

## 6. Arquitectura y archivos previstos

- `modules/vmess_model.sh`: constantes, matriz permitida y validación neutral.
- `modules/vmess_xray_26_10_31.sh`: adaptador de modelo a JSON Xray.
- `modules/vmess_assistant.sh`: interacción, selección de modalidad, parámetros y resumen.
- `scripts/vmess_prepare_config.py`: preparación segura de JSON temporal, incluyendo secretos.
- `scripts/vmess_config_store.py`: persistencia versionada de configuraciones VMess y referencias a secretos.
- `tests/vmess_model.sh`: validación del modelo y rechazos.
- `tests/vmess_assistant.sh`: flujos interactivos y cancelación.
- `tests/xray_vmess_integration.sh`: fixtures y validación con el binario Xray objetivo.

Los nombres son el diseño aprobado; durante la implementación se podrán proponer ajustes sólo si se justifican y se obtiene autorización antes de alterar el alcance.

### 6.1 Persistencia VMess aislada (decisión aprobada durante la implementación)

Para preservar sin cambios el contrato P4 de VLESS, el almacén VMess usa rutas separadas:

- Base VMess: `/var/lib/xray-manager/vmess/`.
- Configuraciones versionadas: `/var/lib/xray-manager/vmess/configurations/`.
- Secretos cifrados: `/var/lib/xray-manager/vmess/secrets/`.
- Catálogo común: `/var/lib/xray-manager/connections/connections.json`, con referencias VMess independientes: `vmess_configuration_ref`, `vmess_secret_ref`, `vmess_configuration_revision` y `vmess_configuration_schema_version`.

VMess no escribe ni interpreta `configuration_ref`, `secret_ref`, `configuration_revision` o `configuration_schema_version`, reservados al flujo VLESS. El bloqueo de integridad compartido se conserva para serializar cambios al catálogo.

P4 VLESS no se modifica y no incluye los archivos del almacén VMess. Advertencia: el backup VLESS conserva una copia del catálogo común. Restaurar una copia antigua puede revertir/eliminar registros VMess del catálogo aunque no toque los archivos del almacén VMess; en ese caso podrían quedar archivos VMess huérfanos. No existe todavía backup/restore VMess; requiere diseño y autorización independientes.

El almacén VMess usa la clave maestra local compartida con VLESS, pero AES-256-GCM mantiene AAD específico `xray-manager:vmess-secret:v1:<connection_id>` para separar criptográficamente el contexto.

## 7. Seguridad y consideraciones operativas

- No registrar UUIDs privados, claves, material TLS/REALITY ni configuración sensible en logs.
- No pasar claves privadas por argumentos visibles de procesos.
- Validar permisos y rutas de archivos secretos; usar almacenamiento privado y temporal con limpieza garantizada.
- Mantener borradores separados de configuración activa.
- No inventar certificados ni generar secretos persistentes durante pruebas.
- Rechazar datos incompletos, UUID inválidos, puertos fuera de rango y parámetros ajenos a la modalidad.
- VMess no ofrece Forward Secrecy equivalente a TLS 1.3 por su propio mecanismo; TLS protege el transporte cuando se selecciona, pero no debe presentarse VMess como sustituto de protocolos modernos con garantías distintas.
- WebSocket y HTTPUpgrade pueden presentar patrones de tráfico identificables y tienen advertencias de mantenimiento/recomendación en la documentación de Xray. Se conservan porque forman parte del alcance aprobado; el asistente debe advertirlo sin ocultar ni retirar las modalidades.

## 8. Pruebas y criterios de aceptación

### Modelo y matriz
- Cada identificador del catálogo se resuelve a una única combinación válida.
- Se prueban todas las combinaciones de la matriz, incluyendo HTTPUpgrade sin TLS y HTTPUpgrade-TLS.
- Se rechazan REALITY en WS, HTTPUpgrade y mKCP.
- Se rechazan campos de TLS/REALITY en modalidades incompatibles.
- Se validan UUID, usuarios, puertos, paths y parámetros requeridos.

### Integración Xray
- Ejecutar `xray run -test` sobre fixtures temporales para cada combinación de la matriz.
- Registrar versión/binario exacto y resultado por modalidad.
- Incluir prueba positiva específica de VMess-HTTPUpgrade-TLS y negativas de certificados/campos ausentes o inválidos.
- `xray run -test` valida estructura/configuración; no demuestra conectividad extremo a extremo. La interoperabilidad cliente-servidor debe registrarse como prueba separada.

### Asistente y persistencia
- Recorrer cada opción del menú, incluida la elección HTTPUpgrade sin TLS/TLS.
- Verificar cancelación, EOF, entradas inválidas y resumen antes de guardar.
- Confirmar que el guardado requiere consentimiento explícito.
- Confirmar cifrado/aislamiento de secretos y que los borradores no activan runtime.
- Suite completa, sintaxis, ShellCheck, formato y `git diff --check`.

### Cierre
VMess sólo podrá declararse IMPLEMENTADO cuando el modelo, adaptador, asistente y persistencia aprobados estén integrados. Sólo podrá declararse VERIFICADO con las pruebas focales y de regresión ejecutadas. PUBLICADO, SINCRONIZADO y ACEPTADO se registrarán por separado. La Etapa 2 permanecerá abierta mientras existan protocolos o modalidades pendientes.

## 9. Resultado de la auditoría previa (referencia, no ejecución de esta revisión)

En la auditoría técnica anterior se ejecutaron pruebas temporales correctas de `xray run -test` con `settings.users` para VMess-WS sin TLS, VMess-gRPC sin TLS, VMess-XHTTP-REALITY y VMess-mKCP sin TLS: PASS. Esas pruebas no cubren toda la matriz ni conectividad real. La prueba de HTTPUpgrade-TLS queda como requisito explícito de la implementación.

## 10. Secuencia de trabajo aprobada

1. Formalizar este diseño y la decisión complementaria.
2. Contrastar nuevamente los requisitos de implementación con este diseño y la documentación preliminar antes de tocar código.
3. Presentar el informe de brechas actualizado y solicitar autorización expresa para implementar VMess.
4. Implementar sólo después de esa autorización.
5. Ejecutar pruebas, actualizar continuidad e historial y sincronizar VPS/GitHub.

**Estado de implementación local (2026-11-02):** modelo, adaptador, asistente, persistencia VMess aislada y pruebas focales están implementados en la VPS, aún sin publicar. La matriz de 14 combinaciones pasó `xray run -test`. No declarar el módulo completo hasta cerrar la suite de regresión, auditoría final y publicación/sincronización. Usuarios VMess aún manuales, pendientes de integración con asociaciones de identidad de Etapa 3. HTTPUpgrade-TLS está incluido y verificado por la matriz.