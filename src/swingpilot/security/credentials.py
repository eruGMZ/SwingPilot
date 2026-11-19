"""Aislamiento de credenciales (REQ-G-058, REQ-G-059, REQ-G-093, REQ-G-033, REQ-G-091;
TC-SEC-001, TC-SEC-002, TC-SEC-006).

- Los secretos se leen del archivo `.env` a un almacén privado; NO se copian a
  `os.environ`, para que no queden al alcance de todo el proceso.
- Cada componente recibe solo las credenciales de su ámbito. El AI Orchestrator y los
  agentes LLM no tienen ámbito: pedir credenciales para ellos es un error.
- `Secret` no se imprime, no se serializa a JSON y no se compara por texto; el valor
  solo se obtiene con `.reveal()` en el punto de uso.
- Este es el único módulo de `src/` que nombra las variables de credenciales (TC-SEC-001).

Nombres de variables: BINANCE_API_KEY y ANTHROPIC_API_KEY vienen de TC-SEC-001;
BINANCE_API_SECRET y TELEGRAM_BOT_TOKEN son nombres de implementación (ver .env.example).
"""
import os
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

COMPONENT_SCOPES: Mapping[str, frozenset[str]] = MappingProxyType({
    "execution_engine": frozenset({"BINANCE_API_KEY", "BINANCE_API_SECRET"}),
    "ai_provider": frozenset({"ANTHROPIC_API_KEY"}),
    "telegram_bot": frozenset({"TELEGRAM_BOT_TOKEN"}),
})
ALL_SECRET_NAMES = frozenset().union(*COMPONENT_SCOPES.values())
# Credenciales que nunca deben estar en el entorno del proceso (alcance global).
PROCESS_ENV_FORBIDDEN = frozenset({"BINANCE_API_KEY", "BINANCE_API_SECRET", "TELEGRAM_BOT_TOKEN"})


class CredentialError(PermissionError):
    pass


class Secret:
    __slots__ = ("_value",)

    def __init__(self, value: str):
        if not isinstance(value, str) or not value:
            raise CredentialError("secreto vacío o inválido")
        self._value = value

    def reveal(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return "Secret(***)"

    __str__ = __repr__

    def __eq__(self, other):  # evita comparaciones accidentales con texto
        return isinstance(other, Secret) and other._value == self._value

    def __hash__(self):
        return hash(("Secret", self._value))

    def __reduce__(self):
        raise TypeError("Secret no es serializable")


def _parse_env(text: str) -> dict[str, str]:
    out = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, sep, value = line.partition("=")
        if not sep:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        out[key.strip()] = value
    return out


class CredentialVault:
    def __init__(self, values: Mapping[str, str]):
        self._secrets = {k: Secret(v) for k, v in values.items() if k in ALL_SECRET_NAMES and v}

    @classmethod
    def from_env_file(cls, path: str | Path) -> "CredentialVault":
        return cls(_parse_env(Path(path).read_text(encoding="utf-8")))

    def for_component(self, component: str) -> Mapping[str, Secret]:
        """Credenciales del ámbito del componente. Falta alguna → CredentialError."""
        if component not in COMPONENT_SCOPES:
            raise CredentialError(f"el componente {component!r} no tiene acceso a credenciales")
        names = COMPONENT_SCOPES[component]
        missing = sorted(n for n in names if n not in self._secrets)
        if missing:
            raise CredentialError(f"faltan credenciales para {component}: {', '.join(missing)}")
        return MappingProxyType({n: self._secrets[n] for n in names})

    def contains_secret(self, text: str) -> bool:
        """True si algún valor secreto aparece en `text` (fuga hacia LLM o registros)."""
        return any(s.reveal() in text for s in self._secrets.values())

    def redact(self, text: str) -> str:
        for s in self._secrets.values():
            text = text.replace(s.reveal(), "***")
        return text

    def __repr__(self) -> str:
        return f"CredentialVault({sorted(self._secrets)})"


def process_env_violations(environ: Mapping[str, str] | None = None) -> list[str]:
    """Credenciales de Binance/Telegram presentes en el entorno del proceso: deben vivir
    solo en `.env` y entregarse por ámbito. Lista no vacía → no arrancar (Fail-Closed)."""
    env = os.environ if environ is None else environ
    return sorted(n for n in PROCESS_ENV_FORBIDDEN if env.get(n))
