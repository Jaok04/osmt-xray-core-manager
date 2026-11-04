# Implementación C-05C — promoción controlada a Validada

**Fecha:** 2026-11-04
**Rama:** `design/user-identity-association-v1`
**Base de trabajo:** `6ab158f436d2d88755d70e954114efb4fa2f6129`
**Estado:** implementada y verificada localmente; auditoría técnica PASS; aceptada formalmente; publicación registrada en el addendum final.
**Alcance autorizado:** exclusivamente C-05C. Sin C-05D, C-05E ni C-05F.

## 1. Objetivo

Integrar el motor C-05A con el almacén permanente C-05B para validar una revisión concreta de una configuración independiente y promoverla a **Validada** únicamente si se cumplen todos los requisitos obligatorios. El informe y el cambio de metadatos forman una única transacción recuperable.

## 2. Archivos

- Modificado: `scripts/xray_configurations.py`.
- Añadido: `scripts/xray_config_promotion.py`.
- Añadido: `tests/test_xray_config_promotion.py`.
- Añadidos los documentos de implementación y auditoría C-05C y actualizaciones de continuidad.

No se modificaron los contratos de C-05A ni C-05B.

## 3. Flujo implementado

1. Adquirir locks exclusivos de configuraciones e informes, siempre en orden configuración → validación.
2. Recuperar cualquier journal de promoción pendiente.
3. Verificar que la configuración existe y está registrada.
4. Resolver la revisión indicada o, por omisión, la revisión actual.
5. Verificar manifiesto, hash de ciphertext, autenticidad AES-256-GCM y descifrado de la revisión exacta.
6. Calcular SHA-256 de los bytes descifrados y ejecutar C-05A sobre esos mismos bytes.
7. Comprobar que el motor devuelve el mismo hash y tamaño.
8. Evaluar los criterios de promoción.
9. Generar el informe normalizado e inmutable con C-05B.
10. Persistir informe, catálogo y metadatos mediante journal transaccional propio.
11. Verificar integridad posterior a la transacción y devolver el estado real.

Ambos locks se mantienen durante la validación nativa para impedir que la revisión sea editada o eliminada mientras se valida. El timeout sigue limitado por C-05A (1–120 segundos).

## 4. Reglas de promoción

Se exige resultado `PASS` o `PASS_WITH_WARNINGS` y estas comprobaciones presentes, sin duplicados, con estado `PASS` y sin errores:

- `json_syntax`
- `xray_structure`
- `required_parameters`
- `types_values`
- `references_conflicts`
- `xray_native`

La comprobación `compatibility` debe existir y estar `PASS` o `DEFERRED_TO_NATIVE`; en el segundo caso, la comprobación nativa obligatoria debe pasar. También debe existir la identidad de versión y SHA-256 del binario Xray.

- `PASS`: no puede contener advertencias.
- `PASS_WITH_WARNINGS`: requiere advertencias registradas y permite promoción si todas las comprobaciones obligatorias pasan.
- `FAIL` / `INCOMPLETE`: el informe se conserva, pero no hay promoción.
- Un resultado PASS incoherente con las comprobaciones, compatibilidad o identidad del binario se rechaza como informe inconsistente.

No se promociona por el mero hecho de que exista un informe o por su resultado nominal.

## 5. Semántica de revisiones y metadatos

El lector de metadatos acepta los estados `not_validated` y `valid` con estas invariantes:

- `valid` exige que `last_validated_revision` sea exactamente igual a `current_revision` y que exista el directorio de revisión.
- `not_validated` no puede señalar la revisión actual como validada; sí puede conservar un puntero a una revisión anterior validada.
- Ningún puntero puede referenciar una revisión posterior a la actual.
- Los directorios referenciados se verifican como directorios root:root 0700, sin componentes simbólicos.

Al editar una configuración se crea una revisión nueva en estado `not_validated` y se conserva el puntero histórico `last_validated_revision`. La edición nunca hereda el estado Validada.

Si se valida una revisión anterior, el puntero identifica exactamente esa revisión y la revisión actual continúa como `not_validated`. Los informes históricos permanecen en el almacén append-only.

## 6. Transacción y recuperación

Nuevo journal: `promotion.transaction.json` dentro del almacén de validación.

La transacción liga ID/revisión, ID y bytes exactos del informe, snapshots anterior/nuevo del catálogo append-only y snapshots anterior/nuevo de metadatos.

- `prepared`: rollback de informe, catálogo y metadatos.
- `committed`: finalización hacia delante de los tres elementos.

Las escrituras son atómicas, con permisos 0600, fsync de archivos/directorios y locks existentes de C-05A/B. El journal valida identidades, hashes, snapshots, catálogo append-only y cambios permitidos en metadatos. Los tests inyectan SIGKILL tras actualizar el catálogo, tras escribir metadatos todavía en prepared y después de registrar committed; se comprueban rollback completo y recuperación hacia delante.

El informe y el estado no se anuncian como confirmados hasta que la transacción termina y se verifica la integridad del catálogo.

## 7. Interfaz

C-05C incorpora una CLI independiente; todavía no integra el menú Bash (C-05E):

```bash
python3 scripts/xray_config_promotion.py validate --config-id ID [--revision rNNNNNN]
```

Opciones globales: `--config-store`, `--master-key`, `--validation-store`, `--xray-binary` y `--timeout`. La CLI no ofrece `apply` ni `activate`; no inicia el servicio ni modifica runtime, systemd, firewall, certificados o red.

## 8. Verificación ejecutada

- Pruebas focales nuevas C-05C: **13/13 PASS**.
- Regresión Python combinada C-05A/B/C: **38/38 PASS**.
- Regresión shell C-01/C-02, C-03, C-04A, C-04B, menú C-04C y almacén de perfiles: PASS.
- Prueba end-to-end con `/usr/local/bin/xray`: PASS sobre almacenes temporales y clave sintética.
- Python compile y AST de los archivos modificados: PASS.
- Ayuda de CLI principal y subcomando: PASS.
- `bash -n modules/xray_configurations_menu.sh`: PASS.
- `git diff --check`: PASS.

Xray real: `Xray 26.10.31`, SHA-256 `cc4b84d3069569f297a61f04b914f2bb37e9d202fd7b84cb50def1fc30fd40e1`.

## 9. Límites y exclusiones

- Menú Bash pendiente (C-05E); historial/comparación pendiente (C-05D); auditoría integral C-05 pendiente (C-05F).
- `xray run -test -config` no demuestra conectividad ni funcionamiento extremo a extremo.
- Persistencia probada solo con almacenes temporales y clave sintética.
- No se crearon `/var/lib/xray-manager/configurations` ni `/var/lib/xray-manager/validation`.
- No se leyó ni utilizó la clave maestra real.
- No se instalaron ni actualizaron dependencias.
- Sin cambios en runtime, servicios, certificados, firewall, puertos, red, `main`, `Xray-Normativa/` o VPS `Vps de Pruebas`.
- No se creó commit, no se hizo push ni se sincronizó GitHub.

C-05C queda implementada, verificada y auditada localmente, pendiente de aceptación formal. Etapa 5 y Etapa 2 permanecen ABIERTAS.

## Registro de publicación

Aceptación formal y publicación registradas el 2026-11-04. Commit: `58c273a18ea32c1feddc02012d0318952c7a0689` (`58c273a`), rama `design/user-identity-association-v1`; push fast-forward.
