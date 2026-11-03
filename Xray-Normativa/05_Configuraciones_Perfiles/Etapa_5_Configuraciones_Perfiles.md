# ETAPA 5 — CONFIGURACIONES, PERFILES Y RESPALDOS

**Proyecto:** Xray Core Manager  
**Versión:** 1.0  
**Estado:** Aprobada — especificación funcional  
**Alcance:** configuraciones JSON, perfiles, activación, respaldos y restauración.

## 1. Objetivo

Definir las funciones para administrar configuraciones de Xray, validar archivos, mantener perfiles y versiones independientes, activar configuraciones con verificación real, y crear/gestionar/restaurar respaldos. Esta especificación es funcional; los mecanismos técnicos pendientes se decidirán antes de programar.

## 2. Menú principal aprobado

```text
╔══════════════════════════════════════════════╗
║       CONFIGURACIONES, PERFILES Y RESPALDOS ║
╠══════════════════════════════════════════════╣
║  CONFIGURACIONES                            ║
║  [1] Gestionar configuraciones de Xray      ║
║  [2] Validar archivos de configuración      ║
║  PERFILES                                   ║
║  [3] Gestionar perfiles                     ║
║  [4] Cambiar perfil activo                  ║
║  RESPALDOS                                  ║
║  [5] Crear respaldo                         ║
║  [6] Gestionar respaldos                    ║
║  [7] Restaurar respaldo                     ║
║  [0] Volver                                 ║
╚══════════════════════════════════════════════╝
```

Todos los submenús incluyen `[0] Volver`. Mostrar resultados antes de regresar; los errores no deben cerrar inesperadamente el gestor.

## 3. [1] Gestionar configuraciones de Xray

```text
[1] Ver configuración actual
[2] Crear configuración nueva
[3] Editar configuración
[4] Importar configuración desde archivo
[5] Exportar configuración
[6] Comparar configuraciones
[7] Eliminar configuración
[0] Volver
```

- **Ver:** mostrar inbounds, outbounds, routing, DNS, otras secciones, JSON completo e información del archivo. Solo lectura. Distinguir configuración guardada de configuración aplicada. La ausencia de configuración no bloquea el gestor.
- **Crear:** nombre único; partir de plantilla o archivo vacío. Permitir guardar como Borrador aunque esté incompleta o tenga errores. Guardar tras vista previa y confirmación. No activar ni reemplazar la configuración activa.
- **Editar:** edición guiada o JSON avanzado. Editar una versión Validada crea una nueva versión Borrador y conserva intacta la anterior. Mostrar diferencias. Fallar validación no destruye el Borrador ni la versión Validada anterior. Editar el archivo activo no cambia lo que ejecuta Xray; advertir posible diferencia entre guardado y aplicado. Cancelar descarta cambios no guardados.
- **Importar:** leer archivo sin modificarlo; comprobar sintaxis, estructura, parámetros requeridos, tipos, valores y compatibilidad detectable. Mostrar vista previa y solicitar nombre único. Crear configuración independiente, nunca activarla. Nombre duplicado: elegir otro o autorizar reemplazo explícito. Archivos incompletos/erróneos pueden guardarse como Borrador, nunca como Validada.
- **Exportar:** seleccionar una o varias configuraciones, destino y nombre. No modificar originales. Confirmar sobrescritura y verificar cada salida. Un fallo no detiene las demás exportaciones.
- **Comparar:** dos configuraciones; identificar iguales, diferentes, solo primera y solo segunda; agrupar por inbounds, outbounds, routing, DNS y otras secciones. Solo lectura.
- **Eliminar:** mostrar nombre, ruta y estado; no eliminar una configuración aplicada mientras siga en uso (activar otra primero); confirmar. Eliminar solo el elemento elegido, nunca perfiles/copias/respaldos relacionados. Ante error conservar registro.

### 3.1 Configuraciones independientes y de perfil

Hay dos clases: configuraciones independientes administradas en [1], y copias JSON independientes pertenecientes a perfiles. Crear perfil desde configuración independiente copia su JSON. No existe sincronización en ninguna dirección. Eliminar la fuente no elimina la copia del perfil. Las configuraciones independientes no son una vía alternativa de activación: se activa mediante perfiles.

## 4. [2] Validar archivos de configuración

```text
[1] Validar configuración guardada
[2] Validar archivo externo
[3] Validar configuración activa
[4] Ver último informe de validación
[5] Consultar historial de validaciones
[0] Volver
```

### 4.1 Validación estática

Comprobar sintaxis JSON, estructura Xray, parámetros requeridos, tipos/valores, compatibilidad con versión instalada y referencias/conflictos detectables. Es obligatoria para clasificar una versión como **Validada**. Informar correcto, advertencias y errores. No corregir, modificar ni aplicar.

