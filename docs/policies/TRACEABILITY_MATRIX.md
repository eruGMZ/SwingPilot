# Matriz de Trazabilidad y Verificación (SwingPilot)

| Campo | Valor |
|---|---|
| Proyecto | SwingPilot |
| Documento | TRACEABILITY_MATRIX.md |
| Versión | 1.0 |
| Estado | BORRADOR — pendiente de aprobación humana |
| Clasificación | Documentación privada |
| Autoridad de aprobación | Propietario de SwingPilot |
| Ámbito | Trazabilidad integral del sistema |

---

## ¿Para qué sirve la matriz?

Establece el mecanismo de trazabilidad, verificación y control de cambios de SwingPilot.

La matriz debe permitir demostrar que cada requisito, política, decisión arquitectónica, contrato, control de seguridad y criterio de aceptación:

1. Tiene un origen documental identificable.
2. Cuenta con un identificador de trazabilidad único.
3. Está relacionado con los componentes responsables de satisfacerlo.
4. Tiene un método de verificación apropiado.
5. Cuenta con evidencia verificable de cumplimiento.
6. Tiene las aprobaciones requeridas según su criticidad.

La matriz no representa únicamente el avance del desarrollo. Su función es demostrar la correspondencia entre lo especificado, lo implementado y lo efectivamente verificado.

---

## ¿Qué abarca?

La matriz tendrá cobertura integral sobre los siguientes elementos:

| Categoría | Elementos incluidos |
|---|---|
| Requisitos funcionales | Comportamientos y capacidades exigidas al sistema |
| Requisitos no funcionales | Rendimiento, disponibilidad, confiabilidad y otras propiedades medibles |
| Políticas | Restricciones y reglas operativas aprobadas |
| Arquitectura | Decisiones, componentes, responsabilidades y restricciones arquitectónicas |
| Contratos API | Interfaces, estructuras, operaciones y condiciones contractuales |
| Seguridad | Amenazas, controles, mitigaciones y pruebas |
| Criterios de aceptación | Condiciones objetivas para aceptar funcionalidades o componentes |
| Implementación | Módulos, servicios, clases o componentes responsables |
| Verificación | Casos de prueba, inspecciones, análisis y resultados |
| Evidencias | Registros que demuestran el cumplimiento o incumplimiento |

El alcance comprende tanto la documentación como la implementación y su validación técnica.

---

## ¿Qué principios son obligatorios?

### Trazabilidad integral

Todo elemento aplicable debe tener una referencia de origen y relaciones suficientes para recorrer su ciclo de vida.

### Trazabilidad bidireccional

La relación debe poder recorrerse en ambas direcciones: desde un requisito hasta su implementación, pruebas y evidencias; desde un componente hasta los requisitos que justifican su existencia; desde una prueba hasta los elementos que verifica; y desde una política hasta los controles que la hacen cumplir.

### Evidencia objetiva

La existencia de documentación o código no demuestra por sí sola el cumplimiento. Un elemento solamente puede declararse `VERIFIED` cuando existe evidencia adecuada a su naturaleza y esta satisface sus criterios de verificación.

### Separación de responsabilidades

La implementación y la verificación deben distinguirse. Los agentes no podrán aprobar unilateralmente elementos críticos que ellos mismos hayan implementado.

### Conservación del origen

Los identificadores originales de los documentos fuente se conservarán. La matriz añadirá sus propios identificadores sin sustituir los existentes.

### Fail-Closed documental

Cuando falte información necesaria para demostrar cumplimiento, el elemento no podrá considerarse verificado. La ausencia de evidencia no equivale a cumplimiento.

---

## ¿Cómo se identifican los elementos?

### Identificador de trazabilidad

Cada registro tendrá un identificador único con el formato `TRC-NNN` (por ejemplo `TRC-001`, `TRC-002`, `TRC-003`).

El identificador será estable durante toda la vida del elemento. No deberá reutilizarse un identificador eliminado, reemplazado o declarado obsoleto.

### Identificadores de origen

La matriz conservará los identificadores originales cuando existan.

| ID de trazabilidad | ID de origen | Documento |
|---|---|---|
| TRC-001 | RISK-001 | RISK_POLICY.md |
| TRC-002 | REQ-001 | requirements.md |
| TRC-003 | ARCH-001 | architecture.md |

