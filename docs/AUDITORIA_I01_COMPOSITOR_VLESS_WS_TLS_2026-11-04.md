# Auditoría técnica I-01 — Compositor VLESS-WS-TLS

**Fecha:** 2026-11-04
**Rama:** `design/user-identity-association-v1`
**HEAD base:** `bf73fd6a15aa169379c7cd71d1ea9cf5fb13f8b1`
**VPS:** `Implementación-Xray:/opt/xray-manager`
**Dictamen:** PASS — auditoría técnica focal completada; sin hallazgos bloqueantes dentro del alcance I-01.

## 1. Alcance auditado

- `scripts/vless_ws_tls_composer.py`.
- `tests/test_vless_ws_tls_composer.py`.
- Integración con `vless_config_store.py`, `users_v2_export_vless_candidate_clients`, `ProfileStore` y el contrato de mapping de `xray_runtime_staging.py`.
- Documentación de implementación y continuidad.

No se auditó ni se cerró ninguna etapa completa. R-01–R-04 no se modificaron.

## 2. Revisión de seguridad y consistencia

| Control | Resultado |
|---|---|
| Modalidad limitada a `vless_ws_tls` | PASS |
| Conexión draft y `runtime_applied=false` | PASS |
| Referencia/revisión de configuración VLESS coherente | PASS |
| Certificado central activo obligatorio | PASS |
| Exportación mediante el validador oficial Usuarios V2 | PASS |
| Exclusión de suspendidos/vencidos y rechazo de candidatos vacíos | PASS |
| UUID, tag y puerto duplicados rechazados | PASS |
| Revisión esperada verificada bajo lock de perfiles | PASS |
| Locks compartidos de catálogos durante composición | PASS |
| Rutas con componentes symlink rechazadas | PASS |
| Revisión anterior inmutable | PASS |
| Nueva revisión no validada y manifiesto pending | PASS |
| Mapping R-02 exacto, privado y atómico | PASS |
| Fallo al escribir mapping expuesto como revisión incompleta | PASS |
| No hay llamadas a Xray/systemd ni publicación runtime | PASS |

### Observaciones

1. El mapping lateral conserva exactamente `schema_version=1` y `bindings`, por lo que el parser real R-02 lo consume sin adaptar el contrato.
2. El archivo se vincula a una única revisión por su ruta `<mapping-root>/<profile_id>/<revision>.json`; el esquema JSON del perfil permanece intacto.
3. La creación de la revisión y la escritura del mapping no forman una única transacción multi-almacén. El fallo parcial se informa explícitamente y bloquea continuar a R-02; la recuperación requiere intervención deliberada.
4. No se prueba `xray run -test` sobre la revisión compuesta: los certificados se dejan vacíos intencionalmente para que R-02 inyecte los leases. La validación nativa pertenece al flujo posterior.
5. No se incorporaron Host WebSocket ni SNI/serverName del cliente, UI/menú ni activación de perfil. Esas brechas permanecen abiertas y no se presentan como resueltas.

## 3. Pruebas

| Suite/control | Resultado |
|---|---:|
| I-01 focal | **10/10 PASS** |
| Python completa | **163/163 PASS** |
| Scripts Bash completos | **58/58 PASS** |
| `python3 -m py_compile scripts/*.py tests/*.py` | PASS |
| `bash -n` en módulos/scripts/tests | PASS |
| ShellCheck `-S error` en módulos/scripts/tests | PASS |
| `git diff --check` | PASS |
| `./install.sh --check` | PASS, sin modificar el sistema |
| Parser R-02 sobre mapping generado | PASS |

La regresión Bash se ejecutó recorriendo cada `tests/*.sh`; los 58 procesos terminaron con código cero. Los mensajes de error/SIGKILL que aparecen en varias pruebas son inyecciones esperadas de escenarios negativos/recuperación, no fallos de la suite.

## 4. Entorno y límites

- Solo fixtures temporales, claves sintéticas y certificado de prueba.
- No se leyó `/etc/xray-manager/keys/master.key`.
- No se accedió a almacenes live.
- No se creó/activó una revisión en el almacén real.
- No se ejecutó Xray real sobre una configuración desplegable.
- No se llamó systemd ni se modificó `xray.service`, `/etc/xray/config.json`, firewall, puertos, DNS o red.
- No se instalaron ni actualizaron dependencias.
- No se utilizó la VPS de pruebas.
- `main` y `Xray-Normativa/` permanecen intactas.

## 5. Hallazgos y acciones pendientes

No se encontraron defectos bloqueantes en el alcance I-01 auditado. Permanecen pendientes, por diseño y fuera de este incremento:

- Integración del CLI en menú/flujo de perfiles.
- Composición de otras modalidades/protocolos.
- Incorporar Host WebSocket y parámetros de cliente/SNI en el modelo correspondiente.
- Puente de mapping con un flujo de operación que invoque R-02 de forma controlada.
- Validación nativa del perfil después de la inyección de leases.
- Pruebas live y aplicación real, que requieren autorización independiente.

## 6. Estado separado

| Estado | Resultado |
|---|---|
| IMPLEMENTADO | Sí |
| VERIFICADO | Sí — 10/10 focal, 163/163 Python, 58/58 Bash |
| AUDITADO | Sí — alcance focal I-01 |
| PUBLICADO | Pendiente de commit/push autorizado el 2026-11-05 |
| SINCRONIZADO | Pendiente de verificación posterior al push |
| ACEPTADO | Sí — aceptación formal del propietario el 2026-11-05, con las limitaciones de esta auditoría |

**Conclusión:** I-01 supera la auditoría técnica focal y la regresión y fue aceptado formalmente por el propietario el 2026-11-05, con las limitaciones aquí documentadas. La autorización de publicación se otorgó por separado. La aceptación no autoriza ejecución live ni cierra Etapa 2, 3, 4 o 5.
