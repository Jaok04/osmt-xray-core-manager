# Auditoría interna H6-G3 — 2026-11-08

**Repositorio:** Jaok04/xray-core-manager  
**Rama:** design/user-identity-association-v1  
**HEAD revisado:** c026cab46b141fad95aa7561bd7258f7bbac5f42  
**Revisor:** misma sesión que participó en el desarrollo.  
**Naturaleza:** revisión interna adversarial; no independiente.  
**Dictamen:** **PASS CON LIMITACIONES — G3-A/B/C/D, alcance fixture, después de corregir el hallazgo H6G3-INT-01.**

## 1. Alcance

Se revisaron el contrato G3, los documentos de implementación A/B/C/D y segunda pasada, el publicador R-04, el orquestador R-05, journal, adaptador fixture, adaptador de servicio, puente xray_service.sh, backend live aislado, lector de evidencia y suites relacionadas. La revisión se hizo contra el tip de la rama autorizada. La VPS de desarrollo /opt/xray-manager coincidía con el HEAD indicado y el árbol estaba limpio antes de iniciar las modificaciones correctivas.

La revisión no se presenta como independiente. Por instrucción expresa del propietario, no se solicitará revisor externo: el desarrollo, las revisiones y las correcciones se realizan aquí.

## 2. Hallazgo adversarial

### H6G3-INT-01 — HIGH — snapshot corrupto deja R-05 en rollback_started

**Ubicación:** scripts/xray_runtime_orchestrator.py, función _restore_after_failure().

**Escenario reproducible:**
1. Crear una operación R-05 fixture con estado de servicio active.
2. Interrumpir después de publicar (crash_at="after_published"), antes de la transición del servicio.
3. Corromper snapshot.json.
4. Invocar _restore_after_failure().

**Resultado antes de la corrección:**
- La recuperación propagaba RuntimeJournalError: Metadatos snapshot no contiene JSON estricto.
- El journal permanecía en rollback_started.
- No se persistía RECOVERY_REQUIRED; una recuperación posterior repetía el fallo.

La reproducción se ejecutó en fixtures de la VPS de desarrollo. No se modificó runtime real ni se invocó systemd.

**Corrección aplicada:**
- _restore_after_failure() captura journal.RuntimeJournalError y OSError al invocar _rollback_locked().
- Vuelve a leer el journal, marca config_status=failed y service_status=not_started, y persiste RECOVERY_REQUIRED.
- No continúa a una mutación del servicio y conserva los bytes runtime publicados para inspección manual.

**Prueba de regresión:** tests/test_xray_runtime_orchestrator.py::RuntimeOrchestratorTests::test_corrupt_snapshot_during_orchestrator_rollback_persists_recovery_required.

La prueba verifica el estado terminal, que el hash runtime publicado no se altera, que no se emite restore del servicio y que la recuperación posterior devuelve NO_OP.

## 3. Validaciones posteriores a la corrección

Ejecutadas en Implementación-Xray, Ubuntu 24.04.4, /opt/xray-manager:

- python3 -B -m unittest discover -s tests -p "test_*.py" — **571/571 PASS**.
- Prueba focal nueva de snapshot corrupto — **1/1 PASS**.
- Suites tests/*.sh — **63/63 PASS**.
- bash -n global sobre módulos/scripts/instalador — **PASS**.
- shellcheck -S error install.sh modules/*.sh scripts/*.sh tests/*.sh — **PASS**.
- bash install.sh --check — **PASS**, sin modificar el sistema.
- git diff --check — **PASS**.

Las pruebas automatizadas usan fixtures y dobles. No se ejecutó systemctl real, no se inició/detuvo/reinició Xray, no se publicó en /etc/xray, ni se modificaron certificados, DNS, firewall, puertos o red. La VPS Pruebas no se utilizó.

## 4. Aislamiento y alcance actualizado

R-05 continúa usando xray_runtime_service_adapter como backend fixture predeterminado; el orquestador R-05 no importa ni instancia LiveRuntimeBackend. La evidencia del lector fixture conserva environment=fixture y no puede autorizar acciones del backend live.

**Actualización necesaria del paquete:** el menú ya contiene dos rutas distintas: opción 11 para R-05 fixture y opción 12 para el puente explícito xray_runtime_live_apply_bridge.py. Por tanto, la antigua comprobación literal “el menú no importa/instancia backend live” quedó obsoleta por la integración posterior del puente dedicado. La comprobación correcta es que R-05 siga aislado y que la opción live sólo use el puente dedicado, su journal/evidencia live, confirmación doble y sus gates fail-closed. Esta revisión confirma la separación a nivel de imports del orquestador y la ruta explícita observada en el menú, pero **no constituye auditoría completa del puente live**.

## 5. Limitaciones y dictamen

El resultado **PASS CON LIMITACIONES** se limita a G3-A/B/C/D en fixtures y a las rutas de aislamiento descritas. No acredita:
1. rollback live completo de archivo y proceso (F-05);
2. reconciliación durable completa del backend live (F-04);
3. configuración efectivamente cargada en memoria por Xray;
4. funcionamiento del primer servicio real ni conectividad externa;
5. auditoría completa de todos los módulos del puente live posterior a G3.

El primer despliegue real permanece bloqueado hasta completar aquí la revisión adversarial del puente live y sus dependencias, resolver hallazgos y obtener autorización específica para las operaciones reales. No se requiere ni se solicitará revisor externo.

**Conclusión:** el defecto HIGH de snapshot corrupto en el rollback R-05 fixture quedó reproducido, corregido y cubierto por regresión. El alcance fixture G3 queda **PASS CON LIMITACIONES**; no se declara habilitado el despliegue live.
