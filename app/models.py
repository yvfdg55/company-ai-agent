"""Shared domain models used by all agents."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


@dataclass(frozen=True)
class IncomingMessage:
    message_id: str
    phone: str
    text: str
    channel: str = "whatsapp"
    language: str | None = None


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    approval_required: bool = False


@dataclass(frozen=True)
class AuditEvent:
    event_type: str
    actor: str
    phone: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


OrderStatus = Literal["draft", "pending_review", "approved", "confirmed", "cancelled", "completed"]
