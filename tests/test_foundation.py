import sqlite3

from app.agents.customer_agent import CustomerAgent
from app.audit import AuditLog
from app.models import IncomingMessage
from app.tools.products import calculate_product


def test_price_tool_rejects_invalid_quantity():
    result = calculate_product([{"Product Name": "A", "Price": 10}], "A", 0)
    assert not result.ok


def test_customer_agent_creates_reviewable_order(tmp_path):
    database = str(tmp_path / "agent.db")
    agent = CustomerAgent([{"Product Name": "A", "Price": 10}], AuditLog(database))
    answer = agent.respond(IncomingMessage("m1", "201", "أريد طلب المنتج A"))
    assert "مسودة" in answer
    with sqlite3.connect(database) as db:
        row = db.execute("SELECT event_type FROM audit_events").fetchone()
    assert row[0] == "tool_call"


def test_customer_agent_searches_company_products(tmp_path):
    agent = CustomerAgent([{"Product Name": "A", "Price": 10}], AuditLog(str(tmp_path / "agent.db")))
    answer = agent.respond(IncomingMessage("m2", "201", "ما المنتجات المتاحة؟"))
    assert "A" in answer
