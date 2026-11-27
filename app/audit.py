"""SQLite audit trail for messages, tools, approvals, and agent decisions."""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from .models import AuditEvent


class AuditLog:
    def __init__(self, database: str):
        self.database = database
        self.initialize()

    def initialize(self) -> None:
        with sqlite3.connect(self.database) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                actor TEXT NOT NULL,
                phone TEXT,
                details TEXT NOT NULL,
                created_at TEXT NOT NULL
            )""")
            db.commit()

    def record(self, event: AuditEvent) -> None:
        with sqlite3.connect(self.database) as db:
            db.execute(
                "INSERT INTO audit_events (event_type, actor, phone, details, created_at) VALUES (?, ?, ?, ?, ?)",
                (event.event_type, event.actor, event.phone, json.dumps(event.details, ensure_ascii=False, default=str), event.created_at),
            )
            db.commit()

    def recent(self, limit: int = 100) -> list[dict[str, Any]]:
        with sqlite3.connect(self.database) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("SELECT * FROM audit_events ORDER BY id DESC LIMIT ?", (max(1, min(limit, 1000)),)).fetchall()
        return [dict(row) for row in rows]
