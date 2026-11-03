# ETAPA 4 — CERTIFICADOS SSL/TLS Y DOMINIOS

**Proyecto:** Xray Core Manager  
**Versión del documento:** 1.1  
**Estado:** Aprobada — especificación funcional  
**Alcance:** administración de dominios y certificados SSL/TLS relacionados con los servicios del servidor.

---

## 1. Objetivo

Definir las funciones del administrador para registrar y gestionar dominios, obtener e instalar certificados, renovarlos, verificar DNS y diagnosticar problemas SSL/TLS.

Esta etapa define el comportamiento funcional. No determina todavía la implementación técnica definitiva del cliente ACME, el proveedor DNS, las rutas concretas ni la integración con cada servicio. Esos detalles se validarán antes de programar.

## 2. Menú principal aprobado

```text
╔══════════════════════════════════════════════╗
║       CERTIFICADOS SSL/TLS Y DOMINIOS       ║
╠══════════════════════════════════════════════╣
║  CERTIFICADOS                               ║
║  [1] Gestionar certificados                 ║
║  [2] Obtener certificado nuevo              ║
║  [3] Renovar certificados                   ║
║                                              ║
║  DOMINIOS                                   ║
║  [4] Gestionar dominios                     ║
║  [5] Verificar configuración DNS            ║
║                                              ║
║  CONFIGURACIÓN Y DIAGNÓSTICO                ║
║  [6] Configuración de Let's Encrypt         ║
║  [7] Diagnóstico SSL/TLS                     ║
║                                              ║
║  [0] Volver                                 ║
╚══════════════════════════════════════════════╝
```

## 3. [1] Gestionar certificados

```text
╔══════════════════════════════════════════════╗
║             GESTIONAR CERTIFICADOS          ║
╠══════════════════════════════════════════════╣
║  [1] Listar certificados instalados         ║
║  [2] Consultar información de un certificado║
║  [3] Verificar estado y validez             ║
║  [4] Consultar dominios asociados           ║
║  [5] Eliminar un certificado                ║
║  [0] Volver                                 ║
╚══════════════════════════════════════════════╝
```

- **Listar certificados instalados:** mostrar los certificados detectados y, cuando la información esté disponible, dominio o nombres cubiertos, emisor, vencimiento y estado.
- **Consultar información:** seleccionar un certificado y mostrar sus detalles.
- **Verificar estado y validez:** comprobar validez temporal y disponibilidad/integridad de los archivos necesarios.
- **Consultar dominios asociados:** mostrar los dominios cubiertos por el certificado.
- **Eliminar:** seleccionar un certificado y solicitar confirmación antes de eliminarlo.

**Regla de protección:** eliminar un certificado no elimina automáticamente el registro del dominio ni modifica la configuración de las conexiones de Xray. Antes de borrar archivos se debe identificar si el certificado está siendo utilizado por algún servicio y advertirlo al administrador.

## 4. [2] Obtener certificado nuevo

```text
╔══════════════════════════════════════════════╗
║             OBTENER CERTIFICADO             ║
╠══════════════════════════════════════════════╣
║  [1] Let's Encrypt (HTTP-01)                ║
║  [2] Let's Encrypt (DNS-01)                 ║
║  [3] Instalar certificado existente         ║
║  [0] Volver                                 ║
╚══════════════════════════════════════════════╝
```

### 4.1 Let's Encrypt (HTTP-01)

Solicitar un certificado mediante validación HTTP. El flujo debe informar que el dominio debe resolver hacia el servidor previsto y que la autoridad certificadora debe poder acceder al recurso de validación HTTP, normalmente por el puerto 80. Si las condiciones previas no se cumplen, informar del problema y no afirmar que la emisión se completó.

### 4.2 Let's Encrypt (DNS-01)

Solicitar un certificado mediante un registro TXT de validación DNS. El flujo debe indicar qué registro debe publicarse y comprobar su disponibilidad antes de continuar. La automatización mediante API de un proveedor DNS queda sujeta a una integración compatible que se definirá posteriormente.

### 4.3 Instalar certificado existente

Permitir indicar las rutas de los archivos del certificado y de la clave privada. Validar que los archivos existan, puedan leerse, sean coherentes entre sí y cubran el dominio solicitado antes de instalarlos o reemplazar una instalación existente.

### 4.4 Dominios incluidos

Permitir seleccionar uno o varios dominios para incluirlos en un mismo certificado, siempre que la autoridad y el método de validación admitan esa combinación. Mostrar el conjunto de nombres solicitado antes de emitir o instalar.

## 5. [3] Renovar certificados

