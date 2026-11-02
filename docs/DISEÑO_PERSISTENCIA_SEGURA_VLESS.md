# Diseño de persistencia segura de configuraciones VLESS

**Proyecto:** Xray Core Manager
**Fecha:** 2026-11-02
**Estado:** diseño técnico elaborado; pendiente de aprobación antes de implementar
**Base:** Etapa 2, decisión complementaria de 2026-11-02, modelo neutral VLESS y adaptador Xray-core 26.10.31.

## 1. Objetivo y alcance

Permitir guardar y recuperar la configuración de una conexión VLESS sin volver a solicitar todos sus parámetros después de reiniciar el Manager, protegiendo los secretos en reposo y conservando la separación entre definición de conexión, opciones específicas, secretos, configuración Xray generada y estado de aplicación al runtime.

Este diseño no activa conexiones ni autoriza todavía listeners, firewall, certificados de producción, rollback transaccional o despliegue runtime.

## 2. Hallazgos del estado actual

1. config/paths.sh define /var/lib/xray-manager como directorio persistente.
2. install.sh crea los directorios del Manager con root:root y modo 0700; los registros JSON usan modo 0600.
3. modules/connections.sh conserva el catálogo en connections.json.
4. lib/json_store.sh ofrece reemplazo atómico de JSON con fsync y renombrado en el mismo directorio.
5. Usuarios y conexiones comparten /run/xray-manager/integrity.lock.
6. El asistente VLESS actual genera opciones/configuración temporales y no las persiste.
7. **Riesgo que debe corregirse:** la clave privada REALITY se pasa hoy a jq con --arg private_key "$reality_private". Los argumentos de procesos pueden ser visibles temporalmente en /proc y herramientas de inspección. La siguiente implementación no debe pasar secretos en argumentos, variables de entorno ni logs.

## 3. Arquitectura propuesta

### 3.1 Separación de datos

Mantener connections.json como catálogo e índice de conexiones. No incluir secretos ni configuración Xray completa allí.

Añadir estas ubicaciones:

| Ruta | Contenido | Permisos |
|---|---|---|
| /var/lib/xray-manager/connections/configurations/ | Opciones no secretas por conexión, JSON versionado | Directorio 0700, archivos 0600 |
| /var/lib/xray-manager/secrets/ | Cargas cifradas de secretos por conexión | Directorio 0700, archivos 0600 |
| /etc/xray-manager/keys/ | Clave maestra local de cifrado | Directorio 0700, clave 0600 root:root |
| /run/xray-manager/ | Material descifrado y configuración de trabajo efímera | Directorio 0700; archivos 0600 |

Los IDs de conexión y nombres de archivo se validarán contra una lista estricta de caracteres permitidos. No se aceptarán rutas construidas desde entradas sin validar ni enlaces simbólicos.

### 3.2 Catálogo de conexiones

connections.json seguirá guardando metadatos, por ejemplo:

- id, name, protocol_id, port, max_users;
- state (draft y estados posteriores definidos);
- runtime_applied;
- configuration_schema_version;
- configuration_ref y secret_ref opacos;
- marcas de tiempo.

No se guardarán en él claves privadas, contraseñas ni contenido completo de xray.json.

### 3.3 Configuración no secreta

Un archivo por conexión guardará el esquema neutral y las opciones no secretas:

- schema_version;
- connection_id;
- protocol, mode_id, transport, security;
- listen_address, listen_port;
- transport_options (path, modo XHTTP, nombre de servicio gRPC);
- tls con referencias de certificado y clave, no el contenido de la clave privada TLS.

El esquema será versionado y validado estrictamente. El adaptador seguirá siendo la única capa que transforma el modelo neutral a JSON de Xray.

### 3.4 Secretos cifrados

Para esta VPS Ubuntu/Debian se propone cifrado autenticado AES-256-GCM mediante la biblioteca Python cryptography, presente en el entorno auditado (41.0.7), pero cuya dependencia todavía debe formalizarse en el instalador.

