# Auditoría C-04C — integración del gestor de configuraciones con menú Bash

**Fecha:** 2026-11-04
**Rama:** design/user-identity-association-v1
**Host/ruta:** Implementación-Xray:/opt/xray-manager
**Autorización:** el propietario autorizó C-04C, limitada a conectar el gestor independiente con el menú Bash, después de solicitar y verificar primero la publicación de C-04B.

## 1. Alcance

C-04C conecta las operaciones ya implementadas y aceptadas C-01–C-04B con la interfaz Bash existente. No amplía el motor Python ni modifica el contrato del almacén.

Archivos modificados:
- bin/xray-manager: carga el nuevo módulo de interfaz.
- config/paths.sh: define la ruta configurable del almacén independiente y la ruta configurable de la clave maestra existente.
- modules/profiles.sh: conecta la opción [1] Gestionar configuraciones de Xray del menú aprobado.
- modules/xray_configurations_menu.sh: nuevo módulo de interfaz y despacho CLI.
- tests/smoke.sh: incorpora el nuevo módulo a la comprobación sintáctica.
- tests/xray_configurations_menu.sh: nueva prueba de integración.

## 2. Operaciones integradas

El submenú ofrece:
- Consultar configuraciones: selección desde el catálogo, metadatos, revisión y estado; mostrar el JSON descifrado requiere confirmación expresa. El contenido se exporta a un directorio temporal privado y se limpia al terminar.
- Crear: plantilla vacía o mínima, confirmación y resultado de creación.
- Editar: selección de configuración, archivo fuente absoluto, preview, diff sin valores secretos, hash y revisión base, confirmación y creación de revisión inmutable.
- Importar: preview, hash SHA-256, nombre, confirmación y aceptación adicional si el JSON inválido se conservará como Borrador.
- Exportar individual: revisión opcional, destino absoluto, confirmación de sobrescritura y confirmación de exportación.
- Exportar múltiples: manifiesto, preview, comprobación de los dos hashes y confirmación exacta antes de ejecutar.
- Comparar: dos configuraciones, revisiones opcionales y diff de solo lectura sin valores secretos.
- Consultar revisiones: historial inmutable por configuración.
- Eliminar: preview y dos confirmaciones, incluida la afirmación explícita de que el elemento no está aplicado ni en uso.

La selección de configuración se obtiene del CLI y no construye rutas a partir de nombres. Los argumentos se transmiten como argumentos separados; no se usa eval.

## 3. Controles y límites

- El CLI exige root, Python 3 y jq; si falta una herramienta, la interfaz informa el problema y no instala dependencias.
- El almacén predeterminado es /var/lib/xray-manager/configurations; la clave predeterminada es la ruta de la clave maestra ya existente. La interfaz no crea, regenera ni lee por su cuenta la clave.
- La prueba de integración sustituye ambas rutas por un directorio temporal y una clave sintética de 32 bytes, con permisos 0600.
- La consulta del JSON descifrado advierte sobre credenciales y exige confirmación. El archivo temporal se crea dentro de un directorio privado.
- La importación y edición conservan las comprobaciones de preview/hash/revisión del motor.
- La exportación individual conserva las comprobaciones de ruta, symlink/hardlink, overwrite y permisos del motor.
- La exportación múltiple conserva el manifiesto estricto, preview, hashes y resultados parciales de C-04B.
- La eliminación conserva preview-delete, --confirm, --expected-name y --assert-not-active; la interfaz advierte que el almacén independiente no puede verificar actividad runtime externa.
- No se añade ninguna ruta apply o activate. El submenú no escribe config.json, no llama a systemctl, no modifica perfiles ni activa configuraciones.
- No se cambia el menú principal ni la normativa protegida; la integración se limita al punto de menú aprobado para configuraciones/perfiles/respaldo.

## 4. Pruebas

Nueva prueba tests/xray_configurations_menu.sh:
- crea una configuración mínima;
- importa un JSON temporal sin alterar la fuente;
- edita y verifica una nueva revisión conservando la anterior;
- consulta metadatos y muestra el JSON sólo tras confirmación;
- exporta individualmente y compara bytes/permisos;
- ejecuta exportación múltiple con manifiesto temporal y confirma los dos destinos;
- compara configuraciones sin exponer valores secretos;
- consulta historial de revisiones;
- elimina un objeto temporal tras las dos confirmaciones;
- verifica la navegación desde el menú aprobado y el recorrido completo desde el menú principal hasta el gestor y de regreso.

Todas las pruebas de esta suite usan un almacén temporal y una clave sintética. No se usa /etc/xray-manager/keys/master.key.

Resultados:
- tests/xray_configurations_menu.sh: PASS.
- tests/smoke.sh: PASS.
- tests/stage1_menu.sh: PASS.
- Regresión completa tests/*.sh: 56/56 PASS.
- bash -n en scripts/*.sh, tests/*.sh, modules/*.sh, bin/xray-manager, config/*.sh y lib/*.sh: PASS.
- ShellCheck focal en modules/xray_configurations_menu.sh, tests/xray_configurations_menu.sh, modules/profiles.sh y config/paths.sh: PASS.
- python3 -m py_compile scripts/*.py: PASS.
- git diff --check: PASS.

## 5. Exclusiones

No se accedió al almacén live ni se leyó la clave maestra real. No se modificaron runtime, configuración activa, perfiles, servicios/systemd, certificados, firewall, puertos, red ni dependencias. No se instaló ni actualizó ningún paquete. No se tocó Vps de Pruebas, main ni Xray-Normativa/.

C-04B ya está publicada y sincronizada en el commit 0f8ea9df5fa4927c27deafab405c446f1c4dc4dd. C-04C permanece IMPLEMENTADA, VERIFICADA Y AUDITADA LOCALMENTE, pendiente de aceptación formal. No se hizo commit, push ni sincronización de C-04C. C-04 completa, Etapa 5 y Etapa 2 permanecen ABIERTAS.
