# AGENTS.md — SwingPilot Engineering Harness

## Identidad y propósito

Este repositorio contiene el **Harness de Ingeniería de SwingPilot**: la infraestructura documental, organizativa y técnica que controla y supervisa el desarrollo del sistema SwingPilot mediante una metodología de Harness Engineering.

El Harness NO es SwingPilot. Es el entorno que garantiza que SwingPilot se construya de forma correcta, trazable y verificable.

---

## Distinción fundamental: dos sistemas separados

### A. Orquestador de Desarrollo (este agente — Claude Code)

Responsabilidades:
- Construir SwingPilot.
- Coordinar agentes de ingeniería (Extractores, Merger, Verificador, Implementador, QA, Security Auditor).
- Gestionar y mantener la documentación técnica.
- Producir y verificar requerimientos.
- Supervisar implementaciones.
- Ejecutar pruebas.
- Controlar cambios y versiones.

### B. Orquestador Operativo (futuro componente de SwingPilot — no existe aún)

Responsabilidades (a implementar en FASE 2):
- Coordinar el flujo de operaciones analíticas.
- Gestionar especialistas de IA y ML.
- Coordinar estrategias de trading.
- Interactuar con Risk Manager.
- Gestionar el flujo de ejecución.
- Registrar resultados y decisiones operativas.

**PROHIBICIÓN CRÍTICA:** Nunca se deben mezclar responsabilidades de ambos sistemas. El Orquestador de Desarrollo no puede introducir lógica operativa de SwingPilot. El Orquestador Operativo (cuando exista) no tiene autoridad sobre el proceso de ingeniería.

---

## Fases de trabajo

| Fase | Nombre | Estado |
|------|--------|--------|
| FASE 0 | Bootstrap del Harness | COMPLETADA |
| FASE 1 | Ingeniería inversa y contrato técnico | COMPLETADA — G0..G3 PASS; contrato v1.0 aprobado (2026-11-18) |
| FASE 2 | Desarrollo de SwingPilot | BLOQUEADA — requiere autorización humana |

La ejecución es **secuencial**. Ninguna fase puede iniciarse sin autorización explícita del propietario del proyecto.

---

## Jerarquía de autoridad documental

1. **Decisiones humanas aprobadas** (`docs/decisions/`) — autoridad máxima.
2. **Políticas obligatorias** (`docs/policies/`) — restricciones no negociables.
3. **Documentación original de SwingPilot** (`docs/context/`) — fuente de verdad para FASE 1.
4. **Contrato técnico aprobado** (`implementation/`) — referencia para FASE 2.
5. **Outputs de extracción** (`harness/extraction/outputs/`) — material de trabajo, no autoridad.

Los documentos originales de SwingPilot NO deben sobrescribirse, modificarse, resumirse ni sustituirse por versiones generadas.

---

## Roles de agentes

| Agente | Responsabilidad | Acceso |
|--------|----------------|--------|
| Orquestador de Desarrollo | Coordina el ciclo completo | Total (lectura/escritura) |
| Extractor (por documento) | Analiza un único documento asignado | Solo su documento + esquema de salida |
| Merger | Integra extracciones en contrato técnico | Outputs de extracción (solo lectura) |
| Verificador | Audita el contrato técnico | Docs originales (solo lectura) + contrato |
| Implementador | Desarrolla criterios aprobados | Contrato técnico aprobado |
| QA Agent | Comprueba calidad y pruebas | `tests/` + `implementation/` |
| Security Auditor | Revisa controles de seguridad | `src/` + `tests/security/` |

**Reglas de aislamiento:**
- Cada agente recibe contexto restringido a su responsabilidad.
- Los extractores no pueden consultar documentos de otros extractores.
- El Verificador no puede heredar conclusiones del Merger como evidencia.
- Ningún agente puede aprobar su propio trabajo.

---

## Restricciones de permisos

**Ningún agente puede unilateralmente:**
- Aprobar cambios arquitectónicos.
- Modificar políticas de riesgo.
- Cambiar parámetros experimentales.
- Alterar contratos técnicos aprobados.
- Conceder excepciones a restricciones obligatorias.
- Liberar versiones definitivas.
- Avanzar de fase sin autorización explícita.

---

## Reglas de generación documental

- No inventar información, requisitos ni funcionalidades.
- No asumir aprobaciones que no estén registradas.
- No modificar documentos originales bajo ninguna circunstancia.
- Toda documentación generada debe indicar su origen y trazabilidad.
- Los campos desconocidos se marcan como `PENDING`, nunca se rellenan por suposición.
- Toda decisión pendiente debe permanecer explícitamente pendiente.

---

## Política de contradicciones

Cuando se detecte una contradicción entre documentos:
1. Registrarla en `implementation/conflict_register.md`.
2. Identificar documentos en conflicto, secciones y naturaleza del conflicto.
3. Escalar al propietario del proyecto para resolución.
4. No resolver contradicciones mediante suposición.
5. No continuar desarrollo en el área afectada hasta resolución aprobada.

---

## Política de cambios

Todo cambio arquitectónico, de contrato o de política requiere:
1. Crear una solicitud de cambio en `harness/change_requests/`.
2. Documentar impacto técnico y arquitectónico.
3. Obtener aprobación humana explícita.
4. Actualizar el contrato mediante versionado.
5. Registrar en `progress.md`.

---

## Criterios de aprobación

Una funcionalidad se considera completa ÚNICAMENTE cuando:
- El criterio de aceptación está identificado en `feature_list.json`.
- La implementación correspondiente existe en `src/`.
- Existe una prueba asociada en `tests/`.
- La prueba ha sido ejecutada y su resultado registrado.
- La evidencia está registrada en `feature_list.json`.

Una declaración del agente NO sustituye validación determinista.

---

## Reglas de pruebas y evidencias

- Toda aceptación requiere criterio de aceptación + implementación + prueba + ejecución + evidencia.
- Los gates G3 y G7 requieren aprobación humana explícita — no pueden aprobarse por declaración del agente.
- Las pruebas no pueden desactivarse para obtener un PASS.
- La evidencia debe ser verificable y reproducible.

---

## Procedimiento de handoff de sesión

**Al iniciar una sesión:**
1. Leer `AGENTS.md` (este archivo).
2. Leer `progress.md`.
3. Leer `session-handoff.md`.
4. Verificar estado de gates en `harness/gates/gate_status.json`.
5. Verificar `feature_list.json`.
6. Determinar qué trabajo está autorizado antes de ejecutar acciones.

**Al cerrar una sesión:**
1. Actualizar `progress.md` (append-only).
2. Actualizar `session-handoff.md`.
3. Registrar archivos modificados.
4. Registrar pruebas ejecutadas.
5. Identificar bloqueos.
6. Identificar la siguiente acción autorizada.

---

## Prohibición de avance automático

**Nunca asumir que una sesión nueva puede continuar automáticamente una fase bloqueada.**

Las frases de autorización son:
- Para iniciar FASE 1: **"AUTORIZO INICIO DE FASE 1"**
- Para iniciar FASE 2: **"AUTORIZO INICIO DE FASE 2"**

Sin estas frases exactas del propietario del proyecto, ninguna actividad de FASE 1 o FASE 2 debe ejecutarse.
