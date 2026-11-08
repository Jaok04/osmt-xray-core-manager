# B4.3-A — revisión adversarial y almacén de evidencia persistente (fixtures)

**Fecha:** 2026-11-08
**Estado:** IMPLEMENTADO Y VERIFICADO EN FIXTURES; PUBLICADO EN RAMA AUTORIZADA; NO INTEGRADO NI LIVE.
**Rama:** `design/user-identity-association-v1`.
**Base:** `b9a6f359eda152bbb6a0ab7ca251c0a53534e56e`.

## 1. Objetivo y alcance

Continuar B4.3 con una revisión adversarial del layout y un prototipo aislado para crear y verificar evidencia persistente bajo el árbol fixture. El objetivo de seguridad es que el supervisor root pueda crear registros mínimos y durables, mientras la identidad de servicio Xray no pueda atravesar el directorio padre ni leer/escribir los registros.

Sólo se modificó el árbol de desarrollo `/opt/xray-manager` y se ejecutaron pruebas automatizadas. No se modificó `modules/xray_service.sh`, unidad systemd, R-05, menú, backend live, cuentas, directorios del host, runtime, DNS, firewall, red ni VPS de pruebas. No se ejecutó systemd ni daemon. `main` y `Xray-Normativa/` permanecen intactas.

## 2. Hallazgo de compatibilidad

La primitiva anterior `write_invocation_evidence()` en `xray_runtime_config_attestation.py` pertenece al fixture B4.1 y exige que `evidence_dir` sea hijo directo de la raíz fixture. Por tanto, no representa el layout B4.3 anidado `var/lib/xray-manager/evidence`. No se cambió esa primitiva ni se conectó el nuevo almacén al lanzador: se creó un módulo separado para mantener el experimento explícito y evitar afirmar integración inexistente.

## 3. Implementación fixture

Nuevo tests/test_xray_runtime_evidence_store.py: 12 pruebas focales.

- Exige raíz fixture marcada y valida el contrato completo de directorios B4.3 antes de cada operación.
- Rechaza evidencia directory que no sea `root:root 0700`, symlinks, drift y layout incompleto.
- Valida InvocationID canónica: 32 caracteres hexadecimales lowercase; el nombre de archivo se deriva únicamente de ese identificador.
- Admite únicamente metadatos mínimos: PID, SHA-256 y tamaño de configuración. Rechaza campos de configuración/bytes, UUID, password, clave privada, PEM y secretos.
- Crea temporal con `O_CREAT|O_EXCL|O_NOFOLLOW`, fija owner/group root y modo `0600`, escribe y hace `fsync`.
- Publica sin sobrescritura mediante hard-link dentro del directorio abierto; un nombre existente (incluido symlink) no se reemplaza. El temporal se elimina y se sincroniza el directorio.
- Verifica el inode abierto con `fstat`: archivo regular, root:root, modo `0600`, tamaño acotado y `st_nlink == 1`; la apertura de lectura usa `O_NOFOLLOW`.
- Permite reabrir y verificar el registro en una nueva instancia de prueba, simulando persistencia entre reinicios sin iniciar servicios.

Nuevo tests/test_xray_runtime_evidence_store.py: 12 pruebas focales.

## 4. Cobertura adversarial

| Control | Resultado |
|---|---|
| Creación atómica y metadatos root-only | PASS |
| Persistencia tras reapertura / simulación de reinicio | PASS |
| Identidad de servicio no puede atravesar padre ni leer evidencia | PASS |
| InvocationID repetida no sobrescribe el registro previo | PASS |
| Symlink en nombre destino rechazado | PASS |
| Hardlink adicional detectado por `st_nlink` | PASS |
| Directorio de evidencia simbólico rechazado | PASS |
| Campos de configuración/secretos rechazados | PASS |
| InvocationID no canónica rechazada | PASS |

Suite nueva focal: **12/12 PASS**.
B4.3 directorios + almacén de evidencia: **21/21 PASS**.
Conjunto B4 relacionado (config attestation + launcher + directorios + almacén): **51/51 PASS** en la ejecución focal combinada.
Regresión Python completa: **458/458 PASS**.
`compileall`: PASS; `bash -n`: 91/91; ShellCheck global `-S error`: PASS; `install.sh --check`: PASS sin modificar sistema; `git diff --check`: PASS.

## 5. Límites y riesgos pendientes

1. El almacén sigue siendo un prototipo fixture-only. No se integra con B4.1/B4.2, `modules/xray_service.sh`, R-05 ni el menú.
2. La ruta interna var/lib/xray-manager/evidence se abre componente por componente desde el descriptor de su padre, usando O_DIRECTORY|O_NOFOLLOW y verificando cada inode con fstat. Esto rechaza symlinks en los componentes internos y evita volver a resolverlos por ruta absoluta. La raíz fixture continúa siendo un ancla confiable: producción debe recibir un descriptor de raíz previamente validado por el Manager (o resolverlo desde un descriptor confiable con openat2), no reabrir una ruta absoluta no confiable.
3. No se ha validado el comportamiento de `ProtectSystem=strict`, `ReadWritePaths`, `StateDirectory`, `RuntimeDirectory`, namespaces ni capacidades bajo systemd real.
4. No se implementa retención ni limpieza. La futura limpieza debe ser una operación del Manager, con lock, protección de la InvocationID vigente, política de retención, auditoría y recuperación; no debe añadirse como cron/manual externo.
5. Los metadatos guardan el hash y tamaño, no bytes de configuración ni credenciales. El hash puede ser información correlacionable y debe tratarse como dato operativo sensible aunque no sea un secreto equivalente al UUID/PEM.

## 6. Estado Git y siguiente paso

Cambios locales sin commit ni push. Árbol de trabajo contiene dos archivos nuevos y actualizaciones documentales; los __pycache__ de pruebas se eliminaron.

Segunda pasada completada: se añadieron pruebas de symlink en directorio padre, fallo inyectado durante publicación con limpieza del temporal y JSON corrupto persistido. La suite focal B4 completa quedó en 51/51 y la regresión Python en 458/458. Siguiente paso recomendado: diseñar la integración fixture del almacén con el supervisor, preservando el anclaje de raíz confiable y sin habilitar operaciones live.
