# Auditoría técnica C-05D — Historial y comparación

**Fecha:** 2026-11-04
**Estado:** IMPLEMENTADA Y VERIFICADA LOCALMENTE; pendiente de aceptación formal. NO publicada ni sincronizada.
**Rama:** `design/user-identity-association-v1`
**HEAD base:** `670e6ab371e620a8cb8b51f9431746f0a2270cda`

## Alcance auditado

Servicio read-only sobre el almacén append-only C-05B. Comparación modalidad A: misma configuración; revisiones distintas permitidas. No incluye C-05E, C-05F ni publicación.

## Archivos añadidos

- `scripts/xray_validation_history.py`
- `tests/test_xray_validation_history.py`
- `docs/IMPLEMENTACION_C05D_HISTORIAL_COMPARACION_2026-11-04.md`
- `docs/AUDITORIA_C05D_HISTORIAL_COMPARACION_2026-11-04.md`

No se modificaron los módulos de persistencia C-05B ni el esquema de informes/catálogo.

## Matriz focal H01–H38

| Grupo | Casos | Resultado |
|---|---|---|
| Historial, filtros y paginación | H01–H13 | PASS |
| Detalle, informes y diagnósticos | H14–H18 | PASS |
| Comparación de informes | H19–H28 | PASS |
| Validación de entradas e integridad | H29–H33 | PASS |
| WAL, concurrencia, saneamiento y solo lectura | H34–H38 | PASS |

**C-05D focal: 38/38 PASS.**

## Regresión

- C-05A/B/C/D, descubrimiento Python completo: **76/76 PASS**.
- Suites shell existentes: **56/56 scripts PASS**.
- `python3 -m py_compile scripts/*.py tests/test_*.py`: PASS.
- `bash -n` para todos los archivos `.sh`: PASS.
- `./install.sh --check`: PASS; comprobó dependencias y no modificó el sistema.
- `shellcheck -S error scripts/*.sh modules/*.sh tests/*.sh`: PASS.
- `shellcheck -S warning` no queda limpio: reporta cuatro advertencias preexistentes en `tests/stage1_header.sh` (SC2034, dos asignaciones), `tests/uninstall.sh` (SC2154) y `tests/vless_backup_restore.sh` (SC2174). No se alteraron esos archivos porque están fuera del alcance C-05D.
- `git diff --check`: PASS.

## Revisión técnica

- El servicio consulta el almacén C-05B bajo su lock y aprovecha recuperación WAL y verificación SHA-256 ya implementadas.
- El listado verifica integridad del catálogo y de los informes antes de filtrar y paginar.
- Las fechas se interpretan como ISO-8601 con zona horaria obligatoria y se normalizan a UTC. Las fechas inválidas no se reparan ni mutan.
- Los informes permanecen consultables sin consultar el almacén de configuraciones.
- La comparación rechaza IDs inválidos, informes inexistentes y configuraciones distintas; permite revisiones distintas del mismo `config_id`.
- La comparación identifica resultado, hash/tamaño, metadatos Xray, checks agregados/eliminados y cambios de estado, errores, advertencias y detalles.
- No se descifra configuración, no se accede a claves, no se ejecuta Xray y no se aplica configuración.
- Prueba de solo lectura compara bytes de archivos del almacén antes/después de consultar.
- Prueba WAL inyecta SIGKILL tras publicar catálogo con journal aún preparado; la consulta recupera y revierte el estado de forma consistente.
- No se cambió esquema ni código de C-05A/B/C.

## Observaciones y límites

- El almacén C-05B verifica todos los informes en cada consulta, conforme a su contrato de integridad. El servicio evita invocar `get_report()` una vez por elemento del listado; carga los informes verificados dentro de una única sección bloqueada.
- El detalle reutiliza el método verificado C-05B. La comparación lee cada uno de sus dos informes por ese método, sin escritura.
- Los avisos ShellCheck de severidad warning enumerados arriba son deuda preexistente fuera de alcance; la severidad error está limpia.
- C-05E (menú Bash) y C-05F (auditoría integral) no se implementaron.
- No hay aceptación formal todavía. La fase no debe declararse cerrada hasta decisión del propietario.

## Protección del entorno y Git

- Rama de trabajo: `design/user-identity-association-v1`.
- HEAD sigue en el commit base `670e6ab371e620a8cb8b51f9431746f0a2270cda`; no se creó commit ni push.
- `main` no se modificó.
- `Xray-Normativa/` no se modificó; SHA-256 de la normativa Etapa 5 coincide con la copia canónica en `/root/Xray_Manager_Documentacion_Final_2026-10-31`.
- No se leyó ni utilizó `/etc/xray-manager/keys/master.key`.
- Pruebas con almacenes temporales y claves sintéticas.
- No se tocaron almacenes live, runtime, servicio, dependencias, certificados desplegados, firewall, puertos, red ni VPS `Vps de Pruebas`.

## Estado administrativo

**C-05D: IMPLEMENTADA, VERIFICADA Y AUDITADA LOCALMENTE; PENDIENTE DE ACEPTACIÓN FORMAL; NO PUBLICADA.**
C-05E y C-05F siguen bloqueadas por autorización independiente. Etapa 5 y Etapa 2 permanecen ABIERTAS.

## Aceptación formal

El propietario aceptó formalmente C-05D el 2026-11-04 y autorizó crear el commit y hacer push exclusivamente a `design/user-identity-association-v1`. La aceptación se limita al alcance auditado en este expediente. C-05E y C-05F no quedan autorizadas.
