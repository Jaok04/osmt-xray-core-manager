# Diseño técnico R-05 — orquestación systemd simulada

**Fecha:** 2026-11-04
**Estado:** PROPUESTA TÉCNICA PARA REVISIÓN DEL PROPIETARIO — NO AUTORIZA IMPLEMENTACIÓN
**Dependencias:** R-01 preflight; R-02 staging/leases TLS; R-03 snapshot/journal; R-04 publicación atómica/rollback.
**Identidad obligatoria:** `profile_id + revision`.
**Entorno previsto:** fixtures desechables, datos sintéticos, mocks y adaptadores simulados en la VPS de desarrollo.

## 1. Objetivo

Definir la orquestación de extremo a extremo del flujo runtime preparado por R-01–R-04, incorporando un adaptador de servicio simulado que permita probar reinicio, consulta de estado, errores, timeouts y recuperación sin invocar systemd real ni iniciar/reiniciar Xray real. R-05 debe demostrar coherencia entre publicación de configuración, estado simulado, journal y resultado final. No demuestra carga real del servicio ni conectividad extremo a extremo.

## 2. Contraste normativo y límites

### 2.1 Etapa 5 — Configuraciones y perfiles

Contraste con `Xray-Normativa/05_Configuraciones_Perfiles/Etapa_5_Configuraciones_Perfiles.md`:
- §3.1: no usar configuraciones independientes como vía alternativa de activación; identidad exacta de perfil y revisión.
- §4.1 y §5: validación estática obligatoria y estados diferenciados; validar/guardar/seleccionar no equivale a aplicar.
- §7: exigir revisión válida, confirmación, aplicación y verificación; actualizar registro activo solo después de verificar; ante fallo intentar restauración e informar si también falla.
- §10.5–10.6: no presentar como validado un estado no verificado; informar fallos y rollbacks con precisión.

### 2.2 Etapa 6 — Servicio

`Xray-Normativa/06_Servicio_Diagnostico/Etapa_6_Servicio_Diagnostico.md` §2 describe operaciones reales del servicio. R-05 solo modela estados y resultados en un adaptador falso; no implementa ni ejecuta esas operaciones, ni sustituye el futuro módulo de gestión de servicio.

### 2.3 Decisiones técnicas aprobadas

- Estrategia inicial de aplicación: `systemctl restart xray.service`; no asumir hot reload.
- Capturar estado previo active/inactive/failed.
- No habilitar/deshabilitar el servicio como efecto lateral.
- Rollback atómico de configuración y recuperación del estado previo.
- Si estaba inactivo, no arrancarlo durante la restauración.
- Si no existe configuración previa y la recuperación no es segura, detenerse y requerir intervención.
- R-01–R-05 solo en entornos aislados; R-06/live requiere autorización nueva y específica.

La estrategia restart es una decisión de diseño; el adaptador R-05 no ejecutará el comando real.

## 3. Alcance propuesto

1. Orquestador que reutilice contratos de preflight, staging, journal y publisher; no duplicar su lógica.
2. Adaptador simulado inyectable con `status` y `restart` para el camino principal. No introducir arranque automático en recuperación.
3. Estados `active`, `inactive`, `failed`, `unknown`.
4. Registro de intención/resultado en journal existente o extensión compatible, con transiciones explícitas e idempotentes.
5. Fallos inyectables: rechazo de restart, estado posterior incorrecto, timeout, pérdida de respuesta, excepción y caída entre publicación y confirmación.
6. Rollback coordinado con R-04 y restauración del estado simulado previo.
7. Pruebas de locks, concurrencia y aislamiento.

No incluye systemd real, daemon real, conectividad externa, UI adicional ni cambios de esquema no aprobados.

## 4. Flujo propuesto

### 4.1 Éxito

1. Recibir `profile_id` y `revision` explícitos; rechazar identidad ambigua.
2. Adquirir locks compartidos según R-03.
3. Ejecutar preflight R-01 para la revisión exacta.
4. Preparar staging R-02 y validar configuración/leases.
5. Crear snapshot/journal R-03.
6. Publicar atómicamente mediante R-04 dentro del fixture.
7. Consultar y registrar estado previo en el adaptador.
8. Solicitar `restart` simulado.
9. Consultar estado posterior y exigir `active` más revisión/hash esperados; respuesta positiva de restart por sí sola no basta.
10. Registrar verificación y finalizar; no marcar como aplicada si falta evidencia.
11. Liberar locks/leases conforme al ciclo existente; no borrar leases referenciados.

### 4.2 Fallo

1. Registrar fallo y preservar evidencia.
2. Ejecutar rollback R-04, validando snapshot y evitando sobrescritura TOCTOU.
3. Reconciliar estado simulado previo:
   - `active`: simular recuperación y verificar `active`.
   - `inactive`: no emitir `start`; mantener `inactive`.
   - `failed`: no promover silenciosamente a `active`; conservar `failed` o marcar `recovery_required` si no puede demostrarse equivalencia.
   - `unknown`: fail-closed; no asumir estado ni arrancar.
4. Registrar por separado rollback de configuración y restauración de servicio.
5. Si cualquiera falla, dejar `recovery_required` y explicar qué se restauró y qué no.

Esto es una simulación determinista, no una garantía sobre systemd real.

## 5. Contrato del adaptador

