# Implementación R-04 — publicación atómica y rollback aislados

**Fecha:** 2026-11-04
**Estado:** Implementada y verificada localmente; pendiente de auditoría/aceptación formal y publicación.
**Ámbito:** exclusivamente fixtures temporales en VPS de desarrollo. No se modifica runtime real ni se ejecuta systemd.

## 1. Referencia normativa y alcance

Contraste con `Xray-Normativa/05_Configuraciones_Perfiles/Etapa_5_Configuraciones_Perfiles.md`, especialmente §§5, 7 y 13:
- Solo una revisión validada de un perfil puede llegar a la aplicación.
- La activación pertenece al perfil (profile_id + revision), no a una configuración independiente.
- Aplicar no equivale a guardar; el registro activo solo se actualiza después de verificar.
- Si falla la aplicación, debe intentarse recuperar la configuración anterior y comunicar el estado real.
- Nunca sobrescribir silenciosamente.

R-04 implementa el paso de publicación atómica en el destino de un **XRAY_SERVICE_ROOT fixture marcado**. La verificación de estado/servicio real queda fuera; R-05 será la orquestación simulada. La prueba real y NetMod siguen fuera de alcance.

## 2. Implementación

Nuevo `scripts/xray_runtime_publisher.py`, con subcomandos `publish`, `rollback`, `recover` e `inspect`.

### Publicación
1. Requiere root, timeout acotado, operation_store marcado y locks lifecycle/application distintos.
2. Lee journal y snapshot íntegros; exige estado `snapshot_saved`.
3. Revalida la revisión staged, su identidad profile_id/revision/validation_id, hashes, mapa de asociaciones, leases TLS y binario Xray.
4. Verifica que el destino actual todavía coincide exactamente con snapshot (hash, tamaño, UID, GID y modo); bloquea cambios TOCTOU, symlinks y hardlinks.
5. Crea un temporal exclusivo en el mismo directorio/filesystem, con propietario root:grupo-servicio y modo 0640; escribe, hace fsync y ejecuta `xray run -test -config <temporal>` bajo UID/GID de servicio.
6. Revalida el destino inmediatamente antes del rename atómico, ejecuta `os.replace`, fsync del directorio y vuelve a leer/verificar hash, propietario y permisos.
7. Solo después actualiza journal a `config_published`, guardando hash y fecha.

### Rollback
- Restaura los bytes exactos del snapshot mediante temporal exclusivo y rename atómico.
- Verifica el archivo restaurado y lo vuelve a validar con Xray bajo UID/GID de servicio.
- Conserva en journal estado, hash restaurado, resultado y errores.
- Si no existía configuración anterior (`no_previous_config`), no borra automáticamente la primera configuración publicada: registra `recovery_required` y exige intervención explícita.
- Si el destino no coincide con snapshot ni staging, o el snapshot está corrupto, no sobrescribe.

### Recuperación
- Limpia temporales de publicación solo si cumplen patrón, tipo, propietario, grupo, permisos y número de enlaces esperados.
- Detecta rename completado antes de actualizar journal; si había snapshot anterior, revierte y valida.
- Distingue publicación no realizada de publicación detectada.
- Recupera idempotentemente interrupciones durante rollback.
- Cuando no existe configuración previa, conserva la configuración publicada y registra intervención requerida.
- No inicia, detiene ni reinicia servicio.

## 3. Persistencia y seguridad

Se amplía el esquema de journal R-03 con bloques estrictos `publication` y `rollback`, estados coherentes y validación de tipos/valores. Los metadatos no contienen claves privadas ni contenido de certificados.

R-04 opera exclusivamente en el XRAY_SERVICE_ROOT fixture registrado y validado por R-03. No existen defaults a `/etc/xray` real. El único ejecutable externo es el binario Xray ya identificado por hash en el manifiesto. Los archivos temporales se crean en el mismo filesystem del destino para que rename sea atómico.

## 4. Pruebas

- `tests/test_xray_runtime_publisher.py`: **12/12 PASS**.
- `tests/test_xray_runtime_journal.py`: **22/22 PASS**.
- `tests/test_xray_runtime_staging.py`: **11/11 PASS**; contiene el recorrido integrado R-02 → R-03 → R-04, incluido rollback.
- Regresión Python completa: **153/153 PASS**.
- Regresión shell: **58/58 PASS**.
- `py_compile`, `bash -n` global, `install.sh --check`, ShellCheck severidad error y `git diff --check`: PASS.

Casos R-04: publicación y rollback; idempotencia; ausencia de configuración previa; interrupción antes/después del rename; interrupción durante rollback; recuperación; TOCTOU; symlink; hardlink; contención de locks; corrupción de snapshot; rechazo por Xray antes de publicar.

## 5. Límites y estado

- Todas las operaciones usan perfiles, leases, certificados, claves, binario y servicio sintéticos/temporales.
- No se modificó configuración real, no se usó clave maestra ni almacenes reales.
- No se llamó systemd ni se reinició/arrancó Xray.
- No se tocaron firewall, puertos, red, dependencias, VPS de pruebas, `main` ni `Xray-Normativa/`.
- R-04 queda pendiente de auditoría/aceptación formal y autorización de publicación.
- R-05 (orquestación systemd simulada) sigue pendiente. R-06/live y prueba NetMod no están autorizadas.
