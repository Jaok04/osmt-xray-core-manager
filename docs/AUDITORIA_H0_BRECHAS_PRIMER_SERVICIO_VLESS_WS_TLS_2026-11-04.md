# Auditoría H0 — brechas para el primer servicio real VLESS + WebSocket + TLS

**Fecha:** 2026-11-04
**Estado:** AUDITORÍA TÉCNICA PREPARADA — PENDIENTE DE REVISIÓN/ACEPTACIÓN DEL PROPIETARIO
**Proyecto:** `Jaok04/xray-core-manager`
**Rama:** `design/user-identity-association-v1`
**HEAD auditado:** `af4b562fb3608392b0a16388390e1dfe9b849898`
**VPS inspeccionada:** `Implementación-Xray:/opt/xray-manager`
**Alcance:** H0 de `docs/PLAN_HITO_PRIMER_SERVICIO_REAL_VLESS_WS_TLS_2026-11-04.md`.

## 1. Dictamen ejecutivo

**El proyecto NO está listo todavía para desplegar y operar un servicio real VLESS-WS-TLS desde Xray-Core Manager.** Sí existe una base significativa que debe reutilizarse: instalador de Xray fijado por versión, preparación y control independiente de systemd, asistente VLESS, adaptador Xray 26.10.31, catálogo central de certificados, leases TLS y las fases transaccionales R-01–R-04.

Las brechas que impiden completar el recorrido son:

1. El módulo funcional de Etapa 4 (dominios, DNS, ACME, renovación y UI de certificados) continúa sin implementar. Existe infraestructura de catálogo/resolución TLS, no un gestor funcional de certificados y dominios.
2. VLESS-WS-TLS genera y valida una configuración de servidor como borrador, pero no administra todavía todos los parámetros necesarios para el recorrido cliente-servidor (en particular, no hay exportación de perfil cliente VLESS ni campos de Host/SNI cliente en el flujo VLESS).
3. Los perfiles pueden gestionarse y validarse, pero la activación de perfil está expresamente pendiente.
4. R-02–R-04 están restringidas a fixtures aislados. R-01 es un preflight de solo lectura que exige un fixture de estado de servicio; no consulta systemd real. Ninguna de estas fases publica en el runtime real.
5. R-05 es diseño, no código. No existe aún una orquestación que conecte publicación, confirmación, reinicio, verificación, journal y rollback.
6. El control real independiente de systemd existe, pero no está integrado con el pipeline transaccional R-01–R-04.
7. Diagnóstico general, DNS/SSL y los respaldos genéricos de Etapa 5 están pendientes.

Por tanto, **no se debe intentar una aplicación live todavía**. La siguiente fase debe diseñarse a partir de estas brechas y de las decisiones del propietario; no se debe repetir la implementación existente.

## 2. Línea base y custodia

### 2.1 Git y VPS

- Rama local: `design/user-identity-association-v1`.
- HEAD local: `af4b562fb3608392b0a16388390e1dfe9b849898`.
- HEAD remoto: el mismo SHA.
- Checkout de `/opt/xray-manager`: limpio antes de iniciar la auditoría y sin modificaciones durante la inspección.
- No se ejecutó pull, checkout, reset, clean, rebase ni push.
- No se modificó `main`.

### 2.2 Documentación normativa

Se compararon los archivos de `Xray-Normativa/` con los homólogos de `/root/Xray_Manager_Documentacion_Final_2026-10-31`:

- 14 archivos con homólogo.
- 14/14 idénticos byte a byte.
- Cero discrepancias.
- No se modificó ningún archivo normativo.

### 2.3 Entorno actual — comprobaciones de solo lectura

- SO: Ubuntu 24.04.4 LTS.
- Arquitectura: amd64.
- `./install.sh --check`: PASS; todas las dependencias requeridas están instaladas. El comando informó que no modificó el sistema.
- Binario: `/usr/local/bin/xray`, versión 26.10.31, build `a4a3dff`.
- Geodata: `geoip.dat` y `geosite.dat` presentes.
- No se encontró archivo regular ni symlink de `xray.service`/`xray@.service` en `/etc/systemd/system`, `/lib/systemd/system`, `/usr/lib/systemd/system` ni `/run/systemd/system`.
- `/etc/xray/config.json`: ausente.
- Cuenta de sistema `xray`: ausente.
- Grupo de sistema `xray`: ausente.

