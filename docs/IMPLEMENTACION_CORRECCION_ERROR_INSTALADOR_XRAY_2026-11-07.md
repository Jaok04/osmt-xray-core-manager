# Corrección del reporte de errores en instalación de Xray-core

**Fecha:** 2026-11-07
**Rama:** `design/user-identity-association-v1`
**Estado:** IMPLEMENTADA Y VERIFICADA EN PRUEBAS AUTOMATIZADAS; NO PUBLICADA.

## Antecedente

En la VPS de pruebas, el menú mostró la versión de Xray-core extraída para validación, regresó al menú y el estado persistente siguió indicando `xray_installed=false`. La inspección read-only no permitió recuperar el código de salida de aquella ejecución ni identificar la causa interna de la instalación fallida. Sí confirmó un defecto en el menú: `xray_admin_install_menu_action()` no capturaba el código de `xray_admin_install_version()` y después ejecutaba `ui_pause`, cuyo resultado podía reemplazar el resultado de la instalación. El dispatcher principal tolera fallos de la acción, por lo que no quedaba garantizado un mensaje de error visible.

## Contraste normativo

Se consultaron `Xray-Normativa/01_Menu_Principal/Etapa_1_Menu_Principal.md`, su YAML y `Xray-Normativa/06_Servicio_Diagnostico/Etapa_6_Servicio_Diagnostico.md`. La normativa contempla la administración/instalación de Xray-core, establece que los errores no deben cerrar el administrador y exige mensajes de error claros. La corrección se limita al manejo y presentación del resultado de la operación; no cambia el flujo funcional ni el alcance de instalación. Los 14 documentos normativos originales coinciden con el respaldo `/root/Xray_Manager_Documentacion_Final_2026-10-31`; `diff -qr` sólo reportó el `README.md` auxiliar de custodia, adicional a la copia maestra. `Xray-Normativa/` no se modificó.

## Cambios

- `modules/xray_admin.sh`: `xray_admin_install_menu_action()` captura el código exacto de `xray_admin_install_version()`.
- Ante fallo, muestra un mensaje explícito con operación, versión y código, e indica que no debe considerarse instalada.
- Ejecuta `ui_pause` sin permitir que su resultado oculte el código original de la operación. Si la operación fue correcta, conserva el resultado de la pausa.
- `tests/xray_admin.sh`: añade regresión con fallo simulado de código 37; comprueba que el menú devuelve 37 y presenta el mensaje de fallo. Se mantiene la prueba existente de cancelación sin descarga.

## Verificación ejecutada en VPS de desarrollo

- `bash tests/xray_admin.sh`: PASS.
- Todos los scripts Bash `tests/*.sh`: **62/62 PASS**.
- Suite Python `python3 -m unittest discover -s tests -p 'test_*.py' -v`: **406/406 PASS**.
- `bash -n` focal y global: PASS.
- `python3 -m compileall -q scripts tests`: PASS.
- ShellCheck global `-S error`: PASS.
- `./install.sh --check`: PASS; informó que no modificó el sistema.
- `git diff --check`: PASS.

## Límites y estado

- La prueba de regresión demuestra que el menú ya no oculta un fallo; no identifica retrospectivamente la causa interna del primer intento real en la VPS de pruebas.
- No se volvió a ejecutar instalación real, no se modificó la VPS de pruebas y no se instaló ni inició Xray-core.
- No se ejecutaron cambios de systemd/runtime, red, DNS, firewall, puertos, certificados ni dependencias.
- Esta verificación fue ejecutada por la misma sesión que implementó el cambio; no es una auditoría independiente.
- Cambio implementado y verificado en el checkout de desarrollo. Sin commit, push ni despliegue, conforme a la limitación expresa del propietario.
- HEAD base: `a47d2e4f4a039430ab8ef0b6b60769113a32f894`; remoto consultado durante esta sesión seguía en ese mismo SHA.
