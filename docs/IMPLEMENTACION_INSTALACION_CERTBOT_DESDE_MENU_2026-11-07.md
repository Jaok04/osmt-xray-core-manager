# Implementación — instalación guiada de Certbot desde el menú

**Fecha:** 2026-11-07; ampliación 2026-11-08
**Estado:** implementada y validada en desarrollo; no ejecutada en VPS Pruebas.

## Objetivo

Cuando el operador solicita un certificado ACME, Xray Core Manager comprueba primero que Certbot exista y pueda ejecutarse. Si falta, solicita consentimiento antes de instalarlo desde APT de Ubuntu.

## Comportamiento implementado

1. certificates_obtain_menu() llama a certificates_ensure_certbot() antes de pedir método, dominio o correo.
2. Si certbot --version termina correctamente, el flujo continúa.
3. Si Certbot no está en PATH, se informa al operador y se solicita confirmación explícita.
4. Si el operador rechaza, la solicitud ACME se cancela sin ejecutar Certbot ni APT.
5. Si acepta, la instalación requiere root, apt-get y Ubuntu (ID=ubuntu o ID_LIKE con Ubuntu).
6. Se adquiere el lock de ciclo de vida compartido, se ejecuta apt-get update y se instala únicamente certbot con --no-install-recommends. No se ejecuta apt upgrade ni se instalan plugins DNS.
7. Antes de APT se comprueban certbot.timer y snap.certbot.renew.timer: si cualquiera está habilitado o activo, el Manager se niega a instalar encima y no lo modifica. La misma comprobación se aplica cuando Certbot ya está instalado.
8. Tras instalar, si certbot.timer queda habilitado/activo, se ejecuta systemctl disable --now certbot.timer y se verifica que certbot.timer y snap.certbot.renew.timer queden deshabilitados e inactivos. Antes de ello se comprueba que systemctl puede consultar el gestor systemd. La renovación automática permanece bloqueada hasta que exista el deploy hook transaccional del Manager.
9. Se libera el lock y se verifica nuevamente certbot --version. Solo después se permite continuar al selector HTTP-01/DNS-01 y al plan ACME existente.
10. Si la instalación, desactivación del timer o verificación falla, el flujo se detiene y no se envía ninguna solicitud ACME.

## Seguridad y límites

- La instalación de paquetes ocurre solo tras consentimiento interactivo del operador.
- No se ejecutó APT ni se instaló Certbot durante desarrollo/pruebas. El comportamiento de systemctl se validó exclusivamente con un doble fixture.
- No se solicitó ningún certificado real ni se modificaron DNS, firewall, puertos, certificados persistentes, Xray, systemd o runtime.
- No se actualizó la VPS Pruebas.
- La selección de paquete se limita a certbot desde los repositorios configurados de Ubuntu; la confianza del repositorio depende de la configuración APT del sistema.
- No se instala python3-certbot-dns-*; DNS-01 continúa siendo manual según la decisión B2 vigente.
- El timer de renovación permanece deshabilitado hasta que exista el deploy hook transaccional que sincronice Certificate Store y runtime.

## Pruebas

- tests/certificates_menu.sh: PASS; cubre Certbot disponible/ausente, simulación APT, desactivación del timer recién instalado, rechazo de timer preexistente y cancelación ACME.
- Bash global en el corte 2026-11-08: 63/63 PASS.
- Python global en el corte 2026-11-08: 570/570 PASS.
- bash -n global: PASS.
- ShellCheck global -S error: PASS.
- git diff --check: PASS.

## Límites y estado live

La implementación no acredita instalación real de Certbot ni emisión ACME. No se ejecutaron APT, Certbot, DNS, firewall, puertos, systemd, runtime o acciones en VPS Pruebas. La revisión independiente H6-G3 sigue pendiente. El flujo ACME integrado con VLESS-WS-TLS está descrito en docs/IMPLEMENTACION_FLUJO_GUIADO_ACME_VLESS_WS_TLS_2026-11-08.md.
