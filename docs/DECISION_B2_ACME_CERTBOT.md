# Decisión técnica B2 — cliente ACME Certbot

**Fecha:** 2026-11-05
**Estado:** APROBADA por el propietario
**Ámbito:** primera implementación ACME de Etapa 4; no modifica la normativa funcional.

## 1. Decisión

Se adopta **Certbot** como cliente ACME inicial con dos modalidades:

- **HTTP-01:** Certbot standalone, usando TCP/80.
- **DNS-01:** Certbot manual, publicación TXT por el operador y verificación de visibilidad antes de continuar.
- La automatización mediante API de Cloudflare u otros proveedores DNS queda aplazada a un bloque posterior.

## 2. Alcance autorizado de implementación

El propietario autorizó B2-A a B2-G en modo fixture-only. Esto permite código, pruebas aisladas, auditoría y documentación. No autoriza:

- instalar o actualizar Certbot, dig ni dependencias;
- solicitar certificados a Let's Encrypt u otra CA;
- modificar DNS, TXT, firewall, puertos o servicios;
- detener servicios para liberar TCP/80;
- importar certificados reales en el almacén persistente de producción;
- modificar Xray, systemd, runtime o la VPS de pruebas;
- publicar cambios en GitHub.

## 3. Contratos

- El modelo de solicitud registra método, cliente, modalidad, dominios, email, nombre de lineage, estado y timestamps; no almacena claves privadas ni tokens ACME.
- Los estados contemplados son requested, challenge_pending, issued, failed e imported.
- La emisión y la importación son operaciones separadas.
- HTTP-01 exige confirmar IP pública prevista, resolución A/AAAA compatible y disponibilidad local de TCP/80. La accesibilidad desde la CA solo se confirma cuando Certbot completa el desafío.
- DNS-01 muestra el nombre _acme-challenge y el valor TXT; requiere visibilidad del valor exacto en los resolutores configurados. La limpieza del TXT es manual y nunca borra otros valores.
- Wildcard solo se admite con DNS-01.
- La importación lee los enlaces del directorio live únicamente si su destino real permanece dentro de archive; copia los bytes a staging root-only y luego reutiliza certificate_store.py.
- El certificado se valida contra los dominios SAN solicitados, su vigencia y la correspondencia criptográfica de la clave privada.
- El certificate_id central se conserva como referencia para el Resolver TLS. La importación no modifica conexiones Xray.

## 4. Decisiones expresamente aplazadas

- Plugins DNS API (Cloudflare u otros).
- Renovación automática, hooks de despliegue y rotación.
- Gestión completa de dominios, DNS A/AAAA/CNAME/TXT y diagnóstico SSL/TLS.
- Instalación/actualización del cliente ACME.
- Política de backup de lineages y limpieza/retención.
- Integración de la UI para instalar certificados externos no emitidos por Certbot.

## 5. Restricciones permanentes

La clave maestra existente se utiliza únicamente a través del Certificate Store; nunca se lee manualmente, regenera ni modifica. Las claves privadas no se imprimen, registran ni incluyen en argumentos. Los certificados vigentes no se reemplazan ante fallos. No se modifica Xray-Normativa/.

## Addendum — instalación guiada desde el menú (2026-11-07)

El propietario solicitó que el Administrador compruebe Certbot al iniciar una solicitud y, si falta, pregunte si desea instalarlo. Se autoriza la implementación de esa experiencia en código y fixtures. El flujo instala exclusivamente el paquete `certbot` desde APT de Ubuntu tras confirmación explícita, usa el lock de ciclo de vida, verifica `certbot --version` y solo entonces permite continuar con el flujo ACME. Rechazar, fallar APT o fallar la verificación bloquea la solicitud. No se incluyen plugins DNS API ni renovación automática. Esta decisión no autoriza ejecutar APT, instalar Certbot, solicitar certificados reales, modificar red/firewall/puertos/servicios ni desplegar en VPS Pruebas; esas operaciones requieren consentimiento en el propio menú y autorización específica del entorno.


## Addendum — política de renovación y recarga Xray (2026-11-07)

Se inicia el diseño de renovación automática con `certbot.timer` y aplicación controlada al runtime. La política objetivo es permitir la renovación automática, pero no iniciar Xray si estaba detenido y no recargarlo si la validación del certificado/configuración falla. El deploy hook no ejecutará `systemctl` directamente: delegará en el controlador único `modules/xray_service.sh` mediante la integración transaccional R-05/H6.

La inspección del código actual encontró bloqueos que deben resolverse antes de implementar un hook operativo: el almacén `certificate_store.py` y el resolutor `certificate_resolver.py` solo admiten revisión 1; la importación ACME crea un `certificate_id` nuevo y no rota uno existente; el backend live sigue desconectado de R-05 y `restore()` live falla cerrado. Por ello, no se instala ni habilita el timer/hook todavía.

El diseño detallado está en `docs/DISENO_RENOVACION_CERTBOT_XRAY_2026-11-07.md`. Próximo bloque: schema versionado de certificados compatible con catálogo v1, migración explícita, rotación inmutable y pruebas fixture. Esta decisión de diseño no autoriza APT, Certbot, ACME, systemd, runtime, VPS Pruebas ni publicación.
