# Plan técnico mínimo — MVP de despliegue VLESS + WebSocket + TLS

**Fecha:** 2026-11-04
**Estado:** PLAN APROBADO COMO PRIORIDAD DE IMPLEMENTACIÓN; no autoriza operaciones live.
**Rama:** `design/user-identity-association-v1`
**Objetivo:** demostrar el recorrido mínimo completo para instalar/preparar Xray-Core, emitir y registrar un certificado TLS, crear un usuario VLESS, generar la configuración y ejecutar/verificar el servidor desde Xray-Core Manager.

## 1. Cambio de alcance

Este documento reduce y prioriza el plan H0–H8 anterior. No elimina las obligaciones normativas ni los trabajos futuros del administrador; establece que no se desarrollarán antes de demostrar el primer despliegue funcional aquellas capacidades avanzadas que no sean imprescindibles para ese resultado.

El criterio rector es un recorrido vertical pequeño y comprobable: **instalar → preparar servicio → obtener certificado → crear usuario/conexión → generar/validar configuración → aplicar/iniciar → verificar**.

No se acepta como éxito configurar Xray manualmente desde shell y después afirmar que el Manager lo administra. Las operaciones de servidor del recorrido deben ejecutarse desde las opciones del administrador. La configuración del cliente externo (NetMod u otro) se puede realizar desde el cliente.

## 2. Alcance incluido

### B0 — Inspección focal y reutilización

Antes de programar cada bloque:
- Revisar los módulos concretos ya identificados por H0 y la sección normativa correspondiente.
- Reutilizar el instalador Xray existente, `modules/xray_service.sh`, asistente/modelo/adaptador VLESS, almacén/resolutor de certificados y persistencia existente.
- Identificar con precisión qué función ya satisface cada requisito y qué falta conectar.
- No reescribir ni repetir R-01–R-04.
- Preparar pruebas aisladas antes de cualquier operación real.

**Salida:** lista corta de archivos/funciones existentes, brecha puntual, cambio mínimo y prueba de aceptación.

### B1 — Instalar Xray-Core y preparar el servicio

Desde el administrador:
1. Detectar arquitectura, binario, versión fijada e integridad.
2. Si la versión fijada ya está instalada y es válida, reutilizarla; no reinstalar ni actualizar por rutina.
3. Si falta, ofrecer instalación desde el administrador después de verificar artefactos e integridad.
4. Crear/verificar usuario y grupo de sistema `xray`, directorios y permisos mínimos.
5. Crear/verificar la unidad `xray.service` con rutas explícitas y ejecución no privilegiada.
6. Mostrar versión y estado del servicio; permitir iniciar/detener desde el menú con confirmación apropiada.

**No incluido en B1:** actualizar Xray a otra versión, habilitar arranque automático sin decisión explícita, instalar dependencias no aprobadas o ejecutar cambios en el servidor objetivo sin autorización live específica.

**Aceptación B1:** el administrador puede detectar Xray y preparar su identidad/unidad de servicio de forma reproducible; las pruebas aisladas verifican idempotencia, permisos y unidad. La instalación/preparación live se demuestra solo con autorización específica.

### B2 — Emisión y gestión mínima del certificado

Propuesta inicial de menor complejidad: **Let's Encrypt mediante Certbot y validación ACME HTTP-01 en modo standalone**, condicionada a que:
- el dominio/subdominio elegido tenga DNS A/AAAA correcto hacia el servidor;
- el puerto TCP 80 sea accesible desde Internet durante el desafío;
- no exista un servicio que impida utilizar temporalmente el modo standalone;
- la disponibilidad del puerto 443 para el servicio TLS esté resuelta.

Desde el administrador:
1. Solicitar dominio y comprobar su resolución DNS.
2. Mostrar los prerrequisitos y bloquear la emisión si no se cumplen.
3. Ejecutar la solicitud ACME a través del cliente elegido, sin exponer secretos en argumentos o logs.
4. Validar SAN/dominio, vigencia, cadena y correspondencia certificado/clave.
5. Importar/registrar el recurso en el almacén central existente y obtener su `certificate_id`.
6. Preparar el acceso seguro de Xray mediante el resolutor/lease existente.
7. Mostrar dominio, vencimiento, estado y resultado de validación.

La incorporación de Certbot y cualquier paquete requerido queda sujeta a autorización de instalación/actualización. No se instalarán dependencias durante la fase de diseño o pruebas aisladas.

