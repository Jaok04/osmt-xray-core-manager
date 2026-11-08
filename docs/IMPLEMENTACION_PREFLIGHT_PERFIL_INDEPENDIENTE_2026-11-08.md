# Separación del preflight de perfil y servicio — L2 (2026-11-08)

**Estado:** IMPLEMENTADO; sólo refactor de validación de lectura, sin ruta live ni operaciones de servicio.
**Rama:** `design/user-identity-association-v1`
**Objetivo:** permitir que la futura envoltura live valide una revisión real sin fabricar el fixture de servicio que R-01 exige para sus pruebas aisladas.

## Hallazgo que bloqueaba stage_live

R-01 (`xray_runtime_preflight.py`) combinaba dos evidencias distintas:

1. perfil/revisión, informe de validación, hash del binario Xray y contenido exacto;
2. fixture JSON de estado de `xray.service`, deliberadamente exigido por R-01 para no consultar systemd real.

No era correcto reutilizar R-01 en producción generando un fixture sintético a partir del adaptador systemd: convertiría una observación live en una afirmación reconstruida y acoplaría dos contratos con semánticas distintas.

## Cambio

Se extrajo `preflight_profile(...)`, que valida únicamente:

- revisión y metadatos del perfil bajo lock compartido;
- manifiesto de revisión validada;
- informe persistido PASS/PASS_WITH_WARNINGS y todos los checks obligatorios;
- correspondencia exacta del hash/tamaño del contenido;
- hash del binario Xray frente al binario registrado en el informe.

Devuelve el contenido exacto en memoria (`profile_content`) para el llamador interno, junto con sus hashes/identificadores. No consulta systemd ni requiere un archivo de estado.

La función pública `preflight(..., service_state)` conserva el contrato R-01: primero valida el fixture root-owned 0600 y después invoca la nueva función. Su salida pública conserva los campos previos y no expone el contenido binario.

## Pruebas y validación

Se añadieron dos pruebas:
- la validación de perfil independiente pasa y no devuelve `service_fixture`;
- la misma validación funciona cuando el fixture de servicio no existe.

Resultados después del cambio:

- **499/499 pruebas Python PASS**.
- **62/62 pruebas Bash PASS**.
- `compileall`, `py_compile`, `bash -n`, ShellCheck global `-S error`, `install.sh --check` y `git diff --check`: PASS.

## Límites

No existe todavía `stage_live`. Esta extracción no consulta el adaptador systemd, no resuelve leases, no crea staging productivo, no publica configuración y no ejecuta Xray/systemd/ACME. No se modificaron hosts de pruebas, `/etc/xray`, `/var/lib/xray-manager`, DNS, firewall o puertos.

## Siguiente paso

La futura envoltura live debe consumir `preflight_profile` y obtener evidencia de servicio directamente mediante `xray_runtime_systemd_adapter.status()`. Debe rechazar cualquier estado/unidad/identidad incompatible y no sintetizar fixtures. Después podrá resolver leases y crear staging temporal bajo un contrato de rutas, permisos y locks productivos explícitos. Esta ruta seguirá desconectada del menú y no se ejecutará antes de H6-G3 y autorización específica.
