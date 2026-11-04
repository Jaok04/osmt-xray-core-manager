# C-05D — Historial y comparación de informes de validación

**Fecha:** 2026-11-04
**Estado:** implementación local en curso; no publicada.
**Alcance:** servicio Python de consulta read-only sobre el almacén append-only C-05B. No incluye menú Bash (C-05E) ni auditoría integral (C-05F).

## Decisión funcional aprobada

La comparación admite únicamente informes que pertenezcan al mismo `config_id`; pueden corresponder a revisiones diferentes. La comparación rechaza identidades de configuración distintas.

## Archivos

- `scripts/xray_validation_history.py`: servicio de historial, detalle, último informe y comparación.
- `tests/test_xray_validation_history.py`: 38 pruebas focales H01–H38.
- No se modifica el esquema persistido de C-05B ni su catálogo.

## API

`ValidationHistoryService(root=None, store=None)`

- `list_history(...)`: devuelve `total`, `limit`, `offset` y metadatos paginados. Filtros opcionales: `config_id`, `revision`, `date_from`, `date_to`, `validation_type`, `result`. Orden descendente por fecha de validación, fecha de almacenamiento e ID.
- `get_report_detail(validation_id)`: devuelve el informe completo verificado, con checks, errores, advertencias y detalles.
- `get_latest_report(config_id=None)`: devuelve el informe más reciente global o de la configuración solicitada; `None` si no existe.
- `compare_reports(first_id, second_id)`: comparación estructurada de dos informes de la misma configuración.

Fechas: ISO-8601 con zona horaria obligatoria, normalizadas a UTC para filtrar y ordenar. Se rechazan fechas inválidas, fechas sin zona horaria e intervalos invertidos. Paginación acotada: límite máximo 1000 y offset máximo 1.000.000.

## Comparación

Compara:
- resultado general;
- revisión, fecha de validación y almacenamiento, hash y tamaño del contenido;
- versión y hash del binario Xray;
- checks agregados/eliminados y cambios de estado, errores, advertencias y detalles.

No compara ni reconstruye el contenido JSON original, no descifra configuraciones y no aplica cambios. Los valores de error/advertencia ya pasan por la sanitización de C-05B.

## Integridad y concurrencia

Cada listado carga el catálogo e informes bajo el lock exclusivo existente, ejecuta recuperación WAL y verifica integridad de catálogo e informes mediante el mecanismo de C-05B. El servicio no escribe en el almacén. Detalle y comparación reutilizan las operaciones verificadas de C-05B; no se crea otro almacén ni otro formato de informe.

Las fechas se validan al consultar porque C-05B sólo impone un límite básico de tipo/longitud al campo `created_at` durante la persistencia. Un timestamp malformado se presenta como error controlado; no se repara ni altera el informe.

## Exclusiones y límites

- No hay retención, purga, edición ni borrado.
- No se consulta `ConfigurationStore`; por ello el informe sigue disponible aunque la configuración original ya no exista.
- No hay menú, comandos CLI ni integración con runtime.
- No se ejecuta Xray ni se accede a claves o almacenes de configuraciones.
- No se cambian dependencias ni el esquema de C-05B.
- No se modifica `Xray-Normativa/`, `main`, servicios, runtime, red, firewall, puertos, certificados ni VPS de pruebas.

## Pruebas

La matriz H01–H38 se materializa en `tests/test_xray_validation_history.py`. Regresión prevista: C-05A/B/C (38 pruebas Python previas), C-05D (38 focales), y suites shell existentes C-01/C-02, C-03, C-04A/B/C y perfiles. Resultados reales y auditoría se registran en `docs/AUDITORIA_C05D_HISTORIAL_COMPARACION_2026-11-04.md`.

## Aceptación formal

El propietario aceptó formalmente C-05D el 2026-11-04 y autorizó la publicación exclusiva en `design/user-identity-association-v1`. Esta aceptación no cierra Etapa 5 ni Etapa 2 y no autoriza C-05E ni C-05F.