La inspección de presencia/metadata no ejecutó `systemctl`, no consultó el estado del servicio ni leyó configuración runtime. No se inspeccionó el contenido de almacenes de datos o secretos.

### 2.4 Límites respetados

- No se leyó ni utilizó `/etc/xray-manager/keys/master.key`.
- No se accedió a catálogos ni almacenes live de certificados, conexiones, usuarios o perfiles.
- No se ejecutó `systemctl`, `journalctl`, instalación, actualización ni preparación de unidad.
- No se modificaron configuración runtime, certificados, DNS, firewall, puertos o red.
- No se utilizó `Vps de Pruebas`.
- No se instalaron ni actualizaron dependencias.
- No se ejecutaron suites de pruebas durante H0. La comprobación `install.sh --check` fue un no-op de dependencias.

## 3. Matriz de trazabilidad de brechas

Estados:
- **IMPLEMENTADO:** existe funcionalidad en el código.
- **PARCIAL:** existe una parte, pero no cubre el requisito completo o su integración.
- **AUSENTE:** no se encontró implementación funcional.
- **FIXTURE ONLY:** existe y se prueba exclusivamente en entorno aislado.
- **HISTÓRICO:** existe evidencia anterior, pero no se reejecutó en H0.
- **NO VERIFICADO:** no se inspeccionó el estado operativo actual por los límites de H0.

