# Xray Core Manager — Estado del proyecto

**Corte de estado:** 2026-11-02 — Bloques 1, 2 y 3 implementados y verificados; publicación del Bloque 3 pendiente
**Estado global:** Etapa 1 aceptada por el propietario; Etapa 2 en desarrollo y abierta.
**Repositorio:** https://github.com/Jaok04/xray-core-manager
**Rama autorizada:** design/user-identity-association-v1
**VPS de desarrollo:** /opt/xray-manager

> Este documento es una fotografía de estado, no sustituye la documentación normativa. Antes de actuar, verifica el HEAD actual de GitHub y vuelve a inspeccionar la VPS.

> **Regla obligatoria permanente:** antes de implementar cualquier etapa o funcionalidad, contrastar el proyecto con la documentación preliminar aprobada en `/root/Xray_Manager_Documentacion_Final_2026-10-31`. Las mejoras requieren informe previo y autorización expresa del propietario. Ver `docs/REGLA_CONTRASTE_DOCUMENTACION_PRELIMINAR.md` y `AGENTS.md`.

> **Segunda regla obligatoria permanente:** ninguna etapa se declara TERMINADA/COMPLETADA sin auditoría integral y documentación técnica de todos sus puntos, subpuntos, módulos, submódulos y componentes internos, matriz de trazabilidad, pruebas y aceptación formal expresa. Cerrar un módulo no cierra su etapa. Ver `docs/REGLA_AUDITORIA_INTEGRAL_CIERRE_ETAPAS.md` y `AGENTS.md`.

## 1. Referencias oficiales

- Documentación normativa: /root/Xray_Manager_Documentacion_Final_2026-10-31
- Especificación funcional Etapa 2: 02_Protocolos_Conexiones/Etapa_2_Protocolos.md y Etapa_2_Protocolos.yaml.
- Código en VPS: /opt/xray-manager
- Rama autorizada: design/user-identity-association-v1
- main: no modificar.

## 2. Estado de repositorio y VPS

### GitHub

- Repositorio: Jaok04/xray-core-manager.
- Rama autorizada: design/user-identity-association-v1.
- Commit funcional de cierre VMess: `ab76a57032faa9793a62348f865fba2c9a7d8f77`.
- Corrección posterior Bloque 1 (restore VLESS preserva VMess): `c890b5b5362e17e439f198b9b8bbbdbe0af0c653` (`fix(vless): preserve current VMess entries on restore`), publicado y sincronizado en la rama autorizada.
- La rama main no se modificó.
- Verificar siempre el HEAD remoto antes de nuevas tareas.

### VPS

- Ruta: /opt/xray-manager.
- La ruta contiene un checkout Git válido.
- El remoto origin apunta al repositorio oficial mediante el alias SSH dedicado.
- La VPS tiene una Deploy Key SSH dedicada con `Allow write access`; el alias `github.com-xray-core-manager` se usa para fetch/push de este repositorio.
- Tras la publicación del cierre técnico y la actualización documental, HEAD local y `origin/design/user-identity-association-v1` se verificaron coincidentes y el árbol de trabajo quedó limpio.
- No se deben asumir estados históricos de sincronización: comprobar rama, HEAD, remoto, árbol y git status en cada sesión.

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
- Modelo neutral VLESS de nueve modalidades y adaptador Xray-core 26.10.31.
- VMess: modelo neutral, adaptador Xray-core 26.10.31, asistente, preparación segura, persistencia versionada cifrada y almacén aislado.
- VMess: 14 modalidades integradas en el catálogo, asistente y navegación; validación positiva y negativa.
- Prueba de integración VLESS para nueve modalidades y VMess para 14 modalidades.

### Límites importantes

