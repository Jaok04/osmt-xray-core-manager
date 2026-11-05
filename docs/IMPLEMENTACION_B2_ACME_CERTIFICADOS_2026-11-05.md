# Implementación B2 — ACME Certbot y certificados TLS

**Fecha:** 2026-11-05
**Estado:** IMPLEMENTADO EN FIXTURES, VERIFICADO, AUDITADO y ACEPTADO FORMALMENTE el 2026-11-05 con las limitaciones de la auditoría; emisión ACME real NO EJECUTADA.
**Rama:** design/user-identity-association-v1

## 1. Alcance

Se implementó el primer flujo técnico de obtención/importación ACME acordado: Certbot HTTP-01 standalone y DNS-01 manual. Se reutilizan el almacén central certificate_store.py, la criptografía existente y el Resolver TLS. No se crea un segundo almacén de certificados.

## 2. Archivos

| Archivo | Responsabilidad |
|---|---|
| scripts/certificate_acme.py | Validación de dominios, construcción de comandos Certbot, preflight HTTP-01, hooks DNS-01, journal de solicitudes e importación de lineages |
| modules/certificates.sh | Submenú ACME, listado del almacén, confirmación explícita y flujo de importación |
| bin/xray-manager | Carga del módulo de certificados |
| modules/main_menu.sh | Enrutamiento de la opción principal [3] al submenú |
| tests/test_certificate_acme.py | Pruebas Python focales de B2 |
| tests/certificates_menu.sh | Prueba del submenú/captura de dominios |
| tests/stage1_menu.sh | Actualización de fixture de navegación para cargar y simular el nuevo submenú |

## 3. Flujo HTTP-01

1. Validar formato y unicidad de dominios; rechazar IP literal y wildcard.
2. Exigir IP pública prevista indicada por el operador.
3. Consultar A y AAAA en los resolutores configurados y exigir coincidencia con una IP prevista.
4. Comprobar que TCP/80 puede enlazarse localmente.
5. Si falla, bloquear sin detener servicios ni modificar firewall.
6. Construir comando Certbot certonly --standalone --preferred-challenges http --http-01-port 80.
7. La ejecución real requiere confirmación de UI y el argumento explícito --confirm-acme.

La comprobación local no demuestra accesibilidad desde Internet ni desde la CA. El resultado final del desafío Certbot es la comprobación autoritativa de ese requisito. La implementación inicial exige coincidencia directa con una IP prevista; topologías CDN/proxy requieren evaluación adicional y no se deben declarar verificadas por esta comprobación.

## 4. Flujo DNS-01 manual

1. Certbot usa --manual --preferred-challenges dns y hooks temporales privados.
2. El hook muestra el registro TXT _acme-challenge.dominio y el valor exacto.
3. El operador publica el TXT manualmente.
4. Tras confirmación, el hook consulta el valor exacto en 1.1.1.1, 8.8.8.8 y 9.9.9.9 usando dig.
5. Si falta en cualquiera, el hook falla cerrado y Certbot no completa la validación.
6. El hook de limpieza solo informa qué valor retirar. No ejecuta cambios DNS ni elimina registros. Certbot conserva su confirmación interactiva de registro de IP pública en DNS-01.

Wildcard se admite únicamente con DNS-01. No se instala dig; si no está disponible, la comprobación falla cerrada.

## 5. Journal y estados

Las solicitudes se registran bajo:

    /var/lib/xray-manager/certificates/acme/requests/

El directorio es root:root 0700 y cada JSON root:root 0600, con escritura atómica/fsync. El registro contiene dominios, método, email, cliente, lineage, estado, timestamps y código de salida; nunca contiene claves privadas ni material secreto del challenge.

Transiciones implementadas: requested → challenge_pending → issued → validated → imported; los errores de preflight/Certbot quedan como failed. Reintentos generan un ID de solicitud distinto. La importación exige que el registro corresponda al método, dominios, email y lineage suministrados.

## 6. Importación Certbot → Certificate Store

Certbot puede mantener enlaces simbólicos en live/. El adaptador:

