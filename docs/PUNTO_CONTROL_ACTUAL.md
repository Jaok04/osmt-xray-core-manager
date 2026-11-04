# Punto de control actual — Xray Core Manager

> Los puntos anteriores son históricos. El punto operativo vigente es el último bloque «Almacén de perfiles v1.1 cifrado — 2026-11-03» al final de este documento.

**Fecha del corte:** 2026-11-03
**Tarea activa:** cerrar verificación y publicación del almacén de perfiles v1.1 con AES-256-GCM. La primera implementación plaintext no fue publicada; el propietario eligió cifrado autenticado. La nueva versión cifra el JSON completo en `config.enc.json` y usa sólo la clave maestra existente, sin crearla ni regenerarla. Regresión integral ejecutada: 51/51 scripts PASS; AST 18/18; bash -n global PASS; ShellCheck focal PASS; shfmt de los dos archivos nuevos PASS. Pendientes: revisión final del diff, commit/push y sincronización GitHub/VPS.
**Estado vigente:** almacén de perfiles v1.1 IMPLEMENTADO LOCALMENTE; aceptación formal pendiente. Regresión integral y publicación pendientes. Contenedor compartido v1 IMPLEMENTADO/VERIFICADO en aislamiento; backup/restore integral PENDIENTE. F-01 a F-05 RESUELTOS/VERIFICADOS; VM-28 VERIFICADO; VM-32 VERIFICADO CON LÍMITE TRANSACCIONAL DOCUMENTADO; VM-33 NO APLICA; VM-38/39/40 focal PASS; suite 40/40 PASS; VM-46 live PASS; VM-47 VMess-TLS loopback PASS. Adicionalmente, Xray-core 26.10.31 está instalado en la VPS; VLESS-WS (conn-1793749234-670662) está creado/persistido/validado como draft, sin runtime apply ni listener. Etapa 2 ABIERTA.

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

**Siguiente acción:** auditar diff/diseño y construir la validación estática Xray por revisión, con informe y pruebas de fallo/rollback. Mantener eliminación y activación deshabilitadas. No ampliar a composición/activación hasta terminar la auditoría del almacén y aprobar el siguiente bloque.


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

**Pendiente:** revisar diff completo; registrar commit; publicar en `design/user-identity-association-v1`; verificar archivos/HEAD remotos y sincronizar la VPS sin reset/clean destructivo. No modificar `main` ni `Xray-Normativa/`. No tocar runtime, servicios, firewall, puertos, certificados o red. Etapa 2 continúa ABIERTA.