# Xray Core Manager --- Etapa 6: Servicio, diagnóstico y mantenimiento

**Versión:** 1.2\
**Estado:** DISEÑO FUNCIONAL APROBADO\
**Fecha:** 31/10/2026

## 1. Objetivo

Definir los módulos de servicio Xray, diagnóstico/registros y
seguridad/red/mantenimiento. Reutiliza mecanismos de etapas anteriores y
evita duplicaciones. No es implementación técnica.

## 2. Módulo 1 --- Gestión del servicio Xray-core

``` text
╔══════════════════════════════════════════════╗
║          GESTIÓN DEL SERVICIO XRAY          ║
╠══════════════════════════════════════════════╣
║ [1] Consultar estado del servicio           ║
║ [2] Iniciar servicio                        ║
║ [3] Detener servicio                        ║
║ [4] Reiniciar servicio                      ║
║ [5] Recargar configuración                  ║
║ [6] Habilitar inicio automático             ║
║ [7] Deshabilitar inicio automático          ║
║ [8] Consultar información del proceso       ║
║ [9] Verificar funcionamiento de Xray        ║
║ [0] Volver                                  ║
╚══════════════════════════════════════════════╝
```

1.  **Estado:** systemd active/inactive/failed/unknown; inicio
    automático enabled/disabled/unknown; PID, inicio, uptime y último
    resultado si están disponibles.
2.  **Iniciar:** comprobar instalación/unidad; no actuar si ya está
    activo; iniciar por systemd y verificar; conservar configuración.
3.  **Detener:** no actuar si ya está detenido; si está activo,
    confirmar, detener y verificar; no deshabilitar inicio automático.
4.  **Reiniciar:** confirmar y advertir interrupción de conexiones;
    reiniciar y verificar. Si estaba detenido puede iniciarse.
5.  **Recargar:** validar configuración en uso mediante validador de
    Etapa 5; exigir mecanismo compatible con versión y unidad. Si no
    existe, informar indisponibilidad; nunca sustituir automáticamente
    por reinicio. El usuario puede elegir \[4\].
6.  **Habilitar inicio automático:** confirmar si cambia, habilitar y
    verificar; no iniciar el servicio.
7.  **Deshabilitar inicio automático:** confirmar si cambia,
    deshabilitar y verificar; no detener el servicio en ejecución.
8.  **Información de proceso:** PID, ejecutable, versión, usuario/grupo,
    inicio, uptime, CPU/RAM si disponible; ocultar secretos en
    argumentos. Solo lectura.
9.  **Verificación:** proceso, ejecutable esperado, capacidad de carga
    de configuración, puertos en escucha y errores recientes. Estados:
    Funcionando, Funcionamiento parcial, No funciona, No verificable.
    Solo lectura.

## 3. Módulo 2 --- Diagnóstico y registros

``` text
╔══════════════════════════════════════════════╗
║             DIAGNÓSTICO Y REGISTROS         ║
╠══════════════════════════════════════════════╣
║ [1] Diagnóstico general del sistema         ║
║ [2] Diagnóstico del servicio Xray           ║
║ [3] Diagnóstico de conexiones y puertos     ║
║ [4] Diagnóstico de configuración            ║
║ [5] Diagnóstico de certificados SSL/TLS     ║
║ [6] Consultar registros de Xray             ║
║ [7] Consultar registros del administrador   ║
║ [8] Gestionar registros e historiales       ║
║ [9] Generar informe de diagnóstico          ║
║ [0] Volver                                  ║
╚══════════════════════════════════════════════╝
```

1.  **General:** SO/distribución/versión/arquitectura; CPU/RAM/disco;
    red/interfaces/IP pública; Xray/binario/versión; systemd/arranque;
    permisos; dependencias. Estados Correcto/Advertencia/Error/No
    verificable. Solo lectura.
2.  **Servicio:** instalación/binario/versión, unidad y estado,
    proceso/PID/usuario, configuración activa
    (existencia/acceso/validación), errores, dependencias y coherencia
    systemd-proceso. Solo lectura.
3.  **Conexiones/puertos:** puertos configurados y en escucha, proceso,
    TCP/UDP, conflictos, firewall y comparación configuración/escucha.
    Resultados Correcto/Puerto no disponible/Conflicto
    detectado/Configuración inconsistente/No verificable. No modificar
    firewall ni conexiones.
4.  **Configuración:** ruta activa, existencia/permisos, JSON,
    estructura, parámetros/tipos/valores, compatibilidad, referencias
    cert/key, conflictos y comparación con perfil activo. Reutilizar
    validadores de Etapa 5.
5.  **SSL/TLS:** existencia/validez/vencimiento, correspondencia
    cert-key, SAN, dominios, cadena, permisos y referencias Xray.
    Reutilizar Etapa 4; renovación/reparación permanecen allí.
