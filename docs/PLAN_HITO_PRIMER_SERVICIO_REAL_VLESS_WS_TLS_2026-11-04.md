# Plan de validación de viabilidad — primer servicio real VLESS + WS + TLS

**Fecha:** 2026-11-04
**Estado:** PLAN DE TRABAJO DOCUMENTAL — NO AUTORIZA CAMBIOS EN RUNTIME REAL
**Objetivo prioritario:** demostrar que Xray-Core Manager puede instalar, configurar, publicar, activar bajo confirmación, verificar, administrar y recuperar un servicio real VLESS + WebSocket + TLS.

## 1. Decisión de dirección

La prioridad de desarrollo pasa a ser la validación práctica del administrador mediante un único servicio real VLESS + WS + TLS. No se ampliará primero el catálogo de protocolos ni se desarrollarán funciones periféricas que no sean necesarias para completar este hito.

La prueba debe demostrar que las operaciones administrativas del servidor se ejecutan desde Xray-Core Manager. No se aceptará como demostración un servicio instalado o configurado manualmente fuera del administrador y luego presentado como gestionado por él.

La configuración del cliente externo (NetMod u otro cliente elegido) se realizará en el cliente; la instalación, configuración, publicación, activación, diagnóstico y recuperación del servidor deberán estar gestionadas por el administrador.

## 2. Estado de partida y reutilización obligatoria

Al corte documental, el último commit verificado es `4433cd324756eb32f2d9b6b5d48ed8dba7681e34`, rama `design/user-identity-association-v1`, con checkout VPS limpio y alineado.

- R-01: implementada, integrada, verificada/auditada, publicada y sincronizada; aceptación formal específica pendiente.
- R-02: implementada, verificada/auditada, publicada y sincronizada; aceptación formal específica pendiente.
- R-03: implementada, verificada/auditada, publicada y sincronizada; aceptación formal específica pendiente.
- R-04: implementada, verificada/auditada, publicada y sincronizada; aceptación formal específica pendiente.
- R-05: existe un diseño para orquestación simulada; no está implementada.
- R-06/live: no autorizada.
- La base ya contiene trabajo de VLESS, persistencia segura, almacén/resolución TLS centralizada y adaptadores de configuración. Algunas integraciones TLS siguen documentadas como parciales. Deben auditarse por modalidad exacta; no se volverán a implementar componentes que ya satisfagan el requisito.

Las cifras de pruebas de R-01–R-04 son evidencia histórica documentada; esta actualización no las reejecuta ni las convierte en aceptación formal.

## 3. Hito y criterio de éxito

El hito se considera técnicamente demostrado cuando, desde los menús/operaciones de Xray-Core Manager:

1. Xray-core queda instalado con una versión fijada y verificada.
2. El administrador detecta y gestiona la unidad/servicio Xray.
3. El dominio resuelve hacia el servidor y el certificado TLS es válido, corresponde al dominio y puede renovarse mediante el mecanismo administrado.
4. Se crea y persiste una conexión VLESS + WS + TLS con UUID, puerto, path, Host/SNI y certificado coherentes.
5. El perfil y la revisión exactos se validan con el binario Xray objetivo.
6. La configuración se publica mediante R-01–R-04, con snapshot, journal, integridad y rollback.
7. Toda aplicación/reinicio del servicio activo requiere confirmación explícita.
8. El administrador verifica el estado del servicio y evidencia de la generación/revisión realmente aplicada.
9. Un cliente externo establece la conexión y transmite datos en ambos sentidos.
10. Se demuestra diagnóstico y recuperación documentada sin intervención manual de shell en el servidor.

Una validación JSON o `xray run -test` por sí sola no demuestra conectividad extremo a extremo.

## 4. Plan de ejecución por bloques

### H0 — Auditoría de brechas y trazabilidad (primero)

- Inventariar código, menús, pruebas y documentos existentes para instalación, unidad systemd, certificados, DNS/ACME, VLESS WS-TLS, perfiles, publicación y diagnóstico.
- Contrastar cada requisito con la normativa aprobada de Etapas 2, 4, 5 y 6.
- Clasificar cada requisito: existente y probado; existente pero parcial; ausente; bloqueado por decisión o autorización.
- Verificar versiones/contratos de Xray y componentes externos sin instalar ni actualizar dependencias.
- Entregar matriz requisito → módulo existente → brecha → trabajo → prueba → autorización.
- No repetir implementaciones existentes y no modificar runtime.

**Salida:** auditoría de brechas aprobada antes de abrir tareas de implementación.

### H1 — Instalación y ciclo de vida de Xray-core desde el administrador

