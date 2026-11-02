# Decisiones complementarias — Etapa 2

**Proyecto:** Xray Core Manager
**Base normativa:** Etapa_2_Protocolos.md, revisión 1.3, aprobada el 30/10/2026.
**Estado:** decisiones complementarias aprobadas por el propietario el 02/11/2026.

## 1. Discrepancias de catálogo y decisiones

- Se conservan las nueve modalidades VLESS existentes en el catálogo, incluidas XHTTP sin TLS/TLS/REALITY.
- VLESS-XHTTP sin TLS, VLESS-XHTTP-TLS y VLESS-XHTTP-REALITY permanecen disponibles en menú y modelo/adaptador.
- El propietario aprobó el diseño técnico VMess y confirmó expresamente que **VMess-HTTPUpgrade-TLS también será implementado**.
- La matriz VMess aprobada incluye HTTPUpgrade sin TLS y HTTPUpgrade-TLS. La variante TLS existe en config/protocols.tsv como vmess_httpupgrade_tls y está integrada en el menú y asistente VMess en la implementación local en curso.
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

- El menú, modelo neutral, adaptador Xray 26.10.31 y asistente VMess existen en la VPS como cambios locales aún no publicados.
- Las 14 combinaciones fueron aceptadas por `xray run -test` en la prueba de integración VMess ejecutada previamente en esta sesión.
- El asistente guarda borradores y recupera configuraciones; HTTPUpgrade-TLS está incluido.
- El almacén VMess se mantiene aislado en `/var/lib/xray-manager/vmess/{configurations,secrets}` y usa campos de catálogo `vmess_*` independientes.
- VMess aún no está integrado con las asociaciones globales de identidad de Etapa 3; sus usuarios se capturan manualmente en el asistente.
- El backup/restore P4 sigue siendo exclusivamente VLESS. No incluye configuraciones ni secretos VMess. Como el catálogo es compartido, restaurar un backup VLESS antiguo puede revertir entradas VMess del catálogo; el almacén VMess separado no se modifica y puede quedar con archivos huérfanos.
- La implementación local permanece en revisión y no está publicada ni aceptada como módulo completo.

## 4. Alcance de integración VLESS aprobado

La creación VLESS se integra con el modelo neutral y el adaptador Xray-core v26.10.31 para construir y validar una previsualización temporal. Los borradores no se activan ni se aplican al runtime. Los secretos se gestionan mediante el almacenamiento seguro implementado para VLESS, con las limitaciones y referencias definidas en su documentación técnica.

## 5. Límites que permanecen

La implementación VMess aprobada se limita a borradores, validación, persistencia cifrada y recuperación temporal. No habilita certificados de producción, apertura de puertos, firewall, activación del servicio, reinicio de Xray ni rollback transaccional. El backup/restore VMess queda pendiente de diseño y aprobación separados.