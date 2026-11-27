"""Local smoke test: no real WhatsApp or Ollama calls are made."""
from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.customer_agent import CustomerAgent
from app.audit import AuditLog
from app.channels.whatsapp import WhatsAppChannel
from app.orchestrator import AgentOrchestrator
from app.runtime import CustomerMessageRuntime
from app.server import create_app


class FakeChannel(WhatsAppChannel):
    def __init__(self):
        super().__init__("token", "phone-id", "secret")
        self.sent: list[tuple[str, str]] = []

    def send_text(self, phone: str, text: str) -> dict:
        self.sent.append((phone, text))
        return {"ok": True}


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        database = str(Path(directory) / "smoke.db")
        channel = FakeChannel()
        audit = AuditLog(database)
        agent = CustomerAgent([{"Product Name": "Product A", "Price": 120}], audit)
        orchestrator = AgentOrchestrator(agent, audit)
        runtime = CustomerMessageRuntime(orchestrator, channel, database, audit)
        client = create_app(runtime, "verify-me").test_client()

        assert client.get("/health").status_code == 200
        assert client.get("/webhook?hub.mode=subscribe&hub.verify_token=verify-me&hub.challenge=ok").data == b"ok"

        body = {"object": "whatsapp_business_account", "entry": [{"changes": [{"value": {
            "metadata": {"phone_number_id": "phone-id"},
            "messages": [{"id": "smoke-1", "from": "201", "type": "text", "text": {"body": "ما المنتجات المتاحة؟"}}],
        }}]}]}
        raw = json.dumps(body, ensure_ascii=False).encode()
        signature = "sha256=" + hmac.new(b"secret", raw, hashlib.sha256).hexdigest()
        response = client.post("/webhook", data=raw, content_type="application/json", headers={"X-Hub-Signature-256": signature})
        assert response.status_code == 200 and response.json["handled"] == 1
        duplicate = client.post("/webhook", data=raw, content_type="application/json", headers={"X-Hub-Signature-256": signature})
        assert duplicate.json["duplicates"] == 1
        assert len(channel.sent) == 1

        with sqlite3.connect(database) as db:
            assert db.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0] >= 1
    print("LOCAL SMOKE TEST: PASS")


if __name__ == "__main__":
    main()
