"""Shared configuration for the company agent platform."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database: str = os.getenv("DATABASE", "company_agent.db")
    ollama_url: str = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen3:8b")
    max_history: int = int(os.getenv("MAX_HISTORY", "12"))
    max_daily_messages: int = int(os.getenv("MAX_DAILY_MESSAGES_PER_CUSTOMER", "100"))
    max_tool_steps: int = int(os.getenv("MAX_TOOL_STEPS", "5"))
    company_data_file: str = os.getenv("EXCEL_FILE", "company.xlsx")
    whatsapp_phone_number_id: str = os.getenv("PHONE_NUMBER_ID", "")
    customer_agent_provider: str = os.getenv("CUSTOMER_AGENT_PROVIDER", "local")
    management_agent_provider: str = os.getenv("MANAGEMENT_AGENT_PROVIDER", "local")
    management_auth_token: str = os.getenv("MANAGEMENT_AUTH_TOKEN", "")

    def validate(self) -> None:
        if self.max_history < 1 or self.max_history > 100:
            raise ValueError("MAX_HISTORY must be between 1 and 100")
        if self.max_daily_messages < 1:
            raise ValueError("MAX_DAILY_MESSAGES_PER_CUSTOMER must be positive")
        if self.max_tool_steps < 1 or self.max_tool_steps > 20:
            raise ValueError("MAX_TOOL_STEPS must be between 1 and 20")
        for name, provider in {
            "CUSTOMER_AGENT_PROVIDER": self.customer_agent_provider,
            "MANAGEMENT_AGENT_PROVIDER": self.management_agent_provider,
        }.items():
            if provider not in {"local", "external_api"}:
                raise ValueError(f"{name} must be local or external_api")
