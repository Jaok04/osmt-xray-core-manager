# Auditoría focal I-04 — Exportación VLESS-WS-TLS para NetMod

**Fecha:** 2026-11-05
**Alcance:** exportación de clientes desde una revisión exacta de perfil con endpoint público `hellen.tvrc.me:443`.
**Resultado:** PASS en el alcance de fixtures.

## 1. Matriz de auditoría

| Control | Resultado |
|---|---|
| Perfil y revisión exactos | PASS |
| Lock compartido de solo lectura; sin recuperación/limpieza de almacén | PASS |
| Mapping privado root:root 0600 y directorio 0700 | PASS |
| Mapping exacto frente a inbounds TLS centralizados | PASS |
| Mapping inbound → connection_id | PASS |
| Configuración fuente validada por VLESS Config Store | PASS |
| Coherencia modalidad/transporte/seguridad/puerto/path/Host | PASS |
| UUID válido y no duplicado | PASS |
| Host WebSocket separado de endpoint | PASS |
| SNI cliente separado de endpoint y certificado servidor | PASS |
| Codificación de URI y path | PASS |
| Rechazo de puerto público distinto al inbound | PASS |
| Archivo opcional 0600, atómico y sin sobrescritura | PASS |
| No aplica runtime ni modifica servicios/red | PASS |

## 2. Pruebas

- Exportador: 7/7 PASS.
- Integración de menú/compositor: PASS.
- Python total: 171/171 PASS.
- Bash total: 59/59 PASS.
- `py_compile`: PASS.
- `bash -n` global: PASS.
- ShellCheck `-S error` focal: PASS.
- `install.sh --check`: PASS, no-op.
- `git diff --check`: PASS.

## 3. Límites de auditoría

No se probó la importación dentro de NetMod ni la conectividad externa. No se comprobó DNS, listener público, firewall, certificado desplegado o runtime. La exportación refleja únicamente datos persistidos y el endpoint indicado por el propietario; no afirma disponibilidad real del servicio.

## 4. Dictamen

No se identificaron fallos en los controles focales ejecutados. I-04 queda IMPLEMENTADA, VERIFICADA y AUDITADA en fixtures. El propietario aceptó formalmente I-04 el 2026-11-05 con las limitaciones documentadas y autorizó expresamente commit/push/sincronización exclusivamente en `design/user-identity-association-v1`. La publicación se registra en el addendum de HISTORY una vez verificado el SHA remoto.