Cada registro cifrado contendrá como mínimo:

- versión de formato;
- algoritmo;
- nonce aleatorio único de 96 bits;
- ciphertext;
- tag de autenticación (incluido por AES-GCM);
- identificador de conexión como contexto autenticado, no como secreto.

La clave maestra será aleatoria de 256 bits, generada con un CSPRNG, almacenada fuera del repositorio en /etc/xray-manager/keys/, propiedad root:root, modo 0600. Nunca se incluirá en Git ni en el archivo de configuración de conexión.

Se usará el ID de conexión y la versión de esquema como AAD (Additional Authenticated Data), para impedir que un blob cifrado se intercambie silenciosamente entre conexiones o contextos.

La carga secreta inicial incluirá la clave privada REALITY. Otros secretos de protocolos futuros podrán usar el mismo almacén con un esquema tipado, sin reutilizar nonce con la misma clave.

**Límite de seguridad:** el cifrado en reposo protege ante exposición aislada de archivos, copias de datos o respaldos que no incluyan la clave maestra. No protege frente a un atacante que ya controle root en la VPS y pueda leer simultáneamente la clave y los datos. Se recomienda cifrado de disco completo en el host cuando el proveedor lo permita.

## 4. Gestión de claves y recuperación

- La clave maestra se crea una sola vez; la operación será idempotente y no sobrescribirá una clave existente.
- Si la clave falta, está dañada o no puede leerse, el Manager fallará de forma cerrada: no regenerará otra automáticamente ni sobrescribirá blobs existentes.
- La rotación futura requerirá descifrar/verificar cada blob con la clave anterior, cifrar con una nueva clave y verificar antes de sustituir; mantener un respaldo de recuperación fuera del servidor.
- Los respaldos deberán tratar los blobs cifrados y la clave maestra como activos separados. Nunca incluir la clave maestra en el mismo respaldo ordinario sin cifrado adicional y control de acceso independiente.
- El procedimiento de recuperación deberá probarse en una VPS limpia antes de declarar la función lista para producción.

## 5. Flujo de guardado

1. Validar que el ID existe y que la conexión sigue en estado draft.
2. Adquirir el bloqueo de integridad compartido.
3. Validar esquema y opciones con el modelo neutral/adaptador; comprobar rutas TLS sin copiar claves privadas.
4. Recibir los secretos por entrada oculta o descriptor de archivo, nunca como argumento de proceso ni variable de entorno.
5. Cifrar el secreto en memoria con AES-256-GCM y nonce nuevo.
6. Escribir blob cifrado y configuración en temporales dentro de sus respectivos directorios, modo 0600; validar, hacer fsync y sustituir atómicamente.
7. Actualizar el catálogo con referencias y versión de esquema usando json_store_commit.
8. Si falla la actualización del catálogo, eliminar los artefactos nuevos que no estén referenciados y conservar la versión anterior.
9. Liberar el bloqueo y limpiar memoria/temporales en la medida que Bash/Python lo permitan.

La operación será idempotente por versión/revisión de configuración y tendrá recuperación ante interrupción. No se marcará la conexión como activa.

## 6. Flujo de lectura y generación

1. Comprobar permisos, propietario, tipo de archivo, ausencia de symlinks y referencias consistentes.
2. Adquirir el bloqueo apropiado y leer los archivos versionados.
3. Descifrar el blob en memoria; autenticar GCM y AAD antes de usar el contenido.
4. Crear un directorio de trabajo privado bajo /run/xray-manager (tmpfs en Ubuntu habitual; comprobarlo en runtime), modo 0700.
5. Escribir opciones completas solo en archivos 0600 dentro de ese directorio efímero.
6. Ejecutar el adaptador y xray run -test sin imprimir secretos ni el JSON completo en logs.
7. Eliminar el directorio temporal incluso ante error/señal; no persistir el JSON final en esta fase.

La configuración de runtime que se implemente más adelante necesitará un ciclo de vida propio y coordinación con el servicio Xray. No forma parte de este diseño de persistencia.

