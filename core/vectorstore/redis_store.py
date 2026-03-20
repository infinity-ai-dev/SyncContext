import json
from uuid import UUID

import numpy as np
import redis.asyncio as redis
from redis.commands.search.field import TagField, VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query

from core.vectorstore.base import VectorStore

INDEX_NAME = "synccontext_vectors"
PREFIX = "memory:"


class RedisVectorStore(VectorStore):
    """Redis Stack backend with RediSearch vector similarity."""

    def __init__(self, redis_url: str, dimension: int = 768):
        self._redis_url = redis_url
        self._dimension = dimension
        self._client: redis.Redis | None = None

    async def initialize(self) -> None:
        self._client = redis.from_url(self._redis_url, decode_responses=False)

        # Check if RediSearch module is available
        try:
            modules = await self._client.module_list()
            module_names = [m[b"name"].decode() if isinstance(m[b"name"], bytes) else m[b"name"] for m in modules]
            if "search" not in module_names:
                raise RuntimeError(
                    "Redis Stack with RediSearch module is required. Use the redis/redis-stack Docker image."
                )
        except redis.ResponseError:
            pass  # Some Redis versions don't support MODULE LIST

        # Create vector index if it doesn't exist
        try:
            await self._client.ft(INDEX_NAME).info()
        except redis.ResponseError:
            schema = (
                TagField("project_token"),
                TagField("memory_id"),
                VectorField(
                    "embedding",
                    "HNSW",
                    {
                        "TYPE": "FLOAT32",
                        "DIM": self._dimension,
                        "DISTANCE_METRIC": "COSINE",
                        "M": 16,
                        "EF_CONSTRUCTION": 64,
                    },
                ),
            )
            definition = IndexDefinition(prefix=[PREFIX], index_type=IndexType.HASH)
            await self._client.ft(INDEX_NAME).create_index(schema, definition=definition)

    async def upsert(self, id: UUID, vector: list[float], metadata: dict) -> None:
        key = f"{PREFIX}{id}"
        embedding_bytes = np.array(vector, dtype=np.float32).tobytes()

        mapping = {
            "embedding": embedding_bytes,
            "project_token": metadata.get("project_token", ""),
            "memory_id": str(id),
            "metadata": json.dumps(metadata),
        }
        await self._client.hset(key, mapping=mapping)

    async def search(
        self,
        query_vector: list[float],
        top_k: int = 10,
        filter_metadata: dict | None = None,
    ) -> list[dict]:
        query_bytes = np.array(query_vector, dtype=np.float32).tobytes()
        project_token = (filter_metadata or {}).get("project_token", "")

        filter_expr = f"@project_token:{{{project_token}}}" if project_token else "*"
        q = (
            Query(f"({filter_expr})=>[KNN {top_k} @embedding $vec AS score]")
            .sort_by("score")
            .return_fields("memory_id", "score", "metadata")
            .dialect(2)
        )

        results = await self._client.ft(INDEX_NAME).search(q, query_params={"vec": query_bytes})

        output = []
        for doc in results.docs:
            score_raw = float(doc.score) if hasattr(doc, "score") else 0.0
            similarity = 1.0 - score_raw  # Convert cosine distance to similarity
            meta_str = doc.metadata if hasattr(doc, "metadata") else "{}"
            if isinstance(meta_str, bytes):
                meta_str = meta_str.decode()

            output.append(
                {
                    "id": UUID(doc.memory_id.decode() if isinstance(doc.memory_id, bytes) else doc.memory_id),
                    "score": similarity,
                    "metadata": json.loads(meta_str),
                }
            )
        return output

    async def delete(self, id: UUID) -> bool:
        key = f"{PREFIX}{id}"
        result = await self._client.delete(key)
        return result > 0

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
