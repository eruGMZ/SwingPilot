"""FEAT-004 con dobles de prueba (sin red ni API key) — REQ-G-034, REQ-G-095, TC-AC-02/05, TC-SEC-001."""
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import anthropic
import httpx2 as httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from swingpilot.ai import AGENT_MODELS, AIProviderAdapter, CLIENT_TIMEOUT_SECONDS  # noqa: E402

SCHEMA = {"type": "object", "additionalProperties": False, "required": ["agent", "status"],
          "properties": {"agent": {"type": "string"}, "status": {"enum": ["COMPLETED", "INSUFFICIENT_DATA", "ERROR"]}}}
GOOD = {"agent": "market_analyst", "status": "COMPLETED"}
REQ = httpx.Request("POST", "https://api.anthropic.com/v1/messages")


def resp(text=None, stop="end_turn", model="claude-haiku-5-5", details=None):
    return NS(stop_reason=stop, stop_details=details, model=model,
              content=[NS(type="text", text=text if text is not None else json.dumps(GOOD))],
              usage=NS(input_tokens=100, output_tokens=20))


class FakeClient:
    """Reproduce una secuencia de respuestas/excepciones y guarda cada llamada."""
    def __init__(self, *script):
        self.script, self.calls = list(script), []
        self.messages = NS(create=self._create)

    def _create(self, **kw):
        self.calls.append(kw)
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def adapter(client, clock=None):
    sleeps = []
    a = AIProviderAdapter(client, sleep=sleeps.append, **({"clock": clock} if clock else {}))
    return a, sleeps


def call(a, agent="market_analyst", **kw):
    return a.call_agent(agent, system="sys", user_content="{}", output_schema=SCHEMA, **kw)


def rate_limit():
    return anthropic.RateLimitError("x", response=httpx.Response(429, request=REQ), body=None)


def server_error():
    return anthropic.InternalServerError("x", response=httpx.Response(529, request=REQ), body=None)


def bad_request():
    return anthropic.BadRequestError("x", response=httpx.Response(400, request=REQ), body=None)


def test_success_records_model_usage_and_structured_request():
    c = FakeClient(resp())
    a, _ = adapter(c)
    r = call(a)
    assert r.ok and r.output == GOOD and r.attempts == 1
    assert r.model_id == "claude-haiku-5-5"
    assert r.usage == [{"model": "claude-haiku-5-5", "input_tokens": 100, "output_tokens": 20}]
    kw = c.calls[0]
    assert kw["model"] == "claude-haiku-5-5"
    assert kw["output_config"]["format"] == {"type": "json_schema", "schema": SCHEMA}
    assert kw["output_config"]["effort"] == "medium"
    assert kw["timeout"] <= CLIENT_TIMEOUT_SECONDS


@pytest.mark.parametrize("agent,model", list(AGENT_MODELS.items()))
def test_each_agent_uses_assigned_exact_model(agent, model):
    c = FakeClient(resp(model=model))
    a, _ = adapter(c)
    assert call(a, agent).model_id == model
    assert c.calls[0]["model"] == model
    assert not re.search(r"-\d{8}$", model)  # sin sufijos de fecha ni alias


def test_decision_synthesis_is_sonnet_and_analysts_haiku():
    assert AGENT_MODELS["decision_synthesis"] == "claude-sonnet-5-5"
    assert {AGENT_MODELS[k] for k in ("market_analyst", "macro_analyst", "strategy_analyst", "risk_analyst")} == {"claude-haiku-5-5"}


def test_model_id_is_the_effective_model_not_llm_claimed():
    schema = {"type": "object", "properties": {"model_id": {"type": "string"}}}
    c = FakeClient(resp(text=json.dumps({"model_id": "claude-fake"}), model="claude-haiku-5-5"))
    a, _ = adapter(c)
    r = a.call_agent("market_analyst", system="s", user_content="{}", output_schema=schema)
    assert r.model_id == "claude-haiku-5-5"  # el del servidor, no el que declara el LLM


# TC-AC-05 (b): sin herramientas, sin fallbacks, sin caching, sin thinking disabled
def test_request_has_no_tools_fallbacks_caching_or_extra_authority():
    c = FakeClient(resp())
    a, _ = adapter(c)
    call(a)
    kw = c.calls[0]
    for forbidden in ("tools", "tool_choice", "fallbacks", "betas", "cache_control", "thinking", "temperature", "speed"):
        assert forbidden not in kw
    assert "cache_control" not in json.dumps(kw)


def test_unknown_agent_rejected():
    a, _ = adapter(FakeClient())
    with pytest.raises(ValueError):
        call(a, "trader_bot")


# Fuera de contrato (TC-AC-02) y reintento único
def test_out_of_contract_retries_once_then_fails():
    c = FakeClient(resp(text='{"agent": 1}'), resp(text="no json"))
    a, sleeps = adapter(c)
    r = call(a)
    assert r.status == "ERROR" and r.error["code"] == "OUT_OF_CONTRACT"
    assert r.attempts == 2 and len(c.calls) == 2 and len(sleeps) == 1
    assert len(r.usage) == 2


def test_out_of_contract_then_valid_recovers():
    c = FakeClient(resp(text="{}"), resp())
    a, _ = adapter(c)
    r = call(a)
    assert r.ok and r.attempts == 2


