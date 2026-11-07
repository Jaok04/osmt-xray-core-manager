# H6-G2 — decisión F-02: contrato de evidencia de operación/publicación

Fecha: 2026-11-06
Estado: diseño aprobado para implementación aislada en desarrollo; sin integración live.

## Problema

Un SHA-256 entregado como argumento no prueba que el contenido proceda de una revisión validada ni que haya sido publicado por una operación concreta del Administrador. La identidad del cambio debe partir de `operation_id` y `generation_id`, y recuperar evidencia persistida desde una fuente confiable.

## Cadena exigida

1. `operation_id` identifica un journal R-05 schema 2.
2. `generation_id` debe coincidir exactamente con el journal de esa operación.
3. El estado debe acreditar publicación completada y no tener rollback iniciado.
4. `validation_id`, `profile_id`, `revision` y hash del contenido deben coincidir entre journal y manifiesto de staging.
5. El informe persistido debe ser exactamente el `validation_id` referenciado, corresponder al perfil/revisión/contenido, tener resultado `PASS` o `PASS_WITH_WARNINGS`, incluir todos los checks requeridos en PASS y corresponder al hash del binario Xray del manifiesto.
6. Los bytes del staging deben coincidir con el hash registrado en staging y con el hash de publicación.
7. El archivo runtime observado debe estar en la ruta destino de esa operación y sus bytes deben coincidir con el hash publicado.
8. Cualquier rollback iniciado, estado no publicado, discrepancia, ruta alternativa o evidencia ausente bloquea la acción.

## Contrato del backend

Las mutaciones reciben `operation_id` y `generation_id`, nunca un hash libre. El backend invoca un lector/verificador de evidencia y compara `runtime_config_sha256` con `published_config_sha256` devuelto por ese verificador. La evidencia debe identificar operación y generación, publicación `published`, validación PASS/PASS_WITH_WARNINGS y entorno `live`. La ausencia del lector o una evidencia marcada `fixture` bloquea toda mutación.

## Límite de esta iteración

El journal R-03/R-05 actual exige marcadores fixture y `journal.read_journal()` lo hace cumplir. Por eso `xray_runtime_operation_evidence.py` verifica hoy la cadena existente, pero devuelve explícitamente `environment=fixture`. No se debilitan esos marcadores ni se presenta un fixture como evidencia live. Un emisor/lector live requerirá una evolución de esquema y almacén aprobada en G3, sin conectar este módulo a R-05 ahora.

El backend live permanece aislado y no se expone a CLI/menú. Fixture sigue siendo predeterminado. Sin acciones live, commits ni push.
