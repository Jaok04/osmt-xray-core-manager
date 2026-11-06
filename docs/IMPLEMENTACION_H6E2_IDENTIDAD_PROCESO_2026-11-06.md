# Implementación H6-E2 — identidad del proceso Xray

**Fecha:** 2026-11-06
**Estado:** IMPLEMENTADA Y VERIFICADA EN FIXTURES — PASS CON LIMITACIONES
**Rama:** design/user-identity-association-v1

## 1. Objetivo

Añadir una inspección read-only e independiente de la identidad de un proceso Xray, como complemento a H6-A. H6-E2 no inicia, detiene, reinicia ni modifica procesos, unidades o archivos de producción.

## 2. Implementación

Nuevo módulo scripts/xray_runtime_process_identity.py:

- Valida PID entero mayor que 1.
- Lee /proc/PID/stat y extrae starttime respetando el campo comm entre paréntesis, incluso cuando contiene espacios/paréntesis.
- Lee UID/GID efectivos desde el segundo campo de Uid: y Gid: en /proc/PID/status, comparándolos con los valores esperados que proporciona el llamador.
- Resuelve /proc/PID/exe y exige coincidencia exacta con el ejecutable administrado esperado; rechaza binarios marcados como eliminados.
- Lee cmdline como bytes separados por NUL y exige coincidencia exacta del argv esperado.
- Calcula SHA-256 del ejecutable abierto a través de /proc/PID/exe; exige archivo regular, root como propietario, un único hardlink, bit de ejecución del propietario y ausencia de escritura de grupo/otros. Comprueba estabilidad de metadatos/tamaño durante la lectura.
- Vuelve a leer starttime al final y rechaza cambios, desaparición o reutilización observable del PID durante la inspección.
- Devuelve evidencia de identidad del proceso, pero declara expresamente configuration_loaded=false y configuration_evidence=not_attested.

La raíz de procfs de producción es /proc. Una raíz alternativa sólo se acepta en pruebas si contiene el marcador regular .xray-manager-proc-fixture con el valor exacto xray-manager-proc-fixture-v1. Esto evita usar accidentalmente un árbol arbitrario como procfs.

## 3. Pruebas

Nuevo archivo tests/test_xray_runtime_process_identity.py: 22/22 PASS. Incluye PID inválido/ausente, raíz fixture no marcada, stat mal formado/PID divergente, UID/GID incorrectos, status mal formado, cmdline vacío/truncado/UTF-8 inválido/argv adicional, ejecutable incorrecto/eliminado, permisos inseguros, hardlink, cambio de metadatos durante hash y cambio de starttime, cmdline, UID/GID y ejecutable durante inspección.

Regresión global: 332/332 pruebas Python PASS. py_compile, compileall, bash -n global, pruebas Bash de servicio/control/preparación, install.sh --check, ShellCheck -S error y git diff --check: PASS.

## 4. Límites y riesgos residuales

- Las pruebas usan procfs simulado y ejecutables temporales; no se inspeccionó un proceso Xray real ni se consultó /proc de producción.
- H6-E2 todavía no está conectado a H6-A/R-05 ni al orquestador; la integración deberá pasar el MainPID obtenido de una observación systemd validada y mantener la correlación con InvocationID/ActiveEnterTimestamp bajo el lock de ciclo de vida.
- La comprobación de starttime detecta cambios observables durante la ventana de inspección, pero no constituye por sí sola una atestación criptográfica del proceso ni prueba qué configuración cargó Xray.
- El SHA-256 es del ejecutable observado, no de la configuración.
- No se modificaron modules/xray_service.sh, unidad systemd, /etc/xray, runtime, certificados, DNS, firewall, puertos, red o dependencias.
- No se habilitó backend mutador ni selector live. No se modificaron main ni Xray-Normativa/.

H6-E2 queda IMPLEMENTADA Y VERIFICADA EN FIXTURES, PASS CON LIMITACIONES. Su integración posterior quedó cubierta por H6-E3; el conjunto H6-E fue auditado integralmente (H6-E4) en docs/AUDITORIA_H6E_INTEGRAL_2026-11-06.md. Ese dictamen no autoriza operaciones live.
