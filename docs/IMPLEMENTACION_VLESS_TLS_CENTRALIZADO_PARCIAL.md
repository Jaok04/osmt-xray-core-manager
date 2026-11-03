# Integración VLESS TLS centralizado — implementación parcial

**Fecha:** 2026-11-03
**Estado:** IMPLEMENTADO PARCIALMENTE / VERIFICADO EN FIXTURES / NO PUBLICADO / NO SINCRONIZADO / NO ACEPTADO
**Rama:** `design/user-identity-association-v1`
**HEAD remoto de partida:** `8d3b8482da369e902b32795dc3a36e5023d25e62`
**Ruta VPS:** `/opt/xray-manager`

## 1. Alcance y gobernanza

Se inició la integración VLESS con el catálogo central de certificados TLS conforme al contrato de `docs/ARQUITECTURA_CERTIFICADOS_CENTRALIZADOS.md`. Se contrastó el diseño con `Xray-Normativa/02_Protocolos_Conexiones/Etapa_2_Protocolos.md` y su YAML. Se conservaron las modalidades VLESS existentes; REALITY permanece separado.

`Xray-Normativa/` no se modificó. No se cambió `main`, no se hizo commit/push ni se aplicó configuración al runtime. No se tocaron servicios, firewall, puertos, certificados desplegados ni la VPS de pruebas.

## 2. Contrato de persistencia

### Nuevas revisiones TLS

`scripts/vless_config_store.py` admite el contrato:

```json
{
  "security": "tls",
  "security_options": {
    "certificate_id": "cert-example"
  }
}
```

- `certificate_id` debe tener formato válido y corresponder a un recurso activo `managed` o `reference` del catálogo central.
- La revisión VLESS no guarda `certificate_file`, `key_file`, `secret_ref` ni una copia cifrada de la clave privada.
- El registro de conexión mantiene `secret_ref: null` para TLS central.
- Se rechazan rutas TLS libres, IDs inexistentes/inactivos y argumentos de secreto privado por conexión.
- La lectura y auditoría vuelven a comprobar que el certificado central siga activo y que no exista una referencia de secreto individual.

### Compatibilidad histórica y REALITY

- La lectura/auditoría mantienen compatibilidad con revisiones TLS históricas `{certificate_file, secret_ref}`.
- El store no acepta ese formato para nuevas revisiones.
- No se migran ni borran secretos históricos.
- REALITY mantiene su clave individual cifrada y su contrato independiente.
- La recuperación del asistente no intenta convertir una revisión TLS histórica en una resolución por rutas: falla cerrada y deja la migración para un procedimiento versionado posterior.

## 3. Preparación y adaptador Xray

- `scripts/vless_prepare_config.py` emite `security_options: {certificate_id}` para TLS y no extrae ni escribe una clave privada por conexión. REALITY sigue produciendo su secreto cifrado individual.
- `modules/vless_xray_26_10_31.sh` recibe opcionalmente un tercer argumento `lease-id|-`. Para TLS exige un lease `resolve-*`; no acepta construir TLS con rutas libres ni sin lease.
- Nuevo `scripts/vless_tls_lease_check.py` verifica la raíz y el directorio del lease, manifest, conexión VLESS, protocolo, certificado, revisión, fingerprint, UID/GID, propietario, grupo, modos y archivos regulares. Las rutas de certificado/clave deben ser exactamente las del lease.
- Un lease no puede utilizarse con modalidades sin TLS o REALITY.

## 4. Asistente y recuperación

- El asistente solicita un ID de certificado central, no rutas de certificado/clave.
- Para TLS, el borrador se guarda bajo confirmación antes de solicitar el lease, porque el resolutor comprueba que la revisión persistida autorice exactamente ese `certificate_id`.
- Si el resolutor no puede verificar la identidad real de Xray, el borrador permanece guardado y la validación falla cerrada; no se modifica runtime.
- Cuando se obtiene un lease, el adaptador construye el JSON con las rutas exactas y, si existe el binario fijado, se ejecuta `xray run -test`. El asistente limpia el lease en éxito y en salida por error mediante `EXIT` trap.
- La recuperación de TLS central vuelve a resolver el certificado y usa un lease temporal. La recuperación de TLS histórico se detiene hasta que exista migración controlada.
- REALITY continúa usando su secreto recuperado temporalmente y no usa el resolutor TLS.

## 5. Backup y restauración

`scripts/vless_backup.py` fue actualizado:

- El manifiesto documenta `certificate_id` como dependencia externa del catálogo central; no incluye ni duplica la clave privada central.
- La validación del payload acepta TLS central sin secreto por conexión, pero rechaza IDs malformados y sigue exigiendo blobs para REALITY y TLS histórico.
- Antes de publicar una restauración con referencias TLS centrales, se exige que el catálogo hermano `certificates/catalog.json` exista y que cada recurso esté activo y sea `managed` o `reference`.
- Si falta el catálogo o el recurso, la restauración se detiene antes de publicar y preserva los datos activos.
- El backup VLESS no incorpora el almacén central de certificados ni el almacén VMess; la dependencia externa se documenta en el manifiesto.

## 6. Pruebas y verificaciones

Pruebas ejecutadas en la VPS de desarrollo, con fixtures temporales:

- Suite completa `tests/*.sh`: **45/45 PASS**.
- Xray-core 26.10.31: **9/9 modalidades VLESS** aceptadas, incluidas TLS centralizado mediante leases de fixture y REALITY; se rechaza TLS sin lease.
- `tests/vless_config_store.sh`: TLS central persiste únicamente `certificate_id`, sin blob por conexión; rechaza certificado inexistente y secreto TLS individual.
- `tests/vless_assistant.sh`: REALITY sigue cifrado; TLS central queda persistido sin secreto individual; el asistente falla cerrado cuando no hay identidad systemd válida.
- `tests/vless_tls_lease_assistant.sh`: `systemctl` simulado informa la identidad `www-data`; un Xray shim verifica que ese UID/GID puede leer certificado/clave del lease y que el asistente limpia el lease tanto tras éxito como tras fallo. Recorre creación RAW/TCP y recuperación RAW/TCP, WS, gRPC y XHTTP. Es una prueba de permisos/ciclo de vida con identidad simulada, no una prueba con Xray real.
- `tests/vless_tls_central_backup.sh`: backup/restore conserva `certificate_id`, no duplica claves y rechaza catálogo central ausente sin alterar los datos activos.
- `tests/vless_restore_preserves_vmess.sh`: preservación VMess y validación de sus referencias centrales siguen pasando.
- `tests/certificate_resolver.sh`: autorización VLESS/VMess, leases temporales, permisos y cleanup PASS.
- `bash -n` de todos los `.sh`: PASS.
- `python3 -m py_compile scripts/*.py`: PASS.
- `./install.sh --check`: PASS, sin modificar el sistema.
- ShellCheck severidad warning de los archivos Bash modificados: PASS.
- `git diff --check`: PASS.

## 7. Límites que permanecen abiertos

1. La VPS de desarrollo no tiene una unidad `xray.service` con `User` y `Group` explícitos y no privilegiados. El CLI real del resolutor falla cerrado. La prueba del asistente confirma ese comportamiento; no se ha probado que un proceso Xray real lea el lease.
2. Las pruebas Xray utilizan certificados, claves y leases de fixture. No son una prueba de conectividad cliente-servidor ni de runtime.
3. No se ejecutó `runtime apply`, reinicio de Xray, cambio de firewall, apertura de puertos ni despliegue de certificados.
4. No se migraron TLS históricos ni se eliminaron blobs antiguos.
5. El catálogo central y sus secretos no forman parte del backup VLESS; la restauración exige que el recurso central ya exista y esté activo.
6. La integración VLESS sigue siendo parcial. No constituye aceptación del módulo ni cierre de Etapa 2/Etapa 4.

## 8. Siguiente trabajo

- Ampliar pruebas negativas de lease cruzado, protocolo incorrecto y rutas externas en cada modalidad TLS VLESS; la matriz positiva de recuperación cubre RAW/TCP, WS, gRPC y XHTTP.
- Diseñar y aprobar la migración histórica VLESS/VMess por fingerprint, con backup, staging, rollback y conservación del original.
- Diseñar backup/restore compartido del catálogo central y sus secretos, sin romper el aislamiento de los backups de protocolo actuales.
- Cuando exista un entorno autorizado con unidad Xray no privilegiada, probar lectura real del lease y su ciclo de vida; no desplegar por inferencia.
- Ejecutar auditoría integral, matriz de trazabilidad y regresión final antes de solicitar aceptación.

**Estado final de este bloque:** contrato VLESS TLS central IMPLEMENTADO PARCIALMENTE y VERIFICADO EN FIXTURES; NO PUBLICADO, NO SINCRONIZADO y NO ACEPTADO. Etapa 2 continúa ABIERTA.


## Actualización de matriz y auditoría cruzada (2026-11-03)

- Se corrigió `modules/vless_xray_26_10_31.sh`: `vless_ws_tls` ahora acepta `path` junto con `certificate_file` y `key_file` del lease; antes la recuperación reconstruía correctamente el transporte pero el adaptador rechazaba esa combinación. `vless_tcp_tls` conserva únicamente certificado/clave; gRPC y XHTTP conservan sus opciones de transporte específicas.
- `tests/vless_tls_lease_assistant.sh` ahora recorre recuperación de RAW/TCP, WS, gRPC y XHTTP, además de creación RAW/TCP y cleanup en éxito/fallo. `tests/xray_vless_integration.sh` valida nuevamente WS-TLS con path.
- Auditoría cruzada: ambos validadores de lease comprueban la misma estructura y permisos POSIX, diferenciando `protocol` (`vless`/`vmess`). Se alinearon las llamadas del asistente VMess para pasar explícitamente rutas configurables del catálogo, managed dir, secretos, lock y master key al resolutor, igual que VLESS; así no dependen accidentalmente de defaults cuando el proyecto usa rutas personalizadas.
- Suite completa `tests/*.sh`: 45/45 PASS tras estas correcciones.
- Se añadieron propuestas no ejecutables: `docs/PLAN_MIGRACION_TLS_HISTORICO.md` y `docs/PLAN_BACKUP_RESTORE_CENTRAL.md`. Definen preflight, deduplicación por identidad criptográfica, journal/reanudación/rollback y estrategia de backup compartido. Ninguna migración ni backup compartido se implementó.
