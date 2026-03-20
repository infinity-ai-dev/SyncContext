import pytest

from core.embeddings import create_embedding_provider
from core.embeddings.gemini import GeminiEmbeddingProvider
from core.embeddings.ollama import OllamaEmbeddingProvider
from core.embeddings.openai import OpenAIEmbeddingProvider


def test_create_gemini_provider():
    provider = create_embedding_provider("gemini", api_key="test-key")
    assert isinstance(provider, GeminiEmbeddingProvider)
    assert provider.dimension == 768


def test_create_openai_provider():
    provider = create_embedding_provider("openai", api_key="test-key")
    assert isinstance(provider, OpenAIEmbeddingProvider)
    assert provider.dimension == 1536


def test_create_ollama_provider():
    provider = create_embedding_provider("ollama")
    assert isinstance(provider, OllamaEmbeddingProvider)
    assert provider.dimension == 768


def test_create_unknown_provider():
    with pytest.raises(ValueError, match="Unknown embedding provider"):
        create_embedding_provider("unknown")


def test_gemini_requires_api_key():
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        create_embedding_provider("gemini", api_key="")


def test_openai_requires_api_key():
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        create_embedding_provider("openai", api_key="")