- Detectar instalación, binario, versión, arquitectura, hash y unidad de servicio.
- Instalar únicamente una versión fijada y autorizada, con verificación de integridad antes de instalar.
- Crear/administrar unidad systemd, usuario/grupo y permisos conforme a normativa y diseño seguro.
- Consultar estado, versión, proceso y registros.
- Incorporar inicio, detención y reinicio con confirmación cuando corresponda.
- No habilitar inicio automático como efecto lateral.
- Validar instalación y servicio en un entorno controlado antes de cualquier servidor objetivo.

**Salida:** instalación reproducible y gestión del servicio desde los menús del administrador.

### H2 — Dominio, DNS y certificados TLS

- Administrar el dominio y comprobar resolución DNS.
- Integrar el proveedor DNS acordado mediante credenciales protegidas y permisos mínimos.
- Gestionar ACME DNS-01, emisión, renovación, revocación/errores y vencimiento.
- Validar SAN, cadena, vigencia y correspondencia criptográfica certificado/clave.
- Guardar el certificado en el almacén central y asociarlo mediante `certificate_id` y leases; no usar rutas libres por conexión.
- Evitar que secretos DNS, claves privadas o tokens aparezcan en argumentos, logs o informes.
- La renovación debe actualizar el recurso central y dejar una aplicación/reinicio controlados y auditables.

**Salida:** certificado válido, asociado al dominio y consumible por el flujo TLS centralizado.

### H3 — Conexión VLESS + WebSocket + TLS

- Auditar específicamente la modalidad VLESS-WS-TLS en catálogo, asistente, modelo, store, adaptador Xray, validación, backup y menú.
- Completar solo las brechas demostradas.
- Gestionar UUID único, inbound/tag, puerto, path WebSocket, Host, SNI y referencia al certificado.
- Verificar coherencia de parámetros entre servidor y cliente.
- Generar previsualización y persistir como borrador bajo confirmación.
- Validar con la versión fijada de Xray; rechazar rutas/certificados no autorizados.
- No abrir puertos ni cambiar firewall sin autorización específica.

**Salida:** conexión VLESS-WS-TLS guardada y validada, todavía no aplicada.

### H4 — Perfil, revisión y configuración efectiva

- Integrar la conexión con el perfil y su revisión exacta `profile_id + revision`.
- Resolver el mapa `inbound_tag → connection_id` y certificados centrales.
- Validar perfil, revisión, leases, binario y configuración final.
- Distinguir claramente Borrador, Validada, Publicada pendiente, Aplicada y Anterior.
- Mantener la identidad y hashes a lo largo de preflight, staging, journal y publicación.

**Salida:** perfil exacto listo para publicación, con evidencia verificable.

### H5 — Orquestación transaccional y confirmaciones

Reutilizar R-01–R-04; no duplicar preflight, staging, snapshot, journal, publisher ni rollback.

Reglas aprobadas por el propietario:

- Si el servicio está `active`, solicitar confirmación explícita antes de reiniciarlo para aplicar una nueva revisión.
- Si el propietario rechaza el reinicio, no reiniciar: la nueva configuración queda `published_pending_apply`; el proceso activo conserva la configuración que ya tenía cargada y la nueva revisión no se marca como aplicada.
- Si el servicio está `inactive`, publicar sin arrancarlo. Registrar `published_pending_start`. La activación posterior se realiza desde la opción manual de inicio del administrador, con confirmación, preflight y verificación.
- Cada operación tiene un identificador único de generación (`generation_id`) aprobado, ligado al journal y a la evidencia del resultado. No aceptar respuestas o estados antiguos como prueba de la generación actual.
- Si el estado es `unknown`, detenerse de forma segura.
- Si está `failed`, no intentar arrancarlo automáticamente ni afirmar recuperación sin evidencia; el resultado debe conservar el fallo o quedar `recovery_required`.

Pendiente de decisión de diseño: extensión versionada del journal existente frente a un registro separado. Recomendación técnica: extender el journal con esquema/versionado y compatibilidad de lectura/recuperación para R-03/R-04, después de revisión específica.

**Salida:** orquestación coherente, con confirmación, estados separados, recuperación idempotente y pruebas de fallos.

### H6 — Adaptador real de systemd y primera aplicación live