| ID | Requisito / componente | Evidencia inspeccionada | Estado | Brecha / implicación |
|---|---|---|---|---|
| H0-01 | Versión Xray fijada | `config/xray-version.conf`; `modules/xray_admin.sh` | IMPLEMENTADO | 26.10.31; adaptador VLESS versionado. No actualizar sin autorización. |
| H0-02 | Descarga e integridad de Xray | `xray_admin_fetch_verified_release`; `xray_admin_install_version` | IMPLEMENTADO | Comprueba release oficial, .dgst y SHA-256; en amd64 compara además con el digest fijado. Requiere autorización para instalar/actualizar. |
| H0-03 | Instalador integral | `install.sh` | IMPLEMENTADO | Instala paquetes faltantes y prepara Xray/unidad. No se ejecutó `--install`; solo `--check`. |
| H0-04 | Binario Xray en VPS de desarrollo | metadata y `xray version` | VERIFICADO EN H0 | Xray 26.10.31 y geodata están presentes. |
| H0-05 | Preparación de usuario/grupo y unidad | `modules/xray_service.sh`; `install.sh` | IMPLEMENTADO EN CÓDIGO / AUSENTE EN VPS | La función crea/verifica identidad y unidad, valida y ejecuta daemon-reload. La unidad y la cuenta/grupo no existen en el entorno inspeccionado. |
| H0-06 | Control real systemd | `modules/xray_service.sh`; `modules/main_menu.sh`; `tests/xray_service_control.sh` | IMPLEMENTADO, CON COBERTURA AISLADA | UI confirma start/stop/restart/enable/disable; status y journal. La prueba de control usa mocks. No se ejecutaron acciones live en H0. |
| H0-07 | Recarga compatible sin reinicio sustitutivo | menú/funciones de servicio y normativa Etapa 6 §2 | AUSENTE | El menú no ofrece reload. La normativa exige mecanismo compatible y prohíbe sustituirlo automáticamente por restart. |
| H0-08 | Diagnóstico de servicio y proceso | `xray_service_status`, `xray_service_show_logs` | PARCIAL | Estado y journal disponibles; no se integra aún el conjunto normativo de PID, ejecutable, CPU/RAM, puertos, verificación completa e informe. |
| H0-09 | Menú de certificados y dominios | `modules/main_menu.sh` | AUSENTE | La opción Etapa 4 llama a un placeholder. No hay menú operativo. |
| H0-10 | Catálogo central de certificados | `scripts/certificate_store.py`; `scripts/certificate_crypto.py` | PARCIAL IMPLEMENTADO | CLI import/list/show/audit, catálogo y secreto cifrado central. No es un gestor completo; no hay UI, rotación, eliminación ni renovación. |
| H0-11 | Resolución TLS por conexión | `scripts/certificate_resolver.py`; asistentes VLESS/VMess | PARCIAL IMPLEMENTADO | Verifica asociación y prepara leases temporales. Requiere identidad efectiva de systemd; falla cerrado si no puede determinarla. |
| H0-12 | Emisión/renovación ACME | inventario de `modules/` y `scripts/`; búsqueda de clientes ACME | AUSENTE | No se encontró integración certbot/acme.sh/lego, HTTP-01, DNS-01, renovación ni tareas de renovación. |
| H0-13 | Gestión de DNS/dominios | inventario de módulos/scripts y menú principal | AUSENTE | No hay registro/CRUD de dominios, consultas DNS A/AAAA/CNAME/TXT, propagación ni integración con proveedor DNS. |
| H0-14 | Importar certificado desde UI | CLI de `certificate_store.py` | PARCIAL | Hay importación CLI de certificado/clave existentes; no existe asistente UI Etapa 4 ni flujo de reemplazo conservando el certificado vigente. |
| H0-15 | VLESS-WS-TLS modelo y adaptador | `modules/vless_model.sh`; `modules/vless_xray_26_10_31.sh` | IMPLEMENTADO PARA GENERACIÓN | Modelo y adaptador generan inbound VLESS WebSocket + TLS para Xray 26.10.31; exige lease central para TLS. |
| H0-16 | Asistente VLESS-WS-TLS | `modules/vless_assistant.sh`; `scripts/vless_config_store.py` | PARCIAL | Pide listen address, path WS y certificate_id; persiste borrador, resuelve lease, genera JSON y ejecuta `xray run -test`. Declara expresamente que no aplica runtime. |
| H0-17 | Host/SNI y datos de cliente VLESS | asistente/adaptador VLESS y búsqueda de exportadores | AUSENTE EN FLUJO VLESS ACTUAL | El adaptador VLESS emite path WS y certificado, pero no `wsSettings.headers.Host`; no se encontró perfil/URI `vless://` ni exportación cliente con serverName/SNI. SNI cliente debe definirse separadamente del certificado del inbound servidor. |
| H0-18 | Conexión y asociación de usuarios | `modules/connections.sh`; `modules/users_v2.sh` | PARCIAL | Se crean conexiones draft y el asistente obtiene candidatos de Users V2. El estado draft/runtime_applied=false no implica usuarios servidos por runtime. |
| H0-19 | Configuración independiente y validación | `modules/xray_configurations_menu.sh`; scripts C-05 | PARCIAL / AUDITORÍA PREVIA | CRUD y validación guardada implementados. La auditoría C-05F registró validación externa y activa deshabilitadas y prueba runtime independiente pendiente. |
| H0-20 | Gestión de perfiles y revisiones | `modules/profiles.sh`; `scripts/xray_profiles.py` | PARCIAL | Crear/consultar/modificar/duplicar/renombrar e historial/validación disponibles. Eliminar está deshabilitado por dependencias. |
| H0-21 | Activar perfil | `modules/profiles.sh`, menú Etapa 5 | AUSENTE | Opción [4] Cambiar perfil activo sigue siendo placeholder/pending runtime. No se actualiza perfil activo después de verificación real. |
| H0-22 | Backup/restore genérico Etapa 5 | menú `modules/profiles.sh`; normativa Etapa 5 §§8–11 | AUSENTE / PARCIAL | Opciones genéricas de backup/restore siguen pendientes. Hay backup VLESS específico, que no sustituye el backup de perfiles ni el backup central compartido de certificados. |
| H0-23 | R-01 preflight | `scripts/xray_runtime_preflight.py` | READ-ONLY / FIXTURE-DEPENDENT | Valida perfil/revisión e identidad a partir de un fixture de estado de servicio; no consulta systemd ni publica runtime. Las pruebas históricas usan almacenes/perfiles sintéticos. |
| H0-24 | R-02 staging y leases | `scripts/xray_runtime_staging.py` | FIXTURE ONLY | Exige fixture marcado y restringe rutas al fixture. No prepara staging live. |
| H0-25 | R-03 snapshot/journal | `scripts/xray_runtime_journal.py` | FIXTURE ONLY | Exige fixture y locks aislados; no captura el runtime real. |
| H0-26 | R-04 publicación/rollback | `scripts/xray_runtime_publisher.py` | FIXTURE ONLY | Publica/recupera exclusivamente dentro de fixture. No escribe `/etc/xray/config.json`. |
| H0-27 | R-05 orquestación systemd | diseño R-05 | NO IMPLEMENTADO | Existe propuesta técnica; no hay adaptador simulado ni orquestador R-05 ejecutable. |
| H0-28 | Adaptador real integrado R-01–R-04 | módulos de servicio y runtime | AUSENTE | El control systemd existente es independiente; no coordina journal, generación, publicación, restart, verificación y rollback. |
| H0-29 | Confirmación y estados aprobados | decisiones del propietario / diseño R-05 | DISEÑO APROBADO, NO IMPLEMENTADO | No se implementan aún `generation_id`, `published_pending_apply`, `published_pending_start` ni la semántica de confirmación rechazada en el pipeline. |
| H0-30 | Diagnóstico DNS/TLS y general | menú principal y normativa Etapa 6 | AUSENTE | Diagnóstico general, conexiones/puertos, DNS, SSL/TLS e informes siguen en placeholder. |
| H0-31 | Prueba VLESS-WS-TLS cliente-servidor | expedientes de validación live | AUSENTE | No existe evidencia de conexión externa VLESS-WS-TLS ni tráfico bidireccional. |
| H0-32 | Verificación de recuperación real | R-03/R-04 y pruebas históricas | FIXTURE ONLY | Rollback y crash recovery están probados en fixture, no ante un fallo de restart systemd real. |

