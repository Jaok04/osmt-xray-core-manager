# Auditoría B2 — ACME Certbot y certificados TLS

**Fecha:** 2026-11-05
**Alcance:** auditoría focal de B2-A a B2-G en fixtures; sin ACME real.
**Estado:** ACEPTADA FORMALMENTE por el propietario el 2026-11-05, con las limitaciones y exclusiones de este informe.

## 1. Contraste normativo Etapa 4

| Requisito normativo | Resultado B2 | Estado |
|---|---|---|
| Obtener certificado HTTP-01 y validar prerrequisitos | Certbot standalone; valida DNS A/AAAA contra IP indicada y bind local TCP/80 | IMPLEMENTADO; acceso externo no probado |
| Obtener certificado DNS-01 | Certbot manual; hook muestra TXT y espera al operador | IMPLEMENTADO EN CÓDIGO |
| Comprobar visibilidad TXT antes de continuar | Consulta valor exacto en tres resolutores con dig; falla si alguno no lo ve | IMPLEMENTADO; solo fixture |
| Admitir varios dominios y mostrar conjunto solicitado | Lista repetible --domain, normalizada, sin duplicados; plan visible antes de confirmar | IMPLEMENTADO |
| Wildcard solo en combinación compatible | Se rechaza HTTP-01 y se acepta DNS-01 | IMPLEMENTADO |
| Cliente ACME concreto | Certbot adoptado por decisión expresa | DECISIÓN APROBADA; compatibilidad instalada no verificada |
| Automatización DNS API pendiente | No se implementa plugin/proveedor API | CONFORME CON APLAZAMIENTO |
| Validar certificado, clave y cobertura dominio | SAN, vigencia y correspondencia criptográfica antes del import | IMPLEMENTADO EN FIXTURES |
| Conservar certificado actual si falla el nuevo | Importación nueva/deduplicada; no existe reemplazo de registro | CONFORME |
| No mostrar ni exportar claves privadas | Clave solo en staging privado y cifrado por Certificate Store | IMPLEMENTADO EN FIXTURES |
| No modificar automáticamente conexiones Xray | El import solo registra recurso central | CONFORME |
| Diagnóstico SSL/TLS solo lectura | No forma parte de B2 | PENDIENTE DE ETAPA 4 |
| Renovación, historial y automática | No forma parte de B2 inicial | PENDIENTE DE ETAPA 4 |
| Gestión y verificación DNS general | Solo preflight HTTP y TXT challenge | PARCIAL; pendiente de Etapa 4 |

La documentación normativa no se modificó.

## 2. Evidencia técnica focal

Pruebas de tests/test_certificate_acme.py:
- validación de dominios, duplicados, IP literal y wildcard;
- construcción de comandos diferenciados HTTP-01/DNS-01;
- preflight HTTP con resolutor y prueba de puerto inyectados;
- propagación TXT parcial/completa mediante resolutor inyectado;
- hook DNS con dig simulado, mostrando valor exacto y sin borrar registros;
- lineage Certbot fixture con symlinks internos a archive;
- rechazo de symlink que escapa del directorio archive;
- staging regular y privado;
- importación al Certificate Store usando clave maestra sintética;
- validación de SAN y correspondencia certificado/clave;
- lease TLS mediante Certificate Resolver con conexión VLESS-WS-TLS fixture;
- limpieza del lease;
- comando plan no ejecuta Certbot.

Prueba Bash tests/certificates_menu.sh: captura/normalización de dominios, rechazo de elemento vacío, construcción de argumentos y retorno del submenú. tests/stage1_menu.sh actualizada para comprobar la nueva ruta de navegación.

## 3. Seguridad

- Comandos construidos como lista de argumentos; no se usa shell para ejecutar Certbot.
- Solicitud real bloqueada sin --confirm-acme, root, Certbot presente y preflight.
- No se instala software ni se cambia configuración del sistema.
- No se detienen servicios ni se modifica firewall.
- TXT se publica manualmente; cleanup solo informa.
- Symlinks Certbot aceptados únicamente cuando resuelven dentro de archive.
- Staging temporal root-only y borrado al salir.
- El Certificate Store existente conserva validación, deduplicación, cifrado y permisos.
- El ID de solicitud no incluye material secreto; los registros no guardan claves ni valores TXT.
- No se lee la clave maestra real durante las pruebas.

## 4. Pruebas y controles globales

Ejecución de regresión global en la VPS de desarrollo:
- Python unittest discover: 182/182 PASS.
- Bash tests/*.sh: 61/61 PASS.
- py_compile scripts/*.py tests/test_*.py: PASS.
- bash -n en todos los módulos y tests Bash, bin/xray-manager y config/paths.sh: PASS.
- ShellCheck -S error sobre módulos, tests Bash, bin/xray-manager y config/paths.sh: PASS.
- ./install.sh --check: PASS; informó que todas las dependencias requeridas ya estaban instaladas y no modificó el sistema.
- git diff --check: PASS.
- Pruebas focales B2: 11/11 PASS; tests/certificates_menu.sh incluido en los 61 scripts Bash.

## 5. Limitaciones / no ejecutado

Certbot no está instalado; dig ya estaba disponible en /usr/bin/dig y no se instaló ni se utilizó para consultas DNS reales. No se ejecutó ACME real ni se consultó una CA. No se alteraron DNS, TXT, puerto 80, firewall, servicios, systemd, runtime, certificados reales ni red. No se probó acceso desde Internet. No se ejecutó el Resolver TLS con una identidad systemd real. No se modificó la normativa, main o la VPS de pruebas.

## 6. Dictamen

El backend inicial de ambos métodos, el menú básico, la importación segura y la prueba de integración fixture con Resolver TLS están IMPLEMENTADOS y VERIFICADOS en el alcance fixture-only: Python 182/182, Bash 61/61, controles estáticos, install.sh --check y git diff --check PASS. La revisión del diff preparado para publicación fue completada sin errores; el propietario aceptó formalmente B2 el 2026-11-05, limitado a los resultados y exclusiones de este informe. B2 no cierra Etapa 4 ni autoriza ACME real.
