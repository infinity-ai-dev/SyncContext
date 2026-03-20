from server.config import Settings


def test_default_settings():
    settings = Settings(project_token="test-token")
    assert settings.vector_store == "pgvector"
    assert settings.embedding_provider == "auto"
    assert settings.embedding_dimension == 768
    assert settings.transport == "stdio"
    assert settings.log_level == "INFO"
    assert settings.admin_token is None
    assert settings.ollama_base_url is None


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("SYNCCONTEXT_PROJECT_TOKEN", "env-token")
    monkeypatch.setenv("SYNCCONTEXT_VECTOR_STORE", "redis")
    monkeypatch.setenv("SYNCCONTEXT_EMBEDDING_PROVIDER", "ollama")
    monkeypatch.setenv("SYNCCONTEXT_ADMIN_TOKEN", "admin-secret")

    settings = Settings()
    assert settings.project_token == "env-token"
    assert settings.vector_store == "redis"
    assert settings.embedding_provider == "ollama"
    assert settings.admin_token == "admin-secret"


def test_resolve_provider_auto_gemini():
    settings = Settings(project_token="t", gemini_api_key="gk")
    assert settings.resolve_embedding_provider() == "gemini"


def test_resolve_provider_auto_openai():
    settings = Settings(project_token="t", openai_api_key="ok")
    assert settings.resolve_embedding_provider() == "openai"


def test_resolve_provider_auto_ollama():
    settings = Settings(project_token="t", ollama_base_url="http://localhost:11434")
    assert settings.resolve_embedding_provider() == "ollama"


def test_resolve_provider_ollama_takes_priority():
    settings = Settings(
        project_token="t",
        gemini_api_key="gk",
        ollama_base_url="http://localhost:11434",
    )
    assert settings.resolve_embedding_provider() == "ollama"


def test_resolve_provider_explicit_overrides_auto():
    settings = Settings(
        project_token="t",
        embedding_provider="openai",
        gemini_api_key="gk",
        ollama_base_url="http://localhost:11434",
    )
    assert settings.resolve_embedding_provider() == "openai"


def test_resolve_provider_fallback_gemini():
    settings = Settings(project_token="t")
    assert settings.resolve_embedding_provider() == "gemini"
