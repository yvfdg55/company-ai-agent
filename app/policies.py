"""Central business and safety policies."""
from __future__ import annotations

from typing import Any


FORBIDDEN_AUTOMATIC_ACTIONS = {
    "confirm_order",
    "take_payment",
    "change_price",
    "change_inventory",
    "send_broadcast",
    "issue_refund",
}


def require_non_empty(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field} is required")
    return text


def validate_quantity(quantity: Any) -> int:
    if isinstance(quantity, bool):
        raise ValueError("quantity must be an integer")
    try:
        value = int(quantity)
    except (TypeError, ValueError) as exc:
        raise ValueError("quantity must be an integer") from exc
    if value < 1 or value > 10000:
        raise ValueError("quantity must be between 1 and 10000")
    return value


def approval_required(action: str) -> bool:
    return action in FORBIDDEN_AUTOMATIC_ACTIONS or action in {"save_order_draft", "create_support_ticket"}
