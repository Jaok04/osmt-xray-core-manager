# Decisiones complementarias — Etapa 2

**Proyecto:** Xray Core Manager
**Base normativa:** Etapa_2_Protocolos.md, revisión 1.3, aprobada el 30/10/2026.
**Estado:** decisión complementaria aprobada por el usuario el 02/11/2026.

## 1. Discrepancias de catálogo

- Se conservan las nueve modalidades VLESS que ya existen en el catálogo: las cinco modalidades base y las tres variantes XHTTP, además de las dos variantes de seguridad gRPC (TLS y REALITY).
- VLESS-XHTTP sin TLS, VLESS-XHTTP-TLS y VLESS-XHTTP-REALITY permanecen disponibles en el menú y en el modelo/adaptador.
- VMess-HTTPUpgrade-TLS queda pendiente de validación técnica y funcional. Su presencia en el catálogo/código no equivale a aprobación de una modalidad independiente. No se elimina ni se declara aprobada en esta decisión.
- No se modifica retroactivamente el documento normativo 1.3; este archivo registra la decisión complementaria.

## 2. Alcance de integración VLESS aprobado

La creación VLESS se integra con el modelo neutral y el adaptador Xray-core v26.10.31 para construir y validar una previsualización temporal. Los borradores no se activan ni se aplican al runtime. Las claves privadas y secretos no se guardan en el registro actual.

## 3. Límites que permanecen

La integración no habilita persistencia segura de configuración, certificados de producción, apertura de puertos, firewall, activación del servicio ni rollback transaccional. Estos puntos requieren diseño e implementación posteriores.
