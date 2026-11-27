"""Read-only product tools."""
from __future__ import annotations

from typing import Any, Iterable

from ..models import ToolResult
from ..policies import require_non_empty, validate_quantity


def _name(row: dict[str, Any]) -> str:
    return str(row.get("Product Name", row.get("product_name", ""))).strip()


def search_products(records: Iterable[dict[str, Any]], query: str) -> ToolResult:
    q = require_non_empty(query, "query").casefold()
    rows = list(records)
    matches = [row for row in rows if q in str(row).casefold()]
    if not matches:
        tokens = [token for token in q.split() if len(token) > 2]
        matches = [row for row in rows if any(token in str(row).casefold() for token in tokens)]
    if not matches and any(word in q for word in ["منتج", "products", "product", "متاح", "available"]):
        matches = rows
    return ToolResult(ok=True, data={"products": matches[:20], "count": len(matches)})


def calculate_product(records: Iterable[dict[str, Any]], product_name: str, quantity: Any) -> ToolResult:
    target = require_non_empty(product_name, "product_name").casefold()
    try:
        qty = validate_quantity(quantity)
    except ValueError as exc:
        return ToolResult(ok=False, error=str(exc))
    matches = [row for row in records if _name(row).casefold() == target]
    if not matches:
        return ToolResult(ok=False, error="Product not found with an approved price.")
    if len(matches) > 1:
        return ToolResult(ok=False, error="Ambiguous product name.")
    row = matches[0]
    try:
        price = float(str(row.get("Price", row.get("price", ""))).replace(",", ""))
    except (TypeError, ValueError):
        return ToolResult(ok=False, error="Product has no valid approved price.")
    if price < 0:
        return ToolResult(ok=False, error="Product price cannot be negative.")
    return ToolResult(ok=True, data={"product": _name(row), "unit_price": price, "quantity": qty, "total": round(price * qty, 2)})
