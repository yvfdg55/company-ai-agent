"""Execution backends for local and external company agents.

External mode uses an OpenAI-compatible chat-completions endpoint. The API key
is read from the environment and is never written to audit events.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests

from ..models import IncomingMessage


@dataclass(frozen=True)
class ProviderSettings:
    name: str
    mode: str = "local"
    endpoint: str = ""
    api_key_env: str = ""
    model: str = ""
    timeout: int = 60
    system_prompt: str = "أجب اعتمادًا على بيانات الشركة الموثقة فقط."

    def validate(self) -> None:
        if self.mode not in {"local", "external_api"}:
            raise ValueError(f"Unsupported provider mode: {self.mode}")
        if self.mode == "external_api" and not self.endpoint:
            raise ValueError(f"External endpoint is required for agent: {self.name}")
        if self.timeout < 1 or self.timeout > 300:
            raise ValueError("Provider timeout must be between 1 and 300 seconds")


class ExternalAPIProvider:
    """Adapter for a company's selected OpenAI-compatible external endpoint."""

    def __init__(self, settings: ProviderSettings, session: Any = requests):
        settings.validate()
        self.settings = settings
        self.session = session

    def _api_key(self) -> str:
        if not self.settings.api_key_env:
            return ""
        return os.getenv(self.settings.api_key_env, "")

    def _answer(self, text: str) -> str:
        headers = {"Content-Type": "application/json"}
        api_key = self._api_key()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        payload = {
            "model": self.settings.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": self.settings.system_prompt},
                {"role": "user", "content": text},
            ],
        }
        response = self.session.post(
            self.settings.endpoint,
            json=payload,
            headers=headers,
            timeout=self.settings.timeout,
        )
        response.raise_for_status()
        data = response.json()
        answer = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not answer or not answer.strip():
            raise RuntimeError(f"External provider returned an empty answer for {self.settings.name}")
        return answer.strip()

    def respond(self, message: IncomingMessage) -> str:
        return self._answer(message.text)

    def answer(self, question: str, use_llm: bool = True) -> str:
        return self._answer(question)


def provider_from_env(agent_name: str, default_mode: str = "local") -> ProviderSettings:
    """Read one agent's backend selection without reading or exposing secrets."""
    prefix = agent_name.upper().replace("-", "_")
    return ProviderSettings(
        name=agent_name,
        mode=os.getenv(f"{prefix}_AGENT_PROVIDER", default_mode),
        endpoint=os.getenv(f"{prefix}_AGENT_API_URL", ""),
        api_key_env=os.getenv(f"{prefix}_AGENT_API_KEY_ENV", ""),
        model=os.getenv(f"{prefix}_AGENT_API_MODEL", ""),
        timeout=int(os.getenv(f"{prefix}_AGENT_API_TIMEOUT", "60")),
        system_prompt=os.getenv(
            f"{prefix}_AGENT_SYSTEM_PROMPT",
            "أجب اعتمادًا على بيانات الشركة الموثقة فقط.",
        ),
    )
