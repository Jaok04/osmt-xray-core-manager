# Implementación B1-A / B1-B — preparación de servicio e integridad Xray

**Fecha:** 2026-11-05
**Estado:** IMPLEMENTADO, VERIFICADO, AUDITADO, ACEPTADO, PUBLICADO y SINCRONIZADO en la rama autorizada.
**Base Git:** `fb5010c7f6bd19aed279eb42d1ae29e4a8050530`.

## 1. B1-B — integridad de la instalación

Nuevo `scripts/xray_install_integrity.py`:

- subcomandos `record` y `verify`;
- valida que binario y geodata sean archivos regulares, sin symlinks en sus rutas, propiedad `root:root` y modos 0755/0644;
- consulta la versión ejecutada del binario y la compara con la versión del manifiesto;
- calcula y compara SHA-256 del binario, `geoip.dat` y `geosite.dat`;
- valida schema exacto, gestor, arquitectura, rutas y SHA-256 del paquete;
- exige manifiesto `root:root 0600` y directorio padre `root:root 0700`;
- crea el manifiesto en un temporal privado, sincroniza archivo y directorio y publica mediante `os.replace`.

Integración en `modules/xray_admin.sh`:

- cada instalación/actualización/reparación exitosa registra el manifiesto después de reemplazar y validar los tres artefactos;
- update de la misma versión solo es no-op después de verificar manifiesto y hashes;
- update/reinstall rechazan instalaciones heredadas sin manifiesto o alteradas;
- repair permanece como ruta de recuperación explícita;
- install rechaza geodata/manifiesto huérfanos cuando falta el binario;
- el respaldo previo incluye el manifiesto; rollback restaura el manifiesto previo o retira el nuevo si no había uno.

`install.sh` fija la ruta del manifiesto usando el prefijo de instalación, de modo que los despliegues aislados no escriban fuera de su fixture.

## 2. B1-A — preparación desde el administrador

En `modules/main_menu.sh` se añade [7] Preparar servicio (verifica integridad) al submenú Administración de Xray-core. Las opciones [1]–[6] permanecen iguales.

La acción `xray_admin_prepare_service_menu_action`:

1. verifica el manifiesto y los hashes;
2. muestra el alcance de preparación;
3. exige confirmación;
4. llama a `xray_service_prepare`;
5. no inicia ni habilita el servicio.

En `modules/xray_service.sh`, `xray_service_require_inactive` comprueba al comienzo que el servicio no esté activo; si está activo, aborta antes de modificar identidad, directorios o unidad. Se conserva la comprobación posterior existente como protección ante cambio de estado durante la operación.

## 3. Archivos

- Nuevo: `scripts/xray_install_integrity.py`.
- Nuevo: `tests/xray_admin_prepare_service.sh`.
- Modificados: `modules/xray_admin.sh`, `modules/main_menu.sh`, `modules/xray_service.sh`, `install.sh`.
- Modificados: `tests/xray_admin.sh`, `tests/xray_service.sh`, `tests/stage1_menu.sh`.
- Documentación: decisión, implementación, auditoría y documentos de continuidad B1.

## 4. Límites observados

No se ejecutó `xray_admin_prepare_service_menu_action` contra el sistema real. No se instaló/reparó Xray real, no se creó usuario/grupo real, no se escribió unidad real, no se invocó el binario real systemctl (el estado se simuló con un stub), no se tocó runtime, certificados reales, DNS, firewall, puertos, red ni dependencias. Todas las pruebas de preparación usan rutas temporales y mocks.

La VPS de desarrollo contiene un Xray 26.10.31 preexistente sin manifiesto administrado; por diseño, la nueva opción [7] lo trataría como **no verificado** y no prepararía el servicio hasta una reparación explícita y autorizada.


### Serialización y protección de servicio activo

La función pública xray_service_prepare serializa la operación mediante el bloqueo de ciclo de vida compartido y delega en xray_service_prepare_locked. Respeta XRAY_MANAGER_LIFECYCLE_LOCK_HELD=1 para el flujo del instalador. El guard xray_service_require_inactive se ejecuta al inicio de la preparación y aborta si el servicio está activo. La comprobación existente posterior se conserva como protección adicional ante una transición concurrente.

## Addendum de publicación — 2026-11-05

El propietario aceptó formalmente B1-A/B1-B y autorizó su publicación. Commit funcional: c8cd20c2a576fb1926fdcf11945cd75cf1c4211c (feat(xray): verify installation and prepare service). Push fast-forward confirmado a design/user-identity-association-v1; HEAD local y remoto coinciden tras la verificación. La publicación no autoriza operaciones live.
