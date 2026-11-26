"""Credencial de consumo de prueba (B6.3): como `FreezeCheck(_FREEZE_CHECK_KEY, ...)` en las pruebas
existentes, construye un `ConsumptionCheck` con la clave privada y una comprobación que acepta.
Importación diferida: las pruebas fijan `sys.path` antes de importar `swingpilot`."""


def ok_consumption_check(fn=None):
    from swingpilot.research.experiments import _CONSUMPTION_CHECK_KEY, ConsumptionCheck
    return ConsumptionCheck(_CONSUMPTION_CHECK_KEY, fn or (lambda records, snapshot_id, partition, experiment_id,
                                                           decision_ref: None))