**Fuera del primer MVP:** integración con APIs de proveedores DNS, DNS-01, múltiples clientes ACME, gestión de múltiples dominios, revocación/rotación avanzada y automatización completa de renovación. La renovación automática se planificará después de comprobar emisión, almacenamiento y consumo seguro del primer certificado.

**Aceptación B2:** el Manager emite o importa el certificado, lo valida, lo registra centralmente y puede preparar un lease legible por la identidad real de Xray sin rutas libres ni permisos excesivos.

### B3 — Crear un usuario y una conexión VLESS-WS-TLS

Desde el administrador:
1. Crear/seleccionar un usuario mediante el flujo de Usuarios V2 existente.
2. Generar UUID único usando los controles de unicidad ya implementados.
3. Crear la conexión VLESS + WebSocket + TLS.
4. Configurar dominio, puerto, ruta WebSocket, certificado y, si se necesita, Host WebSocket.
5. Mantener separadas las propiedades del servidor y del cliente: el certificado TLS del inbound no sustituye el SNI/serverName del cliente.
6. Generar configuración Xray y validar con el binario fijado mediante `xray run -test`.
7. Persistir la conexión y su asociación al usuario usando los mecanismos existentes.
8. Generar los parámetros/perfil de cliente necesarios para configurar NetMod u otro cliente externo.

**No incluido:** panel de exportación para todos los protocolos, gestión masiva de usuarios, múltiples inbounds o modalidades adicionales.

**Aceptación B3:** el Manager crea el usuario y la conexión, produce una configuración válida y entrega datos de cliente coherentes con el dominio, puerto, UUID, transporte, path, Host y SNI que correspondan.

### B4 — Aplicar configuración y ejecutar Xray

Implementar únicamente el puente mínimo y seguro entre la configuración validada y el servicio administrado:
1. Comprobar precondiciones y estado del servicio.
2. Generar archivo temporal en el mismo filesystem y validarlo con el binario Xray fijado.
3. Conservar copia recuperable de la configuración anterior.
4. Publicar mediante reemplazo atómico y permisos estrictos.
5. Si el servicio estaba `active`, pedir confirmación antes del reinicio para aplicar la nueva configuración.
6. Si estaba `inactive`, no arrancarlo como efecto lateral de publicar; el inicio será una acción explícita desde el administrador.
7. Si está `failed` o su estado es desconocido, detener la operación y no intentar iniciar/reiniciar automáticamente.
8. Comprobar el resultado del servicio. Si la aplicación falla, restaurar la configuración anterior cuando sea seguro y verificarla; si no se puede demostrar recuperación, detenerse y requerir intervención.
9. Mostrar el estado real y distinguir configuración validada, publicada y aplicada.

R-01–R-04 siguen siendo reutilizables como base, pero sus implementaciones actuales están confinadas a fixtures. No se presentarán como adaptador live ya existente. El puente real debe ser acotado, revisado y probado en aislamiento antes de cualquier aplicación autorizada. No se ampliará el journal ni se implementará una orquestación general salvo que la auditoría normativa/técnica demuestre que un elemento concreto es imprescindible para este recorrido seguro.

**Aceptación B4:** el Manager publica una configuración válida, solicita la confirmación necesaria, ejecuta la acción permitida sobre `xray.service`, verifica el resultado y conserva una ruta de recuperación comprobable.

### B5 — Verificación del primer servicio

Desde el administrador y con una prueba externa:
- versión y estado de Xray;
- configuración validada y aplicada;
- proceso y puerto de escucha esperado;
- certificado presentado, dominio/SNI y handshake TLS;
- establecimiento WebSocket;
- autenticación VLESS del usuario creado;
- tráfico bidireccional desde cliente externo.

La comprobación `xray run -test` por sí sola no es prueba end-to-end. La apertura de firewall, cambios de red/puertos y pruebas desde Internet requieren autorización específica.

**Aceptación B5:** una conexión externa VLESS-WS-TLS transmite datos en ambos sentidos y la evidencia se correlaciona con el usuario y la configuración creados desde el Manager.

## 3. Orden mínimo de ejecución

1. B0 — inspección focal y matriz de reutilización.
2. B1 — instalación/preparación Xray y servicio.
3. B2 — emisión, validación y registro del certificado.
4. B3 — usuario, conexión y configuración cliente/servidor.
5. B4 — publicación, inicio/aplicación y recuperación mínima.
6. B5 — prueba externa de extremo a extremo.

Cada bloque se implementará primero con fixtures/mocks y pruebas no destructivas. La prueba live se realizará por separado, con autorización explícita y acotada.

