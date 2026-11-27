"""Unified data ingestion and read-only search layer."""
from __future__ import annotations

from collections import Counter
from typing import Any

from .connectors import load_file, load_mysql, load_sqlite
from .unified import UnifiedRecord
from ..search import rank_records


class DataSourceManager:
    def __init__(self):
        self.records: list[UnifiedRecord] = []

    def add(self, records: list[UnifiedRecord]) -> int:
        existing = {record.id for record in self.records}
        new_records = [record for record in records if record.id not in existing]
        self.records.extend(new_records)
        return len(new_records)

    def ingest_file(self, path: str, data_type: str = "record") -> int:
        return self.add(load_file(path, data_type))

    def ingest_sqlite(self, path: str, tables: list[str] | None = None) -> int:
        return self.add(load_sqlite(path, tables))

    def ingest_mysql(self, config: dict[str, Any], tables: list[str] | None = None) -> int:
        return self.add(load_mysql(config, tables))

    def search(self, query: str, data_type: str | None = None, limit: int = 20) -> list[UnifiedRecord]:
        candidates = [record for record in self.records if data_type is None or record.data_type == data_type]
        return rank_records(candidates, query, limit)

    def summary(self) -> dict[str, Any]:
        return {"total": len(self.records), "by_source": dict(Counter(record.source for record in self.records)), "by_type": dict(Counter(record.data_type for record in self.records))}

    def export_context(self, records: list[UnifiedRecord] | None = None, limit: int = 20) -> list[dict[str, Any]]:
        selected = records if records is not None else self.records
        return [record.to_dict() for record in selected[:limit]]
