# Corrección H-01 — Rechazo de symlinks rotos en rutas del historial

**Fecha:** 2026-11-04
**Autorización:** el propietario autorizó corregir H-01, añadir pruebas y ejecutar la regresión correspondiente.
**Alcance:** exclusivamente validación de componentes de la ruta --store en la CLI de historial C-05D/E.
**Estado:** CORREGIDO, PROBADO Y DOCUMENTADO.

## 1. Causa

La comprobación anterior combinaba Path.exists() con Path.is_symlink(). Para un enlace simbólico roto, exists() devuelve falso y el componente no era rechazado; el CLI podía presentar un historial vacío como si el almacén no estuviera inicializado.

## 2. Corrección aplicada

En scripts/xray_validation_history.py se incorporó _reject_symlink_components(Path). Recorre la ruta absoluta desde su raíz e inspecciona cada componente con lstat(), identificando el propio enlace sin seguir su destino. Rechaza enlaces directos, ancestros simbólicos válidos y ancestros simbólicos rotos. Si encuentra un componente inexistente ordinario, detiene la inspección y conserva el comportamiento esperado de almacén aún no creado. Los errores de inspección se convierten en ValidationHistoryError.

No se crea, repara ni modifica el almacén durante consultas.

## 3. Pruebas añadidas

En tests/test_xray_validation_history.py:
- H39: rechaza symlink directo.
- H40: rechaza ancestro symlink cuyo destino existe.
- H41: rechaza ancestro symlink roto.
- H42: permite ruta ordinaria inexistente y devuelve historial vacío.

Las pruebas invocan el CLI real en subprocesos y verifican código de salida y diagnóstico.

## 4. Resultados ejecutados

- Suite focal historial: **42/42 PASS**.
- Regresión Python completa: **80/80 PASS**.
- Regresión shell completa: **57/57 PASS**, cero fallos.
- py_compile scripts/*.py tests/test_*.py: PASS.
- bash -n sobre archivos shell inventariados y install.sh: PASS.
- ShellCheck -S error sobre archivos shell inventariados e install.sh: PASS.
- ShellCheck -S warning sobre los siete archivos Bash focales C-05E: cero advertencias.
- install.sh --check: PASS, no modificó el sistema.
- git diff --check: PASS tras eliminar un espacio final detectado inicialmente.

No se declara un resultado global de ShellCheck -S warning; esa exploración global no forma parte de esta regresión.

## 5. Límites y seguridad

Pruebas ejecutadas con directorios temporales y symlinks sintéticos. No se abrió la clave maestra real ni se accedió a almacenes live. No se modificaron runtime, servicios, certificados, firewall, puertos, red, dependencias, main, Xray-Normativa/ ni VPS de pruebas.

## 6. Estado

H-01 queda **CORREGIDO Y VERIFICADO**. La auditoría C-05F conserva el hallazgo original como resultado histórico reproducido el 2026-11-04; este documento registra su remediación posterior. D-01–D-05 permanecen sin cambios. La aceptación de C-05F no equivale al cierre de Etapa 5 o Etapa 2.
