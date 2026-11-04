# Diseño técnico — aplicación segura de configuración runtime Xray

**Fecha:** 2026-11-04  
**Estado:** PROPUESTA DE DISEÑO; pendiente de revisión y autorización de implementación.  
**Precondición:** U-01 aceptada formalmente por el propietario y su auditoría aceptada.  
**Alcance:** diseñar el paso desde una configuración independiente validada hasta `/etc/xray/config.json` y el proceso Xray administrado por systemd. Este documento no autoriza ejecutar ese flujo.

## 1. Objetivo y límites

Permitir que el administrador aplique una revisión exacta, previamente validada, de forma controlada, verificable y recuperable. La operación debe distinguir claramente entre `validada`, `preparada`, `publicada`, `servicio activo` y `verificada`; ninguna de esas etiquetas debe inferirse de otra.

Fuera de alcance: instalar/actualizar Xray o dependencias; ACME/Cloudflare/DNS-01; importar o renovar certificados; cambios de firewall, puertos o red; migración legacy; activación en VPS de pruebas; y pruebas externas NetMod. Los secretos TLS deben resolverse mediante el almacén central y leases existentes, no copiarse al almacén de configuración ni imprimirse.

## 2. Arquitectura propuesta

1. **Selección inmutable:** el usuario elige `config_id` y `revision` concretos. No se debe resolver silenciosamente `current_revision` después de la confirmación.
2. **Preflight de estado:** adquirir el lock de ciclo de vida compartido con las operaciones systemd y un lock exclusivo de aplicación. Comprobar que la revisión sigue siendo la misma, que su informe persistido corresponde a esa revisión y que el resultado es PASS. Si la revisión cambió, abortar y pedir revalidación.
3. **Materialización temporal:** descifrar sólo en un directorio temporal privado, con permisos mínimos, sin symlinks ni hardlinks, en filesystem adecuado; resolver certificados con leases de vida controlada. No dejar claves privadas en logs ni en directorios persistentes no protegidos.
4. **Composición:** producir una única configuración Xray completa. Validar JSON estricto, estructura, referencias, rutas, listeners/puertos, ausencia de colisiones y política de certificados. La revisión aplicada debe conservar `config_id`, `revision` y SHA-256.
5. **Validación final:** ejecutar el binario Xray exacto que usa systemd con `run -test -config` sobre los bytes ya materializados y con la identidad/permisos efectivos del servicio (`xray:xray`). No validar una copia distinta de la que se publicará.
6. **Snapshot de recuperación:** antes de tocar el destino, capturar de forma segura la configuración efectiva anterior, su hash, metadatos/permisos y estado previo del servicio. Si no hay configuración anterior, registrar explícitamente `no_previous_config`; no inventar una restauración.
7. **Publicación atómica:** escribir archivo temporal en el mismo filesystem/directorio del destino, establecer `root:xray` y modo `0640`, `fsync` del archivo, `rename` atómico a `/etc/xray/config.json` y `fsync` del directorio. Rechazar destinos/symlinks inesperados. Mantener journal durable con ID de operación y estados monotónicos.
8. **Aplicación del proceso:** Xray se administra mediante systemd. La propuesta inicial es `systemctl restart xray.service` (no asumir hot reload). Capturar estado previo `active/inactive/failed`; no habilitar/deshabilitar el servicio como efecto lateral.
9. **Verificación posterior:** confirmar `systemd LoadState`, `ActiveState`, `SubState`, `Result`, `ExecMainStatus`; comprobar que el proceso corresponde a la unidad esperada; confirmar listeners esperados sin confundir puerto abierto con conectividad de cliente; consultar journal de la ventana de operación; y volver a verificar hash/permisos del archivo publicado. La prueba externa es una fase separada.
10. **Commit del estado:** marcar aplicación `verified` sólo si todos los controles pasan. Guardar referencia exacta a revisión, hash, binario Xray, informe de validación, operación, hora y resultado. No actualizar el estado de usuarios/asociaciones a runtime-applied hasta que la aplicación esté verificada.

## 3. Máquina de estados y journal

Estados propuestos: `prepared` → `validated` → `snapshot_saved` → `config_published` → `restart_requested` → `service_active` → `verified`.

Cualquier error posterior a `config_published` debe iniciar recuperación y quedar registrado como `rollback_started` → `rollback_config_restored` → `rollback_service_restored` → `rolled_back`. Si la restauración o el reinicio de recuperación fallan: `rollback_failed`, conservar journal y snapshot, bloquear nuevas aplicaciones y mostrar instrucciones de intervención; nunca borrar evidencia ni afirmar éxito.

El journal debe ser root-owned, modo `0600`, JSON estricto, versionado, limitado en tamaño y protegido contra symlinks/hardlinks. Debe registrar hashes y rutas controladas, no secretos. La recuperación tras SIGKILL/reinicio debe ser idempotente y distinguir entre publicación incompleta, servicio reiniciado y rollback parcial.

## 4. Política de rollback

- Si falla antes de publicar: borrar sólo temporales propios y liberar leases.
- Si falla después de publicar: restaurar bytes anteriores mediante el mismo mecanismo atómico y validar de nuevo la configuración restaurada antes de reiniciar.
- Si el servicio estaba activo antes: reiniciar la versión restaurada y exigir confirmación `active`.
- Si estaba inactivo antes: restaurar archivo sin arrancar el servicio; conservar el estado inactivo.
- Si no existía configuración previa: no borrar automáticamente el destino nuevo ni improvisar una configuración; dejar el sistema en estado de recuperación explícito y detener la operación para intervención controlada.
- No hacer rollback automático de datos de usuarios, certificados o almacenes centrales: la operación sólo revierte el archivo runtime y el estado de servicio asociado.

