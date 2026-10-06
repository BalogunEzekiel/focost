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

    for index in range(1, 21):
        monkeypatch.delenv(
            f"GROQ_API_KEY_{index}",
            raising=False,
        )

    monkeypatch.setenv(
        "GROQ_API_KEY_1",
        "test-groq-key",
    )

    from app.services.llm_service import LLMService

    service = LLMService()

    assert service.providers
    assert service.providers[0]["name"] == "Groq"
    assert service.providers[0]["model"]
    assert service.providers[0]["base_url"]
    assert service.providers[0]["keys"] == ["test-groq-key"]