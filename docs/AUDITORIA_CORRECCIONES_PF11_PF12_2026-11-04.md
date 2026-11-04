# Auditoría correctiva PF-11/PF-12 — almacén de perfiles v1.1

**Fecha:** 2026-11-04
**Host:** `Implementación-Xray`
**Ruta:** `/opt/xray-manager`
**Rama:** `design/user-identity-association-v1`
**Base:** `41309a45caa3c19cb86a697c41ec505c9e25678d`
**Estado:** implementación local; verificación focal y regresión integral PASS; revisión final del diff completada, sin publicar.

## 1. Autorización y alcance

El propietario autorizó corregir PF-11 y PF-12, exclusivamente en la rama de desarrollo autorizada, con pruebas aisladas, auditoría y actualización documental. Esta revisión no autoriza operaciones sobre la VPS de pruebas ni cambios de runtime.

## 2. PF-11 — contrato estricto de manifiestos

**Hallazgo original:** `read_revision_config()` aceptaba `schema_version: true` por equivalencia Python (`True == 1`) y toleraba campos adicionales. Una prueba aislada confirmó que un manifiesto con versión booleana y un campo extra se aceptaba.

**Corrección:** nuevo `validate_revision_manifest()` con conjunto exacto de campos, versión entera exacta, identidad, timestamp UTC real, esquema exacto de `config`, tamaños enteros exactos y límites, SHA-256 canónico, versión criptográfica, procedencia y estados de validación permitidos/coherentes. La lectura de cada revisión ejecuta esta validación antes de verificar el ciphertext y descifrar.

**Pruebas:** 13 variantes malformadas rechazadas con `ProfileError`: versión booleana, campo extra, campo ausente, fecha imposible, campo extra en config, tamaño booleano, tamaño negativo, hash inválido, source de tipo lista, source anidado malformado, estado de validación lista, estado booleano e incoherencia de estados. El manifiesto válido se restaura y la revisión vuelve a leerse.

## 3. PF-12 — reconciliación de perfiles definitivos no registrados

**Hallazgo original:** `create()`/`duplicate()` renombraban `.new-*` al directorio definitivo y sincronizaban `profiles/` antes de iniciar el WAL del catálogo. Un `SIGKILL` en esa ventana dejaba un directorio definitivo fuera del catálogo; la limpieza existente sólo cubría temporales y revisiones huérfanas.

**Corrección:** `cleanup_orphan_profiles()` se ejecuta bajo lock después de recuperar WAL y limpiar/reconciliar revisiones. Sólo elimina perfiles canónicos ausentes de un catálogo existente y seguro, después de validar estructura exacta, propietario/modos, metadatos, puntero de revisión, estado no validado y revisión cifrada íntegra. La eliminación sincroniza el directorio padre.

**Regla conservadora:** si el catálogo no existe (incluido un crash en el primer alta), no se puede distinguir un perfil huérfano de una pérdida externa del catálogo; el perfil se preserva. También se preservan y notifican candidatos con permisos/estructura/identidad/manifiesto/blob no verificables. La prevalidación `lstat` evita que funciones de lectura que normalizan permisos reparen un candidato sospechoso antes de la decisión.

**Pruebas:** `SIGKILL` real tras publicación de directorio en `create()` con y sin configuración y en `duplicate()`; los candidatos válidos se retiran al siguiente lock. Se prueba el primer alta interrumpida sin catálogo (se preserva) y un candidato con `metadata.json` 0644 (se preserva y el modo inseguro permanece intacto).

## 4. Verificación

- `bash tests/xray_profiles.sh`: PASS.
- PF-11: 13 casos malformados rechazados; revisión válida vuelve a leerse.
- PF-12: crash recovery de create/duplicate, primer alta ambigua y preservación de candidato inseguro PASS.
- Python AST, sintaxis Bash de archivos shell afectados, ShellCheck focal y `git diff --check`: PASS en verificación preliminar.
- Regresión completa `tests/*.sh`: **51/51 scripts PASS**, exit code 0, ejecutada después de incorporar la reconciliación conservadora final.

## 5. Archivos afectados

- `scripts/xray_profiles.py`
- `tests/xray_profiles.sh`
- `docs/DISENO_IMPLEMENTACION_PERFILES.md`
- `docs/AUDITORIA_CORRECCIONES_PF11_PF12_2026-11-04.md`
- Documentos de continuidad: pendientes de consolidación al terminar la regresión.

## 6. Restricciones respetadas

Pruebas exclusivamente con almacenes temporales y claves sintéticas. No se leyó ni utilizó `master.key`; no se creó ni modificó el almacén live; no se creó perfil live; no se modificaron Xray/runtime, systemd, certificados, firewall, puertos o red. No se accedió ni modificó `Vps de Pruebas`. `Xray-Normativa/` no se modificó. No se creó commit ni se publicó todavía.

## 7. Estado y siguiente puerta

PF-11 y PF-12 están IMPLEMENTADOS y VERIFICADOS localmente. La prueba focal `tests/xray_profiles.sh` PASS; regresión completa `tests/*.sh` **51/51 PASS** (exit code 0). Python AST PASS; `bash -n` PASS para los archivos shell afectados; ShellCheck focal PASS; `git diff --check` PASS. Se revisó el diff de código y pruebas. El árbol de trabajo queda intencionalmente con cambios locales; no se creó commit ni se publicó/sincronizó.

PF-11/PF-12 no equivalen a aceptación formal del almacén v1.1. Los pendientes funcionales de Etapa 5 siguen separados de esta remediación. Etapa 5 y Etapa 2 permanecen ABIERTAS. La publicación requiere autorización expresa independiente.
