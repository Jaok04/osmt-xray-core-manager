# Decisión técnica complementaria I-04 — Exportación de clientes VLESS-WS-TLS

**Fecha:** 2026-11-05
**Autorización:** confirmación expresa del propietario para exportar perfiles VLESS-WS-TLS a NetMod.
**Rama:** design/user-identity-association-v1.

## Alcance autorizado

- Endpoint público inicial: `hellen.tvrc.me`.
- Puerto público: `443`, coincidente con el puerto configurado en el inbound VLESS.
- Generar un URI estándar `vless://` por cada cliente UUID del inbound VLESS-WS-TLS de una revisión exacta del perfil.
- Reutilizar el mapping privado revisión → inbound_tag → connection_id para recuperar la configuración fuente validada.
- Recuperar path, Host WebSocket y SNI cliente desde la configuración persistida; no inferir SNI ni Host a partir del endpoint.
- Permitir salida por stdout y, opcionalmente, archivo de texto privado creado sin sobrescribir destinos existentes.
- Integrar la exportación como opción del menú de perfiles con selección explícita de perfil/revisión y confirmación.

## Reglas de generación

- URI: `vless://UUID@hellen.tvrc.me:443?encryption=none&security=tls&type=ws...`.
- Incluir `sni` únicamente si está configurado en `client_options.tls_server_name`.
- Incluir `host` únicamente si está configurado en `transport_options.host`.
- Codificar correctamente los parámetros de URI y el fragmento.
- No exportar perfiles que no contengan un inbound VLESS-WS-TLS inequívocamente asociado a una conexión mediante mapping exacto.
- El puerto del inbound debe ser 443; no se admite divergencia endpoint/inbound.
- Rechazar UUID inválidos/duplicados, tags/mappings ambiguos, configuración fuente incompatible y archivos inseguros.
- Exportar todos los clientes declarados en el inbound, sin modificar estados de usuarios ni catálogos.

## Seguridad y exclusiones

- No activa ni valida perfiles, no ejecuta R-01–R-04, no inicia ni reinicia Xray/systemd.
- No modifica DNS, firewall, puertos, certificados, almacenes de producción ni runtime.
- No modifica `Xray-Normativa/` ni `main`.
- Los URI contienen UUID de acceso; deben tratarse como credenciales. El archivo opcional se crea con modo 0600, escritura atómica y sin sobrescritura.
- El SNI y el Host WebSocket siguen siendo campos independientes del endpoint y del certificado del servidor.
- La generación del URI no demuestra conectividad externa ni compatibilidad funcional de extremo a extremo con NetMod.

## Relación normativa

Etapa 2 define VLESS-WS-TLS y los flujos de administración, pero no especifica un formato de URI cliente. Etapa 4 separa registro/resolución de dominios de la configuración de conexiones. Etapa 5 define perfiles y revisiones. Esta decisión técnica complementa esos alcances sin reescribir la normativa aprobada.
