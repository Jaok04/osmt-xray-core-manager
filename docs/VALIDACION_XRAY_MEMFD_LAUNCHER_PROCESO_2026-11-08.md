# Validación Xray real: memfd sellado, ruta JSON y proceso persistente

**Fecha:** 2026-11-08  
**Estado:** COMPATIBILIDAD TÉCNICA CONFIRMADA EN PROCESO AISLADO; sin integración Manager/systemd/live.  
**Host:** VPS de desarrollo `Implementación-Xray`.  
**Binario:** `/usr/local/bin/xray`, Xray 26.10.31, commit `a4a3dff`, Go 1.27.3, linux/amd64.

## Objetivo

Completar la prueba anterior de `docs/IMPLEMENTACION_FIXTURE_B4_MEMFD_2026-11-07.md`: verificar no sólo `run -test`, sino también el arranque normal de Xray leyendo un descriptor memfd sellado, conservándolo en el proceso, y hacerlo con un UID/GID no privilegiado y descriptor propiedad de esa identidad.

## Hallazgos reproducidos

1. La ruta `/proc/self/fd/N` directa no funciona con Xray 26.10.31: la detección automática no reconoce el formato; `-format=json` tampoco evita que el cargador rechace la extensión.
2. Una ruta JSON temporal cuyo enlace simbólico apunta a `/proc/self/fd/N` sí funciona. Xray determina el formato por la extensión `.json` del argumento y abre el descriptor del propio proceso.
3. `xray run -test -config <ruta-json>` terminó con código 0 y `Configuration OK.` cuando el memfd fue creado por `nobody:nogroup`, modo `0400`, sellado con `F_SEAL_WRITE | F_SEAL_GROW | F_SEAL_SHRINK | F_SEAL_SEAL` (máscara 15). El enlace era propiedad de root y apuntaba a `/proc/self/fd/3`.
4. `xray run -config <ruta-json>` arrancó como proceso persistente bajo `nobody:nogroup`. Después de `exec`, el PID seguía activo y `/proc/<PID>/fd/3` apuntaba a `memfd:xray-manager-config.json (deleted)`.
5. La inspección externa del descriptor del proceso confirmó propietario UID/GID 65534:65534, modo `0400`, tamaño 96 bytes, SHA-256 idéntico al contenido esperado y seals completos (máscara 15). El proceso emitió `Reading config` para la ruta `.json` y `Xray ... started`.
6. La prueba de proceso terminó enviando SIGTERM al proceso aislado. No se usó systemd, no se abrieron listeners ni se modificó configuración del host.

La configuración sintética fue mínima, sin inbounds ni credenciales, y con un outbound `freedom`. No es una prueba de tráfico ni de conectividad externa.

## Diseño mínimo recomendado para evaluar en fixtures

La compatibilidad observada permite conservar el contrato directo `User=xray`, `Group=xray` sin incorporar el supervisor root B4.3 al daemon:

- Un launcher pequeño, ejecutado como `xray:xray`, abre el archivo runtime publicado de sólo lectura, calcula/verifica SHA-256 y tamaño, crea el memfd heredable, escribe los bytes exactos, aplica modo `0400` y los cuatro seals, y revalida contenido/metadatos.
- El launcher fija el descriptor en FD 3 (`dup2`/heredabilidad) y ejecuta Xray mediante `exec`, preservando PID y descriptor.
- El argumento de configuración de Xray usa una ruta `.json` root-owned e inmutable cuyo destino es `/proc/self/fd/3`. La ruta debe ser preparada por el Administrador en una ubicación persistente de sólo lectura para el servicio; no debe residir en un directorio que `xray` pueda reemplazar.
- El launcher debe validar los mismos bytes del memfd con `xray run -test` antes del `exec` normal, usando el mismo FD 3 y reposicionándolo a offset cero después del test. Así, la prueba y el proceso final reciben la misma generación inmutable, en lugar de validar un archivo y volver a abrirlo más tarde.
- Tras el arranque, un verificador root-only correlaciona `MainPID`, `InvocationID`, argv, ejecutable/hash, UID/GID, descriptor FD 3, propietario/modo, seals, tamaño y SHA-256 leído desde `/proc/<PID>/fd/3`. El PID debe ser el mismo launcher reemplazado por `exec`.
- La evidencia debe usar un nivel explícito como `sealed_memfd_process_bound`; no describirla como una prueba criptográfica del estado interno del parser. La combinación de validación previa sobre el mismo descriptor, argv de Xray, log de lectura, proceso activo y descriptor sellado inspeccionado desde root constituye evidencia operativa fuerte y reproducible.

