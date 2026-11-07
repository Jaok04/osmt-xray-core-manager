# Instalador inicial — Fase A (Manager)

Estado: instalación Manager-only implementada; bootstrap privado de un solo archivo implementado y verificado mediante pruebas automatizadas. La ejecución live del nuevo flujo de GitHub con PAT queda pendiente de aceptación en una VPS limpia.

## Alcance

`install.sh` prepara únicamente Xray Core Manager en Ubuntu/Debian:

- si se ejecuta como archivo único, solicita un Fine-grained PAT de solo lectura o recibe `XRAY_MANAGER_GITHUB_TOKEN`;
- obtiene `install.sh`/helper y el snapshot de la rama `design/user-identity-association-v1` mediante GitHub API autenticada;
- fija el commit una sola vez, verifica el helper con SHA-256 y cada blob del snapshot contra el árbol Git antes de extraer;
- rechaza árboles truncados, symlinks, hardlinks, submódulos, rutas traversal, archivos faltantes/adicionales y modos no admitidos;
- no clona Git ni descarga historial; no instala `.git`;
- comprueba plataforma, privilegios y dependencias;
- instala solo los paquetes faltantes mediante `apt-get update` y `apt-get install`; nunca ejecuta `apt upgrade`;
- despliega el código verificado en `/opt/xray-manager` cuando el destino no existe;
- rechaza enlaces simbólicos en el destino y no sobrescribe una instalación de código preexistente distinta;
- crea directorios administrativos, datos, caché, logs y respaldos;
- crea preferencias iniciales y el catálogo vacío de conexiones si no existen;
- valida el JSON de conexiones existente y no lo reemplaza si es inválido;
- establece permisos `700` para directorios privados y `600` para archivos sensibles;
- registra el estado inicial en `/var/lib/xray-manager/state/install.json`.

## Exclusiones explícitas

Esta fase no instala Xray-core, no crea ni modifica `/etc/xray`, no crea `xray.service`, no crea usuario/grupo de servicio, no habilita ni inicia servicios y no inicializa ni migra `users.json`. Esas tareas pertenecen a las fases B y C, con la política aprobada de servicio instalado pero deshabilitado y detenido hasta que exista configuración válida.

## Uso

Para una VPS limpia y repositorio privado, seguir el bootstrap autenticado de `docs/INSTALACION_DESDE_VPS_LIMPIA.md`. No es necesario clonar el proyecto.

Desde el árbol completo ya descargado:

```bash
sudo ./install.sh --check
sudo ./install.sh --install
```

`--check` es de solo lectura y requiere el árbol completo del proyecto; un `install.sh` aislado debe ejecutarse con `--install` para que pueda descargarlo. `--install` requiere root. Si `/opt/xray-manager` ya existe y el instalador se ejecuta desde ese mismo directorio, conserva el código existente; si el destino existe pero el origen es distinto, aborta sin sobrescribirlo.

## Pruebas

`tests/install.sh` utiliza un prefijo temporal aislado y cubre despliegue, permisos, idempotencia, conservación de preferencias y datos, colisión de destino y rechazo de JSON inválido. `tests/test_installer_bootstrap.py` cubre autenticación, fijación de commit, verificación de blobs, integridad del tarball, modos, rutas maliciosas y fallos de descarga. No ejecuta `apt-get` ni modifica rutas reales del sistema.

La prueba real de instalación queda pendiente para la VPS desechable identificada en el plan de trabajo.
