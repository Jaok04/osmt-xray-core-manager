# Auditoría focal I-02 / I-03 — VLESS-WS-TLS

**Fecha:** 2026-11-05
**Alcance:** integración del compositor en el menú de perfiles; persistencia y emisión de Host WebSocket/SNI cliente; compatibilidad de config store, resolver y backup/restore.
**Normativa:** Etapa 2 y Etapa 5 contrastadas; no se modificó Xray-Normativa.

## Resultado

Resultado: PASS — alcance focal

### Pruebas específicas

- `tests/test_vless_ws_tls_composer.py`: 11/11 PASS.
- `tests/profiles_vless_composer_menu.sh`: PASS; selección, preview con Host/SNI/certificado, confirmación, nueva revisión y no activación.
- `tests/vless_tls_lease_assistant.sh`: PASS; persistencia Host/SNI separados y recuperación TLS con Xray simulado.
- `tests/vless_tls_central_backup.sh`: PASS; backup/restore de esquemas VLESS 1 y 2, Host/SNI y referencia TLS central.
- `tests/vless_backup.sh`: PASS.
- `tests/xray_vless_integration.sh`: PASS con Xray 26.10.31; valida VLESS-WS-TLS sin Host y con `wsSettings.host`, y rechaza Host inválido.
- ShellCheck focal de módulos/tests modificados: PASS.
- `bash -n` de módulos/tests modificados: PASS.
- `git diff --check`: PASS.

### Regresión completa final

- Python: 164/164 PASS.
- Bash: 59/59 scripts PASS.
- py_compile de scripts y tests: PASS.
- bash -n global de módulos, scripts, tests, librerías, ejecutable e instalador: PASS.
- ShellCheck -S error en todos los módulos y tests Bash modificados: PASS.
- git diff --check: PASS.
- install.sh --check: PASS, no modificó el sistema.
- La suite incluyó Xray 26.10.31; VLESS-WS-TLS con y sin Host fue aceptado. Permanecen los avisos generales de obsolescencia del transporte WebSocket ya conocidos y aceptados por el propietario.

ShellCheck global completo sobre todos los scripts/módulos/tests también había pasado en la ejecución previa; la ejecución final repitió ShellCheck en todos los archivos Bash modificados.

## Matriz de estado

| Área | Resultado |
|---|---|
| I-02 menú y compositor | IMPLEMENTADO / VERIFICADO en fixtures |
| Host WebSocket | IMPLEMENTADO / Xray 26.10.31 VALIDADO |
| SNI del cliente | PERSISTIDO / validación de esquema PASS |
| Config Store / Resolver / Backup | ESQUEMA 1 Y 2 COMPATIBLES |
| Xray/systemd live | NO EJECUTADO |
| Exportación URI cliente | Implementada y auditada por separado en I-04 |
| Auditoría | PASS en el alcance indicado |
| Publicación GitHub | NO AUTORIZADA en esta tarea |
| Sincronización GitHub/VPS | No aplica; cambios solo locales sin commit |
| Aceptación formal del propietario | ACEPTADA el 2026-11-05, con las limitaciones de esta auditoría |

## Hallazgos y observaciones

1. La normativa no especifica Host/SNI en detalle; se incorporaron como decisión complementaria autorizada y separada.
2. Xray 26.10.31 aceptó `wsSettings.host`. La variante `wsSettings.headers.Host` produjo advertencia de obsolescencia y se descartó.
3. La advertencia genérica de obsolescencia de transporte WebSocket sigue siendo emitida por Xray; se conserva la modalidad solicitada, según decisión previa del propietario.
4. SNI del cliente no es un campo de inbound Xray. Se conserva en `client_options.tls_server_name`; no se confunde con el certificado del servidor.
5. No se genera URI de cliente sin endpoint público confirmado.
6. No se activaron perfiles ni se invocaron R-01–R-04.

**Conclusión:** no se identificaron fallos bloqueantes dentro del alcance focal probado. I-02 e I-03 quedan IMPLEMENTADOS, VERIFICADOS, AUDITADOS y ACEPTADOS FORMALMENTE el 2026-11-05, con las limitaciones descritas. La exportación URI se cubre por separado en I-04. La publicación se autorizó expresamente en la rama autorizada.