## 4. Evidencia histórica relevante — no confundir alcances

Los siguientes expedientes existen en el repositorio. Se citan como evidencia histórica, no como pruebas reejecutadas en H0:

1. `docs/VALIDACION_LIVE_XRAY_VLESS_WS_2026-11-03.md`: instalación real de Xray 26.10.31 y creación/recuperación/validación de un borrador **VLESS-WS sin TLS**. El expediente declara que no se creó `xray.service`, no se escribió `/etc/xray/config.json`, no hubo listener ni conexión de cliente/WAN.
2. `docs/VALIDACION_LIVE_VMESS_TLS_LEASE_2026-11-03.md`: un proceso Xray real 26.10.31 leyó certificado/clave sintéticos de un lease bajo UID/GID no privilegiados y completó un handshake TLS 1.3 en la segunda ejecución. No demuestra servicio administrado, runtime apply ni VLESS-WS-TLS.
3. `docs/VALIDACION_CLIENTE_SERVIDOR_VMESS_VM47_2026-11-02.md`: prueba cliente-servidor VMess-TLS sobre loopback. No demuestra VLESS, cliente externo, WAN ni administración de servicio por el Manager.
4. `docs/INSTALADOR_FASE_B_XRAY_SERVICE.md` y `docs/FASE_C_GESTION_SERVICIO_XRAY.md`: documentan pruebas de instalación/unidad/control en VPS desechable. No demuestran que la unidad esté instalada en la VPS de desarrollo inspeccionada hoy.
5. Expedientes R-01–R-04: R-01 valida en modo read-only con fixture de estado; R-02–R-04 registran pruebas focales/integración en fixtures. No equivalen a una aplicación live.

## 5. Brechas críticas y dependencias

### B1 — Servicio administrado no preparado en el entorno actual

