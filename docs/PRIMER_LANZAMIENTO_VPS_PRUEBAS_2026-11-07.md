# Punto de continuidad operativo — primer lanzamiento en VPS Pruebas

**Fecha del corte:** 2026-11-07
**Rama de desarrollo:** `design/user-identity-association-v1`
**Repositorio:** `Jaok04/xray-core-manager` (privado)
**VPS Pruebas (Termalin host ID):** `08827b29-b7f9-4625-8ff3-351918a03c96`
**Ruta instalada:** `/opt/xray-manager`

## 1. Objetivo vigente

Realizar el primer lanzamiento funcional desde Xray-Core Manager en la VPS de Pruebas, sin configurar Xray manualmente. Perfil inicial acordado: **VLESS + WebSocket + TLS**, puerto TCP 443, dominio **`pruebas.tvrc.me`** (con «s» final). El dominio anterior `prueba.tvrc.me` fue una referencia equivocada y queda descartado.

## 2. Estado observado directamente en VPS Pruebas

Última inspección read-only realizada por Termalin el 2026-11-07:

- Sistema: Ubuntu 24.04.4 LTS, `x86_64`.
- IP observada en interfaz `eth0`: `172.235.129.166/24`; IPv6 `2a01:7e04::2000:8dff:fe47:92a8/64`. Confirmar en el panel del proveedor que `172.235.129.166` es la IPv4 pública asignada antes de crear DNS.
- Manager presente en `/opt/xray-manager`, instalado mediante bootstrap; el directorio no tiene `.git` (no tratarlo como clon Git).
- Binario `/usr/local/bin/xray` presente y ejecuta Xray `26.10.31` (`a4a3dff`, `go1.27.3 linux/amd64`).
- Geodata presentes: `/usr/local/share/xray/geoip.dat` y `geosite.dat`.
- Manifiesto `/var/lib/xray-manager/state/xray-install.json` presente.
- Verificación ejecutada y confirmada: `python3 scripts/xray_install_integrity.py verify --manifest /var/lib/xray-manager/state/xray-install.json --binary /usr/local/bin/xray --geoip /usr/local/share/xray/geoip.dat --geosite /usr/local/share/xray/geosite.dat --architecture x86_64` → `OK: Xray 26.10.31 íntegro; binario y geodata coinciden con el manifiesto.`
- `/var/lib/xray-manager/state/install.json` indica `manager_installed=true`, `xray_installed=false`, `service_configured=false`. Este estado del instalador no concuerda con los artefactos Xray encontrados y verificados; no usar ese booleano como única fuente. Investigar/reconciliar posteriormente sin invalidar el manifiesto.
- `/etc/xray` no existe.
- `xray.service` no existe (`LoadState=not-found`, `ActiveState=inactive`, `UnitFileState` vacío); no está preparado ni iniciado.
- No se encontraron listeners TCP 80 ni 443.
- UFW informa `Status: inactive`.
- Las consultas `dig A pruebas.tvrc.me` y `dig AAAA pruebas.tvrc.me` no devolvieron registros en esa observación. DNS pendiente de configuración/verificación.
- `/var/lib/xray-manager/connections/connections.json` existe y contiene una lista vacía (`[]`); no hay conexión configurada.
- No se inspeccionó ni leyó `/etc/xray-manager/keys/master.key`.

**Conclusión exacta:** el binario y los datos Xray están instalados e íntegros. No hay aún configuración de servidor, certificado, unidad systemd, proceso activo ni prueba de conexión externa. No repetir la descarga/instalación de Xray salvo que una nueva verificación detecte corrupción o ausencia.

## 3. Corrección SIGPIPE y estado del código en Pruebas

La causa del primer aborto de instalación fue corregida en desarrollo en `modules/xray_admin.sh`: se captura la salida completa de `xray version`, se valida su código de retorno y se presenta la primera línea sin `head`, evitando SIGPIPE bajo `pipefail`. `tests/xray_admin.sh` incluye fixture de salida larga.

La corrección fue publicada en rama `design/user-identity-association-v1`, commit de código `38cc0ddfac9ab3093a1c5442d14fa04c9e416e42`, documentación `2c068a42b7efd29e5d05ca5882f243689e9e0939`. En la inspección de la VPS Pruebas se encontró el código corregido en `modules/xray_admin.sh`, pero `/opt/xray-manager` no tiene `.git`; no se afirmó ni se pudo acreditar desde esa ruta un SHA Git instalado. La integridad de los artefactos Xray sí fue verificada de forma independiente.

## 4. Dominio y endpoint acordados

