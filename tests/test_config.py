from server.config import Settings


def test_default_settings():
    settings = Settings(project_token="test-token")
    assert settings.vector_store == "pgvector"
    assert settings.embedding_provider == "gemini"
    assert settings.embedding_dimension == 768
    assert settings.transport == "stdio"
    assert settings.log_level == "INFO"
    assert settings.admin_token is None


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
