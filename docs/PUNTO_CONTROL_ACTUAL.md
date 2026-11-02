# Punto de control actual — Xray Core Manager

**Fecha del corte:** 2026-11-02
**Tarea actual:** Etapa 2 — VMess, persistencia aislada y auditoría de regresión.
**Estado:** implementación local en curso; alcance de aislamiento autorizado; sin publicación ni aceptación final.

## 1. Entorno verificado

- Repositorio: Jaok04/xray-core-manager.
- Rama autorizada: `design/user-identity-association-v1`.
- Proyecto VPS: `/opt/xray-manager`.
- HEAD local y remoto comprobados: `402a74174b7a0d97aca41de54dab6564886088df`.
- El árbol de trabajo contiene cambios VMess locales y no publicados.
- Documentación normativa: `/root/Xray_Manager_Documentacion_Final_2026-10-31`.
- Etapa 1: aceptada formalmente.
- Etapa 2: en desarrollo y abierta.
- P4 backup/restore VLESS: completada y aceptada; no se modificó.

## 2. Decisiones y alcance autorizados

- Diseño VMess aprobado, incluidas las 14 combinaciones y HTTPUpgrade-TLS.
- Implementar borradores VMess, validación con Xray-core 26.10.31, persistencia cifrada y recuperación temporal.
- Separar el almacén VMess de P4 VLESS en `/var/lib/xray-manager/vmess/configurations/` y `/var/lib/xray-manager/vmess/secrets/`.
- Usar referencias `vmess_*` independientes en el catálogo común.
- No modificar P4 VLESS, runtime, firewall, puertos ni servicio.
- No integrar asociaciones globales de identidad de Etapa 3 dentro de VMess.

## 3. Estado técnico local

Archivos VMess creados:
- `modules/vmess_model.sh`
- `modules/vmess_xray_26_10_31.sh`
- `modules/vmess_assistant.sh`
- `scripts/vmess_prepare_config.py`
- `scripts/vmess_config_store.py`
- `tests/vmess_model.sh`
- `tests/vmess_assistant.sh`
- `tests/xray_vmess_integration.sh`
- `tests/vmess_vless_backup_isolation.sh`

Archivos existentes modificados:
- `modules/connections.sh`, `bin/xray-manager`, `config/paths.sh`, `modules/uninstall.sh`.
- Pruebas de navegación/smoke y `tests/uninstall.sh`.
- Documentación técnica, estado, decisiones e historial.

La persistencia usa `vmess_configuration_ref`, `vmess_secret_ref`, `vmess_configuration_revision` y `vmess_configuration_schema_version`. No usa los campos VLESS `configuration_ref`/`secret_ref`.

## 4. Límites y advertencias

- El backup/restore VLESS no incluye configuraciones ni secretos VMess.
- El catálogo `connections.json` es compartido. Una restauración VLESS antigua puede revertir/eliminar registros VMess del catálogo, aunque el almacén VMess separado no se toca; podrían quedar archivos huérfanos.
- Usuarios VMess se introducen manualmente; la integración con identidades globales está pendiente de Etapa 3.
- `xray run -test` valida estructura, no conectividad extremo a extremo.
- No se creó ni guardó configuración real de usuario en el almacén persistente del host; pruebas usan directorios temporales.
- No se tocó runtime, firewall, puertos, certificados desplegados ni servicio.

## 5. Verificaciones ejecutadas en esta sesión

- Suite completa `tests/*.sh`: 36/36 PASS en la última ejecución, incluyendo VLESS, VMess, usuarios, navegación, concurrencia, instalación, servicio y desinstalación.
- `tests/xray_vmess_integration.sh`: PASS para las 14 combinaciones con Xray-core 26.10.31, incluida HTTPUpgrade-TLS.
- `tests/vmess_assistant.sh`: PASS tras el aislamiento.
- `tests/vmess_vless_backup_isolation.sh`: PASS; el backup VLESS valida un catálogo mixto y no incluye el almacén VMess externo.
- `tests/uninstall.sh`: PASS tras añadir el directorio VMess a la categoría de datos de conexiones.
- `bash -n` de scripts Bash, `py_compile scripts/*.py`, ShellCheck a nivel warning de archivos afectados, shfmt de archivos VMess nuevos, `install.sh --check` y `git diff --check`: PASS.

## 6. Siguiente paso

1. Completar revisión integral del diff y verificar que no haya cambios fuera del alcance autorizado.
2. Confirmar que el árbol local no contiene artefactos temporales generados por las pruebas.
3. Presentar el informe final y esperar autorización posterior para commit/push en la rama autorizada.

**No declarar VMess completado ni Etapa 2 completada.**