Este diseño evita un supervisor root persistente y mantiene la identidad final del proceso como `xray:xray`. No es todavía una decisión de implementación ni una autorización para modificar la unidad.

## Brechas y controles antes de implementar

- El host de desarrollo no tiene cuenta/grupo `xray` ni unidad `xray.service`; la identidad de prueba fue `nobody:nogroup`. No se debe crear manualmente `xray` para cerrar esta brecha.
- No se ha probado el launcher dentro del sandbox systemd administrado por `modules/xray_service.sh`, ni `ProtectSystem=strict`, `ProtectProc`, `ProcSubset`, `PrivateTmp`, `NoNewPrivileges`, `CapabilityBoundingSet`, `ReadOnlyPaths` o las restricciones reales de procfs.
- El enlace `.json` debe ser root-owned, no reemplazable por `xray`, visible dentro del sandbox y estable entre reinicios. Su ubicación y creación deben formar parte de la preparación administrada por Xray-Core Manager.
- El launcher no debe aceptar rutas/FD arbitrarios, variables de entorno como prueba, configuración mutable ni fallback al archivo original. Debe fijar FD 3, comprobar que no hay colisión/FD residual, cerrar otros descriptores no requeridos y fallar cerrado.
- El observador root debe verificar el descriptor vivo directamente; no confiar en JSON de evidencia escrito por el usuario `xray`.
- Deben añadirse pruebas negativas: descriptor ausente/no sellado, hash/size incorrectos, enlace reemplazable, FD distinto, symlink equivocado, config inválida, timeout, proceso que no conserva FD, systemd con restricciones que ocultan `/proc/self/fd`, y cambios de archivo durante staging.
- El parser de Xray no expone una atestación criptográfica nativa del objeto de configuración interno. El nivel de evidencia propuesto es operacional, no una prueba formal contra un binario Xray comprometido.

## Límites y exclusiones

- Sólo se ejecutaron pruebas aisladas temporales en la VPS de desarrollo.
- No se llamó a systemd ni al controlador `modules/xray_service.sh`.
- No se modificaron unidad, `ExecStart`, `ExecStartPre`, `/etc/xray`, `/run`, `/var/lib/xray-manager`, cuentas/grupos, certificados, DNS, firewall, puertos ni red.
- No se consultó ni modificó la VPS Pruebas.
- No se integró con `xray_runtime_live_start_attestation.py`, coordinator, backend live, R-05, CLI o menú.
- No se declaró `configuration_loaded=true`, `configuration_attested` ni `completed` en el journal.
- `main` y `Xray-Normativa/` permanecen protegidos.

## Conclusión

**GO para construir un prototipo de launcher fixture y su verificador de descriptor vivo; NO-GO para integrar, cambiar systemd o habilitar operaciones live.** La principal incertidumbre de compatibilidad del binario Xray queda resuelta: la versión instalada puede iniciar normalmente desde un memfd sellado heredado a través de una ruta `.json` root-owned hacia `/proc/self/fd/3`, y el proceso mantiene el descriptor inspeccionable después de `exec`. La siguiente fase debe implementar y atacar el launcher exclusivamente en fixtures, y validar después el sandbox mediante pruebas automatizadas aisladas. La unidad real y la VPS Pruebas siguen fuera de alcance hasta auditoría independiente H6-G3 y autorización live específica.
