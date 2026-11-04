# Integración VMess con certificados TLS centralizados — avance 2

**Fecha:** 2026-11-03  
**Bloque:** Etapa 2 — Bloque 3, integración VMess  
**Estado:** IMPLEMENTADO PARCIALMENTE; pruebas automatizadas y validación live acotada PASS; publicado en la rama autorizada; no desplegado como servicio administrado ni aceptado formalmente.

## Alcance implementado

1. `scripts/vmess_config_store.py` acepta para nuevas revisiones TLS únicamente `security_options: {certificate_id}` y exige certificado existente, activo y `managed` o `reference` en el catálogo central. No guarda secreto TLS por conexión ni crea `vmess_secret_ref` para TLS.
2. `scripts/vmess_prepare_config.py` emite el contrato TLS central y rechaza rutas TLS libres o inyección de rutas. REALITY conserva su secreto individual.
3. `scripts/vmess_tls_lease_check.py` valida la estructura y autorización local del lease: ID, directorio, manifiesto, conexión, protocolo VMess, certificado/revisión/huella, UID/GID y permisos root:<grupo-servicio> 0750/0640. Rechaza enlaces simbólicos, hardlinks, rutas externas y material fuera del lease.
4. `modules/vmess_xray_26_10_31.sh` exige ahora tres argumentos (`modelo`, `opciones`, `lease-id| -`). TLS sólo se construye si el certificado y la clave corresponden exactamente al lease y pasan la validación criptográfica. No-TLS rechaza un lease TLS.
5. `modules/vmess_assistant.sh` pasa explícitamente `XRAY_MANAGER_CERTIFICATES_RUNTIME_DIR` al resolutor, utiliza el lease en creación/validación y recuperación, y limpia el lease en éxito y fallo mediante un `EXIT` trap. La lectura de VMess también recibe el catálogo central correcto.
6. La recuperación de TLS histórico con `{certificate_file, secret_ref}` no introduce rutas libres al adaptador: informa que necesita migración controlada y falla cerrada. El store conserva la lectura histórica; no se migran ni eliminan revisiones antiguas.
7. `scripts/vless_backup.py` mantiene el alcance de backup VLESS y la preservación de entradas VMess vigentes. Durante la restauración VLESS, si una entrada VMess usa TLS central, ahora verifica que `certificate_id` exista como recurso activo `managed` o `reference` en el catálogo central. No copia ni reemplaza el almacén VMess ni el catálogo central.
8. Se ampliaron `tests/xray_vmess_integration.sh` y `tests/vless_restore_preserves_vmess.sh`; se añadió `tests/vmess_tls_lease_assistant.sh` para probar recuperación con lease, validación Xray simulada y limpieza en éxito/fallo.

## Pruebas ejecutadas

- Regresión completa `tests/*.sh`: **43/43 PASS**.
- `tests/xray_vmess_integration.sh`: Xray-core 26.10.31 validó las 14 modalidades VMess. Los leases usados por esta prueba son fixtures estructurales con UID/GID sintéticos; no prueban acceso de una unidad Xray real.
- `tests/vmess_tls_lease_assistant.sh`: PASS en recuperación TLS central, preparación/validación/limpieza del lease en éxito y fallo. El resolutor y el binario Xray se simulan en esta prueba para cubrir el ciclo del asistente.
- `tests/vless_restore_preserves_vmess.sh`: PASS para preservar VMess y validar certificado central activo; también rechaza referencia central ausente sin alterar el catálogo.
- ShellCheck con severidad `warning` de módulos y pruebas modificados: PASS.
- `bash -n` de módulos/pruebas Bash modificados: PASS.
- `python3 -m py_compile` de helper TLS, backup VLESS, resolutor y scripts VMess: PASS.
- `git diff --check`: PASS.

## Límites pendientes

