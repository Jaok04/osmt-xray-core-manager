# Decisión técnica B3 — flujo contextual VLESS-WS-TLS y exportación segura

**Fecha:** 2026-11-05
**Estado:** IMPLEMENTADA, VERIFICADA, AUDITADA y ACEPTADA FORMALMENTE el 2026-11-05; publicación autorizada exclusivamente en design/user-identity-association-v1.
**Autorización:** el propietario autorizó B3 exclusivamente con fixtures/pruebas aisladas, reutilizando componentes existentes.

## Decisiones

1. La vista de una conexión VLESS-WS-TLS en estado draft ofrece una acción contextual para gestionar sus usuarios.
2. El flujo permite asociar una identidad global existente o crear una identidad nueva y asociarla directamente a la conexión seleccionada. No vuelve a solicitar el ID de conexión.
3. La asociación conserva el modelo Usuarios V2: UUID VLESS único global, límites/capacidad y estados independientes. La identidad global no se confunde con la credencial UUID.
4. La exportación de clientes exige que el manifiesto de la revisión exacta registre xray_static=pass y status=valid. Las revisiones históricas se evalúan por su propio manifiesto, sin depender del resumen de la revisión actual.
5. Antes de exportar, el certificado central activo debe cubrir el nombre que el cliente verificará: SNI configurado o, si no se configura SNI, el dominio del endpoint público.
6. La comparación de SAN acepta coincidencia DNS exacta o wildcard de un solo nivel. Los endpoints IP fallan cerrados porque el catálogo de certificados actualmente conserva SAN DNS, no SAN IP.
7. La exportación no activa perfiles ni cambia runtime. No se ejecutan ACME, systemd, DNS, firewall, puertos o conectividad externa.

## Componentes reutilizados

- Usuarios V2: identidades, asociaciones, UUID único y capacidad.
- Conexiones: borradores y menú de administración.
- I-01: compositor VLESS-WS-TLS.
- I-02/I-03: Host WebSocket y SNI cliente separados.
- I-04: exportador URI NetMod.
- Certificate Store: metadatos y SAN del certificado.
- Validación de perfiles: manifiesto de validación de revisión exacta y Xray fijado.

## Fuera de alcance

No se implementa activación/publicación de perfiles, aplicación runtime, servicio real, pruebas WAN, cliente NetMod real, ACME real ni gestión de SAN IP. No se modifica la normativa aprobada ni se reconstruyen I-01–I-04 o R-01–R-04.
