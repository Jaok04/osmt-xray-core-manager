# Implementación del resolutor TLS centralizado

**Fecha:** 2026-11-03
**Versión:** 1.0
**Estado:** IMPLEMENTADO PARCIALMENTE Y VERIFICADO EN PRUEBAS AISLADAS
**Rama:** `design/user-identity-association-v1`

## 1. Alcance

Se implementó un primer resolutor controlado que autoriza una conexión VMess/VLESS mediante su configuración persistida, valida el recurso TLS central y prepara una copia temporal de certificado público y clave privada para el grupo efectivo del servicio.

El resolutor no modifica configuraciones Xray, no activa conexiones, no reinicia servicios y no integra todavía los asistentes ni los generadores. Los almacenes VMess/VLESS actuales aún no aceptan el nuevo contrato TLS basado exclusivamente en `certificate_id`; las pruebas del resolutor usan fixtures versionados con el contrato central para validar la frontera de autorización.

## 2. Archivos

| Archivo | Cambio |
|---|---|
| `scripts/certificate_resolver.py` | Nuevo módulo de autorización, resolución temporal, verificación de identidad systemd y limpieza de leases |
| `tests/certificate_resolver.sh` | Pruebas aisladas de VMess/VLESS, managed/reference, permisos, limpieza y rechazos |
| `config/paths.sh` | Ruta operativa reservada `XRAY_MANAGER_CERTIFICATES_RUNTIME_DIR=/run/xray-manager-certificates` |
| `docs/ARQUITECTURA_CERTIFICADOS_CENTRALIZADOS.md` | Estado técnico y contrato de resolución actualizados |
| `docs/IMPLEMENTACION_RESOLUTOR_CERTIFICADOS_TLS.md` | Este informe |
| `PROJECT_STATE.md`, `docs/PUNTO_CONTROL_ACTUAL.md`, `docs/CONTINUIDAD_DEL_PROYECTO.md`, `HISTORY.md` | Continuidad y trazabilidad |

## 3. Autorización por conexión

La operación `prepare` recibe `connection_id` y `certificate_id`, y verifica:

1. El catálogo de conexiones contiene exactamente una entrada para el ID solicitado.
2. El protocolo es VMess o VLESS; otros protocolos se rechazan.
3. La referencia y revisión de configuración corresponden al ID de conexión y al registro de catálogo.
4. El esquema de configuración es versión 1, el protocolo y modalidad coinciden con el catálogo y la modalidad realmente es TLS.
5. El objeto `security_options` contiene exactamente `certificate_id`; no acepta rutas libres, `secret_ref` ni campos adicionales.
6. El ID solicitado coincide exactamente con el ID que la configuración de esa conexión autoriza.
7. La modalidad está en el mapa de modalidades conocido del protocolo.

Los catálogos/configuraciones se leen bajo bloqueo de integridad de conexiones y bloqueo del catálogo central. Se comprueban referencias, revisiones, archivos regulares, propietarios, permisos, symlinks y hardlinks.

## 4. Verificación del recurso central

- El certificado debe existir una sola vez en el catálogo y estar en estado `active`.
- Se admite `managed` y `reference`.
- El blob se recupera desde la referencia central de revisión 1.
- La clave maestra existente se lee mediante `certificate_crypto.py`; no se crea, regenera ni modifica.
- AES-256-GCM autentica el blob y el AAD vincula el secreto al certificado y revisión.
- Se vuelve a comprobar que el certificado y la clave privada correspondan criptográficamente.
- Se comparan huellas SHA-256 del certificado y de la clave pública contra el catálogo.
- Se rechaza un certificado fuera de su período de validez.
- Los errores no imprimen PEM, clave privada, ciphertext ni contenido de secretos.

## 5. Preparación temporal

El directorio operativo previsto es:

`/run/xray-manager-certificates`

La raíz y cada lease se crean con propietario `root`, grupo efectivo del servicio y modo `0750`. Los archivos son `root:<grupo-servicio>` modo `0640`:

- `certificate.pem`
- `private-key.pem`
- `manifest.json` (metadatos no secretos)

El directorio no es escribible por el grupo del servicio; el servicio sólo necesita atravesarlo y leer los archivos. La clave privada no aparece en argumentos de proceso, JSON de respuesta, logs ni manifest. El resultado de `prepare` devuelve únicamente rutas, IDs y el identificador opaco del lease.

El uso de `/run` hace que el material sea volátil y desaparezca tras reinicio del sistema. La integración runtime posterior deberá recrearlo antes de validar/iniciar Xray; este bloque no cambia la unidad systemd.

## 6. Identidad del servicio

La CLI consulta la identidad efectiva de la unidad mediante `systemctl show`. Exige `User` y `Group` explícitos, rechaza grupos suplementarios y cuentas/grupos privilegiados, y no asume automáticamente que exista el usuario `xray`.

