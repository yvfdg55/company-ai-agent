"""Company data access for products and services."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .validation import validate_product_records


class CompanyDataStore:
    def __init__(self, records: list[dict[str, Any]] | None = None, excel_file: str = "company.xlsx"):
        self.excel_file = excel_file
        self.records = list(records or [])

    def load_excel(self, path: str | None = None) -> int:
        target = Path(path or self.excel_file)
        if not target.exists():
            raise FileNotFoundError(f"Company data file not found: {target}")
        try:
            from openpyxl import load_workbook
        except ImportError as exc:
            raise RuntimeError("openpyxl is required to load Excel company data") from exc
        workbook = load_workbook(target, read_only=True, data_only=True)
        sheet = workbook.active
        rows = list(sheet.iter_rows(values_only=True))
        workbook.close()
        if not rows:
            self.records = []
            return 0
        headers = [str(value or "").strip() for value in rows[0]]
        loaded: list[dict[str, Any]] = []
        for row in rows[1:]:
            record = {header: row[i] if i < len(row) else None for i, header in enumerate(headers) if header}
            if any(value not in (None, "") for value in record.values()):
                loaded.append(record)
        self.records = loaded
        return len(loaded)

    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        q = str(query or "").strip().casefold()
        if not q:
            return []
        rows = [row for row in self.records if q in str(row).casefold()]
        if not rows:
            tokens = [token for token in q.split() if len(token) > 2]
            rows = [row for row in self.records if any(token in str(row).casefold() for token in tokens)]
        return rows[:max(1, min(limit, 100))]

    def all(self) -> list[dict[str, Any]]:
        return list(self.records)

    def validate(self) -> dict[str, Any]:
        return validate_product_records(self.records)
