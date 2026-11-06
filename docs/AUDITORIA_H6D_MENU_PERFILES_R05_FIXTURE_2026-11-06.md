# Auditoría H6-D — menú de perfiles y puente R-05 fixture

**Fecha:** 2026-11-06
**Resultado:** PASS CON LIMITACIONES — solo fixture/mock.

## Hallazgos verificados

1. La opción [4] del menú Etapa 5 enruta al flujo de perfiles; Gestión de perfiles expone el mismo flujo en [11].
2. El flujo exige revisión exacta y estado `valid`; no trata selección ni guardado como aplicación.
3. El puente valida el marcador R-02 y confina rutas a la raíz fixture antes de invocar el orquestador.
4. El backend se pasa explícitamente como `xray_runtime_service_adapter`; no hay selector de backend real.
5. La operación requiere confirmaciones y reporta `execution_scope=fixture_only`, `real_systemd_invoked=false`, `real_xray_modified=false`.
6. El modo normal queda bloqueado antes de invocar el puente.
7. No se duplica el menú/controlador de servicio existente.

## Pruebas focales

- Puente Python: 4/4 PASS.
- Menú Bash: PASS.
- Regresión Python global: 280/280 PASS.

## Límites

Las pruebas del puente simulan la llamada al orquestador para verificar el contrato; la prueba Bash verifica el bloqueo normal y el enrutamiento. No demuestran un despliegue live. El puente no conecta H6-A ni invoca systemd real. La opción no puede usarse en modo normal para aplicar una configuración de producción.

No se modificaron `main` ni `Xray-Normativa/`. No se ejecutaron acciones live, ni se tocaron runtime, certificados, DNS, firewall, puertos, red o dependencias.

**Dictamen:** H6-D aceptada técnicamente en alcance fixture-only. La habilitación live exige diseño, auditoría y autorización específica independientes.