Los identificadores anteriores son ilustrativos y no constituyen una declaración de que esos identificadores ya existan en los documentos fuente.

### Referencia documental

Cada elemento deberá registrar documento de origen, sección o ubicación específica, versión del documento fuente e identificador original (si existe).

No se permitirá utilizar referencias ambiguas como "documentación general" cuando sea posible identificar una sección concreta.

---

## ¿Qué granularidad usa la matriz?

La matriz utilizará una estructura híbrida.

### Nivel individual

Cada requisito, política, decisión o control tendrá su propio registro. No se permitirá agrupar requisitos independientes cuando ello impida verificar su cumplimiento individual.

### Nivel modular

Los registros podrán agruparse por módulo o componente para evaluar cobertura total, requisitos pendientes, dependencias, incumplimientos, resultados de verificación y estado global de validación del módulo.

La agrupación modular no sustituye la trazabilidad individual.

---

## ¿Qué campos tiene cada registro?

Cada registro deberá contener, como mínimo, los siguientes campos:

| Campo | Descripción |
|---|---|
| `trace_id` | Identificador único TRC-NNN |
| `source_id` | Identificador original, si existe |
| `source_document` | Documento de origen |
| `source_section` | Sección o ubicación de origen |
| `source_version` | Versión del documento fuente |
| `element_type` | Tipo de elemento trazado |
| `description` | Descripción precisa del elemento |
| `priority` | Prioridad, cuando corresponda |
| `criticality` | Nivel de criticidad |
| `responsible_component` | Componente responsable |
| `implementation_reference` | Referencia a la implementación |
| `verification_method` | Método de verificación |
| `verification_criteria` | Criterios objetivos de cumplimiento |
| `test_references` | Identificadores de pruebas relacionadas |
| `evidence_references` | Referencias a las evidencias |
| `dependencies` | Dependencias identificadas |
| `related_elements` | Relaciones con otros registros |
| `conflicts` | Conflictos conocidos |
| `status` | Estado de trazabilidad |
| `implemented_by` | Responsable de implementación |
| `verified_by` | Responsable de verificación |
| `approved_by` | Autoridad de aprobación, cuando aplique |
| `last_verified` | Fecha de última verificación |
| `change_reference` | Referencia al cambio que afectó el registro |
| `notes` | Observaciones y limitaciones |

Los campos que no correspondan a la naturaleza del elemento podrán marcarse como no aplicables, justificando su ausencia cuando sea necesario.

---

## ¿Cómo se clasifica la criticidad?

La validación y aprobación dependerán de la criticidad del elemento.

| Nivel | Clasificación | Tratamiento |
|---|---|---|
| C1 | Crítico | Verificación independiente y aprobación humana obligatoria |
| C2 | Alto | Verificación independiente |
| C3 | Ordinario | Verificación automatizada o por agente |

La clasificación deberá justificarse según el impacto potencial de un incumplimiento.

Se consideran candidatos a C1, sujetos a evaluación: límites y restricciones de `RISK_POLICY.md`; autorización de operaciones; gestión de órdenes y posiciones; controles de seguridad sobre credenciales y secretos; mecanismos de bloqueo y protección; e integridad de registros críticos.

La clasificación no podrá utilizarse para reducir controles exigidos por una política aprobada. Los criterios definitivos de clasificación deberán detallarse y validarse durante la integración técnica.

---

## ¿Qué evidencia exige cada naturaleza de elemento?

| Naturaleza | Evidencia esperada |
|---|---|
| Requisito funcional | Implementación identificable, pruebas y resultados |
| Requisito no funcional | Métricas, pruebas y resultados medibles |
| Política de riesgo | Reglas implementadas y pruebas de invariantes |
| Decisión arquitectónica | Registro de decisión y arquitectura correspondiente |
| Contrato API | Especificación y pruebas de contrato |
| Control de seguridad | Análisis de amenazas, controles y pruebas de seguridad |
| Criterio de aceptación | Evidencia objetiva de cumplimiento |

### Requisitos de una evidencia

