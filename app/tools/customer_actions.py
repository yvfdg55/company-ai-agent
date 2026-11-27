"""Customer actions that remain reviewable and auditable."""
from __future__ import annotations
from datetime import datetime, timezone
import os, sqlite3
from ..models import ToolResult
from ..policies import require_non_empty
def _database(database): return database or os.getenv("DATABASE", "company_agent.db")
def _now(): return datetime.now(timezone.utc).isoformat()
def initialize_action_tables(database: str) -> None:
    with sqlite3.connect(database) as db:
        db.execute("CREATE TABLE IF NOT EXISTS support_tickets (id INTEGER PRIMARY KEY AUTOINCREMENT, phone TEXT NOT NULL, subject TEXT NOT NULL, details TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS order_drafts (id INTEGER PRIMARY KEY AUTOINCREMENT, phone TEXT NOT NULL, details TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"); db.commit()
def create_support_ticket(phone: str, subject: str, details: str, database: str | None = None) -> ToolResult:
    phone = require_non_empty(phone, "phone"); subject = require_non_empty(subject, "subject"); details = require_non_empty(details, "details")
    if len(subject) > 200 or len(details) > 3000: return ToolResult(ok=False, error="Ticket input is too long.")
    database = _database(database); initialize_action_tables(database); now = _now()
    with sqlite3.connect(database) as db:
        cur = db.execute("INSERT INTO support_tickets (phone, subject, details, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)", (phone, subject, details, "open", now, now)); db.commit(); ident = cur.lastrowid
    return ToolResult(ok=True, approval_required=True, data={"id": ident, "phone": phone, "subject": subject, "details": details, "status": "open", "created_at": now})
def save_order_draft(phone: str, details: str, database: str | None = None) -> ToolResult:
    phone = require_non_empty(phone, "phone"); details = require_non_empty(details, "details")
    if len(details) > 3000: return ToolResult(ok=False, error="Order details are too long.")
    database = _database(database); initialize_action_tables(database); now = _now()
    with sqlite3.connect(database) as db:
        cur = db.execute("INSERT INTO order_drafts (phone, details, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)", (phone, details, "pending_review", now, now)); db.commit(); ident = cur.lastrowid
    return ToolResult(ok=True, approval_required=True, data={"id": ident, "phone": phone, "details": details, "status": "pending_review", "created_at": now})
