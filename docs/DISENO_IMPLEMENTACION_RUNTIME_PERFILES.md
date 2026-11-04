# Diseño e implementación inicial — candidatos runtime mediante perfiles

**Fecha:** 2026-11-03
**Rama:** `design/user-identity-association-v1`
**Estado:** componente de staging implementado y probado en aislamiento; integración con perfiles y activación runtime pendientes.

## 1. Decisión normativa

Se eligió la opción A: respetar estrictamente la normativa aprobada. La activación de Xray debe pertenecer al flujo de cambio de perfil activo definido en la Etapa 5. Las conexiones independientes no constituyen una vía alternativa de activación.

Consecuencias:

- La conexión live `Prueba-VLESS-WS-Real` permanece `draft`, `runtime_applied=false`.
- No se implementa un comando ni una opción de menú que publique directamente una conexión independiente.
- El candidato runtime debe tener procedencia de un perfil y una revisión concretos.
- La infraestructura de staging puede desarrollarse antes del gestor de perfiles, pero no equivale a activación ni modifica el archivo usado por el servicio.

## 2. Hallazgo de arquitectura

La inspección del árbol `modules/`, `scripts/` y `config/` no encontró implementación funcional de perfiles: no hay módulo, menú ni registro operativo de perfiles. `install.sh` prepara el directorio `/var/lib/xray-manager/profiles`, pero eso no constituye un gestor.

Los adaptadores VLESS y VMess existentes generan configuraciones Xray a partir de modelos y opciones de conexión. No implementan la composición completa de una versión de perfil ni el flujo de activación de Etapa 5.

Por ello, no se debe conectar todavía el staging a una conexión concreta ni publicar un archivo runtime sin tener primero el modelo de perfil, su versionado y su validación integral.

## 3. Flujo técnico objetivo

1. Seleccionar perfil y revisión.
2. Obtener una instantánea coherente de la configuración del perfil, conexiones, usuarios/asociaciones y referencias de certificados autorizadas.
3. Construir una configuración Xray completa en staging privado.
4. Validar sintaxis/estructura y referencias del modelo.
5. Validar con el binario Xray instalado usando `xray run -test -config`.
6. Almacenar el candidato inmutable vinculado a `profile_id` y `profile_revision`, con SHA-256 y manifiesto.
7. En una fase posterior, el flujo de Etapa 5 podrá publicar atómicamente el candidato aprobado, conservar la versión anterior y verificar el estado aplicado.
8. Sólo después de la autorización operativa correspondiente se preparará/iniciará el servicio o se cambiará su estado.

La publicación, el arranque, el autostart y la exposición de red son operaciones separadas. La validación de un candidato no prueba que Xray esté ejecutándolo.

## 4. Componente implementado

Archivo: `scripts/xray_runtime_candidates.py`
Prueba: `tests/xray_runtime_candidates.sh`

Comando interno:

```bash
python3 scripts/xray_runtime_candidates.py stage \
  --candidate /ruta/candidato.json \
  --xray-binary /usr/local/bin/xray \
  --store /var/lib/xray-manager/runtime/candidates \
  --profile-id profile-id \
  --profile-revision revision-id
```

La interfaz es una primitiva técnica, no una opción del menú de usuario ni una ruta para activar conexiones independientes.

### 4.1 Controles

- Lee el candidato mediante descriptor `O_NOFOLLOW`; exige archivo regular, un solo hardlink y tamaño entre 1 byte y 16 MiB.
- Comprueba JSON objeto y que `inbounds` y `outbounds` sean arreglos.
- Rechaza symlinks en los componentes de las rutas y tokens de perfil/revisión con traversal.
- Crea almacén privado con modo 0700; bloqueo root-local 0600.
- Escribe configuración y manifiesto con modo 0600.
- Valida con Xray exactamente los bytes que se almacenarán, no vuelve a leer el archivo fuente. Esto evita una sustitución TOCTOU entre la lectura y la validación.
- Timeout de validación configurable entre 1 y 120 segundos (20 por defecto).
- El manifiesto registra perfil, revisión, tamaño, SHA-256, resultado JSON/Xray, binario usado y fecha UTC. No copia salida de error de Xray, para evitar filtrar valores sensibles.
- No sobrescribe una revisión ya almacenada. El staging se construye en directorio temporal privado y se publica mediante rename dentro del mismo filesystem.
- Sincroniza archivos y directorios antes de informar éxito.

### 4.2 Ubicación y permisos

Por defecto:

```text
/var/lib/xray-manager/runtime/candidates/
└── <profile_id>/
    └── <profile_revision>/
        ├── config.json   root:root 0600
        └── manifest.json root:root 0600
```

