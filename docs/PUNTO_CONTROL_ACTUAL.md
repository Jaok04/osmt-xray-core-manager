# Punto de control actual — Xray Core Manager

**Fecha del corte:** 2026-11-02  
**Tipo de trabajo:** creación del sistema de continuidad del proyecto.  
**Estado de esta tarea:** cinco documentos creados, publicados en la rama autorizada y verificados por comparación exacta de texto entre GitHub y VPS.

## 1. Punto exacto del proyecto

- Etapa 1: aceptada formalmente por el propietario.
- Etapa 2: en desarrollo; no está completada.
- Etapa 3: pendiente de desarrollo según la planificación normativa.
- Repositorio: Jaok04/xray-core-manager.
- Rama autorizada: design/user-identity-association-v1.
- VPS: /opt/xray-manager.
- Documentación normativa: /root/Xray_Manager_Documentacion_Final_2026-10-31.

## 2. Último commit conocido

SHA registrado: cd76e84a48974762f28b666e8d440de52062d6a8  
Mensaje: docs: record stage two menu implementation  
Fecha: 2026-11-02 09:55:08 UTC.

Importante: verificar el HEAD remoto actual al reanudar. El SHA de este documento es un punto de referencia histórico, no una garantía de HEAD actual.

## 3. Situación de la VPS al iniciar la creación de estos documentos

- /opt/xray-manager existe y contiene código, tests y documentación técnica.
- No existía /opt/xray-manager/.git en la inspección del 02/11/2026.
- Por tanto, no se puede atribuir branch ni commit a la copia de la VPS.
- Antes de sincronizar, comparar el contenido con GitHub y preservar diferencias.
- En una auditoría previa, modules/main_menu.sh y docs/ETAPA_2_IMPLEMENTACION_MENU_2026-11-02.md tuvieron SHA distinto frente a GitHub pese a que el texto recuperado parecía igual; causa no determinada.

## 4. Estado de Etapa 2

La navegación inicial por familias, modalidades y protocolos opcionales está implementada. La gestión de conexiones permite crear borradores, listarlos, consultar detalles, editar borradores y eliminarlos con confirmación. El catálogo contiene 38 registros.

VLESS dispone de modelo neutral de nueve modalidades y adaptador para Xray-core 26.10.31. La prueba de integración documentada validó las nueve modalidades con xray run -test en fixtures temporales. No es prueba de conectividad extremo a extremo.

Las conexiones siguen siendo borradores. No se aplica automáticamente configuración al runtime, no se abren puertos y no se modifica firewall desde este flujo.

La Etapa 2 sigue abierta. Ver PROJECT_STATE.md y docs/ETAPA_2_CONEXIONES.md.

## 5. Discrepancias que bloquean una continuación sin decisión

1. La especificación funcional normativa Etapa 2 revisión 1.3 enumera cinco modalidades VLESS; el catálogo/modelo/adaptador actuales contienen nueve, incluyendo tres variantes XHTTP.
2. VMess-HTTPUpgrade-TLS aparece en catálogo/código, pero no está expresamente definido como modalidad independiente en la especificación 1.3.
3. La decisión propuesta fue conservar VLESS-XHTTP y dejar VMess-HTTPUpgrade-TLS pendiente de validación. En este corte no consta aprobación del propietario a esa propuesta.
4. La copia VPS carece de .git y hay divergencias de hash previamente observadas que requieren reconciliación.

No modifiques la especificación ni elimines/retires modalidades sin decisión explícita.

## 6. Siguiente acción recomendada

1. Confirmar que estos cinco documentos están presentes en VPS y en la rama autorizada de GitHub.
2. Verificar su contenido y hashes en ambos destinos.
3. Resolver con el propietario la discrepancia normativa VLESS-XHTTP / VMess-HTTPUpgrade-TLS.
4. Solo después, actualizar la especificación normativa si el propietario lo aprueba.
5. Continuar con la integración del asistente VLESS con el modelo y adaptador existentes, una vez autorizado.

No iniciar implementación adicional ni sincronización destructiva por iniciativa propia.

## 7. Checklist para la próxima sesión

- [ ] Leer AGENTS.md, PROJECT_STATE.md, docs/CONTINUIDAD_DEL_PROYECTO.md, este documento y HISTORY.md.
- [ ] Consultar HEAD real de GitHub.
- [ ] Comprobar si /opt/xray-manager tiene .git.
- [ ] Leer documentación normativa pertinente.
- [ ] Comparar GitHub y VPS sin sobrescribir.
- [ ] Presentar estado y divergencias.
- [ ] Obtener autorización para el siguiente cambio.