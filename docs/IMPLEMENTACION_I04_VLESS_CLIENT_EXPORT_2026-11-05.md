# Implementación I-04 — Exportación de clientes VLESS-WS-TLS para NetMod

**Fecha:** 2026-11-05
**Autorización:** el propietario confirmó expresamente la exportación de perfiles VLESS-WS-TLS con endpoint `hellen.tvrc.me:443`.
**Rama de trabajo:** `design/user-identity-association-v1`.
**Estado:** implementada y verificada en fixtures; aceptación formal pendiente; no publicada.

## 1. Alcance

Se añadió la exportación de URI `vless://` por cliente UUID desde una revisión exacta del almacén de perfiles. El endpoint inicial autorizado es `hellen.tvrc.me:443`, coincidente con el puerto del inbound VLESS-WS-TLS.

## 2. Implementación

- Nuevo módulo `scripts/vless_client_export.py`.
- Nueva opción [10] en el menú de perfiles: exportar clientes VLESS-WS-TLS para NetMod.
- Selección explícita del perfil y de la revisión exacta; no se sustituye silenciosamente por la revisión actual.
- Lectura de configuración cifrada mediante `ProfileStore.read_revision_config` bajo lock compartido de solo lectura. No se utiliza `ProfileStore.locked()`, porque ese flujo ejecuta recuperación y limpieza de artefactos; la exportación no debe producir esos efectos secundarios.
- Lectura del mapping privado de la revisión y comprobación exacta contra todos los inbounds TLS centralizados (incluidos otros protocolos). Para cada inbound VLESS-WS-TLS se exige asociación única `inbound_tag → connection_id`.
- Recuperación de la configuración fuente mediante VLESS Config Store y validación de que modalidad, transporte, seguridad, puerto, path y Host coincidan con el inbound.
- Generación de un URI por UUID, con `encryption=none`, `security=tls`, `type=ws`, path codificado y fragmento descriptivo.
- `sni` se incluye solo si está guardado en `client_options.tls_server_name`; `host` se incluye solo si está guardado en `transport_options.host`. No se infieren del endpoint.
- Validación estricta de dominio/IP, UUID, puerto, tags, mapping, configuración fuente y archivos privados.
- Salida por pantalla o archivo TXT opcional. El archivo se crea con modo 0600, escritura atómica y sin sobrescritura; el directorio de destino debe ser root:root 0700 y nunca se cambian sus permisos.
- Se rechaza exportación parcial si hay mappings faltantes/extras, conflicto de puerto o cualquier incoherencia.

## 3. URI de referencia

Con los valores de fixture usados en las pruebas, la estructura generada es:

`vless://UUID@hellen.tvrc.me:443?encryption=none&security=tls&sni=SNI&type=ws&host=HOST&path=%2Fws#ETIQUETA`

Los valores reales se toman de la revisión y de la configuración persistida. El ejemplo anterior es ilustrativo, no una credencial real.

## 4. Pruebas y evidencia

- `tests/test_vless_client_export.py`: 7/7 PASS.
- `tests/profiles_vless_composer_menu.sh`: PASS; compone el perfil en fixture y exporta el URI desde el menú con endpoint `hellen.tvrc.me:443`.
- Se verificó URI por cada cliente, Host y SNI separados, omisión de Host/SNI no configurados, codificación del path, puerto coincidente, rechazo de UUID inválido, mapping ausente/incompleto/excedente y archivo 0600 sin sobrescritura.
- Regresión Python: 171/171 PASS.
- Regresión Bash: 59/59 PASS.
- `py_compile`: PASS.
- `bash -n` global: PASS.
- ShellCheck `-S error` sobre los archivos Bash modificados: PASS.
- `./install.sh --check`: PASS, no-op.
- `git diff --check`: PASS.

## 5. Límites

- No se importó el URI en la aplicación NetMod real ni se probó conectividad WAN.
- El URI no certifica que DNS resuelva a este servidor, que exista un listener público 443 ni que el certificado desplegado cubra el SNI.
- La exportación no activa ni valida perfiles, no ejecuta R-01–R-04 y no inicia/reinicia Xray/systemd.
- No se modificaron DNS, firewall, puertos, certificados reales, runtime, dependencias, VPS de pruebas, `main` ni `Xray-Normativa/`.
- I-02/I-03 continúan sin aceptación formal ni publicación; I-04 tampoco está aceptada/publicada. El conjunto local no se ha sincronizado con GitHub.

## 6. Estado

I-04: **IMPLEMENTADA**, **VERIFICADA** y **DOCUMENTADA** en alcance focal. **ACEPTACIÓN FORMAL PENDIENTE**. **NO PUBLICADA** y **NO SINCRONIZADA**. Etapas 2, 3 y 5 permanecen abiertas.