```text
╔══════════════════════════════════════════════╗
║              RENOVAR CERTIFICADOS           ║
╠══════════════════════════════════════════════╣
║  [1] Renovar un certificado                 ║
║  [2] Renovar todos los certificados         ║
║  [3] Comprobar renovaciones pendientes      ║
║  [4] Configurar renovación automática       ║
║  [5] Consultar historial de renovaciones    ║
║  [0] Volver                                 ║
╚══════════════════════════════════════════════╝
```

- **Renovar uno:** seleccionar el certificado que se desea renovar.
- **Renovar todos:** intentar renovar los certificados administrados por el sistema.
- **Comprobar pendientes:** detectar certificados próximos a vencer o que requieren renovación.
- **Renovación automática:** activar, desactivar y configurar la comprobación periódica.
- **Historial:** consultar resultados anteriores, fechas y errores disponibles.

### Propiedad y administración del historial de renovaciones

- La Etapa 4 es responsable de generar y conservar el historial específico de renovaciones de certificados, incluyendo fecha, certificado afectado, resultado y errores disponibles.
- La Etapa 6 centraliza la consulta, el filtrado, la exportación y la administración de la conservación o limpieza de este historial.
- La Etapa 6 no crea un segundo historial ni duplica su almacenamiento; las operaciones de renovación siguen perteneciendo a la Etapa 4.

### Reglas de renovación

1. Una renovación fallida no debe reemplazar ni invalidar el certificado vigente.
2. Validar el certificado renovado antes de aplicarlo.
3. Informar los resultados individuales cuando se procesen varios certificados.
4. Un error no debe cerrar inesperadamente el administrador.
5. La renovación automática debe ejecutarse mediante un mecanismo del sistema operativo o del cliente ACME, sin requerir que el menú permanezca abierto.
6. La frecuencia y el mecanismo exactos se concretarán durante la implementación, respetando los requisitos del cliente ACME seleccionado.

## 6. [4] Gestionar dominios

```text
╔══════════════════════════════════════════════╗
║                GESTIONAR DOMINIOS           ║
╠══════════════════════════════════════════════╣
║  [1] Agregar un dominio                     ║
║  [2] Listar dominios registrados            ║
║  [3] Consultar información de un dominio    ║
║  [4] Modificar un dominio                   ║
║  [5] Eliminar un dominio                    ║
║  [6] Asociar dominio a un certificado       ║
║  [7] Desasociar dominio de un certificado   ║
║  [0] Volver                                 ║
╚══════════════════════════════════════════════╝
```

- **Agregar:** registrar un dominio o subdominio en el administrador.
- **Listar:** mostrar los dominios registrados, sus certificados asociados y el estado de validación conocido.
- **Consultar:** mostrar información DNS disponible, certificado asociado y vencimiento.
- **Modificar:** cambiar los datos administrativos del dominio. No modificar automáticamente las conexiones de Xray.
- **Eliminar:** retirar el dominio del registro del administrador, previa confirmación.
- **Asociar:** vincular un dominio con un certificado compatible.
- **Desasociar:** retirar la vinculación sin eliminar por ello el dominio ni el certificado.

**Distinción:** registrar un dominio en el administrador no significa que su DNS ya apunte al servidor. La comprobación DNS es independiente.

## 7. [5] Verificar configuración DNS

```text
╔══════════════════════════════════════════════╗
║             VERIFICACIÓN DNS                ║
╠══════════════════════════════════════════════╣
║  [1] Verificar resolución del dominio       ║
║  [2] Consultar registros A y AAAA            ║
║  [3] Consultar registros CNAME               ║
║  [4] Consultar registros TXT                 ║
║  [5] Comprobar propagación DNS               ║
║  [6] Verificar apuntado hacia el servidor    ║
║  [0] Volver                                 ║
╚══════════════════════════════════════════════╝
```

- **Resolución:** comprobar si el dominio puede resolverse.
- **A y AAAA:** consultar direcciones IPv4 e IPv6.
- **CNAME:** consultar alias DNS.
- **TXT:** consultar registros de texto, incluidos los usados en validaciones DNS-01.
- **Propagación:** consultar la visibilidad de los registros desde distintos servidores DNS.
- **Apuntado al servidor:** comparar las direcciones obtenidas con la dirección pública conocida del servidor.

Los resultados deben diferenciar, cuando sea posible, entre registro inexistente, error de resolución, respuestas diferentes entre resolutores y dirección que no coincide con el servidor. Una diferencia no debe etiquetarse automáticamente como error si el dominio utiliza CDN, proxy inverso, balanceador o una arquitectura DNS intencional.

