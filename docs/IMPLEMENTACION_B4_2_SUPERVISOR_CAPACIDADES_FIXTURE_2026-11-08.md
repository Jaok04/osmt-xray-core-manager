# B4.2 — contrato fixture de supervisor limitado y descriptor privado

**Fecha:** 2026-11-08
**Estado:** IMPLEMENTADO Y VERIFICADO EN FIXTURES; integración systemd/live NO AUTORIZADA.
**Autorización:** el propietario autorizó formalizar e implementar B4.2 exclusivamente en desarrollo y fixtures, sin operaciones live.

## 1. Objetivo y alcance

Resolver el conflicto identificado tras B4.1: el lanzador necesita autoridad temporal para preparar el descriptor sellado y escribir evidencia privada, pero Xray debe ejecutarse como identidad de servicio no privilegiada. B4.2 prueba un supervisor root con capacidades reducidas y transfiere el memfd a la identidad de servicio antes del descenso.

El alcance se limita al prototipo fixture `scripts/xray_runtime_launcher_prototype.py` y sus pruebas. No integra R-05, no modifica `modules/xray_service.sh`, no instala ni genera una unidad systemd real, no crea cuentas/grupos en el host y no ejecuta un daemon.

## 2. Contrato de privilegios propuesto

El supervisor requiere únicamente estas capacidades durante la preparación:

- `CAP_CHOWN`: transferir la propiedad del memfd a la identidad de servicio.
- `CAP_SETUID` y `CAP_SETGID`: ejecutar el descenso de identidad y limpiar grupos suplementarios.
- `CAP_NET_BIND_SERVICE`: capacidad que puede conservar Xray para escuchar en puertos privilegiados.

La máscara efectiva fixture comprobada es `0x4c1` (`CHOWN | SETGID | SETUID | NET_BIND_SERVICE`). El supervisor de prueba se ejecutó con `NoNewPrivileges=1`.

Secuencia de preparación del memfd:

1. Crear el memfd heredable con `MFD_ALLOW_SEALING` y escribir los bytes verificados.
2. Aplicar `fchmod(0400)` mientras el descriptor todavía pertenece al supervisor.
3. Aplicar `fchown(service_uid, service_gid)` con `CAP_CHOWN`.
4. Aplicar y verificar `F_SEAL_WRITE | F_SEAL_GROW | F_SEAL_SHRINK | F_SEAL_SEAL`.
5. Revalidar propietario, grupo, modo, tamaño, seals, heredabilidad y SHA-256 antes del fork/exec.
6. El hijo pasa por `setpriv`, elimina privilegios que no necesita, activa `NoNewPrivileges` y ejecuta Xray conservando el PID.

El orden `fchmod` antes de `fchown` es deliberado: evita requerir `CAP_FOWNER` después de transferir la propiedad. La prueba con el conjunto limitado falló al invertir ese orden y pasó al corregirlo.

## 3. Evidencia y acceso

El descriptor contiene los bytes exactos, es propiedad de la identidad de servicio y tiene modo `0400`. La evidencia de invocación permanece separada, bajo directorio root-only y archivo `0600`; el proceso de servicio no puede escribirla. La verificación B4.1 de PID/InvocationID/hash/tamaño se conserva.

El cambio de propietario y modo es una modificación de metadatos del inode memfd; los seals protegen el contenido y el tamaño. Las pruebas confirman que el descriptor sigue siendo legible por Xray después del descenso de privilegios.

## 4. Relación con systemd — propuesta, no unidad aprobada

La hipótesis de unidad para un futuro ensayo controlado es iniciar el supervisor como root, con `CapabilityBoundingSet` y `AmbientCapabilities` limitadas a las cuatro capacidades anteriores, conservar `NoNewPrivileges=true` y las restricciones de aislamiento ya existentes, y ejecutar Xray como `xray:xray` mediante `setpriv`.

`RestrictSUIDSGID=true` no sustituye ni bloquea por sí mismo las llamadas `setuid`/`setgid`; restringe la creación de objetos con bits SUID/SGID. `NoNewPrivileges=true` impide adquirir privilegios nuevos mediante exec, pero no impide que un proceso que ya tiene `CAP_SETUID`/`CAP_SETGID` cambie a una identidad menos privilegiada.

**Bloqueo pendiente de integración:** con `User=root`, las directivas `StateDirectory=xray` y `RuntimeDirectory=xray` pasan a preparar directorios bajo la identidad root, mientras que Xray final se ejecutaría como `xray`. Además, `ProtectSystem=strict` impide escribir evidencia en una ruta persistente salvo que la unidad la permita explícitamente. Antes de tocar la unidad se debe definir, mediante Manager, la propiedad/permisos de los directorios de estado/runtime y una ruta de evidencia root-only permitida por el sandbox (por ejemplo, un directorio de runtime root-owned y modo `0700`, con ciclo de vida y retención definidos). No se debe relajar el sandbox a ciegas ni asumir que las directivas actuales siguen teniendo la misma semántica al cambiar `User=`.

También falta probar el descriptor y el enlace `/proc/self/fd/N` dentro del sandbox systemd real, incluyendo `PrivateTmp`, `ProtectSystem=strict`, `ProtectHome`, `PrivateDevices`, `RestrictAddressFamilies`, capacidades y el comportamiento real de `INVOCATION_ID`.

## 5. Pruebas añadidas y resultados focales

La suite B4.1/B4.2 ahora contiene 20 pruebas, entre ellas:

- memfd con propietario/grupo de servicio y modo `0400`;
- rechazo de manipulación posterior de propietario o modo;
- supervisor fixture con sólo `CAP_CHOWN`, `CAP_SETUID`, `CAP_SETGID`, `CAP_NET_BIND_SERVICE` y `NoNewPrivileges=1`;
- Xray 26.10.31 `run -test` después del descenso de privilegios;
- evidencia privada no escribible por la identidad de servicio;
- validaciones B4.1 de UID/GID, descriptor, ejecutables y timeout.

La identidad utilizada es `nobody:nogroup`, existente en el entorno de desarrollo. No se creó `xray:xray`; por tanto, esto demuestra el contrato UID/GID genérico, no la cuenta de producto ni la unidad systemd final.

## 6. Limitaciones y criterios para avanzar

- El supervisor se simuló mediante `setpriv` en un proceso fixture; no fue iniciado por systemd.
- No se validó una unidad con `systemd-analyze verify` como sustituto de una prueba real del sandbox; una validación sintáctica tampoco probaría la ejecución bajo namespaces/capacidades.
- No se inició `xray run` como daemon; sólo `run -test`.
- No se probó `xray:xray`, InvocationID real, MainPID real ni correlación post-start.
- El riesgo TOCTOU de ejecutables documentado en B4.1 permanece.
- La ruta persistente/root-only de evidencia y el ownership de StateDirectory/RuntimeDirectory requieren diseño e implementación desde Manager antes de integrar.

Siguiente paso permitido: diseñar fixture de layout de directorios/sandbox y contrato de unidad, incluidos `ReadWritePaths` y evidencia, sin instalar ni iniciar systemd. Cualquier prueba live, creación de cuenta, cambio de unidad, integración R-05/controlador, VPS de pruebas o despliegue requiere autorización específica adicional.

## 7. Estado

B4.2 está implementado y verificado en fixtures. No es integración de producción, no habilita backend live y no demuestra todavía que el servicio real pueda arrancar. No se modificó `Xray-Normativa/`, `modules/xray_service.sh`, systemd, runtime, VPS de pruebas, DNS, firewall, puertos o red. No se realizó commit ni push.
