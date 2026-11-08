# B4.3-B — diseño de integración fixture del almacén persistente con el supervisor

**Fecha:** 2026-11-08
**Estado:** DISEÑO TÉCNICO IMPLEMENTADO EN FIXTURES; revisión adversarial independiente pendiente.
**Base:** `1da1b77470179a2b082a0f196db56030d9f72afa`.
**Rama prevista:** `design/user-identity-association-v1`.

## 1. Objetivo y límites

Definir cómo el supervisor fixture B4.1/B4.2 debe escribir la evidencia persistente B4.3-A antes de permitir que el hijo ejecute Xray. La integración debe conservar el gate de ejecución, el memfd sellado y propiedad de servicio, el descenso de privilegios y la separación de acceso a evidencia.

Este diseño no integra el backend live, R-05, menú ni `modules/xray_service.sh`; no genera ni instala unidades systemd; no crea cuentas; no usa rutas reales; no ejecuta daemon ni cambia la VPS Pruebas. La implementación siguiente será exclusivamente fixture en `/opt/xray-manager`.

## 2. Estado base y problema concreto

- `xray_runtime_launcher_prototype.run_fixture_xray_validation()` crea el hijo detenido por un pipe gate, obtiene el PID y, antes de liberarlo, llama a `attestation.write_invocation_evidence()`.
- Esa primitiva B4.1 escribe bajo `fixture_root/evidence` y tiene un contrato plano.
- `xray_runtime_evidence_store.create_evidence()` escribe bajo `fixture_root/var/lib/xray-manager/evidence`, valida el layout B4.3, publica sin sobrescritura y conserva registros `root:root 0600`.
- No existe hoy una ruta que conecte el PID real del hijo bloqueado con el almacén persistente B4.3. No se debe cambiar silenciosamente el contrato B4.1 ni afirmar que B4.3-A ya está integrado.

## 3. Contrato de integración propuesto

Añadir un adaptador independiente fixture, por ejemplo `scripts/xray_runtime_supervisor_evidence.py`, con operaciones explícitas:

1. Recibir un plan fixture ya validado, `target_pid`, `invocation_id`, `service_gid` y un descriptor de directorio raíz (`fixture_root_fd`) abierto por el llamador confiable.
2. Validar que el plan pertenece a `environment=fixture`, que PID > 1 coincide con el hijo bloqueado, que GID coincide con la identidad del plan y que el SHA-256/tamaño proceden de los bytes ya verificados del memfd.
3. Validar el descriptor de raíz con `fstat` (directorio, owner esperado y permisos seguros) y validar el marcador fixture mediante `openat` + `O_NOFOLLOW`, `fstat` y contenido exacto `fixture-only\n`.
4. Resolver `var/lib/xray-manager/evidence` desde el descriptor de raíz, componente a componente con `openat` (`O_DIRECTORY|O_NOFOLLOW`), verificando cada inode y sus owner/group/mode. No reabrir una ruta absoluta después de anclar el descriptor.
5. Crear evidencia mediante el almacén B4.3-A, con el conjunto mínimo `{pid, config_sha256, config_size_bytes}` y la `InvocationID` canónica. El registro debe conservar `evidence_status=prepared_before_exec`.
6. Reabrir y verificar el registro desde el mismo ancla antes de devolver éxito al supervisor.
7. Devolver al supervisor el resultado verificado y la referencia fixture al registro; no devolver bytes de configuración ni secretos.

La extensión del almacén para aceptar un descriptor de raíz debe ser una API explícita y separada de la interfaz por ruta existente. La interfaz actual `create_evidence(fixture_root=...)` seguirá funcionando para los tests existentes; no se degradará su validación ni se añadirá fallback implícito.

## 4. Secuencia dentro del supervisor

La ruta nueva debe ser opt-in explícita (por ejemplo `evidence_backend="persistent_b43"`) y nunca seleccionarse por detección heurística:

1. Validar plan, identidad, ejecutables y memfd como hoy.
2. Crear hijo y mantenerlo bloqueado en el pipe gate.
3. Registrar `target_pid`.
4. Crear y verificar evidencia B4.3-A mediante el adaptador y el descriptor de raíz anclado.
5. Sólo si todos los pasos anteriores pasan, escribir el token del gate y permitir `exec`.
6. Si falla la apertura de raíz, validación de layout, escritura, fsync, publicación o verificación, cerrar el gate, terminar/recolectar el hijo y retornar error. Xray no debe llegar a `exec`.
7. Cerrar los descriptores del supervisor según ownership definido; el descriptor memfd heredable conserva únicamente el ciclo de vida requerido por el hijo.

