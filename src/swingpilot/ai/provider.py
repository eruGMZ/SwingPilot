"""AI Provider Adapter sobre la Messages API de Anthropic (REQ-G-090, REQ-G-091,
REQ-G-095, REQ-G-034).

Reglas del contrato implementadas:
- Modelos con identificador exacto por agente; `model_id` = modelo efectivamente usado
  (el de la respuesta, no el que declare el LLM).
- Una llamada independiente a la Messages API por agente; SIN herramientas, SIN
  `fallbacks`, SIN `cache_control`, sin Agent SDK/Managed Agents/Batches.
- Salida estructurada por esquema (`output_config.format`) y validación local contra el
  mismo esquema; lo que no valida es «fuera de contrato».
- `stop_reason: "refusal"` = fallo del agente, sin reintento ni cambio de modelo.
- Un único reintento (nuestro; el del SDK se desactiva con max_retries=0) ante error
  transitorio o salida fuera de contrato, tras pausa breve y dentro del límite de 5 min
  del ciclo; timeout de 60 s en el cliente. Fallo persistente → resultado ERROR/TIMEOUT
  (el llamador termina el ciclo sin propuesta: Fail-Closed).
- Se registra `usage` de cada llamada (REQ-G-096 (5)).
- La API key llega desde CredentialVault (ámbito «ai_provider», `from_vault`); este módulo no
  nombra variables de credenciales (TC-SEC-001).
- `leak_check`: si un secreto aparece en el prompt o los datos, no se llama al modelo
  (REQ-G-033, TC-SEC-002).
"""
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable

import anthropic
from jsonschema import Draft202012Validator

AGENT_MODELS = {
    "market_analyst": "claude-haiku-5-5",
    "macro_analyst": "claude-haiku-5-5",
    "strategy_analyst": "claude-haiku-5-5",
    "risk_analyst": "claude-haiku-5-5",
    "decision_synthesis": "claude-sonnet-5-5",
}
DEFAULT_EFFORT = "medium"  # valor inicial REQ-G-095; calibración PENDING (modo de prueba)
CLIENT_TIMEOUT_SECONDS = 60.0  # REQ-G-034
CYCLE_DEADLINE_SECONDS = 300.0  # REQ-G-034: límite de 5 min del ciclo
RETRY_PAUSE_SECONDS = 2.0  # «pausa breve» (valor de implementación)
MAX_TOKENS = 16000  # valor de implementación; no fijado por el contrato

_TRANSIENT = (anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.InternalServerError)


@dataclass
class AgentCallResult:
    agent: str
    status: str  # COMPLETED | ERROR | TIMEOUT
    model_id: str | None = None  # modelo efectivo (response.model)
    output: dict | None = None
    error: dict | None = None  # {code, message}
    attempts: int = 0
    usage: list[dict] = field(default_factory=list)  # una entrada por intento con respuesta

    @property
    def ok(self) -> bool:
        return self.status == "COMPLETED"


class _OutOfContract(Exception):
    pass


class _Refusal(Exception):
    pass


