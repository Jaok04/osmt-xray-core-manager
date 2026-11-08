# Implementación inicial del journal live mínimo — fixture-only

**Fecha:** 2026-11-08
**Rama:** `design/user-identity-association-v1`
**Estado:** IMPLEMENTACIÓN PARCIAL DE H6-H1-B; sólo pruebas aisladas. No habilita runtime live.
**Objetivo superior:** primer servidor VLESS + WS + TLS en `pruebas.tvrc.me:443`, desplegado desde Xray-Core Manager.

## 1. Alcance deliberadamente reducido

Se añadió una primera pieza del puente mínimo: persistencia independiente de una operación live y de su snapshot previo. Se reutiliza el contrato aprobado H6-H1 y se mantiene separado el journal fixture R-05.

Archivos nuevos:

- `scripts/xray_runtime_live_journal.py`
- `tests/test_xray_runtime_live_journal.py`

No se modificaron `xray_runtime_journal.py`, R-05, el backend live, el menú, `modules/xray_service.sh`, `Xray-Normativa/` ni `main`.

## 2. Comportamiento implementado

- Ruta productiva fijada en código: `/var/lib/xray-manager/runtime-operations`; las pruebas inyectan un directorio temporal.
- Directorios de almacén, operación y snapshot `root:root 0700`.
- Journal y snapshot `root:root 0600`.
- IDs aleatorios `runtime-op-<32 hex>` y validación estricta de perfil, revisión, validación y hashes.
- JSON estricto: objeto raíz, claves duplicadas y campos desconocidos rechazados.
- Escritura atómica por temporal exclusivo, `fsync` de archivo y directorio, `replace` y relectura/verificación.
- Snapshot exacto de configuración previa con hash, tamaño y metadatos de owner/group/mode; relectura verifica bytes y metadatos.
- Ausencia de configuración previa representada explícitamente. El journal no borra la nueva configuración ni permite declarar rollback de bytes cuando no hay snapshot.
- Transiciones monotónicas y estado `recovery_required`.
- `configuration_attested` y `completed` requieren evidencia marcada expresamente como `attested`; no se infiere a partir de publicación o proceso activo.
- Finalización `rolled_back` exige snapshot previo, configuración restaurada y resolución separada del estado del servicio.

## 3. Pruebas y validación

Pruebas focales nuevas: **16/16 PASS**. Cubren creación/lectura, snapshot exacto, primera instalación sin configuración previa, validación de IDs/hashes, estados monotónicos, evidencia de configuración, rollback, symlink, esquema/entorno fixture y manipulación del snapshot.

Regresión completa después de los cambios: **486/486 pruebas Python PASS** y **62/62 suites Bash PASS**. También PASS:

- `compileall` y `py_compile`.
- `bash -n` en módulos/scripts/lib/instalador.
- ShellCheck global `-S error`.
- `install.sh --check` (sin modificar el sistema).
- `git diff --check`.

## 4. Límites expresos

Esta implementación es sólo la base de persistencia; **no es el journal H6-H1 completo ni una integración del runtime**.

Pendiente antes de cualquier uso live:

1. Locks lifecycle → application y coordinación exclusiva del propietario.
2. Matriz de fallos/crash consistency, failpoints y recuperación de huérfanos.
3. Validación completa del schema de observaciones systemd/proceso y sanitización de errores.
4. Integración con staging/publicador live y correlación de artefactos/leases.
5. Reconciliación read-only después de timeout/respuesta perdida.
6. Rollback real de configuración y servicio, con CAS y recuperación segura.
7. Auditoría adversarial independiente H6-H1-D y revisión independiente H6-G3.
8. Atestación de los bytes realmente cargados por el proceso Xray.

El módulo todavía no tiene CLI, no crea su almacén productivo por sí solo durante pruebas, no está conectado al backend live ni al menú, y no llama `systemctl`, Xray, Certbot o ACME.

## 5. Operaciones no realizadas

No se creó `/var/lib/xray-manager/runtime-operations` en ningún host. No se tocó VPS Pruebas, `/etc/xray`, `xray.service`, usuarios/grupos, certificados, DNS, firewall, puertos ni procesos Xray. No se inició ni reinició ningún servicio.

## 6. Siguiente paso mínimo

Continuar con el staging del MVP: reutilizar el compositor y el resolver TLS existentes para producir una configuración final aislada, con identidad de servicio y lease central verificados. Mantener R-02 fixture intacto y no abrir aún la publicación live. Después implementar un publicador live acotado y conectar el journal como evidencia de la transacción.
