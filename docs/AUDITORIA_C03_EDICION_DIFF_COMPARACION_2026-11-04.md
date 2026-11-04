# Auditoría técnica C-03 — edición, diff y comparación

**Fecha:** 2026-11-04
**Host/ruta:** `Implementación-Xray` — `/opt/xray-manager`
**Rama/base:** `design/user-identity-association-v1` — base inspeccionada `c30a474195406617a20fd517b7588420e48293d2`
**Autorización:** aceptación formal de C-02 y autorización expresa para iniciar C-03.
**Estado:** ACEPTADO FORMALMENTE COMO COMPONENTE LIMITADO POR EL PROPIETARIO (2026-11-04); PRUEBAS FOCALES Y REGRESIÓN COMPLETA PASS.

## 1. Contraste normativo y alcance

C-03 se contrastó con:

- `Xray-Normativa/05_Configuraciones_Perfiles/Etapa_5_Configuraciones_Perfiles.md`, §§2–5 y 14.
- `Xray-Normativa/05_Configuraciones_Perfiles/Etapa_5_Configuraciones_Perfiles.yaml`.
- `docs/DISENO_GESTOR_CONFIGURACIONES_INDEPENDIENTES.md`, §§3.4, 4, 5.4, 5.6 y matriz §11.

Se implementa edición avanzada basada en archivo fuente, vista previa, diff estructural, comparación de solo lectura e inspección del historial de revisiones. No se integra menú Bash, editor interactivo, validador Xray, eliminación, exportación múltiple ni creación de perfiles.

## 2. Operaciones CLI

- `preview-edit --config-id ID --source /ruta/absoluta`: lee un archivo regular UTF-8 de hasta 16 MiB, calcula SHA-256, informa validez JSON y compara contra la revisión actual. No persiste cambios.
- `edit --config-id ID --source /ruta/absoluta --expected-sha256 HASH --expected-revision rNNNNNN|none --confirm [--accept-invalid]`: exige hash de la vista previa, revisión base esperada y confirmación. Si el JSON no es válido, exige además `--accept-invalid`. El contenido queda como Borrador.
- `compare --first ID --second ID [--first-revision REV] [--second-revision REV]`: compara dos objetos/revisiones, sin mutar el almacén.
- `revisions --config-id ID`: enumera revisiones, origen, fecha, tamaño, hash del ciphertext, revisión actual y estado no validado.

La ruta fuente se lee con los controles de importación ya establecidos: ruta absoluta, rechazo de symlink/hardlink, archivo regular, límite de tamaño, lectura estable y UTF-8 válido. El origen no se modifica.

## 3. Diff estructural y confidencialidad

- Los objetos JSON ignoran el orden de sus claves.
- Los arrays conservan orden y se comparan por índice; reordenar elementos se considera cambio.
- Cada diferencia informa ruta JSON Pointer, sección (`inbounds`, `outbounds`, `routing`, `dns` u `otras`) y tipo (`added`, `removed`, `changed`).
- No se devuelven valores anteriores ni nuevos. El diff expone rutas y tipos de cambio, no credenciales, UUID, contraseñas ni claves almacenadas como valores JSON.
- El resultado limita la salida a 10.000 diferencias y el recorrido a 100.000 nodos y 128 niveles; cuando se supera un límite, informa `truncated=true` y no afirma igualdad.
- Si alguno de los dos documentos no es JSON sintácticamente válido, `structural_available=false`; no se simula un diff semántico ni se imprime el contenido.
- UTF-8 BOM y bytes originales se conservan exactamente. No se reserializa JSON.

## 4. Versionado, cifrado y transacción

Cada edición que cambia bytes crea una revisión monotónica nueva e inmutable. La revisión previa no se modifica ni elimina. El manifiesto usa `source=edit`, AES-256-GCM, nonce aleatorio de 12 bytes, AAD vinculada a ID/revisión, hash de ciphertext y estado de validación pendiente. La metadata mueve `current_revision` a la nueva revisión; el componente no promueve a Validada.

La publicación usa el lock exclusivo existente y WAL. La revisión se construye en un directorio privado de staging; el journal describe los directorios de staging/final y el snapshot previo de metadata. El directorio final se publica y metadata se reemplaza atómicamente. Si hay interrupción después de publicar la revisión y antes de confirmar metadata, la recuperación restaura metadata y retira únicamente los directorios transaccionales identificados. No se toca ninguna revisión anterior.

