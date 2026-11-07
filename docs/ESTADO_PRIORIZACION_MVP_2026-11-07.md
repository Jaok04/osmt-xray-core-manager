# Estado de priorización — primer MVP VLESS-WS-TLS (2026-11-07)

**Objetivo prioritario:** desplegar el primer servidor VLESS + WebSocket + TLS desde Xray-Core Manager, sin configuración manual externa. Host de aceptación previsto: VPS Pruebas; FQDN `pruebas.tvrc.me`; TCP/443.

## 1. Regla de ejecución

Priorizar el recorrido vertical mínimo:
**Xray íntegro → preparar servicio → obtener/importar certificado → crear usuario/conexión → validar configuración → publicar/iniciar desde Manager → comprobar conexión externa.**

No rehacer capacidades ya implementadas. No ampliar catálogo de protocolos ni desarrollar automatizaciones avanzadas antes de demostrar el primer servicio. Mantener controles de integridad, permisos, validación, recuperación, auditoría y autorización live.

## 2. Matriz de estado

| Bloque | Capacidad existente | Estado real demostrado | Decisión |
|---|---|---|---|
| B1 — Xray/servicio | Integridad de binario/geodata y opción de preparación de usuario/unidad desde el menú | Fixtures auditados. En VPS Pruebas Xray 26.10.31 y geodata verifican contra manifiesto; aún no existe unidad xray.service ni configuración /etc/xray | Reutilizar. Reconciliar install.json sin reinstalar Xray; después preparar servicio desde el menú con autorización live |
| B2 — Certificado | ACME HTTP-01/DNS-01, importación central, resolver TLS; comprobación e instalación guiada de Certbot | Fixtures auditados; Certbot/ACME real no ejecutados | Reutilizar. Hacer preflight real desde el menú y emitir/importar solo con autorización específica |
| B3 — Usuario/conexión | Usuarios V2, UUID global, compositor VLESS-WS-TLS, validación Xray y exportador URI | Fixtures auditados; no hay cliente externo conectado | Reutilizar sin reimplementación |
| B4 — Aplicación runtime | R-01–R-05 fixture y backend systemd live aislado; controlador único modules/xray_service.sh | No hay flujo live conectado de extremo a extremo; backend live no integrado a R-05/menú | Bloqueador principal. Diseñar y construir el puente mínimo seguro requerido por el MVP |
| B5 — Aceptación | Diagnóstico/observación parcial | No hay prueba WAN, handshake TLS, WebSocket ni tráfico VLESS bidireccional | Ejecutar después de B4 y con autorización live específica |

## 3. Hechos vigentes de VPS Pruebas

- Host Termalin: `08827b29-b7f9-4625-8ff3-351918a03c96`.
- Xray 26.10.31 está instalado; binario y geodata coinciden con `xray-install.json` según `xray_install_integrity.py verify`.
- No reinstalar Xray ni repetir la corrección SIGPIPE.
- `install.json` conserva `xray_installed=false`; reconciliar ese estado administrativo sin reinstalar ni alterar los artefactos íntegros.
- El registro A de `pruebas.tvrc.me` resuelve a `172.235.129.166`, coincidente con la IPv4 pública observada. No volver a cambiar DNS.
- No existen todavía `/etc/xray` ni `xray.service`; no hay listener 80/443. Certificado y conexión externa pendientes.
- UFW está inactivo; la accesibilidad de puertos en el firewall del proveedor no está demostrada.
- No se ha ejecutado APT, Certbot/ACME real, systemd ni modificación runtime en este corte.

## 4. Qué se aplaza

No son prerrequisitos del primer servidor:
- renovación automática Certbot/certbot.timer y deploy hook;
- integración de recarga automática de Xray por renovación;
- restaurador general de shared snapshots;
- ampliación de protocolos/modalidades;
- gestión avanzada de múltiples certificados, dominios o proveedores DNS;
- automatización multi-servidor y observabilidad avanzada.

El schema v2 TLS ya implementado se conserva; no abrir nuevas tareas de almacén salvo que una prueba concreta del MVP demuestre un bloqueo.

## 5. H6-H1 y B4: decisión de secuencia

El contrato H6-H1 fue aprobado por el propietario el 2026-11-07. Sus seis decisiones se conservan y no se revierten. Sin embargo, la implementación completa H6-H1-B/C/D no debe convertirse automáticamente en requisito previo del primer lanzamiento.

Antes de implementar B4, realizar una revisión focal que determine qué garantías de H6-H1 son estrictamente necesarias para la transacción mínima de publicación/configuración y transición del servicio. Reutilizar el journal fixture y los contratos R-05 cuando corresponda, sin debilitar su aislamiento. Evitar construir una infraestructura general de recuperación si una solución mínima, auditable y compatible con la normativa satisface el recorrido.

No conectar el backend live, habilitar R-06 ni ejecutar operaciones reales por el solo hecho de aprobar el diseño. La selección del alcance B4 live y cualquier prueba sobre VPS Pruebas requieren autorización explícita específica.

## 6. Siguiente tarea técnica

**B4-MIN — contrato mínimo de aplicación live para el primer MVP.**

Entregables previos a cualquier código:
1. matriz requisito normativo → función existente → brecha exacta → prueba;
2. secuencia mínima de publicación atómica, validación, copia previa, start/restart explícito y recuperación;
3. separación de configuración publicada, servicio activo y evidencia de configuración cargada;
4. criterios fail-closed ante servicio failed/unknown, drift externo, timeout o snapshot ausente;
5. lista precisa de funciones reutilizables y cambios mínimos;
6. conjunto de pruebas fixture/mocks.

La propuesta debe demostrar por qué cada elemento es imprescindible para el primer lanzamiento. No incluir renovación automática, backup general ni otras funciones aplazadas.

## 7. Restricciones

- Solo rama `design/user-identity-association-v1`; no tocar `main` ni `Xray-Normativa/`.
- No APT, Certbot/ACME, DNS, firewall, puertos, systemd ni runtime sin autorización live específica.
- No leer `/etc/xray-manager/keys/master.key`.
- No modificar VPS Pruebas en esta tarea de diseño.
- No commit/push sin autorización expresa.
- No declarar B4/B5/MVP completados sin pruebas y evidencia real correspondiente.

**Estado:** B1/B2/B3 reutilizables en alcance fixture; B4 es el bloqueo principal; B5 pendiente. H6-H1 aprobado, pero su implementación completa queda subordinada a la necesidad demostrada por B4-MIN y a la prioridad del primer servidor.
