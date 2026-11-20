# IMPL-3 «Integración cuantitativa» — Plan

**Estado:** PLANIFICACIÓN APROBADA (DEC-017, 2026-11-20). Implementación NO iniciada.
**Fuente:** architecture.md §7 fila 3; contrato v1.5; DEC-005, DEC-011, DEC-013, DEC-017.
**Criterio de salida:** las propuestas se relacionan con estrategias, inferencias y evidencia reproducible (architecture.md §7, fila 3).
**Criterios de aceptación:** `feature_list.json` → FEAT-015..022 (DEFINITIVOS PROPUESTOS, pendientes de revisión del propietario).

## 1. Alcance

| FEAT | Contenido | Bloqueado por |
|---|---|---|
| FEAT-015 | Snapshot histórica sellada (Parquet fuera de Git; manifiesto y SHA-256 en el repo) | — |
| FEAT-016 | Datos en vivo por WebSocket público: velas cerradas y resincronización | — |
| FEAT-017 | Research & Backtesting: registro de experimentos, preregistro, Walk-Forward, modelo de ejecución, evaluador; piloto Trend Following H4 | EXP-0001 (solo el preregistro del piloto) |
| FEAT-018 | Regime Engine (`REGIME_CLASSIFIED`) | CR-018 y Q42 |
| FEAT-019 | ML Engine: solo infraestructura (registro, hash, promoción, degradación) | CR-018 (solo el evento) |
| FEAT-020 | Strategy Engine (`STRATEGY_CANDIDATE`, `STRATEGY_EXIT_SIGNAL`, `NO_SETUP`) | CR-018 |
| FEAT-021 | Normalización de TRADE_PROPOSAL §3.3 → §4.1 | CR-018 |
| FEAT-022 | Ciclo Fase 1 → 4 hasta E9 (TRADE_PROPOSAL normalizada) | CR-018 |

## 2. Fuera de alcance (DEC-017)

- Operaciones reales, endpoints privados de Binance, órdenes, Risk Manager real (IMPL-4) y la cadena de ejecución (IMPL-5).
- Puesta en marcha continua en Laptop B (IMPL-5).
- Modelo ML entrenado o inferencias productivas.
- Evaluación OOS y del LOCKBOX: no se ejecutan sin autorización explícita del propietario.
- Cambios de modelos LLM o de effort.

## 3. Secuencia

1. Revisión de los criterios de FEAT-015..022 por el propietario. Después se puede empezar lo que no depende de CR-018 ni de Q42: FEAT-015, FEAT-016, FEAT-017 (salvo el preregistro del piloto mientras falte EXP-0001) y FEAT-019 AC-1..3/5.
2. CR-018 aprobada y aplicada (contrato v1.6, DEC-018) → FEAT-019 AC-4, FEAT-020, FEAT-021 y FEAT-018 con `UNCLASSIFIED`.
3. Q42 decidida → clasificación de FEAT-018.
4. Preregistro congelado del piloto (con EXP-0001) → backtest piloto en Train (tasa de trades) → Walk-Forward en Train+Val.
5. FEAT-022 en local con fixtures; corridas reales con LLM solo a petición del propietario.
6. QA independiente (≤ 2 rondas), G4 con alcance IMPL-3 y aprobación de cierre del propietario.

## 4. Datos y almacenamiento

- Snapshot: `var/snapshots/<snapshot_id>/{train_val,oos,lockbox}.parquet` (fuera de Git; `var/` ya está en `.gitignore`).
- Manifiesto en el repositorio (ubicación propuesta: `research/snapshots/<snapshot_id>.json`) con parámetros de descarga, cortes, filas, huecos, SHA-256 y versiones de librerías.
- Velas en vivo: almacenamiento local fuera de Git (propuesta: SQLite en `var/`).
- Registro de experimentos y preregistros: en el repositorio (texto y JSON), append-only.

## 5. Dependencias nuevas

Del contrato (architecture.md §5): pandas, NumPy, scikit-learn; pyarrow para Parquet; un cliente WebSocket (se elegirá al implementar FEAT-016). XGBoost y PyTorch solo con justificación en un preregistro. Esta máquina no tiene `.venv`: crearla con `requirements-dev.txt` antes de implementar.

## 6. Presupuesto de IA (DEC-017 Q47)

- Libro propio de IMPL-3 (`var/impl3_experiment_budget.db`): tope incremental USD 0.50, aviso único a USD 0.40, bloqueo a USD 0.50; se suma al tope mensual de $5 (REQ-G-096).
- **Reserva por ciclo antes de lanzarlo:** costo máximo de las 3 llamadas paralelas de la Fase 3 + la síntesis, cada una con 1 reintento. Si no cabe, el ciclo no se lanza. El mecanismo de IMPL-2 reserva llamada por llamada y se ampliará para cumplir esta condición.
- Sin gasto automático: cada corrida real la pide el propietario.

## 7. Riesgos metodológicos registrados

- **EXP-0001 como antecedente:** si usó datos que caen en el OOS o el LOCKBOX de la nueva snapshot, esas particiones no están limpias para esta hipótesis; se declara en el preregistro y puede requerir decisión del propietario.
- **Corrección por número de experimentos (P17):** debe contar EXP-0001, Mean Reversion H1 y cualquier variante probada.
- **Redundancia régimen/estrategia:** un régimen basado en EMA200/ADX duplica las condiciones del piloto (propuesta Q42 §1).
- **Tamaño de muestra:** si la tasa de trades del piloto en Train es baja, el histórico puede no alcanzar los mínimos de P15; en ese caso el experimento no pasa de DESIGN (TC-ML-014).

## 8. Documentos relacionados

- `docs/decisions/DEC-017_plan-impl3-integracion-cuantitativa.md`
- `harness/plans/IMPL-3_Q42_regime_engine_propuesta.md` (PENDIENTE DE DECISIÓN)
- `harness/change_requests/CR-018_contratos-motores-cuantitativos.md` (BORRADOR)
