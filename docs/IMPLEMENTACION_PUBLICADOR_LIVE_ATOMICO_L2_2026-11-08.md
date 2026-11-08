# Publicador live atómico mínimo — L2 (2026-11-08)

**Estado:** IMPLEMENTADO Y VALIDADO EN AISLAMIENTO; no ejecutado contra runtime productivo.
**Rama:** `design/user-identity-association-v1`
**Objetivo:** publicar una configuración TLS staged y validada en `/etc/xray/config.json`, conservando recuperación transaccional, sin iniciar, reiniciar, detener ni habilitar Xray.

## Implementación

Se añadieron:

- `scripts/xray_runtime_live_publisher.py`: publicador live separado de R-04 fixture.
- `tests/test_xray_runtime_live_publisher.py`: nueve pruebas aisladas de publicación, CAS, rollback y fallos.

El publicador consume exclusivamente un directorio hijo directo de `/run/xray-manager-runtime-staging`, verifica manifiesto/configuración y hashes, valida identidad real `xray:xray`, comprueba que el binario Xray no cambió y observa systemd mediante el adaptador read-only.

El alcance inicial se restringe deliberadamente a `xray.service` cargado, administrado e **inactivo**. La unidad debe estar en subestado `dead`, sin PID ni InvocationID residual, sin drop-ins y sin daemon-reload pendiente. Si la observación cambió desde el staging, se rechaza la publicación.

## Transacción

1. Adquiere los locks globales en el orden establecido: `lifecycle.lock` y después `integrity.lock`; la adquisición es no bloqueante.
2. Rechaza cualquier operación live previa no terminal.
3. Captura los bytes exactos de `/etc/xray/config.json` (si existe) en el snapshot root-only del journal live.
4. Persiste los estados `prepared → validated → snapshot_saved → publication_requested`.
5. Escribe un temporal en el mismo filesystem/directorio que el destino, con propietario `root:xray` y modo `0640`.
6. Ejecuta `xray run -test` como el usuario/grupo reales del servicio.
7. Reobserva systemd y compara el destino con el snapshot inmediatamente antes de publicar (CAS conservador).
8. Ejecuta `os.replace`, sincroniza el directorio y vuelve a leer/verificar hash, propietario, grupo y permisos.
9. Persiste `config_published` y devuelve `service_action_performed=false`, `service_started=false` y `configuration_loaded=false`.

## Recuperación y límites de seguridad

- Si había configuración previa y una fase posterior al rename falla, sólo restaura si el destino todavía coincide con el candidato de esta operación o con el snapshot previo. Después valida la configuración restaurada bajo `xray:xray` y registra `rolled_back`.
- Si no existía configuración previa, **no elimina** la primera configuración publicada ante un fallo. Conserva el archivo y marca `recovery_required`.
- Si un tercero modifica el destino y éste no coincide con el candidato ni con el snapshot, el rollback CAS se niega a sobrescribirlo y exige intervención.
- Los locks serializan operaciones del Manager; no pueden impedir una modificación manual concurrente de root. El CAS reduce esa ventana, pero no pretende ser un compare-and-swap del kernel frente a administradores externos.
- No hay acción systemd, no se llama a `xray_service_action_locked`, no se integra con R-05 ni con el menú.
- No se limpia el staging ni los leases después de publicar: los paths de certificados que contiene la configuración deben seguir disponibles para el futuro arranque.
- No se ejecutó el publicador en host alguno, ni se modificó `/etc/xray`, systemd, certificados, DNS, firewall o puertos.

## Validación

- Publicador live: **9/9 PASS**.
- Regresión focal combinada (publicador, staging live, journal live, R-02, núcleo TLS y preflight): **75/75 PASS**.
- Suite Python global: **515/515 PASS**.
- Suites Bash: **62/62 PASS**.
- `compileall`, `bash -n` global, ShellCheck global `-S error`, `install.sh --check` y `git diff --check`: PASS.

## Pendiente

La publicación de archivo no demuestra que Xray haya cargado esa configuración. Para el primer servidor aún faltan la integración controlada de publicación con el Administrador, el flujo de start a través del único controlador `modules/xray_service.sh`, la observación posterior correlacionada con InvocationID/PID, evidencia de configuración cargada y prueba de conectividad externa. La revisión independiente H6-G3 y autorización live siguen siendo puertas previas; este módulo permanece aislado y no se debe invocar en producción todavía.
