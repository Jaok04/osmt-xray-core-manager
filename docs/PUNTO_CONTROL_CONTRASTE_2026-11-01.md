# Punto de control de contraste — Xray Core Manager

**Fecha original:** 2026-11-01  
**Última actualización:** 2026-11-02  
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

**Estado vigente: IMPLEMENTADA — lista para aceptación formal; no certificada formalmente.**

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
- Desinstalación: flujo local reforzado con allowlist, rechazo de symlinks, bloqueo de ciclo de vida/integridad/Xray antes del respaldo, exportación SSH/SCP verificada y confirmación final; pruebas aisladas pasan. Falta validación destructiva en entorno desechable.
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
- Rama remota de trabajo: `design/user-identity-association-v1`; `/opt/xray-manager` no contiene metadatos `.git`, por lo que la copia VPS no permite confirmar rama local ni estado de commits.
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

**Conclusión vigente (actualizada 02/11/2026):** Etapa 1 está IMPLEMENTADA y lista para aceptación formal; no se declara certificada hasta la aprobación del usuario. La coordinación interna de concurrencia, las confirmaciones destructivas y los requisitos M04/M06 del encabezado están implementados y probados. En VPS desechable se verificaron instalador aislado, Xray real preexistente, dependencias, preferencias y borrado de un árbol fixture. La descarga/instalación real de Xray-core ya se validó en prefijo temporal. El guard es dependiente del alcance: Manager-only se permite si Xray está detenido, mientras Xray-only/both se bloquean si la unidad sigue instalada; cualquier alcance se bloquea si Xray está activo. U11 se cerró con aserciones completas de la vista previa y confirmaciones. El cotejo final se completó con 47/47 comprobaciones PASS. Limitación conocida: U08 se verificó con mocks SSH/SCP y no con un servidor remoto real. No se debe confundir la implementación verificada con una certificación formal sin aceptación del usuario.


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

- Suite completa: 20/20 scripts aprobados en la última ejecución.
- bash -n: aprobado.
- ShellCheck en los archivos de Etapa 1 y dependencias directas: aprobado.
- shfmt -d: sin diferencias.
- Las pruebas usaron fixtures temporales y mocks; no se ejecutaron operaciones reales de instalación/desinstalación ni se modificaron servicios, firewall, SSH o datos persistentes.


## 8. Actualización — concurrencia y confirmaciones (2026-11-01)

- Nuevo `lib/operation_lock.sh`: lock de ciclo de vida no bloqueante, permisos 600 y rechazo de rutas simbólicas. Las acciones mutantes de `xray.service` también lo adquieren.
- Instalador: adquiere lifecycle e integridad antes de desplegar o inicializar datos. Administración Xray, dependencias y guardado de preferencias comparten lifecycle.
- Desinstalación: adquiere lifecycle, uninstall, integridad y Xray antes de crear el respaldo; mantiene los locks durante respaldo, exportación, confirmación final y borrado.
- `A11`, `U14` y `N03` pasan a IMPLEMENTADO para las operaciones internas cubiertas por estos locks.
- Validación final de esta ronda: 20/20 pruebas, Bash syntax, ShellCheck y shfmt en archivos de producción modificados y pruebas con estilo homogéneo; `tests/uninstall.sh` conserva formato histórico mixto. `./install.sh --check` PASS. Xray permaneció inactivo; no se ejecutaron apt, instalación/desinstalación real, migraciones ni cambios de firewall/SSH.
- En la fotografía de ese corte, M04/M06 estaban cerrados; las validaciones operativas y el cotejo final se completaron después, el 02/11/2026.


## 9. Actualización — M04/M06 (02/11/2026)

- M04: se añadió la cobertura explícita del autostart `disabled`; ahora se distinguen unidad no configurada, habilitada, deshabilitada, enmascarada y estados no aplicables.
- M06: `system_show_header` aísla fallos de cada fuente y conserva el menú principal. Las pruebas fallan independientemente IP, versión Xray, estado del servicio, autostart, perfil y fecha/hora, y luego todas simultáneamente.
- Validación final: 20/20 scripts, Bash syntax, ShellCheck, shfmt y `./install.sh --check` PASS. `tests/port_collisions.sh` falló intermitentemente una vez, pasó tres ejecuciones aisladas consecutivas y pasó en la suite completa repetida. Xray permanece inactive.
- M04/M06 pasan a IMPLEMENTADO en esta actualización histórica; el cierre operativo y el cotejo final se registran en las secciones posteriores.


