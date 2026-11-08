

# B4.3-B — diseño de integración fixture con el supervisor (2026-11-08)

Se completó el diseño `docs/DISENO_INTEGRACION_B4_3B_SUPERVISOR_EVIDENCIA_FIXTURE_2026-11-08.md`, basado en HEAD `1da1b77470179a2b082a0f196db56030d9f72afa`. Es un diseño técnico, todavía NO implementado ni auditado. Define un adaptador fixture que conectará el PID del hijo bloqueado por el pipe gate con el almacén persistente B4.3-A, usando un descriptor de raíz confiable y recorrido interno por dirfd + `O_NOFOLLOW` + `fstat`. El backend nuevo será opt-in y sin fallback silencioso al almacén plano B4.1. Si falla la creación/verificación de evidencia, el hijo no debe recibir el token del gate y no debe ejecutar Xray.

La evidencia conserva `prepared_before_exec`: no demuestra `exec` exitoso, proceso activo, `MainPID` ni estado systemd. H6/R-05 y cualquier integración live permanecen fuera del alcance. Siguiente paso: implementar adaptador y camino `persistent_b43` sólo en fixtures; añadir pruebas de anclaje FD, fallo del gate, symlink/TOCTOU, replay y segregación; ejecutar regresión completa y revisión adversarial. No tocar `modules/xray_service.sh`, unidades, cuentas, systemd real, runtime, VPS Pruebas, `main` ni `Xray-Normativa/`.
# Punto de reanudación vigente — B4.3-A evidencia persistente fixture (2026-11-08)

**Último avance:** revisión adversarial B4.3-A implementada y publicada en fixtures. Nuevo almacén separado scripts/xray_runtime_evidence_store.py y suite tests/test_xray_runtime_evidence_store.py; informe docs/REVISION_B4_3A_EVIDENCIA_PERSISTENTE_FIXTURE_2026-11-08.md.

**Resultado:** almacén valida layout B4.3, crea evidencia root:root 0600 de forma atómica y sin reemplazo, rechaza symlinks/hardlinks, InvocationID no canónica y campos de configuración/secretos; comprueba persistencia tras reapertura y que la identidad de servicio no atraviese el padre root-only. Suite nueva 12/12; B4.3 directorios+evidencia 21/21; conjunto focal B4 51/51; Python global 458/458; compileall, bash -n 91/91, ShellCheck global, install.sh --check y diff-check PASS.

**Hallazgo:** el helper anterior B4.1 exige evidencia como hijo directo de la raíz fixture y no representa el path anidado B4.3; por eso se creó un módulo separado, sin integración. Los componentes desde la raíz fixture se abren por dirfd con O_NOFOLLOW; producción debe recibir una raíz previamente anclada por Manager.

**Publicación:** implementación commit 0fbd7ff30854c3b84e0453545833787ec78a7248; continuidad/documentación commit ce066f763830e26eedb6d8583a405096a0a2cd57; HEAD local/remoto verificado y árbol limpio. **Límites:** no systemd, daemon, unidad, xray:xray, R-05, controlador, menú, backend live, runtime, VPS pruebas ni red. Próximo paso: diseñar integración fixture del almacén con el supervisor, manteniendo el anclaje de raíz confiable. Live requiere autorización específica.

---

# Punto de reanudación vigente — B4.3 layout y sandbox fixture (2026-11-08)

**Prioridad:** primer servidor real VLESS + WebSocket + TLS en `pruebas.tvrc.me:443`, administrado íntegramente por Xray-Core Manager, con conectividad externa bidireccional demostrada.

**Último avance:** B4.2 está publicado y B4.3 define/implementa en fixtures el contrato de directorios para supervisor root y Xray `xray:xray`. Diseño: `docs/DISENO_B4_3_LAYOUT_DIRECTORIOS_SANDBOX_FIXTURE_2026-11-08.md`. Código: `scripts/xray_runtime_directory_contract.py`; pruebas: `tests/test_xray_runtime_directory_contract.py`.

**Layout propuesto:** `/var/lib/xray` y `/run/xray` como `root:xray 0770` para escritura del proceso mediante grupo; `/var/lib/xray-manager` y `/var/lib/xray-manager/evidence` como `root:root 0700`; archivos de evidencia `root:root 0600`. La unidad a evaluar usaría `User=root`, `Group=xray`, `StateDirectory=xray`, `RuntimeDirectory=xray`, modos `0770`, `ProtectSystem=strict` y `ReadWritePaths` limitado a esas tres rutas de escritura. Es un contrato técnico fixture, no una unidad aprobada ni validada por systemd.

**Verificación:** B4.3 focal 9/9; Python global 446/446; Bash syntax 91/91; ShellCheck global `-S error`; `compileall`; `install.sh --check`; `git diff --check` PASS.

**Límites:** no se creó `xray:xray`; fixture usa GID numérico sustituto. No se ejecutó systemd, `systemd-analyze verify`, daemon, ni se probó el sandbox real. No se modificaron `modules/xray_service.sh`, unidad, R-05, menú/backend live, cuentas, runtime ni VPS de pruebas. `main` y `Xray-Normativa/` no se modificaron. En contraste normativo, los 14 archivos comunes coinciden por SHA-256; `Xray-Normativa/README.md` no existe en el respaldo `/root/Xray_Manager_Documentacion_Final_2026-10-31`. No corregir sin decisión del propietario.

**Estado Git:** publicación autorizada exclusivamente en `design/user-identity-association-v1`; Commit B4.3 publicado y verificado: `787525b22573e5d577ef106f105daf7cb555840a`. GitHub devolvió el mismo SHA para la rama autorizada.

**Siguiente paso:** revisión adversarial focal del contrato B4.3 y ampliación de fixtures para evidencia persistente/acceso supervisor-Xray. La integración en módulo/controlador, cambio de unidad, creación de cuenta, prueba systemd real o conexión R-05 requieren autorización específica.

---

# Punto de reanudación vigente — B4.2 publicado (2026-11-08)

**Prioridad del proyecto:** lograr el primer servidor real VLESS + WebSocket + TLS en `pruebas.tvrc.me:443`, administrado íntegramente por Xray-Core Manager, y demostrar conectividad externa bidireccional. No ampliar el alcance innecesariamente.

**Estado de código:** B4.2 está IMPLEMENTADO y VERIFICADO exclusivamente en fixtures. El memfd se transfiere a la identidad de servicio con modo `0400`, conserva seals y se revalida por UID/GID/modo/tamaño/SHA-256. El supervisor fixture usa únicamente `CAP_CHOWN`, `CAP_SETUID`, `CAP_SETGID` y `CAP_NET_BIND_SERVICE`, con `NoNewPrivileges=1`; Xray 26.10.31 `run -test` pasa después del descenso a `nobody:nogroup`. Informe: `docs/IMPLEMENTACION_B4_2_SUPERVISOR_CAPACIDADES_FIXTURE_2026-11-08.md`.

**Verificación registrada:** B4.1/B4.2 focal 20/20; Python 437/437; Bash syntax 91/91; ShellCheck global `-S error`; `compileall`; `install.sh --check`; `git diff --check` PASS. Estas son pruebas de desarrollo/fixtures, no validación de servicio real.

**Límites y bloqueos:** no se creó `xray:xray`; no se probó unidad/sandbox systemd real, `InvocationID`/`MainPID` reales ni daemon. Falta diseñar el ownership de `StateDirectory=xray` y `RuntimeDirectory=xray` cuando systemd inicia el supervisor como root, además de `ReadWritePaths`, la ruta de evidencia root-only compatible con `ProtectSystem=strict` y el ciclo de vida de esos directorios. El siguiente trabajo permitido es diseño y fixtures de ese contrato. No modificar todavía `modules/xray_service.sh`, unidad real, R-05, menú/backend live ni VPS de pruebas.

**Infraestructura protegida:** no hubo operaciones live; no se modificaron systemd, runtime, cuentas, DNS, firewall, puertos o red. `main` y `Xray-Normativa/` permanecen intactas. La publicación autorizada se realiza exclusivamente en `design/user-identity-association-v1`. No confundir IMPLEMENTADO/VERIFICADO con ACEPTADO ni con conectividad end-to-end.

**Publicación verificada:** rama `design/user-identity-association-v1`; commit B4.2 `848324977a2d42a25ecb7db0ab45f38832eaa4ee`. GitHub reportó el mismo SHA para la referencia remota inmediatamente después del push. `main` no fue modificada. La actualización documental posterior deja registrado este resultado; verificar siempre el HEAD remoto real al reanudar.

Para reanudar, seguir el mensaje de inicio y el procedimiento de auditoría de recuperación que aparecen más abajo; comprobar primero el HEAD remoto real, el árbol de trabajo y la integridad de `Xray-Normativa/`. Siguiente tarea: diseñar fixture del layout de directorios/sandbox, sin operaciones live.

---

# Punto de reanudación vigente — auditoría B4.1 fixture (2026-11-07)

B4.1 fue auditado y endurecido en desarrollo. El lanzador revalida identidad NSS/UID/GID y bytes reales del memfd (seals, tamaño y SHA-256), aplica timeout con terminación/recolección del grupo hijo y exige ejecutables regulares root-owned no modificables por grupo/otros. A01–A03 resueltos; A04 mitigado, con TOCTOU residual documentado.

Pruebas: B4.1 16/16; Python 433/433; Bash 62/62; compileall, bash -n, ShellCheck -S error, install.sh --check y diff-check PASS. Informe: docs/IMPLEMENTACION_B4_1_LANZADOR_PRIVILEGIOS_FIXTURE_2026-11-07.md.

**Estado y límites:** cambios locales sin commit/push, rama design/user-identity-association-v1, HEAD base 899f29f4253f56f80d0d803207feceb743879a0a. Aún usa nobody:nogroup, InvocationID sintético y xray run -test; no daemon ni sandbox systemd real. No se tocaron R-05, menú, backend live, modules/xray_service.sh, unidad, /etc/xray, cuentas, servicio ni VPS Pruebas. Xray-Normativa permanece intacta.

**Siguiente acción:** diseñar fixture de identidad xray:xray y análisis de compatibilidad del sandbox systemd. No crear cuentas/unidades ni realizar pruebas live sin autorización específica; toda preparación real debe pasar por Xray-Core Manager. No integrar a R-05/controlador hasta completar diseño, auditoría y autorización separada.


# Punto de reanudación vigente — instalador autónomo GitHub (2026-11-06)

El propietario aprobó implementar la instalación desde un único `install.sh` para el repositorio privado. La implementación está en el árbol de trabajo de `/opt/xray-manager`, rama `design/user-identity-association-v1`, commit de implementación `8d76275b6bfb1eeda5eaa859b45f979804784094`; la actualización de continuidad se registra en el commit documental siguiente y se publicará junto con él.

- Fine-grained PAT de GitHub, limitado al repositorio `Jaok04/xray-core-manager` con `Contents: Read-only`.
- El bootstrap inicial obtiene `install.sh` mediante GitHub API; el instalador descarga el árbol completo de un commit inmutable, verifica helper SHA-256 y todos los Git blobs, y despliega sin `.git` ni historial.
- Código: `install.sh`, `scripts/installer_bootstrap.py`; pruebas: `tests/test_installer_bootstrap.py` y `tests/install.sh`.
- Procedimiento exacto de instalación: `docs/INSTALACION_DESDE_VPS_LIMPIA.md`.
- Pruebas: Python 406/406, Bash 62/62, bootstrap focal 18/18; compileall, bash -n, ShellCheck `-S error`, `install.sh --check` y diff-check PASS.
- **Pendiente:** ejecutar el bootstrap real desde la VPS limpia del propietario con su PAT. No pegar el PAT en el chat. Hasta esa validación, la descarga remota privada queda probada mediante mocks/fixtures y verificación local de `git archive`, no end-to-end.
- Manager-only continúa siendo el default. `--with-xray` sigue siendo explícito; no iniciar Xray ni cambiar DNS/firewall/puertos/certificados.
- H6-G2 permanece abierto; H6-G3 requiere revisión adversarial interna adicional y no se declara independiente.
- `main` y `Xray-Normativa/` no se modificaron.

Para continuar: revisar `docs/DECISION_INSTALADOR_AUTODESCARGA_GITHUB_2026-11-06.md`, el informe de implementación/auditoría y ejecutar una validación en VPS limpia. No reabrir B1/B2/B3 ni las etapas ya aceptadas.

---

# Protocolo de continuidad — Xray Core Manager

> PUNTO DE REANUDACIÓN VIGENTE — 2026-11-06: H6-E1/E2/E3 implementadas y auditoría integral H6-E PASS CON LIMITACIONES. El instalador predeterminado despliega sólo Xray Manager; Xray-core se instala después desde el menú. H6-F NO LISTO END-TO-END. Rama design/user-identity-association-v1; HEAD base local/remoto antes de esta actualización: 32496d749901d34cd1a60f720843901125b536b6. Sincronización confirmada: implementación publicada en 4984ce207ff446bb097cc53c6445ad1e9b53c585 y cierre documental en 537fb5475ce6bfcbba8401a1fced1642ca203cba; HEAD local/remoto 537fb5475ce6bfcbba8401a1fced1642ca203cba y árbol limpio. main y Xray-Normativa/ protegidas.

> Para continuar: leer AGENTS.md, PROJECT_STATE.md, este documento, docs/PUNTO_CONTROL_ACTUAL.md, HISTORY.md y docs/AUDITORIA_H6E_INTEGRAL_2026-11-06.md. Verificar HEAD y árbol de trabajo antes de modificar. No habilitar backend live ni ejecutar acciones systemd/Xray reales sin autorización específica.


> **Punto de reanudación vigente — 2026-11-05:** B3 está implementada, verificada, auditada, aceptada formalmente, publicada y sincronizada en design/user-identity-association-v1. HEAD: `9f4cc18d856ec0ccb31951f343a1fd3e870a0684`. Regresión histórica B3: Python 186/186 y Bash 61/61 PASS; controles estáticos e install.sh --check PASS. Sin operaciones live. main y Xray-Normativa/ intactas; R-06/live NO AUTORIZADA.

> **Evidencia VMess TLS incorporada:** una prueba live posterior verificó que Xray-core 26.10.31, ejecutado como UID 999/GID 988, leyó el certificado y la clave sintéticos de un lease y completó un handshake TLS 1.3 en la segunda ejecución. La primera ejecución no se contabiliza como exitosa. Esto demuestra lectura por un proceso Xray real en el entorno de prueba, no despliegue de `xray.service`, activación del runtime administrado, conectividad WAN ni aceptación integral de VMess TLS. Informe: `docs/VALIDACION_LIVE_VMESS_TLS_LEASE_2026-11-03.md`.

> Los apartados cronológicos antiguos se conservan como historial. Para el estado actual prevalecen los bloques vigentes añadidos al final de `PROJECT_STATE.md`, `docs/PUNTO_CONTROL_ACTUAL.md` y este documento; las decisiones históricas superadas no autorizan nuevas implementaciones.

> Frente activo 2026-11-03: aceptación formal del Snapshot Writer v1 con limitaciones documentadas. La corrección A-16 y B-01/B-02/B-03 están publicadas; se añadieron diez negativos A-16 y una matriz de trazabilidad A-01–A-19 en §10.20. Última regresión: 49/49 scripts PASS; AST 16/16; bash -n 74 archivos; ShellCheck, shfmt y diff-check PASS. Writer ACEPTADO FORMALMENTE CON LIMITACIONES DOCUMENTADAS el 2026-11-03. No crear backups reales ni leer secretos/master.key; no restore/verify independiente ni runtime apply. Xray-Normativa inmutable; no tocar VPS de pruebas.
> La aceptación formal y su actualización documental están registradas en la parte final de este archivo. La rama autorizada sigue siendo design/user-identity-association-v1; main y Xray-Normativa permanecen protegidas.


> Registro histórico: la auditoría inicial de almacenes/certificados y el cierre del contrato se documentaron antes del primer bloque. Consultar los dos informes de implementación para el estado vigente.


> **Línea base VMess — 2026-11-03 (actualizada por evidencia posterior):** F-01–F-05 resueltos/verificados; VM-28 verificado; VM-32 verificado con límite transaccional documentado; VM-33 no aplica al alcance aprobado; VM-38/39/40 verificados; suite 40/40 PASS; Xray 14/14 y 16 negativos PASS; VM-46 live PASS; VM-47 cliente-servidor VMess-TLS loopback PASS. Posteriormente se verificó lectura del lease por proceso Xray real y handshake TLS 1.3; véase el informe live específico. Cliente externo/WAN no probado y no requerido por el diseño. VM-48/aceptación formal de VMess siguen pendientes; Etapa 2 permanece ABIERTA. Leer los informes de auditoría y validación referenciados en los apartados históricos y el informe live nuevo. No iniciar Trojan.


## Punto de reanudación B3 — 2026-11-05

B3 implementada/verificada/auditada focalmente y ACEPTADA FORMALMENTE por el propietario el 2026-11-05, con las limitaciones documentadas en la auditoría. El propietario autorizó commit/push exclusivamente en design/user-identity-association-v1. El flujo contextual de conexión VLESS-WS-TLS permite asociar identidad existente o crear identidad nueva y asociarla. Exportación exige validación Xray PASS de la revisión exacta y comprueba SAN DNS contra SNI o endpoint. Endpoint IP sin SNI DNS verificable falla cerrado.

Pruebas: Python 186/186, Bash 61/61, integración compositor → validador Xray 26.10.31 → exportador PASS; controles estáticos e install.sh --check PASS. No se ejecutó NetMod real, WAN, ACME real, runtime, systemd, DNS, firewall, puertos o red. No se instalaron dependencias ni se leyó la clave maestra real.

Archivos: docs/DECISION_B3_VLESS_WS_TLS.md, docs/IMPLEMENTACION_B3_VLESS_WS_TLS_2026-11-05.md, docs/AUDITORIA_B3_VLESS_WS_TLS_2026-11-05.md.

**Siguiente paso:** continuar con el contraste preliminar read-only del siguiente bloque del MVP. No implementar sin presentar discrepancias y recibir autorización expresa. No modificar main, Xray-Normativa/ ni infraestructura live.

## Actualización de continuidad — 2026-11-07

Último cambio local en desarrollo: corrección del manejo de errores de `xray_admin_install_menu_action()` en `modules/xray_admin.sh`, con regresión en `tests/xray_admin.sh`. La acción ahora conserva el código de `xray_admin_install_version()` a través de `ui_pause` y muestra un mensaje explícito cuando falla. Ver `docs/IMPLEMENTACION_CORRECCION_ERROR_INSTALADOR_XRAY_2026-11-07.md` y `docs/PUNTO_CONTROL_ACTUAL.md`.

Validación ejecutada en VPS de desarrollo: Bash 62/62, Python 406/406, `bash -n` global, compileall, ShellCheck `-S error`, `install.sh --check` y diff-check PASS. No es auditoría independiente. El primer fallo real en VPS Pruebas no tiene causa identificada porque no se capturó su código/salida; no afirmar que este cambio resuelve necesariamente esa causa. No se repitió la instalación, no se tocó VPS Pruebas ni runtime.

La publicación fue autorizada posteriormente y verificada en GitHub. Commit `1c0604975f807ade714d837ab49d71e2e4db517f` en `design/user-identity-association-v1`; checkout limpio y HEAD local/remoto alineado. La VPS Pruebas sigue sin modificaciones ni despliegue. Al retomar, verificar el HEAD y el estado real antes de actuar.

## 1. Objetivo

Permitir que cualquier IA o desarrollador retome el proyecto desde su último estado válido aunque el chat original se haya perdido, borrado o sustituido. La fuente de continuidad es el repositorio y la evidencia de la VPS, no la memoria de una conversación.

## 2. Mensaje para iniciar un chat nuevo

Copia y pega el siguiente texto en el nuevo chat:

~~~text
CONTINUAR PROYECTO XRAY CORE MANAGER

Necesito recuperar y continuar el proyecto exactamente desde su último punto de control documentado.

Repositorio oficial:
https://github.com/Jaok04/xray-core-manager

Rama autorizada:
design/user-identity-association-v1

No modificar la rama main.

Rutas oficiales de la VPS:
- Documentación normativa canónica versionada: `/opt/xray-manager/Xray-Normativa` (en GitHub: `Xray-Normativa/`).
- Copia maestra de respaldo en la VPS: `/root/Xray_Manager_Documentacion_Final_2026-10-31`.
- Proyecto en desarrollo: /opt/xray-manager

Primero lee, en este orden:
1. AGENTS.md
2. PROJECT_STATE.md
3. docs/CONTINUIDAD_DEL_PROYECTO.md
4. docs/PUNTO_CONTROL_ACTUAL.md
5. HISTORY.md

Después realiza una auditoría de recuperación sin modificar archivos:
- consulta el HEAD real de la rama autorizada;
- verifica el estado y contenido de /opt/xray-manager;
- comprueba si la VPS tiene .git; no presupongas que sí;
- consulta la documentación normativa;
- contrasta los archivos y hashes de GitHub y VPS;
- identifica diferencias, cambios sin publicar y estados inciertos;
- recupera el estado de cada etapa y el último punto de control.

Distingue IMPLEMENTADO, VERIFICADO, PUBLICADO, SINCRONIZADO y ACEPTADO. No presentes pruebas históricas como si se hubieran ejecutado ahora.

No implementes, publiques, sincronices ni modifiques nada durante la auditoría. Presenta el informe y espera mi autorización explícita para el siguiente paso.
~~~

## 3. Orden de lectura

1. AGENTS.md: reglas obligatorias para la IA.
2. PROJECT_STATE.md: fotografía consolidada del estado y las etapas.
3. Este documento: procedimiento de recuperación y reanudación.
4. docs/PUNTO_CONTROL_ACTUAL.md: tarea exacta en la que se detuvo el trabajo.
5. HISTORY.md: decisiones e hitos cronológicos.
6. `Xray-Normativa/` y los documentos técnicos específicos de la etapa que se vaya a trabajar.
7. `docs/REGLA_CONTRASTE_DOCUMENTACION_PRELIMINAR.md` y `docs/REGLA_AUDITORIA_INTEGRAL_CIERRE_ETAPAS.md`.

## 4. Auditoría de recuperación obligatoria

Antes de proponer implementación:

### GitHub
- Confirmar que existe el repositorio y la rama autorizada.
- Consultar el HEAD actual de design/user-identity-association-v1.
- Registrar SHA, mensaje y fecha del último commit.
- Revisar los archivos de continuidad y los archivos técnicos relevantes.
- Confirmar que main no se ha modificado.

### VPS
- Inspeccionar /opt/xray-manager.
- Comprobar explícitamente si existe .git.
- Si no existe .git, tratarla como copia de trabajo sin rama/commit verificables.
- Inventariar módulos, configuración, pruebas y documentación.
- Revisar cambios locales y fechas, sin sobrescribir nada.
- Leer la documentación normativa en `Xray-Normativa/`; comparar sus SHA-256 con la copia de respaldo `/root/Xray_Manager_Documentacion_Final_2026-10-31`.

### Contraste
- Comparar archivos por contenido y SHA-256 cuando sea posible.
- Separar coincidencias, divergencias, archivos solo locales y archivos solo remotos.
- No corregir diferencias automáticamente.
- No asumir que una diferencia de hash con texto aparentemente igual carece de importancia; revisar bytes, codificación, saltos de línea y final de archivo.
- Identificar cualquier cambio no publicado o no sincronizado.

## 4.1 Contraste normativo obligatorio antes de implementar

Antes de iniciar cualquier etapa o tarea de implementación, consulta directamente la documentación preliminar aprobada en `Xray-Normativa/` del repositorio y contrástala punto por punto con el estado real de GitHub, la VPS, el código, los catálogos, las pruebas y la documentación técnica. Presenta el informe de conformidad, omisiones y divergencias antes de editar.

Las mejoras son posibles, pero toda mejora o cambio respecto del alcance aprobado debe justificarse, describir sus impactos y alternativas, y recibir autorización expresa del propietario antes de modificar diseño o código. No infieras autorización por silencio, continuidad de la conversación ni aprobaciones anteriores de otras tareas. Si la fuente no está disponible o existe una contradicción relevante, detente y solicita aclaración.

Procedimiento completo y vinculante: `docs/REGLA_CONTRASTE_DOCUMENTACION_PRELIMINAR.md`. Esta regla complementa AGENTS.md y es de cumplimiento obligatorio para cualquier IA o colaborador.


## 4.2 Custodia inmutable de Xray-Normativa

La carpeta `Xray-Normativa/` contiene la documentación maestra normativa aprobada. **Está prohibido modificar, corregir, reformatear, renombrar, mover, eliminar o sustituir cualquiera de sus archivos sin consentimiento previo, explícito y específico del propietario.** La autorización para implementar o publicar código no incluye autorización para alterar la normativa. Ante errores, ambigüedades o mejoras, conservar los originales y presentar una propuesta separada; esperar consentimiento expreso. Toda modificación autorizada debe quedar justificada y registrada en `HISTORY.md`.

Antes de iniciar cada etapa, subetapa o módulo, se debe contrastar su alcance punto por punto con `Xray-Normativa/`, identificar conformidades, ausencias, divergencias y decisiones pendientes, y presentar el resultado antes de editar o implementar. La copia `/root/Xray_Manager_Documentacion_Final_2026-10-31` se conserva en la VPS como respaldo; comprobar sus hashes frente a la carpeta versionada cuando esté disponible. Si hay diferencias, no resolverlas automáticamente: informar y solicitar decisión.

## 4.3 Auditoría integral obligatoria antes de cerrar cualquier etapa

Regla permanente del propietario: ninguna etapa puede declararse TERMINADA/COMPLETADA si no se han auditado y documentado técnicamente todos sus puntos, subpuntos, módulos, submódulos y componentes internos. No basta con cerrar un protocolo, completar una funcionalidad, pasar pruebas, publicar o sincronizar.

Antes de proponer un cierre:
- construir el inventario completo desde la documentación preliminar aprobada;
- trazar cada requisito hacia diseño, implementación, pruebas y evidencia;
- auditar cada elemento individualmente, incluyendo comportamiento, diseño, código, datos, seguridad, errores, integración, pruebas y documentación técnica aplicables;
- identificar explícitamente ausencias, incompletitudes, divergencias, elementos no verificados, riesgos y decisiones pendientes;
- completar la documentación técnica de cada punto/módulo y la regresión integral de la etapa;
- emitir un informe final de auditoría y obtener aceptación formal expresa del propietario.

Cualquier elemento sin auditoría, documentación o evidencia suficiente bloquea el cierre, salvo excepción específica autorizada y documentada por el propietario. Un módulo sí puede cerrarse individualmente, pero la etapa permanece ABIERTA hasta superar la puerta integral.

Documento operativo vinculante: `docs/REGLA_AUDITORIA_INTEGRAL_CIERRE_ETAPAS.md`. Debe leerse junto con la regla de contraste previo; ambas son obligatorias y no se sustituyen entre sí.

## 5. Cómo reanudar el desarrollo

Después de la auditoría:

1. Presentar el estado real y las incertidumbres.
2. Identificar el siguiente paso permitido por la documentación normativa.
3. Señalar qué archivos se modificarían y por qué.
4. Explicar las pruebas previstas y el riesgo.
5. Esperar autorización explícita del propietario.
6. Implementar únicamente el alcance aprobado.
7. Probar y documentar el resultado.
8. Actualizar los documentos de continuidad.
9. Publicar en la rama autorizada si se autorizó la publicación.
10. Verificar GitHub y la VPS por separado.

## 6. Reconciliación segura de GitHub y VPS

La VPS puede no ser un checkout Git. En ese caso, la sincronización debe hacerse como transferencia controlada de archivos:
- comparar antes de copiar;
- conservar una copia de seguridad de los archivos destino que vayan a reemplazarse;
- no sobrescribir archivos divergentes sin resolución;
- verificar el SHA-256 de origen y destino después de transferir;
- registrar la fecha, los archivos y el método utilizado.

Si la VPS tiene .git en una sesión futura, no asumir que está limpia. Inspeccionar branch, status, remotos y commits antes de cualquier operación.

## 7. Actualización obligatoria tras cada cambio aprobado

Todo cambio que se implemente y sea aprobado debe cerrar con la actualización de la continuidad y la sincronización del repositorio con GitHub. Es una regla permanente: no debe depender de que el propietario vuelva a solicitarla en cada tarea. La aprobación del alcance incluye completar el ciclo de documentación, commit y publicación en la rama autorizada, salvo que el propietario indique expresamente una restricción distinta.

Al cerrar cada cambio aprobado:
- **PROJECT_STATE.md:** actualizar la fotografía global cuando cambie el estado, alcance o avance del proyecto.
- **docs/PUNTO_CONTROL_ACTUAL.md:** actualizar el punto exacto de reanudación, lo completado, lo pendiente y la siguiente acción permitida.
- **HISTORY.md:** añadir una entrada cronológica con el cambio, la aprobación/decisión, pruebas y commit; nunca borrar entradas anteriores.
- **AGENTS.md:** actualizar únicamente cuando se apruebe o cambie una regla permanente para agentes.
- **Este documento:** actualizar únicamente cuando cambie el procedimiento de continuidad, recuperación o sincronización.
- **Documentación técnica afectada:** mantenerla alineada con el comportamiento real del código.
- **Documentación normativa:** no modificarla sin aprobación expresa del propietario.

### 7.1 Verificación y publicación

1. Ejecutar las pruebas pertinentes y registrar resultados reales. Anotar las pruebas no ejecutadas y el motivo; nunca presentar pruebas históricas como recién ejecutadas.
2. Revisar el diff completo y validar formato, sintaxis y consistencia de los documentos.
3. Crear un commit descriptivo con los cambios aprobados.
4. Publicar en `design/user-identity-association-v1`; nunca en `main`.
5. Verificar el SHA remoto y los archivos publicados.
6. Verificar que `/opt/xray-manager` coincide con el estado publicado y queda limpio. Si hay divergencias, detener la sincronización destructiva, preservar los cambios y documentar el bloqueo.
7. Informar por separado los estados IMPLEMENTADO, VERIFICADO, ACEPTADO, PUBLICADO y SINCRONIZADO.

No se cierra la tarea mientras falte la actualización documental o la sincronización, excepto cuando exista una restricción explícita o un bloqueo técnico; en ese caso, el pendiente debe quedar claramente registrado.

## 8. Regla de recuperación

Si los archivos de continuidad contradicen el código o la documentación normativa, no elijas una versión por intuición. Informa la contradicción, conserva ambas evidencias y pide una decisión cuando afecte requisitos o comportamiento.


## Diseño de persistencia segura VLESS — 2026-11-02

El diseño arquitectónico está en docs/DISEÑO_PERSISTENCIA_SEGURA_VLESS.md y fue aprobado por el usuario el 2026-11-02. P1 está publicado; P2 está en implementación. La clave maestra real aún no se ha generado.

Hallazgo de seguridad: el asistente actual entrega la clave privada REALITY a jq mediante --arg; corregir esa exposición a argumentos de proceso será requisito de la fase de implementación.

## P1 — Infraestructura criptográfica VLESS (2026-11-02)

P1 está implementada en scripts/vless_crypto.py y probada mediante tests/vless_crypto.sh. La dependencia python3-cryptography quedó formalizada en install.sh y modules/system_admin.sh. La clave maestra real no se ha generado en la VPS; P3 ya permite generarla de forma idempotente durante el primer guardado real de una modalidad con secreto. Las funciones ensure_master_key, load_master_key, encrypt_secret, decrypt_secret, write_encrypted_blob y read_encrypted_blob forman la API inicial. El paso siguiente es P2: almacén versionado de configuración no secreta, referencias de secretos y consistencia transaccional con el catálogo.


### Actualización 2026-11-02 — P2 en curso

Se implementó inicialmente `scripts/vless_config_store.py` con esquema neutral VLESS versión 1, revisiones inmutables, publicación atómica de referencias bajo el bloqueo compartido y auditoría sin borrado automático. `tests/vless_config_store.sh` PASS. P2 no está completado: quedan pruebas de interrupciones/concurrencia, suite completa y auditoría final. No se activó runtime ni se creó la clave maestra real.

P2: `tests/*.sh` 25/25 PASS; pruebas específicas incluyen interrupción antes de publicar catálogo (huérfano detectable) y dos escritores concurrentes. `install.sh --check`, sintaxis, py_compile, ShellCheck, shfmt y diff PASS. El campo `secret_ref` queda reservado como null hasta P3.

### P3 — integración de persistencia segura VLESS (implementada y verificada)

Se integró guardado bajo confirmación desde el asistente, cifrado AES-256-GCM de claves privadas TLS/REALITY, referencias versionadas en catálogo/configuración y recuperación temporal para validación. Nuevo `scripts/vless_prepare_config.py`; `vless_config_store.py` ahora admite secretos cifrados y auditoría de blobs. El asistente deja de pasar la clave REALITY como `jq --arg` y usa `--rawfile`. Pruebas focales REALITY/TLS/recuperación PASS. Borradores no se activan. Suite completa `tests/*.sh` 25/25 PASS; `install.sh --check`, `bash -n`, `py_compile`, ShellCheck, shfmt y `git diff --check` PASS. Clave maestra real de VPS no generada. P3 aún no publicada en GitHub.

### P4 — backup y recuperación segura VLESS (COMPLETADA Y ACEPTADA el 2026-11-02)

El subsistema incluye backup de datos/manifiesto/SHA256SUMS, paquete de recuperación scrypt + AES-256-GCM, verificación, restauración confirmada y menú. La corrección registra `had_connections`/`had_secrets`, fuerza `fsync` de los directorios padres tras renombrados y recupera journals nuevos y legacy de forma conservadora.

