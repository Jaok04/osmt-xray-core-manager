# Formato cifrado compartido — Xray Manager

**Identificador:** `xray-manager-shared-backup`
**Versión:** 1
**Estado:** contrato criptográfico implementado y probado en aislamiento; integración de backup/restore pendiente.
**Módulo:** `scripts/shared_backup_format.py`

## 1. Propósito y neutralidad

El contenedor cifra bytes opacos. No interpreta ni depende de VLESS, VMess, Trojan, Shadowsocks, Hysteria2 u otro protocolo. Los adaptadores de cada protocolo producen y validan el snapshot lógico; este módulo aporta únicamente el contenedor criptográfico común.

Por tanto, un futuro adaptador Trojan podrá utilizar exactamente el mismo contenedor, sin cambiar el formato ni reutilizar la lógica interna de VLESS/VMess.

## 2. Estructura binaria v1

| Campo | Tamaño / representación | Regla |
|---|---|---|
| Magic | 8 bytes: `XRMGSBKP` | Identifica el contenedor |
| Header length | 4 bytes unsigned big-endian | 1–4096 |
| Header | JSON ASCII canónico UTF-8 compatible | Campos exactos, sin duplicados |
| Ciphertext | Longitud declarada en header | AES-GCM ciphertext + tag de 16 bytes |

Cabecera JSON canónica:

```json
{
  "format": "xray-manager-shared-backup",
  "format_version": 1,
  "cipher": "AES-256-GCM",
  "kdf": "scrypt",
  "kdf_params": {"n": 32768, "r": 8, "p": 1},
  "salt": "<base64 de 16 bytes>",
  "nonce": "<base64 de 12 bytes>",
  "ciphertext_length": 123456
}
```

El ejemplo es ilustrativo. No es un backup real ni contiene credenciales.

## 3. Criptografía

- KDF: scrypt, perfil v1 fijo `N=2^15, r=8, p=1`, salida de 32 bytes y límite de memoria de 64 MiB.
- Salt: 16 bytes aleatorios por paquete.
- Cifrado autenticado: AES-256-GCM.
- Nonce: 12 bytes aleatorios por paquete.
- Tag: 16 bytes, incluido al final del ciphertext.
- AAD: magic + longitud de cabecera + bytes exactos de la cabecera canónica. Así se autentican también versión, algoritmo, KDF, parámetros y longitudes.
- Contraseña: entrada como texto UTF-8; mínimo 12 caracteres y 16 bytes, máximo 1024 bytes. No se normaliza ni se acepta NUL.
- El paquete no incluye master key, copia recuperable de master key, contraseña ni clave derivada.

La versión 1 admite exclusivamente este perfil. Se rechazan parámetros KDF alternativos recibidos desde el paquete, evitando que un header no confiable fuerce consumos arbitrarios de CPU/memoria. Un perfil distinto requiere una versión/formato futuro revisado.

## 4. Límites y validación

- Payload en claro: 1 byte a 512 MiB.
- Cabecera: máximo 4096 bytes.
- Longitud total del paquete: limitada por el payload máximo y el overhead fijo.
- Se rechazan magic desconocido, truncamiento, bytes sobrantes, JSON no canónico, claves duplicadas, campos extra/ausentes, versiones desconocidas, parámetros KDF no exactos, Base64 inválido, longitudes incoherentes, contraseña incorrecta y cualquier alteración del tag/cabecera.
- El descifrado solo devuelve bytes después de autenticar correctamente AES-GCM.
- El módulo no extrae TAR, no crea rutas, no escribe staging, no modifica catálogos ni publica restauraciones.

## 5. Contrato de integración

1. El futuro orquestador recopila un snapshot lógico consistente en memoria y genera un manifiesto interno con hashes y metadatos.
2. El adaptador de cada protocolo valida y serializa su propio contenido. El contenedor no debe inferir el protocolo por el nombre de archivo.
3. Se solicita la contraseña interactivamente mediante el futuro CLI/UI; nunca por argumento de proceso, variable de entorno, archivo de configuración ni manifiesto.
4. El payload se cifra antes de persistir el paquete. No crear archivos temporales con el snapshot descifrado.
5. En restore, descifrar y autenticar primero; después validar estructura, hashes, referencias y compatibilidad; solo entonces iniciar el preflight de conflictos.
6. Cada backend vuelve a cifrar sus secretos bajo la master key existente del destino y su AAD nativo. No reutilizar envelopes entre VLESS, VMess y certificados.
7. El restore requiere backup de seguridad legible, confirmación explícita, journal durable y rollback según el diseño aprobado. Este módulo no realiza ninguna de esas acciones.

Python no garantiza el borrado seguro de objetos `bytes` inmutables de memoria. La integración debe minimizar copias, no registrar payloads y considerar el riesgo de swap/core dumps; no afirmar zeroization garantizada.

## 6. Política funcional de secretos

La normativa `Xray-Normativa/05_Configuraciones_Perfiles/Etapa_5_Configuraciones_Perfiles.md` excluye credenciales y claves privadas por defecto. Incluir claves privadas requiere selección expresa, autorización y confirmación adicional. El contenedor criptográfico no constituye por sí solo esa autorización; la futura interfaz/orquestador deberá imponerla y reflejar el alcance en la vista previa.

Los respaldos deben contener los datos/estados actuales seleccionados y excluir historiales de versiones/modificaciones, validaciones, informes y logs. El snapshot compartido no debe convertir la conservación interna de revisiones inmutables en inclusión de todo el historial.

## 7. Pruebas

`tests/shared_backup_format.sh` prueba round-trip, aleatoriedad, contraseña incorrecta, alteración de cabecera/ciphertext, truncamiento, bytes sobrantes, magic inválido, contraseñas débiles y payload inválido. Estas pruebas no equivalen a pruebas de backup/restore integral, migración, conflictos, journal o rollback.
