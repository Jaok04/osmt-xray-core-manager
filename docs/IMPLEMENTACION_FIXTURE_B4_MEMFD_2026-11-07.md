# Implementación fixture B4 — memfd sellado y evidencia por invocación

**Fecha:** 2026-11-07
**Estado:** IMPLEMENTACIÓN AISLADA INICIAL — no integrada en runtime
**Entorno:** VPS desarrollo, fixtures temporales
**Live:** NO IMPLEMENTADO / NO AUTORIZADO

## Alcance

Se añadió `scripts/xray_runtime_config_attestation.py` con primitivas aisladas para:
- crear un memfd heredable con `MFD_ALLOW_SEALING`;
- escribir y verificar bytes/hash/tamaño;
- aplicar y comprobar `F_SEAL_WRITE | F_SEAL_GROW | F_SEAL_SHRINK | F_SEAL_SEAL`;
- escribir evidencia JSON atómica 0600 bajo directorio fixture marcado;
- correlacionar PID, InvocationID, hash y tamaño en un verificador fixture.

La API de evidencia exige marcador `.xray-manager-fixture`; no usa `/var/lib/xray-manager`, `/etc/xray`, systemd, Xray real, menú, R-05 ni backend live. No cambia el significado de los campos live actuales.

## Pruebas focales

`tests/test_xray_runtime_config_attestation.py` cubre bytes exactos, seals de kernel, herencia del descriptor a través de exec y lectura desde el hijo, evidencia privada/correlacionada, rechazo de PID/InvocationID/hash/tamaño incorrectos, replay, raíz sin marcador y hash de entrada incorrecto.

## Resultado de pruebas

- Pruebas nuevas B4: **10/10 PASS**.
- Regresión focal proceso-attestation, backend live y adaptador systemd: **56/56 PASS**.
- Total de esta pasada: **66/66 PASS**.
- `py_compile` y `git diff --check`: PASS.

## Limitaciones conocidas

La prueba de compatibilidad documentada en la sección 5 demuestra que Xray 26.10.31 valida el descriptor mediante un enlace simbólico temporal `.json`; no demuestra todavía que el proceso Go preserve/lea el descriptor en las condiciones de la unidad systemd real. Tampoco implementa lanzador de producción, evidencia live, correlación H6-A/procfs, publicación/rollback live, integración con `modules/xray_service.sh`, modificación de unidad o activación. Esas tareas requieren contrato/auditoría adicionales y autorización específica.

El resultado de verificación tiene explícitamente `environment=fixture`; nunca autoriza operaciones live.

## 5. Compatibilidad real con Xray 26.10.31 (2026-11-07)

Se ejecutó una prueba aislada en el VPS de desarrollo usando el binario ya presente en `/usr/local/bin/xray`:

- Versión observada: `Xray 26.10.31`, commit `a4a3dff`, `go1.27.3 linux/amd64`.
- Configuración sintética JSON, sin inbounds y con un outbound `freedom`; no contiene credenciales ni destinos de usuario.
- SHA-256 exacto: `4937721b3c8c9fe50da93e7792c8d78c41c3b606fbc4eb3a5bc930151489be88` (93 bytes).
- Descriptor `memfd` heredable y sellado: `F_SEAL_SEAL | F_SEAL_SHRINK | F_SEAL_GROW | F_SEAL_WRITE` (máscara observada: `15`).
- Ejecución satisfactoria: `xray run -test -config <ruta-temporal>/config.json`; la ruta temporal era un enlace simbólico a `/proc/self/fd/N`, y el descriptor se heredó explícitamente al proceso hijo.
- Resultado: código de salida `0`, mensaje `Configuration OK.`.

Hallazgos de compatibilidad:

