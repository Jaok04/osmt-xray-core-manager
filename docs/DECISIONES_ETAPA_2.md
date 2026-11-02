# Decisiones complementarias — Etapa 2

**Proyecto:** Xray Core Manager
**Base normativa:** Etapa_2_Protocolos.md, revisión 1.3, aprobada el 30/10/2026.
**Estado:** decisiones complementarias aprobadas por el propietario el 02/11/2026.

## 1. Discrepancias de catálogo y decisiones

- Se conservan las nueve modalidades VLESS existentes en el catálogo, incluidas XHTTP sin TLS/TLS/REALITY.
- VLESS-XHTTP sin TLS, VLESS-XHTTP-TLS y VLESS-XHTTP-REALITY permanecen disponibles en menú y modelo/adaptador.
- El propietario aprobó el diseño técnico VMess y confirmó expresamente que **VMess-HTTPUpgrade-TLS también será implementado**.
- La matriz VMess aprobada incluye HTTPUpgrade sin TLS y HTTPUpgrade-TLS. La variante TLS ya existe en config/protocols.tsv como vmess_httpupgrade_tls, pero todavía no está seleccionable desde el menú ni implementada por un asistente VMess.
- La aprobación de HTTPUpgrade-TLS es una decisión de alcance/diseño. No equivale a validación funcional, prueba de interoperabilidad ni implementación.
- No se modifica retroactivamente la especificación normativa 1.3; este archivo registra las decisiones complementarias autorizadas.

## 2. Diseño VMess aprobado

El diseño formal se conserva en docs/DISEÑO_TECNICO_VMESS.md.

Decisiones principales:
- Xray-core objetivo: v26.10.31.
- Usuarios VMess mediante settings.users con id, level y email; UUID como identificador.
- Matriz de transporte/seguridad cerrada: WS sin TLS/TLS; RAW/TCP TLS/REALITY; gRPC sin TLS/TLS/REALITY; HTTPUpgrade sin TLS/TLS; XHTTP sin TLS/TLS/REALITY; mKCP sin TLS/TLS.
- REALITY no se ofrece para WS, HTTPUpgrade ni mKCP.
- La integración crea borradores y previsualizaciones temporales; no activa runtime ni cambia firewall/puertos.
- Se exige xray run -test por combinación; la prueba de configuración no sustituye la interoperabilidad extremo a extremo.
- Se conserva la advertencia sobre sincronización horaria VMess y sus límites de seguridad/huella de tráfico.

## 3. Estado de implementación

- La navegación actual ofrece HTTPUpgrade sin TLS, pero no permite elegir TLS desde el menú.
- El catálogo contiene vmess_httpupgrade_tls.
- No existen todavía modelo, adaptador Xray, asistente ni persistencia específicos VMess.
- Las pruebas temporales anteriores cubrieron sólo cuatro combinaciones VMess; HTTPUpgrade-TLS sigue pendiente de prueba específica.
- El diseño está aprobado y documentado; la implementación requiere una autorización expresa posterior, tras el contraste obligatorio previo al código.

## 4. Alcance de integración VLESS aprobado

La creación VLESS se integra con el modelo neutral y el adaptador Xray-core v26.10.31 para construir y validar una previsualización temporal. Los borradores no se activan ni se aplican al runtime. Los secretos se gestionan mediante el almacenamiento seguro implementado para VLESS, con las limitaciones y referencias definidas en su documentación técnica.

## 5. Límites que permanecen

La aprobación del diseño VMess no habilita por sí sola persistencia nueva, certificados de producción, apertura de puertos, firewall, activación del servicio, reinicio de Xray ni rollback transaccional. Esas operaciones requieren sus diseños, contrastes y autorizaciones correspondientes.
