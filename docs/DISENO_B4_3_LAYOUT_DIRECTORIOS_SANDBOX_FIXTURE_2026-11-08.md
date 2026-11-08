# B4.3 — contrato fixture de directorios y sandbox systemd

**Fecha:** 2026-11-08
**Estado:** CONTRATO TÉCNICO PROPUESTO E IMPLEMENTADO EN FIXTURES; unidad/sandbox real NO VALIDADA; publicación autorizada en la rama de desarrollo; SHA pendiente de registrar tras el push.
**Alcance autorizado:** diseño y pruebas aisladas en VPS de desarrollo. No autoriza cambios de unidad, cuentas, systemd, runtime, R-05 ni VPS de pruebas.

## 1. Objetivo

Resolver en diseño el conflicto de B4.2: systemd inicia un supervisor root con grupo primario `xray`, mientras el proceso final Xray debe ejecutarse como `xray:xray`. El estado/runtime que Xray necesite escribir no puede quedar root-only; la evidencia de invocación, en cambio, debe seguir siendo inaccesible para el proceso de servicio.

El contrato separa tres clases de datos y sus permisos. No cambia `modules/xray_service.sh` ni declara aprobada una unidad final.

## 2. Layout propuesto

| Ruta | Propietario | Modo | Uso y ciclo de vida |
|---|---|---:|---|
| `/var/lib/xray` | `root:xray` | `0770` | Estado persistente y `WorkingDirectory`; el proceso Xray escribe por pertenencia al grupo. `StateDirectory=xray`. |
| `/run/xray` | `root:xray` | `0770` | Datos runtime efímeros; el proceso Xray puede escribir por grupo. `RuntimeDirectory=xray`, recreado por systemd al iniciar. |
| `/var/lib/xray-manager` | `root:root` | `0700` | Padre privado persistente de la evidencia. Lo provisiona Xray-Core Manager. |
| `/var/lib/xray-manager/evidence` | `root:root` | `0700` | Evidencia durable por invocación; sólo el supervisor root accede. Lo provisiona Xray-Core Manager. |
| Archivo de evidencia | `root:root` | `0600` | JSON mínimo de atestación; nunca contiene configuración, UUID, PEM ni secretos. Escritura atómica. |

`StateDirectoryMode=0770` y `RuntimeDirectoryMode=0770` se proponen porque systemd, con `User=root` y `Group=xray`, prepara esos directorios como `root:xray`; el proceso final `xray:xray` obtiene escritura por el grupo, sin convertirlo en propietario ni abrir acceso a otros usuarios. El grupo debe ser el grupo primario validado del servicio.

La evidencia se mantiene fuera de ambos directorios para que el proceso Xray no pueda atravesar el padre `0700` ni leer/escribir los archivos `0600`. Se propone persistencia para permitir diagnóstico y correlación tras un fallo o reinicio; la retención y limpieza deben ser operaciones del Manager, con lock, exclusión de la invocación vigente y auditoría. No se implementa limpieza en B4.3.

## 3. Contrato declarativo de unidad a evaluar

El fixture representa estas propiedades, no genera ni instala una unidad:

```ini
User=root
Group=xray
StateDirectory=xray
StateDirectoryMode=0770
RuntimeDirectory=xray
RuntimeDirectoryMode=0770
ProtectSystem=strict
NoNewPrivileges=true
CapabilityBoundingSet=CAP_CHOWN CAP_SETUID CAP_SETGID CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_CHOWN CAP_SETUID CAP_SETGID CAP_NET_BIND_SERVICE
ReadWritePaths=/var/lib/xray /run/xray /var/lib/xray-manager/evidence
```

`ReadWritePaths` expresa las únicas rutas adicionales que el sandbox permite escribir bajo `ProtectSystem=strict`. Los permisos POSIX siguen siendo una segunda barrera: la identidad Xray sólo puede escribir en las rutas `root:xray 0770`; la evidencia conserva `root:root 0700`.

