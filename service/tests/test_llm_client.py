import pytest
from searchlab.rag.llm_client import LlmClient, LlmApiError


def test_missing_api_key_raises():
    with pytest.raises(LlmApiError):
        LlmClient(model="gpt-4o-mini", api_key=None)


def test_missing_api_key_via_env(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from searchlab import config
    assert config.openai_api_key() is None
    with pytest.raises(LlmApiError):
        LlmClient(model="gpt-4o-mini", api_key=config.openai_api_key())


def test_timeout_raises_llm_timeout_error(monkeypatch):
    from openai import APITimeoutError
    from searchlab.rag.llm_client import LlmTimeoutError

    client = LlmClient(model="gpt-4o-mini", api_key="test-key")

    def fake_create(**kwargs):
        raise APITimeoutError(request=None)

    monkeypatch.setattr(client._client.chat.completions, "create", fake_create)

    with pytest.raises(LlmTimeoutError):
        client.complete("sys", "user")


def test_api_error_raises_llm_api_error(monkeypatch):
    import httpx
    from openai import APIStatusError

    client = LlmClient(model="gpt-4o-mini", api_key="test-key")

    def fake_create(**kwargs):
        raise APIStatusError(
            "Rate limit",
            response=httpx.Response(429, request=httpx.Request("POST", "https://api.openai.com")),
            body=None,
        )

    monkeypatch.setattr(client._client.chat.completions, "create", fake_create)

    with pytest.raises(LlmApiError) as exc_info:
        client.complete("sys", "user")
    assert exc_info.value.status_code == 429