6.  **Logs Xray:** consultar error/acceso/debug/todos; filtros
    fecha/severidad/palabra/IP; contexto, actualización y exportación
    TXT. Informar logs deshabilitados/ausentes/inaccesibles. No
    habilitarlos ni modificar configuración.
7.  **Logs administrador:** ejecución, errores/excepciones y operaciones
    administrativas; filtros fecha/categoría/severidad/palabra;
    contexto, actualización, exportación TXT/JSON/CSV y enmascaramiento
    de secretos.
8.  **Gestión logs/historiales:** ubicación/nivel/estado; niveles
    error/warning/info/debug; retención por tiempo/cantidad; limpieza al
    iniciar y tras nuevos registros; rotación, uso de disco; eliminación
    individual/seleccionada/total con confirmación. Sin secretos en
    texto plano. Cada etapa conserva propiedad y almacenamiento de sus
    historiales; no duplicar almacenamiento.
9.  **Informe:** alcance
    general/Xray/conexiones/puertos/configuración/SSL-TLS/todo;
    consolidar Correcto/Advertencia/Error/No verificable;
    problema/ubicación/causa/componente; recomendaciones sin reparación
    automática; exportar TXT/MD/JSON; resumen/detalle; guardar y
    retener; no incluir secretos.

## 4. Módulo 3 --- Seguridad, red y mantenimiento

``` text
╔══════════════════════════════════════════════╗
║        SEGURIDAD, RED Y MANTENIMIENTO       ║
╠══════════════════════════════════════════════╣
║ SEGURIDAD                                   ║
║ [1] Gestión de firewall                    ║
║ [2] Seguridad del servidor                  ║
║ [3] Protección y acceso SSH                 ║
║ RED                                         ║
║ [4] Información y diagnóstico de red        ║
║ [5] Gestión de puertos                      ║
║ [6] Gestión de reglas de red                ║
║ MANTENIMIENTO                               ║
║ [7] Mantenimiento del sistema                ║
║ [8] Limpieza de archivos temporales         ║
║ [9] Verificación de integridad              ║
║ [10] Herramientas de mantenimiento Xray     ║
║ [0] Volver                                  ║
╚══════════════════════════════════════════════╝
```

1.  **Firewall:** detectar UFW/Firewalld/iptables/nftables; estado;
    reglas entrada/salida/forward; habilitar/deshabilitar con
    confirmación; añadir/consultar/editar/eliminar reglas;
    respaldo/restauración; evaluar SSH/Xray/puertos; no mezclar gestores
    incompatibles; cancelar si no se protege acceso remoto.
2.  **Seguridad servidor:** actualizaciones de seguridad pendientes,
    usuarios/privilegios, permisos riesgosos, servicios innecesarios,
    protección fuerza bruta (p. ej. Fail2ban), root; informe. Cambios
    autorizados; no deshabilitar servicios esenciales.
3.  **SSH:** instalación/estado/arranque, sshd_config, puertos, root,
    contraseña/clave pública, usuarios/claves autorizadas y ajustes
    débiles. Proteger acceso; confirmar cambio de puerto; no
    deshabilitar contraseña sin autenticar alternativa; no eliminar
    claves/usuarios automáticamente; respaldo y validación.
4.  **Red:** interfaces, IP privada/pública/IPv6, rutas/gateway,
    DNS/resolución, conectividad, latencia/pérdida, conexiones/listeners
    TCP/UDP. Solo lectura.
5.  **Puertos:** TCP/UDP usados/libres/en escucha, proceso, abrir/cerrar
    y reglas, puertos Xray/conflictos/accesibilidad externa. No
    abrir/cerrar automáticamente; proteger SSH y diferenciar listener
    local de acceso desde Internet.
6.  **Reglas de red:** inspeccionar/agregar/editar/eliminar reglas
    entrada/salida/forward, NAT/redirección/conflictos;
    respaldo/restauración; detectar gestor; proteger SSH/Xray y validar.
    Comparte capa de red con \[1\] y \[5\].
7.  **Mantenimiento sistema:** uptime/carga/recursos;
    consultar/actualizar/instalar/eliminar paquetes con autorización;
    dependencias generales, obsoletos, disco y servicios fallidos.
    Mostrar cambios previstos; no actualización/eliminación automática;
    proteger SSH/Xray. Actualizaciones de seguridad pertenecen a \[2\].
8.  **Temporales:** analizar archivos/espacio recuperable/categorías;
    vista previa y confirmación; excluir configs, perfiles,
    certificados, claves, usuarios, respaldos, logs e historiales; no
    borrar archivos en uso ni usar comodines recursivos inseguros.
