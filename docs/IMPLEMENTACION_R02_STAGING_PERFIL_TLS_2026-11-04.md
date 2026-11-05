# Implementación R-02 — staging integrado de perfil y leases TLS

**Fecha:** 2026-11-04
**Estado:** IMPLEMENTADA Y VERIFICADA EN ENTORNO AISLADO; AUDITORÍA LOCAL COMPLETADA; PENDIENTE DE ACEPTACIÓN FORMAL Y PUBLICACIÓN.
**Alcance:** exclusivamente R-02 de docs/DISENO_APLICACION_RUNTIME_XRAY_2026-11-04.md.
**Identidad obligatoria:** profile_id + revision.
**Entorno:** VPS de desarrollo /opt/xray-manager, fixtures y datos sintéticos temporales.

## 1. Contraste normativo y decisiones aplicadas

Se contrastó la implementación con Xray-Normativa/05_Configuraciones_Perfiles/Etapa_5_Configuraciones_Perfiles.md:

- §3.1: la activación se realiza mediante perfiles; no se ofrece una vía de aplicación desde configuraciones independientes.
- §4.1: la validación estática es obligatoria y el preflight R-01 exige el informe persistido ligado a la revisión.
- §5: una revisión Borrador/no validada no puede continuar hacia aplicación.
- §6: cada perfil conserva su copia JSON independiente.
- §7: la selección/validación no equivale a activar; la aplicación y verificación son fases posteriores.
- §8 y reglas de backup: claves privadas no se incorporan al perfil ni al manifiesto de staging.

No se modificó Xray-Normativa/.

El propietario aprobó en esta conversación el mecanismo explícito inbound tag → connection_id. R-02 lo materializa mediante un mapa de asociaciones versionado por esquema y fijado al staging mediante SHA-256. El certificado no se especifica en el mapa: se obtiene de security_options.certificate_id de la configuración central de la conexión, y el resolutor central verifica de nuevo la asociación antes de crear el lease.

## 2. Archivos incorporados

- scripts/xray_runtime_staging.py: servicio/CLI de staging aislado.
- tests/test_xray_runtime_staging.py: pruebas focales, integración con el resolutor TLS real y ejecución bajo UID/GID no privilegiados.
- Este informe y docs/AUDITORIA_R02_STAGING_PERFIL_TLS_2026-11-04.md.
- Actualización de docs/DISENO_APLICACION_RUNTIME_XRAY_2026-11-04.md y documentos de continuidad.

No se modificaron los módulos de servicio ni el flujo live.

## 3. Contrato de asociaciones

El CLI exige --fixture-root con marcador .xray-manager-r02-fixture. Todos los almacenes, claves, catálogos, locks, mapa, staging y leases deben residir dentro de ese árbol aislado; las rutas centrales ya no tienen defaults hacia /etc o /var/lib. El único recurso externo permitido es el binario Xray, cuya identidad/hash se comprueba con R-01. El CLI recibe --bindings-file, un JSON privado root:root, modo 0600, con este esquema:

    {
      "schema_version": 1,
      "bindings": [
        {
          "inbound_tag": "vless-ws-tls-in",
          "connection_id": "vless-tls-01"
        }
      ]
    }

Reglas:

1. Cada inbound TLS del perfil debe tener un tag válido y exactamente una asociación.
2. El mapa debe cubrir todos los inbounds TLS y no puede incluir tags inexistentes ni inbounds no TLS.
3. inbound_tag y connection_id no se pueden repetir dentro del mapa.
4. La conexión central debe existir, ser VLESS o VMess TLS y contener únicamente la referencia admitida certificate_id.
5. El certificado debe ser resuelto por certificate_resolver.prepare; no se aceptan PEM, rutas libres ni claves privadas desde el perfil/mapa.
6. tlsSettings.certificates debe estar ausente o vacío en el perfil. R-02 inyecta el par de rutas de lease temporal. Rechaza certificados/rutas preexistentes para evitar ambigüedad.
7. El mapa no modifica la revisión cifrada del perfil. Su contenido exacto queda fijado por bindings_sha256 y por la lista normalizada incluida en el manifiesto de staging. Esta es una entrada explícita de la operación, no una nueva fuente de autoridad sobre el perfil.

Una conexión central no se reutiliza en dos inbounds del mismo staging. La política es conservadora y evita ambigüedades de propiedad/lease.

## 4. Flujo de staging

