# Xray Core Manager — Estado del proyecto

**Corte de estado:** 2026-11-02  
**Estado global:** Etapa 1 aceptada por el propietario; Etapa 2 en desarrollo y abierta.  
**Repositorio:** https://github.com/Jaok04/xray-core-manager  
**Rama autorizada:** design/user-identity-association-v1  
**VPS de desarrollo:** /opt/xray-manager

> Este documento es una fotografía de estado, no sustituye la documentación normativa. Antes de actuar, verifica el HEAD actual de GitHub y vuelve a inspeccionar la VPS.

> **Regla obligatoria permanente:** antes de implementar cualquier etapa o funcionalidad, contrastar el proyecto con la documentación preliminar aprobada en `/root/Xray_Manager_Documentacion_Final_2026-10-31`. Las mejoras requieren informe previo y autorización expresa del propietario. Ver `docs/REGLA_CONTRASTE_DOCUMENTACION_PRELIMINAR.md` y `AGENTS.md`.

## 1. Referencias oficiales

- Documentación normativa: /root/Xray_Manager_Documentacion_Final_2026-10-31
- Especificación funcional Etapa 2: 02_Protocolos_Conexiones/Etapa_2_Protocolos.md y Etapa_2_Protocolos.yaml.
- Código en VPS: /opt/xray-manager
- Rama autorizada: design/user-identity-association-v1
- main: no modificar.

## 2. Estado de repositorio y VPS

### GitHub

Último commit de la rama registrado en la auditoría previa:
- SHA: cd76e84a48974762f28b666e8d440de52062d6a8
- Mensaje: docs: record stage two menu implementation
- Fecha registrada: 2026-11-02 09:55:08 UTC.

Este SHA es una referencia conocida, no una garantía de que siga siendo HEAD. Cada sesión debe consultar la referencia remota actual antes de trabajar.

### VPS

- Ruta: /opt/xray-manager
- En la inspección del 2026-11-02 no existía /opt/xray-manager/.git.
- Por ello no se puede establecer desde esa ruta branch, HEAD ni git status.
- La VPS y GitHub deben compararse por contenido/hashes; no asumir equivalencia.
- El sistema de continuidad de cinco archivos está creado en la VPS y publicado en la rama autorizada; la primera verificación encontró coincidencia exacta de texto entre ambos destinos.
- En una auditoría previa, la mayoría de los archivos comparados coincidían. modules/main_menu.sh y docs/ETAPA_2_IMPLEMENTACION_MENU_2026-11-02.md mostraron SHA distintos pese a que el texto recuperado parecía igual. La causa no quedó determinada; mantenerlos como divergencia pendiente de reconciliación hasta volver a comparar bytes.

## 3. Etapas

| Etapa | Alcance | Estado |
|---|---|---|
| Etapa 1 | Menú principal y administración del sistema | ACEPTADA por el propietario |
| Etapa 2 | Protocolos y conexiones | EN DESARROLLO; abierta |
| Etapa 3 | Gestión de usuarios, identidades y asociaciones | Hay módulos y documentación existentes; el estado formal y la cobertura de la etapa requieren auditoría específica |
| Etapas posteriores | Según documentación normativa | Pendientes |

No confundir las etapas del proyecto con las fases A/B/C del instalador o de administración de Xray.

La carpeta de desarrollo ya contiene módulos y pruebas de usuarios/identidades/asociaciones (incluidos users_v2); no se debe tratar Etapa 3 como inexistente. Su alcance, cobertura y criterios de cierre deben auditarse por separado antes de declararla completada.

## 4. Etapa 1 — resultado aceptado

El propietario aceptó expresamente la Etapa 1 como completada.

Evidencia documentada:
- Cotejo normativo: 47/47 comprobaciones PASS.
- Suite posterior a los últimos cambios: 20/20 scripts PASS.
- bash -n: PASS.
- ShellCheck: PASS.
- shfmt: PASS en los archivos homogéneos; tests/uninstall.sh conserva formato histórico mixto.
- ./install.sh --check: PASS.
- Validación operativa en VPS desechable Ubuntu 24.04.4 LTS.
- Instalación aislada de Xray 26.10.31, comprobaciones de permisos/unidad y pruebas de guardas, sin activar la unidad real ni alterar firewall/SSH.

Limitaciones conocidas que deben conservarse:
- U08: SSH/SCP y SHA-256 de exportación externa probados con mocks; no hubo destino remoto real ni credenciales.
- No se desinstalaron Xray ni Manager instalados en el host de pruebas.
- No se reinició la VPS para probar persistencia tras reboot.
Estas limitaciones no anulan la aceptación del propietario; deben seguir identificándose como límites de validación, no ocultarse ni convertirse automáticamente en tareas de implementación.

