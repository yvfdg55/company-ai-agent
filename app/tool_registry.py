"""Central registry that constrains what an agent may call."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .audit import AuditLog
from .models import AuditEvent, ToolResult


class ToolRegistry:
    def __init__(self, audit: AuditLog):
        self.audit = audit
        self._tools: dict[str, Callable[..., ToolResult]] = {}

    def register(self, name: str, function: Callable[..., ToolResult]) -> None:
        if not name or name.startswith("_"):
            raise ValueError("Invalid tool name")
        self._tools[name] = function

    def call(self, name: str, *, actor: str, phone: str | None = None, **kwargs: Any) -> ToolResult:
        if name not in self._tools:
            result = ToolResult(ok=False, error="Tool is not available")
        else:
            try:
                result = self._tools[name](**kwargs)
            except Exception as exc:
                result = ToolResult(ok=False, error=str(exc))
        self.audit.record(AuditEvent(
            event_type="tool_call", actor=actor, phone=phone,
            details={"tool": name, "arguments": kwargs, "ok": result.ok, "error": result.error, "approval_required": result.approval_required},
        ))
        return result
