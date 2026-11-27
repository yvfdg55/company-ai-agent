"""Company data access for products and services."""
from __future__ import annotations
from pathlib import Path
from typing import Any
from .validation import validate_product_records
from ..search import rank_records
class CompanyDataStore:
    def __init__(self, records: list[dict[str, Any]] | None = None, excel_file: str = "company.xlsx"):
        self.excel_file = excel_file; self.records = list(records or [])
    def load_excel(self, path: str | None = None) -> int:
        target = Path(path or self.excel_file)
        if not target.exists(): raise FileNotFoundError(f"Company data file not found: {target}")
        try: from openpyxl import load_workbook
        except ImportError as exc: raise RuntimeError("openpyxl is required to load Excel company data") from exc
        workbook = load_workbook(target, read_only=True, data_only=True); sheet = workbook.active; rows = list(sheet.iter_rows(values_only=True)); workbook.close()
        if not rows: self.records = []; return 0
        headers = [str(value or "").strip() for value in rows[0]]; loaded = []
        for row in rows[1:]:
            record = {header: row[i] if i < len(row) else None for i, header in enumerate(headers) if header}
            if any(value not in (None, "") for value in record.values()): loaded.append(record)
        self.records = loaded; return len(loaded)
    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        return rank_records(self.records, query, limit)
    def all(self) -> list[dict[str, Any]]: return list(self.records)
    def validate(self) -> dict[str, Any]: return validate_product_records(self.records)