En la VPS de desarrollo, `xray.service` no está instalada y no existen cuenta/grupo `xray`. Por eso la CLI real falló de forma cerrada antes de crear archivos temporales. La prueba de API usó una identidad sintética no privilegiada (UID/GID 1) para verificar propiedad y permisos, no para afirmar que el usuario Xray real esté instalado.

## 7. Ciclo de vida y limpieza

Cada preparación crea un lease aleatorio `resolve-<32 hex>`. La limpieza:

- exige root;
- valida formato del lease;
- valida propietario, grupo, modo y tipo del directorio;
- valida el manifest y que su ID coincida;
- rechaza symlinks, hardlinks, archivos no regulares o permisos alterados;
- elimina exclusivamente el directorio de ese lease;
- no recorre ni elimina rutas arbitrarias.

No hay limpieza automática por timer ni integración con el ciclo de vida del servicio todavía. La limpieza se invocará explícitamente desde la futura integración; después de reinicio, `/run` ya no contiene los leases.

## 8. Interfaz CLI

La CLI admite:

- `prepare --connection-id ID --certificate-id ID`
- `cleanup --lease-id resolve-...`

La respuesta es JSON sin secretos. Los argumentos globales permiten rutas de catálogo/almacenes y unidad systemd para pruebas y despliegues controlados. La CLI exige identidad real de systemd antes de preparar o limpiar.

## 9. Pruebas ejecutadas

Nueva prueba `tests/certificate_resolver.sh`:

- resolución autorizada VLESS con certificado `managed`;
- resolución autorizada VMess con el mismo recurso central;
- resolución VLESS con certificado `reference`;
- verificación de contenido PEM preparado;
- propietario, grupo y modos exactos;
- manifest sin material secreto;
- limpieza por lease y ausencia posterior del directorio;
- rechazo de ID de certificado no asociado;
- rechazo de configuración que apunta a otro ID;
- rechazo de protocolo no soportado.

Resultado focal: PASS.

Regresión completa posterior a la incorporación del resolutor: **42/42 scripts PASS**.

Verificaciones:
- `bash -n tests/certificate_resolver.sh`: PASS.
- `bash -n config/paths.sh`: PASS.
- `python3 -m py_compile scripts/certificate_crypto.py scripts/certificate_store.py scripts/certificate_resolver.py`: PASS.
- `shellcheck -S warning tests/certificate_resolver.sh tests/certificate_store.sh`: PASS.
- `git diff --check`: PASS.
- Prueba CLI en VPS sin unidad Xray: rechazo fail-closed por ausencia de identidad explícita de servicio; no creó leases.

## 10. Límites explícitos

- No se modificaron `vmess_config_store.py`, `vless_config_store.py`, asistentes ni generadores. Aún rechazan el nuevo contrato central; por tanto el resolutor no puede usarse con conexiones creadas por el flujo actual hasta implementar esas integraciones.
- No se ha probado lectura por un proceso real `xray`; la VPS de desarrollo carece de cuenta/unidad.
- No se ha probado la sandbox real de systemd (`ProtectSystem=strict`, `PrivateTmp`) con archivos en el nuevo directorio.
- No se aplicó ni generó configuración runtime y no se reinició Xray.
- No se modificó la VPS `Vps de Pruebas`, certificados desplegados, firewall ni puertos.
- No se migraron secretos históricos ni se modificó REALITY.
- No se importaron certificados reales al almacén persistente.
- No se modificó `Xray-Normativa/`.
- El plaintext de clave privada existe temporalmente en memoria Python y en el archivo protegido que Xray necesitará leer; Python no garantiza borrado seguro de objetos bytes de memoria.

## 11. Estado por categoría

| Categoría | Estado |
|---|---|
| Autorización por `connection_id` + `certificate_id` | IMPLEMENTADA; pruebas aisladas PASS |
| Validación de catálogo/huellas/vigencia | IMPLEMENTADA; pruebas aisladas PASS |
| Resolución temporal managed/reference | IMPLEMENTADA; pruebas aisladas PASS |
| Permisos root:grupo-servicio | IMPLEMENTADOS; identidad sintética en pruebas |
| Identidad efectiva systemd | IMPLEMENTADA; CLI fail-closed en VPS sin unidad |
| Limpieza por lease | IMPLEMENTADA; pruebas PASS |
| Integración con almacenes VMess/VLESS | PENDIENTE |
| Adaptación asistentes/generadores | PENDIENTE |
| Servicio Xray real y sandbox | NO PROBADO |
| Aplicación a runtime | FUERA DE ESTE BLOQUE |
| Aceptación formal | PENDIENTE |

**No declarar terminada la etapa de certificados ni aceptado el resolutor para producción.**
