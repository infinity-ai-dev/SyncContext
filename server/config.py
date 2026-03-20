from typing import ClassVar, Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from core.db import unique_urls


class Settings(BaseSettings):
    DEFAULT_PROJECT_TOKEN: ClassVar[str] = "default-dev-token"

    model_config = SettingsConfigDict(
        env_prefix="SYNCCONTEXT_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Auth
    project_token: str = DEFAULT_PROJECT_TOKEN
    project_name: str = "Default Project"
    admin_token: str | None = None

    # PostgreSQL (always required for metadata)
    database_url: str = "postgresql://synccontext:password@localhost:5432/synccontext"
    local_database_url: str | None = "postgresql://postgres:7y8auHScpUTrQWhjbrlu8yc0RzNib2wn@postgres:5432/synccontext"
    direct_url: str | None = None

    # Vector store selection
    vector_store: Literal["pgvector", "redis"] = "pgvector"
    redis_url: str = "redis://localhost:6379/0"

    # Embedding provider selection (auto-detected if not set explicitly)
    embedding_provider: Literal["gemini", "openai", "ollama", "auto"] = "auto"
    embedding_dimension: int = 768

    # Provider API keys
    gemini_api_key: str | None = None
    openai_api_key: str | None = None

    # Ollama
    ollama_base_url: str | None = None
    ollama_model: str = "nomic-embed-text"

    # Server
    transport: Literal["stdio", "sse", "streamable-http"] = "stdio"
    host: str = "0.0.0.0"
    port: int = 8080
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    def resolve_embedding_provider(self) -> str:
        """Resolve the embedding provider, auto-detecting from available credentials."""
        if self.embedding_provider != "auto":
            return self.embedding_provider

        # Priority: ollama (if URL set) > openai (if key set) > gemini (if key set)
        if self.ollama_base_url:
            return "ollama"
        if self.openai_api_key:
            return "openai"
        if self.gemini_api_key:
            return "gemini"

        raise ValueError(
            "No embedding provider credentials detected. "
            "Set SYNCCONTEXT_OLLAMA_BASE_URL, SYNCCONTEXT_OPENAI_API_KEY, "
            "or SYNCCONTEXT_GEMINI_API_KEY."
        )

    def has_shared_project_token(self) -> bool:
        """Return True when a non-default shared project token is configured."""
        return self.project_token != self.DEFAULT_PROJECT_TOKEN

    def database_candidates(self) -> list[str]:
        """Return database DSNs in fallback order."""
        return unique_urls([self.local_database_url, self.database_url])

    def resolve_migration_url(self, runtime_database_url: str | None = None) -> str:
        """Prefer a direct connection for migrations when runtime uses a pooler."""
        if runtime_database_url and runtime_database_url == self.local_database_url:
            return runtime_database_url
        return self.direct_url or runtime_database_url or self.database_url
