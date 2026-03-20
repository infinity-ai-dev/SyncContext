import httpx

from core.embeddings.base import EmbeddingProvider

GEMINI_EMBED_URL = "https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent"
GEMINI_BATCH_URL = "https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:batchEmbedContents"


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Gemini text-embedding-004 provider (free tier, 768 dimensions)."""

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("SYNCCONTEXT_GEMINI_API_KEY is required when using Gemini embedding provider")
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=30.0)

    @property
    def dimension(self) -> int:
        return 768

    async def embed(self, text: str) -> list[float]:
        response = await self._client.post(
            GEMINI_EMBED_URL,
            params={"key": self._api_key},
            json={
                "model": "models/text-embedding-004",
                "content": {"parts": [{"text": text}]},
            },
        )
        response.raise_for_status()
        return response.json()["embedding"]["values"]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        requests = [
            {
                "model": "models/text-embedding-004",
                "content": {"parts": [{"text": text}]},
            }
            for text in texts
        ]
        response = await self._client.post(
            GEMINI_BATCH_URL,
            params={"key": self._api_key},
            json={"requests": requests},
        )
        response.raise_for_status()
        return [item["embedding"]["values"] for item in response.json()["embeddings"]]

    async def close(self) -> None:
        await self._client.aclose()
