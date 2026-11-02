# Xray Core Manager — Estado del proyecto

**Corte de estado:** 2026-11-02  
**Estado global:** Etapa 1 aceptada por el propietario; Etapa 2 en desarrollo y abierta.  
**Repositorio:** https://github.com/Jaok04/xray-core-manager  
**Rama autorizada:** design/user-identity-association-v1  
**VPS de desarrollo:** /opt/xray-manager

> Este documento es una fotografía de estado, no sustituye la documentación normativa. Antes de actuar, verifica el HEAD actual de GitHub y vuelve a inspeccionar la VPS.

## 1. Referencias oficiales

- Documentación normativa: /root/Xray_Manager_Documentacion_Final_2026-10-31
- Especificación funcional Etapa 2: 02_Protocolos_Conexiones/Etapa_2_Protocolos.md y Etapa_2_Protocolos.yaml.
- Código en VPS: /opt/xray-manager
- Rama autorizada: design/user-identity-association-v1
- main: no modificar.

## 2. Estado de repositorio y VPS

### GitHub

Último commit de la rama registrado en la auditoría previa:
- SHA: cd76e84a48974762f28b666e8d440de52062d6a8
- Mensaje: docs: record stage two menu implementation
- Fecha registrada: 2026-11-02 09:55:08 UTC.

Este SHA es una referencia conocida, no una garantía de que siga siendo HEAD. Cada sesión debe consultar la referencia remota actual antes de trabajar.

### VPS

- Ruta: /opt/xray-manager
- En la inspección del 2026-11-02 no existía /opt/xray-manager/.git.
- Por ello no se puede establecer desde esa ruta branch, HEAD ni git status.
- La VPS y GitHub deben compararse por contenido/hashes; no asumir equivalencia.
- El sistema de continuidad de cinco archivos está creado en la VPS y publicado en la rama autorizada; la primera verificación encontró coincidencia exacta de texto entre ambos destinos.
- En una auditoría previa, la mayoría de los archivos comparados coincidían. modules/main_menu.sh y docs/ETAPA_2_IMPLEMENTACION_MENU_2026-11-02.md mostraron SHA distintos pese a que el texto recuperado parecía igual. La causa no quedó determinada; mantenerlos como divergencia pendiente de reconciliación hasta volver a comparar bytes.

## 3. Etapas

| Etapa | Alcance | Estado |
|---|---|---|
| Etapa 1 | Menú principal y administración del sistema | ACEPTADA por el propietario |
| Etapa 2 | Protocolos y conexiones | EN DESARROLLO; abierta |
| Etapa 3 | Gestión de usuarios, identidades y asociaciones | Hay módulos y documentación existentes; el estado formal y la cobertura de la etapa requieren auditoría específica |
| Etapas posteriores | Según documentación normativa | Pendientes |

No confundir las etapas del proyecto con las fases A/B/C del instalador o de administración de Xray.

## 4. Etapa 1 — resultado aceptado

El propietario aceptó expresamente la Etapa 1 como completada.

Evidencia documentada:
- Cotejo normativo: 47/47 comprobaciones PASS.
- Suite posterior a los últimos cambios: 20/20 scripts PASS.
- bash -n: PASS.
- ShellCheck: PASS.
- shfmt: PASS en los archivos homogéneos; tests/uninstall.sh conserva formato histórico mixto.
- ./install.sh --check: PASS.
- Validación operativa en VPS desechable Ubuntu 24.04.4 LTS.
- Instalación aislada de Xray 26.10.31, comprobaciones de permisos/unidad y pruebas de guardas, sin activar la unidad real ni alterar firewall/SSH.

Limitaciones conocidas que deben conservarse:
- U08: SSH/SCP y SHA-256 de exportación externa probados con mocks; no hubo destino remoto real ni credenciales.
- No se desinstalaron Xray ni Manager instalados en el host de pruebas.
- No se reinició la VPS para probar persistencia tras reboot.
Estas limitaciones no anulan la aceptación del propietario; deben seguir identificándose como límites de validación, no ocultarse ni convertirse automáticamente en tareas de implementación.

