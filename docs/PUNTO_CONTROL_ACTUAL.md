# Punto de control actual — Xray Core Manager

**Fecha del corte:** 2026-11-02
**Tarea:** P1 infraestructura criptográfica para persistencia segura VLESS.
**Estado:** P1 implementada y verificada; P2 pendiente.

## 1. Entorno

- Repositorio: Jaok04/xray-core-manager.
- Rama autorizada: design/user-identity-association-v1.
- VPS/proyecto: /opt/xray-manager.
- HEAD local de inicio: 8f23b0fbd3be8b61e370be74369ce1bcfd0e5ca0.
- Árbol de trabajo estaba limpio al iniciar.
- Commit de implementación publicado: 29459ce3abd6961238182631a28738633b7cc8d0 (feat: integrate VLESS draft configuration assistant).
- Documentación normativa: /root/Xray_Manager_Documentacion_Final_2026-10-31.
- Etapa 1: aceptada formalmente; no reabrir.
- Etapa 2: en desarrollo y abierta.
- Etapa 3: existen módulos/documentación; su cierre requiere auditoría independiente.

## 2. Decisiones complementarias aprobadas

El propietario aprobó el 2026-11-02:
- conservar las nueve modalidades VLESS del catálogo, incluidas las tres variantes XHTTP;
- dejar VMess-HTTPUpgrade-TLS pendiente de validación, sin considerarlo modalidad funcionalmente aprobada;
- continuar con la integración del asistente VLESS.

La especificación normativa 1.3 no se reescribió. Ver docs/DECISIONES_ETAPA_2.md.

## 3. Cambios implementados en este corte

- Nuevo módulo modules/vless_assistant.sh.
- Integración del módulo en bin/xray-manager.
- El flujo de alta de borradores VLESS llama al asistente después de registrar el borrador.
- Menú VLESS presenta las modalidades XHTTP sin TLS, TLS y REALITY.
- El asistente solicita dirección de escucha y opciones por modalidad, construye modelo neutral y configuración temporal con el adaptador v26.10.31.
- Solicita de forma oculta la clave privada REALITY.
- Ejecuta xray run -test si el binario de validación fijado está disponible.
- Los JSON temporales/secretos se eliminan al terminar. No se persisten secretos ni se guarda una configuración reutilizable.
- El registro permanece state=draft y runtime_applied=false. No se inicia Xray, no se abren puertos ni se modifica firewall.
- Documentación técnica y decisión complementaria: docs/GENERADOR_VLESS_DISENO.md y docs/DECISIONES_ETAPA_2.md.
- Nueva prueba: tests/vless_assistant.sh.

## 4. Verificación ejecutada en esta sesión

- Todos los scripts tests/*.sh: PASS.
- Incluye pruebas de concurrencia, integridad JSON, instalador, navegación, conexiones, usuarios legacy/v2, servicios y desinstalación.
- tests/xray_vless_integration.sh: PASS para las nueve modalidades con Xray 26.10.31; también rechaza opciones XHTTP incompletas y modo desconocido.
- tests/vless_assistant.sh: PASS; valida previsualización temporal, rechazo de ruta WS inválida y conservación del borrador.
- bash -n: PASS para módulos modificados y punto de entrada.
- ShellCheck: PASS para modules/vless_assistant.sh y modules/connections.sh.
- shfmt aplicado al nuevo módulo.
- git diff --check: PASS.
- El binario Xray solo ejecutó modo -test sobre archivos temporales; no se inició servicio ni se abrió listener.

Advertencias observadas en Xray 26.10.31: WebSocket y gRPC están marcados como obsoletos/no recomendados; REALITY avisa sobre riesgo de bloqueo si escucha en puerto distinto de 443. No son fallos de configuración.

## 5. Límites y trabajo pendiente

- La configuración no se persiste: el diseño de almacenamiento seguro está documentado y pendiente de aprobación.
- No se implementó aplicación transaccional, activación runtime, apertura de puertos, firewall ni rollback.
- No se hizo prueba de conectividad extremo a extremo.
- VMess-HTTPUpgrade-TLS sigue pendiente de validación.
- Faltan modelos/asistentes/validadores para VMess, Trojan, Shadowsocks, Hysteria2 y protocolos opcionales.
- Falta integrar asociaciones WireGuard con identidades/Etapa 3.

## 6. Diseño de persistencia segura

Se documentó la propuesta en docs/DISEÑO_PERSISTENCIA_SEGURA_VLESS.md: AES-256-GCM mediante python3-cryptography, clave maestra local root-only, separación de datos, referencias TLS externas, escritura atómica, bloqueo compartido, material descifrado solo bajo /run y recuperación fail-closed. La implementación se divide en P1 infraestructura criptográfica, P2 almacén, P3 integración del asistente y P4 backup/restore.

Hallazgo de seguridad: la clave privada REALITY se pasa actualmente a jq por --arg; debe eliminarse antes de persistir secretos. No se ha instalado dependencia, creado clave maestra ni cambiado el asistente durante este corte.

## 7. Próxima acción

Continuar cerrando P2: añadir pruebas de interrupción/publicación fallida y concurrencia cruzada, revisar integridad de archivos y completar auditoría. P1 está publicada. No generar todavía la clave maestra real; se creará al integrar el primer guardado de secretos en P3. Mantener borradores y no activar runtime.

No modificar main. No declarar Etapa 2 completada.


### Actualización 2026-11-02 — P2 en curso

Se implementó inicialmente `scripts/vless_config_store.py` con esquema neutral VLESS versión 1, revisiones inmutables, publicación atómica de referencias bajo el bloqueo compartido y auditoría sin borrado automático. `tests/vless_config_store.sh` PASS. P2 no está completado: quedan pruebas de interrupciones/concurrencia, suite completa y auditoría final. No se activó runtime ni se creó la clave maestra real.

P2: `tests/*.sh` 25/25 PASS; pruebas específicas incluyen interrupción antes de publicar catálogo (huérfano detectable) y dos escritores concurrentes. `install.sh --check`, sintaxis, py_compile, ShellCheck, shfmt y diff PASS. El campo `secret_ref` queda reservado como null hasta P3.

### P3 — integración de persistencia segura VLESS (implementada y verificada)

Se integró guardado bajo confirmación desde el asistente, cifrado AES-256-GCM de claves privadas TLS/REALITY, referencias versionadas en catálogo/configuración y recuperación temporal para validación. Nuevo `scripts/vless_prepare_config.py`; `vless_config_store.py` ahora admite secretos cifrados y auditoría de blobs. El asistente deja de pasar la clave REALITY como `jq --arg` y usa `--rawfile`. Pruebas focales REALITY/TLS/recuperación PASS. Borradores no se activan. Suite completa `tests/*.sh` 25/25 PASS; `install.sh --check`, `bash -n`, `py_compile`, ShellCheck, shfmt y `git diff --check` PASS. Clave maestra real de VPS no generada. P3 aún no publicada en GitHub.