Directorios 0700. La ruta puede sustituirse para pruebas mediante `XRAY_RUNTIME_CANDIDATES_DIR`; el binario mediante `XRAY_RUNTIME_BINARY`.

### 4.3 Resultado

El comando informa `status=STAGED`, `runtime_published=false` y `service_started=false`. Estos campos son deliberados: este componente no escribe `/etc/xray/config.json`, no crea la unidad systemd, no crea la cuenta de servicio, no inicia Xray ni habilita autostart.

## 5. Pruebas

La prueba `tests/xray_runtime_candidates.sh` usa un binario Xray simulado y un directorio temporal. Cubre:

- staging correcto, manifiesto y hash;
- permisos privados de archivos y directorios;
- no sobrescritura de una revisión existente;
- JSON inválido;
- rechazo por parte del validador Xray;
- symlink, hardlink y traversal.

La prueba no usa perfiles reales ni toca rutas runtime del sistema. No demuestra todavía compatibilidad integral de un perfil real ni aplicación efectiva del servicio.

## 6. Pendientes antes de activar

1. Implementar el modelo/almacén/versionado de perfiles conforme a Etapa 5.
2. Implementar la composición integral de VLESS, VMess y demás modalidades aprobadas, usuarios/asociaciones y referencias TLS, con políticas explícitas para protocolos no soportados.
3. Establecer una instantánea coherente y bloqueos compartidos para impedir que cambien perfiles, conexiones o usuarios durante la construcción.
4. Integrar validación estática, validación nativa Xray, informes e historial.
5. Diseñar publicación runtime atómica con backup/rollback verificado y detección de cambios externos.
6. Integrar el paso de publicación exclusivamente en el flujo de cambio de perfil activo de Etapa 5.
7. Verificar estado aplicado sin confundir candidato, archivo publicado y configuración realmente ejecutada.

## 7. Límites operativos vigentes

Durante este trabajo no se ejecutó `xray_service_prepare`, no se creó `xray.service`, no se creó usuario/grupo Xray, no se escribió `/etc/xray/config.json`, no se inició ni habilitó Xray, no se abrió el puerto 10001 y no se modificó firewall, certificados ni reglas de red. No se hizo prueba de cliente externa/WAN.

No se modificó `Xray-Normativa/` ni `main`. No se hizo commit, push ni sincronización GitHub.

## 8. Endurecimiento y aislamiento de pruebas

- El staging exige ejecución como root.
- El almacén y los directorios de perfil deben ser directorios reales propiedad de root; se normalizan a 0700.
- El archivo de bloqueo debe ser regular, propiedad de root y sin hardlinks; modo 0600.
- El binario Xray debe ser regular, root-owned, sin hardlinks, ejecutable y no modificable por grupo/otros.
- Si el proceso termina abruptamente con SIGKILL durante staging, puede quedar un directorio temporal oculto .candidate-* dentro del directorio de perfil. Permanece privado y no se considera una revisión publicada. No se implementó limpieza automática heurística; deberá abordarse con una recuperación coordinada y pruebas específicas.
- Se corrigió el aislamiento de tests/users.sh: sus rutas de conexiones, usuarios y lock ahora se fijan mediante variables de entorno antes de cargar módulos, evitando que la recarga del módulo apunte al registro live de la VPS.

### Validación adicional con Xray instalado

Además del binario simulado usado por la prueba automatizada, se ejecutó una configuración sintética temporal con el binario real instalado en /usr/local/bin/xray (Xray-core 26.10.31). La operación terminó en STAGED y confirmó runtime_published=false y service_started=false. El directorio temporal se eliminó al finalizar. No se usó una configuración de perfil ni una conexión live.

## 9. Verificación final registrada

- tests/*.sh: 50/50 PASS.
- Python AST: 17/17 PASS.
- bash -n: todos los archivos shell del proyecto PASS.
- ShellCheck y shfmt: prueba focal nueva PASS.
- git diff --check: PASS.
- Xray-core 26.10.31 real validó un candidato sintético temporal; resultado STAGED. No hubo publicación runtime ni arranque.
- 14/14 archivos normativos comparados coinciden con la copia maestra; README.md es auxiliar no normativo.

## 10. Publicación y estado de continuidad

El propietario autorizó la publicación de este diseño junto con la primitiva, la prueba focal y los registros de continuidad en la rama `design/user-identity-association-v1`. La exclusión de `scripts/__pycache__/` es intencional: ese directorio es un artefacto local y no forma parte del código fuente.

La publicación documental/código no cambia los límites de las secciones anteriores: no existe todavía gestor de perfiles, no hay publicación runtime y no se ha iniciado Xray. La conexión live de prueba sigue en borrador. Etapa 2 permanece ABIERTA.
