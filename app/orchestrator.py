"""Central agent orchestrator and policy boundary."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .audit import AuditLog
from .agents.providers import ExternalAPIProvider, provider_from_env
from .models import AuditEvent, IncomingMessage


class Agent(Protocol):
    def respond(self, message: IncomingMessage) -> str: ...


@dataclass(frozen=True)
class RouteDecision:
    agent: str
    reason: str
    allowed: bool = True


class AgentOrchestrator:
    """Routes requests without allowing customer messages to reach admin tools."""

    def __init__(self, customer_agent: Agent, audit: AuditLog, management_agent: Any | None = None):
        self.audit = audit
        self.customer_agent = self._select_backend("customer", customer_agent)
        self.management_agent = (
            self._select_backend("management", management_agent)
            if management_agent is not None else None
        )
        self.agents: dict[str, Agent] = {"customer": self.customer_agent}
        if self.management_agent is not None:
            self.agents["management"] = self.management_agent

    @staticmethod
    def _select_backend(name: str, local_agent: Any) -> Agent:
        settings = provider_from_env(name)
        if settings.mode == "external_api":
            return ExternalAPIProvider(settings)
        return local_agent

    def register(self, name: str, agent: Agent) -> None:
        if name in {"", "customer", "management"} or name.startswith("_"):
            raise ValueError("Invalid or reserved agent name")
        self.agents[name] = agent

    def decide(self, message: IncomingMessage, actor_role: str = "customer") -> RouteDecision:
        role = (actor_role or "customer").casefold()
        if role in {"manager", "admin", "owner", "operations"}:
            if "management" in self.agents:
                return RouteDecision("management", "trusted management role")
            return RouteDecision("customer", "management agent is not configured")
        if role != "customer":
            return RouteDecision("customer", "unknown roles are restricted to customer scope")
        # A customer may mention reports or sales, but that must never grant admin access.
        return RouteDecision("customer", "external customer channel")

    def dispatch(self, message: IncomingMessage, actor_role: str = "customer") -> str:
        decision = self.decide(message, actor_role)
        agent = self.agents.get(decision.agent)
        if agent is None or not decision.allowed:
            raise RuntimeError("No permitted agent is configured for this request")
        self.audit.record(AuditEvent(
            event_type="agent_route", actor="orchestrator", phone=message.phone,
            details={"agent": decision.agent, "reason": decision.reason, "actor_role": actor_role,
                     "provider": provider_from_env(decision.agent).mode},
        ))
        if decision.agent == "management" and hasattr(agent, "answer"):
            return agent.answer(message.text, use_llm=True)
        return agent.respond(message)

    def respond(self, message: IncomingMessage) -> str:
        """Customer-channel compatibility method used by CustomerMessageRuntime."""
        return self.dispatch(message, actor_role="customer")
