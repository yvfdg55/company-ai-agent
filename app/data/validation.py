"""Validation rules for company product data."""
from __future__ import annotations

from typing import Any, Iterable


REQUIRED_PRODUCT_COLUMNS = {"Product Name", "Price"}
OPTIONAL_PRODUCT_COLUMNS = {"Stock", "Category", "Updated", "Description"}


def validate_product_records(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(records)
    if not rows:
        return {"ok": False, "errors": ["No product records were found."], "count": 0}
    columns = set().union(*(row.keys() for row in rows))
    errors: list[str] = []
    missing = REQUIRED_PRODUCT_COLUMNS - columns
    if missing:
        errors.append("Missing required columns: " + ", ".join(sorted(missing)))
    invalid_prices = []
    for index, row in enumerate(rows, start=2):
        name = str(row.get("Product Name", "") or "").strip()
        if not name:
            errors.append(f"Row {index}: Product Name is empty")
        try:
            price = float(str(row.get("Price", "")).replace(",", ""))
            if price < 0:
                invalid_prices.append(index)
        except (TypeError, ValueError):
            invalid_prices.append(index)
    if invalid_prices:
        errors.append("Invalid or negative Price at rows: " + ", ".join(map(str, invalid_prices)))
    return {"ok": not errors, "errors": errors, "count": len(rows), "columns": sorted(columns), "optional_columns": sorted(columns & OPTIONAL_PRODUCT_COLUMNS)}
