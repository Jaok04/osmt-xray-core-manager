# Implementación H6-A — adaptador systemd de observación

**Fecha:** 2026-11-05
**Estado:** IMPLEMENTADO EN CÓDIGO — PRUEBAS AISLADAS PASS
**Alcance:** sólo observación read-only mediante contrato systemd simulado.

## 1. Cambios

- Nuevo `scripts/xray_runtime_systemd_adapter.py`.
- Nuevo `tests/test_xray_runtime_systemd_adapter.py`.
- Se conserva `scripts/xray_runtime_service_adapter.py` como adaptador fixture R-05/B4.
- No se cambia la interfaz de la orquestación R-05 ni se conecta el adaptador nuevo al menú.
- El menú de servicio existente continúa siendo la interfaz general y reutiliza `modules/xray_service.sh`.

## 2. Contrato implementado

El adaptador consulta exclusivamente `xray.service` mediante `systemctl show` con propiedades allowlist, argumentos separados, entorno mínimo y timeout de ocho segundos. No usa shell ni acepta nombres de unidad arbitrarios.

Comprueba la unidad local administrada, tipo/propietario/permisos/enlaces y directivas críticas. Consulta LoadState, ActiveState, SubState, Result, ExecMainStatus, PID, marcas de tiempo, InvocationID, FragmentPath, User, Group y UnitFileState.

Si existe una configuración runtime regular y segura, calcula su SHA-256 por descriptor abierto con O_NOFOLLOW. El campo se denomina `runtime_config_sha256`: no se presenta como hash cargado por el proceso.

El resultado deja expresamente:
- `loaded_generation_id = null`
- `loaded_config_sha256 = null`
- `generation_evidence = not_attested`
- `read_only = true`

No hay métodos start/restart/stop/enable/disable. El módulo no realiza acciones mutadoras.

## 3. Pruebas

11 pruebas focales:
- observación read-only y ausencia de inferencia de generación;
- configuración ausente;
- unidad no administrada;
- symlink y permisos inseguros;
- FragmentPath divergente;
- identidad de servicio incorrecta;
- InvocationID y PID inválidos;
- configuración symlink y hardlink.

Todas las llamadas a systemd en las pruebas se sustituyen por mocks. No se invocó systemctl real.

## 4. Límites

No se conecta aún a R-05, al almacén activo B4 ni a los menús. No escribe runtime, no modifica unidades, no inicia/reinicia Xray y no lee almacenes/secretos reales. H6-A no acredita generación aplicada ni servicio live.
