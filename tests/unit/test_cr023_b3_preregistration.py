"""CR-023 bloque B3 — preregistro, frontera de independencia, ET-1, DEVIATION de independencia y
cargador Train-only del piloto de tasa (§C.3, §C.4, §C.5, §C.7.4, §C.8, §C.9 ET-1, §D.2).

Solo datos sintéticos y directorios temporales (`tmp_path`): ningún registro real, ninguna carpeta
`research/preregistrations/` del repositorio, ninguna snapshot real, OOS ni LOCKBOX. Los ayudantes
públicos de la cabecera (`cr023_fields`, `base_content`, `register_confirmatory`, `store_for`,
`freeze_in_registry`) los reutilizan las pruebas heredadas adaptadas a CR-023.
"""
import copy
import hashlib
import json
import os
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from historical_approval import seed_historical_approval  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from swingpilot.research import boundary as B  # noqa: E402
from swingpilot.research import preregistration as PR  # noqa: E402
from swingpilot.research.experiments import (_FREEZE_CHECK_KEY, ExperimentError, ExperimentRegistry,  # noqa: E402
                                          FreezeCheck)
from swingpilot.research.partitions import PartitionAccessError, PartitionLoader  # noqa: E402
from swingpilot.research.preregistration import (PreregistrationError, build_freeze_check, freeze_evidence,  # noqa: E402
                                                 check_min_history, confirmatory_findings, freeze,
                                                 min_history_months, preregister)
from swingpilot.research.prereg_store import (PreregistrationStore, PreregStoreError,  # noqa: E402
                                              PreregStoreWriteUncertain)

SHA_A, SHA_B = "a" * 64, "b" * 64
WF = {"train_months": 24, "embargo_months": 2, "test_months": 6, "step_months": 6,
      "roll_frequency": "6M", "n_windows": 2}
PILOT_ID = "EXP-0200"
B_DEFAULT = "2027-03-01T00:00:00Z"          # ≥ todo b_not_before obligatorio (el mayor: 2026-11-20)
EVIDENCE_REF = "SwingPilot@abc1234:docs/decisions/DEC-999_prueba.md"
ACTOR = "orquestador"


# --- ayudantes públicos (también los usan las pruebas heredadas) ------------------------------------

def inventory(deviation_ids=(), extra=()):
    """Inventario mínimo obligatorio (decisión 4 del propietario) más entradas adicionales opcionales."""
    entries = [dict(m, evidence=list(m["evidence"]), note="prueba sintética") for m in B.MANDATORY_EXPOSURES]
    entries.extend(copy.deepcopy(list(extra)))
    return {"entries": entries, "general_familiarity_limitation": "familiaridad general con el histórico de BTC/USDT",
            "independence_deviation_ids": list(deviation_ids), "scope": "BTC/USDT"}


def confirmatory_boundary(b=B_DEFAULT, l_oos=12, l_lb=12, k=1, deviation_ids=()):
    return {"confirmatory_eligible": True, "B": b, "L_oos_months": l_oos, "L_lb_months": l_lb, "k": k,
            "calendar_rule": "FIXED_CALENDAR_NO_EXTENSION",
            "open_positions_rule": "FORCED_CLOSE_AT_LAST_CLOSED_CANDLE", "scope": "BTC/USDT",
            "exposure_inventory": inventory(deviation_ids)}


def cr023_fields(planned=("A",), *, pilot=False, pilot_id=PILOT_ID, snapshot_id="SNAP-0001", tv_sha=SHA_A,
                 d_dev="2021-06-17", b=B_DEFAULT, rate=3.0, k=1, l_oos=12, l_lb=12, available=100.0,
                 deviation_ids=()):
    """Campos nuevos de CR-023 (C.5) para un preregistro sintético válido, confirmatorio o piloto."""
    snap = {"snapshot_id": snapshot_id, "train_val_sha256": tv_sha, "d_dev": d_dev}
    if pilot:
        return {"independence_boundary": dict(B.PILOT_BOUNDARY), "conditioning_components": {"declaration": "NONE"},
                "snapshot": snap, "observed_trade_rate_per_month": B.PILOT_RATE, "trade_rate_source": "train_only",
                "min_history": dict(B.PILOT_MIN_HISTORY)}
    return {"independence_boundary": confirmatory_boundary(b, l_oos, l_lb, k, deviation_ids),
            "conditioning_components": {"declaration": "NONE"}, "snapshot": snap,
            "observed_trade_rate_per_month": rate,
            "trade_rate_source": {"scope": "train_only", "pilot_experiment_id": pilot_id},
            "min_history": {"required_months": round(max(38, 100 / rate), 2),
                            "window_min_months": round(k * 30 / rate, 2), "available_months": available, "ok": True},
            "model_config": {"strategy_id": "mean_reversion_h4", "strategy_sha256": SHA_A,
                             "config_sha256": {c: SHA_B for c in planned}}}


def base_content(eid, trials_count, planned=("A",), *, rule=None, metrics=("sharpe",), **fields):
    """Preregistro sintético completo (REQUIRED_FIELDS); `fields` se pasa a `cr023_fields`."""
    p = {k: f"<{k}>" for k in ("research_question", "hypothesis", "null_hypothesis", "justification", "universe",
                               "period", "variables", "entry_rules", "exit_rules", "data_split", "costs",
                               "acceptance_criteria", "rejection_criteria", "limitations", "execution_model",
                               "regime_declaration", "sharpe_definition")}
    p.update(experiment_id=eid, timeframes=["H4"], wf_design=dict(WF), label_horizon_months=1, antecedents=["-"],
             statistical_tests={"dsr_min_probability": 0.95}, metrics=list(metrics), trials_count=trials_count,
             candidate_selection_rule=rule or f"PRIMARY {planned[0]}")
    p.update(cr023_fields(planned, **fields))
    if "model_config" not in p:
        p["model_config"] = "<model_config>"
    return p


def legacy_freeze_check():
    """Solo pruebas heredadas (CR-020/CR-021): congelación sin las comprobaciones de ET-1, construida
    deliberadamente con la credencial privada (B3-01: el registro ya no acepta un invocable arbitrario)."""
    from swingpilot.research.experiments import _FREEZE_CHECK_KEY, FreezeCheck
    return FreezeCheck(_FREEZE_CHECK_KEY, lambda records, experiment_id, evidence: None)


def store_for(reg):
    """Almacén temporal junto al registro de la prueba (nunca el del repositorio)."""
    return PreregistrationStore(Path(reg.path).parent / "preregistrations")


def freeze_in_registry(reg, fz, *, store=None):
    """Congela por la vía sencilla de las pruebas heredadas (CR-020/CR-021, no la frontera): escribe el
    contenido en el almacén y registra PREREGISTERED con la clase CONFIRMATORY y un `freeze_check` nulo.
    Las comprobaciones de ET-1 las ejercita `preregister` en las pruebas de este archivo."""
    (store or store_for(reg)).write_frozen(fz)
    return reg.transition(fz.experiment_id, "PREREGISTERED", actor=ACTOR, freeze_check=legacy_freeze_check(),
                          evidence={"preregistration_sha256": fz.sha256, "min_history_ok": True,
                                    "independence_class": "CONFIRMATORY",
                                    "trials_accounting": fz.content["trials_count"]})


def register_confirmatory(reg, eid, planned=("A",), *, rule=None, store=None, manifest=None):
    """Experimento en DESIGN → PREREGISTERED con un preregistro confirmatorio sintético almacenado.
    `manifest`: liga el preregistro a la snapshot que usará el cargador (FIX-A)."""
    kw = {} if manifest is None else dict(snapshot_id=manifest["snapshot_id"],
                                           tv_sha=manifest["files"]["train_val"]["sha256"], d_dev=manifest["d_dev"])
    fz = freeze(base_content(eid, reg.trials_accounting(eid, list(planned)), planned, rule=rule, **kw))
    freeze_in_registry(reg, fz, store=store)
    return fz


# --- fábricas de este archivo ----------------------------------------------------------------------

def _dev_days(n):
    return (datetime(2017, 8, 17, tzinfo=timezone.utc) + timedelta(days=n)).strftime("%Y-%m-%d")


LONG_DAYS, LONG_DEV_DAYS = 1500, 1400            # ≈ 46 meses de desarrollo ≥ 38