def test_unknown_status_value_is_out_of_contract():
    c = FakeClient(resp(text='{"agent":"x","status":"APPROVED"}'), resp(text='{"agent":"x","status":"APPROVED"}'))
    a, _ = adapter(c)
    assert call(a).error["code"] == "OUT_OF_CONTRACT"


def test_max_tokens_truncation_is_out_of_contract():
    c = FakeClient(resp(stop="max_tokens"), resp(stop="max_tokens"))
    a, _ = adapter(c)
    assert call(a).error["code"] == "OUT_OF_CONTRACT"


# REQ-G-034: transitorios, como máximo 1 reintento
@pytest.mark.parametrize("exc", [rate_limit, server_error,
                                 lambda: anthropic.APIConnectionError(request=REQ)])
def test_transient_error_retries_once_and_recovers(exc):
    c = FakeClient(exc(), resp())
    a, sleeps = adapter(c)
    r = call(a)
    assert r.ok and r.attempts == 2 and len(sleeps) == 1


def test_persistent_transient_error_gives_up_after_one_retry():
    c = FakeClient(rate_limit(), rate_limit(), resp())
    a, _ = adapter(c)
    r = call(a)
    assert r.status == "ERROR" and r.error["code"] == "TRANSIENT_API_ERROR"
    assert len(c.calls) == 2  # el tercer item nunca se consume


def test_timeout_reported_as_timeout_status():
    c = FakeClient(anthropic.APITimeoutError(request=REQ), anthropic.APITimeoutError(request=REQ))
    a, _ = adapter(c)
    r = call(a)
    assert r.status == "TIMEOUT" and r.error["code"] == "TIMEOUT" and r.attempts == 2


def test_non_transient_error_is_not_retried():
    c = FakeClient(bad_request(), resp())
    a, sleeps = adapter(c)
    r = call(a)
    assert r.status == "ERROR" and r.error["code"] == "API_ERROR" and len(c.calls) == 1 and not sleeps


# Rechazo del modelo: fallo del agente, sin reintento ni cambio de modelo
def test_refusal_ends_without_retry_or_model_switch():
    c = FakeClient(resp(text="", stop="refusal", details=NS(category="cyber")), resp())
    a, _ = adapter(c)
    r = call(a)
    assert r.status == "ERROR" and r.error["code"] == "AGENT_REFUSAL" and r.output is None
    assert len(c.calls) == 1


# Límite de 5 min del ciclo
def test_expired_cycle_deadline_makes_no_call():
    c = FakeClient(resp())
    a, _ = adapter(c, clock=lambda: 1000.0)
    r = call(a, deadline=999.0)
    assert r.status == "TIMEOUT" and r.error["code"] == "CYCLE_DEADLINE" and not c.calls


def test_no_retry_beyond_deadline():
    t = {"now": 0.0}
    def clock(): return t["now"]
    class C(FakeClient):
        def _create(self, **kw):
            t["now"] = 301.0  # la primera llamada consume el ciclo completo
            return super()._create(**kw)
    c = C(rate_limit(), resp())
    a, _ = adapter(c, clock=clock)
    r = call(a)
    assert len(c.calls) == 1 and r.status == "TIMEOUT"


def test_call_timeout_is_capped_by_remaining_cycle_time():
    c = FakeClient(resp())
    a, _ = adapter(c, clock=lambda: 0.0)
    call(a, deadline=10.0)
    assert c.calls[0]["timeout"] == 10.0


# Cliente real: reintentos del SDK desactivados y timeout explícito
def test_default_client_disables_sdk_retries_and_sets_timeout(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    a = AIProviderAdapter()
    assert a._client.max_retries == 0
    assert a._client.timeout == CLIENT_TIMEOUT_SECONDS


# TC-SEC-001 sobre src/: los nombres solo en el módulo que lee .env; ningún valor literal
def test_no_api_keys_referenced_in_src():
    allowed = ROOT / "src" / "swingpilot" / "security" / "credentials.py"
    names = [p for p in (ROOT / "src").rglob("*.py") if p != allowed
             and re.search(r"BINANCE_API_KEY|ANTHROPIC_API_KEY|BINANCE_API_SECRET|TELEGRAM_BOT_TOKEN",
                           p.read_text(encoding="utf-8"))]
    literals = [p for p in (ROOT / "src").rglob("*.py")
                if re.search(r"sk-ant-[A-Za-z0-9]|\d{8,10}:[A-Za-z0-9_-]{30,}|['\"][A-Za-z0-9]{64}['\"]",
                             p.read_text(encoding="utf-8"))]
    assert names == [] and literals == []


# QA ronda 1, hallazgo 1: model_id = modelo de la respuesta aunque difiera del pedido
def test_model_id_records_response_model_even_if_different_from_requested():
    c = FakeClient(resp(model="claude-haiku-5-5-variante-servidor"))
    a, _ = adapter(c)
    r = call(a)
    assert c.calls[0]["model"] == "claude-haiku-5-5"
    assert r.model_id == "claude-haiku-5-5-variante-servidor"
    assert r.usage[0]["model"] == "claude-haiku-5-5-variante-servidor"


def test_missing_response_model_is_not_replaced_by_requested():
    r0 = resp()
    del r0.model
    a, _ = adapter(FakeClient(r0))
    assert call(a).model_id is None
