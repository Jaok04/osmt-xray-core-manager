# Implementación C-05B — Almacén permanente de informes

**Fecha:** 2026-11-04
**Estado:** Implementada, auditada y aceptada formalmente por el propietario el 2026-11-04. C-05B cerrada.
**Rama:** `design/user-identity-association-v1`
**Alcance autorizado:** C-05B exclusivamente.

## 1. Archivos incorporados

- `scripts/xray_validation_store.py`: almacén append-only de informes.
- `tests/test_xray_validation_store.py`: pruebas unitarias y recuperación transaccional.
- `docs/IMPLEMENTACION_C05B_ALMACEN_INFORMES_2026-11-04.md`: este registro.
- `docs/AUDITORIA_C05B_ALMACEN_INFORMES_2026-11-04.md`: evidencia y dictamen de auditoría.

No se modificaron archivos preexistentes, el motor C-05A, el gestor de configuraciones, los menús, los perfiles, los estados de configuración ni la normativa.

## 2. Rutas y estructura

Raíz predeterminada: `/var/lib/xray-manager/validation`.

- `reports/validation-<32-hex>.json`: informe inmutable individual.
- `catalog.json`: índice de informes y SHA-256 de cada archivo exacto.
- `validation.lock`: exclusión mutua mediante `flock`.
- `transaction.json`: journal WAL de la operación de persistencia.

La raíz y `reports/` se exigen `root:root 0700`; los archivos persistentes se exigen `root:root 0600`, regulares y con un solo hardlink. Los directorios/archivos sospechosos se rechazan; no se reparan permisos automáticamente.

## 3. API del componente

El componente es independiente del motor y del almacén de configuraciones:

- `ValidationReportStore.save_report(config_id, revision, report)`: valida el contrato, sanea diagnósticos, asigna ID y persiste informe + catálogo.
- `ValidationReportStore.get_report(validation_id)`: verifica el catálogo y la integridad antes de devolver el informe.
- `ValidationReportStore.list_reports()`: verifica todos los informes antes de devolver el índice.

CLI de consulta:
- `python3 scripts/xray_validation_store.py [--root RUTA] list`
- `python3 scripts/xray_validation_store.py [--root RUTA] show --validation-id validation-...`

El llamador entrega la identidad de configuración/revisión y el resultado en memoria producido por el motor. C-05B no abre ni descifra configuraciones, no consulta la clave maestra, no ejecuta Xray y no decide si una revisión debe ser Validada.

## 4. Contrato del informe

Cada informe conserva:

- schema_version e ID único `validation-<32-hex>`;
- config_id y revisión exactos;
- SHA-256 y tamaño de los bytes de configuración evaluados;
- versión del validador y tipo `static_and_native`;
- versión Xray y SHA-256 del binario cuando el motor los proporciona;
- fecha de validación y fecha de persistencia UTC;
- resultado PASS, PASS_WITH_WARNINGS, FAIL o INCOMPLETE;
- comprobaciones, estados, errores, advertencias y detalles acotados;
- huella SHA-256 interna y huella del archivo exacto registrada en catálogo.

Los diagnósticos se limitan y saneen para retirar patrones habituales de credenciales. No se almacenan JSON de configuración, stdout/stderr nativos ni claves. Los informes no contienen el contenido descifrado.

## 5. Inmutabilidad, integridad y transacciones

- No existe operación de edición, reemplazo, eliminación o limpieza de informes.
- La creación usa ID aleatorio y publicación exclusiva; una colisión no sobrescribe.
- El catálogo es append-only y registra hash del archivo exacto.
- Cada lectura verifica catálogo, identidad, huella del archivo y huella interna.
- El directorio de informes debe contener exactamente los archivos indexados; se rechazan extras, ausencias, symlinks y hardlinks.
- Lock exclusivo serializa las mutaciones y lecturas consistentes.
- Escrituras atómicas: temporal exclusivo 0600, escritura completa, fsync, publicación y fsync del directorio.
- WAL contiene rutas cerradas, bytes del informe y snapshots de catálogo anterior/nuevo.
- Estado `prepared`: recuperación revierte informe/catálogo.
- Estado `committed`: recuperación completa la publicación y verifica identidad/hash.
- Recuperación idempotente al adquirir lock; journal inválido se conserva para inspección y bloquea la operación.

Los informes quedan separados de las configuraciones y, por tanto, no dependen de que la configuración origen siga existiendo. No hay retención automática ni eliminación.

## 6. Límites deliberados de C-05B

- No hay promoción ni modificación de estado Validada (C-05C).
- No hay consulta histórica, filtros ni comparación de informes (C-05D).
- No hay integración de menú (C-05E).
- No hay conexión automática con `validate_configuration`; el llamador futuro deberá verificar identidad, revisión y hash antes de persistir.
- No se implementa todavía validación de que el informe corresponda a una revisión existente. Es responsabilidad de la integración transaccional posterior, no de este almacén desacoplado.
- No se ejecutan validaciones ni pruebas runtime al guardar un informe.
- El componente no realiza cambios en el filesystem de producción; las pruebas usan directorios temporales.

## 7. Seguridad y alcance

- No se leyó ni utilizó `/etc/xray-manager/keys/master.key`.
- No se instalaron ni actualizaron dependencias.
- No se modificaron servicios, runtime, certificados, puertos, firewall, configuración activa ni infraestructura.
- No se modificó `main` ni `Xray-Normativa/`.
- No se realizó commit, push ni publicación durante la implementación. La publicación queda autorizada por el propietario tras la aceptación formal.