- **Guardada:** seleccionar archivo y conservar informe asociado a esa versión.
- **Externa:** solicitar ruta legible; mismas comprobaciones, sin importar, modificar ni aplicar.
- **Activa:** identificar configuración usada por el servicio, comprobar servicio y comparar guardado/aplicado cuando sea posible. Si no se puede determinar, decirlo. No reiniciar ni modificar Xray.
- **Prueba de funcionamiento:** comprobación separada de si Xray puede cargar/usar la configuración sin sustituir la instancia en ejecución. Una configuración estáticamente válida puede fallar esta prueba. No asumir que es posible iniciar una segunda instancia del daemon; mecanismo seguro pendiente de diseño.
- **Informes:** consultar último informe e historial por archivo, fecha y tipo; inspeccionar errores/advertencias y comparar resultados. Conservarlos aunque la configuración sea modificada o eliminada. Solo lectura.

## 5. Estados y versiones

- **Borrador:** guardada, puede estar incompleta o contener errores.
- **Validada:** superó las comprobaciones estáticas obligatorias.
- **Aplicada:** se verificó que Xray realmente la ejecuta.
- **Anterior:** dejó de ser vigente, conserva metadatos históricos.

Los estados no son excluyentes: una versión puede ser Validada y Aplicada y posteriormente quedar Anterior. Editar una Validada crea un Borrador nuevo y conserva la Validada anterior. Un Borrador no puede activarse. La prueba de funcionamiento no sustituye validación estática.

## 6. [3] Gestionar perfiles

```text
[1] Crear perfil
[2] Consultar perfiles
[3] Modificar perfil
[4] Duplicar perfil
[5] Renombrar perfil
[6] Eliminar perfil
[0] Volver
```

- **Crear:** nombre único; desde cero, configuración independiente u otro perfil. Copiar JSON independientemente; validar si hay configuración; vista previa y confirmación. No activar automáticamente ni dejar registro parcial si falla.
- **Consultar:** listar nombre, activo/inactivo, configuración, fechas de creación/modificación y validación. Ver detalles/versiones. Indicar ausencia o errores de configuración. Solo lectura.
- **Modificar:** nombre, configuración, descripción/notas. Conservar versiones y crear nueva versión al cambiar configuración. Validar, mostrar diferencias y confirmar. Si está activo, advertir que guardar no aplica cambios. Fallo conserva versión anterior; cancelar descarta cambios no guardados.
- **Duplicar:** nombre único; copiar datos y configuración a una copia independiente; permitir editar nombre/descripción; validar y confirmar. Original intacto; no activar.
- **Renombrar:** modificar solo registro, no JSON; nombre único y confirmación. Si está activo, actualizar identificación sin cambiar runtime.
- **Eliminar:** mostrar perfil/configuración/estado y revisar dependencias. No eliminar perfil activo hasta activar otro. Confirmar. Eliminar solo registro del perfil, no JSON, configuraciones independientes ni respaldos.

Cada perfil tiene su propia copia JSON. Los cambios de un perfil no afectan otros ni la fuente independiente. Eliminar un perfil no elimina copias de otros. Mantener historial de versiones: conservar versiones anteriores, identificar última Validada, consultar/comparar, restaurar versión anterior creando una nueva versión (sin destruir historial) y aplicar retención configurable. Historial de versiones y modificaciones se conserva en gestor, pero no se respalda.

## 7. [4] Cambiar perfil activo

1. Listar perfiles e identificar el activo.
2. Seleccionar perfil destino.
3. Exigir configuración asociada y validación estática satisfactoria.
4. Mostrar perfil/versión anterior y nueva.
5. Confirmar.
6. Aplicar configuración a Xray.
7. Verificar que el servicio ejecuta realmente la nueva configuración.
8. Actualizar registro activo solo después de verificar.

Si falla, intentar restaurar configuración anterior. Si también falla la recuperación, informar estado real. Cancelar conserva perfil anterior.

Registro independiente: ID/nombre del perfil, versión aplicada, fecha/hora, último resultado, ruta JSON y estado del servicio. Detectar discrepancias entre perfil seleccionado, archivo guardado y runtime, reinicios externos y aplicaciones fallidas. Seleccionar o guardar no equivale a activar.

## 8. [5] Crear respaldo

Permitir seleccionar: configuraciones JSON independientes; perfiles y asociaciones (solo versión actual); registro de perfil activo; usuarios/identidades/asociaciones; preferencias del gestor; dominios; certificados y claves privadas solo con selección expresa. Permitir respaldo individual o completo. Solicitar destino/nombre, vista previa y confirmación. Crear y verificar integridad. No modificar originales. No detener/reiniciar Xray salvo necesidad informada previamente.