Toda evidencia utilizada para declarar un elemento verificado deberá permitir identificar qué se verificó; contra qué criterio se verificó; cómo se realizó la verificación; qué resultado se obtuvo; cuándo se obtuvo; quién realizó la verificación; y qué versión de la implementación o documento se verificó.

### Vigencia de evidencias

Una evidencia dejará de considerarse válida cuando un cambio afecte materialmente el elemento verificado o las condiciones bajo las cuales se obtuvo.

La evidencia histórica podrá conservarse para auditoría, pero no podrá utilizarse como demostración de cumplimiento de una versión posterior sin una evaluación de vigencia.

---

## ¿Qué estados y transiciones existen?

Cada registro utilizará uno de los siguientes estados:

| Estado | Significado |
|---|---|
| `NOT_STARTED` | No se ha iniciado el trabajo correspondiente |
| `IN_PROGRESS` | El elemento está en análisis o desarrollo |
| `IMPLEMENTED` | Existe una implementación identificada |
| `VERIFICATION_PENDING` | La implementación está terminada y espera verificación |
| `VERIFIED` | El cumplimiento fue demostrado mediante evidencia válida |
| `FAILED` | La verificación detectó incumplimiento |
| `BLOCKED` | Existe una dependencia o impedimento que impide avanzar |
| `NOT_APPLICABLE` | Se determinó justificadamente que el elemento no aplica |

### Reglas de transición

- `NOT_STARTED` podrá avanzar a `IN_PROGRESS`.
- `IN_PROGRESS` podrá avanzar a `IMPLEMENTED`.
- `IMPLEMENTED` podrá avanzar a `VERIFICATION_PENDING`.
- `VERIFICATION_PENDING` podrá avanzar a `VERIFIED` o `FAILED`.
- `BLOCKED` podrá regresar al estado correspondiente cuando se resuelva su causa.
- `FAILED` requerirá corrección y una nueva verificación antes de poder alcanzar `VERIFIED`.
- `NOT_APPLICABLE` requerirá justificación y aprobación humana.

Las transiciones deberán conservar el historial correspondiente.

### Restricciones

1. `IMPLEMENTED` nunca equivale a `VERIFIED`.
2. `BLOCKED` no equivale a cumplimiento.
3. `FAILED` no podrá ocultarse mediante un cambio directo de estado.
4. `NOT_APPLICABLE` no podrá utilizarse para eliminar requisitos incómodos o pendientes.
5. Ningún agente podrá declarar verificado un elemento crítico sin cumplir su procedimiento de aprobación.

---

## ¿Cómo se modelan relaciones, dependencias y conflictos?

La matriz deberá registrar relaciones explícitas entre requisitos, políticas, decisiones arquitectónicas, componentes, contratos, controles de seguridad, pruebas, evidencias y criterios de aceptación.

### Dependencias

Cada dependencia deberá identificar el elemento del que depende, el elemento dependiente, la naturaleza de la dependencia, la condición necesaria para resolverla y el estado de cumplimiento.

### Conflictos

Cuando dos elementos sean incompatibles o presenten contradicciones, la matriz deberá registrar identificadores involucrados, naturaleza del conflicto, documentos afectados, impacto potencial y resolución aprobada o estado pendiente.

Los agentes no podrán resolver unilateralmente conflictos que alteren políticas o decisiones aprobadas.

### Elementos huérfanos

La auditoría deberá detectar requisitos sin componente responsable; componentes sin requisito o justificación de origen; pruebas sin elementos que verifiquen; requisitos sin pruebas o método de verificación; evidencias sin referencia a un elemento; y dependencias sin resolución.

Los elementos huérfanos deberán justificarse o corregirse.

---

## ¿Cuándo se considera completa la cobertura?

La cobertura de trazabilidad se considerará completa únicamente cuando todos los elementos aplicables:

1. Estén identificados.
2. Tengan origen documental.
3. Estén relacionados con los elementos correspondientes.
4. Tengan componente responsable.
5. Cuenten con implementación identificada.
6. Tengan un método de verificación.
7. Dispongan de evidencia satisfactoria.
8. Cuenten con las aprobaciones exigidas según criticidad.
9. No mantengan dependencias críticas pendientes.

### Condiciones de exclusión

