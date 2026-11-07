# Implementación — instalación guiada de Certbot desde el menú

**Fecha:** 2026-11-07
**Estado:** implementada y verificada en desarrollo; pendiente auditoría/publicación y prueba live.

## Objetivo

Cuando el operador selecciona «Obtener certificado nuevo (ACME)», Xray Core Manager comprueba primero que Certbot exista y pueda ejecutarse. Si falta, pregunta si desea instalarlo antes de continuar.

## Comportamiento implementado

1. `certificates_obtain_menu()` llama a `certificates_ensure_certbot()` antes de pedir método, dominio o correo.
2. Si `certbot --version` termina correctamente, el flujo continúa.
3. Si Certbot no está en PATH, se informa al operador y se solicita confirmación explícita.
4. Si el operador rechaza, la solicitud ACME se cancela sin ejecutar Certbot ni APT.
5. Si acepta, la instalación requiere root, `apt-get` y Ubuntu (`ID=ubuntu` o `ID_LIKE` con Ubuntu).
6. Se adquiere el lock de ciclo de vida compartido, se ejecuta `apt-get update` y se instala únicamente `certbot` con `--no-install-recommends`. No se ejecuta `apt upgrade` ni se instalan plugins DNS.
7. Se libera el lock y se verifica nuevamente `certbot --version`. Solo después se permite continuar al selector HTTP-01/DNS-01 y al plan ACME existente.
8. Si la instalación o verificación falla, el flujo se detiene y no se envía ninguna solicitud ACME.

## Seguridad y límites

- La instalación de paquetes ocurre solo tras consentimiento interactivo del operador.
- No se ejecutó APT ni se instaló Certbot durante desarrollo/pruebas.
- No se solicitó ningún certificado real ni se modificaron DNS, firewall, puertos, certificados persistentes, Xray, systemd o runtime.
- No se actualizó la VPS Pruebas.
- La selección de paquete se limita a `certbot` desde los repositorios configurados de Ubuntu; la confianza del repositorio depende de la configuración APT del sistema.
- No se instala `python3-certbot-dns-*`; DNS-01 continúa siendo manual según la decisión B2 vigente.

## Pruebas

- `bash tests/certificates_menu.sh`: PASS; cubre Certbot disponible, Certbot ausente con consentimiento, simulación de `apt-get update` + `apt-get install certbot`, verificación posterior y cancelación del flujo ACME.
- Bash global: 62/62 PASS.
- Python global: 406/406 PASS.
- `bash -n` global: PASS.
- `python3 -m compileall -q scripts tests`: PASS.
- ShellCheck focal `-S error`: PASS.
- `git diff --check`: PASS.

## Pendiente

Auditoría documental/funcional, actualización de los documentos de continuidad y autorización explícita antes de commit/push o despliegue en VPS Pruebas. La implementación no acredita instalación real de Certbot ni emisión ACME.
