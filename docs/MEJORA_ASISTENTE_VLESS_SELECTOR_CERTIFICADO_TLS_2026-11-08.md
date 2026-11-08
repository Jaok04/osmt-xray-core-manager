# Mejora del asistente VLESS: selección de certificado TLS

Fecha: 2026-11-08  
Rama: `design/user-identity-association-v1`  
Base de trabajo: `3d2c44a88912a6b60620f1395f33d51874e17c47`

## Objetivo

Reducir la intervención manual al crear conexiones VLESS con TLS. El asistente no debe exigir que el operador conozca ni escriba un `certificate_id` interno.

## Cambios

- `modules/vless_assistant.sh` incorpora `connections_vless_assistant_select_certificate`.
- La función consulta el almacén central mediante `certificate_store.py list`, usando las rutas configuradas por el Manager.
- Presenta opciones numeradas con `certificate_id`, SAN DNS y fecha de vencimiento; devuelve el ID seleccionado al asistente sin exponer material privado.
- Si el catálogo está vacío, informa que primero debe obtenerse e importarse un certificado desde el menú SSL/TLS. No crea certificados, no ejecuta ACME y no cambia el runtime.
- La selección inválida o cancelada falla cerrada.
- Los campos Host HTTP WebSocket y SNI del cliente ahora admiten realmente una entrada vacía; se omiten del modelo persistido cuando no se proporcionan.
- Se ampliaron `tests/vless_assistant.sh` y `tests/vless_tls_lease_assistant.sh`, incluyendo la selección por índice y el caso de campos opcionales vacíos.

## Validación

- `bash -n` sobre los módulos y pruebas modificados: PASS.
- ShellCheck `-S error` sobre los tres archivos modificados: PASS.
- Pruebas focales `vless_tls_lease_assistant.sh`, `vless_assistant.sh` y `xray_vless_integration.sh`: PASS.
- Suite Python: 570/570 PASS.
- Suites Bash: 62/62 PASS.
- `bash install.sh --check`: PASS; no modificó el sistema.
- `git diff --check`: PASS.

## Límites y siguiente etapa

Este cambio mejora la selección del certificado, pero no completa por sí solo el asistente integral de aprovisionamiento. La obtención ACME HTTP-01/DNS-01 y la importación del lineage siguen siendo pasos explícitos del menú de certificados, con confirmaciones propias. No se ejecutó Certbot, no se importó ningún certificado real, no se modificó DNS/firewall/puertos, no se publicó `/etc/xray/config.json` y no se inició Xray.

El siguiente incremento debe integrar la preparación del certificado en un flujo guiado para VLESS-WS-TLS, sin eliminar las confirmaciones de ACME ni inferir disponibilidad DNS/red. Después se debe completar el recorrido de creación de usuarios, composición de perfil, validación y primer start. La revisión independiente H6-G3 sigue pendiente; las pruebas internas de esta sesión no sustituyen esa revisión ni autorizan el despliegue live.
