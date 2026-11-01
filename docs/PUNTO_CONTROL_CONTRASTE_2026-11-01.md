# Punto de control de contraste — Xray Core Manager

**Fecha:** 2026-11-01  
**Referencia funcional principal:** `Xray_Manager_Documentacion_Final_2026-10-31`  
**Rama de trabajo:** `design/user-identity-association-v1`  
**Propósito:** mantener cada incremento contrastado con el diseño aprobado y registrar explícitamente las ampliaciones posteriores.

## 1. Regla de autoridad documental

1. La documentación final del 31/10/2026 es la referencia de alcance y comportamiento originalmente aprobado.
2. Este punto de control es la fotografía del estado real del proyecto a 01/11/2026; no sustituye ni reescribe la especificación original.
3. Los documentos técnicos posteriores detallan decisiones de implementación y no pueden contradecir silenciosamente la especificación funcional.
4. Se permiten mejoras no previstas originalmente si tienen justificación técnica/funcional, no rompen decisiones aprobadas, se prueban y se registran como ampliaciones.
5. Una etapa solo se declara completa cuando todos sus requisitos aplicables están implementados, integrados y verificados. Un menú, catálogo o módulo parcial no equivale a completar una etapa.
6. Antes de cada incremento se comprobarán: etapa/requisito relacionado, decisiones/invariantes, archivos afectados, pruebas, riesgos operativos y estado de runtime.

## 2. Estado de las etapas al establecer este punto de control

### Etapa 1 — Menú principal y organización general

**Estado: PARCIAL; no declarada completa.**

Implementado:
- Menú principal y navegación inicial.
- Encabezado dinámico: IP pública, versión Xray, estado del servicio, inicio automático, perfil activo y fecha/hora.
- Acceso a gestión de conexiones y usuarios.
- Administración básica de Xray-core y consulta de información.
- Punto de entrada centralizado al flujo de desinstalación segura.

Parcial o pendiente:
- Instalación/actualización/reinstalación/reparación: existe módulo controlado, catálogo compatible limitado a Xray 26.10.31 y validaciones de paquete; falta validación operativa real y ampliar pruebas de interrupción/rollback.
- Desinstalación: flujo implementado con alcance, política de datos, respaldo y exportación; falta validación destructiva en entorno desechable y hay categorías deliberadamente no eliminables hasta tener rutas administradas verificadas.
- Dependencias del sistema: pendiente.
- Configuración del administrador: pendiente.
- Certificados SSL/TLS y dominios: pendiente.
- Configuraciones, perfiles y respaldos: pendiente.
- Gestión del servicio Xray-core: parcial; no incluye ciclo completo de servicio/runtime.
- Diagnóstico y registros: pendiente.
- Seguridad, red y mantenimiento: pendiente.
- Información y ayuda: básica, no necesariamente satisface todo el contenido funcional aprobado.

**Criterio de cierre:** completar y probar los requisitos originales de Etapa 1; no marcarla completa por el mero hecho de que el menú exista.

### Etapa 2 — Protocolos y conexiones

**Estado: BASE ADMINISTRATIVA IMPLEMENTADA; etapa no declarada completa en términos de operación real.**

Implementado:
- Catálogo de modalidades en `config/protocols.tsv`.
- Alta/listado/edición/eliminación de conexiones en borrador.
- Validaciones de modalidad, identificador, puerto, capacidad y duplicados.
- Comprobación puntual de sockets TCP/UDP mediante `ss`.
- Persistencia JSON atómica, permisos privados y lock compartido.
- Pruebas de concurrencia, carreras cruzadas, fallos de persistencia y colisiones de puertos.
- Modelo neutral y adaptador versionado VLESS, con pruebas de integración para las modalidades implementadas.

Pendiente/límites:
- Un borrador no genera ni aplica configuración Xray.
- No hay transacciones de aplicar/verificar/rollback al runtime.
- No todas las modalidades catalogadas tienen generador/adaptador y validación operativa completa.
- La comprobación con `ss` es puntual y no reserva el puerto.
- La instalación real de Xray y la validación de configuración en un entorno aislado siguen siendo requisitos previos para activar conexiones.

### Etapa 3 — Gestión de usuarios

**Estado: EN DESARROLLO; modelo v2 y primeras operaciones integradas.**

