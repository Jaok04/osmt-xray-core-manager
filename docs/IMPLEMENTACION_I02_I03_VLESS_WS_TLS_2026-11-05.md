# Implementación I-02 / I-03 — Integración VLESS-WS-TLS en perfiles y Host/SNI

**Fecha:** 2026-11-05
**Autorización:** confirmación expresa del propietario para I-02 e I-03.
**Rama:** design/user-identity-association-v1.
**Estado:** I-02 implementado/verificado en fixtures; I-03 implementado en persistencia/adaptador, con exportación URI de cliente pendiente de endpoint.

## 1. Contraste normativo

La normativa aprobada de Etapa 2 contempla VLESS-WS-TLS como modalidad WebSocket + TLS y requiere validar la configuración con la versión objetivo. No fija expresamente la forma de guardar Host WebSocket ni SNI/serverName del cliente. Por ello se documentaron como decisión complementaria en `docs/DECISION_I02_I03_VLESS_WS_TLS.md`, autorizada por el propietario, sin editar `Xray-Normativa/`.

## 2. I-02 — Menú de composición de perfiles

- Se añadió la opción [9] al menú de perfiles.
- Selecciona un perfil con configuración y su revisión actual exacta.
- Filtra conexiones VLESS-WS-TLS con estado `draft` y `runtime_applied=false`.
- Lee la configuración mediante VLESS Config Store, no por rutas construidas desde el catálogo.
- Previsualiza perfil/revisión/conexión/puerto, path WebSocket, Host, SNI del cliente y certificado TLS central.
- Solicita confirmación explícita antes de invocar I-01.
- Reutiliza catálogos Usuarios V2, conexiones, certificado central y mapping TLS previo.
- Crea una nueva revisión inmutable pendiente de validación; no modifica revisiones anteriores.
- No activa perfil, no invoca R-01–R-04 y no toca Xray/systemd/runtime.
- Mantiene fail-closed si el mapping TLS anterior falta o es incompleto.

## 3. I-03 — Host WebSocket y SNI del cliente

### Host WebSocket

- Campo opcional persistido como `transport_options.host`.
- Se valida como nombre DNS ASCII de hasta 253 caracteres, sin espacios, puerto, comodines ni caracteres de control.
- El adaptador genera `streamSettings.wsSettings.host`.
- La validación real con Xray 26.10.31 confirmó que esta forma funciona. Xray emitía una advertencia de obsolescencia al usar `wsSettings.headers.Host`; se descartó esa representación y se adoptó `wsSettings.host`, que es el campo independiente vigente.

### SNI/serverName del cliente

- Campo opcional persistido como `client_options.tls_server_name`.
- Se valida como nombre DNS ASCII; no admite puerto, comodines, espacios ni caracteres de control.
- Solo se almacena como metadata del lado cliente. No se inyecta en el inbound, no sustituye el certificado TLS del servidor y no cambia el lease central.
- La configuración usa esquema 2 cuando se guarda Host o SNI. Las configuraciones de esquema 1 siguen siendo válidas.
- Config Store, Certificate Resolver, backup y restore reconocen esquema 2 y preservan Host/SNI. El backup continúa excluyendo claves privadas/catálogo central.

## 4. Archivos modificados

- `modules/profiles.sh`
- `modules/vless_assistant.sh`
- `modules/vless_xray_26_10_31.sh`
- `scripts/vless_config_store.py`
- `scripts/vless_prepare_config.py`
- `scripts/vless_ws_tls_composer.py`
- `scripts/certificate_resolver.py`
- `scripts/vless_backup.py`
- `tests/test_vless_ws_tls_composer.py`
- `tests/profiles_vless_composer_menu.sh`
- `tests/vless_tls_lease_assistant.sh`
- `tests/vless_tls_central_backup.sh`
- `tests/xray_vless_integration.sh`
- `docs/DECISION_I02_I03_VLESS_WS_TLS.md`

## 5. Límites pendientes

- No se genera aún un URI `vless://` ni un archivo de importación para NetMod. Para hacerlo falta elegir/confirmar el endpoint público (dominio/IP) asociado a cada conexión y su política de exportación. El SNI se guarda, pero no se inventa el endpoint ni se exporta un URI incompleto.
- No se ha integrado activación de perfil ni R-01–R-04 en el menú.
- Regresión completa final: Python 164/164 y Bash 59/59 PASS; py_compile, bash -n global, ShellCheck focal en todos los Bash modificados, git diff --check e install.sh --check PASS. ShellCheck global completo había pasado en la ejecución previa.
- No hay prueba de conectividad externa ni live.
- I-02/I-03 no cierran Etapa 2 ni ninguna otra etapa.

## 6. Seguridad

Solo fixtures, datos sintéticos, claves/certificados temporales y Xray de validación. No se leyó la clave maestra real. No se modificaron runtime Xray/systemd, certificados desplegados, firewall, puertos, DNS, red, dependencias, VPS de pruebas, `main` ni `Xray-Normativa/`.
