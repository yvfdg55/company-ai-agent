import json
import sqlite3
from app.audit import AuditLog
from app.data.company import CompanyDataStore
from app.models import AuditEvent, IncomingMessage
from app.orchestrator import AgentOrchestrator
from app.agents.customer_agent import CustomerAgent
from app.tools.customer_actions import create_support_ticket, save_order_draft

class FakeManagement:
    def answer(self, question, use_llm=True):
        return "ok"

def test_hybrid_search_normalizes_arabic_and_ranks_exact_match():
    store = CompanyDataStore([
        {"Product Name": "هاتف ذكي", "Description": "جهاز جديد"},
        {"Product Name": "Laptop", "Description": "حاسوب محمول"},
    ])
    assert store.search("الهاتف الذكي")[0]["Product Name"] == "هاتف ذكي"

def test_actions_are_persisted_with_status_and_timestamps(tmp_path):
    database = str(tmp_path / "actions.db")
    ticket = create_support_ticket("201", "مشكلة", "التفاصيل", database)
    draft = save_order_draft("201", "منتج A", database)
    assert ticket.ok and ticket.approval_required and draft.approval_required
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT status, created_at, updated_at FROM support_tickets").fetchone()[0] == "open"
        assert db.execute("SELECT status, created_at, updated_at FROM order_drafts").fetchone()[0] == "pending_review"

def test_audit_redacts_secrets_payment_and_large_values(tmp_path):
    audit = AuditLog(str(tmp_path / "audit.db"))
    audit.record(AuditEvent("test", "tester", details={"api_key": "secret", "card_number": "411111", "note": "x" * 700}))
    details = json.loads(audit.recent()[0]["details"])
    assert details["api_key"] == "[REDACTED]"
    assert details["card_number"] == "[REDACTED]"
    assert details["note"].endswith("…[truncated]")

def test_management_token_blocks_role_only_and_accepts_valid_token(tmp_path, monkeypatch):
    monkeypatch.setenv("MANAGEMENT_AUTH_TOKEN", "test-token")
    audit = AuditLog(str(tmp_path / "auth.db"))
    orchestrator = AgentOrchestrator(CustomerAgent([], audit), audit, FakeManagement())
    message = IncomingMessage("m", "manager", "report")
    try:
        orchestrator.dispatch(message, actor_role="manager")
        assert False, "role alone must not authorize management"
    except RuntimeError as exc:
        assert "permitted" in str(exc)
    assert orchestrator.dispatch(message, actor_role="manager", auth_token="test-token") == "ok"
