# Launcher fixture con memfd sellado — B4-MIN (2026-11-08)

**Estado:** IMPLEMENTADO Y VALIDADO EN FIXTURES; sin integración live/systemd.  
**Host:** VPS de desarrollo `Implementación-Xray`.  
**Binario de prueba:** Xray 26.10.31 (`a4a3dff`, Go 1.27.3).  
**Identidad de prueba:** `nobody:nogroup` (UID/GID 65534); no se creó `xray:xray`.

## Objetivo

Construir el prototipo mínimo propuesto en `docs/VALIDACION_XRAY_MEMFD_LAUNCHER_PROCESO_2026-11-08.md`: validar la configuración mediante Xray y ejecutar el daemon final usando exactamente el mismo descriptor memfd sellado, conservando FD 3 a través de `exec`. El proceso final debe ser Xray (mismo PID), no un supervisor root.

## Implementación

Se añadió `scripts/xray_runtime_memfd_exec_launcher.py`.

### `launch_fixture(...)`

- Exige una raíz fixture absoluta, root-owned, modo `0711`, sin symlinks en sus ancestros y con marcador regular root:root `0600`.
- Exige que la configuración fuente esté dentro de la raíz fixture, sea regular, root:root, no tenga hardlinks y no sea modificable por grupo/otros. Abre con `O_NOFOLLOW`, compara inode/metadatos antes y después, lee el tamaño exacto y comprueba SHA-256.
- Exige un enlace `.json` root-owned cuyo directorio y ancestros estén protegidos contra sustitución; el destino literal debe ser `/proc/self/fd/3`.
- Exige un binario Xray regular, root-owned, ejecutable y no modificable por grupo/otros.
- Rechaza ejecución efectiva como root. El launcher crea un memfd como la identidad efectiva, fija modo `0400`, propietario/grupo de esa identidad y los cuatro seals `F_SEAL_WRITE | F_SEAL_GROW | F_SEAL_SHRINK | F_SEAL_SEAL`.
- Fija el descriptor en FD 3, verifica contenido/hash/tamaño/owner/mode/seals y ejecuta `xray run -test -config <symlink.json>` con FD 3 heredado.
- Si Xray no devuelve código 0 y `Configuration OK`, falla cerrado. Reposiciona el mismo FD 3 a offset cero, revalida bytes/seals y hace `execv()` de `xray run -config <symlink.json>` conservando FD 3. No crea evidencia persistente ni invoca systemd.

### `verify_live_descriptor(...)`

Inspector separado para ejecutar como root después del arranque fixture. Comprueba raíz fixture y symlink, PID/starttime antes y después, UID/GID efectivos, ejecutable, argv exacto, FD 3 vivo, nombre memfd, propietario, modo `0400`, tamaño, cuatro seals y SHA-256 leído desde `/proc/PID/fd/3`.

La salida declara `environment=fixture`, `descriptor_process_bound=true`, `configuration_evidence=sealed_memfd_process_bound` y mantiene deliberadamente `configuration_loaded=false`. El descriptor vivo demuestra que el proceso Xray conserva el inode sellado con los bytes esperados; no es una atestación criptográfica del estado interno del parser.

### CLI

El script incluye CLI de laboratorio que recibe únicamente rutas y hash/tamaño explícitos. No hay modo live, opción de servicio, integración con el backend, R-05 o menú. La ejecución correcta reemplaza el launcher por Xray mediante `exec`.

## Pruebas añadidas

`tests/test_xray_runtime_memfd_exec_launcher.py`: **13 pruebas**.

- Arranque real de Xray 26.10.31 como `nobody:nogroup`, validación previa y `exec` conservando el mismo PID y FD 3.
- Inspección root-only del descriptor vivo y coincidencia de hash/tamaño/seals/owner/mode.
- Rechazo de hash y tamaño esperados incorrectos.
- Rechazo de symlink a FD distinto, symlink fuera del fixture y ancestros symlink.
- Rechazo de directorio del enlace modificable por grupo/otros.
- Rechazo de configuración JSON inválida durante `xray run -test`.
- Rechazo de identidad esperada incorrecta, hash incorrecto y PID inexistente en el verificador.
- Rechazo de ejecución root.

La prueba de arranque no abre puertos ni usa inbounds; la configuración es sintética, sin credenciales ni destinos de usuario. El proceso se termina al final de la prueba. No se prueba tráfico ni conectividad externa.

## Validación

- Nueva suite launcher: **13/13 PASS**.
- Suite Python completa: **542/542 PASS**.
- Suites Bash: **62/62 PASS**.
- `bash -n` global: PASS.
- `python3 -m compileall -q scripts tests`: PASS.
- `bash install.sh --check`: PASS; confirma dependencias y no modifica el sistema.
- `git diff --check`: PASS.

No se modificó ningún archivo Bash; la comprobación ShellCheck global se intentó en esta sesión pero excedió el límite de ejecución, por lo que no se declara como una validación nueva de esta etapa.

## Limitaciones y exclusiones

- Todo el launcher y verificador son fixture-only; el marcador fixture es obligatorio.
- No se probó bajo systemd, `ProtectSystem=strict`, `ProtectProc`, `ProcSubset`, `PrivateTmp`, `NoNewPrivileges`, `CapabilityBoundingSet`, `ReadOnlyPaths` ni la unidad administrada real.
- No existe todavía la identidad `xray:xray` en la VPS de desarrollo; no se creó manualmente.
- No se creó ni modificó unidad, `ExecStart`, `ExecStartPre`, `modules/xray_service.sh`, `/etc/xray`, `/run`, `/var/lib/xray-manager`, cuentas/grupos, certificados, DNS, firewall, puertos o red.
- No se integró con journal, publicador, start coordinator, backend live, R-05, CLI o menú.
- No se ejecutó ninguna operación en VPS Pruebas.
- `configuration_loaded` permanece `false`; no se avanza el journal a `configuration_attested` ni `completed`.
- `main` y `Xray-Normativa/` permanecen protegidos.

## Dictamen y siguiente paso

**GO para diseño/fixtures de sandbox; NO-GO para integración live.** El prototipo demuestra que Xray puede validar y arrancar desde el mismo memfd sellado, con el mismo PID y FD 3 inspeccionable por root. El siguiente bloqueo es verificar si la ruta del symlink y `/proc/self/fd/3` son accesibles y conservan el contrato dentro de las restricciones systemd que administra el Manager, sin crear cuentas ni unidades manualmente. Esa comprobación debe hacerse en un entorno aislado con fixtures; después requiere revisión independiente H6-G3 antes de cualquier integración o despliegue.
