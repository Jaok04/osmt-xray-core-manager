# Instalador — Fase B: Xray-core y unidad systemd

Estado: implementada y validada en una VPS desechable con Ubuntu 24.04.4 LTS (2026-11-02).

## Alcance

La Fase B amplía install.sh después de desplegar el Manager. Desde el cambio de flujo del 2026-11-06, esta fase es opcional y sólo se ejecuta con `--install --with-xray`; la instalación predeterminada despliega únicamente el Manager. El mismo flujo de Xray-core está disponible después desde el menú de Administración de Xray-core:

1. Verifica condiciones previas del servicio antes de modificar el binario.
2. Instala Xray-core en la versión fijada por config/xray-version.conf, usando el flujo existente de descarga oficial, SHA-256, extracción segura, respaldo y rollback.
3. Crea o valida el grupo y usuario de sistema xray:
   - grupo primario xray;
   - cuenta de sistema con UID inferior a 1000;
   - home /var/lib/xray;
   - shell /usr/sbin/nologin;
   - sin crear un home automáticamente con useradd.
4. Prepara /etc/xray con permisos root:xray, modo 750.
5. Prepara /var/lib/xray con permisos xray:xray, modo 750.
6. Instala /etc/systemd/system/xray.service de forma atómica y no sobrescribe una unidad ajena.
7. Ejecuta systemd-analyze verify y systemctl daemon-reload.

## Política de activación

La instalación no ejecuta systemctl enable, systemctl start ni systemctl restart. La unidad queda registrada, pero deshabilitada y detenida en una instalación nueva.

La unidad usa ConditionPathExists para omitir el arranque mientras no exista la configuración y ExecStartPre para validarla con xray run -test -config antes de cada arranque. Si todavía no existe /etc/xray/config.json, el servicio no debe arrancar. La habilitación e inicio quedan para la fase de administración del servicio, después de generar y validar una configuración real.

## Unidad systemd

La unidad ejecuta Xray como usuario no privilegiado xray:xray, incluye reinicio ante fallos y límites razonables, y aplica aislamiento de systemd (ProtectSystem=strict, ProtectHome, PrivateTmp, NoNewPrivileges, restricciones de capacidades y familias de sockets). Se conserva CAP_NET_BIND_SERVICE para permitir listeners en puertos privilegiados como 443.

## Idempotencia y seguridad

- Si el binario ya existe y geodata está presente, se solicita actualización; si falta geodata, se usa reparación.
- Una unidad existente solo se acepta si coincide exactamente con la unidad administrada.
- Se rechazan rutas simbólicas y destinos que no sean archivos/directorios regulares.
- Si Xray está activo, la instalación/actualización se bloquea para no reemplazar un binario en ejecución.
- Si ya existe un usuario o grupo con el nombre reservado, se valida que corresponda a una identidad de sistema con los atributos esperados.
- Si existe configuración, se valida con Xray como usuario del servicio antes de preparar la unidad.

## Pruebas

- tests/xray_service.sh: unidad, identidad simulada, idempotencia, colisiones, configuración inválida y rutas simbólicas.
- tests/install.sh: instalación aislada Manager-only por defecto y Fase A+B explícita con `--with-xray`, conservación de datos, permisos, estado y unidad.
- tests/stage1_dependencies.sh: dependencias adicionales de systemd y cuentas de sistema.

La descarga/verificación/instalación real de Xray-core se validó en un prefijo temporal en la VPS desechable. La unidad real del host pasó `systemd-analyze verify` y permaneció inactive/disabled. La persistencia tras reinicio y la activación real de la unidad siguen pendientes de una prueba controlada; no se ejecutó instalación real en la VPS de desarrollo.

## Resultado de la prueba real

La instalación se ejecutó en una VPS desechable Ubuntu 24.04.4 LTS, arquitectura amd64, con systemd activo.

- Xray-core 26.10.31 instalado y verificado; SHA-256 del binario: cc4b84d3069569f297a61f04b914f2bb37e9d202fd7b84cb50def1fc30fd40e1.
- Usuario de sistema xray (UID 999), grupo primario xray (GID 988), shell /usr/sbin/nologin.
- Unidad xray.service aceptada por systemd-analyze verify.
- Estado final: inactive y disabled.
- ConditionPathExists y ExecStartPre impiden iniciar sin /etc/xray/config.json; se comprobó que Xray rechaza la ausencia de ese archivo.
- Segunda ejecución de install.sh --install: idempotente; Xray ya estaba en la versión fijada y la unidad se conservó.
- Las 18 suites se ejecutaron en la VPS desechable. La suite VLESS/XHTTP utilizó el binario Xray recién instalado.
- Hashes de los registros operativos del Manager sin cambios durante las pruebas.
- No se creó una configuración de producción y no se inició ni habilitó Xray.

El análisis estático systemd-analyze security informó un nivel de exposición 3.2 (OK). Las capacidades de red necesarias para listeners privilegiados y el acceso de red del proxy explican parte de la exposición residual.

## Advertencias del release validado

Xray 26.10.31 aceptó todas las configuraciones generadas, pero emitió avisos deprecación para WebSocket y gRPC, recomendando migración futura a XHTTP. También advirtió sobre REALITY en puertos distintos de 443. Son advertencias, no fallos de validación; se conservan las modalidades aprobadas y deben considerarse en la planificación de compatibilidad futura.

## Flujo de instalación actualizado (2026-11-06)

- `sudo ./install.sh --install`: instala sólo Xray Core Manager. No descarga ni instala Xray-core, no crea usuario/grupo `xray`, no prepara `/etc/xray` y no crea/modifica `xray.service`.
- `sudo ./install.sh --install --with-xray`: conserva la instalación integral anterior, con verificación SHA-256 y preparación de unidad; no inicia ni habilita el servicio.
- Después de instalar sólo el Manager, Xray-core se instala desde **Administración de Xray-core → Instalar Xray-core** y la unidad se prepara desde **Preparar servicio**.

Las pruebas aisladas verifican ambas modalidades. El flujo Manager-only no inspecciona ni cambia fixtures de Xray preexistentes.


## Distribución desde VPS limpia (2026-11-06)

La descarga del código del Manager se realiza antes de esta fase mediante el bootstrap privado descrito en `docs/INSTALACION_DESDE_VPS_LIMPIA.md`. El PAT sólo necesita `Contents: Read-only`; la Fase B conserva sin cambios la verificación SHA-256 del artefacto oficial de Xray-core y la política de servicio detenido/deshabilitado. El bootstrap del Manager no instala Xray-core por defecto.