1. Ejecuta el preflight R-01 read-only para el profile_id y revision explícitos.
2. Vuelve a leer la revisión exacta bajo lock compartido y comprueba que su hash coincide con R-01.
3. Lee y valida el mapa de asociaciones con JSON estricto, permisos y límites.
4. Comprueba la correspondencia exacta entre todos los inbounds TLS y el mapa.
5. Resuelve cada connection_id en el catálogo/configuración central VLESS/VMess; obtiene certificate_id desde security_options.
6. Invoca certificate_resolver.prepare, que vuelve a verificar la conexión y el certificado bajo sus locks y genera leases temporales.
7. Inyecta certificateFile y keyFile en tlsSettings.certificates de cada inbound correspondiente.
8. Vuelve a ejecutar R-01 y relee el perfil para proteger frente a TOCTOU durante la preparación de leases.
9. Escribe config.json dentro de un directorio de operación root:grupo-servicio, modo 0750; el archivo queda root:grupo-servicio, modo 0640.
10. Ejecuta exactamente xray run -test -config <staging>/config.json mediante subprocess con argumentos separados, entorno mínimo y UID/GID no privilegiados suministrados para el fixture.
11. Persiste un manifiesto sin secretos, con fixture_root, staging_dir y lease_root fijados; identidad de perfil/revisión, validation_id, hashes de contenido/mapa/configuración final, asociaciones, IDs de leases, identidad simulada y huella del binario Xray.

El lease_root se crea/valida dentro del fixture, root:grupo-servicio 0750, con marcador .xray-manager-r02-leases-fixture. El staging_root debe existir previamente o crearse como root:root modo 0711, con padre root:root no modificable por grupo/otros; no se alteran permisos de directorios preexistentes. El padre no permite listar el contenido de cada operación. El directorio de operación es accesible al grupo de servicio simulado. El lease TLS conserva permisos root:grupo-servicio, directorio 0750, certificado/clave 0640.

## 5. Contrato de salida y límites

La salida exitosa informa STAGED, directorio y rutas de artefactos, validation_id, hash final y IDs de leases. El manifiesto registra runtime_published=false y service_started=false.

Si ocurre un error después de crear leases, R-02 intenta borrar el directorio de staging y liberar los leases en orden inverso. Si alguna limpieza falla, el error identifica los IDs de lease/directorio que requieren intervención; no declara cleanup exitoso.

Los leases exitosos permanecen vivos junto al artefacto staged para que R-03 pueda incorporarlos a snapshot/journal y definir su ciclo de vida. No se realiza publicación, rename a /etc/xray/config.json, acción systemd, inicio/reinicio de Xray ni cambio de estado de usuarios.

## 6. Pruebas y resultados

Prueba focal tests/test_xray_runtime_staging.py: **11/11 PASS**.

Cobertura:
- staging con identidad profile_id + revision y manifiesto exacto;
- rechazo de fixture_root ausente y rutas de datos externas al fixture;
- mapa con tags/conexiones duplicadas;
- inbound inexistente/no asociado;
- permisos inseguros del mapa y symlink en ancestros de staging;
- cambio de perfil/informe durante la preparación de leases (TOCTOU);
- cleanup tras fallo de validación;
- acceso efectivo del UID/GID simulado a config y archivos TLS;
- integración real del certificate_resolver, catálogo central, certificado/clave sintéticos, cleanup del lease y consumo del staging por R-03.

En la VPS de desarrollo se utilizó el binario real /usr/local/bin/xray, Xray-core 26.10.31, para validar la configuración staged bajo UID/GID 65534:65534. El binario aceptó la configuración y leyó el certificado y la clave del lease sintético. No se consultó ni reinició xray.service.

Regresión tras incorporar R-02:
- Python: 140/140 PASS.
- Shell: 58/58 PASS.
- python3 -m py_compile scripts/*.py tests/test_*.py: PASS.
- bash -n sobre todos los scripts shell del repositorio: PASS.
- ./install.sh --check: PASS, sin cambios del sistema.
- shellcheck -S error tests/*.sh: PASS.
- git diff --check: PASS.

## 7. Límites y pendientes

- No se utilizó /etc/xray-manager/keys/master.key ni almacenes reales de perfiles/certificados/conexiones.
- Se utilizaron perfiles, claves, certificados, conexiones, catálogos y leases sintéticos en directorios temporales.
- UID/GID 65534:65534 es una identidad no privilegiada simulada; no representa ni demuestra la identidad configurada en systemd real.
- La prueba Xray run -test no inicia el servicio ni demuestra conectividad WAN/NetMod.
- El mapa se recibe como archivo de entrada independiente; su hash y contenido quedan ligados al artefacto staged. La integración de edición/gestión de ese mapa en la UI de perfiles no forma parte de R-02.
- R-03 ya está implementada y auditada localmente; R-04 (publicación atómica aislada) y R-05 (orquestación systemd simulada) siguen pendientes.
- R-06/live y la prueba real VLESS-WS-TLS con Cloudflare DNS-01/NetMod continúan NO AUTORIZADAS.

R-02 no cierra Etapa 5, Etapa 2 ni Etapa 3.
