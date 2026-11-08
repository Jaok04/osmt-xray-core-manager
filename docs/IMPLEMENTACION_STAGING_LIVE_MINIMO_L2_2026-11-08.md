# Envoltura mínima de staging live TLS — L2 (2026-11-08)

**Estado:** IMPLEMENTADA Y PROBADA EN AISLAMIENTO; no ejecutada contra rutas productivas.
**Rama:** `design/user-identity-association-v1`
**Objetivo:** preparar la configuración VLESS/VMess TLS de una revisión exacta usando la identidad real de `xray.service`, sin publicar configuración ni iniciar/detener/reiniciar el servicio.

## Implementación

Se añadieron:

- `scripts/xray_runtime_live_staging.py`: envoltura live independiente, con rutas productivas constantes y sin argumentos para sustituirlas por fixtures.
- `tests/test_xray_runtime_live_staging.py`: pruebas aisladas de flujo, rechazo de unidad no cargada, TOCTOU del mapping, permisos y limpieza compensatoria.

La envoltura reutiliza:

1. `xray_runtime_preflight.preflight_profile()` para revisar el contenido exacto, el informe persistido y el hash del binario.
2. `xray_runtime_systemd_adapter.status()` directamente para observar la unidad real, sin fabricar un fixture R-01.
3. El contrato de mapping I-01/I-02 en `/var/lib/xray-manager/profile-bindings/<profile_id>/<revision>.json`.
4. `certificate_resolver.service_identity()` y `certificate_resolver.prepare()` para comprobar `xray:xray` y resolver los leases TLS del catálogo central.
5. `xray_runtime_staging_core` para validar la cobertura TLS exacta e inyectar sólo leases coincidentes.
6. El validador nativo existente para ejecutar `xray run -test` con UID/GID reales del servicio.

## Controles

- Lock exclusivo root-only en `/run/xray-manager-runtime-staging.lock`.
- Rutas productivas codificadas; no hay `fixture_root`, rutas CLI alternativas ni selector de entorno por variable.
- Rechazo de symlinks, mapping fuera de contrato, permisos incorrectos, unidad no cargada/no administrada, identidad distinta de `xray:xray` y estados de servicio incompatibles.
- Segunda lectura de perfil, informe, mapping y systemd para detectar cambios durante la resolución de leases.
- Staging temporal bajo `/run/xray-manager-runtime-staging`; archivos root:`xray` 0640 y directorios de operación 0750.
- Limpieza compensatoria de staging y leases si falla cualquier fase posterior a su creación.
- El manifiesto no contiene PEM ni claves privadas.
- La salida declara explícitamente `runtime_published=false` y `service_started=false`.

## Validación

Pruebas focales live staging: **7/7 PASS**.
Regresión focal combinada (live staging, R-02, núcleo TLS y preflight): **50/50 PASS**.
Suite Python completa: **506/506 PASS**.
También PASS: 62/62 suites Bash, `compileall`, sintaxis Bash, ShellCheck global `-S error`, `install.sh --check` y `git diff --check`.

## Límites y puertas pendientes

Esta implementación no es todavía el publicador ni el orquestador live:

- No publica `/etc/xray/config.json`.
- No crea ni modifica `xray.service`, cuentas, permisos del sistema, firewall, DNS o certificados.
- No inicia, detiene, reinicia ni habilita Xray.
- No se ejecutó `stage_live` en ningún host.
- No se integró con el menú ni con R-05.
- No se ejecutó contra VPS Pruebas ni se accedió a sus rutas productivas.

La ruta permanece desconectada del Administrador hasta completar la revisión independiente H6-G3, resolver los hallazgos live pendientes y recibir autorización específica para la siguiente operación. El siguiente bloque de desarrollo debe revisar el contrato del publicador/transacción mínima y su recuperación antes de cualquier integración live. No convertir esta etapa de staging en permiso para publicar o arrancar el servicio.
