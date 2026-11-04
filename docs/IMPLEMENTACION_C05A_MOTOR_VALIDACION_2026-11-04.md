# Implementación C-05A — Motor de validación estática y nativa

**Fecha:** 2026-11-04
**Estado:** C-05A aceptada formalmente por el propietario el 2026-11-04.
**Rama:** `design/user-identity-association-v1`
**Alcance autorizado:** C-05A exclusivamente.

## Archivos incorporados

- `scripts/xray_config_validator.py`
- `tests/test_xray_config_validator.py`
- `docs/IMPLEMENTACION_C05A_MOTOR_VALIDACION_2026-11-04.md` (este registro)
- `docs/AUDITORIA_C05A_MOTOR_VALIDACION_2026-11-04.md`

No se modificaron el gestor de configuraciones, sus manifiestos/metadatos, el almacén de informes, el menú, los perfiles ni los archivos de normativa.

## Contrato del motor

La función pública `validate_configuration(data, xray_binary, timeout)` recibe los bytes exactos de una revisión que el llamador debe haber verificado previamente. El módulo:

- No accede al almacén de configuraciones.
- No carga ni lee la clave maestra.
- No descifra ni altera revisiones.
- No persiste informes ni cambia estados.
- No aplica configuraciones, inicia servicios ni modifica runtime.
- Calcula SHA-256 de los bytes recibidos y devuelve un resultado estructurado en memoria.

Límites: contenido de 1 byte a 16 MiB; timeout nativo entre 1 y 120 segundos.

## Comprobaciones

1. **JSON:** UTF-8 estricto, sintaxis, rechazo de claves duplicadas y raíz objeto.
2. **Estructura Xray:** `inbounds` y `outbounds` como arreglos; secciones opcionales conocidas como objetos; tipos básicos de `routing.rules` y `dns.servers`.
3. **Parámetros requeridos:** al menos un inbound y outbound; protocolo no vacío; tipos básicos de `settings`, `streamSettings` y `tag`.
4. **Tipos/valores:** comprobaciones acotadas de `log.loglevel`, `routing.domainStrategy` y `sendThrough`.
5. **Compatibilidad:** no se mantiene una matriz local no sustentada de opciones por versión. Se delega la aceptación final al validador nativo de la versión instalada.
6. **Referencias/conflictos:** etiquetas duplicadas dentro de cada espacio de nombres, referencias `outboundTag`, `inboundTag` y `balancerTag` detectables.

Las comprobaciones estáticas son deliberadamente conservadoras; Xray nativo es la autoridad final sobre el esquema y las opciones aceptadas por su versión.

## Validación nativa

- Verifica ruta absoluta sin componentes simbólicos.
- Exige binario regular, root-owned, sin hardlinks, no modificable por grupo/otros y ejecutable.
- Obtiene versión y SHA-256 del binario.
- Crea directorio temporal 0700 y configuración 0600.
- Ejecuta `xray run -test -config <archivo-temporal>` sobre los bytes recibidos.
- Aplica timeout y entorno mínimo.
- No conserva stdout/stderr nativo para evitar persistir secretos o datos arbitrarios; registra diagnóstico genérico y código de salida.

La validación `-test` no demuestra conectividad ni sustituye una prueba runtime.

## Clasificación

- `PASS`: comprobaciones estáticas y Xray nativo satisfactorios.
- `PASS_WITH_WARNINGS`: reservado para advertencias no bloqueantes; esta versión no inventa heurísticas de advertencia y no genera advertencias automáticamente.
- `FAIL`: JSON/estructura/parámetros/referencias rechazados o Xray nativo devuelve código distinto de cero.
- `INCOMPLETE`: binario ausente/inseguro, timeout de versión/validación u otro impedimento para completar la prueba nativa.

Si una comprobación estática bloqueante falla, Xray nativo no se ejecuta y el resultado en memoria lo indica como `NOT_RUN`.

## Pruebas ejecutadas

- 17 pruebas unitarias focales: **17/17 PASS**.
- Casos cubiertos: JSON inválido, claves duplicadas, raíz no objeto, secciones/parámetros ausentes, referencias desconocidas, etiquetas duplicadas, espacios de nombres independientes, rechazo nativo simulado, timeout, binario ausente/inseguro, symlink/hardlink del binario, hash exacto y límites.
- Validación real con el binario instalado: configuración sintética mínima aceptada y protocolo inexistente rechazado por Xray 26.10.31.
- Identidad del binario comprobado: SHA-256 `cc4b84d3069569f297a61f04b914f2bb37e9d202fd7b84cb50def1fc30fd40e1`.
- Regresión ejecutada satisfactoriamente: `tests/smoke.sh`, `tests/xray_configurations.sh`, `tests/xray_configurations_c03.sh`, `tests/xray_configurations_c04a.sh`, `tests/xray_configurations_c04b.sh` y `tests/xray_configurations_menu.sh`. Los mensajes de procesos terminados por SIGKILL en las pruebas de C-01/C-03/C-04 son inyecciones de fallos intencionales de sus matrices WAL; los scripts completaron con código de salida satisfactorio.
- `python3 -m py_compile` y `git diff --check`: PASS.

## Límites pendientes

- El motor todavía no está conectado al gestor de configuraciones independientes.
- No se vincula todavía un resultado a `config_id`/revisión en un almacén persistente.
- No existe promoción a estado Validada.
- No existe historial ni menú.
- La matriz local de compatibilidad por versión no se implementa; la aceptación de compatibilidad se delega al Xray nativo.
- Las advertencias no se generan hasta definir señales estáticas no bloqueantes técnicamente justificadas.

Estos puntos corresponden a fases posteriores del plan C-05 y no se implementaron en C-05A.

## Estado Git y seguridad del alcance

- Rama de trabajo: `design/user-identity-association-v1`.
- HEAD permanece en `2676b36403e414e9ece5e85250ce89e0b01185d3`; el trabajo está sin commit.
- No se modificó `main` ni `Xray-Normativa/`.
- No se leyó ni utilizó `/etc/xray-manager/keys/master.key`.
- No se modificaron servicios, runtime, certificados, puertos, firewall, paquetes ni dependencias.
- No se hizo commit, push ni publicación.
- C-05A fue aceptada formalmente por el propietario el 2026-11-04. La fase queda cerrada; C-05B requiere autorización independiente.


## Addendum — aceptación, publicación y sincronización (2026-11-04)

El estado Git descrito en el apartado anterior corresponde al momento de implementación y aceptación local de C-05A; no describe la publicación posterior. C-05A fue aceptada formalmente y publicada conjuntamente con C-05B en el commit `0b0e36e53dbc58c2102805834c2ffc1a5edd6b25`. El registro de aceptación y continuidad se publicó en el commit `1815663438770a2271d769345adbc271714a6817`.

La rama `design/user-identity-association-v1` y `/opt/xray-manager` se verificaron en ese HEAD, con árbol limpio. La publicación fue fast-forward. `main` y `Xray-Normativa/` permanecieron intactas. C-05A está IMPLEMENTADA, VERIFICADA, AUDITADA, ACEPTADA, PUBLICADA y SINCRONIZADA. C-05B fue aceptada y publicada en el mismo cambio. C-05C requiere autorización independiente.