Credenciales y claves privadas excluidas por defecto; inclusión requiere selección, autorización y confirmación adicional. Informar fallos por elemento y nunca declarar completo un respaldo que omitió elementos solicitados. Incluir metadatos de versión del gestor, Xray y estructura.

**Excluir absolutamente todo historial de los respaldos:** historial de versiones y modificaciones de perfiles, historial de validaciones, informes de restauración y registros técnicos/logs. Los historiales permanecen en el gestor con sus propias políticas de retención. El respaldo contiene solo datos y estados actuales de los elementos seleccionados.

## 9. [6] Gestionar respaldos

```text
[1] Listar respaldos
[2] Consultar contenido de un respaldo
[3] Verificar integridad de un respaldo
[4] Exportar respaldo
[5] Eliminar respaldo
[0] Volver
```

- **Listar:** buscar directorios configurados; mostrar nombre, fecha/hora, tamaño, completo/parcial, ubicación e integridad conocida. Filtros por fecha/tipo/nombre. Estados válido, pendiente, dañado o inaccesible. Advertir ubicaciones inaccesibles.
- **Consultar:** metadatos (fecha, tipo, versión gestor/Xray, tamaño, ubicación) y categorías (configuraciones, perfiles, usuarios, certificados/dominios, preferencias y otros). No extraer/restaurar automáticamente. Ocultar secretos salvo autorización. Advertir contenido incompleto/ilegible.
- **Verificar:** existencia, lectura, formato, estructura, archivos internos, posibilidad de leer/extraer y checksums si existen. Resultado correcto/advertencia/error. No modificar/restaurar. Sin checksum no afirmar verificación criptográfica.
- **Exportar:** seleccionar uno/múltiples, verificar integridad, indicar destino/nombre y confirmar. Copiar y comparar salida con original. No modificar original. Confirmar sobrescritura. No exportar dañado como válido; continuar otros si uno falla.
- **Eliminar:** mostrar detalles, seleccionar y confirmar; eliminar solo respaldo seleccionado, nunca datos originales relacionados. Ante fallo conservar registro.

## 10. [7] Restaurar respaldo

### 10.1 Flujo general

Seleccionar respaldo; verificar integridad y compatibilidad gestor/Xray; mostrar contenido; elegir restauración completa o selectiva; detectar conflictos/incompatibilidades; previsualizar agregar/reemplazar/conservar/excluir/no restaurable; crear respaldo de seguridad del estado actual; verificar que se creó y puede leerse; confirmar explícitamente; restaurar; verificar y generar informe.

**Si no se puede crear y leer el respaldo de seguridad, cancelar toda la restauración sin modificar datos. No hay excepción.**

```text
[1] Restaurar respaldo completo
[2] Restaurar elementos específicos
[0] Volver
```

Completa: procesar todos los elementos compatibles incluidos, respetar exclusiones/conflictos; no borrar datos actuales ausentes del respaldo; no sobrescribir silenciosamente. Selectiva: categorías o elementos individuales; no seleccionados intactos; selección individual no se amplía a categoría completa; respaldo de seguridad de elementos afectados.

### 10.2 Políticas globales de conflicto

1. Preguntar siempre y decidir conflicto individual.
2. Reemplazar automáticamente después de confirmación global.
3. Conservar lo actual y restaurar solo lo ausente.

Políticas específicas prevalecen sobre global; global aplica donde no haya una específica. Mostrar políticas efectivas antes de confirmar.

### 10.3 Políticas por categoría

**Usuarios:** conservar; reemplazar; actualizar campos seleccionados (alias, credenciales, duración, expiración, tráfico, conexiones, estado); preguntar individualmente. Previsualizar nuevos, duplicados, actualizados y omitidos. Identidad global separada: conservar identidad y agregar asociaciones faltantes; reemplazar todas las asociaciones; o seleccionar asociaciones individualmente. No cambiar ID ni sustituirlo por alias. Si conexión está llena, rechazar asociación o reasignar a conexión compatible existente con capacidad; nunca aumentar límite automáticamente. Vista previa y confirmación; sin destino compatible/cupo, rechazar.

**Conexiones:** conservar, reemplazar completamente o actualizar campos seleccionados. Mostrar usuarios/asociaciones afectados; validar compatibilidad/cupo; no modificar usuarios automáticamente; confirmar y conservar anterior ante fallo.

**Dominios:** conservar, reemplazar todos los datos o actualizar campos seleccionados. Mostrar conexiones/certificados vinculados; no modificar automáticamente conexiones ni certificados.

