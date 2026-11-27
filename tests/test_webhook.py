import hashlib
import hmac
import json
import sqlite3

from app.agents.customer_agent import CustomerAgent
from app.audit import AuditLog
from app.channels.whatsapp import WhatsAppChannel
from app.models import IncomingMessage
from app.runtime import CustomerMessageRuntime
from app.server import create_app


class FakeChannel(WhatsAppChannel):
    def __init__(self):
        super().__init__("token", "phone-id", "secret")
        self.sent = []

    def send_text(self, phone, text):
        self.sent.append((phone, text))
        return {"ok": True}


def test_webhook_verification_signature_and_duplicate(tmp_path):
    database = str(tmp_path / "agent.db")
    channel = FakeChannel()
    audit = AuditLog(database)
    agent = CustomerAgent([{"Product Name": "A", "Price": 10}], audit)
    runtime = CustomerMessageRuntime(agent, channel, database, audit)
    app = create_app(runtime, "verify-me")
    client = app.test_client()

    response = client.get("/webhook?hub.mode=subscribe&hub.verify_token=verify-me&hub.challenge=123")
    assert response.status_code == 200
    assert response.data == b"123"

    body = {"object": "whatsapp_business_account", "entry": [{"changes": [{"value": {"metadata": {"phone_number_id": "phone-id"}, "messages": [{"id": "m1", "from": "201", "type": "text", "text": {"body": "ما المنتجات المتاحة؟"}}]}}]}]}
    raw = json.dumps(body, ensure_ascii=False).encode()
    signature = "sha256=" + hmac.new(b"secret", raw, hashlib.sha256).hexdigest()
    response = client.post("/webhook", data=raw, content_type="application/json", headers={"X-Hub-Signature-256": signature})
    assert response.status_code == 200
    assert response.json["handled"] == 1
    response = client.post("/webhook", data=raw, content_type="application/json", headers={"X-Hub-Signature-256": signature})
    assert response.json["duplicates"] == 1
    assert len(channel.sent) == 1
