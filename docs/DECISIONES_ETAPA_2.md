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
- Las etiquetas visibles distinguen VMess-WS (sin TLS adicional) y VMess-TLS (RAW/TCP + TLS), manteniendo los IDs `vmess_ws` y `vmess_tcp_tls`.
- El asistente VMess presenta el desfase horario máximo de 120 segundos, advierte sobre WebSocket/HTTPUpgrade y muestra un resumen completo de revisión antes del consentimiento de guardado, sin revelar claves privadas.

## 3. Estado de implementación (actualización 2026-11-02)

- El menú, modelo neutral, adaptador Xray 26.10.31, asistente, preparación de configuración y almacén VMess están implementados y publicados/sincronizados. La auditoría integral del 2026-11-02 confirmó 14/14 y 38/38 PASS, pero detectó F-01–F-04; F-05 live no está verificado. El módulo NO está aceptado. Ver el informe y la matriz de trazabilidad.
- Las 14 combinaciones fueron aceptadas por `xray run -test`; la cobertura de navegación y los casos negativos están registrados en `docs/DISEÑO_TECNICO_VMESS.md` y `docs/PUNTO_CONTROL_ACTUAL.md`.
- El almacén VMess se mantiene aislado en `/var/lib/xray-manager/vmess/{configurations,secrets}` y usa campos de catálogo `vmess_*` independientes.
- VMess aún no está integrado con las asociaciones globales de identidad de Etapa 3; sus usuarios se capturan manualmente en el asistente.
- El backup/restore P4 sigue siendo exclusivamente VLESS y no incluye configuraciones ni secretos VMess. La restauración VLESS ahora combina las entradas VLESS del backup con las entradas VMess vigentes, valida sus referencias y conserva el almacén VMess sin modificarlo. El detalle y la evidencia de esta corrección se registran en la sección 9 de `docs/P4_BACKUP_RECUPERACION_VLESS.md`; su aceptación formal específica está pendiente.
- Backup/restore VMess independiente sigue fuera del alcance y requiere diseño/autorización separados.
- La persistencia VMess no implementa rollback transaccional: una interrupción después de escribir archivos y antes de publicar el catálogo puede dejar artefactos huérfanos; `audit` debe detectarlos y nunca eliminarlos automáticamente.

## 4. Alcance de integración VLESS aprobado

La creación VLESS se integra con el modelo neutral y el adaptador Xray-core v26.10.31 para construir y validar una previsualización temporal. Los borradores no se activan ni se aplican al runtime. Los secretos se gestionan mediante el almacenamiento seguro implementado para VLESS, con las limitaciones y referencias definidas en su documentación técnica.

## 5. Límites que permanecen

La implementación VMess aprobada se limita a borradores, validación, persistencia cifrada y recuperación temporal. No habilita certificados de producción, apertura de puertos, firewall, activación del servicio, reinicio de Xray ni rollback transaccional. El backup/restore VMess queda pendiente de diseño y aprobación separados.

## 7. Resultado del bloque correctivo F-01 a F-04 — 2026-11-02

F-01 a F-04 se implementaron y revalidaron dentro del alcance autorizado. La evidencia está en docs/AUDITORIA_INTEGRAL_VMESS_2026-11-02.md y docs/MATRIZ_TRAZABILIDAD_VMESS_2026-11-02.md. Suite 39/39 PASS; Xray 14/14 modalidades y 16/16 casos negativos PASS. F-05 live continúa no verificado. No se autorizó ni ejecutó inicialización del almacén/clave maestra real, runtime, firewall, puertos, servicios, backup/restore VMess ni Etapa 3. VMess no está aceptado; Etapa 2 permanece abierta.