`tests/vless_backup_journal_crash_matrix.sh` cubre 32 interrupciones abruptas en fases y renombrados, con las cuatro combinaciones de existencia previa de ambos directorios. `tests/vless_backup_journal.sh` cubre journal legacy y destino originalmente ausente. `tests/vless_backup_restore_secrets.sh` comprueba restore de blobs REALITY/TLS con el certificado TLS externo ausente, dependencia declarada y runtime inactivo. La suite completa final tras esta revisión registró 31/31 PASS; `install.sh --check`, sintaxis Bash, `py_compile`, ShellCheck, shfmt y `git diff --check` PASS. No se creó backup operativo ni se accedió a la clave maestra real.
Publicación GitHub: `90766d4cb8000ed1f94fb808b80f18483d5778cb`; árbol `cfdb26fd7716f622127ba5d7784884df58799b4c`; VPS sincronizada con `origin`.

**P4 COMPLETADA:** journal robusto, límites agregados, validación autónoma del payload y cierre TOCTOU implementados; suite 32/32 PASS y aceptación formal del propietario el 2026-11-02. Ver `docs/P4_BACKUP_RECUPERACION_VLESS.md`.


## Incidente de pruebas — EOF en menús y crecimiento de /tmp (2026-11-02)

Se investigó una alerta real de disco al 95–99.9%. La auditoría de la VPS encontró un archivo de salida de 20,465,770,496 bytes dentro de `/tmp/tmp.oaFf5wTZwt/connections-action-error.out` y un proceso huérfano que mantenía abierto otro archivo ya eliminado de aproximadamente 925 MB. El proceso se detuvo de forma ordenada y se eliminó únicamente ese directorio temporal, después de verificar que no había handles abiertos. El disco quedó en 3.7 GB usados, 71 GB libres (5%). No se modificaron datos persistentes, configuraciones ni runtime.

Causa técnica confirmada: `ui_read_option()` convertía EOF en una cadena vacía y devolvía éxito. Los menús dentro de `while true` interpretaban esa cadena como opción inválida y volvían a imprimir el menú indefinidamente. Se corrigió el contrato para devolver estado 1 en EOF, limpiar la variable destino y hacer que los consumidores abandonen el menú/flujo actual de forma ordenada. También se protegieron los prompts de identificador del menú de backup VLESS.

La regresión quedó cubierta en `tests/stage1_menu.sh`: EOF directo en menús principales y secundarios, EOF anidado al navegar conexiones, y límite de salida de 1 MiB para que una regresión no vuelva a llenar el disco. La prueba `tests/vless_backup_restore_secrets.sh`, que ya estaba en la VPS sin seguimiento Git, se revisó y ejecutó PASS; se incorpora al repositorio en este cierre.

Resultados ejecutados: suite completa `tests/*.sh` 30/30 PASS; `install.sh --check`, `bash -n` de todos los `.sh`, ShellCheck de módulos y pruebas modificados, `shfmt -d -i 4 tests/stage1_menu.sh` y `git diff --check`: PASS. Los directorios `/tmp/tmp.u7Vq57eHNx` (282 MB) y `/tmp/tmp.EsxO527Ihe` (47 MB) se inspeccionaron; contienen salidas históricas de pruebas de menú V2 con repetición por EOF, pero se conservaron y no se borraron.

El cambio quedó IMPLEMENTADO y VERIFICADO. Publicación confirmada en GitHub, rama `design/user-identity-association-v1`, commit `fa7242a61248a71b64552511d1db932ebbc8d7d0`. El árbol Git remoto `b03db9b450288eccbf61e761655f286763df3a70` coincide exactamente con el árbol del commit local `b520c53bd5a32007b30519e0756fce13fe8916b5`: los 17 archivos y sus modos son idénticos. La VPS no pudo hacer `git push`/`git fetch` por falta de autenticación SSH y HTTPS; por ello los identificadores de commit local/remoto difieren y la referencia local `origin/design/user-identity-association-v1` permanece desactualizada en el commit base anterior. No se debe volver a aplicar el cambio; en una sesión con autenticación Git disponible, reconciliar la referencia local con el HEAD remoto sin duplicar commits.

## 2026-11-02 — autenticación SSH y reconciliación de referencias

Se creó una clave SSH Ed25519 dedicada a este repositorio y se registró en GitHub como Deploy Key de solo lectura (sin permiso de escritura). La VPS autentica correctamente mediante el alias `github.com-xray-core-manager`; la URL `origin` de este checkout usa ese alias y los demás repositorios/configuraciones SSH no se modificaron. `git fetch` se completó correctamente. Se verificó que el árbol local anterior y el árbol remoto eran idénticos (`b6ed32ae1ff32dc4c8c6953a2d1eec48159b1d08`), por lo que se movió únicamente la referencia local de la rama con comprobación del SHA anterior, sin resetear ni sobrescribir archivos. Estado final: `design/user-identity-association-v1` y `origin/design/user-identity-association-v1` apuntan a `5ade7feda328ff4a4f6796fd7ab263237b40dbfa`; working tree limpio y sin divergencia. Las notas anteriores sobre falta de autenticación y refs obsoletas quedan superadas por esta verificación. La clave SSH anterior se conservó intacta. La Deploy Key nueva es de solo lectura; las publicaciones futuras deberán seguir usando el mecanismo autorizado de GitHub API u otro acceso de escritura expresamente configurado.


### Actualización P4 — auditoría de límites y TOCTOU (2026-11-02)

Se implementó límite agregado de 512 MiB sin comprimir en recolección, creación, verificación y extracción. El lector de payload valida independientemente rutas, traversal, tipos regulares, enlaces, duplicados, cantidad, tamaños y hashes. La restauración verifica y lee el backup y la clave, y extrae el payload únicamente después de adquirir `lifecycle.lock` e `integrity.lock`; el hash se vuelve a comprobar sobre los bytes usados. Nueva prueba `tests/vless_backup_limits.sh` PASS; suite completa posterior 32/32 PASS. P4 quedó COMPLETADA tras la aceptación formal del propietario el 2026-11-02. No se creó backup operativo ni se accedió a la clave maestra real.


### Cierre formal P4 — 2026-11-02

El propietario aceptó las correcciones adicionales de seguridad. La etapa P4 de backup y recuperación segura VLESS queda **COMPLETADA Y ACEPTADA**. Verificación final: suite `tests/*.sh` 32/32 PASS; `install.sh --check`, `bash -n`, `py_compile`, ShellCheck, shfmt y `git diff --check` PASS. El commit de implementación está publicado y sincronizado en la rama del proyecto. El alcance no incluye activar runtime, reiniciar Xray, abrir puertos, cambiar firewall ni desplegar certificados externos.


## VMess — continuidad de implementación (2026-11-02)

El diseño VMess y su implementación fueron autorizados por el propietario, incluyendo HTTPUpgrade-TLS. El trabajo local en `/opt/xray-manager` contiene modelo, adaptador Xray-core 26.10.31, asistente, preparación de configuración, almacén cifrado y pruebas. La matriz de 14 modalidades pasó `xray run -test`; suite completa histórica: 36/36 PASS (la reejecución actual del 2026-11-02 fue 38/38; ver informe vigente). También pasaron `bash -n`, `py_compile`, ShellCheck a nivel warning, shfmt de archivos VMess nuevos, `install.sh --check` y `git diff --check`. Los cambios están publicados y sincronizados en la rama autorizada, pero no aceptados como módulo completo; consultar `docs/PUNTO_CONTROL_ACTUAL.md`.

### Separación del almacenamiento VMess

La persistencia VMess se ubica en `/var/lib/xray-manager/vmess/`, con `configurations/` y `secrets/` privados. El catálogo común continúa en `/var/lib/xray-manager/connections/connections.json`, pero VMess solo usa `vmess_configuration_ref`, `vmess_secret_ref`, `vmess_configuration_revision` y `vmess_configuration_schema_version`. No cambiar los campos VLESS ni `scripts/vless_backup.py` como parte de esta tarea. El bloqueo de integridad continúa compartido para serializar escrituras del catálogo.

P4 VLESS no incluye el almacén VMess separado. La restauración VLESS ahora combina las entradas VLESS del backup con las entradas VMess vigentes y valida sus referencias; los archivos del almacén VMess permanecen intactos. Esta corrección posterior se documenta en la sección 9 de `docs/P4_BACKUP_RECUPERACION_VLESS.md`. Backup/restore VMess independiente debe diseñarse y aprobarse por separado.

Los usuarios VMess todavía se introducen manualmente; la asociación con identidades globales pertenece a Etapa 3 y no debe implementarse dentro de esta tarea sin su definición/autorización.

### Estado de publicación

La implementación VMess y el aislamiento fueron publicados tras autorización expresa: commit `c20277c04b9417f2e22b285891fb3f348ea8e8f4` en `design/user-identity-association-v1`. La Deploy Key SSH de la VPS es de solo lectura; la publicación se efectuó mediante GitHub API y luego la VPS hizo fetch/reset para igualar HEAD local/remoto. No se modificó la rama `main`. No tocar runtime, firewall, puertos ni servicio. La Etapa 2 continúa abierta.

## Cierre técnico VMess — 2026-11-02

La auditoría de cierre contrastó el módulo con la especificación funcional Etapa 2 revisión 1.3 y con el diseño aprobado en `docs/DISEÑO_TECNICO_VMESS.md`. El módulo VMess quedó IMPLEMENTADO y VERIFICADO según la auditoría histórica de esa fecha. Este estado histórico fue revisado por la auditoría integral del 2026-11-02, que detectó F-01–F-04 y F-05 live no verificado; consultar la actualización vigente al final de este documento y los informes de auditoría.

Evidencia de esta revisión:
- Xray-core 26.10.31 (build `a4a3dff`): 14/14 modalidades aceptadas con `xray run -test`.
- Navegación del menú: las 14 combinaciones recorridas individualmente.
- Pruebas negativas: certificado/clave TLS ausentes, symlink, PEM inválido, par certificado-clave no coincidente, REALITY incompleto/short ID inválido/clave inválida, campos incompatibles y combinación modelo-seguridad inválida.
- Se endureció el adaptador VMess para validar PEM y correspondencia criptográfica de certificado y clave privada con la biblioteca `cryptography`. La prueba detectó que `xray run -test` no rechaza por sí solo un certificado PEM malformado; por eso la validación se realiza antes de generar el JSON.
- Suite completa `tests/*.sh`: 36/36 scripts PASS.
- `bash -n`, `python3 -m py_compile scripts/*.py`, `./install.sh --check`, ShellCheck warning, shfmt y `git diff --check`: PASS.

Cambios de esta revisión:
- `modules/vmess_xray_26_10_31.sh`
- `tests/xray_vmess_integration.sh`
- `tests/stage2_navigation.sh`
- `docs/DISEÑO_TECNICO_VMESS.md`
- `PROJECT_STATE.md`
- `docs/PUNTO_CONTROL_ACTUAL.md`

Límites conservados:
- No se probó conectividad extremo a extremo ni se activaron borradores.
- No se tocó runtime, servicio, firewall, puertos, certificados desplegados ni P4 VLESS.
- Backup/restore VMess requiere diseño independiente.
- Integración con identidades globales pertenece a Etapa 3.
- Etapa 2 sigue abierta; completar VMess no implica completar Trojan, Shadowsocks, Hysteria2 ni protocolos opcionales.

**Estado de acceso Git vigente:** la Deploy Key SSH de este repositorio tiene actualmente permiso de escritura y el alias `github.com-xray-core-manager` está configurado en la VPS. Las notas históricas anteriores que la describen como solo lectura quedan superadas por esta configuración posterior.

Publicación del cierre técnico confirmada en `design/user-identity-association-v1`: commit `ab76a57032faa9793a62348f865fba2c9a7d8f77`. La VPS hizo push y fetch del commit funcional y de la actualización documental; HEAD local/remoto se verificaron coincidentes y el árbol quedó limpio. Obtener el SHA vigente con `git rev-parse HEAD`. La Deploy Key SSH actual tiene permiso de escritura; la nota anterior de solo lectura es histórica y está superada.

El punto de reanudación exacto está en `docs/PUNTO_CONTROL_ACTUAL.md`. No iniciar Trojan hasta recibir la aceptación formal de VMess y efectuar el contraste específico de Trojan.


## 2026-11-02 — Bloque 1: preservar VMess durante restauración VLESS

El propietario aprobó el plan completo de correcciones para el cierre de VMess y autorizó iniciar por el Bloque 1. Se contrastó de nuevo la gobernanza, la documentación preliminar de Etapa 2 y el contrato P4 documentado. Se confirmó que `restore_data()` reemplazaba `connections/` con el catálogo histórico del backup; como el catálogo es compartido, esto podía perder entradas VMess actuales.

Se implementó en `scripts/vless_backup.py` una combinación en staging bajo `lifecycle.lock` e `integrity.lock`: las conexiones VLESS proceden del backup y las VMess proceden del catálogo vigente. Las VMess históricas del snapshot no prevalecen. Se validan catálogo actual, IDs únicos, modalidades VMess, referencias de configuración/secreto y archivos regulares con permisos seguros. Colisiones VLESS/VMess, catálogo corrupto, referencias rotas, protocolo desconocido o fallo de escritura staging detienen la operación antes de publicar. El almacén VMess separado no se modifica ni se incluye en el backup VLESS.

Se creó `tests/vless_restore_preserves_vmess.sh` con casos de VMess anteriores y posteriores al backup, referencias `vmess_*`, comprobación byte a byte del almacén, colisión de IDs, catálogo corrupto, refs rotas y fallo de escritura. Se ajustó `tests/vless_backup_journal_crash_matrix.sh` para que su estado previo sea un catálogo VMess JSON válido y se conservaron las 32 pruebas de interrupción/rollback. Suite completa: 38/38 scripts PASS. `python3 -m py_compile scripts/*.py`, `bash -n` de todos los scripts Bash, `install.sh --check`, ShellCheck warning de las pruebas modificadas y `git diff --check`: PASS.

Estado del Bloque 1: IMPLEMENTADO, VERIFICADO, PUBLICADO y SINCRONIZADO; commit `c890b5b5362e17e439f198b9b8bbbdbe0af0c653`. La aceptación formal específica permanece pendiente. P4 conserva su aceptación histórica para el alcance original; la corrección se registra como incremento posterior. No se creó backup operativo ni se accedió a la clave maestra real. No se tocó runtime, servicio, firewall, puertos ni certificados desplegados. La documentación normativa preliminar se mantuvo intacta.

Próximo paso del plan aprobado: Bloque 2, correcciones del asistente VMess. Etapa 2 sigue ABIERTA y VMess no se considera ACEPTADO hasta completar el proceso de cierre.


## 2026-11-02 — Bloque 2: advertencias y resumen del asistente VMess

El asistente VMess ahora informa, antes de solicitar parámetros, que el desfase horario cliente/servidor no debe superar 120 segundos. Muestra una advertencia WebSocket (Xray 26.10.31 lo marca obsoleto/no recomendado y recomienda migrar a XHTTP H2/H3) y una advertencia HTTPUpgrade: Xray 26.10.31 lo marca obsoleto/no recomendado, podría retirarlo y recomienda XHTTP H2/H3; ambos transportes pueden presentar patrones identificables. Ambas modalidades se conservan conforme al alcance aprobado.

Después de `xray run -test` y antes del consentimiento de guardado, se presenta el resumen de conexión: nombre/ID, dirección/puerto, modalidad, transporte/seguridad, usuarios y parámetros aplicables de transporte, TLS o REALITY. No se imprime el contenido de claves privadas. La ruta TLS se muestra como parámetro; para REALITY se indica sólo que la clave está presente y se almacenará cifrada.

Durante la prueba REALITY se detectó una colisión de nombre en las funciones `connections_vmess_read*`: el parámetro local `target` ocultaba el destino del llamador al intentar capturar el target REALITY. Se renombró el parámetro local a `target_name` en las funciones de lectura; la captura REALITY y el resumen quedaron verificados.

`tests/vmess_assistant.sh` cubre avisos, campos del resumen, orden previo al guardado y ausencia de material secreto TLS/REALITY. Pruebas focales `tests/vmess_assistant.sh`, `tests/vmess_model.sh`, `tests/xray_vmess_integration.sh` (14/14 y negativos) y `tests/stage2_navigation.sh` (14/14): PASS. `bash -n` y ShellCheck warning de archivos modificados: PASS. Estado Bloque 2: IMPLEMENTADO, VERIFICADO, PUBLICADO y SINCRONIZADO en `9d03d4b4e77e1a160b94ee2c2f3c74487977e362`. Suite completa se repetirá en Bloque 3.


## 2026-11-02 — Bloque 3: cobertura de pruebas VMess

Se amplió `tests/vmess_assistant.sh` para probar cancelación y EOF en dirección/UUID/path/confirmación, slots inválidos, UUID inválido/duplicado, puerto inválido y modalidad incompatible. Se verifica que las entradas fallidas y la cancelación después del resumen no alteran el catálogo.

Se creó `tests/vmess_persistence_hardening.sh`: store/read TLS AES-256-GCM y AAD; permisos; clave maestra ausente sin regeneración en read; clave inválida en read/store; ciphertext/tag alterado sin plaintext; referencias de configuración y secreto rotas; huérfanos; symlinks; fallos antes de publicar el catálogo; y concurrencia de escritores con IDs distintos y misma conexión/revisiones r1-r2.

La prueba de fallo inyectado confirma que una interrupción después de escribir archivos y antes de publicar el catálogo deja huérfanos detectables, mientras el catálogo permanece intacto. No hay rollback transaccional VMess en el diseño aprobado; `audit` detecta los huérfanos y no los borra automáticamente. No se modificó código de producción en este bloque. La rama autorizada y la VPS quedaron sincronizadas en `08b2044dd820eb465afecbb6ec66fccefe6397a5`; la rama `main` no fue modificada.

Suite completa `tests/*.sh`: 38/38 PASS. También PASS: `python3 -m py_compile scripts/*.py`, `bash -n` de todos los scripts Bash, `install.sh --check`, ShellCheck warning de los archivos modificados y `git diff --check`. Estado Bloque 3: IMPLEMENTADO, VERIFICADO, PUBLICADO y SINCRONIZADO en `08b2044dd820eb465afecbb6ec66fccefe6397a5`.


## 2026-11-02 — Bloque 4: etiquetas explícitas de modalidades VMess

Se actualizó `modules/connections.sh`: VMess-WS se muestra como `VMess-WS (sin TLS adicional)` y VMess-TLS como `VMess-TLS (RAW/TCP + TLS)`, tanto en el menú como en `connections_mode_label` usado por listados. No se cambiaron IDs, modalidades ni el orden. `tests/stage2_navigation.sh` comprueba las etiquetas y conserva las verificaciones de las 14 combinaciones.

Se confirmó que `README.md` define `shfmt -d -i 4 -ci` para archivos Bash seleccionados. No se reformateó el árbol: la aplicación general generaría diffs ajenos al alcance y el proyecto no declara una política para reformateo global. La regla permanece limitada a los archivos explicitados en README.

Cambios implementados y verificados: pruebas focales y suite completa 38/38 PASS; controles estáticos y shfmt baseline PASS. Auditoría integral de VMess pendiente. Cambios publicados y sincronizados en `9528f4b00f6b9654f7236050bbadfd8f9415bf69`.

Publicación Bloque 4: commit `9528f4b00f6b9654f7236050bbadfd8f9415bf69`; HEAD local/remoto y árboles verificados idénticos. `main` no fue modificada.


## Auditoría integral VMess — 2026-11-02 (hallazgos iniciales; superados por el bloque correctivo posterior)

El informe vigente y la matriz requisito→diseño→implementación→prueba→evidencia son docs/AUDITORIA_INTEGRAL_VMESS_2026-11-02.md y docs/MATRIZ_TRAZABILIDAD_VMESS_2026-11-02.md. La suite actual pasó 38/38; Xray validó 14/14 y rechazó 10 casos negativos. Sintaxis Bash, AST Python, ShellCheck, install check, diff check y el gate shfmt definido en README pasaron.

Hallazgos pendientes: F-01 la clave TLS root-owned 0644 se acepta; F-02 read/audit no detectan incoherencia de revisión/schema; F-03 cancelar el asistente deja el registro base draft creado previamente; F-04 el modelo acepta email duplicado que el almacén rechaza; F-05 el estado live no se ha inicializado (catálogo vacío, almacén VMess y master key ausentes). No se corrigió código. Solicitar autorización antes de modificar.

Auditoría y matriz publicadas/sincronizadas en commit 88f82f2f9d7d19833b814d9a810dedb4bc3edc8c de la rama autorizada; main no modificada. scripts/__pycache__/ permanece sin seguimiento y no se eliminó.


## Bloque correctivo VMess F-01 a F-04 — 2026-11-02

F-01 exige clave TLS root:root 0600 y un solo enlace duro en adaptador/preparador; negativos 0644/0640/0400, grupo no root y hardlink, positivo 0600. F-02 valida revisión de catálogo/referencia, schema catálogo/documento y revisión de referencia secreta en store/read/audit, y detecta metadatos parciales. F-03 cancela con estado no exitoso y el flujo común retira sólo el draft VMess vacío/no aplicado bajo bloqueo; preserva otras entradas y configuraciones ya publicadas. F-04 modelo/adaptador/almacén rechazan emails duplicados con comparación exacta consistente.

Suite 39/39 PASS; Xray 14/14 modalidades y 16/16 negativos PASS. bash -n, py_compile, ShellCheck de archivos modificados, install.sh --check, gate shfmt README y git diff --check PASS. ShellCheck global informa warning preexistente SC2174 en tests/vless_backup_restore.sh:7, archivo VLESS sin cambios.

Corrección de código publicada en d2d33a32bdf5e21d1d35ad41d00bd0b116443cb7; actualización final de continuidad sincronizada en 0a39af5c2aa35bf853c05f3a864bcc362d86bf67. F-05 live permanece NO VERIFICADO: catálogo vacío, almacén VMess y clave maestra no inicializados. No se tocó runtime, firewall, puertos ni servicio. VMess no está aceptado; Etapa 2 abierta. Requiere autorización separada validar live y completar VM-38/39/40.


## Revalidación controlada — 2026-11-02

La VPS de desarrollo `/opt/xray-manager` fue confirmada accesible como root, en la rama autorizada y HEAD `4c87557e0aff4166c540c633effe5cb6dac40096`. Se añadió `tests/vmess_navigation_edge_cases.sh`; VM-38 lista vacía/[0], VM-39 entradas inválidas recuperables y VM-40 confirmación destructiva exacta pasan. Suite completa `tests/*.sh`: 40/40 PASS. La primera ejecución parcial de `port_collisions.sh` falló en la comprobación UDP; la repetición aislada y la suite completa posterior pasaron.

F-05 live queda pendiente de autorización específica para crear clave maestra y almacén VMess persistentes en esta VPS de desarrollo. No se crearon, ni se añadió conexión live. Xray no está instalado localmente; las pruebas de integración utilizaron el binario de validación 26.10.31 en caché. Servicio inactivo; no se tocaron runtime, firewall, puertos ni servicios.


## Validación live F-05 — 2026-11-02

El propietario autorizó la inicialización persistente controlada en la VPS de desarrollo. F-05/VM-46 quedó VERIFICADO LIVE: clave maestra compartida generada con 32 bytes `root:root 0600`; almacén VMess creado con directorios `root:root 0700`; borrador VMess-TLS guardado, leído/descifrado, recuperado por el asistente y validado con Xray 26.10.31. Auditoría limpia y alteración GCM rechazada sin plaintext. La conexión temporal y sus dos archivos versionados fueron retirados; catálogo vacío. Se conservan clave maestra y directorios VMess vacíos como estado inicial. Sin activación de runtime, cambios de firewall/puertos/servicios ni certificado desplegado. VM-47 conectividad cliente-servidor sigue NO VERIFICADA. Detalle: `docs/VALIDACION_LIVE_VMESS_F05_2026-11-02.md`.


## Validación cliente-servidor VM-47 — 2026-11-02

VM-47 quedó verificado en loopback local. El modelo y adaptador reales generaron la configuración VMess-TLS del servidor; un cliente Xray SOCKS estableció el túnel TLS/VMess y una solicitud HTTP llegó al destino, que respondió HTTP 200 con el marcador esperado. Configuraciones cliente y servidor `xray run -test`: PASS. Los procesos y listeners temporales se detuvieron. No se tocaron runtime, firewall, puertos públicos, catálogo ni servicio. No se probó cliente externo/WAN. Informe: `docs/VALIDACION_CLIENTE_SERVIDOR_VMESS_VM47_2026-11-02.md`.


## 2026-11-03 — Revalidación y punto de reanudación VMess

La revalidación se ejecutó en `/opt/xray-manager` sobre `design/user-identity-association-v1`. Suite completa `tests/*.sh`: 40/40 PASS; Xray 26.10.31: 14/14 modalidades y 16/16 casos negativos PASS. También pasaron `bash -n` para los archivos Bash VMess, `py_compile` para `vmess_config_store.py` y `vmess_prepare_config.py`, ShellCheck de módulos/pruebas VMess y `git diff --check`.

Se documentaron con supresión local SC2034 tres variables globales intencionales en `tests/vmess_creation_flow.sh` y `tests/vmess_navigation_edge_cases.sh`, consumidas dinámicamente por funciones de `modules/connections.sh` cargado con `source`; se conservaron las asignaciones. La matriz y auditoría aclaran VM-28 como VERIFICADO, VM-32 como atomicidad individual/concurrencia con límite multiarchivo y VM-33 como no aplicable porque el diseño no promete rollback transaccional.

La documentación normativa `Xray-Normativa/` se comparó con el respaldo `/root/Xray_Manager_Documentacion_Final_2026-10-31`: 14 archivos originales coincidentes; no se modificó ninguno. No se tocó runtime, firewall, puertos, certificados desplegados ni servicio.

**Punto exacto de reanudación:** expediente técnico VMess listo para que el propietario emita o deniegue la aceptación formal VM-48. Cliente externo/WAN no probado y no requerido por el diseño aprobado. Etapa 2 permanece ABIERTA; no iniciar Trojan antes de la aceptación formal de VMess y del contraste normativo específico de Trojan.


## 2026-11-03 — Punto de reanudación: integración VMess TLS centralizado parcial

La integración del Bloque 3 comenzó y se publicó como avance intermedio; no se debe confundir con su cierre. Consultar primero `docs/IMPLEMENTACION_VMESS_TLS_CENTRALIZADO_PARCIAL.md`.

- `scripts/vmess_config_store.py`: nuevas revisiones TLS guardan sólo `certificate_id`, exigen certificado central existente/activo y no crean secretos TLS por conexión. REALITY conserva su secreto individual.
- TLS histórico `{certificate_file, secret_ref}` sigue siendo legible para compatibilidad, sin migración ni borrado automático. Nuevas revisiones TLS deben usar el formato central.
- `scripts/vmess_prepare_config.py` emite el contrato TLS central; `scripts/vless_backup.py` conserva la lectura/validación de VMess TLS histórico al restaurar VLESS.
- `modules/vmess_assistant.sh` tiene adaptación preliminar para seleccionar ID central y pedir lease. El flujo interactivo TLS no tiene todavía cobertura integral y no debe considerarse terminado.
- `modules/vmess_xray_26_10_31.sh` aún requiere adaptación/endurecimiento para impedir rutas TLS arbitrarias y consumir sólo leases del resolutor.
- Pruebas focales: persistencia VMess, restauración VLESS preservando VMess, almacén central, resolutor, modelo, creación y aislamiento backup PASS. Sintaxis/compilación y `git diff --check` PASS. La suite global no se ha reejecutado tras este cambio.
- En VPS desarrollo no existe unidad/cuenta/grupo Xray; CLI real del resolutor falla cerrada. No se ha probado lectura de lease por Xray real.
- No se migraron históricos, no se importaron certificados reales, no se modificó runtime/servicios/firewall/puertos, no se tocó VPS de pruebas ni `Xray-Normativa/`.

**Siguiente paso exacto:** adaptar el generador VMess Xray al lease autorizado, después completar y probar asistente/recuperación/cleanup y backup/restore, ejecutar regresión integral y actualizar trazabilidad. No declarar Bloque 3 completado hasta cubrir todo lo anterior.


## 2026-11-03 — Continuidad: VMess TLS centralizado, avance posterior al commit 8d3b848

**Rama de trabajo:** `design/user-identity-association-v1`. El último commit remoto sigue siendo `8d3b848` hasta que el propietario autorice publicar esta actualización. No repetir el análisis de persistencia TLS central ya documentado; continuar desde el endurecimiento del adaptador y el asistente descrito aquí.

- `modules/vmess_xray_26_10_31.sh` ahora requiere `lease-id` como tercer argumento. En TLS sólo acepta `certificate.pem` y `private-key.pem` dentro del lease exacto, con manifiesto válido para `connection_id`, `protocol=vmess`, `certificate_id`, revisión, fingerprint y UID/GID. Rechaza rutas externas y leases reutilizados para otra conexión. Los archivos deben ser root:<grupo-servicio> 0640, el directorio del lease 0750.
- Nuevo `scripts/vmess_tls_lease_check.py` implementa la comprobación estructural del lease antes de construir JSON Xray.
- `modules/vmess_assistant.sh` pasa `--runtime-root` explícito tanto en creación como en recuperación; el `read` de VMess usa el catálogo central correcto. El ciclo limpia lease en éxito y fallo mediante trap. La recuperación de TLS histórico `{certificate_file, secret_ref}` falla cerrada y requiere migración controlada; la lectura histórica del store se mantiene.
- `scripts/vless_backup.py` verifica que un VMess TLS central preservado durante restore VLESS apunte a un recurso `managed`/`reference` activo en `certificates/catalog.json`. No copia ni modifica el almacén VMess ni el catálogo central.
- Tests nuevos/ampliados: `tests/vmess_tls_lease_assistant.sh`, `tests/xray_vmess_integration.sh`, `tests/vless_restore_preserves_vmess.sh`.
- Verificación: `tests/*.sh` 43/43 PASS; Xray 26.10.31 valida 14/14 modalidades usando fixtures de lease; el ciclo de recuperación/cleanup usa resolutor y Xray simulados; ShellCheck warning, Bash syntax, py_compile y `git diff --check` PASS.

**Límites importantes:** el CLI real del resolutor continúa fallando cerrado porque la VPS de desarrollo no tiene `xray.service` ni usuario/grupo Xray. No se demostró lectura de lease por Xray real. No hubo runtime apply ni despliegue. El backup VLESS sigue excluyendo VMess y el catálogo central; backup/restore compartido e independiente VMess continúan pendientes del bloque específico. Integración VLESS del resolutor sigue pendiente. No se migraron TLS históricos, no se importaron certificados reales y no se tocó la VPS de pruebas, firewall, puertos, servicios ni `Xray-Normativa/`.

**Estado:** IMPLEMENTADO PARCIALMENTE, VERIFICADO EN FIXTURES, NO PUBLICADO, NO SINCRONIZADO, NO ACEPTADO. `main` y `Xray-Normativa/` permanecen intactas.

**Siguiente paso:** completar la revisión de todos los caminos de persistencia/backup afectados y decidir el siguiente bloque de integración VLESS; antes de afirmar operatividad TLS real, disponer de una unidad Xray de desarrollo con identidad no privilegiada verificable y probar prepare → lectura real por Xray → cleanup. No tocar runtime de producción ni la VPS de pruebas sin autorización específica.


## 2026-11-03 — Integración VLESS TLS centralizado parcial

Se retomó el acceso a `/opt/xray-manager`; la VPS responde y permanece en `design/user-identity-association-v1`, HEAD `8d3b8482da369e902b32795dc3a36e5023d25e62`. Los cambios locales VMess anteriores se conservaron. La integración VLESS se realizó sobre los archivos vigentes, tras auditoría y contraste con `Xray-Normativa/02_Protocolos_Conexiones/Etapa_2_Protocolos.md` y YAML; `Xray-Normativa/` no se modificó.

- Nuevas revisiones TLS VLESS guardan sólo `certificate_id` y validan recurso central activo `managed`/`reference`; no generan secreto TLS por conexión. Lectura/auditoría admiten revisiones TLS históricas sin migrarlas ni borrarlas. REALITY mantiene secreto individual.
- `vless_prepare_config.py` emite el contrato central. El adaptador `vless_xray_26_10_31.sh` exige lease autorizado para TLS y rechaza rutas libres; `vless_tls_lease_check.py` valida manifest, conexión/protocolo, certificado/revisión/fingerprint, UID/GID y permisos.
- El asistente solicita ID central, persiste el borrador bajo confirmación, solicita lease y limpia en éxito/fallo. Restore central también usa lease; TLS histórico falla cerrado hasta migración.
- Backup/restore VLESS documenta dependencia central y rechaza restaurar si falta el catálogo o el recurso activo. No incorpora el almacén central ni sus secretos al backup VLESS.
- Se añadieron `tests/vless_tls_central_backup.sh` y `tests/vless_tls_lease_assistant.sh`, y se ampliaron pruebas de store, asistente y Xray. Suite global `tests/*.sh`: 45/45 PASS. Xray 26.10.31 aceptó 9/9 modalidades VLESS con fixtures. La prueba del asistente simula `systemctl`/Xray y verifica lectura POSIX por `www-data` más cleanup en éxito/fallo; no prueba un Xray real. Bash syntax global, py_compile, install check, ShellCheck warning de modificados y diff check PASS.

