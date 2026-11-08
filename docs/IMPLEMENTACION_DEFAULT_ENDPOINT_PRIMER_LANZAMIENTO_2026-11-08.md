# Corrección del endpoint público predeterminado

Fecha: 2026-11-08  
Rama: `design/user-identity-association-v1`

## Hallazgo

El objetivo vigente del primer despliegue es `pruebas.tvrc.me:443`, y el puente live valida ese dominio. Sin embargo, el menú de exportación VLESS-WS-TLS todavía utilizaba `hellen.tvrc.me` como valor predeterminado histórico. Esto podía generar un URI de cliente apuntando a un host distinto del servidor que el Administrador estaba preparando.

## Cambio

- `modules/profiles.sh`: el endpoint público predeterminado de exportación ahora es `pruebas.tvrc.me`; `XRAY_MANAGER_VLESS_PUBLIC_ADDRESS` sigue permitiendo una sobreescritura explícita.
- `tests/profiles_vless_composer_menu.sh`: fixture de certificado, endpoint y URI esperado actualizados al dominio aprobado.
- `docs/DISENO_PUENTE_MINIMO_MANAGER_RUNTIME_LIVE_VLESS_WS_TLS_2026-11-08.md`: se elimina la instrucción obsoleta de cambiar el default antes de exportar.

## Validación

`tests/profiles_vless_composer_menu.sh`, `bash -n`, ShellCheck `-S error` y `git diff --check`: PASS. El test comprueba que el URI exportado utiliza `pruebas.tvrc.me:443`.

No se ejecutó exportación de clientes reales ni se modificaron DNS, certificados, firewall, puertos, runtime o servicio.