El backend B4.1 plano seguirá disponible temporalmente para pruebas de regresión existentes, pero no se usará como fallback cuando se solicite el backend persistente. Si el backend persistente falla, el resultado será fallo cerrado.

## 5. Semántica y límites de evidencia

El registro significa únicamente **evidencia preparada antes de exec para un PID e InvocationID**. No demuestra que `exec` tuvo éxito, que Xray esté activo, que systemd lo supervise ni que el proceso haya cargado la configuración. No actualizar el estado a `active` o `running` desde el prototipo.

La confirmación posterior de proceso activo, `MainPID`, `InvocationID` real y estado systemd pertenece a H6 y requiere evidencia independiente del adaptador systemd. No reutilizar la evidencia `prepared_before_exec` como prueba de runtime activo.

La repetición de InvocationID debe fallar sin sobrescribir. No almacenar URI, UUID, bytes/configuración, claves, PEM, tokens, variables de entorno ni argumentos sensibles. El hash y tamaño son metadatos operativos sensibles y no deben imprimirse en logs de prueba.

## 6. Pruebas de aceptación fixture

La implementación B4.3-B debe añadir pruebas focales para:

- flujo correcto: el PID bloqueado se registra y la evidencia persistente se verifica antes de liberar el gate;
- fallo inyectado al crear evidencia: el hijo no ejecuta el binario y es recolectado;
- fallo inyectado en `fsync`, publicación y relectura/verificación: no hay `exec` ni evidencia parcial temporal;
- descriptor raíz no-directorio, cerrado, inválido o ancla con marcador incorrecto: rechazo;
- renombrado/reemplazo de la ruta nominal después de abrir el descriptor: las operaciones siguen limitadas al inode anclado y no siguen el reemplazo;
- symlink en cada componente y drift owner/group/mode: rechazo sin reparación;
- InvocationID repetida o no canónica: rechazo sin sobrescritura;
- proceso de servicio: puede escribir en state/runtime fixture y no puede atravesar el padre root-only ni leer/escribir evidencia;
- registro persistido tras cierre/reapertura del descriptor: verificación correcta;
- contenido del registro: sólo PID, SHA-256, tamaño, schema, estado e InvocationID.

Además, mantener las suites B4.1/B4.2/B4.3-A existentes y ejecutar regresión Python global, `compileall`, `bash -n`, ShellCheck global, `install.sh --check` y `git diff --check`.

## 7. Riesgos que deben resolverse antes de integrar

- **Ancla confiable:** el supervisor no debe convertir una ruta absoluta mutable en confianza. El descriptor debe proceder de una raíz que el Manager haya validado y abierto; el adaptador verifica el inode y el marcador desde ese descriptor.
- **TOCTOU:** toda apertura interna se realiza relativa a un descriptor de padre ya validado, con `O_NOFOLLOW`, `O_DIRECTORY` y `fstat`. No basta con `lstat()` seguido de `open()` por ruta.
- **Ciclo de vida de FD:** definir claramente quién abre/cierra el root FD y garantizar que no se herede al proceso Xray. El memfd de configuración sí debe conservar su herencia controlada.
- **Fallo antes de exec:** el gate es una barrera obligatoria; ninguna ruta de error puede liberar el token.
- **Estado probatorio:** `prepared_before_exec` no equivale a proceso activo. La correlación systemd real queda fuera de B4.3-B.
- **Compatibilidad:** preservar el comportamiento B4.1 actual mientras el nuevo backend fixture se introduce explícitamente y con pruebas de regresión.

## 8. No objetivos y puerta de autorización

No se permite en B4.3-B:

- modificar `modules/xray_service.sh`, unidades systemd, R-05, menú o backend live;
- crear `xray:xray`, cambiar ownership/modos del host o tocar `/var/lib/xray*` real;
- ejecutar `systemctl`, iniciar/reiniciar Xray, usar `INVOCATION_ID` real o ejecutar daemon;
- modificar certificados, DNS, firewall, puertos, red o VPS Pruebas;
- modificar `Xray-Normativa/` o `main`.

La eventual integración productiva y cualquier operación live requerirán diseño, auditoría integral y autorización específica posterior.

## 9. Implementación y siguiente paso

La implementación fixture del contrato se completó en `docs/IMPLEMENTACION_B4_3B_SUPERVISOR_EVIDENCIA_FIXTURE_2026-11-08.md`; la segunda pasada adversarial de la misma sesión está en `docs/AUDITORIA_B4_3B_ADAPTADOR_EVIDENCIA_FIXTURE_2026-11-08.md` y no equivale a auditoría independiente. Las pruebas focales y regresiones globales están registradas en el informe de implementación.

Siguiente paso: revisión independiente de B4.3-B y corrección de hallazgos, si los hubiera. No conectar R-05 ni el controlador systemd en esta fase.