**Límite bloqueante:** la VPS de desarrollo no tiene una unidad Xray con `User`/`Group` explícitos y no privilegiados. El CLI del resolutor falla cerrado; el asistente guarda el borrador y no aplica runtime. No se probó lectura del lease por Xray real. No se tocaron runtime, servicio, firewall, puertos, certificados desplegados, VPS de pruebas ni normativa.

**Estado:** VLESS TLS central IMPLEMENTADO PARCIALMENTE y VERIFICADO EN FIXTURES; NO PUBLICADO, NO SINCRONIZADO, NO ACEPTADO. `main` intacta. No se ha autorizado commit/push. Informe: `docs/IMPLEMENTACION_VLESS_TLS_CENTRALIZADO_PARCIAL.md`.

**Siguiente paso exacto:** ampliar la matriz integrada de recuperación/cleanup para WS, gRPC y XHTTP TLS; después diseñar migración histórica versionada y backup/restore central compartido. Mantener REALITY separado y no tocar runtime sin autorización específica.


## 2026-11-03 — Matriz VLESS TLS, auditoría cruzada y diseños pendientes

Se amplió `tests/vless_tls_lease_assistant.sh`: además de creación RAW/TCP y cleanup tras éxito/fallo del Xray simulado, se ejecuta recuperación de las cuatro modalidades TLS (RAW/TCP, WS, gRPC y XHTTP), comprobando limpieza del lease tras cada recuperación. Durante esa prueba se encontró y corrigió un rechazo incorrecto de `path` en el adaptador `vless_ws_tls`; el adaptador ahora valida opciones exactas por modalidad. `tests/xray_vless_integration.sh` vuelve a validar WS-TLS con su path.

Auditoría cruzada VMess/VLESS: validadores de lease equivalentes salvo el protocolo declarado en manifest. Se alinearon las dos llamadas de preparación del asistente VMess para proporcionar rutas explícitas configurables de almacén central, catálogo, managed dir, secretos, lock y master key, en vez de depender parcialmente de defaults. Suite global final `tests/*.sh`: 45/45 PASS.

Se redactaron dos propuestas sin ejecutar: `docs/PLAN_MIGRACION_TLS_HISTORICO.md` (inventario de solo lectura, validación de pares/fingerprints, deduplicación, importación central, nuevas revisiones inmutables, journal y rollback) y `docs/PLAN_BACKUP_RESTORE_CENTRAL.md` (snapshot coordinado VLESS/VMess/certificados, dependencias reference, envoltura de secretos centrales y restore/rollback). Ambas están marcadas como propuestas no aprobadas.

No se migraron revisiones históricas, no se eliminó ningún blob, no se creó el backup compartido, no se modificó runtime, servicios, firewall, puertos, certificados desplegados, VPS de pruebas ni `Xray-Normativa/`. Sin commit ni push.


## 2026-11-03 — Continuidad: aprobación de migración histórica y backup compartido; preflight inicial

**Rama autorizada:** `design/user-identity-association-v1`. **HEAD de partida sincronizado:** `cd5095514f4a08bc2feca26d29f1fbdc3302db39`. GitHub y VPS estaban alineados antes de este trabajo. `Xray-Normativa/` permanece intacta.

El propietario aprobó los criterios de ambos bloques:

- Migración TLS histórica: VMess y VLESS; `managed` por defecto; `reference` sólo con confirmación expresa; certificados vencidos/no vigentes bloqueados; conservar revisiones y blobs históricos; backup verificable y autorización específica antes de cualquier lote real.
- Backup/restore compartido: reenvolver secretos con cifrado propio del backup y re-cifrarlos bajo la master key existente del destino; no incluir `master.key`; bloquear restore completo si faltan referencias externas; no sobrescribir datos posteriores al snapshot ni realizar merge automático ante conflictos.

**Implementación de migración:** nuevo `scripts/certificate_migration.py`, comando `plan --protocol all|vless|vmess`. Es estrictamente read-only: no crea locks/directorios, no importa certificados, no crea revisiones ni journals y no modifica stores. Valida las referencias/revisiones, permisos y archivos; usa el backend criptográfico específico VLESS o VMess; comprueba PEM, par, vigencia y fingerprints; agrupa pares duplicados y emite `READY`, `BLOCKED` o `ALREADY_CENTRAL`. Si existe el lock de integridad lo toma compartido y revalida hashes de entradas, incluyendo master key, antes de cerrar el plan. No muestra ni persiste claves descifradas.

Prueba nueva `tests/certificate_migration_plan.sh`: fixtures VLESS/VMess, sobres criptográficos diferentes, deduplicación cruzada, no escritura y ciphertext alterado bloqueado. Regresión completa: 46/46 archivos de prueba PASS; Bash syntax, `py_compile`, ShellCheck de prueba nueva y `git diff --check` PASS.

**Inventario real VPS implementación:** `/var/lib/xray-manager/connections/connections.json` contiene 0 registros; preflight `--protocol all` devuelve 0 candidatos TLS, 0 READY, 0 BLOCKED y 0 ALREADY_CENTRAL. La carpeta de configuración VLESS y el catálogo central TLS no existen actualmente; el preflight no los creó. No hay migración real.

**Hallazgo backup crítico:** `scripts/vless_backup.py backup-data` genera `tar.gz` y manifiesto con hashes; el tar no está cifrado integralmente. Los blobs de secretos sí están cifrados bajo la master key del host. `create-recovery` cifra la master key separadamente mediante scrypt + AES-256-GCM. Por tanto, el backup compartido necesita un contenedor cifrado integral nuevo; no debe describirse el backup VLESS actual como ya cifrado. El diseño v1.1 de `docs/PLAN_BACKUP_RESTORE_CENTRAL.md` define paquete compartido independiente, scrypt + AES-256-GCM y re-cifrado de secretos bajo la master key destino, sin escribir plaintext en staging.

Documentos actualizados: `docs/PLAN_MIGRACION_TLS_HISTORICO.md` v1.1, `docs/PLAN_BACKUP_RESTORE_CENTRAL.md` v1.1 y nuevo `docs/IMPLEMENTACION_PREFLIGHT_MIGRACION_TLS.md`.

**Pendiente:** implementar y probar backup/restore compartido; completar fase escritora de migración (importación idempotente, nuevas revisiones, publicación, journal, verify y rollback). Ningún certificado histórico fue migrado ni se creó backup compartido.

**Límites:** no se tocó runtime, servicio, firewall, puertos, certificados desplegados, VPS de pruebas ni `Xray-Normativa/`. No commit/push aún para este avance; `main` no se modificó. `scripts/__pycache__/` continúa no rastreado y excluido.

**Siguiente punto exacto:** terminar el contrato de backup compartido, especialmente el cifrado integral, reconstrucción de envelopes VLESS/VMess/certificados y preflight de conflictos, antes de habilitar la migración escritora.


## Publicación del preflight de migración TLS — 2026-11-03

El bloque anterior quedó publicado y sincronizado en GitHub y VPS de implementación: commit `631d7eda11615b692557a2e0958a8f318b81c223` (`feat(tls): add read-only historical migration preflight`), rama `design/user-identity-association-v1`. `origin/main` permanece en `656ecedc506a94a6461aee296b20871d51a38bf3`. El commit no contiene cambios en `Xray-Normativa/`; `git diff HEAD^ HEAD -- Xray-Normativa/` está vacío. `scripts/__pycache__/` permanece no rastreado y excluido.


## Continuidad — formato cifrado compartido v1 (2026-11-03)

El contenedor neutral se implementó en `scripts/shared_backup_format.py`; contrato detallado en `docs/FORMATO_CIFRADO_COMPARTIDO_V1.md` y plan actualizado en `docs/PLAN_BACKUP_RESTORE_CENTRAL.md` v1.2.

El módulo sólo cifra/descifra bytes opacos y no conoce protocolos ni escribe archivos. Usa scrypt fijo `N=2^15/r=8/p=1`, AES-256-GCM, salt 16 bytes, nonce 12 bytes, tag 16 bytes y AAD que autentica cabecera completa. El payload máximo es 512 MiB. La contraseña no se persiste ni se pasa por CLI.

**Compatibilidad futura:** VLESS, VMess, Trojan y otros protocolos pueden transportar su snapshot por el mismo contenedor. Cada protocolo debe tener un adaptador de snapshot/validación y usar su backend/AAD nativo para re-envolver secretos bajo la master key destino. No reutilizar sobres entre protocolos.

**Restricción normativa:** credenciales y claves privadas excluidas por defecto; incluir requiere selección, autorización y confirmación adicional. Historiales, validaciones, informes y logs excluidos. La futura UI/orquestación deberá hacer cumplir estas reglas.

**Verificación actual:** 47/47 `tests/*.sh` PASS; `py_compile scripts/*.py`, `bash -n` de shell modules/scripts, ShellCheck warning y shfmt focal, `git diff --check` PASS. No se ha generado un backup real ni se ha implementado snapshot/restore. No hubo cambios en runtime, servicios, firewall, puertos, master key, datos persistentes ni `Xray-Normativa/`.

**Siguiente punto:** definir el manifiesto interno y el snapshot lógico de datos actuales, resolver orden global de locks y diseñar adaptadores por protocolo antes de implementar el writer.


**Publicación del contenedor v1:** commit `164f91f9c9be8ab275da0b28a53b2314a636f1e2` en `design/user-identity-association-v1`; HEAD local/remoto coincide. Sin cambios a `Xray-Normativa/` ni `main`.

## Continuidad — política de metadatos VMess para backup compartido (2026-11-03)

La decisión del propietario queda registrada en docs/PLAN_BACKUP_RESTORE_CENTRAL.md §10.1 (v1.3):

- Excluir el UUID VMess por defecto porque es una credencial de autenticación.
- Conservar email y level como metadatos/configuración dentro del payload cifrado. email no autentica ni es necesario para el cliente externo.
- No exponer email en el manifiesto externo ni en logs.
- Marcar los registros sin UUID como incompletos/no restaurables íntegramente hasta que la credencial se aporte mediante flujo autorizado. Incluir UUID exige selección, autorización y confirmación adicional.

No se ha cambiado el esquema VMess ni se ha creado snapshot/backup real. Esta nota describe el estado previo a la aprobación posterior del manifiesto, formato ZIP/JSON y contrato técnico del writer; consultar las actualizaciones de continuidad posteriores para el estado vigente.

## Continuidad — lock TLS en desinstalación (2026-11-03)

Se implementó localmente la coordinación de modules/uninstall.sh con catalog.lock cuando la desinstalación incluye certificados. Orden del flujo: lifecycle.lock → uninstall.lock → integrity.lock → catalog.lock (sólo si aplica) → bloqueo Xray. La adquisición es no bloqueante; si falla, se aborta sin crear backup ni eliminar rutas. Si se adquiere, se mantiene durante confirmación, respaldo y eliminación, y se libera en retorno.

