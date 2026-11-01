# Contraste GitHub — rama design/user-identity-association-v1

**Fecha:** 2026-11-01  
**Repositorio:** Jaok04/xray-core-manager  
**Rama remota:** design/user-identity-association-v1

## 1. Identidad remota confirmada

- HEAD: 3aeeb03cbb9f2bd5022b3f2312fd395acbc562e3
- Último commit: Include Stage 1 menu integration in smoke suite
- Fecha: 2026-11-01T19:19:29Z
- Comparación con main: 167 commits por delante y 0 por detrás.
- Merge base con main: 656ecedc506a94a6461aee296b20871d51a38bf3.

La rama existe y contiene el desarrollo de identidades/asociaciones v2, el selector de menú, el procedimiento de transición y sus pruebas. No está integrada en main.

## 2. Comparación de árboles

| Elemento | Rama GitHub | VPS: /opt/xray-manager |
|---|---:|---:|
| Archivos | 45 | 51 |
| Rutas remotas presentes localmente | 45 de 45 | — |
| Rutas remotas ausentes localmente | 0 | — |

Archivos presentes en el VPS que no existen en el árbol de esa rama:

- config/preferences.sh
- modules/admin_settings.sh
- modules/system_admin.sh
- tests/stage1_dependencies.sh
- tests/stage1_settings.sh
- scripts/__pycache__/users_v2_cutover.cpython-312.pyc (artefacto generado, no fuente)

La copia del VPS es una ampliación del árbol remoto en cuanto a rutas. Esto no demuestra por sí solo su ascendencia Git.

## 3. Diferencias de contenido relevantes

Los identificadores Git de blob calculados localmente no coinciden con los blobs de la rama remota en los archivos revisados.

| Archivo | Remoto | VPS |
|---|---:|---:|
| bin/xray-manager | 1.308 B | 1.494 B |
| config/paths.sh | 1.675 B | 1.827 B |
| modules/main_menu.sh | 8.710 B | 9.615 B |
| modules/xray_admin.sh | 11.716 B | 15.294 B |
| modules/uninstall.sh | 8.481 B | 16.359 B |
| tests/stage1_menu.sh | 1.715 B | 3.770 B |
| tests/uninstall.sh | 1.002 B | 8.075 B |

Diferencias funcionales confirmadas:

1. **Menú y desinstalación única.** La rama remota todavía conserva la ruta de desinstalación dentro del submenú de Administración de Xray-core; su prueba de menú espera esa llamada. La copia del VPS ya eliminó esa duplicidad y conserva el único acceso aprobado: opción 8 → opción 5.
2. **Dependencias y preferencias.** La rama remota no contiene los módulos de dependencias, configuración del administrador ni el archivo de preferencias. Sí existen en el VPS, con pruebas independientes.
3. **Administración de Xray-core.** La copia del VPS contiene una implementación más extensa de descarga verificada, extracción restringida, staging, respaldo y rollback.
4. **Desinstalación.** La copia del VPS incorpora alcance y categorías, respaldo verificado, exportación SSH/SCP con comprobación SHA-256, allowlist, validación de componentes simbólicos y coordinación con locks de usuarios/conexiones y Xray.
5. **Documentación.** Los documentos locales de implementación y punto de control todavía conservaban estados antiguos que marcaban dependencias y preferencias como pendientes. Se actualizan en esta revisión sin modificar la especificación funcional aprobada.

## 4. Límite de certeza sobre el VPS

/opt/xray-manager **no contiene un directorio .git**. Por ello no es posible obtener desde esa ruta git status, confirmar una rama local, saber si los cambios están staged/committed ni establecer la relación exacta de commits con el HEAD remoto. La comparación realizada es de árboles, hashes de contenido y comportamiento de los archivos examinados.

## 5. Decisión de trabajo

- No hacer pull, checkout, merge, commit ni push durante este contraste.
- Mantener la copia del VPS como fotografía de trabajo actual para cerrar Etapa 1, porque contiene los módulos y correcciones que faltan en el HEAD remoto.
- No tratarla como una rama Git sincronizada: primero habrá que recuperar/establecer metadatos Git de forma controlada y reconciliar los cambios locales con la rama remota.
- No hacer merge a main sin autorización.
- La referencia funcional continúa siendo Etapa 1 revisión 1.2 de la documentación aprobada del 31/10/2026; este contraste no altera esa especificación.
