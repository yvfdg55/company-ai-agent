"""Runtime bridge between channels and agents."""
from __future__ import annotations

import sqlite3

from .audit import AuditLog
from .channels.whatsapp import WhatsAppChannel
from .models import IncomingMessage


class CustomerMessageRuntime:
    def __init__(self, agent: object, channel: WhatsAppChannel, database: str, audit: AuditLog):
        """Bridge a customer channel to any object exposing ``respond(message)``.

        This permits the central orchestrator to sit between WhatsApp and the
        customer agent while retaining compatibility with the original agent.
        """
        self.agent = agent
        self.channel = channel
        self.database = database
        self.audit = audit
        self._initialize()

    def _initialize(self) -> None:
        with sqlite3.connect(self.database) as db:
            db.execute("CREATE TABLE IF NOT EXISTS processed_messages (message_id TEXT PRIMARY KEY, status TEXT NOT NULL)")
            db.commit()

    def handle(self, message: IncomingMessage) -> str | None:
        with sqlite3.connect(self.database) as db:
            inserted = db.execute("INSERT OR IGNORE INTO processed_messages (message_id, status) VALUES (?, ?)", (message.message_id, "processing")).rowcount
            if inserted != 1:
                return None
        try:
            answer = self.agent.respond(message)
            self.channel.send_text(message.phone, answer)
            status = "completed"
            return answer
        except Exception:
            status = "failed"
            raise
        finally:
            with sqlite3.connect(self.database) as db:
                db.execute("UPDATE processed_messages SET status=? WHERE message_id=?", (status, message.message_id))
                db.commit()
