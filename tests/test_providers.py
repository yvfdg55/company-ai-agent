import os

from app.agents.providers import ExternalAPIProvider, ProviderSettings
from app.models import IncomingMessage


class FakeResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return {"choices": [{"message": {"content": "إجابة خارجية"}}]}


class FakeSession:
    def __init__(self):
        self.calls = []

    def post(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return FakeResponse()


def test_external_provider_uses_openai_compatible_api_without_logging_key(monkeypatch):
    monkeypatch.setenv("TEST_AGENT_SECRET", "secret-value")
    session = FakeSession()
    provider = ExternalAPIProvider(
        ProviderSettings(
            name="customer",
            mode="external_api",
            endpoint="https://api.example.test/v1/chat/completions",
            api_key_env="TEST_AGENT_SECRET",
            model="company-model",
        ),
        session=session,
    )
    assert provider.respond(IncomingMessage("m1", "201", "ما السعر؟")) == "إجابة خارجية"
    _, kwargs = session.calls[0]
    assert kwargs["headers"]["Authorization"] == "Bearer secret-value"
    assert kwargs["json"]["model"] == "company-model"
