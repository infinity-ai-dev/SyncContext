from core.embeddings.base import EmbeddingProvider


def create_embedding_provider(provider: str, **kwargs) -> EmbeddingProvider:
    """Factory function to create the appropriate embedding provider."""
    match provider:
        case "gemini":
            from core.embeddings.gemini import GeminiEmbeddingProvider

            return GeminiEmbeddingProvider(api_key=kwargs.get("api_key", ""))
        case "openai":
            from core.embeddings.openai import OpenAIEmbeddingProvider

            return OpenAIEmbeddingProvider(api_key=kwargs.get("api_key", ""))
        case "ollama":
            from core.embeddings.ollama import OllamaEmbeddingProvider

            return OllamaEmbeddingProvider(
                base_url=kwargs.get("base_url", "http://localhost:11434"),
                model=kwargs.get("model", "nomic-embed-text"),
            )
        case _:
            raise ValueError(f"Unknown embedding provider: {provider}")


__all__ = ["EmbeddingProvider", "create_embedding_provider"]