## 5. Concurrencia y seguridad

- Un único lock de ciclo de vida debe serializar start/stop/restart/enable/disable y aplicación/rollback.
- Lock de aplicación exclusivo para impedir dos publicaciones simultáneas.
- Revalidar revisión/hash inmediatamente antes de publicar (protección TOCTOU).
- Rechazar symlinks en cada componente sensible, archivos no regulares, hardlinks, permisos laxos, rutas fuera de allowlist y binarios no confiables.
- Nunca interpolar valores de usuario en comandos shell; usar `subprocess` con argumentos separados y entorno mínimo.
- No registrar UUID completos, claves, tokens Cloudflare, PEM ni contenido de configuración.
- Lease TLS debe mantenerse válido mientras Xray lo necesite; cleanup sólo después de confirmar proceso detenido/reemplazado y no mientras el proceso aún referencia esos archivos.
- Aplicar límites de tamaño, timeout, validación estricta y control de propietario/grupo.

## 6. Integración con componentes existentes

- `scripts/xray_config_promotion.py` valida y promueve informes/metadatos C-05C, pero su propio contrato indica que no modifica runtime. No reutilizar su término `promote` como sinónimo de aplicación.
- `scripts/xray_runtime_candidates.py` realiza staging y validación nativa de candidatos; su contrato también prohíbe publicar `/etc/xray/config.json` o iniciar Xray. Puede aportar patrones de staging, hashes, permisos y locks, no se debe convertir sin ampliar explícitamente su contrato.
- `modules/xray_service.sh` valida configuración runtime como usuario de servicio y serializa acciones de systemd mediante lock de ciclo de vida. La futura operación debe compartir el mismo lock, no competir con `xray_service_action`.
- `scripts/certificate_resolver.py` prepara leases TLS. Debe revisarse la duración y limpieza del lease frente al ciclo de vida del proceso Xray antes de diseñar la implementación final.
- La unidad systemd declara `ExecStartPre=/usr/local/bin/xray run -test -config /etc/xray/config.json` y `ExecStart=...`; reinicio implica volver a validar antes de ejecutar.

## 7. Plan de implementación por incrementos

- **R-01 — contrato y preflight read-only:** resolver revisión/hash/informe/binario/identidad/estado de servicio; sin publicar ni reiniciar.
- **R-02 — staging integrado:** ensamblar configuración y leases TLS en directorio temporal; validar con usuario real de servicio; no publicar.
- **R-03 — journal y snapshot:** implementar snapshot, journal, recuperación simulada y matriz de interrupciones; aún sin destino runtime real.
- **R-04 — publicación atómica aislada:** probar con `XRAY_SERVICE_ROOT` temporal y fixtures; demostrar permisos, fsync, TOCTOU y rollback.
- **R-05 — orquestación systemd simulada:** usar adaptador/mocks para start/restart/status y fallos; demostrar preservación de estado previo y rollback idempotente.
- **R-06 — ensayo live controlado:** requiere autorización nueva y específica, backup verificable, preflight de VPS, ventana de cambio y criterios de abortar. No queda autorizado por aprobar este diseño.

## 8. Matriz mínima de aceptación

| ID | Caso | Resultado requerido |
|---|---|---|
| R01 | revisión validada vigente | permite preflight |
| R02 | revisión cambió después de validar | aborta sin publicar |
| R03 | informe ausente, corrupto o no PASS | aborta sin publicar |
| R04 | Xray rechaza bytes finales | aborta sin publicar |
| R05 | certificado/lease ausente, vencido o inconsistente | aborta sin publicar |
| R06 | symlink/hardlink/permisos inseguros | falla cerrado |
| R07 | dos aplicaciones concurrentes | serialización, una sola publicación |
| R08 | error antes de rename | destino anterior intacto |
| R09 | SIGKILL antes/después de rename | recuperación determinista con journal |
| R10 | restart falla | restaura config y estado de servicio previo |
| R11 | servicio estaba inactivo | rollback no lo arranca |
| R12 | rollback falla | conserva evidencia y bloquea nueva aplicación |
| R13 | listeners inesperados/ausentes | no marca `verified` |
| R14 | logs/errores | no revelan UUID, claves ni PEM |
| R15 | reintento tras operación verificada | idempotente; no duplica publicación |

## 9. Decisiones que requieren revisión del propietario

1. Confirmar que la estrategia inicial sea `systemctl restart` y no hot reload.
2. Confirmar política de primera aplicación cuando no exista `/etc/xray/config.json`: detenerse y exigir preparación/instalación controlada, sin autoarranque ni configuración placeholder.
3. Confirmar que rollback restaure el estado previo exacto del servicio (activo permanece activo; inactivo permanece inactivo).
4. Confirmar que la verificación de aplicación incluya listeners locales y journal, mientras la conectividad WAN/NetMod permanezca en fase independiente.
5. Confirmar que R-01–R-05 se implementen y prueben sólo con root temporal, mocks y `XRAY_SERVICE_ROOT` temporal; cualquier ensayo live R-06 requerirá autorización separada.

## 10. No autorizado por este diseño

No se ha implementado ni ejecutado aplicación runtime. No se ha escrito `/etc/xray/config.json`, instalado Xray, creado unidad/usuario de servicio, iniciado/reiniciado Xray, abierto puertos, tocado firewall/red, importado certificado real, ejecutado ACME/Cloudflare ni probado NetMod. La aceptación del diseño no equivaldrá a autorización de R-06 ni al cierre de ninguna etapa.