class AIProviderAdapter:
    def __init__(self, client: Any = None, *, efforts: dict[str, str] | None = None,
                 sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.monotonic, budget: Any = None,
                 leak_check: Callable[[str], bool] | None = None):
        # max_retries=0: el único reintento es el propio (REQ-G-034).
        self._client = client or anthropic.Anthropic(max_retries=0, timeout=CLIENT_TIMEOUT_SECONDS)
        self._efforts = {a: DEFAULT_EFFORT for a in AGENT_MODELS} | (efforts or {})
        self._sleep, self._clock = sleep, clock
        self._budget = budget  # AIBudget opcional (REQ-G-096): tope y registro de costo
        self._leak_check = leak_check

    @classmethod
    def from_vault(cls, vault: Any, **kwargs) -> "AIProviderAdapter":
        """Cliente real con la clave del ámbito «ai_provider» y control de fugas activo."""
        (key,) = vault.for_component("ai_provider").values()
        client = anthropic.Anthropic(api_key=key.reveal(), max_retries=0,
                                     timeout=CLIENT_TIMEOUT_SECONDS)
        kwargs.setdefault("leak_check", vault.contains_secret)
        return cls(client, **kwargs)

    def _request(self, agent: str, system: str, user_content: str, schema: dict, timeout: float) -> dict:
        return dict(
            model=AGENT_MODELS[agent],
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user_content}],
            output_config={"effort": self._efforts[agent],
                           "format": {"type": "json_schema", "schema": schema}},
            timeout=timeout,
        )

    def call_agent(self, agent: str, *, system: str, user_content: str, output_schema: dict,
                   deadline: float | None = None) -> AgentCallResult:
        """`deadline`: instante (reloj monotónico inyectado) en que vence el ciclo; por
        defecto ahora + 5 min."""
        if agent not in AGENT_MODELS:
            raise ValueError(f"agente desconocido: {agent!r}")
        Draft202012Validator.check_schema(output_schema)
        res0 = AgentCallResult(agent=agent, status="ERROR")
        if self._leak_check is not None and (self._leak_check(system) or self._leak_check(user_content)):
            res0.error = {"code": "SECRET_LEAK_BLOCKED", "message": "credencial en el contenido para el LLM"}
            return res0  # nunca se envía
        deadline = self._clock() + CYCLE_DEADLINE_SECONDS if deadline is None else deadline
        res = AgentCallResult(agent=agent, status="ERROR")
        for attempt in (1, 2):
            remaining = deadline - self._clock()
            if remaining <= 0:
                res.status, res.error = "TIMEOUT", {"code": "CYCLE_DEADLINE", "message": "límite del ciclo agotado"}
                return res
            rid = None
            if self._budget is not None:
                rid = self._budget.try_reserve(AGENT_MODELS[agent],
                                               _max_input_tokens(system, user_content, output_schema),
                                               MAX_TOKENS)
                if rid is None:
                    res.status = "ERROR"
                    res.error = {"code": "AI_BUDGET_CAP_REACHED", "message": "tope mensual de IA alcanzado"}
                    return res  # sin llamada (REQ-G-034, REQ-G-096 (1))
            res.attempts = attempt
            try:
                resp = self._client.messages.create(
                    **self._request(agent, system, user_content, output_schema,
                                    min(CLIENT_TIMEOUT_SECONDS, remaining)))
                # Modelo efectivo de la respuesta, sin sustituirlo por el pedido: si falta,
                # la salida no valida contra el contrato (model_id obligatorio).
                res.model_id = getattr(resp, "model", None)
                res.usage.append(_usage(resp))
                if self._budget is not None:
                    u, rid_done, rid = res.usage[-1], rid, None
                    try:
                        self._budget.settle(rid_done, agent, u["model"], u["input_tokens"], u["output_tokens"])
                    except (KeyError, ValueError) as e:
                        res.status = "ERROR"
                        res.error = {"code": "COST_UNMEASURABLE", "message": str(e)}
                        return res  # Fail-Closed: no se puede medir el gasto
                res.output = self._parse(resp, output_schema)
                res.status, res.error = "COMPLETED", None
                return res
            except _Refusal as e:
                res.status, res.error = "ERROR", {"code": "AGENT_REFUSAL", "message": str(e)}
                return res  # sin reintento ni cambio de modelo
            except _OutOfContract as e:
                res.status, res.error = "ERROR", {"code": "OUT_OF_CONTRACT", "message": str(e)}
            except anthropic.APITimeoutError as e:  # subclase de APIConnectionError: antes
                res.status, res.error = "TIMEOUT", {"code": "TIMEOUT", "message": str(e)}
            except _TRANSIENT as e:
                res.status, res.error = "ERROR", {"code": "TRANSIENT_API_ERROR", "message": type(e).__name__}
            except anthropic.APIError as e:  # 400/401/403/404...: no transitorio
                res.status, res.error = "ERROR", {"code": "API_ERROR", "message": type(e).__name__}
                return res
            finally:
                if rid is not None:  # llamada fallida sin respuesta: se libera la reserva
                    self._budget.release(rid)
            if attempt == 1:
                self._sleep(RETRY_PAUSE_SECONDS)
        return res

    @staticmethod
    def _parse(resp: Any, schema: dict) -> dict:
        if resp.stop_reason == "refusal":
            details = getattr(resp, "stop_details", None)
            raise _Refusal(f"el modelo rechazó la solicitud: {getattr(details, 'category', None)}")
        if resp.stop_reason != "end_turn":
            raise _OutOfContract(f"stop_reason inesperado: {resp.stop_reason}")
        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise _OutOfContract(f"la salida no es JSON: {e}") from e
        errs = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.path))
        if errs:
            raise _OutOfContract("; ".join(f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errs))
        return data


def _max_input_tokens(system: str, user_content: str, schema: dict) -> int:
    """Cota superior de tokens de entrada para la reserva: 1 token por BYTE UTF-8 (texto,
    datos y esquema) + 2 000 de margen para el formato de la petición. Un tokenizador de
    nivel byte nunca produce más tokens que bytes, así que la cota vale también para texto
    no ASCII (acentos, CJK, emoji)."""
    size = sum(len(s.encode("utf-8")) for s in (system, user_content, json.dumps(schema, ensure_ascii=False)))
    return size + 2000


def _usage(resp: Any) -> dict:
    u = getattr(resp, "usage", None)
    return {"model": getattr(resp, "model", None),
            "input_tokens": getattr(u, "input_tokens", None),
            "output_tokens": getattr(u, "output_tokens", None)}