## 8. [6] Configuración de Let's Encrypt

```text
╔══════════════════════════════════════════════╗
║          CONFIGURACIÓN LET'S ENCRYPT        ║
╠══════════════════════════════════════════════╣
║  [1] Configurar correo electrónico           ║
║  [2] Seleccionar método de validación        ║
║  [3] Configurar cliente ACME                 ║
║  [4] Configurar directorios y rutas          ║
║  [5] Consultar configuración actual          ║
║  [6] Restaurar configuración predeterminada ║
║  [0] Volver                                 ║
╚══════════════════════════════════════════════╝
```

- **Correo:** configurar el correo de contacto utilizado para la cuenta ACME/Let's Encrypt.
- **Método de validación:** establecer HTTP-01 o DNS-01 como método preferido. La elección podrá cambiarse al solicitar un certificado.
- **Cliente ACME:** seleccionar y configurar el cliente encargado de solicitar y renovar certificados. El cliente concreto se decidirá tras verificar compatibilidad con el sistema objetivo.
- **Directorios y rutas:** definir las ubicaciones de certificados, claves privadas y archivos de trabajo.
- **Consultar configuración:** mostrar los parámetros activos sin revelar secretos.
- **Restaurar:** recuperar valores predeterminados, previa confirmación y mostrando qué parámetros serán modificados.

## 9. [7] Diagnóstico SSL/TLS

```text
╔══════════════════════════════════════════════╗
║              DIAGNÓSTICO SSL/TLS            ║
╠══════════════════════════════════════════════╣
║  [1] Verificar certificado y clave privada  ║
║  [2] Comprobar fecha de vencimiento         ║
║  [3] Verificar coincidencia de dominio      ║
║  [4] Comprobar cadena de confianza          ║
║  [5] Probar conexión TLS                    ║
║  [6] Detectar problemas de configuración    ║
║  [7] Mostrar informe de diagnóstico        ║
║  [0] Volver                                 ║
╚══════════════════════════════════════════════╝
```

1. Comprobar que el certificado y la clave privada sean válidos y correspondan entre sí.
2. Revisar las fechas de emisión y vencimiento.
3. Comprobar que el dominio solicitado esté cubierto por los nombres del certificado (SAN).
4. Verificar la cadena de certificados y la confianza.
5. Probar una conexión TLS con el dominio y puerto indicados.
6. Detectar problemas en rutas, permisos, archivos y parámetros de configuración que puedan comprobarse.
7. Presentar un informe con pruebas realizadas, resultados, problemas y posibles acciones correctivas.

**Regla de solo diagnóstico:** estas operaciones son informativas y no modifican certificados, claves, dominios ni configuraciones automáticamente. Las reparaciones deberán realizarse mediante una operación autorizada y separada.

## 10. Reglas generales de navegación y seguridad

- Cada submenú incluye `[0] Volver` para regresar inmediatamente al nivel anterior.
- Mostrar el resultado de cada operación antes de regresar al menú correspondiente.
- Los errores no deben cerrar inesperadamente el administrador; permitir corregir entradas cuando corresponda.
- Las operaciones destructivas o que reemplacen archivos requieren confirmación explícita.
- Antes de reemplazar un certificado, conservar el certificado vigente hasta validar el nuevo.
- Proteger las claves privadas: no mostrarlas en pantalla ni incluirlas en informes o exportaciones ordinarias.
- No asumir que todos los dominios apuntan directamente a la IP del VPS; contemplar CDN, proxy inverso y DNS externo.
- No modificar automáticamente conexiones Xray al registrar, editar o eliminar dominios o certificados.
- Mostrar claramente qué operaciones se completaron, cuáles fallaron y cuáles quedaron pendientes.

## 11. Aspectos pendientes para implementación

Los siguientes detalles no cambian la estructura funcional aprobada y deberán definirse antes de programar:

- Cliente ACME concreto y método de instalación/actualización.
- Compatibilidad del sistema objetivo con HTTP-01 y DNS-01.
- Proveedores DNS y posibles integraciones API para DNS-01.
- Rutas finales, permisos y estrategia de protección/respaldos de claves privadas.
- Mecanismo del sistema operativo para renovación automática y despliegue del certificado renovado.
- Cómo detectar de forma fiable los servicios y conexiones que utilizan un certificado.
- Frecuencia, fuentes y límites de las pruebas de propagación DNS.

Estos puntos quedan como decisiones técnicas pendientes; no deben interpretarse como funcionalidades ya implementadas.

---

**Fin de la especificación funcional de la etapa 4.**