El binario Xray está instalado, pero no se encontró unidad xray.service/xray@.service en las rutas estándar inspeccionadas, y faltan cuenta/grupo y configuración runtime. El código de preparación existe; ejecutarlo modificará cuentas, archivos y systemd, por lo que exige autorización live específica.

### B2 — TLS central no puede resolverse todavía contra el servicio actual

El resolutor necesita conocer la identidad efectiva de la unidad systemd para crear un lease legible por Xray. Como no hay unidad/cuenta/grupo en el entorno inspeccionado, el flujo TLS real debe fallar cerrado. No debe eludirse con rutas libres ni permisos más amplios.

### B3 — Etapa 4 incompleta

No hay UI ni automatización de dominio/DNS/ACME. El catálogo central no emite ni renueva certificados. Para un servicio VLESS-WS-TLS con dominio real se requiere decidir proveedor DNS, método de validación y cliente ACME; todavía no se solicitaron ni almacenaron credenciales de proveedor.

### B4 — Configuración servidor/cliente incompleta

El asistente VLESS guarda path y certificate_id, pero el modelo actual no genera un perfil cliente con address/port, SNI/serverName, Host y parámetros de conexión exportables. El adaptador actual genera configuración inbound de servidor; no debe confundirse el SNI del cliente con un campo del inbound. El tratamiento del Host WebSocket debe definirse y contrastarse con la versión objetivo antes de extender el adaptador.

### B5 — No existe camino seguro de aplicación real

R-01 es preflight read-only y depende de un fixture de estado de servicio; R-02–R-04 impiden intencionalmente salir de fixtures. El módulo real de systemd no consume los manifiestos/journal R-01–R-04. R-05 no está implementada. No se debe invocar manualmente `systemctl restart` para suplir esa integración.

### B6 — Perfil activo y backups

El perfil no puede activarse desde el menú; los backups genéricos y el backup central de certificados no están completos. Deben resolverse antes de declarar una operación recuperable y administrada de extremo a extremo.

## 6. Orden de trabajo recomendado tras aceptar H0

El orden sigue el plan H0–H8 y evita duplicar componentes:

1. **H1 — Preparación controlada de instalación/servicio:** especificar y probar en fixture el flujo que instala/prepara cuenta, unidad y configuración base. La ejecución en la VPS objetivo requerirá autorización live separada.
2. **H2 — Etapa 4:** diseñar/implementar UI de certificados y dominios, importación central, validación DNS, ACME HTTP-01/DNS-01, renovación y registro de historial. Seleccionar proveedor y método antes de implementar automatización.
3. **H3 — VLESS-WS-TLS:** completar solo brechas demostradas en modelo/asistente, Host cuando corresponda, metadatos cliente y exportación de perfil; probar con Xray 26.10.31 y certificados/leases sintéticos.
4. **H4 — Perfil/revisión:** conectar conexión, asociaciones, certificado y perfil/revisión exactos; mantener estados draft/validated/published/applied separados.
5. **H5 — Orquestación:** implementar primero el adaptador simulado R-05, incorporar `generation_id`, confirmaciones y estados aprobados; decidir el esquema de journal antes de modificarlo.
6. **H6 — Adaptador real:** después de auditoría y autorización específica, conectar la orquestación al `xray.service` administrado. No reutilizar el control independiente como si fuera el adaptador transaccional.
7. **H7 — Diagnóstico y backup:** completar diagnóstico de servicio/TLS/DNS, backup/restore genérico y central, y recuperación.
8. **H8 — Conectividad externa:** prueba cliente-servidor VLESS-WS-TLS con evidencia de TLS, WebSocket, autenticación VLESS y tráfico bidireccional.

La prioridad exacta entre completar H2 y desarrollar H3 debe revisarse con el propietario. H2 es dependencia para un certificado administrado/renovable; H3 puede avanzar en fixtures con certificados sintéticos, sin desplegar nada real.

## 7. Decisiones y preguntas que permanecen abiertas

