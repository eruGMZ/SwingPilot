"""Arranque de la capa de IA (FEAT-007; REQ-G-033, REQ-G-091, REQ-G-093, REQ-G-096; INV-012).

Conecta en un solo punto las piezas de seguridad y costo, para que no dependan de que cada
llamador las active:
1. `startup_violations` → si hay alguna, no arranca (Fail-Closed).
2. CredentialVault desde `.env` (sin copiar a os.environ).
3. AIBudget (tope y aviso; zona America/Mexico_City) con AI_BUDGET_WARNING al EventStore.
4. EventStore con `secret_check` del vault.
5. AIProviderAdapter.from_vault (clave del ámbito ai_provider, leak_check, presupuesto).
6. AIOrchestrator con EntryGate (estado del sistema + tope) y `redact` del vault.

`system_state` lo provee quien arranca (hoy pruebas; el Risk Manager en IMPL-4). Sin él no
hay arranque: el EntryGate no puede decidir y el contrato exige Fail-Closed.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from swingpilot.ai import (
    AIBudget, AIOrchestrator, AIProviderAdapter, EntryGate, budget_warning_emitter,
)
from swingpilot.audit import EventStore
from swingpilot.security import CredentialVault, startup_violations


class StartupError(RuntimeError):
    def __init__(self, violations: list[str]):
        self.violations = violations
        super().__init__("arranque bloqueado: " + ", ".join(violations))


@dataclass
class AIStack:
    mode: str
    vault: CredentialVault
    budget: AIBudget
    store: EventStore
    adapter: AIProviderAdapter
    orchestrator: AIOrchestrator

    def close(self) -> None:
        self.store.close()
        self.budget.close()


def build_ai_stack(*, env_path: str | Path, mode: str, data_dir: str | Path,
                   system_state: Callable[[], dict], client=None,
                   environ=None) -> AIStack:
    """`client`: solo para pruebas (cliente falso); en uso real se crea desde el vault."""
    violations = startup_violations(env_path, mode, environ)
    if violations:
        raise StartupError(violations)
    vault = CredentialVault.from_env_file(env_path)
    data = Path(data_dir)
    data.mkdir(parents=True, exist_ok=True)
    store = EventStore(data / "audit.db", secret_check=vault.contains_secret)
    budget = AIBudget(data / "ai_budget.db", on_warning=budget_warning_emitter(store))
    if client is None:
        adapter = AIProviderAdapter.from_vault(vault, budget=budget)
    else:
        adapter = AIProviderAdapter(client, budget=budget, leak_check=vault.contains_secret)
    orchestrator = AIOrchestrator(adapter, store, precheck=EntryGate(system_state, budget),
                                  redact=vault.redact)
    return AIStack(mode, vault, budget, store, adapter, orchestrator)