- FQDN correcto: `pruebas.tvrc.me`.
- Objetivo DNS: registro `A` hacia la IPv4 pública de la VPS, pendiente de confirmar en el panel del proveedor; `172.235.129.166` es la dirección observada en `eth0`.
- Perfil: VLESS + WS + TLS.
- Puerto TLS: `443/tcp`.
- Transporte WebSocket: path/Host deben definirse mediante el asistente del Manager; no inventar ni reutilizar valores de otro servidor.
- Certificado: Let's Encrypt, pendiente.
- El SNI y el endpoint para este primer lanzamiento deben usar `pruebas.tvrc.me`, salvo decisión explícita posterior.

## 5. Próximos pasos en orden — no repetir lo ya validado

1. **DNS:** confirmar en el panel del proveedor que `172.235.129.166` es la IPv4 pública asignada; crear `A pruebas.tvrc.me` apuntando a esa IP. Añadir AAAA solo si se decide servir IPv6 y está correctamente enrutable/firewalled. Consultar resolvers autoritativos y públicos hasta confirmar propagación.
2. **Reconciliar estado de instalación:** investigar por qué `install.json` dice `xray_installed=false` pese a que binario/geodata/manifiesto existen e integridad pasa. No borrar ni reinstalar artefactos verificados.
3. **Certbot:** desde el menú del Administrador, comprobar/instalar Certbot tras confirmación del operador. Antes de ejecutar APT, revisar el efecto de paquete sobre `certbot.timer`/renovación automática y definir explícitamente si se deja habilitado. La implementación local de `certificates_ensure_certbot()` está pendiente de esta decisión/auditoría y aún no está publicada.
4. **ACME:** solo después de DNS correcto, obtener Let's Encrypt para `pruebas.tvrc.me` desde el menú. HTTP-01 requiere que TCP/80 llegue a la VPS; revisar reglas del proveedor/firewall antes de iniciar el challenge.
5. **Configuración:** desde el menú del Manager, crear usuario y conexión VLESS + WS + TLS. Usar el certificado/SNI `pruebas.tvrc.me`; revisar endpoint, Host y path que presente el Manager. Validar la configuración antes de publicarla.
6. **Servicio:** preparar y activar `xray.service` únicamente desde el Administrador, con autorización específica para esa operación en la VPS Pruebas. Confirmar estado systemd, proceso, listener 443 y logs. No usar configuración manual como sustituto del Manager.
7. **Prueba externa:** conectar un cliente fuera de la VPS; verificar handshake TLS, WebSocket, autenticación VLESS y tráfico bidireccional. Registrar evidencia y documentar fallos.

## 6. Límites y autorizaciones

- Hasta el corte no se ejecutó APT, Certbot real, ACME, cambio DNS, apertura de puertos, firewall, preparación/inicio/reinicio de systemd ni activación de runtime.
- La autorización previa para corregir/publicar SIGPIPE y repetir la instalación Xray no equivale a autorización general para Certbot, ACME, DNS, firewall, puertos o systemd.
- No leer `master.key`; no imprimir ni registrar claves privadas.
- No modificar `main` ni `Xray-Normativa/`.
- No actualizar dependencias sin autorización.
- No declarar MVP ni etapa cerrada hasta que exista conexión externa real, auditoría y documentación.

## 7. Trabajo local pendiente no publicado

Existe una implementación local de instalación guiada de Certbot en `modules/certificates.sh`, pruebas fixture en `tests/certificates_menu.sh` y documentación `docs/IMPLEMENTACION_INSTALACION_CERTBOT_DESDE_MENU_2026-11-07.md`. Sus fixtures y regresiones pasaron (Bash 62/62; Python 406/406), pero no se instaló Certbot real. Antes de publicarla debe resolverse y probarse el comportamiento de `certbot.timer` para no introducir una renovación/activación automática no acordada. No asumir que este código ya está desplegado en VPS Pruebas.

## 8. Instrucción de reanudación para otra IA

Leer primero este documento, después `PROJECT_STATE.md`, `docs/PUNTO_CONTROL_ACTUAL.md`, `docs/CONTINUIDAD_DEL_PROYECTO.md`, la decisión normativa B2 y `docs/IMPLEMENTACION_CORRECCION_SIGPIPE_EXTRACCION_XRAY_2026-11-07.md`. Continuar desde el paso 1 de la sección 5. No volver a diagnosticar la causa SIGPIPE ni reinstalar Xray: la corrección está publicada y los artefactos de Xray en Pruebas pasan verificación de integridad. Mantener `pruebas.tvrc.me` como único dominio de este despliegue. Primero acciones read-only; pedir autorización específica antes de cualquier operación live.