Documentos técnicos de evidencia:
- docs/MATRIZ_TRAZABILIDAD_ETAPA_1_REV_1_2.md
- docs/ETAPA_1_VALIDACION_PRUEBAS_2026-11-01.md
- docs/ETAPA_1_AUDITORIA_FINAL_2026-11-02.md
- docs/ETAPA_1_VALIDACION_OPERATIVA_VPS_DESECHABLE_2026-11-02.md
- docs/ETAPA_1_CONCURRENCIA_CONFIRMACIONES_2026-11-01.md

## 5. Etapa 2 — estado actual

La especificación funcional aprobada es revisión 1.3, aprobada el 30/10/2026. Define cinco familias principales (VLESS, VMess, Trojan, Shadowsocks, Hysteria2), tres opcionales (SOCKS, HTTP Proxy, WireGuard), navegación jerárquica y flujos Crear/Administrar.

### Implementado en la base actual

- Menú de familias y protocolos opcionales.
- Navegación por modalidades y selección de seguridad prevista.
- Flujo Crear / Administrar / Volver.
- Registro y administración inicial de conexiones como borradores.
- Listado, consulta de detalles, edición y eliminación confirmada de borradores.
- Catálogo config/protocols.tsv con 38 registros.
- Modelo neutral VLESS de nueve modalidades.
- Adaptador VLESS específico para Xray-core 26.10.31.
- Prueba de integración documentada para las nueve modalidades VLESS mediante xray run -test.

### Límites importantes

- Las conexiones se guardan como draft; no equivalen a conexiones activas.
- La creación/edición no aplica una configuración al runtime.
- No se abren puertos ni se modifica firewall por el flujo de conexiones.
- El asistente VLESS ya está integrado con el modelo/adaptador para construir una previsualización temporal; cuando está disponible, incorpora usuarios VLESS en estado borrador.
- El asistente solicita opciones por modalidad y ejecuta xray run -test con el binario fijado si está disponible. Los archivos temporales se eliminan al terminar.
- Hallazgo de seguridad pendiente de corregir: la clave privada REALITY se pasa a jq mediante --arg; la implementación de persistencia debe eliminar esa exposición en argumentos de proceso.
- No hay persistencia segura de configuración ni secretos; no se aplica runtime ni se activa el servicio.
- Diseño propuesto de persistencia: docs/DISEÑO_PERSISTENCIA_SEGURA_VLESS.md. Pendiente de aprobación; no se ha instalado ninguna dependencia ni generado clave maestra.
- La validación xray run -test no prueba conectividad extremo a extremo.
- La prueba documentada de nueve modalidades corresponde al entorno y binario Xray 26.10.31; no asumir que se reejecutó en cada sesión.

### Pruebas registradas

Se documentan resultados PASS para navegación, administración de borradores, VLESS, colisiones de puertos, carreras de concurrencia, persistencia JSON, sintaxis Bash, ShellCheck y shfmt. La auditoría del 02/11 no reejecutó todas esas pruebas; consulta los informes y repítelas cuando el cambio lo requiera.

## 6. Decisiones complementarias aprobadas el 2026-11-02

- Se conservan las nueve modalidades VLESS del catálogo, incluidas XHTTP sin TLS, TLS y REALITY.
- VMess-HTTPUpgrade-TLS queda pendiente de validación técnica/funcional; su presencia en catálogo/código no se considera aprobación funcional.
- La especificación normativa 1.3 no se reescribió retroactivamente. La decisión queda registrada en docs/DECISIONES_ETAPA_2.md.

## 7. Pendientes principales de Etapa 2

- Resolver y formalizar las discrepancias normativas indicadas.
- Diseñar y aprobar persistencia segura de opciones VLESS y secretos. Propuesta documentada en docs/DISEÑO_PERSISTENCIA_SEGURA_VLESS.md; aún no implementada.
- Definir e implementar modelos, generadores y validadores para VMess, Trojan, Shadowsocks e Hysteria2.
- Implementar administradores específicos SOCKS, HTTP Proxy y WireGuard.
- Integrar peers WireGuard con las identidades/asociaciones de Etapa 3.
- Diseñar aplicación transaccional de configuración, validación, verificación y rollback.
- Realizar pruebas de runtime e integración por modalidad y dependencias externas.
- Verificar compatibilidad real de plugins externos.

## 8. Reglas de estado