- Las conexiones se guardan como draft; no equivalen a conexiones activas.
- La creación/edición no aplica una configuración al runtime.
- No se abren puertos ni se modifica firewall por el flujo de conexiones.
- El asistente VLESS ya está integrado con el modelo/adaptador para construir una previsualización temporal; cuando está disponible, incorpora usuarios VLESS en estado borrador.
- El asistente solicita opciones por modalidad y ejecuta xray run -test con el binario fijado si está disponible. Los archivos temporales se eliminan al terminar.
- La persistencia segura VLESS P1–P4 está implementada, verificada y aceptada; incluye almacenamiento versionado, cifrado de secretos y backup/recuperación. Consultar docs/DISEÑO_PERSISTENCIA_SEGURA_VLESS.md y docs/P4_BACKUP_RECUPERACION_VLESS.md.
- El asistente VLESS conserva el flujo de borrador/previsualización y no aplica runtime ni activa el servicio.
- La clave REALITY dejó de pasarse a jq mediante --arg; la integración usa lectura de archivo privado para evitar exposición en argumentos de proceso.
- La finalización de P4 no implica despliegue de certificados externos, activación runtime, puertos ni firewall.
- La validación xray run -test no prueba conectividad extremo a extremo.
- La prueba documentada de nueve modalidades corresponde al entorno y binario Xray 26.10.31; no asumir que se reejecutó en cada sesión.

### Pruebas registradas

Se documentan resultados PASS para navegación, administración de borradores, VLESS, colisiones de puertos, carreras de concurrencia, persistencia JSON, sintaxis Bash, ShellCheck y shfmt. La auditoría del 02/11 no reejecutó todas esas pruebas; consulta los informes y repítelas cuando el cambio lo requiera.

## 6. Decisiones complementarias aprobadas el 2026-11-02

- Se conservan las nueve modalidades VLESS del catálogo, incluidas XHTTP sin TLS, TLS y REALITY.
- El propietario aprobó el diseño técnico VMess y confirmó que VMess-HTTPUpgrade-TLS se implementará.
- La matriz VMess aprobada incluye 14 combinaciones, entre ellas HTTPUpgrade sin TLS y HTTPUpgrade-TLS. Las 14 pasan `xray run -test` con Xray-core 26.10.31.
- El adaptador VMess valida certificados y claves TLS PEM, verifica que correspondan criptográficamente y rechaza symlinks/archivos inválidos. Esta comprobación se añade porque `xray run -test` por sí solo no detecta un certificado PEM malformado.
- Las pruebas de navegación recorren las 14 combinaciones y las opciones de seguridad correspondientes.
- La especificación normativa 1.3 no se reescribió retroactivamente. Las decisiones y el diseño se registran en docs/DECISIONES_ETAPA_2.md y docs/DISEÑO_TECNICO_VMESS.md.
- El propietario autorizó expresamente la implementación VMess y, después, el aislamiento del almacén para mantener intacto P4 VLESS.

## 7. Pendientes principales de Etapa 2

- Resolver y formalizar las discrepancias normativas indicadas.
- VMess: auditoría técnica y pruebas de regresión completadas; pendiente aceptación formal del propietario.
- La restauración VLESS conserva las entradas VMess vigentes y su almacén aislado; el backup/restore VMess independiente requiere diseño y aprobación separados.
- Integrar usuarios VMess con asociaciones globales de Etapa 3 solo cuando se aborde esa integración conforme a su especificación.
- Definir e implementar modelos, generadores y validadores para Trojan, Shadowsocks e Hysteria2.
- Implementar administradores específicos SOCKS, HTTP Proxy y WireGuard.
- Integrar peers WireGuard con las identidades/asociaciones de Etapa 3.
- Diseñar aplicación transaccional de configuración, validación, verificación y rollback.
- Realizar pruebas de runtime e integración por modalidad y dependencias externas.
- Verificar compatibilidad real de plugins externos.

## 8. Reglas de estado

Usa siempre IMPLEMENTADO, VERIFICADO, PUBLICADO, SINCRONIZADO y ACEPTADO como estados separados, según AGENTS.md. Registra fecha, evidencia y entorno. No extrapoles un resultado de un entorno a otro.

## 9. Siguiente punto de control

Consultar `docs/PUNTO_CONTROL_ACTUAL.md`. El cierre técnico de VMess está publicado y sincronizado; esperar aceptación formal del propietario antes de declarar el módulo ACEPTADO o iniciar Trojan.
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


## 10. VMess — cierre técnico y aceptación pendiente (2026-11-02)

El módulo VMess está IMPLEMENTADO, VERIFICADO, PUBLICADO y SINCRONIZADO en la rama autorizada. La aceptación formal del propietario sigue pendiente.