La lista de capacidades es el contrato B4.2 del supervisor. El hijo debe descender a UID/GID de servicio y conservar únicamente `CAP_NET_BIND_SERVICE` cuando el puerto lo requiera. No se afirma aquí que la combinación de directivas haya sido probada por systemd.

## 4. Contrato de provisión del Manager

Antes de habilitar una futura unidad, el Manager tendrá que:

1. Resolver y validar UID/GID de `xray:xray` mediante NSS; rechazar UID/GID root, identidades inconsistentes y grupos inesperados.
2. Provisionar `/var/lib/xray-manager` y `evidence` como `root:root 0700`, sin seguir symlinks y sin reparar automáticamente objetos existentes que difieran.
3. Verificar que `/var/lib/xray` coincide con el ownership/mode efectivo esperado por `StateDirectory`; cualquier conflicto se presenta y resuelve transaccionalmente, no con `chown -R`.
4. Dejar que `RuntimeDirectory=xray` sea creado/retirado por systemd; validar tras el inicio que su owner/group/mode son `root:xray 0770` y que el grupo de servicio puede escribir.
5. Comprobar que `ReadWritePaths` coincide exactamente con las rutas administradas, sin comodines ni ampliaciones implícitas.
6. Verificar precondiciones, unidad efectiva, drop-ins, `NeedDaemonReload`, permisos y estado del servicio antes de una futura transición.
7. Aplicar cambios sólo desde Xray-Core Manager, bajo lock, confirmación, journal, verificación postcondición y rollback/recovery cuando proceda.

B4.3 no añade aún esas operaciones al Manager; sólo modela y prueba el contrato. No modifica la unidad existente.

## 5. Implementación fixture

- `scripts/xray_runtime_directory_contract.py` define el contrato declarativo, mapea rutas absolutas a una raíz fixture marcada, crea exclusivamente directorios ausentes y valida UID/GID/modo/tipo de cada directorio.
- Rechaza raíz sin marcador, GID inválido, symlinks en componentes y drift de ownership/modo. No corrige automáticamente un directorio preexistente inseguro.
- `tests/test_xray_runtime_directory_contract.py` prueba separación efectiva de acceso (la identidad de servicio puede escribir estado/runtime y no puede leer ni escribir evidencia), layout válido, idempotencia, rechazo de drift, padres escribibles no confiables, symlinks, raíz no marcada y GID inválido. Suite focal: 9/9 PASS; regresión Python global: 446/446 PASS; `bash -n` 91/91, ShellCheck global, compileall, `install.sh --check` y diff-check PASS.
- El fixture usa GID numérico 65534 como sustituto aislado; no resuelve ni crea `xray:xray` en el host.

## 6. Límites de validación

- No se ejecutó `systemd-analyze verify` ni se inició una unidad de prueba.
- No se validó el comportamiento real de `StateDirectory`, `RuntimeDirectory`, `ReadWritePaths`, namespaces, `PrivateTmp`, `PrivateDevices`, `ProtectHome`, `ProtectSystem`, capacidades ni `INVOCATION_ID` bajo systemd.
- No se probó escritura real de Xray en `/var/lib/xray` o `/run/xray` bajo la unidad propuesta.
- No se modificaron `modules/xray_service.sh`, unidades, cuentas, directorios del host, `/etc/xray`, R-05, menú, backend live o VPS de pruebas.
- No se alteró `Xray-Normativa/`; su README versionado no está presente en el respaldo local, mientras los otros 14 archivos normativos comparados coinciden por SHA-256. Esta diferencia se conserva sin reparación.

## 7. Siguiente paso

Revisión focal adversarial del contrato y su interacción con la unidad real existente; después, ampliar fixtures para validar creación/retención de evidencia y la separación de acceso entre supervisor y proceso Xray. La integración en `modules/xray_service.sh`, el cambio de unidad, creación de cuenta, prueba systemd real o conexión R-05 requieren autorización específica posterior.
