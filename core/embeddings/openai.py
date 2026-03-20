import httpx

from core.embeddings.base import EmbeddingProvider

OPENAI_EMBED_URL = "https://api.openai.com/v1/embeddings"


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI text-embedding-3-small provider (1536 dimensions)."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        if not api_key:
            raise ValueError("SYNCCONTEXT_OPENAI_API_KEY is required when using OpenAI embedding provider")
        self._api_key = api_key
        self._model = model
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    @property
    def dimension(self) -> int:
        return 1536

    async def embed(self, text: str) -> list[float]:
        response = await self._client.post(
            OPENAI_EMBED_URL,
            json={"input": text, "model": self._model},
        )
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        response = await self._client.post(
            OPENAI_EMBED_URL,
            json={"input": texts, "model": self._model},
        )
        response.raise_for_status()
        data = response.json()["data"]
        data.sort(key=lambda x: x["index"])
        return [item["embedding"] for item in data]

    async def close(self) -> None:
        await self._client.aclose()