- Matriz aprobada: 14/14 combinaciones.
- Xray-core 26.10.31: 14/14 configuraciones aceptadas mediante `xray run -test`.
- Navegación: prueba individual de las 14 combinaciones, incluidos los selectores de seguridad de gRPC, HTTPUpgrade, XHTTP y mKCP.
- Pruebas negativas: TLS ausente, symlink, PEM inválido, certificado/clave no coincidentes, campos de seguridad incompatibles, REALITY incompleto, short ID inválido y clave REALITY inválida.
- TLS: el adaptador valida PEM de certificado y clave privada, y compara sus claves públicas con la biblioteca `cryptography`. Xray `run -test` no basta para detectar por sí solo PEM inválido.
- Suite completa: 36/36 scripts PASS en la auditoría final.
- Estáticos: `bash -n`, `python3 -m py_compile scripts/*.py`, `install.sh --check`, ShellCheck warning, shfmt y `git diff --check`: PASS.
- Persistencia aislada: `/var/lib/xray-manager/vmess/configurations/` y `/var/lib/xray-manager/vmess/secrets/`; referencias `vmess_*`, sin reutilizar campos VLESS.
- P4 VLESS y sus archivos de implementación permanecen sin cambios.
- Backup/restore VMess queda como diseño independiente posterior; no bloquea el cierre técnico de este módulo salvo que la especificación normativa disponga lo contrario.
- Los usuarios VMess siguen siendo introducidos manualmente; la integración con identidades globales pertenece a Etapa 3.
- No se tocó runtime, firewall, puertos, certificados desplegados ni servicio. No se probó conectividad cliente-servidor.

Consultar `docs/DISEÑO_TECNICO_VMESS.md` y `docs/PUNTO_CONTROL_ACTUAL.md` para el detalle y el siguiente paso. Etapa 2 permanece abierta porque faltan Trojan, Shadowsocks, Hysteria2 y protocolos opcionales.


## 10. Corrección de restauración VLESS para preservar VMess — 2026-11-02

El propietario autorizó la protección de las entradas VMess actuales durante una restauración VLESS. `scripts/vless_backup.py` prepara el catálogo combinando las entradas VLESS del backup con las entradas VMess vigentes, bajo los bloqueos lifecycle/integrity. Valida catálogo, IDs, modalidad y referencias VMess; ante corrupción, referencias rotas, IDs duplicados o fallo de escritura staging, aborta antes de publicar. El almacén `/var/lib/xray-manager/vmess/` no se modifica y el backup VLESS no incorpora sus archivos.

Pruebas: nuevo `tests/vless_restore_preserves_vmess.sh` cubre VMess anteriores/posteriores al backup, referencias de configuración/secreto, integridad byte a byte del almacén, colisiones, catálogo corrupto, refs rotas y fallo de escritura. `tests/vless_backup_journal_crash_matrix.sh` conserva cobertura de 32 interrupciones con catálogo VMess válido. Suite completa: 37/37 scripts PASS. `python3 -m py_compile scripts/*.py`, `bash -n` de todos los scripts Bash, `install.sh --check`, ShellCheck warning de pruebas modificadas y `git diff --check`: PASS.

Estado del incremento: IMPLEMENTADO, VERIFICADO, PUBLICADO y SINCRONIZADO; aceptación formal específica pendiente. Commit: `c890b5b5362e17e439f198b9b8bbbdbe0af0c653`. P4 conserva su aceptación histórica para el alcance original; esta corrección posterior se registra por separado. No se creó backup operativo ni se accedió a la clave maestra real. No se modificaron runtime, servicio, firewall, puertos, certificados desplegados ni documentación normativa preliminar.


## 11. Bloque 2 — advertencias y resumen del asistente VMess — 2026-11-02

`modules/vmess_assistant.sh` muestra antes de solicitar parámetros el requisito de sincronización horaria VMess (desfase máximo 120 segundos). Añade advertencias específicas para WebSocket y HTTPUpgrade, sin retirar modalidades aprobadas. Tras `xray run -test` y antes del consentimiento de guardado, presenta un resumen de nombre/ID, dirección, puerto, modalidad, transporte/seguridad, usuarios y parámetros aplicables de transporte/TLS/REALITY. El contenido de claves privadas no se muestra; para TLS se muestra la ruta elegida, y para REALITY sólo la presencia del secreto y sus parámetros públicos.

