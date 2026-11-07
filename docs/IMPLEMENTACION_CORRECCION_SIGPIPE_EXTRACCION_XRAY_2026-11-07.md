# Corrección de SIGPIPE durante la validación del binario Xray-core

**Fecha:** 2026-11-07  
**Rama:** `design/user-identity-association-v1`  
**Estado:** IMPLEMENTADA, VERIFICADA Y PUBLICADA EN GITHUB; actualización de VPS Pruebas pendiente.

## Antecedente y evidencia real

En la VPS Pruebas (`08827b29-b7f9-4625-8ff3-351918a03c96`), la segunda instalación real de Xray-core `26.10.31` descargó el ZIP oficial y su archivo `.dgst`. El SHA-256 calculado (`e4bd9119f50ae7c41658b1abd0679ae06f98bd864a2907ff33f2f2cf7081b214`) coincidió con el valor publicado y con el valor fijado localmente. La extracción segura del ZIP y la ejecución de `xray version` funcionaron.

La traza `bash -x` aisló el fallo en `xray_admin_extract_stage()`: después de validar la versión mediante `grep`, se ejecutaba `"$stage/xray" version | head -n 1`. El proyecto opera con `set -o pipefail`; `head` cerraba la tubería al recibir la primera línea, y el productor podía terminar con `SIGPIPE`, haciendo que la tubería completa devolviera error. La función abortaba antes de instalar binario/geodata. El `RETURN` trap hizo limpieza; no quedó binario, geodata ni manifiesto parcial.

## Cambio

- `modules/xray_admin.sh`: captura la salida completa de `xray version` en `version_output`; comprueba el código de salida del binario; busca la versión requerida en la salida capturada; imprime la primera línea mediante expansión de parámetro, sin tubería truncada.
- `tests/xray_admin.sh`: el ZIP fixture contiene un ejecutable Python que imprime la versión seguida de 20.000 líneas. La prueba exige que la extracción termine correctamente y que la salida visible sea exactamente la primera línea. Esta salida supera el tamaño habitual de una tubería y reproduce la condición que hacía fallar `head` bajo `pipefail`.
- Se mantiene el rechazo de rutas ZIP no permitidas y las demás verificaciones de extracción.

## Contraste normativo

Se contrastó la corrección con la documentación aprobada en `Xray-Normativa/`, especialmente el alcance de Administración Xray-core de las Etapas 1 y 6. El cambio repara una condición de error de la validación/instalación; no altera opciones del menú, versiones habilitadas, política de hashes, directorios de datos, ni el límite entre instalar Xray y preparar/iniciar el servicio. La comparación `diff -qr /root/Xray_Manager_Documentacion_Final_2026-10-31 Xray-Normativa` reportó únicamente el `README.md` auxiliar; los documentos normativos originales permanecen idénticos. `Xray-Normativa/` no se modificó.

## Pruebas

- `bash tests/xray_admin.sh`: PASS con fixture de salida multipágina.
- Todas las suites Bash `tests/*.sh`: **62/62 PASS**.
- Suite Python `python3 -m unittest discover -s tests -p 'test_*.py' -v`: **406/406 PASS**.
- Sintaxis Bash global: PASS.
- `python3 -m compileall -q scripts tests`: PASS.
- ShellCheck global `-S error`: PASS.
- `./install.sh --check`: PASS sin modificar el sistema.
- `git diff --check`: PASS.

## Límites y seguridad

- La traza proviene de la VPS Pruebas; la corrección y las pruebas automatizadas se realizan en la VPS de desarrollo.
- No se ejecuta instalación real durante esta fase de desarrollo.
- No se modifica VPS Pruebas, `systemd`, runtime, configuración, certificados, DNS, firewall, puertos ni red durante esta fase.
- No se actualizan dependencias.
- La revisión y pruebas las realiza la misma sesión que implementa; no constituye auditoría independiente.
- Commit publicado: `38cc0ddfac9ab3093a1c5442d14fa04c9e416e42` en `design/user-identity-association-v1`; HEAD local y remoto coinciden.
- La actualización de VPS Pruebas y la instalación real de Xray-core 26.10.31 siguen pendientes. La corrección no se considera validada en ese host hasta completar esa prueba.