Implementado:
- Identidades globales y asociaciones independientes en un único `users.json` v2.
- IDs inmutables; alias no único y no usado para deduplicar.
- Asociaciones múltiples; peers WireGuard múltiples por identidad/conexión.
- UUID VLESS globalmente único.
- Separación de estado funcional, provisioning y runtime.
- Persistencia atómica, lock compartido y validación de referencias.
- Migración legacy no destructiva, dry-run/apply/rollback con confirmaciones y verificaciones.
- Lógica de duración, suspensión, reactivación, renovación y vencimiento.
- Selector legacy/v2 y menú inicial v2.
- Creación de identidad y asociaciones VLESS/WireGuard desde el menú.
- Consulta de detalle de asociación desde el menú, sin exponer credenciales ni modificar datos/runtime.
- Edición de alias y límites de tráfico/conexiones simultáneas desde el menú, por ID de asociación y con commit atómico; no altera credenciales ni runtime.
- Suspensión/reactivación desde el menú: pausa el tiempo restante de duración limitada al suspender y exige una duración nueva al reactivar; no modifica provisioning ni runtime.
- Suite de pruebas de menú y suite general de regresión.

Pendiente:
- Renovación y modificación de duración desde menú.
- Eliminación de asociación individual e identidad con confirmaciones.
- Importación/exportación completa y resolución manual de identidades/conflictos.
- Protección de secretos/cifrado en reposo y gestión de claves.
- Modelo completo de campos específicos WireGuard.
- Barrido periódico de vencimientos.
- Aplicación/revocación real en runtime y sincronización de provisioning.
- Migración real del archivo de usuarios: no ejecutada.

**Límite operativo actual:** el registro real de usuarios sigue en formato legacy vacío; el dry-run de transición se ejecutó con cero filas. No se ha aplicado migración real. El servicio Xray permanece inactivo.

### Etapas 4–6

Certificados/dominios, configuraciones/perfiles/respaldos, servicio/diagnóstico y áreas posteriores permanecen sin implementación funcional completa según el menú/documentación. No inferir avance por placeholders.

## 3. Estado operativo protegido

A la fecha del punto de control:
- Rama de trabajo: `design/user-identity-association-v1`.
- No hacer merge a `main` sin aprobación.
- No ejecutar migración real sin autorización explícita.
- No activar Xray ni aplicar configuraciones al runtime sin autorización explícita.
- No modificar firewall, SSH ni datos reales como parte de pruebas.
- Las pruebas deben usar fixtures/directorios temporales.
- No ejecutar desinstalación real en VPS.
- Los archivos reales de usuarios y conexiones permanecen intactos; el servicio Xray está inactivo.

## 4. Próxima secuencia de implementación acordada

Continuar Etapa 3 de forma incremental, manteniendo Etapas 1 y 2 visibles en la matriz de cierre:

1. Renovación y modificación de duración.
2. Eliminación de asociación individual.
3. Eliminación de identidad y todas sus asociaciones, con confirmación explícita.

Cada operación requiere validación de entradas, lock compartido, rechazo sin escritura ante errores, pruebas aisladas y actualización de documentación. El orden puede cambiar solo si existe una dependencia técnica justificada.

## 5. Plantilla obligatoria para ampliaciones

Toda mejora fuera de la documentación original debe registrar:
- **Requisito original relacionado:** sección/etapa o “sin requisito directo”.
- **Motivo:** problema que resuelve.
- **Decisión:** comportamiento añadido o modificado.
- **Compatibilidad:** por qué no contradice las decisiones aprobadas.
- **Pruebas:** casos y resultados.
- **Impacto operativo:** archivos/datos/runtime afectados.
- **Estado:** propuesta, aprobada, implementada o verificada.

## 6. Regla de comunicación del avance

En cada cierre de incremento se informará:
- Qué se implementó.
- Qué requisito original satisface.
- Qué ampliaciones se incorporaron.
- Qué pruebas pasaron/fallaron.
- Qué archivos/datos reales no fueron tocados.
- Qué queda pendiente.
- Si el estado de una etapa cambia o permanece igual.

**Conclusión inicial:** el proyecto está trabajando principalmente en Etapa 3, con una base administrativa avanzada de Etapa 2 y Etapa 1 parcialmente implementada. Etapa 1 NO está completa. Este es el punto de control de contraste vigente hasta que se apruebe una revisión posterior.
