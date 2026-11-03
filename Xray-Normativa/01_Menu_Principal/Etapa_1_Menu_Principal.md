# Xray Manager --- Etapa 1: Menú principal y organización general

**Versión:** 1.2\
**Estado:** APROBADA\
**Aprobación original:** 30/10/2026\
**Revisión:** 31/10/2026

## 1. Objetivo

Definir el menú principal, encabezado, navegación y responsabilidades
generales. Especificación funcional; no implementación.

## 2. Menú principal aprobado

``` text
╔══════════════════════════════════════════════════════╗
║                    MENÚ PRINCIPAL                    ║
╠══════════════════════════════════════════════════════╣
║  ADMINISTRACIÓN                                      ║
║  [1] Gestión de protocolos y conexiones             ║
║  [2] Gestión de usuarios                            ║
║  [3] Certificados SSL/TLS y dominios                ║
║  CONFIGURACIÓN                                       ║
║  [4] Configuraciones, perfiles y respaldos          ║
║  SISTEMA                                             ║
║  [5] Gestión del servicio Xray-core                 ║
║  [6] Diagnóstico y registros                         ║
║  [7] Seguridad, red y mantenimiento                 ║
║  [8] Configuración del sistema y administrador      ║
║  INFORMACIÓN                                         ║
║  [9] Información y ayuda                             ║
║  [0] Salir                                           ║
╚══════════════════════════════════════════════════════╝
```

El encabezado muestra IP pública si está disponible, versión de Xray,
estado del servicio, estado de inicio automático, perfil activo y
fecha/hora local. Los datos no disponibles no impiden mostrar el menú.

## 3. Responsabilidades

-   \[1\] Protocolos y conexiones.
-   \[2\] Usuarios y asociaciones.
-   \[3\] Certificados SSL/TLS y dominios.
-   \[4\] Configuraciones, perfiles, respaldos y restauraciones.
-   \[5\] Control del servicio Xray-core.
-   \[6\] Diagnóstico y registros.
-   \[7\] Seguridad, red y mantenimiento.
-   \[8\] Instalación, actualización, reparación, dependencias
    específicas, preferencias y desinstalación de
    Xray-core/administrador.
-   \[9\] Información y ayuda.

## 4. Opción \[8\] --- Configuración del sistema y administrador

``` text
[8] CONFIGURACIÓN DEL SISTEMA Y ADMINISTRADOR
├── [1] Administración de Xray-core
│   ├── [1] Instalar Xray-core
│   ├── [2] Actualizar Xray-core
│   ├── [3] Consultar versión instalada
│   ├── [4] Consultar última versión disponible
│   ├── [5] Reinstalar Xray-core
│   └── [6] Reparar instalación
├── [2] Dependencias del sistema
├── [3] Configuración del administrador
├── [4] Información de instalación
├── [5] Desinstalar componentes
└── [0] Volver
```

### 4.1 Delimitación de paquetes

Etapa 1 \[8\] administra Xray-core y las dependencias específicas del
administrador. Etapa 6 módulo 3 \[2\] administra actualizaciones de
seguridad del sistema operativo y \[7\] el mantenimiento general de
paquetes. Se comparte el mecanismo técnico de gestión de paquetes,
evitando gestores independientes.

### 4.2 Desinstalación

La desinstalación se realiza exclusivamente desde Etapa 1 \[8\]. Etapa 6
no tendrá una opción duplicada.

La opción única `[5] Desinstalar componentes` solicita el alcance:

- Solo Xray-core.
- Solo Xray Manager.
- Ambos componentes.

No existe una opción de desinstalación dentro de `[1] Administración de Xray-core`;
todas las variantes utilizan este único flujo.

Política de datos: - Conservar todos. - Eliminar todos. - Seleccionar
categorías: configuraciones Xray; perfiles y versiones actuales;
usuarios/asociaciones; conexiones; dominios; certificados/claves
privadas; respaldos; preferencias; registros e historiales.

Antes de borrar certificados o claves privadas se mostrará una
advertencia específica.

Respaldo previo: - Preguntar si desea crear un respaldo. - Si se
solicita, crearlo y verificarlo antes de cualquier eliminación
riesgosa. - Si falla la creación o verificación, cancelar la eliminación
que ponga datos en riesgo. - Ofrecer exportarlo fuera del servidor y
verificar la exportación antes de continuar. - Si se elige eliminar
todos los datos, también se eliminan respaldos existentes y el respaldo
creado durante el proceso. Una copia descargada externamente será la
única copia externa.

**Advertencia:** los historiales y registros excluidos de los respaldos
de Etapa 5 no se recuperan desde ellos: historial de
versiones/modificaciones de perfiles, historial de validaciones,
informes de restauración y registros técnicos.

Antes de ejecutar, mostrar alcance, categorías conservadas/eliminadas,
estado del respaldo/exportación y advertencias. Exigir confirmación
final explícita e irreversible.

## 5. Navegación y seguridad

Todos los submenús tienen `[0] Volver`; volver regresa al nivel
anterior. Errores no cierran el administrador. Operaciones destructivas
requieren confirmación. Salir requiere confirmación. Al volver al menú
principal se actualiza el encabezado.

## 6. Control de revisión

La revisión 1.1 incorpora el flujo único de desinstalación aprobado y la
delimitación de gestión de paquetes. La revisión 1.2 elimina la entrada
duplicada de desinstalación dentro de Administración de Xray-core y
conserva `[5] Desinstalar componentes` como punto único de acceso. No
implica implementación.