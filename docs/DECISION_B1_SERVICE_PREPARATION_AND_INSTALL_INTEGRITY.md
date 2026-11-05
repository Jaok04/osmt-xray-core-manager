# Decisión complementaria — B1-A preparación del servicio y B1-B integridad de instalación

**Proyecto:** Xray Core Manager
**Fecha:** 2026-11-05
**Rama:** `design/user-identity-association-v1`
**Estado:** alcance de implementación autorizado por el propietario; publicación y operaciones live no autorizadas en este incremento.

## 1. Referencias y contraste normativo

- `Xray-Normativa/01_Menu_Principal`, Etapa 1, revisión 1.2.
- `Xray-Normativa/06_Servicio_Diagnostico`, Etapa 6, revisión 1.2.
- `docs/PLAN_MVP_DESPLIEGUE_VLESS_WS_TLS_2026-11-04.md`, bloque B1.
- `AGENTS.md` y `docs/REGLA_CONTRASTE_DOCUMENTACION_PRELIMINAR.md`.

La Etapa 1 define seis acciones en Administración de Xray-core (instalar, actualizar, consultar versión, consultar última versión, reinstalar y reparar). La Etapa 6 define el control operativo del servicio, pero ninguna de las dos especificaciones incluye una acción explícita para preparar su identidad y unidad. El plan MVP B1 sí requiere que la preparación pueda realizarse desde el administrador.

## 2. Decisión B1-A — ubicación de la preparación

Se incorpora como complemento técnico la opción:

`[7] Preparar servicio (verifica integridad)`

dentro del submenú existente **Administración de Xray-core**. Las opciones normativas [1]–[6] se conservan sin cambios. La opción [7]:

1. Verifica el manifiesto y los hashes de la instalación administrada.
2. Muestra qué se preparará.
3. Exige confirmación explícita.
4. Reutiliza `xray_service_prepare`.
5. No inicia ni habilita el servicio.
6. Bloquea la preparación si el servicio ya está activo.
7. Falla cerrado si la instalación no tiene manifiesto o no coincide con él.

Esta decisión no modifica ni sustituye la normativa aprobada. `Xray-Normativa/` permanece inmutable.

## 3. Decisión B1-B — manifiesto de integridad

Ruta del manifiesto:

`/var/lib/xray-manager/state/xray-install.json`

Esquema v1 registra:

- versión Xray;
- arquitectura del host;
- rutas absolutas del binario, `geoip.dat` y `geosite.dat`;
- SHA-256 del binario y ambos archivos geodata;
- SHA-256 del paquete oficial descargado;
- identificador de gestor y versión del esquema.

Seguridad del manifiesto:

- archivo regular `root:root`, modo `0600`;
- directorio padre `root:root`, modo `0700`;
- rechazo de enlaces simbólicos en componentes de ruta;
- escritura temporal en el mismo directorio, `fsync` del archivo y directorio, y reemplazo atómico.

## 4. Estados y recuperación

- Instalación con manifiesto válido y hashes coincidentes: **íntegra/verificada**.
- Instalación heredada sin manifiesto: **no verificada**; no se infiere integridad por la salida de versión.
- Manifiesto inválido, versión/arquitectura/ruta divergente, archivo ausente, permisos incorrectos o hash distinto: **no verificada**.
- `update` y `reinstall` exigen integridad demostrada antes de reemplazar.
- `repair` es la ruta explícita de recuperación; conserva respaldo previo y registra un manifiesto nuevo solo después de validar los artefactos instalados.
- Si falla el commit, rollback restaura binario, geodata y manifiesto anteriores, o elimina el manifiesto nuevo cuando no existía uno previo.
- `install` rechaza artefactos parciales/manifiesto huérfano si el binario no existe.

## 5. Límites

La implementación y las pruebas de este incremento se realizan solo con fixtures. Esta decisión no autoriza instalar/reparar Xray en un host real, crear usuarios/grupos reales, escribir `xray.service`, ejecutar `systemctl daemon-reload`, iniciar/habilitar/reiniciar servicios, modificar configuración runtime ni tocar red, firewall, DNS, certificados o dependencias.

No se cambia `main`, no se modifica `Xray-Normativa/` y no se publica este incremento sin autorización específica posterior.


### Serialización de preparación

La preparación usa el bloqueo de ciclo de vida compartido para evitar carreras con instalación, actualización, reparación y control del servicio. Si install.sh ya posee el bloqueo, la función respeta XRAY_MANAGER_LIFECYCLE_LOCK_HELD=1 y no intenta adquirirlo de nuevo.
