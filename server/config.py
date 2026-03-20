from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SYNCCONTEXT_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Auth
    project_token: str = "default-dev-token"
    admin_token: str | None = None

    # PostgreSQL (always required for metadata)
    database_url: str = "postgresql://synccontext:password@localhost:5432/synccontext"

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

        return "gemini"  # fallback
