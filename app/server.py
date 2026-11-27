"""Flask application for the new customer-agent runtime."""
from __future__ import annotations

import os
from typing import Any

from flask import Flask, jsonify, request

from .agents.customer_agent import CustomerAgent
from .audit import AuditLog
from .channels.whatsapp import WhatsAppChannel
from .config import Settings
from .runtime import CustomerMessageRuntime


def create_app(runtime: CustomerMessageRuntime, verify_token: str) -> Flask:
    """Create a webhook app around an already configured runtime."""
    app = Flask(__name__)

    @app.get("/health")
    def health() -> Any:
        return jsonify({"status": "ok", "service": "company-customer-agent"})

    @app.get("/webhook")
    def verify_webhook() -> Any:
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if mode == "subscribe" and token == verify_token and challenge:
            return challenge, 200
        return jsonify({"error": "verification_failed"}), 403

    @app.post("/webhook")
    def receive_webhook() -> Any:
        raw_body = request.get_data()
        signature = request.headers.get("X-Hub-Signature-256", "")
        if not runtime.channel.verify_signature(raw_body, signature):
            return jsonify({"error": "unauthorized"}), 401
        body = request.get_json(silent=True) or {}
        messages = runtime.channel.parse_messages(body)
        handled = 0
        duplicates = 0
        for message in messages:
            answer = runtime.handle(message)
            if answer is None:
                duplicates += 1
            else:
                handled += 1
        return jsonify({"status": "EVENT_RECEIVED", "handled": handled, "duplicates": duplicates}), 200

    return app


def create_app_from_environment() -> Flask:
    """Build the real runtime from environment variables."""
    settings = Settings()
    settings.validate()
    token = os.getenv("WHATSAPP_TOKEN", "")
    phone_number_id = os.getenv("PHONE_NUMBER_ID", "")
    app_secret = os.getenv("WHATSAPP_APP_SECRET", "")
    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    api_version = os.getenv("WA_API_VERSION", "v20.0")
    if not all([token, phone_number_id, app_secret, verify_token]):
        raise RuntimeError("WHATSAPP_TOKEN, PHONE_NUMBER_ID, WHATSAPP_APP_SECRET and WHATSAPP_VERIFY_TOKEN are required")
    agent = CustomerAgent.from_settings(settings)
    channel = WhatsAppChannel(token, phone_number_id, app_secret, api_version)
    audit = AuditLog(settings.database)
    runtime = CustomerMessageRuntime(agent, channel, settings.database, audit)
    return create_app(runtime, verify_token)


if __name__ == "__main__":
    application = create_app_from_environment()
    application.run(host=os.getenv("WEBHOOK_HOST", "127.0.0.1"), port=int(os.getenv("WEBHOOK_PORT", "5000")))
