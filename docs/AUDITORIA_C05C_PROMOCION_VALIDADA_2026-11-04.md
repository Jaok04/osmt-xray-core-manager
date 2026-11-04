# Auditoría técnica C-05C — promoción controlada a Validada

**Fecha:** 2026-11-04
**Rama:** `design/user-identity-association-v1`
**Base:** `6ab158f436d2d88755d70e954114efb4fa2f6129`
**Resultado:** **PASS — sin defectos bloqueantes detectados dentro del alcance C-05C.**
**Estado administrativo:** aceptada formalmente; publicación registrada en el addendum final.

## 1. Alcance auditado

Integración del motor C-05A y el almacén C-05B con el gestor de configuraciones independientes: revisión exacta, requisitos de promoción, integridad de informe/catálogo, metadatos, revisiones históricas, edición posterior y recuperación ante SIGKILL.

No se auditó el menú, el historial/comparación ni el cierre integral C-05.

## 2. Inspección de diseño y código

| Control | Resultado |
|---|---|
| Identidad config_id/revisión | PASS |
| Integridad ciphertext y AES-256-GCM antes de validar | PASS |
| SHA-256 de bytes descifrados ligado al informe | PASS |
| Validación nativa obligatoria | PASS |
| Comprobaciones estáticas obligatorias completas | PASS |
| PASS_WITH_WARNINGS sujeto a requisitos | PASS |
| FAIL/INCOMPLETE sin promoción | PASS |
| Revisión histórica no marca actual como Validada | PASS |
| Edición crea Borrador y conserva puntero anterior | PASS |
| Informe inmutable y catálogo append-only | PASS |
| Transacción informe + metadatos | PASS |
| Recuperación prepared/committed | PASS |
| Sin apply/activate ni modificación runtime | PASS |

El journal valida IDs, hashes, snapshots de metadatos y relación append-only entre catálogos. El orden de locks es único: configuraciones → informes.

## 3. Pruebas focales C-05C

**13/13 PASS**:

1. PASS promueve revisión actual y persiste informe.
2. PASS_WITH_WARNINGS promueve si todas las comprobaciones obligatorias pasan.
3. FAIL persiste informe y no promueve.
4. INCOMPLETE persiste informe y no promueve.
5. Ausencia de comprobación obligatoria rechaza el supuesto PASS.
6. Validación histórica no marca la revisión actual como Validada.
7. Edición posterior genera Borrador y preserva el puntero validado anterior.
8. Hash devuelto por el motor que no coincide se rechaza.
9. Metadatos con estados incoherentes o desconocidos se rechazan.
10. SIGKILL en estado prepared revierte informe y catálogo; un segundo punto de inyección tras escribir metadatos confirma que también se restaura el snapshot anterior.
11. SIGKILL después de committed completa la transacción.
12. SIGKILL después de escribir metadatos, antes de committed, restaura el estado anterior completo.
13. End-to-end con Xray real pasa y promueve usando almacenes temporales.

## 4. Regresión

- C-05A + C-05B + C-05C: **38/38 pruebas Python PASS**.
- C-01/C-02: `tests/xray_configurations.sh` PASS.
- C-03: `tests/xray_configurations_c03.sh` PASS.
- C-04A: `tests/xray_configurations_c04a.sh` PASS.
- C-04B: `tests/xray_configurations_c04b.sh` PASS.
- C-04C: `tests/xray_configurations_menu.sh` PASS.
- Perfiles: `tests/xray_profiles.sh` PASS.
- Python compile/AST, CLI help, `bash -n` focal y `git diff --check`: PASS.

Las suites existentes imprimen mensajes de SIGKILL y advertencias de artefactos inseguros deliberadamente inyectados en directorios temporales; forman parte de los casos negativos y las suites concluyeron correctamente.

## 5. Prueba con Xray real

Binario: `/usr/local/bin/xray`
Versión: `Xray 26.10.31 (go1.27.3 linux/amd64)`
SHA-256: `cc4b84d3069569f297a61f04b914f2bb37e9d202fd7b84cb50def1fc30fd40e1`

La prueba end-to-end ejecutó C-05C sobre una configuración SOCKS/Freedom sintética, almacén de configuraciones temporal, almacén de informes temporal y clave AES sintética. Xray aceptó la configuración mediante `run -test`; el informe quedó almacenado y la revisión fue promovida. No se inició un daemon ni se abrió un listener de servicio.

## 6. Integridad normativa y seguridad del entorno

Los hashes de Etapa 5 versionada coincidieron con el respaldo aprobado:

- Markdown: `8915f11da913e2cccba721b10a85246f215619bf867434e69e3745a1ef2970c9`.
- YAML: `e19612d026a107ae93c491318ba871c022df670530f7a084729396b36ff36547`.

Verificación de entorno:
- `/var/lib/xray-manager/configurations`: ausente.
- `/var/lib/xray-manager/validation`: ausente.
- No se leyó `/etc/xray-manager/keys/master.key`.
- No se instalaron ni actualizaron dependencias.
- Sin cambios runtime, servicios, certificados, firewall, puertos, red o configuración activa.
- `main`, `Xray-Normativa/` y `Vps de Pruebas` sin cambios.

## 7. Hallazgos y límites

No se detectaron defectos bloqueantes dentro del alcance probado.

- La promoción se invoca mediante CLI; no está conectada al menú Bash.
- Historial y comparación de informes siguen pendientes (C-05D).
- Auditoría integral C-05 sigue pendiente (C-05F).
- El informe demuestra validación estática/nativa de una revisión, no conectividad ni ejecución en producción.
- La prueba real utiliza datos sintéticos y almacenes temporales; no es una prueba sobre la configuración activa.

## 8. Dictamen

**C-05C: PASS técnico — implementada, verificada y auditada localmente.**

El propietario aceptó formalmente C-05C el 2026-11-04 y autorizó publicar sus cambios y actualizar la documentación. La publicación y sincronización quedan registradas en el addendum final. Esta aceptación no cierra la totalidad de C-05 ni autoriza C-05D/E/F. Etapa 5 y Etapa 2 permanecen ABIERTAS.
