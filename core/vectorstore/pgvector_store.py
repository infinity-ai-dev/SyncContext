import json
from uuid import UUID

import asyncpg
from pgvector.asyncpg import register_vector

from core.vectorstore.base import VectorStore


class PgVectorStore(VectorStore):
    """PostgreSQL + pgvector backend with HNSW indexing."""

    def __init__(self, database_url: str, dimension: int = 768):
        self._database_url = database_url
        self._dimension = dimension
        self._pool: asyncpg.Pool | None = None

    async def initialize(self) -> None:
        self._pool = await asyncpg.create_pool(
            self._database_url,
            min_size=2,
            max_size=10,
            init=self._init_connection,
        )
        async with self._pool.acquire() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS memory_vectors (
                    id UUID PRIMARY KEY,
                    embedding vector({self._dimension}),
                    project_token VARCHAR(255) NOT NULL,
                    metadata JSONB DEFAULT '{{}}'::jsonb
                )
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_vectors_embedding
                ON memory_vectors USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_vectors_project
                ON memory_vectors(project_token)
            """)

    async def _init_connection(self, conn: asyncpg.Connection) -> None:
        await register_vector(conn)

    async def upsert(self, id: UUID, vector: list[float], metadata: dict) -> None:
        project_token = metadata.pop("project_token", "")
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO memory_vectors (id, embedding, project_token, metadata)
                VALUES ($1, $2, $3, $4::jsonb)
                ON CONFLICT (id) DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata
                """,
                id,
                vector,
                project_token,
                json.dumps(metadata),
            )

    async def search(
        self,
        query_vector: list[float],
        top_k: int = 10,
        filter_metadata: dict | None = None,
    ) -> list[dict]:
        project_token = (filter_metadata or {}).get("project_token", "")

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, 1 - (embedding <=> $1::vector) AS score, metadata
                FROM memory_vectors
                WHERE project_token = $2
                ORDER BY embedding <=> $1::vector
                LIMIT $3
                """,
                query_vector,
                project_token,
                top_k,
            )

        return [
            {
                "id": row["id"],
                "score": float(row["score"]),
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
            }
            for row in rows
        ]

    async def delete(self, id: UUID) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute("DELETE FROM memory_vectors WHERE id = $1", id)
            return result == "DELETE 1"

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
