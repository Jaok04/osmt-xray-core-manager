# Registro de decisiones técnicas

Estado: decisiones heredadas del diseño y auditoría, pendientes de validación durante implementación.

## Plataforma

- Ubuntu 24.04 LTS amd64 como referencia inicial.
- Bash >= 5.2.
- systemd y flock se detectan en tiempo de ejecución; no se presuponen en cualquier sistema.
- Idioma: español.
- Zona horaria de aplicación prevista: America/Bogota, sin cambiar la zona horaria del servidor automáticamente.

## Rutas

- Código: /opt/xray-manager
- Datos: /var/lib/xray-manager
- Respaldos: /var/backups/xray-manager
- Logs: /var/log/xray-manager
- Runtime: /run/xray-manager
- Caché: /var/cache/xray-manager

## Xray

- Binario previsto: /usr/local/bin/xray
- Datos: /usr/local/share/xray
- Configuración: /usr/local/etc/xray
- Usuario de servicio: xray
- El administrador se ejecuta con privilegios root; no intenta autoelevarse mediante sudo.
- API administrativa limitada a loopback.
- La API en loopback no se considera aislamiento frente a otros procesos locales.

## Protocolos y API

- HandlerService no se considera universal: cambios dinámicos de usuarios solo para protocolos soportados y validados.
- Cambios de runtime deben persistirse también en configuración y registros propios.
- Estadísticas por usuario requieren stats/policy y asociación por email técnico donde aplique.
- Dato ausente no equivale a cero.
- Hysteria2 en Xray usa protocol hysteria, versión 2, transport hysteria versión 2 y TLS.
- Hysteria sobre QUIC requiere TLS.
- VLESS sin TLS no debe presentarse como transporte protegido por TLS.
- REALITY no se combina con WS, HTTPUpgrade ni mKCP.

## Pendiente de decisión

- Cliente ACME y proveedor DNS para automatización de certificados.
- Frecuencia de consulta de estadísticas/API.
- Autenticidad criptográfica de firmas de distribución.
- Alcance de auditoría antimanipulación.
- Estrategia de pruebas runtime aisladas de la instancia activa.

No implementar opciones pendientes mediante suposiciones silenciosas.