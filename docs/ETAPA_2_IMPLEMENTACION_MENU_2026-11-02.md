# Etapa 2 — Menú y administración inicial

**Fecha:** 2026-11-02. **Estado:** implementado y verificado parcialmente; la Etapa 2 continúa abierta.

La especificación normativa sigue siendo la revisión 1.3 ubicada en `/root/Xray_Manager_Documentacion_Final_2026-10-31/02_Protocolos_Conexiones/Etapa_2_Protocolos.md`.

Se implementó la navegación por familias VLESS, VMess, Trojan, Shadowsocks e Hysteria2, el menú opcional SOCKS/HTTP Proxy/WireGuard, los submenús de modalidades, la selección de seguridad prevista y el flujo Crear/Administrar/Volver. Se añadió selección numerada de conexiones, consulta de detalles y edición de borradores. Los plugins OBFS se identifican como externos.

Pruebas PASS: `bash -n`, ShellCheck del módulo y pruebas nuevas, `tests/stage1_menu.sh`, `tests/stage2_navigation.sh`, `tests/stage2_existing.sh` y `tests/smoke.sh`.

Pendiente: asistentes específicos por protocolo, generadores y validadores de VMess/Trojan/Shadowsocks/Hysteria2/SOCKS/HTTP/WireGuard, integración de VLESS, gestión de peers WireGuard y aplicación transaccional con verificación/rollback. No se modificó el runtime ni el firewall. La Etapa 2 no está completada.