Se corrigió además una colisión de nombre local en las funciones de lectura de parámetros que impedía asignar correctamente el target REALITY. La prueba `tests/vmess_assistant.sh` ahora verifica advertencias, resumen, orden resumen-antes-de-guardar y ausencia de material secreto TLS/REALITY en la salida.

Verificación focal: `tests/vmess_assistant.sh`, `tests/vmess_model.sh`, `tests/xray_vmess_integration.sh` (14/14 combinaciones y negativos) y `tests/stage2_navigation.sh` (14/14): PASS. `bash -n` y ShellCheck warning de archivos modificados: PASS. Suite completa posterior al Bloque 2 queda pendiente del Bloque 3. Estado: IMPLEMENTADO, VERIFICADO, PUBLICADO y SINCRONIZADO; commit `9d03d4b4e77e1a160b94ee2c2f3c74487977e362`. VMess sigue sin aceptación formal.


## 12. Bloque 3 — cobertura de pruebas VMess — 2026-11-02

Se amplió `tests/vmess_assistant.sh` para comprobar cancelación/EOF en dirección, UUID y path; slots inválidos; UUID inválido y duplicado; puerto fuera de rango; modalidad incompatible; y EOF en el consentimiento después del resumen. Los intentos inválidos o cancelados no deben modificar el catálogo. Se conservan las comprobaciones de resumen previo al consentimiento y ocultamiento de material TLS/REALITY.

Se creó `tests/vmess_persistence_hardening.sh`, que cubre store/read TLS AES-256-GCM, AAD, permisos, clave maestra ausente (read no la regenera), clave inválida (read/store fallan antes de publicar), ciphertext/tag alterado (sin plaintext), referencias de configuración/secreto rotas, archivos huérfanos, symlinks, fallo después de escribir archivos y antes de publicar catálogo, auditoría sin borrado automático, dos escritores concurrentes sobre IDs distintos y dos escrituras concurrentes sobre el mismo ID con revisiones r1/r2.

El fallo inyectado en la publicación del catálogo deja los archivos de configuración/secreto como huérfanos detectables; el catálogo permanece intacto. Esto es coherente con el diseño aprobado, que no ofrece rollback transaccional para VMess y exige detección sin borrado automático. No se cambió producción en este bloque; sólo cobertura de pruebas.

Verificación integral posterior: `tests/*.sh` 38/38 PASS; `python3 -m py_compile scripts/*.py`; `bash -n` de todos los scripts Bash; `install.sh --check`; ShellCheck (`-S warning`) sobre archivos modificados; `git diff --check`: PASS. Estado: IMPLEMENTADO, VERIFICADO, PUBLICADO y SINCRONIZADO; commit `08b2044dd820eb465afecbb6ec66fccefe6397a5`. VMess sigue pendiente de aceptación formal.


## 13. Bloque 4 — etiquetas de modalidades y criterio shfmt — 2026-11-02

Se corrigieron las etiquetas visibles del menú VMess y de los listados que usan `connections_mode_label`: `VMess-WS (sin TLS adicional)` y `VMess-TLS (RAW/TCP + TLS)`. Los identificadores `vmess_ws` y `vmess_tcp_tls`, el orden del menú y las 14 modalidades permanecen intactos. `tests/stage2_navigation.sh` comprueba ambos textos en el menú y en la función de etiquetas, además de mantener la navegación de las 14 combinaciones.

Criterio de formato: `README.md` documenta `shfmt -d -i 4 -ci` para archivos Bash seleccionados. Se inspeccionó el formato existente y se compararon las diferencias que `shfmt` produciría en módulos VMess. No existe una regla que autorice reformatear todo el árbol y el cambio produciría diffs de estilo fuera del alcance; por tanto, no se reformateó ningún archivo. El criterio del proyecto se mantiene: aplicar shfmt con `-i 4 -ci` sólo a los archivos incluidos explícitamente en las verificaciones de README, sin ampliar automáticamente el conjunto.

Estado Bloque 4: etiquetas IMPLEMENTADAS y VERIFICADAS mediante pruebas focales y suite completa; PUBLICACIÓN/SINCRONIZACIÓN pendiente. Auditoría integral de VMess pendiente. No se cierra VMess ni Etapa 2.
