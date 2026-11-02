# Instalador inicial — Fase A (Manager)

Estado: implementación inicial y pruebas aisladas completadas; pendiente de validación en VPS desechable.

## Alcance

`install.sh` prepara únicamente Xray Core Manager en Ubuntu/Debian:

- comprueba plataforma, privilegios y dependencias;
- instala solo los paquetes faltantes mediante `apt-get update` y `apt-get install`; nunca ejecuta `apt upgrade`;
- despliega el código en `/opt/xray-manager` cuando el destino no existe;
- rechaza enlaces simbólicos en el destino y no sobrescribe una instalación de código preexistente distinta;
- crea directorios administrativos, datos, caché, logs y respaldos;
- crea preferencias iniciales y el catálogo vacío de conexiones si no existen;
- valida el JSON de conexiones existente y no lo reemplaza si es inválido;
- establece permisos `700` para directorios privados y `600` para archivos sensibles;
- registra el estado inicial en `/var/lib/xray-manager/state/install.json`.

## Exclusiones explícitas

Esta fase no instala Xray-core, no crea ni modifica `/etc/xray`, no crea `xray.service`, no crea usuario/grupo de servicio, no habilita ni inicia servicios y no inicializa ni migra `users.json`. Esas tareas pertenecen a las fases B y C, con la política aprobada de servicio instalado pero deshabilitado y detenido hasta que exista configuración válida.

## Uso

```bash
sudo ./install.sh --check
sudo ./install.sh --install
```

`--check` es de solo lectura. `--install` requiere root. Si `/opt/xray-manager` ya existe y el instalador se ejecuta desde ese mismo directorio, conserva el código existente; si el destino existe pero el origen es distinto, aborta sin sobrescribirlo.

## Pruebas

`tests/install.sh` utiliza un prefijo temporal aislado y cubre despliegue, permisos, idempotencia, conservación de preferencias y datos, colisión de destino y rechazo de JSON inválido. No ejecuta `apt-get` ni modifica rutas reales del sistema.

La prueba real de instalación queda pendiente para la VPS desechable identificada en el plan de trabajo.
