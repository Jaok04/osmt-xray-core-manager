# Punto de control actual — Xray Core Manager

**Fecha del corte:** 2026-11-03
**Tarea activa:** backup/restore compartido — contenedor criptográfico neutral v1 implementado y probado; alcance incremental, contrato de manifiesto y formato ZIP/JSON lógico v1 aprobados; máximo de miembros cerrado en 10.000 entradas ZIP; pendiente diseño de writer/snapshot. VMess continúa técnicamente preparado para aceptación formal; VM-48 sigue pendiente.
**Estado vigente:** contenedor compartido v1 IMPLEMENTADO/VERIFICADO en aislamiento; backup/restore integral PENDIENTE. F-01 a F-05 RESUELTOS/VERIFICADOS; VM-28 VERIFICADO; VM-32 VERIFICADO CON LÍMITE TRANSACCIONAL DOCUMENTADO; VM-33 NO APLICA AL ALCANCE APROBADO; VM-38/39/40 focal PASS; suite 40/40 PASS; Xray 14/14 y 16 negativos PASS; VM-46 live PASS; VM-47 VMess-TLS cliente-servidor loopback PASS. Cliente externo/WAN no probado y no requerido por el diseño aprobado. VMess está técnicamente preparado, pero VM-48 requiere aceptación expresa; Etapa 2 ABIERTA.

**Regla de cierre de etapas:** Etapa 2 permanece ABIERTA aunque VMess esté técnicamente listo. No se podrá declarar completada hasta auditar y documentar todos los puntos, subpuntos, protocolos, modalidades, flujos, módulos y componentes internos definidos por la línea base aprobada, ejecutar la regresión integral y obtener aceptación formal del propietario. Aplicar `docs/REGLA_AUDITORIA_INTEGRAL_CIERRE_ETAPAS.md`.

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
- Suites históricas anteriores: 36/36, 37/37, 38/38 y 39/39 PASS. Revalidación actual: `tests/*.sh` 40/40 PASS, incluida `tests/vmess_navigation_edge_cases.sh`.
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
- Suite completa: 37/37 scripts PASS. Sintaxis Bash/Python, `install.sh --check`, ShellCheck sobre pruebas modificadas y `git diff --check`: PASS.
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

**Pendiente:** repetir la suite completa tras esta segunda corrección y continuar la auditoría global de todos los mutadores/locks. No iniciar writer de backup compartido hasta cerrar la auditoría y contrato de snapshot.

## 16. Auditoría estática de locks — 2026-11-03

**Resultado:** inventario estático de los puntos de adquisición del repositorio completado; no se encontró ciclo/inversión en los caminos inspeccionados.

**Orden recomendado del snapshot:** lifecycle → integrity → catalog; liberar en orden inverso. Writer con adquisición no bloqueante y timeout finito configurable. No usar flock bloqueante indefinido.

**Pruebas:** contención lifecycle/integrity/catalog/Xray, catalog retenido durante confirmación, liberación ante lock Xray ocupado y supervivencia del lock fuera del árbol eliminado. Suite 47/47 PASS; Bash syntax, ShellCheck uninstall, shfmt focal, py_compile y git diff check PASS.

**Limitación:** estática, no stress test exhaustivo. La ruta TLS nueva requiere despliegue con procesos de versión anterior detenidos. No se movió el lock anterior ni se ejecutó runtime apply.

**Siguiente decisión pendiente:** cerrar alcance inicial de categorías/adaptadores del snapshot conforme a Etapa 5 antes de implementar el writer.


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
