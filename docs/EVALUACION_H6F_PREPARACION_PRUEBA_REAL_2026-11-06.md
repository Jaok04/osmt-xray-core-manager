# H6-F — evaluación de preparación para primera prueba real

**Fecha:** 2026-11-06
**Estado:** EVALUACIÓN READ-ONLY COMPLETADA — NO AUTORIZA OPERACIONES LIVE
**Objetivo:** preparar una prueba de aceptación VLESS-WS-TLS en una VPS limpia independiente.

## 1. Contraste con la normativa aprobada

- Etapa 1 incluye explícitamente la opción de menú «Instalar Xray-core»; el menú actual la implementa, junto con «Preparar servicio».
- Etapa 2 define VLESS-WS-TLS como modalidad válida.
- Etapa 4 deja pendiente la selección/validación formal del cliente ACME concreto y del mecanismo de renovación. La implementación actual utiliza Certbot, pero la dependencia no se instala automáticamente.
- Etapa 5 exige revisión exacta validada y aplicación controlada; guardar o componer un perfil no equivale a activarlo.
- Etapa 6 mantiene la gestión del servicio en modules/xray_service.sh; no debe crearse un segundo controlador.

No se modificó Xray-Normativa/ ni la copia maestra.

## 2. Hallazgos del código actual

### 2.1 Instalador

**Estado actualizado tras la implementación Manager-only (2026-11-06):** install.sh --install despliega únicamente Xray Core Manager. No descarga Xray-core, no crea la cuenta xray, no prepara /etc/xray ni modifica systemd. La instalación integral anterior se conserva mediante install.sh --install --with-xray.

El menú ya dispone de:
- Administración de Xray: instalar, actualizar, consultar, reinstalar, reparar.
- Preparar servicio: verifica integridad y crea/verifica la identidad y unidad systemd; no inicia ni habilita el servicio.

El flujo Manager → instalar Xray desde menú → preparar servicio desde menú queda habilitado. El estado inicial del Manager registra xray_installed=false y service_configured=false. La prueba del cambio se hizo en prefijos temporales; no se instaló nada en el host.

### 2.2 Certificados y ACME

- El flujo de certificados utiliza Certbot.
- Certbot no forma parte de REQUIRED_PACKAGES ni REQUIRED_COMMANDS del instalador.
- certificate_acme.py rechaza la solicitud si Certbot no está instalado; no instala dependencias automáticamente.
- HTTP-01 utiliza Certbot standalone en TCP/80 y comprueba previamente la resolución DNS frente a la IP pública prevista.
- DNS-01 está implementado como flujo manual; para la primera prueba conviene HTTP-01 por ser más directo.
- La emisión y la importación al almacén central son operaciones separadas. El import valida SAN, vigencia y correspondencia certificado/clave.

Bloqueo: seleccionar formalmente Certbot como cliente ACME y autorizar su instalación en la VPS de pruebas antes de ejecutar la emisión real.

### 2.3 Creación y exportación VLESS-WS-TLS

- El asistente VLESS-WS-TLS permite crear un borrador asociado a un certificate_id central.
- El compositor puede añadir la conexión a una revisión nueva del perfil.
- La validación estática/nativa existe.
- El exportador de clientes usa actualmente hellen.tvrc.me como dirección pública predeterminada y puerto 443; XRAY_MANAGER_VLESS_PUBLIC_ADDRESS permite sobreescribirlo, pero no hay una captura persistente obligatoria en el menú.

Para el dominio previsto internet.tvrc.me, el endpoint debe quedar configurado explícitamente y mostrarse en la previsualización antes de exportar URI. No se debe inferir el SNI del endpoint: el host WebSocket y el serverName/SNI son parámetros separados.

### 2.4 Aplicación runtime

- El puente del menú de perfiles sigue fixture-only.
- R-05 usa service_adapter fixture por defecto.
- H6-E valida identidad de proceso e invocación, pero la captura combinada sólo se ha probado con dobles/fixtures.
- No existe backend mutador systemd conectado a R-05 ni selector live en CLI/menú.
- El controlador único de servicio es modules/xray_service.sh y debe seguir siendo la autoridad de start/stop/restart/enable/disable.

