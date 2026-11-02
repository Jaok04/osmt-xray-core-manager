# Punto de control actual — Xray Core Manager

**Fecha del corte:** 2026-11-02
**Tarea:** bloque correctivo autorizado F-01 a F-04 y revalidación de VMess.
**Estado vigente:** F-01 a F-04 CORREGIDOS y VERIFICADOS en fixtures; suite 39/39 PASS; Xray 14/14 y 16 negativos PASS. F-05 live NO VERIFICADO. VMess NO está aceptado; Etapa 2 ABIERTA.

**Regla de cierre de etapas:** Etapa 2 permanece ABIERTA aunque VMess esté técnicamente listo. No se podrá declarar completada hasta auditar y documentar todos los puntos, subpuntos, protocolos, modalidades, flujos, módulos y componentes internos definidos por la línea base aprobada, ejecutar la regresión integral y obtener aceptación formal del propietario. Aplicar `docs/REGLA_AUDITORIA_INTEGRAL_CIERRE_ETAPAS.md`.

## 1. Entorno verificado

- Repositorio: `Jaok04/xray-core-manager`.
- Rama autorizada: `design/user-identity-association-v1`.
- Proyecto VPS: `/opt/xray-manager`.
- HEAD de partida de la auditoría: df632aee5d8139c721b81a6d65f14d93f7676226; bloque correctivo y expediente publicados/sincronizados en d2d33a32bdf5e21d1d35ad41d00bd0b116443cb7.
- Commit Bloque 1: `c890b5b5362e17e439f198b9b8bbbdbe0af0c653` (`fix(vless): preserve current VMess entries on restore`), publicado y sincronizado.
- Remoto: `git@github.com-xray-core-manager:Jaok04/xray-core-manager.git`.
- Deploy Key SSH dedicada con permiso de escritura configurado.
- Documentación normativa: `/root/Xray_Manager_Documentacion_Final_2026-10-31`.
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
- Suite completa anterior de VMess: 36/36 scripts PASS. Tras el Bloque 1: 37/37 scripts PASS. Tras el Bloque 3: suite completa `tests/*.sh` 38/38 PASS, incluyendo las pruebas ampliadas de asistente y persistencia.
- Controles estáticos tras Bloque 3: `bash -n` de todos los scripts Bash, `python3 -m py_compile scripts/*.py`, `./install.sh --check`, ShellCheck (`-S warning`) sobre los archivos modificados y `git diff --check`: PASS. shfmt no se reformateó; el criterio sigue pendiente del Bloque 4.

## 4. Límites que no bloquean el cierre de VMess

- `xray run -test` valida estructura y configuración; no demuestra conectividad extremo a extremo.
- No se realizó prueba cliente-servidor real.
- No se activaron borradores ni se modificó configuración activa, runtime, servicio, firewall o puertos.
- Usuarios VMess se introducen manualmente; integración con identidades globales corresponde a Etapa 3.
- Backup/restore VMess no está implementado y requiere diseño y autorización separados.
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
| IMPLEMENTADO | Sí — base VMess y correcciones F-01 a F-04 implementadas |
| VERIFICADO | Pruebas focales y suite 39/39 PASS; Xray 14/14 y 16 negativos PASS. F-05 live no verificado; VM-38 prueba específica pendiente y VM-39/40 cobertura parcial |
| PUBLICADO | Base, Bloques 1–4 y bloque correctivo F-01–F-04 publicados; commit d2d33a3 |
| SINCRONIZADO | HEAD VPS/local/remoto coincidente: d2d33a32bdf5e21d1d35ad41d00bd0b116443cb7 |
| ACEPTADO | NO — F-05 live y cobertura de auditoría restante pendientes |

## 7. Siguiente acción

F-01 a F-04 están corregidos y revalidados. Siguiente paso independiente: solicitar autorización para validar F-05 en un entorno live controlado y resolver cobertura pendiente de VM-38/39/40. No aceptar VMess ni iniciar Trojan.

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
