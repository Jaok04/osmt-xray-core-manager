# H6-G2 — corrección F-01: invariantes de estados systemd

Fecha: 2026-11-06
Entorno: VPS de desarrollo `Implementación-Xray`, `/opt/xray-manager`
Rama: `design/user-identity-association-v1`
Base Git: `9bab1dbed7d4873aa30a3fd00a976a1d666d9355`

## Hallazgo

La auditoría independiente H6-G2 reprodujo que `LiveRuntimeBackend._validate_snapshot()` aceptaba `active_state=inactive` acompañado de `main_pid=4321` e `invocation_id` válido. Esa combinación contradice la semántica esperada del estado inactivo y podía permitir que `start` continuara con una observación incoherente.

## Corrección

En `scripts/xray_runtime_live_backend.py`:

- `inactive`: `main_pid` debe ser `None` o `0`, y `invocation_id` debe ser `None` o cadena vacía.
- `active`: exige `main_pid` entero mayor que 1 (no booleano), `invocation_id` hexadecimal de 32 caracteres, `sub_state=running` y `result=success`.
- Estados transitorios/no reconocidos siguen bloqueados; `failed` y `unknown` se pueden observar, pero no autorizan mutaciones.
- No se ejecutan acciones correctivas ni se altera systemd/runtime.

Se añadieron pruebas adversariales para PID e InvocationID residuales en `inactive`, y para metadatos incompletos/contradictorios en `active`.

## Verificación

- Pruebas focales `test_xray_runtime_live_backend.py`: 17/17 PASS.
- Suite Python completa: 358/358 PASS.
- Suites Bash: 62/62 PASS.
- `py_compile`: PASS.
- `bash -n` en los archivos Bash del puente: PASS.
- `git diff --check`: PASS.
- ShellCheck `-S error` en los archivos Bash del puente: PASS.

Las pruebas se ejecutaron en entorno de desarrollo y con mocks/fixtures. No se invocó systemctl real, no se inició/detuvo/reinició Xray, no se tocaron certificados, DNS, firewall, puertos ni red.

## Dictamen y límites

F-01 queda CORREGIDO EN CÓDIGO Y VERIFICADO EN FIXTURES. Esto no cierra H6-G2 ni habilita integración live. F-02, F-03, F-04 y F-05 continúan abiertos. No se realizó commit ni push; `main` y `Xray-Normativa/` permanecen intactas.
