# Punto de control vigente — corrección del reporte de instalación Xray-core (2026-11-07)

**Estado:** corrección IMPLEMENTADA, VERIFICADA y PUBLICADA en GitHub; NO desplegada en VPS de pruebas.
**Rama:** `design/user-identity-association-v1`; commit publicado `1c0604975f807ade714d837ab49d71e2e4db517f`; HEAD local/remoto verificado.

- Se corrigió `modules/xray_admin.sh`: el menú captura el código original de instalación, muestra error explícito y lo conserva después de `ui_pause`.
- Regresión añadida en `tests/xray_admin.sh` para un fallo simulado código 37.
- Verificación: Bash 62/62, Python 406/406, `bash -n` global, compileall, ShellCheck `-S error`, `install.sh --check` y `git diff --check` PASS.
- Contraste normativo Etapas 1 y 6 realizado; `Xray-Normativa/` sin cambios.
- La causa interna del primer fallo real sigue desconocida: no se capturó su código ni su salida completa.
- No se repitió instalación en VPS Pruebas ni se modificó sistema/runtime. Commit/push sólo en la rama autorizada.

**Siguiente paso permitido:** revisar el diff/documentación de esta corrección. Para reintentar la instalación real en VPS Pruebas se requiere autorización específica; antes se debe capturar la salida completa y código de la operación para determinar la causa original. La publicación en GitHub está completada; cualquier despliegue o instalación real en VPS Pruebas requiere autorización específica.

---

# Punto de control vigente — instalador autónomo GitHub (2026-11-06)

**Estado:** IMPLEMENTADO Y VERIFICADO EN PRUEBAS AUTOMATIZADAS; validación remota real con PAT pendiente.
**Rama:** `design/user-identity-association-v1`.
**Commit de implementación:** `8d76275b6bfb1eeda5eaa859b45f979804784094`; la actualización documental de continuidad se registra en el commit siguiente. La sincronización final se verifica después del push.

- El instalador admite un único `install.sh`, autenticación Fine-grained PAT `Contents: Read-only`, descarga por commit SHA y verificación de helper/árbol Git.
- Archivos principales: `install.sh`, `scripts/installer_bootstrap.py`, `tests/test_installer_bootstrap.py`.
- Procedimiento: `docs/INSTALACION_DESDE_VPS_LIMPIA.md`.
- Pruebas: focal 18/18; Python global 406/406; Bash 62/62; ShellCheck `-S error`, compileall, bash -n, `install.sh --check` y diff-check PASS.
- No se probó GitHub con el PAT real ni instalación desde archivo único en la VPS nueva. El propietario debe ejecutar el procedimiento documentado y compartir salida sin secretos.
- `--install` sigue Manager-only; `--with-xray` sigue opcional y explícito. No hay autorización implícita para iniciar servicio, modificar DNS, firewall, puertos, certificados o runtime.
- H6-G2 continúa abierto; H6-G3 no tiene auditoría independiente. `main` y `Xray-Normativa/` permanecen intactas.

## Punto de control anterior — H6-G3 y backend runtime


> CORTE VIGENTE — 2026-11-06: H6-E1/E2/E3 implementadas; auditoría integral H6-E PASS CON LIMITACIONES. Instalador predeterminado Manager-only. H6-F NO LISTO END-TO-END. Rama design/user-identity-association-v1; HEAD base local/remoto antes de los cambios: 32496d749901d34cd1a60f720843901125b536b6. Implementación publicada en 4984ce207ff446bb097cc53c6445ad1e9b53c585 y actualización documental en 537fb5475ce6bfcbba8401a1fced1642ca203cba; HEAD local/remoto: 537fb5475ce6bfcbba8401a1fced1642ca203cba, árbol limpio. main y Xray-Normativa/ protegidas.

## Estado operativo vigente

- H6-E2: inspector read-only de PID/starttime, UID/GID efectivos, ejecutable, argv y hash.
- H6-E3: correlación H6-A/H6-E2 con MainPID, InvocationID y ActiveEnterTimestamp; gate R-05 y atestación schema v2.
- H6-E4: auditoría integral del conjunto H6-E documentada en docs/AUDITORIA_H6E_INTEGRAL_2026-11-06.md, PASS CON LIMITACIONES.
- Python 332/332 y Bash 62/62 PASS; ShellCheck, compileall, bash -n, install.sh --check y diff-check PASS.
- install.sh --install despliega sólo Xray Core Manager. install.sh --install --with-xray conserva la instalación integral explícita. Xray-core puede instalarse después desde el menú.
- No hay backend mutador runtime live ni selector en CLI/menú. No se ha probado systemd/proceso Xray real, configuración realmente cargada, WAN ni cliente externo.
- H6-F no está listo end-to-end: Certbot/ACME requiere decisión y autorización; falta confirmar endpoint público y parámetros Host/SNI; se requiere VPS de aceptación separada y autorización específica para operaciones live.

Los apartados cronológicos siguientes se conservan como historial. Este bloque prevalece ante contradicciones.

> Registro histórico del punto de control B3 (2026-11-05). El corte vigente es el bloque 2026-11-06 del encabezado; los estados anteriores se conservan por trazabilidad.

**Fecha del corte:** 2026-11-05
**Siguiente tarea:** realizar el contraste documental preliminar del siguiente bloque del plan MVP y definir su alcance antes de cualquier edición. No ejecutar operaciones live por inferencia.
**Estado vigente:** I-01–I-04 y B1-A/B1-B aceptados, publicados y sincronizados en design/user-identity-association-v1. Commit funcional B1 c8cd20c2a576fb1926fdcf11945cd75cf1c4211c. HEAD local/remoto verificado tras push; árbol limpio tras actualización documental. Etapas 2, 3 y 5 ABIERTAS. R-06/live NO AUTORIZADA.


> Registro histórico del punto de control R-04 (2026-11-04). El punto vigente es el bloque B1-A/B1-B al final de este documento.

**Fecha del corte:** 2026-11-04
**Siguiente tarea tras revisión/aceptación formal:** R-05 — orquestación systemd simulada. R-02/R-03/R-04 implementadas y verificadas localmente; sin commit/push.
**Estado vigente:** I-01–I-04 y B1-A/B1-B aceptados, publicados y sincronizados en design/user-identity-association-v1. Commit funcional B1 c8cd20c2a576fb1926fdcf11945cd75cf1c4211c. HEAD local/remoto verificado tras push; árbol limpio tras actualización documental. Etapas 2, 3 y 5 ABIERTAS. R-06/live NO AUTORIZADA.

**Regla de cierre de etapas:** Etapa 2 permanece ABIERTA aunque VMess esté técnicamente listo. No se podrá declarar completada hasta auditar y documentar todos los puntos, subpuntos, protocolos, modalidades, flujos, módulos y componentes internos definidos por la línea base aprobada, ejecutar la regresión integral y obtener aceptación formal del propietario. Aplicar `docs/REGLA_AUDITORIA_INTEGRAL_CIERRE_ETAPAS.md`.

## Punto de control vigente — B3 (2026-11-05)

**Siguiente tarea:** realizar contraste documental read-only del siguiente bloque del MVP; presentar alcance y discrepancias antes de solicitar autorización para cualquier implementación.

**Estado:** B3 IMPLEMENTADA, VERIFICADA, AUDITADA, ACEPTADA FORMALMENTE, PUBLICADA y SINCRONIZADA el 2026-11-05. HEAD local/upstream/remoto: `9f4cc18d856ec0ccb31951f343a1fd3e870a0684`; checkout limpio.

