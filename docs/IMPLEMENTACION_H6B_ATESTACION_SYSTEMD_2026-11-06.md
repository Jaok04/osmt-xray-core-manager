# Implementación H6-B — atestación persistente systemd

Fecha: 2026-11-06
Estado: implementada y verificada en pruebas aisladas; PASS CON LIMITACIONES.
Rama: design/user-identity-association-v1.

## Objetivo
Vincular una operación R-05 aceptada con la nueva invocación de xray.service. El módulo no ejecuta systemctl ni realiza acciones sobre servicios.

## Contrato
La atestación contiene schema_version, operation_id, generation_id, config_sha256, invocation_id, active_enter_timestamp, unit_fragment_sha256, attested_at UTC y service_unit. No contiene configuración, UUID de clientes, certificados, claves privadas ni secretos.

## Validaciones
- Journal schema 2 en service_start_requested o service_restart_requested, confirmación aceptada, acción coherente y resultado accepted.
- Publicación confirmada y hash coincidente antes, después y en una segunda observación posterior.
- start exige estado previo inactive; admite InvocationID previo ausente o válido, pero exige una nueva invocación. restart exige active e InvocationID previo válido y distinto del nuevo.
- Después de la transición: LoadState loaded, ActiveState active, SubState running, Result success, ExecMainStatus 0, PID positivo e identidad xray:xray.
- InvocationID nuevo y estable en dos observaciones; ActiveEnterTimestamp estable.
- Ruta de unidad coincidente y SHA-256 de archivo regular root:root 0644. El caller debe obtener snapshots directamente del adaptador H6-A, que valida el contrato de contenido de la unidad.

## Almacenamiento
Ubicación reservada: /var/lib/xray-manager/attestations. El módulo no crea el directorio. Debe existir como root:root 0700. Archivos JSON root:root 0600, máximo 16 KiB, JSON estricto, lock interproceso, O_NOFOLLOW, escritura exclusiva, enlace atómico sin sobrescritura y fsync. Una repetición idéntica es idempotente; evidencia distinta para el mismo operation_id se rechaza.

## Archivos
Nuevo scripts/xray_runtime_attestation.py y tests/test_xray_runtime_attestation.py. No se conecta a R-05, al menú, al CLI ni al almacén fixture B4.

## Verificación ejecutada
- Pruebas focales H6-B: 12/12 PASS.
- Regresión Python global: 269/269 PASS.
- Pruebas Bash de servicio, control de servicio y preparación del servicio: PASS.
- compileall, bash -n global, ShellCheck -S error, install.sh --check y git diff --check: PASS.
- Escaneo estático del módulo: sin systemctl, subprocess, shell ni eval.
- No se instaló ni actualizó ninguna dependencia.

## Limitaciones y siguiente integración
El almacén y el constructor aún no están conectados al orquestador. El caller deberá mantener el lock de ciclo de vida compartido durante la relectura del estado, la transición, las dos observaciones posteriores y la persistencia. También deberá pasar snapshots recién obtenidos del adaptador H6-A; no se permite construirlos desde datos fixture ni reutilizar el registro activo B4. La ruta reservada no se ha creado ni utilizado en el sistema real.

## Límites
No se invoca systemctl real. No se inicia/reinicia/detiene Xray. No se lee ni escribe /etc/xray, /etc/systemd o /var/lib/xray-manager en producción. No se modifican certificados, DNS, firewall, puertos, red ni dependencias. No se publica el commit.


## H6-C — integración R-05/H6-B (2026-11-06)

El propietario autorizó H6-C exclusivamente con mocks y fixtures. Se modificó scripts/xray_runtime_orchestrator.py para inyección de backend por contexto, manteniendo el adaptador fixture R-05 como default. Los backends alternativos sólo se aceptan como dobles de prueba explícitos; no hay selector real en CLI. Se conectó la persistencia H6-B a las rutas fixture de start/restart, con snapshots sintéticos before/after/confirmed dentro del lock de ciclo de vida. Divergencias provocan rollback fixture. Recovery valida la atestación persistida y falla cerrado si falta.

Evidencia: docs/IMPLEMENTACION_H6C_INTEGRACION_R05_ATESTACION_2026-11-06.md y docs/AUDITORIA_H6C_INTEGRACION_R05_ATESTACION_2026-11-06.md. H6-C 7/7 focales, H6-B 12/12 focales y Python global 276/276 PASS. compileall, bash -n, ShellCheck -S error, install.sh --check, tres pruebas Bash de servicio y git diff --check PASS.

Limitaciones: las observaciones son sintéticas; H6-A no se invocó; no existe backend mutador systemd ni selección live en CLI. La marca de doble de prueba es una salvaguarda de diseño, no una frontera contra código Python arbitrario. Sin systemctl/Xray real, WAN, certificados/DNS/firewall/red o dependencias. No commit/push. main y Xray-Normativa/ intactas. H6-C queda IMPLEMENTADA, VERIFICADA Y AUDITADA, PASS CON LIMITACIONES. Siguiente bloque requiere diseñar el adaptador de servicio real por separado y solicitar autorización live específica.