Documentos técnicos de evidencia:
- docs/MATRIZ_TRAZABILIDAD_ETAPA_1_REV_1_2.md
- docs/ETAPA_1_VALIDACION_PRUEBAS_2026-11-01.md
- docs/ETAPA_1_AUDITORIA_FINAL_2026-11-02.md
- docs/ETAPA_1_VALIDACION_OPERATIVA_VPS_DESECHABLE_2026-11-02.md
- docs/ETAPA_1_CONCURRENCIA_CONFIRMACIONES_2026-11-01.md

## 5. Etapa 2 — estado actual

La especificación funcional aprobada es revisión 1.3, aprobada el 30/10/2026. Define cinco familias principales (VLESS, VMess, Trojan, Shadowsocks, Hysteria2), tres opcionales (SOCKS, HTTP Proxy, WireGuard), navegación jerárquica y flujos Crear/Administrar.

### Implementado en la base actual

- Menú de familias y protocolos opcionales.
- Navegación por modalidades y selección de seguridad prevista.
- Flujo Crear / Administrar / Volver.
- Registro y administración inicial de conexiones como borradores.
- Listado, consulta de detalles, edición y eliminación confirmada de borradores.
- Catálogo config/protocols.tsv con 38 registros.
- Modelo neutral VLESS de nueve modalidades.
- Adaptador VLESS específico para Xray-core 26.10.31.
- Prueba de integración documentada para las nueve modalidades VLESS mediante xray run -test.

### Límites importantes

- Las conexiones se guardan como draft; no equivalen a conexiones activas.
- La creación/edición no aplica una configuración al runtime.
- No se abren puertos ni se modifica firewall por el flujo de conexiones.
- El adaptador VLESS no está integrado todavía en un flujo completo de usuarios reales, certificados de producción, persistencia transaccional y activación del servicio.
- La validación xray run -test no prueba conectividad extremo a extremo.
- La prueba documentada de nueve modalidades corresponde al entorno y binario Xray 26.10.31; no asumir que se reejecutó en cada sesión.

### Pruebas registradas

Se documentan resultados PASS para navegación, administración de borradores, VLESS, colisiones de puertos, carreras de concurrencia, persistencia JSON, sintaxis Bash, ShellCheck y shfmt. La auditoría del 02/11 no reejecutó todas esas pruebas; consulta los informes y repítelas cuando el cambio lo requiera.

## 6. Discrepancias normativas pendientes

No alterar la especificación aprobada sin decisión del propietario.

1. VLESS-XHTTP: el catálogo y el modelo/adaptador incluyen XHTTP sin TLS, TLS y REALITY. La especificación funcional 1.3 enumera cinco modalidades VLESS originales y no refleja explícitamente estas tres ampliaciones.
2. VMess-HTTPUpgrade-TLS: aparece en el catálogo/código, pero no está enumerado expresamente como modalidad independiente en la especificación 1.3.
3. Se requiere decisión explícita del propietario sobre conservar/formalizar VLESS-XHTTP y sobre el estado de VMess-HTTPUpgrade-TLS.

La propuesta de auditoría más reciente fue conservar VLESS-XHTTP y dejar VMess-HTTPUpgrade-TLS pendiente de validación. No hay respuesta de aprobación registrada en el punto de corte de este documento.

## 7. Pendientes principales de Etapa 2

- Resolver y formalizar las discrepancias normativas indicadas.
- Integrar el asistente de creación VLESS con el modelo/adaptador.
- Definir e implementar modelos, generadores y validadores para VMess, Trojan, Shadowsocks e Hysteria2.
- Implementar administradores específicos SOCKS, HTTP Proxy y WireGuard.
- Integrar peers WireGuard con las identidades/asociaciones de Etapa 3.
- Diseñar aplicación transaccional de configuración, validación, verificación y rollback.
- Realizar pruebas de runtime e integración por modalidad y dependencias externas.
- Verificar compatibilidad real de plugins externos.

## 8. Reglas de estado

Usa siempre IMPLEMENTADO, VERIFICADO, PUBLICADO, SINCRONIZADO y ACEPTADO como estados separados, según AGENTS.md. Registra fecha, evidencia y entorno. No extrapoles un resultado de un entorno a otro.

## 9. Siguiente punto de control

Consultar docs/PUNTO_CONTROL_ACTUAL.md. No iniciar una nueva implementación de Etapa 2 hasta recuperar GitHub/VPS, resolver las discrepancias y obtener autorización explícita para la siguiente tarea.