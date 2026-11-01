# Procedimiento seguro de transición del registro de usuarios a v2

**Estado:** herramienta implementada; pruebas aisladas aprobadas; dry-run real ejecutado sin aplicar cambios.  
**Fecha de última verificación:** 2026-11-01

## 1. Objetivo

Migrar `/var/lib/xray-manager/users/users.json` desde el arreglo legacy al documento v2 de identidades y asociaciones, con validación, respaldo verificable, bloqueo compartido, sustitución atómica y rollback condicionado.

Este procedimiento no integra el módulo v2 al menú ni al runtime Xray. Tampoco activa, suspende ni revoca conexiones en el runtime.

## 2. Archivos implicados

- Herramienta: `/opt/xray-manager/scripts/users_v2_cutover.py`
- Pruebas aisladas: `/opt/xray-manager/tests/users_v2_cutover.sh`
- Modelo/validador: `/opt/xray-manager/modules/users_v2.sh`
- Sustitución JSON atómica: `/opt/xray-manager/lib/json_store.sh`
- Usuarios: `/var/lib/xray-manager/users/users.json`
- Conexiones: `/var/lib/xray-manager/connections/connections.json`
- Bloqueo compartido: `/run/xray-manager/integrity.lock`
- Backups: `/var/backups/xray-manager/identity-cutover/`

## 3. Reglas de seguridad

1. La herramienta exige que ambos archivos JSON sean archivos regulares, no enlaces simbólicos.
2. Exige que el registro de usuarios siga siendo un arreglo legacy y que conexiones sea un arreglo JSON válido.
3. No infiere el estado funcional. El operador debe elegir explícitamente `active`, `suspended` o `expired`.
4. La migración conserva el carácter no provisionado de los registros legacy: cada asociación queda con `provisioning_status=draft` y `runtime.status=not_applied`. Elegir estado funcional `active` no instala ni habilita un cliente en Xray.
5. El candidato se valida con `users_v2_validate_file`, incluidas las referencias a conexiones, unicidad de credenciales y límites de capacidad.
6. Dry-run y aplicación usan el mismo bloqueo exclusivo que el gestor.
7. La aplicación crea copias de usuarios y conexiones, verifica SHA-256 y registra un manifest.
8. El reemplazo del archivo de usuarios es atómico y conserva permisos `0600`.
9. Rollback acepta un manifest en estado `prepared` o `applied`, pero solo si el registro actual conserva exactamente el hash v2 del cutover y el catálogo de conexiones conserva el hash de la instantánea. Esto permite recuperarse si el proceso se interrumpe justo después del reemplazo atómico y antes de marcar el manifest como aplicado, sin sobrescribir cambios posteriores.
10. El rollback verifica el hash del backup antes de restaurar.
11. No se debe ejecutar sobre datos reales sin revisión y autorización explícita.

## 4. Dry-run

Ejecutar como root:

```bash
/opt/xray-manager/scripts/users_v2_cutover.py --dry-run --state active
```

Elegir `active`, `suspended` o `expired` según la decisión administrativa. No seleccionar automáticamente un estado por el hecho de que los registros legacy estén en `draft`.

El dry-run:
- crea un candidato temporal en el directorio de usuarios;
- ejecuta la migración y el validador v2;
- muestra hashes, conteos y el token para aplicar;
- elimina el candidato al terminar;
- no reemplaza `users.json` ni crea backup permanente.

Los UUID de identidad y asociación se generan aleatoriamente; por eso el hash del candidato puede variar entre dry-run y aplicación. El token de aplicación se basa en el hash del archivo legacy, no en el hash del candidato.

## 5. Aplicación — requiere autorización explícita

Solo después de revisar el resultado del dry-run y confirmar el estado funcional elegido:

```bash
/opt/xray-manager/scripts/users_v2_cutover.py --apply --state active --confirm 'APPLY-USERS-V2-<hash12>'
```

Sustituir `<hash12>` por el token exacto entregado por el dry-run. El token queda vinculado al SHA-256 del archivo legacy. Si cualquiera de los dos archivos de entrada cambia, hay que repetir el dry-run.

La herramienta guarda:
- `users.legacy.json`
- `connections.snapshot.json`
- `manifest.json` con hashes, conteos, estado funcional y estado de aplicación.

El directorio de backup tiene permisos restrictivos y está dentro de `/var/backups/xray-manager/identity-cutover/`.

## 6. Consultar y ejecutar rollback

Consultar el token de rollback:

```bash
/opt/xray-manager/scripts/users_v2_cutover.py --rollback /var/backups/xray-manager/identity-cutover/<directorio-backup>
```

La herramienta muestra un token `ROLLBACK-USERS-V2-<hash12>`. También permite recuperar un cutover interrumpido después del reemplazo, cuando el manifest quedó en estado `prepared`; los hashes actuales deben coincidir igualmente. Para confirmar:

```bash
/opt/xray-manager/scripts/users_v2_cutover.py --rollback /var/backups/xray-manager/identity-cutover/<directorio-backup> --confirm 'ROLLBACK-USERS-V2-<hash12>'
```

Si `users.json` o `connections.json` cambiaron desde el cutover, el rollback se detiene para evitar pérdida de datos. En ese caso se requiere análisis manual; no se debe forzar el reemplazo.

## 7. Pruebas realizadas

`tests/users_v2_cutover.sh` ejecuta el flujo en un directorio temporal separado:
- dry-run sin modificación del archivo legacy;
- aplicación y validación del documento v2;
- rollback y verificación del hash legacy restaurado;
- rechazo de rollback si el archivo actual cambió;
- rechazo de migración que excede la capacidad configurada.

La prueba crea sus propios archivos de usuarios, conexiones, bloqueo y backups mediante variables de entorno de test. No usa los datos reales de `/var/lib/xray-manager`.

## 8. Estado verificado

- Herramienta implementada en la VPS.
- Pruebas de fixtures aprobadas.
- Dry-run contra los archivos reales ejecutado el 2026-11-01 con `--state active`: 0 registros legacy, 0 identidades y 0 asociaciones propuestas.
- Hash de `users.json` antes y después: `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570`.
- Hash de `connections.json`: `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570`.
- Los dos archivos reales permanecen como arreglos vacíos `[]`; no se reemplazaron ni migraron.
- No se creó backup permanente porque no hubo aplicación.
- No se ha integrado `users_v2.sh` al ejecutable principal.
- No se ha conectado el modelo v2 con el runtime ni se ha programado el barrido de vencimientos.
- Servicio Xray permanece inactivo.

**Próximo paso:** revisar el procedimiento y la implementación en la rama de desarrollo. La aplicación real sigue requiriendo aprobación separada y explícita.
