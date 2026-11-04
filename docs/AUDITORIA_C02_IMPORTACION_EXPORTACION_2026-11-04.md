# Auditoría técnica C-02 — importación y exportación

**Fecha:** 2026-11-04
**Host/ruta:** `Implementación-Xray` — `/opt/xray-manager`
**Rama/base:** `design/user-identity-association-v1` — `7e899d898e99d3a279ccff07dc65cb32dc51cc7e`
**Autorización:** aceptación formal de C-01 como componente limitado y autorización expresa para iniciar C-02.
**Estado:** IMPLEMENTADO LOCALMENTE; AUDITORÍA TÉCNICA COMPLETADA; PENDIENTE DE ACEPTACIÓN.

## 1. Alcance

C-02 amplía `scripts/xray_configurations.py` con `preview-import`, `import` y `export`. No integra todavía menús Bash, validación estática Xray, edición/diff, comparación, eliminación, exportación por lotes ni creación de perfiles desde configuraciones independientes.

## 2. Importación

- La ruta de origen debe ser absoluta. Se rechazan componentes symlink, symlink final, hardlink, archivo no regular, archivo superior a 16 MiB y lectura que cambia durante la operación.
- Se abre con `O_NOFOLLOW`; se compara identidad del archivo antes/después y se exige que bytes leídos y tamaño coincidan.
- El origen nunca se modifica.
- Se exige UTF-8 válido. BOM UTF-8 se reconoce para parseo, pero se conservan exactamente los bytes originales cifrados, incluido el BOM.
- `preview-import` devuelve nombre/ruta, tamaño, SHA-256, BOM, sintaxis JSON, tipo raíz, secciones detectadas y diagnóstico sin exponer el contenido ni secretos.
- La importación requiere `--confirm` y el SHA-256 de la vista previa (`--expected-sha256`); el motor vuelve a leer una sola vez y verifica el hash sobre esos mismos bytes que luego cifra, evitando importar un contenido distinto del previsualizado.
- JSON inválido o archivo vacío requiere `--accept-invalid`; se conserva como Borrador, jamás Validado. UTF-8 inválido se rechaza.
- Los nombres duplicados se rechazan y requieren elegir otro; no existe sobrescritura silenciosa ni reemplazo en C-02.
- Cada importación crea un objeto independiente y revisión inicial nueva, AES-256-GCM, AAD por ID/revisión y manifiesto `source=import`.

## 3. Exportación

- Exporta una configuración/revisión elegida a una ruta absoluta.
- Rechaza symlinks en componentes/destino, destinos no regulares y hardlinks.
- El destino existente requiere `--overwrite` explícito y se verifica que no haya cambiado antes de reemplazarlo.
- Escritura mediante temporal privado en el mismo directorio, modo root:root 0600, fsync y publicación atómica. Si no existe destino, usa publicación que falla si aparece un archivo concurrente.
- Relee el archivo exportado y compara byte a byte con el contenido descifrado. Devuelve SHA-256, tamaño y advertencia de que el archivo queda en claro.
- Un comando exporta una configuración/revisión por invocación; el flujo de lotes y la continuación individual tras error quedan para la integración de interfaz posterior.

## 4. Pruebas C-02

`tests/xray_configurations.sh` PASS. Casos añadidos:
- JSON válido con inbounds/outbounds/routing/DNS y secciones adicionales.
- UTF-8 con BOM, preservación byte a byte y origen sin modificación.
- SHA-256 de preview obligatorio; si el origen cambia, se rechaza.
- JSON inválido rechazado sin aceptación y conservado como Borrador con `--accept-invalid`.
- Archivo vacío preservado como revisión de cero bytes Borrador.
- UTF-8 inválido, symlink, hardlink y archivo >16 MiB rechazados.
- Exportación exacta, permisos 0600, no sobrescritura sin flag, overwrite explícito y symlink de destino rechazado.
- Fallo inyectado de escritura parcial durante exportación: destino anterior conservado y temporal privado retirado.

Regresión global posterior a C-02: `tests/*.sh` **52/52 PASS**, exit code 0. Python AST, `bash -n`, ShellCheck focal y `git diff --check` PASS.

## 5. Límites

- La vista previa detecta sintaxis JSON estricta y secciones superiores; no sustituye validación estática Xray de estructura, parámetros, tipos, compatibilidad ni referencias. Todo importado permanece Borrador.
- No se implementa reemplazo de objeto con nombre duplicado; el usuario elige otro nombre. No hay exportación por lotes todavía.
- Las pruebas no cubren todas las carreras posibles del filesystem ni fallos físicos de kernel/dispositivo.
- No se añade operación `apply`/`activate`; no se escribe runtime.

## 6. Límites operativos

Sólo temporales y clave sintética. No se leyó `/etc/xray-manager/keys/master.key`; no se creó almacén live; no se modificó el almacén de perfiles ni los stores VLESS/VMess; no se tocó runtime, systemd, certificados, firewall, puertos, red ni VPS de pruebas. No se instalaron/actualizaron dependencias. `main` y `Xray-Normativa/` permanecen intactas. Sin commit, push ni sincronización.

**Conclusión:** C-02 implementado y probado dentro del alcance descrito; pendiente de revisión y aceptación expresa. Etapa 5 y Etapa 2 continúan ABIERTAS.
