# Implementación H6-D — puente del menú de perfiles a R-05 fixture

**Fecha:** 2026-11-06
**Estado:** implementada y verificada en alcance fixture-only; PASS CON LIMITACIONES.
**Rama:** `design/user-identity-association-v1`

## 1. Objetivo y contraste normativo

Conectar la opción «Cambiar perfil activo» de Etapa 5 con la orquestación R-05 existente, sin duplicar el controlador de servicio de `modules/xray_service.sh` ni habilitar operaciones live.

Contraste normativo:
- Etapa 5 §5 y §7: distinguir Borrador/Validada/Aplicada/Anterior; exigir revisión exacta validada; confirmar; verificar antes de actualizar el registro activo. Seleccionar/guardar no equivale a activar.
- Etapa 6 §2: gestión general del servicio permanece en el menú `modules/xray_service.sh`; el flujo de perfil no crea un segundo controlador.
- Delimitación Etapa 5/6: activar perfil y recargar configuración son operaciones distintas.

## 2. Cambios

- Nuevo `scripts/xray_runtime_menu_bridge.py` como puente restringido a R-05 fixture.
- El puente exige root, marcador R-02 exacto, rutas absolutas sin symlinks y confinamiento de todas las rutas de operación dentro de `XRAY_RUNTIME_FIXTURE_ROOT`.
- Inyecta explícitamente `xray_runtime_service_adapter` (backend fixture predeterminado). No acepta backend externo, `systemctl`, shell ni selector de backend real.
- Modificado `modules/profiles.sh`: la opción [4] del menú Etapa 5 y la opción [11] de Gestión de perfiles llevan al mismo flujo controlado.
- El flujo selecciona perfil y revisión exactos, exige estado de validación `valid`, pide confirmación explícita para la transición simulada y presenta el resultado con alcance `fixture_only`.
- En modo normal (`XRAY_RUNTIME_MENU_FIXTURE_MODE` distinto de `1`) la opción queda bloqueada y explica que no existe aplicación real habilitada.
- El servicio general sigue bajo `modules/xray_service.sh`; no se duplica start/stop/restart/enable/disable.

## 3. Variables de entorno para pruebas

La activación del puente requiere `XRAY_RUNTIME_MENU_FIXTURE_MODE=1` y configuración explícita de las rutas fixture `XRAY_RUNTIME_*`. Las rutas incluyen almacén de perfiles/clave/validaciones, binario Xray fixture, estado y binding fixture, staging/leases, catálogos de conexiones/certificados, service-root, operation-store, locks, adapter-root y almacén activo B4 fixture. El puente rechaza cualquier ruta fuera de la raíz marcada. El almacén activo B4 fixture es obligatorio en el puente y queda confinado a la misma raíz.

No se crean fixtures automáticamente ni se deducen rutas de producción. Sin la configuración completa, el flujo falla cerrado.

## 4. Pruebas

- `tests/test_xray_runtime_menu_bridge.py`: 4/4 PASS (backend fixture explícito, rechazo de rutas externas, rechazo de marcador no reconocido y almacén activo obligatorio).
- `tests/profiles_runtime_menu.sh`: PASS (bloqueo por defecto y enrutamiento de opción [4]).
- Regresión Python global al implementar: 280/280 PASS.
- La integración R-05 completa depende de los fixtures de staging, publicación y servicio ya probados en sus suites; este bloque añade pruebas del contrato y enrutamiento del puente.

## 5. Límites y dictamen

- No se conectó el adaptador systemd H6-A al puente.
- No se habilitó backend real ni operación mutadora real.
- No se ejecutó `systemctl`, no se escribió `/etc/xray/config.json`, no se inició/reinició Xray real.
- No se modificaron certificados desplegados, DNS, firewall, puertos, red ni dependencias.
- La opción del menú solo ejecuta R-05 cuando se configura explícitamente un fixture válido; en instalación normal permanece deshabilitada.
- Los resultados del fixture no constituyen estado Aplicada en un servidor real ni prueba de conectividad externa.

H6-D queda IMPLEMENTADA Y VERIFICADA en el alcance autorizado, PASS CON LIMITACIONES. H6 live permanece NO AUTORIZADA. No se cierra Etapa 5 ni se afirma el primer servicio real VLESS-WS-TLS.
