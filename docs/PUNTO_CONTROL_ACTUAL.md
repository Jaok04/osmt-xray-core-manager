# Punto de control actual — Xray Core Manager

**Fecha del corte:** 2026-11-02
**Tarea:** cierre técnico VMess antes de iniciar Trojan.
**Estado:** VMess IMPLEMENTADO, VERIFICADO, PUBLICADO y SINCRONIZADO; aceptación formal pendiente del propietario.

## 1. Entorno verificado

- Repositorio: `Jaok04/xray-core-manager`.
- Rama autorizada: `design/user-identity-association-v1`.
- Proyecto VPS: `/opt/xray-manager`.
- Commit de cierre técnico VMess: `ab76a57032faa9793a62348f865fba2c9a7d8f77` (`fix(vmess): validate TLS pairs and complete coverage`).
- Remoto: `git@github.com-xray-core-manager:Jaok04/xray-core-manager.git`.
- Deploy Key SSH dedicada con permiso de escritura configurado.
- Documentación normativa: `/root/Xray_Manager_Documentacion_Final_2026-10-31`.
- Etapa 1: aceptada formalmente.
- Etapa 2: abierta.
- P4 backup/restore VLESS: completada y aceptada; intacta.

## 2. Alcance VMess contrastado

Diseño técnico aprobado: `docs/DISEÑO_TECNICO_VMESS.md`. Matriz cerrada de 14 combinaciones:

- WS sin TLS adicional.
- RAW/TCP TLS.
- WS-TLS.
- RAW/TCP REALITY.
- gRPC sin TLS, TLS y REALITY.
- HTTPUpgrade sin TLS y TLS.
- XHTTP sin TLS, TLS y REALITY.
- mKCP sin TLS y TLS.

Se conserva la distinción de la especificación normativa Etapa 2 revisión 1.3 y las decisiones complementarias aprobadas. No se reescribió la documentación normativa.

## 3. Implementación y verificaciones

- Modelo neutral, adaptador Xray 26.10.31, asistente, preparación segura y persistencia versionada cifrada implementados.
- Almacén VMess aislado en `/var/lib/xray-manager/vmess/configurations/` y `/var/lib/xray-manager/vmess/secrets/`.
- El catálogo compartido usa únicamente las referencias VMess `vmess_configuration_ref`, `vmess_secret_ref`, `vmess_configuration_revision` y `vmess_configuration_schema_version`.
- Xray-core 26.10.31, binario `/var/cache/xray-manager/validation/v26.10.31/xray`, versión `a4a3dff`: 14/14 modalidades aceptadas por `xray run -test`.
- Adaptador TLS reforzado: valida certificado PEM, clave privada PEM y correspondencia de claves públicas mediante `cryptography`; rechaza symlinks y archivos no regulares.
- Casos negativos: TLS sin clave, symlink de clave, PEM inválido, certificado/clave no coincidentes, REALITY sin clave, short ID inválido, clave REALITY inválida, campos TLS en modalidad sin TLS, campos de transporte desconocidos y modelo/seguridad inconsistentes: PASS.
- Navegación: 14/14 combinaciones VMess resueltas individualmente por el menú.
- Suite completa `tests/*.sh`: 36/36 scripts PASS.
- Controles estáticos: `bash -n`, `python3 -m py_compile scripts/*.py`, `./install.sh --check`, ShellCheck (`-S warning`), shfmt y `git diff --check`: PASS.

## 4. Límites que no bloquean el cierre de VMess

- `xray run -test` valida estructura y configuración; no demuestra conectividad extremo a extremo.
- No se realizó prueba cliente-servidor real.
- No se activaron borradores ni se modificó configuración activa, runtime, servicio, firewall o puertos.
- Usuarios VMess se introducen manualmente; integración con identidades globales corresponde a Etapa 3.
- Backup/restore VMess no está implementado y requiere diseño y autorización separados.
- La restauración de un backup VLESS antiguo puede revertir el catálogo común y dejar referencias VMess ausentes; los archivos aislados no se incluyen en backup VLESS.
- P4 VLESS y `scripts/vless_backup.py` no fueron modificados.

## 5. Archivos modificados en el cierre técnico

- `modules/vmess_xray_26_10_31.sh`: validación criptográfica del certificado y clave TLS.
- `tests/xray_vmess_integration.sh`: cobertura negativa TLS/REALITY/transporte.
- `tests/stage2_navigation.sh`: recorrido de las 14 combinaciones VMess.
- `docs/DISEÑO_TECNICO_VMESS.md`: comportamiento y criterios de prueba actualizados.
- `PROJECT_STATE.md`, este documento, `docs/CONTINUIDAD_DEL_PROYECTO.md` y `HISTORY.md`: continuidad y trazabilidad.

## 6. Estado separado

| Estado | Resultado |
|---|---|
| IMPLEMENTADO | Sí |
| VERIFICADO | Sí — 36/36 scripts y controles estáticos |
| PUBLICADO | Sí — `ab76a57032faa9793a62348f865fba2c9a7d8f77` en la rama autorizada |
| SINCRONIZADO | Sí — verificación posterior a los commits de código y documentación; obtener SHA vigente con `git rev-parse HEAD` |
| ACEPTADO | Pendiente de confirmación formal del propietario |

## 7. Siguiente acción

Esperar la aceptación formal del propietario para VMess. Una vez aceptado, iniciar el contraste técnico y normativo de Trojan antes de diseñar o implementar el módulo. No comenzar Shadowsocks ni otros protocolos por inferencia.

No modificar `main`. No modificar VLESS P4, runtime, firewall, puertos, certificados desplegados ni servicio sin autorización expresa.
