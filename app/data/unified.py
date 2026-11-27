"""Unified records for structured, semi-structured, and document data."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class UnifiedRecord:
    id: str
    source: str
    data_type: str
    title: str
    content: str
    structured_data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    permissions: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def searchable_text(self) -> str:
        return " ".join([self.title, self.content, str(self.structured_data), str(self.metadata)]).casefold()