1. La ruta directa `/proc/self/fd/N` falla: con formato automático Xray no puede inferir el formato; con `-format=json` el cargador rechaza la extensión `/proc/self/fd/N`.
2. Un enlace simbólico temporal cuyo nombre termina en `.json` y cuyo destino es `/proc/self/fd/N` sí permite que Xray lea y valide los bytes del descriptor sellado.
3. Por tanto, la implementación futura debe conservar el descriptor heredado y usar una ruta JSON temporal controlada que resuelva al descriptor; no debe copiar los bytes a un archivo mutable.

Limitaciones y alcance:

- La prueba se ejecutó como `root`. El VPS de desarrollo no tiene cuenta `xray`; por ello no se pudo verificar aquí el acceso bajo el UID/GID de servicio.
- No se probó el sandbox de systemd, la unidad real ni el arranque normal de Xray.
- No se cambió la unidad systemd, no se creó `/etc/xray`, no se inició/reinició ningún servicio y no se abrió ningún puerto.
- La prueba acredita que este binario puede validar la configuración desde un `memfd` sellado mediante el enlace simbólico `.json`; no acredita todavía la integración de producción ni la correlación de evidencia posterior al `exec`.
- La compatibilidad observada no autoriza habilitar backend live, conectar el mecanismo a R-05, ni desplegar en el VPS de pruebas.

## 6. Prueba con UID no privilegiado e inspección del VPS de pruebas (2026-11-07)

### UID no privilegiado en desarrollo

Se repitió la validación de la sección 5 ejecutando Xray como `nobody` (UID/GID 65534), sin crear cuentas ni modificar el sistema:

- Se heredó el mismo tipo de descriptor `memfd` sellado (máscara de seals `15`).
- Se mantuvo el enlace simbólico temporal `config.json` → `/proc/self/fd/N`.
- Xray 26.10.31 terminó con código `0` y `Configuration OK.`.

Esto demuestra que el acceso al descriptor heredado y la lectura a través de la ruta temporal funcionan bajo un UID no privilegiado. No equivale a verificar el usuario/grupo `xray` real ni sus políticas de servicio.

### Inspección de solo lectura del VPS de pruebas

En el VPS de pruebas se comprobó, sin modificarlo:

- El binario `/usr/local/bin/xray` existe y reporta Xray 26.10.31 (`a4a3dff`, Go 1.27.3).
- No existe cuenta ni grupo `xray` (`getent passwd/group xray` sin resultado).
- `xray.service` está `LoadState=not-found`, `ActiveState=inactive`; no hay unidad en `/etc/systemd/system` ni `/lib/systemd/system`.
- Por ausencia de unidad y de identidad de servicio, no hay configuración efectiva de sandbox systemd que inspeccionar o probar en ese host.

No se creó el usuario/grupo, no se instaló ni configuró una unidad, no se modificó systemd, no se inició Xray y no se tocó `/etc/xray`.

### Conclusión

La compatibilidad de lectura del `memfd` sellado queda probada como root y como UID no privilegiado (`nobody`). La validación bajo la identidad final `xray` y dentro del sandbox systemd requiere primero una unidad/identidad real; crearlas sería una modificación del VPS de pruebas y queda fuera de esta fase sin autorización explícita de despliegue.


## 7. Restricción permanente de configuración mediante el Administrador

Por decisión expresa del propietario (2026-11-07), la identidad `xray`, el grupo, los directorios, la unidad systemd y sus restricciones no se crearán manualmente para completar las pruebas. La capacidad debe ejecutarse desde Xray-Core Manager mediante `modules/xray_service.sh` y su acción de menú de preparación, con preflight, confirmación, locks, validación, postcondiciones y auditoría. Si el lanzador B4 requiere cambios de unidad, estos se integrarán en el contenido administrado de la unidad y se desplegarán exclusivamente mediante el Administrador. Las pruebas automatizadas pueden utilizar fixtures/entornos aislados; no se debe preparar manualmente un host real. La autorización de implementación/documentación/publicación no autoriza la operación live; esta conserva autorización específica por host y alcance.
