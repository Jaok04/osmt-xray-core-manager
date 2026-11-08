# Extracción del núcleo de staging TLS — L2 (2026-11-08)

**Estado:** IMPLEMENTACIÓN PARCIAL DE L2; núcleo puro reutilizable, envoltura R-02 fixture conservada; no existe todavía una envoltura live.
**Rama:** `design/user-identity-association-v1`
**Objetivo:** preparar la configuración final del primer VLESS + WS + TLS sin duplicar reglas de asociación ni debilitar R-02.

## 1. Cambio implementado

Se añadió `scripts/xray_runtime_staging_core.py`, módulo deliberadamente puro que no accede al filesystem, no resuelve certificados, no crea leases y no ejecuta Xray.

Expone dos operaciones:

- `validate_profile_bindings(document, bindings)`: valida tags, unicidad, cobertura exacta de todos los inbounds TLS y ausencia de certificados/rutas previamente embebidos. Devuelve el índice de inbounds TLS por tag.
- `inject_tls_lease(document, inbound_tag, connection_id, certificate_id, protocol, lease)`: comprueba que el lease preparado corresponda exactamente a la conexión, certificado y protocolo solicitados, valida ID y rutas absolutas, y sólo entonces inyecta `certificateFile` y `keyFile`.

La validación del lease es deliberadamente redundante con el resolutor: no basta con que un lease esté preparado; debe corresponder a la asociación concreta que se está componiendo.

## 2. Integración R-02

`scripts/xray_runtime_staging.py` reutiliza ahora el núcleo para validar las asociaciones y aplicar las rutas del lease. Se conserva sin cambios el perímetro fixture de R-02:

- marcador obligatorio `.xray-manager-r02-fixture`;
- todas las rutas de datos y almacenes confinadas a `fixture_root`;
- marcador independiente para el árbol de leases;
- perfil y mapping privados, validación R-01 y comprobación TOCTOU;
- validación nativa de Xray bajo la identidad no privilegiada suministrada;
- limpieza compensatoria de staging y leases si la operación falla.

No se cambió el esquema ni el CLI de R-02. No se habilitó ninguna ruta de producción.

## 3. Pruebas y validación

Se añadió `tests/test_xray_runtime_staging_core.py` con pruebas para cobertura exacta, bindings faltantes/extra, tags y conexiones duplicadas, certificados preexistentes, lease correcto, mismatch de conexión/certificado/protocolo, ID malformado y rutas relativas.

Ejecución canónica:

```bash
PYTHONPATH=.:scripts python3 -m unittest discover -s tests -p 'test_*.py'
```

Resultado final después de integrar el núcleo: **497 pruebas Python PASS**. Las 62 pruebas Bash pasan. También pasan `compileall`, `py_compile`, `bash -n`, ShellCheck global con `-S error`, `install.sh --check` y `git diff --check`.

## 4. Límites explícitos

Este cambio **no completa L2**. No existe aún `stage_live`; tampoco se ha separado una envoltura de staging con rutas reales. El núcleo puro es la pieza compartida que permite construirla sin copiar ni divergir las reglas de perfil/mapping/lease.

No se han leído claves maestras reales ni material privado de certificados. No se ha creado un lease productivo. No se han modificado `/etc/xray`, `/var/lib/xray-manager`, systemd, cuentas, permisos del sistema, DNS, firewall o puertos. No se ha ejecutado Certbot/ACME, ni Xray live, ni se ha tocado VPS Pruebas.

## 5. Siguiente paso

Diseñar y probar una envoltura `stage_live` separada que reutilice este núcleo, R-01, el mapping I-01/I-02 y el resolutor central. Debe tener rutas/locks/identidad de servicio explícitos, no depender de variables de entorno para cambiar de fixture a live y no exponerse al menú hasta superar auditoría independiente H6-G3 y las puertas de autorización correspondientes.

La prioridad no cambia: el primer VLESS + WS + TLS en `pruebas.tvrc.me:443`. No ampliar el alcance a VMess, renovación automática ni funciones avanzadas como parte de esta tarea.
