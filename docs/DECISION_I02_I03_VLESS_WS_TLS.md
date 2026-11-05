# Decisión técnica complementaria I-02 / I-03 — VLESS-WS-TLS

**Fecha:** 2026-11-05
**Autorización:** confirmación expresa del propietario para implementar I-02 e I-03.
**Rama:** design/user-identity-association-v1.

## Relación con la normativa

La normativa Etapa 2 conserva VLESS-WS-TLS como modalidad WebSocket + TLS y exige validar la combinación con la versión objetivo. No especifica los campos Host WebSocket ni SNI/serverName del cliente. Esta decisión complementaria los incorpora sin modificar Xray-Normativa/.

## I-02 — Integración en perfiles

- Añade una acción al menú de perfiles que selecciona un perfil con revisión actual y una conexión VLESS-WS-TLS elegible.
- Solo admite conexiones draft con runtime_applied=false.
- Muestra perfil, revisión origen, conexión y puerto antes de pedir confirmación.
- Invoca el compositor I-01 con rutas explícitas y reutiliza el catálogo Usuarios V2, el catálogo de conexiones, el certificado central y el mapping TLS de la revisión origen.
- Crea una revisión inmutable nueva; las anteriores no se sobrescriben.
- La nueva revisión queda pendiente de validación. No se activa, no se publica y no llama Xray/systemd.
- Si existe TLS previo en el perfil, el mapping exacto es obligatorio; el compositor mantiene su comportamiento fail-closed.

## I-03 — Host y SNI del cliente

- transport_options.host es opcional y solo corresponde a la cabecera HTTP Host de WebSocket. Se representa en Xray como wsSettings.host.
- client_options.tls_server_name es opcional y corresponde exclusivamente al SNI/serverName usado por el cliente al conectar. No se inyecta en el inbound ni reemplaza el certificado TLS del servidor.
- La configuración VLESS-WS-TLS usa esquema 2 únicamente cuando se guarda al menos uno de esos campos. Las configuraciones existentes de esquema 1 continúan siendo válidas.
- La clave privada/certificado TLS del servidor continúa gestionándose por el catálogo central. El SNI del cliente no altera el certificado ni el lease.
- Este bloque almacena los parámetros de cliente; la exportación de un URI/perfil importable requiere además un endpoint/dominio de conexión explícito y queda fuera de este alcance.

## Seguridad y límites

- Host y SNI se validan como nombres DNS ASCII, sin espacios, puertos, comodines ni caracteres de control.
- No se leen secretos durante el desarrollo ni se ejecuta el compositor contra almacenes live.
- No se toca main, Xray-Normativa/, Xray runtime, systemd, certificados desplegados, firewall, DNS o red.
- R-01–R-04 se reutilizan sin modificaciones.
