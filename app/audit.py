"""SQLite audit trail with conservative redaction of sensitive values."""
from __future__ import annotations
import json, re, sqlite3
from typing import Any
from .models import AuditEvent
_SECRET_KEY = re.compile(r"(secret|token|password|api[_-]?key|authorization|credential)", re.I)
_PAYMENT_KEY = re.compile(r"(card|cvv|cvc|iban|bank|payment|credit|debit)", re.I)
def sanitize(value: Any, key: str = "") -> Any:
    if _SECRET_KEY.search(key) or _PAYMENT_KEY.search(key): return "[REDACTED]"
    if isinstance(value, dict): return {str(k): sanitize(v, str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [sanitize(v, key) for v in value]
    if isinstance(value, str) and len(value) > 500: return value[:500] + "…[truncated]"
    return value
class AuditLog:
    def __init__(self, database: str): self.database = database; self.initialize()
    def initialize(self) -> None:
        with sqlite3.connect(self.database) as db:
            db.execute("CREATE TABLE IF NOT EXISTS audit_events (id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL, actor TEXT NOT NULL, phone TEXT, details TEXT NOT NULL, created_at TEXT NOT NULL)"); db.commit()
    def record(self, event: AuditEvent) -> None:
        with sqlite3.connect(self.database) as db:
            db.execute("INSERT INTO audit_events (event_type, actor, phone, details, created_at) VALUES (?, ?, ?, ?, ?)", (event.event_type, event.actor, event.phone, json.dumps(sanitize(event.details), ensure_ascii=False, default=str), event.created_at)); db.commit()
    def recent(self, limit: int = 100) -> list[dict[str, Any]]:
        with sqlite3.connect(self.database) as db:
            db.row_factory = sqlite3.Row; rows = db.execute("SELECT * FROM audit_events ORDER BY id DESC LIMIT ?", (max(1, min(limit, 1000)),)).fetchall()
        return [dict(row) for row in rows]
