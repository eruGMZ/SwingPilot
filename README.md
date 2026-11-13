# SwingPilot — Engineering Harness

## ¿Qué es SwingPilot Engineering Harness?

SwingPilot Engineering Harness es la infraestructura documental, organizativa y técnica que controla el desarrollo del sistema SwingPilot mediante una metodología de ingeniería controlada (Harness Engineering).

No es el sistema SwingPilot en sí mismo. Es el entorno que garantiza que SwingPilot se construya de forma correcta, trazable y verificable, con autorización humana en cada punto de control crítico.

## ¿Qué problema resuelve?

El desarrollo de sistemas complejos — especialmente aquellos con decisiones financieras, lógica cuantitativa y múltiples agentes de IA — requiere:

- Trazabilidad de cada requisito desde su origen documental hasta su implementación.
- Control de cambios formal y auditado.
- Separación clara entre el sistema de ingeniería y el sistema operativo.
- Evidencia verificable de cumplimiento, no declaraciones.
- Autoridad humana en decisiones críticas.

Este Harness establece esas garantías antes de que exista una sola línea de código funcional.

## Organización del repositorio

```
SwingPilot/
├── AGENTS.md              — instrucciones para todos los agentes de desarrollo
├── README.md              — este archivo
├── feature_list.json      — registro de criterios de aceptación
├── progress.md            — log cronológico de actividades (append-only)
├── session-handoff.md     — contexto para retomar sesiones
├── init.sh                — verificación del entorno
│
├── harness/               — infraestructura del Harness Engineering
│   ├── manifest.json      — inventario de fuentes documentales
│   ├── extraction/        — esquemas y outputs de extractores
│   ├── merge/             — workspace del agente Merger
│   ├── verification/      — esquemas y reportes del Verificador
│   ├── gates/             — estado de los gates de control
│   └── change_requests/   — solicitudes de cambio formales
│
├── docs/                  — documentación del proyecto
│   ├── context/           — documentación original de SwingPilot (fuente de verdad)
│   ├── decisions/         — decisiones humanas aprobadas
│   └── policies/          — políticas obligatorias
│
├── implementation/        — contrato técnico (producido en FASE 1)
│   ├── requirements.md
│   ├── architecture.md
│   ├── api_contracts.md
│   ├── data_flow.md
│   ├── test_plan.md
│   └── conflict_register.md
│
├── scripts/               — scripts de validación del Harness
├── src/                   — código fuente de SwingPilot (FASE 2)
├── tests/                 — pruebas
└── release/               — artefactos de release
```

## Fases del proyecto

| Fase | Nombre | Estado |
|------|--------|--------|
| FASE 0 | Bootstrap del Harness | COMPLETADA |
| FASE 1 | Ingeniería inversa y contrato técnico | BLOQUEADA |
| FASE 2 | Desarrollo e implementación | BLOQUEADA |

La ejecución es **secuencial**. Cada fase requiere autorización humana explícita para iniciarse.

## Cómo iniciar una sesión de trabajo

1. Leer `AGENTS.md` para entender las reglas vigentes.
2. Ejecutar `./init.sh` para verificar el estado del entorno.
3. Leer `session-handoff.md` para conocer el contexto de la sesión anterior.
4. Verificar `harness/gates/gate_status.json` para saber qué gates están activos.
5. Leer `progress.md` para conocer el historial reciente.
6. Actuar únicamente dentro de la fase autorizada.

## Estado actual

**FASE 0 COMPLETADA.** El Harness está inicializado y listo para recibir la documentación original de SwingPilot en `docs/context/`.

Aguardando incorporación documental y autorización humana para iniciar FASE 1.