9.  **Integridad:** archivos manager, binario Xray, configs, perfiles,
    usuarios/asociaciones, certificados/claves, respaldos, dependencias,
    rutas/permisos. Resultados Correcto/Advertencia/Error/Ausente/No
    verificable. Sin reparación automática ni afirmaciones
    criptográficas infundadas.
10. **Mantenimiento Xray:** versión/build/arquitectura/features,
    binario, validación nativa, protocolos/transportes, archivos
    auxiliares y pruebas controladas sin sustituir config activa ni
    interrumpir servicio.

## 5. Cinco delimitaciones de coherencia aprobadas

1.  **Paquetes:** Etapa 1 \[8\] gestiona
    instalación/actualización/reparación/dependencias
    específicas/desinstalación de Xray y manager. Etapa 6 \[2\]
    actualizaciones de seguridad; \[7\] mantenimiento general. Mecanismo
    de paquetes compartido, sin gestores duplicados.
2.  **Historiales:** cada etapa conserva la propiedad de sus datos e historiales. Etapa 4 genera y conserva el historial de renovaciones de certificados; Etapa 5 conserva historiales propios
    (versiones/modificaciones de perfiles, validaciones, informes de
    restauración y preferencias de retención). Etapa 6 centraliza
    consulta, filtro, exportación, administración y limpieza de ambos
    historiales, sin almacenamiento paralelo ni duplicación de datos.
3.  **Activación/recarga:** Etapa 5 \[4\] activa perfiles y verifica.
    Etapa 6 módulo 1 \[5\] recarga configuración en uso. Si activar
    requiere reinicio, advertir y pedir autorización; recarga no
    equivale a reinicio.
4.  **Tareas:** planificador común compatible con SO; Etapa 3
    expiraciones y resets; Etapa 4 renovaciones; Etapa 5 retención de
    historiales; Etapa 6 mantenimiento/limpieza. Cada etapa conserva la
    semántica. Evitar duplicados, registrar resultados, revisar
    pendientes tras reboot, ejecutar máximo una vez si siguen
    válidas/seguras, no acumular ejecuciones. Tareas destructivas
    requieren autorización. Cerrar menú no las detiene.
5.  **Desinstalación:** exclusivamente Etapa 1 \[8\]. Etapa 6 no duplica
    el flujo.

## 6. Reglas transversales aprobadas

-   Capa común de red para firewall, puertos simples y reglas avanzadas;
    evaluar SSH/Xray, respaldar y verificar; cancelar si acceso remoto
    no está protegido.
-   Separar updates de seguridad de mantenimiento general.
-   Distinguir puertos simples de reglas avanzadas.
-   Propiedad de datos por etapa y administración operativa
    centralizada.
-   Recarga solo con mecanismo compatible; no reinicio automático
    sustitutivo.
-   Reutilizar validador Etapa 5 y verificar frescura del resultado.
-   Reutilizar verificaciones SSL/TLS Etapa 4.
-   Verificar compatibilidad Xray/SO; no inventar procedimientos
    alternativos.
-   Operaciones largas con estado, progreso confiable, resultados
    parciales, cancelación segura y registro.
-   Detectar operaciones interrumpidas tras reboot; no repetir
    automáticamente.
-   Mensajes uniformes: éxito, advertencia, error, parcial, no
    verificable.
-   Detectar cambios externos sin sobrescribir/reparar automáticamente.
-   Releer y comparar antes de cambios; detener ante modificaciones
    concurrentes.
-   Tiempos UTC, mostrar zona horaria del servidor y revisar
    sincronización.
-   Identificar dependencias/impactos y proteger componentes esenciales.
-   Revisar RAM/disco/carga; no matar procesos externos automáticamente.
-   Comprobar Internet y diferenciar DNS/ruta/conexión/servicio remoto.
-   Timeouts y reintentos limitados; evitar duplicar efectos.
-   Verificar propietario/grupo/permisos; evitar cambios recursivos
    injustificados.
-   Preparar/validar operaciones multicomponente; rollback y
    verificación.
-   Tareas automáticas identificables, documentadas, acotadas y sin
    instancias simultáneas.
-   Registrar ejecuciones omitidas; revalidar y ejecutar como máximo una
    vez si sigue siendo válida.
-   Cambios de programación identifican tareas afectadas y requieren
    autorización cuando alteren acción/horario.
-   Planificador del SO independiente del menú y de Xray cuando la tarea
    no dependa de él.

Se conservan como alcance aprobado los **24 ajustes transversales**
enumerados en esta sección. No se añaden reglas adicionales ni se
reconstruyen ajustes no incluidos en la documentación vigente.

## 7. Pendientes técnicos (no funcionales)

Prueba segura de carga; aplicación/verificación de perfiles;
compatibilidad por versión; integración del gestor de paquetes;
planificador común; respaldo/verificación/rollback de red;
almacenamiento/retención de logs e historiales. Resolver durante diseño
técnico sin alterar decisiones funcionales.
