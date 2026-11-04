# Validación live VMess TLS — lectura de lease por proceso Xray real

**Fecha de registro:** 2026-11-03
**Componente:** Etapa 2 — VMess TLS centralizado / lease temporal
**Resultado:** segunda ejecución PASS; primera ejecución excluida del resultado exitoso.
**Fuente de evidencia:** capturas compartidas por el propietario en la conversación de trabajo. No se dispone aquí de la transcripción íntegra de comandos ni de los logs originales.

## 1. Objetivo

Comprobar que un proceso real de Xray-core puede acceder al certificado y a la clave sintéticos preparados dentro del lease TLS cuando se ejecuta con la identidad de servicio no privilegiada prevista para la prueba, y que puede completar un handshake TLS 1.3.

## 2. Entorno y condiciones confirmadas

- Binario: Xray-core **26.10.31**.
- Identidad efectiva del proceso: **UID 999 / GID 988**.
- Material TLS: certificado y clave **sintéticos/de prueba** asociados al lease; no son certificados de producción ni secretos reales del usuario.
- Ejecución: proceso Xray real, no un mock del binario.
- Se realizaron al menos dos ejecuciones; la primera no se considera exitosa.

No se registran aquí ruta exacta del lease, comando de lanzamiento, puerto, dirección, SNI, suite criptográfica ni salida íntegra porque esos datos no están presentes en la evidencia disponible. No deben inferirse.

## 3. Resultado observado

La **segunda ejecución** confirmó que Xray-core 26.10.31, bajo UID 999/GID 988, pudo leer el certificado y la clave sintéticos del lease y completar un **handshake TLS 1.3 verificado**. La primera ejecución se excluye explícitamente del conteo de éxito; no se atribuye una causa concreta al primer intento porque no se conserva aquí su salida completa.

## 4. Qué demuestra

1. El proceso Xray real pudo acceder al material sintético del lease bajo la identidad UID 999/GID 988.
2. Los permisos/propiedad efectivos utilizados en esa prueba fueron suficientes para la lectura por ese proceso.
3. El flujo de prueba alcanzó un handshake TLS 1.3 verificado en la segunda ejecución.

Esta evidencia supera la limitación anterior de las pruebas puramente estructurales/simuladas respecto de la lectura del lease por un proceso Xray real.

## 5. Qué NO demuestra

- No demuestra que exista o esté desplegada una unidad `xray.service` administrada por el proyecto.
- No demuestra que el menú del administrador haya aplicado la conexión al runtime o actualizado `/etc/xray/config.json`.
- No demuestra activación mediante perfil activo, rollback ni ciclo transaccional de aplicación.
- No demuestra conectividad desde un cliente externo o por WAN.
- No demuestra uso de certificados/llaves reales, persistencia de material productivo ni rotación.
- No completa la auditoría de VMess TLS ni equivale a aceptación formal de VMess o de la Etapa 2.
- No sustituye las pruebas automatizadas del asistente, restore, cleanup, backup ni las pruebas de integración pendientes.

## 6. Clasificación

| Dimensión | Estado | Alcance |
|---|---|---|
| Proceso Xray real | VERIFICADO | Xray-core 26.10.31 |
| Identidad no privilegiada | VERIFICADO | UID 999 / GID 988 |
| Lectura del lease | VERIFICADO | Certificado y clave sintéticos |
| Handshake TLS | VERIFICADO | TLS 1.3, segunda ejecución |
| Primera ejecución | NO CONTABILIZADA | No se declara PASS |
| Servicio administrado | NO VERIFICADO | No se acredita `xray.service` |
| Runtime apply del Manager | NO VERIFICADO | No se acredita activación |
| Cliente externo/WAN | NO VERIFICADO | Fuera de esta prueba |
| Aceptación formal VMess | PENDIENTE | Requiere decisión y auditoría del propietario |

## 7. Seguridad y cambios operativos

La evidencia describe material sintético de prueba. Este informe no autoriza leer ni utilizar la clave maestra real, importar certificados reales, crear perfiles live, aplicar configuraciones, iniciar/instalar servicios, abrir puertos ni modificar firewall o red. No se afirma que esas operaciones se hayan realizado durante esta prueba.

## 8. Próximos pasos

- Conservar esta evidencia como validación live acotada de lectura del lease.
- En una futura validación autorizada, registrar comandos, identidad efectiva, permisos/propietarios, rutas saneadas y logs completos sin exponer secretos.
- Mantener separada esta prueba de la aceptación formal de VMess y de la integración de activación por perfil.

**Conclusión:** se verificó que un proceso Xray-core 26.10.31 real, ejecutado como UID 999/GID 988, leyó el certificado y la clave sintéticos del lease y completó un handshake TLS 1.3 en la segunda ejecución. Es una prueba live significativa, pero acotada; no acredita despliegue del servicio administrado, runtime apply, conectividad WAN ni aceptación integral.