def _long_binance():
    from test_snapshot import DAY_MS, H, LISTING, START, SmallBinance, interval_ms
    server = START + LONG_DAYS * DAY_MS + 5 * H + 7

    class LongBinance(SmallBinance):
        def __call__(self, url):
            u = urllib.parse.urlparse(url)
            q = dict(urllib.parse.parse_qsl(u.query))
            if u.path == "/api/v3/time":
                return {"serverTime": server}
            iv = q["interval"]
            step = interval_ms(iv)
            first = START if iv == "1d" else LISTING
            t = max((int(q["startTime"]) + step - 1) // step * step, first)
            end, rows = int(q.get("endTime", server)), []
            while t <= min(end, server) and len(rows) < int(q["limit"]):
                p = 1000 + (t // step) % 50
                rows.append([t, str(p), str(p + 5), str(p - 5), str(p + 1), "3.5", t + step - 1, "0", 1, "0", "0", "0"])
                t += step
            return rows
    return LongBinance()


@pytest.fixture(scope="module")
def dev_snap(tmp_path_factory):
    """Snapshot de desarrollo sintética de ≈ 46 meses, construida una vez (Binance simulado)."""
    from swingpilot.market_data import BinancePublicClient, SyntheticTransport
    from swingpilot.research.snapshot import build_snapshot
    tmp = tmp_path_factory.mktemp("devsnap")
    res = build_snapshot(BinancePublicClient(transport=SyntheticTransport(_long_binance())), "SNAP-TEST", tmp / "var" / "snapshots",
                         tmp / "research" / "snapshots", d_dev=_dev_days(LONG_DEV_DAYS), reserved_windows=[],
                         injected_only=True)
    return res, tmp / "var" / "snapshots"


class Env:
    """Registro, almacén y snapshot de desarrollo temporales de una prueba."""

    def __init__(self, tmp, res, data_root):
        self.tmp, self.res, self.data_root = tmp, res, data_root
        dec = tmp / "decisions"
        dec.mkdir()
        (dec / "DEC-900_ok.md").write_text("".join(
            f"AUTORIZA: EXP-{n:04d} {st}\n" for n in range(100, 400) for st in ("OOS_EVALUATION", "APPROVED")))
        self.reg = ExperimentRegistry(tmp / "registry.jsonl", dec)
        self.store = PreregistrationStore(tmp / "preregistrations")
        self.manifest = res.manifest

    def fields(self, planned=("A",), **kw):
        m = self.manifest
        kw.setdefault("snapshot_id", m["snapshot_id"])
        kw.setdefault("tv_sha", m["files"]["train_val"]["sha256"])
        kw.setdefault("d_dev", m["d_dev"])
        kw.setdefault("available", round(B.available_months(m["d_dev_ms"], m["range"]["start_ms"]), 2))
        return kw

    def design(self, eid):
        self.reg.create(eid, "prueba", actor=ACTOR)
        self.reg.transition(eid, "DESIGN", actor=ACTOR)

    def content(self, eid, planned=("A",), mutate=None, **kw):
        trials = self.reg.trials_accounting(eid, list(planned))
        c = base_content(eid, trials, planned, **self.fields(planned, **kw))
        if mutate:
            mutate(c)
        return c

    def frozen(self, eid, planned=("A",), mutate=None, **kw):
        return freeze(self.content(eid, planned, mutate, **kw))

    def prereg(self, fz, **kw):
        args = dict(store=self.store, dev_manifest_path=self.res.manifest_path, data_root=self.data_root, actor=ACTOR)
        args.update(kw)
        return preregister(self.reg, fz, **args)

    def pilot(self, eid=PILOT_ID, planned=("A",)):
        self.design(eid)
        fz = self.frozen(eid, planned, pilot=True)
        self.prereg(fz)
        return fz

    def confirmatory(self, eid, *, pilot_id=PILOT_ID, planned=("A",), mutate=None, **kw):
        self.design(eid)
        fz = self.frozen(eid, planned, mutate, pilot_id=pilot_id, **kw)
        self.prereg(fz)
        return fz

    def records_bytes(self):
        return self.reg.path.read_bytes() if self.reg.path.exists() else b""

    def to_validation(self, eid, planned=("A",)):
        for st, ev in (("DATA_VALIDATION", {}), ("DEVELOPMENT", {"snapshot_verified": True}), ("VALIDATION", {})):
            self.reg.transition(eid, st, actor=ACTOR, evidence=ev)


@pytest.fixture
def env(tmp_path, dev_snap):
    return Env(tmp_path, *dev_snap)


# ====================================================================================================
# Fórmulas de C.8 (TC-ML-014) y fechas
# ====================================================================================================

def test_tc_ml_014_formulas_and_exact_thresholds():
    assert B.dev_min_history_months(8.0) == 38 and B.dev_min_history_months(2.0) == 50
    assert B.dev_min_history_months(100 / 38) == pytest.approx(38)            # umbral exacto de los 38 meses
    assert B.window_min_months(3.0, 1) == pytest.approx(10.0) and B.window_min_months(2.0, 1.5) == pytest.approx(22.5)
    assert min_history_months(1.0) == 100 and min_history_months(8.0, WF) == 38
    ok = check_min_history(2.0, "train_only", available_months=50, k=1)
    assert ok["ok"] and ok["required_months"] == 50 and ok["window_min_months"] == 15.0
    assert not check_min_history(2.0, "train_only", available_months=49.99)["ok"]
    for bad_r in (0, -1, float("nan"), float("inf"), True, "3", None):
        with pytest.raises(B.BoundaryError):
            B.dev_min_history_months(bad_r)
        with pytest.raises(PreregistrationError):
            min_history_months(bad_r)
    for bad_k in (0.99, 0, -1, float("nan"), True, "1"):
        with pytest.raises(B.BoundaryError):
            B.window_min_months(3.0, bad_k)
    with pytest.raises(PreregistrationError):
        check_min_history(3.0, "train_val", available_months=99)
    with pytest.raises(PreregistrationError):
        check_min_history(3.0, "train_only", available_months=99, k=0.5)
    assert not hasattr(PR, "FRAC_TRAIN_VAL") and not hasattr(PR, "FRAC_OOS")


def test_available_months_uses_the_mean_month():
    ms = int(30.436875 * B.DAY_MS)
    assert B.available_months(10 * ms, 0) == pytest.approx(10.0)


@pytest.mark.parametrize("start,n", [("2027-03-01", 12), ("2027-01-31", 1), ("2027-01-31", 25), ("2028-02-29", 12),
                                      ("2028-02-29", 48), ("2027-12-31", 2), ("2027-03-31", 11)])
def test_add_months_matches_pandas_dateoffset(start, n):
    import pandas as pd
    got = B.add_months(B.parse_date(start), n)
    want = pd.Timestamp(start, tz="UTC") + pd.DateOffset(months=n)
    assert got == want.to_pydatetime()


def test_windows_are_oos_then_lockbox_with_their_ids():
    ib = confirmatory_boundary("2027-03-01T00:00:00Z", 12, 18)
    w = B.windows(ib, "EXP-0201")
    assert list(w) == ["EXP-0201/OOS", "EXP-0201/LOCKBOX"]
    assert w["EXP-0201/OOS"] == (B.parse_date("2027-03-01"), B.parse_date("2028-03-01"))
    assert w["EXP-0201/LOCKBOX"] == (B.parse_date("2028-03-01"), B.parse_date("2029-09-01"))
    ib = confirmatory_boundary("2027-01-31T00:00:00Z", 1, 1)           # desde B, sin acumular recortes de fin de mes
    assert B.windows(ib, "EXP-0201")["EXP-0201/LOCKBOX"][1] == B.parse_date("2027-03-31")


# ====================================================================================================
# freeze(): validación pura de la forma (C.3, C.5, C.8)
# ====================================================================================================

TRIALS = {"H_doc": 0, "H_bound": 0, "E": 0, "planned_config_ids": ["A"], "planned_new": 1, "N_pre": 1,
          "provenance_ids": []}
IB = "independence_boundary"


def pure(planned=("A",), mutate=None, **kw):
    trials = dict(TRIALS, planned_config_ids=list(planned), planned_new=len(planned), N_pre=len(planned))
    c = base_content("EXP-0201", trials, planned, **kw)
    if mutate:
        mutate(c)
    return c


def _set(*path, value):
    def f(c):
        d = c
        for k in path[:-1]:
            d = d[k]
        d[path[-1]] = value
    return f


def _del(*path):
    def f(c):
        d = c
        for k in path[:-1]:
            d = d[k]
        del d[path[-1]]
    return f


def test_valid_confirmatory_and_pilot_content_freeze():
    assert freeze(pure()).sha256 and freeze(pure(pilot=True)).sha256
    freeze(pure(l_oos=10, l_lb=10))                                       # L = k·30/r exacto (10.0): admitido
    freeze(pure(k=1.5, rate=2.0, l_oos=23, l_lb=23, available=100.0))     # k decimal, L ≥ 22,5
    freeze(pure(mutate=_set("conditioning_components", value={"components": [
        {"name": "regimen", "version": "1.2", "sha256": SHA_A}]})))
    freeze(pure(planned=("A", "B")))                                      # config_sha256 con una entrada por config


CONFIRMATORY_REJECTIONS = {
    "ib_extra_key": _set(IB, "extra", value=1),
    "ib_missing_k": _del(IB, "k"),
    "ib_missing_inventory": _del(IB, "exposure_inventory"),
    "eligible_int": _set(IB, "confirmatory_eligible", value=1),
    "eligible_str": _set(IB, "confirmatory_eligible", value="true"),
    "B_not_midnight": _set(IB, "B", value="2027-03-01T01:00:00Z"),
    "B_date_only": _set(IB, "B", value="2027-03-01"),
    "B_offset": _set(IB, "B", value="2027-03-01T00:00:00+00:00"),
    "B_impossible_date": _set(IB, "B", value="2027-02-30T00:00:00Z"),
    "B_not_str": _set(IB, "B", value=20270301),
    "L_oos_zero": _set(IB, "L_oos_months", value=0),
    "L_oos_bool": _set(IB, "L_oos_months", value=True),
    "L_oos_float": _set(IB, "L_oos_months", value=12.0),
    "L_oos_str": _set(IB, "L_oos_months", value="12"),
    "L_lb_zero": _set(IB, "L_lb_months", value=0),
    "L_oos_below_k30_over_r": _set(IB, "L_oos_months", value=9),         # r=3, k=1 → mínimo 10
    "L_lb_below_k30_over_r": _set(IB, "L_lb_months", value=9),
    "k_below_one": _set(IB, "k", value=0.5),
    "k_bool": _set(IB, "k", value=True),
    "k_nan": _set(IB, "k", value=float("nan")),
    "k_inf": _set(IB, "k", value=float("inf")),
    "k_str": _set(IB, "k", value="1"),
    "calendar_rule": _set(IB, "calendar_rule", value="EXTENDABLE"),
    "open_positions_rule": _set(IB, "open_positions_rule", value="KEEP_OPEN"),
    "scope": _set(IB, "scope", value="ETH/USDT"),
    "rate_zero": _set("observed_trade_rate_per_month", value=0),
    "rate_negative": _set("observed_trade_rate_per_month", value=-3.0),
    "rate_nan": _set("observed_trade_rate_per_month", value=float("nan")),
    "rate_bool": _set("observed_trade_rate_per_month", value=True),
    "rate_str": _set("observed_trade_rate_per_month", value="3"),
    "rate_pilot_marker": _set("observed_trade_rate_per_month", value=B.PILOT_RATE),
    "source_plain_train_only": _set("trade_rate_source", value="train_only"),
    "source_train_val": _set("trade_rate_source", "scope", value="train_val"),
    "source_no_pilot_id": _del("trade_rate_source", "pilot_experiment_id"),
    "source_bad_pilot_id": _set("trade_rate_source", "pilot_experiment_id", value="EXP-1"),
    "source_extra_key": _set("trade_rate_source", "extra", value=1),
    "source_self_reference": _set("trade_rate_source", "pilot_experiment_id", value="EXP-0201"),
    "mh_old_form": _set("min_history", value={"ok": True}),
    "mh_required_wrong": _set("min_history", "required_months", value=37.0),
    "mh_window_wrong": _set("min_history", "window_min_months", value=11.0),
    "mh_not_ok": _set("min_history", "ok", value=False),
    "mh_ok_truthy_int": _set("min_history", "ok", value=1),
    "mh_available_below_required": _set("min_history", "available_months", value=37.99),
    "mh_available_bool": _set("min_history", "available_months", value=True),
    "mh_available_nan": _set("min_history", "available_months", value=float("nan")),
    "mh_extra_key": _set("min_history", "extra", value=1),
    "mh_pilot_exemption": _set("min_history", value=dict(B.PILOT_MIN_HISTORY)),
    "mc_string": _set("model_config", value="<model_config>"),
    "mc_no_strategy_id": _del("model_config", "strategy_id"),
    "mc_empty_strategy_id": _set("model_config", "strategy_id", value=" "),
    "mc_bad_strategy_sha": _set("model_config", "strategy_sha256", value="xyz"),
    "mc_sha_uppercase": _set("model_config", "strategy_sha256", value="A" * 64),
    "mc_config_sha_extra": _set("model_config", "config_sha256", "Z", value=SHA_B),
    "mc_config_sha_missing": _set("model_config", "config_sha256", value={}),
    "mc_config_sha_bad_value": _set("model_config", "config_sha256", "A", value="123"),
    "mc_config_sha_list": _set("model_config", "config_sha256", value=[SHA_B]),
    "cc_unknown_declaration": _set("conditioning_components", value={"declaration": "SOME"}),
    "cc_empty_components": _set("conditioning_components", value={"components": []}),
    "cc_none_and_components": _set("conditioning_components", value={"declaration": "NONE", "components": [
        {"name": "x", "version": "1", "sha256": SHA_A}]}),
    "cc_component_no_sha": _set("conditioning_components", value={"components": [{"name": "x", "version": "1"}]}),
    "cc_component_bad_sha": _set("conditioning_components", value={"components": [
        {"name": "x", "version": "1", "sha256": "abc"}]}),
    "cc_component_extra": _set("conditioning_components", value={"components": [
        {"name": "x", "version": "1", "sha256": SHA_A, "z": 1}]}),
    "snap_old_form": _set("snapshot", value={"id": "SNAP-X"}),
    "snap_missing_d_dev": _del("snapshot", "d_dev"),
    "snap_extra_key": _set("snapshot", "extra", value=1),
    "snap_bad_id": _set("snapshot", "snapshot_id", value="SNAP-1"),
    "snap_bad_sha": _set("snapshot", "train_val_sha256", value="a" * 63),
    "snap_bad_d_dev": _set("snapshot", "d_dev", value="2021-6-17"),
    "snap_d_dev_not_before_B": _set("snapshot", "d_dev", value="2027-03-01"),
    "snap_d_dev_after_B": _set("snapshot", "d_dev", value="2027-04-01"),
}


@pytest.mark.parametrize("name", sorted(CONFIRMATORY_REJECTIONS))
def test_freeze_rejects_malformed_confirmatory_content(name):
    with pytest.raises(PreregistrationError):
        freeze(pure(mutate=CONFIRMATORY_REJECTIONS[name]))


PILOT_REJECTIONS = {
    "ib_extra_key": _set(IB, "extra", value=1),
    "ib_missing_purpose": _del(IB, "purpose"),
    "ib_other_purpose": _set(IB, "purpose", value="EXPLORATION"),
    "ib_scope_all": _set(IB, "access_scope", value="ALL"),
    "eligible_zero": _set(IB, "confirmatory_eligible", value=0),
    "eligible_none": _set(IB, "confirmatory_eligible", value=None),
    "rate_numeric": _set("observed_trade_rate_per_month", value=3.0),
    "source_train_val": _set("trade_rate_source", value="train_val"),
    "source_dict": _set("trade_rate_source", value={"scope": "train_only", "pilot_experiment_id": "EXP-0200"}),
    "mh_ok_form": _set("min_history", value={"ok": True}),
    "mh_other_exemption": _set("min_history", value={"exempt": "OTHER"}),
    "mh_exempt_plus_ok": _set("min_history", "ok", value=True),
    "snap_old_form": _set("snapshot", value={"id": "SNAP-X"}),
    "cc_bad": _set("conditioning_components", value={"declaration": "none"}),
}


@pytest.mark.parametrize("name", sorted(PILOT_REJECTIONS))
def test_freeze_rejects_malformed_pilot_content(name):
    with pytest.raises(PreregistrationError):
        freeze(pure(pilot=True, mutate=PILOT_REJECTIONS[name]))


@pytest.mark.parametrize("field", ["independence_boundary", "conditioning_components", "snapshot", "min_history",
                                   "trade_rate_source", "observed_trade_rate_per_month"])
def test_freeze_requires_each_new_field(field):
    c = pure()
    del c[field]
    with pytest.raises(PreregistrationError, match="incompleto"):
        freeze(c)
    assert {"independence_boundary", "conditioning_components"} <= set(PR.REQUIRED_FIELDS)


def test_freeze_is_pure_and_does_not_create_the_store(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from swingpilot.research import prereg_store
    freeze(pure())
    assert not prereg_store.DEFAULT_ROOT.exists() and list(tmp_path.iterdir()) == []


# ====================================================================================================
# Inventario de exposición (decisión 4 del propietario)
# ====================================================================================================

def _entry(c, eid):
    return next(e for e in c[IB]["exposure_inventory"]["entries"] if e["id"] == eid)


def _drop_entry(eid):
    def f(c):
        inv = c[IB]["exposure_inventory"]
        inv["entries"] = [e for e in inv["entries"] if e["id"] != eid]
    return f


def _alter(eid, key, value):
    def f(c):
        _entry(c, eid)[key] = value
    return f


MANDATORY_IDS = [m["id"] for m in B.MANDATORY_EXPOSURES]
OTHER_CLASS = {"DOCUMENTED": "UNCERTAIN", "UNCERTAIN": "UNKNOWN", "UNKNOWN": "UNCERTAIN"}


def test_mandatory_exposures_match_the_owner_decision():
    by_id = {m["id"]: m for m in B.MANDATORY_EXPOSURES}
    assert set(by_id) == {"TRADING_BOT_PHASE0_EXP0001_DESIGN", "LOCKBOX_OOS_001", "PRE_2023_RESEARCH",
                          "IMPL2_CALIBRATION_FIXTURE"}
    f = by_id["IMPL2_CALIBRATION_FIXTURE"]
    assert (f["class"], f["period_start"], f["period_end"], f["b_not_before"]) == (
        "UNKNOWN", "UNKNOWN", "UNKNOWN", "2026-11-20T00:00:00Z")      # cota C.4.2.3, no fecha de exposición
    assert by_id["LOCKBOX_OOS_001"]["class"] == "UNCERTAIN"
    assert by_id["TRADING_BOT_PHASE0_EXP0001_DESIGN"]["b_not_before"] == "2025-11-09T00:00:00Z"
    assert by_id["PRE_2023_RESEARCH"]["class"] == "UNKNOWN"
    assert B.max_b_not_before(inventory()) == B.parse_date("2026-11-20")


@pytest.mark.parametrize("eid", MANDATORY_IDS)
def test_missing_mandatory_exposure_is_rejected(eid):
    with pytest.raises(PreregistrationError, match=eid):
        freeze(pure(mutate=_drop_entry(eid)))


@pytest.mark.parametrize("eid", MANDATORY_IDS)
@pytest.mark.parametrize("key", ["class", "period_start", "period_end", "b_not_before"])
def test_altered_mandatory_exposure_is_rejected(eid, key):
    m = next(x for x in B.MANDATORY_EXPOSURES if x["id"] == eid)
    new = OTHER_CLASS[m["class"]] if key == "class" else (None if key == "b_not_before" else "2030-01-01T00:00:00Z")
    with pytest.raises(PreregistrationError, match=eid):
        freeze(pure(mutate=_alter(eid, key, new)))


def test_fixture_exposure_period_must_stay_unknown():
    """Nunca se deducen fechas de exposición de las fechas de creación de un fixture."""
    for key in ("period_start", "period_end"):
        with pytest.raises(PreregistrationError, match="IMPL2_CALIBRATION_FIXTURE"):
            freeze(pure(mutate=_alter("IMPL2_CALIBRATION_FIXTURE", key, "2026-11-19T00:00:00Z")))


@pytest.mark.parametrize("eid", MANDATORY_IDS)
def test_mandatory_evidence_references_cannot_be_dropped(eid):
    def drop_first_ref(c):
        _entry(c, eid)["evidence"].pop(0)
    with pytest.raises(PreregistrationError, match="evidencia|evidence"):
        freeze(pure(mutate=drop_first_ref))


def test_extra_inventory_entries_and_evidence_are_allowed():
    extra = {"id": "EXTRA_NOTEBOOK", "class": "UNCERTAIN", "period_start": "2026-01-01T00:00:00Z",
             "period_end": "2026-02-01T00:00:00Z", "b_not_before": "2026-02-01T00:00:00Z",
             "evidence": [EVIDENCE_REF], "note": "otra exposición"}
    c = pure(mutate=lambda c: c[IB]["exposure_inventory"]["entries"].append(dict(extra)))
    c[IB]["exposure_inventory"]["entries"][0]["evidence"].append(EVIDENCE_REF)
    freeze(c)


BAD_EXTRA = {
    "documented_without_b": {"class": "DOCUMENTED", "b_not_before": None},
    "uncertain_without_b": {"class": "UNCERTAIN", "b_not_before": None},
    "bad_class": {"class": "KNOWN"},
    "b_not_midnight": {"b_not_before": "2026-02-01T12:00:00Z"},
    "period_inverted": {"period_start": "2026-03-01T00:00:00Z"},
    "period_bad": {"period_end": "2026-02-01"},
    "evidence_empty": {"evidence": []},
    "evidence_bad_ref": {"evidence": ["no-es-referencia"]},
    "evidence_path_escape": {"evidence": ["repo@abc1234:../secreto"]},
    "note_not_str": {"note": 5},
    "empty_id": {"id": " "},
}


@pytest.mark.parametrize("name", sorted(BAD_EXTRA))
def test_malformed_extra_entry_is_rejected(name):
    extra = {"id": "EXTRA", "class": "UNCERTAIN", "period_start": "2026-01-01T00:00:00Z",
             "period_end": "2026-02-01T00:00:00Z", "b_not_before": "2026-02-01T00:00:00Z",
             "evidence": [EVIDENCE_REF], "note": "x", **BAD_EXTRA[name]}
    with pytest.raises(PreregistrationError):
        freeze(pure(mutate=lambda c: c[IB]["exposure_inventory"]["entries"].append(extra)))


def test_entry_with_extra_key_or_duplicate_id_is_rejected():
    with pytest.raises(PreregistrationError):
        freeze(pure(mutate=lambda c: _entry(c, "LOCKBOX_OOS_001").update(extra=1)))
    with pytest.raises(PreregistrationError, match="repetido"):
        freeze(pure(mutate=lambda c: c[IB]["exposure_inventory"]["entries"].append(
            dict(_entry(c, "LOCKBOX_OOS_001")))))


INVENTORY = "exposure_inventory"
INVENTORY_REJECTIONS = {
    "extra_key": _set(IB, INVENTORY, "extra", value=1),
    "missing_scope": _del(IB, INVENTORY, "scope"),
    "other_scope": _set(IB, INVENTORY, "scope", value="ETH/USDT"),
    "empty_limitation": _set(IB, INVENTORY, "general_familiarity_limitation", value=" "),
    "missing_limitation": _del(IB, INVENTORY, "general_familiarity_limitation"),
    "ids_not_hex": _set(IB, INVENTORY, "independence_deviation_ids", value=["xyz"]),
    "ids_short": _set(IB, INVENTORY, "independence_deviation_ids", value=["a" * 31]),
    "ids_duplicate": _set(IB, INVENTORY, "independence_deviation_ids", value=["a" * 32, "a" * 32]),
    "ids_not_list": _set(IB, INVENTORY, "independence_deviation_ids", value="a" * 32),
    "entries_empty": _set(IB, INVENTORY, "entries", value=[]),
    "entries_not_list": _set(IB, INVENTORY, "entries", value={}),
}


@pytest.mark.parametrize("name", sorted(INVENTORY_REJECTIONS))
def test_malformed_inventory_is_rejected(name):
    with pytest.raises(PreregistrationError):
        freeze(pure(mutate=INVENTORY_REJECTIONS[name]))


# ====================================================================================================
# ET-1: preregister(), almacén antes de PREREGISTERED, freeze_check dentro del bloqueo
# ====================================================================================================

def _transitions(reg, eid):
    return [r for r in reg.records() if r.get("kind") == "TRANSITION" and r["experiment_id"] == eid]


def test_et1_pilot_is_frozen_with_exemption_and_stored(env):
    fz = env.pilot()
    (rec,) = [r for r in _transitions(env.reg, PILOT_ID) if r["to"] == "PREREGISTERED"]
    ev = rec["evidence"]
    assert ev["independence_class"] == "TRADE_RATE_PILOT" and ev["min_history_exempt"] == "TRADE_RATE_PILOT"
    assert "min_history_ok" not in ev and ev["preregistration_sha256"] == fz.sha256
    assert ev["trials_accounting"] == fz.content["trials_count"]
    assert env.store.verify_cited(PILOT_ID, fz.sha256, fz.sha256) == fz.content


def test_et1_confirmatory_is_frozen_with_class_and_history_evidence(env):
    env.pilot()
    fz = env.confirmatory("EXP-0201")
    (rec,) = [r for r in _transitions(env.reg, "EXP-0201") if r["to"] == "PREREGISTERED"]
    ev = rec["evidence"]
    assert ev["independence_class"] == "CONFIRMATORY" and ev["min_history_ok"] is True
    assert "min_history_exempt" not in ev
    assert env.reg.state("EXP-0201") == "PREREGISTERED" and env.store.load("EXP-0201", fz.sha256) == fz.content


def test_store_is_written_before_the_registry_transition(env, monkeypatch):
    env.design(PILOT_ID)
    fz = env.frozen(PILOT_ID, pilot=True)
    seen = []
    real = env.reg.transition

    def spy(*a, **k):
        seen.append(env.store.path_for(PILOT_ID, fz.sha256).exists())
        return real(*a, **k)
    monkeypatch.setattr(env.reg, "transition", spy)
    env.prereg(fz)
    assert seen == [True]


def test_store_failure_means_no_transition_and_orphan_is_preserved(env, monkeypatch):
    env.design(PILOT_ID)
    fz = env.frozen(PILOT_ID, pilot=True)
    before = env.records_bytes()
    real = PreregistrationStore.write_frozen

    def write_then_fail(self, frozen):
        path = real(self, frozen)
        raise PreregStoreWriteUncertain("fallo simulado tras escribir")
    monkeypatch.setattr(PreregistrationStore, "write_frozen", write_then_fail)
    with pytest.raises(PreregStoreError):
        env.prereg(fz)
    assert env.records_bytes() == before and env.reg.state(PILOT_ID) == "DESIGN"
    assert [e["status"] for e in env.store.entries(PILOT_ID, set())] == ["ORPHAN"]      # se conserva, sin autoridad


def test_unwritable_store_means_no_transition(env, tmp_path):
    env.design(PILOT_ID)
    fz = env.frozen(PILOT_ID, pilot=True)
    before = env.records_bytes()
    with pytest.raises(PreregStoreError):
        env.prereg(fz, store=PreregistrationStore(tmp_path / "no-existe" / "preregistrations"))
    assert env.records_bytes() == before and env.reg.state(PILOT_ID) == "DESIGN"


def test_preregister_requires_a_store_object_and_a_registry(env):
    env.design(PILOT_ID)
    fz = env.frozen(PILOT_ID, pilot=True)
    with pytest.raises(PreregistrationError):
        env.prereg(fz, store=None)
    with pytest.raises(PreregistrationError):
        env.prereg(fz, store=env.store.root)
    with pytest.raises(PreregistrationError):
        preregister(object(), fz, store=env.store, dev_manifest_path=env.res.manifest_path, data_root=env.data_root)
    with pytest.raises(TypeError):                               # el almacén y la snapshot son obligatorios
        preregister(env.reg, fz)
    assert env.reg.state(PILOT_ID) == "DESIGN"


def test_direct_transition_without_freeze_check_is_rejected(env):
    env.design(PILOT_ID)
    ev = {"preregistration_sha256": SHA_A, "independence_class": "CONFIRMATORY", "min_history_ok": True,
          "trials_accounting": env.reg.trials_accounting(PILOT_ID, ["A"])}
    # B3-01: tampoco un invocable arbitrario aportado por quien llama (antes se aceptaba)
    for kw in ({}, {"freeze_check": "no es invocable"}, {"freeze_check": 1}, {"freeze_check": None},
               {"freeze_check": lambda records: None}, {"freeze_check": lambda *a, **k: None}):
        with pytest.raises(ExperimentError, match="freeze_check"):
            env.reg.transition(PILOT_ID, "PREREGISTERED", actor=ACTOR, evidence=ev, **kw)
    assert env.reg.state(PILOT_ID) == "DESIGN"


def test_freeze_check_rejection_and_failure_block_the_transition(env):
    env.design(PILOT_ID)
    ev = {"preregistration_sha256": SHA_A, "independence_class": "CONFIRMATORY", "min_history_ok": True,
          "trials_accounting": env.reg.trials_accounting(PILOT_ID, ["A"])}

    def boom(records, experiment_id, evidence):
        raise RuntimeError("fallo inesperado")
    for fn in (lambda records, experiment_id, evidence: "motivo de rechazo", boom):
        check = FreezeCheck(_FREEZE_CHECK_KEY, fn)
        with pytest.raises(ExperimentError, match="freeze_check"):
            env.reg.transition(PILOT_ID, "PREREGISTERED", actor=ACTOR, evidence=ev, freeze_check=check)
    assert env.reg.state(PILOT_ID) == "DESIGN"


def test_freeze_check_runs_inside_the_lock_with_the_current_records(env):
    import fcntl
    env.design(PILOT_ID)
    seen = {}

    def fn(records, experiment_id, evidence):
        with open(env.reg.path.with_name(env.reg.path.name + ".lock"), "a") as lk:
            try:
                fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
                seen["locked"] = False
            except BlockingIOError:
                seen["locked"] = True
        seen["kinds"] = [r["kind"] for r in records]
        seen["args"] = (experiment_id, evidence["independence_class"])
    env.reg.transition(PILOT_ID, "PREREGISTERED", actor=ACTOR, freeze_check=FreezeCheck(_FREEZE_CHECK_KEY, fn),
                       evidence={"preregistration_sha256": SHA_A, "independence_class": "TRADE_RATE_PILOT",
                                 "min_history_exempt": "TRADE_RATE_PILOT",
                                 "trials_accounting": env.reg.trials_accounting(PILOT_ID, ["A"])})
    assert seen["locked"] is True and seen["kinds"] == ["CREATED", "TRANSITION"]
    assert seen["args"] == (PILOT_ID, "TRADE_RATE_PILOT")


@pytest.mark.parametrize("evidence", [
    {},                                                                           # sin clase
    {"independence_class": "OTRA", "min_history_ok": True},
    {"independence_class": "CONFIRMATORY"},                                       # sin min_history_ok
    {"independence_class": "CONFIRMATORY", "min_history_ok": False},
    {"independence_class": "CONFIRMATORY", "min_history_ok": 1},
    {"independence_class": "CONFIRMATORY", "min_history_exempt": "TRADE_RATE_PILOT"},   # exención ajena al piloto
    {"independence_class": "CONFIRMATORY", "min_history_ok": True, "min_history_exempt": "TRADE_RATE_PILOT"},
    {"independence_class": "TRADE_RATE_PILOT"},                                   # piloto sin exención
    {"independence_class": "TRADE_RATE_PILOT", "min_history_ok": True},
    {"independence_class": "TRADE_RATE_PILOT", "min_history_exempt": "OTRA"},
    {"min_history_exempt": "TRADE_RATE_PILOT"},                                   # exención sin clase
    {"min_history_ok": True},
])
def test_pilot_exemption_only_with_pilot_class_and_class_is_required(env, evidence):
    env.design(PILOT_ID)
    with pytest.raises(ExperimentError):
        env.reg.transition(PILOT_ID, "PREREGISTERED", actor=ACTOR, freeze_check=legacy_freeze_check(),
                           evidence={"preregistration_sha256": SHA_A,
                                     "trials_accounting": env.reg.trials_accounting(PILOT_ID, ["A"]), **evidence})
    assert env.reg.state(PILOT_ID) == "DESIGN"


def _fail_et1(env, eid, fz, match=None, exc=Exception):
    """ET-1 rechazado: sin transición ni cambios en el registro."""
    before = env.records_bytes()
    with pytest.raises(exc, match=match):
        env.prereg(fz)
    assert env.records_bytes() == before and env.reg.state(eid) == "DESIGN"


SNAPSHOT_BINDINGS = {"snapshot_id": "SNAP-0002", "train_val_sha256": SHA_B, "d_dev": "2021-06-18"}


@pytest.mark.parametrize("key", sorted(SNAPSHOT_BINDINGS))
@pytest.mark.parametrize("pilot", [True, False])
def test_et1_snapshot_must_match_the_verified_development_manifest(env, key, pilot):
    env.pilot() if not pilot else None
    env.design("EXP-0201")
    fz = env.frozen("EXP-0201", pilot=pilot, **({"pilot_id": PILOT_ID} if not pilot else {}),
                    **{{"snapshot_id": "snapshot_id", "train_val_sha256": "tv_sha", "d_dev": "d_dev"}[key]:
                       SNAPSHOT_BINDINGS[key]})
    _fail_et1(env, "EXP-0201", fz, "snapshot", PreregistrationError)
    assert env.store.entries("EXP-0201", set()) == []              # ni siquiera se escribió el contenido


def test_et1_available_months_must_be_recomputed_and_sufficient(env):
    env.pilot()
    env.design("EXP-0201")
    right = env.fields()["available"]
    fz = env.frozen("EXP-0201", available=right + 1.0)
    _fail_et1(env, "EXP-0201", fz, "available_months", PreregistrationError)
    assert env.store.entries("EXP-0201", set()) == []
    env.prereg(env.frozen("EXP-0201", available=right))            # el valor recalculado sí congela
    assert env.reg.state("EXP-0201") == "PREREGISTERED"


def test_et1_requires_a_verifiable_development_snapshot(env, tmp_path):
    import shutil
    env.design(PILOT_ID)
    fz = env.frozen(PILOT_ID, pilot=True)
    with pytest.raises(PreregistrationError, match="I2"):
        env.prereg(fz, dev_manifest_path=tmp_path / "no-existe.json")
    root = tmp_path / "copy" / "snapshots"
    shutil.copytree(env.data_root, root)
    manifest = tmp_path / "copy" / "SNAP-TEST.json"
    shutil.copy(env.res.manifest_path, manifest)
    target = root / "SNAP-TEST" / "train_val.parquet"
    os.chmod(target, 0o644)
    with open(target, "ab") as fh:
        fh.write(b"alterado")                                        # SHA-256 distinto del manifiesto
    with pytest.raises(PreregistrationError, match="I2"):
        env.prereg(fz, dev_manifest_path=manifest, data_root=root)
    assert env.reg.state(PILOT_ID) == "DESIGN" and env.store.entries(PILOT_ID, set()) == []


def test_et1_b_must_not_precede_the_inventoried_exposure_end(env):
    env.pilot()
    env.design("EXP-0201")
    fz = env.frozen("EXP-0201", b="2026-11-19T00:00:00Z")           # forma válida; el fixture exige ≥ 2026-11-20
    _fail_et1(env, "EXP-0201", fz, "inventariada")
    assert [e["status"] for e in env.store.entries("EXP-0201", set())] == ["ORPHAN"]
    later = {"id": "EXTRA_LATER", "class": "UNCERTAIN", "period_start": "2027-01-01T00:00:00Z",
             "period_end": "2027-06-01T00:00:00Z", "b_not_before": "2027-06-01T00:00:00Z",
             "evidence": [EVIDENCE_REF], "note": "extra"}
    fz = env.frozen("EXP-0201", mutate=lambda c: c[IB]["exposure_inventory"]["entries"].append(later))
    _fail_et1(env, "EXP-0201", fz, "inventariada")                  # B = 2027-03-01 < 2027-06-01 de la entrada extra
    env.prereg(env.frozen("EXP-0201", b="2026-11-20T00:00:00Z"))   # B igual al mayor b_not_before: admitido
    assert env.reg.state("EXP-0201") == "PREREGISTERED"


def test_et1_rejects_when_the_stored_content_differs_or_is_missing(env):
    env.design(PILOT_ID)
    fz = env.frozen(PILOT_ID, pilot=True)
    check = build_freeze_check(fz, env.store, dev_manifest_path=env.res.manifest_path, data_root=env.data_root)
    ev = freeze_evidence(fz)
    assert "V2" in check([], PILOT_ID, ev)                          # aún no escrito: huérfano inexistente
    env.store.write_frozen(fz)
    path = env.store.path_for(PILOT_ID, fz.sha256)
    assert check([], PILOT_ID, ev) is None
    os.chmod(path, 0o644)
    path.write_bytes(path.read_bytes() + b" ")
    assert "V2" in check([], PILOT_ID, ev)                          # contenido distinto de su nombre


def test_trade_rate_source_must_be_a_native_frozen_pilot_with_verifiable_content(env):
    env.pilot()
    env.confirmatory("EXP-0201")                                    # un confirmatorio no es piloto
    env.design("EXP-0202")
    for pid in ("EXP-0299", "EXP-0201"):
        fz = env.frozen("EXP-0202", pilot_id=pid, b="2029-03-01T00:00:00Z")
        _fail_et1(env, "EXP-0202", fz, "piloto")
    # el piloto citado existe y es piloto, pero su archivo del almacén está alterado
    path = env.store.path_for(PILOT_ID, env.reg.experiments()[PILOT_ID]["history"][-1]["evidence"]["preregistration_sha256"])
    os.chmod(path, 0o644)
    path.write_bytes(b"{}")
    fz = env.frozen("EXP-0202", b="2029-03-01T00:00:00Z")
    _fail_et1(env, "EXP-0202", fz, "piloto")


def test_trade_rate_source_pilot_without_stored_content_is_rejected(env):
    env.design(PILOT_ID)                                            # piloto congelado sin pasar por el almacén
    env.reg.transition(PILOT_ID, "PREREGISTERED", actor=ACTOR, freeze_check=legacy_freeze_check(),
                       evidence={"preregistration_sha256": SHA_A, "independence_class": "TRADE_RATE_PILOT",
                                 "min_history_exempt": "TRADE_RATE_PILOT",
                                 "trials_accounting": env.reg.trials_accounting(PILOT_ID, ["A"])})
    env.design("EXP-0201")
    _fail_et1(env, "EXP-0201", env.frozen("EXP-0201"), "piloto")


# ====================================================================================================
# TC-ML-019 (sustituye la formulación anterior): ventanas anteriores y B posterior
# ====================================================================================================

LB_END = "2029-03-01T00:00:00Z"                  # LOCKBOX de EXP-0201: [2028-03-01, 2029-03-01)


def test_tc_ml_019_second_boundary_must_not_precede_prior_lockbox_end(env):
    env.pilot()
    fz1 = env.confirmatory("EXP-0201")
    assert B.format_instant(B.lockbox_end(fz1.content[IB], "EXP-0201")) == LB_END
    env.design("EXP-0202")
    for b in ("2026-12-01T00:00:00Z", "2027-03-01T00:00:00Z", "2028-03-01T00:00:00Z", "2029-02-28T00:00:00Z"):
        _fail_et1(env, "EXP-0202", env.frozen("EXP-0202", b=b), "LOCKBOX de EXP-0201")
    env.prereg(env.frozen("EXP-0202", b=LB_END))                    # [fin, …): no solapa (fin exclusivo)
    assert env.reg.state("EXP-0202") == "PREREGISTERED"


def test_tc_ml_019_rejected_prior_experiment_still_binds(env):
    env.pilot()
    env.confirmatory("EXP-0201")
    env.reg.transition("EXP-0201", "REJECTED", actor=ACTOR)
    env.design("EXP-0202")
    _fail_et1(env, "EXP-0202", env.frozen("EXP-0202", b="2028-06-01T00:00:00Z"), "LOCKBOX de EXP-0201")
    env.prereg(env.frozen("EXP-0202", b=LB_END))


def test_tc_ml_019_prior_with_independence_deviation_still_binds_and_must_be_cited(env):
    env.pilot()
    fz1 = env.confirmatory("EXP-0201")
    dev = fz1.record_independence_deviation(["EXP-0201/OOS"], "UNAUTHORIZED_EXPOSURE", [EVIDENCE_REF], "UNKNOWN",
                                            "exposición no autorizada", registry=env.reg, informed_by=[], actor=ACTOR)
    env.design("EXP-0202")
    ids = [dev["deviation_id"]]
    _fail_et1(env, "EXP-0202", env.frozen("EXP-0202", b="2028-06-01T00:00:00Z", deviation_ids=ids),
              "LOCKBOX de EXP-0201")                                # contaminada: sigue reservando su periodo
    _fail_et1(env, "EXP-0202", env.frozen("EXP-0202", b=LB_END), "V7")          # sin citar el DEVIATION
    env.prereg(env.frozen("EXP-0202", b=LB_END, deviation_ids=ids))


def test_frozen_experiment_without_independence_class_blocks_fail_closed(env):
    env.pilot()
    env.design("EXP-0300")                                          # congelación anterior a CR-023 (sin clase)
    env.reg._append({"kind": "TRANSITION", "experiment_id": "EXP-0300", "from": "DESIGN", "to": "PREREGISTERED",
                     "actor": ACTOR, "evidence": {"preregistration_sha256": SHA_A}, "reason": ""})
    env.design("EXP-0201")
    _fail_et1(env, "EXP-0201", env.frozen("EXP-0201", b="2040-01-01T00:00:00Z"), "EXP-0300")


def test_prior_confirmatory_with_missing_or_invalid_content_blocks_fail_closed(env):
    env.pilot()
    env.design("EXP-0301")                                          # citado en el registro, ausente del almacén
    env.reg.transition("EXP-0301", "PREREGISTERED", actor=ACTOR, freeze_check=legacy_freeze_check(),
                       evidence={"preregistration_sha256": SHA_A, "independence_class": "CONFIRMATORY",
                                 "min_history_ok": True, "trials_accounting": env.reg.trials_accounting(
                                     "EXP-0301", ["A"])})
    env.design("EXP-0201")
    _fail_et1(env, "EXP-0201", env.frozen("EXP-0201", b="2040-01-01T00:00:00Z"), "EXP-0301")


def test_experiments_never_frozen_do_not_bind_and_pilots_do_not_reserve_windows(env):
    env.pilot()
    env.design("EXP-0302")
    env.reg.transition("EXP-0302", "REJECTED", actor=ACTOR)         # descartado en DESIGN: nunca se congeló
    env.design("EXP-0303")                                          # otro en DESIGN
    env.confirmatory("EXP-0201", b="2027-03-01T00:00:00Z")          # el piloto no reserva ventanas
    assert env.reg.state("EXP-0201") == "PREREGISTERED"


# ====================================================================================================
# V7 mecánico
# ====================================================================================================

def test_v7_inventory_citing_a_deviation_absent_from_the_registry_is_rejected(env):
    env.pilot()
    env.design("EXP-0201")
    _fail_et1(env, "EXP-0201", env.frozen("EXP-0201", deviation_ids=["1" * 32]), "V7")


def test_v7_registry_deviation_missing_from_the_inventory_is_rejected_both_directions(env):
    env.pilot()
    fz1 = env.confirmatory("EXP-0201")
    dev = fz1.record_independence_deviation(["EXP-0201/LOCKBOX"], "PREMATURE_INSPECTION", [EVIDENCE_REF],
                                            "2028-04-01T00:00:00Z", "inspección", registry=env.reg,
                                            informed_by=[], actor=ACTOR)
    env.design("EXP-0202")
    did = dev["deviation_id"]
    _fail_et1(env, "EXP-0202", env.frozen("EXP-0202", b=LB_END), "V7")                          # falta citarlo
    _fail_et1(env, "EXP-0202", env.frozen("EXP-0202", b=LB_END, deviation_ids=[did, "2" * 32]), "V7")   # sobra uno
    env.prereg(env.frozen("EXP-0202", b=LB_END, deviation_ids=[did]))                           # exacto: congela


def test_v7_ignores_deviations_of_other_fields_and_rejects_a_malformed_independence_record(env):
    env.pilot()
    fz1 = env.confirmatory("EXP-0201")
    fz1.record_deviation("limitations", "otra", "ajuste menor", registry=env.reg, informed_by=[])
    env.design("EXP-0202")
    env.prereg(env.frozen("EXP-0202", b=LB_END))                    # una desviación ajena no se cita
    env.design("EXP-0203")
    dev = next(r for r in env.reg.records() if r["kind"] == "DEVIATION")   # copia incoherente inyectada
    env.reg._append({**dev, "deviation_id": "c" * 32, "field": "independence_boundary",
                     "old": fz1.content[IB], "new": {"class": "X"}})
    _fail_et1(env, "EXP-0203", env.frozen("EXP-0203", b="2031-03-01T00:00:00Z"), "incoherente")


# ====================================================================================================
# El piloto nunca transita a OOS_EVALUATION
# ====================================================================================================

def _oos_ev(eid, cfg="A"):
    return {"decision_ref": "DEC-900_ok.md", "selected_config_id": cfg, "informed_by": [],
            "selection_inputs_sha256": hashlib.sha256(eid.encode()).hexdigest()}


def test_pilot_cannot_enter_oos_evaluation_but_confirmatory_can(env):
    pilot = env.pilot()
    env.to_validation(PILOT_ID)
    pilot.begin_evaluation("A", registry=env.reg)
    with pytest.raises(ExperimentError, match="CONFIRMATORY"):
        env.reg.transition(PILOT_ID, "OOS_EVALUATION", actor="propietario", evidence=_oos_ev(PILOT_ID))
    assert env.reg.state(PILOT_ID) == "VALIDATION"
    env.reg.transition(PILOT_ID, "INCONCLUSIVE", actor=ACTOR)       # el piloto termina por decisión (aquí estado)
    conf = env.confirmatory("EXP-0201")
    env.to_validation("EXP-0201")
    conf.begin_evaluation("A", registry=env.reg)
    env.reg.transition("EXP-0201", "OOS_EVALUATION", actor="propietario", evidence=_oos_ev("EXP-0201"))
    assert env.reg.state("EXP-0201") == "OOS_EVALUATION"


def test_experiment_frozen_without_class_cannot_enter_oos_evaluation(env):
    env.design("EXP-0300")
    env.reg._append({"kind": "TRANSITION", "experiment_id": "EXP-0300", "from": "DESIGN", "to": "PREREGISTERED",
                     "actor": ACTOR, "evidence": {"preregistration_sha256": SHA_A,
                                                  "trials_accounting": env.reg.trials_accounting("EXP-0300", ["A"])},
                     "reason": ""})
    env.to_validation("EXP-0300")
    env.reg.begin_configuration_evaluation("EXP-0300", "A", actor=ACTOR)
    with pytest.raises(ExperimentError, match="CONFIRMATORY"):
        env.reg.transition("EXP-0300", "OOS_EVALUATION", actor="propietario", evidence=_oos_ev("EXP-0300"))


# ====================================================================================================
# Train-only del piloto (C.3.3)
# ====================================================================================================

def _loader(env, store="default", tmp_name="access.jsonl"):
    return PartitionLoader(env.res.manifest_path, env.data_root, env.tmp / tmp_name, registry=env.reg,
                           prereg_store=env.store if store == "default" else store)


def _spy(loader):
    reads = []
    loader._read = lambda part: reads.append(part) or (_ for _ in ()).throw(AssertionError("leyó datos"))
    return reads


def _evaluating(env, eid, pilot):
    fz = env.pilot(eid) if pilot else env.confirmatory(eid)
    env.to_validation(eid)
    fz.begin_evaluation("A", registry=env.reg)
    return fz


def test_pilot_loader_delivers_train_only_and_confirmatory_keeps_train_val(env):
    _evaluating(env, PILOT_ID, pilot=True)
    _evaluating(env, "EXP-0201", pilot=False)
    cut = env.manifest["cuts_ms"]["train_end"]
    loader = _loader(env)
    for interval in (None, "1d", "4h"):
        df = loader.load_train_val_for_configuration(PILOT_ID, "A", interval)
        assert len(df) > 0 and df["open_time"].max() < cut          # Validation ausente
    full = loader.load_train_val_for_configuration("EXP-0201", "A")
    assert full["open_time"].max() >= cut and (full["open_time"] >= cut).any()
    assert [r["allowed"] for r in loader.access_history()] == [True, True, True, True]


def test_pilot_loader_denies_without_store_and_reads_nothing(env):
    _evaluating(env, PILOT_ID, pilot=True)
    loader = _loader(env, store=None)
    reads = _spy(loader)
    with pytest.raises(PartitionAccessError, match="almacén"):
        loader.load_train_val_for_configuration(PILOT_ID, "A")
    assert reads == [] and loader.access_history()[-1]["allowed"] is False


def test_loader_denies_with_corrupt_missing_or_swapped_store_files_and_reads_nothing(env, tmp_path):
    pilot = _evaluating(env, PILOT_ID, pilot=True)
    conf = _evaluating(env, "EXP-0201", pilot=False)
    p_file = env.store.path_for(PILOT_ID, pilot.sha256)
    c_file = env.store.path_for("EXP-0201", conf.sha256)
    # (a) almacén vacío: falta el archivo citado
    loader = _loader(env, store=PreregistrationStore(tmp_path / "otro"))
    reads = _spy(loader)
    with pytest.raises(PartitionAccessError, match="falta"):
        loader.load_train_val_for_configuration(PILOT_ID, "A")
    # (b) archivo intercambiado: bytes del confirmatorio con el nombre del piloto
    original = p_file.read_bytes()
    os.chmod(p_file, 0o644)
    p_file.write_bytes(c_file.read_bytes())
    loader = _loader(env)
    reads += _spy(loader)
    with pytest.raises(PartitionAccessError, match="almacén"):
        loader.load_train_val_for_configuration(PILOT_ID, "A")
    # (c) archivo corrupto
    p_file.write_bytes(b"{no es json")
    with pytest.raises(PartitionAccessError, match="almacén"):
        loader.load_train_val_for_configuration(PILOT_ID, "A")
    assert reads == [] and all(r["allowed"] is False for r in loader.access_history())
    p_file.write_bytes(original)                                    # restaurado: vuelve a entregar solo Train
    ok = _loader(env).load_train_val_for_configuration(PILOT_ID, "A")
    assert ok["open_time"].max() < env.manifest["cuts_ms"]["train_end"]


def test_loader_denies_unknown_missing_or_inconsistent_independence_class(env):
    # clase ausente (congelación anterior a CR-023)
    env.design("EXP-0300")
    fz = env.frozen("EXP-0300", pilot=True)
    env.store.write_frozen(fz)
    env.reg._append({"kind": "TRANSITION", "experiment_id": "EXP-0300", "from": "DESIGN", "to": "PREREGISTERED",
                     "actor": ACTOR, "evidence": {"preregistration_sha256": fz.sha256,
                                                  "trials_accounting": fz.content["trials_count"]}, "reason": ""})
    env.to_validation("EXP-0300")
    env.reg.begin_configuration_evaluation("EXP-0300", "A", actor=ACTOR)
    # clase CONFIRMATORY declarada sobre contenido de piloto: incoherente
    env.design("EXP-0301")
    fz2 = env.frozen("EXP-0301", pilot=True)
    env.store.write_frozen(fz2)
    env.reg.transition("EXP-0301", "PREREGISTERED", actor=ACTOR, freeze_check=legacy_freeze_check(),
                       evidence={"preregistration_sha256": fz2.sha256, "independence_class": "CONFIRMATORY",
                                 "min_history_ok": True, "trials_accounting": fz2.content["trials_count"]})
    env.to_validation("EXP-0301")
    env.reg.begin_configuration_evaluation("EXP-0301", "A", actor=ACTOR)
    loader = _loader(env)
    reads = _spy(loader)
    for eid, match in (("EXP-0300", "clase"), ("EXP-0301", "clase")):
        with pytest.raises(PartitionAccessError, match=match):
            loader.load_train_val_for_configuration(eid, "A")
    assert reads == []


def test_existing_denials_keep_precedence_over_the_store_check(env):
    _evaluating(env, PILOT_ID, pilot=True)
    loader = _loader(env, store=None)
    with pytest.raises(PartitionAccessError, match="sin inicio de evaluación"):
        loader.load_train_val_for_configuration(PILOT_ID, "Z")


# ====================================================================================================
# DEVIATION de independencia (D.2)
# ====================================================================================================

def _kinds_after(env):
    return [r["kind"] for r in env.reg.records()]


def _deviation(fz, env, ids=("EXP-0201/OOS",), cls="UNAUTHORIZED_EXPOSURE", evidence=(EVIDENCE_REF,),
               started="UNKNOWN", informed_by=()):
    return fz.record_independence_deviation(list(ids), cls, list(evidence), started, "exposición registrada",
                                            registry=env.reg, informed_by=list(informed_by), actor=ACTOR)


def _confirmatory_in(env, state):
    env.pilot()
    fz = env.confirmatory("EXP-0201")
    if state == "REJECTED":
        env.reg.transition("EXP-0201", "REJECTED", actor=ACTOR)
    elif state == "APPROVED":
        env.to_validation("EXP-0201")
        fz.begin_evaluation("A", registry=env.reg)
        env.reg.transition("EXP-0201", "OOS_EVALUATION", actor="propietario", evidence=_oos_ev("EXP-0201"))
        env.reg.transition("EXP-0201", "AUDIT", actor=ACTOR)
        env.reg.transition("EXP-0201", "HUMAN_REVIEW", actor=ACTOR)
        seed_historical_approval(env.reg, "EXP-0201", "DEC-900_ok.md")   # B8.2: histórico sembrado
    assert env.reg.state("EXP-0201") == state
    return fz


@pytest.mark.parametrize("state", ["PREREGISTERED", "REJECTED", "APPROVED"])
def test_independence_deviation_is_accepted_in_any_state_after_preregistered_including_terminal(env, state):
    fz = _confirmatory_in(env, state)
    rec = _deviation(fz, env, ids=("EXP-0201/OOS", "EXP-0201/LOCKBOX"), cls="DEVELOPMENT_INFORMED",
                     started="2028-03-01T00:00:00Z")
    assert rec["field"] == "independence_boundary" and rec["experiment_id"] == "EXP-0201"
    assert rec["old"] == fz.content[IB] and rec["authorizes_change"] is False and rec["informed_by"] == []
    assert rec["preregistration_sha256"] == fz.sha256 and rec["after_oos"] is False
    assert set(rec["new"]) == {"contaminated_window_ids", "class", "evidence", "exposure_started_at"}
    assert env.reg.state("EXP-0201") == state                       # registrar no cambia el estado
    assert PR._deviation_shape_error(rec) is None
    assert [d["deviation_id"] for d in PR._replay(env.reg, "EXP-0201")] == [rec["deviation_id"]]


def test_independence_deviation_valid_variants_and_start_instant_boundaries(env):
    fz = _confirmatory_in(env, "PREREGISTERED")
    _deviation(fz, env, started="2027-03-01T00:00:00Z")                              # = inicio de la OOS
    _deviation(fz, env, ids=("EXP-0201/LOCKBOX",), cls="PREMATURE_INSPECTION", started="2028-03-01T00:00:00Z")
    _deviation(fz, env, ids=("EXP-0201/LOCKBOX",), cls="INDEPENDENCE_UNVERIFIABLE", started="UNKNOWN")
    _deviation(fz, env, ids=("EXP-0201/LOCKBOX", "EXP-0201/OOS"), started="2029-01-01T00:00:00Z")
    assert len(PR._replay(env.reg, "EXP-0201")) == 4


def _new(**over):
    base = {"contaminated_window_ids": ["EXP-0201/OOS"], "class": "UNAUTHORIZED_EXPOSURE",
            "evidence": [EVIDENCE_REF], "exposure_started_at": "UNKNOWN"}
    base.update(over)
    return {k: v for k, v in base.items() if v is not ...}


MALFORMED_NEW = {
    "extra_key": _new(extra=1),
    "missing_class": _new(**{"class": ...}),
    "missing_evidence": _new(evidence=...),
    "missing_started": _new(exposure_started_at=...),
    "missing_ids": _new(contaminated_window_ids=...),
    "ids_empty": _new(contaminated_window_ids=[]),
    "ids_not_list": _new(contaminated_window_ids="EXP-0201/OOS"),
    "ids_duplicate": _new(contaminated_window_ids=["EXP-0201/OOS", "EXP-0201/OOS"]),
    "ids_other_experiment": _new(contaminated_window_ids=["EXP-0202/OOS"]),
    "ids_unknown_window": _new(contaminated_window_ids=["EXP-0201/CONTEXT"]),
    "ids_lowercase": _new(contaminated_window_ids=["EXP-0201/oos"]),
    "ids_not_str": _new(contaminated_window_ids=[1]),
    "ids_one_foreign_among_valid": _new(contaminated_window_ids=["EXP-0201/OOS", "EXP-0200/LOCKBOX"]),
    "class_unknown": _new(**{"class": "OTHER"}),
    "class_lowercase": _new(**{"class": "unauthorized_exposure"}),
    "evidence_empty": _new(evidence=[]),
    "evidence_not_list": _new(evidence=EVIDENCE_REF),
    "evidence_bad_ref": _new(evidence=["DEC-999"]),
    "evidence_path_traversal": _new(evidence=["repo@abc1234:../x"]),
    "started_before_oos": _new(exposure_started_at="2027-02-28T23:59:59Z"),
    "started_before_lockbox": _new(contaminated_window_ids=["EXP-0201/LOCKBOX"],
                                   exposure_started_at="2028-02-29T23:59:59Z"),
    "started_before_latest_cited_window": _new(contaminated_window_ids=["EXP-0201/OOS", "EXP-0201/LOCKBOX"],
                                               exposure_started_at="2027-06-01T00:00:00Z"),
    "started_date_only": _new(exposure_started_at="2027-03-02"),
    "started_offset": _new(exposure_started_at="2027-03-02T00:00:00+00:00"),
    "started_lowercase_unknown": _new(exposure_started_at="unknown"),
    "started_not_str": _new(exposure_started_at=1800000000),
    "started_none": _new(exposure_started_at=None),
}


@pytest.mark.parametrize("name", sorted(MALFORMED_NEW))
def test_tc_ml_026_malformed_independence_deviation_is_rejected_before_writing(env, name):
    fz = _confirmatory_in(env, "PREREGISTERED")
    before = env.records_bytes()
    with pytest.raises(PreregistrationError):
        fz.record_deviation("independence_boundary", MALFORMED_NEW[name], "x", registry=env.reg, informed_by=[])
    assert env.records_bytes() == before                             # nada escrito
    assert fz.deviations == [] and not [r for r in env.reg.records() if r["kind"] == "DEVIATION"]


def test_malformed_new_that_is_not_a_dict_and_missing_informed_by_are_rejected(env):
    fz = _confirmatory_in(env, "PREREGISTERED")
    before = env.records_bytes()
    for bad in (None, [], "UNKNOWN", ["EXP-0201/OOS"]):
        with pytest.raises(PreregistrationError):
            fz.record_deviation("independence_boundary", bad, "x", registry=env.reg, informed_by=[])
    with pytest.raises(PreregistrationError, match="informed_by"):
        fz.record_deviation("independence_boundary", _new(), "x", registry=env.reg, informed_by=None)
    with pytest.raises(PreregistrationError):                        # el método sancionado también valida
        fz.record_independence_deviation(["EXP-0202/OOS"], "UNAUTHORIZED_EXPOSURE", [EVIDENCE_REF], "UNKNOWN",
                                         "x", registry=env.reg, informed_by=[])
    with pytest.raises(PreregistrationError, match="justificar"):
        _deviation_blank(fz, env)
    assert env.records_bytes() == before


def _deviation_blank(fz, env):
    return fz.record_independence_deviation(["EXP-0201/OOS"], "UNAUTHORIZED_EXPOSURE", [EVIDENCE_REF], "UNKNOWN",
                                            "  ", registry=env.reg, informed_by=[])


def test_independence_deviation_is_rejected_for_a_pilot(env):
    pilot = env.pilot()
    before = env.records_bytes()
    with pytest.raises(PreregistrationError, match="piloto|frontera confirmatoria"):
        pilot.record_independence_deviation([f"{PILOT_ID}/OOS"], "UNAUTHORIZED_EXPOSURE", [EVIDENCE_REF], "UNKNOWN",
                                            "x", registry=env.reg, informed_by=[])
    with pytest.raises(PreregistrationError):
        pilot.record_deviation("independence_boundary", _new(contaminated_window_ids=[f"{PILOT_ID}/OOS"]), "x",
                               registry=env.reg, informed_by=[])
    assert env.records_bytes() == before


INJECTED_NEW = {
    "ids_empty": _new(contaminated_window_ids=[]),
    "wrong_shape": {"class": "X"},
    "extra_key": _new(extra=1),
    "started_before_window": _new(exposure_started_at="2026-01-01T00:00:00Z"),
}


@pytest.mark.parametrize("name", sorted(INJECTED_NEW))
def test_replay_fails_closed_on_a_malformed_independence_record_injected_into_the_registry(env, name):
    fz = _confirmatory_in(env, "PREREGISTERED")
    good = _deviation(fz, env)
    assert PR.confirmatory_findings(env.reg, "EXP-0201")["confirmatory"] is False   # B4: regla endurecida (§C.5)
    env.reg._append({**good, "deviation_id": "e" * 32, "new": INJECTED_NEW[name]})   # inyección sin validar
    with pytest.raises(PreregistrationError, match="incoherente"):
        PR.confirmatory_findings(env.reg, "EXP-0201")
    with pytest.raises(PreregistrationError, match="incoherente"):
        fz.record_deviation("limitations", "y", "x", registry=env.reg, informed_by=[])
    with pytest.raises(PreregistrationError, match="incoherente"):
        PR.confirmatory_status(env.reg, "EXP-0201", preregistration=fz)


@pytest.mark.parametrize("bad_old", ["pilot", "garbage"])
def test_replay_rejects_independence_record_whose_old_is_not_a_valid_confirmatory_boundary(env, bad_old):
    fz = _confirmatory_in(env, "PREREGISTERED")
    good = _deviation(fz, env)
    old = dict(B.PILOT_BOUNDARY) if bad_old == "pilot" else {"confirmatory_eligible": True}
    env.reg._append({**good, "deviation_id": "d" * 32, "old": old})
    with pytest.raises(PreregistrationError, match="incoherente"):
        PR.confirmatory_findings(env.reg, "EXP-0201")


def test_independence_deviation_does_not_change_cr020_accounting_or_status(env):
    fz = _confirmatory_in(env, "PREREGISTERED")
    env.to_validation("EXP-0201")
    fz.begin_evaluation("A", registry=env.reg)
    acc_before, count_before = env.reg.accounting(), env.reg.trials_count()
    status_before = confirmatory_findings(env.reg, "EXP-0201")
    state_before = env.reg.experiments()["EXP-0201"]["state"]
    rec = _deviation(fz, env, started="2027-03-05T00:00:00Z", informed_by=[{"experiment_id": "EXP-0201",
                                                                            "config_id": "A"}])
    acc_after, status_after = env.reg.accounting(), confirmatory_findings(env.reg, "EXP-0201")
    assert acc_after == acc_before and env.reg.trials_count() == count_before
    assert env.reg.experiments()["EXP-0201"]["state"] == state_before
    assert status_before["confirmatory"] is True and status_after["confirmatory"] is False   # B4: regla endurecida (§C.5)
    assert status_after["design_deviations_after_oos"] == [] and status_after["unplanned_config_ids"] == []
    assert [d["deviation_id"] for d in status_after["deviations"]] == [rec["deviation_id"]]
    assert env.reg.certified("EXP-0201", "A") and env.reg.evaluation_recorded("EXP-0201", "A")
    assert PR.evaluation_evidence_error(env.reg, "EXP-0201", "A") is None


def test_independence_is_a_known_deviation_field_for_every_experiment_class():
    assert "independence_boundary" in PR.REQUIRED_FIELDS and "independence_boundary" not in PR.DESIGN_FIELDS


# ====================================================================================================
# B3-01: la comprobación de ET-1 no la aporta quien llama a `transition`
# ====================================================================================================

def _direct(env, eid, fz, check, **ev_over):
    """Transición directa (sin `preregister`) con una comprobación auténtica y evidencia opcionalmente alterada."""
    ev = {**freeze_evidence(fz), **ev_over}
    return env.reg.transition(eid, "PREREGISTERED", actor=ACTOR, evidence=ev, freeze_check=check)


def _check(env, fz, **kw):
    return build_freeze_check(fz, env.store, dev_manifest_path=kw.get("manifest", env.res.manifest_path),
                              data_root=kw.get("data_root", env.data_root))


def test_b3_01_freeze_check_cannot_be_built_without_the_credential_and_is_immutable(env):
    for key in (None, object(), "_FREEZE_CHECK_KEY"):
        with pytest.raises(ExperimentError, match="build_freeze_check"):
            FreezeCheck(key, lambda *a: None)
    with pytest.raises(ExperimentError):
        FreezeCheck(_FREEZE_CHECK_KEY, "no invocable")
    fz = env.frozen(PILOT_ID, pilot=True)
    check = _check(env, fz)
    with pytest.raises(AttributeError):
        check._fn = lambda *a: None


def test_b3_01_plain_callable_cannot_freeze_without_stored_content(env):
    """Sonda P1: antes, un invocable nulo congelaba como CONFIRMATORY sin almacén, snapshot ni piloto."""
    env.design("EXP-0201")
    before = env.records_bytes()
    for fn in (lambda records: None, lambda records, experiment_id, evidence: None):
        with pytest.raises(ExperimentError, match="freeze_check"):
            env.reg.transition("EXP-0201", "PREREGISTERED", actor=ACTOR, freeze_check=fn,
                               evidence={"preregistration_sha256": "b" * 64, "min_history_ok": True,
                                         "independence_class": "CONFIRMATORY",
                                         "trials_accounting": env.reg.trials_accounting("EXP-0201", ["A"])})
    assert env.records_bytes() == before and env.reg.state("EXP-0201") == "DESIGN"


@pytest.mark.parametrize("over", [
    {"independence_class": "CONFIRMATORY", "min_history_ok": True},   # piloto declarado confirmatorio (sonda P2)
    {"preregistration_sha256": "c" * 64},                              # otro SHA-256
    {"trials_accounting": {"H_doc": 0, "H_bound": 0, "E": 0, "planned_config_ids": ["A"], "planned_new": 1,
                           "N_pre": 9, "provenance_ids": []}},
    {"extra": True},                                                   # clave añadida
])
def test_b3_01_authentic_check_rejects_evidence_not_implied_by_the_frozen_content(env, over):
    env.design(PILOT_ID)
    fz = env.frozen(PILOT_ID, pilot=True)
    env.store.write_frozen(fz)
    ev = {**freeze_evidence(fz), **over}
    if "min_history_ok" in over:
        ev.pop("min_history_exempt", None)
    before = env.records_bytes()
    with pytest.raises(ExperimentError):
        env.reg.transition(PILOT_ID, "PREREGISTERED", actor=ACTOR, evidence=ev, freeze_check=_check(env, fz))
    assert env.records_bytes() == before and env.reg.state(PILOT_ID) == "DESIGN"
    _direct(env, PILOT_ID, fz, _check(env, fz))                         # con la evidencia exacta: admitido
    assert env.reg.state(PILOT_ID) == "PREREGISTERED"


def test_b3_01_pilot_cannot_reach_oos_evaluation_through_a_direct_transition(env):
    env.design(PILOT_ID)
    fz = env.frozen(PILOT_ID, pilot=True)
    env.store.write_frozen(fz)
    ev = {k: v for k, v in freeze_evidence(fz).items() if k != "min_history_exempt"}
    ev.update(independence_class="CONFIRMATORY", min_history_ok=True)     # sonda P2
    with pytest.raises(ExperimentError, match="no coincide"):
        env.reg.transition(PILOT_ID, "PREREGISTERED", actor=ACTOR, evidence=ev, freeze_check=_check(env, fz))
    assert env.reg.state(PILOT_ID) == "DESIGN"


def test_b3_01_authentic_check_of_another_experiment_is_rejected(env):
    env.design(PILOT_ID)
    env.design("EXP-0202")
    fz = env.frozen(PILOT_ID, pilot=True)
    env.store.write_frozen(fz)
    with pytest.raises(ExperimentError, match="EXP-0202"):
        env.reg.transition("EXP-0202", "PREREGISTERED", actor=ACTOR, evidence=freeze_evidence(fz),
                           freeze_check=_check(env, fz))
    assert env.reg.state("EXP-0202") == "DESIGN"


def test_b3_01_snapshot_checks_run_inside_the_lock_for_direct_transitions(env, tmp_path):
    """Sonda P3: I2 y la vinculación de la snapshot se comprueban dentro del bloqueo, no solo en `preregister`."""
    env.pilot()
    env.design("EXP-0203")
    fz = env.frozen("EXP-0203", tv_sha="c" * 64)                        # no es la snapshot verificada
    env.store.write_frozen(fz)
    with pytest.raises(ExperimentError, match="train_val_sha256"):
        _direct(env, "EXP-0203", fz, _check(env, fz))
    fz_ok = env.frozen("EXP-0203")
    env.store.write_frozen(fz_ok)
    with pytest.raises(ExperimentError, match="I2"):                     # snapshot no verificable
        _direct(env, "EXP-0203", fz_ok, _check(env, fz_ok, manifest=tmp_path / "no-existe.json"))
    fz_av = env.frozen("EXP-0203", available=60.0)                       # available_months no recalculado
    env.store.write_frozen(fz_av)
    with pytest.raises(ExperimentError, match="available_months"):
        _direct(env, "EXP-0203", fz_av, _check(env, fz_av))
    assert env.reg.state("EXP-0203") == "DESIGN"
    _direct(env, "EXP-0203", fz_ok, _check(env, fz_ok))
    assert env.reg.state("EXP-0203") == "PREREGISTERED"


def test_b3_01_static_guard_freeze_credential_only_in_registry_and_preregistration():
    """Guarda estática (como la de `_load_train_val_for_inspection`): en `src/` y `scripts/` solo
    `experiments.py` y `preregistration.py` referencian la credencial o construyen `FreezeCheck`."""
    root = Path(__file__).resolve().parents[2]
    allowed = {root / "src/swingpilot/research/experiments.py", root / "src/swingpilot/research/preregistration.py"}
    offenders = []
    for base in (root / "src", root / "scripts"):
        for f in base.rglob("*.py"):
            text = f.read_text(encoding="utf-8")
            if f not in allowed and ("_FREEZE_CHECK_KEY" in text or "FreezeCheck(" in text):
                offenders.append(str(f.relative_to(root)))
    assert offenders == []


def test_b3_02_additional_documented_exposure_is_accepted_by_et1_and_raises_the_floor_of_b(env):
    """B3-02: el inventario obligatorio es un mínimo; una exposición documentada adicional se admite en ET-1
    y su `b_not_before` desplaza el `B` mínimo admisible."""
    extra = {"id": "EXTRA_DOCUMENTED_NOTEBOOK", "class": "DOCUMENTED", "period_start": "2026-12-01T00:00:00Z",
             "period_end": "2027-01-01T00:00:00Z", "b_not_before": "2027-01-02T00:00:00Z",
             "evidence": [EVIDENCE_REF], "note": "exposición documentada adicional"}

    def add_extra(c):
        inv = c[IB]["exposure_inventory"]
        inv["entries"].append(dict(extra))
        inv["entries"][0]["evidence"].append(EVIDENCE_REF)        # evidencia adicional en una obligatoria
    env.pilot()
    env.design("EXP-0201")
    _fail_et1(env, "EXP-0201", env.frozen("EXP-0201", mutate=add_extra, b="2027-01-01T00:00:00Z"), "b_not_before|B")
    env.prereg(env.frozen("EXP-0201", mutate=add_extra, b="2027-01-02T00:00:00Z"))
    assert env.reg.state("EXP-0201") == "PREREGISTERED"


# ====================================================================================================
# FIX-A (QA-C1-03): el acceso confirmatorio se liga a snapshot_id, train_val_sha256 y d_dev congelados
# ====================================================================================================

def _mismatch(manifest, key):
    m = copy.deepcopy(manifest)
    if key == "snapshot_id":
        m["snapshot_id"] = "SNAP-OTHER"
    elif key == "train_val_sha256":
        m["files"]["train_val"]["sha256"] = "f" * 64
    else:
        m["d_dev"] = "2000-01-01"
    return m


@pytest.mark.parametrize("key", ["snapshot_id", "train_val_sha256", "d_dev"])
def test_fixa_confirmatory_access_denied_on_snapshot_mismatch_before_data_access(env, key):
    _evaluating(env, PILOT_ID, pilot=True)
    _evaluating(env, "EXP-0201", pilot=False)
    loader = _loader(env)
    loader.manifest = _mismatch(loader.manifest, key)
    reads = _spy(loader)
    with pytest.raises(PartitionAccessError, match="distinta de la preregistrada"):
        loader.load_train_val_for_configuration("EXP-0201", "A")
    assert reads == [] and loader.access_history()[-1]["allowed"] is False


def test_fixa_confirmatory_access_with_matching_snapshot_still_works(env):
    _evaluating(env, PILOT_ID, pilot=True)
    _evaluating(env, "EXP-0201", pilot=False)
    df = _loader(env).load_train_val_for_configuration("EXP-0201", "A")
    assert df["open_time"].max() >= env.manifest["cuts_ms"]["train_end"]
