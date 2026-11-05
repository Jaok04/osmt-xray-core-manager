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
