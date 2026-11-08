# Implementación — flujo guiado ACME desde el asistente VLESS-WS-TLS

**Fecha:** 2026-11-08
**Rama:** design/user-identity-association-v1
**Dominio del primer servicio:** pruebas.tvrc.me
**Estado:** implementado y validado en desarrollo; pendiente revisión independiente/publicación y cualquier operación live.

## 1. Objetivo

Eliminar la ruptura entre el asistente VLESS-WS-TLS y el menú independiente de certificados. Cuando el almacén TLS central está vacío, el Administrador puede conducir al operador por la obtención ACME, importación y selección del certificado, sin volver a capturar método, dominio, correo, lineage ni request ID.

## 2. Flujo implementado

1. connections_vless_assistant_select_certificate() consulta el almacén central.
2. Si no hay certificados, solicita confirmación para iniciar el flujo ACME. Si el operador cancela, el asistente falla cerrado.
3. El asistente llama certificates_obtain_menu vless-ws-tls.
4. Ese flujo conserva ambos métodos:
   - HTTP-01: Certbot standalone, TCP/80; solicita IP pública prevista y ejecuta el preflight DNS/puerto existente.
   - DNS-01: Certbot manual; usa los hooks que muestran el TXT exacto y verifican visibilidad antes de continuar. La publicación y retirada del TXT siguen siendo manuales.
5. En el recorrido VLESS el dominio se fija al valor XRAY_MANAGER_VLESS_TLS_DOMAIN, con fallback pruebas.tvrc.me. No se solicita al operador volver a escribirlo.
6. La solicitud se planifica y requiere confirmación independiente antes de ejecutar Certbot con --confirm-acme.
7. Si Certbot informa issued, el menú recupera certificate_request_id y cert_name del resultado estructurado. No vuelve a pedir esos datos.
8. El Manager audita el almacén y solicita una segunda confirmación explícita para importar el lineage como certificado managed nuevo.
9. certificate_acme.py import-certbot vuelve a validar el registro de solicitud, SAN, vigencia, pareja certificado/clave y límites del lineage; delega el cifrado/almacenamiento en Certificate Store.
10. El asistente vuelve a consultar el catálogo y presenta el selector numerado. Solo continúa si encuentra un certificado importado; de lo contrario falla cerrado.

Si el operador rechaza la segunda confirmación, el lineage permanece emitido y sin importar; puede importarse posteriormente desde el menú de certificados. Una solicitud fallida no modifica el almacén central.

## 3. Protección del timer de Certbot

La instalación APT de Certbot puede aportar certbot.timer. La renovación automática del Manager aún no tiene deploy hook transaccional que sincronice la nueva revisión con el almacén central y el runtime Xray. Por eso el instalador guiado ahora:

- requiere que systemctl pueda consultar el gestor systemd antes de ofrecer la instalación;
- se niega a continuar si certbot.timer o snap.certbot.renew.timer ya está habilitado/activo, tanto si Certbot ya existe como si falta; no modifica timers preexistentes;
- solicita consentimiento para instalar Certbot y mantener su timer deshabilitado;
- después de APT, si el paquete aportó certbot.timer, ejecuta systemctl disable --now certbot.timer;
- verifica que certbot.timer y snap.certbot.renew.timer no queden habilitados ni activos; si la comprobación falla, bloquea la continuación ACME e informa el estado.

La renovación automática queda aplazada. No se instala ni habilita un deploy hook; no se habilita certbot.timer. Esta protección no constituye implementación de renovación ni de rotación automática.

## 4. Límites de seguridad y operación

- Las confirmaciones de emisión e importación son independientes.
- No se guardan claves privadas en el historial de conversación, argumentos ni catálogo en texto claro.
- DNS-01 no usa API de proveedor: TXT manual, verificación de propagación y limpieza manual exacta.
- HTTP-01 no abre TCP/80 ni cambia firewall; solo verifica los prerrequisitos locales y DNS antes de llamar a Certbot.
- La importación crea un certificate_id managed nuevo; no cambia conexiones, perfiles, /etc/xray/config.json, systemd ni runtime.
- No se ejecutó APT, Certbot real, ACME, importación de certificados reales, DNS, firewall, apertura de puertos ni cambios en VPS Pruebas.
- No se modificó main ni Xray-Normativa/.
- H6-G3 independiente sigue pendiente.

## 5. Pruebas y validación

- tests/certificates_menu.sh: PASS; cubre timer nuevo deshabilitado, timer preexistente protegido, emisión/importación con reutilización del request ID, rechazo de la segunda confirmación y DNS-01 con dominio predeterminado.
- tests/vless_acme_guided_selector.sh: PASS; catálogo vacío → consentimiento → workflow VLESS-WS-TLS → catálogo actualizado → selección del certificado.
- Python: 570/570 PASS.
- Bash: 63/63 PASS.
- bash -n global: PASS.
- ShellCheck global -S error: PASS.
- bash install.sh --check: PASS, sin modificar el sistema.
- git diff --check: PASS.

## 6. Siguiente paso

La integración permite preparar y seleccionar el certificado desde el asistente, pero no demuestra una emisión real ni el primer despliegue. Antes de live: revisión independiente H6-G3, publicación/sincronización aprobada, comprobación DNS y accesibilidad de TCP/80 o preparación manual DNS-01. La emisión real requiere consentimiento dentro del menú y autorización específica de operaciones live. El timer de renovación seguirá deshabilitado hasta implementar y validar el deploy hook transaccional del Manager.