- Mantener el adaptador simulado como banco de pruebas; no confundirlo con evidencia de systemd real.
- Implementar un adaptador real acotado a `xray.service`, sin comandos arbitrarios ni interpolación de shell.
- Consultar estado antes y después; registrar resultado, timeout, generación y revisión.
- Verificar servicio, proceso, binario, configuración esperada, puertos y registros disponibles.
- Coordinar la aplicación con snapshot/journal/publicación/rollback.
- Si el reinicio falla, restaurar configuración y reconciliar el estado anterior. Si no se puede demostrar recuperación, marcar `recovery_required`.
- La primera ejecución real se realizará solo después de una autorización explícita y específica que identifique servidor, alcance, operaciones permitidas y ventana de prueba.
- El estado previo `inactive` nunca se arranca por efecto de publicar; el inicio manual es otra operación explícita.

**Salida:** primera aplicación real gestionada por el administrador, con evidencia y rollback probado.

### H7 — Diagnóstico, backup y recuperación

- Diagnosticar servicio, proceso, configuración efectiva, puertos, DNS y TLS desde el administrador.
- Mostrar logs con enmascaramiento de secretos.
- Respaldar configuraciones, metadatos, asociaciones y referencias a certificados según las políticas normativas.
- Excluir claves/credenciales por defecto; cualquier respaldo de secretos requiere diseño, autorización y protección adicionales.
- Restaurar y verificar integridad antes de cualquier aplicación.
- Demostrar rollback de configuración y recuperación de servicio.

**Salida:** operación y recuperación administrables, auditables y documentadas.

### H8 — Prueba externa de extremo a extremo

- Configurar el cliente externo con los parámetros exportados por el administrador.
- Comprobar DNS, TCP, handshake TLS, certificado/SNI, WebSocket/path, autenticación VLESS y tráfico bidireccional.
- Probar reconexión, estabilidad y persistencia tras reinicio controlado, solo si está autorizado.
- Correlacionar el resultado del cliente con generation_id, revisión aplicada y registros del servidor.
- Documentar fallos y repetir únicamente después de corregir su causa.

**Salida:** evidencia de conexión real y matriz de aceptación del hito.

## 5. Dependencias y orden

Orden recomendado: H0 → H1 → H2 → H3 → H4 → H5 → H6 → H7 → H8.

Algunas tareas pueden prepararse en paralelo después de H0, pero ninguna aplicación real se ejecuta antes de cerrar sus dependencias. No se salta la auditoría de brechas ni la verificación de versión/certificado/configuración.

## 6. Decisiones operativas ya aprobadas

1. Protocolo del primer servicio: VLESS + WebSocket + TLS.
2. El administrador será responsable de las operaciones del servidor; no se aceptará configuración manual externa como sustituto.
3. Reiniciar un servicio `active` para aplicar una nueva revisión requiere confirmación explícita.
4. Rechazar la confirmación conserva el proceso actual y deja la revisión nueva publicada pero pendiente de aplicación.
5. Publicar con servicio `inactive` no lo inicia; se podrá iniciar manualmente desde el administrador, con confirmación.
6. Cada operación tendrá `generation_id` único para ligar evidencia y descartar resultados obsoletos.
7. R-01–R-04 se reutilizan; no se repiten.
8. La normativa `Xray-Normativa/` es inmutable sin autorización expresa.
9. `main` no se modifica.

## 7. Límites y autorizaciones

Este plan es una prioridad de producto y una hoja de ruta, no una autorización general para ejecutar cambios live.

Hasta recibir autorización específica permanecen prohibidos: instalar/actualizar Xray o dependencias en el servidor objetivo; crear/modificar unidades systemd reales; escribir configuración runtime; emitir/renovar/instalar certificados reales; cambiar DNS, firewall, puertos o red; iniciar/reiniciar/detener Xray real; ejecutar pruebas NetMod/live; utilizar la VPS de pruebas; modificar `main` o `Xray-Normativa/`; leer `/etc/xray-manager/keys/master.key`.

Cada autorización live debe delimitar servidor, operaciones, rutas, versiones, ventana y mecanismo de reversión. La autorización para diseñar o implementar código aislado no equivale a autorización para desplegarlo.

## 8. Criterios de cierre

No cerrar H0–H8 ni declarar el hito viable sin:
- trazabilidad normativa completa;
- implementación identificada por componente;
- pruebas unitarias, integración, fallos y regresión pertinentes;
- auditoría técnica y de seguridad;
- evidencia de entorno y versión;
- matriz requisito → diseño → código → prueba → evidencia;
- documentación de límites/no ejecutado;
- aceptación formal del propietario.

**Estado al crear este plan:** H0 pendiente; H1–H8 no iniciadas como hitos de este plan. Las capacidades parciales preexistentes se deben inventariar en H0 y no se consideran inexistentes ni aceptadas por anticipado.
