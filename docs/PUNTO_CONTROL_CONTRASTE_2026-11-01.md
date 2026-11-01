# Punto de control de contraste — Xray Core Manager

**Fecha:** 2026-11-01  
**Referencia funcional principal:** `Xray_Manager_Documentacion_Final_2026-10-31`  
**Rama remota de referencia:** `design/user-identity-association-v1` (HEAD `3aeeb03c`); la copia VPS `/opt/xray-manager` no contiene metadatos `.git`, por lo que no se confirma rama local ni estado de commits.  
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
- Módulo de dependencias específicas del administrador: comprobación, instalación de faltantes y actualización limitada a paquetes requeridos.
- Configuración del administrador: preferencias de rutas, editor, tema, idioma, zona horaria, fecha/hora y respaldos.

Parcial o pendiente:
- Instalación/actualización/reinstalación/reparación: existe módulo controlado, catálogo compatible limitado a Xray 26.10.31 y validaciones de paquete; falta validación operativa real y ampliar pruebas de interrupción/rollback.
- Desinstalación: flujo local reforzado con allowlist, rechazo de symlinks, locks de integridad/Xray, respaldo y exportación SSH/SCP verificada; pruebas aisladas pasan. Falta validación destructiva en entorno desechable.
- Dependencias del sistema: módulo local implementado y probado con mocks; falta validar instalación/actualización real de paquetes en entorno desechable.
- Configuración del administrador: módulo local implementado y probado con preferencias temporales; falta validación operativa con las rutas reales de configuración.
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
- Renovación desde el menú para asociaciones activas o vencidas; inicia un periodo nuevo y las deja activas.
- Modificación de duración desde el menú para asociaciones activas o suspendidas; recalcula vencimiento desde ahora para activas y actualiza el tiempo restante pausado para suspendidas, sin reactivarlas.
- Eliminación individual desde el menú por ID y confirmación: elimina solo la asociación elegida y conserva la identidad y asociaciones hermanas; no aplica revocación runtime ni modifica provisioning.
- Eliminación de identidad global desde el menú por ID: vista previa de todas sus asociaciones, confirmación sí/no y reescritura exacta del ID; elimina identidad y asociaciones en un commit atómico. Un snapshot de IDs evita que se incluyan asociaciones añadidas concurrentemente después de la vista previa. También admite identidades sin asociaciones; no revoca runtime ni modifica provisioning.
- Suite de pruebas de menú y suite general de regresión.

Pendiente:
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
- Rama remota de referencia: design/user-identity-association-v1 (HEAD 3aeeb03c); /opt/xray-manager no contiene metadatos .git y no permite confirmar una rama local.
- No hacer merge a `main` sin aprobación.
- No ejecutar migración real sin autorización explícita.
- No activar Xray ni aplicar configuraciones al runtime sin autorización explícita.
- No modificar firewall, SSH ni datos reales como parte de pruebas.
- Las pruebas deben usar fixtures/directorios temporales.
- No ejecutar desinstalación real en VPS.
- Los archivos reales de usuarios y conexiones permanecen intactos; el servicio Xray está inactivo.

## 4. Próxima secuencia de implementación acordada

Cerrar primero Etapa 1 contra la especificación aprobada revisión 1.2. No avanzar con nuevas implementaciones de Etapas 2–6 hasta completar su matriz de trazabilidad, corregir hallazgos y validar operaciones en un entorno desechable. Después se retomará la secuencia pendiente de Etapa 3: importación/exportación completa y resolución manual de conflictos.


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

**Conclusión vigente:** Etapa 1 sigue PARCIAL y no certificada. La copia local ya incorpora dependencias, preferencias y un desinstalador más robusto que el HEAD remoto; aún faltan trazabilidad completa y validaciones operativas aisladas. No se debe avanzar de etapa ni declarar cierre por el solo hecho de que los menús y pruebas aisladas existan.


## 7. Actualización de contraste y pruebas — 2026-11-01

### 7.1 GitHub

- Repositorio: Jaok04/xray-core-manager.
- Rama remota: design/user-identity-association-v1.
- HEAD: 3aeeb03cbb9f2bd5022b3f2312fd395acbc562e3 (Include Stage 1 menu integration in smoke suite).
- La rama está 167 commits por delante y 0 por detrás de main.
- Árbol remoto: 45 archivos. Árbol VPS: 51 archivos; todas las 45 rutas remotas existen localmente.
- Archivos locales ausentes del árbol remoto: config/preferences.sh, modules/admin_settings.sh, modules/system_admin.sh, tests/stage1_dependencies.sh, tests/stage1_settings.sh y un artefacto __pycache__.
- El HEAD remoto conserva la entrada duplicada de desinstalación dentro del menú Xray; el menú local ya la eliminó conforme a Etapa 1 rev. 1.2.
- Los hashes de contenido de los archivos principales revisados no coinciden. Como /opt/xray-manager no tiene .git, no puede determinarse ascendencia ni estado staged/committed.
- No se hizo pull, checkout, merge, commit ni push. main y la rama remota no fueron modificadas.

Informe detallado: docs/CONTRASTE_GITHUB_DESIGN_USER_IDENTITY_ASSOCIATION_V1_2026-11-01.md.

### 7.2 Pruebas

- Suite completa: 15/15 scripts aprobados en la última ejecución.
- bash -n: aprobado.
- ShellCheck en los archivos de Etapa 1 y dependencias directas: aprobado.
- shfmt -d: sin diferencias.
- Las pruebas usaron fixtures temporales y mocks; no se ejecutaron operaciones reales de instalación/desinstalación ni se modificaron servicios, firewall, SSH o datos persistentes.