Éste es el bloqueo técnico principal: todavía no hay un camino autorizado que publique la generación y active/verifique el servicio real dentro de R-05.

## 3. Condiciones para la primera prueba

VPS de aceptación separada del VPS de desarrollo:
- Ubuntu 24.04 LTS limpio, arquitectura compatible.
- Acceso root y consola/proveedor para recuperación.
- Dominio internet.tvrc.me con A/AAAA apuntando a la IP pública de esa VPS.
- TCP/80 accesible desde Internet para HTTP-01.
- TCP/443 accesible desde Internet para VLESS-WS-TLS.
- Certbot instalado tras autorización.
- Cliente externo v2rayNG/v2rayN y una segunda red para probar conectividad.
- No usar el VPS de desarrollo como servidor de aceptación.

## 4. Secuencia propuesta

1. Instalar únicamente Xray Manager con el flujo predeterminado ya implementado.
2. Desde el menú, instalar Xray-core; verificar manifiesto/hash/binario/geodata.
3. Desde el menú, preparar xray.service; dejarlo detenido y deshabilitado.
4. Verificar DNS de internet.tvrc.me y disponibilidad del puerto 80.
5. Solicitar certificado Let's Encrypt mediante Certbot HTTP-01 e importarlo al almacén central.
6. Crear conexión VLESS-WS-TLS desde el asistente.
7. Componer una revisión de perfil y validarla con el binario Xray instalado.
8. Publicar la generación mediante el backend live R-05 autorizado.
9. Iniciar Xray mediante modules/xray_service.sh y atestar MainPID, InvocationID, starttime y hash del ejecutable.
10. Exportar el URI con endpoint internet.tvrc.me:443, host WebSocket y SNI explícitos.
11. Conectar un cliente externo y verificar tráfico real.
12. Auditar logs, configuración efectiva, permisos, rollback y resultado WAN.

No se abrirán puertos ni se cambiarán reglas de firewall automáticamente sin autorización. Tampoco se modificarán registros DNS automáticamente.

## 5. Autorizaciones y decisiones necesarias antes de ejecutar

1. El flujo Manager-only por defecto y la opción integral explícita ya están implementados y probados en prefijos temporales; no queda una decisión de diseño del instalador pendiente.
2. Confirmar formalmente Certbot como cliente ACME de la primera prueba y autorizar su instalación en la VPS de aceptación.
3. Designar la VPS de aceptación y autorizar operaciones concretas: instalación de Xray, preparación de systemd, emisión/importación del certificado, publicación de config y start de xray.service.
4. Autorizar explícitamente la exposición de TCP/80 y TCP/443 en el firewall del proveedor y en el host, si corresponde.
5. Confirmar el endpoint público internet.tvrc.me:443 y sus valores separados de WebSocket Host y TLS SNI.
6. Definir y autorizar por separado el backend mutador runtime real; H6-E sólo aporta observación/atestación y R-05 sigue fixture-only.

La autorización de este documento no se presume por haber autorizado H6-E. Hasta recibir las autorizaciones anteriores no se ejecutarán acciones live ni se habilitará un selector de backend real.

## 6. Dictamen

La base de configuración VLESS-WS-TLS, certificado central, validación, exportación y controlador de servicio existe. El instalador Manager-only por defecto ya está implementado y verificado en prefijos aislados; la instalación integral anterior queda como opción explícita. La prueba real sigue bloqueada por el backend runtime live, la selección formal de Certbot y la configuración explícita del endpoint público.

H6-F: EVALUACIÓN READ-ONLY COMPLETADA Y BLOQUEO DE INSTALADOR RESUELTO. NO LISTO PARA DESPLIEGUE END-TO-END. No se ejecutó systemctl real, Xray real, Certbot, cambios DNS/firewall ni conexión WAN.
