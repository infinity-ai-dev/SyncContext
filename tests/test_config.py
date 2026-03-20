import pytest

from server.config import Settings


def test_default_settings():
    settings = Settings(project_token="test-token")
    assert settings.vector_store == "pgvector"
    assert settings.embedding_provider == "auto"
    assert settings.embedding_dimension == 768
    assert settings.transport == "stdio"
    assert settings.project_name == "Default Project"
    assert settings.local_database_url is not None
    assert settings.direct_url is None
    assert settings.log_level == "INFO"
    assert settings.admin_token is None
    assert settings.ollama_base_url is None
    assert settings.has_shared_project_token() is True


def test_default_project_token_does_not_enable_shared_mode():
    settings = Settings(project_token=Settings.DEFAULT_PROJECT_TOKEN)
    assert settings.has_shared_project_token() is False


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("SYNCCONTEXT_PROJECT_TOKEN", "env-token")
    monkeypatch.setenv("SYNCCONTEXT_PROJECT_NAME", "Env Project")
    monkeypatch.setenv("SYNCCONTEXT_VECTOR_STORE", "redis")
    monkeypatch.setenv("SYNCCONTEXT_EMBEDDING_PROVIDER", "ollama")
    monkeypatch.setenv("SYNCCONTEXT_ADMIN_TOKEN", "admin-secret")
    monkeypatch.setenv("SYNCCONTEXT_DATABASE_URL", "postgresql://remote.example/postgres")
    monkeypatch.setenv("SYNCCONTEXT_DIRECT_URL", "postgresql://direct.example/postgres")

    settings = Settings()
    assert settings.project_token == "env-token"
    assert settings.project_name == "Env Project"
    assert settings.database_url == "postgresql://remote.example/postgres"
    assert settings.direct_url == "postgresql://direct.example/postgres"
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


def test_resolve_provider_without_credentials_raises():
    settings = Settings(project_token="t")
    with pytest.raises(ValueError, match="No embedding provider credentials detected"):
        settings.resolve_embedding_provider()


def test_database_candidates_prioritize_local_then_primary():
    settings = Settings(
        project_token="t",
        local_database_url="postgresql://local",
        database_url="postgresql://remote",
    )
    assert settings.database_candidates() == ["postgresql://local", "postgresql://remote"]


def test_resolve_migration_url_prefers_runtime_local():
    settings = Settings(
        project_token="t",
        local_database_url="postgresql://local",
        database_url="postgresql://remote",
        direct_url="postgresql://direct",
    )
    assert settings.resolve_migration_url("postgresql://local") == "postgresql://local"


def test_resolve_migration_url_prefers_direct_for_remote_runtime():
    settings = Settings(
        project_token="t",
        local_database_url="postgresql://local",
        database_url="postgresql://remote",
        direct_url="postgresql://direct",
    )
    assert settings.resolve_migration_url("postgresql://remote") == "postgresql://direct"