- Inyectable por dependencia; el orquestador no ejecuta shell/systemctl.
- Estado fixture privado, marcado y fuera de rutas operativas.
- Resultados estructurados para `status`/`restart`: código, estado observado y detalle no sensible.
- Secuencias de respuestas/fallos deterministas.
- Timeout simulado sin procesos reales en segundo plano.
- Registro auditable de invocaciones.
- Unidad lógica fija `xray.service`; rechazar cualquier otra.
- Sin comandos arbitrarios, shell fragments, rutas de binarios ni argumentos libres.
- Sin PATH lookup, subprocess, D-Bus ni APIs systemd del host.

La API concreta queda para el diseño de implementación posterior a la aprobación.

## 6. Estados propuestos

`prepared`, `snapshot_saved`, `published`, `service_restart_requested`, `service_verified`, `rollback_started`, `rolled_back`, `recovery_required`, `completed`. No reutilizar estados con semánticas distintas. Cualquier extensión del journal debe preservar lectura/recuperación de journals R-03/R-04 y documentar compatibilidad hacia atrás.

## 7. Matriz mínima de pruebas

| ID | Escenario | Resultado exigido |
|---|---|---|
| R5-01 | Éxito con previo active | Publicación fixture, restart mock, active verificado, completed |
| R5-02 | Previo inactive | No arrancar durante rollback; no afirmar aplicación activa sin evidencia |
| R5-03 | Restart rechazado | Rollback exacto y estado previo reconciliado |
| R5-04 | Restart exitoso, status no active | No declarar aplicado; rollback |
| R5-05 | Timeout ambiguo | Consultar mock; no asumir éxito |
| R5-06 | Pérdida de respuesta tras transición | Recovery idempotente |
| R5-07 | Previo failed | No promover a active silenciosamente |
| R5-08 | Previo unknown | Fail-closed |
| R5-09 | Caída tras publicar antes de restart | Detectar publicación pendiente |
| R5-10 | Caída tras restart antes del journal final | Reconciliar mock; no repetir a ciegas |
| R5-11 | Falla rollback de config | recovery_required y snapshot preservado |
| R5-12 | Falla restauración de servicio | recovery_required, resultados separados |
| R5-13 | Lock ocupado | Abort temprano sin publicación |
| R5-14 | Cambio externo/TOCTOU | No sobrescribir |
| R5-15 | Identidad/hash incorrectos | Rechazo antes de restart |
| R5-16 | Aislamiento | Escrituras solo bajo fixture marcado |
| R5-17 | Auditoría de invocaciones | Cero llamadas reales y cero subprocess de servicio |
| R5-18 | Recovery repetido | Segunda ejecución no altera estado reconciliado |

Matriz propuesta; no existen resultados PASS de R-05.

## 8. Seguridad y aislamiento

- Exigir marcadores de `XRAY_SERVICE_ROOT`, `operation_store`, `lease_root` y fixture del adaptador.
- Rechazar symlinks, hardlinks, ancestros inseguros y rutas externas al fixture.
- Usar datos sintéticos y solo binario Xray existente con hash fijado; no instalar/actualizar nada.
- No leer `/etc/xray-manager/keys/master.key`.
- No acceder a almacenes reales, certificados desplegados ni config real.
- No invocar `systemctl`, `service`, `journalctl`, D-Bus ni APIs systemd del host.
- No iniciar Xray real, abrir puertos ni tocar firewall/red/DNS.
- No modificar dependencias, `main`, `Xray-Normativa/` ni VPS de pruebas.
- Demostrar aislamiento por rutas y ausencia de invocaciones externas.

## 9. Auditoría y aceptación técnica

La auditoría verificará trazabilidad normativa; reutilización R-01–R-04; máquina de estados crash-safe; integridad/compatibilidad del journal; timeouts y resultados ambiguos; rollback exacto; ausencia de falsos positivos; locks/TOCTOU; aislamiento; pruebas focales y regresión; matriz requisito→diseño→código→prueba→evidencia. Documentará que no es prueba live ni demuestra conectividad o comportamiento real de systemd. La aceptación formal corresponde al propietario y R-05 no cierra Etapa 5 por sí sola.

## 10. Decisiones pendientes antes de implementar

1. Estado previo `failed`: ¿mantenerlo `failed` tras rollback o marcar `recovery_required` si no puede demostrarse restauración equivalente? La propuesta no intenta arrancarlo.
2. Estado previo `inactive`: ¿el camino exitoso también debe evitar reiniciar/arrancar y, por tanto, no declarar aplicada una revisión activa? La decisión existente especifica no arrancar durante restauración, pero no fija este caso de éxito.
3. ¿La verificación simulada exige `active` más revisión/hash o también token/nonce de generación para descartar estado stale? Se recomienda token.
4. ¿Se permite extender el journal con campos/estados versionados compatibles hacia atrás o se requiere registro separado?

No inferir respuestas; resolverlas antes de implementar.

## 11. Estado y autorización

R-01–R-04 están implementadas, verificadas/auditadas, publicadas y sincronizadas; aceptación formal individual pendiente. R-05 está en diseño, NO INICIADA y sin pruebas. R-06/live NO AUTORIZADA. Este documento no autoriza código, systemd real ni cambios de infraestructura; requiere aprobación expresa.
