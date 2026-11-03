# XRAY CORE MANAGER

## Índice general de documentación

**Proyecto:** Xray Core Manager\
**Versión:** 2.0\
**Fecha:** 31/10/2026\
**Estado:** Etapas 1--6 aprobadas; Etapa 1 revisión 1.2; Etapa 2 revisión 1.3; Etapa 3 revisión 1.2; Etapa 4 revisión 1.1; Etapa 6 revisión 1.2.

## 1. Objetivo

Punto de entrada a la documentación funcional y estructural. La
programación comenzará después de completar y revisar las
especificaciones funcionales.

## 2. Estructura

``` text
Xray_Manager_Documentacion/
├── 00_Indice_General.md
├── 01_Menu_Principal/
│   ├── Etapa_1_Menu_Principal.md
│   └── Etapa_1_Menu_Principal.yaml
├── 02_Protocolos_Conexiones/
│   ├── Etapa_2_Protocolos.md
│   └── Etapa_2_Protocolos.yaml
├── 03_Gestion_Usuarios/
│   ├── Etapa_3_Usuarios.md
│   └── Etapa_3_Usuarios.yaml
├── 04_Certificados_Dominios/
│   ├── Etapa_4_Certificados_Dominios.md
│   └── Etapa_4_Certificados_Dominios.yaml
├── 05_Configuraciones_Perfiles/
│   ├── Etapa_5_Configuraciones_Perfiles.md
│   └── Etapa_5_Configuraciones_Perfiles.yaml
├── 06_Servicio_Diagnostico/
│   ├── Etapa_6_Servicio_Diagnostico.md
│   └── Etapa_6_Servicio_Diagnostico.yaml
└── 07_Auditoria_Tecnica_Final.md
```

## 3. Estado de las etapas

    N.º Etapa                                   Estado
  ----- --------------------------------------- --------------------
      1 Menú principal y organización general   **Aprobada (1.2)**
      2 Gestión de protocolos y conexiones      **Aprobada (1.3)**
      3 Gestión de usuarios                     **Aprobada (1.2)**
      4 Certificados SSL/TLS y dominios         **Aprobada**
      5 Configuraciones, perfiles y respaldos   **Aprobada**
      6 Servicio, diagnóstico y mantenimiento   **Aprobada (1.2)**

## 4. Documentos por etapa

-   Etapa 1: `01_Menu_Principal/Etapa_1_Menu_Principal.md` y `.yaml` ---
    menú, encabezado, navegación, administración y desinstalación.
-   Etapa 2: `02_Protocolos_Conexiones/Etapa_2_Protocolos.md` y `.yaml` --- conexiones técnicas separadas de identidades y asociaciones.
-   Etapa 3: `03_Gestion_Usuarios/Etapa_3_Usuarios.md` y `.yaml` --- identidades globales y asociaciones de acceso.
-   Etapa 4 (rev. 1.1): `04_Certificados_Dominios/Etapa_4_Certificados_Dominios.md`
    y `.yaml`.
-   Etapa 5:
    `05_Configuraciones_Perfiles/Etapa_5_Configuraciones_Perfiles.md` y
    `.yaml`.
-   Etapa 6 (rev. 1.2): `06_Servicio_Diagnostico/Etapa_6_Servicio_Diagnostico.md` y
    `.yaml` --- tres módulos, cinco delimitaciones y 24 reglas
    transversales aprobadas.

## 5. Delimitaciones generales aprobadas

1.  Xray/manager en Etapa 1 \[8\]; seguridad y mantenimiento general del
    SO en Etapa 6.
2.  Etapa 4 es propietaria del historial de renovaciones de certificados; Etapa 5 es propietaria de sus historiales. Etapa 6 centraliza consulta, filtro, exportación, administración y limpieza sin duplicar almacenamiento.
3.  Activar perfil (Etapa 5) no es recargar configuración (Etapa 6).
4.  Tareas comparten planificador, pero cada etapa conserva su
    responsabilidad.
5.  Desinstalación solo en Etapa 1 \[8\], mediante una única entrada: \[5\] Desinstalar componentes; el alcance permite Xray-core, administrador o ambos.
6.  Etapa 2 administra conexiones técnicas; Etapa 3 administra identidades globales y asociaciones de acceso. Una conexión puede tener varias asociaciones y una identidad puede acceder a varias conexiones. En WireGuard, una identidad puede tener varios peers; eliminar una asociación elimina solo su peer y eliminar la identidad elimina todos sus peers.

## 6. Convenciones

Cada etapa aprobada tendrá Markdown explicativo y YAML estructurado
sincronizados. Registrar revisiones, distinguir aprobado de pendiente y
recordar que documentación no equivale a implementación.

## 7. Orden de avance

1.  Menú principal.
2.  Protocolos y conexiones.
3.  Usuarios.
4.  Certificados y dominios.
5.  Configuraciones, perfiles y respaldos.
6.  Servicio, diagnóstico y mantenimiento.

Las seis etapas están aprobadas. La implementación del código se
abordará después de revisar la coherencia global y resolver los puntos
técnicos pendientes.

## 8. Estado de la auditoría técnica complementaria

La auditoría técnica complementaria ha aprobado los puntos 1--113, con
las siguientes salvedades expresas:

- Punto 55: autenticidad mediante firmas digitales, pospuesto por ahora.
- Punto 61: frecuencia de consulta de estadísticas/API, omitida por ahora.
- Punto 114: integridad y protección frente a manipulación, omitido por ahora.
- Los puntos 110--113 corresponden al cierre e integración del subsistema
de instancias y a revisiones transversales de seguridad, aprobados a nivel
de diseño.

Estas aprobaciones describen requisitos y decisiones de diseño; no
significan que estén implementados ni que las pruebas se hayan ejecutado.
La revisión final de coherencia y viabilidad se completó. El resultado y las
condiciones de implementación están documentados en
`07_Auditoria_Tecnica_Final.md`. La auditoría de diseño queda cerrada con
condiciones explícitas; esto no equivale a implementación ni a pruebas reales.

## 9. Informe final de auditoría

`07_Auditoria_Tecnica_Final.md` contiene los tres trabajos finales: auditoría
de coherencia entre etapas, evaluación de viabilidad técnica y registro de
pendientes/criterios de implementación. Incluye las restricciones oficiales
de Xray para API, estadísticas, protocolos y transportes.

**Resultado:** aprobada con condiciones y pendientes explícitos. Los puntos
55, 61 y 114 permanecen pospuestos u omitidos, según lo acordado; no se
consideran aprobados ni implementados.