## 10. Validación operativa desechable (02/11/2026)

Se completaron pruebas operativas seguras en Ubuntu 24.04.4 LTS: instalación del Manager en prefijo temporal (Xray ficticio, sin apt), segunda ejecución idempotente, validación de Xray 26.10.31 real como usuario `xray`, reporte de dependencias sin faltantes y simulación apt sin cambios, guardado/recarga/restauración exacta de preferencias y borrado real de un `APP_ROOT` fixture mediante el módulo de desinstalación.

No se descargó/reinstaló Xray real ni se eliminó el Manager/unidad reales. La unidad del host permaneció inactive/disabled; los datos persistentes y preferencias quedaron intactos.

En esta fotografía intermedia aún se consideraba PARCIAL. La instalación real de Xray-core en prefijo temporal, el despliegue del Manager, el guard de desinstalación frente a la unidad real y la revisión final se completaron en actualizaciones posteriores del 02/11.


## 11. Xray-core real aislado y guard de desinstalación (02/11/2026)

Se descargó Xray 26.10.31 del release oficial, se verificó el digest publicado y el SHA-256 fijado, y se instaló binario/geodata en prefijo temporal. Después `install.sh --install` desplegó el Manager sobre ese prefijo, preparó la unidad sin tocar systemd del host y pasó una segunda ejecución idempotente.

`systemd-analyze verify` pasó para la unidad real del host. Con `xray.service` inactive/disabled, Manager-only eliminó únicamente un `APP_ROOT` fixture y preservó la unidad y el core; Xray-only fue bloqueado por la unidad real. No se alteraron systemd, firewall ni SSH. U15 pasa a IMPLEMENTADO.

U11 se implementó y probó: resumen completo de alcance, política, categorías, rutas, respaldo/exportación, advertencias y confirmaciones. Cotejo final: 47/47 comprobaciones PASS; no quedan filas normativas PARCIAL/PENDIENTE. U08 mantiene como limitación no haber usado un destino SSH/SCP real. Etapa 1 queda lista para aceptación formal.


## 12. U11 — vista previa completa de desinstalación (02/11/2026)

`tests/uninstall.sh` cubre un escenario `both + selected(users)` y verifica alcance, política, categoría seleccionada, todas las rutas, respaldo temporal, exportación verificada, advertencia de systemd, exclusiones de Etapa 5 y los prompts de respaldo, exportación y confirmación irreversible. El respaldo fixture queda en modo 600 y las rutas seleccionadas se eliminan. Se corrigieron los saltos de línea del resumen. U11 pasa a IMPLEMENTADO.

Validación de ese corte: suite 20/20; sintaxis Bash, ShellCheck, shfmt de archivos homogéneos e `install.sh --check`: PASS. El cotejo final 47/47 se completó posteriormente y se documenta en la sección 14.


## 13. U15 — guard de desinstalación según alcance (02/11/2026)

Se corrigió la sobreprotección detectada: ahora Manager-only puede retirar el administrador cuando Xray está detenido, aunque la unidad siga instalada, y conserva binario/unidad. Si el alcance incluye Xray-core, se bloquea ante una unidad instalada para evitar dejar una unidad huérfana. Si Xray está activo, todos los alcances se bloquean.

Pruebas automatizadas y VPS desechable con unidad real inactive/disabled confirmaron Manager-only sobre fixture, preservación de Xray/unidad y bloqueo de Xray-only. No se modificaron systemd, firewall ni SSH.


## 14. Cotejo final de la especificación (02/11/2026)

Se parseó `Etapa_1_Menu_Principal.yaml` y se cotejaron las etiquetas del menú principal, las entradas de opción [8], las seis opciones de administración Xray y los alcances/políticas/categorías de desinstalación con el código. También se revisaron advertencias, orden de respaldo/confirmación/borrado, verificación SHA-256, fallbacks del encabezado, límite de paquetes y confirmación de salida. Resultado: **47/47 PASS**.

La matriz no conserva filas normativas PARCIAL o PENDIENTE. U15 es un control adicional de seguridad. U08 tiene código y pruebas automatizadas con mocks; no se hizo una exportación real por SSH/SCP por falta de destino/credenciales. Etapa 1 está implementada y lista para aceptación formal, no certificada formalmente hasta aprobación del usuario.
