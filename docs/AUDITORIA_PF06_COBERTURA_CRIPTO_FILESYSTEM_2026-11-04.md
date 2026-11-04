# Auditoría correctiva PF-06 — autenticidad criptográfica y fallos de filesystem

**Fecha:** 2026-11-04
**Host:** `Implementación-Xray`
**Ruta:** `/opt/xray-manager`
**Rama:** `design/user-identity-association-v1`
**Base:** `23d9af69898d48b3aa106fad9b60b42105185a3b`
**Alcance:** pruebas aisladas y documentación; sin cambios de código de producción.

## 1. Autorización

El propietario autorizó implementar y verificar las pruebas pendientes de PF-06, sin modificar el comportamiento funcional del almacén ni tocar runtime. Se trabajó exclusivamente en la VPS de desarrollo y en la rama autorizada.

## 2. Pruebas añadidas

### 2.1 Autenticidad AES-256-GCM

La prueba crea un perfil en almacén temporal con clave sintética, altera un byte del ciphertext y recalcula en el manifiesto tanto `stored_size_bytes` como `ciphertext_sha256`. Esto hace que la lectura supere intencionalmente el control de hash y llegue a `AESGCM.decrypt()`. La lectura debe fallar con `ProfileError` de autenticación/descifrado. Después se restauran exactamente el blob y el manifiesto y se verifica la lectura del plaintext original.

### 2.2 Fallos de filesystem

- `os.write`: escritura parcial seguida de `OSError`; el destino anterior permanece intacto y el temporal de la operación se limpia.
- `fsync` de archivo: error antes de `replace`; el destino previo se conserva y no queda temporal privado.
- `os.replace`: ya cubierto por una prueba existente; el destino no se modifica cuando el reemplazo falla.
- `fsync` de directorio: ya cubierto por una prueba existente; tras publicar, el destino queda publicado y no se elimina por error de sincronización.
- `Path.unlink` del WAL: falla una vez después de reemplazar los destinos; el camino de recuperación restaura el estado anterior, elimina el journal y permite una consulta coherente.
- Crash recovery: continúan las pruebas de SIGKILL entre reemplazos, después de reemplazar ambos destinos y durante el rollback, con recuperación posterior idempotente.

## 3. Resultados

- `bash -n tests/xray_profiles.sh`: PASS.
- `bash tests/xray_profiles.sh`: PASS, incluidos los nuevos casos PF-06.
- Regresión `tests/*.sh`: **51/51 PASS**, exit code 0.
- No se modificó `scripts/xray_profiles.py` ni código de producción.

## 4. Archivos modificados

- `tests/xray_profiles.sh` — nuevas pruebas PF-06.
- `docs/AUDITORIA_FORMAL_PERFILES_V1_1_2026-11-03.md` — estado PF-06 actualizado con alcance y límites.
- `docs/DISENO_IMPLEMENTACION_PERFILES.md` — sección 17.
- `docs/AUDITORIA_PF06_COBERTURA_CRIPTO_FILESYSTEM_2026-11-04.md` — este informe.
- `PROJECT_STATE.md`, `docs/PUNTO_CONTROL_ACTUAL.md`, `docs/CONTINUIDAD_DEL_PROYECTO.md` y `HISTORY.md` — continuidad.

## 5. Límites y restricciones

Todas las pruebas usaron almacenes temporales y claves sintéticas. No se leyó ni utilizó `/etc/xray-manager/keys/master.key`; no se creó ni modificó `/var/lib/xray-manager/profiles`; no se creó perfil live; no se modificaron runtime, systemd, certificados, firewall, puertos o red. No se accedió ni modificó `Vps de Pruebas`. `Xray-Normativa/` y `main` no se modificaron. No se instalaron ni actualizaron dependencias.

La cobertura no es una enumeración exhaustiva de todas las combinaciones de fallos, ni simula fallos físicos del dispositivo/kernel o un filesystem que incumpla garantías de durabilidad. PF-06 se considera cerrado únicamente dentro de los escenarios de prueba enumerados.

## 6. Estado

PF-06 queda **CERRADO DENTRO DEL ALCANCE PROBADO**. Esto no equivale a aceptación formal del almacén v1.1 ni a cierre de Etapa 5 o Etapa 2. No se creó commit, no se hizo push ni sincronización; requieren autorización expresa independiente.