- Menú contextual en conexión VLESS-WS-TLS draft para asociar identidad existente o crear identidad global y asociarla.
- Exportador exige Xray PASS en manifiesto de revisión exacta.
- SAN DNS del certificado activo debe cubrir SNI configurado o endpoint DNS cuando SNI no está configurado; endpoint IP sin SNI DNS verificable se rechaza.
- Integración compone, valida con Xray 26.10.31 y exporta URI fixture.
- Python 186/186; Bash 61/61; compileall, bash -n, ShellCheck -S error, git diff --check e install.sh --check PASS.
- Sin NetMod real, WAN, ACME real, runtime, systemd, DNS, firewall, puertos, red, dependencias nuevas, clave maestra real ni VPS de pruebas.
- main y Xray-Normativa/ intactas. R-06/live NO AUTORIZADA.
- Documentación B3: decisión, implementación y auditoría en los tres archivos docs/*B3*2026-11-05.md indicados en PROJECT_STATE.md.

## 1. Entorno verificado

- Repositorio: `Jaok04/xray-core-manager`.
- Rama autorizada: `design/user-identity-association-v1`.
- Proyecto VPS: `/opt/xray-manager`.
- HEAD de partida de la auditoría histórica: df632aee5d8139c721b81a6d65f14d93f7676226; bloque correctivo y continuidad publicados hasta `4c87557e0aff4166c540c633effe5cb6dac40096`. Revalidación actual ejecutada sobre ese HEAD.
- Commit Bloque 1: `c890b5b5362e17e439f198b9b8bbbdbe0af0c653` (`fix(vless): preserve current VMess entries on restore`), publicado y sincronizado.
- Remoto: `git@github.com-xray-core-manager:Jaok04/xray-core-manager.git`.
- Deploy Key SSH dedicada con permiso de escritura configurado.
- Documentación normativa canónica: `Xray-Normativa/` (versionada en GitHub y presente en `/opt/xray-manager`).
- Respaldo original en la VPS: `/root/Xray_Manager_Documentacion_Final_2026-10-31`; comparar hashes con la copia versionada.
- Etapa 1: aceptada formalmente.
- Etapa 2: abierta.
- P4 backup/restore VLESS: alcance original completado y aceptado; corrección posterior de preservación VMess implementada y verificada, aceptación específica pendiente.

## 2. Alcance VMess contrastado

Diseño técnico aprobado: `docs/DISEÑO_TECNICO_VMESS.md`. Matriz cerrada de 14 combinaciones:

- WS sin TLS adicional.
- RAW/TCP TLS.
- WS-TLS.
- RAW/TCP REALITY.
- gRPC sin TLS, TLS y REALITY.
- HTTPUpgrade sin TLS y TLS.
- XHTTP sin TLS, TLS y REALITY.
- mKCP sin TLS y TLS.

Se conserva la distinción de la especificación normativa Etapa 2 revisión 1.3 y las decisiones complementarias aprobadas. No se reescribió la documentación normativa.

## 3. Implementación y verificaciones

- Modelo neutral, adaptador Xray 26.10.31, asistente, preparación segura y persistencia versionada cifrada implementados.
- Almacén VMess aislado en `/var/lib/xray-manager/vmess/configurations/` y `/var/lib/xray-manager/vmess/secrets/`.
- El catálogo compartido usa únicamente las referencias VMess `vmess_configuration_ref`, `vmess_secret_ref`, `vmess_configuration_revision` y `vmess_configuration_schema_version`.
- Xray-core 26.10.31, binario `/var/cache/xray-manager/validation/v26.10.31/xray`, versión `a4a3dff`: 14/14 modalidades aceptadas por `xray run -test`.
- Adaptador TLS reforzado: valida certificado PEM, clave privada PEM y correspondencia de claves públicas mediante `cryptography`; rechaza symlinks y archivos no regulares.
- Casos negativos: TLS sin clave, symlink de clave, PEM inválido, certificado/clave no coincidentes, REALITY sin clave, short ID inválido, clave REALITY inválida, campos TLS en modalidad sin TLS, campos de transporte desconocidos y modelo/seguridad inconsistentes: PASS.
- Navegación: 14/14 combinaciones VMess resueltas individualmente por el menú.
- Suites históricas anteriores: 36/36, 38/38, 38/38 y 39/39 PASS. Revalidación actual: `tests/*.sh` 40/40 PASS, incluida `tests/vmess_navigation_edge_cases.sh`.
- Controles estáticos históricos: `bash -n`, `python3 -m py_compile scripts/*.py`, `./install.sh --check`, ShellCheck y `git diff --check`: PASS. La revalidación actual también pasó ShellCheck y `shfmt -d -i 4 -ci` para la nueva prueba focal.

## 4. Límites que no bloquean el cierre de VMess

- `xray run -test` valida estructura y configuración; no demuestra conectividad extremo a extremo.
- VM-47 sí se verificó en loopback local; no se probó cliente externo/WAN. El diseño VMess §8 no convierte una prueba WAN en requisito de aceptación.
- No se activaron borradores ni se modificó configuración activa, runtime, servicio, firewall o puertos.
- Usuarios VMess se introducen manualmente; integración con identidades globales corresponde a Etapa 3 (VM-43).
- El almacén VMess no promete rollback transaccional multiarchivo; VM-32 se verifica a nivel de archivo/catálogo y VM-33 no aplica como requisito del diseño aprobado.
- Backup/restore VMess independiente no está implementado y requiere diseño y autorización separados; VM-42 está fuera del alcance aprobado.
- La restauración VLESS combina las entradas VLESS del backup con las entradas VMess vigentes, valida sus referencias y conserva sin cambios el almacén VMess.
- El backup VLESS sigue sin incluir configuraciones ni secretos VMess. Backup/restore VMess independiente queda fuera de alcance.

## 5. Archivos modificados en el cierre técnico VMess

- `modules/vmess_xray_26_10_31.sh`: validación criptográfica del certificado y clave TLS.
- `tests/xray_vmess_integration.sh`: cobertura negativa TLS/REALITY/transporte.
- `tests/stage2_navigation.sh`: recorrido de las 14 combinaciones VMess.
- `docs/DISEÑO_TECNICO_VMESS.md`: comportamiento y criterios de prueba actualizados.
- `PROJECT_STATE.md`, este documento, `docs/CONTINUIDAD_DEL_PROYECTO.md` y `HISTORY.md`: continuidad y trazabilidad.

## 6. Estado separado

| Estado | Resultado |
|---|---|
| IMPLEMENTADO | Sí — base VMess y correcciones F-01 a F-05 implementadas/verificadas |
| VERIFICADO | Suite 40/40 PASS; Xray 14/14 y 16 negativos PASS; VM-28 y VM-38/39/40 PASS; VM-46 live PASS; VM-47 loopback PASS; VM-32 con límite multiarchivo documentado |
| PUBLICADO | Base y pruebas anteriores publicadas; este informe y la validación live se incluyen en la actualización de la rama autorizada |
| SINCRONIZADO | Actualización live documentada y sincronizada en `design/user-identity-association-v1`; `main` intacta |
| ACEPTADO | PENDIENTE — requiere decisión expresa del propietario; cliente externo/WAN no probado y no requerido por el diseño |

## 7. Siguiente acción

La revalidación técnica de VMess está preparada para aceptación. Siguiente acción: el propietario revisa el expediente y decide expresamente si acepta VMess. La prueba externa/WAN es opcional y requeriría autorización separada; no es un bloqueo del alcance aprobado. No iniciar Trojan hasta recibir aceptación formal de VMess y efectuar el contraste específico de Trojan.

No modificar `main`. No ampliar la corrección P4 más allá de la preservación VMess aprobada. No tocar runtime, firewall, puertos, certificados desplegados ni servicio.


## 8. Bloque 1 — protección VMess durante restauración VLESS

**Estado:** IMPLEMENTADO, VERIFICADO, PUBLICADO y SINCRONIZADO; aceptación formal específica pendiente. Commit `c890b5b5362e17e439f198b9b8bbbdbe0af0c653`.

- `scripts/vless_backup.py`: antes de crear journal o publicar, el catálogo staging se combina con entradas VMess actuales. Se ignoran entradas VMess antiguas del snapshot, se conservan las actuales y sus refs `vmess_*`, se valida la estructura y existencia de archivos referenciados, se rechazan colisiones de IDs y protocolos no cubiertos y se verifica la escritura staging.
- Los almacenes VMess (`vmess/configurations` y `vmess/secrets`) no se modifican ni se incorporan al backup VLESS.
- `tests/vless_restore_preserves_vmess.sh`: cubre VMess anteriores/posteriores al backup, referencias de configuración y secreto, integridad del almacén, colisión de IDs, catálogo corrupto, refs rotas y fallo de escritura sin modificación del catálogo activo.
- `tests/vless_backup_journal_crash_matrix.sh`: fixtures actualizados para usar un catálogo VMess válido; 32 escenarios de interrupción/rollback PASS.
- Suite completa: 38/38 scripts PASS. Sintaxis Bash/Python, `install.sh --check`, ShellCheck sobre pruebas modificadas y `git diff --check`: PASS.
- No se creó backup operativo ni se leyó/creó la clave maestra real.

## 9. Siguiente acción permitida

Presentar F-01 a F-04 al propietario para autorización de corrección y decisión sobre la semántica de cancelación. F-05 requiere autorización para una validación live en entorno controlado. No tocar código, almacén/clave real, runtime, firewall, puertos, certificados desplegados ni servicio hasta contar con autorización para el alcance concreto.


## 10. Bloque 2 — advertencias y resumen del asistente VMess

**Estado:** IMPLEMENTADO, VERIFICADO, PUBLICADO y SINCRONIZADO; commit `9d03d4b4e77e1a160b94ee2c2f3c74487977e362`.

- Aviso operativo antes de pedir parámetros: sincronización de relojes cliente/servidor, desfase máximo 120 segundos.
- Advertencia WebSocket: Xray 26.10.31 lo marca obsoleto/no recomendado y recomienda XHTTP H2/H3; se conserva por alcance aprobado.
- Advertencia HTTPUpgrade: Xray 26.10.31 lo marca obsoleto/no recomendado, podría retirarlo y recomienda migrar a XHTTP H2/H3; también puede presentar patrones identificables. Se conserva por alcance aprobado.
- Resumen tras `xray run -test` y antes del consentimiento: nombre/ID, dirección, puerto, modalidad, transporte/seguridad, usuarios, path/host/service/mode/header/seed y parámetros TLS/REALITY aplicables. No muestra contenido de claves privadas.
- Se corrigió la asignación de `target` REALITY: el parámetro local de las funciones de lectura ya no oculta la variable destino del llamador.
- `tests/vmess_assistant.sh` valida los avisos, los campos del resumen, el orden resumen→consentimiento y que no se revele material TLS/REALITY. `tests/vmess_assistant.sh`, `tests/vmess_model.sh`, `tests/xray_vmess_integration.sh` y `tests/stage2_navigation.sh`: PASS.
- `bash -n` y ShellCheck warning de los dos archivos modificados: PASS. Suite completa posterior se ejecutará en Bloque 3.


## 11. Bloque 3 — cobertura integral de pruebas VMess

**Estado:** IMPLEMENTADO, VERIFICADO, PUBLICADO y SINCRONIZADO; commit `08b2044dd820eb465afecbb6ec66fccefe6397a5`.

- `tests/vmess_assistant.sh`: añade EOF/cancelación en distintos puntos, slots inválidos, UUID inválido/duplicado, puerto fuera de rango, modalidad incompatible y EOF al confirmar; comprueba que los flujos fallidos/cancelados no cambian el catálogo.
- `tests/vmess_persistence_hardening.sh`: clave maestra ausente/inválida, ciphertext/tag alterado, ausencia de plaintext ante error, refs de configuración/secreto rotas, huérfanos, symlinks, permisos, fallo de publicación del catálogo, detección de huérfanos sin borrado automático y concurrencia (IDs distintos y misma conexión r1/r2).
- El fallo inyectado entre escritura de archivos y publicación de catálogo deja huérfanos detectables, sin cambiar el catálogo. Es el comportamiento previsto: VMess no ofrece rollback transaccional y la auditoría no borra automáticamente.
- Suite completa: 38/38 scripts PASS. `python3 -m py_compile scripts/*.py`, `bash -n` de todos los scripts Bash, `install.sh --check`, ShellCheck warning de los archivos modificados y `git diff --check`: PASS.
- No se modificó código de producción en este bloque. No se accedió a la clave maestra real ni se tocó runtime.


## 12. Bloque 4 — etiquetas explícitas VMess y formato

**Estado:** etiquetas IMPLEMENTADAS, VERIFICADAS, PUBLICADAS y SINCRONIZADAS; commit `9528f4b00f6b9654f7236050bbadfd8f9415bf69`. Auditoría integral pendiente.

- Menú y listados: `VMess-WS (sin TLS adicional)` y `VMess-TLS (RAW/TCP + TLS)`.
- IDs, modalidades y navegación sin cambios: `vmess_ws`, `vmess_tcp_tls`; matriz 14/14 preservada.
- `tests/stage2_navigation.sh` añade comprobaciones de ambas etiquetas tanto en menú como en función de listado.
- `README.md` documenta `shfmt -d -i 4 -ci` para archivos seleccionados. Se inspeccionaron las convenciones existentes y el diff potencial; no se reformatearon archivos ni se amplió el alcance de formato.
- Pruebas focales y suite completa 38/38 PASS; controles estáticos y shfmt baseline PASS. Cambios publicados y sincronizados. Pendiente: auditoría integral documentada de VMess.


## 12. Revalidación controlada VMess — 2026-11-02

La VPS de desarrollo se confirmó accesible como root; rama `design/user-identity-association-v1`, HEAD de partida `4c87557e0aff4166c540c633effe5cb6dac40096`. Se agregó `tests/vmess_navigation_edge_cases.sh`, con VM-38/39/40 focales PASS. Suite completa `tests/*.sh`: 40/40 PASS. `port_collisions.sh` falló en UDP durante una primera ejecución aislada dentro de la suite parcial; repetición aislada y suite completa posterior pasaron.

Preflight live de la VPS de desarrollo: `/etc/xray-manager/keys/master.key` y `/var/lib/xray-manager/vmess/` no existen; catálogo de conexiones válido y vacío; servicio Xray inactivo. F-05 no se ejecutó: no se creó clave maestra real, almacén VMess live ni conexión persistente. Xray no está instalado localmente; la integración usó binario de validación en caché. Servicio inactivo; sin cambios de runtime, firewall, puertos o servicios. VM-47 conectividad real no verificada.


## 13. Validación live F-05 — 2026-11-02

Autorización del propietario ejecutada en la VPS de desarrollo. Preflight: catálogo vacío, sin entradas/datos VLESS persistidos y sin clave maestra previa; servicio Xray inactivo. Se creó un borrador `vmess_tcp_tls` temporal mediante el flujo real; Xray 26.10.31 aceptó el borrador. Store generó clave maestra compartida (32 bytes, `root:root 0600`) y almacén VMess (directorios `root:root 0700`), persistió config y secreto AES-256-GCM. Read recuperó el secreto byte a byte; el recuperador real reconstruyó la configuración y Xray volvió a validarla. Audit live limpio. El ciphertext alterado fue rechazado sin producir plaintext.

Se eliminó el borrador temporal y sus dos archivos versionados; auditoría posterior limpia y catálogo vacío. Se conservaron intencionalmente la clave maestra compartida y los directorios VMess vacíos. Certificado/clave temporal y outputs de prueba se retiraron. Servicio Xray continuó `inactive`; puerto de prueba sin escucha; runtime/firewall/puertos/servicios intactos. F-05/VM-46: VERIFICADO LIVE. VM-47 conectividad cliente-servidor: NO VERIFICADO. Evidencia completa: `docs/VALIDACION_LIVE_VMESS_F05_2026-11-02.md`.


## 14. Validación cliente-servidor VM-47 — 2026-11-02

VM-47: PASS en loopback local con dos procesos Xray 26.10.31. El modelo y adaptador reales generaron el servidor VMess-TLS; el cliente SOCKS estableció el túnel, el servidor aceptó el usuario sintético y el destino HTTP respondió 200 con el marcador esperado. Configuraciones cliente/servidor pasaron `xray run -test`. Listeners y procesos temporales detenidos. Sin cambios en runtime, firewall, puertos públicos, catálogo o servicio. No se probó cliente externo/WAN. Evidencia: `docs/VALIDACION_CLIENTE_SERVIDOR_VMESS_VM47_2026-11-02.md`.


## 10. Revalidación de preparación para aceptación — 2026-11-03

Se reejecutó en la VPS `/opt/xray-manager`: suite completa 40/40 PASS; Xray-core 26.10.31 14/14 combinaciones y 16/16 negativos PASS; `bash -n` de módulos/pruebas VMess; `py_compile` de los dos scripts Python VMess; ShellCheck de módulos/pruebas VMess y `git diff --check`: PASS.

Se documentaron sólo tres variables globales intencionales consumidas por funciones de `modules/connections.sh` cargado con `source`, mediante supresión local SC2034; se conservaron las asignaciones necesarias. No se modificó código de producción ni normativa. VM-28 pasa a VERIFICADO por evidencia de versionado, referencias separadas, coherencia y concurrencia r1/r2. VM-32 se precisa como atomicidad individual y concurrencia con límite multiarchivo documentado; VM-33 no aplica porque el diseño no promete rollback transaccional.

VM-47 sigue probado en loopback local; WAN no probado y no requerido por el diseño. VMess queda listo para decisión formal del propietario (VM-48). Etapa 2 permanece ABIERTA.


## 15. Nuevo punto de control — certificados TLS centralizados (2026-11-03)

**Decisión del propietario:** APROBADO el modelo centralizado. Las conexiones VMess/VLESS usarán `certificate_id`; la clave privada se conservará una sola vez, cifrada en el almacén central; `managed` y `reference` tendrán semántica diferenciada; un resolutor autorizado preparará los archivos para Xray; REALITY queda separado.

**Documento contractual:** `docs/ARQUITECTURA_CERTIFICADOS_CENTRALIZADOS.md` (versión 1.0, diseño documentado, revisión técnica pendiente).

**Estado de esta entrega:**
- Contrato arquitectónico: DOCUMENTADO.
- Código: SIN CAMBIOS por esta iniciativa.
- Pruebas de implementación: NO EJECUTADAS / aún no aplicables.
- Normativa `Xray-Normativa/`: SIN CAMBIOS.
- VPS `Vps de Pruebas`, runtime, servicio, firewall, puertos y certificados desplegados: SIN CAMBIOS.
- Publicación GitHub: PENDIENTE en esta entrega.
- Aceptación de implementación: PENDIENTE.

**Siguiente paso permitido:** inspección técnica read-only de `scripts/vmess_config_store.py`, `scripts/vless_config_store.py`, módulos crypto, generadores, backups, `config/paths.sh`, unidad systemd y permisos de la VPS de desarrollo. Cerrar las decisiones abiertas de §14 del contrato antes de crear el almacén central. No migrar datos reales ni tocar runtime.

La Etapa 4 normativa permanece funcionalmente NO IMPLEMENTADA en su conjunto. Este contrato no constituye cierre de Etapa 4 ni aceptación de una funcionalidad operativa.


## 16. Primer bloque de almacén central TLS — 2026-11-03

Estado: catálogo y cifrado central IMPLEMENTADOS PARCIALMENTE; pruebas PASS. Aceptación global pendiente.

- Archivos: scripts/certificate_crypto.py, scripts/certificate_store.py, config/paths.sh, tests/certificate_store.sh.
- CLI: import, list, show, audit.
- Contrato criptográfico: AES-256-GCM; AAD xray-manager:certificate-secret:v1:<certificate_id>:<revision>; clave maestra común existente sólo lectura.
- Pruebas: focal tests/certificate_store.sh PASS; suite completa 41/41 PASS; bash -n, py_compile, ShellCheck de prueba nueva y git diff --check PASS.
- No se importaron certificados reales; fixtures temporales solamente.
- No se modificaron asistentes, generadores, modelos, stores históricos VMess/VLESS ni backup/restore. No hay resolutor ni migración.
- El servicio Xray no está instalado en la VPS de desarrollo; identidad y permisos de runtime quedan pendientes. No tocar VPS Vps de Pruebas.
- Informe: docs/IMPLEMENTACION_ALMACEN_CERTIFICADOS_CENTRALIZADOS.md.

Siguiente paso: revisión de seguridad del almacén y diseño/implementación del resolutor TLS sin integración runtime; después integrar VMess y VLESS por separado. Mantener intactos secretos históricos y REALITY.


## 17. Publicación y sincronización del bloque TLS — 2026-11-03

- Implementación y documentación publicadas en la rama autorizada.
- HEAD local: 6d35b0dde502db66d9826bc4fb67e8500b6b4561.
- HEAD remoto consultado directamente y origin/design/user-identity-association-v1 tras fetch: mismo SHA.
- Rama main: 656ecedc506a94a6461aee296b20871d51a38bf3; no modificada.
- El diff de Xray-Normativa desde el HEAD de partida no contiene cambios. SHA-256 de la especificación Etapa 4: Markdown f6cb3ecfa2a09c50009d07fe511227973f13db62b51c9ced06efc498797e7cba; YAML f0947cb3af935d58035341e257ce6d5565b044aa97857b5a49b34168565b3dd5.
- El checkout versionado coincide con la rama remota. Permanece el directorio preexistente y no seguido scripts/__pycache__; no se eliminó ni incorporó al commit.


## 18. Segundo bloque — resolutor TLS parcial (2026-11-03)

Este punto sustituye el siguiente paso anterior de diseño del resolutor, pero no cierra la integración.

- Nuevo: scripts/certificate_resolver.py; prueba: tests/certificate_resolver.sh.
- Verifica asociación exacta conexión/certificado, modalidad TLS, referencias/revisiones, integridad AES-GCM, par criptográfico, huellas y vigencia.
- Admite recursos managed/reference y prepara lease temporal con archivos root:<grupo-servicio> 0640 y directorios 0750. La limpieza comprueba manifest y permisos antes de borrar sólo el lease.
- CLI consulta identidad efectiva systemd; sin User/Group explícitos falla cerrada. En VPS desarrollo no hay xray.service ni usuario/grupo xray. Prueba API con UID/GID sintético 1 no demuestra lectura real por Xray.
- Suite completa 42/42 PASS; bash -n, py_compile, ShellCheck de ambas pruebas y git diff --check PASS.
- Limitación bloqueante para integración: vmess_config_store.py y vless_config_store.py, asistentes y generadores aún rechazan/no emiten el contrato TLS central certificate_id. Las pruebas del resolutor usan fixtures.
- No hay runtime apply ni reinicio; VPS Vps de Pruebas y Xray-Normativa intactas.
- Informe: docs/IMPLEMENTACION_RESOLUTOR_CERTIFICADOS_TLS.md.

Siguiente paso: integrar el nuevo contrato de forma versionada en VMess, primero store y generador, sin tocar los secretos históricos ni runtime. Después VLESS en un bloque separado y con regresión cruzada.


## 10. Bloque 3 — integración VMess TLS centralizado (avance intermedio, 2026-11-03)

- Estado: PARCIAL; persistencia central y preparación TLS implementadas con pruebas focales. No equivale a integración completa ni aceptación.
- Nuevas configuraciones VMess TLS usan `certificate_id` y no almacenan una clave privada cifrada por conexión. El certificado debe existir y estar activo en el catálogo central.
- REALITY mantiene el secreto cifrado individual. Las configuraciones TLS históricas continúan siendo legibles; no se migran ni eliminan automáticamente.
- Preparador VMess y compatibilidad de restore VLESS actualizados. El asistente tiene adaptación preliminar, sin prueba integral del flujo TLS.
- Pendiente: endurecer `modules/vmess_xray_26_10_31.sh` para consumir sólo lease autorizado, completar asistente/restore/cleanup y backup/restore, y ejecutar suite completa.
- No hay Xray service/user/group en VPS de desarrollo; no se ha probado lease con proceso Xray real.
- Regresión completa `tests/*.sh`: 42/42 PASS; ShellCheck (severidad warning), sintaxis Bash, py_compile y `git diff --check` PASS.
- No tocar `Xray-Normativa/`, runtime, servicios, firewall, puertos ni VPS de pruebas.

**Siguiente acción:** integrar generador VMess con resolutor; continuar las pruebas de extremo a extremo del asistente sin desplegar runtime.


## 19. VMess TLS centralizado — endurecimiento del lease (2026-11-03)

- Adaptador `modules/vmess_xray_26_10_31.sh`: TLS exige lease central; no acepta rutas libres. Nuevo `scripts/vmess_tls_lease_check.py` valida manifest, identidad de conexión/protocolo/certificado y permisos root:<grupo-servicio> 0750/0640.
- Asistente VMess: pasa `--runtime-root` explícito, lee contra el catálogo central y limpia leases en éxito/fallo. La recuperación TLS histórica se detiene y requiere migración controlada; no se reescriben datos históricos.
- Restore VLESS: las entradas VMess TLS central preservadas deben referenciar un certificado activo del catálogo central. El backup VLESS sigue sin incluir almacén VMess ni catálogo de certificados.
- Suite completa: 43/43 PASS. Xray 26.10.31 valida 14/14 modalidades con leases de fixture. Recuperación/cleanup del asistente probada con resolutor/Xray simulados. ShellCheck warning, Bash syntax, py_compile y diff check PASS.
- Sin servicio/usuario/grupo Xray en VPS desarrollo: no se probó lectura de lease por proceso real. Sin runtime apply, despliegue, firewall, puertos, certificados reales ni migración. VLESS y backup compartido pendientes.
- Estado: IMPLEMENTADO PARCIALMENTE / VERIFICADO EN FIXTURES / NO PUBLICADO / NO SINCRONIZADO / NO ACEPTADO. `main` y `Xray-Normativa/` intactas.
- Informe actualizado: `docs/IMPLEMENTACION_VMESS_TLS_CENTRALIZADO_PARCIAL.md`.


## 20. Integración VLESS TLS centralizado — punto de control (2026-11-03)

**Estado:** IMPLEMENTADO PARCIALMENTE / VERIFICADO EN FIXTURES / NO PUBLICADO / NO SINCRONIZADO / NO ACEPTADO. Etapa 2 continúa ABIERTA.

- Nuevas revisiones TLS VLESS persisten exclusivamente `certificate_id`; el catálogo central valida existencia, estado activo y tipo `managed`/`reference`. No se crea secreto TLS por conexión.
- Las revisiones históricas `{certificate_file, secret_ref}` siguen siendo legibles/auditables. No se migran ni eliminan automáticamente. REALITY conserva su secreto individual.
- Preparador y adaptador VLESS actualizados. El adaptador exige lease autorizado y rechaza rutas libres. Nuevo `scripts/vless_tls_lease_check.py` valida asociación, protocolo, revisión, fingerprint, identidad y permisos.
- El asistente VLESS solicita ID central, guarda el borrador bajo consentimiento, solicita lease y limpia en éxito/fallo. La recuperación TLS central también usa lease. Las revisiones TLS históricas fallan cerradas hasta migración controlada.
- Backup/restore VLESS documenta `certificate_id` como dependencia externa y exige que el catálogo central/recurso estén activos antes de publicar restauración. No empaqueta el catálogo ni sus secretos.
- Suite completa `tests/*.sh`: 45/45 PASS. Xray 26.10.31 validó 9/9 modalidades VLESS con leases de fixture. `tests/vless_tls_lease_assistant.sh` simula `systemctl`/Xray, verifica lectura POSIX como `www-data` y cleanup en éxito/fallo; no prueba Xray real. `bash -n` global, `py_compile scripts/*.py`, `install.sh --check`, ShellCheck warning de modificados y `git diff --check`: PASS.
- Limitación: VPS desarrollo sin unidad Xray con `User`/`Group` explícitos y no privilegiados. Resolutor CLI falla cerrado; no se probó lectura por proceso Xray real. No runtime apply, despliegue, firewall, puertos, certificados reales ni VPS de pruebas.
- Informe: `docs/IMPLEMENTACION_VLESS_TLS_CENTRALIZADO_PARCIAL.md`.

**Siguiente paso:** ampliar la matriz integrada de recuperación/cleanup para WS, gRPC y XHTTP TLS; después diseñar migración histórica y backup/restore compartido. No declarar completa la integración hasta auditoría integral, trazabilidad y aceptación expresa.


## 21. Matriz VLESS TLS y propuestas de migración/backup (2026-11-03)

- Corregido adaptador VLESS-WS-TLS para aceptar `path` junto con las rutas exactas del lease; RAW/TCP, gRPC y XHTTP mantienen contratos específicos.
- `tests/vless_tls_lease_assistant.sh` valida creación RAW/TCP y recuperación TLS de RAW/TCP, WS, gRPC y XHTTP, cleanup tras éxito/fallo, con `systemctl`/Xray simulados y lectura POSIX como `www-data`. No demuestra lectura por Xray real.
- Asistentes VMess y VLESS pasan rutas configurables completas al resolutor. Validadores VMess/VLESS equivalentes, con comprobación del protocolo del manifest.
- Suite completa `tests/*.sh`: 45/45 PASS.
- Diseños nuevos: `docs/PLAN_MIGRACION_TLS_HISTORICO.md` y `docs/PLAN_BACKUP_RESTORE_CENTRAL.md`. Ambos son propuestas; no hay CLI de migración ni backup compartido implementados.
- No se migraron datos históricos ni se borraron blobs. No runtime apply, servicio, firewall, puertos, certificados reales, VPS pruebas ni cambios a normativa. No commit/push.

**Decisiones requeridas antes de seguir:** aprobar alcance inicial de migración (VLESS/VMess/ambos), política `managed` vs `reference`, retención de blobs históricos; y aprobar re-envoltura de secretos centrales para backup/restore o escrow externo de master key, además de política para dependencias `reference` ausentes y merge con datos posteriores al snapshot.


## 22. Migración histórica TLS aprobada: preflight inicial (2026-11-03)

- Criterios aprobados por el propietario: alcance VMess+VLESS; `managed` por defecto y `reference` con confirmación; bloquear certificados vencidos/no vigentes; conservar históricos; backup obligatorio y aprobación específica para lote real. Backup compartido: secretos reenvueltos por cifrado propio del backup, restore bajo master key destino, no incluir master key, bloquear restore completo ante references ausentes y no sobrescribir datos posteriores al snapshot.
- Nuevo `scripts/certificate_migration.py plan --protocol all|vless|vmess`: read-only. Usa los backends de descifrado separados VLESS/VMess, valida refs/revisiones/permisos, par PEM, vigencia y fingerprints; agrupa duplicados y emite READY/BLOCKED/ALREADY_CENTRAL. No escribe datos ni genera material plaintext.
- Nuevo `tests/certificate_migration_plan.sh`: fixtures sintéticos y negativos PASS. Suite completa 46/46; Bash syntax, py_compile, ShellCheck de prueba y diff-check PASS.
- Preflight real VPS implementación: catálogo de conexiones vacío (0 registros); 0 candidatos TLS. No se crearon directorios VLESS/catálogo central ni se migró dato alguno.
- Auditoría del backup existente: el `tar.gz` VLESS no tiene cifrado integral; sólo blobs secretos están cifrados bajo master key. La recuperación de master key se cifra aparte. El backup compartido requiere contenedor cifrado nuevo, documentado en plan v1.1.
- Documentación: `docs/PLAN_MIGRACION_TLS_HISTORICO.md` v1.1, `docs/PLAN_BACKUP_RESTORE_CENTRAL.md` v1.1, `docs/IMPLEMENTACION_PREFLIGHT_MIGRACION_TLS.md`.
- Pendiente: implementación backup/restore compartido; migración escritora, journal y rollback. Sin backup compartido ni migración real.
- No runtime, servicios, firewall, puertos, certificados desplegados, VPS pruebas ni cambios a `Xray-Normativa/`. No commit/push aún; rama `design/user-identity-association-v1`, base `cd50955`.

**Siguiente paso:** cerrar/implementar el contrato de backup cifrado compartido y sus pruebas antes de habilitar la fase escritora de migración.


### Publicación del punto 22

Commit `631d7eda11615b692557a2e0958a8f318b81c223` (`feat(tls): add read-only historical migration preflight`) publicado y verificado en `origin/design/user-identity-association-v1`; HEAD local/remoto idéntico. `main` permanece en `656ecedc506a94a6461aee296b20871d51a38bf3`. Sin cambios en `Xray-Normativa/`.


## 12. Contenedor cifrado compartido v1 — 2026-11-03

**Estado:** IMPLEMENTADO / VERIFICADO en aislamiento / PUBLICADO y SINCRONIZADO / NO ACEPTADO formalmente.

- Nuevo `scripts/shared_backup_format.py`: contenedor neutral de bytes opacos, independiente de protocolos. Magic `XRMGSBKP`, cabecera JSON canónica, scrypt fijo `N=2^15/r=8/p=1`, AES-256-GCM y AAD sobre cabecera completa. Salt/nonce aleatorios; límites de tamaño y parámetros KDF cerrados.
- Passphrase UTF-8 con mínimo 12 caracteres/16 bytes, máximo 1024 bytes; el módulo no recibe secretos por CLI ni persiste contraseña.
- Nuevo `tests/shared_backup_format.sh`: round-trip, aleatoriedad, contraseña incorrecta, manipulación de cabecera/ciphertext, truncamiento, bytes sobrantes, magic inválido, contraseña débil y payload inválido.
- Nuevo `docs/FORMATO_CIFRADO_COMPARTIDO_V1.md`; `docs/PLAN_BACKUP_RESTORE_CENTRAL.md` actualizado a v1.2.
- Contraste normativo: Etapa 5 exige excluir credenciales/claves privadas por defecto y pedir selección, autorización y confirmación adicional para incluirlas; la futura interfaz/orquestador deberá imponerlo. También exige excluir historiales/logs. El contenedor no decide qué datos se incluyen.
- El contenedor es reutilizable por VLESS, VMess, Trojan y otros protocolos, pero cada protocolo necesitará un adaptador independiente y re-envoltura con su backend/AAD nativo.
- Regresión `tests/*.sh`: 47/47 PASS. `py_compile scripts/*.py`, `bash -n` de shell modules/scripts, ShellCheck warning y shfmt de la nueva prueba, `git diff --check`: PASS.
- No se creó backup real, snapshot, staging, archivo temporal con plaintext, journal ni restore. No se leyó/modificó la master key ni datos persistentes; no se tocó runtime, servicios, firewall, puertos, certificados desplegados, VPS de pruebas ni `Xray-Normativa/`.

**Siguiente paso:** diseñar y probar el manifiesto interno y el snapshot lógico actual (sin historiales), resolver el orden global de locks y definir adaptadores de exportación/re-envoltura para VLESS, VMess y certificados. Después implementar el backup writer; no iniciar restore real ni migración TLS escritora sin autorización específica.


### Publicación del contenedor cifrado compartido v1

Commit `164f91f9c9be8ab275da0b28a53b2314a636f1e2` (`feat(backup): add protocol-neutral encrypted container v1`) publicado en `origin/design/user-identity-association-v1`. HEAD local/remoto verificado idéntico (`164f91f`). `main` no se modificó. `Xray-Normativa/` no tiene cambios. `scripts/__pycache__/` sigue sin seguimiento y quedó excluido.

## 13. Política de metadatos VMess para backup compartido — 2026-11-03

**Decisión registrada:** UUID VMess excluido por defecto como credencial; email y level conservados como metadatos/configuración dentro del payload cifrado. email no autentica ni es necesario para el cliente externo y no debe exponerse en manifiesto externo ni logs. Los registros sin UUID quedan incompletos/no restaurables íntegramente hasta que la credencial se aporte mediante flujo autorizado. Inclusión de UUID requiere selección, autorización y confirmación adicional.

Contrato: docs/PLAN_BACKUP_RESTORE_CENTRAL.md v1.3, §10.1.

**Estado:** decisión DOCUMENTADA; no cambia código ni esquema operativo. No hay snapshot ni backup compartido real.

**Siguiente paso exacto:** diseñar el schema del manifiesto interno y el snapshot lógico actual, definiendo cómo se representan las exclusiones y la completitud por elemento. En paralelo, completar la auditoría estática de todos los mutadores/locks y documentar cualquier ruta no inspeccionable. No implementar writer ni restore hasta cerrar esos contratos y pruebas sintéticas.

## 14. Lock de catálogo TLS en desinstalación — 2026-11-03

**IMPLEMENTADO localmente:** modules/uninstall.sh adquiere catalog.lock cuando se selecciona eliminar certificados, tras integrity.lock y antes del lock Xray. Orden en este flujo: lifecycle → uninstall → integrity → catalog → Xray. Si el lock está ocupado, cancela antes del backup/borrado; si se adquiere, lo mantiene durante confirmación, backup y eliminación.

**Pruebas:** tests/uninstall.sh cubre lock ocupado y conservación de datos, además de verificar que el lock sigue tomado durante la confirmación. Todos los tests/*.sh PASS; Bash syntax PASS; ShellCheck del módulo PASS; py_compile scripts/*.py PASS; git diff --check PASS.

**Alcance/limitación:** corrección del flujo de desinstalación, no auditoría global concluida. Falta inventario exhaustivo de todos los mutadores, validación de sus órdenes y pruebas adicionales de concurrencia. No iniciar writer compartido hasta cerrar esos puntos.

**Sin tocar:** Xray-Normativa/, datos persistentes, master key, certificados reales, runtime, servicios, firewall, puertos ni VPS de pruebas.

## 15. Ubicación estable de catalog.lock — 2026-11-03

**Decisión técnica:** el default pasa a /run/xray-manager-certificate-locks/catalog.lock. La ubicación anterior estaba dentro del árbol que se elimina y podía dejar procesos bloqueando un inode desvinculado mientras otros abrían un archivo nuevo.

**Cambios locales:** config/paths.sh, defaults de certificate_store.py y certificate_resolver.py, fallbacks VLESS/VMess, uninstall.sh y documentación. El padre se crea/valida root-only mediante safe_dir del almacén. Tests añadidos para defaults CLI y supervivencia del lock fuera del árbol eliminado.

**No ejecutado:** no se movieron ni borraron locks reales, no se aplicó runtime ni se modificaron datos persistentes.

**Estado histórico:** en ese punto se debía repetir la suite y continuar la auditoría. La auditoría estática y el contrato de snapshot/writer se cerraron posteriormente; consultar las actualizaciones finales de este documento.

## 16. Auditoría estática de locks — 2026-11-03

**Resultado:** inventario estático de los puntos de adquisición del repositorio completado; no se encontró ciclo/inversión en los caminos inspeccionados.

**Orden recomendado del snapshot:** lifecycle → integrity → catalog; liberar en orden inverso. Writer con adquisición no bloqueante y timeout finito configurable. No usar flock bloqueante indefinido.

**Pruebas:** contención lifecycle/integrity/catalog/Xray, catalog retenido durante confirmación, liberación ante lock Xray ocupado y supervivencia del lock fuera del árbol eliminado. Suite 47/47 PASS; Bash syntax, ShellCheck uninstall, shfmt focal, py_compile y git diff check PASS.

**Limitación:** estática, no stress test exhaustivo. La ruta TLS nueva requiere despliegue con procesos de versión anterior detenidos. No se movió el lock anterior ni se ejecutó runtime apply.

**Estado histórico:** el alcance inicial de categorías/adaptadores fue aprobado posteriormente; el contrato técnico del writer también quedó aprobado. Consultar la actualización final de este documento.


## 2026-11-03 — Aprobación del alcance incremental del snapshot compartido v1

El propietario aprobó el alcance incremental: snapshot de conexiones/configuraciones actuales VLESS y VMess; metadatos no secretos de usuarios, identidades y asociaciones; catálogo central TLS, certificados públicos `managed` y dependencias `reference`. Se excluyen por defecto UUID VLESS/VMess, secretos REALITY, claves privadas TLS y cualquier otra credencial; los elementos afectados se marcan incompletos. Se mantienen `email` y `level` VMess como metadatos protegidos.

Perfiles, perfil activo, preferencias, dominios independientes y protocolos distintos de VLESS/VMess quedan `unsupported` en v1. Si una categoría no soportada es solicitada, el resultado global será `PARTIAL`, nunca `COMPLETE`. Esto se contrasta con Etapa 5 normativa, que sigue siendo la referencia íntegra y no se modifica.

`docs/PLAN_BACKUP_RESTORE_CENTRAL.md` actualizado a v1.6 con la decisión y un borrador del contrato lógico de manifiesto. El borrador sigue pendiente de aprobación: no es schema congelado. La aprobación actual no autoriza writer, paquetes reales, restore, inclusión de secretos ni runtime apply.


**Publicación del alcance incremental v1:** commit `bccaba94be4160e6c01f281c7f4829f02c07db41` (`docs(backup): approve incremental snapshot v1 scope`) publicado en `origin/design/user-identity-association-v1`; HEAD local/remoto verificado idéntico en ese commit. Sólo documentación; `Xray-Normativa/` intacta. No se implementó writer ni se crearon paquetes/backups reales.


## 2026-11-03 — Borrador detallado de schema del manifiesto compartido

Se amplió `docs/PLAN_BACKUP_RESTORE_CENTRAL.md` a v1.7 con una propuesta concreta de estructura JSON y reglas de validación para el manifiesto interno: solicitud/categorías, recursos, miembros content-addressed, exclusiones, dependencias, snapshot de origen y completitud. `COMPLETE`/`PARTIAL` son estados de paquete; `BLOCKED` es preflight fallido y no produce paquete. El manifiesto permanece dentro del payload cifrado y no contiene credenciales ni email VMess.

El schema sigue PENDIENTE DE APROBACIÓN. No se implementó writer, verify, restore ni formato de empaquetado; no se creó backup real. `Xray-Normativa/` permanece intacta.


**Publicación del borrador de manifiesto:** commit `2bffbb6eee3c84b8008d2445ae0c0377bca40536` (`docs(backup): draft shared manifest schema v1`) publicado en `origin/design/user-identity-association-v1`; HEAD local/remoto verificado idéntico en ese commit. Sólo documentación; `Xray-Normativa/` intacta. El schema continúa pendiente de aprobación y no hay writer ni backup real.


## 2026-11-03 — Aprobación del contrato JSON del manifiesto compartido v1

El propietario aprobó expresamente el contrato lógico y la estructura JSON de las secciones 10.6 y 10.7 de `docs/PLAN_BACKUP_RESTORE_CENTRAL.md`. Se aprueban campos/relaciones, categorías, recursos, miembros content-addressed, exclusiones, dependencias, source snapshot, hashes/tamaños, paths relativos, reglas de validación y estados `COMPLETE`/`PARTIAL`; `BLOCKED` queda como resultado de preflight que aborta sin publicar paquete. El manifiesto no contiene credenciales ni email VMess.

El plan pasa a v1.8 y el contrato de manifiesto v1 queda APROBADO. Empaquetado físico, máximo de miembros y canonicalización JSON exacta siguen pendientes de cierre técnico. No se implementó writer/verify/restore ni se creó backup real. `Xray-Normativa/` permanece inmutable.


**Publicación de aprobación del manifiesto:** commit `000eb537fbb11c9870b6bef917769b1ca8448c66` (`docs(backup): approve shared manifest contract v1`) publicado en `origin/design/user-identity-association-v1`; HEAD local/remoto verificado idéntico en ese commit. Sólo documentación; `Xray-Normativa/` intacta. El writer sigue sin implementarse.


## Actualización del punto de control — ZIP/JSON lógico v1 aprobado (2026-11-03)

- ZIP interno con `ZIP_STORED`; `manifest.json` e `index.json`; sólo archivos regulares. Rechazo de rutas inseguras, duplicados, symlinks/tipos especiales, métodos distintos, entradas no indexadas/ausentes y discrepancias de tamaño/hash.
- Canonicalización JSON propia: UTF-8 estricto sin BOM, claves ordenadas, separadores compactos, sin claves duplicadas, floats ni valores no finitos, enteros interoperables; comparación de bytes con serialización canónica. No se afirma RFC 8785/JCS.
- Límite del ZIP completo: 512 MiB. Máximo aprobado: 10.000 entradas ZIP totales (incluye `manifest.json` e `index.json`), hasta 9.998 miembros de datos; excederlo aborta sin publicar paquete.
- `docs/PLAN_BACKUP_RESTORE_CENTRAL.md` v1.9. `Xray-Normativa/` intacta. No writer/verify/restore, no paquete real, no secretos ni runtime apply.


## Actualización — máximo de entradas ZIP aprobado (2026-11-03)

Límite estricto: 10.000 entradas ZIP totales, contando `manifest.json` e `index.json`; máximo 9.998 miembros de datos. Superarlo aborta la creación sin publicar paquete parcial y el lector/verify debe rechazarlo. Plan v1.10. El límite de miembros queda cerrado; writer, verify, restore y paquetes reales siguen sin implementar/autorización.


## 2026-11-03 — Aprobación del contrato técnico del snapshot writer v1

El propietario aprobó el contrato técnico del snapshot writer compartido v1 y la ampliación de cifrado incremental compatible con el contenedor criptográfico v1. Se congelan: secuencia fail-closed; locks `lifecycle → integrity → catalog`, adquisición no bloqueante con timeout total configurable (30 s inicial recomendado) y liberación inversa; captura coherente de catálogos/revisiones referenciadas; adaptadores VLESS/VMess/identidades/TLS; exclusiones predeterminadas; validación segura de archivos; manifiesto/índice/ZIP `ZIP_STORED`; máximo 10.000 entradas y 512 MiB; cifrado GCM por bloques sin cambiar el formato binario v1; verificación y publicación atómica exclusiva sin sobrescritura; estados de resultado y matriz de pruebas.

La interfaz incremental deberá conservar magic, cabecera/AAD, perfil scrypt, salt/nonce, AES-256-GCM y tag del formato v1, con compatibilidad cruzada respecto a la interfaz actual. El ZIP se emitirá en streaming al cifrador sin crear ZIP en claro en disco; el tamaño exacto del ZIP se calculará antes de fijar `ciphertext_length` y se contrastará con el flujo emitido.

`docs/PLAN_BACKUP_RESTORE_CENTRAL.md` pasa a v1.11. La aprobación autoriza implementar writer y cifrado incremental en la rama autorizada, pero no crear backups reales, incluir secretos, implementar restore/verify independiente, leer/modificar master key ni tocar runtime/servicios/firewall/puertos/certificados desplegados/VPS de pruebas. `Xray-Normativa/` permanece inmutable.


## Actualización — API incremental del contenedor cifrado v1 (2026-11-03)

- `scripts/shared_backup_format.py`: añadidas `encrypt_payload_stream()` y `verify_package_stream()` con AES-GCM por bloques, longitud conocida, autenticación de cabecera/AAD y tag final; el formato binario v1 no cambia y las APIs de bytes existentes se conservan.
- Pruebas focales PASS; compatibilidad cruzada streaming/no streaming PASS; suite completa `tests/*.sh`: 47/47 PASS; sintaxis Python y `git diff --check` PASS.
- Siguiente: ZIP `ZIP_STORED` determinista en streaming y snapshot writer. No se ha creado backup real ni se han tocado secretos, master key o runtime.


## Actualización — generador ZIP determinista streaming v1 (2026-11-03)

- Nuevo `scripts/shared_backup_zip.py`: `ZipMember` con `allowed_root`, lectura segura sin symlinks en componentes, root:root 0600, nlink 1, detección TOCTOU, SHA-256/CRC-32 antes y durante emisión; `ZipStream.read(n)` para alimentar cifrado GCM incremental sin ZIP claro temporal; `write_zip_stream()` para sinks de prueba.
- ZIP_STORED determinista, UTF-8/NFC, timestamps fijos, `manifest.json`/`index.json` primeros, datos ordenados, sin ZIP64, máximo 10.000 entradas y 512 MiB incluyendo overhead.
- `tests/shared_backup_zip.sh` PASS, incluida integración ZIP→cifrado incremental→verificación GCM→ZIP válido. Suite completa `tests/*.sh`: 48/48 PASS; sintaxis Python, ShellCheck focal, shfmt focal y `git diff --check` PASS.
- Snapshot writer/orquestador, adaptadores, locks y publicación atómica siguen pendientes. No backup real, secretos, master key ni runtime.


## Punto de control — snapshot writer compartido v1, implementación local inicial (2026-11-03)

**Estado:** IMPLEMENTADO LOCALMENTE / VERIFICADO PARCIALMENTE / NO PUBLICADO / NO SINCRONIZADO / NO ACEPTADO.

- Archivo nuevo: scripts/shared_snapshot_writer.py.
- Pruebas nuevas: tests/shared_snapshot_writer.sh.
- SW-01 corregido: modo selective sin categorías explícitas se rechaza en API y CLI.
- SW-02 corregido: validación de destino y staging privado preceden al prompt de passphrase; la passphrase precede a la adquisición de locks.
- SW-03 corregido: no se crean directorios operativos para locks; se rechazan padres ausentes o inseguros. El timeout rechaza bool, strings, negativos y valores no finitos.
- Pruebas sintéticas cubren staging/cleanup, locks y orden inverso, timeout, referencias de identidad y exclusión de credenciales; email/level VMess permanecen como metadatos protegidos.
- Resultados focales: writer PASS; contenedor cifrado PASS; ZIP streaming PASS; AST Python PASS. Regresión global tests/*.sh: 49/49 PASS; git diff --check PASS.
- No ejecutar todavía backup real. No restore ni verify independiente. No master key/secretos reales, runtime, servicios, firewall, puertos, certificados desplegados, VPS de pruebas ni cambios en Xray-Normativa/.
- Próximo paso: completar matriz integral §10.11 y suite de aceptación (errores de catálogos/revisiones, TOCTOU, límites, fuga de secretos, fallos de cifrado/publicación/interrupción y limpieza), revisar los cambios locales y presentar informe antes de commit/push.
- Rama design/user-identity-association-v1; HEAD ec9b306b38f0bce17f28c301c47df3b3d092785a. Sin commit/push.

## 2026-11-03 — Endurecimiento y ampliación de pruebas del snapshot writer v1

Implementados localmente los cuatro bloques autorizados de corrección:

1. **Destino y TOCTOU:** la validación inspecciona toda la cadena de directorios; exige root:root, rechaza symlinks y ancestros group/world-writable sin sticky bit; conserva la excepción segura para directorios sticky como /tmp y exige 0700 en el directorio final.
2. **Dependencias TLS:** se incorpora `external-dependencies.json` como miembro del ZIP cifrado. Para certificados `reference` registra certificate_id, fingerprint, ruta esperada, conexiones dependientes y validación requerida. La ruta absoluta no se incorpora al manifiesto y sólo queda dentro del payload cifrado. Las dependencias TLS reference se identifican como `tls_reference`.
3. **Errores y estados:** passphrase inválida, origen/miembro ZIP alterado, límites/formato cifrado inválido y verificación fallida se clasifican como `BLOCKED`; fallos operativos de I/O se mantienen como `FAILED`.
4. **Snapshot y exclusiones:** `source_snapshot` registra catalog_id, schema_version, revision, SHA-256 y presencia. Los almacenes sin schema/revision propia declaran null, no valores inventados. El catálogo de identidades ausente bloquea en vez de interpretarse silenciosamente como vacío. Las exclusiones de asociaciones ahora identifican asociación, identidad y conexión y se representan como recursos individuales.

La suite focal `tests/shared_snapshot_writer.sh` se amplió con:
- Rechazo de ancestros inseguros y symlinks en el destino.
- Rechazo de passphrase débil como BLOCKED.
- Revisiones VLESS/VMess incorrectas, destino preexistente y cleanup.
- Dependencias TLS reference con agregación de conexiones y path confinado al miembro cifrado.
- E2E sintético VLESS + VMess + identidades: UUID ausentes del paquete, email/level VMess conservados.
- E2E sintético TLS reference y TLS managed: certificado público managed incluido; clave privada excluida; ruta reference sólo en external-dependencies.json.
- Cambio de configuración después del preflight rechazado por hash/size del miembro.
- Fallos de verificación, fsync, interrupción controlada y carrera de publicación sin sobrescritura.
- Medición tracemalloc de emisión ZIP→AES-GCM para un miembro de 16 MiB con umbral de memoria Python inferior a 8 MiB.

Pruebas focales writer, formato cifrado y ZIP PASS; AST Python, ShellCheck, shfmt y git diff --check PASS. Regresión global `tests/*.sh`: 49/49 PASS.

**Limitaciones aún abiertas antes de aceptación:** no se ha ejecutado una matriz de terminaciones abruptas SIGKILL en cada fase; la medición de memoria es tracemalloc (no RSS máximo del proceso); los límites de 10.000 entradas/512 MiB se verifican en el generador ZIP, pero falta una prueba de orquestación que los fuerce desde el writer; falta ampliar escenarios integrales de catálogos y revisiones VLESS/VMess y pruebas de publicación/durabilidad posteriores al punto de commit. Por tanto, el writer sigue NO ACEPTADO.

No se creó backup real ni se accedió a master.key o secretos reales. No se ejecutó restore/verify independiente ni se modificó runtime, servicios, firewall, puertos, certificados desplegados o VPS de pruebas. `Xray-Normativa/` permanece intacta. Sin commit/push ni sincronización GitHub; rama `design/user-identity-association-v1`, HEAD sin cambio `ec9b306b38f0bce17f28c301c47df3b3d092785a`.

## 2026-11-03 — Cierre de la matriz ampliada de pruebas del snapshot writer

Se completó una segunda ampliación de la suite de aceptación local:

- E2E sintético VLESS + VMess + identidades, TLS `reference` y TLS `managed`; se verificó ausencia de UUID/credenciales excluidas, conservación de `email`/`level` VMess y ruta de referencia sólo dentro del miembro cifrado.
- TOCTOU de configuración después del preflight: el cambio de bytes se detecta y bloquea antes de publicar.
- Límites ejercidos a través de `create_snapshot`: 10.001 entradas y ZIP lógico superior a 512 MiB producen BLOCKED sin paquete final.
- Locks con contención real: timeout al segundo lock y liberación del primero comprobada.
- Publicación: destino concurrente no sobrescrito; fallos pre-commit limpian staging; fallo de fsync post-commit informa FAILED y conserva el artefacto ya publicado, que se vuelve a autenticar.
- Terminación abrupta mediante `os._exit` en tres puntos (antes del prompt, durante emisión cifrada y antes del enlace final): no aparece destino final; los residuos observados permanecen dentro de staging root:root 0700 y archivo 0600. La prueba los elimina al terminar.
- Memoria: tracemalloc bajo el umbral de 8 MiB adicionales; proceso aislado con miembro de 16 MiB midió RSS máximo de 73.436 KiB (incluye Python y scrypt).
- CLI/API: `all_available` delega selección por defecto correctamente; `selective` exige categorías explícitas.

Validación final: `tests/*.sh` 49/49 PASS; AST Python 16/16; ShellCheck PASS; shfmt PASS; `git diff --check` PASS.

**Consideración operativa pendiente:** tras una terminación no capturable (`os._exit`/SIGKILL), el proceso no puede ejecutar `finally`; puede quedar un staging privado sin destino publicado. La matriz demuestra que el residuo es privado y no contiene un ZIP en claro, pero no se implementó un recolector automático de staging huérfano. No se borrarán esos directorios de forma heurística mientras pueda existir otro proceso activo.

El writer continúa **IMPLEMENTADO LOCALMENTE / VERIFICADO EN AISLAMIENTO / NO PUBLICADO / NO ACEPTADO FORMALMENTE**. No se ejecutó backup real ni se accedió a master.key/secretos reales; no restore, verify independiente ni runtime apply. `Xray-Normativa/` intacta. Rama `design/user-identity-association-v1`, HEAD `ec9b306b38f0bce17f28c301c47df3b3d092785a`; sin commit/push ni sincronización GitHub.

## Actualización de estado — recuperación de staging autorizada (2026-11-03)

Implementación local: passphrase antes de staging; `.xrm-coordination.lock` serializa la inspección y preparación; `owner.lock` root:root 0600 (`nlink == 1`) se mantiene bloqueado por el proceso propietario. Recuperación estricta de temporales abandonados con lock libre; conservación de temporales activos y de estructuras inesperadas; limpieza normal coordinada. Se conserva el orden de locks de datos `lifecycle → integrity → catalog`.

Verificación: suite focal PASS; `bash tests/*.sh` PASS; AST Python 16/16; ShellCheck focal PASS; shfmt focal PASS; `git diff --check` PASS. RSS máximo medido en proceso aislado: 74.120 KiB. El crash matrix ahora prueba terminaciones durante cifrado y antes de publicación; SW-02 verifica que un cierre durante el prompt no cree staging. Writer implementado localmente, no publicado y no aceptado formalmente. Sin backup real, lectura de secretos/master.key, restore, verify independiente ni cambios de runtime. `Xray-Normativa/` intacta; sin commit/push/sincronización GitHub.

## Punto de control — 2026-11-03: coordinación y manifiesto endurecidos

Se corrigió el orden de validación de `.xrm-coordination.lock` para que hardlinks, symlinks, FIFO y archivos con metadatos inseguros se rechacen sin modificar el inode preexistente. Creación inicial exclusiva y validación de identidad del descriptor. Se añadieron pruebas de contención/timeout. `_validate_manifest_contract()` ahora verifica UUID v4, timestamp UTC RFC 3339, estructura/versión, categorías y listas, tamaños/hashes de miembros y coherencia de completitud.

Verificación actual: `tests/shared_snapshot_writer.sh` PASS; los 49 scripts `tests/*.sh` PASS; AST 16/16; `bash -n`, ShellCheck, shfmt y `git diff --check` PASS. RSS focal 75.120 KiB.

Estado: writer y correcciones locales, no publicados ni aceptados formalmente. HEAD permanece `ec9b306b38f0bce17f28c301c47df3b3d092785a`; cambios locales preexistentes y nuevos deben preservarse. No commit/push/sync. Próximo paso permitido: revisión de aceptación del propietario; no ejecutar backup real ni acceder a datos secretos, restore, verify independiente o runtime apply.


## Punto de control — snapshot writer v1 publicado, pendiente de aceptación (2026-11-03)

**Estado:** IMPLEMENTADO / VERIFICADO EN AISLAMIENTO / PUBLICADO / NO ACEPTADO FORMALMENTE.

- Rama: design/user-identity-association-v1.
- Commit de publicación: ae8a7a089809e2e1913c14a714f45d956f8a5a1d.
- Se publicaron writer, suite de pruebas, dependencias ZIP/API y documentación técnica. scripts/__pycache__/ fue excluido.
- Verificación previa: 49/49 scripts PASS; AST 16/16; bash -n, ShellCheck, shfmt, git diff --check PASS; normativa 14/14 hashes coincidentes.
- Siguiente paso: revisión de aceptación integral contra §10.11.8 / plan v1.14 y decisión expresa del propietario.
- No crear backup real, no leer secretos/master.key, no implementar restore/verify independiente ni tocar runtime, servicios, firewall, puertos, certificados desplegados o VPS de pruebas.


## Punto de control — correcciones de segunda revisión del snapshot writer (2026-11-03)

**Estado:** BASE IMPLEMENTADA / VERIFICADA EN AISLAMIENTO / PUBLICADA; CORRECCIONES B-01/B-02/B-03 IMPLEMENTADAS Y VERIFICADAS LOCALMENTE / NO PUBLICADAS / NO ACEPTADO FORMALMENTE.

- **B-01:** allowlist estricta de identidades/asociaciones; sólo VLESS/VMess se preservan saneados. WireGuard y otros protocolos fuera del alcance v1 se excluyen íntegramente y se trazan como unsupported_protocol, causando PARTIAL. Campos inesperados/sensibles bloquean.
- **B-02:** cleanup fail-closed; owner_fd siempre se cierra. Fallos de lock de coordinación, unlink, rmdir o fsync no se silencian y producen FAILED. Si el enlace final ya existe, el paquete se conserva y el error distingue publicación de limpieza.
- **B-03:** sólo manifest_version: 1; included ∪ unsupported == requested y conjuntos disjuntos. Estructura exacta validada para resources/members/exclusions/dependencies/source_snapshot.
- **Crash matrix:** prompt antes de staging, cifrado, antes del enlace y después del enlace exclusivo antes de fsync de directorio.
- **Verificación ejecutada:** 49/49 tests/*.sh PASS; AST 16/16; bash -n 74 archivos; ShellCheck focal PASS; shfmt focal PASS; git diff --check PASS.
- Normativa: 14/14 hashes SHA-256 coinciden con la copia maestra.
- Rama: design/user-identity-association-v1. HEAD remoto y local de partida: ae8a7a089809e2e1913c14a714f45d956f8a5a1d. Correcciones y documentación actuales permanecen locales, sin commit/push/sync.
- Próximo paso: revisar el diff completo y la matriz de aceptación; presentar conclusión y esperar aceptación expresa. No crear backup real, no leer master.key/secretos, no restore/verify independiente ni runtime apply. Xray-Normativa permanece inmutable.


## Registro histórico SUPERADO — publicación B-01/B-02/B-03 y bloqueo A-16 (2026-11-03)

**Estado:** B-01/B-02/B-03 autorizados para publicación; Snapshot Writer v1 **NO ACEPTADO** por bloqueo A-16.

- A-16 reproducido en VPS con entorno sintético: tras el hard link de publicación, `package.tmp` y `final_path` comparten inode (`st_nlink == 2`); `_recover_orphan_staging()` exige `st_nlink == 1`, lanza `SnapshotBlocked` y conserva staging y destino.
- Los tests actuales simulan el crash post-link pero eliminan staging manualmente; no prueban `_recover_orphan_staging()` sobre el residuo real. Los fallos de cleanup tampoco demuestran recuperabilidad.
- La publicación de B-01/B-02/B-03 no corrige ni exonera A-16. No marcar writer como aceptado.
- Siguiente paso: después de publicar/sincronizar, solicitar autorización específica para corregir recuperación post-link sin relajar la política contra hardlinks arbitrarios; añadir pruebas de recuperación tras crash post-link, unlink fallido y coordinación fallida. Ejecutar matriz completa y nueva auditoría.
- Restricciones: no backup real, no `master.key`/secretos, no restore/verify independiente, no runtime apply, no cambios a `Xray-Normativa/`.

- Publicación de B-01/B-02/B-03 verificada en commit `b6582da` de `origin/design/user-identity-association-v1`. El checkout de la VPS se encuentra en ese commit; `scripts/__pycache__/` permanece como artefacto local no versionado y no fue incluido.

## Punto de control — A-16 corregido localmente (2026-11-03)

**Estado:** A-16 IMPLEMENTADO LOCALMENTE / PRUEBA FOCAL PASS / AUDITORÍA GLOBAL PENDIENTE. Snapshot Writer v1 continúa **NO ACEPTADO**.

- publication.json privado/durable ata destino exacto, device/inode, tamaño y SHA-256 antes de os.link.
- Recuperación acepta package.tmp nlink == 2 sólo con marcador y destino exactos; retira únicamente el nombre temporal y valida que el paquete final permanece intacto con nlink == 1.
- Reanudación idempotente tras crash del recuperador después del unlink del temporal.
- Rechazo probado de hardlink arbitrario sin marcador, destino con basename distinto y tercer hardlink (nlink == 3).
- Verificación posterior: tests/*.sh 49/49 PASS; AST 16/16; bash -n 74 archivos; ShellCheck PASS; shfmt focal PASS; git diff --check PASS; SHA normativa 14/14 coincidente. A-16 pasa la recuperación post-link y la reanudación idempotente.
- Próximo paso: revisar el diff completo y la matriz A-01–A-19; presentar resultados al propietario para aceptación formal o nuevos hallazgos. No backup real, no acceso a secretos/master.key, no runtime ni restore/verify independiente. No commit/push/sync sin autorización expresa; mantener la condición NO ACEPTADO.

## Punto de control — A-16 publicado y VPS sincronizada (2026-11-03)

**Estado:** A-16 IMPLEMENTADO / VERIFICADO / PUBLICADO / SINCRONIZADO. Snapshot Writer v1 permanece **NO ACEPTADO FORMALMENTE**.

- Rama: `design/user-identity-association-v1`.
- Commit: `40c907e2a9da639f3458547e09fec6f26fdac5e1`.
- SHA remoto confirmado mediante `git ls-remote`; `/opt/xray-manager` está en el mismo HEAD y limpio.
- Próximo paso permitido: presentar al propietario el estado publicado y esperar su decisión expresa sobre aceptación formal del Snapshot Writer v1 o nuevas observaciones. No ejecutar backup real, no leer secretos/master.key, no restore/verify independiente, no runtime apply y no modificar `Xray-Normativa/`.


## Registro de auditoría técnica A-01–A-19 (2026-11-03)

- Matriz de trazabilidad completa documentada en `docs/PLAN_BACKUP_RESTORE_CENTRAL.md` §10.20. Se recuperaron los nombres originales de los 19 criterios y se enlazaron con sus pruebas versionadas; A-01–A-15 y A-17–A-19 conservan su resultado PASS de la auditoría previa y la regresión actual volvió a ejecutarse.
- A-16: diez negativos nuevos para marcador malformado/no canónico, hash/device/inode/tamaño alterados, campo extra, symlink, hardlink y modo inseguro. Cada caso confirma bloqueo fail-closed y preservación de la evidencia. No requirió modificar el código del writer.
- Verificación actual: 49/49 scripts PASS; AST 16/16; `bash -n` 74 archivos; ShellCheck PASS; shfmt PASS; `git diff --check` PASS; RSS focal 76.336 KiB. Normativa 14/14 hashes coincidentes con la copia maestra; `README.md` es archivo adicional no normativo.
- Rama `design/user-identity-association-v1`; base verificada `b1e2ef4537eafeacefd5584a7fde5c9fd02626a9`. La matriz y los diez negativos A-16 se publicaron en `101853e6ef0990686128f45561b22e1cd4248aea`; el registro final de publicación quedó en `7f03efcf080465d8bced447549e29f8abb95248b`. VPS y GitHub comparten el HEAD final.
- `Xray-Normativa/` no se modificó. No backup real, no acceso a `master.key`/secretos, no restore/verify independiente, no runtime apply.
- Estado: A-01–A-19 PASS en pruebas aisladas/sintéticas; Snapshot Writer v1 **NO ACEPTADO FORMALMENTE**. La aceptación formal requiere decisión expresa del propietario y no se infiere de pruebas o publicación.


## Estado vigente — después de aceptar Snapshot Writer v1

**Estado del componente:** Snapshot Writer v1 **ACEPTADO FORMALMENTE CON LIMITACIONES DOCUMENTADAS** por decisión expresa del propietario del 2026-11-03. La evidencia técnica A-01–A-19 permanece en §10.20 del plan; la aceptación y sus límites están en §10.22.

**Siguiente punto de trabajo:** backup/restore integral, incluyendo diseño y validación del flujo de restauración y verify independiente, previa autorización y contraste normativo. No ejecutar backup real, restore, verify independiente, leer secretos/master.key ni aplicar cambios al runtime hasta que exista autorización específica. **Etapa 2 permanece ABIERTA**; esta aceptación es sólo del componente Snapshot Writer v1.


## Validación live inicial de Xray-core y VLESS-WS — 2026-11-03

**Estado:** instalación real de Xray-core PASS; creación/persistencia/recuperación/validación VLESS-WS PASS; runtime apply y conectividad cliente externa PENDIENTES.

- Xray-core 26.10.31 (a4a3dff) instalado mediante el menú de administración. Release/ZIP SHA-256, versión del binario y geodata verificados.
- Se ajustó /var/lib/xray-manager/connections de root:root 750 a root:root 700, alineándolo con la política de install.sh y el contrato del almacén VLESS. No se modificó código.
- Conexión Prueba-VLESS-WS-Real, ID conn-1793749234-670662, vless_ws, 0.0.0.0:10001, WebSocket /ws, seguridad none, un slot. Estado draft, runtime_applied=false, revisión 1.
- Usuario de prueba Cliente-Prueba-VLESS-WS creado con el gestor legacy porque el archivo live de usuarios sigue siendo un arreglo JSON. UUID omitido de la documentación.
- Asistente y recuperación del Manager validaron la configuración; segunda recuperación con XRAY_VALIDATION_BINARY=/usr/local/bin/xray confirmó Configuration OK usando el binario instalado.
- Auditoría del almacén: cero referencias rotas, cero archivos huérfanos y cero secretos huérfanos.
- Xray permanece inactivo; /etc/xray/config.json y xray.service no existen; puerto 10001 no escucha. Sin firewall, runtime apply, certificados ni WAN.
- Xray advierte que WebSocket está obsoleto/no recomendado y recomienda XHTTP H2/H3.
- Informe: docs/VALIDACION_LIVE_XRAY_VLESS_WS_2026-11-03.md.

**Siguiente punto:** revisar y autorizar por separado el diseño/implementación del flujo de aplicación runtime. La inspección del menú actual no encontró una acción que publique esta configuración en /etc/xray/config.json; no preparar/iniciar servicio ni abrir red hasta autorización expresa. Etapa 2 permanece ABIERTA.

## Punto de control — candidatos runtime vinculados a perfiles (2026-11-03)

**Decisión:** opción A aprobada; activación exclusivamente mediante el flujo de perfil activo de Etapa 5.

**Hallazgo:** no existe todavía un gestor funcional de perfiles. El directorio de datos preparado por install.sh no equivale a implementación. Los adaptadores VLESS/VMess generan configuración por conexión y no una composición integral de perfil.

**Implementación local:**
- Nuevo `scripts/xray_runtime_candidates.py`.
- Nueva prueba `tests/xray_runtime_candidates.sh`.
- Diseño: `docs/DISENO_IMPLEMENTACION_RUNTIME_PERFILES.md`.
- La prueba focal sintética PASS: staging, hash/manifiesto, permisos, no sobrescritura, JSON inválido, rechazo Xray simulado, symlink, hardlink y traversal.
- La validación Xray se ejecuta sobre la copia privada exacta que se almacena, mitigando TOCTOU.
- Almacén de candidatos privado: directorios 0700; config/manifiesto 0600; revisión inmutable y bloqueo.

**No es activación:** no se escribe /etc/xray/config.json; no se prepara systemd ni cuenta/grupo; no se inicia/habilita Xray; no se modifica firewall, puerto 10001, certificados ni reglas de red. No se usa conexión independiente como origen.

La conexión Prueba-VLESS-WS-Real sigue draft y runtime_applied=false. Etapa 2 sigue ABIERTA. La integración de publicación queda bloqueada hasta implementar perfiles y el flujo de activación de Etapa 5.

**Estado Git:** rama design/user-identity-association-v1, HEAD de base d632908300441341d84db8573c417f14002c3f70; cambios locales previos de documentación se preservan. Sin commit/push/sync. Xray-Normativa/ sin modificar y main intacta.

### Corrección de aislamiento de prueba

Se corrigió tests/users.sh para fijar las rutas de datos y lock temporales antes de cargar y volver a cargar módulos. La ejecución inicial había detectado el usuario de prueba live en el archivo real y se detuvo por capacidad; no escribió ni alteró el registro live. Tras la corrección, tests/users.sh y tests/smoke.sh pasan.

### Verificación final

50/50 scripts PASS; Python AST 17/17; bash -n en todos los archivos shell PASS; ShellCheck y shfmt focal PASS; git diff --check PASS. Xray-core 26.10.31 real validó un candidato sintético temporal: STAGED, runtime_published=false, service_started=false. Comparación de normativa: 14/14 MATCH; README.md es auxiliar no normativo. Sin commit/push/sync.

## Publicación GitHub — staging de candidatos runtime por perfil (2026-11-03)

Por autorización expresa, los cambios pendientes fueron preparados para publicación en la rama autorizada `design/user-identity-association-v1`: primitiva de staging, prueba focal, aislamiento de `tests/users.sh`, documentación de diseño, validación live y registros de estado/continuidad/historial. El artefacto local `scripts/__pycache__/` se excluye.

La publicación es exclusivamente de código y documentación. No implica que exista ya un gestor de perfiles ni que el runtime esté implementado/activado. La conexión de prueba continúa draft, sin runtime apply y sin listener. `Xray-Normativa/` y `main` no se modifican. Etapa 2 sigue ABIERTA.


## Punto de control — almacén de perfiles v1 (2026-11-03)

**Estado:** IMPLEMENTADO LOCALMENTE / REGRESIÓN PASS / NO PUBLICADO TODAVÍA / NO ACEPTADO FORMALMENTE COMO SUBSISTEMA COMPLETO.

**[DECISIÓN HISTÓRICA SUPERADA EL 2026-11-03]** La primera implementación local contempló configuraciones JSON de perfiles en texto plano. El propietario eligió después AES-256-GCM; la versión plaintext no fue publicada. Consultar el último punto de control.

**Archivos nuevos:**
- `scripts/xray_profiles.py`
- `modules/profiles.sh`
- `tests/xray_profiles.sh`
- `docs/DISENO_IMPLEMENTACION_PERFILES.md`

**Archivos integrados/modificados:**
- `bin/xray-manager`
- `modules/main_menu.sh`
- `tests/stage1_menu.sh`
- `tests/smoke.sh`
- `PROJECT_STATE.md`
- `docs/CONTINUIDAD_DEL_PROYECTO.md`
- `docs/PUNTO_CONTROL_ACTUAL.md`
- `HISTORY.md`

**Funcionalidad presente en la primera iteración (histórico):** crear desde cero o JSON; consultar; modificar; duplicar; renombrar; listar revisiones y restaurar como revisión nueva. La persistencia plaintext fue sustituida antes de publicar por `config.enc.json` con AES-256-GCM. Eliminación deshabilitada.

**Validación:** sólo JSON estricto acreditado; validación nativa Xray no ejecutada (`xray_static=not_run`); estado `not_validated`. Estado activo `not_integrated`. No activar ni publicar runtime.

**Pruebas:** 51/51 scripts PASS; Python AST 18/18; `bash -n` global PASS; ShellCheck/shfmt focal PASS; `git diff --check` PASS.

**Límites:** pruebas en almacenes temporales; no se creó `/var/lib/xray-manager/profiles` ni perfil real. No se tocó `Prueba-VLESS-WS-Real`, `/etc/xray/config.json`, servicio Xray, systemd, firewall, puertos, certificados o red. No `master.key`. `Xray-Normativa/` y `main` intactas. Etapa 2 sigue ABIERTA.

**Siguiente acción histórica SUPERADA:** auditar diff/diseño y construir la validación estática Xray por revisión. Antes de iniciar esa implementación, el propietario debe revisar y aceptar formalmente (o devolver para ajustes) el subsistema v1.1. La siguiente acción vigente está registrada en el último punto de control de este documento.


## Almacén de perfiles v1.1 cifrado — 2026-11-03

**Decisión:** el propietario eligió AES-256-GCM para el almacenamiento de perfiles. No se autorizó la persistencia plaintext y esa primera versión local no se publicó.

**Implementación local actual:**
- `scripts/xray_profiles.py` cifra el JSON completo por revisión en `config.enc.json` con AES-256-GCM, nonce aleatorio de 12 bytes y AAD asociado a perfil/revisión.
- La clave se lee desde la clave maestra existente mediante el cargador seguro. No hay creación automática, regeneración ni fallback plaintext.
- Clave ausente/incorrecta, blob alterado, formato no reconocido o manifiesto plaintext: rechazo fail-closed.
- Las pruebas usan claves sintéticas temporales. Se cubre no exposición de un marcador secreto, descifrado, copia con nueva AAD, clave incorrecta, alteración GCM, no creación automática de clave, versionado y restauración no destructiva.
- El almacén live `/var/lib/xray-manager/profiles` no existe; no hay perfiles reales que migrar. No se leyó ni modificó la clave maestra real.
- Diseño técnico actualizado: `docs/DISENO_IMPLEMENTACION_PERFILES.md`.

**Verificación:** `tests/*.sh` 51/51 PASS; Python AST 18/18; `bash -n` global PASS; ShellCheck focal PASS; shfmt de los archivos nuevos PASS; `git diff --check` PASS.

**Siguiente paso:** el propietario revisa el diseño/implementación y decide si acepta el subsistema o solicita ajustes. No implementar validación Xray, composición integral, eliminación, registro activo ni activación hasta autorización/contraste específicos. No usar la clave maestra real en pruebas. No modificar `main` ni `Xray-Normativa/`. No tocar runtime, servicios, firewall, puertos, certificados o red. Etapa 2 continúa ABIERTA.


## Punto de control vigente — regularización documental y revisión formal de perfiles v1.1 (2026-11-03)

**Regularización de evidencia VMess TLS**

Se incorporó `docs/VALIDACION_LIVE_VMESS_TLS_LEASE_2026-11-03.md` a partir de las capturas compartidas por el propietario. Resultado confirmado: Xray-core 26.10.31, proceso real bajo UID 999/GID 988, lectura del certificado y clave sintéticos del lease y handshake TLS 1.3 verificado en la segunda ejecución. La primera ejecución no se contabiliza como PASS. No se dispone de la transcripción íntegra de comandos/logs, por lo que no se inventan ruta, puerto, SNI, cipher suite ni causa del primer fallo.

La evidencia no acredita `xray.service` administrado, runtime apply, activación de perfil, conectividad WAN ni aceptación formal de VMess. Etapa 2 permanece ABIERTA.

**Estado del almacén de perfiles v1.1**

- IMPLEMENTADO: `scripts/xray_profiles.py` y `modules/profiles.sh`, integrados en el menú.
- VERIFICADO: pruebas sintéticas registradas, 51/51 scripts PASS; AST 18/18; Bash syntax global; ShellCheck/shfmt focal; `git diff --check`.
- PUBLICADO/SINCRONIZADO: rama `design/user-identity-association-v1`, commits funcional y de reconciliación registrados en `PROJECT_STATE.md`; HEAD de partida previo a esta regularización: `b72d926dbfb7a57954d2c325405bf9e79e2fccee`.
- ACEPTADO: pendiente de decisión formal del propietario.
- Límites vigentes: no existe almacén live ni perfil real; no validación Xray por revisión; no composición integral; no registro activo; no activación/rollback; eliminación deshabilitada; sin rotación/recuperación de clave maestra.

**Siguiente acción vigente — revisión formal de solo lectura**

1. Contrastar el diseño y el código con Etapa 5 normativa y YAML.
2. Auditar `scripts/xray_profiles.py`, `modules/profiles.sh`, integración del menú y `tests/xray_profiles.sh`; revisar controles criptográficos, filesystem, atomicidad, concurrencia, errores, estados y operaciones.
3. Verificar qué requisitos están implementados, verificados, parciales, ausentes o divergentes; no confundir PASS sintéticos con validación live.
4. No modificar código ni ejecutar operaciones sobre almacenes/secretos reales durante esta revisión.
5. Presentar informe y solicitar decisión expresa del propietario sobre aceptación o correcciones.

`Xray-Normativa/` y `main` permanecen inmutables. No usar `master.key` real, no crear perfiles live, no activar runtime ni tocar servicios, firewall, puertos, certificados o red. Etapa 2 sigue ABIERTA.


## Punto de control vigente — perfiles v1.1 auditado; aceptación bloqueada (2026-11-03)

**Auditoría:** `docs/AUDITORIA_FORMAL_PERFILES_V1_1_2026-11-03.md`.

**Verificaciones ejecutadas en esta revisión:** `tests/xray_profiles.sh`, `tests/stage1_menu.sh`, `tests/smoke.sh`, Python AST, `bash -n`, ShellCheck focal y `git diff --check`: PASS. La suite histórica 51/51 no se volvió a ejecutar completa. La normativa 14/14 coincide por SHA-256 con la copia maestra.

**Bloqueos:**
- PF-01 BLOQUEANTE: `update()` puede persistir `metadata.json` y fallar al guardar `catalog.json`; fault injection temporal reprodujo una discrepancia que hace fallar `list_profiles()`.
- PF-02 ALTO: `create`, `duplicate`, `rename`, `update` y `restore` necesitan un contrato transaccional/durabilidad/recuperación multiarchivo probado ante write/replace/fsync/crash.

**Otros pendientes de Etapa 5:** preview/diff, validación Xray e informes, creación desde configuración independiente, comparación/retención/historial, registro activo, composición integral, activación/verificación/rollback y backup/restore. La eliminación sigue deshabilitada.

**Estado:** código sin cambios; implementación publicada/sincronizada; NO ACEPTADA formalmente. No se leyó `master.key`, no se creó almacén/perfil live, no se tocó runtime, servicios, firewall, puertos, certificados reales o red.

**Siguiente acción permitida:** solicitar decisión del propietario para autorizar una corrección acotada PF-01/PF-02, con diseño previo, pruebas de fault injection/crash recovery en almacén temporal y nueva auditoría. No implementar hasta recibir autorización expresa. Etapa 2 continúa ABIERTA.


## Punto de control — fase correctiva transaccional PF-01/PF-02 en curso

Autorización recibida. Implementación local: journal `.profiles.transaction.json`, snapshots previos de catálogo/metadatos, rutas permitidas, rollback idempotente y recuperación automática bajo lock. Integrado en create/duplicate/rename/update/restore.

Pruebas focales añadidas: fallo de creación del journal, fallo de catálogo, fsync posterior a replace, crash entre escrituras, crash tras ambos replaces, interrupción durante rollback, catálogo inicialmente ausente y recuperación al reabrir; limpieza de perfiles/revisiones no confirmados. `tests/xray_profiles.sh` PASS; regresión completa final 51/51 scripts PASS; Python AST, Bash syntax, ShellCheck focal y `git diff --check` PASS.

**No publicar todavía.** Siguiente: revisión detallada del diff, repetición de las 51 pruebas, estáticos, comprobar estado Git limpio tras retirar artefactos temporales y luego commit/push a `design/user-identity-association-v1`. No modificar main/normativa; no usar master.key real ni crear perfiles live.
## Punto de control vigente — fase de temporales huérfanos implementada (2026-11-04)

Rama: design/user-identity-association-v1
HEAD base: 3f8f88d8146409acfdf457529ce53075242a5bcd
Checkout: /opt/xray-manager en la VPS accesible por Termalin.

Implementación local:
- Recuperación WAL antes de cualquier limpieza, bajo lock exclusivo.
- Limpieza limitada a patrones/ubicaciones exactos para .new-*, .revision-* y temporales atómicos conocidos.
- lstat, root:root, permisos exactos, hardlinks y estructura acotada antes de borrar.
- Symlinks, permisos anómalos, propietarios/grupos incorrectos, hardlinks y contenido desconocido se conservan y reportan.
- atomic_write() limpia sólo su temporal si replace/fsync falla; nunca retira el destino.

Pruebas: suite completa 51/51 PASS; AST Python 18/18; Bash syntax; ShellCheck focal con exclusiones históricas SC2251/SC2034; shfmt focal; git diff --check. Incluye SIGKILL, idempotencia, anomalías de symlink/modo/owner/hardlink preservadas, revisión válida conservada y destino publicado intacto ante fallo de fsync. Todo en almacenes temporales y claves sintéticas.

Límites: no se leyó master.key; no se creó ni limpió almacén live; no runtime apply ni cambios en servicios, systemd, firewall, puertos, certificados o red. Xray-Normativa/ y main no se modifican.

Siguiente paso: revisión del diff, comprobar estado Git y publicar únicamente en design/user-identity-association-v1. La aceptación formal del almacén y el cierre de etapas siguen pendientes.
## Punto de control — WAL de perfiles endurecido (2026-11-04)

La recuperación WAL ahora valida íntegramente el journal antes de aplicar cualquier rollback. Se validan todas las rutas permitidas, duplicados, snapshots Base64 y límites, directorios padre, destinos existentes, directorios a retirar y ausencia de solapamientos. Si cualquier entrada es inválida, el journal se conserva y no se modifica ningún destino.

Pruebas nuevas demuestran que una entrada inválida tardía y una ruta de eliminación inválida no causan rollback parcial; el catálogo permanece byte a byte igual. La prueba focal `tests/xray_profiles.sh` PASS. PF-01/PF-02 se consideran corregidos dentro del alcance probado; PF-06 queda parcialmente cubierto y PF-07 sigue pendiente de revisión. Aceptación formal de perfiles pendiente; Etapa 5 y Etapa 2 abiertas.

No se usó `master.key`, no se creó ni modificó almacén live, y no se tocó runtime/servicios/firewall/puertos/certificados/red. `main` y `Xray-Normativa/` permanecen protegidas.

## Punto de control — PF-07 en implementación (2026-11-04)

Se endureció `ProfileStore.load_catalog()` con esquema estricto, tipos exactos, límite de registros, campos obligatorios/exclusivos, ID `profile-` + 32 hex, nombre normalizado sin controles, timestamps UTC válidos y orden cronológico; se rechazan duplicados. Los errores se convierten en `ProfileError` y el archivo inválido se conserva sin mutación.

La prueba focal `tests/xray_profiles.sh` pasó, incluidos 18 casos malformados con almacén temporal y clave sintética. Verificación final: 51/51 scripts, AST 18/18, bash -n, ShellCheck focal, shfmt y `git diff --check` PASS. Revisión final completada y cambios publicados/sincronizados en `design/user-identity-association-v1`, commit `85c637c93778780c98589dc2f791b190daeedfd6`; árbol Git limpio. No se usaron secretos ni almacén live; no se tocó runtime ni normativa.

## Correcciones PF-08/PF-09/PF-10 del almacén de perfiles — 2026-11-04

Autorización del propietario aplicada en la rama design/user-identity-association-v1, host Implementación-Xray, ruta /opt/xray-manager.

- PF-08: validación previa de tipos, límites y texto imprimible de descripción/notas; configuración validada antes de publicar una nueva revisión. Cuatro casos negativos verifican que no se crea revisión huérfana.
- PF-09: reconciliación bajo lock de revisiones definitivas posteriores al current_revision confirmado. Sólo se elimina una revisión con directorio/archivos seguros, contenido exacto y manifiesto coherente; artefactos no verificables se preservan y reportan.
- PF-10: contrato estricto de metadatos: conjunto exacto de campos, tipos no coercitivos, fechas UTC reales, límites y caracteres de texto, IDs de revisión y coherencia de estado/punteros.

Pruebas focales: tests/xray_profiles.sh PASS; PF-08 cuatro casos, PF-09 SIGKILL después del rename y recuperación en la siguiente operación, PF-10 dieciocho metadatos malformados rechazados. Python AST 18/18, py_compile del módulo modificado, bash -n global, ShellCheck focal y git diff --check PASS. shfmt -d -i 4 tests/xray_profiles.sh muestra diferencias de estilo preexistentes (indentación de bloques if en el archivo); no se reformateó el archivo completo para evitar cambios ajenos al alcance.

Informe: docs/AUDITORIA_CORRECCIONES_PF08_PF09_PF10_2026-11-04.md. Regresión general tests/*.sh finalizada: 51/51 scripts PASS (exit code 0).

Límites: sólo almacenes temporales y claves sintéticas. No se leyó master.key, no se crearon perfiles live, no se tocó runtime/servicios/certificados/firewall/puertos/red. Xray-Normativa/ y main intactas. No publicado en GitHub; publicación requiere autorización expresa posterior. Almacén v1.1 no aceptado formalmente; Etapa 5 y Etapa 2 siguen ABIERTAS.

Sincronización GitHub/VPS de desarrollo completada el 2026-11-04: commit 46444bcf11b41750d45f2187d77eeb5f7fce654c publicado en origin/design/user-identity-association-v1. El checkout /opt/xray-manager del host Implementación-Xray quedó en ese mismo commit, con árbol limpio. main y Xray-Normativa/ sin cambios.

## Punto de control vigente — PF-11/PF-12 implementados localmente (2026-11-04)

Rama: `design/user-identity-association-v1`
Base: `41309a45caa3c19cb86a697c41ec505c9e25678d`
Host/ruta: `Implementación-Xray` / `/opt/xray-manager`

- PF-11: validación estricta del manifiesto de cada revisión; campos exactos, tipos no coercitivos, fecha UTC, metadatos cifrados, tamaños, hash, procedencia y coherencia de estados.
- PF-12: recuperación segura de perfiles definitivos fuera del catálogo tras SIGKILL en create/duplicate. Sólo elimina candidato íntegro y verificable. Catálogo ausente/inseguro o perfil candidato ambiguo implica preservación, no borrado. `lstat` previo evita reparar permisos inseguros antes de preservarlos.
- Prueba focal `tests/xray_profiles.sh` PASS; 13 manifiestos malformados y escenarios crash/preservación PF-12 PASS.
- Regresión global `tests/*.sh`: **51/51 PASS**, exit code 0. Python AST, `bash -n`, ShellCheck focal y `git diff --check` PASS.
- Documentos: `docs/DISENO_IMPLEMENTACION_PERFILES.md` §16; `docs/AUDITORIA_CORRECCIONES_PF11_PF12_2026-11-04.md`.
- Árbol de trabajo aún local; sin commit/push. Antes de publicar: revisar diff completo, repetir estáticos, verificar `git status`, confirmar normativa protegida y comprobar que sólo se publica en esta rama.
- No se leyó `master.key`, no se creó perfil/almacén live, no se tocó runtime/servicios/certificados/firewall/puertos/red ni `Vps de Pruebas`. `Xray-Normativa/` intacta.
- Almacén v1.1 no aceptado formalmente. Etapa 5 y Etapa 2 ABIERTAS. La prueba integral VLESS WS TLS sigue condicionada a superar los puntos de control correspondientes.


## Punto de control — PF-06 pruebas complementarias verificadas (2026-11-04)

Se amplió `tests/xray_profiles.sh` sin modificar código de producción. La prueba GCM altera ciphertext y recalcula el hash del manifiesto, confirmando que AES-256-GCM rechaza el contenido adulterado. Se añadieron fallos inyectados de escritura parcial, fsync de archivo y unlink del WAL; se conservan pruebas de replace, fsync de directorio y crash recovery.

Resultados: suite focal PASS; regresión completa 51/51 PASS. PF-06 queda cerrado sólo dentro de los escenarios probados y documentados; no cubre todas las permutaciones ni fallos físicos del almacenamiento. Informe: `docs/AUDITORIA_PF06_COBERTURA_CRIPTO_FILESYSTEM_2026-11-04.md`; diseño §17.

Sólo pruebas/documentación; sin cambios de producción, dependencias, master.key, almacén live, runtime o VPS de pruebas. `main` y `Xray-Normativa/` intactas. Sin commit/push/sync. Aceptación del almacén v1.1 pendiente; Etapa 5 y Etapa 2 siguen ABIERTAS.

## Punto de control vigente — almacén de perfiles v1.1 aceptado con alcance limitado (2026-11-04)

**Decisión del propietario:** el almacén de persistencia de perfiles v1.1 queda **ACEPTADO FORMALMENTE COMO COMPONENTE LIMITADO**, conforme a la sección 14 de docs/AUDITORIA_FORMAL_PERFILES_V1_1_2026-11-03.md.

La aceptación comprende únicamente los contratos, controles y escenarios probados: cifrado/autenticidad AES-256-GCM; esquemas estrictos de catálogo, metadatos y manifiestos; revisiones; transacciones WAL y recuperación; reconciliación conservadora de artefactos huérfanos; controles de locking/filesystem; y las pruebas PF-01/PF-02 y PF-06 a PF-12 dentro de sus límites documentados.

**Etapa 5: ABIERTA. Etapa 2: ABIERTA.** No se declaran implementadas las funciones pendientes: preview/diff, creación desde configuración independiente, validación estática Xray por revisión, comparación de revisiones, historial/retención, registro y composición de perfil activo, eliminación segura integrada, activación/verificación/rollback y backup/restore integral.

No se afirma validación Xray, activación ni conectividad extremo a extremo. Las pruebas sintéticas no son cobertura combinatoria exhaustiva ni pruebas de fallos físicos. No se leyó master.key, no se tocó almacén live/runtime/servicios/red/certificados/firewall/puertos ni VPS de pruebas. main y Xray-Normativa/ intactas. Este registro es local: sin commit, push o sincronización.

## Diseño siguiente — configuraciones independientes (2026-11-04)

La normativa Etapa 5 §§2–5 y 14 fue contrastada con los módulos actuales. No hay gestor de configuraciones JSON independientes; VLESS/VMess persisten configuraciones por conexión y perfiles mantienen copias propias. No deben mezclarse.

Diseño propuesto: docs/DISENO_GESTOR_CONFIGURACIONES_INDEPENDIENTES.md. Define catálogo/objetos/revisiones separados, cifrado AES-256-GCM, WAL, importación/exportación, preview, diff/comparación, estados Borrador/Validada/Anterior y prohibición de activar desde este módulo. El validador estático será separado y sus informes quedarán ligados a hash/revisión. La futura creación de perfil copiará bytes sin sincronización.

**Estado: DISEÑO PROPUESTO; NO IMPLEMENTADO.** Siguiente autorización requerida: iniciar C-01 (contrato y persistencia) y C-02 (importación/exportación). No se modificó código funcional ni runtime; sin commit/push/sync. Etapa 5 y Etapa 2 ABIERTAS.

## Punto de control — C-01 del gestor de configuraciones independientes (2026-11-04)

`C-01` se implementó localmente en `scripts/xray_configurations.py`: almacén separado, `create` vacío/plantilla mínima, `list`, `show`, catálogo/metadatos/manifiesto estrictos, AES-256-GCM, AAD por ID/revisión, revisiones inmutables, lock y WAL recuperable. No se integró menú ni se modificaron los almacenes de perfiles o conexiones.

Pruebas focales PASS y regresión global `tests/*.sh` **52/52 PASS**. Se probaron claves sintéticas, ciphertext adulterado con hash recalculado y SIGKILL antes/durante/después de la publicación. Auditoría: `docs/AUDITORIA_C01_GESTOR_CONFIGURACIONES_2026-11-04.md`.

Estado: implementado y auditado localmente; **pendiente de aceptación**. C-02 (importación/exportación) no iniciada. Etapa 5 y Etapa 2 ABIERTAS. Sin clave real, almacén live, runtime, servicios, red, certificados, firewall o puertos; sin dependencias; `main`, `Xray-Normativa/` y VPS de pruebas intactas. Sin commit/push/sync.

## Punto de control — C-01 aceptado y C-02 implementado (2026-11-04)

C-01 del gestor independiente fue aceptado formalmente como componente limitado. C-02 se implementó localmente: `preview-import`, `import` y `export` en `scripts/xray_configurations.py`.

Importación: UTF-8 estricto, BOM detectado, origen regular sin symlink/hardlink, límite 16 MiB, lectura estable, SHA-256 de preview confirmado en import, conservación exacta de bytes, Borrador para JSON inválido/vacío sólo con aceptación explícita. Exportación: destino absoluto sin symlink/hardlink, confirmación de overwrite, temporal privado, modo 0600, fsync y verificación byte a byte. No se activa ni se escribe runtime.

Auditoría C-02: `docs/AUDITORIA_C02_IMPORTACION_EXPORTACION_2026-11-04.md`. C-02 implementado y pendiente de aceptación. La vista previa no equivale a validación estática Xray. C-03–C-06 pendientes; Etapa 5 y Etapa 2 ABIERTAS. Sólo claves sintéticas y almacenes temporales; no runtime, secretos, dependencias, VPS de pruebas, `main` o normativa. Sin commit/push/sync.


## Punto de control vigente — sincronización C-01/C-02 (2026-11-04)

C-01 del gestor independiente está aceptado formalmente como componente limitado. C-02 está implementado y auditado, pero sigue **pendiente de aceptación expresa**. Se sincronizan el motor `scripts/xray_configurations.py`, su suite `tests/xray_configurations.sh`, las auditorías C-01/C-02 y los documentos de estado/diseño/continuidad.

Verificación previa: regresión `tests/*.sh` **52/52 PASS**; `bash -n`, Python AST y `git diff --check` PASS. ShellCheck no está instalado y no se instalaron dependencias.

No iniciar C-03 sin aceptación y autorización específicas. No declarar completada Etapa 5 ni Etapa 2. No se modificaron runtime, servicios, certificados, firewall, puertos, red ni almacenes live; no se leyó `master.key`. La VPS de pruebas, `main` y `Xray-Normativa/` permanecen intactas.

La sincronización final se identifica en `PROJECT_STATE.md` y `HISTORY.md` una vez confirmado el commit de GitHub y el HEAD de `/opt/xray-manager`.


**Sincronización verificada (2026-11-04):** `3523368729a4e872d65dc7a37c8a2276a04f640e` en GitHub `origin/design/user-identity-association-v1` y en `Implementación-Xray:/opt/xray-manager`; push fast-forward, sin force, árbol limpio.

## Punto de control vigente — C-03 aceptada; C-04 pendiente de diseño (2026-11-04)

- C-01 y C-02 del gestor de configuraciones independientes: aceptadas formalmente como componentes limitados.
- C-03: aceptada formalmente como componente limitado. Auditoría: `docs/AUDITORIA_C03_EDICION_DIFF_COMPARACION_2026-11-04.md`.
- Operaciones: `preview-edit`, `edit`, `compare`, `revisions`. Revisión inmutable, AES-256-GCM, hash de preview, revisión base esperada, confirmación, WAL y recuperación SIGKILL. Diff estructural sin valores, comparación de solo lectura, preservación exacta UTF-8/BOM.
- Prueba focal PASS; `tests/*.sh` 53/53 PASS. Python compile, Bash syntax global, ShellCheck focal y `git diff --check` PASS. ShellCheck global mantiene diagnósticos preexistentes fuera de C-03.
- C-04–C-06 no iniciadas. Sin menú, validador Xray, promoción a Validada, eliminación, activación ni integración perfil. Etapa 5/Etapa 2 abiertas.
- No se leyó `master.key` ni se creó almacén live. Sin cambios en runtime, servicios, certificados, firewall, puertos, red, dependencias, VPS de pruebas, `main` o `Xray-Normativa/`.
- C-03 aceptada formalmente. La sincronización se registra en el bloque de publicación de este corte. C-04 requiere diseño, aprobación y autorización independientes.

**Decisión vigente del propietario (2026-11-04):** C-03 aceptada formalmente como componente limitado según su auditoría. Próximo trabajo propuesto: diseño de C-04; no implementarla hasta obtener aprobación y autorización explícitas. Etapa 5 y Etapa 2 siguen abiertas.

## Punto de control vigente — C-04A eliminación segura (2026-11-04)

- Aprobación del diseño C-04 recibida; autorización de implementación limitada a C-04A.
- scripts/xray_configurations.py: preview-delete y delete; verificación completa de objeto y revisiones, autenticidad AES-256-GCM, confirmación y nombre esperado.
- El borrado requiere --assert-not-active. El almacén independiente no verifica aplicaciones runtime manuales externas; preview informa runtime_activity_verified=false. La afirmación explícita del operador es obligatoria.
- WAL v2/tombstone: prepared revierte rename y catálogo; committed termina la limpieza. WAL v1 anterior sin cambios.
- Sólo se elimina el objeto independiente seleccionado; perfiles/copias y respaldos no se modifican.
- Prueba focal PASS; regresión 54/54 PASS; Python compile, Bash syntax, ShellCheck focal y git diff --check PASS.
- Auditoría: docs/AUDITORIA_C04A_ELIMINACION_SEGURA_2026-11-04.md.
- C-04A pendiente de aceptación formal. C-04B y C-04C no iniciadas. Etapa 5 y Etapa 2 ABIERTAS.
- Sin commit/push/sync. Sin acceso al almacén real ni clave maestra; sin runtime, servicios, dependencias, certificados, firewall, puertos, red o VPS de pruebas. main y Xray-Normativa/ intactas.


## Punto de control vigente — C-04A aceptada formalmente (2026-11-04)

- **Aceptación:** el propietario aceptó C-04A como componente limitado conforme a `docs/AUDITORIA_C04A_ELIMINACION_SEGURA_2026-11-04.md`.
- **Estado:** IMPLEMENTADA, VERIFICADA, AUDITADA, PUBLICADA y SINCRONIZADA.
- **Commit de implementación:** `afb2f7bf8cc040ca2731787b9e113b5a4660a00f` en `design/user-identity-association-v1`.
- **Evidencia:** `tests/xray_configurations_c04a.sh`; regresión completa 54/54 PASS; Python compile, Bash syntax, ShellCheck focal y `git diff --check` PASS, según auditoría.
- **Límite runtime:** el almacén independiente no verifica aplicaciones externas; `--assert-not-active` sigue siendo una afirmación explícita del operador, no una comprobación automática del runtime.
- **Pendiente:** C-04B y C-04C no autorizadas ni iniciadas. C-04, Etapa 5 y Etapa 2 no están cerradas.
- **Exclusiones:** no se tocó clave maestra real, almacén live, runtime, servicios, certificados, firewall, puertos, red, dependencias, VPS de pruebas, `main` ni `Xray-Normativa/`.

## Punto de control vigente — C-04B implementada y verificada localmente (2026-11-04)

- C-01/C-02/C-03: aceptadas formalmente como componentes limitados.
- C-04A: aceptada formalmente, publicada y sincronizada en commit `afb2f7bf8cc040ca2731787b9e113b5a4660a00f`.
- C-04B: autorización expresa recibida; `preview-export-batch` y `export-batch` implementados en `scripts/xray_configurations.py`.
- El manifiesto es JSON estricto, 1–100 entradas, root:root 0600, sin symlink/hardlink. Cada salida define configuración, revisión o `null`, destino absoluto y overwrite booleano.
- Preview devuelve hash del manifiesto y hash del preview. Ejecución requiere ambos hashes y `--confirm`; vuelve a construir el preview para impedir exportar una revisión distinta a la revisada. Destinos repetidos bloquean todas las entradas involucradas.
- Exportación por elemento reutiliza el writer individual con permisos 0600, escritura atómica y verificación byte a byte. Los fallos individuales no cancelan las demás salidas; se devuelven contadores y resultados por elemento.
- Prueba focal `tests/xray_configurations_c04b.sh`: PASS. Regresión integral final `tests/*.sh`: **55/55 PASS**. Python compile, Bash syntax global, ShellCheck focal y `git diff --check`: PASS.
- Auditoría: `docs/AUDITORIA_C04B_EXPORTACION_MULTIPLE_2026-11-04.md`.
- Estado C-04B: IMPLEMENTADA/VERIFICADA LOCALMENTE; pendiente de aceptación formal. C-04C (menú Bash) no autorizada ni iniciada. C-04 no está completa. Etapa 5 y Etapa 2 siguen ABIERTAS.
- Sólo pruebas temporales y claves sintéticas. No se leyó clave maestra real ni se accedió al almacén real. Sin cambios en runtime/servicios/certificados/firewall/puertos/red/dependencias/VPS de pruebas/`main`/`Xray-Normativa/`. Sin commit/push/sync.

## Punto de control vigente — C-04B aceptada formalmente (2026-11-04)

- **Aceptación:** el propietario aceptó formalmente C-04B como componente limitado conforme a `docs/AUDITORIA_C04B_EXPORTACION_MULTIPLE_2026-11-04.md`.
- **Estado:** IMPLEMENTADA, VERIFICADA y ACEPTADA LOCALMENTE.
- **Evidencia:** `tests/xray_configurations_c04b.sh` PASS; regresión completa 55/55 PASS; Python compile, Bash syntax global, ShellCheck focal y `git diff --check` PASS.
- **Pendiente:** C-04C (integración del menú Bash). Esta fase requiere autorización específica antes de iniciar implementación.
- **Publicación:** no se hizo commit, push ni sincronización; la aceptación de C-04B no autoriza esas acciones.
- **Exclusiones:** no se modificaron `main`, `Xray-Normativa/`, runtime, servicios, dependencias, certificados, firewall, puertos, red ni VPS de pruebas.
- C-04, Etapa 5 y Etapa 2 permanecen ABIERTAS.


## Punto de control vigente — C-04C integrada y auditada localmente (2026-11-04)

- Autorización: el propietario autorizó C-04C limitada a integrar el gestor independiente con el menú Bash, después de publicar C-04B.
- C-04B: publicada y sincronizada en 0f8ea9df5fa4927c27deafab405c446f1c4dc4dd.
- Integración: bin/xray-manager carga modules/xray_configurations_menu.sh; modules/profiles.sh enruta la opción [1] Gestionar configuraciones de Xray; config/paths.sh declara las rutas del almacén y la clave maestra existente.
- Operaciones: consulta, creación, edición, importación, exportación individual/múltiple, comparación, historial de revisiones y eliminación. No hay apply/activate. Mostrar contenido descifrado exige confirmación; eliminar requiere preview y doble confirmación.
- Pruebas: tests/xray_configurations_menu.sh, tests/smoke.sh y tests/stage1_menu.sh PASS. Regresión completa tests/*.sh: 56/56 PASS. Bash syntax global, ShellCheck focal, Python compile y git diff --check PASS.
- Auditoría: docs/AUDITORIA_C04C_INTEGRACION_MENU_BASH_2026-11-04.md.
- Estado: C-04C IMPLEMENTADA, VERIFICADA y AUDITADA LOCALMENTE; pendiente de aceptación formal. Sin commit/push/sync.
- Exclusiones: sólo almacén temporal y clave sintética en pruebas. No se leyó clave maestra real ni se accedió al almacén live. Sin cambios en runtime, servicios, dependencias, certificados, firewall, puertos, red, VPS de pruebas, main o Xray-Normativa/.
- C-04 completa, Etapa 5 y Etapa 2 permanecen ABIERTAS.


## Aceptación formal C-04C y publicación autorizada — 2026-11-04

- C-04C aceptada formalmente conforme a `docs/AUDITORIA_C04C_INTEGRACION_MENU_BASH_2026-11-04.md`.
- Publicación autorizada expresamente: implementación, prueba, auditoría y registro de aceptación, sólo en `design/user-identity-association-v1`.
- No se autoriza C-05 ni se cierra C-04 completa, Etapa 5 o Etapa 2.
- `main`, `Xray-Normativa/`, runtime, servicios e infraestructura permanecen fuera del alcance.


## Decisión vigente — cierre integral C-04 aceptado (2026-11-04)

- **Aceptación:** el propietario acepta formalmente el cierre integral de C-04.
- **Alcance completado:** C-04A eliminación segura, C-04B exportación múltiple y C-04C integración del menú Bash.
- **Evidencia:** auditorías individuales y auditoría integral; regresión completa **56/56 PASS**; verificaciones estáticas documentadas PASS; ningún defecto funcional bloqueante identificado.
- **Publicación previa:** correcciones documentales publicadas en `7f215b1dbfaa0b2dc7a2a3726a76dfa25b1cbb10`. Este registro de aceptación es un cambio documental posterior, aún local y sin commit/push.
- **Siguiente control:** definir el alcance de la siguiente fase y solicitar autorización específica antes de iniciar C-05.
- **Límites:** C-05 no autorizada ni iniciada. Etapa 5 y Etapa 2 permanecen ABIERTAS. `main`, `Xray-Normativa/`, runtime, servicios e infraestructura no se modifican.


## Punto de control vigente — C-05A/C-05B aceptadas y publicadas (2026-11-04)

- **C-05A — motor de validación:** aceptada formalmente como componente limitado. Implementación `scripts/xray_config_validator.py`; auditoría `docs/AUDITORIA_C05A_MOTOR_VALIDACION_2026-11-04.md`.
- **C-05B — almacén de informes:** aceptada formalmente. Implementación `scripts/xray_validation_store.py`; auditoría `docs/AUDITORIA_C05B_ALMACEN_INFORMES_2026-11-04.md`. Informes permanentes, inmutables, con catálogo SHA-256, controles filesystem, lock y WAL.
- **Pruebas:** 25/25 pruebas Python C-05A/B PASS; regresión shell de C-01/C-02, C-03, C-04A/B/C y smoke general PASS; Python compile, `bash -n modules/*.sh` y `git diff --check` PASS.
- **Publicación de código:** commit `0b0e36e53dbc58c2102805834c2ffc1a5edd6b25`, ocho archivos nuevos C-05A/B.
- **Sincronización inicial:** GitHub y `/opt/xray-manager` se verificaron en el mismo commit después del push; árbol limpio. La actualización de este punto de control se publica en un commit documental posterior.
- **Siguiente fase:** C-05C promoción controlada al estado Validada. NO autorizada ni iniciada. C-05D historial/comparación, C-05E menú y C-05F auditoría integral también requieren autorizaciones independientes.
- **Límites:** C-05B aún no se integra con el motor ni modifica estado Validada; no se creó `/var/lib/xray-manager/validation`. No se leyó la clave maestra real ni se tocaron runtime, servicios, certificados, firewall, puertos, dependencias o configuración activa.
- `main` y `Xray-Normativa/` permanecen intactas. Etapa 5 y Etapa 2 siguen ABIERTAS.


## Verificación documental previa a reanudar — 2026-11-04

Los documentos de continuidad y diseño se actualizaron para reflejar C-05A/C-05B aceptadas, publicadas y sincronizadas. Los expedientes de implementación/auditoría C-05A/B recibieron addenda que distinguen su estado histórico prepublicación de la publicación posterior. El HEAD verificado antes de esta actualización fue 1815663438770a2271d769345adbc271714a6817. La siguiente fase sigue siendo C-05C, no autorizada ni iniciada; no iniciar sin autorización expresa.


## Punto de control vigente — C-05C implementada y auditada localmente (2026-11-04)

- **Autorización recibida:** implementar exclusivamente C-05C, con pruebas, auditoría técnica y documentación. Publicación/sincronización expresamente excluidas.
- **Base:** `6ab158f436d2d88755d70e954114efb4fa2f6129`, rama `design/user-identity-association-v1`.
- **Implementación:** `scripts/xray_config_promotion.py`; cambios de estado/versionado en `scripts/xray_configurations.py`; suite `tests/test_xray_config_promotion.py`.
- **Documentación:** `docs/IMPLEMENTACION_C05C_PROMOCION_VALIDADA_2026-11-04.md`; auditoría `docs/AUDITORIA_C05C_PROMOCION_VALIDADA_2026-11-04.md`.
- **Resultado:** C-05C focal 13/13 PASS; regresión Python C-05A/B/C 38/38 PASS; shell C-01/C-02, C-03, C-04A/B/C y perfiles PASS; prueba real Xray 26.10.31 PASS con almacenes temporales.
- **Estado:** IMPLEMENTADA, VERIFICADA y AUDITADA LOCALMENTE; pendiente de aceptación formal. Sin commit, push ni sincronización.
- **Siguiente acción:** revisión del expediente y decisión expresa del propietario. No iniciar C-05D (historial), C-05E (menú) ni C-05F (auditoría integral) sin autorización independiente.
- **Seguridad:** almacenes live ausentes; clave maestra real no leída; sin dependencias instaladas/actualizadas ni cambios runtime/servicios/infraestructura. `main`, `Xray-Normativa/` y VPS de pruebas intactas.
- Etapa 5 y Etapa 2 permanecen ABIERTAS.


## Punto de control vigente tras publicación C-05C — 2026-11-04

- C-05C aceptada formalmente y publicada en `design/user-identity-association-v1`.
- Implementación: `scripts/xray_config_promotion.py`; metadatos: `scripts/xray_configurations.py`; pruebas: `tests/test_xray_config_promotion.py`.
- Auditoría focal: 13/13 PASS; regresión Python C-05A/B/C: 38/38 PASS; regresiones shell previas: PASS.
- La publicación se realizó mediante commit normal y push fast-forward. No se hizo force push.
- Siguiente fase posible: C-05D (historial/comparación), pendiente de autorización independiente. C-05E/F también requieren autorizaciones propias.
- Etapa 5 y Etapa 2 permanecen ABIERTAS.
- No se crearon almacenes live ni se leyó clave maestra real. No hubo cambios de runtime/infraestructura, `main`, `Xray-Normativa/` ni VPS de pruebas.

**SHA publicado C-05C:** `58c273a18ea32c1feddc02012d0318952c7a0689` (`58c273a`), rama `design/user-identity-association-v1`; push fast-forward y sincronización del checkout de desarrollo verificados.

## Addendum de punto de control — recuperación C-05C (2026-11-04)

**Estado vigente verificado:** C-05A, C-05B y C-05C aceptadas, auditadas, publicadas y sincronizadas. C-05D (historial/comparación), C-05E (menú Bash) y C-05F (auditoría integral) siguen sin autorización independiente. Etapa 5 y Etapa 2 permanecen ABIERTAS.

**Git:** /opt/xray-manager está en design/user-identity-association-v1, HEAD 670e6ab371e620a8cb8b51f9431746f0a2270cda, árbol limpio. GitHub confirma el mismo HEAD. main permanece en 656ecedc506a94a6461aee296b20871d51a38bf3. Un primer git ls-remote origin falló, pero el diagnóstico de autenticación SSH RW/RO y una repetición de git ls-remote fueron satisfactorios. No se modificó la configuración SSH ni el remoto. La referencia local origin/main no está creada; la rama remota fue confirmada por GitHub.

**Normativa:** SHA-256 del Markdown y YAML de Etapa 5 coinciden con la copia aprobada en /root/Xray_Manager_Documentacion_Final_2026-10-31. Xray-Normativa/ permanece intacta.

**Lectura de la cronología:** las entradas anteriores que muestran C-05C pendiente de aceptación/publicación corresponden a estados históricos previos. Prevalece este addendum y el registro posterior de aceptación/publicación C-05C; no se deben interpretar los bloques antiguos como el estado actual.

**Siguiente actividad permitida:** preparar, sin implementar, el diseño técnico y la matriz de pruebas de C-05D para revisión del propietario. La implementación C-05D requiere autorización expresa independiente. No hay autorización para C-05E/F, publicación, runtime ni infraestructura.

## Registro de implementación C-05D — 2026-11-04

El propietario autorizó C-05D: historial y comparación de informes de validación. Se implementó exclusivamente el servicio read-only `scripts/xray_validation_history.py` y su suite `tests/test_xray_validation_history.py`; se añadieron los documentos de implementación y auditoría. La modalidad aprobada es comparación de informes de una misma configuración, permitiendo revisiones distintas y rechazando configuraciones diferentes.

Verificación local: C-05D focal H01–H38 38/38 PASS; regresión Python C-05A/B/C/D 76/76 PASS; suites shell existentes 56/56 PASS; `py_compile`, `bash -n`, `install.sh --check`, ShellCheck severidad error y `git diff --check` PASS. ShellCheck en severidad warning informa cuatro advertencias preexistentes en tests/stage1_header.sh (SC2034, dos), tests/uninstall.sh (SC2154) y tests/vless_backup_restore.sh (SC2174); no se modificaron por estar fuera del alcance.

El servicio consulta el almacén C-05B bajo su lock, valida fechas ISO-8601 con zona horaria, ofrece filtros/paginación, detalle y comparación estructurada. No modifica informes/catálogo ni el esquema C-05B. Prueba WAL con SIGKILL, integridad, concurrencia, saneamiento y solo lectura PASS.

Estado: C-05D IMPLEMENTADA, VERIFICADA Y AUDITADA LOCALMENTE; PENDIENTE DE ACEPTACIÓN FORMAL; NO PUBLICADA NI SINCRONIZADA. No se creó commit ni push. C-05E y C-05F siguen sin autorización; Etapa 5 y Etapa 2 permanecen ABIERTAS. No se modificaron main, Xray-Normativa/, almacenes live, clave maestra real, runtime, servicios, dependencias, certificados, firewall, puertos, red ni VPS de pruebas.


## Aceptación formal y publicación C-05D — 2026-11-04

El propietario aceptó formalmente C-05D y autorizó crear el commit y publicar exclusivamente en `design/user-identity-association-v1`. La aceptación cubre el servicio de historial/comparación, sus pruebas focales y la auditoría documentada. C-05D queda ACEPTADA; C-05E y C-05F continúan sin autorización independiente. Etapa 5 y Etapa 2 permanecen ABIERTAS.


## Punto de control vigente — C-05E implementada y auditada localmente (2026-11-04)

- **Autorización:** el propietario aprobó el diseño C-05E y autorizó expresamente implementación completa, pruebas, auditoría y documentación; commit/push excluidos.
- **Base:** `ed700c1e770063f6e67c6ebaeae4652172bb2f02`, rama `design/user-identity-association-v1`.
- **Implementación:** `modules/xray_validation_menu.sh`; CLI read-only añadida a `scripts/xray_validation_history.py`; integración en `modules/profiles.sh`, `bin/xray-manager` y `config/paths.sh`.
- **Pruebas:** focal C-05E PASS; Python C-05A/B/C/D 76/76 PASS; shell 57/57 PASS; `bash -n`, ShellCheck severidad error, `install.sh --check` y `git diff --check` PASS.
- **Documentación:** `docs/IMPLEMENTACION_C05E_MENU_BASH_2026-11-04.md`; `docs/AUDITORIA_C05E_MENU_BASH_2026-11-04.md`; diseño actualizado.
- **Estado:** IMPLEMENTADA, VERIFICADA y AUDITADA LOCALMENTE; pendiente de aceptación formal. Sin commit, push ni sincronización.
- **Siguiente acción:** revisión del expediente y decisión expresa del propietario. No iniciar C-05F ni publicar sin autorización separada.
- **Límites:** no se creó almacén live ni se leyó la clave maestra real; no hubo cambios de runtime, servicios, certificados, firewall, puertos, red o dependencias. `main`, `Xray-Normativa/` y VPS de pruebas permanecen intactas.
- Etapa 5 y Etapa 2 permanecen ABIERTAS.

## Punto de control vigente — C-05E aceptada formalmente (2026-11-04)

- **Decisión:** el propietario aceptó formalmente C-05E — Integración del menú Bash.
- **Evidencia:** `docs/IMPLEMENTACION_C05E_MENU_BASH_2026-11-04.md` y `docs/AUDITORIA_C05E_MENU_BASH_2026-11-04.md`; la auditoría conserva la trazabilidad real de E01–E38 y sus estados PASS/PARCIAL/PENDIENTE/regresión.
- **Estado funcional:** C-05E ACEPTADA. C-05A/B/C/D continúan aceptadas y publicadas.
- **Git:** cambios C-05E siguen sin commit ni push, en `design/user-identity-association-v1`, sobre base `ed700c1e770063f6e67c6ebaeae4652172bb2f02`.
- **Publicación:** pendiente de autorización independiente; no hacer commit, push ni sincronización todavía.
- **Siguiente paso:** obtener decisión expresa sobre publicación de C-05E. C-05F requiere autorización independiente y no se ha iniciado.
- **Protecciones:** `main`, `Xray-Normativa/`, VPS de pruebas, secretos, almacenes live, runtime e infraestructura no se modifican.
- **Etapas:** Etapa 5 y Etapa 2 permanecen ABIERTAS.

## Punto de control vigente — C-05E publicada y sincronizada (2026-11-04)

- **Estado C-05E:** ACEPTADA, AUDITADA, PUBLICADA y SINCRONIZADA.
- **Rama:** `design/user-identity-association-v1`.
- **Commit:** `8378ca47a751678f4eeeab20a5e2d06effd47fff` (`feat(validation): integrate C-05E validation menu`).
- **Sincronización:** push fast-forward desde `ed700c1e770063f6e67c6ebaeae4652172bb2f02`; SHA remoto verificado con `git ls-remote`.
- **main:** SHA remoto `656ecedc506a94a6461aee296b20871d51a38bf3`, sin cambios.
- **Siguiente decisión:** C-05F no está autorizada ni iniciada; requiere autorización expresa independiente.
- **Protecciones:** `Xray-Normativa/`, VPS de pruebas, secretos, almacenes live, runtime e infraestructura no fueron modificados.
- **Etapas:** Etapa 5 y Etapa 2 permanecen ABIERTAS.

## Punto de control — diseño C-05F preparado (2026-11-04)

- **Trabajo autorizado:** preparar diseño técnico y matriz de C-05F. No se ha autorizado todavía ejecutar la auditoría ni corregir/implementar hallazgos.
- **Documentos:** `docs/DISENO_C05F_AUDITORIA_INTEGRAL_2026-11-04.md` y `docs/MATRIZ_C05F_AUDITORIA_INTEGRAL_2026-11-04.md`.
- **Alcance propuesto:** auditoría transversal C-05A–C-05E del subsistema de validación Xray; no cierra ni audita integralmente toda Etapa 5.
- **Matriz:** F01–F71 y G01–G15; todos pendientes de ejecución o decisión.
- **Decisiones requeridas:** confirmar alcance del subsistema C-05A–E; confirmar que validación externa/activa deshabilitadas se documenten como divergencias sin implementarlas en C-05F; confirmar que las correcciones de hallazgos requieren autorización separada.
- **Estado Git:** documentos locales sin commit/push; rama autorizada y base publicada `a4f2c6356652e04206918c410ddf3f6aa3181808`.
- **Protecciones:** no se modificaron código, pruebas, `main`, `Xray-Normativa/`, secretos, almacenes live, runtime, infraestructura ni VPS de pruebas.

## Punto de control — C-05F ejecutada, pendiente de aceptación (2026-11-04)

- C-05F fue autorizada bajo las tres condiciones aprobadas y ejecutada localmente.
- Expediente: docs/AUDITORIA_C05F_AUDITORIA_INTEGRAL_2026-11-04.md.
- Matriz final: docs/MATRIZ_C05F_AUDITORIA_INTEGRAL_2026-11-04.md.
- Resultado: PASS técnico con H-01 de baja severidad y divergencias D-01–D-05.
- Python 76/76 PASS; shell 57/57 PASS; flujo integral A→E con Xray real y almacenes temporales PASS; cuatro validaciones concurrentes PASS.
- H-01: symlink roto en componente padre de la ruta CLI se interpreta como almacén ausente; no corregido, requiere autorización separada.
- D-01/D-02: validación externa y activa deshabilitadas respecto de normativa. D-03: prueba runtime pendiente. D-04: backup/restore fuera del alcance C-05F. D-05: filtros UI parciales frente a CLI.
- No se modificó código ni normativa; no commit/push. Rama y HEAD siguen en a4f2c6356652e04206918c410ddf3f6aa3181808.
- main, Xray-Normativa/, clave maestra real, almacenes live, runtime/infraestructura y VPS de pruebas intactos.
- **Siguiente control:** revisión del propietario y aceptación formal C-05F. Correcciones solo con autorización independiente. Etapa 5 y Etapa 2 continúan abiertas.


## Punto de control vigente — C-05F aceptada formalmente (2026-11-04)

- **Decisión del propietario:** C-05F ACEPTADA FORMALMENTE, incluyendo dictamen PASS, H-01 y D-01–D-05.
- **Expediente:** docs/AUDITORIA_C05F_AUDITORIA_INTEGRAL_2026-11-04.md.
- **Matriz final:** docs/MATRIZ_C05F_AUDITORIA_INTEGRAL_2026-11-04.md.
- **H-01:** abierto, no corregido; requiere autorización separada.
- **D-01–D-05:** permanecen como divergencias/pendientes documentados; aceptación no los resuelve ni autoriza implementarlos.
- **Git:** cambios de aceptación exclusivamente documentales, locales, rama design/user-identity-association-v1, base HEAD a4f2c6356652e04206918c410ddf3f6aa3181808. Sin commit, push ni sincronización autorizados.
- main, Xray-Normativa/, runtime, infraestructura, secretos, almacenes live y VPS de pruebas permanecen fuera del alcance.
- **Etapas:** Etapa 5 y Etapa 2 siguen ABIERTAS.

## Punto de control vigente — H-01 corregido (2026-11-04)

- C-05F permanece ACEPTADA FORMALMENTE.
- H-01: CORREGIDO Y VERIFICADO mediante lstat() en cada componente de la ruta CLI del almacén.
- Pruebas: H39–H42; historial 42/42; Python 80/80; shell 57/57; verificaciones estáticas y install.sh --check PASS.
- Evidencia: docs/CORRECCION_H01_RUTAS_SYMLINK_C05F_2026-11-04.md.
- D-01–D-05 siguen documentados y sin resolver. No se ha autorizado implementar validación externa/activa, mecanismo runtime ni ampliaciones UI.
- Etapa 5 y Etapa 2 siguen ABIERTAS.


## Punto de control vigente — U-01 Usuarios V2 → VLESS (2026-11-04)

- **Autorización:** el propietario aprobó el diseño U-01 y autorizó su implementación con el alcance descrito.
- **Base:** `ca6d76895821310a3072d9de47268f925ecea7ba`, rama `design/user-identity-association-v1`.
- **Implementación:** `users_v2_export_vless_candidate_clients` separa candidato de runtime; el asistente VLESS usa exclusivamente Usuarios V2 para crear y reconstruir modelos; el menú V2 ofrece UUID automático predeterminado o manual oculto.
- **Pruebas:** 58/58 scripts shell PASS. Xray-core 26.10.31 real acepta una configuración VLESS-WS con asociación V2 active/draft/not_applied. `bash -n`, `py_compile`, `install.sh --check`, ShellCheck -S error, shfmt y `git diff --check`: PASS.
- **Documentación:** `docs/IMPLEMENTACION_U01_INTEGRACION_USUARIOS_V2_VLESS_2026-11-04.md`; `docs/AUDITORIA_U01_INTEGRACION_USUARIOS_V2_VLESS_2026-11-04.md`; `docs/DISENO_IDENTIDADES_ASOCIACIONES_V1.md` actualizado.
- **Estado:** IMPLEMENTADA, VERIFICADA, AUDITADA, PUBLICADA y SINCRONIZADA; aceptación formal pendiente. Commit `1c2cd12f15be75d9f3a080ce028951724618c492`.
- **Siguiente paso:** solicitar aceptación formal de U-01. Después diseñar el mecanismo de aplicación runtime segura y obtener autorización independiente.
- **Fuera de alcance:** migración/cutover legacy, ACME/Cloudflare DNS-01, publicación runtime, inicio de Xray, certificados desplegados, firewall, puertos, red, dependencias, VPS de pruebas.
- `main`, `Xray-Normativa/` y la clave maestra real permanecen intactas. Etapa 2, Etapa 3 y Etapa 5 no quedan cerradas.


## Addendum de publicación U-01 — 2026-11-04

U-01 está PUBLICADA y SINCRONIZADA en `design/user-identity-association-v1`. Commit: `1c2cd12f15be75d9f3a080ce028951724618c492` (`feat(vless): integrate V2 users into candidate generation`), push fast-forward desde `ca6d76895821310a3072d9de47268f925ecea7ba`. La consulta posterior confirmó el SHA remoto. Aceptación formal pendiente. `main` y `Xray-Normativa/` permanecen intactas.


## Punto de control vigente — U-01 aceptada; diseño runtime preparado (2026-11-04)

- **Decisión del propietario:** U-01 y su auditoría ACEPTADAS FORMALMENTE.
- **Publicación:** rama `design/user-identity-association-v1`, commit remoto/local verificado `bcb3338a527e3f4021489815d92797b9a59fdd62`; árbol limpio antes de este registro. `main` y `Xray-Normativa/` permanecen intactas.
- **Diseño siguiente:** `docs/DISENO_APLICACION_RUNTIME_XRAY_2026-11-04.md`, propuesta pendiente de revisión y autorización de implementación.
- **Principio de seguridad:** ninguna revisión se aplica por el mero hecho de estar validada. Se requiere revisión/hash exacto, staging con lease TLS, validación como usuario de servicio, snapshot/journal, publicación atómica, restart systemd, verificación posterior y rollback recuperable.
- **Decisiones pendientes:** estrategia restart vs hot reload; primera aplicación sin config previa; restauración del estado previo del servicio; señales locales de verificación; alcance R-01–R-05 aislado y R-06 live.
- **No autorizado/ejecutado:** implementación runtime, escritura de `/etc/xray/config.json`, restart/start Xray, ACME/Cloudflare, instalación de dependencias, firewall/puertos/red, VPS de pruebas o prueba NetMod.
- **Etapas:** U-01 aceptada; Etapas 2, 3 y 5 siguen ABIERTAS. La prueba real VLESS-WS-TLS aún no está hecha.


## Decisiones aprobadas — aplicación runtime (2026-11-04)

- El propietario aprobó `systemctl restart xray.service` como mecanismo inicial de aplicación controlada; no se presupone hot reload.
- El propietario aprobó rollback de configuración y recuperación del estado previo del servicio: activo permanece activo; inactivo permanece inactivo.
- Si no existe configuración anterior, la operación se detiene en estado de recuperación explícito; no crea placeholder ni arranca Xray.
- Diseño actualizado: `docs/DISENO_APLICACION_RUNTIME_XRAY_2026-11-04.md`.
- **No implica autorización de implementación** R-01–R-05 ni ensayo live R-06. Siguen pendientes primera aplicación sin config, señales locales de verificación y alcance de incrementos aislados/live.
- Runtime, servicios, certificados desplegados, firewall, puertos, red y VPS de pruebas no fueron modificados.


## Punto de control vigente — R-01 publicada; siguiente R-02 (2026-11-04)

- **Autorización:** R-01–R-05 exclusivamente en entornos aislados. R-06/live requiere autorización nueva y específica. Identidad obligatoria: profile_id + revision.
- **R-01:** IMPLEMENTADA, INTEGRADA EN CLI/MENÚ, VERIFICADA EN FIXTURES, AUDITADA LOCALMENTE, PUBLICADA y SINCRONIZADA. Aceptación formal de R-01 pendiente.
- **Implementación:** scripts/xray_profile_validation_store.py, scripts/xray_profile_validation.py, scripts/xray_runtime_preflight.py; opción 8 en modules/profiles.sh; transacciones de manifiesto/metadata en scripts/xray_profiles.py; ruta en config/paths.sh.
- **Diseño y expedientes:** docs/DISENO_APLICACION_RUNTIME_XRAY_2026-11-04.md; docs/IMPLEMENTACION_R01_PREFLIGHT_PERFIL_2026-11-04.md; docs/AUDITORIA_R01_PREFLIGHT_PERFIL_2026-11-04.md.
- **Pruebas:** focal R-01 28/28 PASS (preflight 18/18 + validación 11/11); Python 108/108 PASS; shell 58/58 PASS. py_compile, bash -n global, ShellCheck focal, install.sh --check y git diff --check PASS.
- **Publicación de código:** c605b3efc904d75a142e9e8c539210eb65070acd. Registro de publicación/continuidad previo: 856662b0981ad4457f4e4bba72c41735e998f958; reconciliación documental: 94556849316852625fbcf98d8ea0796600097088. Comprobar siempre el HEAD remoto real.
- **Límites verificados:** pruebas solo con perfiles/keys/binarios sintéticos y temporales; no se ejecutó contra almacén/clave reales ni systemd real. La validación nativa todavía corre con identidad del llamador; validación de leases y permisos efectivos de xray corresponde a R-02.
- **Siguiente paso permitido:** R-02 — staging integrado de la revisión exacta del perfil y leases TLS en directorio temporal, validación bajo identidad de servicio simulada. Mantener sin publicación runtime.
- **No autorizado:** R-06/live; cambios en Xray real, /etc/xray/config.json, systemd real, runtime, certificados desplegados, firewall, puertos, red, dependencias, VPS de pruebas, main o Xray-Normativa/.
- **Etapas:** Etapas 2, 3 y 5 siguen ABIERTAS.

## Punto de control vigente — R-02 implementada y auditada localmente (2026-11-04)

- R-01: publicada/sincronizada; aceptación formal específica pendiente.
- R-02: IMPLEMENTADA, VERIFICADA y AUDITADA LOCALMENTE; pendiente de aceptación formal/publicación.
- Contrato aprobado: mapa explícito inbound tag → connection_id. El mapa debe cubrir todos los inbounds TLS exactamente una vez. El certificado se obtiene del almacén central; no se aceptan rutas PEM libres.
- Implementación: scripts/xray_runtime_staging.py. Pruebas: tests/test_xray_runtime_staging.py.
- Expedientes: docs/IMPLEMENTACION_R02_STAGING_PERFIL_TLS_2026-11-04.md; docs/AUDITORIA_R02_STAGING_PERFIL_TLS_2026-11-04.md; diseño actualizado en docs/DISENO_APLICACION_RUNTIME_XRAY_2026-11-04.md.
- Resultados: focal R-02 9/9 PASS; Python 117/117 PASS; shell 58/58 PASS; py_compile, bash -n global, install.sh --check, ShellCheck -S error en tests/*.sh y git diff --check PASS.
- Xray real: Xray-core 26.10.31 aceptó configuración staged con lease sintético y pudo leer certificado/clave bajo UID/GID simulado 65534:65534. No se ejecutó systemd real ni se inició/reinició Xray.
- Límite: el mapa es un archivo de operación separado, cuyo hash y contenido se fijan en el manifiesto staged; no es todavía un recurso editable/persistido en UI de perfiles. R-03 debe integrar su identidad y los leases en snapshot/journal.
- Git: R-02 permanece local, sin commit/push. Solicitar aceptación formal y autorización de publicación.
- Siguiente paso tras aceptación: R-03 — snapshot, journal, recuperación simulada y matriz de interrupciones.
- Fuera de alcance: R-06/live, /etc/xray/config.json, systemd real, runtime, almacenes/clave/certificados reales, firewall, puertos, red, dependencias y VPS de pruebas.
- Etapas: 2, 3 y 5 ABIERTAS.

## Punto de control vigente — R-03 snapshot/journal local (2026-11-04)

- R-01: publicada/sincronizada; aceptación formal específica pendiente.
- R-02: implementada, probada con Xray-core 26.10.31 real y leases sintéticos, auditada localmente; pendiente de aceptación formal/publicación. fixture_root obligatorio y sin defaults a almacenes live.
- R-03: IMPLEMENTADA, VERIFICADA Y AUDITADA LOCALMENTE; pendiente de aceptación formal/publicación.
- Implementación R-03: scripts/xray_runtime_journal.py; pruebas tests/test_xray_runtime_journal.py.
- Expedientes: docs/IMPLEMENTACION_R03_SNAPSHOT_JOURNAL_2026-11-04.md; docs/AUDITORIA_R03_SNAPSHOT_JOURNAL_2026-11-04.md.
- Controles: marcadores fixture obligatorios en XRAY_SERVICE_ROOT, operation_store y lease_root; locks distintos dentro de operation_store/locks; journal root:root 0600; snapshot root:root 0600; no_previous_config explícito.
- Pruebas: R-02 focal 11/11; R-03 focal 21/21; Python 140/140; shell 58/58; verificaciones estáticas PASS.
- Integración R-02→R-03: el staging real con lease TLS sintético se entrega al journal, que valida rutas/markers y captura snapshot en XRAY_SERVICE_ROOT temporal.
- No se escribió el config del fixture, no se publicó runtime y no se llamó systemd.
- Git: R-02/R-03 siguen locales, sin commit/push. Aceptación formal y autorización de publicación pendientes.
- Siguiente paso tras revisión: R-04 — publicación atómica aislada.
- R-06/live y cambios de runtime/systemd real no autorizados. Etapas 2, 3 y 5 siguen ABIERTAS.


## Punto de control vigente — R-04 publicación atómica aislada (2026-11-04)

- R-01 publicada/sincronizada; aceptación formal específica pendiente.
- R-02 implementada/auditada localmente: 11/11.
- R-03 implementada/auditada localmente: journal 22/22.
- R-04 IMPLEMENTADA/VERIFICADA LOCALMENTE: 12/12; pendiente de auditoría/aceptación formal y publicación.
- R-04 escribe solo dentro de XRAY_SERVICE_ROOT fixture. Temporal exclusivo, fsync, validación Xray bajo UID/GID simulado, rename atómico, verificación de hash/permisos, rollback exacto y recuperación idempotente.
- Expedientes: docs/IMPLEMENTACION_R04_PUBLICACION_ATOMICA_2026-11-04.md; docs/AUDITORIA_R04_PUBLICACION_ATOMICA_2026-11-04.md.
- Regresión Python 153/153; shell 58/58; verificaciones estáticas PASS.
- Integración R-02→R-03→R-04 comprobada en fixture.
- No se publicó runtime real ni se llamó systemd. Sin cambios en servicio real, claves, certificados desplegados, red o firewall.
- R-02/R-03/R-04 siguen locales sin commit/push. Requieren revisión/aceptación y autorización de publicación.
- Siguiente paso tras aceptación: R-05 — orquestación systemd simulada.
- R-06/live y NetMod NO AUTORIZADAS. Etapas 2, 3 y 5 ABIERTAS.


## Punto de control vigente — 2026-11-04

**HEAD publicado:** `05aceabf11414040abbb32fff1428984370ff521` en `design/user-identity-association-v1`. VPS `/opt/xray-manager` y GitHub se verificaron alineados al inicio de esta recuperación; árbol limpio.

| Incremento | Implementado | Verificado/auditado | Publicado/sincronizado | Aceptación formal |
|---|---|---|---|---|
| R-01 | Sí | Sí | Sí | Pendiente |
| R-02 | Sí | Sí | Sí | Pendiente |
| R-03 | Sí | Sí | Sí | Pendiente |
| R-04 | Sí | Sí | Sí | Pendiente |
| R-05 | No | No | No | No iniciado |
| R-06/live | No | No | No | No autorizado |

Resultados documentados: R-01 28/28 focal; R-02 11/11; R-03 22/22; R-04 12/12; Python 153/153; Bash 58/58; verificaciones estáticas PASS. No se reejecutaron en esta sesión.

**Siguiente paso:** revisión del diseño `docs/DISENO_R05_ORQUESTACION_SYSTEMD_SIMULADA_2026-11-04.md`. R-05 no debe implementarse hasta aprobación expresa. Los estados previos que indiquen R-02–R-04 sin publicar son históricos y quedan superados por este punto de control.

Límites: normativa inmutable; `main` protegida; R-06/live no autorizada; sin cambios reales de Xray/systemd, certificados, claves, almacenes, firewall, puertos, red o dependencias; no utilizar VPS de pruebas. Etapas 2, 3 y 5 ABIERTAS.


## Punto de control vigente — prioridad primer servicio real VLESS + WS + TLS (2026-11-04)

**Rama:** `design/user-identity-association-v1`
**HEAD base verificado antes de esta actualización:** `4433cd324756eb32f2d9b6b5d48ed8dba7681e34`
**VPS:** `Implementación-Xray:/opt/xray-manager`
**Estado base:** árbol limpio, rama/upstream correctos, HEAD local y remoto coincidentes.

### Prioridad

Demostrar el primer servicio real VLESS + WebSocket + TLS gestionado por Xray-Core Manager. La hoja de ruta completa está en `docs/PLAN_HITO_PRIMER_SERVICIO_REAL_VLESS_WS_TLS_2026-11-04.md`.

### Estado

| Componente | Estado al corte |
|---|---|
| R-01 | Implementada, verificada/auditada, publicada/sincronizada; aceptación formal pendiente |
| R-02 | Implementada, verificada/auditada, publicada/sincronizada; aceptación formal pendiente |
| R-03 | Implementada, verificada/auditada, publicada/sincronizada; aceptación formal pendiente |
| R-04 | Implementada, verificada/auditada, publicada/sincronizada; aceptación formal pendiente |
| R-05 | Diseño de orquestación simulada; no implementada; debe evolucionar hacia adaptador real |
| H0 auditoría de brechas | Siguiente trabajo; no iniciada |
| H1–H8 | No iniciadas como hitos de la nueva hoja de ruta |
| R-06/live | No autorizada |

### Decisiones del propietario

- VLESS + WS + TLS será el primer servicio de validación.
- El reinicio de un servicio `active` exige confirmación explícita.
- Si se rechaza, no se reinicia; la revisión queda publicada pendiente de aplicación y el proceso actual conserva su configuración cargada.
- Si el servicio estaba `inactive`, publicar no lo inicia. El inicio manual desde el administrador requiere confirmación y verificación.
- Cada operación usa un `generation_id` único, asociado a journal y evidencia.

### Siguiente acción permitida

Ejecutar H0: inventario/auditoría de brechas del código, menús, pruebas y documentación frente a las Etapas normativas 2, 4, 5 y 6. Solo lectura y documentación; no instalar, modificar código de producto ni tocar runtime, systemd, certificados, DNS, firewall, puertos o red.

No repetir R-01–R-04. No usar la VPS de pruebas. No modificar `main` ni `Xray-Normativa/`. No ejecutar R-06/live ni prueba NetMod sin autorización específica.


## Punto de control — auditoría H0 preparada (2026-11-04)

**Informe:** `docs/AUDITORIA_H0_BRECHAS_PRIMER_SERVICIO_VLESS_WS_TLS_2026-11-04.md`
**HEAD base auditado:** `af4b562fb3608392b0a16388390e1dfe9b849898`
**Estado:** H0 PREPARADA; aceptación formal del propietario pendiente.

### Dictamen

El proyecto aún no puede desplegar un servicio real VLESS-WS-TLS desde el Manager. Existe código de instalación Xray, control systemd independiente, asistente/adaptador VLESS, almacén/resolutor TLS y R-01–R-04. Sin embargo, Etapa 4 DNS/ACME/UI, activación de perfil, integración runtime real, R-05, diagnóstico completo y backup genérico permanecen incompletos.

### Entorno de desarrollo (metadata read-only)

- Ubuntu 24.04.4 amd64; dependencias presentes; `install.sh --check` PASS.
- Xray 26.10.31 y geodata presentes.
- `xray.service`, `/etc/xray/config.json`, usuario y grupo `xray`: ausentes.
- No se ejecutó systemctl ni se consultó el estado de servicio.

### Siguiente acción permitida

Revisar/aceptar la matriz H0 y decidir el alcance del siguiente diseño de implementación. No iniciar código ni acciones live por inferencia.

No repetir R-01–R-04. R-05 no implementada. No leer la clave maestra ni acceder a almacenes live. No modificar `Xray-Normativa/`, `main`, runtime, systemd, certificados, DNS, firewall, puertos o red. No usar la VPS de pruebas.


## Punto de control vigente — MVP mínimo VLESS-WS-TLS (2026-11-04)

**Aceptación H0:** ACEPTADA FORMALMENTE por el propietario.
**Plan vigente:** `docs/PLAN_MVP_DESPLIEGUE_VLESS_WS_TLS_2026-11-04.md`.
**Rama autorizada:** `design/user-identity-association-v1`.
**HEAD previo a esta actualización documental:** `3f47ffdcc00d0c3b2837213effe76fb0a5a29cef`.

### Objetivo inmediato

Demostrar un recorrido vertical mínimo administrado desde Xray-Core Manager:
1. instalar/preparar Xray y `xray.service`;
2. emitir, validar y registrar certificado TLS;
3. crear usuario y conexión VLESS + WS + TLS;
4. generar/validar y publicar configuración;
5. iniciar/aplicar Xray desde el administrador;
6. verificar conexión externa bidireccional.

### Alcance y límites

- Ejecutar B0–B5 del plan MVP en orden.
- Reutilizar módulos existentes; no repetir R-01–R-04.
- R-05 avanzado y ampliaciones de journal/reconciliación quedan en pausa.
- Certbot HTTP-01 standalone es una propuesta para el primer MVP, sujeta a verificación de DNS/puerto 80 y autorización de dependencias.
- Mantener copia recuperable, validación previa, publicación atómica, permisos mínimos y confirmaciones/guardas de servicio.
- No hay autorización live. Toda instalación, modificación de cuenta/unidad, emisión de certificado real, publicación runtime, inicio/reinicio, cambio DNS/firewall/puertos/red o prueba externa requiere autorización específica.
- No usar VPS de pruebas, no leer la clave maestra, no modificar `main` ni `Xray-Normativa/`.

### Siguiente acción permitida

B0: inspección focal de funciones existentes y normativa pertinente; entregar matriz requisito → función reutilizable → brecha → cambio mínimo → prueba. Después iniciar B1 únicamente con pruebas aisladas. No ejecutar operaciones live.


## Punto de control vigente — I-01 compositor VLESS-WS-TLS (2026-11-04)

**Rama:** `design/user-identity-association-v1`
**HEAD base antes de I-01:** `bf73fd6a15aa169379c7cd71d1ea9cf5fb13f8b1`
**VPS:** `Implementación-Xray:/opt/xray-manager`
**Estado al 2026-11-05:** I-01 aceptado formalmente con limitaciones; commit/push autorizado, publicación y sincronización pendientes de verificación.

### Decisión de persistencia aprobada

El mapping TLS se almacena como archivo auxiliar privado fuera del JSON del perfil. Su ubicación `<mapping-root>/<profile_id>/<revision>.json` enlaza inequívocamente el mapping con una revisión concreta y conserva el contrato de entrada de R-02 sin ampliar el esquema de perfiles.

### Resultado de I-01

- Nuevo `scripts/vless_ws_tls_composer.py`; suite focal `tests/test_vless_ws_tls_composer.py`.
- Modalidad cubierta: exclusivamente VLESS-WS-TLS.
- Reutiliza VLESS Config Store, certificado central, exportador oficial Usuarios V2 y ProfileStore.
- Crea inbound `vless`, `network=ws`, `security=tls`, `tlsSettings.certificates=[]`; conserva el resto del perfil.
- Nueva revisión inmutable y no validada; mapping exacto para R-02 con permisos root:root 0700/0600.
- Bloqueos compartidos de catálogos y comparación de revisión esperada para evitar carreras y TOCTOU.
- Prueba focal: 11/11 PASS; incluye parser real de mapping R-02 y fallos de certificado, configuración, candidatos, UUID, puerto, mapping previo, revisión obsoleta y ruta symlink. Regresión: Python 163/163 y Bash 58/58 PASS; ShellCheck -S error, bash -n, py_compile, diff e install.sh --check PASS.

| Estado | Resultado |
|---|---|
| IMPLEMENTADO | Sí |
| VERIFICADO | 11/11 focal; Python 163/163; Bash 58/58 PASS |
| AUDITADO | Sí — alcance focal I-01 |
| PUBLICADO | Pendiente de verificación del commit remoto |
| SINCRONIZADO | Pendiente de comparación VPS/GitHub |
| ACEPTADO | Sí — aceptación formal del propietario el 2026-11-05 |

### Siguiente paso

Auditoría focal: `docs/AUDITORIA_I01_COMPOSITOR_VLESS_WS_TLS_2026-11-04.md` (PASS). Aceptación formal recibida el 2026-11-05 con limitaciones; autorización de publicación recibida por separado. Verificar publicación y sincronización.

R-01–R-04 se reutilizan, no se repiten. R-05 en pausa. R-06/live y NetMod NO AUTORIZADAS. Etapas 2, 3 y 5 ABIERTAS. Normativa y `main` intactas; sin cambios live ni en VPS de pruebas.


## Punto de control vigente — I-02 / I-03 VLESS-WS-TLS (2026-11-05)

Base publicada: 792f382ca1b4f753ff763dc50a442aa66a0cd42f
Rama: design/user-identity-association-v1
Estado: I-02/I-03 implementados localmente, verificados y auditados focalmente; aceptación formal y publicación pendientes.

- Menú perfiles [9] integra I-01, lee config de conexión por Config Store, previsualiza path/Host/SNI/certificado, confirma y crea nueva revisión inmutable pendiente.
- Filtro estricto: conexión vless_ws_tls, state=draft, runtime_applied=false.
- Host opcional: transport_options.host → Xray wsSettings.host. Validado por Xray 26.10.31; se evitó wsSettings.headers.Host por obsolescencia.
- SNI opcional: client_options.tls_server_name; persistido como dato cliente, no se inyecta en inbound ni reemplaza TLS/certificado del servidor.
- Esquema VLESS 2 para Host/SNI; esquema 1 compatible. Resolver y backup/restore actualizados.
- Compositor focal 11/11; menú, asistente TLS, backup/restore, Xray integration y ShellCheck focal PASS. Regresión global final: Python 164/164, Bash 59/59; py_compile, bash -n global, ShellCheck focal en todos los Bash modificados, diff e instalador PASS.
- Exportación URI de cliente aún pendiente de endpoint público explícito.
- I-02/I-03 NO están aceptados formalmente ni publicados/sincronizados. No realizar commit/push sin autorización separada.
- No se ejecutó live, no se modificó runtime, systemd, certificados reales, DNS, firewall, puertos o red. main y Xray-Normativa intactas.

### Próximas acciones

1. Revisión del propietario y aceptación formal del alcance I-02/I-03.
2. Recibir autorización independiente para commit/push a la rama autorizada.
3. Definir endpoint público antes de implementar exportación URI de cliente.
4. No integrar todavía activación ni R-01–R-04 en este menú.

## Punto de control vigente — I-04 exportación VLESS-WS-TLS (2026-11-05)

El propietario autorizó generar URI vless:// para NetMod con endpoint público hellen.tvrc.me:443; el puerto público coincide con el puerto del inbound. Implementación: scripts/vless_client_export.py; menú de perfiles [10]. Se selecciona perfil y revisión exactos. El exportador valida el mapping privado exacto, recupera configuración fuente con VLESS Config Store y produce un URI por UUID. Host WebSocket y SNI cliente permanecen independientes; solo se exportan si están configurados. El archivo TXT opcional se crea 0600, atómico y sin sobrescritura.

**Evidencia:** I-04 focal 7/7 PASS; integración de menú/compositor PASS; Python 171/171; Bash 59/59; py_compile, bash -n global, ShellCheck focal, install.sh --check y git diff --check PASS. No se probó NetMod real, DNS, listener ni conectividad WAN.

**Límites:** no activa/valida perfiles, no ejecuta R-01–R-04, no inicia/reinicia Xray/systemd, no modifica certificados reales, DNS, firewall, puertos, red ni dependencias. No se modificaron main ni Xray-Normativa/.

**Estado:** I-02/I-03/I-04 IMPLEMENTADOS, VERIFICADOS y AUDITADOS localmente; aceptación formal pendiente; no publicados ni sincronizados. Cambios locales I-02/I-03 preservados. No hacer commit/push sin autorización expresa.

**Documentos:** docs/DECISION_I04_VLESS_CLIENT_EXPORT.md, docs/IMPLEMENTACION_I04_VLESS_CLIENT_EXPORT_2026-11-05.md, docs/AUDITORIA_I04_VLESS_CLIENT_EXPORT_2026-11-05.md.


## Punto de control vigente — aceptación y publicación I-02/I-03/I-04 (2026-11-05)

- El propietario aceptó formalmente I-02 (integración del compositor en menú de perfiles), I-03 (Host WebSocket y SNI cliente separados) e I-04 (exportación VLESS-WS-TLS para NetMod), cada una con las limitaciones de su auditoría.
- El propietario autorizó commit, push y sincronización únicamente en `design/user-identity-association-v1`.
- Base remota/local antes de publicar: `792f382ca1b4f753ff763dc50a442aa66a0cd42f`. No se detectó divergencia; cambios I-02/I-03/I-04 locales preservados.
- Regresión reejecutada antes de publicar: Python 171/171; Bash 59/59; `py_compile`, `bash -n`, ShellCheck `-S error`, `install.sh --check`, `git diff --check`: PASS.
- Comparación normativa: 13 archivos normativos sustantivos idénticos byte a byte al respaldo `/root/Xray_Manager_Documentacion_Final_2026-10-31`. `README.md` es auxiliar de la carpeta normativa y no forma parte de los 13 documentos sustantivos; `Xray-Normativa/` no se modificó.
- I-02/I-03/I-04 no activan perfiles, no ejecutan R-01–R-04, no modifican Xray/systemd real y no acreditan conectividad NetMod/WAN. R-06/live sigue NO AUTORIZADA.
- Tras la publicación, actualizar aquí el SHA definitivo, confirmar GitHub y comparar los archivos publicados contra `/opt/xray-manager`. No declarar sincronización antes de esas verificaciones.
- Etapas 2, 3 y 5 permanecen ABIERTAS; la aceptación de estos incrementos no cierra etapas.


## Cierre de publicación vigente — I-02/I-03/I-04 (2026-11-05)

- Commit funcional publicado: `ac119d923ba0eae35579e944d59f5262c5d105a7` — `feat(vless): integrate profile composition and NetMod export`.
- Push fast-forward desde `792f382ca1b4f753ff763dc50a442aa66a0cd42f` a `design/user-identity-association-v1`; GitHub confirmó exactamente `ac119d923ba0eae35579e944d59f5262c5d105a7`.
- `git fetch` posterior confirmó `HEAD` local igual a `origin/design/user-identity-association-v1`; checkout limpio.
- Se verificó que GitHub contiene los archivos de implementación, pruebas y auditorías I-02/I-03/I-04. El contenido de la VPS corresponde al mismo commit.
- `main` permanece en `656ecedc506a94a6461aee296b20871d51a38bf3`.
- `Xray-Normativa/` no tiene cambios; 13 documentos normativos sustantivos comparados byte a byte con el respaldo: PASS.
- Resultado: I-02/I-03/I-04 PUBLICADOS y SINCRONIZADOS. No hubo cambios live, DNS, certificados reales, firewall, puertos, red ni dependencias.


## Punto de control vigente — B1-A / B1-B (2026-11-05)

Autorización recibida: implementar B1-A y B1-B exclusivamente con fixtures, sin operaciones live. El propietario aceptó formalmente ambos bloques y autorizó commit/push en la rama design/user-identity-association-v1.

B1-A implementado: opción [7] Preparar servicio (verifica integridad) en Administración de Xray-core. Requiere manifiesto válido y confirmación explícita; adquiere el bloqueo de ciclo de vida, revalida integridad bajo el lock y reutiliza xray_service_prepare; no inicia ni habilita Xray; usa el bloqueo de ciclo de vida y aborta antes de cambios si el servicio está activo.

B1-B implementado: manifiesto v1 xray-install.json con versión, arquitectura, rutas y SHA-256 de binario, geodata y paquete oficial. Escritura atómica/fsync, root:root 0600 y directorio 0700. update/reinstall fallan cerrados ante manifiesto ausente o discrepancias; repair es recuperación explícita; rollback conserva/restaura manifiesto.

Evidencia actual:
- Bash 60/60 scripts PASS.
- Python unittest 171/171 PASS.
- py_compile global, bash -n global, ShellCheck -S error global, install.sh --check y git diff --check: PASS.
- Auditoría: docs/AUDITORIA_B1_A_B1_B_2026-11-05.md.
- Implementación: docs/IMPLEMENTACION_B1_A_B1_B_2026-11-05.md.
- Decisión complementaria: docs/DECISION_B1_SERVICE_PREPARATION_AND_INSTALL_INTEGRITY.md.

Límites: todas las pruebas se realizaron en fixtures. No se ejecutó preparación live, instalación/reparación live ni el binario real systemctl; la comprobación de servicio activo se simuló con un stub. No se creó identidad/unidad real ni se cambiaron runtime, certificados, DNS, firewall, puertos, red o dependencias.

Git: rama design/user-identity-association-v1; commit funcional B1 c8cd20c2a576fb1926fdcf11945cd75cf1c4211c. Push fast-forward confirmado; HEAD local/remoto coinciden. main intacta; Xray-Normativa/ intacta.

Estado separado: B1-A/B1-B IMPLEMENTADOS, VERIFICADOS, AUDITADOS, ACEPTADOS, PUBLICADOS y SINCRONIZADOS. Etapas 2, 3 y 5 ABIERTAS; R-06/live NO AUTORIZADA.

Siguiente acción: continuar con el siguiente bloque del plan MVP después del contraste documental y autorización de alcance específica. No ejecutar B1 live ni avanzar a B2 sin autorización específica.


## Punto de reanudación vigente — B2 ACME Certbot (2026-11-05)

El propietario aprobó Certbot (HTTP-01 standalone y DNS-01 manual TXT) y autorizó B2-A a B2-G solo con fixtures. Código incorporado localmente: scripts/certificate_acme.py, modules/certificates.sh, integración de menú y pruebas focales. No se ejecutó ACME real, no se instaló Certbot/dig, no se modificó DNS/puerto 80/servicios/runtime ni se publicaron cambios.

Pruebas B2: Python 182/182 y Bash 61/61 PASS; py_compile, bash -n, ShellCheck -S error, install.sh --check y git diff --check PASS. La prueba integrada usa certificado y conexión sintéticos para crear y limpiar un lease TLS. Evidencia en docs/AUDITORIA_B2_ACME_CERTIFICADOS_2026-11-05.md.

**Siguiente acción:** concluir regresión, controles estáticos y revisión de diff; completar evidencias de auditoría; solicitar aceptación formal. La publicación en GitHub requiere autorización separada. No tocar main, Xray-Normativa/, VPS de pruebas ni entorno live.


## Punto de reanudación vigente — B2 aceptada; preparar B3 (2026-11-05)

**B2 — ACME Certbot:** IMPLEMENTADA, VERIFICADA, AUDITADA, ACEPTADA FORMALMENTE, PUBLICADA y SINCRONIZADA, exclusivamente en el alcance fixture-only documentado. Aceptación formal del propietario: 2026-11-05. Ver `docs/AUDITORIA_B2_ACME_CERTIFICADOS_2026-11-05.md`.

- Commit funcional: `2669c45` — `feat(certificates): add Certbot ACME workflows`.
- Commit documental: `21a103a7a15e003ddc3e2031aaf591efefe064ce` — `docs(certificates): record B2 ACME implementation and audit`.
- Rama autorizada: `design/user-identity-association-v1`; HEAD local/GitHub verificado y checkout limpio al último control.
- Sin ACME real, instalación de Certbot, DNS/TXT real, prueba WAN/TCP 80, identidad systemd real ni cambios live.
- `Xray-Normativa/` permanece inmutable; `main` intacta.

### Siguiente acción permitida

Iniciar B3 — usuario y conexión VLESS-WS-TLS — con recuperación de estado Git/VPS, lectura de la normativa pertinente de Etapas 2 y 3 y del plan MVP, inventario read-only de los componentes ya implementados (Usuarios V2, compositor I-01, menú I-02/I-03 e I-04 exportador), y matriz requisito → implementación reutilizable → brecha → prueba. Presentar el contraste antes de modificar código y esperar autorización expresa del alcance concreto.

No repetir I-01–I-04 ni B1/B2. No repetir R-01–R-04. Etapa 4 sigue ABIERTA; Etapas 2, 3 y 5 siguen ABIERTAS. R-06/live NO AUTORIZADA. No instalar dependencias ni tocar runtime, systemd, certificados reales, DNS, firewall, puertos, red, clave maestra, `main`, `Xray-Normativa/` ni VPS de pruebas.

## Punto de control adicional — 2026-11-05 — R-05

R-05 fixture-only está implementada y auditada. Código principal: `scripts/xray_runtime_service_adapter.py` y `scripts/xray_runtime_orchestrator.py`; journal schema 2 mantiene lectura schema 1. Evidencia y contrato:
- `docs/DECISION_R05_JOURNAL_GENERATION_2026-11-05.md`
- `docs/IMPLEMENTACION_R05_ORQUESTACION_FIXTURE_2026-11-05.md`
- `docs/AUDITORIA_R05_ORQUESTACION_FIXTURE_2026-11-05.md`

40/40 focales R-05, 227/227 Python global y 61/61 Bash PASS; controles estáticos PASS. R-05 no llama systemd real ni Xray real. Sin UI y sin registro persistente de perfil activo; por tanto Etapa 5 sigue abierta. Etapa 6 sigue abierta. R-06/live NO AUTORIZADA.

**No continuar a publicación sin aceptación formal de auditoría y autorización separada para commit/push.** No tocar `main`, `Xray-Normativa/`, runtime real, certificados, claves, DNS, firewall, puertos, red, dependencias ni VPS de pruebas.


## Addendum vigente — corrección y reauditoría de concurrencia R-05 (2026-11-05)

El propietario autorizó corregir el hallazgo de concurrencia y repetir la auditoría exclusivamente con fixtures. Se incorporó `fcntl.flock` interproceso mediante `adapter.lock` root-only. El bloqueo cubre la transacción completa de `status`, `restart`, `restore` y `audit_events`, incluyendo CAS y escritura de bitácora. Se valida `O_NOFOLLOW`, tipo/propietario/permisos, hardlinks, marcador e identidad de inode.

Se añadieron pruebas multiproceso: dos restart concurrentes con el mismo estado previo (un ganador y un rechazo), cuatro status concurrentes sin pérdida de eventos, dos restore concurrentes (una restauración y un rechazo) y rechazo de lock symlink.

**Resultado actualizado:** 43/43 pruebas focales R-05; 230/230 Python global; 61/61 Bash; `compileall`, `bash -n`, ShellCheck `-S error`, `install.sh --check` y `git diff --check` PASS. Escaneo del adaptador sin invocaciones a servicios/procesos reales. Sin dependencias nuevas.

R-05 queda CORREGIDA, VERIFICADA Y AUDITADA LOCALMENTE; aceptación formal pendiente. No se publicó ni se autorizó publicación. No se ejecutaron operaciones live ni se modificaron systemd/Xray real, runtime persistente, certificados, claves, DNS, firewall, puertos, red, `main`, `Xray-Normativa/` o VPS de pruebas. R-06/live continúa NO AUTORIZADA.

**Siguiente acción:** revisión del propietario y aceptación formal de la auditoría corregida. La publicación requiere autorización separada.

## Actualización de control — aceptación formal R-05 y publicación autorizada (2026-11-05)

R-05 queda ACEPTADA FORMALMENTE por el propietario, limitada al alcance fixture-only y a las restricciones de `docs/AUDITORIA_R05_ORQUESTACION_FIXTURE_2026-11-05.md`. El propietario autoriza commit/push exclusivamente en `design/user-identity-association-v1`. No se autoriza adaptador systemd real, UI, integración del registro persistente de perfil activo ni R-06/live. Etapas 2, 5 y 6 permanecen ABIERTAS. `main` y `Xray-Normativa/` no se modifican.

## Punto de control — B4 fixture-only (2026-11-05)

B4 recibió autorización limitada a fixtures/mocks. Se implementó el registro activo independiente y el flujo de start explícito simulado para \`published_pending_start\`. El registro solo se actualiza después de verificar \`active\` + generation_id + SHA-256; pending/rollback preservan el registro anterior. Recovery reconcilia por generación/hash y es idempotente.

Código: \`scripts/xray_runtime_active_profile.py\`, \`scripts/xray_runtime_orchestrator.py\`, \`scripts/xray_runtime_service_adapter.py\`, \`scripts/xray_runtime_journal.py\`. Pruebas B4 añadidas a \`tests/test_xray_runtime_orchestrator.py\`.

Evidencia: \`docs/IMPLEMENTACION_B4_APLICACION_FIXTURE_2026-11-05.md\`, \`docs/AUDITORIA_B4_APLICACION_FIXTURE_2026-11-05.md\`. 59/59 focales, 246/246 Python global, 61/61 suites Bash; análisis estático PASS.

Limitación: este bloque no integra menú de producción ni systemd real. No acredita funcionamiento en VPS ni conexión WAN. No hubo operaciones live, commit o push. \`Xray-Normativa/\` y \`main\` siguen intactas. HEAD base: \`2902b2ef602dfe97acf62428d6b7c35ce7c81d5d\`.

## Punto de control — H6-A observación systemd read-only (2026-11-05)

H6-A añade un adaptador Python separado de observación systemd. Consulta propiedades de `xray.service`, verifica la unidad administrada y calcula el hash del archivo runtime sin inferir que sea el hash cargado por el proceso. La generación y el hash cargados quedan no atestiguados. No hay métodos mutadores ni integración con R-05/menús.

Evidencia: 11/11 focales H6-A, 59/59 R-05+B4, 257/257 Python globales, smoke Bash, ShellCheck, AST y diff-check PASS. Las pruebas usan mocks; no se invocó systemctl real.

No se modificó runtime, unidades, certificados, DNS, firewall, puertos/red, dependencias, `main` ni `Xray-Normativa/`. Sin commit/push. H6/live continúa NO AUTORIZADA.


## H6-B — atestación persistente de generación systemd (2026-11-06)

Se implementó H6-B en alcance aislado: `scripts/xray_runtime_attestation.py` y `tests/test_xray_runtime_attestation.py`. La atestación enlaza operation_id, generation_id, SHA-256 publicado, InvocationID nuevo/estable, ActiveEnterTimestamp, SHA-256 de la unidad y fecha UTC. El almacén reservado es `/var/lib/xray-manager/attestations`, pero no se creó ni se utilizó en el sistema real.

Contraste normativo: Etapa 5 §§4, 5 y 7 exige distinguir configuración guardada/aplicada, verificar la configuración realmente ejecutada y actualizar el registro activo solo después de verificar. Etapa 6 §2 exige observación del estado/proceso y verificación de funcionamiento. H6-B aporta evidencia técnica para ese objetivo, pero aún no completa la activación funcional ni la verificación end-to-end.

Auditoría: 12/12 pruebas focales H6-B; 269/269 Python global; pruebas Bash de servicio, control de servicio y preparación PASS; compileall, bash -n global, ShellCheck -S error, install.sh --check y git diff --check PASS. El módulo no invoca systemctl, subprocess, shell ni eval.

Limitaciones: observaciones sintéticas; sin systemctl/Xray real; no conectado a H6-A, R-05, B4, menú ni CLI. La futura integración debe mantener el lock de ciclo de vida durante transición, observaciones y persistencia, y usar snapshots directos de H6-A. H6-B queda IMPLEMENTADA, VERIFICADA Y AUDITADA, PASS CON LIMITACIONES. No se hizo commit ni push. HEAD continúa `be524eef65037f74bb36ee9e7fd9b385c3ffb613`; rama `design/user-identity-association-v1`. `main` y `Xray-Normativa/` permanecen intactas. No hubo operaciones live ni cambios de runtime, systemd, certificados, DNS, firewall, puertos, red o dependencias.

Siguiente paso propuesto: H6-C, integración del almacén/atestación con R-05 mediante backend inyectable, manteniendo fixture como default y sin habilitar ejecución real desde CLI. Requiere revisión y autorización del alcance de integración; no habilita operaciones live.


## H6-C — integración R-05/H6-B (2026-11-06)

El propietario autorizó H6-C exclusivamente con mocks y fixtures. Se modificó scripts/xray_runtime_orchestrator.py para inyección de backend por contexto, manteniendo el adaptador fixture R-05 como default. Los backends alternativos sólo se aceptan como dobles de prueba explícitos; no hay selector real en CLI. Se conectó la persistencia H6-B a las rutas fixture de start/restart, con snapshots sintéticos before/after/confirmed dentro del lock de ciclo de vida. Divergencias provocan rollback fixture. Recovery valida la atestación persistida y falla cerrado si falta.

Evidencia: docs/IMPLEMENTACION_H6C_INTEGRACION_R05_ATESTACION_2026-11-06.md y docs/AUDITORIA_H6C_INTEGRACION_R05_ATESTACION_2026-11-06.md. H6-C 7/7 focales, H6-B 12/12 focales y Python global 276/276 PASS. compileall, bash -n, ShellCheck -S error, install.sh --check, tres pruebas Bash de servicio y git diff --check PASS.

Limitaciones: las observaciones son sintéticas; H6-A no se invocó; no existe backend mutador systemd ni selección live en CLI. La marca de doble de prueba es una salvaguarda de diseño, no una frontera contra código Python arbitrario. Sin systemctl/Xray real, WAN, certificados/DNS/firewall/red o dependencias. No commit/push. main y Xray-Normativa/ intactas. H6-C queda IMPLEMENTADA, VERIFICADA Y AUDITADA, PASS CON LIMITACIONES. Siguiente bloque requiere diseñar el adaptador de servicio real por separado y solicitar autorización live específica.
## H6-D — estado actualizado (2026-11-06)

Menú de perfiles conectado a R-05 fixture-only mediante puente confinado a raíz marcada. En modo normal queda bloqueado. No live, no systemd real, no Xray real. Focal 4/4 + menú Bash PASS; Python global 280/280 PASS. Auditoría H6-D PASS CON LIMITACIONES.

## Punto de control — H6-E1 (2026-11-06)

H6-E1 implementada y auditada PASS CON LIMITACIONES. El adaptador read-only ahora valida NeedDaemonReload=no, ausencia de drop-ins, Type=simple, ExecStartPre/ExecStart efectivos y exactos. La configuración runtime debe ser root:xray/0640 y se comprueba la identidad inode durante la apertura.

Evidencia: 20/20 focales H6-A; 289/289 Python global; compileall, bash -n, ShellCheck -S error, pruebas Bash de servicio, install.sh --check y git diff --check PASS. Sólo mocks/fixtures; no systemctl real, no /proc, no Xray real ni acciones mutadoras.

H6-E2 es el siguiente bloque previsto. No hay backend live, selector en menú/CLI ni autorización para operaciones reales. Sin commit/push; main y Xray-Normativa/ intactas.

## Punto de control — H6-E2 (2026-11-06)

H6-E2 implementada y verificada en fixtures, PASS CON LIMITACIONES. El nuevo inspector scripts/xray_runtime_process_identity.py comprueba PID/starttime, UID/GID efectivos, ejecutable /proc/PID/exe, argv exacto y hash del binario; rechaza inconsistencias y cambios observables durante la inspección. No afirma qué configuración cargó el proceso.

Evidencia: 22/22 pruebas focales, 332/332 Python global, py_compile, compileall, bash -n, tres pruebas Bash de servicio, install.sh --check, ShellCheck -S error y git diff --check PASS. No se consultó /proc real ni systemd/Xray real. No se conectó con H6-A/R-05, no hay backend mutador ni selector live. H6-E3 y H6-E4 pendientes. Sin commit/push; main y Xray-Normativa/ intactas.

## Punto de control — H6-E3 (2026-11-06)

H6-E3 implementada y verificada con dobles/fixtures, PASS CON LIMITACIONES. Se correlaciona H6-A con H6-E2 para verificar MainPID, proceso, ejecutable, argv, UID/GID, starttime, InvocationID y ActiveEnterTimestamp estables. R-05 falla cerrado si falta o diverge process_identity. H6-B schema v2 persiste la identidad del proceso junto con la invocación.

Evidencia: correlación 16/16, H6-B 15/15, H6-C 9/9, Python global 332/332; py_compile, compileall, bash -n, pruebas Bash de servicio, install.sh --check, ShellCheck -S error y git diff --check PASS. No hubo systemctl/Xray/procfs real ni backend mutador. H6-E4 pendiente; H6-F/live no habilitado. Sin commit/push; main y Xray-Normativa/ intactas.

## Punto de control — auditoría integral H6-E (2026-11-06)

Dictamen H6-E: PASS CON LIMITACIONES. H6-E2 22/22; correlación 16/16; H6-B schema v2 15/15; H6-C 9/9; Python global 332/332. py_compile, compileall, bash -n, pruebas Bash de servicio, install.sh --check, ShellCheck -S error y git diff --check PASS.

No hubo systemctl/Xray/procfs real, backend mutador, prueba WAN ni instalación limpia end-to-end. No se demuestra aún qué configuración carga Xray ni la conexión de cliente. Próximo control: H6-F, evaluación de preparación y autorización live específica. Sin commit/push; main y Xray-Normativa/ intactas.

## Punto de control — H6-F evaluación read-only (2026-11-06)

Evaluación de preparación completada; NO LISTO END-TO-END. Hallazgos principales: install.sh instala Xray y prepara systemd por defecto; Certbot no se instala automáticamente; la normativa Etapa 4 deja pendiente la selección formal ACME; el exportador VLESS-WS-TLS usa hellen.tvrc.me por defecto; R-05 sigue fixture-only y no hay backend mutador live.

El plan y autorizaciones necesarias están en docs/EVALUACION_H6F_PREPARACION_PRUEBA_REAL_2026-11-06.md. No se ejecutó systemctl/Xray/Certbot real, ni se tocaron DNS, firewall, puertos, dependencias o WAN. Se requiere autorización específica antes de habilitar el backend real y ejecutar la prueba en una VPS limpia.

## Punto de control — instalador Manager-only (2026-11-06)

Implementado: install.sh --install instala sólo Xray Core Manager. No descarga Xray-core, no crea usuario/grupo xray, no crea /etc/xray ni modifica xray.service. La instalación integral se conserva con --install --with-xray; el flag requiere --install. README, docs de Fase B y H6-F actualizados.

Pruebas: tests/install.sh PASS; Python 332/332; Bash 62/62; bash -n, ShellCheck -S error, compileall, install.sh --check y git diff --check PASS. Sólo prefijos temporales. No se instaló Xray ni se ejecutó systemctl real. H6-F sigue NO LISTO END-TO-END por backend live, ACME y endpoint público. Sin commit/push.

## Actualización documental — 2026-11-06

H6-E4 corresponde a la auditoría integral de H6-A/B/C/D/E1/E2/E3 y queda completada con PASS CON LIMITACIONES. La modificación Manager-only del instalador está implementada y probada en prefijos temporales. H6-F no está lista end-to-end: backend runtime live no disponible, Certbot requiere decisión/autorización, endpoint y valores Host/SNI deben confirmarse, y falta designar una VPS de aceptación. Los estados antiguos que contradigan el encabezado vigente son históricos.


## H6-G2 — puente seguro hacia el controlador de servicio (2026-11-06)

Contrato G1 aprobado y documentado en `docs/DECISION_H6G1_CONTRATO_BACKEND_RUNTIME_LIVE_2026-11-06.md`. El propietario aprobó el contrato H6-G1 y autorizó la implementación G2 en desarrollo, exclusivamente con mocks/fixtures. Se agregó `scripts/xray_runtime_service_control.py` y el punto de entrada `xray_service_action_inherited_lock()` en `modules/xray_service.sh`. Python hereda explícitamente el descriptor lifecycle lock hacia Bash; ambos lados verifican ruta/inode y condiciones de seguridad. Las acciones permitidas en este puente son start/restart/stop y se delegan al controlador único `xray_service.sh`; Python no ejecuta systemctl directamente.

Pruebas: puente Python 9/9; observación systemd y atestación de proceso/identidad 58/58; Python global 341/341; las 62 suites Bash ejecutadas finalizaron correctamente; `bash -n`, `py_compile` y `git diff --check` PASS. La integración Python→Bash utilizó systemctl mock. Las pruebas VLESS/VMess con Xray 26.10.31 validan configuraciones en entorno temporal, no una instancia real expuesta a WAN.

**Límites:** G2 está IMPLEMENTADA PARCIALMENTE; falta auditoría formal independiente. El puente no está conectado a R-05, no se habilitó backend live en `_with_service_backend` ni en el menú. No se modificó journal/orquestador, runtime persistente, unidad systemd real, `/etc/xray`, certificados, DNS, firewall, puertos ni red. No se ejecutaron acciones reales start/restart/stop, ACME ni conexión externa. El hash del archivo runtime sigue sin equivaler a evidencia de configuración cargada en memoria.

Archivos de esta entrega: `modules/xray_service.sh`, `scripts/xray_runtime_service_control.py`, `tests/test_xray_runtime_service_control.py`, `tests/xray_service_control.sh` y `docs/IMPLEMENTACION_H6G2_PUENTE_CONTROL_SERVICIO_2026-11-06.md`.

Estado Git: rama `design/user-identity-association-v1`, HEAD base `9bab1dbed7d4873aa30a3fd00a976a1d666d9355`; árbol con cambios locales sin commit. Sin push. `main` y `Xray-Normativa/` intactas. Las VPS de prueba no fueron utilizadas.

**Siguiente:** auditoría formal del puente G2 y luego G3: diseñar la semántica live de observación, transición, correlación de InvocationID y rollback sin inferir configuración cargada. No habilitar live hasta superar G3/G4/G5 y recibir autorización específica para el host real.


## Punto de control actualizado — H6-G2-B (2026-11-06)

El backend live aislado se implementó y validó con mocks (14/14 nuevas; suite Python 355/355; Bash 62/62). No se habilitó en R-05 ni en el menú. No ejecutado systemd real. Rollback/restore live no implementado y falla cerrado. Estado: H6-G2 parcial; siguiente paso: revisión independiente y auditoría G2; después G3 integración transaccional con journal/publicación/recuperación.


## Punto de control — auditoría H6-G2 (2026-11-06)

Dictamen PASS CON LIMITACIONES; G2 NO CERRADO. Bloqueadores para integración live: F-01 estado inactive contradictorio aceptado; F-02 ausencia de evidencia de generación publicada/validada para start; F-03 propiedad/handoff lifecycle lock no demostrada. G3 debe resolver además timeout/RECOVERY_REQUIRED y rollback live. Backend live deshabilitado, fixture default. Ver `docs/AUDITORIA_H6G2_BACKEND_RUNTIME_LIVE_2026-11-06.md`.


## H6-G2 — resolución F-01 (2026-11-06)

Se corrigió la validación de snapshots systemd en `scripts/xray_runtime_live_backend.py`. Un estado `inactive` ahora rechaza PID distinto de `null/0` e InvocationID residual. Un estado `active` requiere PID entero mayor que 1, InvocationID hexadecimal de 32 caracteres, subestado `running` y resultado `success`. Se agregaron pruebas adversariales. Resultado: 17/17 focales, Python global 358/358, Bash 62/62, py_compile, bash -n focal, ShellCheck y diff-check PASS.

F-01 queda corregido y verificado únicamente con fixtures. H6-G2 no se cierra ni se habilita live. F-02/F-03 siguen siendo bloqueadores para integración; F-04/F-05 se resolverán en G3. No hubo acciones sobre systemd/Xray real, runtime, certificados, DNS, firewall, puertos ni red. Sin commit/push; `main` y `Xray-Normativa/` intactas. Informe: `docs/IMPLEMENTACION_H6G2_F01_VALIDACION_ESTADOS_2026-11-06.md`.


## H6-G2 — F-02: contrato y lector de evidencia (2026-11-06)

Se implementó `scripts/xray_runtime_operation_evidence.py` para verificar operation_id/generation_id, journal schema 2, publicación confirmada, rollback no iniciado, staging/lease, informe persistido exacto, checks requeridos, hash de binario y hash de bytes runtime. El historial de validación se consulta read-only. El backend live dejó de aceptar un SHA-256 libre y exige evidencia correlacionada con operación y generación; solo acepta `environment=live`.

Límite deliberado: el journal actual está restringido a fixtures, por lo que el lector devuelve `environment=fixture` y el backend lo rechaza para mutaciones live. No se debilitó el aislamiento ni se conectó R-05/menú. F-02 queda implementado para el contrato y verificado en fixtures, pero evidencia live sigue pendiente de G3. Pruebas: backend 20/20, lector 9/9, Python 370/370, Bash 62/62; verificaciones estáticas PASS. Sin acciones live ni commit/push. Documentos: `docs/DECISION_H6G2_F02_EVIDENCIA_OPERACION_GENERACION_2026-11-06.md`, `docs/IMPLEMENTACION_H6G2_F02_EVIDENCIA_OPERACION_2026-11-06.md`.


## Punto de control — H6-G2 F-03 (2026-11-06)

Corregida la comprobación de propiedad/handoff del lifecycle lock en el puente Python/Bash. La prueba usa `/proc/.../fdinfo` para acreditar FLOCK exclusivo vinculado al descriptor y PID propietario R-05; no vuelve a adquirir el lock. Pruebas focales Python 12/12 y Bash PASS. F-03 implementado en aislamiento, pendiente auditoría. G2 sigue abierto y live deshabilitado.

Limitación: aún no se integró R-05 ni se extendió el lock sobre toda la transacción; G3 debe resolver ese ciclo de vida y evitar reacquisiciones anidadas. Ver `docs/IMPLEMENTACION_H6G2_F03_PROPIEDAD_LIFECYCLE_LOCK_2026-11-06.md`.

## Punto de control — H6-G3-A/B (2026-11-06)

**Estado:** implementado y verificado en fixtures; auditoría independiente pendiente. Se agregó `publisher.transaction_locks()` como único propietario de lifecycle→application. Apply, start pendiente, restart, rollback y `_recover_one()` reutilizan el mismo ámbito sin reacquisiciones internas ni ventanas entre transición y rollback.

**Pruebas:** Python 377/377; Bash 62/62; py_compile/compileall, bash -n, ShellCheck -S error y git diff --check PASS. Las pruebas de lock verifican contención durante publicación/transición/rollback y en start/recovery anidados.

**No habilita live:** journal y publisher siguen fixture-only; backend live continúa desconectado y rechazando evidencia fixture. G3-C, G3-D y G3-E pendientes. Sin systemctl/Xray real, red, certificados, DNS, firewall, puertos ni dependencias. Sin commit/push; main y Xray-Normativa/ intactas.


## H6-G3-C — reconciliación de timeout/ambigüedad (2026-11-06)

Implementado en R-05 fixture. Los resultados timeout/response_lost se conservan en el journal y la transición se decide por observación exacta de estado, generación y hash. Timeout antes de la acción con estado previo intacto permite rollback de configuración sin mutar servicio; timeout o respuesta perdida después de transición exacta se reconcilia como completado sin repetir acción. Si la observación es failed/unknown, no correlacionada o no disponible, se restaura la configuración cuando es seguro y se registra `RECOVERY_REQUIRED`, sin otra mutación de servicio. Ese estado queda como `NO_OP` en recuperaciones automáticas.

Se añadió failpoint de prueba tras persistir start request y pruebas para start timeout_before/timeout_after/response_lost_after, crash antes de start, estados failed/unknown y reobservación fallida. Suite focal R-05: 67/67 PASS. Evidencia: `docs/IMPLEMENTACION_H6G3_C_TIMEOUT_RECONCILIACION_2026-11-06.md`.

**Límites:** sólo fixtures/mocks. El backend live continúa aislado, sin reconciliación durable propia, sin conexión a R-05/CLI/menú. No se modifica journal para aceptar live ni se realiza rollback live. G3-C implementado focalmente; auditoría pendiente. G3-D y G3-E pendientes; H6-G2 permanece abierto. Sin systemctl/Xray real, dependencias, cambios persistentes, commit ni push.


## H6-G3-D — rollback fixture adversarial e idempotencia (2026-11-06)

La auditoría adversarial encontró un defecto: si el snapshot se corrompía después de publicar, `_load_operation()` lanzaba antes de que rollback/recovery pudiera persistir `RECOVERY_REQUIRED`. Se ajustó el camino controlado del publicador para leer el journal estructuralmente, validar snapshot y registrar `recovery_required` ante corrupción, sin usar el snapshot ni sobrescribir el runtime.

Pruebas adversariales añadidas: drift externo antes de rollback; snapshot corrupto durante rollback y recovery; drift externo después de crash tras rename; recovery repetido byte-a-byte idempotente; generación de servicio ajena después de restaurar configuración; crash después de restaurar servicio sin repetir restore; fallo de restore seguido de recovery `NO_OP`. Se conservan pruebas de symlink/hardlink, TOCTOU, ausencia de snapshot previo y crashes de rename.

Resultados: publicador + orquestador 86/86 PASS; Python global 388/388 PASS. Documento: `docs/IMPLEMENTACION_H6G3_D_ROLLBACK_FIXTURE_2026-11-06.md`.

**Estado:** G3-A/B/C/D implementados y verificados con fixtures. G3-E auditoría independiente integral pendiente. H6-G2 permanece abierto; backend live no conectado y no habilitado. Sin systemctl/Xray real, dependencias, operaciones persistentes, commit ni push. `main` y `Xray-Normativa/` intactas.


## H6-G3-E — auditoría integral de segunda pasada (2026-11-06)

Se completó una segunda pasada sobre G3-A/B/C/D, contrastando el contrato transaccional, publicador R-04, orquestador R-05, journal, rollback, recuperación y aislamiento live. **Dictamen: PASS CON LIMITACIONES en alcance fixture.** No se identificó un defecto bloqueante nuevo dentro de ese alcance.

Validación global: Python **388/388**, Bash **62/62**, `bash -n` global, ShellCheck `-S error`, `install.sh --check` y `git diff --check` PASS. Los 14 archivos normativos maestros coinciden byte a byte con `Xray-Normativa/`; el único archivo adicional es el README auxiliar. `main` y `Xray-Normativa/` permanecen sin modificaciones.

Esta revisión fue realizada por la misma sesión que participó en la implementación: es una **auditoría de segunda pasada, no independiente**. No habilita live. El backend live sigue desconectado y bloqueado; H6-G2 permanece abierto y el MVP NO está listo para despliegue end-to-end. Las suites de protocolos invocaron Xray 26.10.31 únicamente con `run -test` sobre configuraciones temporales; no se inició un servidor ni se modificó runtime persistente.

Informe: `docs/AUDITORIA_H6G3_E_SEGUNDA_PASADA_2026-11-06.md`. Sin systemctl real, cambios de runtime, certificados, DNS, firewall, puertos, red, dependencias, VPS de pruebas, commit o push.

## Próximo paso obligatorio — revisión independiente H6-G3

Preparado `docs/PAQUETE_REVISION_INDEPENDIENTE_H6G3_2026-11-06.md`. Pendiente que otra IA o revisor humano inspeccione el árbol de trabajo real y emita informe adversarial. Hasta entonces G3-E sólo es segunda pasada; no integrar ni habilitar backend live.
