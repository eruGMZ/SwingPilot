"""Solo pruebas: siembra un APPROVED *histórico* (anterior a B8.2) en un registro sintético.

Reproduce la forma exacta del registro que `transition` escribía antes de B8.2, tras exigir las mismas
comprobaciones previas (HUMAN_REVIEW, propietario, línea `AUTORIZA: EXP APPROVED`). No es una credencial
`ApprovalCheck` ni una vía de producción: usa el bloqueo y `_write` del propio registro. Las pruebas de
la transición vinculante (ET-8 genuino) están en test_cr024_b8_2_approval_transition.py."""


def seed_historical_approval(reg, eid, decision_ref, actor="propietario"):
    with reg._locked():
        assert reg.state(eid) == "HUMAN_REVIEW", "solo se siembra desde HUMAN_REVIEW"
        why = reg.decision_ok(decision_ref, eid, target_state="APPROVED")
        assert why is None, why
        return reg._write({"kind": "TRANSITION", "experiment_id": eid, "from": "HUMAN_REVIEW", "to": "APPROVED",
                           "actor": actor, "evidence": {"decision_ref": decision_ref}, "reason": ""})


def legacy_promotion_check(exps):
    """Solo pruebas heredadas (infraestructura de motores/ML con APPROVED sembrado): PromotionCheck sin ET-9,
    construido con la credencial privada (precedente `legacy_freeze_check`). Las pruebas de ET-9 genuino están
    en test_cr024_b8_3_promotion_eligibility.py."""
    from swingpilot.research.experiments import _PROMOTION_CHECK_KEY, PromotionCheck
    return PromotionCheck(_PROMOTION_CHECK_KEY, lambda records, experiment_id: None, exps)
