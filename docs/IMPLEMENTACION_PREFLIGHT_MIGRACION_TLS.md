# Implementación del preflight de migración TLS histórica

**Fecha:** 2026-11-03
**Estado:** PREFLIGHT IMPLEMENTADO / FIXTURES PASS / INVENTARIO LIVE SIN CANDIDATOS
**Rama:** `design/user-identity-association-v1`

## Alcance entregado

Se añadió `scripts/certificate_migration.py` con la operación:

```bash
python3 scripts/certificate_migration.py plan --protocol all
```

Permite limitar el inventario a `--protocol vless` o `--protocol vmess`.

El comando es estrictamente de solo lectura: no crea locks ni directorios, no importa certificados, no crea revisiones, no genera journals y no modifica catálogos, configuraciones o blobs.

## Controles

- Reconoce las modalidades TLS mediante los mapas `MODES` de `vless_config_store.py` y `vmess_config_store.py`.
- Valida la identidad de conexión, referencia de configuración, revisión, schema y referencia del secreto.
- Rechaza archivos ausentes, permisos inseguros, symlinks y hardlinks.
- Descifra secretos en memoria mediante el backend y AAD específicos de cada protocolo: VLESS usa `vless_crypto.decrypt_secret`; VMess usa `vmess_config_store.decrypt`.
- Comprueba PEM, correspondencia certificado/clave, vigencia temporal y fingerprints SHA-256 del certificado y clave pública.
- Agrupa por identidad criptográfica validada, permitiendo detectar pares compartidos entre VLESS y VMess.
- Clasifica cada entrada como `READY`, `BLOCKED` o `ALREADY_CENTRAL`. La clasificación central exige que el ID exista una sola vez y esté activo en el catálogo central.
- Produce hashes de entradas, grupos de deduplicación y un `plan_id` determinista sobre el contenido del plan.
- Adquiere bloqueo compartido de integridad si el archivo ya existe, sin crearlo. Revalida hashes de catálogo, configuración, blob, certificado y clave maestra antes de cerrar el plan.
- No imprime ni persiste PEM, clave privada descifrada, passphrase o clave maestra.

## Pruebas

Nuevo `tests/certificate_migration_plan.sh`:

- Fixtures sintéticos VLESS y VMess con sobres criptográficos distintos.
- Mismo certificado/par compartido entre ambos protocolos: un grupo de deduplicación.
- Comprueba que el inventario no modifica los archivos de entrada.
- Alteración de ciphertext/tag: el candidato afectado queda `BLOCKED`; el otro protocolo continúa analizándose.
- Confirma `read_only=true`, `writes_performed=false`, `automatic_migration=false` y `automatic_deletion=false`.

Verificación global ejecutada en VPS de implementación:

| Validación | Resultado |
|---|---:|
| Scripts de prueba `tests/*.sh` | 46/46 PASS |
| Sintaxis Bash | PASS |
| `python3 -m py_compile scripts/*.py` | PASS |
| ShellCheck `-S warning` de la prueba nueva | PASS |
| `git diff --check` | PASS |

## Inventario real en VPS de implementación

Ejecución de `certificate_migration.py plan --protocol all`:

- Catálogo de conexiones: 0 registros.
- Candidatos TLS históricos: 0.
- READY: 0.
- BLOCKED: 0.
- ALREADY_CENTRAL: 0.
- Grupos de deduplicación: 0.
- `writes_performed=false`.

La ruta de configuración VLESS y el catálogo persistente de certificados centrales no existen actualmente en esta VPS. No se crearon durante el preflight.

## Límites y siguientes pasos

No se implementó aún la fase escritora de migración: backup obligatorio, importación idempotente `managed`, nuevas revisiones inmutables, publicación coordinada de catálogos, journal durable, verify y rollback.

No se ejecutó migración real, backup, restore, runtime apply, reinicio, despliegue ni cambios en servicios, firewall o puertos. No se utilizó la VPS de pruebas. `Xray-Normativa/` permanece intacta.

**Siguiente paso:** completar y probar el contrato de backup/restore compartido antes de habilitar cualquier migración real; después implementar la fase escritora de migración sobre fixtures, con fallos inyectados y rollback.