## 7. Certificados TLS

En esta primera iteración se almacenarán rutas de certificado y clave TLS, no se copiará automáticamente material privado del sistema.

Validaciones mínimas:
- rutas absolutas y canónicas;
- archivos regulares, legibles por el proceso que valida/aplica;
- rechazo de enlaces simbólicos y rutas fuera de ubicaciones permitidas según política;
- comprobar correspondencia certificado/clave y vigencia antes de aplicar.

La gestión/renovación de certificados y la importación segura de claves TLS se diseñarán como componente separado. El usuario será responsable de la rotación externa mientras se use referencia por ruta.

## 8. Errores, integridad y auditoría

- No mostrar ni registrar secretos, ciphertext completo, clave maestra o configuración sensible.
- Los logs solo registrarán ID de conexión, operación, resultado, versión de esquema y código de error.
- Error de descifrado, tag GCM inválido, archivo truncado, permisos incorrectos o referencia ausente: fallar de forma cerrada y no generar runtime.
- Detectar archivos huérfanos y referencias rotas con una herramienta de diagnóstico; no borrarlos automáticamente.
- Usar bloqueo compartido y operaciones atómicas; evitar escrituras concurrentes que pierdan cambios.
- Aplicar límites de tamaño a JSON y secretos para evitar consumo de memoria arbitrario.

## 9. Pruebas de aceptación requeridas

1. Guardar y recuperar cada modalidad VLESS sin pérdida de opciones.
2. Verificar que la clave REALITY no aparece en ps, /proc/*/cmdline, entorno, logs, catálogo ni configuración no secreta.
3. Verificar permisos 0700/0600, propietario y rechazo de symlinks.
4. Verificar descifrado correcto y fallo ante nonce/tag/AAD alterados.
5. Verificar que una clave maestra ausente/corrupta no se regenera ni destruye datos.
6. Simular fallo entre escritura de blob, configuración y actualización del catálogo; comprobar recuperación y ausencia de referencias parciales.
7. Probar concurrencia entre cambios de usuarios/conexiones/configuración.
8. Reiniciar el proceso/host y recuperar configuración.
9. Probar backup y restore en VPS aislada sin incluir la clave maestra en el respaldo ordinario.
10. Verificar que todas las operaciones mantienen state=draft y runtime_applied=false.
11. Confirmar que ningún test inicia listeners, cambia firewall o aplica el runtime.

## 10. Implementación por incrementos

**P1 — Infraestructura criptográfica**
- formalizar e instalar python3-cryptography;
- módulo de clave maestra, cifrado/descifrado AES-GCM y validación de permisos;
- pruebas unitarias y de manipulación de blobs.

**P2 — Almacén de configuración**
- esquemas versionados;
- guardado/lectura atómica con bloqueo;
- referencias en catálogo y limpieza controlada de huérfanos.

**P3 — Integración del asistente VLESS**
- reemplazar la generación efímera actual por guardado persistente;
- corregir la exposición de secretos vía argumentos jq --arg;
- recuperar opciones guardadas y generar preview temporal;
- mantener borradores sin activar.

**P4 — Backup/restore y recuperación**
- respaldo separado de blobs cifrados;
- exportación/importación protegida de clave con procedimiento explícito;
- prueba de recuperación en VPS aislada.

Cada incremento tendrá pruebas, actualización de continuidad y sincronización de la rama autorizada. No se modificará main.

## 11. Decisiones que requieren aprobación antes de implementar

1. Aprobar AES-256-GCM con python3-cryptography y clave maestra local root-only.
2. Aprobar separar configuración no secreta y secretos cifrados en archivos distintos.
3. Aprobar conservar las claves TLS como referencias a archivos externos en esta primera iteración.
4. Aprobar que la pérdida de la clave maestra implique bloqueo seguro y restauración desde respaldo de recuperación, nunca regeneración automática.
5. Aprobar el alcance P1–P4, manteniendo toda conexión como draft hasta una etapa posterior de aplicación transaccional.
