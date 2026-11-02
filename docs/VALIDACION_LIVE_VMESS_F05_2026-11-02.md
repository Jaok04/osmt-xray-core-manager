# Validación operativa live VMess — F-05 — 2026-11-02

## Alcance autorizado

El propietario autorizó utilizar la VPS de desarrollo `Implementación-Xray`, en `/opt/xray-manager`, para inicializar la clave maestra y el almacén VMess, guardar y recuperar una conexión temporal, auditar la persistencia y retirar la conexión de prueba. La autorización excluyó activar runtime, modificar firewall, abrir puertos, reiniciar/instalar Xray o alterar conexiones ajenas.

## Preflight y protección de VLESS

- Rama: `design/user-identity-association-v1`.
- HEAD de partida: `695f71bae8d6e34bb79e2fd2a80d2099ac2a05f8`.
- Catálogo compartido `/var/lib/xray-manager/connections/connections.json`: JSON válido, arreglo vacío.
- `/etc/xray-manager/keys/master.key` y `/var/lib/xray-manager/vmess/`: ausentes.
- Rutas de secretos/configuraciones VLESS: ausentes; no había entradas VLESS ni datos cifrados preexistentes que pudieran quedar inaccesibles al crear la clave compartida.
- Servicio Xray: `inactive`.

La clave maestra es compartida por los almacenes VLESS y VMess. El preflight confirmó que no existían datos VLESS persistidos dependientes de una clave anterior.

## Ejecución

Se generó un certificado autofirmado y una clave privada de prueba, ambos temporales bajo `/run/xray-manager/`; no se instalaron ni desplegaron. Se creó mediante `connections_create_draft` una conexión `vmess_tcp_tls` temporal, con escucha declarada `127.0.0.1`, puerto de catálogo `43891`, un usuario sintético y estado `draft`.

El asistente construyó la configuración y el binario de validación Xray 26.10.31 (`a4a3dff`) respondió `Configuration OK`. Tras consentimiento explícito de la prueba, `vmess_config_store.py store`:

- creó `/etc/xray-manager/keys/master.key` (32 bytes, `root:root`, modo `0600`);
- creó `/var/lib/xray-manager/vmess/`, `configurations/` y `secrets/` con `root:root`, modo `0700`;
- guardó la configuración en revisión `r000001` y el secreto TLS cifrado AES-256-GCM;
- publicó las referencias VMess en el catálogo compartido, manteniendo el registro como `draft` y `runtime_applied=false`.

La lectura con `vmess_config_store.py read` autenticó y descifró el secreto. El archivo recuperado coincidió byte a byte con la clave de prueba y quedó `root:root 0600`. El recuperador real `connections_vmess_assistant_restore` reconstruyó la configuración y Xray 26.10.31 devolvió `Configuration OK`.

La auditoría live devolvió `broken_references`, `orphan_files`, `orphan_secret_files` y `unsafe_entries` vacíos, con `automatic_deletion=false`.

La prueba negativa modificó un byte del ciphertext/tag GCM: `read` falló cerrado y no produjo archivo de secreto. Restaurado el blob original, la lectura autenticada volvió a pasar.

## Limpieza

Se eliminó el borrador temporal mediante `connections_delete_draft` y confirmación exacta `ELIMINAR`. Después se retiraron únicamente los dos archivos versionados asociados a ese ID: su configuración `r000001` y su blob secreto. No se eliminó ninguna entrada ajena.

Se eliminaron los certificados, clave privada y salidas temporales de prueba bajo `/run/xray-manager/`. La auditoría posterior a la limpieza volvió a informar cero referencias rotas, huérfanos o entradas inseguras. El catálogo compartido volvió a quedar vacío.

## Estado persistente intencional

Se conservaron deliberadamente:

- `/etc/xray-manager/keys/master.key` — `root:root`, modo `0600`, 32 bytes.
- `/var/lib/xray-manager/vmess/` y sus subdirectorios vacíos — `root:root`, modo `0700`.

La clave se conserva porque es la clave maestra compartida prevista por la arquitectura VLESS/VMess; eliminarla después de inicializar el entorno no sería apropiado y podría invalidar futuros secretos. No había datos VLESS preexistentes en esta VPS. No se guardaron secretos ni certificados de prueba en el repositorio.

## Resultado y límites

- Primer guardado real con secreto TLS: PASS.
- Inicialización de clave maestra y almacén: PASS.
- Permisos y propietarios: PASS.
- Recuperación autenticada y comparación byte a byte: PASS.
- Reconstrucción y validación del borrador recuperado con Xray 26.10.31: PASS.
- Detección de alteración GCM sin liberar plaintext: PASS.
- Auditoría antes y después de limpieza: PASS.
- Catálogo final: vacío; conexión temporal retirada.
- Puerto `43891`: no estaba escuchando al finalizar.
- Servicio Xray: permaneció `inactive`.
- No se activó runtime ni se modificaron firewall, puertos, servicios, certificados desplegados o configuración de Xray.

**F-05 / VM-46: VERIFICADO LIVE.** Esta prueba verifica persistencia live y recuperación de un borrador con TLS. No verifica conectividad cliente-servidor real (VM-47), despliegue/arranque de una instancia Xray ni todas las modalidades. VMess sigue pendiente de aceptación formal y Etapa 2 permanece ABIERTA.