No se infieren ni se aprueban por esta auditoría:

- Proveedor DNS y método ACME (HTTP-01 o DNS-01) para el dominio objetivo.
- Dominio/subdominio y servidor de destino de la primera prueba live.
- Tratamiento de Host WebSocket y definición del perfil cliente/exportación.
- Estado previo `failed` en la recuperación de servicio.
- Extensión versionada del journal R-03/R-04 frente a registro separado.
- Ventana, operaciones y rollback de cualquier intervención live.

Las decisiones aprobadas previamente se mantienen: servicio activo requiere confirmación para reinicio; rechazar deja `published_pending_apply`; publicar con servicio inactivo no lo inicia y queda `published_pending_start`; el inicio manual requiere confirmación; cada operación debe usar `generation_id` único.

## 8. Resultado de H0 y puerta de autorización

- Auditoría de brechas: **PREPARADA**.
- Aceptación formal de H0: **PENDIENTE**.
- Implementación de código tras H0: **NO AUTORIZADA POR ESTE INFORME**.
- Intervención live: **NO AUTORIZADA**.
- R-01–R-04: reutilizar; no repetir.
- R-05: no implementada.
- R-06/live: no autorizada.
- Etapas 2, 3 y 5: permanecen abiertas.

La aceptación de este informe permitirá acordar el siguiente diseño/alcance de implementación, pero no autoriza por sí sola instalar Xray, crear la unidad systemd, desplegar certificados, modificar DNS/firewall/puertos/red ni iniciar/reiniciar Xray real.

## 9. Verificaciones realizadas en H0

| Verificación | Resultado |
|---|---|
| Rama/HEAD local y remoto | Coinciden en `af4b562fb3608392b0a16388390e1dfe9b849898` |
| Árbol de trabajo | Limpio |
| Normativa vs respaldo | 14/14 idénticos |
| `./install.sh --check` | PASS; no-op |
| Versión Xray binaria | 26.10.31 / `a4a3dff` |
| Binario/geodata | Presentes |
| Unidad `xray.service` / `xray@.service` | No encontrada en rutas estándar por inspección read-only |
| `/etc/xray/config.json` | Ausente por comprobación de archivo |
| Cuenta/grupo `xray` | Ausentes por consulta NSS |
| Suites de pruebas | No ejecutadas en H0 |
| `systemctl` / `journalctl` | No invocados |
| Runtime, secretos y almacenes live | No modificados ni inspeccionados |

**Fin de la auditoría H0.**


## Seguimiento H0-17 — actualización I-02 / I-03 (2026-11-05)

El Host WebSocket se incorporó como transport_options.host y se emite mediante wsSettings.host, validado con Xray 26.10.31. El SNI del cliente se persiste por separado como client_options.tls_server_name y no se mezcla con el certificado TLS del inbound. La integración de menú y persistencia se documentan en docs/IMPLEMENTACION_I02_I03_VLESS_WS_TLS_2026-11-05.md. La exportación de URI vless:// sigue pendiente de endpoint público explícito; por tanto, H0-17 queda PARCIALMENTE RESUELTO, no cerrado.


## Seguimiento H0-17 — cierre de brecha de exportación mediante I-04 (2026-11-05)

La brecha de exportación cliente identificada en H0-17 quedó implementada en alcance focal mediante I-04, autorizada por el propietario con endpoint hellen.tvrc.me:443. El nuevo exportador genera URI vless:// por UUID desde una revisión exacta, usa mapping privado y configuración fuente validada, y conserva Host WebSocket/SNI como parámetros separados. Evidencia: docs/IMPLEMENTACION_I04_VLESS_CLIENT_EXPORT_2026-11-05.md y docs/AUDITORIA_I04_VLESS_CLIENT_EXPORT_2026-11-05.md.

H0-17 queda RESUELTO EN ALCANCE DE EXPORTACIÓN SINTÉTICA/LOCAL. No significa que el servicio live esté listo: DNS, certificado desplegado, listener público, importación en NetMod y conectividad WAN no se han probado ni autorizado.
