"""WhatsApp Cloud API adapter for the new agent runtime."""
from __future__ import annotations

import hashlib
import hmac
from typing import Any

import requests

from ..models import IncomingMessage


class WhatsAppChannel:
    def __init__(self, token: str, phone_number_id: str, app_secret: str, api_version: str = "v20.0"):
        self.token = token
        self.phone_number_id = phone_number_id
        self.app_secret = app_secret
        self.api_version = api_version

    def verify_signature(self, raw_body: bytes, signature: str) -> bool:
        if not self.app_secret or not signature.startswith("sha256="):
            return False
        expected = "sha256=" + hmac.new(self.app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def parse_messages(self, body: dict[str, Any]) -> list[IncomingMessage]:
        messages: list[IncomingMessage] = []
        if body.get("object") != "whatsapp_business_account":
            return messages
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                metadata = value.get("metadata", {}) or {}
                if self.phone_number_id and metadata.get("phone_number_id") != self.phone_number_id:
                    continue
                for message in value.get("messages", []):
                    if message.get("type") != "text":
                        continue
                    text = str(message.get("text", {}).get("body", "")).strip()
                    phone = str(message.get("from", "")).strip()
                    message_id = str(message.get("id", "")).strip()
                    if message_id and phone and text:
                        messages.append(IncomingMessage(message_id, phone, text))
        return messages

    def send_text(self, phone: str, text: str) -> dict[str, Any]:
        if not self.token or not self.phone_number_id:
            raise RuntimeError("WhatsApp credentials are missing")
        url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"
        response = requests.post(url, headers={"Authorization": f"Bearer {self.token}"}, json={
            "messaging_product": "whatsapp", "recipient_type": "individual", "to": phone,
            "type": "text", "text": {"preview_url": False, "body": str(text)[:4000]},
        }, timeout=30)
        response.raise_for_status()
        return response.json()
