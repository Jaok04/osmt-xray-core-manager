# Implementación U-01 — Integración Usuarios V2 con VLESS

**Fecha:** 2026-11-04
**Autorización:** aprobación expresa del propietario del diseño U-01 y de su implementación con el alcance descrito.
**Rama:** `design/user-identity-association-v1`
**Estado de esta entrega:** IMPLEMENTADA, VERIFICADA, PUBLICADA y SINCRONIZADA; aceptación formal del propietario pendiente. Commit: `1c2cd12f15be75d9f3a080ce028951724618c492`.

## 1. Objetivo

Eliminar la desconexión entre el registro administrativo Usuarios V2 y el generador VLESS. Usuarios V2 es la única fuente de identidades, asociaciones y credenciales para construir modelos VLESS candidatos. La integración no publica configuraciones en runtime.

## 2. Cambios implementados

### 2.1 Exportación de asociaciones candidatas

Se añadió `users_v2_export_vless_candidate_clients <connection_id>` en `modules/users_v2.sh`.

- Toma una instantánea coherente bajo el bloqueo compartido `XRAY_MANAGER_INTEGRITY_LOCK` (`flock -s`), compatible con las escrituras exclusivas (`flock -x`) del módulo.
- Valida el documento V2 completo y el catálogo de conexiones antes de exportar.
- Exige que la conexión solicitada exista y sea VLESS.
- Incluye asociaciones de esa conexión con `protocol=vless`, `state=active` y vencimiento nulo o futuro.
- Excluye asociaciones `suspended`, `expired` y activas cuyo vencimiento ya pasó, incluso si el barrido periódico todavía no actualizó su estado.
- No filtra por `provisioning_status` ni `runtime.status`: un alta `active/draft/not_applied` puede formar el primer candidato y un fallo previo puede reintentarse.
- Rechaza fechas de vencimiento no interpretables, JSON corrupto, referencias inconsistentes y almacén ausente.
- No crea ni inicializa `users.json` cuando falta; no modifica el almacén.

La salida conserva el contrato neutral Xray:

```json
[
  {
    "id": "UUID-de-credencial-de-la-asociacion",
    "email": "assoc:UUID-de-asociacion"
  }
]
```

`id` es la credencial UUID propia de la asociación; `email` deriva del ID estable de asociación. El alias y el ID global de identidad no se usan como identificadores técnicos.

### 2.2 Separación entre candidato y runtime

`users_v2_export_vless_clients <connection_id>` conserva su semántica previa de vista runtime: solo devuelve asociaciones activas con `provisioning_status=applied` y `runtime.status=applied`.

La nueva exportación candidata es independiente. No se cambió el significado de la exportación runtime ni se declara que una asociación draft tenga acceso efectivo.

### 2.3 Integración del asistente VLESS

Se añadió `connections_vless_assistant_build_model` en `modules/vless_assistant.sh`.

- Obtiene los clientes exclusivamente mediante la exportación candidata Usuarios V2.
- Construye el modelo neutral VLESS y asigna el resultado a `users[]`.
- Se utiliza tanto en la creación como en la recuperación/reconstrucción de una configuración.
- No utiliza `users_build_vless_model` ni el almacén legacy como fallback.
- Si falta el adaptador V2, el almacén no existe o los datos no superan la validación, falla de forma explícita y no genera una configuración vacía por omisión.

### 2.4 Generación de UUID VLESS en el menú V2

El flujo de asociación VLESS ofrece:

1. Generar UUID automáticamente (opción predeterminada).
2. Introducir UUID manualmente con entrada oculta.

La generación comprueba el formato y busca colisiones antes de continuar. La operación de creación vuelve a validar unicidad global bajo el lock, por lo que la comprobación previa del menú no sustituye la validación atómica. Los UUID se normalizan a minúsculas antes de persistirlos; la unicidad se compara sin distinguir mayúsculas/minúsculas. El UUID nunca se imprime en el resumen.

## 3. Archivos afectados

- `modules/users_v2.sh`
- `modules/users_v2_menu.sh`
- `modules/vless_assistant.sh`
- `tests/users_v2_vless_candidate.sh` (nuevo)
- `tests/users_v2_menu.sh`
- `tests/vless_assistant.sh`
- `tests/vless_tls_lease_assistant.sh`
- `tests/xray_vless_integration.sh`
- `tests/smoke.sh`
- `docs/DISENO_IDENTIDADES_ASOCIACIONES_V1.md`
- `docs/IMPLEMENTACION_U01_INTEGRACION_USUARIOS_V2_VLESS_2026-11-04.md`
- `docs/AUDITORIA_U01_INTEGRACION_USUARIOS_V2_VLESS_2026-11-04.md`

## 4. Pruebas y verificaciones

La evidencia detallada se encuentra en `docs/AUDITORIA_U01_INTEGRACION_USUARIOS_V2_VLESS_2026-11-04.md`.

- Prueba específica de exportación candidata: incluye active/draft, excluye suspended/expired/vencidos/otras conexiones/otros protocolos, separa runtime, valida fecha inválida y falla cerrado sin inicializar el almacén.
- Pruebas de menú: UUID automático y manual, normalización, unicidad y protección de datos sensibles.
- Pruebas del asistente: V2 obligatorio, ausencia del almacén sin inicialización accidental, ausencia de fallback legacy y persistencia de borradores sin aplicar runtime.
- Integración con Xray 26.10.31 real: asociación V2 `active/draft/not_applied` proyectada a `clients[]` y aceptada por `xray run -test`.
- Regresión completa de scripts shell: 58/58 PASS.
- Controles estáticos: `bash -n`, `python3 -m py_compile scripts/*.py`, `./install.sh --check`, ShellCheck severidad error, `shfmt` y `git diff --check` PASS.

## 5. Límites expresos

U-01 no implementa ni autoriza:

- Migración de registros legacy ni cutover real.
- ACME, Cloudflare, DNS-01 ni emisión/renovación de certificados.
- Publicación de configuraciones candidatas al runtime.
- Inicio/reinicio del servicio Xray, listeners, firewall, puertos o cambios de red.
- Aplicación efectiva de suspensiones/vencimientos a runtime.
- Pruebas de cliente externo, WAN o tráfico real.

Una configuración candidata validada por `xray run -test` no es una conexión activa. Las asociaciones `active/draft/not_applied` representan el estado administrativo deseado y todavía no conceden acceso efectivo.

## 6. Custodia y gobernanza

- Se trabajó únicamente en `/opt/xray-manager` de la VPS `Implementación-Xray`.
- Se usaron almacenes temporales, claves y credenciales sintéticas.
- No se leyó ni utilizó `/etc/xray-manager/keys/master.key` real.
- No se modificaron almacenes live, runtime, servicios, certificados desplegados, firewall, puertos, dependencias ni configuración activa.
- No se consultó ni modificó la VPS `Vps de Pruebas`.
- `main` y `Xray-Normativa/` permanecen intactas.
- Etapa 2 y Etapa 5 permanecen ABIERTAS. U-01 no cierra Etapa 2 ni Etapa 3.


## 7. Publicación

El cambio se publicó mediante commit `1c2cd12f15be75d9f3a080ce028951724618c492` (`feat(vless): integrate V2 users into candidate generation`) en `design/user-identity-association-v1`, con push fast-forward desde `ca6d76895821310a3072d9de47268f925ecea7ba`. La consulta posterior a GitHub confirmó el SHA remoto. `main` permaneció intacta. La aceptación formal de U-01 corresponde al propietario y sigue pendiente.
