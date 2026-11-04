# Auditoría técnica C-01 — gestor de configuraciones independientes

**Fecha:** 2026-11-04
**Host/ruta:** `Implementación-Xray` — `/opt/xray-manager`
**Rama/base:** `design/user-identity-association-v1` — `7e899d898e99d3a279ccff07dc65cb32dc51cc7e`
**Alcance autorizado:** C-01, exclusivamente contrato y persistencia inicial.
**Estado:** ACEPTADO FORMALMENTE COMO COMPONENTE LIMITADO por decisión expresa del propietario el 2026-11-04.

## 1. Resultado

Se implementó `scripts/xray_configurations.py` como almacén separado de configuraciones JSON independientes. No reutiliza ni modifica `scripts/xray_profiles.py`, los almacenes de conexiones VLESS/VMess ni sus catálogos.

Operaciones disponibles en esta fase:
- `create --name ... [--template empty|minimal]`
- `list`
- `show --config-id ...`

La plantilla vacía crea un objeto Borrador sin contenido/revisión y no requiere leer clave. La plantilla mínima crea una primera revisión cifrada, no validada. No se implementaron importación/exportación, edición, diff, comparación, eliminación, menú Bash, validador estático, integración con perfiles ni activación.

## 2. Persistencia y seguridad implementadas

- Raíz separada: `/var/lib/xray-manager/configurations` (en pruebas se sustituye por un directorio temporal).
- Catálogo `catalog.json`, objetos `items/config-<32 hex>`, metadatos, revisiones `rNNNNNN`, `config.enc.json` y `manifest.json`.
- Contratos cerrados de catálogo, metadatos y manifiesto; tipos estrictos, fechas UTC reales, IDs, nombres normalizados, punteros y estado coherentes.
- Límite de contenido de 16 MiB; catálogo máximo 10.000 objetos.
- AES-256-GCM, nonce aleatorio de 12 bytes y AAD ligada a ID/revisión. Clave maestra existente leída mediante `certificate_crypto.load_master_key`; no se crea ni regenera.
- SHA-256 del blob cifrado y autenticación GCM al consultar la revisión.
- Directorios root:root 0700, archivos root:root 0600; rechaza symlink/hardlink y no corrige automáticamente permisos sospechosos.
- Lock exclusivo `flock`, escrituras atómicas con fsync y journal WAL independiente.
- Publicación de directorio incluida dentro de la transacción: el WAL se persiste antes del rename; recuperación revierte catálogo y retira directorio/staging si la operación se interrumpe.
- Estados conservadores: `not_validated`; activación declarada como `not_managed_by_independent_configurations`.

## 3. Pruebas

`tests/xray_configurations.sh` PASS. Incluye:
- creación vacía y plantilla mínima;
- list/show, nombres duplicados y estados no activos;
- modos/propietario de objetos y artefactos;
- lectura autenticada con clave sintética;
- rechazo de clave incorrecta;
- alteración de ciphertext con SHA-256 del manifiesto recalculado (se alcanza AES-GCM y se rechaza por autenticidad);
- rechazo de catálogo malformado sin reparación;
- ausencia de creación/regeneración de clave cuando no existe;
- SIGKILL después de publicar WAL, después de publicar el directorio y después de actualizar catálogo; recuperación al siguiente lock, sin objeto/catálogo parcial ni journal sobrante.

Verificación global posterior a la implementación: `tests/*.sh` **52/52 PASS**, exit code 0. `bash -n tests/xray_configurations.sh`, ShellCheck focal, Python AST y `git diff --check` PASS.

## 4. Límites y pendientes

- La matriz no representa todas las permutaciones de fallos de filesystem ni fallos físicos de kernel/dispositivo.
- No se ha integrado el módulo en `install.sh` ni en menús: la fase C-01 es deliberadamente de persistencia aislada.
- C-02 importación/exportación, C-03 edición/diff, C-04 interfaz/eliminación, C-05 validador y C-06 creación de perfil desde fuente independiente siguen pendientes y requieren autorización/fases separadas.
- No se declara configuración Validada: no existe todavía el validador estático ni informe asociado al hash.
- No existe operación `apply`/`activate`; el módulo no escribe runtime.
- No se probó la clave maestra real ni el almacén live.

## 5. Límites operativos

Se usaron únicamente directorios temporales y claves sintéticas. No se leyó `/etc/xray-manager/keys/master.key`, no se creó almacén live, no se tocó `xray_profiles.py`, VLESS/VMess, runtime, systemd, certificados, firewall, puertos, red ni la VPS `Vps de Pruebas`. No se instalaron ni actualizaron dependencias. `main` y `Xray-Normativa/` no se modificaron. No se hizo commit, push ni sincronización.

**Conclusión:** C-01 implementado y probado dentro del alcance descrito. C-01 queda aceptado únicamente en el alcance probado. Esta aceptación no completa Etapa 5 ni Etapa 2. C-02 se inició con autorización expresa independiente y se audita en `docs/AUDITORIA_C02_IMPORTACION_EXPORTACION_2026-11-04.md`.
