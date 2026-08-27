def test_llm_service_runtime_status(monkeypatch):

    monkeypatch.setenv(
        "GROQ_API_KEY_1",
        "test-groq-key",
    )

    monkeypatch.setenv(
        "MODEL_NAME",
        "test-model",
    )

    from app.services.llm_service import LLMService

    service = LLMService()

    status = service.get_runtime_status()

    assert status["operational"] is True
    assert status["provider_count"] >= 1
    assert status["coach_enabled"] is True
    assert status["provider_abstraction"] is True


def test_llm_service_provider_is_configured(monkeypatch):

    monkeypatch.setenv(
        "GROQ_API_KEY_1",
        "test-groq-key",
    )

    from app.services.llm_service import LLMService

    service = LLMService()

    client, model, provider = service._next_client()

    assert client is not None
    assert model
    assert provider == "Groq"