# Implementación B3 — creación de usuario y conexión VLESS-WS-TLS

**Fecha:** 2026-11-05
**Estado:** IMPLEMENTADA, VERIFICADA y AUDITADA en fixtures; ACEPTADA FORMALMENTE el 2026-11-05. Publicación autorizada exclusivamente en `design/user-identity-association-v1`.

## Alcance implementado

### B3-01 — flujo contextual de Usuarios V2

- En la administración de una conexión VLESS-WS-TLS en borrador aparece la opción [5] para gestionar sus usuarios.
- El flujo ofrece asociar una identidad global existente o crear una identidad global nueva y asociarla.
- La acción contextual fija la conexión seleccionada y no vuelve a pedir su ID.
- Se valida que la conexión exista, sea vless_ws_tls, esté en draft y tenga runtime_applied=false.
- Se reutilizan users_identity_create, users_association_create y users_v2_menu_create_association; no se duplica el modelo ni se crean credenciales paralelas.
- La credencial UUID continúa oculta durante la captura y la vista administrativa. La asociación queda en provisioning draft y runtime not_applied.

Archivos:
- modules/connections.sh
- modules/users_v2_menu.sh
- tests/users_v2_menu.sh

### B3-02 — validación estricta de revisión antes de exportar

scripts/vless_client_export.py ahora solo exporta si el manifiesto de la revisión exacta declara xray_static=pass y status=valid. No basta con que una revisión no esté marcada como inválida: pending y estados incompletos se rechazan.

La decisión se basa en el manifiesto de la revisión solicitada. No exige que el resumen metadata.json de la revisión actual apunte a una revisión histórica que se esté exportando.

### B3-03 — correspondencia TLS/SNI/certificado

- Se consulta el Certificate Store existente y se exige certificado central activo.
- Con SNI explícito, se comprueba que el SAN DNS del certificado cubra ese nombre.
- Sin SNI explícito, se valida el dominio del endpoint que el cliente usará para TLS.
- Se admiten SAN exactos y wildcard de un único nivel DNS.
- SNI incompatible, catálogo ausente/inválido, certificado no activo y endpoint IP sin un SNI DNS verificable se rechazan antes de generar URI.

### B3-04 — integración y regresión

La prueba de menú compone VLESS-WS-TLS, valida la revisión mediante el servicio real de validación de perfiles y el binario Xray 26.10.31 disponible en la VPS, y después exporta URI para el endpoint fixture hellen.tvrc.me:443. No se inicia Xray ni se publica el perfil.

## Pruebas y verificaciones

- Python unittest global: 186/186 PASS.
- Bash tests/*.sh: 61/61 PASS.
- Exportador VLESS focal: 11/11 PASS.
- Flujo de menú Usuarios V2: PASS.
- Composición → validación Xray → exportación NetMod fixture: PASS.
- python3 -m compileall -q scripts: PASS.
- bash -n global: PASS.
- ShellCheck -S error global: PASS.
- git diff --check: PASS.
- ./install.sh --check: PASS; no modificó el sistema.

Los tests usan certificados, claves, usuarios, conexiones, perfiles, mappings y almacenes temporales sintéticos. La revisión fixture fue validada con Xray 26.10.31. El resultado PASS_WITH_WARNINGS también se considera válido según el contrato existente de validación; los avisos de obsolescencia WebSocket permanecen según decisión previa del propietario.

## Límites y exclusiones

- No se probó NetMod real ni conectividad WAN.
- No se emitieron certificados ACME reales ni se consultó DNS público.
- No se activó perfil ni se ejecutaron R-01–R-04 sobre infraestructura real.
- No se instaló/actualizó ninguna dependencia.
- No se modificaron runtime Xray, systemd, certificados persistentes, claves, DNS, firewall, puertos o red.
- No se utilizó la VPS de pruebas ni se leyó la clave maestra real.
- No se modificaron main ni Xray-Normativa/.

## Estado separado

| Estado | Resultado |
|---|---|
| IMPLEMENTADO | Sí, en alcance B3 autorizado |
| VERIFICADO | Sí, pruebas globales y focales PASS |
| AUDITADO | Sí, auditoría focal B3 |
| ACEPTADO | Sí, formalmente el 2026-11-05 con las limitaciones de la auditoría B3 |
| PUBLICADO | Autorizado por el propietario; resultado SHA se registra tras el push |
| SINCRONIZADO | Pendiente de verificación final GitHub/VPS |

Etapas 2, 3 y 4 permanecen ABIERTAS. B3 no acredita aplicación runtime ni cierra ninguna etapa.