- La VPS de desarrollo no dispone de un `xray.service` administrado por el proyecto. El CLI del resolutor consulta la identidad systemd y falla cerrado si ésta no está configurada. La prueba live posterior ejecutó el binario Xray real directamente bajo UID 999/GID 988 y verificó lectura del lease; no equivale a desplegar ni validar una unidad systemd del administrador.
- La prueba del ciclo del asistente usa un resolutor simulado y Xray simulado; la prueba de las 14 modalidades usa el Xray real de validación, pero con fixtures de lease. La prueba live posterior de lectura del lease y handshake TLS 1.3 está descrita por separado en `docs/VALIDACION_LIVE_VMESS_TLS_LEASE_2026-11-03.md`.
- El asistente de creación persiste el borrador antes de preparar el lease; si la identidad Xray no puede verificarse, el borrador permanece guardado y el runtime no se modifica.
- No existe todavía una operación de migración de revisiones TLS históricas. La lectura histórica se conserva; la recuperación/validación de una revisión TLS antigua falla cerrada hasta migración controlada.
- El backup VLESS sigue siendo VLESS: no incorpora el almacén VMess ni el catálogo central. El backup/restore independiente VMess y el backup compartido del recurso central corresponden al bloque de backup/restore de Etapa 2 y siguen pendientes.
- La integración VLESS con el resolutor y los generadores sigue pendiente en su bloque separado.

## Límites operativos y de gobernanza

- No se aplicaron borradores al runtime administrado ni se modificaron servicios, firewall o puertos. La prueba live posterior fue una ejecución de validación acotada del proceso Xray bajo UID/GID no privilegiados con materiales sintéticos.
- No se modificó la VPS `Vps de Pruebas`, no se importaron certificados reales persistentes y no se migraron secretos históricos.
- REALITY permanece separado.
- `Xray-Normativa/` y `main` no se modificaron.
- La implementación y su documentación forman parte de la rama autorizada `design/user-identity-association-v1`. La evidencia live adicional se registra en un informe separado; su incorporación documental no cambia la clasificación de aceptación.

## Clasificación

| Estado | Resultado |
|---|---|
| IMPLEMENTADO | Adaptador TLS por lease, recuperación/limpieza del asistente y validación de referencias centrales en restore VLESS |
| VERIFICADO | Suite 43/43 y validaciones automatizadas históricas; además, lectura live del lease por Xray-core 26.10.31 bajo UID 999/GID 988 y handshake TLS 1.3 en la segunda ejecución; evidencia acotada en informe separado |
| PUBLICADO | Implementación y documentación en `design/user-identity-association-v1` |
| SINCRONIZADO | El checkout de VPS y GitHub coincidían en el HEAD auditado antes de esta regularización documental |
| ACEPTADO | No; Bloque 3/VMess y Etapa 2 continúan abiertos |


## Actualización cruzada — integración VLESS (2026-11-03)

La integración VLESS TLS centralizada ya comenzó en un bloque separado. Su estado, pruebas y límites se documentan en `docs/IMPLEMENTACION_VLESS_TLS_CENTRALIZADO_PARCIAL.md`. Esto no modifica la clasificación de VMess de este informe ni convierte la integración conjunta en completa. El backup compartido del catálogo central, la migración histórica y la lectura de leases por un servicio Xray real siguen pendientes.


## Actualización — validación live de lectura del lease por Xray real (2026-11-03)

La evidencia compartida por el propietario confirma una prueba live acotada posterior a las pruebas con fixtures: Xray-core 26.10.31 se ejecutó como UID 999/GID 988, accedió al certificado y a la clave sintéticos del lease y completó un handshake TLS 1.3 verificado en la segunda ejecución. La primera ejecución no se contabiliza como exitosa.

El resultado demuestra que un proceso Xray real pudo leer los materiales sintéticos del lease bajo esa identidad. No demuestra que `xray.service` del administrador esté instalado/configurado, que el flujo completo del asistente haya aplicado una conexión al runtime, que se hayan usado certificados reales, que exista conectividad WAN ni que VMess haya recibido aceptación formal. No se atribuyen suite, comandos, cipher suite, endpoint o logs no incluidos en la evidencia disponible.

Informe: `docs/VALIDACION_LIVE_VMESS_TLS_LEASE_2026-11-03.md`.
