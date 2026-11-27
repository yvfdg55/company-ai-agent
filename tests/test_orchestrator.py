import sqlite3

from app.agents.customer_agent import CustomerAgent
from app.audit import AuditLog
from app.models import IncomingMessage
from app.orchestrator import AgentOrchestrator


class FakeManagement:
    def __init__(self):
        self.questions = []

    def answer(self, question, use_llm=True):
        self.questions.append(question)
        return "management answer"


def test_orchestrator_routes_customer_to_customer_agent(tmp_path):
    db = str(tmp_path / "agent.db")
    audit = AuditLog(db)
    customer = CustomerAgent([{"Product Name": "A", "Price": 10}], audit)
    management = FakeManagement()
    orchestrator = AgentOrchestrator(customer, audit, management)
    answer = orchestrator.dispatch(IncomingMessage("m1", "201", "ما المنتجات المتاحة؟"), actor_role="customer")
    assert "A" in answer
    assert management.questions == []


def test_orchestrator_allows_management_only_for_trusted_role(tmp_path):
    db = str(tmp_path / "agent.db")
    audit = AuditLog(db)
    customer = CustomerAgent([], audit)
    management = FakeManagement()
    orchestrator = AgentOrchestrator(customer, audit, management)
    answer = orchestrator.dispatch(IncomingMessage("m2", "manager", "أعطني التقرير"), actor_role="manager")
    assert answer == "management answer"
    assert management.questions == ["أعطني التقرير"]
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM audit_events WHERE event_type='agent_route'").fetchone()[0] == 1
