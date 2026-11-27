"""Customer actions that remain reviewable and auditable."""
from __future__ import annotations

from typing import Any

from ..models import ToolResult
from ..policies import approval_required, require_non_empty


def create_support_ticket(phone: str, subject: str, details: str) -> ToolResult:
    phone = require_non_empty(phone, "phone")
    subject = require_non_empty(subject, "subject")
    details = require_non_empty(details, "details")
    if len(subject) > 200 or len(details) > 3000:
        return ToolResult(ok=False, error="Ticket input is too long.")
    return ToolResult(ok=True, approval_required=True, data={"phone": phone, "subject": subject, "details": details, "status": "open"})


def save_order_draft(phone: str, details: str) -> ToolResult:
    phone = require_non_empty(phone, "phone")
    details = require_non_empty(details, "details")
    if len(details) > 3000:
        return ToolResult(ok=False, error="Order details are too long.")
    return ToolResult(ok=True, approval_required=True, data={"phone": phone, "details": details, "status": "pending_review"})