Usa siempre IMPLEMENTADO, VERIFICADO, PUBLICADO, SINCRONIZADO y ACEPTADO como estados separados, según AGENTS.md. Registra fecha, evidencia y entorno. No extrapoles un resultado de un entorno a otro.

## 9. Siguiente punto de control

Consultar docs/PUNTO_CONTROL_ACTUAL.md. No iniciar una nueva implementación de Etapa 2 hasta recuperar GitHub/VPS, resolver las discrepancias y obtener autorización explícita para la siguiente tarea.
## Hito P1 — Persistencia segura VLESS (2026-11-02)

- P1 IMPLEMENTADO: primitivas AES-256-GCM, clave maestra idempotente y fail-closed, AAD, blobs versionados, escritura atómica y controles de permisos.
- Dependencia python3-cryptography formalizada en instalador y gestor de dependencias.
- P1 VERIFICADO: 21/21 pruebas tests/*.sh PASS; controles de sintaxis, ShellCheck, compilación Python, install.sh --check y diff PASS.
- La clave maestra real no fue generada; no se modificaron datos operativos ni runtime.
- Siguiente: P2, almacén versionado de configuraciones y referencias.


### Actualización 2026-11-02 — P2 en curso

Se implementó inicialmente `scripts/vless_config_store.py` con esquema neutral VLESS versión 1, revisiones inmutables, publicación atómica de referencias bajo el bloqueo compartido y auditoría sin borrado automático. `tests/vless_config_store.sh` PASS. P2 no está completado: quedan pruebas de interrupciones/concurrencia, suite completa y auditoría final. No se activó runtime ni se creó la clave maestra real.

P2: `tests/*.sh` 25/25 PASS; pruebas específicas incluyen interrupción antes de publicar catálogo (huérfano detectable) y dos escritores concurrentes. `install.sh --check`, sintaxis, py_compile, ShellCheck, shfmt y diff PASS. El campo `secret_ref` queda reservado como null hasta P3.

### P3 — integración de persistencia segura VLESS (implementada y verificada)

Se integró guardado bajo confirmación desde el asistente, cifrado AES-256-GCM de claves privadas TLS/REALITY, referencias versionadas en catálogo/configuración y recuperación temporal para validación. Nuevo `scripts/vless_prepare_config.py`; `vless_config_store.py` ahora admite secretos cifrados y auditoría de blobs. El asistente deja de pasar la clave REALITY como `jq --arg` y usa `--rawfile`. Pruebas focales REALITY/TLS/recuperación PASS. Borradores no se activan. Suite completa `tests/*.sh` 25/25 PASS; `install.sh --check`, `bash -n`, `py_compile`, ShellCheck, shfmt y `git diff --check` PASS. Clave maestra real de VPS no generada. P3 aún no publicada en GitHub.

## 2026-11-02 — P4 backup/recuperación VLESS (COMPLETADA Y ACEPTADA)

Se corrigió la recuperación del journal para registrar si `connections/` y `secrets/` existían antes de restaurar, forzar `fsync` de directorios padres tras los renombrados y admitir journals legacy sin esos indicadores mediante inferencia conservadora. `tests/vless_backup_journal_crash_matrix.sh` valida 32 interrupciones abruptas, incluidas todas las fases y renombrados y las cuatro combinaciones de existencia previa. `tests/vless_backup_journal.sh` valida también journals legacy y destinos originalmente ausentes. `tests/vless_backup_restore_secrets.sh` confirma que la restauración funciona con el certificado TLS externo referenciado ausente, deja documentada la dependencia y no activa runtime. La suite completa final tras esta revisión registró 31/31 PASS; `install.sh --check`, sintaxis Bash, `py_compile`, ShellCheck, shfmt y `git diff --check` PASS. En la revisión inicial P4 seguía ABIERTA; esos puntos se corrigieron en la actualización posterior documentada abajo y recibieron aceptación formal del propietario el 2026-11-02. No se creó backup operativo ni se accedió a la clave maestra real. Publicado en GitHub: `90766d4cb8000ed1f94fb808b80f18483d5778cb` (árbol `cfdb26fd7716f622127ba5d7784884df58799b4c`); VPS sincronizada con `origin`. Consultar `docs/P4_BACKUP_RECUPERACION_VLESS.md`.


## Incidente de pruebas por EOF — 2026-11-02

- Se confirmó que la alerta de disco correspondió a un episodio real: `/tmp/tmp.oaFf5wTZwt/connections-action-error.out` alcanzó 20,465,770,496 bytes. Un proceso huérfano conservaba además un archivo borrado de aproximadamente 925 MB abierto.
- Se detuvo el proceso huérfano y se eliminó solo `/tmp/tmp.oaFf5wTZwt`; el filesystem quedó en 3.7 GB usados, 71 GB libres y 5% de uso. No se tocaron datos persistentes ni runtime.
- Causa: `ui_read_option()` ocultaba EOF como respuesta vacía; los menús con bucles repetían indefinidamente el mensaje de opción inválida. Se corrigió la propagación de EOF en los consumidores de menús y prompts.
- `tests/stage1_menu.sh` ahora verifica EOF en menús anidados y limita la salida de regresión a 1 MiB. Pruebas de menú Etapa 1, usuarios V2, preferencias, restore end-to-end TLS/REALITY, sintaxis Bash, ShellCheck y diff check: PASS.
- Se conservan sin borrar `/tmp/tmp.u7Vq57eHNx` (282 MB) y `/tmp/tmp.EsxO527Ihe` (47 MB), artefactos históricos de pruebas V2 con salida repetitiva por EOF.
- `tests/vless_backup_restore_secrets.sh` era un archivo local sin seguimiento Git; se revisó, ejecutó PASS y se incorpora al control de versiones.
- Publicado en GitHub: commit `fa7242a61248a71b64552511d1db932ebbc8d7d0` en `design/user-identity-association-v1`; árbol remoto `b03db9b450288eccbf61e761655f286763df3a70` idéntico al árbol del commit local `b520c53bd5a32007b30519e0756fce13fe8916b5`. La VPS no pudo actualizar refs mediante Git SSH/HTTPS; la referencia remota local quedó obsoleta y requiere reconciliación Git autenticada, sin repetir los cambios.

## 2026-11-02 — autenticación SSH y reconciliación de referencias

Se creó una clave SSH Ed25519 dedicada a este repositorio y se registró en GitHub como Deploy Key de solo lectura (sin permiso de escritura). La VPS autentica correctamente mediante el alias `github.com-xray-core-manager`; la URL `origin` de este checkout usa ese alias y los demás repositorios/configuraciones SSH no se modificaron. `git fetch` se completó correctamente. Se verificó que el árbol local anterior y el árbol remoto eran idénticos (`b6ed32ae1ff32dc4c8c6953a2d1eec48159b1d08`), por lo que se movió únicamente la referencia local de la rama con comprobación del SHA anterior, sin resetear ni sobrescribir archivos. Estado final: `design/user-identity-association-v1` y `origin/design/user-identity-association-v1` apuntan a `5ade7feda328ff4a4f6796fd7ab263237b40dbfa`; working tree limpio y sin divergencia. Las notas anteriores sobre falta de autenticación y refs obsoletas quedan superadas por esta verificación. La clave SSH anterior se conservó intacta. La Deploy Key nueva es de solo lectura; las publicaciones futuras deberán seguir usando el mecanismo autorizado de GitHub API u otro acceso de escritura expresamente configurado.


### Actualización P4 — límites agregados y validación bajo locks (2026-11-02)

Se corrigieron los dos hallazgos adicionales de auditoría. `scripts/vless_backup.py` limita a 512 MiB el contenido total sin comprimir en recolección, creación, verificación y extracción. La validación de payload verifica rutas relativas y traversal, archivos regulares, enlaces, duplicados, conteo, tamaño individual/agregado y hashes del manifiesto. `restore_data()` realiza verificación, lectura de clave, lectura final del archivo y extracción después de adquirir los locks; el hash se contrasta sobre los mismos bytes entregados al validador. Prueba focal `tests/vless_backup_limits.sh` PASS; suite completa posterior 32/32 PASS. El propietario aceptó formalmente estas correcciones el 2026-11-02; P4 queda COMPLETADA. No se creó backup operativo ni se accedió a la clave maestra real.


### Aceptación formal P4 — 2026-11-02

El propietario respondió afirmativamente a la solicitud de aceptación de las correcciones adicionales de límites agregados y TOCTOU. **P4 BACKUP/RECUPERACIÓN VLESS: COMPLETADA Y ACEPTADA.** Cierre respaldado por suite completa 32/32 PASS, `install.sh --check`, sintaxis Bash, `py_compile`, ShellCheck, shfmt y `git diff --check` satisfactorios; commit publicado y VPS sincronizada. El alcance excluye activar conexiones/runtime, reiniciar Xray, abrir puertos, cambiar firewall o desplegar certificados externos. No se creó backup operativo ni se leyó la clave maestra real durante estas pruebas.
