# DEC-007 — Monitoreo, reintentos, fallo de agentes y hosting

**Fecha:** 2026-11-18
**Propietario:** Erick Uriel Reyes Gómez
**Origen:** Sesión de validación técnica (puntos D, E y F del feedback externo; preguntas Q18–Q22). Opciones y recomendaciones presentadas en la sesión.
**Alcance:** Registra las decisiones. Los cambios al contrato técnico que derivan de ellas se tramitan en CR-004. NO constituye aprobación de G3 ni autoriza FASE 2.

---

## Decisiones

| Pregunta | Tema | Decisión |
|---|---|---|
| Q18 | Aviso si el bot se cae (heartbeat) | **Opción B:** servicio externo de vigilancia (dead-man's switch). El propietario eligió inicialmente C, pero al definir las máquinas (ver Q22) no queda ninguna máquina encendida 24/7 distinta de la que ejecuta el bot: Laptop A se apaga. Corregido el 2026-11-18. |
| Q19 | Ubicación de Strategy Analyst y Risk Analyst | **Opción B:** filtro determinista primero; sin candidato, sin llamadas a LLM. Detalle en CR-004. |
| Q20 | Reintentos de llamadas a la IA (amplía P18) | **Opción B:** 1 reintento tras pausa breve, solo ante errores transitorios (red, saturación, límite de tasa) o respuesta que no cumple el contrato JSON; siempre dentro del límite de 5 min del ciclo. No aplica a órdenes a Binance (rigen por REQ-G-032). |
| Q21 | Agente que falla tras el reintento | **Opción A:** cualquier agente que falle termina el ciclo sin propuesta (Fail-Closed). |
| Q22 | Dónde corre SwingPilot | **Laptop B** (la antigua, encendida siempre, bajo consumo) ejecuta SwingPilot en producción. **Laptop A** (la actual, potente; se apaga) se usa para desarrollo, investigación, backtesting y experimentos de ML. Nunca guarda credenciales de producción. |

## Condiciones de Q22 (hosting en Laptop B)

Responsabilidad del propietario (operativas, no son requisitos del software):
1. **No-break** para módem de Megacable, router y antena satelital. El propietario se encarga.
2. **Configuración de la laptop:** no suspender al cerrar la tapa ni por inactividad; limitar carga al ~80% si el modelo lo permite; actualizaciones del sistema sin reinicio automático.
3. **Laptop B dedicada** a SwingPilot: disco cifrado, usuario sin privilegios para el bot, sin navegación ni otros usos.
4. **Verificado en Laptop B (2026-11-18, declarado por el propietario):**
   - Sistema operativo: Linux Mint 22 XFCE, versión con soporte de largo plazo (con actualizaciones de seguridad hasta 2029, según el ciclo de soporte de Mint 22). Cumple.
   - Batería: ~4.5 h de autonomía. Apagones más largos apagan la laptop; la posición abierta sigue protegida por el stop en Binance (REQ-G-031).
5. **Apagado limpio por batería baja:** configurar el gestor de energía para hibernar o apagar ordenadamente con batería baja, en lugar de agotarla. Al volver la luz, si la laptop no enciende sola, el propietario la enciende; SwingPilot arranca en modo seguro (REQ-G-P26).
6. **No-break:** idealmente con autonomía similar a la de la laptop (~4.5 h) para módem, router y antena; si es menor, la laptop seguirá encendida sin internet durante el resto del apagón (sin operar).

Requisitos del software derivados (en CR-004):
- Verificación de IP pública al arrancar y en cada ciclo; si cambió (p. ej. cambio a internet satelital), Fail-Closed y aviso por Telegram antes de intentar operar.
- En modo satelital no se abren operaciones nuevas; la posición abierta queda protegida por el stop en Binance (REQ-G-031).
- Reinicio automático del proceso de SwingPilot si se cae; al arrancar entra en modo seguro (REQ-G-P26).

## Condiciones de Q18 (servicio externo de vigilancia)

- El vigilante no puede correr en la misma máquina que el bot (Laptop B), y Laptop A no está encendida siempre; por eso se usa un servicio externo.
- El latido no contiene saldo, posiciones ni credenciales. La URL o clave de ping se trata como secreto (`.env`), para que nadie pueda simular latidos.
- El servicio externo avisa al propietario por su propio canal; no tiene ninguna capacidad de aprobar operaciones.

## Notas

- Con este registro queda definida la política de reintentos mencionada en REQ-G-P18 y que DEC-006 no había fijado.
- Queda pendiente la aclaración de P24 (DEC-005).