tests/uninstall.sh prueba que el lock ocupado impide la operación y que, durante la confirmación de eliminación de certificados, otro adquirente no puede tomar catalog.lock. La suite completa tests/*.sh, Bash syntax, ShellCheck del módulo modificado, py_compile y git diff check pasaron.

La auditoría estática de locks descrita en esta nota fue completada posteriormente para los puntos localizados; no equivale a stress test exhaustivo. El contrato de manifiesto, snapshot y writer se aprobó después. Consultar la actualización de aprobación del contrato técnico al final de este documento.

## Continuidad — ubicación estable de catalog.lock (2026-11-03)

Se corrigió una segunda condición necesaria para que el lock de desinstalación sea efectivo: el archivo no puede vivir dentro del directorio que se elimina. Default único actualizado a /run/xray-manager-certificate-locks/catalog.lock, fuera de /var/lib/xray-manager. certificate_store.py crea/valida el directorio padre root-only; certificate_resolver.py utiliza el mismo acquire_lock. uninstall.sh prepara el padre como root:root 0700 y comprueba ese modo antes de tomar el lock.

Defaults CLI, paths centrales, asistentes VLESS/VMess, desinstalación y docs quedaron alineados. tests/certificate_store.sh valida defaults de ambos CLI; tests/uninstall.sh valida contención del lock y supervivencia fuera del árbol borrado. La suite completa debe volver a ejecutarse tras estos cambios.

No se movió ni eliminó ningún lock real, no se aplicó runtime ni se tocaron datos persistentes. La auditoría global de todos los mutadores sigue abierta.

## Continuidad — auditoría estática de locks (2026-11-03)

Se completó el inventario estático de puntos de adquisición localizados en scripts, modules, lib, config e install.sh. No se encontró ciclo/inversión en los caminos inspeccionados. El orden recomendado para el snapshot compartido es lifecycle → integrity → catalog, liberando en orden inverso. El writer deberá usar locks no bloqueantes con timeout finito; los stores Python actuales son bloqueantes y no deben copiarse sin límite.

La desinstalación ahora coordina catalog.lock cuando elimina certificados. El lock vive fuera del árbol de datos, en /run/xray-manager-certificate-locks/catalog.lock, con padre root:root 0700. Pruebas cubren contención lifecycle/integrity/catalog/Xray, retención durante confirmación, liberación si Xray está ocupado y supervivencia al borrado del árbol. Suite 47/47 PASS y verificaciones estáticas PASS.

La auditoría estática no sustituye pruebas de estrés exhaustivas. El cambio de ruta requiere despliegue con procesos de versión anterior detenidos; no se movió el lock antiguo ni se ejecutó runtime apply.


## 2026-11-03 — Aprobación del alcance incremental del snapshot compartido v1

El propietario aprobó el alcance incremental: snapshot de conexiones/configuraciones actuales VLESS y VMess; metadatos no secretos de usuarios, identidades y asociaciones; catálogo central TLS, certificados públicos `managed` y dependencias `reference`. Se excluyen por defecto UUID VLESS/VMess, secretos REALITY, claves privadas TLS y cualquier otra credencial; los elementos afectados se marcan incompletos. Se mantienen `email` y `level` VMess como metadatos protegidos.

Perfiles, perfil activo, preferencias, dominios independientes y protocolos distintos de VLESS/VMess quedan `unsupported` en v1. Si una categoría no soportada es solicitada, el resultado global será `PARTIAL`, nunca `COMPLETE`. Esto se contrasta con Etapa 5 normativa, que sigue siendo la referencia íntegra y no se modifica.

`docs/PLAN_BACKUP_RESTORE_CENTRAL.md` actualizado a v1.6 con la decisión y un borrador del contrato lógico de manifiesto. El borrador sigue pendiente de aprobación: no es schema congelado. La aprobación actual no autoriza writer, paquetes reales, restore, inclusión de secretos ni runtime apply.


**Publicación del alcance incremental v1:** commit `bccaba94be4160e6c01f281c7f4829f02c07db41` (`docs(backup): approve incremental snapshot v1 scope`) publicado en `origin/design/user-identity-association-v1`; HEAD local/remoto verificado idéntico en ese commit. Sólo documentación; `Xray-Normativa/` intacta. No se implementó writer ni se crearon paquetes/backups reales.


## 2026-11-03 — Borrador detallado de schema del manifiesto compartido

Se amplió `docs/PLAN_BACKUP_RESTORE_CENTRAL.md` a v1.7 con una propuesta concreta de estructura JSON y reglas de validación para el manifiesto interno: solicitud/categorías, recursos, miembros content-addressed, exclusiones, dependencias, snapshot de origen y completitud. `COMPLETE`/`PARTIAL` son estados de paquete; `BLOCKED` es preflight fallido y no produce paquete. El manifiesto permanece dentro del payload cifrado y no contiene credenciales ni email VMess.

El schema sigue PENDIENTE DE APROBACIÓN. No se implementó writer, verify, restore ni formato de empaquetado; no se creó backup real. `Xray-Normativa/` permanece intacta.


**Publicación del borrador de manifiesto:** commit `2bffbb6eee3c84b8008d2445ae0c0377bca40536` (`docs(backup): draft shared manifest schema v1`) publicado en `origin/design/user-identity-association-v1`; HEAD local/remoto verificado idéntico en ese commit. Sólo documentación; `Xray-Normativa/` intacta. El schema continúa pendiente de aprobación y no hay writer ni backup real.


## 2026-11-03 — Aprobación del contrato JSON del manifiesto compartido v1

El propietario aprobó expresamente el contrato lógico y la estructura JSON de las secciones 10.6 y 10.7 de `docs/PLAN_BACKUP_RESTORE_CENTRAL.md`. Se aprueban campos/relaciones, categorías, recursos, miembros content-addressed, exclusiones, dependencias, source snapshot, hashes/tamaños, paths relativos, reglas de validación y estados `COMPLETE`/`PARTIAL`; `BLOCKED` queda como resultado de preflight que aborta sin publicar paquete. El manifiesto no contiene credenciales ni email VMess.

El plan pasa a v1.8 y el contrato de manifiesto v1 queda APROBADO. Empaquetado físico, máximo de miembros y canonicalización JSON exacta siguen pendientes de cierre técnico. No se implementó writer/verify/restore ni se creó backup real. `Xray-Normativa/` permanece inmutable.


**Publicación de aprobación del manifiesto:** commit `000eb537fbb11c9870b6bef917769b1ca8448c66` (`docs(backup): approve shared manifest contract v1`) publicado en `origin/design/user-identity-association-v1`; HEAD local/remoto verificado idéntico en ese commit. Sólo documentación; `Xray-Normativa/` intacta. El writer sigue sin implementarse.


## 2026-11-03 — Aprobación de formato lógico ZIP/JSON v1

El propietario aprobó ZIP con `ZIP_STORED`, `manifest.json` e `index.json`, validación estricta de paths/tipos/duplicados/miembros indexados/tamaño/SHA-256. Límite total ZIP: 512 MiB. Canonicalización JSON propia: UTF-8 estricto sin BOM, claves ordenadas lexicográficamente, separadores compactos, sin duplicados, floats ni valores no finitos, enteros interoperables y comparación byte-a-byte con serialización canónica. No se declara RFC 8785/JCS. Máximo de entradas ZIP aprobado: 10.000 en total (incluye `manifest.json` e `index.json`; hasta 9.998 miembros de datos).

El plan es v1.9. No existe writer, verify, restore ni paquete real; esta aprobación no autoriza su implementación ni runtime apply. `Xray-Normativa/` permanece intacta.


## 2026-11-03 — Máximo de entradas ZIP aprobado

Se aprobó el límite estricto de 10.000 entradas ZIP totales (incluye `manifest.json` e `index.json`), por lo que caben hasta 9.998 miembros de datos. Si se supera, writer/preflight aborta sin publicar paquete parcial y verify/lector rechaza el paquete. El plan pasa a v1.10. Esta decisión cierra el límite de miembros, pero no autoriza writer, verify, restore ni paquetes reales.


## 2026-11-03 — Aprobación del contrato técnico del snapshot writer v1

El propietario aprobó el contrato técnico del snapshot writer compartido v1 y la ampliación de cifrado incremental compatible con el contenedor criptográfico v1. Se congelan: secuencia fail-closed; locks `lifecycle → integrity → catalog`, adquisición no bloqueante con timeout total configurable (30 s inicial recomendado) y liberación inversa; captura coherente de catálogos/revisiones referenciadas; adaptadores VLESS/VMess/identidades/TLS; exclusiones predeterminadas; validación segura de archivos; manifiesto/índice/ZIP `ZIP_STORED`; máximo 10.000 entradas y 512 MiB; cifrado GCM por bloques sin cambiar el formato binario v1; verificación y publicación atómica exclusiva sin sobrescritura; estados de resultado y matriz de pruebas.

La interfaz incremental deberá conservar magic, cabecera/AAD, perfil scrypt, salt/nonce, AES-256-GCM y tag del formato v1, con compatibilidad cruzada respecto a la interfaz actual. El ZIP se emitirá en streaming al cifrador sin crear ZIP en claro en disco; el tamaño exacto del ZIP se calculará antes de fijar `ciphertext_length` y se contrastará con el flujo emitido.

`docs/PLAN_BACKUP_RESTORE_CENTRAL.md` pasa a v1.11. La aprobación autoriza implementar writer y cifrado incremental en la rama autorizada, pero no crear backups reales, incluir secretos, implementar restore/verify independiente, leer/modificar master key ni tocar runtime/servicios/firewall/puertos/certificados desplegados/VPS de pruebas. `Xray-Normativa/` permanece inmutable.


## Continuidad — cifrado incremental compatible con contenedor compartido v1 (2026-11-03)

Se amplió `scripts/shared_backup_format.py` con `encrypt_payload_stream()` y `verify_package_stream()`. El cifrado incremental usa AES-GCM por bloques y longitud de plaintext conocida; conserva magic, cabecera canónica, AAD, scrypt v1, salt/nonce, AES-256-GCM y tag. El verificador incremental requiere flujo seekable, descarta plaintext no autenticado y sólo informa éxito después de validar el tag. Las APIs de bytes existentes se mantienen.

`tests/shared_backup_format.sh` cubre compatibilidad cruzada: paquetes de la API incremental se descifran con la API v1 de bytes y el verificador incremental autentica paquetes de ambas interfaces; también comprueba truncamiento, bytes sobrantes, alteración/tag, contraseña incorrecta y longitudes de entrada. Prueba focal PASS; suite completa `tests/*.sh`: 47/47 PASS; sintaxis Python y `git diff --check` PASS. Pruebas adicionales con tamaños aleatorios y límites de bloque PASS.

Estado: API incremental IMPLEMENTADA/VERIFICADA en aislamiento. El ZIP streaming/determinista y snapshot writer aún no están implementados. No se creó backup real, no se leyeron secretos/master key ni se tocó runtime.


## Continuidad — generador ZIP determinista en streaming v1 (2026-11-03)

Se añadió `scripts/shared_backup_zip.py`: `ZipMember` prepara miembros bytes o archivos dentro de un `allowed_root` explícito; valida root:root 0600, archivo regular, `st_nlink == 1`, recorrido de directorios sin symlinks, identidad de inode/metadatos y hashes/CRC en preflight y emisión. `ZipStream.read(n)` genera ZIP `ZIP_STORED` determinista directamente como fuente para `encrypt_payload_stream()`, sin ZIP temporal en claro. `write_zip_stream()` permite probar/emisión a un sink.

El ZIP fija timestamps, UTF-8/NFC, nombres y orden; `manifest.json`/`index.json` son las dos primeras entradas. Se rechazan traversal, paths absolutos, separadores alternativos, NUL/control, colisiones normalizadas/casefold, symlinks/hardlinks, permisos inseguros, cambios TOCTOU, ZIP64, más de 10.000 entradas y tamaño total >512 MiB.

Prueba focal `tests/shared_backup_zip.sh` PASS: lectura ZIP estándar, ZIP_STORED, CRC, determinismo, integración directa ZIP→AES-GCM streaming→verificación→ZIP válido, límites, paths y archivos inseguros. Suite completa `tests/*.sh`: 48/48 PASS; sintaxis Python, ShellCheck focal, shfmt focal y `git diff --check` PASS. Snapshot writer y adaptadores aún no implementados; no se creó backup real ni se tocaron secretos/master key/runtime.


## Continuidad — primera implementación local del snapshot writer compartido v1 (2026-11-03)

Se creó localmente scripts/shared_snapshot_writer.py conforme al contrato técnico aprobado §10.11. Se corrigieron tres puntos de la revisión: selective requiere categorías explícitas; la secuencia valida destino/prepara staging privado antes de pedir passphrase y solicita passphrase antes de adquirir locks; los directorios padres de locks deben existir y superar controles de propiedad/permisos, sin crearlos automáticamente. El timeout ahora rechaza valores no numéricos, booleanos, negativos o no finitos.

Se añadió tests/shared_snapshot_writer.sh. Cubre selección, staging antes del prompt, limpieza por contraseña no coincidente, locks ausentes/inseguros, orden de adquisición/liberación, timeout, referencias de identidad y exclusión de credenciales. Pruebas sintéticas confirman que los UUID de asociaciones/VMess no aparecen en el catálogo saneado, mientras email y level VMess se conservan como metadatos protegidos.

Verificación focal VPS: tests/shared_snapshot_writer.sh, tests/shared_backup_format.sh, tests/shared_backup_zip.sh y AST Python: PASS. Regresión global tests/*.sh: 49/49 PASS; git diff --check: PASS. No se ejecutó create_snapshot contra datos reales; no se generó backup; no se accedió a master key ni secretos reales. No se ejecutó restore ni verify independiente.

Estado: IMPLEMENTADO LOCALMENTE / VERIFICADO PARCIALMENTE / NO PUBLICADO / NO SINCRONIZADO / NO ACEPTADO. Pendiente completar la suite de aceptación integral y auditoría de trazabilidad §10.11. Rama autorizada design/user-identity-association-v1, HEAD ec9b306b38f0bce17f28c301c47df3b3d092785a; no se creó commit ni se hizo push. Xray-Normativa/ y main permanecen intactas.

## 2026-11-03 — Endurecimiento y ampliación de pruebas del snapshot writer v1

Implementados localmente los cuatro bloques autorizados de corrección:

1. **Destino y TOCTOU:** la validación inspecciona toda la cadena de directorios; exige root:root, rechaza symlinks y ancestros group/world-writable sin sticky bit; conserva la excepción segura para directorios sticky como /tmp y exige 0700 en el directorio final.
2. **Dependencias TLS:** se incorpora `external-dependencies.json` como miembro del ZIP cifrado. Para certificados `reference` registra certificate_id, fingerprint, ruta esperada, conexiones dependientes y validación requerida. La ruta absoluta no se incorpora al manifiesto y sólo queda dentro del payload cifrado. Las dependencias TLS reference se identifican como `tls_reference`.
3. **Errores y estados:** passphrase inválida, origen/miembro ZIP alterado, límites/formato cifrado inválido y verificación fallida se clasifican como `BLOCKED`; fallos operativos de I/O se mantienen como `FAILED`.
4. **Snapshot y exclusiones:** `source_snapshot` registra catalog_id, schema_version, revision, SHA-256 y presencia. Los almacenes sin schema/revision propia declaran null, no valores inventados. El catálogo de identidades ausente bloquea en vez de interpretarse silenciosamente como vacío. Las exclusiones de asociaciones ahora identifican asociación, identidad y conexión y se representan como recursos individuales.

La suite focal `tests/shared_snapshot_writer.sh` se amplió con:
- Rechazo de ancestros inseguros y symlinks en el destino.
- Rechazo de passphrase débil como BLOCKED.
- Revisiones VLESS/VMess incorrectas, destino preexistente y cleanup.
- Dependencias TLS reference con agregación de conexiones y path confinado al miembro cifrado.
- E2E sintético VLESS + VMess + identidades: UUID ausentes del paquete, email/level VMess conservados.
- E2E sintético TLS reference y TLS managed: certificado público managed incluido; clave privada excluida; ruta reference sólo en external-dependencies.json.
- Cambio de configuración después del preflight rechazado por hash/size del miembro.
- Fallos de verificación, fsync, interrupción controlada y carrera de publicación sin sobrescritura.
- Medición tracemalloc de emisión ZIP→AES-GCM para un miembro de 16 MiB con umbral de memoria Python inferior a 8 MiB.

Pruebas focales writer, formato cifrado y ZIP PASS; AST Python, ShellCheck, shfmt y git diff --check PASS. Regresión global `tests/*.sh`: 49/49 PASS.

**Limitaciones aún abiertas antes de aceptación:** no se ha ejecutado una matriz de terminaciones abruptas SIGKILL en cada fase; la medición de memoria es tracemalloc (no RSS máximo del proceso); los límites de 10.000 entradas/512 MiB se verifican en el generador ZIP, pero falta una prueba de orquestación que los fuerce desde el writer; falta ampliar escenarios integrales de catálogos y revisiones VLESS/VMess y pruebas de publicación/durabilidad posteriores al punto de commit. Por tanto, el writer sigue NO ACEPTADO.

No se creó backup real ni se accedió a master.key o secretos reales. No se ejecutó restore/verify independiente ni se modificó runtime, servicios, firewall, puertos, certificados desplegados o VPS de pruebas. `Xray-Normativa/` permanece intacta. Sin commit/push ni sincronización GitHub; rama `design/user-identity-association-v1`, HEAD sin cambio `ec9b306b38f0bce17f28c301c47df3b3d092785a`.

## 2026-11-03 — Cierre de la matriz ampliada de pruebas del snapshot writer

Se completó una segunda ampliación de la suite de aceptación local:

- E2E sintético VLESS + VMess + identidades, TLS `reference` y TLS `managed`; se verificó ausencia de UUID/credenciales excluidas, conservación de `email`/`level` VMess y ruta de referencia sólo dentro del miembro cifrado.
- TOCTOU de configuración después del preflight: el cambio de bytes se detecta y bloquea antes de publicar.
- Límites ejercidos a través de `create_snapshot`: 10.001 entradas y ZIP lógico superior a 512 MiB producen BLOCKED sin paquete final.
- Locks con contención real: timeout al segundo lock y liberación del primero comprobada.
- Publicación: destino concurrente no sobrescrito; fallos pre-commit limpian staging; fallo de fsync post-commit informa FAILED y conserva el artefacto ya publicado, que se vuelve a autenticar.
- Terminación abrupta mediante `os._exit` en tres puntos (antes del prompt, durante emisión cifrada y antes del enlace final): no aparece destino final; los residuos observados permanecen dentro de staging root:root 0700 y archivo 0600. La prueba los elimina al terminar.
- Memoria: tracemalloc bajo el umbral de 8 MiB adicionales; proceso aislado con miembro de 16 MiB midió RSS máximo de 73.436 KiB (incluye Python y scrypt).
- CLI/API: `all_available` delega selección por defecto correctamente; `selective` exige categorías explícitas.

Validación final: `tests/*.sh` 49/49 PASS; AST Python 16/16; ShellCheck PASS; shfmt PASS; `git diff --check` PASS.

**Consideración operativa pendiente:** tras una terminación no capturable (`os._exit`/SIGKILL), el proceso no puede ejecutar `finally`; puede quedar un staging privado sin destino publicado. La matriz demuestra que el residuo es privado y no contiene un ZIP en claro, pero no se implementó un recolector automático de staging huérfano. No se borrarán esos directorios de forma heurística mientras pueda existir otro proceso activo.

El writer continúa **IMPLEMENTADO LOCALMENTE / VERIFICADO EN AISLAMIENTO / NO PUBLICADO / NO ACEPTADO FORMALMENTE**. No se ejecutó backup real ni se accedió a master.key/secretos reales; no restore, verify independiente ni runtime apply. `Xray-Normativa/` intacta. Rama `design/user-identity-association-v1`, HEAD `ec9b306b38f0bce17f28c301c47df3b3d092785a`; sin commit/push ni sincronización GitHub.

## Actualización de continuidad — recuperación de staging autorizada (2026-11-03)

La enmienda autorizada a §10.11 fue implementada localmente. La passphrase se solicita y valida antes de crear staging. `.xrm-coordination.lock` serializa recuperación/preparación/limpieza; `owner.lock` root:root 0600 y `nlink == 1` permanece bloqueado durante cada operación. Se recuperan sólo directorios `.xrm-snapshot-*` cuyo lock esté libre y cuya estructura sea estrictamente válida. Staging activos se conservan; temporales vacíos sólo se retiran bajo coordinación; nombres/tipos/permisos inesperados bloquean fail-closed y no se borran. La coordinación se libera antes de adquirir los locks de datos, cuyo orden sigue siendo `lifecycle → integrity → catalog`.

La suite focal pasó tras corregir una colisión inicial del nombre del lock de coordinación con el patrón de staging. Se retiró el caso de terminación abrupta durante el prompt del crash matrix porque ahora no debe existir staging en esa fase; SW-02 verifica esa propiedad. Permanecen los casos de terminación durante cifrado y antes de publicación. `bash tests/*.sh` PASS; AST 16/16; ShellCheck, shfmt y `git diff --check` PASS. RSS aislado medido: 74.120 KiB. El writer sigue implementado localmente, no publicado y pendiente de aceptación formal. No se creó backup real ni se accedió a secretos o `master.key`; normativa intacta; sin commit/push/sync.

## 2026-11-03 — Corrección del lock de coordinación y contrato de manifiesto

Por autorización expresa del propietario se corrigió `_acquire_coordination_lock()`: los locks preexistentes se inspeccionan sin mutación; se rechazan hardlinks, symlinks, tipos especiales y permisos/propietarios incorrectos antes de modificar nada. Se comprueba que el descriptor abierto conserve el inode inspeccionado. El archivo nuevo se crea de forma exclusiva (`O_EXCL`/`O_NOFOLLOW`) y sólo entonces se fijan propietario y modo.

Se completaron validaciones del manifiesto: estructura raíz, UUID v4 canónico, timestamp UTC RFC 3339 `Z`, versión entera, source, selección y categorías únicas/no vacías, listas estructurales, contadores, miembros SHA-256/tamaño/media type y coherencia de recursos/global `COMPLETE` con exclusiones/dependencias.

Pruebas nuevas: hardlink (incluida preservación de modo, inode, nlink y contenido del otro nombre), symlink, FIFO, modo inseguro, contención/timeout de coordinación y manifiestos con UUID/timestamps/categorías/versión inválidos. Suite focal PASS; regresión completa PASS (49 scripts); AST 16/16; `bash -n`, ShellCheck, shfmt y `git diff --check` PASS. RSS aislado focal 75.120 KiB.

Estado: IMPLEMENTADO LOCALMENTE / VERIFICADO EN AISLAMIENTO / NO PUBLICADO / NO ACEPTADO FORMALMENTE. No commit/push ni sincronización GitHub. No se creó backup real ni se accedió a datos secretos; no restore/verify independiente ni runtime apply. Normativa inmutable. Siguiente paso: revisión de aceptación actualizada; no publicar sin autorización expresa.


## Continuidad — publicación del snapshot writer v1 (2026-11-03)

Se publicó el código local del snapshot writer v1, las pruebas, dependencias de ZIP streaming/API y documentos técnicos en la rama autorizada design/user-identity-association-v1. Commit publicado: ae8a7a089809e2e1913c14a714f45d956f8a5a1d, verificado como HEAD remoto el 2026-11-03.

La regresión local previa a publicar pasó: 49/49 scripts; AST 16/16; bash -n, ShellCheck, shfmt y git diff --check. La normativa mantiene 14/14 hashes coincidentes con la copia maestra. scripts/__pycache__/ quedó fuera del commit. El writer sigue NO ACEPTADO FORMALMENTE; publicar no equivale a aceptar. Próximo paso: revisión de aceptación contra §10.11.8 y plan v1.14. No ejecutar backup real, restore/verify independiente, ni tocar secretos/master.key/runtime.


## Continuidad — correcciones de la segunda revisión del snapshot writer (2026-11-03)

El propietario autorizó corregir B-01/B-02/B-03 manteniendo el writer NO ACEPTADO. Se implementó allowlist de identidades/asociaciones y exclusión íntegra de WireGuard/protocolos no soportados; limpieza fail-closed con cierre garantizado de owner_fd y reporte FAILED cuando falla cleanup; validación estricta de versión v1, conjuntos de categorías y estructura de objetos del manifiesto.

La suite focal añade pruebas sintéticas para claves privadas/PSK, campos desconocidos, versión 2, categorías extra/omitidas/duplicadas, objetos internos incompletos, fallos de coordinación/unlink/rmdir/fsync y crash tras el enlace final antes del fsync del directorio.

Verificación ejecutada en esta sesión: 49/49 scripts PASS; AST 16/16; bash -n 74 archivos; ShellCheck focal, shfmt focal y git diff --check PASS. SHA-256 de la documentación normativa: 14/14 coincidentes con /root/Xray_Manager_Documentacion_Final_2026-10-31.

**Punto exacto de reanudación:** revisar diff y documentación técnica actualizados; ejecutar auditoría de aceptación final. No aceptar el writer ni publicar estas correcciones hasta decisión expresa del propietario. Base publicada: ae8a7a089809e2e1913c14a714f45d956f8a5a1d; cambios actuales locales no committeados. No backup real, master.key, secretos, restore/verify independiente ni runtime.


## Registro histórico SUPERADO — publicación B-01/B-02/B-03 con bloqueo A-16 (2026-11-03)

El propietario autorizó publicar las correcciones B-01/B-02/B-03 en la rama autorizada, sin aceptar Snapshot Writer v1. La publicación debe incluir este estado de auditoría: **A-16 BLOQUEANTE / WRITER NO ACEPTADO**.

A-16: `_recover_orphan_staging()` rechaza un staging post-publicación legítimo porque `os.link(package.tmp, final_path)` deja temporal y destino apuntando al mismo inode (`st_nlink == 2`), mientras el recuperador exige `st_nlink == 1`. La reproducción sintética produjo `SnapshotBlocked` y conservó ambos nombres. Los tests de crash/cleanup no ejecutan recuperación sobre ese estado.

Siguiente paso tras publicar/sincronizar: diseñar y solicitar autorización para una corrección fail-closed que reconozca sólo el hardlink post-link demostrablemente correspondiente al paquete final; mantener rechazo de hardlinks arbitrarios, staging activo, symlinks, tipos especiales y metadatos inseguros. Añadir tests de recuperación tras crash post-link, unlink fallido y fallo de coordinación, comprobando integridad/preservación del paquete final y conservación de staging ambiguos. Repetir auditoría antes de proponer aceptación.

No ejecutar backup real, no leer `master.key`/secretos, no restore/verify independiente, no runtime apply ni modificar `Xray-Normativa/`.

## Continuidad — A-16 corregido localmente, pendiente de auditoría (2026-11-03)

El propietario autorizó corregir A-16. La implementación local incorpora publication.json en el staging privado, escrito y sincronizado antes del hardlink final. El marcador vincula el basename exacto de destino, device/inode, tamaño y SHA-256 del paquete. El recuperador admite el estado legítimo package.tmp nlink == 2 sólo con marcador válido y destino coincidente; retira exclusivamente package.tmp, comprueba que el destino conserva nlink == 1 y elimina después marcador/owner/staging. El flujo soporta reintento si el recuperador se interrumpe tras retirar el nombre temporal.

Se mantienen bloqueados hardlinks sin marcador, nlink > 2, destino con nombre/inode/tamaño/hash distinto, symlinks, tipos especiales, metadatos inseguros y staging activos. Los tests focales ejercitan crash post-link, fallos de coordinación/unlink y crash del propio recuperador. Verificación ejecutada: tests/*.sh 49/49 PASS; AST 16/16; bash -n 74 archivos; ShellCheck PASS; shfmt focal PASS; git diff --check PASS; normativa 14/14 hashes coincidentes. A-16 pasa. El Snapshot Writer sigue NO ACEPTADO formalmente hasta revisión/decisión expresa del propietario.

No crear backup real, no leer master.key/secretos, no restore/verify independiente, no runtime apply y no modificar Xray-Normativa/.

## Publicación y sincronización A-16 — 2026-11-03

Por autorización expresa del propietario, la corrección A-16, sus pruebas y la documentación afectada quedaron publicadas en `design/user-identity-association-v1`, commit `40c907e2a9da639f3458547e09fec6f26fdac5e1`. `git ls-remote` confirmó el mismo SHA en GitHub; el checkout de `/opt/xray-manager` coincide con el commit y quedó limpio. La rama `main` y `Xray-Normativa/` no se modificaron. Snapshot Writer v1 continúa NO ACEPTADO FORMALMENTE: publicar/sincronizar no equivale a aceptación.


## Estado vigente — cierre técnico de aceptación A-01–A-19 (2026-11-03)

- Matriz de trazabilidad completa documentada en `docs/PLAN_BACKUP_RESTORE_CENTRAL.md` §10.20. Se recuperaron los nombres originales de los 19 criterios y se enlazaron con sus pruebas versionadas; A-01–A-15 y A-17–A-19 conservan su resultado PASS de la auditoría previa y la regresión actual volvió a ejecutarse.
- A-16: diez negativos nuevos para marcador malformado/no canónico, hash/device/inode/tamaño alterados, campo extra, symlink, hardlink y modo inseguro. Cada caso confirma bloqueo fail-closed y preservación de la evidencia. No requirió modificar el código del writer.
- Verificación actual: 49/49 scripts PASS; AST 16/16; `bash -n` 74 archivos; ShellCheck PASS; shfmt PASS; `git diff --check` PASS; RSS focal 76.336 KiB. Normativa 14/14 hashes coincidentes con la copia maestra; `README.md` es archivo adicional no normativo.
- Rama `design/user-identity-association-v1`; base verificada `b1e2ef4537eafeacefd5584a7fde5c9fd02626a9`. La matriz y los diez negativos A-16 se publicaron en `101853e6ef0990686128f45561b22e1cd4248aea`; el registro final de publicación quedó en `7f03efcf080465d8bced447549e29f8abb95248b`. VPS y GitHub comparten el HEAD final.
- `Xray-Normativa/` no se modificó. No backup real, no acceso a `master.key`/secretos, no restore/verify independiente, no runtime apply.
- Estado: A-01–A-19 PASS en pruebas aisladas/sintéticas; Snapshot Writer v1 **NO ACEPTADO FORMALMENTE**. La aceptación formal requiere decisión expresa del propietario y no se infiere de pruebas o publicación.


## Punto de reanudación posterior a la aceptación del Snapshot Writer v1

La continuidad más reciente se amplía con la validación live inicial de Xray-core y VLESS-WS registrada al final de este documento.

## Aceptación formal del Snapshot Writer v1 — 2026-11-03

El propietario aceptó formalmente el **Snapshot Writer v1**, con las limitaciones expresamente documentadas en la matriz A-01–A-19 y en este plan. Esta aceptación cierra el componente Snapshot Writer v1; no equivale a certificar el flujo integral de backup/restore ni autoriza operaciones reales.

**Alcance de la aceptación:** implementación v1 para las categorías soportadas y sus contratos de captura, manifiesto, ZIP streaming, cifrado, publicación, limpieza y recuperación; resultados A-01–A-19 PASS en pruebas aisladas/sintéticas; correcciones B-01/B-02/B-03 y A-16 incluidas.

**Limitaciones que permanecen vigentes:**
- No se ha ejecutado un backup real sobre datos del usuario.
- No se ha ejecutado restore ni verify independiente de un backup real.
- No se ha leído `master.key` ni secretos reales.
- No se ha aplicado el Writer al runtime ni modificado servicios, firewall, puertos o certificados desplegados.
- Los PASS acreditan pruebas aisladas/sintéticas; no constituyen evidencia de operación real ni conectividad extremo a extremo.
- Categorías/protocolos fuera del alcance v1 se excluyen y pueden producir `PARTIAL`; `BLOCKED` y `FAILED` conservan sus semánticas documentadas.
- Se mantienen los límites de 10.000 entradas ZIP y 512 MiB.

**Decisión:** Snapshot Writer v1 = **ACEPTADO FORMALMENTE CON LIMITACIONES DOCUMENTADAS**. Backup/restore integral y sus verificaciones reales permanecen pendientes y no se declaran aceptados por esta decisión. La Etapa 2 del proyecto permanece ABIERTA conforme a la regla de auditoría integral de cierre de etapas.


Siguiente trabajo permitido: continuar con el plan de backup/restore integral y sus componentes pendientes, siempre contrastando la normativa y solicitando autorización para cada nuevo alcance. La aceptación del Writer no autoriza backup real, restore/verify independiente ni cambios de runtime. Etapa 2 sigue ABIERTA.


## Validación live inicial de Xray-core y VLESS-WS — 2026-11-03

Se realizó la primera prueba operativa real del administrador en la VPS de desarrollo.

**Instalación Xray-core**
- El menú real de administración instaló Xray-core 26.10.31 (a4a3dff) para Linux amd64.
- El release oficial, su archivo .dgst, el SHA-256 fijado para el ZIP, la versión del binario y los archivos geodata se verificaron correctamente.
- El administrador informó instalación exitosa y no creó ni inició un servicio systemd.

**Ajuste de permisos del almacén**
- El preflight de vless_config_store.py detectó /var/lib/xray-manager/connections en modo 750, incompatible con su contrato root:root 0700.
- Se confirmó que install.sh establece esa ruta en modo 700. Se ajustó sólo ese directorio de 750 a 700; el audit posterior pasó. No se modificó código del repositorio.

**Conexión de prueba**
- Creada desde el menú: Prueba-VLESS-WS-Real, ID conn-1793749234-670662.
- Modalidad vless_ws; escucha prevista 0.0.0.0:10001; WebSocket /ws; seguridad none; capacidad 1.
- Se creó un usuario de prueba Cliente-Prueba-VLESS-WS con estado draft. El registro live de usuarios sigue en esquema legacy (arreglo JSON), por lo que se utilizó el gestor VLESS legacy. No se migró a users v2. El UUID se omite de la documentación.
- La revisión neutral 1 se persistió en connections/configurations/conn-1793749234-670662.r000001.json; secret_ref=null; conexión draft; runtime_applied=false.
- La previsualización y recuperación desde el Manager terminaron con Configuration OK. Se repitió la recuperación fijando XRAY_VALIDATION_BINARY=/usr/local/bin/xray, validando expresamente con el binario instalado.
- Audit del almacén: cero referencias rotas, cero archivos huérfanos y cero secretos huérfanos.

**Límites y advertencias**
- Xray emitió la advertencia oficial de que WebSocket está obsoleto/no recomendado, puede retirarse y recomienda XHTTP H2/H3.
- No se creó /etc/xray/config.json; no se ejecutó xray_service_prepare; no existe xray.service ni se creó cuenta/grupo Xray durante esta prueba.
- Servicio inactivo, sin proceso Xray y puerto 10001 sin listener. No firewall, no apertura de puertos, no runtime apply y no conexión cliente externa/WAN.
- La inspección del menú actual no encontró una acción de aplicación runtime de la conexión. El siguiente frente requiere diseño/implementación y autorización específica antes de preparar servicio, publicar configuración o iniciar listener.

Evidencia detallada: docs/VALIDACION_LIVE_XRAY_VLESS_WS_2026-11-03.md.

**Estado:** Xray instalado y verificado en entorno real; VLESS-WS creado, persistido y validado en entorno real; conectividad externa y runtime apply pendientes. Etapa 2 sigue ABIERTA. Código sin cambios; documentación actualizada localmente, sin commit/push/sync. Xray-Normativa/ y main intactas.

## Continuidad — infraestructura inicial de candidatos runtime mediante perfiles (2026-11-03)

El propietario aprobó la opción A: respetar estrictamente la normativa de Etapa 5. La activación debe ocurrir a través del cambio de perfil activo; una conexión independiente no es una vía alternativa.

La inspección del árbol confirmó que todavía no existe un gestor funcional de perfiles (módulo, menú y esquema/registro). Los adaptadores VLESS/VMess existentes construyen configuraciones por conexión, pero no componen una versión integral de perfil. No conectar el runtime directamente a Prueba-VLESS-WS-Real ni inventar un esquema de perfil.

Se implementó localmente:
- `scripts/xray_runtime_candidates.py`: primitiva de staging privado de candidatos asociados a profile_id/profile_revision.
- `tests/xray_runtime_candidates.sh`: prueba sintética focal.
- `docs/DISENO_IMPLEMENTACION_RUNTIME_PERFILES.md`: decisiones, flujo objetivo, controles, pruebas y pendientes.

El staging exige JSON objeto con inbounds/outbounds, archivo fuente regular nlink 1 sin symlinks, máximo 16 MiB, tokens de perfil/revisión sin traversal, validación nativa con Xray, bloqueo, no sobrescritura de revisión, hash SHA-256 y manifiesto. Los bytes se copian a un archivo temporal privado y Xray valida exactamente esa copia; luego se publica el directorio candidato mediante rename. Configuración/manifiesto 0600 y directorios 0700.

Límite fundamental: el componente sólo almacena un candidato validado. No escribe /etc/xray/config.json ni prepara/inicia/habilita Xray. No existe aún flujo de publicación runtime integrado; deberá implementarse dentro del cambio de perfil activo de Etapa 5.

La conexión Prueba-VLESS-WS-Real sigue draft y runtime_applied=false. No se ejecutó xray_service_prepare, no se creó usuario/grupo de servicio ni unidad, no se abrió 10001, no se cambió firewall ni certificados y no se probó conectividad WAN.

**Próximo paso:** ejecutar la prueba focal y regresión; probar validación con el binario real sólo sobre configuración sintética temporal. Después, diseñar/implementar el subsistema de perfiles y su composición/validación. No publicar ni activar runtime hasta que el flujo de perfil esté integrado y autorizado. No commit/push/sync sin autorización expresa. Xray-Normativa/ y main permanecen inmutables.

### Nota de regresión segura

La primera ejecución de tests/smoke.sh reveló que tests/users.sh perdía las rutas temporales al volver a cargar modules/users.sh y llegaba a consultar el registro live. La prueba se detuvo al detectar el límite de capacidad del usuario de prueba; no modificó el registro real. Se corrigió el fixture para fijar XRAY_MANAGER_USERS_DIR, XRAY_MANAGER_USERS_FILE, XRAY_MANAGER_CONNECTIONS_DIR, XRAY_MANAGER_CONNECTIONS_FILE y XRAY_MANAGER_INTEGRITY_LOCK antes de cargar los módulos. Después de la corrección, tests/users.sh y tests/smoke.sh pasan.

### Verificación final de este punto de continuidad

Regresión completa: 50/50 scripts PASS; Python AST 17/17; bash -n de todos los archivos shell PASS; ShellCheck y shfmt de la nueva prueba focal PASS; git diff --check PASS. El binario Xray-core 26.10.31 real validó un candidato sintético temporal y el staging devolvió STAGED sin publicar runtime ni iniciar servicio. Los 14 archivos normativos comparados coinciden con la copia maestra (README.md es auxiliar y no normativo). No commit/push/sync.

## Publicación de la infraestructura de candidatos runtime — 2026-11-03

Por autorización expresa del propietario, se sincronizan con GitHub en `design/user-identity-association-v1` los cambios locales de la infraestructura de staging por perfiles, el aislamiento de `tests/users.sh` y los documentos de continuidad/diseño/validación live. Se incluyen los nueve archivos de proyecto identificados en el punto de control de esta publicación. Se excluye `scripts/__pycache__/`, que permanece como artefacto local y no forma parte del repositorio.

La publicación no activa Xray ni altera el estado operativo: `Prueba-VLESS-WS-Real` permanece draft y `runtime_applied=false`; no existe configuración runtime aplicada ni listener 10001. No se ejecutó preparación/arranque del servicio ni se modificó firewall, red o certificados. `Xray-Normativa/` y `main` permanecen intactas. Etapa 2 continúa ABIERTA; el siguiente bloque de desarrollo es el subsistema de perfiles, conforme a la opción A aprobada.


## Continuidad — almacén de perfiles v1 (2026-11-03)

[SUPERADO EL 2026-11-03] La decisión provisional de la primera iteración fue mantener las configuraciones de perfiles en texto plano. El propietario eligió después AES-256-GCM; consultar el punto de reanudación vigente y el último bloque de este documento. Los datos se protegen mediante directorios `root:root 0700` y archivos `root:root 0600`; esta protección no equivale a cifrado y root puede leer el contenido.

### Implementación disponible

- `scripts/xray_profiles.py`: CLI y persistencia del catálogo, perfiles y revisiones.
- `modules/profiles.sh`: submenú funcional inicial.
- `tests/xray_profiles.sh`: pruebas sintéticas focales.
- `bin/xray-manager`: carga el módulo.
- `modules/main_menu.sh`: opción principal de configuraciones/perfiles/respaldo conectada al submenú normativo.
- `docs/DISENO_IMPLEMENTACION_PERFILES.md`: diseño, estructura, controles, operaciones y límites.

El almacén usa `/var/lib/xray-manager/profiles/` cuando se invoque desde el Manager; las pruebas usan exclusivamente `--store`/`XRAY_MANAGER_PROFILES_DIR` en rutas temporales. El catálogo tiene IDs inmutables y nombres únicos; cada perfil mantiene metadatos y directorios de revisiones. [DESCRIPCIÓN HISTÓRICA SUPERADA] La primera implementación guardaba `config.json` en texto plano. La versión vigente usa `config.enc.json` cifrado con AES-256-GCM; consultar el último bloque de este documento y `docs/DISENO_IMPLEMENTACION_PERFILES.md`. Renombrar no cambia JSON ni ID.

### Operaciones que ya se pueden usar

Crear desde cero sin JSON; crear copiando un archivo JSON externo; consultar perfiles y revisiones; modificar nombre/descripción/notas y/o importar una nueva configuración; duplicar; renombrar; consultar hashes de revisiones; restaurar una revisión como nueva. La eliminación aparece deshabilitada hasta integrar/verificar el registro activo y dependencias.

### Límites y pendientes vinculantes

- Una importación sólo acredita sintaxis JSON estricta. `xray_static=not_run`; `validation_status=not_validated`. No afirmar Validada ni Aplicada.
- El estado activo se informa como no integrado. No se ha creado el registro `active-profile.json` ni conectado el antiguo indicador de perfil activo.
- No existe validación Xray nativa asociada a cada revisión, informes de validación, comparación de revisiones, historial de modificaciones ni retención configurable.
- No hay composición integral de conexiones/usuarios/asociaciones/certificados en un perfil.
- No hay activación, publicación runtime, verificación del servicio ni rollback de activación. La regla opción A permanece: sólo el cambio de perfil activo podrá ser la vía de activación.
- No hay eliminación real de perfiles; no habilitarla antes de proteger perfil activo, dependencias y conservación de JSON.

### Verificación ejecutada

En la VPS: `tests/xray_profiles.sh`, `tests/stage1_menu.sh`, `tests/smoke.sh` y regresión `tests/*.sh`: 51/51 PASS; Python AST 18/18; `bash -n` todos los shell scripts; ShellCheck/shfmt focal; `git diff --check`. La suite nueva cubre permisos, ciphertext sin marcador plaintext, descifrado, clave ausente/incorrecta, autenticación GCM/AAD, copias independientes, nombres únicos, modificación/versionado, rename sin cambio de blob, restore no destructivo, JSON malformado/duplicado, symlink/hardlink, almacén simbólico y concurrencia por nombre.

Las pruebas usan almacenes temporales. No se creó `/var/lib/xray-manager/profiles`, no hay perfiles reales y no se alteró la conexión live. No se escribió `/etc/xray/config.json`, no se inició Xray ni se tocaron systemd, firewall, puertos, certificados o red. No se leyó ni usó `master.key`. `Xray-Normativa/` y `main` siguen intactas. Etapa 2 continúa ABIERTA.

**Punto exacto de reanudación:** revisar el diff completo y el diseño; después implementar validación estática Xray por revisión con pruebas sintéticas/aisladas, sin iniciar el servicio ni publicar runtime. Mantener deshabilitada la eliminación y no crear flujo de activación todavía.


## Punto de reanudación posterior a la implementación de cifrado de perfiles — 2026-11-03

La primera versión local del gestor de perfiles almacenaba `config.json` en texto plano. Al contrastarla con Etapa 5 normativa se detectó que esto contradecía la regla de no guardar credenciales ni claves privadas en texto plano. No se publicó aquella versión. El propietario eligió explícitamente AES-256-GCM (opción 1).

La implementación local actual cifra todo el JSON por revisión en `config.enc.json` con nonce aleatorio y AAD ligado a `profile_id`/revisión. Lee únicamente la clave maestra existente por el cargador seguro; no la crea ni la regenera. Las pruebas utilizan claves sintéticas temporales. Clave ausente o incorrecta y ciphertext manipulado se rechazan fail-closed. Los manifests plaintext/no reconocidos también se rechazan; no existe migración automática.

La inspección confirmó que `/var/lib/xray-manager/profiles` no existe; no hay perfiles reales que migrar. No se ha leído ni modificado `/etc/xray-manager/keys/master.key`. No se modificó runtime, servicio, firewall, puertos, certificados, conexión live ni `Xray-Normativa/`.

**Verificación:** `tests/*.sh` 51/51 PASS; Python AST 18/18; `bash -n` global PASS; ShellCheck focal PASS; shfmt de los archivos nuevos PASS; `git diff --check` PASS.

**Estado:** IMPLEMENTADO, VERIFICADO EN PRUEBAS SINTÉTICAS, PUBLICADO y SINCRONIZADO byte a byte en `design/user-identity-association-v1`. Commit funcional inicial `03b63ca109a2fabb262924daf5d2fe4a683b23d8`; commit de reconciliación byte a byte `4cec7496585390adbe72d8887cb6dacd94743c32`. El árbol Git local y remoto coincide. `scripts/__pycache__/` es un artefacto local preexistente y se preserva/excluye. `main` permanece protegida.

**Próxima acción:** revisión del propietario y aceptación formal del subsistema o solicitud de ajustes. No usar la clave maestra real en pruebas ni ejecutar activación runtime.


## Regularización documental — evidencia live VMess TLS y reanudación de perfiles (2026-11-03)

Se incorporó el informe `docs/VALIDACION_LIVE_VMESS_TLS_LEASE_2026-11-03.md` a partir de la evidencia compartida por el propietario en las capturas de la prueba. El resultado válido es la segunda ejecución: Xray-core 26.10.31, proceso con UID 999/GID 988, lectura de certificado y clave sintéticos desde el lease y handshake TLS 1.3 verificado. La primera ejecución no se cuenta como PASS. No se dispone en este registro de la transcripción completa de comandos/stdout/stderr; el informe distingue esa limitación y no inventa detalles ausentes.

La prueba no acredita despliegue de `xray.service`, activación runtime del administrador, persistencia de certificados reales, conectividad cliente externa/WAN ni aceptación integral de VMess TLS. VMess y Etapa 2 conservan sus estados formales pendientes.

Se corrigió el encabezado de este documento para reflejar que perfiles v1.1 ya fue publicado y sincronizado; su aceptación formal permanece pendiente. La siguiente actividad permitida es una revisión formal de solo lectura del subsistema de perfiles contra Etapa 5, sin modificar código ni utilizar secretos reales.


## Auditoría formal de perfiles v1.1 — 2026-11-03

Se completó la revisión de solo lectura de `scripts/xray_profiles.py`, `modules/profiles.sh`, integración del menú, pruebas y diseño contra la especificación Etapa 5 (Markdown/YAML). La prueba focal de perfiles, `tests/stage1_menu.sh`, `tests/smoke.sh`, AST Python, sintaxis Bash, ShellCheck focal y `git diff --check` pasaron en esta sesión. La regresión histórica 51/51 no se volvió a ejecutar completa.

Hallazgo bloqueante PF-01: fault injection en almacén temporal confirmó que si `update()` guarda `metadata.json` y falla al guardar `catalog.json`, la siguiente consulta falla por discrepancia de nombre. PF-02 documenta ventanas de consistencia/durabilidad en operaciones multiarchivo. Se encontraron además requisitos pendientes de preview/diff, validación Xray, comparación/retención/historial, composición, registro activo, activación/rollback y backup/restore.

Se corrigió en `docs/DISENO_IMPLEMENTACION_PERFILES.md` una descripción inexacta del hash del manifiesto: el código guarda SHA-256 del ciphertext y tamaño del plaintext, no SHA-256 del plaintext. Informe completo: `docs/AUDITORIA_FORMAL_PERFILES_V1_1_2026-11-03.md`.

**Estado:** código sin cambios; perfiles v1.1 permanece publicado/sincronizado, pero NO aceptado formalmente. Siguiente acción: decisión expresa del propietario sobre autorizar la corrección PF-01/PF-02 y las pruebas de fallo/recuperación. No leer clave maestra real, no crear perfiles live ni activar runtime. Etapa 2 permanece ABIERTA.

## Correcciones PF-08/PF-09/PF-10 del almacén de perfiles — 2026-11-04

Autorización del propietario aplicada en la rama design/user-identity-association-v1, host Implementación-Xray, ruta /opt/xray-manager.

- PF-08: validación previa de tipos, límites y texto imprimible de descripción/notas; configuración validada antes de publicar una nueva revisión. Cuatro casos negativos verifican que no se crea revisión huérfana.
- PF-09: reconciliación bajo lock de revisiones definitivas posteriores al current_revision confirmado. Sólo se elimina una revisión con directorio/archivos seguros, contenido exacto y manifiesto coherente; artefactos no verificables se preservan y reportan.
- PF-10: contrato estricto de metadatos: conjunto exacto de campos, tipos no coercitivos, fechas UTC reales, límites y caracteres de texto, IDs de revisión y coherencia de estado/punteros.

Pruebas focales: tests/xray_profiles.sh PASS; PF-08 cuatro casos, PF-09 SIGKILL después del rename y recuperación en la siguiente operación, PF-10 dieciocho metadatos malformados rechazados. Python AST 18/18, py_compile del módulo modificado, bash -n global, ShellCheck focal y git diff --check PASS. shfmt -d -i 4 tests/xray_profiles.sh muestra diferencias de estilo preexistentes (indentación de bloques if en el archivo); no se reformateó el archivo completo para evitar cambios ajenos al alcance.

Informe: docs/AUDITORIA_CORRECCIONES_PF08_PF09_PF10_2026-11-04.md. Regresión general tests/*.sh finalizada: 51/51 scripts PASS (exit code 0).

Límites: sólo almacenes temporales y claves sintéticas. No se leyó master.key, no se crearon perfiles live, no se tocó runtime/servicios/certificados/firewall/puertos/red. Xray-Normativa/ y main intactas. No publicado en GitHub; publicación requiere autorización expresa posterior. Almacén v1.1 no aceptado formalmente; Etapa 5 y Etapa 2 siguen ABIERTAS.

Sincronización GitHub/VPS de desarrollo completada el 2026-11-04: commit 46444bcf11b41750d45f2187d77eeb5f7fce654c publicado en origin/design/user-identity-association-v1. El checkout /opt/xray-manager del host Implementación-Xray quedó en ese mismo commit, con árbol limpio. main y Xray-Normativa/ sin cambios.

## Continuidad — remediación PF-11/PF-12 de perfiles (2026-11-04)

El propietario autorizó corregir PF-11/PF-12 exclusivamente en la rama `design/user-identity-association-v1`, con pruebas aisladas y actualización documental.

### Estado de implementación local

- `scripts/xray_profiles.py`: `validate_revision_manifest()` exige contrato exacto de manifiesto y valida tipos estrictos, timestamp UTC, identidad, tamaños, SHA-256, formato cifrado, source y estados de validación coherentes.
- La lectura de revisión valida manifiesto antes de hash del ciphertext y autenticación/descifrado AES-256-GCM.
- `cleanup_orphan_profiles()` se ejecuta bajo lock después de WAL, temporales y revisiones. Retira sólo directorios definitivos no registrados cuyo catálogo exista y sea seguro, estructura/metadata/permisos sean exactos y única revisión cifrada pase lectura integral.
- Catálogo ausente o inseguro: preservar candidatos, no inferir pérdida/ausencia de catálogo como autorización para borrar. Candidatos ambiguos o inseguros se conservan y notifican. La inspección `lstat` precede a lectores que pueden normalizar permisos.
- `tests/xray_profiles.sh`: 13 manifiestos malformados rechazados; SIGKILL en create sin/con configuración y duplicate; primera alta sin catálogo preservada; candidato con metadata 0644 preservado sin corregir modo. Prueba focal PASS.

### Documentación y validación

Diseño: `docs/DISENO_IMPLEMENTACION_PERFILES.md` §16. Informe: `docs/AUDITORIA_CORRECCIONES_PF11_PF12_2026-11-04.md`. Regresión global posterior a la última modificación: **51/51 scripts PASS**, exit code 0. Python AST, `bash -n`, ShellCheck focal y `git diff --check` PASS.

### Próximo paso

Terminar la regresión, revisar el diff completo, ejecutar AST Python, Bash syntax, ShellCheck focal y `git diff --check`; actualizar el informe/continuidad con resultados; verificar `Xray-Normativa/` y `main` sin cambios. Publicar únicamente en la rama autorizada después de revisión final. No tocar `Vps de Pruebas`, runtime, servicios, secretos ni almacén live.

PF-11/PF-12 no implican aceptación formal del almacén v1.1 ni cierre de Etapa 5/Etapa 2. Siguen pendientes las funcionalidades normativas de Etapa 5 documentadas en el informe de auditoría.


## Continuidad — cierre acotado de PF-06 (2026-11-04)

El propietario autorizó implementar las pruebas pendientes de PF-06 sin modificar el comportamiento del almacén ni tocar runtime. En `tests/xray_profiles.sh` se añadió: (1) alteración del ciphertext con SHA-256 recalculado en el manifiesto para verificar rechazo real de autenticidad AES-256-GCM; (2) escritura parcial seguida de error; (3) fallo de fsync del archivo antes de replace; y (4) fallo de unlink del WAL después de publicar destinos, verificando rollback y recuperación. Ya existían pruebas de replace, fsync de directorio y crash recovery.

Prueba focal PASS; regresión completa 51/51 PASS. Sólo se modificaron pruebas y documentación; no código de producción. PF-06 queda cerrado dentro del alcance de escenarios enumerados, no como cobertura exhaustiva de todas las combinaciones ni de fallos físicos. Informe `docs/AUDITORIA_PF06_COBERTURA_CRIPTO_FILESYSTEM_2026-11-04.md`; diseño §17.

Siguiente puerta: revisión final de diff/estáticos y decidir aceptación limitada del almacén v1.1. No publicar ni sincronizar sin autorización independiente. No tocar VPS de pruebas, master.key, almacén live, runtime, servicios, red, `main` o `Xray-Normativa/`. Etapa 5 y Etapa 2 permanecen ABIERTAS.

## Continuidad — aceptación limitada del almacén de perfiles v1.1 (2026-11-04)

El propietario aceptó expresamente el almacén de persistencia de perfiles v1.1 **como componente limitado**. La decisión está desarrollada en docs/AUDITORIA_FORMAL_PERFILES_V1_1_2026-11-03.md, sección 14.

### Punto aceptado

Se acepta el núcleo de persistencia en los contratos y escenarios probados: AES-256-GCM/autenticidad, validación estricta de catálogo/metadatos/manifiestos, revisiones inmutables, WAL/rollback/recuperación, limpieza y reconciliación conservadora de temporales/revisiones/perfiles huérfanos, controles de locking/filesystem y pruebas PF-01/PF-02 y PF-06 a PF-12 dentro de sus límites documentados.

### Límites que no se deben sobrepasar

La aceptación no convierte en disponibles ni terminadas las funciones aún pendientes de Etapa 5: preview/diff, creación desde configuración independiente, validación estática Xray por revisión e informe, comparación de revisiones, historial separado/retención, registro y composición de perfil activo, eliminación integrada segura, activación/verificación/rollback y backup/restore integral. not_validated y not_integrated siguen siendo estados conservadores.

**Etapa 5 y Etapa 2 permanecen ABIERTAS.** La aceptación no certifica operación real, activación ni conectividad extremo a extremo; tampoco implica cobertura combinatoria exhaustiva o fallos físicos. La prueba integral VLESS WS TLS sigue condicionada a completar los requisitos y puntos de control que correspondan.

### Próxima continuidad

Conservar este punto de control como base aceptada del componente. El siguiente trabajo debe abordar los requisitos funcionales pendientes de Etapa 5, contrastando cada cambio con Xray-Normativa/ y solicitando autorización para la implementación correspondiente. No publicar ni sincronizar cambios sin autorización independiente.

No se leyó master.key, no se tocó almacén live, runtime, servicios, certificados, firewall, puertos, red ni VPS de pruebas. main y Xray-Normativa/ intactas. Esta actualización documental permanece local, sin commit/push/sync.

## Continuidad — diseño del gestor de configuraciones independientes (2026-11-04)

Se completó el contraste de la normativa Etapa 5 §§2–5 y 14 con los módulos actuales. El repositorio no contiene un gestor de configuraciones independientes: VLESS/VMess tienen almacenamiento por conexión y el almacén de perfiles conserva copias propias. Esos modelos no sustituyen el catálogo independiente.

Diseño: docs/DISENO_GESTOR_CONFIGURACIONES_INDEPENDIENTES.md. Arquitectura propuesta con catálogo y objetos propios, revisiones inmutables, AES-256-GCM con AAD por objeto/revisión, WAL, permisos root-only, importación/exportación segura, preview, diff/comparación y estados Borrador/Validada/Anterior. No hay comando apply/activate. El validador estático será separado; solo informe PASS ligado a hash/revisión puede promover una versión a Validada. La futura creación de perfil copiará bytes y quedará desacoplada.

Siguiente paso: solicitar autorización para implementar C-01 (contrato/persistencia) y C-02 (importación/exportación). No iniciar C-03 a C-06 sin aceptación de fases y sus dependencias. No modificar el almacén de perfiles aceptado, VLESS/VMess por conexión, runtime, servicios, certificados, firewall, puertos o red. No usar secretos reales. No publicar ni sincronizar sin autorización independiente. Etapa 5 y Etapa 2 permanecen ABIERTAS.

## Continuidad — implementación C-01 de configuraciones independientes (2026-11-04)

El usuario indicó continuar con el siguiente paso tras la sincronización del diseño. Se inició C-01 exclusivamente en `Implementación-Xray`, `/opt/xray-manager`, rama `design/user-identity-association-v1`.

- Nuevo motor: `scripts/xray_configurations.py`.
- Nuevo test: `tests/xray_configurations.sh`.
- Operaciones: `create --name ... [--template empty|minimal]`, `list`, `show --config-id ...`.
- Persistencia independiente bajo `/var/lib/xray-manager/configurations`; pruebas redirigen a temporales.
- Catálogo/metadatos/manifiesto cerrados; IDs `config-` + 32 hex; revisiones `rNNNNNN`; límite 16 MiB y catálogo de 10.000.
- AES-256-GCM con nonce de 12 bytes y AAD por ID/revisión; usa helper existente para cargar clave maestra, nunca crea/regenera una. No se leyó la clave real.
- Directorios root:root 0700, archivos 0600, lock exclusivo, escrituras atómicas y WAL. El journal se publica antes del rename definitivo; recuperación revierte el catálogo y retira directorio/staging tras interrupciones.
- Pruebas: plantillas, permisos, catálogo malformado, clave incorrecta/ausente, ciphertext alterado con hash recalculado y SIGKILL en tres ventanas de commit. Focal PASS; regresión completa 52/52 PASS; AST, `bash -n`, ShellCheck focal y `git diff --check` PASS.
- Auditoría: `docs/AUDITORIA_C01_GESTOR_CONFIGURACIONES_2026-11-04.md`; diseño actualizado en `docs/DISENO_GESTOR_CONFIGURACIONES_INDEPENDIENTES.md`.

**Estado:** C-01 implementado y auditado localmente, pendiente de aceptación expresa. C-02 importación/exportación no iniciada. No se integró menú, validador, edición/diff, eliminación ni perfil desde configuración independiente. No hay `apply`/`activate`. Etapa 5 y Etapa 2 siguen ABIERTAS.

Límites: no se leyó `master.key`, no se creó almacén live, no se tocó `xray_profiles.py`, VLESS/VMess, runtime, servicios, systemd, certificados, firewall, puertos o red. No se instalaron/actualizaron dependencias. VPS de pruebas, `main` y `Xray-Normativa/` intactas. Cambios locales; no commit/push/sync.

Siguiente puerta: revisión/aceptación formal de C-01. C-02 requiere autorización independiente; no continuar fases posteriores por inferencia.

## Continuidad — aceptación C-01 e implementación C-02 (2026-11-04)

El propietario respondió afirmativamente a la aceptación de C-01 como componente limitado y autorizó C-02.

### C-01

Aceptado formalmente dentro del alcance de `docs/AUDITORIA_C01_GESTOR_CONFIGURACIONES_2026-11-04.md`. No implica completar Etapa 5 ni Etapa 2.

### C-02 implementado localmente

- `preview-import --source`: vista previa sin escribir; ruta absoluta, archivo regular, rechaza symlink/hardlink y exceso 16 MiB; detecta UTF-8/BOM, JSON estricto y secciones; informa SHA-256.
- `import`: requiere `--confirm` y `--expected-sha256` de la vista previa; vuelve a leer el origen una vez y cifra exactamente esos bytes. Origen inalterado. JSON inválido o vacío requiere `--accept-invalid` y se conserva como Borrador. UTF-8 inválido se rechaza.
- `export`: una configuración/revisión por invocación; destino absoluto, symlink/hardlink rechazados, overwrite sólo con `--overwrite`; temporal privado, modo 0600, fsync y verificación byte a byte. Advierte que el resultado está en claro.
- Se amplió el contrato de manifiesto para admitir `source=import` y contenido importado de cero bytes, manteniendo revisión autenticada y estado pendiente/no validado.
- Tests incluyen BOM, JSON válido/inválido, vacío, UTF-8 inválido, origen cambiado tras preview, límites, symlink/hardlink, export exacto, overwrite y fallo parcial de escritura.

Auditoría: `docs/AUDITORIA_C02_IMPORTACION_EXPORTACION_2026-11-04.md`. C-02 implementado localmente; pendiente de aceptación expresa. C-03–C-06 no iniciadas. La preview no sustituye al validador estático Xray; no se implementó menú, exportación por lotes, reemplazo de nombre duplicado ni activación.

Límites: sólo temporales y claves sintéticas. No se leyó `master.key`, no se creó almacén live, no se modificaron perfiles/VLESS/VMess/runtime/servicios/certificados/firewall/puertos/red, ni VPS de pruebas. No se instalaron/actualizaron dependencias. `main` y `Xray-Normativa/` intactas. Sin commit/push/sync.


## Punto de continuidad vigente — C-01/C-02 sincronizados (2026-11-04)

- Rama autorizada: `design/user-identity-association-v1`; host: `Implementación-Xray`; ruta: `/opt/xray-manager`.
- C-01 del gestor de configuraciones independientes: **ACEPTADO FORMALMENTE COMO COMPONENTE LIMITADO**.
- C-02: importación/exportación implementadas, auditadas y verificadas; **pendiente de aceptación expresa**. La vista previa no equivale a validación estática Xray.
- Regresión completa: `tests/*.sh` **52/52 PASS**. `bash -n`, Python AST y `git diff --check`: PASS. ShellCheck no estaba disponible en el host y no se instaló ninguna dependencia.
- Archivos sincronizados: `scripts/xray_configurations.py`, `tests/xray_configurations.sh`, auditorías C-01/C-02 y actualizaciones de `PROJECT_STATE.md`, `HISTORY.md`, `docs/CONTINUIDAD_DEL_PROYECTO.md`, `docs/PUNTO_CONTROL_ACTUAL.md` y `docs/DISENO_GESTOR_CONFIGURACIONES_INDEPENDIENTES.md`.
- C-03–C-06 no iniciadas. Sin menú, validador estático, diff/comparación, activación ni integración de perfil desde configuración independiente. Etapa 5 y Etapa 2 siguen ABIERTAS.
- Sólo pruebas temporales y claves sintéticas. No se leyó `master.key`; no se creó almacén live; no se modificó runtime, servicios, systemd, certificados reales, firewall, puertos o red. No se tocó `Vps de Pruebas`, `main` ni `Xray-Normativa/`. No se instalaron/actualizaron dependencias.
- Sincronización GitHub/VPS solicitada expresamente por el propietario. El identificador final del commit y la verificación de árbol limpio se añadirán al cierre de esta operación.


**Resultado de sincronización:** commit `3523368729a4e872d65dc7a37c8a2276a04f640e` publicado en `origin/design/user-identity-association-v1`; checkout `Implementación-Xray:/opt/xray-manager` verificado en el mismo SHA. Push fast-forward y árbol limpio. C-02 continúa pendiente de aceptación formal; Etapa 5/Etapa 2 abiertas.

## Punto de reanudación vigente — C-03 implementada y pendiente de aceptación (2026-11-04)

C-01 y C-02 del gestor independiente están aceptados formalmente como componentes limitados. C-03 está implementada y auditada localmente en `scripts/xray_configurations.py`, con pruebas en `tests/xray_configurations_c03.sh`. Leer `docs/AUDITORIA_C03_EDICION_DIFF_COMPARACION_2026-11-04.md` antes de aceptarla.

Operaciones añadidas: `preview-edit`, `edit`, `compare`, `revisions`. La edición requiere hash de preview, revisión base y confirmación; crea una revisión nueva cifrada, conserva la anterior y utiliza WAL. Diff por JSON Pointer sin valores, objetos insensibles al orden de claves, arrays sensibles al orden. JSON inválido no produce diff estructural y sólo se conserva como Borrador con aceptación expresa. No hay validador Xray ni promoción a Validada.

Prueba focal C-03 PASS; regresión completa `tests/*.sh` 53/53 PASS. Python compile, `bash -n`, ShellCheck de la nueva prueba y `git diff --check` PASS. ShellCheck global presenta diagnósticos históricos en otros scripts/tests.

C-03 pendiente de aceptación formal. C-04 no autorizada/iniciada. No publicar ni sincronizar sin autorización independiente. Etapa 5 y Etapa 2 permanecen ABIERTAS. Sólo temporales y claves sintéticas; sin clave maestra real, almacén live, runtime, servicios, dependencias, certificados, firewall, puertos, red, VPS de pruebas, `main` o `Xray-Normativa/`.


## Aceptación C-03 y sincronización autorizada — 2026-11-04

El propietario aceptó formalmente C-03 como componente limitado dentro de `docs/AUDITORIA_C03_EDICION_DIFF_COMPARACION_2026-11-04.md`. Se autoriza publicar únicamente los cambios de C-03 y su documentación en `design/user-identity-association-v1` y sincronizar `/opt/xray-manager` con ese commit. C-04 no se inicia por esta aceptación. Etapa 5 y Etapa 2 permanecen ABIERTAS. `main`, `Xray-Normativa/`, runtime, servicios y VPS de pruebas quedan fuera del alcance.

## Continuidad vigente — C-04A implementada y auditada (2026-11-04)

C-01, C-02 y C-03 del gestor independiente están aceptadas formalmente como componentes limitados. El propietario aprobó el diseño C-04 y autorizó exclusivamente C-04A.

C-04A implementa preview-delete y delete en scripts/xray_configurations.py: valida catálogo/metadatos y todas las revisiones; verifica hash y AES-256-GCM; requiere --confirm, --expected-name y --assert-not-active; usa WAL v2 y tombstone con rollback prepared y finalización committed. Sólo elimina el objeto independiente seleccionado. Perfiles/copias, exportaciones y respaldos quedan intactos.

El almacén no integra el registro runtime y no puede detectar una aplicación manual externa. El preview lo declara (runtime_activity_verified=false) y exige la afirmación explícita del operador; no se confunde estado interno con estado real de Xray.

Auditoría: docs/AUDITORIA_C04A_ELIMINACION_SEGURA_2026-11-04.md. Focal PASS; regresión completa 54/54 PASS; Python compile, Bash syntax, ShellCheck focal y git diff --check PASS.

C-04A pendiente de aceptación formal. C-04B (exportación múltiple) y C-04C (menú Bash) no iniciadas. Etapa 5 y Etapa 2 ABIERTAS. No commit/push/sync sin autorización expresa. Sólo temporales y claves sintéticas; no almacén real, clave maestra, runtime, servicios, dependencias, certificados, firewall, puertos, red o VPS de pruebas. main y Xray-Normativa/ intactas.


## Continuidad vigente — C-04A aceptada y publicada (2026-11-04)

El propietario aceptó formalmente C-04A como componente limitado, conforme a `docs/AUDITORIA_C04A_ELIMINACION_SEGURA_2026-11-04.md`. La aceptación comprende sólo el alcance técnico, controles, pruebas y exclusiones del informe.

La implementación, prueba focal y auditoría están publicadas en `design/user-identity-association-v1`. Commit: `afb2f7bf8cc040ca2731787b9e113b5a4660a00f`. La VPS `Implementación-Xray:/opt/xray-manager` y GitHub se verificaron en el mismo SHA, con árbol de trabajo limpio en el momento de la verificación.

C-04B y C-04C no están autorizadas ni iniciadas. C-04 no está completa. Etapa 5 y Etapa 2 siguen ABIERTAS. No se tocó `main`, `Xray-Normativa/`, la VPS de pruebas ni runtime/servicios/red.

## Continuidad vigente — C-04B exportación múltiple implementada (2026-11-04)

C-01/C-02/C-03 permanecen aceptadas formalmente como componentes limitados. C-04A está aceptada, publicada y sincronizada. El propietario autorizó ahora exclusivamente C-04B; C-04C (integración del menú Bash) no está autorizada ni iniciada.

C-04B añade `preview-export-batch` y `export-batch` a `scripts/xray_configurations.py`. La entrada es un manifiesto JSON cerrado de 1–100 exportaciones, con ID, revisión (o `null` para resolver la actual), destino absoluto y overwrite individual. Preview verifica cada elemento y devuelve hash del manifiesto y hash del preview. La ejecución exige ambos hashes y confirmación explícita, vuelve a calcular preview y utiliza la revisión exacta que se mostró. Los destinos duplicados bloquean todas las entradas afectadas. Las exportaciones reutilizan el writer individual, con escritura atómica, modo 0600, verificación byte a byte y advertencia de plaintext. Un fallo individual no cancela las demás.

Auditoría: `docs/AUDITORIA_C04B_EXPORTACION_MULTIPLE_2026-11-04.md`. Prueba focal `tests/xray_configurations_c04b.sh` PASS. Regresión global final `tests/*.sh` **55/55 PASS**, incluida la revisión obsoleta. Python compile, Bash syntax, ShellCheck focal y `git diff --check` PASS.

Estado: C-04B implementada/verificada localmente, pendiente de aceptación formal. No se ha hecho commit/push/sync. No iniciar C-04C sin autorización específica. C-04, Etapa 5 y Etapa 2 siguen ABIERTAS. Sólo almacenes temporales y claves sintéticas; no se leyó `master.key`, no se accedió al almacén real, no se tocaron runtime/servicios/dependencias/certificados/firewall/puertos/red/VPS de pruebas/`main`/`Xray-Normativa/`.

## Aceptación C-04B — 2026-11-04

El propietario aceptó formalmente C-04B como componente limitado conforme a `docs/AUDITORIA_C04B_EXPORTACION_MULTIPLE_2026-11-04.md`. La implementación y sus pruebas quedan aceptadas localmente. La aceptación no implica publicación, commit, push ni sincronización. C-04C (integración del menú Bash) requiere autorización específica antes de iniciar. C-04 no está completa; Etapa 5 y Etapa 2 siguen abiertas. No se modificaron `main`, `Xray-Normativa/`, runtime, servicios, dependencias ni VPS de pruebas.


## Continuidad vigente — C-04C menú Bash implementado localmente (2026-11-04)

C-04B fue publicada y verificada en GitHub/VPS en el commit 0f8ea9df5fa4927c27deafab405c446f1c4dc4dd. Después de esa publicación, el propietario autorizó C-04C, limitada a la integración del menú Bash.

El menú aprobado CONFIGURACIONES, PERFILES Y RESPALDOS conecta ahora [1] Gestionar configuraciones de Xray con menu_independent_configurations. El módulo modules/xray_configurations_menu.sh integra consulta, creación, edición, importación, exportación individual y múltiple, comparación, revisiones y eliminación. Consulta de contenido descifrado y eliminación requieren confirmaciones específicas. No hay apply/activate ni conexión con runtime.

Auditoría: docs/AUDITORIA_C04C_INTEGRACION_MENU_BASH_2026-11-04.md. Prueba focal PASS; tests/smoke.sh y tests/stage1_menu.sh PASS; regresión completa tests/*.sh 56/56 PASS. Bash syntax global, ShellCheck focal, Python compile y git diff --check PASS.

C-04C está IMPLEMENTADA, VERIFICADA y AUDITADA LOCALMENTE; pendiente de aceptación formal. No commit/push/sync de C-04C. No se accedió al almacén real ni se leyó la clave maestra; no se modificaron runtime, servicios, dependencias, certificados, firewall, puertos, red, VPS de pruebas, main ni Xray-Normativa/. C-04, Etapa 5 y Etapa 2 continúan ABIERTAS.


## Aceptación formal C-04C y autorización de publicación — 2026-11-04

El propietario aceptó C-04C conforme a `docs/AUDITORIA_C04C_INTEGRACION_MENU_BASH_2026-11-04.md` y autorizó expresamente publicar la implementación, pruebas, auditoría y registro de aceptación en `design/user-identity-association-v1`. La aceptación es limitada a C-04C; C-04 completa, Etapa 5 y Etapa 2 siguen abiertas. No se inicia C-05. `main` y `Xray-Normativa/` continúan protegidas.


## Continuidad vigente — C-04 cerrada formalmente (2026-11-04)

El propietario aceptó formalmente el cierre integral de C-04. C-04A (eliminación segura), C-04B (exportación múltiple) y C-04C (integración del menú Bash) están implementadas, auditadas, aceptadas y publicadas. La auditoría integral obtuvo 56/56 PASS en la regresión completa y no identificó defectos funcionales bloqueantes.

Última publicación previa: `7f215b1dbfaa0b2dc7a2a3726a76dfa25b1cbb10` en `design/user-identity-association-v1`. El registro de cierre integral que se añade ahora es documental y permanece sin commit/push. C-05 no está autorizada ni iniciada. Etapa 5 y Etapa 2 siguen ABIERTAS. No se autoriza ni se realiza cambio de runtime, servicios, dependencias, certificados, firewall, puertos, red o VPS de pruebas. `main` y `Xray-Normativa/` permanecen protegidas.


## Punto de reanudación vigente — C-05A/C-05B publicadas y sincronizadas (2026-11-04)

- Rama autorizada: `design/user-identity-association-v1`.
- HEAD GitHub/VPS verificado: `1815663438770a2271d769345adbc271714a6817` (`Record accepted and published C-05A/C-05B`). Árbol de trabajo limpio.
- C-05A: motor `scripts/xray_config_validator.py`, 17/17 pruebas focales PASS, Xray 26.10.31 real aceptó una configuración sintética válida y rechazó protocolo inexistente. Aceptada formalmente como componente limitado.
- C-05B: almacén `scripts/xray_validation_store.py`, 8/8 pruebas focales PASS; informes permanentes/append-only, catálogo SHA-256, controles filesystem, lock, atomicidad, fsync y WAL. Aceptada formalmente.
- Regresión focal combinada C-05A/B: 25/25 PASS. Regresión shell C-01/C-02, C-03, C-04A/B/C y smoke general PASS; Python compile, `bash -n modules/*.sh` y `git diff --check` PASS según registro publicado.
- C-05A/B se publicaron en `0b0e36e53dbc58c2102805834c2ffc1a5edd6b25`; aceptación y continuidad se registraron en `1815663438770a2271d769345adbc271714a6817`.
- Próximo paso propuesto: C-05C, integración transaccional de motor/almacén y promoción controlada a Validada. **No autorizada ni iniciada.** Requiere autorización específica. C-05D, C-05E y C-05F también son independientes.
- No se creó el almacén live `/var/lib/xray-manager/validation`; no se leyó `/etc/xray-manager/keys/master.key`; no se modificaron runtime, servicios, certificados, firewall, puertos, dependencias ni configuración activa.
- `main` permanece en `656ecedc506a94a6461aee296b20871d51a38bf3`; `Xray-Normativa/` permanece intacta. Etapa 5 y Etapa 2 siguen ABIERTAS.
- Para reanudar: leer primero `AGENTS.md`, `PROJECT_STATE.md`, este documento, `docs/PUNTO_CONTROL_ACTUAL.md` y `HISTORY.md`; después revisar el diseño C-05 aprobado, los informes C-05A/B y la normativa Etapa 5. Ejecutar auditoría de recuperación de solo lectura y esperar autorización expresa antes de implementar C-05C.


## Punto de reanudación vigente — C-05C implementada y auditada localmente (2026-11-04)

- Base Git de la sesión: `6ab158f436d2d88755d70e954114efb4fa2f6129`; rama `design/user-identity-association-v1`.
- C-05A/B continúan aceptadas, publicadas y sincronizadas.
- C-05C: implementación en `scripts/xray_config_promotion.py`; ampliación controlada de metadatos en `scripts/xray_configurations.py`; pruebas en `tests/test_xray_config_promotion.py`.
- Expedientes: `docs/IMPLEMENTACION_C05C_PROMOCION_VALIDADA_2026-11-04.md` y `docs/AUDITORIA_C05C_PROMOCION_VALIDADA_2026-11-04.md`.
- Pruebas focales C-05C: 13/13 PASS. Regresión Python C-05A/B/C: 38/38 PASS. Shell C-01/C-02, C-03, C-04A/B/C y perfiles: PASS. Xray 26.10.31 real integrado con almacenes temporales y clave sintética.
- Estado: IMPLEMENTADA, VERIFICADA y AUDITADA LOCALMENTE; pendiente de aceptación formal. No publicada ni sincronizada.
- Siguiente paso permitido: que el propietario revise la auditoría y decida si acepta C-05C. No iniciar C-05D/E/F ni publicar/sincronizar sin autorización independiente.
- No se creó `/var/lib/xray-manager/configurations` ni `/var/lib/xray-manager/validation`; no se leyó clave maestra real ni se modificó runtime/infraestructura.


## Registro de aceptación y publicación C-05C — 2026-11-04

- Aceptación formal del propietario: «Acepto, publica cambios actualiza documentación».
- C-05C: aceptada, publicada y sincronizada en `design/user-identity-association-v1`.
- Implementación: `scripts/xray_config_promotion.py`; metadatos en `scripts/xray_configurations.py`; pruebas `tests/test_xray_config_promotion.py`.
- Evidencias: `docs/IMPLEMENTACION_C05C_PROMOCION_VALIDADA_2026-11-04.md` y `docs/AUDITORIA_C05C_PROMOCION_VALIDADA_2026-11-04.md`.
- Pruebas: 13/13 focal C-05C; 38/38 Python C-05A/B/C; suites shell C-01/C-02, C-03, C-04A/B/C y perfiles PASS.
- La publicación fue fast-forward, sin force push. El commit y HEAD remoto se consultan en el registro Git de esta publicación.
- C-05D/E/F no están autorizadas. Etapa 5 y Etapa 2 permanecen ABIERTAS.
- No se crearon almacenes live, no se leyó la clave maestra real, no se modificó runtime/infraestructura ni VPS de pruebas.

**Referencia Git de publicación C-05C:** commit `58c273a18ea32c1feddc02012d0318952c7a0689` (`58c273a`) en `design/user-identity-association-v1`; push fast-forward verificado desde el HEAD base `6ab158f436d2d88755d70e954114efb4fa2f6129`.

## Addendum de recuperación — C-05C y conectividad Git (2026-11-04)

Este addendum es la referencia cronológica más reciente para la reanudación. C-05C está ACEPTADA, AUDITADA, PUBLICADA y SINCRONIZADA. Punto Git verificado en esta sesión: rama design/user-identity-association-v1, HEAD local y GitHub 670e6ab371e620a8cb8b51f9431746f0a2270cda; árbol de trabajo limpio. El commit padre 58c273a18ea32c1feddc02012d0318952c7a0689 contiene la publicación C-05C. GitHub main permanece en 656ecedc506a94a6461aee296b20871d51a38bf3.

Los registros anteriores que describen C-05C como pendiente de aceptación o publicación son fotografías históricas anteriores a la decisión y publicación posteriores; no describen el estado vigente. No se eliminan porque preservan la trazabilidad. Para el estado actual prevalece este addendum y el registro final de aceptación/publicación C-05C.

Diagnóstico Git SSH de solo lectura: el primer git ls-remote origin falló transitoriamente. Se comprobó que el alias github.com-xray-core-manager resuelve a github.com, usuario git, y selecciona la identidad id_ed25519_xray_core_manager_rw. La autenticación directa con las identidades RW y RO fue aceptada por GitHub. Una repetición posterior de git ls-remote origin terminó correctamente y devolvió los SHA de ambas ramas. No se cambiaron claves, configuración SSH, remoto ni credenciales. La referencia local de seguimiento origin/main no existe, pero la rama remota main sí fue confirmada directamente en GitHub; no crearla ni modificarla como parte de este diagnóstico.

Normativa Etapa 5: los SHA-256 de Markdown y YAML en Xray-Normativa/ coinciden byte a byte con sus homólogos en /root/Xray_Manager_Documentacion_Final_2026-10-31. La carpeta normativa no fue modificada.

Siguiente trabajo propuesto: preparar diseño y matriz de pruebas C-05D. C-05D, C-05E y C-05F continúan sin autorización. Esta revisión no autoriza implementación, commit, push ni cambios de infraestructura. Etapa 5 y Etapa 2 siguen ABIERTAS.

## Registro de implementación C-05D — 2026-11-04

El propietario autorizó C-05D: historial y comparación de informes de validación. Se implementó exclusivamente el servicio read-only `scripts/xray_validation_history.py` y su suite `tests/test_xray_validation_history.py`; se añadieron los documentos de implementación y auditoría. La modalidad aprobada es comparación de informes de una misma configuración, permitiendo revisiones distintas y rechazando configuraciones diferentes.

Verificación local: C-05D focal H01–H38 38/38 PASS; regresión Python C-05A/B/C/D 76/76 PASS; suites shell existentes 56/56 PASS; `py_compile`, `bash -n`, `install.sh --check`, ShellCheck severidad error y `git diff --check` PASS. ShellCheck en severidad warning informa cuatro advertencias preexistentes en tests/stage1_header.sh (SC2034, dos), tests/uninstall.sh (SC2154) y tests/vless_backup_restore.sh (SC2174); no se modificaron por estar fuera del alcance.

El servicio consulta el almacén C-05B bajo su lock, valida fechas ISO-8601 con zona horaria, ofrece filtros/paginación, detalle y comparación estructurada. No modifica informes/catálogo ni el esquema C-05B. Prueba WAL con SIGKILL, integridad, concurrencia, saneamiento y solo lectura PASS.

Estado: C-05D IMPLEMENTADA, VERIFICADA Y AUDITADA LOCALMENTE; PENDIENTE DE ACEPTACIÓN FORMAL; NO PUBLICADA NI SINCRONIZADA. No se creó commit ni push. C-05E y C-05F siguen sin autorización; Etapa 5 y Etapa 2 permanecen ABIERTAS. No se modificaron main, Xray-Normativa/, almacenes live, clave maestra real, runtime, servicios, dependencias, certificados, firewall, puertos, red ni VPS de pruebas.


## Aceptación formal y publicación C-05D — 2026-11-04

El propietario aceptó formalmente C-05D y autorizó crear el commit y publicar exclusivamente en `design/user-identity-association-v1`. La aceptación cubre el servicio de historial/comparación, sus pruebas focales y la auditoría documentada. C-05D queda ACEPTADA; C-05E y C-05F continúan sin autorización independiente. Etapa 5 y Etapa 2 permanecen ABIERTAS.

## Addendum vigente — aceptación formal C-05E (2026-11-04)

C-05E — Integración del menú Bash — fue ACEPTADA FORMALMENTE por el propietario. La aceptación cubre la implementación, las pruebas, la auditoría y las limitaciones E01–E38 documentadas en `docs/AUDITORIA_C05E_MENU_BASH_2026-11-04.md`. Las entradas anteriores que indican «pendiente de aceptación» son fotografías históricas previas a esta decisión y quedan superadas por este addendum.

La aceptación no incluye publicación. Los cambios continúan locales en `design/user-identity-association-v1`, sin commit ni push; la base conocida es `ed700c1e770063f6e67c6ebaeae4652172bb2f02`. Antes de cualquier publicación se requiere autorización expresa independiente. C-05F no está autorizada ni iniciada. No se modificaron `main`, `Xray-Normativa/`, VPS de pruebas, secretos, almacenes live, runtime ni infraestructura. Etapa 5 y Etapa 2 permanecen ABIERTAS.

## Addendum de publicación — C-05E (2026-11-04)

C-05E está ACEPTADA, AUDITADA, PUBLICADA y SINCRONIZADA. Commit publicado en `design/user-identity-association-v1`: `8378ca47a751678f4eeeab20a5e2d06effd47fff` (`feat(validation): integrate C-05E validation menu`). Push fast-forward desde `ed700c1e770063f6e67c6ebaeae4652172bb2f02`; la consulta posterior a GitHub confirmó el SHA remoto idéntico. `main` permanece en `656ecedc506a94a6461aee296b20871d51a38bf3`. La aceptación y publicación de C-05E no autorizan C-05F. `Xray-Normativa/`, VPS de pruebas, secretos, almacenes live, runtime e infraestructura permanecen intactos. Etapa 5 y Etapa 2 siguen ABIERTAS.

## Addendum de continuidad — diseño C-05F preparado (2026-11-04)

El propietario autorizó preparar el diseño y la matriz de C-05F, no ejecutar aún la auditoría ni implementar correcciones. Consultar `docs/DISENO_C05F_AUDITORIA_INTEGRAL_2026-11-04.md` y `docs/MATRIZ_C05F_AUDITORIA_INTEGRAL_2026-11-04.md`. El alcance propuesto es una auditoría transversal del subsistema C-05A–C-05E frente a la parte de validación de Etapa 5; no es el cierre integral de Etapa 5. La matriz define 71 criterios y 15 huecos conocidos, sin resultados de ejecución. Antes de iniciar, obtener confirmación del propietario sobre el alcance, el tratamiento de las opciones normativa de validación externa/activa actualmente deshabilitadas y la separación entre auditoría y corrección. No modificar código ni ejecutar la auditoría hasta recibir esa autorización. Los documentos se encuentran locales, sin commit ni push. C-05A–E siguen aceptadas/publicadas; C-05F no ejecutada. Etapa 5 y Etapa 2 siguen abiertas.

## Addendum de continuidad — C-05F ejecutada (2026-11-04)

C-05F se ejecutó después de que el propietario aprobara las condiciones de alcance. Revisar primero docs/AUDITORIA_C05F_AUDITORIA_INTEGRAL_2026-11-04.md y docs/MATRIZ_C05F_AUDITORIA_INTEGRAL_2026-11-04.md. La auditoría se limitó a C-05A–C-05E; no cierra Etapa 5. Resultado técnico PASS con hallazgo menor H-01 (symlink roto en componente padre de la ruta CLI tratado como almacén ausente) y divergencias D-01/D-02 (validación externa/activa deshabilitadas), D-03 (mecanismo runtime pendiente), D-04 (backup/restore fuera de alcance C-05F) y D-05 (filtros UI parciales). Regresión: 76/76 Python y 57/57 shell PASS. Flujo A→E y concurrencia con datos sintéticos/almacenes temporales PASS. No se corrigió código, no se tocó normativa ni infraestructura y no se hizo commit/push. C-05F está pendiente de aceptación formal. La corrección H-01 y la implementación de funciones pendientes requieren autorización separada. Etapa 5 y Etapa 2 permanecen abiertas.


## Continuidad — C-05F aceptada formalmente (2026-11-04)

El propietario aceptó formalmente C-05F, considerando el dictamen PASS, H-01 y D-01–D-05. Consultar el expediente y la matriz C-05F para los resultados y límites completos. La aceptación es administrativa: H-01 permanece abierto y no corregido; validación externa/activa y mecanismo runtime no se implementaron; backup/restore y filtros UI conservan sus pendientes documentados. No se autorizó publicación, commit, push ni sincronización. Tampoco se autorizó cerrar Etapa 5 o Etapa 2. Para continuar, solicitar decisión expresa sobre el siguiente trabajo concreto, especialmente si se propone corregir H-01.

## Continuidad — remediación H-01 completada (2026-11-04)

H-01 de C-05F quedó CORREGIDO Y VERIFICADO bajo autorización expresa del propietario. La CLI inspecciona con lstat() cada componente de la ruta absoluta del almacén y rechaza symlinks rotos o válidos. Pruebas H39–H42; historial 42/42, Python 80/80 y shell 57/57 PASS. Consultar docs/CORRECCION_H01_RUTAS_SYMLINK_C05F_2026-11-04.md. D-01–D-05 continúan pendientes/documentados; no se implementó validación externa/activa ni prueba runtime, y backup/restore sigue pendiente de auditoría. Etapa 5 y Etapa 2 siguen abiertas.


## Punto de reanudación histórico — U-01 Usuarios V2 → VLESS (2026-11-04)

El propietario aprobó el diseño U-01 y autorizó su implementación con el alcance descrito. La implementación está terminada localmente en `/opt/xray-manager`, rama `design/user-identity-association-v1`, sobre la base `ca6d76895821310a3072d9de47268f925ecea7ba`; commit publicado `1c2cd12f15be75d9f3a080ce028951724618c492`.

- Usuarios V2 es la fuente única del asistente VLESS; no existe fallback al gestor legacy.
- Nuevo exportador candidato `users_v2_export_vless_candidate_clients`: active y no vencido, independiente de provisioning/runtime, lock compartido, sin inicialización accidental del almacén. La vista runtime previa conserva filtro applied/applied.
- Menú V2: UUID automático predeterminado o UUID manual oculto; unicidad global y normalización.
- Creación y recuperación VLESS usan el constructor V2.
- Pruebas shell: 58/58 PASS. Controles: bash -n, py_compile, install.sh --check, ShellCheck -S error, shfmt y git diff --check PASS. Xray 26.10.31 real aceptó un candidato VLESS-WS generado desde una asociación V2 active/draft/not_applied.
- Expedientes: `docs/IMPLEMENTACION_U01_INTEGRACION_USUARIOS_V2_VLESS_2026-11-04.md` y `docs/AUDITORIA_U01_INTEGRACION_USUARIOS_V2_VLESS_2026-11-04.md`.
- Estado: IMPLEMENTADA, VERIFICADA, AUDITADA, PUBLICADA y SINCRONIZADA; aceptación formal pendiente. Commit `1c2cd12f15be75d9f3a080ce028951724618c492`.
- Siguiente paso: solicitar aceptación formal de U-01. Después, diseñar y solicitar autorización específica para el mecanismo seguro de publicación/aplicación runtime. ACME DNS-01/Cloudflare y prueba externa NetMod continúan fuera de U-01.
- No se migraron registros legacy, no se usó la clave maestra real, no se modificaron almacenes live/runtime/servicios/certificados/firewall/puertos/red/dependencias, no se accedió a la VPS de pruebas y `main`/`Xray-Normativa/` permanecen intactas.
- Etapa 2, Etapa 3 y Etapa 5 no quedan cerradas por U-01.


## Registro de publicación U-01 — 2026-11-04

U-01 se publicó en `design/user-identity-association-v1` mediante commit `1c2cd12f15be75d9f3a080ce028951724618c492` (`feat(vless): integrate V2 users into candidate generation`). Push fast-forward desde `ca6d76895821310a3072d9de47268f925ecea7ba`; no se utilizó force push. La consulta a GitHub confirmó el SHA remoto. La aceptación formal del propietario sigue pendiente. `main`, `Xray-Normativa/`, VPS de pruebas, almacenes live, runtime e infraestructura permanecen intactos.

## Aceptación formal U-01 y auditoría — 2026-11-04

El propietario respondió afirmativamente a la solicitud de aceptación formal de U-01 y su auditoría, autorizando avanzar al diseño del mecanismo de aplicación runtime. U-01 queda **ACEPTADA FORMALMENTE** junto con su auditoría. La aceptación no cierra Etapa 2, Etapa 3 ni Etapa 5, y no convierte la validación `xray run -test` en una prueba de conectividad real.

U-01 permanece IMPLEMENTADA, VERIFICADA, AUDITADA, PUBLICADA y SINCRONIZADA en `design/user-identity-association-v1`. Referencias de publicación: `1c2cd12f15be75d9f3a080ce028951724618c492` y `bcb3338a527e3f4021489815d92797b9a59fdd62`. La documentación normativa y `main` no se modificaron.

Se preparó `docs/DISENO_APLICACION_RUNTIME_XRAY_2026-11-04.md`. Es una propuesta técnica, no una autorización de implementación ni de aplicación live. Separa validación, staging, publicación atómica, reinicio systemd, verificación y rollback; define R-01–R-06 y una matriz inicial de 15 criterios. Las decisiones de §9 deben ser revisadas por el propietario antes de implementar. R-06 exige autorización independiente y específica.

## Decisiones runtime aprobadas — 2026-11-04

El propietario aprobó el **reinicio controlado** mediante `systemctl restart xray.service` (sin asumir hot reload) y la estrategia de **rollback**: restaurar la configuración anterior de forma atómica y recuperar el estado previo del servicio; si estaba inactivo, no arrancarlo. Si no existe configuración previa, detenerse y requerir intervención controlada. Estas decisiones se incorporan a `docs/DISENO_APLICACION_RUNTIME_XRAY_2026-11-04.md`.

La aprobación no autoriza todavía implementación R-01–R-05 ni ensayo live R-06. Siguen pendientes las decisiones sobre primera aplicación sin configuración anterior, señales locales de verificación y alcance aislado/live. No se modificó runtime ni infraestructura.


## Continuidad vigente — R-01 publicada; siguiente R-02 (2026-11-04)

El estado vigente del proyecto está consolidado en PROJECT_STATE.md y docs/PUNTO_CONTROL_ACTUAL.md. Este bloque es el punto de reanudación; los apartados anteriores conservan trazabilidad histórica y no deben usarse como estado actual si difieren de este bloque.

- **Repositorio:** Jaok04/xray-core-manager.
- **Rama autorizada:** design/user-identity-association-v1. No modificar main.
- **VPS desarrollo:** /opt/xray-manager. No tocar la VPS de pruebas.
- **Sincronización documental:** la reconciliación se publicó en 94556849316852625fbcf98d8ea0796600097088 en design/user-identity-association-v1. GitHub confirmó el mismo SHA y /opt/xray-manager quedó limpio y alineado. Volver a verificar el HEAD real al iniciar cada sesión.
- **Normativa:** Xray-Normativa/ es inmutable sin consentimiento explícito. Los 14 archivos Markdown/YAML coinciden byte a byte con /root/Xray_Manager_Documentacion_Final_2026-10-31. No editar ni regenerar.
- **U-01:** aceptada formalmente.
- **Diseño runtime:** aprobado para R-01–R-05 exclusivamente aisladas; la identidad debe ser profile_id + revision conforme a Etapa 5 §3.1. R-06/live no autorizada.
- **R-01:** implementada, integrada en CLI/menú, verificada en fixtures, auditada localmente, publicada y sincronizada; aceptación formal específica pendiente.
- **Componentes:** scripts/xray_profile_validation_store.py (almacén independiente de informes); scripts/xray_profile_validation.py (motor estático/nativo y persistencia transaccional); scripts/xray_runtime_preflight.py (preflight read-only); modules/profiles.sh opción 8; scripts/xray_profiles.py (transacciones manifiesto/metadata); config/paths.sh (ruta del almacén).
- **Expedientes:** docs/DISENO_APLICACION_RUNTIME_XRAY_2026-11-04.md; docs/IMPLEMENTACION_R01_PREFLIGHT_PERFIL_2026-11-04.md; docs/AUDITORIA_R01_PREFLIGHT_PERFIL_2026-11-04.md.
- **Pruebas:** focal R-01 28/28 PASS (preflight 18/18 + integración 11/11); regresión Python 108/108 PASS; shell 58/58 PASS; py_compile, bash -n global, ShellCheck focal, install.sh --check y git diff --check PASS.
- **Limitaciones:** no se usó el almacén de perfiles ni la clave maestra reales; el estado systemd es fixture; no se probó la identidad efectiva xray ni lectura de leases TLS. Eso corresponde a R-02.
- **Siguiente paso autorizado:** R-02 — staging de la revisión exacta del perfil y leases TLS en directorio temporal, validación bajo identidad de servicio simulada. No publicar runtime.
- **Fuera de alcance:** R-06/live, /etc/xray/config.json, systemd real, runtime, certificados desplegados, firewall, puertos, red, dependencias, VPS de pruebas, main y Xray-Normativa/.
- **Etapas:** Etapas 2, 3 y 5 permanecen ABIERTAS.

Para comenzar en otra conversación, leer AGENTS.md, PROJECT_STATE.md, docs/PUNTO_CONTROL_ACTUAL.md, este documento y HISTORY.md; verificar HEAD remoto, rama, árbol y SHA-256 normativos antes de continuar. No repetir R-01 ni inferir que R-02 ya comenzó.

## Continuidad vigente — R-02 implementada, auditada y pendiente de aceptación (2026-11-04)

El último incremento local es R-02. Antes de continuar, revisar docs/IMPLEMENTACION_R02_STAGING_PERFIL_TLS_2026-11-04.md, docs/AUDITORIA_R02_STAGING_PERFIL_TLS_2026-11-04.md y la sección 13 de docs/DISENO_APLICACION_RUNTIME_XRAY_2026-11-04.md.

- Repositorio: Jaok04/xray-core-manager; rama autorizada design/user-identity-association-v1; VPS de desarrollo /opt/xray-manager.
- R-01 está publicada/sincronizada y su aceptación formal específica está pendiente.
- R-02 está implementada/verificada/auditada localmente; todavía no tiene commit ni push.
- Mecanismo: mapa explícito inbound tag → connection_id; certificate_id desde configuración central; lease mediante certificate_resolver; configuración staged con rutas TLS temporales.
- Validación final: Xray-core 26.10.31 real, UID/GID simulado 65534:65534, certificado/clave sintéticos. No se ejecutó systemd real.
- Pruebas: R-02 9/9; Python 117/117; shell 58/58; verificaciones estáticas PASS.
- Limitación: el mapa es un archivo de entrada separado y su hash/contenido quedan ligados al manifiesto staged; UI/almacén persistente del mapa fuera del alcance R-02.
- Siguiente paso: aceptación formal R-02 y autorización de publicación; después R-03 snapshot/journal.
- No repetir R-01/R-02. No ejecutar R-06/live ni prueba NetMod. No tocar clave maestra real, almacenes live, runtime, systemd real, certificados desplegados, firewall, puertos, red, dependencias, VPS de pruebas, main o Xray-Normativa/.
- Etapas 2, 3 y 5 siguen ABIERTAS.

## Continuidad vigente — R-03 snapshot/journal (2026-11-04)

Leer docs/IMPLEMENTACION_R02_STAGING_PERFIL_TLS_2026-11-04.md, docs/AUDITORIA_R02_STAGING_PERFIL_TLS_2026-11-04.md, docs/IMPLEMENTACION_R03_SNAPSHOT_JOURNAL_2026-11-04.md y docs/AUDITORIA_R03_SNAPSHOT_JOURNAL_2026-11-04.md antes de modificar estos incrementos.

- R-01: publicada/sincronizada; aceptación formal específica pendiente.
- R-02: implementada y auditada localmente; Xray 26.10.31 real aceptó la config staged con lease TLS sintético. CLI endurecido: fixture_root obligatorio y todas las rutas de datos dentro del fixture; no hay defaults a claves/almacenes live.
- R-03: implementada y auditada localmente; snapshot/journal/recuperación idempotente, sin publicación ni acciones systemd.
- Pruebas: R-02 11/11; R-03 21/21; Python 140/140; shell 58/58; verificaciones estáticas PASS.
- Integración R-02→R-03: staging real, resolutor central, lease sintético y snapshot en XRAY_SERVICE_ROOT fixture comprobados en una misma prueba.
- Marcadores obligatorios R-03: XRAY_SERVICE_ROOT, operation_store y lease_root; locks dentro de operation_store.
- No se ha creado commit ni push para R-02/R-03. Solicitar aceptación formal y autorización de publicación.
- Siguiente paso: R-04 publicación atómica aislada, después de revisión/aceptación.
- No tocar clave maestra real, almacenes live, /etc/xray/config.json, systemd real, runtime, certificados desplegados, firewall, puertos, red, dependencias, VPS de pruebas, main o Xray-Normativa/. No ejecutar R-06/live ni NetMod.
- Etapas 2, 3 y 5 siguen ABIERTAS.


## Continuidad vigente — R-04 publicación atómica aislada (2026-11-04)

Antes de continuar leer:
- docs/IMPLEMENTACION_R02_STAGING_PERFIL_TLS_2026-11-04.md y docs/AUDITORIA_R02_STAGING_PERFIL_TLS_2026-11-04.md
- docs/IMPLEMENTACION_R03_SNAPSHOT_JOURNAL_2026-11-04.md y docs/AUDITORIA_R03_SNAPSHOT_JOURNAL_2026-11-04.md
- docs/IMPLEMENTACION_R04_PUBLICACION_ATOMICA_2026-11-04.md y docs/AUDITORIA_R04_PUBLICACION_ATOMICA_2026-11-04.md

Estado: R-02 11/11; R-03 journal 22/22; R-04 12/12; Python 153/153; shell 58/58 PASS. Integración R-02→R-03→R-04 verificada en fixture. R-04 implementa publicación atómica en XRAY_SERVICE_ROOT fixture, validación Xray, journal, rollback y recuperación; no ejecuta systemd.

R-02/R-03/R-04 siguen locales, sin commit/push, pendientes de revisión/aceptación formal y autorización de publicación. Siguiente paso después de aceptación: R-05 systemd simulado. No ejecutar R-06/live ni NetMod.

Restricciones intactas: no tocar /etc/xray real, systemd real, clave maestra ni almacenes live, certificados desplegados, firewall, puertos, red, dependencias, VPS de pruebas, main o Xray-Normativa/. Etapas 2, 3 y 5 siguen ABIERTAS.


## Continuidad vigente — R-01–R-04 publicadas; R-05 en diseño (2026-11-04)

Este bloque es el punto de reanudación vigente y supera los bloques históricos que describen R-02–R-04 como no publicados. Los registros anteriores se conservan por trazabilidad.

- Repositorio: `Jaok04/xray-core-manager`; rama autorizada: `design/user-identity-association-v1`.
- VPS de desarrollo: `Implementación-Xray`; directorio `/opt/xray-manager`.
- HEAD verificado al corte: `05aceabf11414040abbb32fff1428984370ff521`.
- R-01–R-04: implementadas, verificadas/auditadas, publicadas y sincronizadas; aceptación formal individual pendiente para cada incremento.
- Pruebas focales documentadas: R-01 28/28, R-02 11/11, R-03 22/22, R-04 12/12. Regresión global documentada: Python 153/153 y Bash 58/58 PASS. No se reejecutaron en esta actualización.
- R-05: NO INICIADA. Diseño propuesto en `docs/DISENO_R05_ORQUESTACION_SYSTEMD_SIMULADA_2026-11-04.md`; requiere aprobación expresa antes de implementar.
- R-06/live: NO AUTORIZADA.
- Decisiones aprobadas: identidad `profile_id + revision`; asociación explícita `inbound_tag → connection_id`; staging temporal; snapshot/journal; publicación atómica; estrategia inicial `systemctl restart xray.service` sin asumir hot reload; rollback de configuración y recuperación del estado previo; si estaba inactivo, no arrancarlo durante la restauración.
- Los 13 archivos normativos sustantivos de `Xray-Normativa/` coinciden por SHA-256 con la copia maestra; `README.md` es auxiliar. La normativa es inmutable sin autorización específica.
- Etapas 2, 3 y 5 permanecen ABIERTAS. Publicar no equivale a aceptación formal ni a cierre de etapa.

Siguiente acción: revisar y aprobar o devolver el diseño R-05. No repetir R-01–R-04. No ejecutar systemd/Xray real, leer la clave maestra, tocar almacenes live, certificados desplegados, firewall, puertos, red, dependencias ni VPS de pruebas.


## Continuidad vigente — objetivo primer servicio real VLESS + WS + TLS (2026-11-04)

La prioridad del proyecto cambió: el siguiente objetivo de validación es ejecutar un servicio real VLESS + WebSocket + TLS desde Xray-Core Manager. No comenzar protocolos adicionales ni repetir R-01–R-04.

1. Leer `docs/PLAN_HITO_PRIMER_SERVICIO_REAL_VLESS_WS_TLS_2026-11-04.md` para el plan H0–H8.
2. Leer `docs/PUNTO_CONTROL_ACTUAL.md` y `PROJECT_STATE.md` para el estado vigente.
3. R-01–R-04 ya están publicadas/sincronizadas en la rama autorizada; sus aceptaciones formales individuales siguen pendientes. Las pruebas son evidencia histórica, no resultados reejecutados en esta actualización.
4. R-05 dispone de diseño de orquestación simulada. El simulador será un banco de pruebas, no el resultado final: la arquitectura deberá admitir un adaptador real acotado a `xray.service`, sujeto a autorización live independiente.
5. Decisiones aprobadas: reinicio de servicio activo requiere confirmación; si se rechaza, queda `published_pending_apply`; publicar con servicio inactivo no lo inicia y queda `published_pending_start`; el inicio manual desde el administrador requiere confirmación; cada operación tiene `generation_id` único.
6. Decisiones pendientes de diseño: estado previo `failed` si no puede demostrarse equivalencia después de rollback; extensión versionada del journal existente frente a registro separado. No inventar aprobación.
7. Siguiente tarea: H0, auditoría de brechas, solo lectura. Clasificar módulos existentes/parciales/ausentes para instalación, systemd, DNS/ACME, TLS centralizado, VLESS-WS-TLS, perfiles, publicación y diagnóstico. No implementar hasta entregar la matriz y recibir aprobación.
8. R-06/live continúa NO AUTORIZADA. Este cambio de prioridad no permite instalar Xray, modificar systemd/runtime, certificados reales, DNS, firewall, puertos, red ni ejecutar NetMod.
9. Mantener normativa inmutable, `main` protegida, no usar VPS de pruebas, no leer la clave maestra y publicar únicamente en `design/user-identity-association-v1`.

Para reanudar, verificar HEAD, upstream, árbol limpio y sincronización GitHub/VPS. No asumir que el estado del último commit histórico sigue vigente.


## Continuidad vigente — auditoría H0 del primer VLESS-WS-TLS (2026-11-04)

1. El informe H0 está en `docs/AUDITORIA_H0_BRECHAS_PRIMER_SERVICIO_VLESS_WS_TLS_2026-11-04.md`. Leerlo antes de proponer implementación.
2. Dictamen: aún no existe recorrido completo VLESS-WS-TLS administrado por el Manager. Reutilizar instalador Xray, control systemd independiente, asistente/adaptador VLESS, catálogo/resolutor TLS y R-01–R-04.
3. Brechas clave: Etapa 4 (UI/domains/DNS/ACME), perfil cliente/Host/SNI VLESS, activación de perfil, runtime apply live, R-05, diagnóstico completo y backup genérico.
4. En la VPS `Implementación-Xray`, comprobación read-only de H0: Ubuntu 24.04.4 amd64; Xray 26.10.31/geodata presentes; unidad `xray.service`, `/etc/xray/config.json`, usuario/grupo `xray` ausentes. No ejecutar systemctl ni asumir estado del servicio.
5. Normativa comparada: 14/14 archivos con homólogo en el respaldo idénticos byte a byte. No modificar `Xray-Normativa/`.
6. H0 está preparada y pendiente de aceptación formal. No comenzar implementación hasta revisar el informe y aprobar el alcance siguiente.
7. R-01 no se repite: es preflight read-only dependiente de fixture de estado. R-02–R-04 no se repiten y continúan aisladas a fixtures. R-05 no implementada. R-06/live no autorizada.
8. No leer `/etc/xray-manager/keys/master.key`, no acceder a almacenes live, no usar la VPS de pruebas y no modificar runtime, systemd, DNS, certificados, firewall, puertos o red sin autorización específica.
9. Verificar rama, HEAD, árbol y sincronización antes de continuar; la línea base de esta auditoría fue `af4b562fb3608392b0a16388390e1dfe9b849898`.


## Continuidad vigente — MVP mínimo de despliegue VLESS-WS-TLS (2026-11-04)

1. La aceptación formal de H0 fue otorgada. Leer `docs/AUDITORIA_H0_BRECHAS_PRIMER_SERVICIO_VLESS_WS_TLS_2026-11-04.md`.
2. El propietario redujo el alcance: el objetivo inmediato es demostrar que el Manager puede instalar/preparar Xray, gestionar un certificado, crear usuario/conexión VLESS-WS-TLS, generar/validar configuración y ejecutar/verificar el servicio.
3. Seguir exclusivamente el plan vigente `docs/PLAN_MVP_DESPLIEGUE_VLESS_WS_TLS_2026-11-04.md`: B0 inspección focal; B1 Xray/servicio; B2 certificado; B3 usuario/conexión; B4 aplicación/inicio; B5 prueba externa.
4. Reutilizar lo existente. No repetir R-01–R-04 ni convertir R-05 avanzado en prerrequisito. Mantener la arquitectura y seguridad mínimas necesarias, sin ampliar el alcance.
5. Método ACME propuesto para el primer recorrido: Let's Encrypt + Certbot HTTP-01 standalone; validar DNS A/AAAA y accesibilidad del puerto 80 antes de emitir. No instalar Certbot ni otras dependencias sin autorización expresa.
6. Mantener la distinción cliente/servidor: certificado inbound, Host WebSocket y SNI/serverName del cliente son parámetros relacionados pero no intercambiables.
7. Reglas esenciales: validar con Xray antes de publicar; conservar copia recuperable; publicar atómicamente; permisos mínimos; servicio active requiere confirmación para restart; servicio inactive no se inicia por publicar; estado failed/unknown bloquea la acción automática.
8. La implementación y pruebas aisladas están dentro del alcance aprobado. Live requiere autorización específica para el servidor, las operaciones, rutas, ventana y reversión. No modificar systemd/runtime, certificados reales, DNS, firewall, puertos o red por inferencia.
9. No usar `Vps de Pruebas`; usar únicamente `Implementación-Xray` para inspección/desarrollo autorizado. No leer `/etc/xray-manager/keys/master.key`.
10. No modificar `main` ni `Xray-Normativa/`. Publicar solo en `design/user-identity-association-v1`; mantener pruebas, auditoría y continuidad por bloque.

**Siguiente punto:** B0 — inspeccionar funciones/archivos concretos que se reutilizarán y definir el cambio mínimo de B1. No ejecutar instalaciones ni cambios live.


## Continuidad vigente — I-01 compositor VLESS-WS-TLS (2026-11-04)

Este bloque sustituye como siguiente tarea los puntos de continuidad anteriores que proponían iniciar B0. La decisión actual es implementar el puente de composición entre Usuarios V2, VLESS-WS-TLS y perfiles versionados, sin ejecutar live.

- Rama: `design/user-identity-association-v1`; VPS: `Implementación-Xray:/opt/xray-manager`.
- HEAD base antes de los cambios locales: `bf73fd6a15aa169379c7cd71d1ea9cf5fb13f8b1`. Los archivos I-01 están actualmente sin commit.
- El propietario aprobó un mapping TLS auxiliar privado separado del JSON de perfil, vinculado por path a `profile_id` y revisión, con el esquema exacto `{schema_version:1,bindings:[{inbound_tag,connection_id}]}` que consume R-02.
- Nuevo `scripts/vless_ws_tls_composer.py`: solo modalidad `vless_ws_tls`; verifica conexión draft/no aplicada, configuración persistida, certificado central activo, exportador oficial Usuarios V2, UUID/tag/puerto, revisión esperada y mappings TLS previos.
- Construye inbound VLESS `network=ws`, `security=tls`, `tlsSettings.certificates=[]`; preserva los demás inbounds/outbounds y crea revisión inmutable no validada. No activa perfil ni ejecuta R-02.
- Mapping: `<mapping-root>/<profile_id>/<revision>.json`, directorios 0700 y archivo 0600, escritura atómica. Si el mapping falla después de crear la revisión, informa `REVISIÓN INCOMPLETA`; no continuar a R-02.
- Prueba focal `tests/test_vless_ws_tls_composer.py`: 11/11 PASS, incluida lectura del mapping mediante el parser real R-02. Regresión completa: Python 163/163 y Bash 58/58 PASS; `py_compile`, `bash -n`, ShellCheck `-S error`, `git diff --check` e `install.sh --check` PASS.
- Documentación: `docs/IMPLEMENTACION_I01_COMPOSITOR_VLESS_WS_TLS_2026-11-04.md` y `docs/AUDITORIA_I01_COMPOSITOR_VLESS_WS_TLS_2026-11-04.md` (auditoría focal PASS).
- Estado al corte: IMPLEMENTADO, VERIFICADO y AUDITADO en alcance focal; ACEPTADO formalmente el 2026-11-05 con limitaciones documentadas. Publicación autorizada por separado; confirmar commit/push y sincronización.
- No repetir R-01–R-04. R-05 en pausa; R-06/live y NetMod NO AUTORIZADAS. No tocar clave maestra real, almacenes live, Xray/systemd real, certificados desplegados, DNS, firewall, puertos, red, dependencias, VPS de pruebas, `main` ni `Xray-Normativa/`.

Para reanudar, leer `AGENTS.md`, `PROJECT_STATE.md`, `docs/PUNTO_CONTROL_ACTUAL.md`, este documento, `docs/IMPLEMENTACION_I01_COMPOSITOR_VLESS_WS_TLS_2026-11-04.md` y `HISTORY.md`; verificar rama, HEAD, árbol y remoto. I-01 está aceptado formalmente; verificar el commit remoto y la sincronización antes de continuar.


## Continuidad vigente — I-02 / I-03 VLESS-WS-TLS (2026-11-05)

Este bloque sustituye el siguiente paso anterior que proponía integrar I-01 y resolver Host/SNI. I-02/I-03 ya están implementados localmente en el alcance descrito; no repetir su trabajo.

- Rama autorizada: design/user-identity-association-v1.
- HEAD remoto/local de partida: commit I-01 792f382ca1b4f753ff763dc50a442aa66a0cd42f. Los cambios I-02/I-03 permanecen locales, sin commit/push.
- I-02: opción [9] del menú de perfiles; selección de perfil con configuración/revisión actual y conexión VLESS-WS-TLS draft y runtime_applied=false; previsualización incluye path, Host, SNI y certificado; confirmación; crea revisión nueva e inmutable pendiente de validación. No activa perfil ni ejecuta R-01–R-04.
- I-03: transport_options.host y client_options.tls_server_name, esquema 2; esquema 1 compatible. Xray inbound recibe wsSettings.host; SNI permanece solo como metadata del cliente.
- Xray 26.10.31 valida WS-TLS con y sin Host. No usar wsSettings.headers.Host porque Xray lo marca obsoleto; el campo actual es wsSettings.host.
- Config Store, Certificate Resolver y backup/restore admiten esquema 2; backup/restore conserva Host/SNI y el ID de certificado central.
- Pruebas: compositor focal 11/11; menú, asistente TLS, backup/restore y Xray integration PASS. Regresión completa final: Python 164/164, Bash 59/59; py_compile, bash -n global, ShellCheck focal en todos los Bash modificados, git diff --check e install.sh --check PASS. ShellCheck global completo había pasado en la ejecución previa.
- Exportación URI VLESS para NetMod no está implementada. Antes se debe definir endpoint público por conexión (dominio/IP y política). No asumir internet.tvrc.me u otro dominio histórico.
- Aún falta aceptación formal de I-02/I-03 y autorización separada de commit/push. No publicar ni sincronizar hasta recibirlas.
- No se ha hecho ninguna operación live. No tocar Xray/systemd real, certificados reales, DNS, firewall, puertos, red, dependencias, VPS de pruebas, main o Xray-Normativa/.
- Documentos: docs/DECISION_I02_I03_VLESS_WS_TLS.md, docs/IMPLEMENTACION_I02_I03_VLESS_WS_TLS_2026-11-05.md, docs/AUDITORIA_I02_I03_VLESS_WS_TLS_2026-11-05.md.

Siguiente paso: presentar el informe al propietario para revisión y aceptación formal; mantener cambios locales hasta autorización separada de publicación. Para exportación cliente, definir antes el endpoint público de conexión.


## Punto de reanudación vigente — I-04 VLESS-WS-TLS exportación cliente (2026-11-05)

El propietario autorizó expresamente exportación para NetMod usando hellen.tvrc.me:443, con puerto público igual al puerto del inbound. Se añadió scripts/vless_client_export.py y la opción [10] del menú de perfiles. La exportación toma un perfil y revisión exactos, contrasta mapping privado con inbounds TLS centralizados y recupera la configuración fuente con VLESS Config Store. Emite un URI por UUID; host y sni se incluyen solo si están configurados, sin inferirlos del endpoint. El TXT opcional es 0600, atómico y sin sobrescritura.

Pruebas focales I-04: 7/7 PASS; integración de menú/compositor PASS. Regresión: Python 171/171 y Bash 59/59 PASS; py_compile, bash -n, ShellCheck focal, install.sh --check y git diff --check PASS. La exportación no activa ni valida perfiles, no llama R-01–R-04 y no toca runtime/systemd, DNS, firewall, puertos ni certificados desplegados. No se probó NetMod real ni conectividad externa.

**Estado:** I-02/I-03/I-04 IMPLEMENTADOS, VERIFICADOS y AUDITADOS en alcance focal; aceptación formal pendiente; no publicados ni sincronizados. Conservar todos los cambios locales. No hacer commit/push sin autorización expresa. main y Xray-Normativa/ permanecen protegidas.

**Siguiente paso:** revisión del propietario y aceptación formal de I-02/I-03/I-04; después, solicitar autorización separada de publicación en design/user-identity-association-v1. No iniciar operaciones live.


## Continuidad vigente — publicación I-02/I-03/I-04 (2026-11-05)

1. El propietario aceptó formalmente I-02, I-03 e I-04 con las limitaciones de `docs/AUDITORIA_I02_I03_VLESS_WS_TLS_2026-11-05.md` y `docs/AUDITORIA_I04_VLESS_CLIENT_EXPORT_2026-11-05.md`.
2. El propietario autorizó expresamente commit/push/sincronización exclusivamente a `design/user-identity-association-v1`. `main` y `Xray-Normativa/` permanecen protegidas.
3. Base de publicación: I-01 `792f382ca1b4f753ff763dc50a442aa66a0cd42f`; cambios I-02/I-03/I-04 estaban locales y sin divergencia remota.
4. Regresión previa a publicar: Python 171/171 y Bash 59/59 PASS; `py_compile`, `bash -n`, ShellCheck `-S error`, `install.sh --check`, `git diff --check` PASS.
5. Comparación de normativa sustantiva: 13/13 archivos byte a byte coincidentes con el respaldo. No modificar `Xray-Normativa/`.
6. I-02 agrega opción [9] del menú para componer nueva revisión inmutable. I-03 persiste Host WebSocket y SNI cliente por separado (esquema 2, esquema 1 compatible). I-04 exporta URI para `hellen.tvrc.me:443`; no valida DNS, certificado desplegado, listener, NetMod ni WAN.
7. No activar perfiles ni ejecutar R-01–R-04 como parte de esta publicación. No tocar runtime/systemd real, certificados reales, DNS, firewall, puertos, red, dependencias, clave maestra ni VPS de pruebas. R-06/live no autorizada.
8. Tras el push, verificar SHA remoto, archivos publicados y contenido del checkout. La aceptación de incrementos no cierra Etapas 2, 3 ni 5.


## Cierre de publicación — I-02/I-03/I-04 (2026-11-05)

- Commit funcional: `ac119d923ba0eae35579e944d59f5262c5d105a7` (`feat(vless): integrate profile composition and NetMod export`).
- Publicado por fast-forward en `design/user-identity-association-v1`; SHA remoto confirmado idéntico.
- `git fetch` confirmó HEAD local = `origin/design/user-identity-association-v1`; checkout limpio después de publicar.
- Archivos de código, pruebas, auditorías, decisiones y continuidad I-02/I-03/I-04 presentes en el árbol remoto.
- `main` intacta (`656ecedc506a94a6461aee296b20871d51a38bf3`). `Xray-Normativa/` intacta; 13/13 documentos sustantivos coinciden byte a byte con el respaldo.
- I-02/I-03/I-04: IMPLEMENTADAS, VERIFICADAS, AUDITADAS, ACEPTADAS, PUBLICADAS y SINCRONIZADAS. No implica cierre de Etapas 2, 3 o 5.
- Sin operaciones live, NetMod real, WAN, DNS, certificados reales, firewall, puertos, red ni cambios de dependencias. R-06/live sigue NO AUTORIZADA.


## Continuidad vigente — B1-A / B1-B (2026-11-05)

El propietario autorizó la implementación B1-A/B1-B exclusivamente mediante fixtures, sin operaciones live. El resultado fue aceptado formalmente y publicado mediante commit c8cd20c2a576fb1926fdcf11945cd75cf1c4211c en design/user-identity-association-v1. El push fast-forward fue confirmado y la verificación posterior comprobó HEAD local/remoto coincidentes y árbol limpio.

### B1-A — preparación del servicio
- Opción [7] añadida al submenú Administración de Xray-core: Preparar servicio (verifica integridad).
- La acción exige manifiesto válido, presenta el alcance y pide confirmación; adquiere el bloqueo de ciclo de vida, revalida integridad bajo el lock y reutiliza xray_service_prepare.
- No inicia ni habilita el servicio. La preparación usa el bloqueo de ciclo de vida compartido y el guard xray_service_require_inactive impide preparar si el servicio está activo.
- Pruebas: tests/xray_admin_prepare_service.sh, tests/stage1_menu.sh, tests/xray_service.sh.

### B1-B — integridad de instalación
- scripts/xray_install_integrity.py registra/verifica versión, arquitectura, rutas, SHA-256 del binario, geodata y paquete de origen.
- Manifiesto: /var/lib/xray-manager/state/xray-install.json, root:root 0600; directorio root:root 0700; escritura atómica/fsync.
- Instalación heredada sin manifiesto queda como no verificada. update/reinstall no reemplazan estados no verificados; repair es la recuperación explícita. Respaldo/rollback incluye el manifiesto.
- Pruebas: tests/xray_admin.sh y tests/install.sh.

### Evidencia
- Bash: 60/60 scripts PASS.
- Python: python3 -m unittest discover -s tests -p 'test_*.py' — 171/171 PASS.
- py_compile, bash -n global, ShellCheck -S error global, install.sh --check y git diff --check: PASS.
- No se ejecutó la nueva acción contra el sistema real. No se invocó el binario real systemctl; el estado activo se simuló con un stub en fixture. No se modificó unidad, usuario/grupo, runtime, certificados reales, DNS, firewall, puertos, red o dependencias.
- Documentación B1: docs/DECISION_B1_SERVICE_PREPARATION_AND_INSTALL_INTEGRITY.md, docs/IMPLEMENTACION_B1_A_B1_B_2026-11-05.md y docs/AUDITORIA_B1_A_B1_B_2026-11-05.md.

### Git y siguiente acción
- Rama autorizada: design/user-identity-association-v1; HEAD local/remoto base fb5010c7f6bd19aed279eb42d1ae29e4a8050530.
- Cambios B1 publicados y sincronizados mediante commit funcional c8cd20c2a576fb1926fdcf11945cd75cf1c4211c. Push fast-forward confirmado; HEAD local/remoto coinciden.
- No modificar main ni Xray-Normativa/.
- No ejecutar B1 live ni iniciar B2 sin autorización específica. R-06/live sigue NO AUTORIZADA; Etapas 2, 3 y 5 abiertas.


## Continuidad vigente — implementación B2 ACME Certbot (2026-11-05)

1. El propietario aprobó Certbot como cliente ACME inicial: HTTP-01 standalone y DNS-01 manual mediante TXT. Las integraciones API DNS quedan aplazadas.
2. El propietario autorizó implementar B2-A a B2-G exclusivamente con fixtures. Posteriormente aceptó formalmente B2 el 2026-11-05, con las limitaciones de la auditoría; la publicación en la rama autorizada fue verificada.
3. Nuevo backend: scripts/certificate_acme.py. La emisión exige confirmación explícita --confirm-acme, root, Certbot presente y preflight. El comando plan no ejecuta Certbot.
4. HTTP-01 requiere IP pública prevista, A/AAAA compatible y puerto 80 libre localmente; no detiene servicios. La accesibilidad externa solo la valida la CA al completar el desafío. DNS-01 publica TXT manualmente y comprueba el valor exacto con dig; no elimina registros.
5. La importación Certbot verifica que los symlinks live resuelvan dentro de archive, copia a staging root-only y reutiliza certificate_store.py. La prueba fixture integra el certificado con certificate_resolver.prepare y cleanup.
6. Nuevo menú: modules/certificates.sh, cargado por bin/xray-manager y enrutado desde modules/main_menu.sh. Incluye solicitud, listado e importación Certbot; no implementa aún toda la Etapa 4.
7. Documentos B2: docs/DECISION_B2_ACME_CERTBOT.md, docs/IMPLEMENTACION_B2_ACME_CERTIFICADOS_2026-11-05.md y docs/AUDITORIA_B2_ACME_CERTIFICADOS_2026-11-05.md.
8. No se instalaron Certbot/dig, no hubo ACME real, DNS, TCP/80 live, firewall, systemd/runtime, certificados reales, clave maestra ni VPS de pruebas. Xray-Normativa/ y main permanecen intactas.
9. Regresión global registrada: Python 182/182, Bash 61/61, py_compile, bash -n, ShellCheck -S error, install.sh --check y git diff --check PASS. El propietario aceptó formalmente B2 el 2026-11-05 con las limitaciones de la auditoría. Commit funcional `2669c45`; commit documental `21a103a7a15e003ddc3e2031aaf591efefe064ce`; HEAD local/GitHub coincidente y checkout limpio.

La Etapa 4 permanece ABIERTA; R-06/live sigue NO AUTORIZADA.


## Continuidad vigente — B2 aceptada y publicada; siguiente bloque B3 (2026-11-05)

- B2 — ACME Certbot: IMPLEMENTADA, VERIFICADA, AUDITADA, ACEPTADA FORMALMENTE, PUBLICADA y SINCRONIZADA en el alcance fixture-only descrito en `docs/AUDITORIA_B2_ACME_CERTIFICADOS_2026-11-05.md`.
- Aceptación formal del propietario recibida el 2026-11-05. No equivale a aceptación de la Etapa 4 completa ni a autorización live.
- Commit funcional `2669c45` y commit documental `21a103a7a15e003ddc3e2031aaf591efefe064ce`, rama `design/user-identity-association-v1`.
- B2 no instaló Certbot ni ejecutó ACME real; no probó CA, DNS/TXT público, WAN/TCP 80 ni lease con identidad systemd real.
- Siguiente trabajo: B3 del MVP — usuario y conexión VLESS-WS-TLS — sujeto a contraste normativo específico, inventario read-only de funciones reutilizables y presentación de brechas/alcance antes de editar.
- No repetir I-01–I-04 ni B1-A/B1-B. Reutilizar componentes existentes y no rehacer R-01–R-04.
- Etapa 4 permanece ABIERTA; Etapas 2, 3 y 5 también ABIERTAS. R-06/live sigue NO AUTORIZADA. No modificar `main`, `Xray-Normativa/`, infraestructura real, secretos ni VPS de pruebas.

## Addendum de continuidad — 2026-11-05 — R-05 fixture-only

R-05 fue implementada bajo autorización explícita limitada a fixtures, mocks y almacenes temporales. Reutiliza R-01–R-04 y añade adaptador simulado, orquestador, generation_id único y schema 2 compatible con journals schema 1.

**Evidencia:** `docs/DECISION_R05_JOURNAL_GENERATION_2026-11-05.md`, `docs/IMPLEMENTACION_R05_ORQUESTACION_FIXTURE_2026-11-05.md`, `docs/AUDITORIA_R05_ORQUESTACION_FIXTURE_2026-11-05.md`. Pruebas focales R-05 40/40; Python global 227/227; Bash 61/61; compileall, bash -n, ShellCheck, install.sh --check y git diff --check PASS.

**Limitaciones:** solo adaptador simulado; no UI; no integración del registro persistente de perfil activo de Etapa 5 §7; no systemd/Xray real. Etapa 5 y Etapa 6 continúan abiertas. R-06/live NO AUTORIZADA.

**Gobernanza:** implementación auditada, pero no aceptada formalmente ni publicada. Esperar revisión/aceptación del propietario y autorización separada de commit/push. No modificar `main`, `Xray-Normativa/`, infraestructura real, secretos ni VPS de pruebas.


## Addendum vigente — corrección y reauditoría de concurrencia R-05 (2026-11-05)

El propietario autorizó corregir el hallazgo de concurrencia y repetir la auditoría exclusivamente con fixtures. Se incorporó `fcntl.flock` interproceso mediante `adapter.lock` root-only. El bloqueo cubre la transacción completa de `status`, `restart`, `restore` y `audit_events`, incluyendo CAS y escritura de bitácora. Se valida `O_NOFOLLOW`, tipo/propietario/permisos, hardlinks, marcador e identidad de inode.

Se añadieron pruebas multiproceso: dos restart concurrentes con el mismo estado previo (un ganador y un rechazo), cuatro status concurrentes sin pérdida de eventos, dos restore concurrentes (una restauración y un rechazo) y rechazo de lock symlink.

**Resultado actualizado:** 43/43 pruebas focales R-05; 230/230 Python global; 61/61 Bash; `compileall`, `bash -n`, ShellCheck `-S error`, `install.sh --check` y `git diff --check` PASS. Escaneo del adaptador sin invocaciones a servicios/procesos reales. Sin dependencias nuevas.

R-05 queda CORREGIDA, VERIFICADA Y AUDITADA LOCALMENTE; aceptación formal pendiente. No se publicó ni se autorizó publicación. No se ejecutaron operaciones live ni se modificaron systemd/Xray real, runtime persistente, certificados, claves, DNS, firewall, puertos, red, `main`, `Xray-Normativa/` o VPS de pruebas. R-06/live continúa NO AUTORIZADA.

**Siguiente acción:** revisión del propietario y aceptación formal de la auditoría corregida. La publicación requiere autorización separada.

## Addendum vigente — aceptación formal y autorización de publicación R-05 (2026-11-05)

El propietario acepta R-05 en el alcance fixture-only auditado y autoriza commit/push exclusivamente en `design/user-identity-association-v1`. La auditoría registra 43/43 pruebas focales R-05, 230/230 Python globales y 61/61 Bash globales PASS. La aceptación no habilita UI, registro persistente de perfil activo, adaptador systemd real ni operaciones live. R-06/live sigue NO AUTORIZADA; Etapas 2, 5 y 6 permanecen ABIERTAS. No modificar `main` ni `Xray-Normativa/`.

## Continuidad B4 fixture-only — 2026-11-05

El propietario autorizó B4 únicamente en fixtures/mocks. La implementación añade registro activo persistente aislado, ligado a profile_id/revision/validation_id/generation_id/config_sha256/operation_id. Solo se actualiza tras observar servicio fixture \`active\` con generación y hash exactos. Estados pending y rollback conservan el registro anterior.

Se añadió acción \`start\` fixture por CAS para operaciones \`published_pending_start\`, siempre con confirmación explícita. La publicación desde servicio inactive no inicia automáticamente. Journal schema 2 registra \`service_start_requested\`; recovery evita repetir start y puede reconciliar una caída tras transición/verificación.

Leer primero:
- \`docs/IMPLEMENTACION_B4_APLICACION_FIXTURE_2026-11-05.md\`
- \`docs/AUDITORIA_B4_APLICACION_FIXTURE_2026-11-05.md\`

Pruebas: 59/59 focales R05+B4; 246/246 Python global; 61/61 suites Bash. \`compileall\`, \`bash -n\`, ShellCheck, \`install.sh --check\` y \`git diff --check\` PASS.

No continuar a systemd real sin autorización separada. Falta integración de menú y adaptador real. No modificar \`Xray-Normativa/\` ni \`main\`; no publicar sin autorización explícita. HEAD base \`2902b2ef602dfe97acf62428d6b7c35ce7c81d5d\`.

## Continuidad H6-A — observación systemd read-only (2026-11-05)

Leer:
- `docs/DISENO_ADAPTADOR_SYSTEMD_REAL_INTEGRACION_RUNTIME_2026-11-05.md`
- `docs/IMPLEMENTACION_H6A_ADAPTADOR_SYSTEMD_OBSERVACION_2026-11-05.md`
- `docs/AUDITORIA_H6A_ADAPTADOR_SYSTEMD_OBSERVACION_2026-11-05.md`

Se añadió `scripts/xray_runtime_systemd_adapter.py` con consulta read-only de propiedades allowlist para `xray.service`, comprobación de unidad y hash del archivo runtime. No afirma generación/hash cargados: ambos permanecen nulos sin atestación de InvocationID. Las 11 pruebas focales usan mocks.

Regresión: 11/11 focales H6-A, 59/59 R-05+B4 y 257/257 Python globales PASS; smoke Bash, ShellCheck, AST y diff-check PASS. No se invocó systemctl real ni se modificó runtime. El adaptador no está conectado a R-05 ni a los menús; no hay acciones mutadoras. Siguiente: atestación generation/hash/InvocationID e inyección de backend manteniendo fixture como default. H6/live requiere autorización nueva y específica. No publicar sin autorización; no modificar `main` ni `Xray-Normativa/`.


## H6-B — atestación persistente de generación systemd (2026-11-06)

Se implementó H6-B en alcance aislado: `scripts/xray_runtime_attestation.py` y `tests/test_xray_runtime_attestation.py`. La atestación enlaza operation_id, generation_id, SHA-256 publicado, InvocationID nuevo/estable, ActiveEnterTimestamp, SHA-256 de la unidad y fecha UTC. El almacén reservado es `/var/lib/xray-manager/attestations`, pero no se creó ni se utilizó en el sistema real.

Contraste normativo: Etapa 5 §§4, 5 y 7 exige distinguir configuración guardada/aplicada, verificar la configuración realmente ejecutada y actualizar el registro activo solo después de verificar. Etapa 6 §2 exige observación del estado/proceso y verificación de funcionamiento. H6-B aporta evidencia técnica para ese objetivo, pero aún no completa la activación funcional ni la verificación end-to-end.

Auditoría: 12/12 pruebas focales H6-B; 269/269 Python global; pruebas Bash de servicio, control de servicio y preparación PASS; compileall, bash -n global, ShellCheck -S error, install.sh --check y git diff --check PASS. El módulo no invoca systemctl, subprocess, shell ni eval.

Limitaciones: observaciones sintéticas; sin systemctl/Xray real; no conectado a H6-A, R-05, B4, menú ni CLI. La futura integración debe mantener el lock de ciclo de vida durante transición, observaciones y persistencia, y usar snapshots directos de H6-A. H6-B queda IMPLEMENTADA, VERIFICADA Y AUDITADA, PASS CON LIMITACIONES. No se hizo commit ni push. HEAD continúa `be524eef65037f74bb36ee9e7fd9b385c3ffb613`; rama `design/user-identity-association-v1`. `main` y `Xray-Normativa/` permanecen intactas. No hubo operaciones live ni cambios de runtime, systemd, certificados, DNS, firewall, puertos, red o dependencias.

Siguiente paso propuesto: H6-C, integración del almacén/atestación con R-05 mediante backend inyectable, manteniendo fixture como default y sin habilitar ejecución real desde CLI. Requiere revisión y autorización del alcance de integración; no habilita operaciones live.


## H6-C — integración R-05/H6-B (2026-11-06)

El propietario autorizó H6-C exclusivamente con mocks y fixtures. Se modificó scripts/xray_runtime_orchestrator.py para inyección de backend por contexto, manteniendo el adaptador fixture R-05 como default. Los backends alternativos sólo se aceptan como dobles de prueba explícitos; no hay selector real en CLI. Se conectó la persistencia H6-B a las rutas fixture de start/restart, con snapshots sintéticos before/after/confirmed dentro del lock de ciclo de vida. Divergencias provocan rollback fixture. Recovery valida la atestación persistida y falla cerrado si falta.

Evidencia: docs/IMPLEMENTACION_H6C_INTEGRACION_R05_ATESTACION_2026-11-06.md y docs/AUDITORIA_H6C_INTEGRACION_R05_ATESTACION_2026-11-06.md. H6-C 7/7 focales, H6-B 12/12 focales y Python global 276/276 PASS. compileall, bash -n, ShellCheck -S error, install.sh --check, tres pruebas Bash de servicio y git diff --check PASS.

Limitaciones: las observaciones son sintéticas; H6-A no se invocó; no existe backend mutador systemd ni selección live en CLI. La marca de doble de prueba es una salvaguarda de diseño, no una frontera contra código Python arbitrario. Sin systemctl/Xray real, WAN, certificados/DNS/firewall/red o dependencias. No commit/push. main y Xray-Normativa/ intactas. H6-C queda IMPLEMENTADA, VERIFICADA Y AUDITADA, PASS CON LIMITACIONES. Siguiente bloque requiere diseñar el adaptador de servicio real por separado y solicitar autorización live específica.
## Continuidad H6-D (2026-11-06)

H6-D conectó la opción «Cambiar perfil activo» de Etapa 5 y Gestión de perfiles con `scripts/xray_runtime_menu_bridge.py`, limitado a fixtures R-05 marcados y rutas confinadas. Revisión exacta validada y confirmación obligatorias. En modo normal la operación está bloqueada. No existe conexión con H6-A ni backend systemd real; no se modificó Xray real. Ver `docs/IMPLEMENTACION_H6D_MENU_PERFILES_R05_FIXTURE_2026-11-06.md` y `docs/AUDITORIA_H6D_MENU_PERFILES_R05_FIXTURE_2026-11-06.md`.

## Continuidad H6-E1 — contrato systemd read-only (2026-11-06)

H6-E1 amplió scripts/xray_runtime_systemd_adapter.py: consulta y valida NeedDaemonReload, DropInPaths, Type, ExecStartPre y ExecStart; rechaza definiciones pendientes, drop-ins y argv divergentes. Corrige la comprobación de grupo del archivo runtime a root:xray/0640 y detecta sustitución de inode entre lstat y open.

Evidencia: docs/IMPLEMENTACION_H6E1_CONTRATO_OBSERVACION_SYSTEMD_2026-11-06.md y docs/AUDITORIA_H6E1_CONTRATO_OBSERVACION_SYSTEMD_2026-11-06.md. 20/20 focales, 289/289 Python globales, compileall, bash -n, ShellCheck, pruebas Bash de servicio, install.sh --check y diff-check PASS.

Limitaciones: todas las consultas systemd fueron mockeadas; no se inspeccionó /proc, no hay backend mutador ni integración live. La compatibilidad exacta del formato ExecStart se deberá contrastar en entorno objetivo sólo cuando exista autorización para una prueba de lectura real. Siguiente: H6-E2 — inspección aislada de identidad de proceso. No commit/push; no modificar main ni Xray-Normativa/.

## Continuidad H6-E2 — identidad del proceso (2026-11-06)

Leer:
- docs/IMPLEMENTACION_H6E2_IDENTIDAD_PROCESO_2026-11-06.md
- docs/AUDITORIA_H6E2_IDENTIDAD_PROCESO_2026-11-06.md

Nuevo inspector read-only scripts/xray_runtime_process_identity.py: PID/starttime antes y después, UID/GID efectivos, ruta /proc/PID/exe, argv exacto y SHA-256 del ejecutable. Sólo acepta raíces procfs alternativas con marcador fixture. No acredita configuración cargada. Pruebas focales 22/22; Python global 332/332; análisis estático, Bash y install.sh --check PASS.

Siguiente: H6-E3, diseñar la integración de H6-A y la inspección de proceso con R-05/atestación, usando mocks/fixtures y correlacionando MainPID, InvocationID y starttime bajo el lock de ciclo de vida. No crear backend mutador ni selector live. H6-E4 será auditoría. H6-F/live requiere evaluación y autorización separada. No commit/push sin autorización; no modificar main ni Xray-Normativa/.

## Continuidad H6-E3 — correlación y persistencia de identidad (2026-11-06)

Leer:
- docs/IMPLEMENTACION_H6E3_CORRELACION_PROCESO_ATESTACION_2026-11-06.md
- docs/AUDITORIA_H6E3_CORRELACION_PROCESO_ATESTACION_2026-11-06.md

H6-E3 conecta snapshots H6-A con inspección H6-E2 del MainPID y exige estabilidad de PID, InvocationID, ActiveEnterTimestamp y FragmentPath. R-05 requiere evidencia process_identity en after/confirmed; ausencias/divergencias provocan rollback/fail-closed. H6-B schema v2 persiste PID/starttime, ejecutable/hash, UID/GID y argv. Correlación 16/16, H6-B 15/15, H6-C 9/9 y Python global 332/332 PASS; análisis estático/Bash/instalador PASS.

Sólo mocks/dobles/fixtures: no se ejecutó systemctl, no se inspeccionó /proc real ni proceso Xray real; backend mutador y selector live siguen deshabilitados. Siguiente: H6-E4, auditoría integral de H6-A..E3, revisión de compatibilidad, recuperación, locks y límites. H6-F/live requiere evaluación y autorización específica. No commit/push; no modificar main ni Xray-Normativa/.

## Continuidad — auditoría integral H6-E (2026-11-06)

Leer docs/AUDITORIA_H6E_INTEGRAL_2026-11-06.md. Dictamen PASS CON LIMITACIONES. H6-E2 22/22, correlación 16/16, H6-B schema v2 15/15, H6-C 9/9, Python global 332/332; análisis Python/Bash, ShellCheck e instalador PASS.

H6-E no habilita live: no se probó systemd real, proceso Xray real, procfs de producción, backend mutador, WAN, certificados, DNS, firewall ni cliente externo. H6-F debe evaluar preparación y delimitar autorización específica para una VPS limpia de pruebas. No publicar ni modificar main/Xray-Normativa/ sin autorización.

## Continuidad H6-F — evaluación de preparación live (2026-11-06)

Leer docs/EVALUACION_H6F_PREPARACION_PRUEBA_REAL_2026-11-06.md. La evaluación encontró que install.sh instala Xray y prepara la unidad automáticamente; Certbot no se instala con el Manager; la selección formal de cliente ACME sigue pendiente en la normativa; el exportador VLESS-WS-TLS tiene hellen.tvrc.me como endpoint predeterminado; R-05 y menú de perfiles continúan fixture-only.

No listo para aceptación end-to-end. Antes de live: decidir instalador Manager-only frente a instalación integral, aprobar Certbot, designar VPS limpia, autorizar instalación/preparación/publicación/start, autorizar puertos 80/443 y confirmar endpoint internet.tvrc.me:443 con Host/SNI separados. Sin operaciones live, DNS/firewall, Certbot ni WAN.

## Continuidad — instalador Manager-only (2026-11-06)

Leer docs/IMPLEMENTACION_INSTALADOR_MANAGER_ONLY_2026-11-06.md y docs/AUDITORIA_INSTALADOR_MANAGER_ONLY_2026-11-06.md. install.sh --install despliega sólo Manager; Xray-core se instala después desde Administración de Xray-core. La instalación integral anterior queda como --install --with-xray. Pruebas en prefijos temporales: Manager-only, fixtures preservados, no unidad ni /etc/xray, estado false/false, rechazo de rutas simbólicas en modo integral; regresión Python 332/332 y Bash 62/62 PASS.

H6-F queda parcialmente desbloqueada por el cambio del instalador, pero aún no lista para prueba end-to-end: falta backend runtime live, aprobación ACME/Certbot y endpoint público explícito. No se instaló nada en el host ni se ejecutó systemctl/Xray real. Sin commit/push.

## Sincronización y estado documental — 2026-11-06

Se reconciliaron los estados de H6-E2/E3/E4 y H6-F. Los párrafos cronológicos previos que indicaban E3/E4 pendientes o que el instalador aún requería separación describen cortes históricos, no el estado actual. El corte vigente es el bloque superior. No asumir que el push está confirmado hasta verificar que el SHA local y el remoto coinciden.


## H6-G2 — puente seguro hacia el controlador de servicio (2026-11-06)

Contrato G1 aprobado y documentado en `docs/DECISION_H6G1_CONTRATO_BACKEND_RUNTIME_LIVE_2026-11-06.md`. El propietario aprobó el contrato H6-G1 y autorizó la implementación G2 en desarrollo, exclusivamente con mocks/fixtures. Se agregó `scripts/xray_runtime_service_control.py` y el punto de entrada `xray_service_action_inherited_lock()` en `modules/xray_service.sh`. Python hereda explícitamente el descriptor lifecycle lock hacia Bash; ambos lados verifican ruta/inode y condiciones de seguridad. Las acciones permitidas en este puente son start/restart/stop y se delegan al controlador único `xray_service.sh`; Python no ejecuta systemctl directamente.

Pruebas: puente Python 9/9; observación systemd y atestación de proceso/identidad 58/58; Python global 341/341; las 62 suites Bash ejecutadas finalizaron correctamente; `bash -n`, `py_compile` y `git diff --check` PASS. La integración Python→Bash utilizó systemctl mock. Las pruebas VLESS/VMess con Xray 26.10.31 validan configuraciones en entorno temporal, no una instancia real expuesta a WAN.

**Límites:** G2 está IMPLEMENTADA PARCIALMENTE; falta auditoría formal independiente. El puente no está conectado a R-05, no se habilitó backend live en `_with_service_backend` ni en el menú. No se modificó journal/orquestador, runtime persistente, unidad systemd real, `/etc/xray`, certificados, DNS, firewall, puertos ni red. No se ejecutaron acciones reales start/restart/stop, ACME ni conexión externa. El hash del archivo runtime sigue sin equivaler a evidencia de configuración cargada en memoria.

Archivos de esta entrega: `modules/xray_service.sh`, `scripts/xray_runtime_service_control.py`, `tests/test_xray_runtime_service_control.py`, `tests/xray_service_control.sh` y `docs/IMPLEMENTACION_H6G2_PUENTE_CONTROL_SERVICIO_2026-11-06.md`.

Estado Git: rama `design/user-identity-association-v1`, HEAD base `9bab1dbed7d4873aa30a3fd00a976a1d666d9355`; árbol con cambios locales sin commit. Sin push. `main` y `Xray-Normativa/` intactas. Las VPS de prueba no fueron utilizadas.

**Siguiente:** auditoría formal del puente G2 y luego G3: diseñar la semántica live de observación, transición, correlación de InvocationID y rollback sin inferir configuración cargada. No habilitar live hasta superar G3/G4/G5 y recibir autorización específica para el host real.


## Continuidad — H6-G2-B (2026-11-06)

Último avance local en `/opt/xray-manager`: backend live aislado `scripts/xray_runtime_live_backend.py` y 14 pruebas nuevas. Observa systemd y correlaciona proceso; distingue `runtime_config_sha256`, `process_identity` y `loaded_config_sha256=null`. Start solo inactive; restart solo active con proceso verificado; stop solo recuperación justificada; todos requieren confirmación y hash esperado, doble observación previa y resultado no verificado hasta observar postcondición. `restore()` falla cerrado. Pruebas completas: Python 355/355, Bash 62/62, estáticas PASS. No está conectado a R-05/menú; fixture sigue default. G2 permanece parcial, requiere revisión/auditoría. No hubo operaciones live ni commit/push. Documento: `docs/IMPLEMENTACION_H6G2B_BACKEND_RUNTIME_LIVE_2026-11-06.md`.


## Continuidad — auditoría independiente H6-G2 (2026-11-06)

Auditoría concluida sobre VPS desarrollo. Dictamen PASS CON LIMITACIONES; H6-G2 sigue PARCIAL y backend live no habilitado. Hallazgos: F-01 validar invariantes PID/InvocationID para inactive; F-02 start requiere evidencia de generación publicada y validada, no solo hash runtime; F-03 el puente puede adquirir flock libre y no demuestra handoff previo de R-05; F-04 timeout debe reconciliarse mediante journal sin reintento ciego; F-05 restore/rollback live falta y debe resolverse en G3. Suites: Python 355/355, Bash 62/62, ShellCheck Bash y checks estáticos PASS. Informe `docs/AUDITORIA_H6G2_BACKEND_RUNTIME_LIVE_2026-11-06.md`. Siguiente paso: resolver F-01–F-03 y diseñar G3 transaccional; no usar VPS pruebas ni operaciones live sin autorización separada.


## H6-G2 — resolución F-01 (2026-11-06)

Se corrigió la validación de snapshots systemd en `scripts/xray_runtime_live_backend.py`. Un estado `inactive` ahora rechaza PID distinto de `null/0` e InvocationID residual. Un estado `active` requiere PID entero mayor que 1, InvocationID hexadecimal de 32 caracteres, subestado `running` y resultado `success`. Se agregaron pruebas adversariales. Resultado: 17/17 focales, Python global 358/358, Bash 62/62, py_compile, bash -n focal, ShellCheck y diff-check PASS.

F-01 queda corregido y verificado únicamente con fixtures. H6-G2 no se cierra ni se habilita live. F-02/F-03 siguen siendo bloqueadores para integración; F-04/F-05 se resolverán en G3. No hubo acciones sobre systemd/Xray real, runtime, certificados, DNS, firewall, puertos ni red. Sin commit/push; `main` y `Xray-Normativa/` intactas. Informe: `docs/IMPLEMENTACION_H6G2_F01_VALIDACION_ESTADOS_2026-11-06.md`.


## H6-G2 — F-02: contrato y lector de evidencia (2026-11-06)

Se implementó `scripts/xray_runtime_operation_evidence.py` para verificar operation_id/generation_id, journal schema 2, publicación confirmada, rollback no iniciado, staging/lease, informe persistido exacto, checks requeridos, hash de binario y hash de bytes runtime. El historial de validación se consulta read-only. El backend live dejó de aceptar un SHA-256 libre y exige evidencia correlacionada con operación y generación; solo acepta `environment=live`.

Límite deliberado: el journal actual está restringido a fixtures, por lo que el lector devuelve `environment=fixture` y el backend lo rechaza para mutaciones live. No se debilitó el aislamiento ni se conectó R-05/menú. F-02 queda implementado para el contrato y verificado en fixtures, pero evidencia live sigue pendiente de G3. Pruebas: backend 20/20, lector 9/9, Python 370/370, Bash 62/62; verificaciones estáticas PASS. Sin acciones live ni commit/push. Documentos: `docs/DECISION_H6G2_F02_EVIDENCIA_OPERACION_GENERACION_2026-11-06.md`, `docs/IMPLEMENTACION_H6G2_F02_EVIDENCIA_OPERACION_2026-11-06.md`.


## Continuidad — H6-G2 F-03 (2026-11-06)

F-03 implementado en el puente aislado. Python y Bash prueban que el descriptor exacto contiene un FLOCK exclusivo en `/proc/.../fdinfo`, cuyo PID propietario coincide con R-05; ya no se usa `flock` para validar ni se adquiere accidentalmente un lock libre. Pruebas focales Python 12/12 y Bash PASS. Informe: `docs/IMPLEMENTACION_H6G2_F03_PROPIEDAD_LIFECYCLE_LOCK_2026-11-06.md`; decisión: `docs/DECISION_H6G2_F03_PROPIEDAD_LIFECYCLE_LOCK_2026-11-06.md`.

Pendiente auditoría independiente. No integrado a R-05/menú; fixture sigue default. G3 debe mantener lifecycle lock coherente durante publicación, transición, observación, journal y recuperación, evitando reacquisiciones. Sin systemctl/Xray real, cambios live, commit/push.

## Continuidad — H6-G3-A/B (2026-11-06)

Leer `docs/DECISION_H6G3_COORDINACION_TRANSACCIONAL_2026-11-06.md` y `docs/IMPLEMENTACION_H6G3_A_B_COORDINACION_LOCKS_2026-11-06.md`. Se implementó un contexto de locks con propietario único y reutilización anidada. Apply conserva lifecycle/application desde la revalidación post-staging hasta publicación, transición, observación y rollback; start pendiente y recovery también mantienen el mismo lock.

Validación: Python 377/377, Bash 62/62, py_compile/compileall, bash -n, ShellCheck -S error y diff-check PASS. Pruebas específicas demuestran que otro descriptor no adquiere lifecycle lock durante restart, start y rollback, incluso en llamadas anidadas.

No hay live: fixture default, backend mutador no conectado, no systemctl/Xray real ni cambios de runtime. G3-C timeout/ambigüedad, G3-D rollback adversarial y G3-E auditoría independiente siguen pendientes. No commit/push; no modificar main ni Xray-Normativa/.


## H6-G3-C — reconciliación de timeout/ambigüedad (2026-11-06)

Implementado en R-05 fixture. Los resultados timeout/response_lost se conservan en el journal y la transición se decide por observación exacta de estado, generación y hash. Timeout antes de la acción con estado previo intacto permite rollback de configuración sin mutar servicio; timeout o respuesta perdida después de transición exacta se reconcilia como completado sin repetir acción. Si la observación es failed/unknown, no correlacionada o no disponible, se restaura la configuración cuando es seguro y se registra `RECOVERY_REQUIRED`, sin otra mutación de servicio. Ese estado queda como `NO_OP` en recuperaciones automáticas.

Se añadió failpoint de prueba tras persistir start request y pruebas para start timeout_before/timeout_after/response_lost_after, crash antes de start, estados failed/unknown y reobservación fallida. Suite focal R-05: 67/67 PASS. Evidencia: `docs/IMPLEMENTACION_H6G3_C_TIMEOUT_RECONCILIACION_2026-11-06.md`.

**Límites:** sólo fixtures/mocks. El backend live continúa aislado, sin reconciliación durable propia, sin conexión a R-05/CLI/menú. No se modifica journal para aceptar live ni se realiza rollback live. G3-C implementado focalmente; auditoría pendiente. G3-D y G3-E pendientes; H6-G2 permanece abierto. Sin systemctl/Xray real, dependencias, cambios persistentes, commit ni push.


## H6-G3-D — rollback fixture adversarial e idempotencia (2026-11-06)

La auditoría adversarial encontró un defecto: si el snapshot se corrompía después de publicar, `_load_operation()` lanzaba antes de que rollback/recovery pudiera persistir `RECOVERY_REQUIRED`. Se ajustó el camino controlado del publicador para leer el journal estructuralmente, validar snapshot y registrar `recovery_required` ante corrupción, sin usar el snapshot ni sobrescribir el runtime.

Pruebas adversariales añadidas: drift externo antes de rollback; snapshot corrupto durante rollback y recovery; drift externo después de crash tras rename; recovery repetido byte-a-byte idempotente; generación de servicio ajena después de restaurar configuración; crash después de restaurar servicio sin repetir restore; fallo de restore seguido de recovery `NO_OP`. Se conservan pruebas de symlink/hardlink, TOCTOU, ausencia de snapshot previo y crashes de rename.

Resultados: publicador + orquestador 86/86 PASS; Python global 388/388 PASS. Documento: `docs/IMPLEMENTACION_H6G3_D_ROLLBACK_FIXTURE_2026-11-06.md`.

**Estado:** G3-A/B/C/D implementados y verificados con fixtures. G3-E auditoría independiente integral pendiente. H6-G2 permanece abierto; backend live no conectado y no habilitado. Sin systemctl/Xray real, dependencias, operaciones persistentes, commit ni push. `main` y `Xray-Normativa/` intactas.


## H6-G3-E — auditoría integral de segunda pasada (2026-11-06)

Se completó una segunda pasada sobre G3-A/B/C/D, contrastando el contrato transaccional, publicador R-04, orquestador R-05, journal, rollback, recuperación y aislamiento live. **Dictamen: PASS CON LIMITACIONES en alcance fixture.** No se identificó un defecto bloqueante nuevo dentro de ese alcance.

Validación global: Python **388/388**, Bash **62/62**, `bash -n` global, ShellCheck `-S error`, `install.sh --check` y `git diff --check` PASS. Los 14 archivos normativos maestros coinciden byte a byte con `Xray-Normativa/`; el único archivo adicional es el README auxiliar. `main` y `Xray-Normativa/` permanecen sin modificaciones.

Esta revisión fue realizada por la misma sesión que participó en la implementación: es una **auditoría de segunda pasada, no independiente**. No habilita live. El backend live sigue desconectado y bloqueado; H6-G2 permanece abierto y el MVP NO está listo para despliegue end-to-end. Las suites de protocolos invocaron Xray 26.10.31 únicamente con `run -test` sobre configuraciones temporales; no se inició un servidor ni se modificó runtime persistente.

Informe: `docs/AUDITORIA_H6G3_E_SEGUNDA_PASADA_2026-11-06.md`. Sin systemctl real, cambios de runtime, certificados, DNS, firewall, puertos, red, dependencias, VPS de pruebas, commit o push.

## Próximo paso obligatorio — revisión independiente H6-G3

Antes de integración live, entregar `docs/PAQUETE_REVISION_INDEPENDIENTE_H6G3_2026-11-06.md` a otra IA o revisor humano que no haya participado. Debe inspeccionar el árbol de trabajo real en `/opt/xray-manager`, no sólo HEAD, y emitir hallazgos reproducibles sin modificar archivos ni ejecutar operaciones live. No declarar revisión independiente hasta recibir y evaluar ese informe.

## Continuidad inmediata — corrección SIGPIPE instalador Xray (2026-11-07)

El último fallo real de instalación en VPS Pruebas ya está localizado. El ZIP y su SHA-256 son correctos; el binario temporal funciona. El aborto ocurría en `xray_admin_extract_stage()` por `xray version | head -n 1` bajo `set -o pipefail`. Se corrigió en desarrollo capturando la salida completa antes de extraer la primera línea. La prueba focal usa un binario fixture que emite 20.000 líneas para reproducir el cierre anticipado de tubería.

Antes de continuar, revisar `docs/IMPLEMENTACION_CORRECCION_SIGPIPE_EXTRACCION_XRAY_2026-11-07.md` y el bloque vigente de `PROJECT_STATE.md`. Pruebas globales completadas: Bash 62/62 y Python 406/406 PASS; bash -n, compileall, ShellCheck global, install.sh --check y diff-check PASS. Publicado en `design/user-identity-association-v1`, commit `38cc0ddfac9ab3093a1c5442d14fa04c9e416e42`. Siguiente: actualizar VPS Pruebas usando respaldo y verificación de commit. Después repetir la instalación Xray 26.10.31 con captura de salida y código de retorno. No iniciar/preparar systemd, no tocar runtime, DNS, firewall, puertos ni certificados. La VPS Pruebas sigue sin Xray instalado; no borrar el respaldo `/opt/xray-manager.pre-update.20261107T114049Z`.

## Continuidad vigente — instalación guiada de Certbot (2026-11-07)

- El usuario pidió que al iniciar «Obtener certificado nuevo» el Administrador verifique Certbot y, si falta, pregunte si desea instalarlo.
- Implementación local: `certificates_ensure_certbot()` en `modules/certificates.sh`; comprueba `certbot --version`, pide consentimiento si falta, limita la instalación a Ubuntu/root, utiliza lock compartido, `apt-get update` e instala solo `certbot`; verifica después y bloquea ACME si falla.
- Pruebas globales: Bash 62/62 y Python 406/406 PASS; sintaxis Bash, compileall, ShellCheck focal y diff-check PASS.
- No se ejecutó APT/Certbot real ni solicitud ACME, no hubo cambios DNS/firewall/puertos/servicios/runtime y no se actualizó VPS Pruebas.
- Ver `docs/IMPLEMENTACION_INSTALACION_CERTBOT_DESDE_MENU_2026-11-07.md`. Implementación local pendiente de auditoría y autorización de commit/push.

## Punto exacto de reanudación — primer lanzamiento en VPS Pruebas (2026-11-07)

**Este bloque reemplaza las indicaciones anteriores que decían que Xray seguía sin instalarse.** El usuario corrigió el dominio: el FQDN válido es `pruebas.tvrc.me` (no `prueba.tvrc.me`). Objetivo: primer servidor VLESS + WebSocket + TLS, TCP/443, todo configurado desde Xray-Core Manager.

VPS Pruebas Termalin host ID `08827b29-b7f9-4625-8ff3-351918a03c96`, Ubuntu 24.04.4 LTS x86_64, ruta `/opt/xray-manager` sin `.git`. En la última inspección read-only se encontró `/usr/local/bin/xray` versión 26.10.31, `geoip.dat`, `geosite.dat` y `/var/lib/xray-manager/state/xray-install.json`. La verificación de integridad con `scripts/xray_install_integrity.py verify` terminó PASS: binario y geodata coinciden con el manifiesto. **No reinstalar Xray ni repetir el diagnóstico SIGPIPE** salvo nueva evidencia de corrupción/ausencia. Hay una inconsistencia a reconciliar: `/var/lib/xray-manager/state/install.json` aún indica `xray_installed=false`, aunque los artefactos/manifiesto existen y verifican correctamente.

Todavía NO existe `/etc/xray`, `xray.service` no existe/no está activo, no hay listener 80/443 ni conexión en `connections.json` (lista vacía). UFW está inactivo. `dig A pruebas.tvrc.me` y `dig AAAA pruebas.tvrc.me` no devolvieron registros en el corte. IP observada en `eth0`: `172.235.129.166/24`; confirmar que sea la IPv4 pública asignada antes de configurar el registro A. Certificado ACME aún no emitido. No se ejecutaron APT, Certbot real, ACME, DNS, firewall, puertos ni systemd.

**Siguiente paso:** (1) confirmar IP pública y configurar/verificar `A pruebas.tvrc.me`; (2) reconciliar el booleano `xray_installed=false` sin tocar artefactos íntegros; (3) resolver antes de APT el efecto de `certbot.timer` y la política de renovación; (4) obtener certificado desde el menú; (5) crear VLESS+WS+TLS desde el menú; (6) preparar/iniciar servicio desde el Administrador con autorización específica; (7) probar cliente externo. Detalle completo, comandos de verificación, evidencias y restricciones en `docs/PRIMER_LANZAMIENTO_VPS_PRUEBAS_2026-11-07.md`.

La corrección SIGPIPE ya está publicada en `design/user-identity-association-v1` (`38cc0dd...` código, `2c068a4...` docs) y el código corregido se observó en la VPS; no se acreditó un SHA Git instalado porque el directorio de Pruebas es bootstrap sin `.git`. La implementación guiada Certbot sigue local y no publicada: sus fixtures pasaron, pero debe auditarse el comportamiento del timer antes de desplegarla. No confundir pruebas fixture con instalación/servicio real.


## Continuidad — diseño de renovación Certbot/Xray (2026-11-07)

Leer `docs/DISENO_RENOVACION_CERTBOT_XRAY_2026-11-07.md`. La inspección encontró que el almacén y resolutor TLS admiten únicamente revisión 1. El importador ACME crea un certificado nuevo y no rota el `certificate_id` existente. Por ello, un deploy hook no puede actualizar de forma segura los certificados asociados a conexiones.

El backend live continúa desconectado de R-05; no existe rollback transaccional certificado/configuración/proceso. No implementar un hook que ejecute `systemctl` directamente ni habilitar `certbot.timer` todavía. Política objetivo: renovar automáticamente; validar y versionar el certificado; aplicar/recargar solo si Xray estaba activo; nunca iniciar Xray desde el hook. Mutaciones exclusivamente a través de `modules/xray_service.sh` bajo R-05.

Siguiente paso: diseñar e implementar schema v2 del almacén, migración explícita v1→v2, revisiones inmutables y rotación/rollback con fixtures; adaptar `certificate_resolver.py`; luego hook idempotente y finalmente integración H6 live auditada. Sin operaciones live, APT/Certbot/ACME, systemd/runtime, VPS Pruebas, DNS/firewall/puertos/red, commit o push.

## Continuidad inmediata — schema v2 del almacén TLS (2026-11-07)

Revisar `docs/IMPLEMENTACION_SCHEMA_V2_CERTIFICADOS_2026-11-07.md`. En desarrollo se implementó la primera parte del schema v2: lectura compatible v1/v2, historial `revisions[]`, `active_revision`, importación y rotación managed versionada, migración explícita v1→v2 con copia verificada y originales preservados, rollback con verificación criptográfica/vigencia, auditoría de todas las revisiones y resolución TLS por revisión activa. El CLI ACME admite `--certificate-id` explícito; no hay asociación automática de lineage. El snapshot writer exporta certificados managed versionados sin claves privadas ni referencias secretas.

Validación focal: store, resolver, snapshot writer PASS; ACME 11/11. Global Python 406/406 y Bash 62/62 PASS. Cambios solo en VPS desarrollo. El trabajo no está cerrado ni listo para despliegue.

Pendiente obligatorio: adaptar/testear restauración snapshot v2 end-to-end; integrar migración/rotación/rollback al menú con confirmaciones; auditar consumidores completos y pruebas de fallo/corrupción; auditoría adversarial independiente. No habilitar `certbot.timer` ni deploy hook hasta completar ese trabajo y la integración transaccional de R-05. No usar VPS Pruebas, no leer master.key real, no APT/ACME/systemd/runtime, no commit/push.

## Continuidad — schema v2 TLS, segunda pasada (2026-11-07)

El menú ya permite auditar el almacén, migrar v1→v2, rotar un ID existente desde la importación Certbot y hacer rollback a una revisión concreta. Cada operación sensible exige auditoría limpia y confirmación; la rotación es managed/versionada y no aplica Xray automáticamente. El historial completo ahora exige huellas únicas. Ver `docs/IMPLEMENTACION_SCHEMA_V2_CERTIFICADOS_2026-11-07.md`.

La revisión de consumidores confirmó compatibilidad por `load_catalog()` y la proyección de la revisión activa. `shared_snapshot_writer.py` crea snapshot TLS v2, pero el repositorio no tiene un restaurador general para esos paquetes. `vless_backup.py` solo restaura su propio formato VLESS/VMess y valida referencias a certificados centrales existentes; no restaura el catálogo TLS. Mantener esta limitación explícita y diseñar/aprobar contrato general de restore antes de implementarlo.

Pruebas focales del menú/store pasan. Ejecutar batería global completa y revisión final. No APT/Certbot/ACME, no leer clave maestra real, no systemd/runtime ni VPS Pruebas. Sin commit/push.

Validación global de la segunda pasada: 62 suites Bash y 406 tests Python PASS; `bash -n`, `compileall`, ShellCheck `-S error`, `install.sh --check` y `git diff --check` PASS. No se ejecutó runtime live. El restaurador general de shared snapshots sigue pendiente de contrato aprobado.

La rotación ACME ya comprueba existencia del `certificate_id`, schema v2, tipo managed y conservación de todos los SAN históricos; la prueba de pérdida de SAN falla cerrada sin cambiar el catálogo. ACME focal 12/12 PASS. La suite global se repite tras este ajuste.

Validación tras el control SAN: 62 suites Bash y 407 tests Python PASS; `bash -n` y `compileall` globales, ShellCheck focal de archivos Bash modificados, `install.sh --check` y diff-check PASS. ShellCheck global completo pasó en la pasada anterior.

Se creó `docs/DISENO_RESTAURACION_SHARED_SNAPSHOT_2026-11-07.md`: el repo no tiene lector/restaurador de paquetes shared snapshots. El formato excluye claves privadas y `secret_ref`; una restauración no puede inventar material TLS. La propuesta es restore autenticado, preflight, merge no destructivo, TLS solo con blob cifrado local existente y verificado, journal durable y data-only sin runtime. No implementar hasta aprobar decisiones pendientes del diseño.

## Reanudación exacta — auditoría global TLS v2 (2026-11-07)

La batería final de la rama de desarrollo terminó: **62/62 Bash y 23/23 Python PASS**, además de `bash -n`, `compileall`, ShellCheck global `-S error`, `install.sh --check` y `git diff --check`. Para ejecutar pruebas Python individuales usar `PYTHONPATH=. python3 tests/test_*.py`; sin `PYTHONPATH` una prueba que importa `scripts` no encuentra el paquete.

Cambios de schema v2, resolver, ACME, snapshot writer, menú, tests y documentación quedan listos para sincronización en `design/user-identity-association-v1`. No declarar listo para producción: restore general shared snapshot pendiente; su diseño requiere aprobación; Certbot timer/hook y recarga Xray siguen sin habilitar; H6 live no está conectado a R-05. No se hicieron operaciones live ni cambios en VPS Pruebas. `main` y `Xray-Normativa/` permanecen protegidos.

## Regla prioritaria de continuidad — primer servidor funcional desde el Administrador (2026-11-07)

**Prioridad máxima del proyecto:** conseguir el primer despliegue end-to-end de un servidor Xray funcional usando el Administrador, con el flujo más básico que cumpla la normativa y sin configuración manual externa. El objetivo inicial se mantiene en **VLESS + WebSocket + TLS**, para pruebas.tvrc.me, TCP/443.

La secuencia de trabajo debe priorizar únicamente los bloqueos necesarios para demostrar ese resultado:
1. reconciliar de forma segura el estado del Manager con la instalación Xray ya verificada en VPS Pruebas;
2. completar desde el Administrador la gestión del certificado TLS;
3. crear y validar desde el Administrador la configuración VLESS-WS-TLS mínima;
4. preparar y activar el servicio mediante el controlador único del Administrador;
5. verificar el estado real del servicio y realizar una conexión desde un cliente externo.

Posponer funciones avanzadas, automatizaciones, ampliaciones de protocolos, restauradores y mejoras no imprescindibles hasta que el primer servidor esté operativo y probado. No recortar verificaciones de integridad, seguridad, rollback, auditoría ni documentación obligatorias. «Lo más básico» significa el menor alcance funcional necesario, no saltarse controles.

Toda fase debe declarar explícitamente si acerca o no al primer lanzamiento. Si una tarea no es un bloqueo para ese objetivo, se aplaza. No confundir pruebas fixture con un servidor real ni declarar MVP completado sin evidencia de conexión externa.

Esta prioridad gobierna la planificación y la continuidad futura hasta que el propietario la cambie expresamente.

## H6-H1 — contrato de journal live aprobado (2026-11-07)

El propietario aprobó las seis decisiones de docs/DISENO_JOURNAL_RUNTIME_LIVE_H6H1_2026-11-07.md: ruta fija /var/lib/xray-manager/runtime-operations; snapshot exacto root-only 0600, sin cifrado adicional y excluido de backups, sin usar master.key; retención indefinida de operaciones no terminales/recovery_required y 30 días para terminales con limpieza explícita auditada; journal JSON autoritativo atómico sin event log append-only inicial; sin configuración previa, rollback se detiene en recovery_required sin borrar configuración nueva ni crear placeholder; no marcar completed hasta demostrar los bytes realmente cargados.

Contrato aprobado no equivale a implementación ni autorización live. Siguiente trabajo H6-H1-B/C: módulo live independiente, fixtures/mocks/directorios temporales en VPS desarrollo; sin systemctl real, sin /etc/xray, sin VPS Pruebas y sin conectar backend a R-05/menú. Después H6-H1-D auditoría adversarial. R-06/live requiere aprobación separada.

## Corrección de estado VPS Pruebas — verificación más reciente (2026-11-07)

Esta verificación sustituye cualquier instrucción anterior que indique que Xray no está instalado o que el DNS A aún debe configurarse. En VPS Pruebas (Termalin 08827b29-b7f9-4625-8ff3-351918a03c96), Xray 26.10.31 está instalado y su binario/geodata coinciden con el manifiesto mediante xray_install_integrity.py verify. No reinstalar ni repetir SIGPIPE. El estado install.json sigue desactualizado con xray_installed=false y debe reconciliarse sin reinstalación.

El A de pruebas.tvrc.me resuelve a 172.235.129.166, coincidente con la IPv4 pública observada por curl -4 api.ipify.org. DNS está configurado y propagado; no volver a modificarlo. AAAA no está verificado para uso operativo. Aún faltan /etc/xray, xray.service, configuración VLESS, certificado TLS y conexión externa. No hay listener TCP 80/443; UFW está inactivo. Certbot/ACME no se han ejecutado y no se han realizado cambios live adicionales.

Siguiente foco: desde el Administrador, reconciliar install.json; completar la ruta Certbot/certificado y configuración VLESS-WS-TLS; luego preparar y activar servicio solo con autorización live específica. Mantener el objetivo de mínimo despliegue funcional. No hacer configuración manual externa ni repetir tareas ya verificadas.

## Priorización MVP — siguiente punto de trabajo (2026-11-07)

Se realizó inspección focal de B1–B4 y del plan MVP. B1/B2/B3 se reutilizan; no rehacer sus implementaciones. B4 — aplicación live de configuración y operación de xray.service desde el Administrador — es el bloqueo principal. B5 — conexión externa con tráfico bidireccional — queda después de B4. Ver `docs/ESTADO_PRIORIZACION_MVP_2026-11-07.md` para matriz de estado, hechos actuales de VPS Pruebas, exclusiones y secuencia.

H6-H1 mantiene su contrato aprobado, pero su implementación completa queda subordinada a la necesidad demostrada por B4-MIN; no convertir journal general, renovación automática, restaurador shared snapshots ni mejoras avanzadas en prerrequisitos sin justificación normativa/técnica. Próximo paso: diseñar B4-MIN y entregar matriz normativa → reutilización → brecha → prueba, solo en desarrollo/fixtures. No live, no VPS Pruebas, no APT/ACME/systemd/runtime, no commit/push.

## B4-MIN — brecha de evidencia y diseño preliminar (2026-11-07)

La revisión focal de R-04/R-05 y backend live confirma que publicación atómica, hash runtime y proceso active no prueban por sí solos qué bytes leyó Xray. `xray_runtime_process_attestation.py` mantiene deliberadamente `configuration_loaded=false`; `xray_runtime_live_backend.py` sólo devuelve `accepted_not_verified` y no implementa restore live. Se creó `docs/DISENO_B4_MIN_EVIDENCIA_CONFIGURACION_CARGADA_2026-11-07.md` con el mecanismo preliminar de lanzador + memfd sellado, contrato mínimo, transacción, 20 pruebas y decisiones pendientes. No se modificó código ni unidad; todo sigue fixture-only y R-06/live no autorizado. Próximo paso: aprobación del diseño y decisiones del apartado 8 antes de implementar pruebas/fixtures del lanzador.

## B4-MIN — primera implementación fixture (2026-11-07)

El propietario aprobó las tres decisiones del diseño: memfd sellado como mecanismo de evidencia, publicación separada del inicio cuando el servicio está inactive, y conservación de `xray.service` con futuro lanzador root-owned/evidencia root-only sujeto a autorización de despliegue. Se añadió `scripts/xray_runtime_config_attestation.py` (primitivas fixture aisladas) y `tests/test_xray_runtime_config_attestation.py`. Pruebas nuevas 10/10 PASS; regresión focal de process-attestation/backend live/systemd adapter 56/56 PASS; total 66/66 PASS. La prueba demuestra que el descriptor memfd sellado sobrevive a exec y el proceso hijo lee los bytes exactos; no demuestra compatibilidad de Xray real con `/proc/self/fd/N`. Sin integración al menú/R-05/backend live; no se modificó unidad ni runtime, no se usó VPS Pruebas y no se hizo commit/push. Próximo paso: probar con binario Xray fijado sólo en entorno aislado, confirmar compatibilidad `-config /proc/self/fd/N` y diseñar el lanzador real separado con guardas, antes de cualquier integración live.

### Actualización B4-MIN: prueba de compatibilidad Xray (2026-11-07)
La prueba real aislada de Xray 26.10.31 confirmó que `run -test` puede validar la configuración desde el `memfd` sellado heredado si se presenta mediante un enlace simbólico temporal terminado en `.json` hacia `/proc/self/fd/N`. La ruta directa falla por detección/extensión. Resultado satisfactorio: `Configuration OK`, código 0. Se ejecutó como root; falta verificar bajo UID/GID `xray` y sandbox systemd. No se modificó unidad, servicio ni `/etc/xray`; no se desplegó live ni en Test VPS. Detalle y hash en `docs/IMPLEMENTACION_FIXTURE_B4_MEMFD_2026-11-07.md`.

### Actualización B4-MIN: UID no privilegiado y Test VPS (2026-11-07)
La compatibilidad memfd se repitió como `nobody` (UID/GID 65534): Xray 26.10.31 devolvió `Configuration OK`, exit 0. Inspección read-only de Test VPS: existe el binario Xray, pero no hay usuario/grupo `xray` ni unidad `xray.service` (LoadState=not-found); por tanto no existe sandbox systemd real que comprobar. No se creó usuario/unidad ni se modificó el host. No preparar ese entorno manualmente: la identidad y la unidad deben gestionarse desde el Administrador; la operación real conserva autorización live específica. Ver `docs/IMPLEMENTACION_FIXTURE_B4_MEMFD_2026-11-07.md`.


## Regla permanente — configuración exclusivamente desde Xray-Core Manager (2026-11-07)

El propietario establece que ninguna configuración necesaria del sistema operativo o Xray debe hacerse manualmente fuera del Administrador. Esto incluye usuario/grupo `xray`, directorios y permisos, unidad/restricciones systemd, configuración runtime, certificados, firewall, puertos, DNS, red y dependencias. Si una prueba necesita esos componentes, primero debe existir la función correspondiente en el Administrador; el entorno se prepara mediante sus menús/módulos, no con comandos manuales ni instrucciones al propietario. Se permiten inspecciones read-only y pruebas automatizadas aisladas. Toda operación live conserva la puerta de autorización específica por host y alcance. `modules/xray_service.sh` sigue siendo el único controlador de systemd para Xray. Esta regla no autoriza cambios en `Xray-Normativa/`.


## Actualización de continuidad — B4.2 (2026-11-08)

La prioridad vigente sigue siendo arrancar mediante Xray-Core Manager el servidor real VLESS + WS + TLS en `pruebas.tvrc.me:443` y demostrar conectividad externa bidireccional. El último avance autorizado es B4.2 en fixtures: supervisor root con capacidades reducidas, `NoNewPrivileges=1`, memfd propiedad de la identidad de servicio y modo 0400, contenido sellado, evidencia root-only y Xray 26.10.31 `run -test` después del descenso. Informe: `docs/IMPLEMENTACION_B4_2_SUPERVISOR_CAPACIDADES_FIXTURE_2026-11-08.md`.

La identidad usada fue `nobody:nogroup`; no se creó la cuenta xray. No se probó unidad/sandbox systemd real, InvocationID/MainPID real ni daemon. Antes de integrar hay que resolver el ownership que systemd asigna a `StateDirectory=xray`/`RuntimeDirectory=xray` al ejecutar el supervisor como root, y definir una ruta de evidencia root-only permitida por `ProtectSystem=strict`. Próximo paso: diseño/fixtures de layout de directorios y contrato de sandbox; no modificar todavía `modules/xray_service.sh`, unidad real, R-05 ni VPS de pruebas. Cambios locales sin commit/push.


## Actualización inmediata — B4.3-B implementado en fixtures (2026-11-08)

Se implementó el adaptador fixture que conecta el PID del hijo bloqueado con el almacén persistente B4.3-A mediante descriptor de raíz anclado. Archivos: `scripts/xray_runtime_supervisor_evidence.py`; APIs FD en `scripts/xray_runtime_evidence_store.py`; selector opt-in `evidence_backend="persistent_b43"` en `scripts/xray_runtime_launcher_prototype.py`. El backend B4.1 sigue como default; no hay fallback desde B4.3-B. El hijo cierra el FD raíz antes de esperar el gate; el padre lo cierra al finalizar. Fallo de creación/verificación mantiene gate cerrado y recolecta el hijo.

Validación final: B4.3-A/B focal 43/43; Python global 469/469; Bash 62/62; `compileall`, `py_compile`, `bash -n`, ShellCheck global `-S error`, `install.sh --check` y `git diff --check` PASS. El nuevo backend se probó con ejecutable fixture; la prueba Xray 26.10.31 existente corresponde al camino B4.1, no al nuevo selector.

Informe: `docs/IMPLEMENTACION_B4_3B_SUPERVISOR_EVIDENCIA_FIXTURE_2026-11-08.md`. Revisión adversarial de segunda pasada (misma sesión, NO independiente): `docs/AUDITORIA_B4_3B_ADAPTADOR_EVIDENCIA_FIXTURE_2026-11-08.md`. Dictamen PASS CON LIMITACIONES para fixtures; queda apto para revisión independiente, no para live. La evidencia `prepared_before_exec` no prueba exec, configuración cargada, proceso activo ni systemd.

Siguiente paso: revisión independiente del código y cobertura, corregir hallazgos si aparecen y volver a ejecutar regresión. Después, diseñar explícitamente la integración mínima necesaria hacia el objetivo VLESS+WS+TLS en `pruebas.tvrc.me:443`. No tocar `modules/xray_service.sh`, R-05, menú, backend live, systemd real, cuentas, runtime, VPS Pruebas, `main` ni `Xray-Normativa/` sin autorización específica.


## Revisión técnica posterior B4.3-B (2026-11-08)

Segunda pasada de revisión (misma sesión/agente, no auditoría externa independiente). Se detectó H-01: claves de metadatos no textuales provocaban `AttributeError`; se corrigió con rechazo controlado y prueba negativa. Se normalizaron también errores OSError del descriptor raíz en el adaptador. Regresión posterior: B4.3-A/B focal 44/44, Python global 470/470, Bash 62/62, compileall, py_compile, bash -n, ShellCheck global `-S error`, `install.sh --check` y `git diff --check` PASS. Informe: `docs/AUDITORIA_TECNICA_B4_3B_SEGUNDA_PASADA_2026-11-08.md`. Dictamen PASS CON LIMITACIONES, sólo fixture.


## Diseño del puente mínimo — etapa completada (2026-11-08)

La segunda revisión técnica corrigió H-01 y deja B4.3-B PASS CON LIMITACIONES en fixtures. No equivale a auditoría externa independiente. El diseño del puente mínimo se completó en `docs/DISENO_PUENTE_MINIMO_MANAGER_RUNTIME_LIVE_VLESS_WS_TLS_2026-11-08.md`. La decisión recomendada es conservar la plantilla de servicio directa `xray:xray`; B4.3 supervisor root permanece como prototipo fixture y no se conecta al daemon. La siguiente tarea es obtener revisión externa independiente H6-G3 con el paquete existente; después se implementarán L1-L5 del diseño, primero en fixtures y sin habilitar live.


## Diseño del puente mínimo Manager → runtime live (2026-11-08)

Se completó el diseño `docs/DISENO_PUENTE_MINIMO_MANAGER_RUNTIME_LIVE_VLESS_WS_TLS_2026-11-08.md`, sin implementar ni habilitar live. Decisión recomendada: conservar la unidad existente `User=xray`, `Group=xray`, `ExecStart` directo; no convertirla ahora a supervisor root B4.2/B4.3, porque eso cambiaría unidad, observador, argv, capacidades, permisos y sandbox. B4.3-B no debe conectarse al daemon: su prototipo ejecuta `xray run -test` y `prepared_before_exec` no acredita configuración cargada por systemd.

La matriz identifica el puente faltante: almacén live de operación/evidencia; staging live separado de R-02 fixture; publicador/rollback live; orquestador live separado de R-05; menú live con confirmaciones. Los componentes actuales de servicio, observación systemd, atestación de proceso y delegación al controlador existen, pero el backend live sigue sin lector live de evidencia y `restore()` falla cerrado.

Se documentó además que el exportador conserva el endpoint default histórico `hellen.tvrc.me`; para el objetivo aprobado `pruebas.tvrc.me:443` debe especificarse el endpoint correcto antes de exportar el cliente. El mapping por perfil/revisión ya se genera mediante I-01/I-02; no debe duplicarse.

Puertas previas: revisión externa independiente H6-G3 mediante `docs/PAQUETE_REVISION_INDEPENDIENTE_H6G3_2026-11-06.md`, resolución F-02/F-04/F-05 live, L1-L5 y autorización específica antes de cualquier acción real. No se modificó `modules/xray_service.sh`, backend live, R-05, journal, runtime, VPS Pruebas, `main` ni `Xray-Normativa/`.


## MVP mínimo — journal live inicial en fixtures (2026-11-08)

Se inició la implementación reducida del puente Manager → runtime live, priorizando el primer VLESS+WS+TLS y descartando integrar el supervisor root B4.3 al daemon. Se añadió `scripts/xray_runtime_live_journal.py` con almacén productivo fijo `/var/lib/xray-manager/runtime-operations`, snapshot exacto root-only, journal JSON atómico, schema estricto y transiciones monotónicas. `tests/test_xray_runtime_live_journal.py` contiene 16 pruebas aisladas.

Validación después del cambio: **486/486 Python y 62/62 Bash PASS**; `compileall`, `py_compile`, `bash -n`, ShellCheck global `-S error`, `install.sh --check` y `git diff --check` PASS. Informe: `docs/IMPLEMENTACION_JOURNAL_LIVE_MINIMO_FIXTURE_2026-11-08.md`.

Esto es sólo la base de persistencia de H6-H1-B, no una integración live ni H6-H1 completo. No hay CLI, locks/coordinación, crash recovery, reconciliación, publicador, orquestador ni menú conectados. La finalización exige atestación explícita de configuración; sin configuración previa no se permite rollback destructivo. No se creó el almacén productivo en ningún host ni se ejecutó systemctl/Xray/ACME.

Siguiente paso: construir únicamente el staging mínimo para el MVP, reutilizando mapping I-01/I-02, resolver TLS central y validación Xray bajo `xray:xray`, manteniendo R-02 fixture sin cambios. Luego diseñar el publicador live más pequeño compatible con snapshot/journal y con la unidad directa `xray:xray`. La auditoría independiente H6-G3 y la autorización específica siguen siendo puertas previas a operaciones reales. No tocar VPS Pruebas, `/etc/xray`, systemd real, DNS, firewall, certificados ni runtime.


## L2 — extracción del núcleo puro de staging TLS (2026-11-08)

Se inició L2 sin crear todavía una envoltura live. Se añadió `scripts/xray_runtime_staging_core.py`, núcleo puro sin acceso a filesystem, certificados ni procesos. Valida cobertura exacta de inbounds TLS, tags/conexiones únicas y ausencia de rutas de certificado embebidas; inyecta exclusivamente un lease preparado que debe coincidir en `connection_id`, `certificate_id` y protocolo. `scripts/xray_runtime_staging.py` (R-02) reutiliza este núcleo, conservando intactos el marcador fixture, confinamiento de rutas, locks, preflight R-01, leases centrales, validación Xray y limpieza compensatoria. No se relajó R-02 ni se habilitó `stage_live`.

Pruebas: núcleo 11/11 y staging R-02 11/11 PASS. Regresión canónica posterior: 497/497 Python y 62/62 Bash PASS; `compileall`, `py_compile`, `bash -n`, ShellCheck global `-S error`, `install.sh --check` y `git diff --check` PASS. Informe: `docs/IMPLEMENTACION_NUCLEO_STAGING_TLS_L2_FIXTURE_2026-11-08.md`.

Alcance exclusivamente fixture/desarrollo. No se creó lease productivo ni se leyó clave maestra real; no se ejecutó Xray live/ACME/systemd; no se tocaron `/etc/xray`, `/var/lib/xray-manager`, VPS Pruebas, DNS, firewall, puertos, `main` o `Xray-Normativa/`.

Siguiente paso: diseñar y probar una envoltura `stage_live` separada que reutilice el núcleo, R-01, mapping I-01/I-02 y resolutor TLS central. Debe tener rutas y locks explícitos, no permitir cambio fixture/live por variable de entorno y permanecer fuera del menú hasta auditoría independiente H6-G3 y autorización específica. No duplicar el núcleo ni convertir el staging fixture existente en live.

## L2 — preflight de perfil independiente del estado de servicio (2026-11-08)

Al diseñar `stage_live` se detectó que R-01 mezcla la validación de perfil/revisión con un fixture JSON de estado de servicio. No es aceptable sintetizar ese fixture a partir de systemd real. Se extrajo `preflight_profile(...)` en `scripts/xray_runtime_preflight.py`: valida perfil/revisión, manifiesto, informe persistido, checks obligatorios y hash del binario, y devuelve el contenido exacto en memoria; no consulta systemd ni exige fixture. La función existente `preflight(..., service_state)` conserva el contrato R-01 y su fixture obligatorio, ahora reutilizando la nueva función. La salida pública R-01 mantiene sus campos y no expone el contenido binario.

Se añadieron dos pruebas para la independencia del fixture. Pruebas focales R-01: 21/21 PASS. La validación completa posterior y las regresiones se registran en el informe `docs/IMPLEMENTACION_PREFLIGHT_PERFIL_INDEPENDIENTE_2026-11-08.md`.

No se creó `stage_live`, no se llamó `xray_runtime_systemd_adapter.status()` contra el host, no se resolvieron leases ni se crearon rutas productivas. No se consultó ni modificó VPS Pruebas, `/etc/xray`, `/var/lib/xray-manager`, systemd, certificados, DNS, firewall o puertos.

Siguiente paso: implementar una envoltura live aislada que consuma `preflight_profile` y el adaptador systemd de solo lectura directamente; debe rechazar unidad/identidad/estado incompatibles, mantener staging y leases temporales bajo rutas productivas fijas y privadas, usar lock exclusivo y limpieza compensatoria, y no publicar ni arrancar servicio. Mantenerla fuera del menú y no invocarla hasta H6-G3 y autorización específica.
