# Auditoría B3 — creación de usuario y conexión VLESS-WS-TLS

**Fecha:** 2026-11-05
**Dictamen:** PASS en el alcance aislado autorizado; ACEPTADA FORMALMENTE por el propietario el 2026-11-05 y autorizada para publicación en la rama de desarrollo.

## 1. Matriz de trazabilidad

| Requisito B3 | Implementación reutilizada/nueva | Evidencia | Resultado |
|---|---|---|---|
| Crear/seleccionar usuario | Usuarios V2; flujo contextual nuevo | tests/users_v2_menu.sh | PASS |
| UUID único | users_association_create existente | Suite Usuarios V2 | PASS |
| Asociar usuario a conexión seleccionada | Argumentos contextuales en Usuarios V2 | Prueba de identidad nueva + asociación | PASS |
| Evitar conexión no elegible | Guarda VLESS-WS-TLS/draft/runtime_applied=false | Prueba contextual y revisión de código | PASS |
| Componer inbound y clientes | I-01/I-02/I-03 | tests/profiles_vless_composer_menu.sh | PASS |
| Validar revisión exacta | xray_profile_validation.py | Integración con Xray 26.10.31 | PASS |
| Exportar cliente | I-04 | Pruebas del exportador | PASS |
| Exigir revisión validada | Cambio B3 en exportador | Test de revisión pending | PASS |
| SNI cubierto por SAN | Certificate Store + validador B3 | Tests SAN exacto, wildcard, mismatch y endpoint | PASS |
| Mantener runtime intacto | Flujos de composición/exportación | runtime_changed=false; service_started=false | PASS |

## 2. Resultados

- Python: 186/186.
- Bash: 61/61.
- Exportador B3 focal: 11/11.
- Flujo contextual Usuarios V2: PASS.
- Integración compositor → validación Xray 26.10.31 → exportación: PASS.
- py_compile/compileall, bash -n global, ShellCheck -S error, git diff --check e install.sh --check: PASS.

## 3. Hallazgos resueltos

1. El menú de conexión no ofrecía una acción directa para crear/asociar usuarios sobre esa conexión. Se añadió flujo contextual que reutiliza Usuarios V2.
2. El exportador permitía revisión pendiente. Ahora exige manifiesto de la revisión exacta con Xray PASS.
3. El exportador no comprobaba correspondencia entre SNI y certificado. Ahora comprueba SAN DNS exacto o wildcard de un nivel, usando endpoint como nombre efectivo cuando no hay SNI explícito.
4. El flujo integral no estaba probado desde composición hasta exportación. Se amplió la integración para ejecutar el validador real con Xray 26.10.31.

## 4. Límites residuales

- Los endpoints IP se rechazan en este recorrido si no hay SNI DNS verificable, porque el catálogo central conserva SAN DNS y todavía no expone SAN IP.
- No se ha probado cliente NetMod real, DNS público, WAN, emisión ACME real, listener, firewall, publicación de perfil ni aplicación runtime.
- La prueba Xray valida la configuración, no la conectividad externa.
- Los avisos de obsolescencia WebSocket se conservan por decisión previa; no se cambió el transporte.
- No se cierra Etapa 2, 3, 4 o 5.

## 5. Seguridad y alcance

Todas las operaciones se realizaron en fixtures temporales. No hubo dependencias nuevas, lectura de clave maestra real, operaciones live, systemctl, cambios runtime, certificados persistentes, DNS, firewall, puertos, red, VPS de pruebas, main o Xray-Normativa.

## 6. Dictamen

B3 queda IMPLEMENTADA, VERIFICADA, AUDITADA y ACEPTADA FORMALMENTE por el propietario el 2026-11-05, con las limitaciones de esta auditoría. El propietario autorizó commit/push exclusivamente en `design/user-identity-association-v1`; publicación y sincronización se registran tras verificar el push. La aceptación no cierra Etapas 2, 3 o 4 ni autoriza pruebas NetMod/WAN o despliegue live.