Se añadieron al contrato WAL sólo los patrones exactos de staging y revisión final propios de C-03; se mantienen restricciones de rutas, número de cambios y directorios, y validación antes de recuperar.

Una edición con contenido idéntico se rechaza para evitar revisiones redundantes. La edición exige que `current_revision` siga coincidiendo con la revisión vista en preview; un cambio concurrente obliga a previsualizar de nuevo.

## 5. Pruebas C-03

Nueva suite: `tests/xray_configurations_c03.sh`.

Casos verificados:

- Vista previa no persistente y hash SHA-256.
- Edición confirmada produce `r000002`; revisión `r000001` permanece byte a byte intacta.
- Descifrado/autenticación AES-GCM de la revisión nueva con clave sintética.
- Manifiesto `source=edit` y estado `pending`; no se marca Validada.
- Historial enumera revisiones y distingue la actual.
- Comparación de revisiones del mismo objeto y de objetos distintos.
- Orden de claves JSON ignorado; orden de arrays conservado y detectado.
- Diff agrupado por secciones, sin exponer valores secretos de prueba.
- JSON inválido: diff estructural deshabilitado y edición rechazada sin `--accept-invalid`; con aceptación queda Borrador y conserva bytes exactos.
- UTF-8 BOM preservado byte a byte.
- Hash incorrecto, revisión base obsoleta, falta de confirmación y edición sin cambios rechazados.
- Inyección SIGKILL después de publicar directorio de revisión y antes de metadata: siguiente operación recupera WAL, conserva la revisión anterior y elimina la nueva incompleta.

Resultado de la prueba focal C-03: **PASS**. Regresión completa de `tests/*.sh`: **53/53 scripts PASS**. C-01/C-02 continúan pasando.

## 6. Controles estáticos

- `python3 -m py_compile scripts/*.py`: PASS.
- `bash -n` en todos los `scripts/*.sh` y `tests/*.sh`: PASS.
- ShellCheck de `tests/xray_configurations_c03.sh`: PASS.
- `git diff --check`: PASS.
- ShellCheck de todo el repositorio presenta diagnósticos preexistentes en otros tests/scripts (SC1091, SC2317, SC2034 y otros); no se alteraron esos archivos. No se declara ShellCheck global limpio.
- No se instalaron dependencias.

## 7. Límites y exclusiones

- El diff comprueba sintaxis JSON, no validez semántica ni compatibilidad con Xray.
- No hay informe de validación persistido ni promoción a Validada.
- No hay editor guiado/interactive TUI, menú Bash, activación, aplicación, runtime verification, rollback de runtime, eliminación, retención ni backup/restore integral.
- No se demuestra conectividad extremo a extremo.
- La salida de diff no contiene valores, pero las rutas JSON pueden reflejar nombres de claves del documento.

## 8. Límites operativos

Sólo almacenes temporales y claves sintéticas. No se leyó `/etc/xray-manager/keys/master.key`; no se creó ni modificó almacén live; no se tocó almacén de perfiles, VLESS/VMess, runtime, systemd, servicios, certificados, firewall, puertos, red o VPS de pruebas. No se instalaron/actualizaron dependencias. `main` y `Xray-Normativa/` permanecen intactas.

La aceptación formal de C-03 fue otorgada por el propietario el 2026-11-04, limitada a los controles, escenarios, resultados y exclusiones descritos en esta auditoría. La autorización posterior para sincronizar permite publicar los cambios de implementación y documentación en la rama autorizada y dejar la VPS de desarrollo en el mismo commit; no autoriza C-04 ni cambios en otros entornos.

**Decisión del propietario (2026-11-04):** C-03 queda **ACEPTADO FORMALMENTE COMO COMPONENTE LIMITADO**, exclusivamente dentro del alcance probado y descrito en esta auditoría. La aceptación no cierra C-03 como parte de la Etapa 5 completa ni cierra Etapa 5 o Etapa 2. C-04 no se ha iniciado y requiere diseño/aprobación/autorización independientes. Etapa 5 y Etapa 2 permanecen ABIERTAS.