## 4. Fuera de alcance hasta demostrar el MVP

Se aplazan, sin eliminarlos del roadmap general:
- implementación general de R-05 como orquestador avanzado;
- ampliación del journal con campos/generaciones adicionales, salvo necesidad técnica demostrada;
- reconciliación avanzada de timeouts y resultados ambiguos;
- múltiples proveedores DNS y ACME DNS-01;
- renovación/rotación/revocación avanzada de certificados;
- todos los protocolos y modalidades adicionales;
- múltiples instancias, perfiles complejos y administración masiva;
- hot reload, diagnóstico integral y observabilidad avanzada;
- backup/restore general de todas las etapas;
- automatización general de recuperación y operación multi-servidor.

Las reglas de seguridad imprescindibles no se aplazan: validación antes de publicar, copia recuperable, reemplazo atómico, permisos mínimos, confirmación antes de reiniciar un servicio activo y comportamiento fail-closed ante estado `failed`/desconocido.

## 5. Decisiones aún necesarias, sin bloquear el diseño

Antes de la primera emisión ACME live se necesitarán el dominio/subdominio, el servidor objetivo, confirmación de DNS y disponibilidad del puerto 80. El método HTTP-01 standalone es una propuesta para el primer MVP, no una afirmación de que el entorno ya cumple sus prerrequisitos.

No se asumirá proveedor DNS, dominio, dirección IP, puerto, path, Host ni credenciales. Se pedirán cuando el bloque correspondiente lo requiera.

## 6. Puertas de autorización

Este plan autoriza preparar e implementar el código mínimo en la rama autorizada, con pruebas aisladas, revisión normativa, auditoría y documentación. **No autoriza operaciones live.**

Requieren autorización live separada:
- instalar/actualizar Xray o dependencias en el host;
- crear usuario/grupo o modificar archivos del sistema y unidad systemd;
- solicitar/instalar certificados reales;
- escribir configuración runtime;
- iniciar, detener o reiniciar Xray;
- cambiar DNS, firewall, puertos o red;
- ejecutar pruebas externas desde NetMod u otro cliente.

Cada autorización live debe identificar el servidor, operación exacta, alcance, ventana y reversión. La VPS `Vps de Pruebas` no se utilizará sin autorización expresa. No leer `/etc/xray-manager/keys/master.key`.

## 7. Gobierno y aceptación

- Contrastar cada bloque con la documentación normativa aprobada; no modificar `Xray-Normativa/` sin consentimiento.
- Mantener intacta la rama `main`; trabajar solo en `design/user-identity-association-v1`.
- Reutilizar R-01–R-04 sin repetir pruebas/implementaciones salvo necesidad justificada.
- Registrar por separado IMPLEMENTADO, VERIFICADO, AUDITADO, PUBLICADO, SINCRONIZADO y ACEPTADO.
- Cada bloque requiere pruebas, auditoría, documentación técnica y aceptación del propietario antes de cerrarse.
- La aceptación de este plan no equivale a aceptación de R-01–R-04, cierre de etapas ni autorización live.

## 8. Estado al aprobar el plan

- H0: auditoría de brechas completada y formalmente aceptada por el propietario.
- MVP B0–B5: plan aprobado; implementación aún no iniciada.
- R-01–R-04: conservar su estado publicado/sincronizado; aceptación formal individual pendiente según punto de control del proyecto.
- R-05: diseño avanzado en pausa; no implementar por ahora.
- R-06/live: no autorizada.
- Etapas 2, 3 y 5: abiertas.


## Addendum de decisión posterior — B2 ACME Certbot (2026-11-05)

Este addendum registra una decisión complementaria posterior; no reescribe la versión histórica del plan ni la documentación normativa. El propietario aprobó Certbot como cliente ACME inicial con HTTP-01 standalone y DNS-01 manual TXT. La automatización DNS mediante API (Cloudflare u otros proveedores) queda aplazada. B2 fue implementada en fixtures, auditada y aceptada formalmente con las limitaciones de `docs/AUDITORIA_B2_ACME_CERTIFICADOS_2026-11-05.md`.

La aceptación de B2 no acredita emisión ACME real ni satisface por sí sola todos los requisitos de Etapa 4; tampoco autoriza instalar Certbot, ejecutar desafíos reales, cambiar DNS/puerto 80/firewall/servicios o modificar runtime. Etapa 4 permanece ABIERTA. El trabajo siguiente del MVP es B3, precedido por contraste documental y autorización específica de implementación.
