# Creación de perfil base VLESS-WS-TLS desde el menú

Fecha: 2026-11-08  
Rama: `design/user-identity-association-v1`  
Base: `520f6c282609e028229c5a29dc64c23665d45fb1`

## Brecha corregida

El compositor VLESS-WS-TLS requiere una revisión de perfil que contenga `inbounds` y `outbounds`. El menú permitía crear perfiles vacíos, copiar desde JSON externo o duplicar otro perfil, por lo que una instalación limpia no podía iniciar el flujo de composición sin preparar un JSON manualmente.

## Implementación

En `modules/profiles.sh`, `profiles_create_menu` incorpora el origen `[4] Crear perfil base para VLESS-WS-TLS`.

El Administrador genera un archivo temporal privado con esta estructura mínima:

```json
{
  "log": {"loglevel": "warning"},
  "inbounds": [],
  "outbounds": [
    {"tag": "direct", "protocol": "freedom", "settings": {}}
  ]
}
```

El archivo se crea con permisos privados, se entrega al almacén de perfiles existente y se elimina tanto en éxito como en error. El perfil queda como borrador, sin usuarios, certificados, runtime ni servicio activo. Después puede utilizarse la opción de composición VLESS-WS-TLS para añadir el inbound desde una conexión administrada.

## Validación

- `bash -n modules/profiles.sh tests/xray_profiles.sh`: PASS.
- ShellCheck `-S error` sobre los archivos modificados: PASS.
- `tests/xray_profiles.sh`: PASS; el test recupera la revisión creada y compara exactamente el JSON base esperado.
- No se modificó runtime, Xray, systemd, certificados, DNS, firewall ni puertos.

## Próximo paso

Integrar la obtención/importación del certificado TLS en el recorrido guiado VLESS-WS-TLS, preservando confirmación ACME y controles de DNS/HTTP-01. Después cerrar el flujo de creación de conexión/usuarios, perfil, validación y primer start. H6-G3 independiente continúa pendiente; esta implementación no autoriza despliegue live.
