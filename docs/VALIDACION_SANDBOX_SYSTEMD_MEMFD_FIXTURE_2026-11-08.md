# Validación del sandbox systemd para launcher memfd — fixture (2026-11-08)

**Resultado:** PASS para compatibilidad técnica del launcher memfd con el sandbox probado.
**Host:** VPS de desarrollo Implementación-Xray (Ubuntu 24.04.4, systemd 255).
**Rama/commit base:** design/user-identity-association-v1, 0b4f6f1c7af3496975682726e9070ed4fae14c3f.
**Unidad:** servicio transitorio xray-manager-sandbox-20261108.service, creado con systemd-run --collect y retirado al finalizar.
**Identidad de prueba:** nobody:nogroup (65534:65534); no se creó xray:xray.

## Objetivo

Comprobar que Xray 26.10.31 puede ejecutar el launcher fixture con memfd sellado bajo el aislamiento de un servicio systemd, conservar FD 3 tras exec y permitir su inspección root-only desde el host. La prueba no debe crear ni modificar una unidad persistente ni abrir listeners.

## Preparación y aislamiento

- Fixture efímero creado dentro de /opt/xray-manager, raíz root-owned modo 0711, marcador root:root 0600, configuración sintética root:root 0644 y symlink root-owned .json hacia /proc/self/fd/3.
- Configuración de 96 bytes, SHA-256 bd916b0ed2eefbaf8b26f8d0dc5a4289ca0ebfeea31ae2da9256c81436dc4018, con inbounds: []; no contiene credenciales ni destinos de usuario.
- Binario de prueba: /usr/local/bin/xray (Xray 26.10.31).
- Proceso ejecutado por systemd como nobody:nogroup, no como root.
- Unidad transitoria con Type=exec, NoNewPrivileges=true, PrivateTmp=true, PrivateDevices=true, ProtectHome=true, ProtectSystem=strict, ReadOnlyPaths=/opt/xray-manager, ProtectKernelTunables=true, ProtectKernelModules=true, ProtectControlGroups=true, ProtectClock=true, ProtectHostname=true, ProtectKernelLogs=true, LockPersonality=true, RestrictSUIDSGID=true, RestrictRealtime=true, RestrictNamespaces=true, RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6, SystemCallArchitectures=native, CapabilityBoundingSet=CAP_NET_BIND_SERVICE, AmbientCapabilities=CAP_NET_BIND_SERVICE, ProtectProc=invisible y ProcSubset=pid.
- Se eligió un servicio transitorio, no systemd-run --scope: el scope hereda el entorno de ejecución del llamador y no reproduce el sandbox aislado de un servicio.
- El fixture se ubicó fuera de /tmp para que PrivateTmp=true no ocultara su ruta.

## Resultado observado

systemd mostró la unidad en active/running, con User=nobody, Group=nogroup, ProtectSystem=strict, ProtectProc=invisible, ProcSubset=pid, PrivateTmp=yes, NoNewPrivileges=yes, CapabilityBoundingSet=cap_net_bind_service y AmbientCapabilities=cap_net_bind_service.

El proceso Xray permaneció activo después de que el launcher ejecutara xray run -test y se reemplazara mediante exec. El verificador root-only inspeccionó el PID principal del servicio y confirmó:

- verified=true, environment=fixture.
- PID del proceso Xray igual al MainPID de la unidad transitoria.
- UID/GID efectivos 65534:65534.
- FD 3 presente, con destino /memfd:xray-manager-config (deleted).
- Hash y tamaño del descriptor iguales a la configuración sintética.
- Modo 0400 y seals completos, máscara 15.
- descriptor_process_bound=true.
- configuration_loaded=false, configuration_evidence=sealed_memfd_process_bound.

La lectura de /proc/self/fd/3 por Xray funcionó dentro del sandbox que aplicó ProtectProc=invisible y ProcSubset=pid. El proceso conservó el descriptor y el mismo PID después de exec.

## Limpieza y alcance

- Se detuvo la unidad transitoria.
- Con --collect, systemd la descargó: LoadState=not-found, ActiveState=inactive, SubState=dead.
- El directorio fixture se eliminó mediante el trap de limpieza.
- La comprobación posterior no encontró proceso Xray ni directorio fixture residual.
- No se abrió ningún listener: la configuración tenía inbounds: [].
- No se creó ni modificó xray.service, una unidad persistente, cuentas/grupos, /etc/xray, configuración runtime, certificados, DNS, firewall, puertos o red.
- No se ejecutó ninguna operación en VPS Pruebas. No se conectó el launcher a modules/xray_service.sh, backend live, journal, publicador, start coordinator, R-05 ni menú.

## Dictamen y límites

**GO para compatibilidad del prototipo memfd dentro del sandbox fixture probado. NO-GO para integración live o despliegue.**

La prueba demuestra que systemd 255, con las propiedades indicadas, no rompe el acceso de Xray a FD 3 ni la inspección root-only del descriptor en este host. No demuestra la configuración final de xray.service, la identidad xray:xray, el uso de CAP_NET_BIND_SERVICE para abrir 443, el comportamiento de ExecStartPre separado, el tráfico de red ni la conexión externa. Tampoco demuestra criptográficamente qué bytes aceptó el parser interno: configuration_loaded permanece false.

No cambiar el contrato actual de la unidad directa ni integrar el launcher hasta revisión independiente H6-G3, resolución de los hallazgos pendientes y autorización live específica por host/alcance. La siguiente tarea recomendada es actualizar la matriz de brechas de B4-MIN y preparar el paquete H6-G3 con esta evidencia nueva; no ejecutar operaciones live.