- resuelve el destino real de fullchain.pem y privkey.pem;
- exige que ambos permanezcan dentro de config-dir/archive;
- rechaza destinos inseguros, archivos no regulares, hardlinks y permisos abiertos de clave;
- copia a staging temporal root-only como archivos regulares;
- comprueba SAN solicitados y correspondencia criptográfica;
- delega la importación al almacén central existente, que valida vigencia, par de claves, deduplicación y cifra la clave con el mecanismo existente;
- elimina el staging al salir.

No sobrescribe un certificado existente. Una emisión o importación fallida no invalida el certificado vigente.

## 7. Integración Resolver TLS

La prueba de integración importa un certificado sintético desde un lineage fixture y llama a certificate_resolver.prepare para una conexión VLESS-WS-TLS fixture. Comprueba creación del lease temporal y limpieza. No consulta systemd real, no lee la clave maestra real y no activa Xray.

## 8. Interfaz

La opción principal [3] ya abre un submenú con:
- obtener certificado ACME;
- listar certificados del almacén central;
- importar un lineage Certbot.

La UI muestra un plan antes de solicitar y pide confirmación explícita antes de ejecutar Certbot. Las demás funciones normativas de Etapa 4 (gestión de dominios, renovación, diagnóstico completo y configuración general ACME) siguen pendientes.

## 9. Comandos de inspección sin operación live

Plan HTTP-01 (no ejecuta Certbot):

    python3 scripts/certificate_acme.py plan --method http-01 --domain example.com --email admin@example.com

Plan DNS-01 (no ejecuta Certbot):

    python3 scripts/certificate_acme.py plan --method dns-01 --domain '*.example.com' --email admin@example.com

La suborden issue requiere --confirm-acme, root, Certbot instalado y preflight. No se ejecutó durante esta implementación.

## 10. Límites de verificación

- Certbot no está instalado ni se instaló en esta tarea. dig ya estaba presente en /usr/bin/dig; no se instaló ni se ejecutaron consultas DNS reales.
- No se ejecutó certbot --version, una solicitud ACME real ni comunicación con una CA.
- No se comprobó conectividad pública TCP/80, DNS público real ni propagación TXT real.
- No se validó una cadena real emitida por una CA en el entorno objetivo; la emisión exitosa de Certbot es la fuente de validación ACME cuando se autorice la primera ejecución real.
- No se probaron topologías CDN/proxy ni IPs múltiples en infraestructura real.
- No hay automatización API DNS, renovación, rotación, despliegue, gestión general de dominios ni diagnóstico SSL/TLS completo.
- El flujo de importación de certificados externos ajenos a Certbot sigue pendiente.
- El Resolver TLS se probó solo con fixtures y UID/GID simulados.
- No se modificaron runtime, systemd, certificados persistentes reales, DNS, firewall, puertos, red, dependencias, clave maestra, VPS de pruebas, main ni Xray-Normativa/.

## 11. Estado

B2-A a B2-G: IMPLEMENTADOS EN EL ALCANCE FIXTURE-ONLY AUTORIZADO; VERIFICADOS CON PRUEBAS AISLADAS Y REGRESIÓN GLOBAL Python 182/182, Bash 61/61. Controles estáticos y install.sh --check PASS. No declarar Etapa 4 terminada. No declarar Certbot compatible con el sistema objetivo hasta validar su versión/paquete en una tarea posterior autorizada.


## 12. Aceptación formal del propietario — 2026-11-05

El propietario aceptó formalmente B2 — ACME Certbot y certificados TLS — con las limitaciones, exclusiones y verificaciones descritas en `docs/AUDITORIA_B2_ACME_CERTIFICADOS_2026-11-05.md`. Esta aceptación cubre exclusivamente el incremento fixture-only implementado y auditado. No acredita emisión real, compatibilidad instalada de Certbot, propagación DNS, accesibilidad WAN/TCP 80 ni lectura de leases por una identidad systemd real. No autoriza instalar dependencias, ejecutar ACME real, modificar DNS, servicios, runtime, certificados persistentes, firewall, puertos o red. Etapa 4 permanece ABIERTA y R-06/live NO AUTORIZADA.
