# Punto de control actual — Xray Core Manager

**Fecha del corte:** 2026-11-02
**Tarea actual:** Etapa 2 — formalización del diseño VMess.
**Estado:** diseño VMess APROBADO y documentado; implementación todavía no autorizada.

## 1. Entorno verificado

- Repositorio: Jaok04/xray-core-manager.
- Rama autorizada: design/user-identity-association-v1.
- Proyecto VPS: /opt/xray-manager.
- HEAD local y remoto al iniciar esta actualización: b249b3e5b005c2dae301dd1f9230712933f9f482.
- Árbol de trabajo limpio antes de esta actualización.
- Documentación normativa: /root/Xray_Manager_Documentacion_Final_2026-10-31.
- Etapa 1: aceptada formalmente.
- Etapa 2: en desarrollo y abierta.
- P4 de persistencia/backup VLESS: completada y aceptada.
- La VPS tiene checkout Git; la referencia remota se comprobó con git ls-remote.

## 2. Decisión más reciente del propietario

El propietario aprobó el diseño técnico VMess y confirmó que **VMess-HTTPUpgrade-TLS también se implementará**.

La matriz aprobada incluye:
- WS sin TLS/TLS.
- RAW/TCP con TLS o REALITY.
- gRPC sin TLS/TLS/REALITY.
- HTTPUpgrade sin TLS/TLS.
- XHTTP sin TLS/TLS/REALITY.
- mKCP sin TLS/TLS.

La especificación preliminar 1.3 se conserva sin reescritura retroactiva. La ampliación queda registrada como decisión complementaria en docs/DECISIONES_ETAPA_2.md.

## 3. Diseño formal

Documento: docs/DISEÑO_TECNICO_VMESS.md.

Decisiones clave:
- Xray-core v26.10.31 como versión objetivo.
- VMess usa settings.users (id, level, email), no settings.clients de VLESS.
- UUID como identificador de usuario.
- Modelo neutral separado del adaptador Xray.
- Asistente de creación, previsualización temporal y persistencia versionada/segura.
- Borradores sin activación de runtime.
- Pruebas xray run -test para cada combinación, incluida una prueba positiva específica de HTTPUpgrade-TLS.
- Advertencias de sincronización horaria, Forward Secrecy y huella de tráfico VMess documentadas.

## 4. Contraste del estado existente

- Catálogo: están presentes los 14 identificadores VMess, incluidos vmess_httpupgrade y vmess_httpupgrade_tls.
- Menú: HTTPUpgrade sólo permite seleccionar la modalidad sin TLS; falta selector de seguridad para HTTPUpgrade-TLS.
- Implementación: no existen todavía vmess_model.sh, vmess_xray_26_10_31.sh, vmess_assistant.sh ni persistencia VMess específica.
- Validación histórica temporal: PASS para VMess-WS sin TLS, gRPC sin TLS, XHTTP-REALITY y mKCP sin TLS. No cubre la matriz completa.
- HTTPUpgrade-TLS: aprobado en el diseño; aún no probado específicamente, implementado ni verificado.
- No se modificó código, catálogo, runtime, firewall, puertos ni certificados durante la formalización documental.

## 5. Siguiente paso permitido

Realizar el contraste previo específico para implementar VMess: revisar nuevamente la documentación preliminar, diseño aprobado, catálogo, navegación, módulos, almacenamiento seguro, asociaciones de identidad, binario Xray y pruebas. Presentar una matriz de brechas y los archivos exactos que se modificarían. Después solicitar autorización expresa para implementar.

**No iniciar cambios de código hasta esa autorización.** No declarar VMess implementado ni Etapa 2 completada.