No se podrá declarar cobertura completa si existen elementos críticos en `BLOCKED` o `FAILED`; elementos aplicables sin evidencia; aprobaciones humanas obligatorias pendientes; conflictos críticos sin resolución; o dependencias críticas sin satisfacer.

Los elementos `NOT_APPLICABLE` solamente podrán excluirse del cómputo después de su justificación y aprobación humana.

### Relación con Harness Engineering

La matriz será utilizada transversalmente durante las fases y gates de Harness Engineering.

| Fase | Uso de la matriz |
|---|---|
| Fase 0 — Control documental | Registrar fuentes, versiones, integridad e identificadores |
| Fase 1 — Extracción aislada | Identificar elementos y preservar sus referencias originales |
| Fase 2 — Integración | Relacionar requisitos, políticas, arquitectura y contratos |
| Fase 3 — Verificación adversarial | Identificar contradicciones, omisiones y dependencias |
| Fase 4 — Aprobación y bloqueo | Comprobar evidencia y aprobaciones requeridas |
| Fase 5 — Implementación | Vincular registros con componentes y cambios de código |
| Fase 6 — Validación | Consolidar resultados de pruebas y cobertura |
| Fase 7 — Release | Confirmar cumplimiento de los gates de liberación |

La matriz no reemplaza los gates. Proporciona evidencia para evaluar su cumplimiento.

---

## ¿Cómo se gestionan los cambios y su impacto?

Todo cambio documental o técnico que afecte elementos trazados deberá activar una revisión de impacto.

### Procedimiento obligatorio

1. Identificar el elemento modificado.
2. Registrar el documento, componente o implementación afectada.
3. Identificar los registros relacionados y dependientes.
4. Evaluar el impacto sobre requisitos, políticas y arquitectura.
5. Identificar pruebas que deben repetirse.
6. Determinar qué evidencias pierden vigencia.
7. Identificar aprobaciones que deben renovarse.
8. Actualizar los registros afectados.
9. Registrar la referencia del cambio.
10. Verificar que no queden impactos pendientes antes de cerrar el cambio.

### Protección de decisiones aprobadas

Un cambio que afecte una política o decisión aprobada no podrá modificarla automáticamente. Será necesaria una decisión humana explícita y el correspondiente registro de cambios.

### Historial

La matriz deberá conservar el historial de cambios de estado, cambios de relaciones, modificaciones de criterios, evidencias incorporadas o invalidadas, cambios de responsables, aprobaciones y rechazos, y revisiones de impacto.

No se permitirá sobrescribir el historial para ocultar incumplimientos anteriores.

---

## ¿Cuándo y cómo se audita la matriz?

La matriz tendrá dos disparadores obligatorios de auditoría.

### Auditoría por hitos

Se ejecutará al completar cada fase o gate de Harness Engineering.

### Auditoría por cambios críticos

Se ejecutará cuando existan cambios que afecten políticas de riesgo, seguridad, arquitectura, ejecución, autorizaciones o controles críticos.

### Criterios de auditoría

Cada auditoría deberá revisar:

1. Integridad de identificadores y referencias.
2. Coherencia con las versiones vigentes de los documentos fuente.
3. Cobertura bidireccional.
4. Existencia de elementos huérfanos.
5. Relaciones y dependencias.
6. Conflictos abiertos.
7. Estados de trazabilidad.
8. Vigencia de evidencias.
9. Autoridad de verificación.
10. Aprobaciones correspondientes.
11. Impactos de cambios pendientes.
12. Cumplimiento de criterios de cobertura.

### Resultado de auditoría

La auditoría deberá generar un registro que contenga fecha, alcance, versión de la matriz, elementos revisados, hallazgos, incumplimientos, dependencias pendientes, evidencias examinadas, acciones correctivas, responsable, resultado y aprobación correspondiente.

Un resultado satisfactorio de auditoría no sustituye la aprobación humana de elementos que la requieren.

---

## ¿Quién es responsable de qué?

| Actor | Responsabilidad |
|---|---|
| Propietario de SwingPilot | Aprobar políticas, decisiones críticas y excepciones |
| Agente de análisis | Identificar y relacionar elementos documentales |
| Agente de implementación | Vincular requisitos con componentes y cambios realizados |
| Agente de verificación | Ejecutar o revisar pruebas y evidencias |
| Agente auditor | Detectar inconsistencias, omisiones y conflictos |
| Responsable de documentación | Mantener integridad, referencias e historial de la matriz |

