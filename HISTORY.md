# Historial de hitos — Xray Core Manager

Este archivo registra hitos, decisiones y publicaciones relevantes. Es cronológico: añade entradas nuevas al principio y no borres el historial anterior. Para el estado actual consulta PROJECT_STATE.md y docs/PUNTO_CONTROL_ACTUAL.md.

## 2026-11-02 — Creación del sistema de continuidad

**Objetivo:** permitir que cualquier IA retome el proyecto desde el estado real de GitHub y de la VPS, aunque se pierda el chat.

Se estableció el conjunto de cinco documentos:
- AGENTS.md — reglas permanentes para agentes.
- PROJECT_STATE.md — fotografía consolidada del proyecto.
- docs/CONTINUIDAD_DEL_PROYECTO.md — procedimiento y prompt de recuperación.
- docs/PUNTO_CONTROL_ACTUAL.md — punto exacto de reanudación.
- HISTORY.md — historial cronológico.

La primera inspección confirmó que ninguno de esos cinco archivos existía en /opt/xray-manager ni en la rama consultada de GitHub antes de crearlos.

**Estado de destinos:** pendiente de registrar la escritura y verificación final en cada destino.

## 2026-11-02 — Auditoría y estado de Etapa 2

- Especificación normativa vigente: Etapa 2, revisión 1.3, aprobada el 30/10/2026.
- Se observó catálogo de 38 modalidades en config/protocols.tsv.
- Se observó navegación y administración inicial de conexiones en módulos de Etapa 2.
- VLESS dispone de modelo neutral de nueve modalidades y adaptador Xray-core 26.10.31.
- La prueba documentada de integración VLESS aceptó nueve fixtures con xray run -test.
- La implementación actual registra conexiones como borradores; todavía no aplica configuración al runtime ni abre puertos desde el administrador de conexiones.
- La Etapa 2 permanece abierta.

### Discrepancias identificadas

- Las tres modalidades VLESS-XHTTP están en el catálogo y en el diseño técnico, pero no aparecen explícitamente en la clasificación VLESS de la especificación normativa 1.3.
- VMess-HTTPUpgrade-TLS aparece en catálogo/código, pero no está definido expresamente como modalidad independiente en la especificación 1.3.
- Se recomendó conservar VLESS-XHTTP y dejar VMess-HTTPUpgrade-TLS pendiente de validación; queda pendiente la decisión del propietario.

## 2026-11-02 — Etapa 1 aceptada

El propietario declaró expresamente aceptada la Etapa 1 como completada.

Evidencia técnica registrada en la documentación:
- 47/47 comprobaciones normativas PASS.
- 20/20 scripts de prueba PASS.
- bash -n, ShellCheck, shfmt e ./install.sh --check PASS.
- Validación operativa en una VPS desechable Ubuntu 24.04.4 LTS.

Limitaciones documentadas que se conservan:
- La exportación remota SSH/SCP y SHA-256 se probó con mocks, no con un servidor remoto real.
- No se desinstalaron Xray ni Manager instalados en el host de pruebas.
- No se realizó un reinicio del host para validar persistencia tras reboot.

## 2026-11-02 — Último commit conocido de GitHub

- Repositorio: Jaok04/xray-core-manager.
- Rama de trabajo: design/user-identity-association-v1.
- SHA conocido: cd76e84a48974762f28b666e8d440de52062d6a8.
- Mensaje: docs: record stage two menu implementation.
- Fecha: 2026-11-02 09:55:08 UTC.

Este dato debe revalidarse contra el HEAD remoto en cada sesión.

## 2026-11-01 — Ampliación del catálogo VLESS con XHTTP

La documentación técnica registra la decisión de conservar WebSocket/gRPC e incorporar XHTTP como transporte adicional. El catálogo pasó de 35 a 38 registros; VLESS pasó de seis a nueve modalidades. No se migraron registros existentes ni se cambiaron sus identificadores.

Se documentaron pruebas de XHTTP sin TLS, TLS y REALITY con Xray-core 26.10.31. Esta ampliación técnica no actualizó por sí misma la especificación funcional normativa 1.3.

## 2026-10-30 — Aprobación de especificación funcional Etapa 2

La especificación Etapa 2 revisión 1.3 quedó registrada como APROBADA. Define la clasificación funcional de protocolos, modalidades, flujos de creación/administración y reglas de navegación. La aprobación funcional no garantiza compatibilidad técnica anticipada; cada combinación debe validarse contra la versión objetivo y los componentes externos.