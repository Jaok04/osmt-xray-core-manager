# Punto de control actual — Xray Core Manager

**Fecha del corte:** 2026-11-02
**Tarea actual:** Etapa 2 — P4, backup y recuperación segura VLESS.
**Estado actual:** corrección del journal implementada y verificada; suite completa 31/31 PASS; P4 abierta por auditoría de límites/permisos y aceptación formal.

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

## Actualización 2026-11-02 — P4 en implementación

- HEAD inicial: `46c3e52b2a59f6ca69ea2de9013cf3cda0e0331a`, rama autorizada limpia.
- Aprobado por el usuario el contrato técnico de P4.
- Añadidos backup de datos y manifiesto verificable, paquete de recuperación scrypt/AES-256-GCM, verificación y restauración con staging/journal; menú de acceso integrado.
- Pruebas focales backup, restore aislado y recuperación scrypt/AES-GCM PASS; suite completa 29/29 PASS en primera revisión. Se añadieron correcciones posteriores y pruebas focales repetidas.
- No se tocó `/var/backups/xray-manager` histórico, la clave maestra real, datos operativos, firewall ni runtime.
- P4 sigue ABIERTA: falta probar cortes abruptos en todas las fronteras del journal y completar pruebas end-to-end de restauración de blobs cifrados TLS/REALITY. Detalle en `docs/P4_BACKUP_RECUPERACION_VLESS.md`.


## Actualización de punto de control — EOF en menús y auditoría de disco (2026-11-02)

**Tarea actual:** corregir el tratamiento de EOF que provocó bucles de menús y crecimiento ilimitado de archivos de salida durante pruebas.

**Entorno verificado al iniciar:** rama `design/user-identity-association-v1`, HEAD `4ecd898ab9034ae0a499f2a2b5dac74c7b35ad71`, remoto `origin` en el mismo commit. `/opt/xray-manager` tiene `.git`; el árbol tenía dos artefactos locales sin seguimiento: `scripts/__pycache__/` y `tests/vless_backup_restore_secrets.sh`.

**Cambios implementados:**
- `ui_read_option()` ahora devuelve estado 1 al detectar EOF y limpia la variable destino.
- Los menús principales/secundarios y los prompts de selección salen de forma ordenada al recibir EOF.
- Los prompts de identificador del menú de backup VLESS también abortan al recibir EOF.
- `tests/stage1_menu.sh` incluye pruebas EOF para navegación directa/anidada y limita a 1 MiB la salida de cada caso de regresión.
- Se incorpora `tests/vless_backup_restore_secrets.sh`, preexistente en la VPS, después de revisar su aislamiento y ejecutar PASS.

**Verificación ejecutada:** `tests/stage1_menu.sh`, `tests/users_v2_menu.sh`, `tests/stage1_settings.sh` y `tests/vless_backup_restore_secrets.sh`: PASS. `bash -n` para todos los scripts `.sh`, ShellCheck para archivos modificados y `git diff --check`: PASS. Suite completa `tests/*.sh`: 30/30 PASS; `install.sh --check`, `bash -n` de todos los scripts shell, ShellCheck, shfmt del test nuevo y `git diff --check`: PASS.

**Incidente de disco:** se eliminó únicamente `/tmp/tmp.oaFf5wTZwt` tras detener PID 36728 y confirmar que no había handles abiertos. Se liberaron el archivo de 20.46 GB y el archivo borrado de ~925 MB que el proceso retenía. Estado posterior: 3.7 GB usados, 71 GB libres, 5%. Los directorios `/tmp/tmp.u7Vq57eHNx` (282 MB) y `/tmp/tmp.EsxO527Ihe` (47 MB) se inspeccionaron y se dejaron intactos; son salidas históricas de pruebas de menú V2.

**Publicación verificada:** GitHub `design/user-identity-association-v1` apunta al commit `fa7242a61248a71b64552511d1db932ebbc8d7d0`; su árbol `b03db9b450288eccbf61e761655f286763df3a70` coincide con el árbol del commit local `b520c53bd5a32007b30519e0756fce13fe8916b5` en los 17 archivos. El push SSH de la VPS fue rechazado por falta de clave autorizada y el fetch HTTPS requiere credenciales; la referencia local `origin/...` permanece en el commit base anterior. En la próxima sesión, recuperar autenticación Git y reconciliar el HEAD local con el remoto sin volver a aplicar cambios. P4 sigue abierta: faltan pruebas de corte abrupto en todas las fronteras del journal, comportamiento ante certificado TLS externo ausente y aceptación formal.

## 2026-11-02 — autenticación SSH y reconciliación de referencias

Se creó una clave SSH Ed25519 dedicada a este repositorio y se registró en GitHub como Deploy Key de solo lectura (sin permiso de escritura). La VPS autentica correctamente mediante el alias `github.com-xray-core-manager`; la URL `origin` de este checkout usa ese alias y los demás repositorios/configuraciones SSH no se modificaron. `git fetch` se completó correctamente. Se verificó que el árbol local anterior y el árbol remoto eran idénticos (`b6ed32ae1ff32dc4c8c6953a2d1eec48159b1d08`), por lo que se movió únicamente la referencia local de la rama con comprobación del SHA anterior, sin resetear ni sobrescribir archivos. Estado final: `design/user-identity-association-v1` y `origin/design/user-identity-association-v1` apuntan a `5ade7feda328ff4a4f6796fd7ab263237b40dbfa`; working tree limpio y sin divergencia. Las notas anteriores sobre falta de autenticación y refs obsoletas quedan superadas por esta verificación. La clave SSH anterior se conservó intacta. La Deploy Key nueva es de solo lectura; las publicaciones futuras deberán seguir usando el mecanismo autorizado de GitHub API u otro acceso de escritura expresamente configurado.


## Punto de control actualizado — P4 journal/restore (2026-11-02)

- Se corrigió `scripts/vless_backup.py`: el journal registra la existencia previa de `connections/` y `secrets/`; cada rename relevante fuerza `fsync` del directorio padre antes de avanzar la fase. `recover-restore` acepta journals nuevos y legacy y preserva los artefactos parciales en cuarentena.
- `tests/vless_backup_journal_crash_matrix.sh`: 32 interrupciones abruptas simuladas mediante `os._exit`, con cobertura de fases, renombrados, publicación y las cuatro combinaciones de existencia previa. PASS.
- `tests/vless_backup_journal.sh`: rollback de journal legacy/nuevo y destino originalmente ausente. PASS.
- `tests/vless_backup_restore.sh` y `tests/vless_backup_restore_secrets.sh`: PASS; el último prueba el certificado TLS externo referenciado pero ausente, sin impedir la restauración ni activar runtime.
- Suite completa final `tests/*.sh`: 31/31 PASS. `install.sh --check`, sintaxis Bash de todos los scripts, `py_compile`, ShellCheck/shfmt de pruebas modificadas y `git diff --check`: PASS.
- No se creó backup operativo ni se accedió a la clave maestra real. No se modificaron runtime, firewall ni certificados.
- **Pendiente:** auditar límites agregados de extracción/descompresión, memoria, rutas y permisos de staging/publicación; repetir suite final; obtener aceptación formal. P4 NO está aceptada ni completada.