**Certificados:** conservar, reemplazar o seleccionar individualmente. Validar vigencia, dominios, correspondencia certificado-clave y legibilidad. Claves privadas excluidas por defecto; selección, autorización y confirmación adicional. No modificar conexiones vinculadas; conservar anterior ante fallo.

**Preferencias del gestor:** conservar todas, reemplazar todas o seleccionar individualmente. Mostrar rutas, permisos, idioma, formato de fecha, colores y preferencias de respaldo. Validar, confirmar y prever recuperación.

### 10.4 Exclusiones y orden

Permitir excluir categorías o elementos; excluidos quedan intactos. Lo ausente del respaldo nunca elimina datos actuales.

Orden aprobado:
1. Preparar, leer y validar preferencias seleccionadas al inicio usando rutas/condiciones actuales, sin aplicarlas.
2. Dominios y certificados.
3. Configuraciones independientes.
4. Perfiles y configuraciones actuales.
5. Conexiones.
6. Usuarios, identidades y asociaciones.
7. Aplicar al final preferencias seleccionadas.
8. Verificación final.

Verificar que el gestor siga funcionando después de aplicar preferencias.

### 10.5 Estados y perfil activo restaurados

Conservar estado original: Borrador sigue Borrador; Validada sigue Validada solo si se verifica integridad y correspondencia con versión respaldada. Si no se verifica, no presentarla como Validada. Activar exige validación estática.

Los respaldos contienen solo versión actual de cada perfil, no historial de versiones/modificaciones. Si el respaldo identifica perfil activo, restaurar sus datos no lo activa ni sustituye automáticamente configuración en ejecución. Al terminar preguntar si desea activarlo; si acepta, ejecutar flujo normal de validación, aplicación y verificación.

### 10.6 Fallos e incompatibilidades

Fallo aislado: revertir elemento afectado. Mantener éxitos independientes si consistencia global se conserva; si se compromete, intentar rollback más amplio. Si rollback falla, informar exactamente elementos/estados afectados. No declarar éxito completo ante fallos.

Respaldo dañado: continuar solo con elementos cuya integridad pueda verificarse independientemente, con vista previa y confirmación. Si no hay recuperables, cancelar sin cambios y generar informe Fallido. Incompatibles pueden excluirse individualmente; continuar compatibles; nunca forzar incompatibles.

Resultados:
- **Exitoso:** todos los elementos seleccionados y compatibles restaurados.
- **Parcial:** algunos seleccionados restaurados y otros seleccionados rechazados/fallidos.
- **Fallido:** ningún elemento seleccionado restaurado.

Exclusiones voluntarias e incompatibles omitidos deliberadamente se reportan, pero no son fallos de ejecución.

## 11. Informes de restauración

Elegir: resumen solamente; informe detallado no conservado; informe detallado guardado en historial. Incluir resultado, elementos procesados, agregados/reemplazados/conservados/omitidos, incompatibilidades, errores, verificaciones y rollbacks.

Historial guardado: retención configurable por tiempo y máximo de registros; limpieza al iniciar gestor y después de guardar informe; eliminar uno, varios o todos con confirmación. Informes excluidos de respaldos.

## 12. Registros técnicos

Activación/desactivación configurable. Si está activo, registrar operaciones, rutas/elementos afectados, errores, rollbacks y fecha/hora. Nunca guardar credenciales ni claves privadas en texto plano.

Retención por tiempo y máximo de registros, independiente de informes; limpieza al iniciar gestor y después de generar nuevos logs. Funciones: ver recientes; filtrar fecha/operación/resultado/elementos/errores/rollbacks; exportar todos/filtrados/seleccionados TXT, JSON o CSV; eliminar uno/varios/todos con confirmación. No se requiere panel estadístico. Logs excluidos de respaldos.

## 13. Reglas generales

- Nunca sobrescribir silenciosamente.
- Vista previa y confirmación antes de restaurar.
- Respaldo de seguridad verificado obligatorio.
- Claves privadas requieren selección/autorización explícitas.
- Perfil restaurado no se activa automáticamente.
- Ausencia de elemento en respaldo no elimina datos actuales.
- Todo historial se excluye de respaldos.
- Verificar resultado real antes de declarar éxito.
- Informar fallos, reversiones y estado final.

## 14. Pendientes técnicos para implementación

Formato/empaquetado/versionado/checksums; método seguro de prueba runtime sin interferir instancia activa; aplicación/verificación de configuración; modelo interno de versiones/metadatos; rutas/permisos/protección de secretos; rollback por elemento/operación; almacenamiento de historiales/informes; limpieza por retención y cantidad máxima.

---

**Fin de la especificación funcional de la etapa 5.**