Los roles podrán ser desempeñados por agentes distintos o por procesos especializados. Sin embargo, deberán conservarse las separaciones de autoridad exigidas por la criticidad.

---

## ¿En qué formato se mantiene la matriz?

La matriz podrá mantenerse en Markdown mediante una tabla principal y secciones complementarias cuando el volumen de registros lo requiera.

Ejemplo ilustrativo:

| TRC | Origen | Elemento | Componente | Verificación | Estado |
|---|---|---|---|---|---|
| TRC-001 | RISK_POLICY | Riesgo máximo por operación | Risk Manager | Prueba de límite de riesgo | NOT_STARTED |
| TRC-002 | RISK_POLICY | Una sola posición abierta | Execution Manager | Prueba de exclusividad | NOT_STARTED |
| TRC-003 | AI_INTEGRATION | Autorización humana | Authorization Module | Prueba de autorización | NOT_STARTED |

Los registros anteriores son ejemplos estructurales. No constituyen evidencia de implementación ni validación.

Si el volumen vuelve inmanejable una tabla única, podrán utilizarse archivos auxiliares o vistas por módulo, manteniendo un identificador y una fuente de verdad consistentes.

---

## ¿Cuándo se aprueba este documento?

`TRACEABILITY_MATRIX.md` podrá aprobarse cuando cumpla los siguientes criterios:

| ID | Criterio | Condición de aceptación |
|---|---|---|
| TMA-001 | Alcance integral | Incluye todas las categorías definidas en la sección 2 |
| TMA-002 | Identificación | Define identificadores propios y conserva los originales |
| TMA-003 | Granularidad | Permite trazabilidad individual y agrupación modular |
| TMA-004 | Evidencia | Define evidencia diferenciada según la naturaleza del elemento |
| TMA-005 | Estados | Define los ocho estados y sus restricciones |
| TMA-006 | Autoridad | Establece validación según criticidad |
| TMA-007 | Relaciones | Define trazabilidad bidireccional y dependencias |
| TMA-008 | Cobertura | Define condiciones integrales para declarar cobertura completa |
| TMA-009 | Cambios | Exige análisis de impacto y conservación del historial |
| TMA-010 | Auditoría | Define auditorías por hitos y cambios críticos |
| TMA-011 | Consistencia | No contradice las políticas ni decisiones aprobadas |
| TMA-012 | Aplicabilidad | Permite distinguir elementos no aplicables de elementos pendientes |

La aprobación del documento no demuestra que todos los requisitos de SwingPilot estén implementados o verificados. Esa condición deberá demostrarse progresivamente mediante la matriz y sus evidencias.

---

## ¿Qué falta definir a nivel técnico?

Los siguientes aspectos deberán resolverse durante la integración técnica, sin alterar las decisiones aprobadas:

- Esquema definitivo de clasificación de criticidad.
- Taxonomía completa de tipos de elementos.
- Reglas técnicas de generación y reserva de identificadores.
- Formato definitivo de almacenamiento.
- Convenciones de referencias a código, commits, PR y pruebas.
- Mecanismo de registro histórico y control de versiones.
- Cálculo automatizado de cobertura.

Y además:

- Integración con los gates de Harness Engineering.
- Procedimiento de reconciliación cuando existan referencias documentales obsoletas.
- Criterios de independencia de los agentes verificadores.

Estos pendientes no autorizan a los agentes a inventar reglas ni a asumir decisiones del propietario.

---

## ¿Cómo se versiona este documento?

| Versión | Fecha | Descripción | Estado |
|---|---|---|---|
| 1.0 | 2026-11-11 | Primera especificación consolidada a partir de diez decisiones aprobadas | BORRADOR |

[RESUELTO — DEC-001 / CR-001: estado canónico BORRADOR — pendiente de aprobación humana.]

Cualquier modificación futura deberá registrar versión anterior, versión nueva, motivo, secciones afectadas, impacto sobre registros existentes y aprobación correspondiente.
