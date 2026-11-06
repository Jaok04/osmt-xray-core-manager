# Auditoría — instalador Manager-only por defecto

**Fecha:** 2026-11-06
**Dictamen:** PASS EN PREFIJOS AISLADOS
**Alcance:** comportamiento de install.sh, modo predeterminado y opción integral explícita.

## Verificaciones

- El modo --install instala sólo Manager y no entra en Fase B.
- No crea ni modifica /etc/xray, /usr/local/bin/xray, geodata ni xray.service.
- No ejecuta preflight de rutas Xray ni sigue symlinks de esas rutas.
- Conserva los fixtures Xray existentes byte por byte.
- Estado inicial correcto: Manager true, Xray false, servicio false.
- Una ruta Xray simbólica no afecta Manager-only; el modo integral rechaza la misma ruta antes de desplegar.
- --with-xray sin --install se rechaza.
- --install --with-xray conserva el flujo Fase A+B y prepara la unidad en el prefijo fixture.
- Idempotencia, preservación de preferencias/conexiones, colisiones, rutas simbólicas del Manager y locks siguen cubiertos.

## Regresión

- tests/install.sh: PASS.
- Python: 332/332 PASS.
- Bash: 62/62 PASS.
- bash -n: PASS.
- ShellCheck -S error: PASS.
- compileall: PASS.
- install.sh --check: PASS, no-op.
- git diff --check: PASS.

## Límites

No se ejecutó install.sh en modo real. No se instaló Xray-core ni Certbot, no se creó usuario/grupo real, no se ejecutó systemctl, no se modificó unidad real ni se tocó red/firewall/DNS/certificados. El backend R-05 sigue fixture-only. Sin commit/push.

## Dictamen

PASS EN PREFIJOS AISLADOS. El flujo por defecto ya permite instalar primero sólo Xray Core Manager; la instalación de Xray queda como acción posterior del menú o como modalidad integral explícita --with-xray.
